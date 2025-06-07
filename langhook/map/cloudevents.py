"""CloudEvents wrapper and schema validation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema
import structlog

logger = structlog.get_logger("langhook")


class CloudEventWrapper:
    """Wrapper for creating and validating CloudEvents."""

    def __init__(self) -> None:
        self._schema = self._load_schema()

    def _load_schema(self) -> dict[str, Any]:
        """Load the canonical event JSON schema."""
        # Get the project root directory
        current_file = Path(__file__)
        # langhook/map/cloudevents.py -> langhook/map -> langhook -> project_root -> schemas
        project_root = current_file.parent.parent.parent
        schema_path = project_root / "schemas" / "canonical_event_v1.json"

        try:
            with open(schema_path) as f:
                schema = json.load(f)
            logger.info("Loaded canonical event schema", schema_path=str(schema_path))
            return schema
        except Exception as e:
            logger.error(
                "Failed to load canonical event schema",
                schema_path=str(schema_path),
                error=str(e),
                exc_info=True
            )
            raise

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
        try:
            jsonschema.validate(event, self._schema)
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
