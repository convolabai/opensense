"""LLM-based mapping suggestion service."""

from typing import Any, Dict, Optional

import structlog
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI

from opensense.map.config import settings

logger = structlog.get_logger()


class LLMSuggestionService:
    """Service for generating JSONata mapping suggestions using LLM."""
    
    def __init__(self) -> None:
        self.llm: Optional[ChatOpenAI] = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize the LLM client."""
        if settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name="gpt-4",
                    temperature=0.1,  # Low temperature for consistent output
                    max_tokens=1000,
                )
                logger.info("OpenAI LLM initialized")
            except Exception as e:
                logger.error(
                    "Failed to initialize OpenAI LLM",
                    error=str(e),
                    exc_info=True
                )
        else:
            logger.warning("No OpenAI API key provided, LLM suggestions disabled")
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.llm is not None
    
    async def suggest_mapping(self, source: str, raw_payload: Dict[str, Any]) -> Optional[str]:
        """
        Generate a JSONata mapping suggestion for the given raw payload.
        
        Args:
            source: Source identifier (e.g., 'github', 'stripe')
            raw_payload: Raw webhook payload to analyze
            
        Returns:
            JSONata expression string or None if generation fails
        """
        if not self.is_available():
            logger.warning("LLM service not available for mapping suggestion")
            return None
        
        try:
            # Create the prompt
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(source, raw_payload)
            
            # Generate suggestion
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.agenerate([messages])
            suggestion = response.generations[0][0].text.strip()
            
            logger.info(
                "LLM mapping suggestion generated",
                source=source,
                suggestion_length=len(suggestion)
            )
            
            return suggestion
            
        except Exception as e:
            logger.error(
                "Failed to generate LLM mapping suggestion",
                source=source,
                error=str(e),
                exc_info=True
            )
            return None
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        return """You are an API analyst specializing in webhook payload transformation.

Your task is to analyze webhook JSON payloads and create JSONata expressions that transform them into a canonical format.

The canonical format has these required fields:
- publisher: upstream slug/identifier (string)
- resource: main domain object name (string, e.g., "pull_request", "issue", "invoice")
- action: CRUD-like verb (string, e.g., "opened", "approved", "deleted", "paid")
- key: unique identifier field name (string, e.g., "number", "id", "uuid")
- value: unique identifier value (any type, e.g., 1374, "abc123")

Guidelines:
1. Analyze the payload structure to identify the main resource and action
2. Find the most appropriate unique identifier
3. Use JSONata syntax to extract and transform the data
4. Return ONLY the JSONata expression, no explanations or code blocks
5. The expression should produce a JSON object with exactly the 5 required fields

Example JSONata expression:
{
  "publisher": "github",
  "resource": "pull_request", 
  "action": action,
  "key": "number",
  "value": pull_request.number
}"""
    
    def _create_user_prompt(self, source: str, raw_payload: Dict[str, Any]) -> str:
        """Create the user prompt with the specific payload to analyze."""
        import json
        
        payload_json = json.dumps(raw_payload, indent=2)
        
        return f"""Analyze this webhook payload from "{source}" and create a JSONata expression:

Publisher: {source}

Payload:
{payload_json}

Create a JSONata expression that extracts the canonical fields from this payload."""


# Global LLM suggestion service instance
llm_service = LLMSuggestionService()