"""Shared FastAPI utilities and components."""

import uuid

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger("langhook")


class HealthResponse(BaseModel):
    """Standard health check response model."""

    status: str
    service: str
    version: str


def create_health_endpoint(service_name: str, version: str):
    """Create a standardized health check endpoint."""
    async def health_check() -> HealthResponse:
        """Health check endpoint for readiness probes."""
        return HealthResponse(
            status="up",
            service=service_name,
            version=version
        )
    return health_check


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
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def add_request_id_header(response: Response) -> str:
    """Add a request ID header to the response and return the ID."""
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    return request_id
