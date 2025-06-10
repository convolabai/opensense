"""
Integration test for LangHook SDK with actual server
This test requires a running LangHook server at http://localhost:8000
"""

import asyncio
import pytest
import httpx
from sdk.python import LangHookClient, LangHookClientConfig


@pytest.mark.asyncio 
@pytest.mark.integration
async def test_sdk_with_live_server():
    """Test SDK with live LangHook server (optional integration test)"""
    
    # This test only runs if explicitly requested with pytest -m integration
    # and if a server is actually running at localhost:8000
    
    config = LangHookClientConfig(endpoint="http://localhost:8000")
    
    try:
        # Test basic connectivity first
        async with httpx.AsyncClient() as test_client:
            response = await test_client.get("http://localhost:8000/health/")
            if response.status_code != 200:
                pytest.skip("LangHook server not available")
    except Exception:
        pytest.skip("LangHook server not available")
    
    # Test the SDK functionality
    async with LangHookClient(config) as client:
        # Health check via SDK
        await client.init()
        
        # Test subscription management
        subscription = await client.create_subscription("Test SDK integration subscription")
        assert subscription.id is not None
        assert "SDK integration" in subscription.description
        
        # List subscriptions
        subscriptions = await client.list_subscriptions()
        assert any(sub.id == subscription.id for sub in subscriptions)
        
        # Test event ingestion
        result = await client.ingest_raw_event("test-sdk", {
            "event": "test_integration",
            "timestamp": "2023-01-01T12:00:00Z",
            "data": {"source": "sdk-test"}
        })
        assert result.message == "Event accepted"
        assert result.request_id is not None
        
        # Clean up
        await client.delete_subscription(str(subscription.id))
        
        print("✅ SDK integration test passed!")


if __name__ == "__main__":
    # Run integration test directly
    asyncio.run(test_sdk_with_live_server())