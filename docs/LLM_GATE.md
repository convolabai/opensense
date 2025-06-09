# LLM Gate - Semantic Event Filtering

LLM Gate is a semantic event filtering system that uses Large Language Models to evaluate whether events should be delivered to subscribers based on their intent, not just pattern matching.

## Overview

Traditional event routing relies on pattern matching against subjects like `langhook.events.github.pull_request.*.*`. While this works for exact filtering, it can't understand the semantic meaning of events. LLM Gate adds an intelligent layer that evaluates whether an event truly matches what the user wants to be notified about.

## Features

- **Semantic Filtering**: Uses LLMs to understand event content and user intent
- **Configurable Models**: Support for OpenAI GPT models, Anthropic Claude, Google Gemini, and local LLMs
- **Prompt Templates**: Pre-built templates for common filtering needs
- **Failover Policies**: Configurable behavior when LLM is unavailable
- **Budget Monitoring**: Track and alert on LLM usage costs
- **Prometheus Metrics**: Comprehensive observability and monitoring

## Configuration

### Subscription Gate Configuration

```json
{
  "description": "Important GitHub pull requests",
  "channel_type": "webhook",
  "channel_config": {"url": "https://example.com/webhook"},
  "gate": {
    "enabled": true,
    "model": "gpt-4o-mini",
    "prompt": "important_only",
    "threshold": 0.8,
    "audit": true,
    "failover_policy": "fail_open"
  }
}
```

### Gate Configuration Fields

- **enabled**: Whether the LLM gate is active
- **model**: LLM model to use (`gpt-4o-mini`, `gpt-4o`, `gpt-4`, `claude-3-haiku`, etc.)
- **prompt**: Prompt template name or custom prompt text
- **threshold**: Confidence threshold (0.0-1.0) for allowing events
- **audit**: Whether to log gate decisions for analysis
- **failover_policy**: Behavior when LLM unavailable (`fail_open` or `fail_closed`)

### Environment Variables

```bash
# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=500

# Budget Settings
GATE_DAILY_COST_LIMIT_USD=10.0
GATE_COST_ALERT_THRESHOLD=0.8
```

## Prompt Templates

### Built-in Templates

1. **default**: Balanced filtering for general use cases
2. **important_only**: Strict filtering for high-priority events only  
3. **high_value**: Business-focused filtering for actionable events
4. **security_focused**: Specialized for security-related events
5. **critical_only**: Emergency-level filtering for outages and failures

### Custom Prompts

You can use custom prompts by providing the full prompt text instead of a template name:

```json
{
  "prompt": "You are filtering events for a DevOps team. Only allow events that indicate:\n- Production outages\n- Security incidents\n- Failed deployments\n\nReturn JSON: {\"decision\": true/false, \"confidence\": 0.0-1.0, \"reasoning\": \"explanation\"}"
}
```

### Template Variables

Prompts support the following variables:
- `{description}`: The subscription description
- `{event_data}`: The full event data as JSON

## API Endpoints

### Gate Management

```bash
# Get budget status
GET /subscriptions/gate/budget

# Get available templates  
GET /subscriptions/gate/templates

# Reload templates from disk
POST /subscriptions/gate/templates/reload
```

### Subscription with Gate

```bash
# Create subscription with gate
POST /subscriptions/
{
  "description": "Critical production alerts",
  "gate": {
    "enabled": true,
    "prompt": "critical_only",
    "threshold": 0.9
  }
}

# Update gate configuration
PUT /subscriptions/{id}
{
  "gate": {
    "enabled": false
  }
}
```

## Monitoring

### Prometheus Metrics

- `langhook_gate_evaluations_total`: Total gate evaluations by decision and model
- `langhook_gate_evaluation_duration_seconds`: Time spent on LLM evaluations
- `langhook_gate_llm_cost_usd_total`: Total LLM costs in USD
- `langhook_gate_daily_cost_usd`: Daily cost by date
- `langhook_gate_budget_alerts_total`: Number of budget alerts sent

### Budget Alerts

