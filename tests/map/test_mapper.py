"""Test the mapping engine functionality."""

import tempfile
from pathlib import Path
import pytest

from langhook.map.mapper import MappingEngine


@pytest.mark.asyncio
async def test_mapping_engine_loads_jsonata_files():
    """Test that the mapping engine loads JSONata files correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test mapping file
        mapping_file = Path(temp_dir) / "test.jsonata"
        mapping_file.write_text('{"publisher": "test", "resource": {"type": "item", "id": $.id}, "action": $.action = "created" ? "create" : "update"}')

        # Create engine with temp directory
        engine = MappingEngine()
        engine._mappings = {}  # Clear any existing mappings

        # Override mappings directory
        original_dir = engine.mappings_dir if hasattr(engine, 'mappings_dir') else None

        # Manually load from temp directory
        from langhook.map.config import settings
        original_mappings_dir = settings.mappings_dir
        settings.mappings_dir = temp_dir

        try:
            engine._load_mappings()
            assert engine.has_mapping("test")

            # Test applying the mapping
            test_payload = {"action": "created", "id": 123}
            result = await engine.apply_mapping("test", test_payload)

            assert result is not None
            assert result["publisher"] == "test"
            assert result["resource"]["type"] == "item"
            assert result["resource"]["id"] == 123
            assert result["action"] == "created"

        finally:
            settings.mappings_dir = original_mappings_dir


@pytest.mark.asyncio
async def test_mapping_engine_handles_missing_fields():
    """Test that the mapping engine handles missing required fields."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mapping file that's missing required fields
        mapping_file = Path(temp_dir) / "incomplete.jsonata"
        mapping_file.write_text('{"publisher": "test", "action": "create"}')  # Missing resource

        engine = MappingEngine()
        engine._mappings = {}

        from langhook.map.config import settings
        original_mappings_dir = settings.mappings_dir
        settings.mappings_dir = temp_dir

        try:
            engine._load_mappings()
            assert engine.has_mapping("incomplete")

            # Test applying the incomplete mapping
            test_payload = {"action": "created", "id": 123}
            result = await engine.apply_mapping("incomplete", test_payload)

            # Should return None due to missing required fields
            assert result is None

        finally:
            settings.mappings_dir = original_mappings_dir


@pytest.mark.asyncio
async def test_github_mapping():
    """Test the GitHub mapping with sample data."""
    engine = MappingEngine()

    # Sample GitHub PR payload
    github_payload = {
        "action": "opened",
        "pull_request": {
            "number": 1374,
            "title": "Add new feature",
            "state": "open"
        },
        "repository": {
            "name": "test-repo",
            "id": 12345
        }
    }

    # Load mappings from the actual mappings directory
    engine._load_mappings()

    if engine.has_mapping("github"):
        result = await engine.apply_mapping("github", github_payload)

        assert result is not None
        assert result["publisher"] == "github"
        assert result["resource"]["type"] == "pull_request"
        assert result["resource"]["id"] == 1374
        assert result["action"] == "created"  # "opened" maps to "create" which converts to "created"
    else:
        print("GitHub mapping not found - test skipped")


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_mapping_engine_loads_jsonata_files()
        await test_mapping_engine_handles_missing_fields()
        await test_github_mapping()
        print("All mapping tests passed!")
    
    asyncio.run(run_tests())
