# LangHook

> **Make any event from anywhere instantly understandable and actionable by anyone.**

LangHook transforms chaotic webhook payloads into standardized CloudEvents with a canonical format that both humans and machines can understand. Create smart event routing with natural language - no JSON wrangling required.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/convolabai/langhook.git
   cd langhook
   ```

2. **Start the core stack (without the `langhook` service):**
   ```bash
   docker-compose up -d
   ```

   **To include and start the `langhook` service container**, enable its Compose profile:

   ```bash
   docker-compose --profile docker up -d
   ```

3. **Install LangHook into your Python environment:**
   ```bash
   pip install -e .
   ```

4. **Build the frontend demo (optional):**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

5. **Run the LangHook service:**
   ```bash
   langhook
   ```

   > If you prefer to debug or develop against your local Python process instead of the container, simply skip the `--profile docker` option above and start with `langhook` after installing.

The API server will be available at `http://localhost:8000` with:
- Webhook ingestion at `/ingest/{source}`
- Event schema registry at `/schema/`
- Schema management at `/schema/publishers/...` (DELETE endpoints)
- Interactive console at `/console`
- API docs at `/docs`

## 🎯 Core Features

### Universal Webhook Ingestion
- **Single endpoint** accepts webhooks from any source (GitHub, Stripe, Slack, etc.)
- **HMAC signature verification** ensures payload authenticity
- **Rate limiting** protects against abuse
- **Dead letter queue** for error handling

### Intelligent Event Transformation
- **JSONata mapping engine** converts raw payloads to canonical format
- **LLM-powered fallback** generates mappings for unknown events
- **CloudEvents 1.0 compliance** for interoperability
- **Schema validation** ensures data quality

### Natural Language Subscriptions
- **Plain English queries** like "Notify me when PR 1374 is approved"
- **LLM-generated NATS filter patterns** automatically translate intent to code
- **Multiple delivery channels** (Slack, email, webhooks)

### Dynamic Schema Registry
- **Automatic schema discovery** collects publisher, resource type, and action combinations from all processed events
- **Real-time schema API** at `/schema` exposes available event types for accurate subscription generation
- **Schema management** with deletion capabilities at publisher, resource type, and action levels
- **LLM grounding** ensures natural language subscriptions only use actually available event schemas
- **Non-blocking collection** - schema registry failures don't affect event processing

## 📊 Canonical Event Format

LangHook transforms any webhook into a standardized canonical format:

```json
{
  "publisher": "github",
  "resource": {
    "type": "pull_request",
    "id": 1374
  },
  "action": "updated",
  "timestamp": "2025-06-03T15:45:02Z",
  "payload": { /* original webhook payload */ }
}
```

This consistent structure enables powerful filtering and routing capabilities across all event sources. **Schema Registry**: As events are processed, LangHook automatically collects and tracks all unique combinations of `publisher`, `resource.type`, and `action` values, building a dynamic registry of available event schemas accessible via the `/schema` API endpoint.

## 🛠 Usage Examples

### 1. Ingest a GitHub Webhook

```bash
curl -X POST http://localhost:8000/ingest/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 1374,
      "title": "Add new feature"
    }
  }'
```

### 2. Generate a Mapping Suggestion

```bash
curl -X POST http://localhost:8000/map/suggest-map \
  -H "Content-Type: application/json" \
  -d '{
    "source": "github",
    "payload": {
      "action": "opened",
      "pull_request": {"number": 1374}
    }
  }'
```

### 3. Query Available Event Schemas

```bash
curl http://localhost:8000/schema/
```

Response:
```json
{
  "publishers": ["github", "stripe", "jira"],
  "resource_types": {
    "github": ["pull_request", "repository"],
    "stripe": ["refund"],
    "jira": ["issue"]
  },
  "actions": ["created", "updated", "deleted", "read"]
}
```

### 4. Manage Schema Registry

Delete schema entries for specific publishers, resource types, or actions:

```bash
# Delete entire publisher and all associated schemas
curl -X DELETE http://localhost:8000/schema/publishers/github

# Delete specific resource type under a publisher
curl -X DELETE http://localhost:8000/schema/publishers/github/resource-types/pull_request

# Delete specific action for a publisher/resource type combination
curl -X DELETE http://localhost:8000/schema/publishers/github/resource-types/pull_request/actions/created
```

All deletion operations:
- Return `204 No Content` on success
- Return `404 Not Found` if the schema entry doesn't exist
- Require confirmation in the frontend interface
- Automatically refresh schema data after successful deletion

### 5. Monitor System Metrics

LangHook provides comprehensive Prometheus metrics for monitoring:

```bash
# View metrics in Prometheus format
curl http://localhost:8000/map/metrics

# View metrics in JSON format  
curl http://localhost:8000/map/metrics/json
```

**Available Metrics:**
- `langhook_events_processed_total` - Total events processed
- `langhook_events_mapped_total` - Successfully mapped events  
- `langhook_events_failed_total` - Failed events with reason labels
- `langhook_llm_invocations_total` - LLM API calls
- `langhook_mapping_duration_seconds` - Processing time histogram
- `langhook_active_mappings` - Number of loaded mapping rules

