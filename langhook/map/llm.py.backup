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
        if not self.is_available():
            logger.warning("LLM service not available for JSONata generation")
            return None

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
                        # Convert the jsonata dict back to string for validation
                        jsonata_str = json.dumps(jsonata_expr)

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
        return """
You are **LangHook Webhook → JSONata Mapper v2**.

╭───────────────────────────── CORE TASK ─────────────────────────────╮
│ 1. Receive: one raw webhook JSON object + the string `source_name`. │
│ 2. Produce:                                                      │
│    a. `fingerprint`  – 64-hex SHA-256 of the webhook’s **type-     │
│       skeleton** (see “Fingerprint Rules”).                        │
│    b. `jsonata`      – a JSONata expression that converts that     │
│       payload to LangHook’s canonical format.                      │
╰──────────────────────────────────────────────────────────────────────╯

─────────────────────────────  Canonical Format  ─────────────────────────────
{ "publisher": <string>,                       # use source_name verbatim
  "resource":  { "type": <singular-noun>,
                 "id":   <atomic-identifier> },
  "action":    <created|read|updated|deleted>,
  "timestamp": <ISO-8601>,
  "raw":       $ }                            # ALWAYS assign complete payload

──────────────────────────────  JSONata Rules  ───────────────────────────────
1. Pick the **main object** (PR, issue, message…) as `resource.type`.
2. Choose exactly one CRUD verb for `action`.  
   • “opened”, “created” ⇒ `created`  
   • “approved”, “merged”, “edited” ⇒ `updated`  
   • “deleted”, “removed” ⇒ `deleted`  
   • “viewed”, “accessed” ⇒ `read`
3. `resource.id` must be a single scalar path (no concatenation).
4. If multiple plausible timestamps exist, use the most specific one  
   (e.g., `pull_request.created_at` over `repository.pushed_at`).
5. Use **object constructor** syntax only (no transform operators).
6. Return **nothing except** the three required fields in the exact format  
   described in OUTPUT FORMAT.

──────────────────────────────  Event Field Rules  ───────────────────────────
1. Identify the field that indicates the event type or action.
2. This is typically named "action", "event", "type", "state", etc.
3. The event_field expression should be a simple JSONata path (e.g., "action", "event.type").
4. This field's value will be used to distinguish events with the same structure but different actions.

──────────────────────────────  Fingerprint Rules  ───────────────────────────
A. Build a **type skeleton**:
   • Recursively replace every leaf value with its JSON datatype
     ("string", "number", "boolean", "null", "array", "object").
B. Sort all keys alphabetically at every depth.
C. Serialize the skeleton as **minified JSON** (no spaces).
D. Compute SHA-256 of that string; output lower-case hex (64 chars).

───────────────────────────────  OUTPUT FORMAT  ──────────────────────────────
Return ONE line containing a JSON object **without code fences**:

{"fingerprint":"<64-hex>","jsonata":{"publisher":...},"event_field":"<jsonata-path>"}

Nothing else – no comments, newlines, or markdown.

────────────────────────────────  EXAMPLES  ──────────────────────────────────
### Example 1 – GitHub PR opened
Input payload (abridged):
{
  "action":"opened",
  "number":42,
  "pull_request":{"id":1480863564,"title":"Fix typo"},
  "repository":{"id":5580001,"name":"langhook"}
}
source_name: "github"

Expected output **exactly one line**:
{"fingerprint":"3b1eab4cf804c4e1c832b61f6b8ae9f24f5db59b6d5795adbb7d75de5ce3e722","jsonata":{"publisher":"github","resource":{"type":"pull_request","id":pull_request.id},"action":"created","timestamp":pull_request.created_at,"raw":$},"event_field":"action"}

### Example 2 – GitHub PR review approved
Input payload (abridged):
{
  "action":"submitted",
  "review":{"state":"approved"},
  "pull_request":{"id":1480863564,"merged":false},
  "repository":{"id":5580001}
}
source_name: "github"

Output:
{"fingerprint":"95cfb8b3840d9c8864c7ca7b14b12df9d450e33bb8a42894e54445e2e49d0c9e","jsonata":{"publisher":"github","resource":{"type":"pull_request","id":pull_request.id},"action":"updated","timestamp":pull_request.updated_at,"raw":$},"event_field":"action"}

( The fingerprints above assume the exact skeleton algorithm; they are shown for illustration. )
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

            # Test the JSONata expression
            result = jsonata.transform(jsonata_expr, raw_payload)

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
