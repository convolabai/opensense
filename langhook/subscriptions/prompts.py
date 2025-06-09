"""Prompt library for LLM Gate templates."""

import os
import yaml
from typing import Dict, Any

import structlog

logger = structlog.get_logger("langhook")


class PromptLibrary:
    """Library for managing LLM gate prompt templates."""

    def __init__(self, prompts_dir: str = None) -> None:
        """Initialize the prompt library."""
        self.prompts_dir = prompts_dir or os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
        self.templates: Dict[str, str] = {}
        self.load_templates()

    def load_templates(self) -> None:
        """Load prompt templates from YAML files."""
        try:
            templates_file = os.path.join(self.prompts_dir, "gate_templates.yaml")
            if os.path.exists(templates_file):
                with open(templates_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.templates = data.get("templates", {})
                logger.info(f"Loaded {len(self.templates)} prompt templates", prompts_dir=self.prompts_dir)
            else:
                logger.warning("No prompt templates file found, using defaults", templates_file=templates_file)
                self._load_default_templates()
        except Exception as e:
            logger.error("Failed to load prompt templates", error=str(e), prompts_dir=self.prompts_dir)
            self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default prompt templates."""
        self.templates = {
            "default": """You are an intelligent event filter for a subscription monitoring system.

The user has subscribed to: "{description}"

Your task is to evaluate whether the following event genuinely matches the user's intent.

Return ONLY a JSON object with this exact format:
{{
    "decision": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}

Event to evaluate:
{event_data}

Consider:
- Does this event truly match what the user wants to be notified about?
- Is this event important enough to warrant an alert?
- Would a reasonable person consider this relevant to their subscription?

Be selective - only pass events that clearly match the user's intent.""",

            "important_only": """You are a strict event filter that only allows truly important events.

The user wants to be notified about: "{description}"

Your job is to be VERY selective and only allow events that are genuinely important or urgent.

Return ONLY a JSON object:
{{
    "decision": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}

Event to evaluate:
{event_data}

Only return true if:
- The event is urgent or time-sensitive
- The event indicates a problem or critical change
- The event requires immediate attention
- The event is clearly what the user specifically wants

Be strict - when in doubt, block the event.""",

            "high_value": """You are filtering events for a busy professional who only wants high-value notifications.

Subscription intent: "{description}"

Evaluate if this event provides genuine business value or actionable information.

Return ONLY a JSON object:
{{
    "decision": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}

Event to evaluate:
{event_data}

Allow events that:
- Require decision-making or action
- Indicate significant business impact
- Represent meaningful progress or completion
- Signal problems that need attention

Block routine/informational events unless specifically requested.""",

            "security_focused": """You are a security-focused event filter.

The user is monitoring: "{description}"

Focus on security implications and potential threats.

Return ONLY a JSON object:
{{
    "decision": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}

Event to evaluate:
{event_data}

Prioritize events involving:
- Security vulnerabilities or incidents
- Authentication or access changes
- Permission modifications
- Failed login attempts
- Suspicious activity
- Security-related configuration changes

Be vigilant about potential security implications."""
        }

    def get_template(self, template_name: str) -> str:
        """Get a prompt template by name."""
        return self.templates.get(template_name, self.templates.get("default", ""))

    def list_templates(self) -> Dict[str, str]:
        """List all available templates."""
        return {name: template[:100] + "..." for name, template in self.templates.items()}

    def reload_templates(self) -> None:
        """Reload templates from disk."""
        self.load_templates()


# Global prompt library instance
prompt_library = PromptLibrary()