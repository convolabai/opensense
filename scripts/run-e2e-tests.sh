#!/bin/bash

# End-to-End Test Runner Script
# This script sets up the environment and runs the e2e tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are available
command -v docker >/dev/null 2>&1 || { print_error "Docker is required but not installed. Aborting."; exit 1; }
if ! docker compose version >/dev/null 2>&1; then
    print_error "Docker Compose is required but not installed. Aborting."
    exit 1
fi

print_status "Starting LangHook End-to-End Test Suite"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating basic .env file for testing"
    cat > .env << 'EOF'
# LangHook Environment Configuration
DEBUG=true
LOG_LEVEL=DEBUG
TEST_MODE=true

# Service URLs for Docker Compose
NATS_URL=nats://nats:4222
REDIS_URL=redis://redis:6379
POSTGRES_DSN=postgresql://langhook:langhook@postgres:5432/langhook

# Application settings
MAX_BODY_BYTES=1048576
RATE_LIMIT=1000/minute
MAPPINGS_DIR=/app/mappings
NATS_STREAM_EVENTS=events
NATS_CONSUMER_GROUP=svc-map
MAX_EVENTS_PER_SECOND=2000
EOF
fi

# Clean up any existing containers
print_status "Cleaning up existing containers"
docker compose -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true

# Build and start infrastructure services first
print_status "Building and starting infrastructure services"
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build nats redis postgres langhook-streams

# Wait for services to be ready
print_status "Waiting for infrastructure services to be ready (this may take a few minutes)"

# Function to check if infrastructure services are healthy
check_infrastructure_health() {
    local redis_status=$(docker compose -f docker-compose.yml -f docker-compose.test.yml ps redis --format "{{.Health}}")
    local postgres_status=$(docker compose -f docker-compose.yml -f docker-compose.test.yml ps postgres --format "{{.Health}}")
    local streams_status=$(docker compose -f docker-compose.yml -f docker-compose.test.yml ps -a langhook-streams --format "{{.Status}}")
    
    [[ "$redis_status" == "healthy" ]] && \
    [[ "$postgres_status" == "healthy" ]] && \
    [[ "$streams_status" == *"Exited (0)"* ]]
}

# Wait for infrastructure services
max_attempts=60
attempt=1
while [ $attempt -le $max_attempts ]; do
    if check_infrastructure_health; then
        print_status "Infrastructure services are ready!"
        break
    fi
    
    if [ $((attempt % 10)) -eq 0 ]; then
        print_status "Still waiting for infrastructure... (attempt $attempt/$max_attempts)"
        docker compose -f docker-compose.yml -f docker-compose.test.yml ps
    fi
    
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    print_error "Infrastructure services failed to become healthy"
    docker compose -f docker-compose.yml -f docker-compose.test.yml ps
    docker compose -f docker-compose.yml -f docker-compose.test.yml logs
    exit 1
fi

# Now start the main LangHook service
print_status "Starting LangHook service"
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d langhook

# Application health check
print_status "Performing application health check"
max_attempts=36
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health/ 2>/dev/null; then
        print_status "Application health check passed"
        break
    fi
    
    if [ $((attempt % 6)) -eq 0 ]; then
        print_status "Still waiting for application... (attempt $attempt/$max_attempts)"
        docker compose -f docker-compose.yml -f docker-compose.test.yml ps langhook
    fi
    
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    print_error "Application health check failed"
    print_status "Application logs:"
    docker compose -f docker-compose.yml -f docker-compose.test.yml logs langhook
    exit 1
fi

# Run the tests
print_status "Running end-to-end tests"
if docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner; then
    print_status "All tests passed! ✅"
    test_result=0
else
    print_error "Some tests failed! ❌"
    test_result=1
fi

# Show test summary
print_status "Test Summary:"
docker compose -f docker-compose.yml -f docker-compose.test.yml logs test-runner | tail -20

# Clean up
print_status "Cleaning up test environment"
docker compose -f docker-compose.yml -f docker-compose.test.yml down -v --remove-orphans

if [ $test_result -eq 0 ]; then
    print_status "End-to-end test suite completed successfully! 🎉"
else
    print_error "End-to-end test suite failed. Check the logs above for details."
fi

exit $test_result