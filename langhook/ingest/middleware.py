"""Rate limiting middleware for the ingest gateway."""

import time
from collections.abc import Callable

import redis.asyncio as redis
import structlog
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from langhook.ingest.config import settings

logger = structlog.get_logger("langhook")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis."""

    def __init__(self, app, redis_client: redis.Redis = None):
        super().__init__(app)
        self.redis_client = redis_client or redis.from_url(settings.redis_url)
        self.parse_rate_limit()

    def parse_rate_limit(self) -> None:
        """Parse rate limit string like '200/minute' into requests and window."""
        try:
            requests_str, window_str = settings.rate_limit.split('/')
            self.max_requests = int(requests_str)

            if window_str == 'second':
                self.window_seconds = 1
            elif window_str == 'minute':
                self.window_seconds = 60
            elif window_str == 'hour':
                self.window_seconds = 3600
            else:
                raise ValueError(f"Unsupported window: {window_str}")

        except (ValueError, AttributeError) as e:
            logger.warning(
                "Invalid rate limit format, using default",
                rate_limit=settings.rate_limit,
                error=str(e)
            )
            self.max_requests = 200
            self.window_seconds = 60

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        # Skip rate limiting for health endpoint
        if request.url.path == "/health/":
            return await call_next(request)

        # Get client IP
        client_ip = self.get_client_ip(request)

        # Check rate limit
        if await self.is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded", client_ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )

        # Process request
        response = await call_next(request)
        return response

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers first (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"

    async def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited using sliding window."""
        try:
            # Use sliding window rate limiting
            now = int(time.time())
            window_start = now - self.window_seconds

            # Redis key for this IP
            key = f"rate_limit:{client_ip}"

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, self.window_seconds)

            results = await pipe.execute()
            current_requests = results[1]  # Result of zcard

            return current_requests >= self.max_requests

        except Exception as e:
            logger.error(
                "Error checking rate limit, allowing request",
                client_ip=client_ip,
                error=str(e),
                exc_info=True
            )
            # Allow request if Redis is unavailable
            return False
