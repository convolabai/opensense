"""Integration tests for LangHook Python SDK"""

import asyncio
import pytest
from unittest.mock import patch

from sdk.python import LangHookClient, LangHookClientConfig


@pytest.mark.asyncio 
async def test_sdk_integration_with_langhook_api():
    """Test SDK integration with LangHook API endpoints (mocked)"""
    
    config = LangHookClientConfig(endpoint="http://localhost:8000")
    
    # Mock the actual HTTP calls to the LangHook API
    with patch('httpx.AsyncClient') as mock_client_class:
        import httpx
        from unittest.mock import AsyncMock, MagicMock
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock health check response
        health_response = AsyncMock()
        health_response.raise_for_status = MagicMock()
        health_response.json = MagicMock(return_value={"status": "up"})
        
        # Mock subscription creation response
        create_sub_response = AsyncMock()
        create_sub_response.raise_for_status = MagicMock()
        create_sub_response.json = MagicMock(return_value={
            "id": 123,
            "subscriber_id": "default",
            "description": "Notify me when PR 1374 is approved",
            "pattern": "langhook.events.github.pull_request.1374.updated",
            "channel_type": None,
            "channel_config": None,
            "active": True,
            "gate": None,
            "created_at": "2023-01-01T00:00:00Z"
        })
        
        # Mock list subscriptions response
        list_subs_response = AsyncMock()
        list_subs_response.raise_for_status = MagicMock()
        list_subs_response.json = MagicMock(return_value={
            "subscriptions": [create_sub_response.json()],
            "total": 1,
            "page": 1,
            "size": 50
        })
        
        # Mock ingest response
        ingest_response = AsyncMock()
        ingest_response.raise_for_status = MagicMock()
        ingest_response.json = MagicMock(return_value={
            "message": "Event accepted",
            "request_id": "req_12345"
        })
        
        # Mock delete response
        delete_response = AsyncMock()
        delete_response.raise_for_status = MagicMock()
        
        # Set up mock client responses
        mock_client.get.side_effect = [health_response, list_subs_response]
        mock_client.post.side_effect = [create_sub_response, ingest_response]
        mock_client.delete.return_value = delete_response
        
        # Test the SDK workflow
        async with LangHookClient(config) as client:
            # Should have called health check
            assert mock_client.get.call_count >= 1
            
            # Create subscription
            subscription = await client.create_subscription("Notify me when PR 1374 is approved")
            assert subscription.id == 123
            assert "PR 1374" in subscription.description
            
            # List subscriptions
            subscriptions = await client.list_subscriptions()
            assert len(subscriptions) >= 1
            
            # Ingest event
            result = await client.ingest_raw_event("github", {
                "action": "closed",
                "pull_request": {"number": 1374, "merged": True}
            })
            assert result.message == "Event accepted"
            assert result.request_id == "req_12345"
            
            # Delete subscription
            await client.delete_subscription("123")
            
        # Verify all expected calls were made
        assert mock_client.get.call_count >= 2  # health + list
        assert mock_client.post.call_count == 2  # create + ingest
        assert mock_client.delete.call_count == 1
        assert mock_client.aclose.call_count == 1