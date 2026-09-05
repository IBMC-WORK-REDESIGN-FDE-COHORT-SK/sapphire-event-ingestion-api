"""
Response models (Pydantic)
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MetricsIngestionResponse(BaseModel):
    """Response model for successful ingestion"""
    request_id: str = Field(..., description="Original request ID")
    status: str = Field(..., description="Status (accepted, partial, rejected)")
    accepted_count: int = Field(..., description="Number of metrics accepted")
    rejected_count: int = Field(0, description="Number of metrics rejected")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req-uuid-12345",
                "status": "accepted",
                "accepted_count": 15,
                "rejected_count": 0,
                "timestamp": "2024-01-28T10:30:00Z"
            }
        }


class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: str = Field(..., description="Field path that caused error")
    issue: str = Field(..., description="Description of the issue")


class ErrorInfo(BaseModel):
    """Error information"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID if available")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry (for rate limiting)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid metric format",
                "details": [
                    {
                        "field": "metrics[0].data.data_points[0].value",
                        "issue": "Value must be a positive number"
                    }
                ],
                "request_id": "req-uuid-12345",
                "timestamp": "2024-01-28T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: ErrorInfo


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    version: str = Field(..., description="API version")
    checks: Dict[str, str] = Field(..., description="Individual component health")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "checks": {
                    "kafka": "healthy",
                    "schema_registry": "healthy",
                    "redis": "healthy"
                },
                "timestamp": "2024-01-28T10:30:00Z"
            }
        }

# Made with Bob
