"""Subscription consumer service for real-time event processing."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
import httpx
from sqlalchemy.exc import SQLAlchemyError

from langhook.core.nats import BaseNATSConsumer
from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import SubscriptionEventLog, Subscription
from langhook.subscriptions.gate import llm_gate_service

logger = structlog.get_logger("langhook")


class SubscriptionConsumer(BaseNATSConsumer):
    """NATS consumer for a specific subscription."""

    def __init__(self, subscription: Subscription) -> None:
        self.subscription = subscription
        
        super().__init__(
            nats_url=subscription_settings.nats_url,
            stream_name=subscription_settings.nats_stream_events,
            consumer_name=f"{subscription_settings.nats_consumer_group}_sub_{subscription.id}",
            filter_subject=subscription.pattern,  # Use the LLM-generated pattern directly
            message_handler=self._handle_subscription_event,
        )

    async def _handle_subscription_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle an event that matches this subscription.

        Args:
            event_data: CloudEvent containing canonical data
        """
        try:
            # Extract CloudEvent metadata
            event_id = event_data.get("id")
            source = event_data.get("source")
            subject = event_data.get("subject", "")
            
            # Extract canonical data from CloudEvent
            canonical_data = event_data.get("data", {})
            
            if not canonical_data:
                logger.warning(
                    "No canonical data found in subscription event", 
                    event_id=event_id,
                    subscription_id=self.subscription.id
                )
                return

            # Extract canonical fields
            publisher = canonical_data.get("publisher")
            resource = canonical_data.get("resource", {})
            resource_type = resource.get("type")
            resource_id = str(resource.get("id", ""))
            action = canonical_data.get("action")
            
            # Parse timestamp
            timestamp_str = canonical_data.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Extract raw payload if available
            raw_payload = canonical_data.get("payload")

            # Validate required fields
            if not all([event_id, source, publisher, resource_type, action]):
                logger.warning(
                    "Missing required fields for subscription event logging",
                    event_id=event_id,
                    source=source,
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action,
                    subscription_id=self.subscription.id
                )
                return

            # Evaluate LLM gate if enabled
            gate_passed = None  # None means gate not enabled
            gate_reason = None
            
            if self.subscription.gate and self.subscription.gate.get("enabled", False):
                gate_passed, gate_reason = await llm_gate_service.evaluate_event(
                    event_data=canonical_data,
                    gate_config=self.subscription.gate,
                    subscription_id=self.subscription.id
                )
                
                if not gate_passed:
                    logger.info(
                        "Event blocked by LLM gate",
                        subscription_id=self.subscription.id,
                        event_id=event_id,
                        reason=gate_reason
                    )
                    # Still log the event but don't send webhook
                    # Create subscription event log entry (webhook_sent will be False)
                    subscription_event_log = SubscriptionEventLog(
                        subscription_id=self.subscription.id,
                        event_id=event_id,
                        source=source,
                        subject=subject,
                        publisher=publisher,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=action,
                        canonical_data=canonical_data,
                        raw_payload=raw_payload,
                        timestamp=timestamp,
                        webhook_sent=False,
                        webhook_response_status=None,
                        gate_passed=gate_passed,
                        gate_reason=gate_reason
                    )
                    await self._save_subscription_event_log(subscription_event_log)
                    return

            # Send webhook if configured and gate passed
            webhook_sent = False
            webhook_status = None
            if self.subscription.channel_type == "webhook" and self.subscription.channel_config:
                webhook_sent, webhook_status = await self._send_webhook(canonical_data)

            # Create subscription event log entry
            subscription_event_log = SubscriptionEventLog(
                subscription_id=self.subscription.id,
                event_id=event_id,
                source=source,
                subject=subject,
                publisher=publisher,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                canonical_data=canonical_data,
                raw_payload=raw_payload,
                timestamp=timestamp,
                webhook_sent=webhook_sent,
                webhook_response_status=webhook_status,
                gate_passed=gate_passed,
                gate_reason=gate_reason
            )

            # Save to database
            await self._save_subscription_event_log(subscription_event_log)

            # Mark disposable subscription as used after successful event processing
            if self.subscription.disposable:
                await self._mark_subscription_as_used()

            logger.debug(
                "Subscription event logged successfully",
                event_id=event_id,
                subscription_id=self.subscription.id,
                webhook_sent=webhook_sent,
                webhook_status=webhook_status,
                gate_passed=gate_passed,
                gate_reason=gate_reason
            )

        except SQLAlchemyError as e:
            logger.error(
                "Database error while logging subscription event",
                event_id=event_data.get("id"),
                subscription_id=self.subscription.id,
                error=str(e),
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "Unexpected error while handling subscription event",
                event_id=event_data.get("id"),
                subscription_id=self.subscription.id,
                error=str(e),
                exc_info=True
            )

    async def _save_subscription_event_log(self, subscription_event_log: SubscriptionEventLog) -> None:
        """Save subscription event log to database."""
        try:
            with db_service.get_session() as session:
                session.add(subscription_event_log)
                session.commit()
        except SQLAlchemyError as e:
            logger.error(
                "Database error while logging subscription event",
                event_id=subscription_event_log.event_id,
                subscription_id=subscription_event_log.subscription_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def _send_webhook(self, canonical_data: Dict[str, Any]) -> tuple[bool, int | None]:
        """
        Send webhook notification for the event.

        Args:
            canonical_data: The canonical event data to send

        Returns:
            Tuple of (webhook_sent: bool, status_code: int | None)
        """
        try:
            if not self.subscription.channel_config:
                return False, None

            # Parse channel config
            channel_config = json.loads(self.subscription.channel_config) if isinstance(self.subscription.channel_config, str) else self.subscription.channel_config
            webhook_url = channel_config.get("url")

            if not webhook_url:
                logger.warning(
                    "No webhook URL configured for subscription",
                    subscription_id=self.subscription.id
                )
                return False, None

            # Send webhook
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook_url,
                    json=canonical_data,
                    headers={"Content-Type": "application/json"}
                )

                logger.debug(
                    "Webhook sent",
                    subscription_id=self.subscription.id,
                    webhook_url=webhook_url,
                    status_code=response.status_code
                )

                return True, response.status_code

        except httpx.TimeoutException:
            logger.warning(
                "Webhook timeout",
                subscription_id=self.subscription.id,
                webhook_url=webhook_url
            )
            return True, 408  # Request Timeout
        except httpx.RequestError as e:
            logger.warning(
                "Webhook request error",
                subscription_id=self.subscription.id,
                webhook_url=webhook_url,
                error=str(e)
            )
            return True, 500  # Assume server error
        except Exception as e:
            logger.error(
                "Unexpected error sending webhook",
                subscription_id=self.subscription.id,
                webhook_url=webhook_url,
                error=str(e),
                exc_info=True
            )
            return True, 500

    async def _mark_subscription_as_used(self) -> None:
        """Mark this disposable subscription as used."""
        try:
            await db_service.mark_disposable_subscription_as_used(self.subscription.id)
            logger.info(
                "Disposable subscription marked as used",
                subscription_id=self.subscription.id
            )
        except Exception as e:
            logger.error(
                "Failed to mark disposable subscription as used",
                subscription_id=self.subscription.id,
                error=str(e),
                exc_info=True
            )


