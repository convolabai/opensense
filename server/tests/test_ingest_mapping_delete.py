"""Test ingest mapping deletion functionality."""

import pytest
from unittest.mock import patch, MagicMock

from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import IngestMapping


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    with patch.object(db_service, 'get_session') as mock_get_session:
        mock_get_session.return_value.__enter__.return_value = session
        mock_get_session.return_value.__exit__.return_value = None
        yield session


@pytest.mark.asyncio
async def test_delete_ingestion_mapping_success(mock_session):
    """Test successful deletion of an ingest mapping."""
    # Mock mapping object
    mock_mapping = MagicMock()
    mock_mapping.fingerprint = "test_fingerprint"
    mock_mapping.publisher = "github"
    mock_mapping.event_name = "pull_request created"
    
    # Configure session mock
    mock_session.query.return_value.filter.return_value.first.return_value = mock_mapping
    
    # Test deletion
    result = await db_service.delete_ingestion_mapping("test_fingerprint")
    
    assert result is True
    mock_session.delete.assert_called_once_with(mock_mapping)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_ingestion_mapping_not_found(mock_session):
    """Test deletion of non-existent ingest mapping."""
    # Configure session mock to return None
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    # Test deletion
    result = await db_service.delete_ingestion_mapping("nonexistent_fingerprint")
    
    assert result is False
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()