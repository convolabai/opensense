"""
Example usage of the LangHook Python SDK
"""

import asyncio
from sdk.python import LangHookClient, LangHookClientConfig, AuthConfig


async def main():
    """Example of using the LangHook SDK"""
    
    # Create client configuration
    config = LangHookClientConfig(
        endpoint="http://localhost:8000",
        auth=AuthConfig(type="token", value="your-auth-token")
    )
    
    # Use client as context manager
    async with LangHookClient(config) as client:
        # Initialize connection
        print("✅ Connected to LangHook server")
        
        # Create a subscription
        subscription = await client.create_subscription(
            "Notify me when PR 1374 is approved"
        )
        print(f"✅ Created subscription: {subscription.id}")
        
        # List all subscriptions
        subscriptions = await client.list_subscriptions()
        print(f"📋 Found {len(subscriptions)} subscriptions")
        
        # Set up event listener
        def event_handler(event):
            print(f"🎉 Got matching event: {event.publisher}/{event.action}")
            print(f"   Resource: {event.resource}")
            print(f"   Timestamp: {event.timestamp}")
        
        # Start listening for events (with 15 second polling interval)
        stop_listening = client.listen(
            str(subscription.id), 
            event_handler, 
            {"intervalSeconds": 15}
        )
        
        print("👂 Listening for events... (will run for 30 seconds)")
        
        # Let it run for a bit
        await asyncio.sleep(30)
        
        # Stop listening
        stop_listening()
        print("⏹️  Stopped listening")
        
        # Ingest a test event
        result = await client.ingest_raw_event("github", {
            "action": "opened",
            "pull_request": {
                "number": 1374,
                "title": "Test PR"
            }
        })
        print(f"📤 Ingested event: {result.request_id}")
        
        # Clean up - delete the subscription
        await client.delete_subscription(str(subscription.id))
        print("🗑️  Deleted subscription")


if __name__ == "__main__":
    asyncio.run(main())