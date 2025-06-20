"""Tests for repository-specific filtering improvements in subscription prompts."""

import pytest
from unittest.mock import AsyncMock, patch

from langhook.subscriptions.llm import LLMPatternService


class TestRepositoryFilteringImprovement:
    """Test improvements for repository-specific filtering in gate prompts."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with dummy configuration for testing."""
        with patch('langhook.subscriptions.llm.subscription_settings') as mock_settings:
            mock_settings.llm_api_key = "dummy-key"
            mock_settings.llm_provider = "openai"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_temperature = 0.1
            mock_settings.llm_max_tokens = 500
            mock_settings.llm_base_url = None
            
            service = LLMPatternService()
            service.llm = AsyncMock()  # Mock the actual LLM to avoid real API calls
            return service

    @pytest.mark.asyncio
    async def test_system_prompt_includes_repository_examples(self, llm_service):
        """Test that the system prompt includes repository-specific filtering examples."""
        mock_schema_data = {
            "publishers": ["github"],
            "resource_types": {"github": ["pull_request", "issue"]},
            "actions": ["created", "updated"],
            "publisher_resource_actions": {
                "github": {
                    "pull_request": ["created", "updated"],
                    "issue": ["created", "updated"]
                }
            }
        }
        
        with patch('langhook.subscriptions.schema_registry.schema_registry_service') as mock_registry:
            mock_registry.get_schema_summary = AsyncMock(return_value=mock_schema_data)
            
            system_prompt = await llm_service._get_system_prompt_with_schemas(gate_enabled=True)
            
            # Check that repository-specific filtering examples are included
            assert "backend-service" in system_prompt
            assert "repository name is 'backend-service'" in system_prompt
            assert "web-frontend repository" in system_prompt
            assert "repository name is 'web-frontend'" in system_prompt

    def test_user_prompt_for_repository_case(self, llm_service):
        """Test user prompt generation for repository-specific cases."""
        description = "Github PR on backend-service is merged"
        user_prompt = llm_service._create_user_prompt(description, gate_enabled=True)
        
        assert description in user_prompt
        assert "JSON" in user_prompt
        assert "pattern" in user_prompt
        assert "gate_prompt" in user_prompt

    def test_parse_repository_specific_response(self, llm_service):
        """Test parsing of repository-specific gate prompt responses."""
        # Test case similar to the issue description but with different names
        response = '''{
            "pattern": "langhook.events.github.pull_request.*.updated",
            "gate_prompt": "Checks whether the pull request is from backend-service repository"
        }'''
        
        result = llm_service._parse_llm_response(response, gate_enabled=True)
        
        assert result is not None
        assert result["pattern"] == "langhook.events.github.pull_request.*.updated"
        assert "backend-service" in result["gate_prompt"]
        assert "repository" in result["gate_prompt"]

    def test_parse_alternative_repository_response_formats(self, llm_service):
        """Test parsing of various repository-specific response formats."""
        test_cases = [
            # Case 1: Direct repository check
            '''{
                "pattern": "langhook.events.github.pull_request.*.updated",
                "gate_prompt": "Evaluate if this event is a GitHub pull request AND the repository name is 'backend-service'"
            }''',
            
            # Case 2: Repository filter with creation check
            '''{
                "pattern": "langhook.events.github.issue.*.created",
                "gate_prompt": "Evaluate if this event is an issue creation AND the repository name is 'web-frontend'"
            }''',
            
            # Case 3: Enterprise account filtering
            '''{
                "pattern": "langhook.events.stripe.payment.*.created",
                "gate_prompt": "Evaluate if this event is a Stripe payment AND the account type is 'enterprise'"
            }'''
        ]
        
        for i, response in enumerate(test_cases):
            result = llm_service._parse_llm_response(response, gate_enabled=True)
            
            assert result is not None, f"Test case {i+1} failed to parse"
            assert "pattern" in result, f"Test case {i+1} missing pattern"
            assert "gate_prompt" in result, f"Test case {i+1} missing gate_prompt"

    @pytest.mark.asyncio
    async def test_system_prompt_covers_issue_scenario(self, llm_service):
        """Test that the system prompt helps with the specific issue scenario."""
        mock_schema_data = {
            "publishers": ["github"],
            "resource_types": {"github": ["pull_request"]},
            "actions": ["created", "updated"],
            "publisher_resource_actions": {
                "github": {
                    "pull_request": ["created", "updated"]
                }
            }
        }
        
        with patch('langhook.subscriptions.schema_registry.schema_registry_service') as mock_registry:
            mock_registry.get_schema_summary = AsyncMock(return_value=mock_schema_data)
            
            system_prompt = await llm_service._get_system_prompt_with_schemas(gate_enabled=True)
            
            # Verify the system prompt contains relevant examples for repository filtering
            # Should show conceptually similar examples without exact matching
            assert "backend-service" in system_prompt or "web-frontend" in system_prompt
            
            # Check that the pattern examples show correct mapping
            assert "langhook.events.github.pull_request.*.updated" in system_prompt
            
            # Verify gate prompt guidance
            assert "repository name" in system_prompt
            assert "AND" in system_prompt  # Shows conjunction pattern for filtering