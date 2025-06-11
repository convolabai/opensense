"""LLM-based mapping suggestion service."""

from typing import Any

import structlog

from langhook.map.config import settings

logger = structlog.get_logger("langhook")


class LLMSuggestionService:
    """Service for generating JSONata mapping suggestions using LLM."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            logger.error("No OpenAI API key provided - LLM is required for mapping service startup")
            raise ValueError("OpenAI API key is required for mapping service startup")

        try:
            # Import and initialize LLM only if API key is available
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                openai_api_key=settings.openai_api_key,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=1000,
            )
            logger.info("OpenAI LLM initialized")
        except ImportError as e:
            logger.error("LangChain OpenAI not available - startup aborted")
            raise e
        except Exception as e:
            logger.error(
                "Failed to initialize OpenAI LLM - startup aborted",
                error=str(e),
                exc_info=True
            )
            raise e

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return True  # Always True since initialization fails fast if LLM not available

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
        if jsonata_expr is None:
            logger.error("Failed to generate JSONata expression", source=source)
            return None
            
        # Sanitize JSONata expression for compatibility
        jsonata_expr = jsonata_expr.replace("\\'", '"')
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

    async def generate_jsonata_mapping_with_event_field(
        self,
        source: str,
        raw_payload: dict[str, Any]
    ) -> tuple[str, str | None] | None:
        """
        Generate JSONata mapping expression and event field expression for enhanced fingerprinting.

        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload to analyze

        Returns:
            Tuple of (jsonata_expression, event_field_expression) or None if generation fails
        """
        try:
            # Import here to avoid errors if langchain is not installed
            import json

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

            # Try to parse the response as JSON to extract both jsonata and event_field
            try:
                response_data = json.loads(response_text)
                if isinstance(response_data, dict):
                    jsonata_expr = response_data.get("jsonata")
                    event_field_expr = response_data.get("event_field")

                    if jsonata_expr:
                        # Normalise to string WITHOUT adding another pair of quotes
                        if isinstance(jsonata_expr, str):
                            jsonata_str = jsonata_expr.strip()
                        else:  # LLM returned an object representation
                            import json
                            jsonata_str = json.dumps(jsonata_expr, separators=(",", ":"))
                        # Validate the JSONata expression by testing it
                        if not self._validate_jsonata_expression(jsonata_str, raw_payload, source):
                            return None

                        logger.info(
                            "LLM JSONata generation with event field completed",
                            source=source,
                            expression_length=len(jsonata_str),
                            event_field_expr=event_field_expr
                        )

                        return (jsonata_str, event_field_expr)
                    else:
                        logger.error("No jsonata field in LLM response", response=response_text)
                        return None
                else:
                    logger.error("LLM response is not a JSON object", response=response_text)
                    return None
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse LLM response as JSON",
                    response=response_text,
                    error=str(e)
                )
                return None

        except Exception as e:
            logger.error(
                "Failed to generate JSONata mapping with event field",
                source=source,
                error=str(e),
                exc_info=True
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
        return """
You are LangHook Webhook → JSONata Mapper.

Input:
	•	source_name: webhook source (e.g. "github")
	•	payload: raw JSON webhook object

Output:

One-line JSON:

{"jsonata":{...},"event_field":"<jsonata-path>"}

Goal:

Generate:
	•	jsonata: converts payload to canonical format:

{
  "publisher": <source_name>,
  "resource": { "type": <singular-noun>, "id": <scalar-id-path> },
  "action": "created" | "read" | "updated" | "deleted",
  "timestamp": <ISO-8601>
}

	•	event_field: JSONata path to distinguish event type (e.g. "action", "event.type")

Rules:
	1.	Use source_name as publisher.
	2.	Pick main object (e.g., PR, message) as resource.type.
	3.	Map action to CRUD:
	•	created → "opened", "created"
	•	updated → "approved", "merged", "edited"
	•	deleted → "deleted", "removed"
	•	read    → "viewed", "accessed"
	4.	resource.id: scalar path (no concat).
	5.	timestamp: most specific available.
	6.	Use object constructor syntax only.
	7.	event_field: simple path indicating event type (e.g. "action").

Examples

Example 1 - GitHub PR Opened

{
  "jsonata": "{ \"publisher\": \"github\", \"resource\": { \"type\": \"pull_request\", \"id\": pull_request.id }, \"action\": \"created\", \"timestamp\": pull_request.created_at }",
  "event_field": "action"
}


⸻

Example 2 - GitHub PR Review Approved

{
  "jsonata": "{ \"publisher\": \"github\", \"resource\": { \"type\": \"pull_request\", \"id\": pull_request.id }, \"action\": \"updated\", \"timestamp\": pull_request.updated_at }",
  "event_field": "action"
}


⸻

Example 3 - Stripe Payment Succeeded

{
  "jsonata": "{ \"publisher\": \"stripe\", \"resource\": { \"type\": \"payment\", \"id\": data.object.id }, \"action\": \"updated\", \"timestamp\": $formatInteger(created * 1000, \"[Y0001]-[M01]-[D01]T[H01]:[m01]:[s01]Z\") }",
  "event_field": "type"
}


⸻

Example 4 - Slack Message Posted

{
  "jsonata": "{ \"publisher\": \"slack\", \"resource\": { \"type\": \"message\", \"id\": event.ts }, \"action\": \"created\", \"timestamp\": $fromMillis($number(event.ts) * 1000) }",
  "event_field": "event.type"
}


⸻

Example 5 - Salesforce Contact Updated

{
  "jsonata": "{ \"publisher\": \"salesforce\", \"resource\": { \"type\": \"contact\", \"id\": sobject.Id }, \"action\": \"updated\", \"timestamp\": sobject.LastModifiedDate }",
  "event_field": "eventType"
}

"""

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

            # Sanitize JSONata expression for compatibility (same as in transform_to_canonical)
            sanitized_expr = jsonata_expr.replace("\\'", '"')
            
            # Test the JSONata expression
            result = jsonata.transform(sanitized_expr, raw_payload)

            if not isinstance(result, dict):
                logger.error(
                    "JSONata expression result is not a dictionary",
                    source=source,
                    result_type=type(result).__name__
                )
                return False
            # if timestamp is not in result, add it with current time
            if 'timestamp' not in result:
                logger.warning(
                    f"JSONata expression {jsonata_expr} result missing timestamp, adding current time")
                from datetime import datetime
                result['timestamp'] = datetime.utcnow().isoformat() + 'Z'
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
                error=str(e),
                exc_info=True
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
# Note: Service initialization moved to calling code to avoid import-time failures
# when LLM is not configured. Use LLMSuggestionService() directly where needed.
