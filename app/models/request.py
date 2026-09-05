"""
Request models (Pydantic)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class ResourceAttributes(BaseModel):
    """Device and user identification attributes"""
    device_id: str = Field(..., description="Unique device identifier")
    device_type: str = Field(..., description="Type of device (smartwatch, fitness_band, mobile_app, etc.)")
    device_manufacturer: Optional[str] = Field(None, description="Device manufacturer")
    device_model: Optional[str] = Field(None, description="Device model")
    user_id: str = Field(..., description="Unique user identifier (pseudonymized)")
    app_version: Optional[str] = Field(None, description="Application version")


class Resource(BaseModel):
    """Resource information following OpenTelemetry model"""
    attributes: ResourceAttributes


class Scope(BaseModel):
    """Instrumentation scope following OpenTelemetry model"""
    name: str = Field(..., description="Scope name (e.g., health.metrics.collector)")
    version: str = Field(..., description="Scope version")


class DataPoint(BaseModel):
    """Individual metric data point following OpenTelemetry model"""
    attributes: Dict[str, str] = Field(default_factory=dict, description="Additional attributes")
    start_time_unix_nano: Optional[int] = Field(None, description="Start time in nanoseconds (for aggregated metrics)")
    time_unix_nano: int = Field(..., description="Measurement timestamp in nanoseconds since Unix epoch")
    value: float = Field(..., description="Metric value")
    
    class Config:
        json_schema_extra = {
            "example": {
                "attributes": {"aggregation.window": "5m"},
                "start_time_unix_nano": 1706432400000000000,
                "time_unix_nano": 1706432700000000000,
                "value": 450
            }
        }


class MetricData(BaseModel):
    """Container for data points"""
    data_points: List[DataPoint] = Field(..., min_length=1, description="List of data points")


class Metric(BaseModel):
    """Individual metric following OpenTelemetry model"""
    name: str = Field(..., description="Metric name (e.g., health.activity.steps)")
    description: Optional[str] = Field(None, description="Metric description")
    unit: str = Field(..., description="Metric unit (UCUM format)")
    data: MetricData = Field(..., description="Metric data points")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "health.activity.steps",
                "description": "Step count",
                "unit": "steps",
                "data": {
                    "data_points": [
                        {
                            "attributes": {"aggregation.window": "5m"},
                            "time_unix_nano": 1706432700000000000,
                            "value": 450
                        }
                    ]
                }
            }
        }


class MetricsIngestionRequest(BaseModel):
    """Main request model for metrics ingestion"""
    request_id: str = Field(..., description="Unique request ID for idempotency")
    resource: Resource = Field(..., description="Resource information")
    scope: Scope = Field(..., description="Instrumentation scope")
    metrics: List[Metric] = Field(..., min_length=1, max_length=100, description="List of metrics (max 100 per request)")
    
    @field_validator('request_id')
    @classmethod
    def validate_request_id(cls, v: str) -> str:
        """Validate request_id format (UUID or custom format)"""
        if not re.match(r'^[a-zA-Z0-9\-_]{8,64}$', v):
            raise ValueError('request_id must be 8-64 alphanumeric characters, hyphens, or underscores')
        return v
    
    @field_validator('metrics')
    @classmethod
    def validate_metric_names(cls, v: List[Metric]) -> List[Metric]:
        """Validate metric names follow convention"""
        valid_pattern = r'^health\.[a-z]+\.[a-z_\.]+$'
        for metric in v:
            if not re.match(valid_pattern, metric.name):
                raise ValueError(f'Invalid metric name: {metric.name}. Must match pattern: health.<category>.<name> (can include dots and underscores)')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req-uuid-12345",
                "resource": {
                    "attributes": {
                        "device_id": "watch-12345",
                        "device_type": "smartwatch",
                        "user_id": "user-67890"
                    }
                },
                "scope": {
                    "name": "health.metrics.collector",
                    "version": "1.0.0"
                },
                "metrics": [
                    {
                        "name": "health.activity.steps",
                        "unit": "steps",
                        "data": {
                            "data_points": [
                                {
                                    "time_unix_nano": 1706432700000000000,
                                    "value": 450
                                }
                            ]
                        }
                    }
                ]
            }
        }

# Made with Bob
