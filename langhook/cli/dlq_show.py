#!/usr/bin/env python3
"""DLQ viewer CLI tool for inspecting dead letter queue messages."""

import asyncio
import json
import sys

import structlog
from aiokafka import AIOKafkaConsumer

from langhook.ingest.config import settings

logger = structlog.get_logger("langhook")


async def show_dlq_messages(count: int = 10) -> None:
    """Show the last N messages from the DLQ."""
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_dlq,
        bootstrap_servers=settings.kafka_brokers,
        auto_offset_reset='latest',
        enable_auto_commit=False,
        group_id=None,  # Don't use consumer group to read all messages
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    )

    try:
        await consumer.start()
        print(f"Reading last {count} messages from DLQ topic: {settings.kafka_topic_dlq}")
        print("=" * 80)

        # Get topic partitions
        partitions = consumer.assignment()
        if not partitions:
            # Manually assign partitions
            topic_partitions = consumer.partitions_for_topic(settings.kafka_topic_dlq)
            if topic_partitions:
                from aiokafka import TopicPartition
                partitions = [TopicPartition(settings.kafka_topic_dlq, p) for p in topic_partitions]
                consumer.assign(partitions)

        # Seek to end and read backwards
        await consumer.seek_to_end()

        # Read messages
        messages = []
        message_count = 0

        timeout_ms = 5000  # 5 seconds timeout

        async for message in consumer:
            messages.append(message)
            message_count += 1

            if message_count >= count:
                break

        if not messages:
            print("No messages found in DLQ.")
            return

        # Display messages
        for i, msg in enumerate(reversed(messages[-count:]), 1):
            print(f"\n--- Message {i} ---")
            print(f"Offset: {msg.offset}")
            print(f"Timestamp: {msg.timestamp}")
            print(f"Key: {msg.key.decode() if msg.key else None}")

            try:
                dlq_data = msg.value
                print(f"ID: {dlq_data.get('id', 'N/A')}")
                print(f"Source: {dlq_data.get('source', 'N/A')}")
                print(f"Error: {dlq_data.get('error', 'N/A')}")
                print(f"Timestamp: {dlq_data.get('timestamp', 'N/A')}")

                if 'headers' in dlq_data:
                    print("Headers:")
                    for k, v in dlq_data['headers'].items():
                        print(f"  {k}: {v}")

                if 'payload' in dlq_data:
                    payload = dlq_data['payload']
                    if len(payload) > 200:
                        payload = payload[:200] + "..."
                    print(f"Payload: {payload}")

            except Exception as e:
                print(f"Error parsing message: {e}")
                print(f"Raw value: {msg.value}")

    except Exception as e:
        logger.error("Error reading DLQ messages", error=str(e), exc_info=True)
        print(f"Error: {e}")

    finally:
        await consumer.stop()


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="View LangHook DLQ messages")
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=10,
        help="Number of messages to show (default: 10)"
    )
    parser.add_argument(
        "--kafka-brokers",
        default=None,
        help="Kafka brokers (default: from config)"
    )

    args = parser.parse_args()

    # Override Kafka brokers if provided
    if args.kafka_brokers:
        settings.kafka_brokers = args.kafka_brokers

    try:
        asyncio.run(show_dlq_messages(args.count))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
