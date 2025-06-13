"""Integration tests for disposable subscription workflow."""

import json


def test_disposable_subscription_json_serialization():
    """Test that disposable subscriptions can be properly serialized to JSON."""
    from langhook.subscriptions.schemas import SubscriptionCreate
    
    # Test disposable subscription
    disposable_subscription = SubscriptionCreate(
        description="Test disposable",
        disposable=True,
        channel_type="webhook",
        channel_config={"url": "https://example.com/webhook"}
    )
    
    # Convert to dict and then to JSON to simulate API requests
    subscription_dict = disposable_subscription.model_dump()
    json_data = json.dumps(subscription_dict)
    
    # Parse back and verify
    parsed_data = json.loads(json_data)
    assert parsed_data["disposable"] is True
    assert parsed_data["description"] == "Test disposable"
    
    # Test regular subscription
    regular_subscription = SubscriptionCreate(
        description="Test regular",
        disposable=False
    )
    
    subscription_dict = regular_subscription.model_dump()
    json_data = json.dumps(subscription_dict)
    parsed_data = json.loads(json_data)
    assert parsed_data["disposable"] is False
    
    print("✓ JSON serialization test completed successfully")


def test_subscription_response_includes_disposable_fields():
    """Test that SubscriptionResponse includes disposable and used fields."""
    from langhook.subscriptions.schemas import SubscriptionResponse
    
    # Create a subscription response with disposable fields
    response_data = {
        "id": 1,
        "subscriber_id": "test_user",
        "description": "Test subscription",
        "pattern": "test.pattern",
        "channel_type": None,
        "channel_config": None,
        "active": True,
        "disposable": True,
        "used": False,
        "gate": None,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": None
    }
    
    # Create SubscriptionResponse object
    subscription_response = SubscriptionResponse(**response_data)
    
    # Verify all fields are present
    assert subscription_response.id == 1
    assert subscription_response.disposable is True
    assert subscription_response.used is False
    assert subscription_response.active is True
    
    print("✓ SubscriptionResponse test completed successfully")


def test_subscription_create_with_all_fields():
    """Test creating a subscription with all possible fields."""
    from langhook.subscriptions.schemas import SubscriptionCreate, GateConfig
    
    gate_config = GateConfig(enabled=True, prompt="Only critical events")
    
    subscription = SubscriptionCreate(
        description="Complete test subscription",
        channel_type="webhook",
        channel_config={"url": "https://example.com/webhook", "method": "POST"},
        gate=gate_config,
        disposable=True
    )
    
    assert subscription.description == "Complete test subscription"
    assert subscription.channel_type == "webhook"
    assert subscription.disposable is True
    assert subscription.gate.enabled is True
    assert subscription.gate.prompt == "Only critical events"
    
    print("✓ Complete subscription creation test completed successfully")


if __name__ == "__main__":
    # Run the tests
    test_disposable_subscription_json_serialization()
    test_subscription_response_includes_disposable_fields()
    test_subscription_create_with_all_fields()
    
    print("\n🎉 All integration tests passed!")