class SubscriptionConsumerService:
    """Service for managing subscription NATS consumers."""

    def __init__(self) -> None:
        self.consumers: Dict[int, SubscriptionConsumer] = {}
        self._running = False

    async def start(self) -> None:
        """Start the subscription consumer service."""
        logger.info("Starting subscription consumer service")
        
        # Ensure subscription event logs table exists
        db_service.create_subscription_event_logs_table()
        
        # Load all active subscriptions and create consumers
        await self._load_active_subscriptions()
        
        self._running = True
        logger.info(
            "Subscription consumer service started",
            active_consumers=len(self.consumers)
        )

    async def stop(self) -> None:
        """Stop the subscription consumer service."""
        if not self._running:
            return

        logger.info("Stopping subscription consumer service")
        self._running = False

        # Stop all consumers
        tasks = []
        for consumer in self.consumers.values():
            tasks.append(consumer.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.consumers.clear()
        logger.info("Subscription consumer service stopped")

    async def run(self) -> None:
        """Run the subscription consumer service (start consumers)."""
        if not self._running:
            await self.start()

        try:
            # Start all consumers
            tasks = []
            for consumer in self.consumers.values():
                tasks.append(consumer.consume_messages())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription consumer."""
        if subscription.id in self.consumers:
            logger.warning(
                "Consumer already exists for subscription",
                subscription_id=subscription.id
            )
            return

        logger.info(
            "Adding subscription consumer",
            subscription_id=subscription.id,
            pattern=subscription.pattern
        )

        consumer = SubscriptionConsumer(subscription)
        await consumer.start()
        
        self.consumers[subscription.id] = consumer
        
        # Start consuming in the background if service is running
        if self._running:
            asyncio.create_task(consumer.consume_messages())

    async def remove_subscription(self, subscription_id: int) -> None:
        """Remove a subscription consumer."""
        consumer = self.consumers.get(subscription_id)
        if not consumer:
            logger.warning(
                "No consumer found for subscription",
                subscription_id=subscription_id
            )
            return

        logger.info(
            "Removing subscription consumer",
            subscription_id=subscription_id
        )

        await consumer.stop()
        del self.consumers[subscription_id]

    async def update_subscription(self, subscription: Subscription) -> None:
        """Update a subscription consumer (restart with new config)."""
        # Remove existing consumer
        await self.remove_subscription(subscription.id)
        
        # Add new consumer with updated config
        if subscription.active:
            await self.add_subscription(subscription)

    async def _load_active_subscriptions(self) -> None:
        """Load all active subscriptions and create consumers."""
        try:
            subscriptions = await db_service.get_all_active_subscriptions()
            
            logger.info(
                "Loading active subscriptions",
                count=len(subscriptions)
            )

            for subscription in subscriptions:
                await self.add_subscription(subscription)

        except Exception as e:
            logger.error(
                "Failed to load active subscriptions",
                error=str(e),
                exc_info=True
            )


# Global subscription consumer service instance
subscription_consumer_service = SubscriptionConsumerService()