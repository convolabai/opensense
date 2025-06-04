"""Test the CloudEvents wrapper functionality."""

import json
from opensense.map.cloudevents import CloudEventWrapper


def test_canonical_event_creation():
    """Test creating a canonical CloudEvent."""
    wrapper = CloudEventWrapper()
    
    canonical_data = {
        "publisher": "github",
        "resource": "pull_request",
        "action": "opened",
        "key": "number",
        "value": 1374
    }
    
    raw_payload = {
        "action": "opened",
        "pull_request": {"number": 1374, "title": "Test PR"}
    }
    
    event = wrapper.create_canonical_event(
        event_id="test-id-123",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )
    
    # Verify CloudEvent structure
    assert event["id"] == "test-id-123"
    assert event["specversion"] == "1.0"
    assert event["source"] == "/github"
    assert event["type"] == "com.opensense.event"
    assert event["schema_version"] == 1
    assert "time" in event
    
    # Verify data section
    data = event["data"]
    assert data["publisher"] == "github"
    assert data["resource"] == "pull_request"
    assert data["action"] == "opened"
    assert data["key"] == "number"
    assert data["value"] == 1374
    assert data["raw"] == raw_payload


def test_event_validation():
    """Test CloudEvent validation."""
    wrapper = CloudEventWrapper()
    
    # Valid event
    valid_event = {
        "id": "test-123",
        "specversion": "1.0",
        "source": "/github",
        "type": "com.opensense.event",
        "time": "2025-06-03T15:45:02Z",
        "schema_version": 1,
        "data": {
            "publisher": "github",
            "resource": "pull_request",
            "action": "opened",
            "key": "number",
            "value": 1374,
            "raw": {"test": "data"}
        }
    }
    
    assert wrapper.validate_canonical_event(valid_event) is True
    
    # Invalid event (missing required field)
    invalid_event = valid_event.copy()
    del invalid_event["data"]["publisher"]
    
    assert wrapper.validate_canonical_event(invalid_event) is False


def test_wrap_and_validate():
    """Test the combined wrap and validate functionality."""
    wrapper = CloudEventWrapper()
    
    canonical_data = {
        "publisher": "github",
        "resource": "issue",
        "action": "closed",
        "key": "number",
        "value": 456
    }
    
    raw_payload = {"action": "closed", "issue": {"number": 456}}
    
    event = wrapper.wrap_and_validate(
        event_id="test-456",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )
    
    # Should return a valid event
    assert event is not None
    assert event["id"] == "test-456"
    assert event["data"]["action"] == "closed"
    assert event["data"]["value"] == 456


if __name__ == "__main__":
    test_canonical_event_creation()
    test_event_validation()
    test_wrap_and_validate()
    print("All CloudEvent tests passed!")