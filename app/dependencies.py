"""
Dependency injection for FastAPI endpoints
"""

from typing import Dict
from fastapi import Request, HTTPException, status
from app.core.logging import get_logger

logger = get_logger(__name__)


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
