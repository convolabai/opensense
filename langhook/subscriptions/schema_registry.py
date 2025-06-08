"""Service for managing event schema registry."""

from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import EventSchemaRegistry

logger = structlog.get_logger("langhook")


class SchemaRegistryService:
    """Service for managing the event schema registry."""

    async def register_event_schema(
        self, publisher: str, resource_type: str, action: str
    ) -> None:
        """
        Register a new event schema combination with upsert logic.

        Args:
            publisher: Event publisher (e.g., 'github', 'stripe')
            resource_type: Resource type (e.g., 'pull_request', 'refund')
            action: Action type (e.g., 'created', 'updated', 'deleted')
        """
        try:
            with db_service.get_session() as session:
                # Use INSERT ... ON CONFLICT DO NOTHING for performance
                insert_stmt = text("""
                    INSERT INTO event_schema_registry (publisher, resource_type, action)
                    VALUES (:publisher, :resource_type, :action)
                    ON CONFLICT (publisher, resource_type, action) DO NOTHING
                """)

                session.execute(
                    insert_stmt,
                    {
                        "publisher": publisher,
                        "resource_type": resource_type,
                        "action": action,
                    },
                )
                session.commit()

                logger.debug(
                    "Schema registry entry processed",
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action,
                )

        except SQLAlchemyError as e:
            logger.error(
                "Failed to register event schema",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True,
            )
            # Don't raise - schema registry failures shouldn't break event processing
        except Exception as e:
            logger.error(
                "Unexpected error in schema registry",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True,
            )

    async def get_schema_summary(self) -> dict[str, Any]:
        """
        Get a structured summary of all registered schemas.

        Returns:
            Dictionary with publishers, resource_types grouped by publisher, and actions
        """
        try:
            with db_service.get_session() as session:
                # Get all distinct entries
                all_entries = session.query(EventSchemaRegistry).all()

                # Build response structure
                publishers = list({entry.publisher for entry in all_entries})
                publishers.sort()

                resource_types: dict[str, list[str]] = {}
                actions = list({entry.action for entry in all_entries})
                actions.sort()

                # Group resource types by publisher
                for publisher in publishers:
                    publisher_entries = [
                        e for e in all_entries if e.publisher == publisher
                    ]
                    publisher_resource_types = list(
                        {e.resource_type for e in publisher_entries}
                    )
                    publisher_resource_types.sort()
                    resource_types[publisher] = publisher_resource_types

                return {
                    "publishers": publishers,
                    "resource_types": resource_types,
                    "actions": actions,
                }

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve schema summary", error=str(e), exc_info=True
            )
            return {"publishers": [], "resource_types": {}, "actions": []}
        except Exception as e:
            logger.error(
                "Unexpected error retrieving schema summary",
                error=str(e),
                exc_info=True,
            )
            return {"publishers": [], "resource_types": {}, "actions": []}


# Global schema registry service instance
schema_registry_service = SchemaRegistryService()
