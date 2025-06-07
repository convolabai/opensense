"""Natural Language Processing service for converting descriptions to NATS filter patterns."""

import json
import re
from typing import Optional

import structlog
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from langhook.subscriptions.config import subscription_settings

logger = structlog.get_logger("langhook")


class NLPPatternService:
    """Service for converting natural language descriptions to NATS filter patterns."""

    def __init__(self) -> None:
        self.llm_available = False
        if subscription_settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    openai_api_key=subscription_settings.openai_api_key,
                    model_name="gpt-4",
                    temperature=0.1,
                    max_tokens=500,
                )
                self.llm_available = True
                logger.info("OpenAI LLM initialized for NLP pattern service")
            except ImportError:
                logger.warning("LangChain not available, NLP pattern service disabled")
            except Exception as e:
                logger.error(
                    "Failed to initialize OpenAI LLM for NLP pattern service",
                    error=str(e),
                    exc_info=True
                )
        else:
            logger.info("No OpenAI API key provided, NLP pattern service using fallback")

    def is_available(self) -> bool:
        """Check if NLP service is available."""
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

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text.strip()

            # Parse the response to extract the pattern
            pattern = self._extract_pattern_from_response(response_text)
            
            if pattern:
                logger.info(
                    "NLP pattern conversion completed",
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

NATS subject pattern format: <publisher>.<resource_type>.<resource_id>.<action>

Examples:
- "github.pull_request.1374.update" - GitHub PR 1374 updates
- "stripe.payment_intent.*.create" - Any Stripe payment intent creation
- "*.user.123.delete" - User 123 deletion from any system
- "github.*.*.update" - Any GitHub resource updates

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

    def _extract_pattern_from_response(self, response: str) -> Optional[str]:
        """Extract the NATS pattern from the LLM response."""
        # Look for a pattern that matches the NATS subject format
        pattern_regex = r'([a-z0-9_\-*>]+\.){3}[a-z0-9_\-*>]+'
        
        match = re.search(pattern_regex, response.lower())
        if match:
            return match.group(0)
        
        # If no pattern found, check if the entire response looks like a pattern
        cleaned = response.strip().lower()
        if re.match(r'^([a-z0-9_\-*>]+\.){3}[a-z0-9_\-*>]+$', cleaned):
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
            
        pattern = f"{publisher}.{resource_type}.{resource_id}.{action}"
        
        logger.info(
            "Fallback pattern conversion completed",
            description=description,
            pattern=pattern
        )
        
        return pattern


# Global NLP service instance
nlp_service = NLPPatternService()