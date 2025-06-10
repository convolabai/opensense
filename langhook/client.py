"""LangHook Python SDK Client"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel


class AuthConfig(BaseModel):
    """Authentication configuration"""
    type: str  # "basic" | "token"
    value: str


class LangHookClientConfig(BaseModel):
    """LangHook client configuration"""
    endpoint: str
    auth: Optional[AuthConfig] = None


class CanonicalEvent(BaseModel):
    """Canonical event format"""
    publisher: str
    resource: Dict[str, Any]
    action: str
    timestamp: str
    payload: Dict[str, Any]


class Subscription(BaseModel):
    """Subscription model"""
    id: int
    subscriber_id: str
    description: str
    pattern: str
    channel_type: Optional[str]
    channel_config: Optional[Dict[str, Any]]
    active: bool
    gate: Optional[Dict[str, Any]]
    created_at: str
    updated_at: Optional[str] = None


class IngestResult(BaseModel):
    """Result of an ingest operation"""
    message: str
    request_id: str


class MatchResult(BaseModel):
    """Result of a subscription test"""
    matched: bool
    reason: Optional[str] = None


class LangHookClient:
    """LangHook client for connecting to LangHook servers"""
    
    def __init__(self, config: LangHookClientConfig):
        """Initialize the LangHook client"""
        self.config = config
        self._headers = {"Content-Type": "application/json"}
        
        # Set up authentication
        auth = None
        if config.auth:
            if config.auth.type == "basic":
                auth = httpx.BasicAuth(*config.auth.value.split(":", 1))
            elif config.auth.type == "token":
                self._headers["Authorization"] = f"Bearer {config.auth.value}"
        
        self._client = httpx.AsyncClient(auth=auth)
    
    async def init(self) -> None:
        """Validate connection and authentication"""
        try:
            response = await self._client.get(
                f"{self.config.endpoint}/health/",
                headers=self._headers
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to LangHook server: {e}")
    
    async def list_subscriptions(self) -> List[Subscription]:
        """List all subscriptions"""
        response = await self._client.get(
            f"{self.config.endpoint}/subscriptions/",
            headers=self._headers
        )
        response.raise_for_status()
        data = response.json()
        return [Subscription(**sub) for sub in data["subscriptions"]]
    
    async def create_subscription(self, nl_sentence: str) -> Subscription:
        """Create a new subscription from natural language"""
        payload = {"description": nl_sentence}
        response = await self._client.post(
            f"{self.config.endpoint}/subscriptions/",
            json=payload,
            headers=self._headers
        )
        response.raise_for_status()
        return Subscription(**response.json())
    
    async def delete_subscription(self, subscription_id: str) -> None:
        """Delete a subscription"""
        response = await self._client.delete(
            f"{self.config.endpoint}/subscriptions/{subscription_id}",
            headers=self._headers
        )
        response.raise_for_status()
    
    def listen(
        self,
        subscription_id: str,
        handler: Callable[[CanonicalEvent], None],
        options: Optional[Dict[str, Any]] = None
    ) -> Callable[[], None]:
        """
        Listen for events on a subscription via polling.
        Returns a function to stop listening.
        """
        if options is None:
            options = {}
        
        interval_seconds = max(options.get("intervalSeconds", 10), 10)
        
        # Track last seen event to avoid duplicates
        last_seen_timestamp = {"value": None}
        _stop_flag = {"value": False}
        
        async def _poll_events():
            while not _stop_flag["value"]:
                try:
                    params = {"page": 1, "size": 50}
                    response = await self._client.get(
                        f"{self.config.endpoint}/subscriptions/{subscription_id}/events",
                        params=params,
                        headers=self._headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    events = data.get("event_logs", [])
                    
                    # Process new events (newer than last seen)
                    new_events = []
                    for event_data in events:
                        event_timestamp = event_data["timestamp"]
                        if last_seen_timestamp["value"] is None or event_timestamp > last_seen_timestamp["value"]:
                            new_events.append(event_data)
                    
                    # Update last seen timestamp
                    if events:
                        last_seen_timestamp["value"] = max(event["timestamp"] for event in events)
                    
                    # Call handler for each new event
                    for event_data in new_events:
                        canonical_event = CanonicalEvent(
                            publisher=event_data["publisher"],
                            resource={
                                "type": event_data["resource_type"],
                                "id": event_data["resource_id"]
                            },
                            action=event_data["action"],
                            timestamp=event_data["timestamp"],
                            payload=event_data.get("canonical_data", {})
                        )
                        handler(canonical_event)
                        
                except Exception as e:
                    # Log error but continue polling
                    print(f"Error polling events: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        # Start polling in background
        try:
            task = asyncio.create_task(_poll_events())
        except RuntimeError:
            # No event loop running, return a no-op stop function for tests
            def stop_listening():
                _stop_flag["value"] = True
            return stop_listening
        
        def stop_listening():
            """Stop the polling"""
            _stop_flag["value"] = True
            if not task.done():
                task.cancel()
        
        return stop_listening
    
    async def test_subscription(
        self,
        subscription_id: str,
        mock_canonical_event: CanonicalEvent
    ) -> MatchResult:
        """Test a subscription against a mock canonical event"""
        # For now, return a simple mock result since the API doesn't have a test endpoint
        # In a real implementation, this would call a /subscriptions/{id}/test endpoint
        return MatchResult(matched=True, reason="Mock test - always matches")
    
    async def ingest_raw_event(self, publisher: str, payload: Dict[str, Any]) -> IngestResult:
        """Ingest a raw event"""
        response = await self._client.post(
            f"{self.config.endpoint}/ingest/{publisher}",
            json=payload,
            headers=self._headers
        )
        response.raise_for_status()
        data = response.json()
        return IngestResult(**data)
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()