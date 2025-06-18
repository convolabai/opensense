# LangHook

> **Make any event from anywhere instantly understandable and actionable by anyone.**

LangHook transforms chaotic webhook payloads into standardized CloudEvents with a canonical format that both humans and machines can understand. Create smart event routing with natural language - no JSON wrangling required.

## 🎭 Demo

Visit our interactive demo to see LangHook in action:
**[https://demo.langhook.dev](https://demo.langhook.dev/demo)** *(placeholder URL)*

Try sending sample webhooks and see real-time event transformation, schema discovery, and natural language subscriptions.

## ⚡ Quickstart: Using LangHook SDK

Install the LangHook Python SDK to integrate event processing into your applications:

```bash
pip install langhook
```

For SDK-specific dependencies, see the [SDK documentation](./sdk/).

### Python SDK Usage

```python
import asyncio
from sdk.python import LangHookClient, LangHookClientConfig, AuthConfig

async def main():
    # Configure client to connect to your LangHook server
    config = LangHookClientConfig(
        endpoint="http://localhost:8000",
        auth=AuthConfig(type="token", value="your-auth-token")  # Optional
    )
    
    # Use client as context manager
    async with LangHookClient(config) as client:
        # Create a subscription using natural language
        subscription = await client.create_subscription(
            "Notify me when any pull request is merged"
        )
        
        # Set up event listener
        def event_handler(event):
            print(f"Got event: {event.publisher}/{event.action}")
        
        # Start listening for events
        stop_listening = client.listen(
            str(subscription.id), 
            event_handler, 
            {"intervalSeconds": 15}
        )
        
        # ... do other work ...
        
        # Stop listening and clean up
        stop_listening()
        await client.delete_subscription(str(subscription.id))

asyncio.run(main())
```

### TypeScript/JavaScript SDK

```bash
npm install langhook-sdk
```

```typescript
import { LangHookClient, LangHookClientConfig } from 'langhook-sdk';

async function main() {
  // Configure client to connect to your LangHook server
  const config: LangHookClientConfig = {
    endpoint: 'http://localhost:8000',
    auth: {
      type: 'token',
      value: 'your-auth-token'  // Optional
    }
  };
  
  // Create client
  const client = new LangHookClient(config);
  
  // Initialize connection
  await client.init();
  
  // Create a subscription using natural language
  const subscription = await client.createSubscription(
    'Notify me when any pull request is merged'
  );
  
  // Set up event listener
  const eventHandler = (event) => {
    console.log(`Got event: ${event.publisher}/${event.action}`);
  };
  
  // Start listening for events
  const stopListening = client.listen(
    subscription.id.toString(),
    eventHandler,
    { intervalSeconds: 15 }
  );
  
  // ... do other work ...
  
  // Stop listening and clean up
  stopListening();
  await client.deleteSubscription(subscription.id.toString());
}

main().catch(console.error);
```

## 🚀 Running LangHook Server

### Option 1: Using Docker Compose (Recommended)

The easiest way to run LangHook with all dependencies:

```bash
# Download docker-compose.yml
curl -O https://raw.githubusercontent.com/touchaponk/langhook/main/docker-compose.yml

# Start PostgreSQL + NATS + Redis + LangHook
docker-compose --profile docker up -d

# Check status
docker-compose ps
```

The server will be available at `http://localhost:8000`.

### Option 2: Running LangHook Server Only

If you already have PostgreSQL, NATS, and Redis running:

```bash
# Install the server package
pip install langhook[server]

# Configure environment (copy and edit .env.example)
curl -O https://raw.githubusercontent.com/touchaponk/langhook/main/.env.example
cp .env.example .env
# Edit .env with your database and message broker URLs

# Start the server
langhook
```

**Required services:**
- **NATS JetStream** (message broker) - `nats://localhost:4222`
- **Redis** (rate limiting) - `redis://localhost:6379`  
- **PostgreSQL** (optional, for subscriptions) - `postgresql://user:pass@localhost:5432/langhook`

### Option 3: Running from Source Code

For development or customization:

```bash
# Clone the repository
git clone https://github.com/touchaponk/langhook.git
cd langhook

# Start dependencies only
docker-compose up -d nats redis postgres

# Install in development mode
pip install -e .

# Copy environment configuration
cp .env.example .env
# Edit .env as needed

# Run the server
langhook
```

### Using LangHook CLI to Start the Server

The `langhook` command starts the full server with all services:

```bash
# Basic usage
langhook

# View help
langhook --help

# With custom configuration
DEBUG=true LOG_LEVEL=debug langhook
```

**Other CLI tools:**
- `langhook-streams` - Manage NATS JetStream streams
- `langhook-dlq-show` - View dead letter queue messages

### 🎯 Try it Out

Once your server is running, visit:
- **`http://localhost:8000/console`** - Interactive web console to send test webhooks and manage subscriptions
- **`http://localhost:8000/docs`** - API documentation  
- **`http://localhost:8000/schema`** - View discovered event schemas

**Send your first webhook:**
```bash
curl -X POST http://localhost:8000/ingest/github \
  -H "Content-Type: application/json" \
  -d '{"action": "opened", "pull_request": {"number": 123}}'
```

## 🎯 Core Features

### Universal Webhook Ingestion
- **Single endpoint** accepts webhooks from any source (GitHub, Stripe, Slack, etc.)
- **HMAC signature verification** ensures payload authenticity
- **Rate limiting** protects against abuse
- **Dead letter queue** for error handling

### Intelligent Event Transformation
- **JSONata mapping engine** converts raw payloads to canonical format
- **LLM-powered fallback** generates mappings for unknown events
- **Enhanced fingerprinting** distinguishes events with same structure but different actions
- **CloudEvents 1.0 compliance** for interoperability
- **Schema validation** ensures data quality

### Natural Language Subscriptions
- **Plain English queries** like "Notify me when PR 1374 is approved"
- **LLM-generated NATS filter patterns** automatically translate intent to code
- **Multiple delivery channels** (Slack, email, webhooks)

### Dynamic Schema Registry
- **Automatic schema discovery** from all processed events
- **Real-time schema API** exposes available event types
- **Schema management** with deletion capabilities
- **LLM grounding** ensures subscriptions use real schemas

## 📊 Canonical Event Format

LangHook transforms any webhook into this standardized format:

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

## ⚙️ Configuration

LangHook uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

### Essential Settings
```bash
# Message broker (required)
NATS_URL=nats://localhost:4222

# Database (optional, for subscriptions)
POSTGRES_DSN=postgresql://user:pass@localhost:5432/langhook

# Cache and rate limiting (required)
REDIS_URL=redis://localhost:6379
```

### AI Features (Required)
```bash
# Enable LLM-powered mapping suggestions
OPENAI_API_KEY=sk-your-openai-key

# Or use local Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

See [.env.example](.env.example) for all available options.

## 🛠 Usage Examples

### 1. Query Available Event Schemas
```bash
curl http://localhost:8000/schema/
```

### 2. Send a Webhook Event
```bash
curl -X POST http://localhost:8000/ingest/github \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {"number": 1374}
  }'
