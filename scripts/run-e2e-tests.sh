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
    print_status "Creating .env file from example"
    cp .env.example .env
    echo "TEST_MODE=true" >> .env
fi

# Clean up any existing containers
print_status "Cleaning up existing containers"
docker compose -f docker compose.yml -f docker compose.test.yml down -v --remove-orphans 2>/dev/null || true

# Build and start services
print_status "Building and starting services"
docker compose -f docker compose.yml -f docker compose.test.yml up -d --build

# Wait for services to be ready
print_status "Waiting for services to be ready (this may take a few minutes)"

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f docker compose.yml -f docker compose.test.yml ps $service_name | grep -q "healthy\|Up"; then
            return 0
        fi
        
        if [ $((attempt % 10)) -eq 0 ]; then
            print_status "Still waiting for $service_name... (attempt $attempt/$max_attempts)"
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Check individual services
services=("nats" "redis" "postgres" "langhook")
for service in "${services[@]}"; do
    print_status "Checking $service service"
    if ! check_service_health $service; then
        print_error "$service service failed to start properly"
        print_status "Service logs:"
        docker compose -f docker compose.yml -f docker compose.test.yml logs $service
        exit 1
    fi
    print_status "$service service is ready"
done

# Additional health check for the main application
print_status "Performing application health check"
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health/ 2>/dev/null; then
        print_status "Application health check passed"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Application health check failed"
        print_status "Application logs:"
        docker compose -f docker compose.yml -f docker compose.test.yml logs langhook
        exit 1
    fi
    
    sleep 3
    attempt=$((attempt + 1))
done

# Run the tests
print_status "Running end-to-end tests"
if docker compose -f docker compose.yml -f docker compose.test.yml run --rm test-runner; then
    print_status "All tests passed! ✅"
    test_result=0
else
    print_error "Some tests failed! ❌"
    test_result=1
fi

# Show test summary
print_status "Test Summary:"
docker compose -f docker compose.yml -f docker compose.test.yml logs test-runner | tail -20

# Clean up
print_status "Cleaning up test environment"
docker compose -f docker compose.yml -f docker compose.test.yml down -v --remove-orphans

if [ $test_result -eq 0 ]; then
    print_status "End-to-end test suite completed successfully! 🎉"
else
    print_error "End-to-end test suite failed. Check the logs above for details."
fi

exit $test_result