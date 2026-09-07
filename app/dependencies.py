"""
Dependency injection for FastAPI endpoints
"""

from typing import Dict
from fastapi import Request, HTTPException, status
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_rate_limit_service(request: Request):
    """
    Factory dependency that returns the RateLimitService instance.

    The underlying redis client is obtained from the app state (set during startup).
    Importing here (not at module level) avoids circular imports.
    """
    from app.middleware.rate_limit import RateLimitService

    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is None:
        # Fail open: if Redis is not wired up, return a no-op service
        logger.warning("Redis client not available; rate limiting is disabled")

        class _NoOpRateLimit:
            async def check_rate_limit(self, device_id: str):
                return True, 0

        return _NoOpRateLimit()

    return RateLimitService(redis_client)


async def get_current_device(request: Request) -> Dict[str, str]:
    """
    Get current device information from request state
    
    This dependency extracts device info that was added by AuthMiddleware
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict containing device_id, user_id, and client_id
        
    Raises:
        HTTPException: If device info is not available
    """
    if not hasattr(request.state, "device_info"):
        logger.error("Device info not found in request state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return request.state.device_info

# Made with Bob
