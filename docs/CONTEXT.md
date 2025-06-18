# PRODUCT.md · **LangHook**

**Version:** 0.1  
**Date:**  3 June 2025  
**Owner:** Product / Platform Team

---

## 1 · Vision ✦  
> **“Make any event from anywhere instantly understandable and actionable by anyone.”**

LangHook turns the chaotic world of bespoke web-hooks into a **single, intelligible event language** that both humans and machines can subscribe to in plain English.  
We want an engineer, product manager, or support rep to describe *what they care about* (“Notify me when PR 1374 is approved”) and get the right signal—without ever touching JSON, queues, or custom code.

---

## 2 · Problem We Solve  
| Current Pain | Why it Hurts |
|--------------|--------------|
| Every SaaS has its **own payload schema** | Engineers write/maintain brittle glue code for each source. |
| Business users can’t write JSONPath/SQL | They ping devs for every new alert, slowing everyone down. |
| Proprietary iPaaS tools lock customers in | • High pricing tiers • No self-host • Limited extensibility. |

---

## 3 · Value Proposition  
| Stakeholder | Benefit |
|-------------|---------|
| **Developers** | One intake URL, canonical JSON, NATS-compatible bus → **⚡ 10× faster** integrations. |
| **Ops / SRE** | Single place to monitor, replay, & audit all external events. |
| **Product / Support** | Create or disable alerts with a *sentence*—no ticket to Engineering. |
| **Enterprises / Regulated** | MIT-licensed, self-host or cloud; run inside existing compliance boundaries. |

---

## 4 · Product Principles  
1. **Open First** Source-available (Apache-2.0), CloudEvents standard, pluggable everything.  
2. **Human-Centric** Natural-language comes first; config files second.  
3. **Observable by Default** Every event traceable end-to-end with metrics & structured logs.  
4. **Batteries Included, Swappable** We ship a happy-path stack (Svix → Redpanda → FastAPI), but any layer can be replaced.  
5. **Security Is Foundational** HMAC-verified ingest, RBAC on subscriptions, encrypted secrets—no shortcuts.

---

## 5 · Core Concepts  
| Term | Description |
|------|------------|
| **Canonical Event** | CloudEvents envelope + standardized structure `{publisher, resource, action, timestamp, payload}` where `resource` contains `{type: string, id: string|number}`. |
| **Schema Registry** | Dynamic database that automatically collects and tracks all unique combinations of `publisher`, `resource.type`, and `action` from processed canonical events, accessible via `/schema` API with management capabilities (deletion at publisher, resource type, and action levels). |
| **Subscription** | Natural-language sentence + LLM-generated **NATS filter pattern** + delivery channels. |
| **Channel** | Output target (Slack, e-mail, webhook, etc.). |
| **Mapping** | JSONata or LLM-generated rule that converts a raw payload into a canonical event. |
| **Ingest Mapping** | Cached fingerprint-based mapping with payload structure and optional event field expressions for enhanced fingerprinting, enabling fast transformation and disambiguation of events with similar structures but different actions. |

---

## 6 · Primary Use Cases (MVP-1)  
1. **GitHub PR approval alert** – Product owner gets Slack DM when a specific PR is approved, with LLM grounded in actual GitHub event schemas.  
2. **Stripe high-value refund ping** – Finance lead notified when refund > $500, with subscription validation against collected Stripe schemas.  
3. **Jira ticket transitioned** – Support channel post when issue moves to “Done”.  
4. **Custom app heartbeat** – Ops receives webhook if internal service reports error rate > 5 %.  

---

## 7 · Competitive Landscape  
| Product | Gaps We Fill |
|---------|--------------|
| Zapier / IFTTT | Closed-source, per-task fees, limited self-host. |
| Segment, Merge.dev | Domain-specific (analytics / HRIS) only. |
| Trigger.dev | Code-first—still requires writing TypeScript for every mapping + rule. |
| Microsoft Power Automate | M365-locked, pricey at scale, Windows-only connectors. |

LangHook is **domain-agnostic**, **LLM-assisted**, and **fully open**.

---

## 8 · Out-of-Scope (MVP-1)  
* Visual flow-builder UI  
* Built-in billing & multi-tenant invoicing  
* Guaranteed exactly-once delivery (at-least-once is fine)  
* Edge-optimized ingestion—MVP runs in a single region

---

## 9 · Success Metrics  
| Metric | Target (after GA) |
|--------|-------------------|
| **Time-to-first alert** | < 10 minutes from `git clone` to Slack DM |
| **Events processed/sec (single node)** | ≥ 2 000 e/s with p95 latency ≤ 3 s |
| **Mapping coverage** | ≥ 90 % canonical-field accuracy on top-10 webhook sources |
| **GitHub ⭐ in first 6 months** | 1 000+ |
| **Community PR merge time** | Median < 3 days |

