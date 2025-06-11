"""Large Language Model service for converting descriptions to NATS filter patterns."""

import re
from typing import Any

import structlog

from langhook.subscriptions.config import subscription_settings

logger = structlog.get_logger("langhook")


class NoSuitableSchemaError(Exception):
    """Raised when no suitable schema is found for the subscription request."""
    pass


class LLMPatternService:
    """Service for converting natural language descriptions to NATS filter patterns using LLM."""

    def __init__(self) -> None:
        # Support legacy OpenAI API key for backward compatibility
        api_key = subscription_settings.llm_api_key or subscription_settings.openai_api_key

        if not api_key:
            logger.error("No LLM API key provided - LLM is required for pattern service startup")
            raise ValueError("LLM API key is required for pattern service startup")

        try:
            self.llm = self._initialize_llm(api_key)
            if not self.llm:
                logger.error("Failed to initialize LLM - startup aborted")
                raise RuntimeError("Failed to initialize LLM for pattern service")
            
            logger.info(
                "LLM initialized for pattern service",
                provider=subscription_settings.llm_provider,
                model=subscription_settings.llm_model
            )
        except ImportError as e:
            logger.error(
                "LLM dependencies not available - startup aborted",
                provider=subscription_settings.llm_provider,
                error=str(e)
            )
            raise e
        except Exception as e:
            logger.error(
                "Failed to initialize LLM for pattern service - startup aborted",
                provider=subscription_settings.llm_provider,
                error=str(e),
                exc_info=True
            )
            raise e

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
        return True  # Always True since initialization fails fast if LLM not available

    async def convert_to_pattern_and_gate(self, description: str, gate_enabled: bool = False) -> dict:
        """
        Convert natural language description to NATS filter pattern and optionally generate gate prompt.

        Args:
            description: Natural language description like "Notify me when PR 1374 is approved"
            gate_enabled: Whether to generate a gate prompt for semantic filtering

        Returns:
            Dict containing:
            - pattern: NATS filter pattern like "github.pull_request.1374.update"
            - gate_prompt: Gate evaluation prompt (only if gate_enabled=True)

        Raises:
            NoSuitableSchemaError: When no suitable schema is found for the request
        """
        try:
            system_prompt = await self._get_system_prompt_with_schemas(gate_enabled)
            user_prompt = self._create_user_prompt(description, gate_enabled)

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

            # Check if LLM indicated no suitable schema
            if self._is_no_schema_response(response_text):
                logger.warning(
                    "LLM indicated no suitable schema found",
                    description=description,
                    response=response_text
                )
                raise NoSuitableSchemaError(f"No suitable schema found for description: {description}")

            # Parse the response - try JSON first, then fallback to pattern extraction
            result = self._parse_llm_response(response_text, gate_enabled)

            if result and result.get("pattern"):
                logger.info(
                    "LLM pattern and gate conversion completed",
                    description=description,
                    pattern=result["pattern"],
                    gate_enabled=gate_enabled,
                    has_gate_prompt=gate_enabled and "gate_prompt" in result
                )
                return result
            else:
                if gate_enabled:
                    # When gate is enabled, we require LLM to provide both pattern and gate_prompt
                    logger.error(
                        "LLM failed to provide required gate prompt",
                        description=description,
                        response=response_text
                    )
                    raise ValueError(
                        f"LLM failed to generate required gate prompt for description: '{description}'. "
                        f"Gate prompts require LLM to return JSON with both 'pattern' and 'gate_prompt' fields."
                    )
                else:
                    logger.error(
                        "Failed to extract pattern from LLM response",
                        description=description,
                        response=response_text
                    )
                    raise ValueError(f"LLM failed to generate valid pattern for description: '{description}'")

        except NoSuitableSchemaError:
            raise
        except ValueError as e:
            # Re-raise ValueError as they are expected error conditions
            logger.error(
                "Pattern conversion failed",
                description=description,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "LLM pattern and gate conversion failed",
                description=description,
                error=str(e),
                exc_info=True
            )
            raise ValueError(
                f"LLM service failed to generate pattern for description: '{description}'. "
                f"Error: {str(e)}"
            ) from e

    async def convert_to_pattern(self, description: str) -> str:
        """
        Convert natural language description to NATS filter pattern.
        Kept for backward compatibility.

        Args:
            description: Natural language description like "Notify me when PR 1374 is approved"

        Returns:
            NATS filter pattern like "github.pull_request.1374.update"

        Raises:
            NoSuitableSchemaError: When no suitable schema is found for the request
        """
        result = await self.convert_to_pattern_and_gate(description, gate_enabled=False)
        return result["pattern"]

    async def _get_system_prompt_with_schemas(self, gate_enabled: bool = False) -> str:
        """Get the system prompt for pattern conversion with real schema data and optional gate prompt generation."""
        # Import here to avoid circular imports
        from langhook.subscriptions.schema_registry import schema_registry_service

        try:
            schema_data = await schema_registry_service.get_schema_summary()
        except Exception as e:
            logger.warning(
                "Failed to fetch schema data for prompt, using fallback",
                error=str(e)
            )
            schema_data = {
                "publishers": [],
                "resource_types": {},
                "actions": [],
                "publisher_resource_actions": {}
            }

        # Build schema information for the prompt
        if not schema_data["publishers"]:
            # No schemas available, include instruction to reject
            schema_info = """
IMPORTANT: No event schemas are currently registered in the system. You must respond with "ERROR: No registered schemas available" for any subscription request."""
        else:
            # Build schema information from real data using granular publisher+resource -> actions mapping
            if "publisher_resource_actions" in schema_data and schema_data["publisher_resource_actions"]:
                # Use the new granular format
                publishers_list = ", ".join(schema_data["publishers"])
                
                # Build detailed schema information showing exact combinations
                schema_combinations = []
                for publisher, resource_actions in schema_data["publisher_resource_actions"].items():
                    for resource_type, actions in resource_actions.items():
                        actions_str = ", ".join(actions)
                        schema_combinations.append(f"- {publisher}.{resource_type}: {actions_str}")
                
                schema_combinations_text = "\n".join(schema_combinations)
                
                schema_info = f"""
AVAILABLE EVENT SCHEMAS:
Publishers: {publishers_list}

Available publisher.resource_type combinations and their supported actions:
{schema_combinations_text}

IMPORTANT: You may ONLY use the exact publisher, resource type, and action combinations listed above. If the user's request cannot be mapped to these exact schemas, respond with "ERROR: No suitable schema found" instead of a pattern."""
            else:
                # Fallback to old format if granular data is not available
                publishers_list = ", ".join(schema_data["publishers"])
                actions_list = ", ".join(schema_data["actions"])

                resource_types_info = []
                for publisher, resource_types in schema_data["resource_types"].items():
                    types_str = ", ".join(resource_types)
                    resource_types_info.append(f"- {publisher}: {types_str}")
                resource_types_text = "\n".join(resource_types_info)

                schema_info = f"""
AVAILABLE EVENT SCHEMAS:
Publishers: {publishers_list}
Actions: {actions_list}
Resource types by publisher:
{resource_types_text}

IMPORTANT: You may ONLY use the publishers, resource types, and actions listed above. If the user's request cannot be mapped to these exact schemas, respond with "ERROR: No suitable schema found" instead of a pattern."""

        if gate_enabled:
            # Combined prompt for pattern + gate prompt generation
            gate_instructions = """

GATE PROMPT GENERATION:
Additionally, you must generate a gate_prompt that will be used to evaluate whether incoming events match the user's specific intent. This prompt should:
1. Be specific to the user's exact criteria and requirements
2. Only evaluate what the user explicitly requested (no bias toward "importance" or "urgency")
3. Focus on the user's specific conditions, filters, or criteria
4. NOT include JSON format instructions (the system will handle response formatting)

Examples of good gate prompts:
- For "GitHub comments from Alice": "Evaluate if this event is a GitHub comment AND the author is Alice"
- For "Stripe payments over $1000": "Evaluate if this event is a Stripe payment AND the amount is greater than $1000"
- For "Slack messages containing 'urgent'": "Evaluate if this event is a Slack message AND contains the word 'urgent'"
- For "Stripe refunds over $500": "Approve if this Stripe refund is more than $500 in value"
- For "Production deployments that failed": "Approve if this deployment event indicates a failure in the production environment"
- For "High priority security alerts": "Approve if this security event has high priority or critical severity"

RESPONSE FORMAT:
You must respond with a JSON object containing both the pattern and gate_prompt:
{
  "pattern": "langhook.events.publisher.resource.id.action",
  "gate_prompt": "Your gate evaluation prompt here"
}

If no suitable schema is found, respond with:
{
  "error": "No suitable schema found"
}"""
        else:
            gate_instructions = """

RESPONSE FORMAT:
Respond with only the pattern or respond with "ERROR: No suitable schema found" if no suitable schema is found."""

        return f"""You are a NATS JetStream filter pattern generator for LangHook.

Your task: convert a natural-language event description into a valid NATS subject pattern using this schema:

Pattern: langhook.events.<publisher>.<resource_type>.<resource_id>.<action>
Wildcards: `*` = one token, `>` = one or more tokens at end

Allowed:

{schema_info}


Rules:
1. Think like a REST API: map natural verbs to `created`, `read`, or `updated`.
   - e.g., “opened” = created, “seen” = read, “merged” = updated
2. Only use exact values from allowed schema
3. Use `*` for missing IDs
4. If no valid mapping, reply: `"ERROR: No suitable schema found"`

Examples:
🟢 "A GitHub PR is merged" → `langhook.events.github.pull_request.*.updated`
🟢 "Slack file is uploaded" → `langhook.events.slack.file.*.created`
🟢 "PR submitted on GitHub" → `langhook.events.github.pull_request.*.created`
🔴 "A comment is liked" → `"ERROR: No suitable schema found"`{gate_instructions}"""

    def _create_user_prompt(self, description: str, gate_enabled: bool = False) -> str:
        """Create the user prompt for pattern conversion and optional gate prompt generation."""
        if gate_enabled:
            return f"""Convert this natural language description to a NATS filter pattern and generate a gate prompt:

"{description}"

Respond with JSON containing both pattern and gate_prompt."""
        else:
            return f"""Convert this natural language description to a NATS filter pattern:

"{description}"

Pattern:"""

    def _is_no_schema_response(self, response: str) -> bool:
        """Check if the LLM response indicates no suitable schema was found."""
        response_lower = response.lower().strip()
        error_indicators = [
            "error: no suitable schema found",
            "error: no registered schemas available",
            "no suitable schema",
            "no registered schemas",
            "cannot be mapped",
            "not available in",
            "schema not found"
        ]
        return any(indicator in response_lower for indicator in error_indicators)

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

    def _parse_llm_response(self, response: str, gate_enabled: bool) -> dict | None:
        """Parse LLM response for pattern and optional gate prompt."""
        import json

        if gate_enabled:
            # Try to parse JSON response
            try:
                data = json.loads(response.strip())
                if isinstance(data, dict) and "pattern" in data:
                    # When gate is enabled, gate_prompt is required
                    if "gate_prompt" not in data:
                        raise ValueError("LLM response missing required gate_prompt when gate is enabled")
                    return data
            except json.JSONDecodeError:
                pass

            # For gate-enabled requests, we need proper JSON with both pattern and gate_prompt
            pattern = self._extract_pattern_from_response(response)
            if pattern:
                raise ValueError(
                    f"LLM failed to return properly formatted JSON response with gate_prompt. "
                    f"Expected JSON with 'pattern' and 'gate_prompt' fields, but got: {response[:100]}..."
                )
        else:
            # Only pattern extraction needed
            pattern = self._extract_pattern_from_response(response)
            if pattern:
                return {"pattern": pattern}

        return None


# Global LLM service instance
# Note: Service initialization moved to calling code to avoid import-time failures
# when LLM is not configured. Use LLMPatternService() directly where needed.
