"""Test the fingerprinting and mapping integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langhook.map.fingerprint import generate_fingerprint


@pytest.mark.asyncio
async def test_mapping_engine_fingerprint_lookup():
    """Test that mapping engine looks up fingerprints."""
    from langhook.map.mapper import MappingEngine
    from langhook.subscriptions.database import db_service
    
    # Mock the database service
    original_get_ingestion_mappings_by_structure = db_service.get_ingestion_mappings_by_structure
    db_service.get_ingestion_mappings_by_structure = AsyncMock(return_value=[])
    
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
        db_service.get_ingestion_mappings_by_structure.assert_called_once_with(fingerprint)
        
    finally:
        # Restore original method
        db_service.get_ingestion_mappings_by_structure = original_get_ingestion_mappings_by_structure


@pytest.mark.asyncio 
async def test_store_jsonata_mapping():
    """Test storing a JSONata mapping expression."""
    from langhook.map.mapper import MappingEngine
    from langhook.subscriptions.database import db_service
    
    # Mock the database service
    original_create_ingestion_mapping = db_service.create_ingestion_mapping
    db_service.create_ingestion_mapping = AsyncMock()
    
    try:
        engine = MappingEngine()
        
        raw_payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {"number": 123, "title": "Test"}
        }
        
        jsonata_expr = '{"publisher": "github", "resource": {"type": "pull_request", "id": pull_request.number}, "action": "created"}'
        
        # Should store the mapping
        await engine.store_jsonata_mapping("github", raw_payload, jsonata_expr)
        
        # Verify database call was made
        assert db_service.create_ingestion_mapping.called
        call_args = db_service.create_ingestion_mapping.call_args[1]
        
        assert call_args["publisher"] == "github"
        assert call_args["event_name"] == "pull_request created"
        assert "fingerprint" in call_args
        assert "mapping_expr" in call_args
        
    finally:
        # Restore original method  
        db_service.create_ingestion_mapping = original_create_ingestion_mapping


if __name__ == "__main__":
    import asyncio
    
    # Run the async tests
    async def run_async_tests():
        await test_mapping_engine_fingerprint_lookup()
        print("Mapping engine fingerprint lookup test passed!")
        
        await test_store_jsonata_mapping()
        print("Store JSONata mapping test passed!")
    
    asyncio.run(run_async_tests())
    print("All integration tests passed!")