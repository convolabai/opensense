"""Database service for subscription management."""

import json

import structlog
from sqlalchemy import and_, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.models import Base, Subscription, EventLog, SubscriptionEventLog, WebhookMapping
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
        # Explicitly ensure subscription event logs table exists
        self.create_subscription_event_logs_table()
        # Add gate column to subscriptions table if it doesn't exist
        self.add_gate_column_to_subscriptions()
        # Add gate evaluation columns to subscription event logs table if they don't exist
        self.add_gate_columns_to_subscription_event_logs()
        # Explicitly ensure webhook mappings table exists
        self.create_webhook_mappings_table()
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

    def create_subscription_event_logs_table(self) -> None:
        """Create the subscription event logs table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Create table with explicit SQL to ensure it exists
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS subscription_event_logs (
                        id SERIAL PRIMARY KEY,
                        subscription_id INTEGER NOT NULL,
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
                        webhook_sent BOOLEAN NOT NULL DEFAULT FALSE,
                        webhook_response_status INTEGER,
                        logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                session.execute(create_table_sql)
                
                # Create indexes for better query performance
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_subscription_id ON subscription_event_logs(subscription_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_event_id ON subscription_event_logs(event_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_source ON subscription_event_logs(source)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_publisher ON subscription_event_logs(publisher)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_resource_type ON subscription_event_logs(resource_type)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_resource_id ON subscription_event_logs(resource_id)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_action ON subscription_event_logs(action)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_timestamp ON subscription_event_logs(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_subscription_event_logs_logged_at ON subscription_event_logs(logged_at)",
                ]
                
                for index_sql in index_sqls:
                    session.execute(text(index_sql))
                
                session.commit()
                logger.info("Subscription event logs table ensured")
        except Exception as e:
            logger.error(
                "Failed to create subscription event logs table",
                error=str(e),
                exc_info=True
            )

    def add_gate_column_to_subscriptions(self) -> None:
        """Add gate column to subscriptions table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Check if column exists
                check_column_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscriptions' AND column_name='gate'
                """)
                result = session.execute(check_column_sql).fetchone()
                
                if not result:
                    # Add column if it doesn't exist
                    add_column_sql = text("""
                        ALTER TABLE subscriptions 
                        ADD COLUMN gate JSONB
                    """)
                    session.execute(add_column_sql)
                    session.commit()
                    logger.info("Added gate column to subscriptions table")
                else:
                    logger.info("Gate column already exists in subscriptions table")
        except Exception as e:
            logger.error(
                "Failed to add gate column to subscriptions table",
                error=str(e),
                exc_info=True
            )

    def add_gate_columns_to_subscription_event_logs(self) -> None:
        """Add gate evaluation columns to subscription_event_logs table if they don't exist."""
        try:
            with self.get_session() as session:
                # Check if gate_passed column exists
                check_gate_passed_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscription_event_logs' AND column_name='gate_passed'
                """)
                result = session.execute(check_gate_passed_sql).fetchone()
                
                if not result:
                    # Add gate_passed column if it doesn't exist
                    add_gate_passed_sql = text("""
                        ALTER TABLE subscription_event_logs 
                        ADD COLUMN gate_passed BOOLEAN
                    """)
                    session.execute(add_gate_passed_sql)
                    logger.info("Added gate_passed column to subscription_event_logs table")
                
                # Check if gate_reason column exists
                check_gate_reason_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscription_event_logs' AND column_name='gate_reason'
                """)
                result = session.execute(check_gate_reason_sql).fetchone()
                
                if not result:
                    # Add gate_reason column if it doesn't exist
                    add_gate_reason_sql = text("""
                        ALTER TABLE subscription_event_logs 
                        ADD COLUMN gate_reason TEXT
                    """)
                    session.execute(add_gate_reason_sql)
                    logger.info("Added gate_reason column to subscription_event_logs table")
                
                session.commit()
                
        except Exception as e:
            logger.error(
                "Failed to add gate columns to subscription_event_logs table")
    def create_webhook_mappings_table(self) -> None:
        """Create the webhook mappings table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Create table with explicit SQL to ensure it exists
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS webhook_mappings (
                        fingerprint VARCHAR(64) PRIMARY KEY NOT NULL,
                        publisher VARCHAR(255) NOT NULL,
                        event_name VARCHAR(255) NOT NULL,
                        mapping_expr TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(create_table_sql)
                
                # Create indexes for better query performance
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_webhook_mappings_publisher ON webhook_mappings(publisher)",
                    "CREATE INDEX IF NOT EXISTS idx_webhook_mappings_event_name ON webhook_mappings(event_name)",
                    "CREATE INDEX IF NOT EXISTS idx_webhook_mappings_created_at ON webhook_mappings(created_at)",
                ]
                
                for index_sql in index_sqls:
                    session.execute(text(index_sql))
                
                session.commit()
                logger.info("Webhook mappings table ensured")
        except Exception as e:
            logger.error(
                "Failed to create webhook mappings table",
                error=str(e),
                exc_info=True
            )

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def _parse_subscription_data(self, subscription: Subscription) -> None:
        """Parse JSON fields in subscription back to Python objects."""
        if subscription.channel_config:
            subscription.channel_config = json.loads(subscription.channel_config)
        # gate field is already stored as JSON, no need to parse

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
                gate=subscription_data.gate.model_dump() if subscription_data.gate else None,
                active=True
            )

            session.add(subscription)
            session.commit()
            session.refresh(subscription)

            # Parse the channel_config JSON back to dict for response if it exists
            self._parse_subscription_data(subscription)

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
                self._parse_subscription_data(subscription)

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
                self._parse_subscription_data(subscription)

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
            if update_data.gate is not None:
                subscription.gate = update_data.gate.model_dump()
            if update_data.active is not None:
                subscription.active = update_data.active

            session.commit()
            session.refresh(subscription)

            # Parse the channel_config JSON if it exists
            self._parse_subscription_data(subscription)

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

            # Parse channel_config JSON for each subscription if it exists
            for subscription in subscriptions:
                self._parse_subscription_data(subscription)

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
        subscription_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[SubscriptionEventLog], int]:
        """Get subscription event logs with pagination."""
        with self.get_session() as session:
            query = session.query(SubscriptionEventLog).filter(
                SubscriptionEventLog.subscription_id == subscription_id
            ).order_by(SubscriptionEventLog.logged_at.desc())

            total = query.count()
            subscription_events = query.offset(skip).limit(limit).all()

            return subscription_events, total


    async def get_ingestion_mapping(self, fingerprint: str) -> WebhookMapping | None:
        """Get an ingestion mapping by fingerprint."""
        with self.get_session() as session:
            mapping = session.query(WebhookMapping).filter(
                WebhookMapping.fingerprint == fingerprint
            ).first()
            return mapping

    async def create_ingestion_mapping(
        self,
        fingerprint: str,
        publisher: str,
        event_name: str,
        mapping_expr: str
    ) -> WebhookMapping:
        """Create a new ingestion mapping."""
        with self.get_session() as session:
            mapping = WebhookMapping(
                fingerprint=fingerprint,
                publisher=publisher,
                event_name=event_name,
                mapping_expr=mapping_expr
            )

            session.add(mapping)
            session.commit()
            session.refresh(mapping)

            logger.info(
                "Webhook mapping created",
                fingerprint=fingerprint,
                publisher=publisher,
                event_name=event_name
            )

            return mapping


# Global database service instance
db_service = DatabaseService()
