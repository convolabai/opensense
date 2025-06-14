"""Database service for subscription management."""

import json
from typing import Any

import structlog
from sqlalchemy import and_, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.models import (
    Base,
    EventLog,
    IngestMapping,
    Subscription,
    SubscriptionEventLog,
)
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
        """Create all database tables and schema objects."""
        Base.metadata.create_all(bind=self.engine)

        # Create schema versioning table first
        self.create_schema_migrations_table()

        # Core subscription system tables
        self.create_schema_registry_table()
        self.create_event_logs_table()
        self.create_subscription_event_logs_table()
        self.create_ingest_mappings_table()
        
        # Add/update columns to existing tables
        self.add_gate_column_to_subscriptions()
        self.add_disposable_columns_to_subscriptions()
        self.add_gate_columns_to_subscription_event_logs()
        
        # Additional application tables
        self.create_application_tables()
        
        # Create foreign key constraints
        self.create_foreign_key_constraints()
        
        # Record schema version
        self.record_schema_version("1.0.0", "Initial comprehensive schema with all core and application tables")
        
        logger.info("Database schema creation completed successfully")

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

    def add_disposable_columns_to_subscriptions(self) -> None:
        """Add disposable and used columns to subscriptions table if they don't exist."""
        try:
            with self.get_session() as session:
                # Check if disposable column exists
                check_disposable_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscriptions' AND column_name='disposable'
                """)
                result = session.execute(check_disposable_sql).fetchone()

                if not result:
                    # Add disposable column if it doesn't exist
                    add_disposable_sql = text("""
                        ALTER TABLE subscriptions 
                        ADD COLUMN disposable BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                    session.execute(add_disposable_sql)
                    logger.info("Added disposable column to subscriptions table")

                # Check if used column exists
                check_used_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscriptions' AND column_name='used'
                """)
                result = session.execute(check_used_sql).fetchone()

                if not result:
                    # Add used column if it doesn't exist
                    add_used_sql = text("""
                        ALTER TABLE subscriptions 
                        ADD COLUMN used BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                    session.execute(add_used_sql)
                    logger.info("Added used column to subscriptions table")

                session.commit()

        except Exception as e:
            logger.error(
                "Failed to add disposable columns to subscriptions table",
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

        except Exception:
            logger.error(
                "Failed to add gate columns to subscription_event_logs table")
    def create_ingest_mappings_table(self) -> None:
        """Create the ingest mappings table if it doesn't exist."""
        try:
            with self.get_session() as session:
                # Create table with explicit SQL to ensure it exists
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS ingest_mappings (
                        fingerprint VARCHAR(64) PRIMARY KEY NOT NULL,
                        publisher VARCHAR(255) NOT NULL,
                        event_name VARCHAR(255) NOT NULL,
                        mapping_expr TEXT NOT NULL,
                        event_field_expr TEXT,
                        structure JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(create_table_sql)

                # Add event_field_expr column if it doesn't exist (for existing installations)
                self.add_event_field_expr_column_to_ingest_mappings(session)

                # Create indexes for better query performance
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_publisher ON ingest_mappings(publisher)",
                    "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_event_name ON ingest_mappings(event_name)",
                    "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_created_at ON ingest_mappings(created_at)",
                ]

                for index_sql in index_sqls:
                    session.execute(text(index_sql))

                session.commit()
                logger.info("Ingest mappings table ensured")
        except Exception as e:
            logger.error(
                "Failed to create ingest mappings table",
                error=str(e),
                exc_info=True
            )

    def add_event_field_expr_column_to_ingest_mappings(self, session: Session) -> None:
        """Add event_field_expr column to ingest_mappings table if it doesn't exist."""
        try:
            # Check if event_field_expr column exists
            check_column_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='ingest_mappings' AND column_name='event_field_expr'
            """)
            result = session.execute(check_column_sql).fetchone()

            if not result:
                # Add event_field_expr column if it doesn't exist
                add_column_sql = text("""
                    ALTER TABLE ingest_mappings 
                    ADD COLUMN event_field_expr TEXT
                """)
                session.execute(add_column_sql)
                logger.info("Added event_field_expr column to ingest_mappings table")

        except Exception as e:
            logger.error(
                "Failed to add event_field_expr column to ingest_mappings table",
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
                disposable=subscription_data.disposable,
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
            if update_data.disposable is not None:
                subscription.disposable = update_data.disposable

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
        """Get all active subscriptions for consumer management, excluding used disposable subscriptions."""
        with self.get_session() as session:
            subscriptions = session.query(Subscription).filter(
                and_(
                    Subscription.active,
                    # Exclude disposable subscriptions that have been used
                    ~(and_(Subscription.disposable, Subscription.used))
                )
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


    async def get_ingestion_mappings_by_structure(
        self,
        structure_fingerprint: str
    ) -> list[IngestMapping]:
        """
        Get all ingestion mappings that have the same base structure fingerprint.

        This is used for finding mappings that match the payload structure but may
        have different event field values.
        """
        with self.get_session() as session:
            # Create a custom query to find mappings with the same structure
            # We'll store the structure fingerprint separately for this lookup
            mappings = session.query(IngestMapping).all()

            # Filter mappings that have the same structure
            import hashlib

            from langhook.map.fingerprint import (
                create_canonical_string,
            )

            matching_mappings = []
            for mapping in mappings:
                # Check if the structure matches by recreating the structure fingerprint
                if mapping.structure:
                    mapping_structure_fingerprint = hashlib.sha256(
                        create_canonical_string(mapping.structure).encode('utf-8')
                    ).hexdigest()
                    if mapping_structure_fingerprint == structure_fingerprint:
                        matching_mappings.append(mapping)

            return matching_mappings

    async def get_ingestion_mapping(self, fingerprint: str) -> IngestMapping | None:
        """Get an ingestion mapping by fingerprint."""
        with self.get_session() as session:
            mapping = session.query(IngestMapping).filter(
                IngestMapping.fingerprint == fingerprint
            ).first()
            return mapping

    async def create_ingestion_mapping(
        self,
        fingerprint: str,
        publisher: str,
        event_name: str,
        mapping_expr: str,
        structure: dict[str, Any],
        event_field_expr: str | None = None
    ) -> IngestMapping:
        """Create a new ingestion mapping."""
        with self.get_session() as session:
            mapping = IngestMapping(
                fingerprint=fingerprint,
                publisher=publisher,
                event_name=event_name,
                mapping_expr=mapping_expr,
                event_field_expr=event_field_expr,
                structure=structure
            )

            session.add(mapping)
            session.commit()
            session.refresh(mapping)

            logger.info(
                "Ingest mapping created",
                fingerprint=fingerprint,
                publisher=publisher,
                event_name=event_name,
                has_event_field_expr=event_field_expr is not None
            )

            return mapping

    async def get_all_ingestion_mappings(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[IngestMapping], int]:
        """Get all ingestion mappings with pagination."""
        with self.get_session() as session:
            query = session.query(IngestMapping).order_by(IngestMapping.created_at.desc())

            total = query.count()
            mappings = query.offset(skip).limit(limit).all()

            return mappings, total

    async def delete_ingestion_mapping(self, fingerprint: str) -> bool:
        """Delete an ingestion mapping by fingerprint."""
        with self.get_session() as session:
            mapping = session.query(IngestMapping).filter(
                IngestMapping.fingerprint == fingerprint
            ).first()
            
            if not mapping:
                logger.info(
                    "Ingest mapping not found for deletion",
                    fingerprint=fingerprint
                )
                return False
            
            session.delete(mapping)
            session.commit()
            
            logger.info(
                "Ingest mapping deleted",
                fingerprint=fingerprint,
                publisher=mapping.publisher,
                event_name=mapping.event_name
            )
            
            return True

    async def mark_disposable_subscription_as_used(self, subscription_id: int) -> bool:
        """Mark a disposable subscription as used."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter(
                Subscription.id == subscription_id
            ).first()

            if not subscription:
                logger.warning(
                    "Subscription not found for marking as used",
                    subscription_id=subscription_id
                )
                return False

            if not subscription.disposable:
                logger.warning(
                    "Attempted to mark non-disposable subscription as used",
                    subscription_id=subscription_id
                )
                return False

            if subscription.used:
                logger.info(
                    "Disposable subscription already marked as used",
                    subscription_id=subscription_id
                )
                return True

            subscription.used = True
            session.commit()

            logger.info(
                "Disposable subscription marked as used",
                subscription_id=subscription_id
            )

            return True

    def create_schema_migrations_table(self) -> None:
        """Create schema migrations table for tracking database versions."""
        try:
            with self.get_session() as session:
                create_table_sql = text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        description TEXT,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                session.execute(create_table_sql)
                
                # Create index for version lookups
                index_sql = text("CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version)")
                session.execute(index_sql)
                
                session.commit()
                logger.info("Schema migrations table ensured")
        except Exception as e:
            logger.error("Failed to create schema migrations table", error=str(e), exc_info=True)

    def record_schema_version(self, version: str, description: str) -> None:
        """Record schema version in migrations table."""
        try:
            with self.get_session() as session:
                # Check if version already exists
                existing = session.execute(text(
                    "SELECT version FROM schema_migrations WHERE version = :version"
                ), {"version": version}).fetchone()

                if not existing:
                    session.execute(text("""
                        INSERT INTO schema_migrations (version, description)
                        VALUES (:version, :description)
                    """), {"version": version, "description": description})
                    session.commit()
                    logger.info("Schema version recorded", version=version, description=description)
                else:
                    logger.info("Schema version already exists", version=version)
        except Exception as e:
            logger.error("Failed to record schema version", version=version, error=str(e), exc_info=True)

    def create_application_tables(self) -> None:
        """Create additional application tables (users, projects, etc.)."""
        try:
            with self.get_session() as session:
                # Users table for authentication and user management
                users_sql = text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        email VARCHAR(255) NOT NULL UNIQUE,
                        password_hash VARCHAR(255),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(users_sql)

                # Projects table for project management
                projects_sql = text("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        owner_id INTEGER,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(projects_sql)

                # Snippets table for code/configuration snippets
                snippets_sql = text("""
                    CREATE TABLE IF NOT EXISTS snippets (
                        id SERIAL PRIMARY KEY,
                        project_id INTEGER,
                        name VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        language VARCHAR(50),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(snippets_sql)

                # Responses table for tracking API responses
                responses_sql = text("""
                    CREATE TABLE IF NOT EXISTS responses (
                        id SERIAL PRIMARY KEY,
                        request_id VARCHAR(255),
                        endpoint VARCHAR(255),
                        method VARCHAR(10),
                        status_code INTEGER,
                        response_data JSONB,
                        processing_time_ms INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                session.execute(responses_sql)

                # Sessions table for user sessions
                sessions_sql = text("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL UNIQUE,
                        user_id INTEGER,
                        data JSONB,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
                session.execute(sessions_sql)

                # Logs table for general application logging
                logs_sql = text("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id SERIAL PRIMARY KEY,
                        level VARCHAR(20) NOT NULL,
                        message TEXT NOT NULL,
                        context JSONB,
                        source VARCHAR(255),
                        user_id INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                session.execute(logs_sql)

                # Create indexes for application tables
                app_indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                    "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id)",
                    "CREATE INDEX IF NOT EXISTS idx_projects_is_active ON projects(is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_snippets_project_id ON snippets(project_id)",
                    "CREATE INDEX IF NOT EXISTS idx_snippets_is_active ON snippets(is_active)",
                    "CREATE INDEX IF NOT EXISTS idx_responses_request_id ON responses(request_id)",
                    "CREATE INDEX IF NOT EXISTS idx_responses_endpoint ON responses(endpoint)",
                    "CREATE INDEX IF NOT EXISTS idx_responses_created_at ON responses(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
                    "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
                    "CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source)",
                    "CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)",
                ]

                for index_sql in app_indexes:
                    session.execute(text(index_sql))

                session.commit()
                logger.info("Application tables ensured")
        except Exception as e:
            logger.error("Failed to create application tables", error=str(e), exc_info=True)

    def create_foreign_key_constraints(self) -> None:
        """Create foreign key constraints between tables."""
        try:
            with self.get_session() as session:
                constraints = [
                    ("fk_projects_owner_id", "ALTER TABLE projects ADD CONSTRAINT fk_projects_owner_id FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL"),
                    ("fk_snippets_project_id", "ALTER TABLE snippets ADD CONSTRAINT fk_snippets_project_id FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE"),
                    ("fk_sessions_user_id", "ALTER TABLE sessions ADD CONSTRAINT fk_sessions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"),
                    ("fk_logs_user_id", "ALTER TABLE logs ADD CONSTRAINT fk_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"),
                ]

                for constraint_name, constraint_sql in constraints:
                    # Check if constraint already exists
                    check_sql = text("""
                        SELECT constraint_name FROM information_schema.table_constraints
                        WHERE constraint_name = :constraint_name
                    """)
                    result = session.execute(check_sql, {"constraint_name": constraint_name}).fetchone()
                    
                    if not result:
                        try:
                            session.execute(text(constraint_sql))
                            session.commit()
                            logger.info("Foreign key constraint created", constraint=constraint_name)
                        except Exception as e:
                            # If constraint creation fails (e.g., due to existing data), log and continue
                            logger.warning("Failed to create foreign key constraint", 
                                         constraint=constraint_name, error=str(e))
                    else:
                        logger.info("Foreign key constraint already exists", constraint=constraint_name)

        except Exception as e:
            logger.error("Failed to create foreign key constraints", error=str(e), exc_info=True)


# Global database service instance
db_service = DatabaseService()
