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
                    model_name="gpt-4o-mini",
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
        Transform raw payload directly to canonical format using LLM (deprecated).

        This method is kept for backward compatibility. New code should use generate_jsonata_mapping.

        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload to analyze

        Returns:
            Canonical event dict or None if transformation fails
        """
        logger.warning("transform_to_canonical is deprecated, use generate_jsonata_mapping instead")

        # For backward compatibility, generate JSONata and apply it
        jsonata_expr = await self.generate_jsonata_mapping(source, raw_payload)
        if not jsonata_expr:
            return None

        # Apply the JSONata expression to get canonical data
        try:
            import jsonata
            result = jsonata.transform(jsonata_expr, raw_payload)
            if isinstance(result, dict):
                # Set publisher if not already set
                if "publisher" not in result:
                    result["publisher"] = source
                return result
            return None
        except Exception as e:
            logger.error(
                "Failed to apply generated JSONata for backward compatibility",
                source=source,
                error=str(e)
            )
            return None

    async def generate_jsonata_mapping(self, source: str, raw_payload: dict[str, Any]) -> str | None:
        """
        Generate JSONata mapping expression for transforming raw payload to canonical format.

        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload to analyze

        Returns:
            JSONata expression string or None if generation fails
        """
        if not self.is_available():
            logger.warning("LLM service not available for JSONata generation")
            return None

        try:
            # Import here to avoid errors if langchain is not installed
            from langchain.schema import HumanMessage, SystemMessage

            # Create the prompt
            system_prompt = self._create_jsonata_system_prompt()
            user_prompt = self._create_user_prompt(source, raw_payload)

            # Generate JSONata expression
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text.strip()

            # Remove any markdown code block formatting if present
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text

            # Validate the JSONata expression by testing it
            if not self._validate_jsonata_expression(response_text, raw_payload, source):
                return None

            logger.info(
                "LLM JSONata generation completed",
                source=source,
                expression_length=len(response_text)
            )

            return response_text

        except Exception as e:
            logger.error(
                "Failed to generate JSONata mapping",
                source=source,
                error=str(e),
                exc_info=True
            )
            return None

    def _create_jsonata_system_prompt(self) -> str:
        """Create the system prompt for JSONata generation."""
        return """You are an API analyst specializing in JSONata expression generation for webhook payload transformation.

Your task is to analyze webhook JSON payloads and generate JSONata expressions that transform them into a canonical format.

The canonical format is a JSON object with these required fields:
- publisher: string (use the source name provided)
- resource: object with "type" (singular noun) and "id" (atomic identifier) fields
- action: CRUD verb (string, must be one of: "created", "read", "updated", "deleted")
- timestamp: ISO 8601 timestamp string

JSONata Expression Guidelines:
1. Analyze the payload structure to identify the main resource
2. Hardcode the action to one of: "created", "read", "updated", "deleted" (choose the most appropriate one based on the webhook event)
3. Extract resource ID (atomic identifier) using appropriate JSONata path
4. Extract timestamp from payload or use appropriate date field
5. Use simple JSONata object syntax (not transform operators)
6. Use proper JSONata field path syntax (e.g., pull_request.number, issue.id)
7. Return ONLY the JSONata expression, no explanations or code blocks

Example JSONata expression:
{"publisher": "github", "resource": {"type": "pull_request", "id": pull_request.id}, "action": "created", "timestamp": pull_request.created_at}"""

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM (deprecated - use _create_jsonata_system_prompt)."""
        return self._create_jsonata_system_prompt()

    def _create_user_prompt(self, source: str, raw_payload: dict[str, Any]) -> str:
        """Create the user prompt with the specific payload to analyze."""
        import json

        payload_json = json.dumps(raw_payload, indent=2)

        return f"""{payload_json}"""

    def _validate_jsonata_expression(self, jsonata_expr: str, raw_payload: dict[str, Any], source: str) -> bool:
        """Validate that the JSONata expression produces valid canonical format."""
        try:
            import jsonata

            # Test the JSONata expression
            result = jsonata.transform(jsonata_expr, raw_payload)

            if not isinstance(result, dict):
                logger.error(
                    "JSONata expression result is not a dictionary",
                    source=source,
                    result_type=type(result).__name__
                )
                return False

            # Validate required fields
            required_fields = ['publisher', 'resource', 'action', 'timestamp']
            missing_fields = [field for field in required_fields if field not in result]

            if missing_fields:
                logger.error(
                    "JSONata expression result missing required fields",
                    source=source,
                    missing_fields=missing_fields,
                    result=result
                )
                return False

            # Validate resource structure
            if not isinstance(result.get('resource'), dict):
                logger.error(
                    "JSONata expression resource must be an object with type and id fields",
                    source=source,
                    resource=result.get('resource')
                )
                return False

            resource = result['resource']
            if 'type' not in resource or 'id' not in resource:
                logger.error(
                    "JSONata expression resource object missing type or id field",
                    source=source,
                    resource=resource
                )
                return False

            # Validate action is CRUD enum in past tense
            valid_actions = ['created', 'read', 'updated', 'deleted']
            if result['action'] not in valid_actions:
                logger.error(
                    "JSONata expression invalid action - must be one of: created, read, updated, deleted",
                    source=source,
                    action=result['action']
                )
                return False

            # Validate atomic ID (no composite keys with # or space, but allow /)
            resource_id = str(resource['id'])
            invalid_chars = ['#', ' ']
            if any(char in resource_id for char in invalid_chars):
                logger.error(
                    "JSONata expression resource ID contains invalid characters (#, space) - atomic IDs only",
                    source=source,
                    resource_id=resource_id
                )
                return False

            # Validate timestamp is a string (basic validation)
            timestamp = result.get('timestamp')
            if not isinstance(timestamp, str):
                logger.error(
                    "JSONata expression timestamp must be a string",
                    source=source,
                    timestamp=timestamp,
                    timestamp_type=type(timestamp).__name__
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Failed to validate JSONata expression",
                source=source,
                expression=jsonata_expr[:200],
                error=str(e)
            )
            return False
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
        required_fields = ['publisher', 'resource', 'action', 'timestamp']
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

        # Validate action is CRUD enum in past tense
        valid_actions = ['created', 'read', 'updated', 'deleted']
        if canonical_data['action'] not in valid_actions:
            logger.error(
                "LLM canonical invalid action - must be one of: created, read, updated, deleted",
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

        # Validate timestamp is a string (basic validation)
        timestamp = canonical_data.get('timestamp')
        if not isinstance(timestamp, str):
            logger.error(
                "LLM canonical timestamp must be a string",
                source=source,
                timestamp=timestamp,
                timestamp_type=type(timestamp).__name__
            )
            return False

        return True


# Global LLM suggestion service instance
llm_service = LLMSuggestionService()
