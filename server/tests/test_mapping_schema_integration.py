"""Integration test for schema registry with mapping service."""

from unittest.mock import AsyncMock, patch

import pytest

from langhook.map.service import MappingService


@pytest.mark.asyncio
async def test_mapping_service_registers_schema():
    """Test that the mapping service registers event schemas."""
    service = MappingService()

    # Mock all dependencies
    with patch('langhook.map.service.cloud_event_wrapper') as mock_wrapper, \
         patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.mapping_engine') as mock_engine, \
         patch('langhook.map.service.schema_registry_service') as mock_schema_service, \
         patch('langhook.map.service.metrics'):

        # Mock mapping engine to return canonical data
        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 1374},
            "action": "created"
        }
        mock_engine.apply_mapping.return_value = canonical_data

        # Mock cloud event wrapper
        canonical_event = {"data": canonical_data}
        mock_wrapper.wrap_and_validate.return_value = canonical_event

        # Mock producer
        mock_producer.send_canonical_event = AsyncMock()

        # Mock schema registry service
        mock_schema_service.register_event_schema = AsyncMock()

        # Create raw event
        raw_event = {
            "id": "test-123",
            "source": "github",
            "payload": {"action": "opened", "pull_request": {"number": 1374}}
        }

        # Process the event
        await service._process_raw_event(raw_event)

        # Verify schema registry was called
        mock_schema_service.register_event_schema.assert_called_once_with(
            publisher="github",
            resource_type="pull_request",
            action="created"
        )

        # Verify canonical event was sent
        mock_producer.send_canonical_event.assert_called_once_with(canonical_event)


@pytest.mark.asyncio
async def test_mapping_service_handles_schema_registration_failure():
    """Test that mapping service continues even if schema registration fails."""
    service = MappingService()

    with patch('langhook.map.service.cloud_event_wrapper') as mock_wrapper, \
         patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.mapping_engine') as mock_engine, \
         patch('langhook.map.service.schema_registry_service') as mock_schema_service, \
         patch('langhook.map.service.metrics'):

        # Mock mapping engine to return canonical data
        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 1374},
            "action": "created"
        }
        mock_engine.apply_mapping.return_value = canonical_data

        # Mock cloud event wrapper
        canonical_event = {"data": canonical_data}
        mock_wrapper.wrap_and_validate.return_value = canonical_event

        # Mock producer
        mock_producer.send_canonical_event = AsyncMock()

        # Mock schema registry service to raise exception
        mock_schema_service.register_event_schema = AsyncMock(side_effect=Exception("DB error"))

        # Create raw event
        raw_event = {
            "id": "test-123",
            "source": "github",
            "payload": {"action": "opened", "pull_request": {"number": 1374}}
        }

        # Process the event - should not raise exception
        await service._process_raw_event(raw_event)

        # Verify canonical event was still sent despite schema registry failure
        mock_producer.send_canonical_event.assert_called_once_with(canonical_event)


@pytest.mark.asyncio
async def test_mapping_service_skips_schema_registration_for_incomplete_data():
    """Test that mapping service skips schema registration for incomplete canonical data."""
    service = MappingService()

    with patch('langhook.map.service.cloud_event_wrapper') as mock_wrapper, \
         patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.mapping_engine') as mock_engine, \
         patch('langhook.map.service.schema_registry_service') as mock_schema_service, \
         patch('langhook.map.service.metrics'):

        # Mock mapping engine to return incomplete canonical data (missing action)
        canonical_data = {
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 1374}
            # missing action
        }
        mock_engine.apply_mapping.return_value = canonical_data

        # Mock cloud event wrapper
        canonical_event = {"data": canonical_data}
        mock_wrapper.wrap_and_validate.return_value = canonical_event

        # Mock producer
        mock_producer.send_canonical_event = AsyncMock()
        mock_producer.send_mapping_failure = AsyncMock()

        # Mock schema registry service
        mock_schema_service.register_event_schema = AsyncMock()

        # Create raw event
        raw_event = {
            "id": "test-123",
            "source": "github",
            "payload": {"action": "opened", "pull_request": {"number": 1374}}
        }

        # Process the event - will fail due to missing action in logging
        await service._process_raw_event(raw_event)

        # Verify schema registry was NOT called due to incomplete data
        mock_schema_service.register_event_schema.assert_not_called()

        # Since the event processing failed, mapping failure should be called
        mock_producer.send_mapping_failure.assert_called_once()


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        await test_mapping_service_registers_schema()
        await test_mapping_service_handles_schema_registration_failure()
        await test_mapping_service_skips_schema_registration_for_incomplete_data()
        print("All mapping service integration tests passed!")

    asyncio.run(run_tests())
