"""CloudEvents wrapper and schema validation."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import jsonschema
import structlog
from cloudevents.http import CloudEvent

logger = structlog.get_logger()


class CloudEventWrapper:
    """Wrapper for creating and validating CloudEvents."""
    
    def __init__(self) -> None:
        self._schema = self._load_schema()
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load the canonical event JSON schema."""
        # Get the project root directory 
        current_file = Path(__file__)
        # opensense/map/cloudevents.py -> opensense/map -> opensense -> project_root -> schemas
        project_root = current_file.parent.parent.parent
        schema_path = project_root / "schemas" / "canonical_event_v1.json"
        
        try:
            with open(schema_path, 'r') as f:
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
        canonical_data: Dict[str, Any],
        raw_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a canonical CloudEvent.
        
        Args:
            event_id: Unique event identifier
            source: Source identifier  
            canonical_data: Five-tuple from mapping {publisher, resource, action, key, value}
            raw_payload: Original raw webhook payload
            
        Returns:
            CloudEvent as dictionary
        """
        # Prepare the data section
        data = {
            "publisher": canonical_data["publisher"],
            "resource": canonical_data["resource"], 
            "action": canonical_data["action"],
            "key": canonical_data["key"],
            "value": canonical_data["value"],
            "raw": raw_payload
        }
        
        # Create CloudEvent
        event_dict = {
            "id": event_id,
            "specversion": "1.0",
            "source": f"/{canonical_data['publisher']}",
            "type": "com.opensense.event",
            "time": datetime.now(timezone.utc).isoformat(),
            "schema_version": 1,
            "data": data
        }
        
        return event_dict
    
    def validate_canonical_event(self, event: Dict[str, Any]) -> bool:
        """
        Validate a canonical event against the JSON schema.
        
        Args:
            event: Event dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            jsonschema.validate(event, self._schema)
            logger.debug("Event validation passed", event_id=event.get("id"))
            return True
        except jsonschema.ValidationError as e:
            logger.error(
                "Event validation failed",
                event_id=event.get("id"),
                error=str(e),
                path=".".join(str(p) for p in e.path) if e.path else None
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error during validation",
                event_id=event.get("id"),
                error=str(e),
                exc_info=True
            )
            return False
    
    def wrap_and_validate(
        self,
        event_id: str,
        source: str,
        canonical_data: Dict[str, Any],
        raw_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and validate a canonical CloudEvent.
        
        Args:
            event_id: Unique event identifier
            source: Source identifier
            canonical_data: Five-tuple from mapping
            raw_payload: Original raw webhook payload
            
        Returns:
            Validated CloudEvent as dictionary
            
        Raises:
            ValueError: If event validation fails
        """
        event = self.create_canonical_event(event_id, source, canonical_data, raw_payload)
        
        if not self.validate_canonical_event(event):
            raise ValueError("Failed to validate canonical event")
        
        return event


# Global wrapper instance
cloud_event_wrapper = CloudEventWrapper()