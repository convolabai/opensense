"""Tests for disposable subscription functionality."""

import pytest


def test_subscription_model_has_disposable_fields():
    """Test that the Subscription model has the new disposable and used fields."""
    from langhook.subscriptions.models import Subscription
    
    # Check that the model has the new attributes
    assert hasattr(Subscription, 'disposable')
    assert hasattr(Subscription, 'used')


def test_subscription_create_schema_has_disposable_field():
    """Test that SubscriptionCreate schema has disposable field."""
    from langhook.subscriptions.schemas import SubscriptionCreate
    
    # Test that we can create a subscription with disposable=True
    subscription_data = SubscriptionCreate(
        description="Test disposable subscription",
        disposable=True
    )
    
    assert subscription_data.disposable is True
    
    # Test default value
    subscription_data_default = SubscriptionCreate(
        description="Test regular subscription"
    )
    
    assert subscription_data_default.disposable is False


def test_subscription_response_schema_has_disposable_fields():
    """Test that SubscriptionResponse schema has disposable and used fields."""
    from langhook.subscriptions.schemas import SubscriptionResponse
    
    # Check that the response schema includes the new fields
    fields = SubscriptionResponse.model_fields
    assert 'disposable' in fields
    assert 'used' in fields


def test_subscription_update_schema_has_disposable_field():
    """Test that SubscriptionUpdate schema has disposable field."""
    from langhook.subscriptions.schemas import SubscriptionUpdate
    
    # Test that we can update a subscription's disposable field
    subscription_update = SubscriptionUpdate(
        disposable=True
    )
    
    assert subscription_update.disposable is True
    
    # Check that the update schema includes the new field
    fields = SubscriptionUpdate.model_fields
    assert 'disposable' in fields