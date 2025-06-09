"""JSONata mapping engine for transforming raw events to canonical format."""

from pathlib import Path
from typing import Any

import jsonata
import structlog

from langhook.map.config import settings
from langhook.map.fingerprint import generate_fingerprint
from langhook.subscriptions.database import db_service

logger = structlog.get_logger("langhook")


class MappingEngine:
    """Engine for loading and applying JSONata mappings."""

    def __init__(self) -> None:
        self._mappings: dict[str, str] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load all JSONata mapping files from the mappings directory."""
        mappings_path = Path(settings.mappings_dir)
        if not mappings_path.exists():
            logger.warning(
                "Mappings directory does not exist",
                mappings_dir=settings.mappings_dir
            )
            return

        for mapping_file in mappings_path.glob("*.jsonata"):
            source = mapping_file.stem  # filename without extension
            try:
                with open(mapping_file) as f:
                    jsonata_expression = f.read().strip()

                # Store the JSONata expression string
                self._mappings[source] = jsonata_expression

                logger.info(
                    "Loaded mapping",
                    source=source,
                    file=str(mapping_file)
                )
            except Exception as e:
                logger.error(
                    "Failed to load mapping",
                    source=source,
                    file=str(mapping_file),
                    error=str(e),
                    exc_info=True
                )

    def get_mapping(self, source: str) -> str | None:
        """Get JSONata mapping expression for a source."""
        return self._mappings.get(source)

    def has_mapping(self, source: str) -> bool:
        """Check if mapping exists for a source."""
        return source in self._mappings

    async def apply_mapping(self, source: str, raw_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Apply JSONata mapping to transform raw payload to canonical format.
        
        First checks fingerprint-based mappings in database, then falls back to file-based mappings.
        
        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload
            
        Returns:
            Canonical event dict or None if mapping fails
        """
        # Generate fingerprint for the payload
        fingerprint = generate_fingerprint(raw_payload)
        
        logger.debug(
            "Generated payload fingerprint",
            source=source,
            fingerprint=fingerprint
        )
        
        # First, try to get mapping from database using fingerprint
        try:
            webhook_mapping = await db_service.get_webhook_mapping(fingerprint)
            if webhook_mapping:
                logger.debug(
                    "Found fingerprint-based mapping",
                    source=source,
                    fingerprint=fingerprint,
                    publisher=webhook_mapping.publisher
                )
                
                return await self._apply_jsonata_mapping(webhook_mapping.mapping_expr, raw_payload, source)
        except Exception as e:
            logger.warning(
                "Failed to lookup fingerprint mapping",
                source=source,
                fingerprint=fingerprint,
                error=str(e)
            )
        
        # Fallback to file-based mapping if no fingerprint match
        mapping_expr = self.get_mapping(source)
        if not mapping_expr:
            logger.debug(
                "No mapping found for source",
                source=source,
                fingerprint=fingerprint
            )
            return None

        return await self._apply_jsonata_mapping(mapping_expr, raw_payload, source)

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

    async def store_mapping_from_canonical(
        self,
        source: str,
        raw_payload: dict[str, Any],
        canonical_data: dict[str, Any]
    ) -> None:
        """
        Store a mapping generated from canonical data in the database.
        
        Args:
            source: Source identifier  
            raw_payload: Raw webhook payload
            canonical_data: Canonical data produced by LLM
        """
        try:
            from langhook.map.jsonata_generator import generate_jsonata_from_canonical
            
            # Generate fingerprint
            fingerprint = generate_fingerprint(raw_payload)
            
            # Generate JSONata expression
            jsonata_expr = generate_jsonata_from_canonical(canonical_data, raw_payload)
            
            # Create event name from canonical data
            resource = canonical_data.get("resource", {})
            event_name = f"{resource.get('type', 'unknown')} {canonical_data.get('action', 'unknown')}"
            
            # Store in database
            await db_service.create_webhook_mapping(
                fingerprint=fingerprint,
                publisher=source,
                event_name=event_name,
                mapping_expr=jsonata_expr
            )
            
            logger.info(
                "Stored new mapping from canonical data",
                source=source,
                fingerprint=fingerprint,
                event_name=event_name
            )
            
        except Exception as e:
            logger.error(
                "Failed to store mapping from canonical data",
                source=source,
                error=str(e),
                exc_info=True
            )

    def reload_mappings(self) -> None:
        """Reload all mappings from disk."""
        self._mappings.clear()
        self._load_mappings()
        logger.info("Mappings reloaded", mapping_count=len(self._mappings))


# Global mapping engine instance
mapping_engine = MappingEngine()
