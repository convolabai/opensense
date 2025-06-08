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