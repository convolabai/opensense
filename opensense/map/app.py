"""FastAPI application for the mapping service HTTP endpoints."""

import json
from typing import Any, Dict

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi import Response
from pydantic import BaseModel

from opensense.core.fastapi import global_exception_handler, create_health_endpoint
from opensense.map.config import settings
from opensense.map.llm import llm_service
from opensense.map.service import mapping_service
from opensense.map.metrics import metrics

logger = structlog.get_logger()


class SuggestMapRequest(BaseModel):
    """Request model for mapping suggestion endpoint."""
    
    source: str
    payload: Dict[str, Any]


class SuggestMapResponse(BaseModel):
    """Response model for mapping suggestion endpoint."""
    
    jsonata: str
    source: str


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    
    events_processed: int
    events_mapped: int
    events_failed: int
    llm_invocations: int
    mapping_success_rate: float
    llm_usage_rate: float


# Create FastAPI app
app = FastAPI(
    title="OpenSense Canonicaliser",
    description="Event mapping service that transforms raw webhooks into canonical CloudEvents",
    version="0.3.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Add health check endpoint
health_endpoint = create_health_endpoint("svc-map", "0.3.0")
app.get("/health/")(health_endpoint)


@app.post("/suggest-map", response_model=SuggestMapResponse)
async def suggest_mapping(request: SuggestMapRequest) -> SuggestMapResponse:
    """
    Generate JSONata mapping suggestion using LLM.
    
    This endpoint is for development/testing purposes to help create
    mapping files manually.
    """
    if not llm_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not available"
        )
    
    try:
        suggestion = await llm_service.suggest_mapping(
            source=request.source,
            raw_payload=request.payload
        )
        
        if suggestion is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate mapping suggestion"
            )
        
        logger.info(
            "Mapping suggestion generated via API",
            source=request.source,
            suggestion_length=len(suggestion)
        )
        
        return SuggestMapResponse(
            jsonata=suggestion,
            source=request.source
        )
        
    except Exception as e:
        logger.error(
            "Error in suggest-map endpoint",
            source=request.source,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus-style metrics for monitoring."""
    metrics_text = metrics.get_metrics_text()
    return Response(content=metrics_text, media_type="text/plain")


@app.get("/metrics/json", response_model=MetricsResponse)
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
        "opensense.map.app:app",
        host="0.0.0.0",
        port=8001,  # Different port from ingest service
        reload=settings.debug,
    )