"""
Demo script to showcase disposable subscription functionality.

This script demonstrates:
1. Creating disposable and regular subscriptions
2. How the schemas validate the disposable field
3. How the response includes disposable and used status
"""

from langhook.subscriptions.schemas import SubscriptionCreate, SubscriptionResponse, GateConfig


def demo_disposable_subscriptions():
    """Demonstrate disposable subscription functionality."""
    
    print("=== Disposable Subscription Demo ===\n")
    
    # 1. Create a disposable subscription
    print("1. Creating a disposable subscription:")
    disposable_sub = SubscriptionCreate(
        description="Alert me when a critical issue occurs - one time only",
        channel_type="webhook",
        channel_config={"url": "https://my-app.com/critical-alert"},
        disposable=True  # This makes it one-time use
    )
    
    print(f"   Description: {disposable_sub.description}")
    print(f"   Disposable: {disposable_sub.disposable}")
    print(f"   Channel: {disposable_sub.channel_type}")
    print()
    
    # 2. Create a regular subscription
    print("2. Creating a regular subscription:")
    regular_sub = SubscriptionCreate(
        description="Alert me for all deployment events",
        channel_type="webhook",
        channel_config={"url": "https://my-app.com/deployment-alert"},
        disposable=False  # Explicit false, though default is False
    )
    
    print(f"   Description: {regular_sub.description}")
    print(f"   Disposable: {regular_sub.disposable}")
    print(f"   Channel: {regular_sub.channel_type}")
    print()
    
    # 3. Create subscription with LLM gate
    print("3. Creating a disposable subscription with LLM gate:")
    gate_config = GateConfig(enabled=True, prompt="Only allow critical severity events")
    
    gated_disposable_sub = SubscriptionCreate(
        description="Critical incidents requiring immediate attention",
        gate=gate_config,
        disposable=True
    )
    
    print(f"   Description: {gated_disposable_sub.description}")
    print(f"   Disposable: {gated_disposable_sub.disposable}")
    print(f"   Gate enabled: {gated_disposable_sub.gate.enabled}")
    print(f"   Gate prompt: {gated_disposable_sub.gate.prompt}")
    print()
    
    # 4. Simulate subscription responses
    print("4. Simulating subscription responses:")
    
    # Fresh disposable subscription (not used yet)
    fresh_disposable_response = SubscriptionResponse(
        id=1,
        subscriber_id="user123",
        description="Alert me when a critical issue occurs - one time only",
        pattern="incidents.critical.*",
        channel_type="webhook",
        channel_config={"url": "https://my-app.com/critical-alert"},
        active=True,
        disposable=True,
        used=False,  # Not used yet, so still active
        gate=None,
        created_at="2023-01-01T10:00:00Z"
    )
    
    print("   Fresh disposable subscription:")
    print(f"     ID: {fresh_disposable_response.id}")
    print(f"     Active: {fresh_disposable_response.active}")
    print(f"     Disposable: {fresh_disposable_response.disposable}")
    print(f"     Used: {fresh_disposable_response.used}")
    print(f"     Status: {'Will trigger once' if not fresh_disposable_response.used else 'Already used'}")
    print()
    
    # Used disposable subscription
    used_disposable_response = SubscriptionResponse(
        id=2,
        subscriber_id="user123",
        description="Alert me when a critical issue occurs - one time only",
        pattern="incidents.critical.*",
        channel_type="webhook",
        channel_config={"url": "https://my-app.com/critical-alert"},
        active=True,
        disposable=True,
        used=True,  # Already triggered once
        gate=None,
        created_at="2023-01-01T10:00:00Z"
    )
    
    print("   Used disposable subscription:")
    print(f"     ID: {used_disposable_response.id}")
    print(f"     Active: {used_disposable_response.active}")
    print(f"     Disposable: {used_disposable_response.disposable}")
    print(f"     Used: {used_disposable_response.used}")
    print(f"     Status: {'Will trigger once' if not used_disposable_response.used else 'Already used - no longer active'}")
    print()
    
    # Regular subscription
    regular_response = SubscriptionResponse(
        id=3,
        subscriber_id="user123",
        description="Alert me for all deployment events",
        pattern="deployments.*",
        channel_type="webhook",
        channel_config={"url": "https://my-app.com/deployment-alert"},
        active=True,
        disposable=False,
        used=False,  # N/A for regular subscriptions
        gate=None,
        created_at="2023-01-01T10:00:00Z"
    )
    
    print("   Regular subscription:")
    print(f"     ID: {regular_response.id}")
    print(f"     Active: {regular_response.active}")
    print(f"     Disposable: {regular_response.disposable}")
    print(f"     Used: {regular_response.used}")
    print(f"     Status: {'Always active' if not regular_response.disposable else 'One-time use'}")
    print()
    
    print("=== Demo completed! ===")
    print("\nKey Benefits of Disposable Subscriptions:")
    print("- ✅ Perfect for one-time alerts (security breaches, critical incidents)")
    print("- ✅ Automatically disabled after first trigger to avoid spam")
    print("- ✅ Subscription remains in database for audit trail")
    print("- ✅ Clear UI indicators show when a subscription has been used")
    print("- ✅ Works with all features: webhooks, LLM gates, etc.")


if __name__ == "__main__":
    demo_disposable_subscriptions()