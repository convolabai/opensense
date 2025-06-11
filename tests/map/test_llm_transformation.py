"""Test LLM direct transformation functionality."""

from unittest.mock import AsyncMock, Mock

import pytest

from langhook.map.llm import LLMSuggestionService


@pytest.fixture
def mock_llm_service(monkeypatch):
    """Create a mock LLM service for testing."""
    # Mock the settings to have an API key
    from langhook.map import config
    monkeypatch.setattr(config.settings, 'openai_api_key', 'test-key-for-testing')
    
    # Mock the ChatOpenAI import to avoid actual initialization
    from unittest.mock import Mock, patch
    with patch('langchain_openai.ChatOpenAI') as mock_chat_openai:
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        service = LLMSuggestionService()
        service.llm = Mock()
        return service


@pytest.mark.asyncio
async def test_transform_to_canonical_success(mock_llm_service):
    """Test successful transformation to canonical format."""
    # Mock LLM response
    mock_response = Mock()
    mock_response.generations = [[Mock()]]
    mock_response.generations[0][0].text = '{"publisher": "github", "resource": {"type": "pull_request", "id": 123}, "action": "created", "timestamp": "2024-01-01T00:00:00Z"}'

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
    assert result["timestamp"] == "2024-01-01T00:00:00Z"


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
async def test_llm_service_initialization_failure():
    """Test that LLM service fails to initialize when not properly configured."""
    import os
    
    # Save current API key if it exists
    original_key = os.environ.get('OPENAI_API_KEY')
    
    try:
        # Remove API key to simulate unavailable LLM
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        # Should raise ValueError during initialization
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            LLMSuggestionService()
            
    finally:
        # Restore original API key if it existed
        if original_key:
            os.environ['OPENAI_API_KEY'] = original_key


def test_validate_canonical_format_success(monkeypatch):
    """Test validation of correct canonical format."""
    # Mock the settings to have an API key
    from langhook.map import config
    monkeypatch.setattr(config.settings, 'openai_api_key', 'test-key-for-testing')
    
    # Mock the ChatOpenAI import to avoid actual initialization
    from unittest.mock import Mock, patch
    with patch('langchain_openai.ChatOpenAI') as mock_chat_openai:
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        service = LLMSuggestionService()

        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 123},
            "action": "created",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        result = service._validate_canonical_format(canonical_data, "github")
        assert result is True


def test_validate_canonical_format_invalid_action(monkeypatch):
    """Test validation fails for invalid action."""
    # Mock the settings to have an API key
    from langhook.map import config
    monkeypatch.setattr(config.settings, 'openai_api_key', 'test-key-for-testing')
    
    # Mock the ChatOpenAI import to avoid actual initialization
    from unittest.mock import Mock, patch
    with patch('langchain_openai.ChatOpenAI') as mock_chat_openai:
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        service = LLMSuggestionService()

        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 123},
            "action": "invalid_action",  # Invalid action
            "timestamp": "2024-01-01T00:00:00Z"
        }

        result = service._validate_canonical_format(canonical_data, "github")
        assert result is False


def test_validate_canonical_format_invalid_resource_id(monkeypatch):
    """Test validation fails for resource ID with invalid characters."""
    # Mock the settings to have an API key
    from langhook.map import config
    monkeypatch.setattr(config.settings, 'openai_api_key', 'test-key-for-testing')
    
    # Mock the ChatOpenAI import to avoid actual initialization
    from unittest.mock import Mock, patch
    with patch('langchain_openai.ChatOpenAI') as mock_chat_openai:
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        service = LLMSuggestionService()

        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": "123#456"},  # Invalid ID with hash
            "action": "created",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        result = service._validate_canonical_format(canonical_data, "github")
        assert result is False


def test_validate_canonical_format_allows_slash_in_resource_id(monkeypatch):
    """Test validation allows slash in resource ID."""
    # Mock the settings to have an API key
    from langhook.map import config
    monkeypatch.setattr(config.settings, 'openai_api_key', 'test-key-for-testing')
    
    # Mock the ChatOpenAI import to avoid actual initialization
    from unittest.mock import Mock, patch
    with patch('langchain_openai.ChatOpenAI') as mock_chat_openai:
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        service = LLMSuggestionService()

        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": "123/456"},  # Valid ID with slash (now allowed)
            "action": "created",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        result = service._validate_canonical_format(canonical_data, "github")
        assert result is True
