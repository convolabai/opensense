"""Test the schema deletion API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from langhook.app import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_delete_publisher_success(client):
    """Test successful publisher deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_publisher',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        response = client.delete("/schema/publishers/github")

        assert response.status_code == 204
        mock_delete.assert_called_once_with("github")


def test_delete_publisher_not_found(client):
    """Test deleting non-existent publisher."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_publisher',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = False

        response = client.delete("/schema/publishers/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Publisher 'nonexistent' not found"
        mock_delete.assert_called_once_with("nonexistent")


def test_delete_publisher_server_error(client):
    """Test server error during publisher deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_publisher',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = Exception("Database error")

        response = client.delete("/schema/publishers/github")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to delete publisher"


def test_delete_resource_type_success(client):
    """Test successful resource type deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_resource_type',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        response = client.delete("/schema/publishers/github/resource-types/pull_request")

        assert response.status_code == 204
        mock_delete.assert_called_once_with("github", "pull_request")


def test_delete_resource_type_not_found(client):
    """Test deleting non-existent resource type."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_resource_type',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = False

        response = client.delete("/schema/publishers/github/resource-types/nonexistent")

        assert response.status_code == 404
        assert "Resource type 'nonexistent' not found for publisher 'github'" in response.json()["detail"]
        mock_delete.assert_called_once_with("github", "nonexistent")


def test_delete_resource_type_server_error(client):
    """Test server error during resource type deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_resource_type',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = Exception("Database error")

        response = client.delete("/schema/publishers/github/resource-types/pull_request")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to delete resource type"


def test_delete_action_success(client):
    """Test successful action deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_action',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        response = client.delete("/schema/publishers/github/resource-types/pull_request/actions/created")

        assert response.status_code == 204
        mock_delete.assert_called_once_with("github", "pull_request", "created")


def test_delete_action_not_found(client):
    """Test deleting non-existent action."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_action',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = False

        response = client.delete("/schema/publishers/github/resource-types/pull_request/actions/nonexistent")

        assert response.status_code == 404
        assert "Action 'nonexistent' not found for publisher 'github' and resource type 'pull_request'" in response.json()["detail"]
        mock_delete.assert_called_once_with("github", "pull_request", "nonexistent")


def test_delete_action_server_error(client):
    """Test server error during action deletion."""
    with patch('langhook.subscriptions.schema_routes.schema_registry_service.delete_action',
               new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = Exception("Database error")

        response = client.delete("/schema/publishers/github/resource-types/pull_request/actions/created")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to delete action"


def test_get_schema_still_works(client):
    """Test that the GET /schema endpoint still works after moving to router."""
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


if __name__ == "__main__":
    test_client = TestClient(app)
    print("Schema deletion API tests running...")
    
    # Run basic test
    test_delete_publisher_success(test_client)
    test_get_schema_still_works(test_client)
    
    print("Schema deletion API tests passed!")