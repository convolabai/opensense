"""End-to-end tests for OpenAI LLM transformations.

This module tests the complete LLM transformation pipeline with real OpenAI API calls,
validating that webhook payloads are correctly transformed to canonical format.
"""

from typing import Any

import pytest
import structlog

from langhook.map.cloudevents import CloudEventWrapper
from langhook.map.llm import LLMSuggestionService

logger = structlog.get_logger(__name__)


@pytest.fixture
def openai_llm_service():
    """Create real LLM service that calls OpenAI API."""
    service = LLMSuggestionService()
    if not service.is_available():
        pytest.skip("OpenAI API key not available - set OPENAI_API_KEY environment variable")
    return service


@pytest.fixture
def cloud_wrapper():
    """Create CloudEvent wrapper for validation."""
    return CloudEventWrapper()


class TestWebhookTransformations:
    """Test LLM transformations for various webhook payloads."""

    # Test data for 14 webhook scenarios
    WEBHOOK_TEST_CASES = [
        {
            "name": "GitHub push",
            "source": "github",
            "payload": {
                "ref": "refs/heads/main",
                "before": "e9e67c9d2be3724fce7d5d44ef4a0677c10bb4d6",
                "after": "4c7ca98fceb21f61301d997a5afb662b0f38e553",
                "repository": {"id": 987654321, "full_name": "octo-corp/widgets"},
                "pusher": {"name": "alice"},
                "head_commit": {
                    "id": "4c7ca98fceb21f61301d997a5afb662b0f38e553",
                    "message": "Fix race condition in task scheduler",
                    "timestamp": "2025-06-08T03:14:27Z"
                }
            },
            "expected": {
                "publisher": "github",
                "resource": {"type": "repository", "id": 987654321},
                "action": "update"
            }
        },
        {
            "name": "Stripe payment_intent.succeeded",
            "source": "stripe",
            "payload": {
                "id": "evt_X",
                "type": "payment_intent.succeeded",
                "created": 1759961327,
                "data": {
                    "object": {
                        "id": "pi_3PyQwz2eZvKYlo2C0Yk1pTvb",
                        "amount": 7500,
                        "currency": "usd",
                        "status": "succeeded",
                        "metadata": {"order_id": "ORD-4982"}
                    }
                }
            },
            "expected": {
                "publisher": "stripe",
                "resource": {"type": "payment_intent", "id": "pi_3PyQwz2eZvKYlo2C0Yk1pTvb"},
                "action": "update"
            }
        },
        {
            "name": "Slack message",
            "source": "slack",
            "payload": {
                "event": {
                    "type": "message",
                    "channel": "C024BE91L",
                    "user": "U2147483697",
                    "text": "Daily stand-up in 5 minutes ⏰",
                    "ts": "1728447902.000200"
                },
                "event_time": 1728447902
            },
            "expected": {
                "publisher": "slack",
                "resource": {"type": "message", "id": "1728447902.000200"},
                "action": "create"
            }
        },
        {
            "name": "Twilio inbound SMS",
            "source": "twilio",
            "payload": {
                "MessageSid": "SM9a42e3e5e9e0670f28c8b773793b5b83",
                "From": "+14155551234",
                "To": "+15558675309",
                "Body": "Hi, is curbside pickup available today?",
                "DateCreated": "2025-06-08T03:24:00Z"
            },
            "expected": {
                "publisher": "twilio",
                "resource": {"type": "sms", "id": "SM9a42e3e5e9e0670f28c8b773793b5b83"},
                "action": "create"
            }
        },
        {
            "name": "Shopify order create",
            "source": "shopify",
            "payload": {
                "id": 5902160010102,
                "email": "jordan@example.com",
                "total_price": "129.99",
                "currency": "USD",
                "created_at": "2025-06-08T03:20:55Z"
            },
            "expected": {
                "publisher": "shopify",
                "resource": {"type": "order", "id": 5902160010102},
                "action": "create"
            }
        },
        {
            "name": "AWS SNS notification",
            "source": "aws_sns",
            "payload": {
                "Type": "Notification",
                "MessageId": "6b4b6d77-3cbe-48e6-8da4-2b3e4f9dd3b5",
                "TopicArn": "arn:aws:sns:us-east-1:123456789012:system-alerts",
                "Subject": "HighCPU",
                "Message": "CPU utilization is 93.7%",
                "Timestamp": "2025-06-08T03:24:13Z"
            },
            "expected": {
                "publisher": "aws_sns",
                "resource": {"type": "notification", "id": "6b4b6d77-3cbe-48e6-8da4-2b3e4f9dd3b5"},
                "action": "create"
            }
        },
        {
            "name": "GitLab push",
            "source": "gitlab",
            "payload": {
                "object_kind": "push",
                "project": {"id": 15, "name": "diaspora", "path_with_namespace": "mike/diaspora"},
                "user_name": "jsmith",
                "commits": [
                    {"id": "da156088ca0ab6ad89568e2b6ebb6cc3e4e6fb7e"},
                    {"id": "da156088ca0ab6ad89568e2b6ebb6cc3e4e6fb7f"},
                    {"id": "da156088ca0ab6ad89568e2b6ebb6cc3e4e6fb7g"},
                    {"id": "da156088ca0ab6ad89568e2b6ebb6cc3e4e6fb7h"}
                ],
                "total_commits_count": 4
            },
            "expected": {
                "publisher": "gitlab",
                "resource": {"type": "repository", "id": 15},
                "action": "update"
            }
        },
        {
            "name": "Bitbucket repo push",
            "source": "bitbucket",
            "payload": {
                "repository": {"full_name": "team_name/dummy-web"},
                "push": {
                    "changes": [{
                        "new": {
                            "name": "feature/login-flow",
                            "target": {"hash": "bc72f4f3"}
                        }
                    }]
                },
                "actor": {"display_name": "Tony Stark"}
            },
            "expected": {
                "publisher": "bitbucket",
                "resource": {"type": "repository", "id": "team_name/dummy-web"},
                "action": "update"
            }
        },
        {
            "name": "Jira issue created",
            "source": "jira",
            "payload": {
                "webhookEvent": "jira:issue_created",
                "issue": {
                    "key": "TP-42",
                    "fields": {
                        "summary": "Search API returns 500",
                        "priority": {"name": "High"},
                        "issuetype": {"name": "Bug"},
                        "creator": {"displayName": "Paul Rothrock"}
                    }
                },
                "timestamp": 1728430959131
            },
            "expected": {
                "publisher": "jira",
                "resource": {"type": "issue", "id": "TP-42"},
                "action": "create"
            }
        },
        {
            "name": "Trello create card",
            "source": "trello",
            "payload": {
                "action": {
                    "type": "createCard",
                    "data": {
                        "card": {
                            "id": "51a79e72dbb7e23c7c003778",
                            "name": "Webhooks MVP"
                        },
                        "board": {"name": "Product Roadmap"}
                    }
                }
            },
            "expected": {
                "publisher": "trello",
                "resource": {"type": "card", "id": "51a79e72dbb7e23c7c003778"},
                "action": "create"
            }
        },
        {
            "name": "Notion page content updated",
            "source": "notion",
            "payload": {
                "object": "event",
                "type": "page.content_updated",
                "page": {
                    "id": "9c1659d2-84c0-4416-9fcb-1fb6d173e3b4",
                    "parent": {"workspace_id": "a3c44d51-3c01-4067-8f6b-9b4a8ef8b5e2"}
                },
                "created_time": "2025-06-08T03:50:27.112Z"
            },
            "expected": {
                "publisher": "notion",
                "resource": {"type": "page", "id": "9c1659d2-84c0-4416-9fcb-1fb6d173e3b4"},
                "action": "update"
            }
        },
        {
            "name": "Zoom meeting created",
            "source": "zoom",
            "payload": {
                "event": "meeting.created",
                "payload": {
                    "object": {
                        "id": 9988776655,
                        "topic": "Sprint Demo – Week 23",
                        "duration": 60,
                        "host_id": "uBcD123XYZ",
                        "start_time": "2025-06-09T02:00:00Z"
                    }
                }
            },
            "expected": {
                "publisher": "zoom",
                "resource": {"type": "meeting", "id": 9988776655},
                "action": "create"
            }
        },
        {
            "name": "PayPal payment capture completed",
            "source": "paypal",
            "payload": {
                "event_type": "PAYMENT.CAPTURE.COMPLETED",
                "resource": {
                    "id": "5O190127TN364715T",
                    "amount": {"currency_code": "USD", "value": "80.00"},
                    "invoice_id": "INV-5021",
                    "status": "COMPLETED"
                },
                "create_time": "2025-06-08T03:48:12Z"
            },
            "expected": {
                "publisher": "paypal",
                "resource": {"type": "payment", "id": "5O190127TN364715T"},
                "action": "update"
            }
        },
        {
            "name": "Calendly invitee created",
            "source": "calendly",
            "payload": {
                "event": "invitee.created",
                "payload": {
                    "name": "Jordan Lee",
                    "event": {
                        "uuid": "CAEB32DE-3B88-455B-8CBC-1234567890AB",
                        "name": "Discovery Call"
                    },
                    "scheduled_event": {
                        "start_time": "2025-06-12T09:00:00Z",
                        "location": {"type": "zoom"}
                    }
                }
            },
            "expected": {
                "publisher": "calendly",
                "resource": {"type": "event", "id": "CAEB32DE-3B88-455B-8CBC-1234567890AB"},
                "action": "create"
            }
        }
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", WEBHOOK_TEST_CASES)
    async def test_webhook_transformation_strict(
        self,
        test_case: dict[str, Any],
        openai_llm_service: LLMSuggestionService,
        cloud_wrapper: CloudEventWrapper
    ):
        """Test LLM transformation with strict validation against expected values."""
        logger.info("Testing webhook transformation (strict)", name=test_case["name"], source=test_case["source"])

        # Call the LLM service to transform payload
        result = await openai_llm_service.transform_to_canonical(
            test_case["source"],
            test_case["payload"]
        )

        # Assert transformation succeeded
        assert result is not None, f"LLM transformation failed for {test_case['name']}"

        # Validate core canonical fields
        assert "publisher" in result
        assert "resource" in result
        assert "action" in result

        # Validate publisher matches expected
        assert result["publisher"] == test_case["expected"]["publisher"], \
            f"Publisher mismatch for {test_case['name']}: got {result['publisher']}, expected {test_case['expected']['publisher']}"

        # Validate resource structure
        assert isinstance(result["resource"], dict)
        assert "type" in result["resource"]
        assert "id" in result["resource"]

        # Validate resource type matches expected
        assert result["resource"]["type"] == test_case["expected"]["resource"]["type"], \
            f"Resource type mismatch for {test_case['name']}: got {result['resource']['type']}, expected {test_case['expected']['resource']['type']}"

        # Validate resource ID matches expected (convert to same type for comparison)
        expected_id = test_case["expected"]["resource"]["id"]
        actual_id = result["resource"]["id"]

        # Handle ID type conversion for comparison
        if isinstance(expected_id, int) and isinstance(actual_id, str):
            actual_id = int(actual_id) if actual_id.isdigit() else actual_id
        elif isinstance(expected_id, str) and isinstance(actual_id, int):
            expected_id = str(expected_id)

        assert actual_id == expected_id, \
            f"Resource ID mismatch for {test_case['name']}: got {actual_id}, expected {expected_id}"

        # Validate action matches expected
        assert result["action"] == test_case["expected"]["action"], \
            f"Action mismatch for {test_case['name']}: got {result['action']}, expected {test_case['expected']['action']}"

        # Test creation of full canonical event with CloudEvent wrapper
        canonical_event = cloud_wrapper.create_canonical_event(
            event_id=f"test-{test_case['name'].lower().replace(' ', '-')}",
            source=test_case["source"],
            canonical_data=result,
            raw_payload=test_case["payload"]
        )

        # Validate full canonical event structure
        assert canonical_event["publisher"] == result["publisher"]
        assert canonical_event["resource"] == result["resource"]
        assert canonical_event["action"] == result["action"]
        assert "timestamp" in canonical_event
        assert canonical_event["payload"] == test_case["payload"]

        # Validate against JSON schema
        assert cloud_wrapper.validate_canonical_event(canonical_event), \
            f"Canonical event validation failed for {test_case['name']}"

        logger.info(
            "Webhook transformation successful",
            name=test_case["name"],
            publisher=result["publisher"],
            resource_type=result["resource"]["type"],
            resource_id=result["resource"]["id"],
            action=result["action"]
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", WEBHOOK_TEST_CASES)
    async def test_webhook_transformation_flexible(
        self,
        test_case: dict[str, Any],
        openai_llm_service: LLMSuggestionService,
        cloud_wrapper: CloudEventWrapper
    ):
        """Test LLM transformation with flexible validation (structure validation only)."""
        logger.info("Testing webhook transformation (flexible)", name=test_case["name"], source=test_case["source"])

        # Call the LLM service to transform payload
        result = await openai_llm_service.transform_to_canonical(
            test_case["source"],
            test_case["payload"]
        )

        # Assert transformation succeeded
        assert result is not None, f"LLM transformation failed for {test_case['name']}"

        # Validate core canonical fields exist
        assert "publisher" in result
        assert "resource" in result
        assert "action" in result

        # Validate publisher is reasonable (should be lowercase, match source pattern)
        assert isinstance(result["publisher"], str)
        assert result["publisher"].islower()
        assert "_" not in result["publisher"] or result["publisher"].replace("_", "").isalnum()

        # Validate resource structure
        assert isinstance(result["resource"], dict)
        assert "type" in result["resource"]
        assert "id" in result["resource"]

        # Validate resource type is reasonable (should be singular noun)
        assert isinstance(result["resource"]["type"], str)
        assert len(result["resource"]["type"]) > 0

        # Validate resource ID exists and is reasonable
        resource_id = result["resource"]["id"]
        assert resource_id is not None
        assert isinstance(resource_id, str | int)
        if isinstance(resource_id, str):
            assert len(resource_id) > 0

        # Validate action is a valid CRUD verb
        assert result["action"] in ["create", "read", "update", "delete"]

        # Test creation of full canonical event with CloudEvent wrapper
        canonical_event = cloud_wrapper.create_canonical_event(
            event_id=f"test-flexible-{test_case['name'].lower().replace(' ', '-')}",
            source=test_case["source"],
            canonical_data=result,
            raw_payload=test_case["payload"]
        )

        # Validate full canonical event structure
        assert canonical_event["publisher"] == result["publisher"]
        assert canonical_event["resource"] == result["resource"]
        assert canonical_event["action"] == result["action"]
        assert "timestamp" in canonical_event
        assert canonical_event["payload"] == test_case["payload"]

        # Validate against JSON schema
        assert cloud_wrapper.validate_canonical_event(canonical_event), \
            f"Canonical event validation failed for {test_case['name']}"

        logger.info(
            "Webhook transformation successful (flexible)",
            name=test_case["name"],
            publisher=result["publisher"],
            resource_type=result["resource"]["type"],
            resource_id=result["resource"]["id"],
            action=result["action"]
        )

    @pytest.mark.asyncio
    async def test_llm_service_availability(self, openai_llm_service: LLMSuggestionService):
        """Test that LLM service is properly initialized and available."""
        assert openai_llm_service.is_available()
        assert openai_llm_service.llm is not None

    @pytest.mark.asyncio
    async def test_invalid_payload_handling(self, openai_llm_service: LLMSuggestionService):
        """Test LLM handling of invalid/malformed payloads."""
        # Test empty payload
        await openai_llm_service.transform_to_canonical("github", {})
        # Should handle gracefully - either return None or a reasonable default

        # Test payload with no meaningful data
        await openai_llm_service.transform_to_canonical("unknown", {"random": "data"})
        # Should handle gracefully

    @pytest.mark.asyncio
    async def test_prompt_consistency(self, openai_llm_service: LLMSuggestionService):
        """Test that the same payload consistently produces the same canonical output."""
        test_payload = {
            "action": "opened",
            "pull_request": {"number": 123, "title": "Test PR"},
            "repository": {"id": 456, "name": "test-repo"}
        }

        # Run transformation multiple times
        results = []
        for _i in range(3):
            result = await openai_llm_service.transform_to_canonical("github", test_payload)
            results.append(result)

        # All results should be valid
        for result in results:
            assert result is not None
            assert result["publisher"] == "github"
            assert result["action"] in ["create", "update"]  # Could be either for PR opened

        # Results should be consistent
        first_result = results[0]
        for result in results[1:]:
            assert result["publisher"] == first_result["publisher"]
            assert result["resource"]["type"] == first_result["resource"]["type"]
            assert result["action"] == first_result["action"]
