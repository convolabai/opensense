"""Test the automatic NATS stream creation functionality."""

import pytest
from unittest.mock import AsyncMock, patch, Mock

from langhook.core.startup import ensure_nats_streams


@pytest.mark.asyncio
async def test_ensure_nats_streams_success():
    """Test successful NATS stream creation."""
    
    # Mock the StreamManager and its methods
    with patch('langhook.core.startup.StreamManager') as mock_stream_manager_class:
        mock_stream_manager = Mock()
        mock_stream_manager.connect = AsyncMock()
        mock_stream_manager.create_streams = AsyncMock()
        mock_stream_manager.disconnect = AsyncMock()
        mock_stream_manager_class.return_value = mock_stream_manager
        
        # Call the function
        await ensure_nats_streams("nats://localhost:4222")
        
        # Verify the StreamManager was used correctly
        mock_stream_manager_class.assert_called_once_with("nats://localhost:4222")
        mock_stream_manager.connect.assert_called_once()
        mock_stream_manager.create_streams.assert_called_once()
        mock_stream_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_nats_streams_connection_failure():
    """Test handling of NATS connection failure."""
    
    with patch('langhook.core.startup.StreamManager') as mock_stream_manager_class:
        mock_stream_manager = Mock()
        mock_stream_manager.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_stream_manager.disconnect = AsyncMock()
        mock_stream_manager_class.return_value = mock_stream_manager
        
        # The function should re-raise the exception
        with pytest.raises(Exception, match="Connection failed"):
            await ensure_nats_streams("nats://localhost:4222")
        
        # Verify cleanup was called even after failure
        mock_stream_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_nats_streams_creation_failure():
    """Test handling of stream creation failure."""
    
    with patch('langhook.core.startup.StreamManager') as mock_stream_manager_class:
        mock_stream_manager = Mock()
        mock_stream_manager.connect = AsyncMock()
        mock_stream_manager.create_streams = AsyncMock(side_effect=Exception("Stream creation failed"))
        mock_stream_manager.disconnect = AsyncMock()
        mock_stream_manager_class.return_value = mock_stream_manager
        
        # The function should re-raise the exception
        with pytest.raises(Exception, match="Stream creation failed"):
            await ensure_nats_streams("nats://localhost:4222")
        
        # Verify cleanup was called even after failure
        mock_stream_manager.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_nats_streams_streams_already_exist():
    """Test that the function works correctly when streams already exist."""
    
    with patch('langhook.core.startup.StreamManager') as mock_stream_manager_class:
        mock_stream_manager = Mock()
        mock_stream_manager.connect = AsyncMock()
        # Simulate the case where create_streams handles existing streams gracefully
        mock_stream_manager.create_streams = AsyncMock()
        mock_stream_manager.disconnect = AsyncMock()
        mock_stream_manager_class.return_value = mock_stream_manager
        
        # Call the function - should not raise any exceptions
        await ensure_nats_streams("nats://localhost:4222")
        
        # Verify all methods were called
        mock_stream_manager.connect.assert_called_once()
        mock_stream_manager.create_streams.assert_called_once()
        mock_stream_manager.disconnect.assert_called_once()