#!/usr/bin/env python3
"""
Database creation script for LangHook.

This script creates all required tables, indexes, and constraints that LangHook
depends on. It includes idempotent checks and schema versioning to support
safe database initialization and evolution.

Usage:
    python database_creation.py [--postgres-dsn=<dsn>] [--dry-run]

Example:
    python database_creation.py --postgres-dsn="postgresql://user:pass@localhost:5432/langhook"
"""

import argparse
import sys

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Schema version for tracking migrations
CURRENT_SCHEMA_VERSION = "1.0.0"

logger = structlog.get_logger("langhook.database_creation")


class DatabaseCreator:
    """Database creation and schema management service."""

    def __init__(self, postgres_dsn: str, dry_run: bool = False):
        """Initialize database creator.

        Args:
            postgres_dsn: PostgreSQL connection string
            dry_run: If True, only print SQL statements without executing
        """
        self.postgres_dsn = postgres_dsn
        self.dry_run = dry_run
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker | None = None

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.engine = create_engine(
                self.postgres_dsn,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "langhook_database_creation",
                }
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info("Database connection established", dsn=self.postgres_dsn)

        except Exception as e:
            logger.error("Failed to connect to database", error=str(e), dsn=self.postgres_dsn)
            raise

    def execute_sql(self, sql: str, description: str) -> None:
        """Execute SQL statement with logging.

        Args:
            sql: SQL statement to execute
            description: Human readable description of the operation
        """
        if self.dry_run:
            print(f"[DRY RUN] {description}:")
            print(sql)
            print("-" * 60)
            return

        try:
            with self.SessionLocal() as session:
                session.execute(text(sql))
                session.commit()
            logger.info("SQL executed successfully", description=description)
        except Exception as e:
            logger.error("Failed to execute SQL", description=description, error=str(e))
            raise

    def create_schema_migrations_table(self) -> None:
        """Create schema migrations table for version tracking."""
        sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                checksum VARCHAR(64)
            )
        """
        self.execute_sql(sql, "Create schema_migrations table")

        # Create index for version lookups
        index_sql = "CREATE INDEX IF NOT EXISTS idx_schema_migrations_version ON schema_migrations(version)"
        self.execute_sql(index_sql, "Create index on schema_migrations.version")

    def record_schema_version(self, version: str, description: str) -> None:
        """Record schema version in migrations table.

        Args:
            version: Schema version string
            description: Description of the schema changes
        """
        if self.dry_run:
            print(f"[DRY RUN] Record schema version {version}: {description}")
            return

        try:
            with self.SessionLocal() as session:
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
            logger.error("Failed to record schema version", version=version, error=str(e))
            raise

    def create_subscriptions_table(self) -> None:
        """Create subscriptions table."""
        sql = """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                subscriber_id VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                pattern VARCHAR(255) NOT NULL,
                channel_type VARCHAR(50),
                channel_config TEXT,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                disposable BOOLEAN NOT NULL DEFAULT FALSE,
                used BOOLEAN NOT NULL DEFAULT FALSE,
                gate JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """
        self.execute_sql(sql, "Create subscriptions table")

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_subscriber_id ON subscriptions(subscriber_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_disposable_used ON subscriptions(disposable, used)",
        ]

        for index_sql in indexes:
            self.execute_sql(index_sql, f"Create index: {index_sql.split('idx_')[1].split(' ')[0]}")

    def create_event_schema_registry_table(self) -> None:
        """Create event_schema_registry table."""
        sql = """
            CREATE TABLE IF NOT EXISTS event_schema_registry (
                publisher VARCHAR(255) NOT NULL,
                resource_type VARCHAR(255) NOT NULL,
                action VARCHAR(255) NOT NULL,
                PRIMARY KEY (publisher, resource_type, action)
            )
        """
        self.execute_sql(sql, "Create event_schema_registry table")

    def create_event_logs_table(self) -> None:
        """Create event_logs table."""
        sql = """
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
        """
        self.execute_sql(sql, "Create event_logs table")

        # Create indexes for query performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_event_logs_event_id ON event_logs(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_source ON event_logs(source)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_publisher ON event_logs(publisher)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_resource_type ON event_logs(resource_type)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_resource_id ON event_logs(resource_id)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_action ON event_logs(action)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_logged_at ON event_logs(logged_at)",
        ]

        for index_sql in indexes:
            self.execute_sql(index_sql, f"Create index: {index_sql.split('idx_')[1].split(' ')[0]}")

    def create_subscription_event_logs_table(self) -> None:
        """Create subscription_event_logs table."""
        sql = """
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
                gate_passed BOOLEAN,
                gate_reason TEXT,
                logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        self.execute_sql(sql, "Create subscription_event_logs table")

        # Create indexes for query performance
        indexes = [
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

        for index_sql in indexes:
            self.execute_sql(index_sql, f"Create index: {index_sql.split('idx_')[1].split(' ')[0]}")

    def create_ingest_mappings_table(self) -> None:
        """Create ingest_mappings table."""
        sql = """
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
        """
        self.execute_sql(sql, "Create ingest_mappings table")

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_publisher ON ingest_mappings(publisher)",
            "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_event_name ON ingest_mappings(event_name)",
            "CREATE INDEX IF NOT EXISTS idx_ingest_mappings_created_at ON ingest_mappings(created_at)",
        ]

        for index_sql in indexes:
            self.execute_sql(index_sql, f"Create index: {index_sql.split('idx_')[1].split(' ')[0]}")

    def create_application_tables(self) -> None:
        """Create additional application tables mentioned in requirements."""

        # Users table for user management
        users_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                full_name VARCHAR(255),
                hashed_password VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """
        self.execute_sql(users_sql, "Create users table")

        # Projects table for project management
        projects_sql = """
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                owner_id INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """
        self.execute_sql(projects_sql, "Create projects table")

        # Snippets table for code/configuration snippets
        snippets_sql = """
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
        """
        self.execute_sql(snippets_sql, "Create snippets table")

        # Responses table for tracking API responses
        responses_sql = """
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
        """
        self.execute_sql(responses_sql, "Create responses table")

        # Sessions table for user sessions
        sessions_sql = """
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL UNIQUE,
                user_id INTEGER,
                data JSONB,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """
        self.execute_sql(sessions_sql, "Create sessions table")

        # Logs table for general application logging
        logs_sql = """
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                level VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                context JSONB,
                source VARCHAR(255),
                user_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        self.execute_sql(logs_sql, "Create logs table")

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
            self.execute_sql(index_sql, f"Create index: {index_sql.split('idx_')[1].split(' ')[0]}")

    def create_foreign_key_constraints(self) -> None:
        """Create foreign key constraints between tables."""
        constraints = [
            "ALTER TABLE projects ADD CONSTRAINT fk_projects_owner_id FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL",
            "ALTER TABLE snippets ADD CONSTRAINT fk_snippets_project_id FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE",
            "ALTER TABLE sessions ADD CONSTRAINT fk_sessions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
            "ALTER TABLE logs ADD CONSTRAINT fk_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL",
        ]

        for constraint_sql in constraints:
            # Add IF NOT EXISTS equivalent for constraints by checking first
            constraint_name = constraint_sql.split('CONSTRAINT ')[1].split(' ')[0]
            check_sql = f"""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE constraint_name = '{constraint_name}'
            """

            if self.dry_run:
                print(f"[DRY RUN] Check and create foreign key constraint: {constraint_name}")
                print(constraint_sql)
                print("-" * 60)
                continue

            try:
                with self.SessionLocal() as session:
                    result = session.execute(text(check_sql)).fetchone()
                    if not result:
                        session.execute(text(constraint_sql))
                        session.commit()
                        logger.info("Foreign key constraint created", constraint=constraint_name)
                    else:
                        logger.info("Foreign key constraint already exists", constraint=constraint_name)
            except Exception as e:
                # If constraint creation fails (e.g., due to existing data), log and continue
                logger.warning("Failed to create foreign key constraint",
                             constraint=constraint_name, error=str(e))

    def create_all_tables(self) -> None:
        """Create all required database tables and schema objects."""
        logger.info("Starting database schema creation", version=CURRENT_SCHEMA_VERSION, dry_run=self.dry_run)

        try:
            # Create schema versioning table first
            self.create_schema_migrations_table()

            # Create core subscription system tables
            self.create_subscriptions_table()
            self.create_event_schema_registry_table()
            self.create_event_logs_table()
            self.create_subscription_event_logs_table()
            self.create_ingest_mappings_table()

            # Create additional application tables
            self.create_application_tables()

            # Create foreign key constraints
            self.create_foreign_key_constraints()

            # Record schema version
            self.record_schema_version(
                CURRENT_SCHEMA_VERSION,
                "Initial schema with all core and application tables"
            )

            logger.info("Database schema creation completed successfully", version=CURRENT_SCHEMA_VERSION)

        except Exception as e:
            logger.error("Database schema creation failed", error=str(e))
            raise

    def check_database_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).fetchone()
                logger.info("Database connection test successful", db_version=result[0] if result else "unknown")
                return True
        except Exception as e:
            logger.error("Database connection test failed", error=str(e))
            return False


def main():
    """Main function for command line execution."""
    parser = argparse.ArgumentParser(description="Create LangHook database schema")
    parser.add_argument(
        "--postgres-dsn",
        default="postgresql://langhook:langhook@localhost:5432/langhook",
        help="PostgreSQL connection string"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL statements without executing them"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
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
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    try:
        creator = DatabaseCreator(postgres_dsn=args.postgres_dsn, dry_run=args.dry_run)

        if not args.dry_run:
            creator.connect()
            if not creator.check_database_connection():
                logger.error("Database connection check failed")
                sys.exit(1)

        creator.create_all_tables()

        if args.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN COMPLETED - No changes were made to the database")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("DATABASE CREATION COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print(f"Schema version: {CURRENT_SCHEMA_VERSION}")
            print("All tables, indexes, and constraints have been created.")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Database creation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Database creation failed", error=str(e))
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

