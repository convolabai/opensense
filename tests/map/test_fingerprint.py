"""Test fingerprint functionality."""

from langhook.map.fingerprint import extract_type_skeleton, create_canonical_string, generate_fingerprint


def test_extract_type_skeleton_simple():
    """Test extracting type skeleton from a simple payload."""
    payload = {
        "action": "opened",
        "number": 42,
        "merged": False
    }
    
    expected = {
        "action": "string",
        "number": "number", 
        "merged": "boolean"
    }
    
    result = extract_type_skeleton(payload)
    assert result == expected


def test_extract_type_skeleton_nested():
    """Test extracting type skeleton from nested payload."""
    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        },
        "repository": {
            "id": 5580001,
            "name": "langhook",
            "owner": {"login": "langhook-org"}
        }
    }
    
    expected = {
        "action": "string",
        "number": "number",
        "pull_request": {
            "id": "number",
            "title": "string",
            "user": {"login": "string"},
            "merged": "boolean"
        },
        "repository": {
            "id": "number",
            "name": "string",
            "owner": {"login": "string"}
        }
    }
    
    result = extract_type_skeleton(payload)
    assert result == expected


def test_create_canonical_string():
    """Test creating canonical string with sorted keys."""
    skeleton = {
        "action": "string",
        "number": "number",
        "pull_request": {
            "id": "number",
            "merged": "boolean",
            "title": "string",
            "user": {"login": "string"}
        },
        "repository": {
            "id": "number",
            "name": "string",
            "owner": {"login": "string"}
        }
    }
    
    expected = '{"action":"string","number":"number","pull_request":{"id":"number","merged":"boolean","title":"string","user":{"login":"string"}},"repository":{"id":"number","name":"string","owner":{"login":"string"}}}'
    
    result = create_canonical_string(skeleton)
    assert result == expected


def test_generate_fingerprint_github_example():
    """Test fingerprint generation with the GitHub example from the issue."""
    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1480863564,
            "title": "Fix typo in README",
            "user": {"login": "alice"},
            "merged": False
        },
        "repository": {
            "id": 5580001,
            "name": "langhook",
            "owner": {"login": "langhook-org"}
        }
    }
    
    fingerprint = generate_fingerprint(payload)
    
    # Should be a 64-character hex string
    assert len(fingerprint) == 64
    assert all(c in '0123456789abcdef' for c in fingerprint)
    
    # Same payload should produce same fingerprint
    fingerprint2 = generate_fingerprint(payload)
    assert fingerprint == fingerprint2


def test_generate_fingerprint_different_values_same_structure():
    """Test that different values with same structure produce same fingerprint."""
    payload1 = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 123,
            "title": "First PR",
            "user": {"login": "alice"},
            "merged": False
        }
    }
    
    payload2 = {
        "action": "closed", 
        "number": 999,
        "pull_request": {
            "id": 456,
            "title": "Different PR",
            "user": {"login": "bob"},
            "merged": True
        }
    }
    
    fingerprint1 = generate_fingerprint(payload1)
    fingerprint2 = generate_fingerprint(payload2)
    
    # Should be the same because structure is identical
    assert fingerprint1 == fingerprint2


def test_github_issue_example_basic_fingerprints():
    """Test the GitHub issue example - same structure should produce same basic fingerprint."""
    # GitHub PR opened
    payload_opened = {
        "action": "opened",
        "number": 1374,
        "pull_request": {
            "id": 1374,
            "number": 1374,
            "title": "Add new feature",
            "state": "open",
            "user": {
                "login": "alice",
                "id": 12345
            },
            "body": "This PR adds a new feature to the application.",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123"
            },
            "base": {
                "ref": "main",
                "sha": "def456"
            }
        },
        "repository": {
            "id": 12345,
            "name": "test-repo",
            "full_name": "alice/test-repo",
            "private": False
        },
        "sender": {
            "login": "alice",
            "id": 12345
        }
    }
    
    # GitHub PR approved (same structure, different action)
    payload_approved = {
        "action": "approved",  # Different action
        "number": 1374,
        "pull_request": {
            "id": 1374,
            "number": 1374,
            "title": "Add new feature",
            "state": "approved",  # Different state
            "user": {
                "login": "alice",
                "id": 12345
            },
            "body": "This PR adds a new feature to the application.",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123"
            },
            "base": {
                "ref": "main",
                "sha": "def456"
            }
        },
        "repository": {
            "id": 12345,
            "name": "test-repo",
            "full_name": "alice/test-repo",
            "private": False
        },
        "sender": {
            "login": "alice",
            "id": 12345
        }
    }
    
    # Basic fingerprints should be identical (same structure)
    basic_fp_opened = generate_fingerprint(payload_opened)
    basic_fp_approved = generate_fingerprint(payload_approved)
    assert basic_fp_opened == basic_fp_approved


