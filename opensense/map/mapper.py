"""JSONata mapping engine for transforming raw events to canonical format."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import jsonata

from opensense.map.config import settings

logger = structlog.get_logger()


class MappingEngine:
    """Engine for loading and applying JSONata mappings."""
    
    def __init__(self) -> None:
        self._mappings: Dict[str, str] = {}
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
                with open(mapping_file, 'r') as f:
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
    
    def get_mapping(self, source: str) -> Optional[str]:
        """Get JSONata mapping expression for a source."""
        return self._mappings.get(source)
    
    def has_mapping(self, source: str) -> bool:
        """Check if mapping exists for a source."""
        return source in self._mappings
    
    def apply_mapping(self, source: str, raw_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply JSONata mapping to transform raw payload to canonical format.
        
        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload
            
        Returns:
            Canonical five-tuple dict or None if mapping fails
        """
        mapping_expr = self.get_mapping(source)
        if not mapping_expr:
            logger.debug(
                "No mapping found for source",
                source=source
            )
            return None
        
        try:
            # Apply JSONata transformation using the transform function
            result = jsonata.transform(mapping_expr, raw_payload)
            
            # Ensure result has required fields
            if not isinstance(result, dict):
                logger.error(
                    "Mapping result is not a dictionary",
                    source=source,
                    result_type=type(result).__name__
                )
                return None
            
            required_fields = ['publisher', 'resource', 'action', 'key', 'value']
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                logger.error(
                    "Mapping result missing required fields",
                    source=source,
                    missing_fields=missing_fields,
                    result=result
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
    
    def reload_mappings(self) -> None:
        """Reload all mappings from disk."""
        self._mappings.clear()
        self._load_mappings()
        logger.info("Mappings reloaded", mapping_count=len(self._mappings))


# Global mapping engine instance
mapping_engine = MappingEngine()