```

### 3. Create a Natural Language Subscription
Visit `http://localhost:8000/console` and try:
> "Notify me when any pull request is merged"

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
2. **svc-map**: Event transformation engine with LLM fallback and schema collection
3. **Schema Registry**: Dynamic database tracking all event types
4. **Rule Engine**: Natural language subscription matching

## 🧪 Testing

### Unit Tests
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ --ignore=tests/e2e/
```

### End-to-End Tests
```bash
# Complete E2E test suite (requires Docker)
./scripts/run-e2e-tests.sh
```

## 📖 API Reference

LangHook provides a comprehensive REST API for webhook ingestion, event processing, subscription management, and schema operations. All endpoints return JSON unless otherwise specified.

### Base URL Structure
- **Local Development**: `http://localhost:8000`
- **With SERVER_PATH**: `http://your-domain{SERVER_PATH}`

All API responses include standard HTTP status codes and may include a `X-Request-ID` header for tracing.

---

### 🏥 Health & Status

#### **GET** `/health/`
Health check endpoint for monitoring and readiness probes.

**Response:**
```json
{
  "status": "up",
  "services": {
    "ingest": "up",
    "map": "up"
  },
  "version": "0.3.0"
}
```

---

### 📥 Webhook Ingestion

#### **POST** `/ingest/{source}`
Accepts webhook payloads from any source. Events are processed asynchronously and transformed into canonical format.

**Parameters:**
- `source` (path): Source identifier (e.g., "github", "stripe", "slack")

