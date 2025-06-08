"""LLM-based mapping suggestion service."""

from typing import Any

import structlog

from langhook.map.config import settings

logger = structlog.get_logger("langhook")


class LLMSuggestionService:
    """Service for generating JSONata mapping suggestions using LLM."""

    def __init__(self) -> None:
        self.llm_available = False
        if settings.openai_api_key:
            try:
                # Import and initialize LLM only if API key is available
                from langchain.chat_models import ChatOpenAI
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name="gpt-4.1-nano",
                    temperature=0.1,
                    max_tokens=1000,
                )
                self.llm_available = True
                logger.info("OpenAI LLM initialized")
            except ImportError as e:
                logger.warning("LangChain not available, LLM suggestions disabled")
                raise e
            except Exception as e:
                logger.error(
                    "Failed to initialize OpenAI LLM",
                    error=str(e),
                    exc_info=True
                )
                raise e
        else:
            logger.info("No OpenAI API key provided, LLM suggestions disabled")

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.llm_available

    async def transform_to_canonical(self, source: str, raw_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Transform raw payload directly to canonical format using LLM.
        
        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload to analyze
            
        Returns:
            Canonical event dict or None if transformation fails
        """
        if not self.is_available():
            logger.warning("LLM service not available for canonical transformation")
            return None

        try:
            # Import here to avoid errors if langchain is not installed
            import json

            from langchain.schema import HumanMessage, SystemMessage

            # Create the prompt
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(source, raw_payload)

            # Generate canonical event
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text.strip()

            # Parse the JSON response
            try:
                canonical_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(
                    "LLM returned invalid JSON",
                    source=source,
                    response=response_text[:500],
                    error=str(e)
                )
                return None

            # Validate the canonical format
            if not self._validate_canonical_format(canonical_data, source):
                return None

            logger.info(
                "LLM canonical transformation completed",
                source=source,
                publisher=canonical_data.get("publisher"),
                resource_type=canonical_data.get("resource", {}).get("type"),
                action=canonical_data.get("action")
            )

            return canonical_data

        except Exception as e:
            logger.error(
                "Failed to transform payload to canonical format",
                source=source,
                error=str(e),
                exc_info=True
            )
            return None

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        return """You are an API analyst specializing in webhook payload transformation.

Your task is to analyze webhook JSON payloads and transform them directly into a canonical format.

The canonical format is a JSON object with these required fields:
- publisher: upstream slug/identifier (string, lowercase snake_case)
- resource: object with "type" (singular noun) and "id" (atomic identifier) fields  
- action: CRUD verb (string, must be one of: "create", "read", "update", "delete")

Guidelines:
1. Analyze the payload structure to identify the main resource and action
2. Look for event type / action indicator - this will often give you resource type and action
3. Map webhook actions to CRUD verbs: opened/created→create, closed/deleted→delete, edited/updated→update, viewed→read
4. Extract resource ID (atomic identifier)
5. Return ONLY a valid JSON object with the canonical fields, no explanations or code blocks
6. Use the source name as the publisher value (lowercase, snake_case)

Example canonical format:
{
  "publisher": "github",
  "resource": {"type": "pull_request", "id": 123},
  "action": "create"
}"""

    def _create_user_prompt(self, source: str, raw_payload: dict[str, Any]) -> str:
        """Create the user prompt with the specific payload to analyze."""
        import json

        payload_json = json.dumps(raw_payload, indent=2)

        return f"""{payload_json}"""

    def _validate_canonical_format(self, canonical_data: dict[str, Any], source: str) -> bool:
        """Validate that the canonical data has the required format."""
        # Ensure result has required fields for canonical format
        if not isinstance(canonical_data, dict):
            logger.error(
                "LLM canonical result is not a dictionary",
                source=source,
                result_type=type(canonical_data).__name__
            )
            return False

        # Validate required fields
        required_fields = ['publisher', 'resource', 'action']
        missing_fields = [field for field in required_fields if field not in canonical_data]

        if missing_fields:
            logger.error(
                "LLM canonical result missing required fields",
                source=source,
                missing_fields=missing_fields,
                result=canonical_data
            )
            return False

        # Validate resource structure
        if not isinstance(canonical_data.get('resource'), dict):
            logger.error(
                "LLM canonical resource must be an object with type and id fields",
                source=source,
                resource=canonical_data.get('resource')
            )
            return False

        resource = canonical_data['resource']
        if 'type' not in resource or 'id' not in resource:
            logger.error(
                "LLM canonical resource object missing type or id field",
                source=source,
                resource=resource
            )
            return False

        # Validate action is CRUD enum
        valid_actions = ['create', 'read', 'update', 'delete']
        if canonical_data['action'] not in valid_actions:
            logger.error(
                "LLM canonical invalid action - must be one of: create, read, update, delete",
                source=source,
                action=canonical_data['action']
            )
            return False

        # Validate atomic ID (no composite keys with # or space, but allow /)
        resource_id = str(resource['id'])
        invalid_chars = ['#', ' ']
        if any(char in resource_id for char in invalid_chars):
            logger.error(
                "LLM canonical resource ID contains invalid characters (#, space) - atomic IDs only",
                source=source,
                resource_id=resource_id
            )
            return False

        return True


# Global LLM suggestion service instance
llm_service = LLMSuggestionService()
