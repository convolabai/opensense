"""Test for subscription channel_type NOT NULL constraint issue."""

import pytest
from unittest.mock import patch, Mock
import tempfile
import os

from langhook.subscriptions.database import DatabaseService
from langhook.subscriptions.schemas import SubscriptionCreate, GateConfig


class TestChannelTypeConstraint:
    """Test subscription creation with and without channel_type."""

    @pytest.fixture
    def test_db_service(self):
        """Create a test database service with in-memory SQLite."""
        # Use in-memory SQLite for testing to avoid PostgreSQL dependency
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            test_db_path = tmp_file.name
        
        try:
            # Mock the subscription settings to use SQLite
            with patch('langhook.subscriptions.database.subscription_settings') as mock_settings:
                mock_settings.postgres_dsn = f"sqlite:///{test_db_path}"
                
                # Create a custom DatabaseService that handles SQLite properly
                from langhook.subscriptions.database import DatabaseService
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                db_service = DatabaseService()
                # Override the engine to not use PostgreSQL-specific connect_args
                db_service.engine = create_engine(f"sqlite:///{test_db_path}")
                db_service.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_service.engine)
                db_service.create_tables()
                yield db_service
        finally:
            # Clean up the temporary database file
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)

    @pytest.mark.asyncio
    async def test_create_subscription_with_webhook_channel(self, test_db_service):
        """Test creating subscription with webhook channel type (should work)."""
        subscription_data = SubscriptionCreate(
            description="Test subscription with webhook",
            channel_type="webhook",
            channel_config={"url": "https://example.com/webhook"}
        )

        # This should work fine
        result = await test_db_service.create_subscription(
            subscriber_id="test_user",
            pattern="test.pattern.*",
            subscription_data=subscription_data
        )

        assert result is not None
        assert result.channel_type == "webhook"
        assert result.channel_config == {"url": "https://example.com/webhook"}

    @pytest.mark.asyncio 
    async def test_create_subscription_without_channel_type(self, test_db_service):
        """Test creating subscription without channel type (polling-only)."""
        subscription_data = SubscriptionCreate(
            description="Test subscription without webhook (polling-only)",
            # No channel_type or channel_config specified
        )

        # This should work according to the SQLAlchemy model (nullable=True)
        result = await test_db_service.create_subscription(
            subscriber_id="test_user",
            pattern="test.pattern.*",
            subscription_data=subscription_data
        )

        assert result is not None
        assert result.channel_type is None
        assert result.channel_config is None

    @pytest.mark.asyncio
    async def test_create_gated_subscription_without_channel(self, test_db_service):
        """Test creating gated subscription without channel (reproduces the reported issue)."""
        gate_config = GateConfig(
            enabled=True,
            prompt="Evaluate if this event is important"
        )
        
        subscription_data = SubscriptionCreate(
            description="Tell me when there's a payment with more than $1000 in values on stripe",
            # No channel_type or channel_config - this should be polling-only
            gate=gate_config
        )

        # This is the scenario that fails in the reported issue
        # It should work if channel_type is properly nullable
        result = await test_db_service.create_subscription(
            subscriber_id="default", 
            pattern="langhook.events.stripe.payment_intent.*.created",
            subscription_data=subscription_data
        )

        assert result is not None
        assert result.channel_type is None
        assert result.channel_config is None
        assert result.gate is not None
        assert result.gate["enabled"] is True

    @pytest.mark.asyncio
    async def test_create_gated_subscription_with_webhook(self, test_db_service):
        """Test creating gated subscription with webhook (should also work)."""
        gate_config = GateConfig(
            enabled=True,
            prompt="Evaluate if this event is important"
        )
        
        subscription_data = SubscriptionCreate(
            description="Gated subscription with webhook",
            channel_type="webhook",
            channel_config={"url": "https://example.com/webhook"},
            gate=gate_config
        )

        result = await test_db_service.create_subscription(
            subscriber_id="test_user",
            pattern="test.pattern.*", 
            subscription_data=subscription_data
        )

        assert result is not None
        assert result.channel_type == "webhook"
        assert result.channel_config == {"url": "https://example.com/webhook"}
        assert result.gate is not None
        assert result.gate["enabled"] is True


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        """Run the tests manually for debugging."""
        test_instance = TestChannelTypeConstraint()
        
        # Create test database
        import tempfile
        import os
        from langhook.subscriptions.database import DatabaseService
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            test_db_path = tmp_file.name
        
        try:
            # Mock the subscription settings
            with patch('langhook.subscriptions.database.subscription_settings') as mock_settings:
                mock_settings.postgres_dsn = f"sqlite:///{test_db_path}"
                
                # Create a custom DatabaseService that handles SQLite properly
                from langhook.subscriptions.database import DatabaseService
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                db_service = DatabaseService()
                # Override the engine to not use PostgreSQL-specific connect_args
                db_service.engine = create_engine(f"sqlite:///{test_db_path}")
                db_service.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_service.engine)
                db_service.create_tables()
                
                print("Testing subscription creation...")
                
                # Test with webhook
                await test_instance.test_create_subscription_with_webhook_channel(db_service)
                print("✓ Webhook subscription creation works")
                
                # Test without channel type  
                await test_instance.test_create_subscription_without_channel_type(db_service)
                print("✓ Polling-only subscription creation works")
                
                # Test gated without channel (the failing case)
                await test_instance.test_create_gated_subscription_without_channel(db_service)
                print("✓ Gated polling-only subscription creation works")
                
                # Test gated with webhook
                await test_instance.test_create_gated_subscription_with_webhook(db_service)
                print("✓ Gated webhook subscription creation works")
                
                print("All tests passed!")
                
        finally:
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
    
    asyncio.run(run_tests())