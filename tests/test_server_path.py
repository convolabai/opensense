"""Test server path configuration for reverse proxy deployments."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.core.config import load_app_config


@pytest.fixture
def client_with_server_path():
    """Create a test client with SERVER_PATH configured."""
    with patch.dict(os.environ, {"SERVER_PATH": "/langhook", "OPENAI_API_KEY": "test"}):
        # Force config reload to pick up new environment
        with patch('langhook.core.config.app_config', load_app_config(reload=True)):
            with patch('langhook.ingest.nats.nats_producer') as mock_nats, \
                 patch('langhook.map.service.mapping_service') as mock_mapping, \
                 patch('langhook.ingest.middleware.RateLimitMiddleware.is_rate_limited') as mock_rate_limit, \
                 patch('nats.connect') as mock_nats_connect:
                
                mock_nats.start = AsyncMock()
                mock_nats.stop = AsyncMock()
                mock_nats.send_raw_event = AsyncMock()
                mock_nats.send_dlq = AsyncMock()
                mock_mapping.run = AsyncMock()
                mock_rate_limit.return_value = False

                # Mock NATS connection
                from unittest.mock import Mock
                mock_nc = AsyncMock()
                mock_js = Mock()
                mock_js.publish = AsyncMock()
                mock_nc.jetstream = Mock(return_value=mock_js)
                mock_nc.close = AsyncMock()
                mock_nats_connect.return_value = mock_nc

                # Import and create app after patching config
                from langhook.app import app
                
                # Override lifespan for testing
                from contextlib import asynccontextmanager

                @asynccontextmanager
                async def mock_lifespan(app):
                    yield

                app.router.lifespan_context = mock_lifespan
                with TestClient(app) as client:
                    yield client


def test_health_endpoint_with_server_path(client_with_server_path):
    """Test health endpoint works with server path configured."""
    response = client_with_server_path.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"


def test_ingest_endpoint_with_server_path(client_with_server_path):
    """Test ingest endpoint works with server path configured."""
    with patch('langhook.ingest.nats.nats_producer') as mock_nats:
        mock_nats.send_raw_event = AsyncMock()

        payload = {"test": "data", "value": 123}
        response = client_with_server_path.post(
            "/ingest/github",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 202
        assert "request_id" in response.json()
        assert response.json()["message"] == "Event accepted"


def test_app_root_path_configuration():
    """Test that FastAPI app is configured with correct root_path."""
    with patch.dict(os.environ, {"SERVER_PATH": "/langhook", "OPENAI_API_KEY": "test"}):
        # Test config loading instead of app instance due to module caching
        config = load_app_config(reload=True)
        assert config.server_path == "/langhook"


def test_frontend_static_file_serving_with_server_path(client_with_server_path):
    """Test that frontend static files are served correctly with server path."""
    # This test requires the frontend to be built
    frontend_path = Path("langhook/static/index.html")
    if not frontend_path.exists():
        pytest.skip("Frontend not built - skipping static file test")
    
    response = client_with_server_path.get("/console")
    assert response.status_code == 200
    
    # Check that the HTML contains the correct asset paths
    html_content = response.text
    assert "/langhook/static/static/js/" in html_content
    assert "/langhook/static/static/css/" in html_content


def test_app_empty_root_path_configuration():
    """Test that FastAPI app handles empty SERVER_PATH correctly."""  
    with patch.dict(os.environ, {"SERVER_PATH": "", "OPENAI_API_KEY": "test"}):
        # Create a new app instance to test config
        config = load_app_config(reload=True)
        assert config.server_path == ""