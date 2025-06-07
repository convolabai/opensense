"""Subscription API routes."""


import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from langhook.subscriptions.auth import get_current_user
from langhook.subscriptions.database import db_service
from langhook.subscriptions.nlp import llm_service
from langhook.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)

logger = structlog.get_logger("langhook")

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_subscriber: str = Depends(get_current_user)
) -> SubscriptionResponse:
    """Create a new subscription."""
    try:
        # Convert natural language description to NATS filter pattern
        pattern = await llm_service.convert_to_pattern(subscription_data.description)

        # Create subscription in database
        subscription = await db_service.create_subscription(
            subscriber_id=current_subscriber,
            pattern=pattern,
            subscription_data=subscription_data
        )

        logger.info(
            "Subscription created via API",
            subscription_id=subscription.id,
            subscriber_id=current_subscriber,
            pattern=pattern
        )

        return SubscriptionResponse.from_orm(subscription)

    except Exception as e:
        logger.error(
            "Failed to create subscription",
            subscriber_id=current_subscriber,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        ) from e


@router.get("/", response_model=SubscriptionListResponse)
async def list_subscriptions(
    current_subscriber: str = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page")
) -> SubscriptionListResponse:
    """List subscriber's subscriptions with pagination."""
    try:
        skip = (page - 1) * size
        subscriptions, total = await db_service.get_subscriber_subscriptions(
            subscriber_id=current_subscriber,
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
            subscriber_id=current_subscriber,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list subscriptions"
        ) from e


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    current_subscriber: str = Depends(get_current_user)
) -> SubscriptionResponse:
    """Get a specific subscription."""
    subscription = await db_service.get_subscription(subscription_id, current_subscriber)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return SubscriptionResponse.from_orm(subscription)


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    update_data: SubscriptionUpdate,
    current_subscriber: str = Depends(get_current_user)
) -> SubscriptionResponse:
    """Update a subscription."""
    try:
        # If description is being updated, regenerate the pattern
        pattern = None
        if update_data.description is not None:
            pattern = await llm_service.convert_to_pattern(update_data.description)

        subscription = await db_service.update_subscription(
            subscription_id=subscription_id,
            subscriber_id=current_subscriber,
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
            subscriber_id=current_subscriber
        )

        return SubscriptionResponse.from_orm(subscription)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update subscription",
            subscription_id=subscription_id,
            subscriber_id=current_subscriber,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        ) from e


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    current_subscriber: str = Depends(get_current_user)
) -> None:
    """Delete a subscription."""
    try:
        deleted = await db_service.delete_subscription(subscription_id, current_subscriber)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        logger.info(
            "Subscription deleted via API",
            subscription_id=subscription_id,
            subscriber_id=current_subscriber
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete subscription",
            subscription_id=subscription_id,
            subscriber_id=current_subscriber,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription"
        ) from e
