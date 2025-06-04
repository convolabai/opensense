"""Main entry point for the OpenSense Canonicaliser service."""

import asyncio
import signal
import sys
from typing import Set

import structlog
import uvicorn
from contextlib import asynccontextmanager

from opensense.map.app import app
from opensense.map.config import settings
from opensense.map.service import mapping_service

logger = structlog.get_logger()


class ServiceManager:
    """Manages both the HTTP server and Kafka consumer."""
    
    def __init__(self) -> None:
        self.tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
    
    async def start_services(self) -> None:
        """Start both HTTP and Kafka services."""
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
        
        logger.info("Starting OpenSense Canonicaliser", version="0.3.0")
        
        # Start mapping service (Kafka consumer)
        mapping_task = asyncio.create_task(mapping_service.run())
        self.tasks.add(mapping_task)
        
        # Start HTTP server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8001,
            log_config=None,  # Use our structured logging
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        self.tasks.add(server_task)
        
        logger.info("All services started")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All services stopped")
    
    def shutdown(self) -> None:
        """Signal shutdown to all services."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    service_manager = ServiceManager()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame) -> None:
        service_manager.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service_manager.start_services()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error in main", error=str(e), exc_info=True)
        sys.exit(1)


def cli_main() -> None:
    """CLI entry point for the opensense-map command."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()