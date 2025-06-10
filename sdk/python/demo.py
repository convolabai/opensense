"""
Demo script showing the LangHook SDK in action
This demonstrates the exact example from the issue requirements
"""

import asyncio
from sdk.python import LangHookClient, LangHookClientConfig, AuthConfig


async def demo_sdk_usage():
    """Demo the SDK usage as specified in the issue"""
    
    print("🚀 LangHook SDK Demo")
    print("=" * 50)
    
    # Create client with the exact configuration from the issue
    client = LangHookClient(LangHookClientConfig(
        endpoint="http://localhost:8000",  # Would be "https://api.langhook.dev" in production
        auth=AuthConfig(type="token", value="sk-1234")  # Example token
    ))
    
    try:
        # Initialize connection (as specified in the issue)
        print("1. Initializing connection...")
        await client.init()
        print("   ✅ Connected to LangHook server")
        
        # Create subscription with the exact example from the issue
        print("\n2. Creating subscription...")
        subscription = await client.create_subscription("Notify me when PR 1374 is approved")
        print(f"   ✅ Created subscription: {subscription.id}")
        print(f"   📝 Description: {subscription.description}")
        print(f"   🎯 Pattern: {subscription.pattern}")
        
        # Demonstrate listen() method as specified
        print("\n3. Setting up event listener...")
        
        def event_handler(event):
            """Handler function as specified in the issue"""
            print("   🎉 Got matching event!")
            print(f"      Publisher: {event.publisher}")
            print(f"      Resource: {event.resource}")
            print(f"      Action: {event.action}")
            print(f"      Timestamp: {event.timestamp}")
        
        # Start listening with 15 second intervals (as in the issue example)
        stop_listening = client.listen(
            str(subscription.id), 
            event_handler, 
            {"intervalSeconds": 15}
        )
        print("   ✅ Started listening for events (15 second intervals)")
        
        # Demonstrate event ingestion
        print("\n4. Ingesting test event...")
        ingest_result = await client.ingest_raw_event("github", {
            "action": "synchronize",  # This would trigger the PR subscription
            "pull_request": {
                "number": 1374,
                "title": "Add new feature",
                "state": "open",
                "user": {"login": "developer"}
            },
            "repository": {"name": "test-repo"}
        })
        print(f"   ✅ Ingested event: {ingest_result.request_id}")
        
        # Let it run briefly to show polling
        print("\n5. Monitoring for events (10 seconds)...")
        await asyncio.sleep(10)
        
        # Stop listening
        print("\n6. Stopping listener...")
        stop_listening()
        print("   ✅ Stopped listening")
        
        # List all subscriptions  
        print("\n7. Listing all subscriptions...")
        subscriptions = await client.list_subscriptions()
        print(f"   📋 Found {len(subscriptions)} subscription(s)")
        for sub in subscriptions:
            print(f"      - ID: {sub.id}, Description: {sub.description}")
        
        # Test subscription functionality
        print("\n8. Testing subscription...")
        from sdk.python.client import CanonicalEvent
        test_event = CanonicalEvent(
            publisher="github",
            resource={"type": "pull_request", "id": 1374},
            action="approved",
            timestamp="2023-01-01T12:00:00Z",
            payload={"approved_by": "reviewer"}
        )
        test_result = await client.test_subscription(str(subscription.id), test_event)
        print(f"   ✅ Test result: {test_result.matched} - {test_result.reason}")
        
        # Clean up
        print("\n9. Cleaning up...")
        await client.delete_subscription(str(subscription.id))
        print("   ✅ Deleted subscription")
        
        print("\n🎯 Demo completed successfully!")
        print("\nThe LangHook SDK provides all the functionality specified in the issue:")
        print("✅ init() method for endpoint + optional auth")
        print("✅ createSubscription() with natural language")
        print("✅ listSubscriptions() to get all subscriptions") 
        print("✅ deleteSubscription() for cleanup")
        print("✅ listen() for polling-based event listening")
        print("✅ testSubscription() for testing subscriptions")
        print("✅ ingestRawEvent() for event ingestion")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nNote: This demo requires a running LangHook server.")
        print("To run a real demo, start the LangHook server with: langhook")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(demo_sdk_usage())