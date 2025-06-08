"""Large Language Model service for converting descriptions to NATS filter patterns."""

import re
from typing import Any

import structlog

from langhook.subscriptions.config import subscription_settings

logger = structlog.get_logger("langhook")


class LLMPatternService:
    """Service for converting natural language descriptions to NATS filter patterns using LLM."""

    def __init__(self) -> None:
        self.llm_available = False
        self.llm: Any | None = None

        # Support legacy OpenAI API key for backward compatibility
        api_key = subscription_settings.llm_api_key or subscription_settings.openai_api_key

        if api_key:
            try:
                self.llm = self._initialize_llm(api_key)
                if self.llm:
                    self.llm_available = True
                    logger.info(
                        "LLM initialized for pattern service",
                        provider=subscription_settings.llm_provider,
                        model=subscription_settings.llm_model
                    )
            except ImportError as e:
                logger.warning(
                    "LLM dependencies not available, pattern service disabled",
                    provider=subscription_settings.llm_provider,
                    error=str(e)
                )
            except Exception as e:
                logger.error(
                    "Failed to initialize LLM for pattern service",
                    provider=subscription_settings.llm_provider,
                    error=str(e),
                    exc_info=True
                )
        else:
            logger.info("No LLM API key provided, pattern service using fallback")

    def _initialize_llm(self, api_key: str) -> Any | None:
        """Initialize the appropriate LLM based on provider configuration."""
        provider = subscription_settings.llm_provider.lower()

        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    openai_api_key=api_key,
                    model_name=subscription_settings.llm_model,
                    temperature=subscription_settings.llm_temperature,
                    max_tokens=subscription_settings.llm_max_tokens,
                    base_url=subscription_settings.llm_base_url,
                )
            elif provider == "azure_openai":
                from langchain_openai import AzureChatOpenAI
                return AzureChatOpenAI(
                    openai_api_key=api_key,
                    model_name=subscription_settings.llm_model,
                    temperature=subscription_settings.llm_temperature,
                    max_tokens=subscription_settings.llm_max_tokens,
                    azure_endpoint=subscription_settings.llm_base_url,
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    anthropic_api_key=api_key,
                    model=subscription_settings.llm_model,
                    temperature=subscription_settings.llm_temperature,
                    max_tokens=subscription_settings.llm_max_tokens,
                )
            elif provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=subscription_settings.llm_model,
                    temperature=subscription_settings.llm_temperature,
                    max_output_tokens=subscription_settings.llm_max_tokens,
                )
            elif provider == "local":
                # For local LLMs using OpenAI-compatible API
                from langchain_openai import ChatOpenAI
                if not subscription_settings.llm_base_url:
                    raise ValueError("LLM_BASE_URL is required for local LLM provider")
                return ChatOpenAI(
                    openai_api_key=api_key or "dummy-key",  # Local LLMs often don't need real API keys
                    model_name=subscription_settings.llm_model,
                    temperature=subscription_settings.llm_temperature,
                    max_tokens=subscription_settings.llm_max_tokens,
                    base_url=subscription_settings.llm_base_url,
                )
            else:
                logger.error(f"Unsupported LLM provider: {provider}")
                return None

        except ImportError as e:
            logger.error(
                f"Failed to import LLM provider {provider}",
                error=str(e),
                provider=provider
            )
            return None

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.llm_available

    async def convert_to_pattern(self, description: str) -> str:
        """
        Convert natural language description to NATS filter pattern.

        Args:
            description: Natural language description like "Notify me when PR 1374 is approved"

        Returns:
            NATS filter pattern like "github.pull_request.1374.update"
        """
        if not self.llm_available:
            return self._fallback_pattern_conversion(description)

        try:
            system_prompt = self._get_system_prompt()
            user_prompt = self._create_user_prompt(description)

            # Create messages in a format compatible with different LLM providers
            if hasattr(self.llm, 'agenerate'):
                # LangChain-style interface
                from langchain.schema import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = await self.llm.agenerate([messages])
                response_text = response.generations[0][0].text.strip()
            else:
                # Direct interface for some LLM providers
                full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
                response_text = await self.llm.ainvoke(full_prompt)
                if hasattr(response_text, 'content'):
                    response_text = response_text.content.strip()
                else:
                    response_text = str(response_text).strip()

            # Parse the response to extract the pattern
            pattern = self._extract_pattern_from_response(response_text)

            if pattern:
                logger.info(
                    "LLM pattern conversion completed",
                    description=description,
                    pattern=pattern
                )
                return pattern
            else:
                logger.warning(
                    "Failed to extract pattern from LLM response, using fallback",
                    description=description,
                    response=response_text
                )
                return self._fallback_pattern_conversion(description)

        except Exception as e:
            logger.error(
                "Failed to convert description to pattern using LLM",
                description=description,
                error=str(e),
                exc_info=True
            )
            return self._fallback_pattern_conversion(description)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for pattern conversion."""
        return """You are a NATS JetStream filter pattern generator for LangHook event subscriptions.

