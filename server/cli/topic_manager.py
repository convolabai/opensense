#!/usr/bin/env python3
"""Topic management CLI tool for creating and configuring Kafka topics."""

import asyncio
import sys

import structlog
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.admin.config_resource import ConfigResource, ConfigResourceType

logger = structlog.get_logger("langhook")


class TopicManager:
    """Manages Kafka topic creation and configuration."""

    def __init__(self, brokers: str):
        self.brokers = brokers.split(',')
        self.admin_client: AIOKafkaAdminClient | None = None

    async def start(self) -> None:
        """Start the admin client."""
        self.admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.brokers
        )
        await self.admin_client.start()
        logger.info("Topic manager started", brokers=self.brokers)

    async def stop(self) -> None:
        """Stop the admin client."""
        if self.admin_client:
            await self.admin_client.close()
            self.admin_client = None
            logger.info("Topic manager stopped")

    async def create_langhook_topics(self) -> None:
        """Create all LangHook core topics with proper configuration."""
        if not self.admin_client:
            raise RuntimeError("Admin client not started")

        # Epic 3 core topics configuration
        topics_config = {
            'raw_ingest': {
                'partitions': 3,
                'replication_factor': 1,
                'config': {
                    'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                    'cleanup.policy': 'delete',  # No log compaction
                    'compression.type': 'gzip',
                    'segment.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                }
            },
            'langhook.events': {
                'partitions': 3,
                'replication_factor': 1,
                'config': {
                    'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                    'cleanup.policy': 'delete',  # No log compaction
                    'compression.type': 'gzip',
                    'segment.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                }
            },
            'langhook.matches': {
                'partitions': 3,
                'replication_factor': 1,
                'config': {
                    'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                    'cleanup.policy': 'compact',  # Log compaction for matches
                    'compression.type': 'gzip',
                    'segment.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                    'min.cleanable.dirty.ratio': '0.5',
                    'delete.retention.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                }
            },
            'langhook.dlq': {
                'partitions': 1,
                'replication_factor': 1,
                'config': {
                    'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                    'cleanup.policy': 'delete',  # No log compaction
                    'compression.type': 'gzip',
                    'segment.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                }
            },
            'langhook.map_fail': {
                'partitions': 1,
                'replication_factor': 1,
                'config': {
                    'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 days
                    'cleanup.policy': 'delete',  # No log compaction
                    'compression.type': 'gzip',
                    'segment.ms': str(24 * 60 * 60 * 1000),  # 24 hours
                }
            }
        }

        # Check existing topics
        existing_topics = await self.list_topics()

        # Create new topics
        new_topics = []
        for topic_name, config in topics_config.items():
            if topic_name not in existing_topics:
                new_topic = NewTopic(
                    name=topic_name,
                    num_partitions=config['partitions'],
                    replication_factor=config['replication_factor'],
                    topic_configs=config['config']
                )
                new_topics.append(new_topic)
                logger.info("Will create topic", topic=topic_name, config=config)
            else:
                logger.info("Topic already exists", topic=topic_name)

        if new_topics:
            try:
                result = await self.admin_client.create_topics(new_topics)
                # Handle different response types from aiokafka
                if hasattr(result, 'items'):
                    # Old API - result is a dict
                    for topic_name, future in result.items():
                        try:
                            await future  # Wait for creation to complete
                            logger.info("Topic created successfully", topic=topic_name)
                        except Exception as e:
                            logger.error("Failed to create topic", topic=topic_name, error=str(e))
                else:
                    # New API - result might be a different type
                    # Just log success for all topics since no exceptions were raised
                    for topic in new_topics:
                        logger.info("Topic created successfully", topic=topic.name)
            except Exception as e:
                logger.error("Failed to create topics", error=str(e))
                raise
        else:
            logger.info("All LangHook topics already exist")

    async def list_topics(self) -> list[str]:
        """List all existing topics."""
        if not self.admin_client:
            raise RuntimeError("Admin client not started")

        metadata = await self.admin_client.list_topics()
        # Handle different return types from aiokafka
        if hasattr(metadata, 'topics'):
            return list(metadata.topics.keys())
        else:
            # If metadata is a list or set of topic names
            return list(metadata)

    async def describe_topic(self, topic_name: str) -> dict:
        """Describe a specific topic."""
        if not self.admin_client:
            raise RuntimeError("Admin client not started")

        metadata = await self.admin_client.describe_topics([topic_name])
        if topic_name in metadata.topics:
            topic = metadata.topics[topic_name]
            return {
                'name': topic.topic,
                'partitions': len(topic.partitions),
                'partition_details': [
                    {
                        'partition': p.partition,
                        'leader': p.leader,
                        'replicas': p.replicas,
                        'isr': p.isr
                    }
                    for p in topic.partitions
                ]
            }
        else:
            raise ValueError(f"Topic {topic_name} not found")

    async def get_topic_config(self, topic_name: str) -> dict[str, str]:
        """Get configuration for a specific topic."""
        if not self.admin_client:
            raise RuntimeError("Admin client not started")

        resources = [ConfigResource(ConfigResourceType.TOPIC, topic_name)]
        result = await self.admin_client.describe_configs(resources)

        if resources[0] in result:
            config_entries = result[resources[0]]
            return {entry.name: entry.value for entry in config_entries}
        else:
            return {}


async def create_topics(brokers: str) -> None:
    """Create all LangHook topics."""
    manager = TopicManager(brokers)
    try:
        await manager.start()
        await manager.create_langhook_topics()
        print("✅ LangHook topics created successfully")
    except Exception as e:
        logger.error("Failed to create topics", error=str(e))
        print(f"❌ Failed to create topics: {e}")
        raise
    finally:
        await manager.stop()


async def list_topics(brokers: str) -> None:
    """List all topics."""
    manager = TopicManager(brokers)
    try:
        await manager.start()
        topics = await manager.list_topics()
        print(f"Found {len(topics)} topics:")
        for topic in sorted(topics):
            print(f"  - {topic}")
    except Exception as e:
        logger.error("Failed to list topics", error=str(e))
        print(f"❌ Failed to list topics: {e}")
        raise
    finally:
        await manager.stop()


async def describe_topic(brokers: str, topic_name: str) -> None:
    """Describe a specific topic."""
    manager = TopicManager(brokers)
    try:
        await manager.start()
        info = await manager.describe_topic(topic_name)
        config = await manager.get_topic_config(topic_name)

        print(f"Topic: {info['name']}")
        print(f"Partitions: {info['partitions']}")
        print("\nPartition Details:")
        for p in info['partition_details']:
            print(f"  Partition {p['partition']}: Leader={p['leader']}, Replicas={p['replicas']}, ISR={p['isr']}")

        print("\nConfiguration:")
        for key, value in sorted(config.items()):
            print(f"  {key} = {value}")

    except Exception as e:
        logger.error("Failed to describe topic", topic=topic_name, error=str(e))
        print(f"❌ Failed to describe topic: {e}")
        raise
    finally:
        await manager.stop()


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage LangHook Kafka topics")
    parser.add_argument(
        "--brokers", "-b",
        default="localhost:19092",
        help="Kafka brokers (default: localhost:19092)"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create topics command
    create_parser = subparsers.add_parser('create', help='Create LangHook topics')

    # List topics command
    list_parser = subparsers.add_parser('list', help='List all topics')

    # Describe topic command
    describe_parser = subparsers.add_parser('describe', help='Describe a topic')
    describe_parser.add_argument('topic', help='Topic name to describe')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'create':
            asyncio.run(create_topics(args.brokers))
        elif args.command == 'list':
            asyncio.run(list_topics(args.brokers))
        elif args.command == 'describe':
            asyncio.run(describe_topic(args.brokers, args.topic))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
