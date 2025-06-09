"""End-to-end test of the fingerprinting workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langhook.map.fingerprint import generate_fingerprint
from langhook.map.mapper import MappingEngine
from langhook.map.service import MappingService


@pytest.mark.asyncio
async def test_end_to_end_fingerprinting_workflow():
    """
    Test the complete fingerprinting workflow:
    1. Raw payload comes in 
    2. No fingerprint match found
    3. LLM generates canonical data
    4. JSONata mapping is generated and stored
    5. Next identical payload structure uses stored mapping
    """
    from langhook.subscriptions.database import db_service
    from langhook.map.llm import llm_service
    
    # Mock the database and LLM services
    original_get_ingestion_mapping = db_service.get_ingestion_mapping
    original_create_ingestion_mapping = db_service.create_ingestion_mapping
    original_generate_jsonata_mapping = llm_service.generate_jsonata_mapping
    original_is_available = llm_service.is_available
    
    # Setup mocks
    stored_mappings = {}
    
    async def mock_get_ingestion_mapping(fingerprint: str):
        return stored_mappings.get(fingerprint)
    
    async def mock_create_ingestion_mapping(fingerprint: str, publisher: str, event_name: str, mapping_expr: str):
        mapping = MagicMock()
        mapping.fingerprint = fingerprint
        mapping.publisher = publisher
        mapping.event_name = event_name
        mapping.mapping_expr = mapping_expr
        stored_mappings[fingerprint] = mapping
        return mapping
    
    async def mock_generate_jsonata_mapping(source: str, raw_payload: dict):
        # Mock JSONata generation based on payload structure
        if "pull_request" in raw_payload:
            return '{"publisher": "' + source + '", "resource": {"type": "pull_request", "id": pull_request.number}, "action": "created", "timestamp": pull_request.created_at}'
        return None
    
    def mock_is_available():
        return True
    
    # Apply mocks
    db_service.get_ingestion_mapping = mock_get_ingestion_mapping
    db_service.create_ingestion_mapping = mock_create_ingestion_mapping
    llm_service.generate_jsonata_mapping = mock_generate_jsonata_mapping
    llm_service.is_available = mock_is_available
    
    try:
        # Create test payloads with same structure but different values
        payload1 = {
            "action": "opened",
            "number": 42,
            "pull_request": {"number": 1374, "title": "First PR", "created_at": "2024-01-01T00:00:00Z"},
            "repository": {"name": "test-repo"}
        }
        
        payload2 = {
            "action": "opened", 
            "number": 99,
            "pull_request": {"number": 5678, "title": "Second PR", "created_at": "2024-01-02T00:00:00Z"},
            "repository": {"name": "other-repo"}
        }
        
        # Both should have same fingerprint
        fingerprint1 = generate_fingerprint(payload1)
        fingerprint2 = generate_fingerprint(payload2)
        assert fingerprint1 == fingerprint2
        
        engine = MappingEngine()
        
        # First payload: no mapping exists, should return None 
        result1 = await engine.apply_mapping("github", payload1)
        
        # Should return None since no mapping exists yet
        assert result1 is None
        
        # Simulate what the service would do: call LLM to generate JSONata mapping
        jsonata_expr = await mock_generate_jsonata_mapping("github", payload1)
        assert jsonata_expr is not None
        
        # Store the JSONata mapping (simulating what the service would do)
        await engine.store_jsonata_mapping("github", payload1, jsonata_expr)
        
        # Verify mapping was stored
        assert fingerprint1 in stored_mappings
        stored_mapping = stored_mappings[fingerprint1]
        assert stored_mapping.publisher == "github"
        assert stored_mapping.event_name == "pull_request created"
        
        # Now the first payload should work with the stored mapping
        result1_retry = await engine.apply_mapping("github", payload1)
        assert result1_retry is not None
        assert result1_retry["publisher"] == "github"
        assert result1_retry["resource"]["type"] == "pull_request"
        assert result1_retry["resource"]["id"] == 1374
        assert result1_retry["action"] == "created"
        
        # Second payload: should use stored mapping, not LLM
        result2 = await engine.apply_mapping("github", payload2)
        
        # Should have same structure but different values
        assert result2 is not None
        assert result2["publisher"] == "github"
        assert result2["resource"]["type"] == "pull_request"
        assert result2["resource"]["id"] == 5678  # Different value from payload2
        assert result2["action"] == "created"
        
    finally:
        # Restore original methods
        db_service.get_ingestion_mapping = original_get_ingestion_mapping
        db_service.create_ingestion_mapping = original_create_ingestion_mapping
        llm_service.generate_jsonata_mapping = original_generate_jsonata_mapping
        llm_service.is_available = original_is_available


@pytest.mark.asyncio
async def test_fingerprinting_with_different_structures():
    """Test that different payload structures get different fingerprints and mappings."""
    from langhook.subscriptions.database import db_service
    from langhook.map.llm import llm_service
    
    # Mock services
    original_get_ingestion_mapping = db_service.get_ingestion_mapping
    original_is_available = llm_service.is_available
    
    stored_mappings = {}
    
    async def mock_get_ingestion_mapping(fingerprint: str):
        return stored_mappings.get(fingerprint)
    
    def mock_is_available():
        return False  # Force no LLM to test fingerprint differentiation
    
    db_service.get_ingestion_mapping = mock_get_ingestion_mapping
    llm_service.is_available = mock_is_available
    
    try:
        # Different payload structures
        payload_pr = {
            "action": "opened",
            "pull_request": {"number": 123},
            "repository": {"name": "test"}
        }
        
        payload_issue = {
            "action": "opened", 
            "issue": {"number": 456},
            "repository": {"name": "test"}
        }
        
        # Should generate different fingerprints
        fingerprint_pr = generate_fingerprint(payload_pr)
        fingerprint_issue = generate_fingerprint(payload_issue)
        
        assert fingerprint_pr != fingerprint_issue
        
        # Both should return None since no mapping exists and LLM is disabled
        engine = MappingEngine()
        
        result_pr = await engine.apply_mapping("github", payload_pr)
        result_issue = await engine.apply_mapping("github", payload_issue)
        
        assert result_pr is None
        assert result_issue is None
        
    finally:
        # Restore original methods
        db_service.get_ingestion_mapping = original_get_ingestion_mapping  
        llm_service.is_available = original_is_available


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_end_to_end_fingerprinting_workflow()
        print("End-to-end fingerprinting workflow test passed!")
        
        await test_fingerprinting_with_different_structures()
        print("Different structures test passed!")
    
    asyncio.run(run_tests())
    print("All end-to-end tests passed!")