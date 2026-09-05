"""
Validation service for metrics
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.request import MetricsIngestionRequest
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ValidationService:
    """Service for validating metric requests"""
    
    # Value ranges for different metric types
    VALUE_RANGES = {
        "health.activity.steps": (0, 100000),
        "health.activity.distance": (0, 1000000),  # meters
        "health.activity.calories": (0, 50000),
        "health.heartrate.bpm": (30, 250),
        "health.heartrate.resting": (30, 120),
        "health.heartrate.max": (100, 250),
        "health.bloodpressure.systolic": (70, 250),
        "health.bloodpressure.diastolic": (40, 150),
        "health.glucose.level": (20, 600),
        "health.spo2.percentage": (70, 100),
        "health.sleep.quality": (0, 100),
    }
    
    async def validate_request(
        self,
        request: MetricsIngestionRequest
    ) -> List[Dict[str, str]]:
        """
        Validate metrics ingestion request
        
        Args:
            request: Metrics ingestion request
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate number of metrics
        if len(request.metrics) > settings.MAX_METRICS_PER_REQUEST:
            errors.append({
                "field": "metrics",
                "issue": f"Too many metrics. Maximum {settings.MAX_METRICS_PER_REQUEST} per request"
            })
        
        # Validate each metric
        for idx, metric in enumerate(request.metrics):
            metric_errors = await self._validate_metric(metric, idx)
            errors.extend(metric_errors)
        
        return errors
    
    async def _validate_metric(
        self,
        metric: Any,
        index: int
    ) -> List[Dict[str, str]]:
        """Validate individual metric"""
        errors = []
        
        # Validate number of data points
        if len(metric.data.data_points) > settings.MAX_DATAPOINTS_PER_METRIC:
            errors.append({
                "field": f"metrics[{index}].data.data_points",
                "issue": f"Too many data points. Maximum {settings.MAX_DATAPOINTS_PER_METRIC} per metric"
            })
        
        # Validate each data point
        for dp_idx, data_point in enumerate(metric.data.data_points):
            dp_errors = self._validate_data_point(
                metric.name,
                data_point,
                index,
                dp_idx
            )
            errors.extend(dp_errors)
        
        return errors
    
    def _validate_data_point(
        self,
        metric_name: str,
        data_point: Any,
        metric_idx: int,
        dp_idx: int
    ) -> List[Dict[str, str]]:
        """Validate individual data point"""
        errors = []
        
        # Validate timestamp
        try:
            timestamp_errors = self._validate_timestamp(
                data_point.time_unix_nano,
                metric_idx,
                dp_idx
            )
            errors.extend(timestamp_errors)
        except Exception as e:
            errors.append({
                "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].time_unix_nano",
                "issue": f"Invalid timestamp: {str(e)}"
            })
        
        # Validate value range
        try:
            value_errors = self._validate_value(
                metric_name,
                data_point.value,
                metric_idx,
                dp_idx
            )
            errors.extend(value_errors)
        except Exception as e:
            errors.append({
                "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].value",
                "issue": f"Invalid value: {str(e)}"
            })
        
        return errors
    
    def _validate_timestamp(
        self,
        timestamp_nano: int,
        metric_idx: int,
        dp_idx: int
    ) -> List[Dict[str, str]]:
        """Validate timestamp is reasonable"""
        errors = []
        
        try:
            now = datetime.utcnow()
            timestamp = datetime.utcfromtimestamp(timestamp_nano / 1e9)
            
            # Check not too far in future (allow clock skew)
            if timestamp > now + timedelta(minutes=settings.TIMESTAMP_TOLERANCE_MINUTES):
                errors.append({
                    "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].time_unix_nano",
                    "issue": f"Timestamp is too far in the future (max {settings.TIMESTAMP_TOLERANCE_MINUTES} minutes)"
                })
            
            # Check not too old
            if timestamp < now - timedelta(days=settings.TIMESTAMP_MAX_AGE_DAYS):
                errors.append({
                    "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].time_unix_nano",
                    "issue": f"Timestamp is too old (max {settings.TIMESTAMP_MAX_AGE_DAYS} days)"
                })
        
        except (ValueError, OSError) as e:
            errors.append({
                "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].time_unix_nano",
                "issue": f"Invalid timestamp format: {str(e)}"
            })
        
        return errors
    
    def _validate_value(
        self,
        metric_name: str,
        value: float,
        metric_idx: int,
        dp_idx: int
    ) -> List[Dict[str, str]]:
        """Validate value is within acceptable range"""
        errors = []
        
        # Check if metric has defined range
        if metric_name in self.VALUE_RANGES:
            min_val, max_val = self.VALUE_RANGES[metric_name]
            
            if not (min_val <= value <= max_val):
                errors.append({
                    "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].value",
                    "issue": f"Value {value} out of valid range [{min_val}, {max_val}] for {metric_name}"
                })
        
        # Check for NaN or Inf
        if not isinstance(value, (int, float)) or value != value:  # NaN check
            errors.append({
                "field": f"metrics[{metric_idx}].data.data_points[{dp_idx}].value",
                "issue": "Value must be a valid number (not NaN or Infinity)"
            })
        
        return errors


# Global validation service instance
validation_service = ValidationService()

# Made with Bob