The system monitors daily LLM spending and sends alerts when:
- 80% of daily limit is reached (configurable)
- Daily limit is exceeded

### Grafana Dashboard

Key metrics to monitor:
- Gate pass/block rates
- Average evaluation latency
- Daily/monthly costs
- Model usage distribution
- Subscription-level gate activity

## Usage Examples

### Example 1: GitHub Security Alerts

```json
{
  "description": "High-priority GitHub security vulnerabilities",
  "pattern": "langhook.events.github.security.*.*",
  "gate": {
    "enabled": true,
    "model": "gpt-4o-mini",
    "prompt": "security_focused",
    "threshold": 0.8,
    "failover_policy": "fail_closed"
  }
}
```

**Event**: GitHub security advisory for a critical vulnerability
**Gate Decision**: PASS (confidence: 0.95)
**Reasoning**: "Critical security vulnerability requires immediate attention"

### Example 2: Important Email Filtering

```json
{
  "description": "Important emails from customers or team",
  "pattern": "langhook.events.email.*.*.*",
  "gate": {
    "enabled": true,
    "model": "gpt-4o-mini", 
    "prompt": "high_value",
    "threshold": 0.7,
    "failover_policy": "fail_open"
  }
}
```

**Event**: Newsletter subscription confirmation
**Gate Decision**: BLOCK (confidence: 0.2)
**Reasoning**: "Automated marketing email, not important for user"

### Example 3: Production Incident Alerts

```json
{
  "description": "Production outages and critical system failures",
  "pattern": "langhook.events.monitoring.*.*.*",
  "gate": {
    "enabled": true,
    "model": "gpt-4o",
    "prompt": "critical_only",
    "threshold": 0.9,
    "failover_policy": "fail_closed"
  }
}
```

**Event**: CPU usage at 85% (warning threshold)
**Gate Decision**: BLOCK (confidence: 0.3)
**Reasoning**: "High CPU usage but not critical failure level"

**Event**: Service completely down, 500 errors
**Gate Decision**: PASS (confidence: 0.98)
**Reasoning**: "Complete service outage requires immediate response"

## Best Practices

### Cost Optimization

1. **Use efficient models**: `gpt-4o-mini` for most use cases, reserve `gpt-4o` for complex reasoning
2. **Set appropriate thresholds**: Higher thresholds reduce false positives and costs
3. **Monitor spending**: Set up budget alerts and review usage regularly
4. **Cache decisions**: Consider caching for repeated similar events

### Prompt Engineering

1. **Be specific**: Clear criteria lead to better decisions
2. **Include examples**: Show the model what you want
3. **Set context**: Explain the user's role and priorities
4. **Request reasoning**: Always ask for explanation of decisions

### Reliability

1. **Use fail_open carefully**: Only for non-critical notifications
2. **Test failover**: Verify behavior when LLM is unavailable
3. **Monitor metrics**: Watch for anomalies in pass/block rates
4. **Audit decisions**: Review gate logs to improve prompts

## Troubleshooting

### High Costs

- Review model selection (use smaller models when possible)
- Check for prompt inefficiencies
- Verify subscription isn't matching too many events
- Adjust thresholds to reduce evaluations

### Poor Filtering Quality

- Review and improve prompt templates
- Analyze gate decision logs
- Adjust confidence thresholds
- Consider using more capable models for complex cases

### Reliability Issues

- Check LLM service availability
- Review failover policy settings
- Monitor evaluation latency
- Verify API key and credentials

## Development

### Adding New Templates

1. Add template to `/prompts/gate_templates.yaml`
2. Reload templates: `POST /subscriptions/gate/templates/reload`
3. Test with representative events
4. Update documentation

### Custom Integrations

The LLM Gate service can be extended with:
- Custom prompt loading from external sources
- Integration with user preference systems
- Advanced caching and optimization
- Custom model providers

## Security Considerations

- API keys are sensitive - use proper secret management
- Event data is sent to LLM providers - review privacy implications
- Gate decisions are logged - ensure compliance with data retention policies
- Budget limits prevent runaway costs but monitor usage actively