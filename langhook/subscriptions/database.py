"""Database service for subscription management."""

import json

import structlog
from sqlalchemy import and_, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.models import Base, Subscription, EventLog
from langhook.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate

logger = structlog.get_logger("langhook")


class DatabaseService:
    """Service for managing subscription database operations."""

    def __init__(self) -> None:
        # Create engine with connection pool settings suitable for Docker environments
        self.engine = create_engine(
            subscription_settings.postgres_dsn,
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recreate connections after 1 hour
            connect_args={
                "connect_timeout": 10,
                "application_name": "langhook_subscriptions",
            }
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self) -> None:
        """Create database tables."""
        Base.metadata.create_all(bind=self.engine)

        # Explicitly ensure event schema registry table exists
        self.create_schema_registry_table()
        # Explicitly ensure event logs table exists
        self.create_event_logs_table()
        logger.info("Subscription database tables created")

    def create_schema_registry_table(self) -> None:
        """Create the event schema registry table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Create table with explicit SQL to ensure it exists
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS event_schema_registry (
                        publisher VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(255) NOT NULL,
                        action VARCHAR(255) NOT NULL,
                        PRIMARY KEY (publisher, resource_type, action)
                    )
                """)
                session.execute(create_table_sql)
                session.commit()
                logger.info("Event schema registry table ensured")
        except Exception as e:
            logger.error(
                "Failed to create event schema registry table",
                error=str(e),
                exc_info=True
            )

    def create_event_logs_table(self) -> None:
        """Create the event logs table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Create table with explicit SQL to ensure it exists
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS event_logs (
                        id SERIAL PRIMARY KEY,
                        event_id VARCHAR(255) NOT NULL,
                        source VARCHAR(255) NOT NULL,
                        subject VARCHAR(255) NOT NULL,
                        publisher VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(255) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        action VARCHAR(255) NOT NULL,
                        canonical_data JSONB NOT NULL,
                        raw_payload JSONB,
                        timestamp TIMESTAMPTZ NOT NULL,
                        logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                session.execute(create_table_sql)
                
                # Create indexes for better query performance
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_event_id ON event_logs(event_id)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_source ON event_logs(source)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_publisher ON event_logs(publisher)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_resource_type ON event_logs(resource_type)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_resource_id ON event_logs(resource_id)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_action ON event_logs(action)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_event_logs_logged_at ON event_logs(logged_at)",
                ]
                
                for index_sql in index_sqls:
                    session.execute(text(index_sql))
                
                session.commit()
                logger.info("Event logs table ensured")
        except Exception as e:
            logger.error(
                "Failed to create event logs table",
                error=str(e),
                exc_info=True
            )

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
                channel_config=json.dumps(subscription_data.channel_config) if subscription_data.channel_config else None,
                active=True
            )

            session.add(subscription)
            session.commit()
            session.refresh(subscription)

            # Parse the channel_config JSON back to dict for response if it exists
            if subscription.channel_config:
                subscription.channel_config = json.loads(subscription.channel_config)

            logger.info(
                "Subscription created",
                subscription_id=subscription.id,
                subscriber_id=subscriber_id,
                pattern=pattern
            )

            return subscription

    async def get_subscription(self, subscription_id: int, subscriber_id: str) -> Subscription | None:
        """Get a subscription by ID for a specific subscriber."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter(
                and_(
                    Subscription.id == subscription_id,
                    Subscription.subscriber_id == subscriber_id
                )
            ).first()

            if subscription:
                # Parse the channel_config JSON if it exists
                if subscription.channel_config:
                    subscription.channel_config = json.loads(subscription.channel_config)

            return subscription

    async def get_subscriber_subscriptions(
        self,
        subscriber_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Subscription], int]:
        """Get all subscriptions for a subscriber with pagination."""
        with self.get_session() as session:
            query = session.query(Subscription).filter(Subscription.subscriber_id == subscriber_id)

            total = query.count()
            subscriptions = query.offset(skip).limit(limit).all()

            # Parse channel_config JSON for each subscription if it exists
            for subscription in subscriptions:
                if subscription.channel_config:
                    subscription.channel_config = json.loads(subscription.channel_config)

            return subscriptions, total

    async def update_subscription(
        self,
        subscription_id: int,
        subscriber_id: str,
        pattern: str | None,
        update_data: SubscriptionUpdate
    ) -> Subscription | None:
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

            # Parse the channel_config JSON if it exists
            if subscription.channel_config:
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

    async def get_all_active_subscriptions(self) -> list[Subscription]:
        """Get all active subscriptions for consumer management."""
        with self.get_session() as session:
            subscriptions = session.query(Subscription).filter(
                Subscription.active
            ).all()

            # Parse channel_config JSON for each subscription
            for subscription in subscriptions:
                subscription.channel_config = json.loads(subscription.channel_config)

            return subscriptions

    async def get_event_logs(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[EventLog], int]:
        """Get event logs with pagination."""
        with self.get_session() as session:
            query = session.query(EventLog).order_by(EventLog.logged_at.desc())

            total = query.count()
            event_logs = query.offset(skip).limit(limit).all()

            return event_logs, total

    async def get_subscription_events(
        self,
        subscription_pattern: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[EventLog], int]:
        """Get event logs for a specific subscription pattern with pagination."""
        with self.get_session() as session:
            # Convert NATS pattern to SQL pattern for filtering
            # NATS patterns use * for single level wildcard and > for multi-level wildcard
            # We need to match events where their subject matches the subscription pattern
            
            # For now, we'll get all events and filter in Python since the pattern matching
            # is complex (NATS-style patterns). In production, this should be optimized.
            query = session.query(EventLog).order_by(EventLog.logged_at.desc())
            all_events = query.all()
            
            # Filter events that match the subscription pattern
            matching_events = []
            for event in all_events:
                if self._matches_pattern(event.subject, subscription_pattern):
                    matching_events.append(event)
            
            total = len(matching_events)
            paginated_events = matching_events[skip:skip + limit]
            
            return paginated_events, total
    
    def _matches_pattern(self, subject: str, pattern: str) -> bool:
        """Check if a subject matches a NATS pattern."""
        import re
        
        # Convert NATS pattern to regex
        # * matches a single token (no dots)
        # > matches one or more tokens (including dots)
        regex_pattern = pattern.replace('.', r'\.')  # Escape dots
        regex_pattern = regex_pattern.replace('*', r'[^.]+')  # * -> one or more non-dot chars
        regex_pattern = regex_pattern.replace('>', r'.*')  # > -> any chars including dots
        regex_pattern = f'^{regex_pattern}$'
        
        try:
            return bool(re.match(regex_pattern, subject))
        except re.error:
            # If pattern is invalid, return False
            return False


# Global database service instance
db_service = DatabaseService()