**Headers:**
- `Content-Type: application/json` (required)
- `X-Hub-Signature-256`: HMAC signature (optional, for verification)

**Request Body:** JSON payload from webhook source

**Response (202 Accepted):**
```json
{
  "message": "Event accepted",
  "request_id": "req_12345abcde"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/ingest/github \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 1374,
      "title": "Add new feature"
    }
  }'
```

---

### 📋 Schema Registry

#### **GET** `/schema/`
Get the complete event schema registry with all discovered publishers, resource types, and actions.

**Response:**
```json
{
  "publishers": ["github", "stripe", "slack"],
  "resource_types": {
    "github": ["pull_request", "issue", "push"],
    "stripe": ["invoice", "payment_intent"]
  },
  "actions": ["opened", "closed", "created", "updated"]
}
```

#### **DELETE** `/schema/publishers/{publisher}`
Delete all schema entries for a specific publisher.

**Parameters:**
- `publisher` (path): Publisher name to delete

**Response:** 204 No Content

#### **DELETE** `/schema/publishers/{publisher}/resource-types/{resource_type}`
Delete schema entries for a publisher/resource_type combination.

**Parameters:**
- `publisher` (path): Publisher name
- `resource_type` (path): Resource type to delete

**Response:** 204 No Content

#### **DELETE** `/schema/publishers/{publisher}/resource-types/{resource_type}/actions/{action}`
Delete a specific schema entry.

**Parameters:**
- `publisher` (path): Publisher name
- `resource_type` (path): Resource type
- `action` (path): Action to delete

**Response:** 204 No Content

---

### 🔔 Subscriptions

#### **POST** `/subscriptions/`
Create a new subscription using natural language or structured data.

**Request Body:**
```json
{
  "description": "Notify me when any pull request is merged",
  "channel_type": "webhook",
  "channel_config": {
    "url": "https://your-webhook-endpoint.com/notify"
  },
  "gate": {
    "enabled": true,
    "prompt": "Only notify for high-priority PRs"
  }
}
```

**Response (201 Created):**
```json
{
  "id": 123,
  "subscriber_id": "default",
  "description": "Notify me when any pull request is merged",
  "pattern": "langhook.events.github.pull_request.*.closed",
  "channel_type": "webhook",
  "channel_config": {
    "url": "https://your-webhook-endpoint.com/notify"
  },
  "active": true,
  "disposable": false,
  "used": false,
  "gate": {
    "enabled": true,
    "prompt": "Only notify for high-priority PRs"
  },
  "created_at": "2023-06-18T12:00:00Z"
}
```

#### **GET** `/subscriptions/`
List all subscriptions with pagination.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `size` (optional): Items per page (default: 50, max: 100)

