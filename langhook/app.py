"""Consolidated FastAPI application for OpenSense services."""

# init dotenv
from dotenv import load_dotenv
load_dotenv(override=True)

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from langhook.core.fastapi import (
    add_request_id_header,
    global_exception_handler,
)
from langhook.ingest.config import settings as ingest_settings
from langhook.ingest.kafka import kafka_producer
from langhook.ingest.middleware import RateLimitMiddleware
from langhook.ingest.security import verify_signature
from langhook.map.config import settings as map_settings
from langhook.map.llm import llm_service
from langhook.map.metrics import metrics
from langhook.map.service import mapping_service

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for both services."""
    import asyncio

    # Startup
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger()
    logger.info("Starting OpenSense Services", version="0.3.0")

    # Start Kafka producer (for ingest)
    await kafka_producer.start()

    # Start mapping service (Kafka consumer for map) in background
    mapping_task = asyncio.create_task(mapping_service.run())

    yield

    # Shutdown
    logger.info("Shutting down OpenSense Services")

    # Cancel mapping service
    mapping_task.cancel()
    try:
        await asyncio.wait_for(mapping_task, timeout=5.0)
    except (TimeoutError, asyncio.CancelledError):
        logger.info("Mapping service stopped")

    # Stop Kafka producer
    await kafka_producer.stop()


app = FastAPI(
    title="OpenSense Services",
    description="Unified API for OpenSense ingest gateway and canonicaliser services",
    version="0.3.0",
    docs_url="/docs" if (ingest_settings.debug or map_settings.debug) else None,
    redoc_url="/redoc" if (ingest_settings.debug or map_settings.debug) else None,
    lifespan=lifespan,
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Frontend demo routes
frontend_path = Path(__file__).parent.parent / "frontend" / "build"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

    @app.get("/demo")
    async def demo():
        """Serve the React demo application."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Demo not available - frontend not built")

    @app.get("/demo/{path:path}")
    async def demo_assets(path: str):
        """Serve demo assets."""
        file_path = frontend_path / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # For React Router, serve index.html for any unmatched routes
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="File not found")
else:
    @app.get("/demo")
    async def demo_not_available():
        """Demo not available when frontend is not built."""
        return {
            "message": "Demo not available",
            "instructions": "To build the frontend demo:\n1. cd frontend\n2. npm install\n3. npm run build"
        }


# ================================
# SHARED ENDPOINTS
# ================================

class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    services: dict[str, str]
    version: str


@app.get("/health/")
async def health_check() -> HealthResponse:
    """Health check endpoint for both services."""
    return HealthResponse(
        status="up",
        services={
            "ingest": "up",
            "map": "up"
        },
        version="0.3.0"
    )


# ================================
# INGEST ENDPOINTS
# ================================

class IngestResponse(BaseModel):
    """Ingest endpoint response model."""

    message: str
    request_id: str


@app.post("/ingest/{source}", response_model=IngestResponse)
async def ingest_webhook(
    source: str,
    request: Request,
    response: Response,
) -> IngestResponse:
    """
    Catch-all webhook endpoint that accepts JSON payloads.
    
    Args:
        source: Source identifier from URL path (e.g., 'github', 'stripe')
        request: FastAPI request object
        response: FastAPI response object
    
    Returns:
        IngestResponse: Success response with request ID
    
    Raises:
        HTTPException: For various error conditions (400, 401, 413, 429)
    """
    request_id = add_request_id_header(response)

    # Get request headers and body
    headers = dict(request.headers)

    try:
        # Read request body
        body_bytes = await request.body()

        # Check body size limit
        if len(body_bytes) > ingest_settings.max_body_bytes:
            logger.warning(
                "Request body too large",
                source=source,
                request_id=request_id,
                body_size=len(body_bytes),
                limit=ingest_settings.max_body_bytes,
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request body too large"
            )

        # Parse JSON payload
        try:
            payload = json.loads(body_bytes)
        except json.JSONDecodeError as e:
            # Send malformed JSON to DLQ
            await send_to_dlq(source, request_id, body_bytes, str(e), headers)
            logger.error(
                "Invalid JSON payload",
                source=source,
                request_id=request_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )

        # Verify HMAC signature if configured for this source
        signature_valid = await verify_signature(source, body_bytes, headers)
        if signature_valid is False:
            logger.warning(
                "Invalid HMAC signature",
                source=source,
                request_id=request_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        # Create event message for Kafka
        event_message = {
            "id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": source,
            "signature_valid": signature_valid,
            "headers": headers,
            "payload": payload,
        }

        # Send to Kafka
        await kafka_producer.send_event(event_message)

        logger.info(
            "Event ingested successfully",
            source=source,
            request_id=request_id,
            signature_valid=signature_valid,
        )

        response.status_code = status.HTTP_202_ACCEPTED
        return IngestResponse(
            message="Event accepted",
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error processing request",
            source=source,
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def send_to_dlq(
    source: str,
    request_id: str,
    body_bytes: bytes,
    error: str,
    headers: dict[str, Any],
) -> None:
    """Send malformed event to dead letter queue."""
    dlq_message = {
        "id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "source": source,
        "error": error,
        "headers": headers,
        "payload": body_bytes.decode("utf-8", errors="replace"),
    }

    await kafka_producer.send_dlq(dlq_message)


# ================================
# MAP ENDPOINTS
# ================================

class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""

    events_processed: int
    events_mapped: int
    events_failed: int
    llm_invocations: int
    mapping_success_rate: float
    llm_usage_rate: float


@app.get("/map/metrics")
async def get_prometheus_metrics():
    """Get Prometheus-style metrics for monitoring."""
    metrics_text = metrics.get_metrics_text()
    return Response(content=metrics_text, media_type="text/plain")


@app.get("/map/metrics/json", response_model=MetricsResponse)
async def get_json_metrics() -> MetricsResponse:
    """Get metrics in JSON format for easy consumption."""
    service_metrics = mapping_service.get_metrics()

    return MetricsResponse(
        events_processed=service_metrics["events_processed"],
        events_mapped=service_metrics["events_mapped"],
        events_failed=service_metrics["events_failed"],
        llm_invocations=service_metrics["llm_invocations"],
        mapping_success_rate=service_metrics["mapping_success_rate"],
        llm_usage_rate=service_metrics["llm_usage_rate"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "opensense.app:app",
        host="0.0.0.0",
        port=8000,
        reload=ingest_settings.debug or map_settings.debug,
    )
