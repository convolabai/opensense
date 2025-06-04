"""Main entry point for the ingest gateway service."""

import signal
import sys

import uvicorn

from opensense.ingest.config import settings


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    print(f"Received shutdown signal {signum}")
    sys.exit(0)


def main() -> None:
    """Run the ingest gateway service."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the server
    uvicorn.run(
        "opensense.ingest.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()