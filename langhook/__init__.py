"""LangHook - Make any event from anywhere instantly understandable and actionable by anyone

This package provides both the LangHook Python SDK for connecting to LangHook servers
and the server components for running a LangHook instance.

To use the SDK only:
    from langhook import LangHookClient, LangHookClientConfig

To run the server:
    pip install langhook[server]
    langhook
"""

# SDK exports
from .client import (
    LangHookClient, 
    LangHookClientConfig, 
    AuthConfig,
    CanonicalEvent,
    Subscription,
    IngestResult,
    MatchResult
)

__version__ = "0.3.0"

# SDK components are always available
__all__ = [
    "LangHookClient", 
    "LangHookClientConfig", 
    "AuthConfig",
    "CanonicalEvent",
    "Subscription", 
    "IngestResult",
    "MatchResult"
]
