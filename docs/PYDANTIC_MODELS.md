# Pydantic Models Specification

This document provides the complete Pydantic model specifications for the Health & Fitness Telemetry Ingestion API.

## Base Models

### Resource Attributes
```python
from pydantic import BaseModel, Field
from typing import Dict, Optional

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
```

### Scope
```python
class Scope(BaseModel):
    """Instrumentation scope following OpenTelemetry model"""
    name: str = Field(..., description="Scope name (e.g., health.metrics.collector)")
    version: str = Field(..., description="Scope version")
```

### Data Point
```python
from typing import Any, Optional

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
```

### Metric Data
```python
from typing import List

class MetricData(BaseModel):
    """Container for data points"""
    data_points: List[DataPoint] = Field(..., min_length=1, description="List of data points")
```

### Metric
```python
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
```

## Request Models

### Ingestion Request
```python
from typing import List
from pydantic import Field, field_validator
import re

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
        valid_pattern = r'^health\.[a-z]+\.[a-z_]+$'
        for metric in v:
            if not re.match(valid_pattern, metric.name):
                raise ValueError(f'Invalid metric name: {metric.name}. Must match pattern: health.<category>.<name>')
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
```

## Response Models

### Success Response
```python
from datetime import datetime

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
```

### Error Response
```python
from typing import List, Optional

class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: str = Field(..., description="Field path that caused error")
    issue: str = Field(..., description="Description of the issue")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: 'ErrorInfo'
    
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
```

### Health Check Response
```python
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
                    "schema_registry": "healthy"
                },
                "timestamp": "2024-01-28T10:30:00Z"
            }
        }
```

## Metric Type-Specific Models

### Activity Metrics
```python
class ActivityMetricNames:
    """Valid activity metric names"""
    STEPS = "health.activity.steps"
    DISTANCE = "health.activity.distance"
    CALORIES = "health.activity.calories"
    ACTIVE_MINUTES = "health.activity.active_minutes"
    FLOORS_CLIMBED = "health.activity.floors_climbed"

class ActivityMetricUnits:
    """Valid units for activity metrics"""
    STEPS = "steps"
    DISTANCE = "m"  # meters
    CALORIES = "kcal"
    ACTIVE_MINUTES = "min"
    FLOORS = "{floors}"
```

### Heart Rate Metrics
```python
class HeartRateMetricNames:
    """Valid heart rate metric names"""
    BPM = "health.heartrate.bpm"
    RESTING = "health.heartrate.resting"
    MAX = "health.heartrate.max"
    AVERAGE = "health.heartrate.average"
    VARIABILITY = "health.heartrate.variability"

class HeartRateMetricUnits:
    """Valid units for heart rate metrics"""
    BPM = "{beats}/min"
    VARIABILITY = "ms"  # milliseconds for HRV
```

### Sleep Metrics
```python
class SleepMetricNames:
    """Valid sleep metric names"""
    DURATION = "health.sleep.duration"
    STAGE_DEEP = "health.sleep.stage.deep"
    STAGE_LIGHT = "health.sleep.stage.light"
    STAGE_REM = "health.sleep.stage.rem"
    STAGE_AWAKE = "health.sleep.stage.awake"
    QUALITY = "health.sleep.quality"

class SleepMetricUnits:
    """Valid units for sleep metrics"""
    DURATION = "s"  # seconds
    QUALITY = "{score}"  # 0-100 score
```

### Blood Pressure Metrics
```python
class BloodPressureMetricNames:
    """Valid blood pressure metric names"""
    SYSTOLIC = "health.bloodpressure.systolic"
    DIASTOLIC = "health.bloodpressure.diastolic"
    PULSE_PRESSURE = "health.bloodpressure.pulse_pressure"

class BloodPressureMetricUnits:
    """Valid units for blood pressure metrics"""
    PRESSURE = "mm[Hg]"  # millimeters of mercury
```

### Blood Glucose Metrics
```python
class GlucoseMetricNames:
    """Valid glucose metric names"""
    LEVEL = "health.glucose.level"
    FASTING = "health.glucose.fasting"
    POST_MEAL = "health.glucose.post_meal"

class GlucoseMetricUnits:
    """Valid units for glucose metrics"""
    MG_DL = "mg/dL"  # milligrams per deciliter
    MMOL_L = "mmol/L"  # millimoles per liter
```

### SpO2 Metrics
```python
class SpO2MetricNames:
    """Valid SpO2 metric names"""
    PERCENTAGE = "health.spo2.percentage"
    AVERAGE = "health.spo2.average"
    MIN = "health.spo2.min"

class SpO2MetricUnits:
    """Valid units for SpO2 metrics"""
    PERCENTAGE = "%"
```

### Workout Metrics
```python
class WorkoutMetricNames:
    """Valid workout metric names"""
    DURATION = "health.workout.duration"
    DISTANCE = "health.workout.distance"
    CALORIES = "health.workout.calories"
    ELEVATION_GAIN = "health.workout.elevation_gain"
    PACE = "health.workout.pace"
    POWER = "health.workout.power"

class WorkoutMetricUnits:
    """Valid units for workout metrics"""
    DURATION = "s"
    DISTANCE = "m"
    CALORIES = "kcal"
    ELEVATION = "m"
    PACE = "min/km"
    POWER = "W"  # watts
```

