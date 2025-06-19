#!/usr/bin/env python3
"""Test to reproduce the canonical event subject transformation bug."""

from langhook.map.cloudevents import CloudEventWrapper

def test_subject_field_evaluation():
    """Test that field paths in resource IDs are properly evaluated."""
    wrapper = CloudEventWrapper()
    
    # GitHub push webhook payload from the issue
    raw_payload = {
        "ref": "refs/heads/release/2.6.2",
        "before": "0000000000000000000000000000000000000000",
        "after": "384c3b877a118f0957e893f202f86ecdbddd3f4e",
        "head_commit": {
            "id": "384c3b877a118f0957e893f202f86ecdbddd3f4e",
            "tree_id": "375b20ddf5f785a8da017791a995e6585f54c5bf",
            "message": "Fix bugs on Microphone\n- cannot detect sound properly sometime",
            "timestamp": "2025-06-19T00:40:27+07:00",
            "author": {
                "name": "Yati Dumrongsukit",
                "email": "yati@amityrobotics.com",
                "username": "yati-amity"
            }
        },
        "repository": {
            "id": 732007732,
            "name": "robotics-android",
            "full_name": "AmityCo/robotics-android"
        }
    }
    
    # This is what the JSONata mapping should produce - with the actual commit ID
    canonical_data = {
        "publisher": "github",
        "resource": {"type": "commit", "id": "384c3b877a118f0957e893f202f86ecdbddd3f4e"},
        "action": "created"
    }
    
    canonical_event = wrapper.create_canonical_event(
        event_id="test-push-123",
        source="github",
        canonical_data=canonical_data,
        raw_payload=raw_payload
    )
    
    cloud_event = wrapper.create_cloudevents_envelope("test-push-123", canonical_event)
    
    # Should show the actual commit ID in the subject, not "head_commit.id"
    print(f"Expected subject: commit/384c3b877a118f0957e893f202f86ecdbddd3f4e")
    print(f"Actual subject: {cloud_event['subject']}")
    
    assert cloud_event["subject"] == "commit/384c3b877a118f0957e893f202f86ecdbddd3f4e"

def test_subject_bug_reproduction():
    """Reproduce the bug where resource ID is literal string instead of field value."""
    wrapper = CloudEventWrapper()
    
    # GitHub push webhook payload from the issue
    raw_payload = {
        "ref": "refs/heads/release/2.6.2",
        "before": "0000000000000000000000000000000000000000",
        "after": "384c3b877a118f0957e893f202f86ecdbddd3f4e",
        "head_commit": {
            "id": "384c3b877a118f0957e893f202f86ecdbddd3f4e",
            "tree_id": "375b20ddf5f785a8da017791a995e6585f54c5bf",
            "message": "Fix bugs on Microphone\n- cannot detect sound properly sometime",
            "timestamp": "2025-06-19T00:40:27+07:00",
            "author": {
                "name": "Yati Dumrongsukit",
                "email": "yati@amityrobotics.com",
                "username": "yati-amity"
            }
        },
        "repository": {
            "id": 732007732,
            "name": "robotics-android",
            "full_name": "AmityCo/robotics-android"
        }
    }
    
    # This simulates the bug - the resource ID is the literal string instead of the field value
    # This is what would happen if the JSONata mapping had a bug
    canonical_data_with_bug = {
        "publisher": "github",
        "resource": {"type": "commit", "id": "head_commit.id"},  # BUG: literal string
        "action": "created"
    }
    
    canonical_event = wrapper.create_canonical_event(
        event_id="test-push-bug-123",
        source="github",
        canonical_data=canonical_data_with_bug,
        raw_payload=raw_payload
    )
    
    cloud_event = wrapper.create_cloudevents_envelope("test-push-bug-123", canonical_event)
    
    # This shows the bug - the subject contains "head_commit.id" instead of the actual commit ID
    print(f"Buggy subject: {cloud_event['subject']}")
    
    # This demonstrates the bug
    assert cloud_event["subject"] == "commit/head_commit.id"  # This is the bug


if __name__ == "__main__":
    print("Testing correct behavior:")
    test_subject_field_evaluation()
    print("✅ Correct behavior works\n")
    
    print("Testing bug reproduction:")
    test_subject_bug_reproduction()
    print("🐛 Bug reproduced\n")
    
    print("The issue is that somewhere in the JSONata transformation,")
    print("field paths like 'head_commit.id' are not being evaluated properly.")