Your job is to convert natural language descriptions into NATS subject filter patterns.

NATS subject pattern format: langhook.events.<publisher>.<resource_type>.<resource_id>.<action>

Examples:
- "langhook.events.github.pull_request.1374.update" - GitHub PR 1374 updates
- "langhook.events.stripe.payment_intent.*.create" - Any Stripe payment intent creation
- "langhook.events.*.user.123.delete" - User 123 deletion from any system
- "langhook.events.github.*.*.update" - Any GitHub resource updates

Wildcards:
- "*" matches exactly one token
- ">" matches one or more tokens at the end

Publishers: github, stripe, slack, jira, custom-app, etc.
Resource types: pull_request, issue, payment_intent, user, order, etc.
Actions: create, read, update, delete

Respond with just the pattern, nothing else."""

    def _create_user_prompt(self, description: str) -> str:
        """Create the user prompt for pattern conversion."""
        return f"""Convert this natural language description to a NATS filter pattern:

"{description}"

Pattern:"""

    def _extract_pattern_from_response(self, response: str) -> str | None:
        """Extract the NATS pattern from the LLM response."""
        # Look for a pattern that matches the new NATS subject format with langhook.events prefix
        pattern_regex = r'langhook\.events\.([a-z0-9_\-*>]+\.){3}[a-z0-9_\-*>]+'

        match = re.search(pattern_regex, response.lower())
        if match:
            return match.group(0)

        # If no pattern found, check if the entire response looks like a pattern
        cleaned = response.strip().lower()
        if re.match(r'^langhook\.events\.([a-z0-9_\-*>]+\.){3}[a-z0-9_\-*>]+$', cleaned):
            return cleaned

        return None

    def _fallback_pattern_conversion(self, description: str) -> str:
        """
        Fallback pattern conversion using simple text matching.

        This provides basic functionality when LLM is not available.
        """
        description_lower = description.lower()

        # Extract common patterns
        publisher = "*"
        resource_type = "*"
        resource_id = "*"
        action = "*"

        # Try to detect publisher
        if "github" in description_lower or "pr" in description_lower or "pull request" in description_lower:
            publisher = "github"
            if "pr" in description_lower or "pull request" in description_lower:
                resource_type = "pull_request"
        elif "stripe" in description_lower or "payment" in description_lower:
            publisher = "stripe"
            if "payment" in description_lower:
                resource_type = "payment_intent"
        elif "slack" in description_lower:
            publisher = "slack"
        elif "jira" in description_lower:
            publisher = "jira"

        # Try to extract specific IDs
        id_match = re.search(r'\b(\d+)\b', description)
        if id_match:
            resource_id = id_match.group(1)

        # Try to detect action
        if any(word in description_lower for word in ["create", "created", "new"]):
            action = "create"
        elif any(word in description_lower for word in ["update", "updated", "change", "modified"]):
            action = "update"
        elif any(word in description_lower for word in ["delete", "deleted", "remove", "removed"]):
            action = "delete"
        elif any(word in description_lower for word in ["approve", "approved"]):
            action = "update"  # Approval is typically an update action

        pattern = f"langhook.events.{publisher}.{resource_type}.{resource_id}.{action}"

        logger.info(
            "Fallback pattern conversion completed",
            description=description,
            pattern=pattern
        )

        return pattern


# Global LLM service instance
llm_service = LLMPatternService()
