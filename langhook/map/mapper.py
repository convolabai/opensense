"""JSONata mapping engine for transforming raw events to canonical format."""

from typing import Any

import jsonata
import structlog

from langhook.map.fingerprint import extract_type_skeleton, generate_fingerprint
from langhook.subscriptions.database import db_service

logger = structlog.get_logger("langhook")


class MappingEngine:
    """Engine for applying JSONata mappings from fingerprint-based database storage."""

    def __init__(self) -> None:
        # No longer loading file-based mappings
        pass

    async def apply_mapping(self, source: str, raw_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Apply JSONata mapping to transform raw payload to canonical format.

        Uses enhanced fingerprinting to find mappings that match both structure and event field.

        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload

        Returns:
            Canonical event dict or None if mapping fails
        """
        # Generate basic structure fingerprint for the payload
        structure_fingerprint = generate_fingerprint(raw_payload)

        logger.debug(
            "Generated payload structure fingerprint",
            source=source,
            fingerprint=structure_fingerprint
        )

        # First, try to find mappings with matching structure
        try:
            matching_mappings = await db_service.get_ingestion_mappings_by_structure(structure_fingerprint)

            if matching_mappings:
                logger.debug(
                    "Found mappings with matching structure",
                    source=source,
                    count=len(matching_mappings)
                )

                # Try to find a mapping where the event field matches
                from langhook.map.fingerprint import generate_enhanced_fingerprint

                for mapping in matching_mappings:
                    if mapping.event_field_expr:
                        # Generate enhanced fingerprint using this mapping's event field expression
                        enhanced_fingerprint = generate_enhanced_fingerprint(
                            raw_payload,
                            mapping.event_field_expr
                        )
                        if enhanced_fingerprint == mapping.fingerprint:
                            logger.debug(
                                "Found enhanced fingerprint match",
                                source=source,
                                fingerprint=enhanced_fingerprint,
                                event_field_expr=mapping.event_field_expr
                            )
                            return await self._apply_jsonata_mapping(mapping.mapping_expr, raw_payload, source)
                    else:
                        # No event field, check if basic fingerprint matches
                        if structure_fingerprint == mapping.fingerprint:
                            logger.debug(
                                "Found basic fingerprint match",
                                source=source,
                                fingerprint=structure_fingerprint
                            )
                            return await self._apply_jsonata_mapping(mapping.mapping_expr, raw_payload, source)

                logger.debug(
                    "No exact fingerprint match found among structure matches",
                    source=source
                )
            else:
                logger.debug(
                    "No mappings found with matching structure",
                    source=source,
                    structure_fingerprint=structure_fingerprint
                )

        except Exception as e:
            logger.warning(
                "Failed to lookup fingerprint mapping",
                source=source,
                fingerprint=structure_fingerprint,
                error=str(e)
            )

        # No fingerprint match found, return None to trigger LLM mapping generation
        logger.debug(
            "No fingerprint mapping found",
            source=source,
            fingerprint=structure_fingerprint
        )
        return None

    async def _apply_jsonata_mapping(self, mapping_expr: str, raw_payload: dict[str, Any], source: str) -> dict[str, Any] | None:
        """
        Apply a JSONata mapping expression to transform raw payload to canonical format.

        Args:
            mapping_expr: JSONata expression to apply
            raw_payload: Raw webhook payload
            source: Source identifier for logging

        Returns:
            Canonical event dict or None if mapping fails
        """
        try:
            # Apply JSONata transformation using the transform function
            result = jsonata.transform(mapping_expr, raw_payload)

            # Ensure result has required fields for new canonical format
            if not isinstance(result, dict):
                logger.error(
                    "Mapping result is not a dictionary",
                    source=source,
                    result_type=type(result).__name__
                )
                return None

            # Validate new canonical format requirements
            required_fields = ['publisher', 'resource', 'action']
            missing_fields = [field for field in required_fields if field not in result]

            if missing_fields:
                logger.error(
                    "Mapping result missing required fields",
                    source=source,
                    missing_fields=missing_fields,
                    result=result
                )
                return None

            # Validate resource structure
            if not isinstance(result.get('resource'), dict):
                logger.error(
                    "Resource must be an object with type and id fields",
                    source=source,
                    resource=result.get('resource')
                )
                return None

            resource = result['resource']
            if 'type' not in resource or 'id' not in resource:
                logger.error(
                    "Resource object missing type or id field",
                    source=source,
                    resource=resource
                )
                return None

            # Convert present tense actions to past tense for canonical format
            action_mapping = {
                'create': 'created',
                'update': 'updated',
                'delete': 'deleted',
                'read': 'read'
            }

            # Support both present and past tense input
            if result['action'] in action_mapping:
                result['action'] = action_mapping[result['action']]

            # Validate action is past tense CRUD enum
            valid_actions = ['created', 'read', 'updated', 'deleted']
            if result['action'] not in valid_actions:
                logger.error(
                    "Invalid action - must be one of: created, read, updated, deleted",
                    source=source,
                    action=result['action']
                )
                return None

            # Validate atomic ID (no composite keys with /, #, or space)
            resource_id = str(resource['id'])
            invalid_chars = ['/', '#', ' ']
            if any(char in resource_id for char in invalid_chars):
                logger.error(
                    "Resource ID contains invalid characters (/, #, space) - atomic IDs only",
                    source=source,
                    resource_id=resource_id
                )
                return None

            logger.debug(
                "Mapping applied successfully",
                source=source,
                result=result
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to apply mapping",
                source=source,
                error=str(e),
                exc_info=True
            )
            return None

    async def store_jsonata_mapping_with_event_field(
        self,
        source: str,
        raw_payload: dict[str, Any],
        jsonata_expr: str,
        event_field_expr: str | None = None
    ) -> None:
        """
        Store a JSONata mapping expression with event field expression in the database.

        Args:
            source: Source identifier
            raw_payload: Raw webhook payload
            jsonata_expr: JSONata expression that transforms payload to canonical format
            event_field_expr: Optional JSONata expression to extract event/action field
        """
        try:
            from langhook.map.fingerprint import (
                extract_type_skeleton,
                generate_enhanced_fingerprint,
            )

            # Generate enhanced fingerprint using event field expression
            fingerprint = generate_enhanced_fingerprint(raw_payload, event_field_expr)
            structure = extract_type_skeleton(raw_payload)

            # Test the JSONata expression to extract event name
            import jsonata
            canonical_result = jsonata.transform(jsonata_expr, raw_payload)

            if canonical_result and isinstance(canonical_result, dict):
                resource = canonical_result.get("resource", {})
                event_name = f"{resource.get('type', 'unknown')} {canonical_result.get('action', 'unknown')}"
            else:
                event_name = "unknown unknown"

            # Store in database with event field expression
            await db_service.create_ingestion_mapping(
                fingerprint=fingerprint,
                publisher=source,
                event_name=event_name,
                mapping_expr=jsonata_expr,
                structure=structure,
                event_field_expr=event_field_expr
            )

            logger.info(
                "Stored new JSONata mapping with event field",
                source=source,
                fingerprint=fingerprint,
                event_name=event_name,
                has_event_field_expr=event_field_expr is not None
            )

        except Exception as e:
            logger.error(
                "Failed to store JSONata mapping with event field",
                source=source,
                error=str(e),
                exc_info=True
            )

    async def store_jsonata_mapping(
        self,
        source: str,
        raw_payload: dict[str, Any],
        jsonata_expr: str
    ) -> None:
        """
        Store a JSONata mapping expression in the database.

        Args:
            source: Source identifier
            raw_payload: Raw webhook payload
            jsonata_expr: JSONata expression that transforms payload to canonical format
        """
        try:
            # Generate fingerprint and extract structure
            fingerprint = generate_fingerprint(raw_payload)
            structure = extract_type_skeleton(raw_payload)

            # Test the JSONata expression to extract event name
            import jsonata
            canonical_result = jsonata.transform(jsonata_expr, raw_payload)

            if canonical_result and isinstance(canonical_result, dict):
                resource = canonical_result.get("resource", {})
                event_name = f"{resource.get('type', 'unknown')} {canonical_result.get('action', 'unknown')}"
            else:
                event_name = "unknown unknown"

            # Store in database
            await db_service.create_ingestion_mapping(
                fingerprint=fingerprint,
                publisher=source,
                event_name=event_name,
                mapping_expr=jsonata_expr,
                structure=structure
            )

            logger.info(
                "Stored new JSONata mapping",
                source=source,
                fingerprint=fingerprint,
                event_name=event_name
            )

        except Exception as e:
            logger.error(
                "Failed to store JSONata mapping",
                source=source,
                error=str(e),
                exc_info=True
            )

# Global mapping engine instance
mapping_engine = MappingEngine()
