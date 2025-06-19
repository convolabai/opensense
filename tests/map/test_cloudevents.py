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


def test_field_path_evaluation_in_subject():
    """Test that field paths in resource IDs are properly evaluated in the subject."""
    wrapper = CloudEventWrapper()
    
    # GitHub push webhook payload example
    raw_payload = {
        "ref": "refs/heads/main",
        "head_commit": {
            "id": "384c3b877a118f0957e893f202f86ecdbddd3f4e",
            "message": "Fix bugs"
        }
    }
    
    # Canonical data where resource ID is a field path (simulating JSONata output)
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "commit", "id": "head_commit.id"},  # Field path
        "action": "created"
    }
    
    canonical_event = wrapper.create_canonical_event(
        event_id="test-field-path",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )
    
    cloud_event = wrapper.create_cloudevents_envelope("test-field-path", canonical_event)
    
    # The field path should be evaluated to get the actual commit ID
    assert cloud_event["subject"] == "commit/384c3b877a118f0957e893f202f86ecdbddd3f4e"
    assert cloud_event["type"] == "com.github.commit.created"


def test_field_path_edge_cases():
    """Test edge cases for field path evaluation."""
    wrapper = CloudEventWrapper()
    
    raw_payload = {
        "user": {"id": "user123"},
        "nonexistent": "value"
    }
    
    # Test cases: (resource_id, expected_subject_suffix)
    test_cases = [
        # Valid field path
        ("user.id", "user123"),
        # Non-existent field path (should return original)
        ("missing.field", "missing.field"),
        # Regular string (should not be evaluated)
        ("regular_string", "regular_string"),
        # Numeric ID (should pass through)
        (12345, "12345"),
        # URL (should not be evaluated)
        ("https://example.com", "https://example.com"),
    ]
    
    for resource_id, expected_suffix in test_cases:
        canonical_data = {
            "publisher": "test",
            "resource": {"type": "resource", "id": resource_id},
            "action": "created"
        }
        
        canonical_event = wrapper.create_canonical_event(
            event_id="test-edge",
            source="test",
            canonical_data=canonical_data,
            raw_payload=raw_payload
        )
        
        cloud_event = wrapper.create_cloudevents_envelope("test-edge", canonical_event)
        expected_subject = f"resource/{expected_suffix}"
        
        assert cloud_event["subject"] == expected_subject


if __name__ == "__main__":
    test_canonical_event_creation()
    test_event_validation()
    test_wrap_and_validate()
    test_field_path_evaluation_in_subject()
    test_field_path_edge_cases()
    print("All CloudEvent tests passed!")
