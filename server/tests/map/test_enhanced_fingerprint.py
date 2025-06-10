"""Test enhanced fingerprinting functionality."""

from langhook.map.fingerprint import generate_fingerprint, generate_enhanced_fingerprint


def test_enhanced_fingerprint_without_event_field():
    """Test that enhanced fingerprint without event field matches basic fingerprint."""
    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        }
    }
    
    basic_fingerprint = generate_fingerprint(payload)
    enhanced_fingerprint = generate_enhanced_fingerprint(payload, None)
    
    # Should be identical when no event field expression is provided
    assert basic_fingerprint == enhanced_fingerprint


def test_enhanced_fingerprint_with_event_field():
    """Test that enhanced fingerprint includes event field value."""
    payload1 = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        }
    }
    
    payload2 = {
        "action": "closed",  # Different action
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        }
    }
    
    # Basic fingerprints should be the same (same structure)
    basic_fp1 = generate_fingerprint(payload1)
    basic_fp2 = generate_fingerprint(payload2)
    assert basic_fp1 == basic_fp2
    
    # Enhanced fingerprints should be different (different action values)
    enhanced_fp1 = generate_enhanced_fingerprint(payload1, "action")
    enhanced_fp2 = generate_enhanced_fingerprint(payload2, "action")
    assert enhanced_fp1 != enhanced_fp2
    
    # Enhanced fingerprints should be different from basic fingerprints
    assert enhanced_fp1 != basic_fp1
    assert enhanced_fp2 != basic_fp2


def test_enhanced_fingerprint_same_action():
    """Test that enhanced fingerprint is same for payloads with same structure and action."""
    payload1 = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        }
    }
    
    payload2 = {
        "action": "opened",  # Same action
        "number": 999,       # Different values
        "pull_request": {
            "id": 987654321,
            "title": "Different title",
            "user": {"login": "bob"},
            "merged": True
        }
    }
    
    enhanced_fp1 = generate_enhanced_fingerprint(payload1, "action")
    enhanced_fp2 = generate_enhanced_fingerprint(payload2, "action")
    
    # Should be the same because structure and action value are identical
    assert enhanced_fp1 == enhanced_fp2


def test_enhanced_fingerprint_nested_event_field():
    """Test enhanced fingerprint with nested event field expression."""
    payload1 = {
        "event": {"type": "pull_request", "action": "opened"},
        "data": {"id": 123}
    }
    
    payload2 = {
        "event": {"type": "pull_request", "action": "closed"},
        "data": {"id": 456}
    }
    
    enhanced_fp1 = generate_enhanced_fingerprint(payload1, "event.action")
    enhanced_fp2 = generate_enhanced_fingerprint(payload2, "event.action")
    
    # Should be different because nested action values are different
    assert enhanced_fp1 != enhanced_fp2


def test_enhanced_fingerprint_invalid_event_field():
    """Test enhanced fingerprint with invalid event field expression falls back gracefully."""
    payload = {
        "action": "opened",
        "number": 42
    }
    
    basic_fingerprint = generate_fingerprint(payload)
    
    # Test with non-existent field
    enhanced_fp1 = generate_enhanced_fingerprint(payload, "nonexistent.field")
    
    # Should fall back to basic fingerprint when event field doesn't exist
    assert enhanced_fp1 == basic_fingerprint
    
    # Test with invalid JSONata expression
    enhanced_fp2 = generate_enhanced_fingerprint(payload, "invalid expression!")
    
    # Should fall back to basic fingerprint when JSONata fails
    assert enhanced_fp2 == basic_fingerprint


if __name__ == "__main__":
    test_enhanced_fingerprint_without_event_field()
    test_enhanced_fingerprint_with_event_field()
    test_enhanced_fingerprint_same_action()
    test_enhanced_fingerprint_nested_event_field()
    test_enhanced_fingerprint_invalid_event_field()
    print("All enhanced fingerprint tests passed!")