**Push to Prometheus (Optional):**
Configure `PROMETHEUS_PUSHGATEWAY_URL` to automatically push metrics to your Prometheus server:

```bash
# Enable automatic metrics pushing
export PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091
export PROMETHEUS_JOB_NAME=langhook-production
export PROMETHEUS_PUSH_INTERVAL=30  # seconds

# Restart LangHook to enable push gateway
langhook
```

## 🎭 Interactive Demo

Visit `http://localhost:8000/console` to:
- Send sample webhooks from popular services
- See real-time event transformation
- Test natural language subscriptions
- Explore the canonical event format
- Manage schema registry with delete capabilities

## ⚙ Configuration

LangHook is configured via environment variables:

### Core Settings
```bash
# NATS Configuration
NATS_URL=nats://localhost:4222
NATS_STREAM_EVENTS=events

# Service Settings
LOG_LEVEL=info
DEBUG=false
MAX_BODY_BYTES=10485760  # 10MB
```

### Security (Optional)
```bash
# HMAC signature verification
GITHUB_WEBHOOK_SECRET=your-github-secret
STRIPE_WEBHOOK_SECRET=whsec_your-stripe-secret

# LLM integration for mapping suggestions
OPENAI_API_KEY=sk-your-openai-key
```

### Advanced Configuration
```bash
# Mapping files location
MAPPINGS_DIR=/app/mappings

# NATS JetStream configuration
NATS_STREAM_EVENTS=events
NATS_CONSUMER_GROUP=svc-map

# Rate limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60

# Redis for rate limiting
REDIS_URL=redis://localhost:6379

# PostgreSQL for subscription metadata
POSTGRES_DSN=postgresql://user:pass@localhost:5432/langhook

# Prometheus metrics (optional)
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091  # Enable metrics push to Prometheus
PROMETHEUS_JOB_NAME=langhook-map                    # Job name for metrics
PROMETHEUS_PUSH_INTERVAL=30                         # Push interval in seconds
```

## 📈 Performance

LangHook is designed for high throughput:

- **≥ 2,000 events/second** (single 2-core container)
- **≤ 40ms p95 latency** for event transformation
- **< 1% mapping failure rate**
- **≤ 5% LLM fallback usage**

## 🏗 Architecture

```mermaid
graph TD
    A[Webhooks] --> B[svc-ingest]
    B --> C[NATS: raw.*]
    C --> D[svc-map]
    D --> E[NATS: langhook.events.*]
    D --> SR[Schema Registry DB]
    E --> F[Rule Engine]
    F --> G[Channels]
    H[JSONata Mappings] --> D
    I[LLM Service] -.-> D
    SR --> J[/schema API]
    SR --> K[LLM Prompt Augmentation]
    K --> L[Natural Language Subscriptions]
```

### Services

1. **svc-ingest**: HTTP webhook receiver with signature verification
2. **svc-map**: Event transformation engine with LLM fallback and automatic schema collection
3. **Schema Registry**: Dynamic database tracking all event types, exposed via `/schema` API
4. **Rule Engine**: Natural language subscription matching (coming soon)

## 🧪 Testing

LangHook includes comprehensive testing at multiple levels:

### Unit Tests
```bash
# Run all unit tests
pytest tests/ --ignore=tests/e2e/

# Run specific test files
pytest tests/test_app.py -v
pytest tests/map/test_mapper.py -v
```

### End-to-End Tests
```bash
# Run complete E2E test suite (requires Docker)
./scripts/run-e2e-tests.sh

# Manual E2E testing
docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d --build
docker-compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner
```

The E2E test suite covers:
- ✅ **Subscription API CRUD**: Create, read, update, delete subscriptions
- ✅ **Event Ingestion**: Webhook processing from GitHub, Stripe, and custom sources
- ✅ **Event Processing Flow**: Complete event transformation and routing
- ✅ **Service Integration**: Multi-service Docker Compose orchestration
- ✅ **Health Checks**: Service health monitoring and metrics

See [tests/e2e/README.md](tests/e2e/README.md) for detailed documentation.

### CI/CD Pipeline
Tests run automatically on every PR via GitHub Actions:
- Unit tests and linting
- End-to-end integration tests
- Security scanning

## 📚 Documentation

- [Agent Documentation](./AGENTS.md) - For AI agents and contributors
- [API Reference](http://localhost:8000/docs) - Interactive OpenAPI docs
- [Examples](./examples/) - Sample payloads and mappings
- [Schemas](./schemas/) - JSON schemas for validation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
ruff check langhook/
ruff format langhook/

# Run type checking
mypy langhook/
```

## 📄 License

LangHook is licensed under the [MIT License](./LICENSE).

## 🌟 Why LangHook?

| Traditional Integration | LangHook |
|------------------------|-----------|
| Write custom parsers for each webhook | Single canonical format |
| Maintain brittle glue code | JSONata mappings + LLM fallback |
| Technical expertise required | Natural language subscriptions |
| Vendor lock-in with iPaaS | Open source, self-hostable |
| Complex debugging | End-to-end observability |

---

**Ready to simplify your event integrations?** Get started with the [Quick Start](#-quick-start) guide or try the [interactive demo](http://localhost:8000/demo).

For questions or support, visit our [GitHub Issues](https://github.com/convolabai/langhook/issues).