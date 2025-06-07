"""Database service for subscription management."""

import json
from typing import List, Optional

import structlog
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session

from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.models import Base, Subscription
from langhook.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate

logger = structlog.get_logger("langhook")


class DatabaseService:
    """Service for managing subscription database operations."""

    def __init__(self) -> None:
        self.engine = create_engine(subscription_settings.postgres_dsn)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self) -> None:
        """Create database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Subscription database tables created")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    async def create_subscription(
        self, 
        subscriber_id: str, 
        pattern: str, 
        subscription_data: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription."""
        with self.get_session() as session:
            subscription = Subscription(
                subscriber_id=subscriber_id,
                description=subscription_data.description,
                pattern=pattern,
                channel_type=subscription_data.channel_type,
                channel_config=json.dumps(subscription_data.channel_config),
                active=True
            )
            
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            
            logger.info(
                "Subscription created",
                subscription_id=subscription.id,
                subscriber_id=subscriber_id,
                pattern=pattern
            )
            
            return subscription

    async def get_subscription(self, subscription_id: int, subscriber_id: str) -> Optional[Subscription]:
        """Get a subscription by ID for a specific subscriber."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter(
                and_(
                    Subscription.id == subscription_id,
                    Subscription.subscriber_id == subscriber_id
                )
            ).first()
            
            if subscription:
                # Parse the channel_config JSON
                subscription.channel_config = json.loads(subscription.channel_config)
                
            return subscription

    async def get_subscriber_subscriptions(
        self, 
        subscriber_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> tuple[List[Subscription], int]:
        """Get all subscriptions for a subscriber with pagination."""
        with self.get_session() as session:
            query = session.query(Subscription).filter(Subscription.subscriber_id == subscriber_id)
            
            total = query.count()
            subscriptions = query.offset(skip).limit(limit).all()
            
            # Parse channel_config JSON for each subscription
            for subscription in subscriptions:
                subscription.channel_config = json.loads(subscription.channel_config)
            
            return subscriptions, total

    async def update_subscription(
        self, 
        subscription_id: int, 
        subscriber_id: str, 
        pattern: Optional[str],
        update_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update a subscription."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter(
                and_(
                    Subscription.id == subscription_id,
                    Subscription.subscriber_id == subscriber_id
                )
            ).first()
            
            if not subscription:
                return None
                
            # Update fields
            if update_data.description is not None:
                subscription.description = update_data.description
            if pattern is not None:
                subscription.pattern = pattern
            if update_data.channel_type is not None:
                subscription.channel_type = update_data.channel_type
            if update_data.channel_config is not None:
                subscription.channel_config = json.dumps(update_data.channel_config)
            if update_data.active is not None:
                subscription.active = update_data.active
                
            session.commit()
            session.refresh(subscription)
            
            # Parse the channel_config JSON
            subscription.channel_config = json.loads(subscription.channel_config)
            
            logger.info(
                "Subscription updated",
                subscription_id=subscription.id,
                subscriber_id=subscriber_id
            )
            
            return subscription

    async def delete_subscription(self, subscription_id: int, subscriber_id: str) -> bool:
        """Delete a subscription."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter(
                and_(
                    Subscription.id == subscription_id,
                    Subscription.subscriber_id == subscriber_id
                )
            ).first()
            
            if not subscription:
                return False
                
            session.delete(subscription)
            session.commit()
            
            logger.info(
                "Subscription deleted",
                subscription_id=subscription.id,
                subscriber_id=subscriber_id
            )
            
            return True

    async def get_all_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions for consumer management."""
        with self.get_session() as session:
            subscriptions = session.query(Subscription).filter(
                Subscription.active == True
            ).all()
            
            # Parse channel_config JSON for each subscription
            for subscription in subscriptions:
                subscription.channel_config = json.loads(subscription.channel_config)
            
            return subscriptions


# Global database service instance
db_service = DatabaseService()