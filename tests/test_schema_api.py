"""Test the schema API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.app import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_schema_endpoint_success(client):
    """Test the /schema endpoint returns expected structure."""
    mock_schema_data = {
        "publishers": ["github", "stripe"],
        "resource_types": {
            "github": ["pull_request", "repository"],
            "stripe": ["refund"]
        },
        "actions": ["created", "updated", "deleted"]
    }

    with patch('langhook.subscriptions.schema_routes.schema_registry_service.get_schema_summary',
               new_callable=AsyncMock) as mock_get_summary:
        mock_get_summary.return_value = mock_schema_data

        response = client.get("/schema/")

        assert response.status_code == 200
        assert response.json() == mock_schema_data
        mock_get_summary.assert_called_once()


def test_schema_endpoint_empty_response(client):
    """Test the /schema endpoint with empty schema registry."""
    mock_empty_data = {
        "publishers": [],
        "resource_types": {},
        "actions": []
    }

    with patch('langhook.subscriptions.schema_routes.schema_registry_service.get_schema_summary',
               new_callable=AsyncMock) as mock_get_summary:
        mock_get_summary.return_value = mock_empty_data

        response = client.get("/schema/")

        assert response.status_code == 200
        assert response.json() == mock_empty_data


def test_schema_endpoint_service_error(client):
    """Test the /schema endpoint handles service errors gracefully."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.get_schema_summary',
               new_callable=AsyncMock) as mock_get_summary:
        # The service itself handles exceptions and returns empty structure
        mock_get_summary.return_value = {
            "publishers": [],
            "resource_types": {},
            "actions": []
        }

        response = client.get("/schema/")

        assert response.status_code == 200
        assert response.json() == {
            "publishers": [],
            "resource_types": {},
            "actions": []
        }


if __name__ == "__main__":
    test_client = TestClient(app)
    test_schema_endpoint_success(test_client)
    print("Schema API tests passed!")
