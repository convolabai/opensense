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
        if not self.llm_available:
            pattern = self._fallback_pattern_conversion(description)
            result = {"pattern": pattern}
            if gate_enabled:
                result["gate_prompt"] = self._fallback_gate_prompt(description)
            return result

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
                    gate_enabled=gate_enabled
                )
                return result
            else:
                logger.warning(
                    "Failed to extract pattern from LLM response, using fallback",
                    description=description,
                    response=response_text
                )
                pattern = self._fallback_pattern_conversion(description)
                result = {"pattern": pattern}
                if gate_enabled:
                    result["gate_prompt"] = self._fallback_gate_prompt(description)
                return result

        except NoSuitableSchemaError:
            raise
        except Exception as e:
            logger.error(
                "LLM pattern and gate conversion failed",
                description=description,
                error=str(e),
                exc_info=True
            )
            pattern = self._fallback_pattern_conversion(description)
            result = {"pattern": pattern}
            if gate_enabled:
                result["gate_prompt"] = self._fallback_gate_prompt(description)
            return result

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
                "actions": []
            }

        # Build schema information for the prompt
        if not schema_data["publishers"]:
            # No schemas available, include instruction to reject
            schema_info = """
IMPORTANT: No event schemas are currently registered in the system. You must respond with "ERROR: No registered schemas available" for any subscription request."""
        else:
            # Build schema information from real data
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
3. Instruct the evaluator to return JSON: {"decision": true or false}
4. Focus on the user's specific conditions, filters, or criteria

Examples of good gate prompts:
- For "GitHub comments from Alice": "Evaluate if this event is a GitHub comment AND the author is Alice. Return {"decision": true or false}"
- For "Stripe payments over $1000": "Evaluate if this event is a Stripe payment AND the amount is greater than $1000. Return {"decision": true or false}"
- For "Slack messages containing 'urgent'": "Evaluate if this event is a Slack message AND contains the word 'urgent'. Return {"decision": true or false}"

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

        # Try to detect action (convert to past tense)
        if any(word in description_lower for word in ["create", "created", "new"]):
            action = "created"
        elif any(word in description_lower for word in ["update", "updated", "change", "modified"]):
            action = "updated"
        elif any(word in description_lower for word in ["delete", "deleted", "remove", "removed"]):
            action = "deleted"
        elif any(word in description_lower for word in ["approve", "approved"]):
            action = "updated"  # Approval is typically an update action

        pattern = f"langhook.events.{publisher}.{resource_type}.{resource_id}.{action}"

        logger.info(
            "Fallback pattern conversion completed",
            description=description,
            pattern=pattern
        )

        return pattern

    def _parse_llm_response(self, response: str, gate_enabled: bool) -> dict | None:
        """Parse LLM response for pattern and optional gate prompt."""
        import json
        
        if gate_enabled:
            # Try to parse JSON response
            try:
                data = json.loads(response.strip())
                if isinstance(data, dict) and "pattern" in data:
                    return data
            except json.JSONDecodeError:
                pass
            
            # If JSON parsing fails, try to extract pattern and create fallback gate prompt
            pattern = self._extract_pattern_from_response(response)
            if pattern:
                # Extract the original description from the pattern for fallback gate prompt
                return {
                    "pattern": pattern,
                    "gate_prompt": "Evaluate if this event matches the subscription criteria. Return {\"decision\": true or false}"
                }
        else:
            # Only pattern extraction needed
            pattern = self._extract_pattern_from_response(response)
            if pattern:
                return {"pattern": pattern}
        
        return None

    def _fallback_gate_prompt(self, description: str) -> str:
        """Generate a fallback gate prompt when LLM is not available."""
        return f"""Evaluate if this event matches the subscription: "{description}"

Return ONLY a JSON object:
{{
    "decision": true or false
}}

Return true if the event matches what the user requested, false otherwise."""


# Global LLM service instance
llm_service = LLMPatternService()
