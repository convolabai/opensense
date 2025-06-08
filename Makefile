# LangHook Development Makefile

.PHONY: help install-dev install test test-unit test-e2e lint format type-check clean docker-up docker-down

# Default target
help: ## Show this help message
	@echo "LangHook Development Commands"
	@echo "=============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install package only (production dependencies)
	pip install -e .

install-dev: ## Install package with development dependencies
	pip install -e ".[dev]"

# Testing
test: test-unit ## Run all tests (unit tests only by default)

test-unit: ## Run unit tests
	python -m pytest tests/ -v --tb=short -x --ignore=tests/e2e/

test-e2e: ## Run end-to-end tests (requires Docker environment)
	./scripts/run-e2e-tests.sh

# Code Quality
lint: ## Run linting
	ruff check langhook/ tests/

format: ## Format code
	ruff format langhook/ tests/

type-check: ## Run type checking
	mypy langhook/

# Docker
docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

# Cleanup
clean: ## Clean up Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Development workflow
dev-setup: install-dev docker-up ## Complete development setup
	@echo "Development environment ready!"
	@echo "- Python dependencies installed"
	@echo "- Docker services started"
	@echo "- Run 'make test' to verify everything works"

check: lint type-check test-unit ## Run all code quality checks