**Response:**
```json
{
  "subscriptions": [
    {
      "id": 123,
      "subscriber_id": "default",
      "description": "Notify me when any pull request is merged",
      "pattern": "langhook.events.github.pull_request.*.closed",
      "active": true,
      "created_at": "2023-06-18T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

#### **GET** `/subscriptions/{subscription_id}`
Get details of a specific subscription.

**Parameters:**
- `subscription_id` (path): Subscription ID

**Response:** Same format as POST response

#### **PUT** `/subscriptions/{subscription_id}`
Update an existing subscription.

**Parameters:**
- `subscription_id` (path): Subscription ID

**Request Body:** Partial subscription data (same format as POST)

**Response:** Updated subscription data

#### **DELETE** `/subscriptions/{subscription_id}`
Delete a subscription.

**Parameters:**
- `subscription_id` (path): Subscription ID

**Response:** 204 No Content

#### **GET** `/subscriptions/{subscription_id}/events`
List events that matched a specific subscription.

**Parameters:**
- `subscription_id` (path): Subscription ID
- `page` (query, optional): Page number (default: 1)
- `size` (query, optional): Items per page (default: 50, max: 100)

**Response:**
```json
{
  "event_logs": [
    {
      "id": 456,
      "subscription_id": 123,
      "event_id": "evt_abc123",
      "source": "github",
      "subject": "pull_request.1374",
      "publisher": "github",
      "resource_type": "pull_request",
      "resource_id": "1374",
      "action": "closed",
      "canonical_data": {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": "1374"},
        "action": "closed"
      },
      "timestamp": "2023-06-18T12:00:00Z",
      "webhook_sent": true,
      "webhook_response_status": 200,
      "gate_passed": true
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

---

### 🗄️ Ingest Mappings

#### **GET** `/subscriptions/ingest-mappings`
List discovered ingest mappings that transform webhook payloads.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `size` (optional): Items per page (default: 50, max: 100)

**Response:**
```json
{
  "mappings": [
    {
      "fingerprint": "github_pull_request_opened",
      "publisher": "github",
      "event_name": "pull_request.opened",
      "mapping_expr": "{ \"publisher\": \"github\", \"resource\": { \"type\": \"pull_request\", \"id\": pull_request.number }, \"action\": action }",
      "structure": {
        "action": "string",
        "pull_request": "object"
      },
      "created_at": "2023-06-18T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

#### **DELETE** `/subscriptions/ingest-mappings/{fingerprint}`
Delete a specific ingest mapping.

**Parameters:**
- `fingerprint` (path): Mapping fingerprint

**Response:** 204 No Content

---

### 📊 Metrics & Monitoring

#### **GET** `/map/metrics`
Get Prometheus-formatted metrics for monitoring.

**Response:** Plain text Prometheus metrics format

#### **GET** `/map/metrics/json`
Get metrics in JSON format for easy consumption.

**Response:**
```json
{
  "events_processed": 1250,
  "events_mapped": 1200,
  "events_failed": 50,
  "llm_invocations": 15,
  "mapping_success_rate": 0.96,
  "llm_usage_rate": 0.012
}
```

---

### 📜 Event Logs

#### **GET** `/event-logs`
List all processed events with pagination.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `size` (optional): Items per page (default: 50, max: 100)

**Response:**
```json
{
  "event_logs": [
    {
      "id": 789,
      "event_id": "evt_xyz789",
      "source": "github",
      "subject": "pull_request.1374",
      "publisher": "github",
      "resource_type": "pull_request",
      "resource_id": "1374",
      "action": "opened",
      "canonical_data": {
        "publisher": "github",
        "resource": {"type": "pull_request", "id": "1374"},
        "action": "opened"
      },
      "raw_payload": {
        "action": "opened",
        "pull_request": {"number": 1374}
      },
      "timestamp": "2023-06-18T12:00:00Z",
      "logged_at": "2023-06-18T12:00:01Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

---

### 🎨 Frontend Routes

#### **GET** `/console`
Serves the interactive web console for managing subscriptions and testing webhooks.

#### **GET** `/demo`
Serves the demo playground application.

#### **GET** `/`
Redirects to the console interface.

---

### Error Responses

All endpoints may return these error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid JSON payload",
  "request_id": "req_12345abcde"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid signature",
  "request_id": "req_12345abcde"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found",
  "request_id": "req_12345abcde"
}
```

**413 Request Entity Too Large:**
```json
{
  "detail": "Request body too large",
  "request_id": "req_12345abcde"
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": "No suitable event schema found for description",
  "request_id": "req_12345abcde"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error",
  "request_id": "req_12345abcde"
}
```

---

## 📚 Documentation

- [Agent Documentation](./AGENTS.md) - For AI agents and contributors
- [Interactive API Docs](http://localhost:8000/docs) - OpenAPI documentation (when debug enabled)
- [Examples](./examples/) - Sample payloads and mappings
- [Contributing Guide](./CONTRIBUTING.md) - Development setup

## 🤝 Contributing

We welcome contributions! Install development dependencies:

```bash
pip install -e ".[dev]"

# Run linting
ruff check langhook/
ruff format langhook/

# Run type checking
mypy langhook/
```

## 🌟 Why LangHook?

| Traditional Integration | LangHook |
|------------------------|-----------|
| Write custom parsers for each webhook | Single canonical format |
| Maintain brittle glue code | JSONata mappings + LLM fallback |
| Technical expertise required | Natural language subscriptions |
| Vendor lock-in with iPaaS | Open source, self-hostable |
| Complex debugging | End-to-end observability |

## 📄 License

LangHook is licensed under the [MIT License](./LICENSE).

---

**Ready to simplify your event integrations?** Get started with the [Quickstart](#-quickstart-using-langhook-sdk) or try the [interactive demo](https://demo.langhook.dev/demo).

For questions or support, visit our [GitHub Issues](https://github.com/touchaponk/langhook/issues).