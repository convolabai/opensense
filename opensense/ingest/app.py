"""FastAPI application for the ingest gateway service."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from opensense.ingest.config import settings
from opensense.ingest.kafka import kafka_producer
from opensense.ingest.security import verify_signature
from opensense.ingest.middleware import RateLimitMiddleware

logger = structlog.get_logger()

# Create FastAPI app with lifespan
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager."""
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
    logger.info("Starting OpenSense Ingest Gateway", version="0.2.0")
    
    # Start Kafka producer
    await kafka_producer.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpenSense Ingest Gateway")
    await kafka_producer.stop()


app = FastAPI(
    title="OpenSense Ingest Gateway",
    description="Secure webhook receiver that accepts and forwards events to the event bus",
    version="0.2.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str


class IngestResponse(BaseModel):
    """Ingest endpoint response model."""
    
    message: str
    request_id: str


@app.get("/health/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for readiness probes."""
    return HealthResponse(status="up")


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
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    
    # Get request headers and body
    headers = dict(request.headers)
    
    try:
        # Read request body
        body_bytes = await request.body()
        
        # Check body size limit
        if len(body_bytes) > settings.max_body_bytes:
            logger.warning(
                "Request body too large",
                source=source,
                request_id=request_id,
                body_size=len(body_bytes),
                limit=settings.max_body_bytes,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    headers: Dict[str, Any],
) -> None:
    """Send malformed event to dead letter queue."""
    dlq_message = {
        "id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "error": error,
        "headers": headers,
        "payload": body_bytes.decode("utf-8", errors="replace"),
    }
    
    await kafka_producer.send_dlq(dlq_message)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    request_id = str(uuid.uuid4())
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "opensense.ingest.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )