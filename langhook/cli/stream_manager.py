"""CLI tool for managing NATS JetStream streams."""

import argparse
import asyncio
import sys

import nats
import structlog
from nats.js import JetStreamContext
from nats.js.api import RetentionPolicy, StorageType, StreamConfig

logger = structlog.get_logger("langhook")


class StreamManager:
    """Manage NATS JetStream streams for LangHook."""

    def __init__(self, nats_url: str) -> None:
        self.nats_url = nats_url
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self) -> None:
        """Connect to NATS server."""
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info("Connected to NATS", url=self.nats_url)
        except Exception as e:
            logger.error("Failed to connect to NATS", url=self.nats_url, error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def create_streams(self) -> None:
        """Create required JetStream streams."""
        if not self.js:
            raise RuntimeError("Not connected to NATS")

        # Create the main events stream
        stream_config = StreamConfig(
            name="events",
            subjects=[
                "langhook.events.>",  # Canonical events
                "raw.>",              # Raw events for processing
                "dlq.>"               # Dead letter queue events
            ],
            storage=StorageType.FILE,
            retention=RetentionPolicy.LIMITS,
            max_age=7 * 24 * 60 * 60,  # 7 days in seconds
            max_bytes=10 * 1024 * 1024 * 1024,  # 10GB
            max_msgs=1000000,  # 1M messages
            discard="old",
        )

        try:
            await self.js.add_stream(stream_config)
            logger.info("Created stream 'events'", subjects=stream_config.subjects)
            print(f"✅ Created stream 'events' with subjects {', '.join(stream_config.subjects)}")
        except Exception as e:
            error_str = str(e).lower()
            logger.error("Failed to create stream 'events'", error=error_str)
            print(f"❌ Failed to create stream 'events': {error_str}")
            if ("stream name already in use" in error_str or
                "insufficient storage resources" in error_str or
                "err_code=10047" in error_str):
                logger.info("Stream 'events' already exists: %s", error_str)
                print("ℹ️  Stream 'events' already exists")
            else:
                logger.error("Failed to create stream 'events'", error=str(e))
                raise

    async def list_streams(self) -> None:
        """List all JetStream streams."""
        if not self.js:
            raise RuntimeError("Not connected to NATS")

        try:
            streams_info = await self.js.streams_info()

            if not streams_info:
                print("No streams found")
                return

            print("\nStreams:")
            print("-" * 50)
            for stream in streams_info:
                print(f"Name: {stream.config.name}")
                print(f"Subjects: {stream.config.subjects}")
                print(f"Messages: {stream.state.messages}")
                print(f"Bytes: {stream.state.bytes}")
                print(f"Max Age: {stream.config.max_age}s")
                print("-" * 50)

        except Exception as e:
            logger.error("Failed to list streams", error=str(e))
            raise

    async def delete_streams(self) -> None:
        """Delete all streams (for cleanup)."""
        if not self.js:
            raise RuntimeError("Not connected to NATS")

        try:
            await self.js.delete_stream("events")
            logger.info("Deleted stream 'events'")
            print("✅ Deleted stream 'events'")
        except Exception as e:
            if "stream not found" in str(e).lower():
                logger.info("Stream 'events' does not exist")
                print("ℹ️  Stream 'events' does not exist")
            else:
                logger.error("Failed to delete stream 'events'", error=str(e))
                raise


async def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage LangHook NATS JetStream streams")
    parser.add_argument(
        "--url",
        default="nats://localhost:4222",
        help="NATS server URL"
    )
    parser.add_argument(
        "action",
        choices=["create", "list", "delete"],
        help="Action to perform"
    )

    args = parser.parse_args()

    # Configure structured logging
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
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    manager = StreamManager(args.url)

    try:
        await manager.connect()

        if args.action == "create":
            await manager.create_streams()
        elif args.action == "list":
            await manager.list_streams()
        elif args.action == "delete":
            await manager.delete_streams()

    except Exception as e:
        logger.error("Stream management failed", error=str(e))
        sys.exit(1)
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
