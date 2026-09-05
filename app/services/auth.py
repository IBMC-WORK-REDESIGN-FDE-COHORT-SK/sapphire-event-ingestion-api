"""
Authentication service with Keycloak JWT validation using JWKS
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import requests
from jwt import PyJWKClient
from app.config import settings
from app.core.exceptions import AuthenticationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Keycloak JWT-based authentication service"""
    
    def __init__(self):
        self.jwks_url = settings.KEYCLOAK_JWKS_URL
        self.issuer = settings.KEYCLOAK_ISSUER
        self.audience = settings.KEYCLOAK_AUDIENCE
        self.algorithm = settings.JWT_ALGORITHM
        
        # Initialize JWKS client for fetching public keys
        self.jwks_client = PyJWKClient(self.jwks_url)
        
        logger.info(f"Initialized Keycloak auth service with JWKS URL: {self.jwks_url}")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a Keycloak JWT token using JWKS
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict: Decoded token claims
            
        Raises:
            AuthenticationException: If token is invalid or expired
        """
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify token
            # Note: audience validation is optional for client credentials grant
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": False,  # Don't verify audience for client credentials
                }
            )
            
            logger.debug(f"Token verified successfully for subject: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise AuthenticationException("Token has expired")
        except jwt.InvalidIssuerError:
            logger.warning(f"Invalid token issuer. Expected: {self.issuer}")
            raise AuthenticationException("Invalid token issuer")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationException(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AuthenticationException(f"Token verification failed: {str(e)}")
    
    def extract_device_info(self, token: str) -> Dict[str, str]:
        """
        Extract device information from Keycloak token
        
        Args:
            token: JWT token
            
        Returns:
            Dict: Device information (device_id, user_id, client_id)
        """
        payload = self.verify_token(token)
        
        # Extract standard Keycloak claims
        client_id = payload.get("azp", payload.get("client_id", ""))  # azp = authorized party
        user_id = payload.get("sub", "")  # sub = subject (user ID)
        
        # For client credentials grant, device_id is typically the client_id
        # You can override this by adding custom claims in Keycloak
        device_id = payload.get("device_id", client_id)
        
        # Extract username - for service accounts it's "service-account-{client_id}"
        username = payload.get("preferred_username", f"service-account-{client_id}")
        
        logger.debug(f"Extracted device info: client_id={client_id}, device_id={device_id}, user_id={user_id}")
        
        return {
            "client_id": client_id,
            "device_id": device_id,
            "user_id": user_id,
            "username": username,
            "email": payload.get("email", "")
        }
    
    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """
        Get all claims from token without full verification (for debugging)
        
        Args:
            token: JWT token
            
        Returns:
            Dict: All token claims
        """
        try:
            # Decode without verification (for debugging only)
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return {}


# Global auth service instance
auth_service = AuthService()

# Made with Bob
