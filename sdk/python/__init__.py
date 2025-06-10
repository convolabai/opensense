"""LangHook Python SDK

A Python client library for connecting to LangHook servers.
"""

from .client import (
    LangHookClient, 
    LangHookClientConfig, 
    AuthConfig,
    CanonicalEvent,
    Subscription,
    IngestResult,
    MatchResult
)

__version__ = "0.1.0"
__all__ = [
    "LangHookClient", 
    "LangHookClientConfig", 
    "AuthConfig",
    "CanonicalEvent",
    "Subscription", 
    "IngestResult",
    "MatchResult"
]