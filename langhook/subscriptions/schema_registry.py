"""Service for managing event schema registry."""

from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import EventLog, EventSchemaRegistry

logger = structlog.get_logger("langhook")


class SchemaRegistryService:
    """Service for managing the event schema registry."""

    async def register_event_schema(
        self,
        publisher: str,
        resource_type: str,
        action: str
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

                session.execute(insert_stmt, {
                    'publisher': publisher,
                    'resource_type': resource_type,
                    'action': action
                })
                session.commit()

                logger.debug(
                    "Schema registry entry processed",
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action
                )

        except SQLAlchemyError as e:
            logger.error(
                "Failed to register event schema",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True
            )
            # Don't raise - schema registry failures shouldn't break event processing
        except Exception as e:
            logger.error(
                "Unexpected error in schema registry",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True
            )

    async def get_schema_summary(self, include_samples: bool = False) -> dict[str, Any]:
        """
        Get a structured summary of all registered schemas.

        Args:
            include_samples: Whether to include sample event data for each schema combination

        Returns:
            Dictionary with publishers, resource_types grouped by publisher, actions,
            granular publisher_resource_actions showing exact combinations, and optionally
            sample_events with example data for each publisher.resource_type combination
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
                    publisher_entries = [e for e in all_entries if e.publisher == publisher]
                    publisher_resource_types = list({e.resource_type for e in publisher_entries})
                    publisher_resource_types.sort()
                    resource_types[publisher] = publisher_resource_types

                # Build granular publisher+resource_type -> actions mapping
                publisher_resource_actions: dict[str, dict[str, list[str]]] = {}
                for publisher in publishers:
                    publisher_resource_actions[publisher] = {}
                    publisher_entries = [e for e in all_entries if e.publisher == publisher]

                    # Group by resource type within this publisher
                    resource_types_for_publisher = list({e.resource_type for e in publisher_entries})
                    for resource_type in resource_types_for_publisher:
                        resource_entries = [e for e in publisher_entries if e.resource_type == resource_type]
                        resource_actions = list({e.action for e in resource_entries})
                        resource_actions.sort()
                        publisher_resource_actions[publisher][resource_type] = resource_actions

                result = {
                    "publishers": publishers,
                    "resource_types": resource_types,
                    "actions": actions,
                    "publisher_resource_actions": publisher_resource_actions
                }

                # Add sample events if requested
                if include_samples:
                    sample_events = await self._get_sample_events(session, publisher_resource_actions)
                    result["sample_events"] = sample_events

                return result

        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve schema summary",
                error=str(e),
                exc_info=True
            )
            return {
                "publishers": [],
                "resource_types": {},
                "actions": [],
                "publisher_resource_actions": {}
            }
        except Exception as e:
            logger.error(
                "Unexpected error retrieving schema summary",
                error=str(e),
                exc_info=True
            )
            return {
                "publishers": [],
                "resource_types": {},
                "actions": [],
                "publisher_resource_actions": {}
            }

    async def _get_sample_events(self, session, publisher_resource_actions: dict) -> dict[str, dict[str, Any]]:
        """
        Get sample event data for each publisher.resource_type combination.

        Args:
            session: Database session
            publisher_resource_actions: Dictionary of publisher -> resource_type -> actions

        Returns:
            Dictionary with publisher.resource_type keys and sample event data as values
        """
        sample_events = {}

        try:
            # Get a sample event for each publisher.resource_type combination
            for publisher, resource_types in publisher_resource_actions.items():
                for resource_type in resource_types.keys():
                    # Query for a recent sample event
                    sample_event = session.query(EventLog).filter(
                        EventLog.publisher == publisher,
                        EventLog.resource_type == resource_type
                    ).order_by(EventLog.logged_at.desc()).first()

                    if sample_event:
                        key = f"{publisher}.{resource_type}"
                        sample_events[key] = {
                            "resource_id": sample_event.resource_id,
                            "action": sample_event.action,
                            "canonical_data": sample_event.canonical_data,
                            "subject": sample_event.subject
                        }

        except SQLAlchemyError as e:
            logger.warning(
                "Failed to fetch sample events for schema summary",
                error=str(e)
            )
            # Return empty samples on error - this shouldn't break the main functionality

        return sample_events

    async def delete_publisher(self, publisher: str) -> bool:
        """
        Delete all schema entries for a publisher.

        Args:
            publisher: Publisher name to delete

        Returns:
            bool: True if any entries were deleted, False if publisher didn't exist
        """
        try:
            with db_service.get_session() as session:
                # Count entries to delete
                count_query = session.query(EventSchemaRegistry).filter(
                    EventSchemaRegistry.publisher == publisher
                ).count()

                if count_query == 0:
                    logger.info(
                        "Publisher not found for deletion",
                        publisher=publisher
                    )
                    return False

                # Delete entries
                delete_query = session.query(EventSchemaRegistry).filter(
                    EventSchemaRegistry.publisher == publisher
                )
                deleted_count = delete_query.delete()
                session.commit()

                logger.info(
                    "Publisher deleted from schema registry",
                    publisher=publisher,
                    deleted_count=deleted_count
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                "Failed to delete publisher from schema registry",
                publisher=publisher,
                error=str(e),
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error deleting publisher from schema registry",
                publisher=publisher,
                error=str(e),
                exc_info=True
            )
            raise

    async def delete_resource_type(self, publisher: str, resource_type: str) -> bool:
        """
        Delete all schema entries for a publisher/resource_type combination.

        Args:
            publisher: Publisher name
            resource_type: Resource type to delete

        Returns:
            bool: True if any entries were deleted, False if combination didn't exist
        """
        try:
            with db_service.get_session() as session:
                # Count entries to delete
                count_query = session.query(EventSchemaRegistry).filter(
                    EventSchemaRegistry.publisher == publisher,
                    EventSchemaRegistry.resource_type == resource_type
                ).count()

                if count_query == 0:
                    logger.info(
                        "Resource type not found for deletion",
                        publisher=publisher,
                        resource_type=resource_type
                    )
                    return False

                # Delete entries
                delete_query = session.query(EventSchemaRegistry).filter(
                    EventSchemaRegistry.publisher == publisher,
                    EventSchemaRegistry.resource_type == resource_type
                )
                deleted_count = delete_query.delete()
                session.commit()

                logger.info(
                    "Resource type deleted from schema registry",
                    publisher=publisher,
                    resource_type=resource_type,
                    deleted_count=deleted_count
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                "Failed to delete resource type from schema registry",
                publisher=publisher,
                resource_type=resource_type,
                error=str(e),
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error deleting resource type from schema registry",
                publisher=publisher,
                resource_type=resource_type,
                error=str(e),
                exc_info=True
            )
            raise

    async def delete_action(self, publisher: str, resource_type: str, action: str) -> bool:
        """
        Delete a specific schema entry.

        Args:
            publisher: Publisher name
            resource_type: Resource type
            action: Action to delete

        Returns:
            bool: True if entry was deleted, False if it didn't exist
        """
        try:
            with db_service.get_session() as session:
                # Find the specific entry
                entry = session.query(EventSchemaRegistry).filter(
                    EventSchemaRegistry.publisher == publisher,
                    EventSchemaRegistry.resource_type == resource_type,
                    EventSchemaRegistry.action == action
                ).first()

                if not entry:
                    logger.info(
                        "Action not found for deletion",
                        publisher=publisher,
                        resource_type=resource_type,
                        action=action
                    )
                    return False

                # Delete the entry
                session.delete(entry)
                session.commit()

                logger.info(
                    "Action deleted from schema registry",
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action
                )
                return True

        except SQLAlchemyError as e:
            logger.error(
                "Failed to delete action from schema registry",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error deleting action from schema registry",
                publisher=publisher,
                resource_type=resource_type,
                action=action,
                error=str(e),
                exc_info=True
            )
            raise


# Global schema registry service instance
schema_registry_service = SchemaRegistryService()
