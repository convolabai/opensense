# Multi-stage build for LangHook Services
FROM node:18-slim as frontend-builder

# Set working directory for frontend
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install --only=production

# Copy frontend source
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/tsconfig.json ./

# Build frontend
RUN npm run build

FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml LICENSE README.md ./

# Copy source code
COPY langhook/ ./langhook/

# Install dependencies
RUN uv pip install --system -e .

# Test stage - extends builder with dev dependencies
FROM builder as test

# Install dev dependencies for testing
RUN uv pip install --system -e .[dev]

# Production stage
FROM python:3.12-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r langhook && useradd -r -g langhook langhook

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY langhook/ ./langhook/
COPY mappings/ ./mappings/
COPY schemas/ ./schemas/
COPY scripts/ ./scripts/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Set ownership
RUN chown -R langhook:langhook /app

# Switch to non-root user
USER langhook

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the consolidated application
CMD ["python", "-m", "langhook.main"]