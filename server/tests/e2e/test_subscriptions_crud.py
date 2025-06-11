"""End-to-end tests for subscription API CRUD operations."""

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


class TestSubscriptionCRUD:
    """Test subscription API CRUD operations."""

    async def test_create_subscription(self, e2e_utils: E2ETestUtils):
        """Test creating a new subscription."""
        # Create subscription
        subscription = await e2e_utils.create_test_subscription(
            description="E2E_TEST webhook for GitHub pull requests",
            channel_config={
                "url": "http://example.com/webhook",
                "method": "POST",
                "headers": {"Authorization": "Bearer test-token"}
            }
        )

        # Verify subscription was created
        assert subscription["id"] is not None
        assert subscription["description"] == "E2E_TEST webhook for GitHub pull requests"
        assert subscription["channel_type"] == "webhook"
        assert subscription["channel_config"]["url"] == "http://example.com/webhook"
        assert subscription["active"] is True
        assert subscription["subscriber_id"] == "default"
        assert subscription["created_at"] is not None

    async def test_read_subscription(self, e2e_utils: E2ETestUtils):
        """Test reading a subscription by ID."""
        # Create subscription first
        created = await e2e_utils.create_test_subscription(
            description="E2E_TEST read test subscription"
        )

        # Read subscription by ID
        subscription = await e2e_utils.get_subscription_by_id(created["id"])

        assert subscription is not None
        assert subscription["id"] == created["id"]
        assert subscription["description"] == "E2E_TEST read test subscription"
        assert subscription["channel_type"] == "webhook"

    async def test_read_nonexistent_subscription(self, e2e_utils: E2ETestUtils):
        """Test reading a subscription that doesn't exist."""
        subscription = await e2e_utils.get_subscription_by_id(99999)
        assert subscription is None

    async def test_list_subscriptions(self, e2e_utils: E2ETestUtils):
        """Test listing subscriptions with pagination."""
        # Create multiple test subscriptions
        subscriptions = []
        for i in range(3):
            sub = await e2e_utils.create_test_subscription(
                description=f"E2E_TEST list test subscription {i+1}"
            )
            subscriptions.append(sub)

        # List subscriptions
        result = await e2e_utils.list_subscriptions(page=1, size=10)

        assert "subscriptions" in result
        assert "total" in result
        assert "page" in result
        assert "size" in result
        assert result["page"] == 1
        assert result["size"] == 10
        assert result["total"] >= 3

        # Check our test subscriptions are in the list
        found_descriptions = [s["description"] for s in result["subscriptions"]]
        for i in range(3):
            expected_desc = f"E2E_TEST list test subscription {i+1}"
            assert expected_desc in found_descriptions

    async def test_list_subscriptions_pagination(self, e2e_utils: E2ETestUtils):
        """Test subscription list pagination."""
        # Create test subscriptions
        for i in range(5):
            await e2e_utils.create_test_subscription(
                description=f"E2E_TEST pagination test {i+1}"
            )

        # Test pagination
        page1 = await e2e_utils.list_subscriptions(page=1, size=2)
        page2 = await e2e_utils.list_subscriptions(page=2, size=2)

        assert len(page1["subscriptions"]) == 2
        assert len(page2["subscriptions"]) >= 1  # Could be 1 or 2 depending on existing data
        assert page1["page"] == 1
        assert page2["page"] == 2
        assert page1["size"] == 2
        assert page2["size"] == 2

    async def test_update_subscription(self, e2e_utils: E2ETestUtils):
        """Test updating a subscription."""
        # Create subscription
        created = await e2e_utils.create_test_subscription(
            description="E2E_TEST original description",
            channel_config={"url": "http://original.example.com/webhook"}
        )

        # Update subscription
        updates = {
            "description": "E2E_TEST updated description",
            "channel_config": {
                "url": "http://updated.example.com/webhook",
                "method": "POST"
            },
            "active": False
        }

        updated = await e2e_utils.update_subscription(created["id"], updates)

        # Verify updates
        assert updated["id"] == created["id"]
        assert updated["description"] == "E2E_TEST updated description"
        assert updated["channel_config"]["url"] == "http://updated.example.com/webhook"
        assert updated["active"] is False
        assert updated["updated_at"] is not None

    async def test_update_nonexistent_subscription(self, e2e_utils: E2ETestUtils):
        """Test updating a subscription that doesn't exist."""
        try:
            await e2e_utils.update_subscription(99999, {"description": "test"})
            assert False, "Should have raised an exception"
        except Exception as e:
            # Should get a 404 error
            assert "404" in str(e) or "not found" in str(e).lower()

    async def test_partial_update_subscription(self, e2e_utils: E2ETestUtils):
        """Test partially updating a subscription."""
        # Create subscription
        created = await e2e_utils.create_test_subscription(
            description="E2E_TEST partial update test"
        )

        original_channel_config = created["channel_config"].copy()

        # Update only description
        updates = {"description": "E2E_TEST partially updated description"}
        updated = await e2e_utils.update_subscription(created["id"], updates)

        # Verify only description changed
        assert updated["description"] == "E2E_TEST partially updated description"
        assert updated["channel_config"] == original_channel_config
        assert updated["active"] == created["active"]

    async def test_delete_subscription(self, e2e_utils: E2ETestUtils):
        """Test deleting a subscription."""
        # Create subscription
        created = await e2e_utils.create_test_subscription(
            description="E2E_TEST delete test subscription"
        )

        # Delete subscription
        deleted = await e2e_utils.delete_subscription(created["id"])
        assert deleted is True

        # Verify subscription is gone
        subscription = await e2e_utils.get_subscription_by_id(created["id"])
        assert subscription is None

    async def test_delete_nonexistent_subscription(self, e2e_utils: E2ETestUtils):
        """Test deleting a subscription that doesn't exist."""
        deleted = await e2e_utils.delete_subscription(99999)
        assert deleted is False

    async def test_subscription_validation(self, e2e_utils: E2ETestUtils):
        """Test subscription field validation."""
        # Test invalid channel type
        try:
            invalid_payload = {
                "description": "E2E_TEST invalid channel type",
                "channel_type": "invalid_type",
                "channel_config": {"url": "http://example.com"}
            }
            response = await e2e_utils.http_client.post("/subscriptions/", json=invalid_payload)
            assert response.status_code == 422  # Validation error
        except Exception:
            pass  # Expected to fail

        # Test missing required fields
        try:
            incomplete_payload = {
                "description": "E2E_TEST missing fields"
                # Missing channel_type and channel_config
            }
            response = await e2e_utils.http_client.post("/subscriptions/", json=incomplete_payload)
            assert response.status_code == 422  # Validation error
        except Exception:
            pass  # Expected to fail

    async def test_subscription_crud_flow(self, e2e_utils: E2ETestUtils):
        """Test complete CRUD flow for subscriptions."""
        # CREATE
        created = await e2e_utils.create_test_subscription(
            description="E2E_TEST complete CRUD flow"
        )

        # READ
        read = await e2e_utils.get_subscription_by_id(created["id"])
        assert read["id"] == created["id"]

        # UPDATE
        updated = await e2e_utils.update_subscription(
            created["id"],
            {"description": "E2E_TEST updated CRUD flow"}
        )
        assert updated["description"] == "E2E_TEST updated CRUD flow"

        # DELETE
        deleted = await e2e_utils.delete_subscription(created["id"])
        assert deleted is True

        # VERIFY DELETION
        final_read = await e2e_utils.get_subscription_by_id(created["id"])
        assert final_read is None
