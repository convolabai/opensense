"""Main entry point for the consolidated LangHook services."""

import argparse
import signal
import sys

import uvicorn
from dotenv import load_dotenv

from langhook.ingest.config import settings as ingest_settings
from langhook.map.config import settings as map_settings

load_dotenv(override=True)


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    print(f"Received shutdown signal {signum}")
    sys.exit(0)


def main() -> None:
    """Run the consolidated LangHook services."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="LangHook - Universal webhook processing and event transformation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  langhook                    # Start the server with default settings
  langhook --port 9000        # Start on port 9000
  langhook --debug            # Enable debug mode

Environment Variables:
  OPENAI_API_KEY             # Required for LLM-powered mapping suggestions
  NATS_URL                   # NATS server URL (default: nats://localhost:4222)
  REDIS_URL                  # Redis URL (default: redis://localhost:6379)
  POSTGRES_DSN               # PostgreSQL connection string (optional)

See .env.example for all configuration options.
        """,
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (auto-reload, verbose logging)",
    )

    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        help="Set log level (overrides environment variable)",
    )

    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Use debug mode if either service has it enabled or --debug flag
    debug_mode = args.debug or ingest_settings.debug or map_settings.debug

    # Use the most verbose log level from either service or command line
    if args.log_level:
        log_level = args.log_level
    else:
        log_level = (
            "debug"
            if debug_mode
            else min(
                ingest_settings.log_level.lower(),
                map_settings.log_level.lower(),
                key=lambda x: {"debug": 0, "info": 1, "warning": 2, "error": 3}.get(
                    x, 1
                ),
            )
        )

    # Run the server
    uvicorn.run(
        "langhook.app:app",
        host=args.host,
        port=args.port,
        reload=debug_mode,
        log_level=log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()
