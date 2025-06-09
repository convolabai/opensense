"""Test the fingerprinting and mapping integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langhook.map.fingerprint import generate_fingerprint
from langhook.map.jsonata_generator import generate_jsonata_from_canonical


def test_jsonata_generator_basic():
    """Test basic JSONata generation from canonical data."""
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": 1374},
        "action": "created"
    }
    
    raw_payload = {
        "action": "opened", 
        "pull_request": {"number": 1374},
        "repository": {"name": "test-repo"}
    }
    
    jsonata_expr = generate_jsonata_from_canonical(canonical_data, raw_payload)
    
    # Should contain the basic structure
    assert '"publisher": "github"' in jsonata_expr
    assert '"type": "pull_request"' in jsonata_expr
    assert '"action": "created"' in jsonata_expr
    assert "pull_request.number" in jsonata_expr


@pytest.mark.asyncio
async def test_mapping_engine_fingerprint_lookup():
    """Test that mapping engine looks up fingerprints."""
    from langhook.map.mapper import MappingEngine
    from langhook.subscriptions.database import db_service
    
    # Mock the database service
    original_get_webhook_mapping = db_service.get_webhook_mapping
    db_service.get_webhook_mapping = AsyncMock(return_value=None)
    
    try:
        engine = MappingEngine()
        
        payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {"id": 123, "title": "Test"}
        }
        
        # Should not fail even with mocked database
        result = await engine.apply_mapping("github", payload)
        
        # Should have attempted database lookup
        fingerprint = generate_fingerprint(payload)
        db_service.get_webhook_mapping.assert_called_once_with(fingerprint)
        
    finally:
        # Restore original method
        db_service.get_webhook_mapping = original_get_webhook_mapping


@pytest.mark.asyncio 
async def test_store_mapping_from_canonical():
    """Test storing a mapping generated from canonical data."""
    from langhook.map.mapper import MappingEngine
    from langhook.subscriptions.database import db_service
    
    # Mock the database service
    original_create_webhook_mapping = db_service.create_webhook_mapping
    db_service.create_webhook_mapping = AsyncMock()
    
    try:
        engine = MappingEngine()
        
        raw_payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {"id": 123, "title": "Test"}
        }
        
        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 123},
            "action": "created"
        }
        
        # Should store the mapping
        await engine.store_mapping_from_canonical("github", raw_payload, canonical_data)
        
        # Verify database call was made
        assert db_service.create_webhook_mapping.called
        call_args = db_service.create_webhook_mapping.call_args[1]
        
        assert call_args["publisher"] == "github"
        assert call_args["event_name"] == "pull_request created"
        assert "fingerprint" in call_args
        assert "mapping_expr" in call_args
        
    finally:
        # Restore original method  
        db_service.create_webhook_mapping = original_create_webhook_mapping


if __name__ == "__main__":
    import asyncio
    
    # Run the sync tests
    test_jsonata_generator_basic()
    print("JSONata generator test passed!")
    
    # Run the async tests
    async def run_async_tests():
        await test_mapping_engine_fingerprint_lookup()
        print("Mapping engine fingerprint lookup test passed!")
        
        await test_store_mapping_from_canonical()
        print("Store mapping test passed!")
    
    asyncio.run(run_async_tests())
    print("All integration tests passed!")