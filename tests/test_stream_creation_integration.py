"""Test that stream creation is integrated into the app startup process."""

import pytest
from unittest.mock import AsyncMock, patch, Mock

from langhook.core.startup import ensure_nats_streams


def test_simple_verify_import():
    """Simple test to verify that the startup module can be imported correctly."""
    from langhook.core.startup import ensure_nats_streams
    from langhook.app import app
    
    # If we can import these, the integration is working
    assert ensure_nats_streams is not None
    assert app is not None
    
    # Verify that the app.py file contains the import we added
    import inspect
    import langhook.app
    
    # Get the source code of the lifespan function
    lifespan_source = inspect.getsource(langhook.app.lifespan)
    
    # Verify that our stream creation is called in the lifespan
    assert "ensure_nats_streams" in lifespan_source
    assert "from langhook.core.startup import ensure_nats_streams" in lifespan_source


@pytest.mark.asyncio 
async def test_ensure_nats_streams_integration():
    """Test that ensure_nats_streams function works as expected in isolation."""
    
    # Test that the function handles the NATS URL correctly
    with patch('langhook.core.startup.StreamManager') as mock_stream_manager_class:
        mock_stream_manager = Mock()
        mock_stream_manager.connect = AsyncMock()
        mock_stream_manager.create_streams = AsyncMock()
        mock_stream_manager.disconnect = AsyncMock()
        mock_stream_manager_class.return_value = mock_stream_manager
        
        # Test with a sample NATS URL
        test_url = "nats://localhost:4222"
        await ensure_nats_streams(test_url)
        
        # Verify StreamManager was initialized with correct URL
        mock_stream_manager_class.assert_called_once_with(test_url)
        
        # Verify the correct sequence of calls
        mock_stream_manager.connect.assert_called_once()
        mock_stream_manager.create_streams.assert_called_once()
        mock_stream_manager.disconnect.assert_called_once()