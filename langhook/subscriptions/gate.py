"""LLM Gate service for semantic event filtering."""

import json
import time
from typing import Any, Dict, Tuple

import structlog
from prometheus_client import Counter, Histogram, Summary

from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.llm import LLMPatternService
from langhook.subscriptions.prompts import prompt_library
from langhook.subscriptions.budget import budget_monitor


logger = structlog.get_logger("langhook")

# Prometheus metrics for LLM Gate
gate_evaluations_total = Counter(
    "langhook_gate_evaluations_total",
    "Total number of LLM gate evaluations",
    ["subscription_id", "decision", "model", "failover_reason"]
)

gate_evaluation_duration = Histogram(
    "langhook_gate_evaluation_duration_seconds",
    "Time spent evaluating events with LLM gate",
    ["subscription_id", "model"]
)

gate_llm_cost_usd = Summary(
    "langhook_gate_llm_cost_usd_total",
    "Total LLM cost in USD for gate evaluations",
    ["subscription_id", "model"]
)


class LLMGateService:
    """Service for evaluating events against LLM gates."""

    def __init__(self) -> None:
        """Initialize the LLM Gate service."""
        self.llm_service = LLMPatternService()
        logger.info("LLM Gate service initialized")

    def _get_default_prompt(self, description: str) -> str:
        """Get default prompt template for gate evaluation."""
        return prompt_library.get_template("default").format(
            description=description,
            event_data="{event_data}"
        )

    async def evaluate_event(
        self,
        event_data: Dict[str, Any],
        gate_config: Dict[str, Any],
        subscription_description: str,
        subscription_id: int
    ) -> Tuple[bool, str, float]:
        """
        Evaluate whether an event should pass through the LLM gate.

        Args:
            event_data: The canonical event data to evaluate
            gate_config: Gate configuration containing model, prompt, threshold, etc.
            subscription_description: Natural language subscription description
            subscription_id: Subscription ID for metrics

        Returns:
            Tuple of (should_pass, reason, confidence)
        """
        start_time = time.time()
        model = gate_config.get("model", "gpt-4o-mini")
        threshold = gate_config.get("threshold", 0.8)
        failover_policy = gate_config.get("failover_policy", "fail_open")

        try:
            if not self.llm_service.is_available():
                reason = "LLM service unavailable"
                decision = failover_policy == "fail_open"
                gate_evaluations_total.labels(
                    subscription_id=subscription_id,
                    decision="pass" if decision else "block",
                    model=model,
                    failover_reason="llm_unavailable"
                ).inc()
                logger.warning(
                    "LLM gate evaluation failed - service unavailable",
                    subscription_id=subscription_id,
                    failover_policy=failover_policy,
                    decision="pass" if decision else "block"
                )
                return decision, reason, 0.0

            # Get prompt template
            prompt_template = gate_config.get("prompt", "")
            if not prompt_template:
                prompt_template = self._get_default_prompt(subscription_description)
            else:
                # Check if it's a template name or custom prompt
                if prompt_template in prompt_library.templates:
                    prompt_template = prompt_library.get_template(prompt_template)
                
                # Format template with description if it contains placeholders
                if "{description}" in prompt_template:
                    prompt_template = prompt_template.format(
                        description=subscription_description,
                        event_data="{event_data}"
                    )

            # Format the prompt with event data
            prompt = prompt_template.replace("{event_data}", json.dumps(event_data, indent=2))

            # Query the LLM
            response = await self._query_llm(prompt, model)
            
            # Parse response
            decision_data = self._parse_llm_response(response)
            
            confidence = decision_data.get("confidence", 0.0)
            reasoning = decision_data.get("reasoning", "No reasoning provided")
            raw_decision = decision_data.get("decision", False)
            
            # Apply threshold
            should_pass = raw_decision and confidence >= threshold
            
            # Record metrics
            gate_evaluations_total.labels(
                subscription_id=subscription_id,
                decision="pass" if should_pass else "block",
                model=model,
                failover_reason=""
            ).inc()
            
            duration = time.time() - start_time
            gate_evaluation_duration.labels(
                subscription_id=subscription_id,
                model=model
            ).observe(duration)

            # Estimate cost (rough approximation)
            estimated_cost = self._estimate_cost(prompt, response, model)
            gate_llm_cost_usd.labels(
                subscription_id=subscription_id,
                model=model
            ).observe(estimated_cost)

            # Record cost in budget monitor
            budget_monitor.record_cost(estimated_cost, subscription_id)

            logger.info(
                "LLM gate evaluation completed",
                subscription_id=subscription_id,
                model=model,
                decision="pass" if should_pass else "block",
                confidence=confidence,
                threshold=threshold,
                reasoning=reasoning,
                duration=duration,
                estimated_cost_usd=estimated_cost
            )

            return should_pass, reasoning, confidence

        except Exception as e:
            duration = time.time() - start_time
            reason = f"Gate evaluation error: {str(e)}"
            decision = failover_policy == "fail_open"
            
            gate_evaluations_total.labels(
                subscription_id=subscription_id,
                decision="pass" if decision else "block",
                model=model,
                failover_reason="evaluation_error"
            ).inc()
            
            logger.error(
                "LLM gate evaluation failed",
                subscription_id=subscription_id,
                model=model,
                error=str(e),
                failover_policy=failover_policy,
                decision="pass" if decision else "block",
                duration=duration,
                exc_info=True
            )
            
            return decision, reason, 0.0

    async def _query_llm(self, prompt: str, model: str) -> str:
        """Query the LLM with the given prompt."""
        try:
            # Use the existing LLM service infrastructure
            if hasattr(self.llm_service, 'llm') and self.llm_service.llm:
                response = await self.llm_service.llm.ainvoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            else:
                raise RuntimeError("LLM not available")
        except Exception as e:
            logger.error("Failed to query LLM for gate evaluation", error=str(e), model=model)
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
            if "confidence" not in parsed:
                parsed["confidence"] = 0.0
            if "reasoning" not in parsed:
                parsed["reasoning"] = "No reasoning provided"
            
            # Normalize types
            parsed["decision"] = bool(parsed["decision"])
            parsed["confidence"] = float(parsed["confidence"])
            parsed["reasoning"] = str(parsed["reasoning"])
            
            return parsed
            
        except Exception as e:
            logger.warning("Failed to parse LLM response", response=response, error=str(e))
            return {
                "decision": False,
                "confidence": 0.0,
                "reasoning": f"Failed to parse LLM response: {str(e)}"
            }

    def _estimate_cost(self, prompt: str, response: str, model: str) -> float:
        """Estimate the cost of the LLM query in USD."""
        # Rough token estimation (4 chars per token)
        prompt_tokens = len(prompt) / 4
        response_tokens = len(response) / 4
        
        # Cost per 1K tokens (rough estimates as of 2024)
        costs = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        }
        
        # Default to gpt-4o-mini if model not found
        model_costs = costs.get(model, costs["gpt-4o-mini"])
        
        input_cost = (prompt_tokens / 1000) * model_costs["input"]
        output_cost = (response_tokens / 1000) * model_costs["output"]
        
        return input_cost + output_cost


# Global LLM Gate service instance
llm_gate_service = LLMGateService()