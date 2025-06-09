"""Subscription API routes."""


import structlog
from fastapi import APIRouter, HTTPException, Query, status

from langhook.subscriptions.database import db_service
from langhook.subscriptions.llm import llm_service, NoSuitableSchemaError
from langhook.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    EventLogListResponse,
)

logger = structlog.get_logger("langhook")

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate
) -> SubscriptionResponse:
    """Create a new subscription."""
    # Use placeholder subscriber ID since auth is out of scope
    subscriber_id = "default"
    
    try:
        # Convert natural language description to NATS filter pattern
        try:
            pattern = await llm_service.convert_to_pattern(subscription_data.description)
        except NoSuitableSchemaError as e:
            logger.warning(
                "Subscription rejected - no suitable schema found",
                subscriber_id=subscriber_id,
                description=subscription_data.description,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No suitable event schema found for description: '{subscription_data.description}'. Please check available schemas at /schema endpoint."
            ) from e

        # Create subscription in database
        subscription = await db_service.create_subscription(
            subscriber_id=subscriber_id,
            pattern=pattern,
            subscription_data=subscription_data
        )

        logger.info(
            "Subscription created via API",
            subscription_id=subscription.id,
            subscriber_id=subscriber_id,
            pattern=pattern
        )

        return SubscriptionResponse.from_orm(subscription)

    except HTTPException:
        raise
    except Exception as e:
        error_details = str(e)
        # Log the full error with stack trace for debugging
        logger.error(
            "Failed to create subscription",
            subscriber_id=subscriber_id,
            description=subscription_data.description,
            channel_type=subscription_data.channel_type,
            error=error_details,
            exc_info=True
        )
        
        # Return a more specific error message based on error type
        if "relation" in error_details.lower() and "does not exist" in error_details.lower():
            detail = "Database not properly initialized - subscription tables missing"
        elif "connection" in error_details.lower():
            detail = "Database connection failed"
        elif "permission" in error_details.lower():
            detail = "Database permission denied"
        else:
            detail = f"Failed to create subscription: {error_details}"
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        ) from e


@router.get("/event-logs", response_model=EventLogListResponse)
async def list_event_logs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page")
) -> EventLogListResponse:
    """List event logs with pagination."""
    try:
        skip = (page - 1) * size
        event_logs, total = await db_service.get_event_logs(
            skip=skip,
            limit=size
        )

        from langhook.subscriptions.schemas import EventLogResponse
        return EventLogListResponse(
            event_logs=[EventLogResponse.from_orm(log) for log in event_logs],
            total=total,
            page=page,
            size=size
        )

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


@router.get("/", response_model=SubscriptionListResponse)
async def list_subscriptions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page")
) -> SubscriptionListResponse:
    """List subscriptions with pagination."""
    # Use placeholder subscriber ID since auth is out of scope
    subscriber_id = "default"
    
    try:
        skip = (page - 1) * size
        subscriptions, total = await db_service.get_subscriber_subscriptions(
            subscriber_id=subscriber_id,
            skip=skip,
            limit=size
        )

        return SubscriptionListResponse(
            subscriptions=[SubscriptionResponse.from_orm(sub) for sub in subscriptions],
            total=total,
            page=page,
            size=size
        )

    except Exception as e:
        logger.error(
            "Failed to list subscriptions",
            subscriber_id=subscriber_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list subscriptions"
        ) from e


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int
) -> SubscriptionResponse:
    """Get a specific subscription."""
    # Use placeholder subscriber ID since auth is out of scope
    subscriber_id = "default"
    
    subscription = await db_service.get_subscription(subscription_id, subscriber_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return SubscriptionResponse.from_orm(subscription)


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdate
) -> SubscriptionResponse:
    """Update a subscription."""
    # Use placeholder subscriber ID since auth is out of scope
    subscriber_id = "default"
    
    try:
        # If description is being updated, regenerate the pattern
        pattern = None
        if update_data.description is not None:
            try:
                pattern = await llm_service.convert_to_pattern(update_data.description)
            except NoSuitableSchemaError as e:
                logger.warning(
                    "Subscription update rejected - no suitable schema found",
                    subscription_id=subscription_id,
                    subscriber_id=subscriber_id,
                    description=update_data.description,
                    error=str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"No suitable event schema found for description: '{update_data.description}'. Please check available schemas at /schema endpoint."
                ) from e

        subscription = await db_service.update_subscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            pattern=pattern,
            update_data=update_data
        )

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        logger.info(
            "Subscription updated via API",
            subscription_id=subscription.id,
            subscriber_id=subscriber_id
        )

        return SubscriptionResponse.from_orm(subscription)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update subscription",
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        ) from e


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int
) -> None:
    """Delete a subscription."""
    # Use placeholder subscriber ID since auth is out of scope
    subscriber_id = "default"
    
    try:
        deleted = await db_service.delete_subscription(subscription_id, subscriber_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        logger.info(
            "Subscription deleted via API",
            subscription_id=subscription_id,
            subscriber_id=subscriber_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete subscription",
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription"
        ) from e