### Nutrition Metrics
```python
class NutritionMetricNames:
    """Valid nutrition metric names"""
    CALORIES = "health.nutrition.calories"
    PROTEIN = "health.nutrition.protein"
    CARBOHYDRATES = "health.nutrition.carbohydrates"
    FAT = "health.nutrition.fat"
    FIBER = "health.nutrition.fiber"
    WATER = "health.nutrition.water"
    SODIUM = "health.nutrition.sodium"
    SUGAR = "health.nutrition.sugar"

class NutritionMetricUnits:
    """Valid units for nutrition metrics"""
    CALORIES = "kcal"
    MACROS = "g"  # grams
    WATER = "mL"  # milliliters
    SODIUM = "mg"  # milligrams
```

### Custom Metrics
```python
class CustomMetricNames:
    """Custom metric naming pattern"""
    PREFIX = "health.custom."
    # Examples:
    # health.custom.stress_level
    # health.custom.mood
    # health.custom.meditation_duration
    # health.custom.hydration_reminder
```

## Validation Rules

### Timestamp Validation
```python
from datetime import datetime, timedelta

class TimestampValidator:
    """Validation rules for timestamps"""
    
    @staticmethod
    def validate_timestamp(timestamp_nano: int) -> bool:
        """
        Validate timestamp is reasonable:
        - Not in the future (allow 5 min clock skew)
        - Not older than 7 days
        """
        now = datetime.utcnow()
        timestamp = datetime.fromtimestamp(timestamp_nano / 1e9)
        
        # Check not too far in future (5 min tolerance)
        if timestamp > now + timedelta(minutes=5):
            raise ValueError("Timestamp is in the future")
        
        # Check not too old (7 days)
        if timestamp < now - timedelta(days=7):
            raise ValueError("Timestamp is older than 7 days")
        
        return True
```

### Value Validation
```python
class ValueValidator:
    """Validation rules for metric values"""
    
    # Value ranges for different metric types
    RANGES = {
        "health.activity.steps": (0, 100000),
        "health.heartrate.bpm": (30, 250),
        "health.bloodpressure.systolic": (70, 250),
        "health.bloodpressure.diastolic": (40, 150),
        "health.glucose.level": (20, 600),
        "health.spo2.percentage": (70, 100),
        "health.sleep.quality": (0, 100),
    }
    
    @staticmethod
    def validate_value(metric_name: str, value: float) -> bool:
        """Validate value is within acceptable range"""
        if metric_name in ValueValidator.RANGES:
            min_val, max_val = ValueValidator.RANGES[metric_name]
            if not (min_val <= value <= max_val):
                raise ValueError(f"Value {value} out of range [{min_val}, {max_val}] for {metric_name}")
        return True
```

## Usage Examples

### Creating a Request
```python
# Example: Creating an activity metrics request
request = MetricsIngestionRequest(
    request_id="req-12345",
    resource=Resource(
        attributes=ResourceAttributes(
            device_id="watch-12345",
            device_type="smartwatch",
            user_id="user-67890"
        )
    ),
    scope=Scope(
        name="health.metrics.collector",
        version="1.0.0"
    ),
    metrics=[
        Metric(
            name=ActivityMetricNames.STEPS,
            unit=ActivityMetricUnits.STEPS,
            data=MetricData(
                data_points=[
                    DataPoint(
                        time_unix_nano=int(datetime.utcnow().timestamp() * 1e9),
                        value=450,
                        attributes={"aggregation.window": "5m"}
                    )
                ]
            )
        )
    ]
)
```

### Validating a Request
```python
# Pydantic will automatically validate on instantiation
try:
    request = MetricsIngestionRequest(**request_data)
except ValidationError as e:
    # Handle validation errors
    print(e.json())
```

## Model Inheritance Hierarchy

```
BaseModel (Pydantic)
├── ResourceAttributes
├── Resource
├── Scope
├── DataPoint
├── MetricData
├── Metric
├── MetricsIngestionRequest
├── MetricsIngestionResponse
├── ErrorDetail
├── ErrorInfo
├── ErrorResponse
└── HealthCheckResponse
```

## Field Constraints Summary

| Model | Field | Constraint |
|-------|-------|------------|
| MetricsIngestionRequest | request_id | 8-64 chars, alphanumeric + hyphens/underscores |
| MetricsIngestionRequest | metrics | 1-100 items |
| Metric | name | Must match `health.<category>.<name>` pattern |
| DataPoint | time_unix_nano | Must be valid timestamp (not future, not >7 days old) |
| DataPoint | value | Must be within valid range for metric type |
| ResourceAttributes | device_id | Required, non-empty string |
| ResourceAttributes | user_id | Required, non-empty string |

## Configuration

### Pydantic Settings
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    api_title: str = "Health Metrics Ingestion API"
    api_version: str = "1.0.0"
    api_description: str = "REST API for ingesting health and fitness telemetry data"
    
    # Validation Settings
    max_metrics_per_request: int = 100
    max_datapoints_per_metric: int = 1000
    timestamp_tolerance_minutes: int = 5
    timestamp_max_age_days: int = 7
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    rate_limit_per_day: int = 10000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"