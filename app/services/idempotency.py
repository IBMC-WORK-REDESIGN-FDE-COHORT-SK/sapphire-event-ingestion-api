"""
Idempotency tracking service
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)


class IdempotencyService:
    """Service for tracking request idempotency"""
    
    def __init__(self):
        # In-memory cache for idempotency tracking
        # In production, use Redis for distributed caching
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_minutes = 60  # Cache entries expire after 60 minutes
    
    async def is_duplicate(self, request_id: str, device_id: str) -> bool:
        """
        Check if request is a duplicate
        
        Args:
            request_id: Request ID
            device_id: Device ID
            
        Returns:
            bool: True if duplicate, False otherwise
        """
        cache_key = f"{device_id}:{request_id}"
        
        # Clean expired entries
        self._clean_expired()
        
        if cache_key in self.cache:
            logger.info(f"Duplicate request detected: {request_id}")
            return True
        
        return False
    
    async def cache_response(
        self,
        request_id: str,
        device_id: str,
        response: Any
    ):
        """
        Cache response for idempotency
        
        Args:
            request_id: Request ID
            device_id: Device ID
            response: Response to cache
        """
        cache_key = f"{device_id}:{request_id}"
        
        self.cache[cache_key] = {
            "response": response,
            "timestamp": datetime.utcnow()
        }
        
        logger.debug(f"Cached response for request: {request_id}")
    
    async def get_response(self, request_id: str) -> Optional[Any]:
        """
        Get cached response for a request
        
        Args:
            request_id: Request ID
            
        Returns:
            Optional response if found
        """
        # Search for request_id in cache
        for key, value in self.cache.items():
            if key.endswith(f":{request_id}"):
                return value.get("response")
        
        return None
    
    def _clean_expired(self):
        """Remove expired cache entries"""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, value in self.cache.items():
            timestamp = value.get("timestamp")
            if timestamp and (now - timestamp) > timedelta(minutes=self.ttl_minutes):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Idempotency cache cleared")


# Global idempotency service instance
idempotency_service = IdempotencyService()

# Made with Bob
