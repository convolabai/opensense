"""Test the complete mapping service end-to-end."""

import asyncio
from unittest.mock import AsyncMock, patch

from langhook.map.service import MappingService


async def test_llm_transformation_flow():
    """Test that LLM transformation is used when no mapping exists."""
    print("Testing LLM transformation flow...")

    # Mock both the Kafka producer and LLM service
    with patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.llm_service') as mock_llm:

        mock_producer.send_canonical_event = AsyncMock()
        mock_producer.send_mapping_failure = AsyncMock()

        # Mock LLM service to be available and return JSONata expression
        mock_llm.is_available.return_value = True
        mock_llm.generate_jsonata_mapping = AsyncMock(return_value='{"publisher": "github", "resource": {"type": "pull_request", "id": pull_request.number}, "action": "created"}')
        mock_llm.transform_to_canonical = AsyncMock(return_value={
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 1374},
            "action": "created",
            "summary": "PR 1374 opened"
        })

        service = MappingService()

        # Test raw event from svc-ingest (GitHub PR opened)
        raw_event = {
            'id': 'test-event-123',
            'timestamp': '2025-06-03T15:45:02Z',
            'source': 'github',
            'signature_valid': True,
            'headers': {'x-github-event': 'pull_request'},
            'payload': {
                'action': 'opened',
                'pull_request': {
                    'number': 1374,
                    'title': 'Add new feature',
                    'state': 'open'
                }
            }
        }

        # Process the event
        await service._process_raw_event(raw_event)

        # Verify LLM was called for JSONata generation
        assert mock_llm.generate_jsonata_mapping.called
        jsonata_call = mock_llm.generate_jsonata_mapping.call_args
        assert jsonata_call[0][0] == 'github'  # source
        assert jsonata_call[0][1] == raw_event['payload']  # payload

        # Verify canonical event was sent
        assert mock_producer.send_canonical_event.called

        # Check metrics
        metrics = service.get_metrics()
        assert metrics['events_processed'] == 1
        assert metrics['events_mapped'] == 1
        assert metrics['events_failed'] == 0
        assert metrics['llm_invocations'] == 1
        assert metrics['mapping_success_rate'] == 1.0

        print("✅ LLM transformation test passed!")
        print(f"✅ LLM invocations: {metrics['llm_invocations']}")


async def test_llm_unavailable_flow():
    """Test handling when LLM service is unavailable."""
    print("\nTesting LLM unavailable flow...")

    with patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.llm_service') as mock_llm:

        mock_producer.send_canonical_event = AsyncMock()
        mock_producer.send_mapping_failure = AsyncMock()

        # Mock LLM service to be unavailable
        mock_llm.is_available.return_value = False

        service = MappingService()

        # Test raw event from unknown source
        raw_event = {
            'id': 'test-event-456',
            'timestamp': '2025-06-03T15:45:02Z',
            'source': 'unknown-source',
            'signature_valid': True,
            'headers': {},
            'payload': {
                'action': 'created',
                'item': {'id': 789}
            }
        }

        # Process the event
        await service._process_raw_event(raw_event)

        # Verify failure was sent to DLQ (mock the Kafka producer call)
        assert mock_producer.send_mapping_failure.called
        failure_call = mock_producer.send_mapping_failure.call_args
        failure_event = failure_call[0][0]
        assert failure_event['id'] == 'test-event-456'
        assert failure_event['source'] == 'unknown-source'
        assert 'No mapping available and LLM service unavailable' in failure_event['error']

        # Verify canonical event was NOT sent
        assert not mock_producer.send_canonical_event.called

        # Check metrics (should show failure due to increment in _send_mapping_failure)
        metrics = service.get_metrics()
        assert metrics['events_processed'] == 1
        assert metrics['events_mapped'] == 0
        assert metrics['events_failed'] == 1
        assert metrics['mapping_success_rate'] == 0.0

        print("✅ LLM unavailable test passed!")


async def test_llm_transformation_failure():
    """Test handling when LLM transformation fails."""
    print("\nTesting LLM transformation failure...")

    with patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.llm_service') as mock_llm:

        mock_producer.send_canonical_event = AsyncMock()
        mock_producer.send_mapping_failure = AsyncMock()

        # Mock LLM service to be available but return None (JSONata generation failed)
        mock_llm.is_available.return_value = True
        mock_llm.generate_jsonata_mapping = AsyncMock(return_value=None)

        service = MappingService()

        # Test raw event
        raw_event = {
            'id': 'test-event-789',
            'timestamp': '2025-06-03T15:45:02Z',
            'source': 'test-source',
            'signature_valid': True,
            'headers': {},
            'payload': {
                'invalid': 'data'
            }
        }

        # Process the event
        await service._process_raw_event(raw_event)

        # Verify LLM was called
        assert mock_llm.generate_jsonata_mapping.called

        # Verify failure was sent to DLQ
        assert mock_producer.send_mapping_failure.called
        failure_call = mock_producer.send_mapping_failure.call_args
        failure_event = failure_call[0][0]
        assert 'LLM failed to generate valid JSONata expression' in failure_event['error']

        # Verify canonical event was NOT sent
        assert not mock_producer.send_canonical_event.called

        print("✅ LLM transformation failure test passed!")


if __name__ == "__main__":
    import os
    os.environ['MAPPINGS_DIR'] = './mappings'

    asyncio.run(test_llm_transformation_flow())
    asyncio.run(test_llm_unavailable_flow())
    asyncio.run(test_llm_transformation_failure())
    print("\n🎉 All service tests passed!")
