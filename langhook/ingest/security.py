"""Security utilities for HMAC signature verification."""

import hashlib
import hmac
from typing import Any

import structlog

from langhook.ingest.config import settings

logger = structlog.get_logger("langhook")


async def verify_signature(
    source: str,
    body_bytes: bytes,
    headers: dict[str, Any],
) -> bool | None:
    """
    Verify HMAC signature for a webhook request.
    
    Args:
        source: Source identifier (e.g., 'github', 'stripe')
        body_bytes: Raw request body bytes
        headers: Request headers
    
    Returns:
        bool: True if signature is valid, False if invalid, None if no secret configured
    """
    secret = settings.get_secret(source)
    if not secret:
        logger.debug("No HMAC secret configured for source", source=source)
        return None

    # GitHub-style signature verification
    if source.lower() == "github":
        return _verify_github_signature(body_bytes, headers, secret)

    # Stripe-style signature verification
    elif source.lower() == "stripe":
        return _verify_stripe_signature(body_bytes, headers, secret)

    # Generic signature verification
    else:
        return _verify_generic_signature(body_bytes, headers, secret)


def _verify_github_signature(
    body_bytes: bytes,
    headers: dict[str, Any],
    secret: str,
) -> bool:
    """Verify GitHub-style HMAC signature."""
    # GitHub sends X-Hub-Signature-256 header
    signature_header = headers.get("x-hub-signature-256")
    if not signature_header:
        # Fallback to legacy SHA-1
        signature_header = headers.get("x-hub-signature")
        if not signature_header:
            logger.warning("No GitHub signature header found")
            return False

        # SHA-1 verification
        expected_sig = "sha1=" + hmac.new(
            secret.encode(),
            body_bytes,
            hashlib.sha1,
        ).hexdigest()
    else:
        # SHA-256 verification
        expected_sig = "sha256=" + hmac.new(
            secret.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

    return hmac.compare_digest(signature_header, expected_sig)


def _verify_stripe_signature(
    body_bytes: bytes,
    headers: dict[str, Any],
    secret: str,
) -> bool:
    """Verify Stripe-style HMAC signature."""
    # Stripe sends Stripe-Signature header
    signature_header = headers.get("stripe-signature")
    if not signature_header:
        logger.warning("No Stripe signature header found")
        return False

    # Parse Stripe signature format: t=timestamp,v1=signature
    sig_elements = {}
    for element in signature_header.split(","):
        key, value = element.split("=", 1)
        sig_elements[key] = value

    timestamp = sig_elements.get("t")
    signature = sig_elements.get("v1")

    if not timestamp or not signature:
        logger.warning("Invalid Stripe signature format")
        return False

    # Stripe payload is timestamp + "." + body
    payload = f"{timestamp}.{body_bytes.decode()}"
    expected_sig = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_sig)


def _verify_generic_signature(
    body_bytes: bytes,
    headers: dict[str, Any],
    secret: str,
) -> bool:
    """Verify generic HMAC signature."""
    # Look for common signature headers
    signature_header = (
        headers.get("x-webhook-signature") or
        headers.get("x-signature") or
        headers.get("signature")
    )

    if not signature_header:
        logger.warning("No signature header found for generic verification")
        return False

    # Try SHA-256 first
    if signature_header.startswith("sha256="):
        expected_sig = "sha256=" + hmac.new(
            secret.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature_header, expected_sig)

    # Try SHA-1
    elif signature_header.startswith("sha1="):
        expected_sig = "sha1=" + hmac.new(
            secret.encode(),
            body_bytes,
            hashlib.sha1,
        ).hexdigest()
        return hmac.compare_digest(signature_header, expected_sig)

    # Direct hex comparison (assume SHA-256)
    else:
        expected_sig = hmac.new(
            secret.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature_header, expected_sig)
