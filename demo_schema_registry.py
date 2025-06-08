#!/usr/bin/env python3
"""
Simple demonstration script showing the schema registry functionality.
This script demonstrates how canonical events automatically populate the schema registry.
"""

import asyncio
import json
from langhook.subscriptions.schema_registry import schema_registry_service
from langhook.map.service import MappingService
from unittest.mock import patch, AsyncMock


async def demo_schema_registry():
    """Demonstrate the schema registry functionality."""
    print("🚀 Schema Registry Demo")
    print("=" * 50)
    
    # Mock all dependencies so we can test in isolation
    with patch('langhook.map.service.cloud_event_wrapper') as mock_wrapper, \
         patch('langhook.map.service.map_producer') as mock_producer, \
         patch('langhook.map.service.mapping_engine') as mock_engine, \
         patch('langhook.map.service.metrics'), \
         patch('langhook.subscriptions.schema_registry.db_service') as mock_db:
        
        # Mock database session
        mock_session = AsyncMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock mapping service dependencies
        mock_producer.send_canonical_event = AsyncMock()
        
        service = MappingService()
        
        # Test different canonical event types
        test_events = [
            {
                "source": "github",
                "canonical_data": {
                    "publisher": "github",
                    "resource": {"type": "pull_request", "id": 1374},
                    "action": "create"
                }
            },
            {
                "source": "github", 
                "canonical_data": {
                    "publisher": "github",
                    "resource": {"type": "pull_request", "id": 1375},
                    "action": "update"
                }
            },
            {
                "source": "stripe",
                "canonical_data": {
                    "publisher": "stripe",
                    "resource": {"type": "refund", "id": "re_123"},
                    "action": "create"
                }
            },
            {
                "source": "jira",
                "canonical_data": {
                    "publisher": "jira",
                    "resource": {"type": "issue", "id": "PROJ-123"},
                    "action": "update"
                }
            }
        ]
        
        print("📋 Processing canonical events...")
        
        for i, event_data in enumerate(test_events, 1):
            canonical_data = event_data["canonical_data"]
            
            # Mock the mapping engine to return our test data
            mock_engine.apply_mapping.return_value = canonical_data
            
            # Mock cloud event wrapper
            canonical_event = {"data": canonical_data}
            mock_wrapper.wrap_and_validate.return_value = canonical_event
            
            # Create raw event
            raw_event = {
                "id": f"test-{i}",
                "source": event_data["source"],
                "payload": {"test": "data"}
            }
            
            print(f"  {i}. Processing {canonical_data['publisher']}.{canonical_data['resource']['type']}.{canonical_data['action']}")
            
            # Process the event - this should trigger schema registration
            await service._process_raw_event(raw_event)
        
        print("\n✅ All events processed!")
        
        # Show what calls were made to schema registry
        print(f"\n📊 Schema registry calls made: {mock_session.execute.call_count}")
        for call in mock_session.execute.call_args_list:
            if call[0]:  # Check if there are positional args
                query_params = call[1] if len(call) > 1 else {}
                print(f"  - {query_params}")
        
        print("\n🎯 Expected schema registry structure:")
        expected_schema = {
            "publishers": ["github", "jira", "stripe"],
            "resource_types": {
                "github": ["pull_request"],
                "jira": ["issue"],
                "stripe": ["refund"]
            },
            "actions": ["create", "update"]
        }
        print(json.dumps(expected_schema, indent=2))
        
        print("\n✨ Demo completed! Schema registry would now contain these entries.")


if __name__ == "__main__":
    asyncio.run(demo_schema_registry())