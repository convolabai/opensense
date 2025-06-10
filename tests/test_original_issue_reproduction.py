"""Test reproduction of the specific channel_type NOT NULL constraint issue."""

import pytest
from unittest.mock import patch
import tempfile
import os

from langhook.subscriptions.database import DatabaseService
from langhook.subscriptions.schemas import SubscriptionCreate, GateConfig


@pytest.mark.asyncio
async def test_reproduce_original_issue():
    """Reproduce the exact issue reported in the problem statement."""
    
    # Create a test database service
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        with patch('langhook.subscriptions.database.subscription_settings') as mock_settings:
            mock_settings.postgres_dsn = f"sqlite:///{test_db_path}"
            
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            db_service = DatabaseService()
            # Override for SQLite compatibility
            db_service.engine = create_engine(f"sqlite:///{test_db_path}")
            db_service.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_service.engine)
            db_service.create_tables()
            
            # Reproduce the exact scenario from the error message
            subscription_data = SubscriptionCreate(
                description="Tell me when there's a payment with more than $1000 in values on stripe",
                # Note: No channel_type or channel_config specified - this should be allowed for polling-only
                gate=GateConfig(
                    enabled=True,
                    prompt="Evaluate if this event is a Stripe payment AND the amount is greater than $1000. Return {\"decision\": true or false}"
                )
            )

            # This should work after the fix
            result = await db_service.create_subscription(
                subscriber_id="default",
                pattern="langhook.events.stripe.payment_intent.*.created",
                subscription_data=subscription_data
            )

            # Verify the subscription was created correctly
            assert result is not None
            assert result.subscriber_id == "default"
            assert result.description == "Tell me when there's a payment with more than $1000 in values on stripe"
            assert result.pattern == "langhook.events.stripe.payment_intent.*.created"
            assert result.channel_type is None  # This should be None for polling-only
            assert result.channel_config is None  # This should be None for polling-only
            assert result.active is True
            assert result.gate is not None
            assert result.gate["enabled"] is True
            assert "Evaluate if this event is a Stripe payment" in result.gate["prompt"]
            
            print("✅ Successfully created gated subscription without channel_type (polling-only)")
            
    finally:
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_reproduce_original_issue())