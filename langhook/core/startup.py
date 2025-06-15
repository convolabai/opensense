"""Startup utilities for LangHook services."""

import structlog

from langhook.cli.stream_manager import StreamManager

logger = structlog.get_logger("langhook")


async def ensure_nats_streams(nats_url: str) -> None:
    """
    Ensure required NATS JetStream streams exist.

    This function will create the required streams if they don't exist,
    or silently continue if they already exist.

    Args:
        nats_url: NATS server URL to connect to

    Raises:
        Exception: If unable to connect to NATS or create streams
    """
    logger.info("Ensuring NATS streams exist", nats_url=nats_url)

    stream_manager = StreamManager(nats_url)

    try:
        await stream_manager.connect()
        await stream_manager.create_streams()
        logger.info("NATS streams are ready")
    except Exception as e:
        logger.error("Failed to ensure NATS streams", error=str(e), exc_info=True)
        raise
    finally:
        await stream_manager.disconnect()
