"""Payload fingerprinting for webhook mapping caching."""

import hashlib
import json
from typing import Any

import structlog

logger = structlog.get_logger("langhook")


def extract_type_skeleton(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the type skeleton from a payload, ignoring values and keeping only structure.

    Args:
        payload: Raw webhook payload

    Returns:
        Type skeleton with only keys and value types
    """
    if not isinstance(payload, dict):
        return {}

    skeleton = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            skeleton[key] = extract_type_skeleton(value)
        elif isinstance(value, list):
            # For lists, take the type of the first element if it exists
            if value and isinstance(value[0], dict):
                skeleton[key] = [extract_type_skeleton(value[0])]
            elif value:
                skeleton[key] = [_normalize_type_name(type(value[0]))]
            else:
                skeleton[key] = []
        else:
            skeleton[key] = _normalize_type_name(type(value))

    return skeleton


def _normalize_type_name(python_type: type) -> str:
    """
    Convert Python type to normalized type name for JSON Schema-like representation.

    Args:
        python_type: Python type object

    Returns:
        Normalized type name string
    """
    type_mapping = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        type(None): "null"
    }

    return type_mapping.get(python_type, python_type.__name__)


def create_canonical_string(skeleton: dict[str, Any]) -> str:
    """
    Create a canonical string representation by sorting keys lexicographically.

    Args:
        skeleton: Type skeleton from extract_type_skeleton

    Returns:
        Canonical string representation
    """
    return json.dumps(skeleton, sort_keys=True, separators=(',', ':'))


def generate_fingerprint(payload: dict[str, Any]) -> str:
    """
    Generate a SHA-256 fingerprint for a webhook payload based on its structure.

    Args:
        payload: Raw webhook payload

    Returns:
        64-character hexadecimal SHA-256 fingerprint
    """
    skeleton = extract_type_skeleton(payload)
    canonical_string = create_canonical_string(skeleton)

    fingerprint = hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()
    return fingerprint


def generate_enhanced_fingerprint(
    payload: dict[str, Any],
    event_field_expr: str | None = None
) -> str:
    """
    Generate an enhanced SHA-256 fingerprint that includes both structure and event field value.

    Args:
        payload: Raw webhook payload
        event_field_expr: JSONata expression to extract event/action field (e.g., "action")

    Returns:
        64-character hexadecimal SHA-256 fingerprint
    """
    # Start with the base structure fingerprint
    skeleton = extract_type_skeleton(payload)
    canonical_string = create_canonical_string(skeleton)

    # If event field expression is provided, extract the event value and include it
    if event_field_expr:
        try:
            import jsonata
            event_value = jsonata.transform(event_field_expr, payload)

            # Convert event value to string and append to canonical string
            if event_value is not None:
                event_str = str(event_value)
                # Use a separator to distinguish between structure and event value
                canonical_string = f"{canonical_string}||event:{event_str}"

                logger.debug(
                    "Enhanced fingerprint includes event field",
                    event_field_expr=event_field_expr,
                    event_value=event_value
                )
            else:
                logger.warning(
                    "Event field expression returned None",
                    event_field_expr=event_field_expr
                )
        except Exception as e:
            logger.warning(
                "Failed to extract event field for enhanced fingerprint",
                event_field_expr=event_field_expr,
                error=str(e)
            )
            # Fall back to structure-only fingerprint

    fingerprint = hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()
    return fingerprint
