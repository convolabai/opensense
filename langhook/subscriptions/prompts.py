"""Prompt library for LLM templates."""

import os
import yaml
from typing import Dict, Any

import structlog

logger = structlog.get_logger("langhook")


class PromptLibrary:
    """Library for managing LLM prompt templates for gate, mapping, and subscription pattern generation."""

    def __init__(self, prompts_dir: str = None) -> None:
        """Initialize the prompt library."""
        self.prompts_dir = prompts_dir or os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
        self.gate_templates: dict[str, str] = {}
        self.mapping_templates: dict[str, str] = {}
        self.subscription_templates: dict[str, str] = {}
        self.load_templates()

    def load_templates(self) -> None:
        """Load prompt templates from YAML files."""
        try:
            # Load gate templates
            gate_templates_file = os.path.join(self.prompts_dir, "gate_templates.yaml")
            if os.path.exists(gate_templates_file):
                with open(gate_templates_file, encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.gate_templates = data.get("templates", {})

            # Load mapping templates
            mapping_templates_file = os.path.join(self.prompts_dir, "mapping_templates.yaml")
            if os.path.exists(mapping_templates_file):
                with open(mapping_templates_file, encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.mapping_templates = data.get("templates", {})

            # Load subscription pattern templates
            subscription_templates_file = os.path.join(self.prompts_dir, "subscription_templates.yaml")
            if os.path.exists(subscription_templates_file):
                with open(subscription_templates_file, encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.subscription_templates = data.get("templates", {})

            template_counts = len(self.gate_templates) + len(self.mapping_templates) + len(self.subscription_templates)
            logger.info(f"Loaded {template_counts} prompt templates",
                       gate=len(self.gate_templates),
                       mapping=len(self.mapping_templates),
                       subscription=len(self.subscription_templates),
                       prompts_dir=self.prompts_dir)

            # Load defaults for any missing template types
            if not self.gate_templates:
                self._load_default_gate_templates()
            if not self.mapping_templates:
                self._load_default_mapping_templates()
            if not self.subscription_templates:
                self._load_default_subscription_templates()

        except Exception as e:
            logger.error("Failed to load prompt templates", error=str(e), prompts_dir=self.prompts_dir)
            self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load all default prompt templates."""
        self._load_default_gate_templates()
        self._load_default_mapping_templates()
        self._load_default_subscription_templates()

    def _load_default_gate_templates(self) -> None:
        """Load default gate prompt templates."""
        self.gate_templates = {
            "default": """You are an intelligent event filter for a subscription monitoring system.

The user has subscribed to: "{description}"

Your task is to evaluate whether the following event genuinely matches the user's intent.

Return ONLY a JSON object with this exact format:
{{
    "decision": true or false
}}

Event to evaluate:
{event_data}

Consider:
- Does this event truly match what the user wants to be notified about?
- Would a reasonable person consider this relevant to their subscription?

Be selective - only pass events that clearly match the user's specific intent.""",

            "strict": """You are a strict event filter that only allows events that clearly match the subscription.

The user wants to be notified about: "{description}"

Your job is to be VERY selective and only allow events that genuinely match the user's criteria.

Return ONLY a JSON object:
{{
    "decision": true or false
}}

Event to evaluate:
{event_data}

Only return true if:
- The event clearly matches the user's specific criteria
- The event is exactly what the user requested
- There is no ambiguity about the match

Be strict - when in doubt, block the event.""",

            "precise": """You are filtering events to match precise user criteria.

Subscription intent: "{description}"

Evaluate if this event matches the user's specific requirements exactly as stated.

Return ONLY a JSON object:
{{
    "decision": true or false
}}

Event to evaluate:
{event_data}

Allow events that:
- Match the exact criteria specified by the user
- Fulfill the specific conditions requested
- Are exactly what the user described in their subscription

Only pass events that precisely match the user's stated requirements.""",

            "security_focused": """You are a security-focused event filter.

The user is monitoring: "{description}"

Focus on security implications and potential threats.

Return ONLY a JSON object:
{{
    "decision": true or false
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

Evaluate based on the user's specific security criteria.""",

            "exact_match": """You are filtering events for exact matching to user criteria.

The user monitors: "{description}"

ONLY allow events that exactly match the user's specific criteria.

Return ONLY a JSON object:
{{
    "decision": true or false
}}

Event to evaluate:
{event_data}

Allow ONLY if the event matches the user's exact specification including:
- Specific source, type, or content mentioned
- Exact conditions or filters specified
- Precise criteria outlined in the description

Block anything that doesn't precisely match the user's stated requirements."""
        }

    def _load_default_mapping_templates(self) -> None:
        """Load default mapping prompt templates."""
        self.mapping_templates = {
            "default": """You are LangHook Webhook → JSONata Mapper.

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
	•	updated → "approved", "merged", "edited", "closed"
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

Example 3 - GitHub PR Closed

{
  "jsonata": "{ \"publisher\": \"github\", \"resource\": { \"type\": \"pull_request\", \"id\": pull_request.id }, \"action\": \"updated\", \"timestamp\": pull_request.closed_at }",
  "event_field": "action"
}


⸻

Example 4 - Stripe Payment Succeeded

{
  "jsonata": "{ \"publisher\": \"stripe\", \"resource\": { \"type\": \"payment\", \"id\": data.object.id }, \"action\": \"updated\", \"timestamp\": $formatInteger(created * 1000, \"[Y0001]-[M01]-[D01]T[H01]:[m01]:[s01]Z\") }",
  "event_field": "type"
}


⸻

Example 5 - Slack Message Posted

{
  "jsonata": "{ \"publisher\": \"slack\", \"resource\": { \"type\": \"message\", \"id\": event.ts }, \"action\": \"created\", \"timestamp\": $fromMillis($number(event.ts) * 1000) }",
  "event_field": "event.type"
}


⸻

Example 6 - Salesforce Contact Updated

{
  "jsonata": "{ \"publisher\": \"salesforce\", \"resource\": { \"type\": \"contact\", \"id\": sobject.Id }, \"action\": \"updated\", \"timestamp\": sobject.LastModifiedDate }",
  "event_field": "eventType"
}

"""
        }

    def _load_default_subscription_templates(self) -> None:
        """Load default subscription pattern generation templates."""
        self.subscription_templates = {
            "default": """You are a NATS JetStream filter pattern generator for LangHook.

Your task: convert a natural-language event description into a valid NATS subject pattern using this schema:

Pattern: langhook.events.<publisher>.<resource_type>.<resource_id>.<action>

Wildcards: `*` = one token, `>` = one or more tokens at end

Allowed:

{schema_info}


Rules:
1. Think like a REST API: map natural verbs to `created`, `read`, or `updated`.
   - e.g., "opened" = created, "seen" = read, "merged" = updated
2. Only use exact values from allowed schema
3. Use `*` for missing IDs
4. **CRITICAL**: Resource IDs are atomic identifiers (numbers, UUIDs, codes). If user mentions names (repository names, user names, etc.), or ID of something that is not a resource ID, use `*` for the ID and let LLM Gate handle name filtering
5. If no valid mapping, reply: `"ERROR: No suitable schema found"`

Examples:
- "GitHub PR approved" → "langhook.events.github.pull_request.*.updated"
- "Stripe payment over $100" → "langhook.events.stripe.payment.*.updated"
- "Any Slack message" → "langhook.events.slack.message.*.*"

{gate_instructions}"""
        }

    def get_template(self, template_name: str, template_type: str = "gate") -> str:
        """Get a prompt template by name and type."""
        if template_type == "gate":
            return self.gate_templates.get(template_name, self.gate_templates.get("default", ""))
        elif template_type == "mapping":
            return self.mapping_templates.get(template_name, self.mapping_templates.get("default", ""))
        elif template_type == "subscription":
            return self.subscription_templates.get(template_name, self.subscription_templates.get("default", ""))
        else:
            raise ValueError(f"Unknown template type: {template_type}")

    def get_gate_template(self, template_name: str) -> str:
        """Get a gate prompt template by name (backward compatibility)."""
        return self.get_template(template_name, "gate")

    def get_mapping_template(self, template_name: str = "default") -> str:
        """Get a mapping prompt template by name."""
        return self.get_template(template_name, "mapping")

    def get_subscription_template(self, template_name: str = "default") -> str:
        """Get a subscription pattern generation template by name."""
        return self.get_template(template_name, "subscription")

    def list_templates(self, template_type: str = None) -> Dict[str, Any]:
        """List all available templates, optionally filtered by type."""
        if template_type == "gate":
            return {name: template[:100] + "..." for name, template in self.gate_templates.items()}
        elif template_type == "mapping":
            return {name: template[:100] + "..." for name, template in self.mapping_templates.items()}
        elif template_type == "subscription":
            return {name: template[:100] + "..." for name, template in self.subscription_templates.items()}
        else:
            # Return all templates grouped by type
            return {
                "gate": {name: template[:100] + "..." for name, template in self.gate_templates.items()},
                "mapping": {name: template[:100] + "..." for name, template in self.mapping_templates.items()},
                "subscription": {name: template[:100] + "..." for name, template in self.subscription_templates.items()}
            }

    def list_gate_templates(self) -> Dict[str, str]:
        """List gate templates (backward compatibility)."""
        return {name: template[:100] + "..." for name, template in self.gate_templates.items()}

    def set_template(self, template_name: str, template_content: str, template_type: str) -> None:
        """Set a prompt template."""
        if template_type == "gate":
            self.gate_templates[template_name] = template_content
        elif template_type == "mapping":
            self.mapping_templates[template_name] = template_content
        elif template_type == "subscription":
            self.subscription_templates[template_name] = template_content
        else:
            raise ValueError(f"Unknown template type: {template_type}")

    def delete_template(self, template_name: str, template_type: str) -> bool:
        """Delete a prompt template. Returns True if deleted, False if not found."""
        if template_type == "gate":
            return self.gate_templates.pop(template_name, None) is not None
        elif template_type == "mapping":
            return self.mapping_templates.pop(template_name, None) is not None
        elif template_type == "subscription":
            return self.subscription_templates.pop(template_name, None) is not None
        else:
            raise ValueError(f"Unknown template type: {template_type}")

    def reload_templates(self) -> None:
        """Reload templates from disk."""
        self.load_templates()

    # Backward compatibility properties
    @property
    def templates(self) -> Dict[str, str]:
        """Get gate templates for backward compatibility."""
        return self.gate_templates


# Global prompt library instance
prompt_library = PromptLibrary()
