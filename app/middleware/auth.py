"""
JWT authentication middleware
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.services.auth import auth_service
from app.core.exceptions import AuthenticationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication"""
    
    # Paths that don't require authentication
    EXCLUDED_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/oauth/token",
        "/v1/health"
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and verify authentication"""
        
        # Skip authentication for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Extract authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Missing Authorization header",
                        "timestamp": None
                    }
                }
            )
        
        # Verify Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Invalid Authorization header format. Expected: Bearer <token>",
                        "timestamp": None
                    }
                }
            )
        
        token = parts[1]
        
        try:
            # Verify token and extract device info
            device_info = auth_service.extract_device_info(token)
            
            # Add device info to request state
            request.state.device_info = device_info
            
            logger.debug(f"Authenticated request from device: {device_info.get('device_id')}")
            
            # Continue processing request
            response = await call_next(request)
            return response
            
        except AuthenticationException as e:
            logger.warning(f"Authentication failed: {e.message}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": str(e),
                        "timestamp": e.timestamp.isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                        "timestamp": None
                    }
                }
            )

# Made with Bob