---

## 10 · Roadmap Slice  
| Quarter | Theme | Highlights |
|---------|-------|------------|
| **Q3 2025** | MVP-1 GA | Core ingest, NL subscriptions, Slack & webhook channels, Docker Compose |
| **Q4 2025** | **Trust & Extensibility** | Multi-tenant RBAC, UI dashboard, plugin SDK, Postgres → BYO DB |
| **Q1 2026** | **Scale & Ecosystem** | Exactly-once (Idempotence), S3 backup, marketplace for community mappings |

*(Roadmap is directional and subject to change.)*

---

## 10.5 · Schema Registry Architecture

| Component | Purpose |
|-----------|---------|
| **Auto-Discovery** | Canonical events automatically register their `publisher`, `resource.type`, and `action` combinations into PostgreSQL |
| **Schema API** | `/schema/` endpoint exposes structured JSON of all collected event schemas for LLM consumption |
| **Schema Management** | DELETE endpoints at `/schema/publishers/{publisher}`, `/schema/publishers/{publisher}/resource-types/{resource_type}`, and `/schema/publishers/{publisher}/resource-types/{resource_type}/actions/{action}` for selective schema cleanup |
| **LLM Grounding** | Natural language subscription generation uses real schema data instead of hardcoded examples |
| **Error Prevention** | Invalid subscription requests return helpful errors directing users to check `/schema` endpoint |

**Flow Integration**: Schema registration happens after successful canonical event creation but before metrics recording, ensuring data consistency without blocking event processing.

**Management Operations**:
- Delete entire publishers and all associated schemas
- Delete specific resource types under a publisher  
- Delete individual actions for publisher/resource type combinations
- All operations include confirmation dialogs in frontend interface
- Automatic schema refresh after successful deletions

---

## 11 · Glossary  
| Acronym | Definition |
|---------|------------|
| **NATS** | Neural Autonomic Transport System — messaging system for event streaming. |
| **DLQ** | Dead-Letter Queue (for failed/malformed events). |
| **LLM** | Large Language Model (e.g., GPT-4o, Llama-3). |

---

> **Remember:** Every epic, story, or pull-request should ladder back to the vision of making events *understandable* and *actionable*—without bespoke code or vendor lock-in.


# LangHook Ingest Gateway

A lightweight FastAPI-based webhook receiver that replaces Svix with a secure, catch-all HTTPS endpoint for webhook ingestion.

## Features

- **Single Endpoint**: Accepts all webhooks at `/ingest/{source}`
- **HMAC Verification**: Supports GitHub and Stripe signature verification
- **Rate Limiting**: IP-based rate limiting (200 requests/minute default)
- **Body Size Limits**: Configurable request size limits (1 MiB default)
- **Dead Letter Queue**: Malformed JSON sent to DLQ for inspection
- **NATS Integration**: Events forwarded to NATS JetStream
- **Structured Logging**: JSON logs with correlation IDs
- **Health Checks**: `/health/` endpoint for monitoring

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Clone and setup
git clone <repository>
cd langhook

# Copy environment template
cp .env.ingest.example .env.ingest

# Edit secrets (optional for testing)
# vim .env.ingest

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health/

# Test webhook ingestion
curl -X POST http://localhost:8000/ingest/github \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook", "action": "opened"}'
```

### 2. Local Development

```bash
# Install dependencies
pip install -e .

# Start Redis and NATS
docker-compose up redis nats -d

# Set environment variables
export NATS_URL=nats://localhost:4222
export REDIS_URL=redis://localhost:6379

# Run the service
langhook-ingest
```

## Configuration

Create `.env.ingest` with your webhook secrets:

```bash
# HMAC secrets for webhook verification
GITHUB_SECRET=your_github_webhook_secret_here
STRIPE_SECRET=your_stripe_webhook_secret_here

# Optional overrides
MAX_BODY_BYTES=1048576
RATE_LIMIT=200/minute
NATS_URL=nats://nats:4222
REDIS_URL=redis://redis:6379
```

## API Endpoints

### Health Check
```
GET /health/
```
Response: `{"status": "up"}`

### Webhook Ingestion
```
POST /ingest/{source}
Content-Type: application/json

