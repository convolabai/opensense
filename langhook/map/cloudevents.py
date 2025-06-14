"""CloudEvents wrapper and schema validation."""

from datetime import UTC, datetime
from typing import Any

import jsonschema
import structlog

logger = structlog.get_logger("langhook")


class CloudEventWrapper:
    """Wrapper for creating and validating CloudEvents."""

    def create_canonical_event(
        self,
        event_id: str,
        source: str,
        canonical_data: dict[str, Any],
        raw_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a canonical event in the new v1 format.

        Args:
            event_id: Unique event identifier
            source: Source identifier
            canonical_data: Canonical data from mapping {publisher, resource, action, ...}
            raw_payload: Original raw webhook payload

        Returns:
            Canonical event as dictionary (not CloudEvents wrapped)
        """

        # Create the canonical event in the new format
        canonical_event = {
            "publisher": canonical_data["publisher"],
            "resource": canonical_data["resource"],  # Now an object with type and id
            "action": canonical_data["action"],
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": raw_payload
        }

        return canonical_event

    def create_cloudevents_envelope(
        self,
        event_id: str,
        canonical_event: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Wrap canonical event in CloudEvents envelope for CNCF compatibility.

        Args:
            event_id: Unique event identifier
            canonical_event: Canonical event data

        Returns:
            CloudEvent envelope with canonical event as data
        """
        # Extract publisher and resource for CloudEvents attributes
        publisher = canonical_event["publisher"]
        resource = canonical_event["resource"]
        action = canonical_event["action"]

        # Create CloudEvent envelope
        cloud_event = {
            "id": event_id,
            "specversion": "1.0",
            "source": f"/{publisher}",
            "type": f"com.{publisher}.{resource['type']}.{action}",
            "subject": f"{resource['type']}/{resource['id']}",
            "time": canonical_event["timestamp"],
            "data": canonical_event
        }

        return cloud_event

    def validate_canonical_event(self, event: dict[str, Any]) -> bool:
        """
        Validate a canonical event against the JSON schema.

        Args:
            event: Canonical event dictionary to validate (not CloudEvents envelope)

        Returns:
            True if valid, False otherwise
        """
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "LangHook Canonical Event v1",
            "description": "Schema for LangHook canonical events with REST-aligned structure",
            "type": "object",
            "required": [
                "publisher",
                "resource",
                "action", 
                "timestamp",
                "payload"
            ],
            "properties": {
                "publisher": {
                    "type": "string",
                    "pattern": "^[a-z0-9_]+$",
                    "description": "Lowercase slug of the system (github, stripe, etc.)"
                },
                "resource": {
                    "type": "object",
                    "required": ["type", "id"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Singular noun (pull_request, issue, payment_intent)"
                        },
                        "id": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "integer"}
                            ],
                            "description": "Atomic identifier - no composite keys"
                        }
                    },
                    "additionalProperties": False,
                    "description": "One logical entity"
                },
                "action": {
                    "type": "string",
                    "enum": ["created", "read", "updated", "deleted"],
                    "description": "CRUD action enum in past tense"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO-8601 timestamp in UTC (YYYY-MM-DDTHH:mm:ssZ)"
                },
                "payload": {
                    "type": "object",
                    "description": "Entire original payload - no filtering"
                }
            },
            "additionalProperties": False
        }
        
        try:
            jsonschema.validate(event, schema)
            logger.debug("Canonical event validation passed", publisher=event.get("publisher"))
            return True
        except jsonschema.ValidationError as e:
            logger.error(
                "Canonical event validation failed",
                publisher=event.get("publisher"),
                error=str(e),
                path=".".join(str(p) for p in e.path) if e.path else None
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error during validation",
                publisher=event.get("publisher"),
                error=str(e),
                exc_info=True
            )
            return False

    def wrap_and_validate(
        self,
        event_id: str,
        source: str,
        canonical_data: dict[str, Any],
        raw_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create and validate a canonical event, then wrap in CloudEvents envelope.

        Args:
            event_id: Unique event identifier
            source: Source identifier
            canonical_data: Canonical data from mapping
            raw_payload: Original raw webhook payload

        Returns:
            CloudEvents envelope containing validated canonical event

        Raises:
            ValueError: If canonical event validation fails
        """
        # Create canonical event
        canonical_event = self.create_canonical_event(event_id, source, canonical_data, raw_payload)

        # Validate canonical event
        if not self.validate_canonical_event(canonical_event):
            raise ValueError("Failed to validate canonical event")

        # Wrap in CloudEvents envelope
        cloud_event = self.create_cloudevents_envelope(event_id, canonical_event)

        return cloud_event


# Global wrapper instance
cloud_event_wrapper = CloudEventWrapper()
