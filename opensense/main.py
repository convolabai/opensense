"""Main entry point for the consolidated EventScribe services."""

import signal
import sys

import uvicorn

from opensense.ingest.config import settings as ingest_settings
from opensense.map.config import settings as map_settings


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    print(f"Received shutdown signal {signum}")
    sys.exit(0)


def main() -> None:
    """Run the consolidated EventScribe services."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Use debug mode if either service has it enabled
    debug_mode = ingest_settings.debug or map_settings.debug
    
    # Use the most verbose log level from either service
    log_level = "debug" if debug_mode else min(
        ingest_settings.log_level.lower(),
        map_settings.log_level.lower(),
        key=lambda x: {"debug": 0, "info": 1, "warning": 2, "error": 3}.get(x, 1)
    )
    
    # Run the server
    uvicorn.run(
        "opensense.app:app",
        host="0.0.0.0",
        port=8000,  # Single port for all services
        reload=debug_mode,
        log_level=log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()