{
  "your": "webhook",
  "payload": "here"
}
```

**Path Parameters:**
- `source`: Source identifier (e.g., `github`, `stripe`, `jira`)

**Headers:**
- `Content-Type: application/json` (required)
- `X-Hub-Signature-256`: GitHub HMAC signature (if configured)
- `Stripe-Signature`: Stripe HMAC signature (if configured)

**Response:**
- `202 Accepted`: Event ingested successfully
- `400 Bad Request`: Invalid JSON payload
- `401 Unauthorized`: Invalid HMAC signature
- `413 Request Entity Too Large`: Body exceeds size limit
- `429 Too Many Requests`: Rate limit exceeded

## Event Format

Events are forwarded to NATS with this structure:

```json
{
  "id": "8b0272bb-e2e5-4568-a2e0-ab123c789f90",
  "timestamp": "2025-06-03T15:12:08.123Z",
  "source": "github",
  "signature_valid": true,
  "headers": {
    "user-agent": "GitHub-Hookshot/12345",
    "x-hub-signature-256": "sha256=..."
  },
  "payload": {
    "action": "opened",
    "pull_request": {
      "number": 1374
    }
  }
}
```

## Dead Letter Queue

View malformed events that couldn't be processed:

```bash
# Show last 10 DLQ messages
langhook-dlq-show

# Show last 50 DLQ messages
langhook-dlq-show --count 50

# Custom NATS URL
langhook-dlq-show --nats-url nats://localhost:4222
```

## HMAC Signature Verification

### GitHub
Uses `X-Hub-Signature-256` header with SHA-256 HMAC.

### Stripe  
Uses `Stripe-Signature` header with timestamp and SHA-256 HMAC.

### Custom Sources
Uses `X-Webhook-Signature` header. Configure secret as `{SOURCE}_SECRET` environment variable.

## Rate Limiting

Per-IP rate limiting using Redis sliding window:
- Default: 200 requests/minute
- Configurable via `RATE_LIMIT` environment variable
- Format: `{requests}/{window}` (e.g., `100/second`, `500/hour`)

## Monitoring

### Logs
Structured JSON logs to stdout:
```json
{
  "timestamp": "2025-06-03T15:12:08.123Z",
  "level": "info",
  "event": "Event ingested successfully",
  "source": "github",
  "request_id": "8b0272bb-e2e5-4568-a2e0-ab123c789f90",
  "signature_valid": true
}
```

### Health Check
```bash
curl http://localhost:8000/health/
```

### Docker Health Check
Built-in Docker health check calls `/health/` endpoint.

## Development

### Testing
```bash
# Run tests (requires httpx)
pip install httpx pytest pytest-asyncio
pytest tests/
```

### Linting
```bash
pip install ruff mypy
ruff check langhook/
mypy langhook/
```

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Webhooks      │───▶│ svc-ingest   │───▶│ NATS        │
│ (GitHub, etc.)  │    │ (FastAPI)    │    │ JetStream   │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │                     │
                              ▼                     ▼
                       ┌──────────────┐    ┌─────────────┐
                       │    Redis     │    │ Canonical   │
                       │ (Rate Limit) │    │ Events      │
                       └──────────────┘    └─────────────┘
```

## License

MIT License - see LICENSE file for details.

# Event Logging to PostgreSQL

This feature allows LangHook to optionally log all incoming events and their canonical transformation results to PostgreSQL for auditing, analytics, and debugging purposes.

## Configuration

The event logging feature is **disabled by default** and can be enabled using environment variables:

### Environment Variables

- `EVENT_LOGGING_ENABLED`: Set to `true` to enable event logging (default: `false`)
- `POSTGRES_DSN`: PostgreSQL connection string (shared with subscription service)
- `NATS_URL`: NATS server URL (shared with other services)
- `NATS_STREAM_EVENTS`: NATS events stream name (shared with other services)
- `NATS_CONSUMER_GROUP`: NATS consumer group name (shared with other services)

### Docker Compose

To enable event logging in the Docker Compose setup, update the environment variables:

```yaml
environment:
  - EVENT_LOGGING_ENABLED=true  # Enable event logging
  # ... other environment variables
```

### Environment File

You can also configure this in your `.env.subscriptions` file:

```bash
EVENT_LOGGING_ENABLED=true
POSTGRES_DSN=postgresql://langhook:langhook@localhost:5432/langhook
```

## Database Schema

When enabled, the service automatically creates an `event_logs` table with the following structure:

```sql
CREATE TABLE event_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,        -- CloudEvent ID
    source VARCHAR(255) NOT NULL,          -- Event source (e.g., 'github', 'stripe')
    subject VARCHAR(255) NOT NULL,         -- NATS subject
    publisher VARCHAR(255) NOT NULL,       -- Canonical publisher
    resource_type VARCHAR(255) NOT NULL,   -- Canonical resource type
    resource_id VARCHAR(255) NOT NULL,     -- Canonical resource ID
    action VARCHAR(255) NOT NULL,          -- Canonical action
    canonical_data JSONB NOT NULL,         -- Full canonical event data
    raw_payload JSONB,                     -- Original raw payload (if available)
    timestamp TIMESTAMPTZ NOT NULL,        -- Event timestamp
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- Log insertion time
);
```

