"""Test the complete mapping service end-to-end."""

import asyncio
from unittest.mock import AsyncMock, patch

from langhook.map.service import MappingService


async def test_end_to_end_mapping():
    """Test the complete mapping service flow with LLM transformation."""
    print("Testing end-to-end mapping service...")
    
    # Mock the Kafka producer to avoid connection errors
    with patch('langhook.map.kafka.map_producer') as mock_producer, \
         patch('langhook.map.service.llm_service') as mock_llm:
        
        mock_producer.send_canonical_event = AsyncMock()
        mock_producer.send_mapping_failure = AsyncMock()
        
        # Mock LLM service to be available and return canonical data
        mock_llm.is_available.return_value = True
        mock_llm.transform_to_canonical = AsyncMock(return_value={
            "publisher": "github",
            "resource": {"type": "pull_request", "id": 1374},
            "action": "create",
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
                },
                'repository': {
                    'name': 'test-repo',
                    'id': 12345
                }
            }
        }
        
        # Process the event
        await service._process_raw_event(raw_event)
        
        # Verify LLM was called for transformation
        assert mock_llm.transform_to_canonical.called
        
        # Verify canonical event was sent
        assert mock_producer.send_canonical_event.called
        canonical_event = mock_producer.send_canonical_event.call_args[0][0]
        
        # Verify CloudEvent structure
        assert canonical_event['id'] == 'test-event-123'
        assert canonical_event['source'] == '/github'
        assert canonical_event['type'] == 'com.opensense.event'
        assert canonical_event['specversion'] == '1.0'
        assert canonical_event['schema_version'] == 1
        
        # Verify canonical data (new format)
        data = canonical_event['data']
        assert data['publisher'] == 'github'
        assert data['resource']['type'] == 'pull_request'
        assert data['resource']['id'] == 1374
        assert data['action'] == 'create'
        assert data['summary'] == 'PR 1374 opened'
        assert data['raw'] == raw_event['payload']
        
        # Check metrics
        metrics = service.get_metrics()
        assert metrics['events_processed'] == 1
        assert metrics['events_mapped'] == 1
        assert metrics['events_failed'] == 0
        assert metrics['llm_invocations'] == 1
        assert metrics['mapping_success_rate'] == 1.0
        
        print("✅ End-to-end test passed!")
        print(f"✅ Processed {metrics['events_processed']} events")
        print(f"✅ Mapped {metrics['events_mapped']} events successfully")
        print(f"✅ LLM invocations: {metrics['llm_invocations']}")
        print(f"✅ Success rate: {metrics['mapping_success_rate']:.1%}")


async def test_missing_mapping():
    """Test handling of events with no mapping available and LLM unavailable."""
    print("\nTesting missing mapping handling...")
    
    with patch('langhook.map.kafka.map_producer') as mock_producer, \
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
        
        # Verify failure was sent to DLQ
        assert mock_producer.send_mapping_failure.called
        failure_event = mock_producer.send_mapping_failure.call_args[0][0]
        
        assert failure_event['id'] == 'test-event-456'
        assert failure_event['source'] == 'unknown-source'
        assert 'No mapping available and LLM service unavailable' in failure_event['error']
        
        # Verify canonical event was NOT sent
        assert not mock_producer.send_canonical_event.called
        
        # Check metrics
        metrics = service.get_metrics()
        assert metrics['events_processed'] == 1
        assert metrics['events_mapped'] == 0
        assert metrics['events_failed'] == 1
        assert metrics['mapping_success_rate'] == 0.0
        
        print("✅ Missing mapping test passed!")
        print(f"✅ Failed event sent to DLQ")


if __name__ == "__main__":
    import os
    os.environ['MAPPINGS_DIR'] = './mappings'
    
    asyncio.run(test_end_to_end_mapping())
    asyncio.run(test_missing_mapping())
    print("\n🎉 All end-to-end tests passed!")