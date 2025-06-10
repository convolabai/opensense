"""Utilities for end-to-end testing."""

import asyncio
import os
import time
from typing import Any

import httpx
import nats
import redis
import structlog
from sqlalchemy import create_engine, text

logger = structlog.get_logger(__name__)


class E2ETestUtils:
    """Utilities for setting up and tearing down end-to-end tests."""

    def __init__(self):
        self.base_url = os.getenv("LANGHOOK_BASE_URL", "http://localhost:8000")
        self.nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.postgres_dsn = os.getenv(
            "POSTGRES_DSN", "postgresql://langhook:langhook@localhost:5432/langhook"
        )

        self.http_client: httpx.AsyncClient | None = None
        self.nats_client: nats.NATS | None = None
        self.redis_client: redis.Redis | None = None

    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up E2E test environment")

        # Wait for services to be ready
        await self.wait_for_services()

        # Initialize clients
        self.http_client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        self.nats_client = await nats.connect(self.nats_url)
        self.redis_client = redis.from_url(self.redis_url)

        # Clean up any existing test data
        await self.cleanup_test_data()

        logger.info("E2E test environment ready")

    async def teardown(self):
        """Tear down test environment."""
        logger.info("Tearing down E2E test environment")

        # Clean up test data
        await self.cleanup_test_data()

        # Close clients
        if self.http_client:
            await self.http_client.aclose()
        if self.nats_client:
            await self.nats_client.close()
        if self.redis_client:
            self.redis_client.close()

        logger.info("E2E test environment cleaned up")

    async def wait_for_services(self, timeout: int = 120):
        """Wait for all services to be ready."""
        logger.info("Waiting for services to be ready", timeout=timeout)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check HTTP health endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health/", timeout=5.0)
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "up":
                            logger.info("LangHook service is ready")
                            return
            except Exception as e:
                logger.debug("Service not ready yet", error=str(e))

            await asyncio.sleep(2)

        raise TimeoutError(f"Services not ready after {timeout} seconds")

    async def cleanup_test_data(self):
        """Clean up test data from all services."""
        logger.info("Cleaning up test data")

        try:
            # Clean up subscription database
            engine = create_engine(self.postgres_dsn)
            with engine.connect() as conn:
                # Delete test subscriptions
                conn.execute(text("DELETE FROM subscriptions WHERE subscriber_id = 'test-user'"))
                conn.execute(text("DELETE FROM subscriptions WHERE description LIKE '%E2E_TEST%'"))
                conn.commit()
        except Exception as e:
            logger.warning("Failed to clean up database", error=str(e))

        try:
            # Clean up Redis
            if self.redis_client:
                # Clean up rate limiting data
                for key in self.redis_client.scan_iter(match="rate_limit:*"):
                    self.redis_client.delete(key)
        except Exception as e:
            logger.warning("Failed to clean up Redis", error=str(e))

        # Note: NATS streams are typically persistent, but we could clean up specific subjects if needed

    async def create_test_subscription(
        self,
        description: str = "E2E_TEST webhook for pull requests",
        channel_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a test subscription."""
        if channel_config is None:
            channel_config = {
                "url": "http://test-webhook.example.com/webhook",
                "method": "POST"
            }

        payload = {
            "description": description,
            "channel_type": "webhook",
            "channel_config": channel_config
        }

        response = await self.http_client.post("/subscriptions/", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_test_event(
        self,
        source: str = "github",
        payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a test event to the ingest endpoint."""
        if payload is None:
            payload = {
                "action": "opened",
                "pull_request": {
                    "number": 123,
                    "title": "E2E Test PR",
                    "state": "open"
                },
                "repository": {
                    "name": "test-repo",
                    "id": 12345
                }
            }

        response = await self.http_client.post(
            f"/ingest/{source}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()

    async def wait_for_event_processing(self, event_id: str, timeout: int = 30):
        """Wait for an event to be processed through the mapping service."""
        logger.info("Waiting for event processing", event_id=event_id, timeout=timeout)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check if event was processed by looking at metrics
                response = await self.http_client.get("/map/metrics/json")
                if response.status_code == 200:
                    metrics = response.json()
                    if metrics.get("events_processed", 0) > 0:
                        logger.info("Event processing detected in metrics")
                        return True
            except Exception as e:
                logger.debug("Error checking event processing", error=str(e))

            await asyncio.sleep(1)

        logger.warning("Event processing timeout", event_id=event_id)
        return False

    async def get_subscription_by_id(self, subscription_id: int) -> dict[str, Any] | None:
        """Get a subscription by ID."""
        try:
            response = await self.http_client.get(f"/subscriptions/{subscription_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    async def list_subscriptions(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """List subscriptions."""
        response = await self.http_client.get(f"/subscriptions/?page={page}&size={size}")
        response.raise_for_status()
        return response.json()

    async def update_subscription(
        self,
        subscription_id: int,
        updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a subscription."""
        response = await self.http_client.put(f"/subscriptions/{subscription_id}", json=updates)
        response.raise_for_status()
        return response.json()

    async def delete_subscription(self, subscription_id: int) -> bool:
        """Delete a subscription."""
        response = await self.http_client.delete(f"/subscriptions/{subscription_id}")
        return response.status_code == 204

    async def check_health(self) -> dict[str, Any]:
        """Check service health."""
        response = await self.http_client.get("/health/")
        response.raise_for_status()
        return response.json()

    async def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        response = await self.http_client.get("/map/metrics/json")
        response.raise_for_status()
        return response.json()
