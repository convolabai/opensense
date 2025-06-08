"""Test LLM direct transformation functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from langhook.map.llm import LLMSuggestionService


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service for testing."""
    service = LLMSuggestionService()
    service.llm_available = True
    service.llm = Mock()
    return service


@pytest.mark.asyncio
async def test_transform_to_canonical_success(mock_llm_service):
    """Test successful transformation to canonical format."""
    # Mock LLM response
    mock_response = Mock()
    mock_response.generations = [[Mock()]]
    mock_response.generations[0][0].text = '{"publisher": "github", "resource": {"type": "pull_request", "id": 123}, "action": "created"}'
    
    mock_llm_service.llm.agenerate = AsyncMock(return_value=mock_response)
    
    # Test data
    source = "github"
    raw_payload = {"action": "opened", "pull_request": {"number": 123}}
    
    # Call the transformation
    result = await mock_llm_service.transform_to_canonical(source, raw_payload)
    
    # Assertions
    assert result is not None
    assert result["publisher"] == "github"
    assert result["resource"]["type"] == "pull_request"
    assert result["resource"]["id"] == 123
    assert result["action"] == "created"


@pytest.mark.asyncio
async def test_transform_to_canonical_invalid_json(mock_llm_service):
    """Test handling of invalid JSON response from LLM."""
    # Mock LLM response with invalid JSON
    mock_response = Mock()
    mock_response.generations = [[Mock()]]
    mock_response.generations[0][0].text = 'invalid json {'
    
    mock_llm_service.llm.agenerate = AsyncMock(return_value=mock_response)
    
    # Test data
    source = "github"
    raw_payload = {"action": "opened", "pull_request": {"number": 123}}
    
    # Call the transformation
    result = await mock_llm_service.transform_to_canonical(source, raw_payload)
    
    # Should return None for invalid JSON
    assert result is None


@pytest.mark.asyncio
async def test_transform_to_canonical_missing_fields(mock_llm_service):
    """Test handling of canonical format missing required fields."""
    # Mock LLM response missing required fields
    mock_response = Mock()
    mock_response.generations = [[Mock()]]
    mock_response.generations[0][0].text = '{"publisher": "github", "action": "created"}'  # Missing resource
    
    mock_llm_service.llm.agenerate = AsyncMock(return_value=mock_response)
    
    # Test data
    source = "github"
    raw_payload = {"action": "opened", "pull_request": {"number": 123}}
    
    # Call the transformation
    result = await mock_llm_service.transform_to_canonical(source, raw_payload)
    
    # Should return None for missing required fields
    assert result is None


@pytest.mark.asyncio
async def test_transform_to_canonical_service_unavailable():
    """Test transformation when LLM service is unavailable."""
    service = LLMSuggestionService()
    service.llm_available = False
    
    # Test data
    source = "github"
    raw_payload = {"action": "opened", "pull_request": {"number": 123}}
    
    # Call the transformation
    result = await service.transform_to_canonical(source, raw_payload)
    
    # Should return None when service unavailable
    assert result is None


def test_validate_canonical_format_success():
    """Test validation of correct canonical format."""
    service = LLMSuggestionService()
    
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": 123},
        "action": "created"
    }
    
    result = service._validate_canonical_format(canonical_data, "github")
    assert result is True


def test_validate_canonical_format_invalid_action():
    """Test validation fails for invalid action."""
    service = LLMSuggestionService()
    
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": 123},
        "action": "invalid_action"  # Invalid action
    }
    
    result = service._validate_canonical_format(canonical_data, "github")
    assert result is False


def test_validate_canonical_format_invalid_resource_id():
    """Test validation fails for resource ID with invalid characters."""
    service = LLMSuggestionService()
    
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": "123#456"},  # Invalid ID with hash
        "action": "created"
    }
    
    result = service._validate_canonical_format(canonical_data, "github")
    assert result is False


def test_validate_canonical_format_allows_slash_in_resource_id():
    """Test validation allows slash in resource ID."""
    service = LLMSuggestionService()
    
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": "123/456"},  # Valid ID with slash (now allowed)
        "action": "created"
    }
    
    result = service._validate_canonical_format(canonical_data, "github")
    assert result is True