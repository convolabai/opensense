"""Test to verify schema creation behavior doesn't create unwanted actions."""

import pytest
from unittest.mock import patch, MagicMock

from langhook.subscriptions.schema_registry import schema_registry_service
from langhook.map.service import MappingService


@pytest.mark.asyncio
async def test_single_action_registration():
    """Test that only the specific action in the event is registered, not multiple default actions."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        # Register a single event with a 'created' action
        await schema_registry_service.register_event_schema(
            publisher="github",
            resource_type="pull_request", 
            action="created"
        )
        
        # Verify only one call to execute (one INSERT statement)
        assert mock_session.execute.call_count == 1
        
        # Get the executed query and parameters
        call_args = mock_session.execute.call_args
        query_params = call_args[0][1]  # Second argument is the parameters dict
        
        # Verify only the specific action was inserted
        assert query_params['action'] == 'created'
        assert query_params['publisher'] == 'github'
        assert query_params['resource_type'] == 'pull_request'
        
        # No additional actions like 'updated' or 'read' should be created
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_canonical_event_processing_single_action():
    """Test that processing a canonical event only registers the actual action, not default actions."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        # Create a mapping service
        service = MappingService()
        
        # Test canonical data with only one action
        canonical_data = {
            "publisher": "github",
            "resource": {
                "type": "pull_request",
                "id": "123"
            },
            "action": "opened",  # Only this action should be registered
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        # Call the schema registration method directly
        await service._register_event_schema(canonical_data)
        
        # Verify only one registration call
        assert mock_session.execute.call_count == 1
        
        # Verify the correct action was registered
        call_args = mock_session.execute.call_args
        query_params = call_args[0][1]
        assert query_params['action'] == 'opened'
        
        # Actions like 'created', 'updated', 'read' should NOT be present
        assert query_params['action'] != 'created'
        assert query_params['action'] != 'updated'
        assert query_params['action'] != 'read'


@pytest.mark.asyncio
async def test_multiple_events_different_actions():
    """Test that multiple events with different actions register correctly."""
    with patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        # Register different actions separately
        await schema_registry_service.register_event_schema(
            publisher="github",
            resource_type="pull_request",
            action="opened"
        )
        
        await schema_registry_service.register_event_schema(
            publisher="github", 
            resource_type="pull_request",
            action="closed"
        )
        
        # Should have exactly 2 calls, one for each action
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 2
        
        # Verify the actions registered
        call_args_list = mock_session.execute.call_args_list
        actions_registered = [call[0][1]['action'] for call in call_args_list]
        
        assert 'opened' in actions_registered
        assert 'closed' in actions_registered
        assert len(actions_registered) == 2  # Only these two, no extras