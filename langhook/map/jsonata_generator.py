"""Utility to generate JSONata expressions from canonical data and raw payloads."""

import json
from typing import Any


def generate_jsonata_from_canonical(
    canonical_data: dict[str, Any], 
    raw_payload: dict[str, Any]
) -> str:
    """
    Generate a JSONata expression that would transform raw_payload to canonical_data.
    
    This is a simplified approach that creates a static JSONata expression.
    For more complex cases, this could be enhanced with field mapping detection.
    
    Args:
        canonical_data: The canonical format data we want to produce
        raw_payload: The raw payload that should be transformed
        
    Returns:
        JSONata expression string
    """
    # Extract the key information from canonical data
    publisher = canonical_data.get("publisher")
    resource = canonical_data.get("resource", {})
    resource_type = resource.get("type")
    resource_id = resource.get("id")
    action = canonical_data.get("action")
    
    # Try to find the source of resource_id in the raw payload
    id_path = _find_value_path(raw_payload, resource_id)
    if not id_path:
        # Fallback to common patterns
        id_path = _guess_id_path(raw_payload, resource_type)
    
    # Try to find the source of action in the raw payload
    action_path = _find_action_path(raw_payload, action)
    
    # Build the JSONata expression
    jsonata_parts = [
        f'"publisher": "{publisher}"',
        f'"resource": {{"type": "{resource_type}", "id": {id_path}}}',
        f'"action": "{action}"'
    ]
    
    # Include additional fields if they exist in canonical data
    for key, value in canonical_data.items():
        if key not in ["publisher", "resource", "action"]:
            if isinstance(value, str):
                # Try to find the source path or use literal
                source_path = _find_value_path(raw_payload, value)
                if source_path:
                    jsonata_parts.append(f'"{key}": {source_path}')
                else:
                    jsonata_parts.append(f'"{key}": "{value}"')
            else:
                # For non-string values, serialize as JSON
                jsonata_parts.append(f'"{key}": {json.dumps(value)}')
    
    jsonata_expr = "{" + ", ".join(jsonata_parts) + "}"
    return jsonata_expr


def _find_value_path(data: dict[str, Any], target_value: Any, path: str = "") -> str | None:
    """
    Find the JSONata path to a value in nested data.
    
    Args:
        data: Data to search in
        target_value: Value to find
        path: Current path (used for recursion)
        
    Returns:
        JSONata path string or None if not found
    """
    if not isinstance(data, dict):
        return None
    
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        
        if value == target_value:
            return current_path
        elif isinstance(value, dict):
            result = _find_value_path(value, target_value, current_path)
            if result:
                return result
        elif isinstance(value, list) and value:
            # For lists, check the first item
            if isinstance(value[0], dict):
                result = _find_value_path(value[0], target_value, f"{current_path}[0]")
                if result:
                    # Remove the [0] index for general case
                    return result.replace("[0]", "")
    
    return None


def _guess_id_path(raw_payload: dict[str, Any], resource_type: str) -> str:
    """
    Guess the ID path based on common patterns.
    
    Args:
        raw_payload: Raw payload to analyze
        resource_type: Type of resource
        
    Returns:
        Likely JSONata path for the ID
    """
    # Common patterns for different resource types
    common_patterns = {
        "pull_request": ["pull_request.number", "pull_request.id", "number", "id"],
        "issue": ["issue.number", "issue.id", "number", "id"],
        "repository": ["repository.id", "repo.id", "id"],
        "user": ["user.id", "sender.id", "id"],
        "commit": ["head_commit.id", "commit.id", "sha", "id"],
    }
    
    patterns = common_patterns.get(resource_type, ["id"])
    
    # Try each pattern
    for pattern in patterns:
        if _path_exists(raw_payload, pattern):
            return pattern
    
    # Default fallback
    return "id"


def _find_action_path(raw_payload: dict[str, Any], canonical_action: str) -> str:
    """
    Find the source of the action in the raw payload.
    
    Args:
        raw_payload: Raw payload to search
        canonical_action: The canonical action (created, updated, etc.)
        
    Returns:
        JSONata expression for the action
    """
    # Map canonical actions back to common webhook actions
    action_mappings = {
        "created": ["opened", "created", "added"],
        "updated": ["edited", "updated", "modified"],
        "deleted": ["closed", "deleted", "removed"],
        "read": ["viewed", "read", "accessed"]
    }
    
    possible_actions = action_mappings.get(canonical_action, [canonical_action])
    
    # Look for action field in the payload
    if "action" in raw_payload and raw_payload["action"] in possible_actions:
        # Use a mapping expression to convert to canonical form
        return f'action = "opened" ? "created" : action = "edited" ? "updated" : action = "closed" ? "deleted" : "read"'
    
    # Fallback to literal value
    return f'"{canonical_action}"'


def _path_exists(data: dict[str, Any], path: str) -> bool:
    """
    Check if a JSONata-style path exists in the data.
    
    Args:
        data: Data to check
        path: Dot-notation path (e.g., "pull_request.number")
        
    Returns:
        True if path exists, False otherwise
    """
    try:
        current = data
        for part in path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        return True
    except (KeyError, TypeError):
        return False