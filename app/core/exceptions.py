"""
Custom exceptions for the application
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class BaseAPIException(Exception):
    """Base exception for all API exceptions"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class ValidationException(BaseAPIException):
    """Raised when request validation fails"""
    pass


class AuthenticationException(BaseAPIException):
    """Raised when authentication fails"""
    pass


class AuthorizationException(BaseAPIException):
    """Raised when authorization fails"""
    pass


class RateLimitException(BaseAPIException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class KafkaException(BaseAPIException):
    """Raised when Kafka operations fail"""
    pass


class SchemaRegistryException(BaseAPIException):
    """Raised when Schema Registry operations fail"""
    pass


class IdempotencyException(BaseAPIException):
    """Raised when idempotency check fails"""
    pass

# Made with Bob
