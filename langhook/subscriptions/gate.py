"""LLM Gate service for semantic event filtering."""

import json
import time
from typing import Any, Dict, Tuple

import structlog
from prometheus_client import Counter, Histogram

from langhook.subscriptions.llm import LLMPatternService


logger = structlog.get_logger("langhook")

# Prometheus metrics for LLM Gate
gate_evaluations_total = Counter(
    "langhook_gate_evaluations_total",
    "Total number of LLM gate evaluations",
    ["subscription_id", "decision"]
)

gate_evaluation_duration = Histogram(
    "langhook_gate_evaluation_duration_seconds",
    "Time spent evaluating events with LLM gate",
    ["subscription_id"]
)


class LLMGateService:
    """Service for evaluating events against LLM gates."""

    def __init__(self) -> None:
        """Initialize the LLM Gate service."""
        self.llm_service = LLMPatternService()
        logger.info("LLM Gate service initialized")

    async def evaluate_event(
        self,
        event_data: Dict[str, Any],
        gate_config: Dict[str, Any],
        subscription_id: int
    ) -> Tuple[bool, str]:
        """
        Evaluate whether an event should pass through the LLM gate.

        Args:
            event_data: The canonical event data to evaluate
            gate_config: Gate configuration containing enabled flag and prompt
            subscription_id: Subscription ID for metrics

        Returns:
            Tuple of (should_pass, reason)
        """
        start_time = time.time()

        try:
            if not self.llm_service.is_available():
                reason = "LLM service unavailable - failing open"
                gate_evaluations_total.labels(
                    subscription_id=subscription_id,
                    decision="pass"
                ).inc()
                logger.warning(
                    "LLM gate evaluation failed - service unavailable",
                    subscription_id=subscription_id,
                    decision="pass"
                )
                return True, reason

            # Get prompt from gate config
            prompt_template = gate_config.get("prompt", "")
            if not prompt_template:
                reason = "No prompt configured - failing open"
                gate_evaluations_total.labels(
                    subscription_id=subscription_id,
                    decision="pass"
                ).inc()
                return True, reason

            # Format the prompt with event data
            prompt = prompt_template.replace("{event_data}", json.dumps(event_data, indent=2))

            # Query the LLM
            response = await self._query_llm(prompt)
            
            # Parse response
            decision_data = self._parse_llm_response(response)
            
            reasoning = decision_data.get("reasoning", "No reasoning provided")
            should_pass = decision_data.get("decision", False)
            
            # Record metrics
            gate_evaluations_total.labels(
                subscription_id=subscription_id,
                decision="pass" if should_pass else "block"
            ).inc()
            
            duration = time.time() - start_time
            gate_evaluation_duration.labels(
                subscription_id=subscription_id
            ).observe(duration)

            logger.info(
                "LLM gate evaluation completed",
                subscription_id=subscription_id,
                decision="pass" if should_pass else "block",
                reasoning=reasoning,
                duration=duration
            )

            return should_pass, reasoning

        except Exception as e:
            duration = time.time() - start_time
            reason = f"Gate evaluation error: {str(e)} - failing open"
            
            gate_evaluations_total.labels(
                subscription_id=subscription_id,
                decision="pass"
            ).inc()
            
            logger.error(
                "LLM gate evaluation failed",
                subscription_id=subscription_id,
                error=str(e),
                decision="pass",
                duration=duration,
                exc_info=True
            )
            
            return True, reason

    async def _query_llm(self, prompt: str) -> str:
        """Query the LLM with the given prompt."""
        try:
            # Use the existing LLM service infrastructure
            if hasattr(self.llm_service, 'llm') and self.llm_service.llm:
                response = await self.llm_service.llm.ainvoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            else:
                raise RuntimeError("LLM not available")
        except Exception as e:
            logger.error("Failed to query LLM for gate evaluation", error=str(e))
            raise

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response JSON."""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            
            # Handle code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            # Try to find JSON object
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                response = response[start:end]
            
            parsed = json.loads(response)
            
            # Validate required fields
            if "decision" not in parsed:
                parsed["decision"] = False
            if "reasoning" not in parsed:
                parsed["reasoning"] = "No reasoning provided"
            
            # Normalize types
            parsed["decision"] = bool(parsed["decision"])
            parsed["reasoning"] = str(parsed["reasoning"])
            
            return parsed
            
        except Exception as e:
            logger.warning("Failed to parse LLM response", response=response, error=str(e))
            return {
                "decision": False,
                "reasoning": f"Failed to parse LLM response: {str(e)}"
            }


# Global LLM Gate service instance
llm_gate_service = LLMGateService()