# Contributing to LangHook

Thank you for your interest in contributing to LangHook! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Git

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/convolabai/langhook.git
cd langhook

# Complete development environment setup
make dev-setup
```

This will install development dependencies and start Docker services.

### Manual Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Start Docker services
docker-compose up -d

# Verify installation
make test-unit
```

## Development Workflow

### Running Tests
```bash
# Run unit tests
make test-unit

# Run E2E tests (requires Docker)
make test-e2e

# Run all code quality checks
make check
```

### Code Quality
Before submitting a PR, ensure your code passes all quality checks:

```bash
# Format code
make format

# Check linting
make lint

# Run type checking
make type-check

# Run all checks
make check
```

### Common Issues

#### "No module named pytest"
You need to install development dependencies:
```bash
pip install -e ".[dev]"
# OR
make install-dev
```

#### Docker Services Not Starting
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs

# Restart services
make docker-down
make docker-up
```

#### E2E Tests Failing
E2E tests require a full Docker environment:
```bash
# Use the provided script
./scripts/run-e2e-tests.sh

# Or manually
make test-e2e
```

## Project Structure

```
langhook/
├── langhook/           # Main application code
├── tests/              # Test files
│   ├── e2e/           # End-to-end tests
│   └── ...            # Unit tests
├── scripts/           # Development scripts
├── examples/          # Example configurations
├── schemas/           # JSON schemas
├── mappings/          # Event mapping configurations
└── frontend/          # Frontend demo
```

## Submitting Changes

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** your changes (`make check`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to the branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Pull Request Guidelines

- Include a clear description of what your changes do
- Reference any related issues
- Ensure all tests pass
- Follow the existing code style
- Update documentation if necessary

## Testing

### Unit Tests
Unit tests are located in the `tests/` directory and test individual components in isolation.

### End-to-End Tests
E2E tests are in `tests/e2e/` and test the complete system with real services running in Docker.

### Test Coverage
We aim for high test coverage. New features should include appropriate tests.

## Code Style

- We use `ruff` for linting and formatting
- Type hints are required for all public functions
- Follow existing naming conventions
- Write clear, self-documenting code

## Getting Help

- Check existing [Issues](https://github.com/convolabai/langhook/issues)
- Create a new issue for bugs or feature requests
- Ask questions in discussions

## License

By contributing to LangHook, you agree that your contributions will be licensed under the MIT License.