Indexes are automatically created on frequently queried fields for optimal performance.

## How It Works

1. **Event Flow**: Raw events → Ingest → NATS → Map Service → Canonical Events → NATS
2. **Logging**: When enabled, a separate `EventLoggingService` consumes canonical events from NATS
3. **Storage**: Each canonical event is parsed and stored in the `event_logs` table
4. **Performance**: The logging runs asynchronously and doesn't block event processing

## Querying Event Logs

Once enabled, you can query the logged events directly from PostgreSQL:

```sql
-- Find all events from GitHub in the last hour
SELECT event_id, action, resource_type, timestamp 
FROM event_logs 
WHERE publisher = 'github' 
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Count events by publisher and action
SELECT publisher, action, COUNT(*) as event_count
FROM event_logs 
WHERE logged_at > NOW() - INTERVAL '1 day'
GROUP BY publisher, action
ORDER BY event_count DESC;

-- Find events for a specific resource
SELECT event_id, action, canonical_data
FROM event_logs 
WHERE publisher = 'github' 
  AND resource_type = 'pull_request' 
  AND resource_id = '123';
```

## Performance Considerations

- **Disk Space**: Each event is stored as JSONB, so monitor disk usage in high-volume environments
- **Database Performance**: The service uses connection pooling and indexes for efficient writes
- **Error Handling**: Database errors are logged but don't block event processing
- **Asynchronous**: Logging runs in a separate consumer and doesn't impact main event flow

## Monitoring

The event logging service provides structured logging for monitoring:

- Service start/stop events
- Successful event logging
- Database connection errors
- Invalid event data warnings

## Security

- Event data is stored as-is, including any sensitive information in payloads
- Consider database encryption and access controls for sensitive environments
- Raw payloads may contain authentication tokens or personal data

## Troubleshooting

### Service Not Starting

Check that:
1. `EVENT_LOGGING_ENABLED=true` is set
2. PostgreSQL connection is available
3. NATS connection is available
4. Database permissions allow table creation

### Events Not Being Logged

Verify:
1. The service started successfully (check logs)
2. Canonical events are being published to NATS
3. No database connection errors in logs
4. The `event_logs` table was created

### Performance Issues

Consider:
1. Database indexing strategy for your query patterns
2. Connection pool settings
3. Disk space and I/O capacity
4. Archiving old event logs

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


# Server Path Configuration for Reverse Proxy Deployments

LangHook server supports deployment behind reverse proxies (like nginx) with path-based routing through the `SERVER_PATH` environment variable.

## Configuration

Set the `SERVER_PATH` environment variable to the path prefix where your LangHook server will be accessed:

```bash
# For serving at https://example.com/langhook/
export SERVER_PATH=/langhook

# Or in your .env file
SERVER_PATH=/langhook
```

## Frontend Build

When building the frontend with a custom server path, make sure to set the `SERVER_PATH` environment variable before building:

```bash
cd frontend
SERVER_PATH=/langhook npm run build
```

This ensures that all static asset references in the frontend (JavaScript, CSS, images) are correctly prefixed with the server path.

## Nginx Configuration Example

Here's an example nginx configuration for serving LangHook at a subpath:

**How it works:**
- Nginx receives requests at `/langhook/*` (e.g., `/langhook/health/`)
- The `proxy_pass` directive with trailing slash automatically strips the `/langhook` prefix
- FastAPI receives the request without the prefix (e.g., `/health/`)
- FastAPI's `root_path="/langhook"` tells it that its public base URL is `/langhook` for URL generation

```nginx
server {
    listen 80;
    server_name example.com;

    # Serve LangHook at /langhook
    location /langhook/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

You can test the configuration by:

1. Setting the `SERVER_PATH` environment variable
2. Starting the server: `uvicorn langhook.app:app --host 0.0.0.0 --port 8000`
3. Accessing the API at `http://localhost:8000/langhook/health/`
4. Accessing the console at `http://localhost:8000/langhook/console`

## API Endpoints

All API endpoints automatically work with the configured server path:

- Health: `{SERVER_PATH}/health/`
- Ingest: `{SERVER_PATH}/ingest/{source}`  
- Console: `{SERVER_PATH}/console`
- Demo: `{SERVER_PATH}/demo`
- Docs: `{SERVER_PATH}/docs` (when debug enabled)

The server automatically handles URL routing and static asset serving for the configured path.