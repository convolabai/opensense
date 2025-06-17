"""Consolidated FastAPI application for LangHook services."""

# init dotenv
from dotenv import load_dotenv

load_dotenv(override=True)

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from structlog.dev import ConsoleRenderer

from langhook.core.fastapi import (
    add_request_id_header,
    global_exception_handler,
)
from langhook.ingest.config import settings as ingest_settings
from langhook.ingest.middleware import RateLimitMiddleware
from langhook.ingest.nats import nats_producer
from langhook.ingest.security import verify_signature
from langhook.map.config import settings as map_settings
from langhook.map.metrics import metrics
from langhook.map.service import mapping_service
from langhook.subscriptions.routes import router as subscriptions_router
from langhook.subscriptions.schema_routes import router as schema_router
from langhook.subscriptions.schema_registry import schema_registry_service
from langhook.subscriptions.event_logging import event_logging_service
from langhook.subscriptions.dlq_logging import dlq_logging_service
from langhook.core.config import app_config

logger = structlog.get_logger("langhook")


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for both services."""
    import asyncio

    # Startup
    logging.basicConfig(
        level=logging.INFO,
        # format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Enable DEBUG only for our own modules
    if ingest_settings.debug or map_settings.debug:
        logging.getLogger("langhook").setLevel(logging.DEBUG)

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
            ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("langhook")
    logger.info("Starting LangHook Services", version="0.3.0")

    # Ensure NATS streams exist before starting services
    from langhook.core.startup import ensure_nats_streams
    await ensure_nats_streams(ingest_settings.nats_url)

    # Start NATS producer (for ingest)
    await nats_producer.start()

    # Start mapping service (Kafka consumer for map) in background
    mapping_task = asyncio.create_task(mapping_service.run())

    # Start event logging service in background (if enabled)
    event_logging_task = None
    dlq_logging_task = None
    subscription_consumer_task = None
    
    try:
        await event_logging_service.start()
        if event_logging_service._running:
            event_logging_task = asyncio.create_task(event_logging_service.run())
            logger.info("Event logging service started")
    except Exception as e:
        logger.warning("Failed to start event logging service", error=str(e))

    # Start DLQ logging service in background (if enabled)
    try:
        await dlq_logging_service.start()
        if dlq_logging_service._running:
            dlq_logging_task = asyncio.create_task(dlq_logging_service.run())
            logger.info("DLQ logging service started")
    except Exception as e:
        logger.warning("Failed to start DLQ logging service", error=str(e))

    # Start subscription consumer service in background
    try:
        from langhook.subscriptions.consumer_service import subscription_consumer_service
        await subscription_consumer_service.start()
        if subscription_consumer_service._running:
            subscription_consumer_task = asyncio.create_task(subscription_consumer_service.run())
            logger.info("Subscription consumer service started")
    except Exception as e:
        logger.warning("Failed to start subscription consumer service", error=str(e))

    # Initialize subscription database tables with retry logic
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from langhook.subscriptions.database import db_service
            db_service.create_tables()
            logger.info("Subscription database initialized successfully", attempt=attempt + 1)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error("Failed to initialize subscription database after max retries",
                           error=str(e), attempts=max_retries, exc_info=True)
                raise RuntimeError(f"Cannot start application - database initialization failed after {max_retries} attempts: {e}") from e
            else:
                logger.warning("Database initialization failed, retrying",
                             error=str(e), attempt=attempt + 1, max_retries=max_retries)
                await asyncio.sleep(retry_delay)

    yield

    # Shutdown
    logger.info("Shutting down LangHook Services")

    # Cancel mapping service
    mapping_task.cancel()
    try:
        await asyncio.wait_for(mapping_task, timeout=5.0)
    except (TimeoutError, asyncio.CancelledError):
        logger.info("Mapping service stopped")

    # Cancel event logging service if running
    if event_logging_task:
        event_logging_task.cancel()
        try:
            await asyncio.wait_for(event_logging_task, timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            logger.info("Event logging service stopped")

    # Cancel DLQ logging service if running
    if dlq_logging_task:
        dlq_logging_task.cancel()
        try:
            await asyncio.wait_for(dlq_logging_task, timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            logger.info("DLQ logging service stopped")

    # Cancel subscription consumer service if running
    if subscription_consumer_task:
        subscription_consumer_task.cancel()
        try:
            await asyncio.wait_for(subscription_consumer_task, timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            logger.info("Subscription consumer service stopped")

    # Stop NATS producer
    await nats_producer.stop()


app = FastAPI(
    title="LangHook Services",
    description="Unified API for LangHook ingest gateway and canonicaliser services",
    version="0.3.0",
    docs_url="/docs" if (ingest_settings.debug or map_settings.debug) else None,
    redoc_url="/redoc" if (ingest_settings.debug or map_settings.debug) else None,
    lifespan=lifespan,
    root_path=app_config.server_path,
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Include subscription API routes
app.include_router(subscriptions_router)

# Include schema API routes
app.include_router(schema_router)

# Frontend demo routes
frontend_path = Path(__file__).parent / "static"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

    @app.get("/console")
    async def console():
        """Serve the React console application."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Console not available - frontend not built")

    @app.get("/console/{path:path}")
    async def console_assets(path: str):
        """Serve console assets."""
        file_path = frontend_path / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # For React Router, serve index.html for any unmatched routes
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="File not found")
        
    @app.get("/demo")
    async def demo():
        """Serve the React demo playground application."""
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
        
    @app.get("/")
    async def root():
        """Redirect root path to console."""
        return RedirectResponse(url="/console", status_code=302)
else:
    @app.get("/console")
    async def console_not_available():
        """Console not available when frontend is not built."""
        return {
            "message": "Console not available",
            "instructions": "To build the frontend console:\n1. cd frontend\n2. npm install\n3. npm run build"
        }
        
    @app.get("/")
    async def root_not_available():
        """Redirect root path to console (not available)."""
        return RedirectResponse(url="/console", status_code=302)


# ================================
# SHARED ENDPOINTS
# ================================

class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    services: dict[str, str]
    version: str



@app.get("/event-logs", response_model=dict)
async def list_event_logs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page")
) -> dict:
    """List event logs with pagination."""
    try:
        from langhook.subscriptions.database import db_service
        from langhook.subscriptions.schemas import EventLogResponse, EventLogListResponse
        
        skip = (page - 1) * size
        event_logs, total = await db_service.get_event_logs(
            skip=skip,
            limit=size
        )

        return EventLogListResponse(
            event_logs=[EventLogResponse.from_orm(log) for log in event_logs],
            total=total,
            page=page,
            size=size
        ).dict()

    except Exception as e:
        logger.error(
            "Failed to list event logs",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list event logs"
        ) from e


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

        # Send to NATS
        await nats_producer.send_raw_event(event_message)

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

    await nats_producer.send_dlq(dlq_message)


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
        "langhook.app:app",
        host="0.0.0.0",
        port=8000,
        reload=ingest_settings.debug or map_settings.debug,
    )
