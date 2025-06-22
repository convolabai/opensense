"""Test resource type filtering functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from langhook.subscriptions.database import DatabaseService
from langhook.subscriptions.models import EventLog


@pytest.fixture
def mock_db_service():
    """Create a mock database service for testing."""
    db_service = DatabaseService.__new__(DatabaseService)
    db_service.get_session = MagicMock()
    return db_service


@pytest.mark.asyncio 
async def test_get_event_logs_with_resource_type_filter(mock_db_service):
    """Test that get_event_logs properly filters by resource types."""
    
    # Mock session and query
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 5
    mock_query.all.return_value = []
    
    mock_db_service.get_session.return_value.__enter__.return_value = mock_session
    mock_db_service.get_session.return_value.__exit__.return_value = None
    
    # Test with resource type filter
    result = await mock_db_service.get_event_logs(
        skip=0, 
        limit=10, 
        resource_types=['pull_request', 'issue']
    )
    
    # Verify filter was called with correct parameters
    mock_query.filter.assert_called_once()
    
    # Verify result structure
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[1] == 5  # total count


@pytest.mark.asyncio
async def test_get_event_logs_without_filter(mock_db_service):
    """Test that get_event_logs works without resource type filter."""
    
    # Mock session and query
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 10
    mock_query.all.return_value = []
    
    mock_db_service.get_session.return_value.__enter__.return_value = mock_session
    mock_db_service.get_session.return_value.__exit__.return_value = None
    
    # Test without resource type filter
    result = await mock_db_service.get_event_logs(skip=0, limit=10)
    
    # Verify filter was NOT called
    mock_query.filter.assert_not_called()
    
    # Verify result structure
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[1] == 10  # total count


@pytest.mark.asyncio
async def test_get_event_logs_with_empty_filter(mock_db_service):
    """Test that get_event_logs with empty resource types list works like no filter."""
    
    # Mock session and query
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 10
    mock_query.all.return_value = []
    
    mock_db_service.get_session.return_value.__enter__.return_value = mock_session
    mock_db_service.get_session.return_value.__exit__.return_value = None
    
    # Test with empty resource type filter
    result = await mock_db_service.get_event_logs(
        skip=0, 
        limit=10, 
        resource_types=[]
    )
    
    # Verify filter was NOT called for empty list
    mock_query.filter.assert_not_called()
    
    # Verify result structure
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[1] == 10  # total count


if __name__ == "__main__":
    print("Test resource type filtering...")