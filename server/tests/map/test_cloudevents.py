"""Test the CloudEvents wrapper functionality."""

from langhook.map.cloudevents import CloudEventWrapper


def test_canonical_event_creation():
    """Test creating a canonical event in the new format."""
    wrapper = CloudEventWrapper()

    canonical_data = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": 1374},
        "action": "created"
    }

    raw_payload = {
        "action": "opened",
        "pull_request": {"number": 1374, "title": "Test PR"}
    }

    canonical_event = wrapper.create_canonical_event(
        event_id="test-id-123",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )

    # Verify canonical event structure (not CloudEvents envelope)
    assert canonical_event["publisher"] == "github"
    assert canonical_event["resource"]["type"] == "pull_request"
    assert canonical_event["resource"]["id"] == 1374
    assert canonical_event["action"] == "created"
    assert canonical_event["payload"] == raw_payload
    assert "timestamp" in canonical_event

    # Test CloudEvents envelope creation
    cloud_event = wrapper.create_cloudevents_envelope("test-id-123", canonical_event)

    assert cloud_event["id"] == "test-id-123"
    assert cloud_event["specversion"] == "1.0"
    assert cloud_event["source"] == "/github"
    assert cloud_event["type"] == "com.github.pull_request.created"
    assert cloud_event["subject"] == "pull_request/1374"
    assert cloud_event["data"] == canonical_event


def test_event_validation():
    """Test canonical event validation."""
    wrapper = CloudEventWrapper()

    # Valid canonical event (new format)
    valid_event = {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": 1374},
        "action": "created",
        "timestamp": "2025-06-03T15:45:02Z",
        "payload": {"test": "data"}
    }

    assert wrapper.validate_canonical_event(valid_event) is True

    # Invalid event (missing required field)
    invalid_event = valid_event.copy()
    del invalid_event["publisher"]

    assert wrapper.validate_canonical_event(invalid_event) is False

    # Invalid action (not CRUD)
    invalid_action_event = valid_event.copy()
    invalid_action_event["action"] = "opened"  # Should be "created"

    assert wrapper.validate_canonical_event(invalid_action_event) is False


def test_wrap_and_validate():
    """Test the combined wrap and validate functionality."""
    wrapper = CloudEventWrapper()

    canonical_data = {
        "publisher": "github",
        "resource": {"type": "issue", "id": 456},
        "action": "deleted"
    }

    raw_payload = {"action": "closed", "issue": {"number": 456}}

    cloud_event = wrapper.wrap_and_validate(
        event_id="test-456",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )

    # Should return a CloudEvents envelope
    assert cloud_event is not None
    assert cloud_event["id"] == "test-456"
    assert cloud_event["type"] == "com.github.issue.deleted"
    assert cloud_event["subject"] == "issue/456"
    assert cloud_event["data"]["action"] == "deleted"
    assert cloud_event["data"]["resource"]["id"] == 456


if __name__ == "__main__":
    test_canonical_event_creation()
    test_event_validation()
    test_wrap_and_validate()
    print("All CloudEvent tests passed!")
