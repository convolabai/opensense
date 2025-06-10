"""Test the enhanced fingerprinting and mapping workflow end-to-end."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langhook.map.mapper import MappingEngine
from langhook.map.fingerprint import generate_fingerprint, generate_enhanced_fingerprint
from langhook.subscriptions import database as db_service


@pytest.mark.asyncio
async def test_enhanced_fingerprinting_workflow():
    """Test that enhanced fingerprinting correctly distinguishes between events with same structure but different actions."""
    
    # Mock the database service
    original_get_ingestion_mappings_by_structure = db_service.db_service.get_ingestion_mappings_by_structure
    original_create_ingestion_mapping = db_service.db_service.create_ingestion_mapping
    
    # Storage for mappings
    stored_mappings = {}
    
    async def mock_get_ingestion_mappings_by_structure(structure_fingerprint: str):
        """Mock method to return stored mappings with matching structure."""
        matching = []
        for mapping in stored_mappings.values():
            if mapping.structure:
                from langhook.map.fingerprint import create_canonical_string
                import hashlib
                mapping_structure_fingerprint = hashlib.sha256(
                    create_canonical_string(mapping.structure).encode('utf-8')
                ).hexdigest()
                if mapping_structure_fingerprint == structure_fingerprint:
                    matching.append(mapping)
        return matching
    
    async def mock_create_ingestion_mapping(fingerprint, publisher, event_name, mapping_expr, structure, event_field_expr=None):
        """Mock method to store mapping."""
        class MockMapping:
            def __init__(self, fp, pub, en, me, struct, efe):
                self.fingerprint = fp
                self.publisher = pub
                self.event_name = en
                self.mapping_expr = me
                self.structure = struct
                self.event_field_expr = efe
        
        mapping = MockMapping(fingerprint, publisher, event_name, mapping_expr, structure, event_field_expr)
        stored_mappings[fingerprint] = mapping
        return mapping
    
    # Apply mocks
    db_service.db_service.get_ingestion_mappings_by_structure = mock_get_ingestion_mappings_by_structure
    db_service.db_service.create_ingestion_mapping = mock_create_ingestion_mapping
    
    try:
        # GitHub PR opened payload
        payload_opened = {
            "action": "opened",
            "number": 1374,
            "pull_request": {
                "id": 1374,
                "title": "Add new feature",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "repository": {"name": "test-repo"}
        }
        
        # GitHub PR approved payload (same structure, different action)
        payload_approved = {
            "action": "approved",  # Different action
            "number": 1374,
            "pull_request": {
                "id": 1374,
                "title": "Add new feature",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "repository": {"name": "test-repo"}
        }
        
        # Verify basic fingerprints are the same (problem described in issue)
        basic_fp_opened = generate_fingerprint(payload_opened)
        basic_fp_approved = generate_fingerprint(payload_approved)
        assert basic_fp_opened == basic_fp_approved
        
        # Verify enhanced fingerprints are different (solution)
        enhanced_fp_opened = generate_enhanced_fingerprint(payload_opened, "action")
        enhanced_fp_approved = generate_enhanced_fingerprint(payload_approved, "action")
        assert enhanced_fp_opened != enhanced_fp_approved
        
        engine = MappingEngine()
        
        # First, neither payload should find a mapping
        result1 = await engine.apply_mapping("github", payload_opened)
        assert result1 is None
        
        result2 = await engine.apply_mapping("github", payload_approved)
        assert result2 is None
        
        # Store mapping for "opened" action with event field expression
        jsonata_opened = '{"publisher":"github","resource":{"type":"pull_request","id":pull_request.id},"action":"created","timestamp":pull_request.created_at,"raw":$}'
        
        await engine.store_jsonata_mapping_with_event_field(
            "github", 
            payload_opened, 
            jsonata_opened,
            "action"  # Event field expression
        )
        
        # Verify the mapping was stored with enhanced fingerprint
        assert enhanced_fp_opened in stored_mappings
        stored_mapping = stored_mappings[enhanced_fp_opened]
        assert stored_mapping.event_field_expr == "action"
        
        # Now the "opened" payload should find its mapping
        result1_retry = await engine.apply_mapping("github", payload_opened)
        assert result1_retry is not None
        assert result1_retry["action"] == "created"
        
        # But the "approved" payload should still not find a mapping
        result2_retry = await engine.apply_mapping("github", payload_approved)
        assert result2_retry is None  # Different enhanced fingerprint
        
        # Store mapping for "approved" action
        jsonata_approved = '{"publisher":"github","resource":{"type":"pull_request","id":pull_request.id},"action":"updated","timestamp":pull_request.created_at,"raw":$}'
        
        await engine.store_jsonata_mapping_with_event_field(
            "github", 
            payload_approved, 
            jsonata_approved,
            "action"  # Same event field expression
        )
        
        # Now both payloads should find their respective mappings
        result1_final = await engine.apply_mapping("github", payload_opened)
        assert result1_final is not None
        assert result1_final["action"] == "created"
        
        result2_final = await engine.apply_mapping("github", payload_approved)
        assert result2_final is not None
        assert result2_final["action"] == "updated"
        
        # Verify we have two different mappings stored
        assert len(stored_mappings) == 2
        assert enhanced_fp_opened in stored_mappings
        assert enhanced_fp_approved in stored_mappings
        
    finally:
        # Restore original methods
        db_service.db_service.get_ingestion_mappings_by_structure = original_get_ingestion_mappings_by_structure
        db_service.db_service.create_ingestion_mapping = original_create_ingestion_mapping


@pytest.mark.asyncio
async def test_backwards_compatibility_with_basic_fingerprints():
    """Test that the system still works with existing mappings that don't have event field expressions."""
    
    # Mock the database service
    original_get_ingestion_mappings_by_structure = db_service.db_service.get_ingestion_mappings_by_structure
    
    # Storage for mappings
    stored_mappings = {}
    
    async def mock_get_ingestion_mappings_by_structure(structure_fingerprint: str):
        """Mock method to return a basic mapping without event field expression."""
        class MockMapping:
            def __init__(self):
                self.fingerprint = structure_fingerprint  # Basic fingerprint
                self.publisher = "github"
                self.event_name = "pull_request unknown"
                self.mapping_expr = '{"publisher":"github","resource":{"type":"pull_request","id":pull_request.id},"action":"updated","timestamp":"2024-01-01T00:00:00Z","raw":$}'
                self.structure = {"action": "string", "number": "number", "pull_request": {"id": "number", "title": "string"}}
                self.event_field_expr = None  # No event field expression (legacy mapping)
        
        return [MockMapping()] if structure_fingerprint in stored_mappings else []
    
    # Apply mock
    db_service.db_service.get_ingestion_mappings_by_structure = mock_get_ingestion_mappings_by_structure
    
    try:
        payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {
                "id": 123,
                "title": "Test PR"
            }
        }
        
        basic_fingerprint = generate_fingerprint(payload)
        stored_mappings[basic_fingerprint] = True  # Mark as stored
        
        engine = MappingEngine()
        
        # Should find the legacy mapping
        result = await engine.apply_mapping("github", payload)
        assert result is not None
        assert result["publisher"] == "github"
        assert result["action"] == "updated"
        
    finally:
        # Restore original method
        db_service.db_service.get_ingestion_mappings_by_structure = original_get_ingestion_mappings_by_structure


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_enhanced_fingerprinting_workflow()
        print("Enhanced fingerprinting workflow test passed!")
        
        await test_backwards_compatibility_with_basic_fingerprints()
        print("Backwards compatibility test passed!")
    
    asyncio.run(run_tests())
    print("All integration tests passed!")