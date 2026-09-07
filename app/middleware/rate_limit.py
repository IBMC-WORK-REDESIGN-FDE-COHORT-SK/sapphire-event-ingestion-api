"""
Per-device rate limiting using a Redis sliding-window algorithm.

FR-002a: Devices are limited to RATE_LIMIT_RPM requests per minute.
Exceeding the limit returns HTTP 429 with a Retry-After header.
"""

import time
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitService:
    """
    Sliding-window rate limiter backed by Redis.

    Redis key: rate_limit:{device_id}
    TTL: 60 seconds (one sliding window)
    Limit: settings.RATE_LIMIT_RPM requests per window

    References: FR-002a
    """

    def __init__(self, redis_client):
        self._redis = redis_client

    async def check_rate_limit(self, device_id: str) -> tuple[bool, int]:
        """
        Check whether a device is within its rate limit.

        Implements a sliding-window counter:
        1. Atomically increment the counter for the device key.
        2. On first increment, set TTL of 60 s so the window expires automatically.
        3. If count <= limit → allowed.
        4. If count > limit → rejected; compute retry_after from remaining TTL.

        Args:
            device_id: Unique device identifier from the JWT.

        Returns:
            (True, 0)                  — request is within the limit.
            (False, retry_after_secs)  — limit exceeded; caller should respond
                                         with HTTP 429 and Retry-After: <secs>.
        """
        key = f"rate_limit:{device_id}"
        limit = settings.RATE_LIMIT_RPM

        try:
            # Increment counter (creates key if absent)
            count = await self._redis.incr(key)

            # Set TTL only on the first request in this window
            if count == 1:
                await self._redis.expire(key, 60)

            if count <= limit:
                return True, 0

            # Limit exceeded — compute how long until the window resets
            ttl = await self._redis.ttl(key)
            retry_after = max(ttl, 1)  # at least 1 second
            logger.warning(
                f"Rate limit exceeded for device {device_id}: "
                f"count={count}, limit={limit}, retry_after={retry_after}s"
            )
            return False, retry_after

        except Exception as exc:
            # If Redis is unavailable, fail open to avoid blocking all devices
            logger.error(f"Rate limit check failed for device {device_id}: {exc}")
            return True, 0
