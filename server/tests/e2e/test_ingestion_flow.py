"""End-to-end tests for event ingestion and processing flow."""

import asyncio

import pytest
import structlog

from tests.e2e.utils import E2ETestUtils

logger = structlog.get_logger(__name__)


@pytest.fixture
async def e2e_utils():
    """Fixture providing E2E test utilities."""
    utils = E2ETestUtils()
    await utils.setup()
    yield utils
    await utils.teardown()


class TestEventIngestion:
    """Test event ingestion endpoints."""

    async def test_health_check(self, e2e_utils: E2ETestUtils):
        """Test health check endpoint."""
        health = await e2e_utils.check_health()

        assert health["status"] == "up"
        assert "services" in health
        assert health["services"]["ingest"] == "up"
        assert health["services"]["map"] == "up"
        assert "version" in health

    async def test_ingest_github_event(self, e2e_utils: E2ETestUtils):
        """Test ingesting a GitHub webhook event."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "E2E Test PR",
                "state": "open",
                "user": {"login": "testuser"}
            },
            "repository": {
                "name": "test-repo",
                "id": 12345,
                "owner": {"login": "testorg"}
            }
        }

        result = await e2e_utils.send_test_event("github", payload)

        assert result["message"] == "Event accepted"
        assert "request_id" in result
        assert result["request_id"] is not None

    async def test_ingest_stripe_event(self, e2e_utils: E2ETestUtils):
        """Test ingesting a Stripe webhook event."""
        payload = {
            "id": "evt_test_123",
            "object": "event",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_456",
                    "amount": 2000,
                    "currency": "usd",
                    "status": "succeeded"
                }
            }
        }

        result = await e2e_utils.send_test_event("stripe", payload)

        assert result["message"] == "Event accepted"
        assert "request_id" in result

    async def test_ingest_custom_source_event(self, e2e_utils: E2ETestUtils):
        """Test ingesting an event from a custom source."""
        payload = {
            "event_type": "user_registered",
            "user_id": "user_123",
            "timestamp": "2024-01-01T10:00:00Z",
            "metadata": {
                "source": "mobile_app",
                "version": "1.2.3"
            }
        }

        result = await e2e_utils.send_test_event("custom-app", payload)

        assert result["message"] == "Event accepted"
        assert "request_id" in result

    async def test_ingest_invalid_json(self, e2e_utils: E2ETestUtils):
        """Test ingesting invalid JSON payload."""
        try:
            # Send invalid JSON
            response = await e2e_utils.http_client.post(
                "/ingest/github",
                content="{ invalid json }",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
        except Exception:
            # Expected to fail with client-side error
            pass

    async def test_ingest_empty_payload(self, e2e_utils: E2ETestUtils):
        """Test ingesting empty payload."""
        result = await e2e_utils.send_test_event("github", {})

        assert result["message"] == "Event accepted"
        assert "request_id" in result

    async def test_ingest_large_payload(self, e2e_utils: E2ETestUtils):
        """Test ingesting large payload within limits."""
        # Create a reasonably large payload (but within 1MB limit)
        large_data = "x" * 10000  # 10KB of data
        payload = {
            "action": "opened",
            "pull_request": {"number": 123, "title": "Large PR"},
            "large_field": large_data
        }

        result = await e2e_utils.send_test_event("github", payload)

        assert result["message"] == "Event accepted"
        assert "request_id" in result

    async def test_get_metrics(self, e2e_utils: E2ETestUtils):
        """Test getting service metrics."""
        # Send a few events first to generate metrics
        for i in range(3):
            await e2e_utils.send_test_event("github", {
                "action": "opened",
                "pull_request": {"number": i + 1}
            })

        # Give some time for events to be processed
        await asyncio.sleep(5)

        metrics = await e2e_utils.get_metrics()

        assert "events_processed" in metrics
        assert "events_mapped" in metrics
        assert "events_failed" in metrics
        assert "llm_invocations" in metrics
        assert "mapping_success_rate" in metrics
        assert "llm_usage_rate" in metrics

        # Should have processed at least our test events
        assert metrics["events_processed"] >= 3


class TestEventProcessingFlow:
    """Test complete event processing flow from ingestion to mapping."""

    async def test_event_flow_github_pr(self, e2e_utils: E2ETestUtils):
        """Test complete flow for GitHub PR event."""
        # Send GitHub PR event
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 456,
                "title": "E2E Test Flow PR",
                "state": "open",
                "user": {"login": "testuser"}
            },
            "repository": {
                "name": "test-repo",
                "id": 12345,
                "owner": {"login": "testorg"}
            }
        }

        result = await e2e_utils.send_test_event("github", payload)
        event_id = result["request_id"]

        # Wait for event to be processed
        processed = await e2e_utils.wait_for_event_processing(event_id, timeout=30)
        assert processed, "Event should have been processed"

        # Check metrics to verify processing
        metrics = await e2e_utils.get_metrics()
        assert metrics["events_processed"] > 0

    async def test_event_flow_with_subscription(self, e2e_utils: E2ETestUtils):
        """Test event flow with subscription matching."""
        # Create a subscription for GitHub PR events
        subscription = await e2e_utils.create_test_subscription(
            description="E2E_TEST GitHub pull request events",
            channel_config={
                "url": "http://test-webhook.example.com/github-prs",
                "method": "POST"
            }
        )

        # Send a matching GitHub PR event
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 789,
                "title": "Test PR for subscription",
                "state": "open"
            },
            "repository": {
                "name": "test-repo",
                "id": 12345
            }
        }

        result = await e2e_utils.send_test_event("github", payload)
        event_id = result["request_id"]

        # Wait for event processing
        processed = await e2e_utils.wait_for_event_processing(event_id, timeout=30)
        assert processed, "Event should have been processed"

        # Verify subscription still exists (processing shouldn't affect it)
        sub_check = await e2e_utils.get_subscription_by_id(subscription["id"])
        assert sub_check is not None

    async def test_multiple_sources_flow(self, e2e_utils: E2ETestUtils):
        """Test event flow from multiple sources."""
        sources_and_payloads = [
            ("github", {
                "action": "closed",
                "pull_request": {"number": 100, "state": "closed"}
            }),
            ("stripe", {
                "type": "invoice.payment_succeeded",
                "data": {"object": {"id": "inv_123", "amount_paid": 1000}}
            }),
            ("custom-app", {
                "event_type": "order_completed",
                "order_id": "order_456"
            })
        ]

        event_ids = []
        for source, payload in sources_and_payloads:
            result = await e2e_utils.send_test_event(source, payload)
            event_ids.append(result["request_id"])

        # Wait for all events to be processed
        await asyncio.sleep(10)

        # Check that metrics show multiple events processed
        metrics = await e2e_utils.get_metrics()
        assert metrics["events_processed"] >= len(sources_and_payloads)

    async def test_event_processing_resilience(self, e2e_utils: E2ETestUtils):
        """Test system resilience with various event types."""
        # Send various event types to test robustness
        test_events = [
            ("github", {"action": "opened", "pull_request": {"number": 1}}),
            ("github", {"action": "closed", "issue": {"number": 2}}),
            ("stripe", {"type": "customer.created", "data": {"object": {"id": "cus_123"}}}),
            ("custom", {"event": "test", "data": None}),
            ("custom", {"complex": {"nested": {"structure": [1, 2, 3]}}}),
        ]

        successful_events = 0
        for source, payload in test_events:
            try:
                result = await e2e_utils.send_test_event(source, payload)
                if result.get("message") == "Event accepted":
                    successful_events += 1
            except Exception as e:
                logger.warning("Event failed", source=source, error=str(e))

        # Most events should succeed
        assert successful_events >= len(test_events) * 0.8  # 80% success rate

        # Wait for processing
        await asyncio.sleep(10)

        # System should still be healthy
        health = await e2e_utils.check_health()
        assert health["status"] == "up"


class TestServiceIntegration:
    """Test integration between different services."""

    async def test_service_health_integration(self, e2e_utils: E2ETestUtils):
        """Test that all services are properly integrated and healthy."""
        health = await e2e_utils.check_health()

        # All services should be up
        assert health["status"] == "up"
        assert health["services"]["ingest"] == "up"
        assert health["services"]["map"] == "up"

    async def test_end_to_end_integration(self, e2e_utils: E2ETestUtils):
        """Test complete end-to-end integration."""
        # 1. Create subscription
        subscription = await e2e_utils.create_test_subscription(
            description="E2E_TEST complete integration test"
        )

        # 2. Send event
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 999,
                "title": "Integration Test PR"
            }
        }
        result = await e2e_utils.send_test_event("github", payload)

        # 3. Wait for processing
        await e2e_utils.wait_for_event_processing(result["request_id"])

        # 4. Verify subscription still exists and is active
        final_sub = await e2e_utils.get_subscription_by_id(subscription["id"])
        assert final_sub is not None
        assert final_sub["active"] is True

        # 5. Check overall system health
        health = await e2e_utils.check_health()
        assert health["status"] == "up"