def test_github_issue_example_enhanced_fingerprints():
    """Test the GitHub issue example - enhanced fingerprints should be different for different actions."""
    from langhook.map.fingerprint import generate_enhanced_fingerprint
    
    # GitHub PR opened
    payload_opened = {
        "action": "opened",
        "number": 1374,
        "pull_request": {
            "id": 1374,
            "number": 1374,
            "title": "Add new feature",
            "state": "open",
            "user": {
                "login": "alice",
                "id": 12345
            },
            "body": "This PR adds a new feature to the application.",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123"
            },
            "base": {
                "ref": "main",
                "sha": "def456"
            }
        },
        "repository": {
            "id": 12345,
            "name": "test-repo",
            "full_name": "alice/test-repo",
            "private": False
        },
        "sender": {
            "login": "alice",
            "id": 12345
        }
    }
    
    # GitHub PR approved (same structure, different action)
    payload_approved = {
        "action": "approved",  # Different action
        "number": 1374,
        "pull_request": {
            "id": 1374,
            "number": 1374,
            "title": "Add new feature",
            "state": "approved",  # Different state
            "user": {
                "login": "alice",
                "id": 12345
            },
            "body": "This PR adds a new feature to the application.",
            "head": {
                "ref": "feature-branch",
                "sha": "abc123"
            },
            "base": {
                "ref": "main",
                "sha": "def456"
            }
        },
        "repository": {
            "id": 12345,
            "name": "test-repo",
            "full_name": "alice/test-repo",
            "private": False
        },
        "sender": {
            "login": "alice",
            "id": 12345
        }
    }
    
    # Enhanced fingerprints should be different (different action values)
    enhanced_fp_opened = generate_enhanced_fingerprint(payload_opened, "action")
    enhanced_fp_approved = generate_enhanced_fingerprint(payload_approved, "action")
    
    assert enhanced_fp_opened != enhanced_fp_approved
    
    # They should also be different from the basic fingerprints
    basic_fp = generate_fingerprint(payload_opened)
    assert enhanced_fp_opened != basic_fp
    assert enhanced_fp_approved != basic_fp


def test_generate_fingerprint_different_structure():
    """Test that different structure produces different fingerprint."""
    payload1 = {
        "action": "opened",
        "number": 42
    }
    
    payload2 = {
        "action": "opened",
        "number": 42,
        "extra_field": "value"
    }
    
    fingerprint1 = generate_fingerprint(payload1)
    fingerprint2 = generate_fingerprint(payload2)
    
    # Should be different because structure is different
    assert fingerprint1 != fingerprint2


def test_extract_type_skeleton_with_lists():
    """Test extracting type skeleton with list fields."""
    payload = {
        "items": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}],
        "tags": ["tag1", "tag2"],
        "empty_list": []
    }
    
    expected = {
        "items": [{"id": "number", "name": "string"}],
        "tags": ["string"],
        "empty_list": []
    }
    
    result = extract_type_skeleton(payload)
    assert result == expected


if __name__ == "__main__":
    test_extract_type_skeleton_simple()
    test_extract_type_skeleton_nested()
    test_create_canonical_string()
    test_generate_fingerprint_github_example()
    test_generate_fingerprint_different_values_same_structure()
    test_github_issue_example_basic_fingerprints()
    test_github_issue_example_enhanced_fingerprints()
    test_generate_fingerprint_different_structure()
    test_extract_type_skeleton_with_lists()
    print("All fingerprint tests passed!")