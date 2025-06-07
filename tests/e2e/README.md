# End-to-End Test Suite

This directory contains comprehensive end-to-end tests for the LangHook platform. These tests verify the complete functionality of all services working together in a realistic environment using Docker Compose.

## Overview

The E2E test suite covers:

### CRUD Operations
- **Subscription API**: Create, Read, Update, Delete subscriptions
- **Health checks**: Service health and status endpoints
- **Metrics**: Service metrics and monitoring endpoints

### Event Processing Flow
- **Event Ingestion**: Webhook ingestion from multiple sources (GitHub, Stripe, custom)
- **Event Mapping**: Raw event transformation to canonical format
- **Subscription Matching**: Event routing to matching subscriptions
- **End-to-end Flow**: Complete event journey from ingestion to notification

### Service Integration
- **Docker Compose**: Multi-service orchestration
- **NATS Messaging**: Event streaming and processing
- **Redis**: Rate limiting and caching
- **PostgreSQL**: Subscription metadata storage

## Structure

```
tests/e2e/
├── __init__.py
├── utils.py                     # Test utilities and helper functions
├── test_subscriptions_crud.py   # Subscription API CRUD tests
├── test_ingestion_flow.py       # Event ingestion and processing tests
└── README.md                    # This file
```

## Running Tests

### Local Development

#### Prerequisites
- Docker and Docker Compose installed
- Python 3.12+ (for local unit tests)

#### Quick Start
```bash
# Run the complete E2E test suite
./scripts/run-e2e-tests.sh
```

#### Manual Setup
```bash
# 1. Create environment file
cp .env.example .env

# 2. Start services
docker compose -f docker compose.yml -f docker compose.test.yml up -d --build

# 3. Wait for services to be ready (check health)
curl http://localhost:8000/health/

# 4. Run tests
docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner

# 5. Clean up
docker compose -f docker compose.yml -f docker compose.test.yml down -v
```

#### Running Specific Tests
```bash
# Run only subscription CRUD tests
docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner python -m pytest tests/e2e/test_subscriptions_crud.py -v

# Run only ingestion flow tests
docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner python -m pytest tests/e2e/test_ingestion_flow.py -v

# Run with debug output
docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner python -m pytest tests/e2e/ -v -s
```

### CI/CD Pipeline

The tests run automatically on:
- Every pull request to `main` or `develop` branches
- Direct pushes to `main` or `develop` branches
- Manual workflow dispatch

The CI pipeline includes:
1. **Unit Tests**: Fast unit tests for individual components
2. **E2E Tests**: Complete integration tests using Docker Compose
3. **Linting**: Code quality checks with ruff and mypy
4. **Security**: Security scanning with safety and bandit

## Test Configuration

### Environment Variables
Tests use the following environment variables (set automatically in Docker Compose):

```bash
LANGHOOK_BASE_URL=http://langhook:8000    # Base URL for API calls
NATS_URL=nats://nats:4222                 # NATS connection
REDIS_URL=redis://redis:6379              # Redis connection
POSTGRES_DSN=postgresql://...             # PostgreSQL connection
```

### Service Configuration
The `docker compose.test.yml` override provides:
- Faster health check intervals for quicker startup
- Debug logging enabled
- Higher rate limits for testing
- Test-specific environment variables

## Test Details

### Subscription CRUD Tests (`test_subscriptions_crud.py`)

Tests the complete subscription lifecycle:

- ✅ **Create**: Create new subscriptions with various configurations
- ✅ **Read**: Retrieve subscriptions by ID and list with pagination
- ✅ **Update**: Modify subscription properties (partial and full updates)
- ✅ **Delete**: Remove subscriptions and verify deletion
- ✅ **Validation**: Test input validation and error handling
- ✅ **End-to-end CRUD flow**: Complete lifecycle testing

### Ingestion Flow Tests (`test_ingestion_flow.py`)

Tests event processing and service integration:

#### Event Ingestion
- ✅ GitHub webhook events
- ✅ Stripe webhook events  
- ✅ Custom source events
- ✅ Invalid JSON handling
- ✅ Large payload handling
- ✅ Health checks and metrics

#### Event Processing Flow
- ✅ Complete GitHub PR event flow
- ✅ Event flow with subscription matching
- ✅ Multiple source event processing
- ✅ System resilience testing

#### Service Integration
- ✅ Multi-service health validation
- ✅ End-to-end integration testing
- ✅ Cross-service communication

## Test Utilities (`utils.py`)

The `E2ETestUtils` class provides:

### Setup/Teardown
- Service readiness waiting
- Test data cleanup
- Client initialization (HTTP, NATS, Redis)

### HTTP Operations
- Subscription CRUD operations
- Event ingestion
- Health checks and metrics

### Data Management
- Test subscription creation
- Event payload generation
- Database cleanup

### Event Processing
- Event processing verification
- Metrics monitoring
- Flow validation

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service logs
docker compose -f docker compose.yml -f docker compose.test.yml logs <service-name>

# Check service status
docker compose -f docker compose.yml -f docker compose.test.yml ps
```

#### Tests Timing Out
- Increase timeout values in test configuration
- Check if services have sufficient resources
- Verify network connectivity between containers

#### Database Connection Issues
```bash
# Check PostgreSQL logs
docker compose -f docker compose.yml -f docker compose.test.yml logs postgres

# Test database connection
docker compose -f docker compose.yml -f docker compose.test.yml exec postgres psql -U langhook -d langhook -c "\dt"
```

#### NATS Connection Issues
```bash
# Check NATS logs
docker compose -f docker compose.yml -f docker compose.test.yml logs nats

# Test NATS connectivity
curl http://localhost:8222/varz
```

### Debug Mode

Enable verbose logging:
```bash
# Set debug environment
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env

# Run with debug output
docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner python -m pytest tests/e2e/ -v -s --log-cli-level=DEBUG
```

## Contributing

When adding new E2E tests:

1. **Follow existing patterns**: Use the `E2ETestUtils` class for common operations
2. **Clean up test data**: Ensure tests clean up after themselves
3. **Use descriptive names**: Test names should clearly indicate what is being tested
4. **Add appropriate timeouts**: Account for service startup and processing time
5. **Test error conditions**: Include negative test cases
6. **Document complex scenarios**: Add comments for complex test logic

### Adding New Test Files

1. Create new test file in `tests/e2e/`
2. Import and use `E2ETestUtils` fixture
3. Follow naming convention: `test_<feature>_<scenario>.py`
4. Add to CI pipeline if needed

### Example Test Structure

```python
import pytest
from tests.e2e.utils import E2ETestUtils

@pytest.fixture
async def e2e_utils():
    utils = E2ETestUtils()
    await utils.setup()
    yield utils
    await utils.teardown()

class TestNewFeature:
    async def test_new_functionality(self, e2e_utils: E2ETestUtils):
        # Test implementation
        pass
```