"""Test the event schema registry functionality."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from langhook.subscriptions.models import EventSchemaRegistry
from langhook.subscriptions.schema_registry import SchemaRegistryService


@pytest.fixture
def schema_service():
    """Fixture for schema registry service."""
    return SchemaRegistryService()


@pytest.mark.asyncio
async def test_register_event_schema_success(schema_service):
    """Test successful schema registration."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = Mock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        await schema_service.register_event_schema(
            publisher="github",
            resource_type="pull_request",
            action="created"
        )

        # Verify database interaction
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_event_schema_sql_error(schema_service):
    """Test schema registration handles SQL errors gracefully."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = Mock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection error")
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Should not raise exception
        await schema_service.register_event_schema(
            publisher="github",
            resource_type="pull_request",
            action="created"
        )


@pytest.mark.asyncio
async def test_get_schema_summary_success(schema_service):
    """Test successful schema summary retrieval."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = Mock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock database entries
        mock_entries = [
            Mock(publisher="github", resource_type="pull_request", action="created"),
            Mock(publisher="github", resource_type="pull_request", action="updated"),
            Mock(publisher="github", resource_type="repository", action="created"),
            Mock(publisher="stripe", resource_type="refund", action="created"),
        ]
        mock_session.query.return_value.all.return_value = mock_entries

        result = await schema_service.get_schema_summary()

        expected = {
            "publishers": ["github", "stripe"],
            "resource_types": {
                "github": ["pull_request", "repository"],
                "stripe": ["refund"]
            },
            "actions": ["created", "updated"],
            "publisher_resource_actions": {
                "github": {
                    "pull_request": ["created", "updated"],
                    "repository": ["created"]
                },
                "stripe": {
                    "refund": ["created"]
                }
            }
        }

        assert result == expected


@pytest.mark.asyncio
async def test_get_schema_summary_empty_db(schema_service):
    """Test schema summary with empty database."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = Mock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.all.return_value = []

        result = await schema_service.get_schema_summary()

        expected = {
            "publishers": [],
            "resource_types": {},
            "actions": [],
            "publisher_resource_actions": {}
        }

        assert result == expected


@pytest.mark.asyncio
async def test_get_schema_summary_sql_error(schema_service):
    """Test schema summary handles SQL errors gracefully."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = Mock()
        mock_session.query.side_effect = SQLAlchemyError("Connection error")
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        result = await schema_service.get_schema_summary()

        # Should return empty structure on error
        expected = {
            "publishers": [],
            "resource_types": {},
            "actions": [],
            "publisher_resource_actions": {}
        }

        assert result == expected


def test_event_schema_registry_model():
    """Test the EventSchemaRegistry model structure."""
    # This is a basic structural test
    assert hasattr(EventSchemaRegistry, '__tablename__')
    assert EventSchemaRegistry.__tablename__ == "event_schema_registry"
    assert hasattr(EventSchemaRegistry, 'publisher')
    assert hasattr(EventSchemaRegistry, 'resource_type')
    assert hasattr(EventSchemaRegistry, 'action')


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        service = SchemaRegistryService()
        await test_register_event_schema_success(service)
        await test_get_schema_summary_success(service)
        await test_get_schema_summary_empty_db(service)
        print("All schema registry tests passed!")

    asyncio.run(run_tests())
