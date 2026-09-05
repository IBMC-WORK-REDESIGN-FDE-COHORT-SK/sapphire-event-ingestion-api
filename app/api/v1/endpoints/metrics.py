"""
Metrics ingestion endpoint
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header
from opentelemetry import trace

from app.models.request import MetricsIngestionRequest
from app.models.response import MetricsIngestionResponse
from app.services.kafka_producer import kafka_producer
from app.services.idempotency import idempotency_service
from app.services.validation import validation_service
from app.dependencies import get_current_device
from app.core.exceptions import ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
tracer = trace.get_tracer(__name__)


@router.post(
    "/metrics/ingest",
    response_model=MetricsIngestionResponse,
    status_code=202,
    summary="Ingest health metrics",
    description="Ingest a batch of health and fitness metrics from devices"
)
async def ingest_metrics(
    request: MetricsIngestionRequest,
    device_info: dict = Depends(get_current_device),
    x_request_id: Optional[str] = Header(None),
    x_device_timezone: Optional[str] = Header(None),
):
    """
    Ingest health metrics endpoint
    
    - Validates JWT token
    - Checks idempotency
    - Validates metric data
    - Publishes to Kafka topics
    - Returns acceptance status
    """
    
    with tracer.start_as_current_span("ingest_metrics") as span:
        # Add span attributes
        span.set_attribute("device.id", device_info["device_id"])
        span.set_attribute("user.id", device_info["user_id"])
        span.set_attribute("metrics.count", len(request.metrics))
        
        # Check idempotency
        request_id = x_request_id or request.request_id
        if await idempotency_service.is_duplicate(request_id, device_info["device_id"]):
            logger.info(f"Duplicate request detected: {request_id}")
            span.set_attribute("duplicate", True)
            
            # Return cached response
            cached_response = await idempotency_service.get_response(request_id)
            if cached_response:
                return cached_response
        
        # Validate request
        validation_errors = await validation_service.validate_request(request)
        if validation_errors:
            span.set_attribute("validation.errors", len(validation_errors))
            raise ValidationException("Validation failed", details=validation_errors)
        
        # Prepare messages for Kafka
        messages = []
        accepted_count = 0
        rejected_count = 0
        
        for metric in request.metrics:
            try:
                # Create Kafka message
                message = {
                    "request_id": request_id,
                    "resource": {
                        "attributes": {
                            "device_id": request.resource.attributes.device_id,
                            "device_type": request.resource.attributes.device_type,
                            "device_manufacturer": request.resource.attributes.device_manufacturer or "",
                            "device_model": request.resource.attributes.device_model or "",
                            "user_id": request.resource.attributes.user_id,
                            "app_version": request.resource.attributes.app_version or ""
                        }
                    },
                    "scope": {
                        "name": request.scope.name,
                        "version": request.scope.version
                    },
                    "metric_name": metric.name.replace(".", "_"),
                    "unit": metric.unit,
                    "data_points": {
                        "attributes": json.dumps(metric.data.data_points[0].attributes) if metric.data.data_points[0].attributes else "{}",
                        "start_time_unix_nano": metric.data.data_points[0].start_time_unix_nano or 0,
                        "time_unix_nano": metric.data.data_points[0].time_unix_nano,
                        "value": metric.data.data_points[0].value
                    },
                    "ingestion_timestamp": int(datetime.utcnow().timestamp() * 1e9),
                    "schema_version": 1
                }
                
                messages.append((
                    metric.name,
                    message,
                    request.resource.attributes.user_id
                ))
                accepted_count += 1
                
            except Exception as e:
                logger.error(f"Error preparing metric {metric.name}: {e}")
                rejected_count += 1
        
        # Publish to Kafka
        trace_id = span.get_span_context().trace_id
        success_count, failure_count = await kafka_producer.publish_batch(
            messages=messages,
            trace_id=hex(trace_id)[2:]
        )
        
        # Update counts
        accepted_count = success_count
        rejected_count += failure_count
        
        # Create response
        response = MetricsIngestionResponse(
            request_id=request_id,
            status="accepted" if rejected_count == 0 else "partial",
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            timestamp=datetime.utcnow()
        )
        
        # Cache response for idempotency
        await idempotency_service.cache_response(
            request_id,
            device_info["device_id"],
            response
        )
        
        # Add span attributes
        span.set_attribute("metrics.accepted", accepted_count)
        span.set_attribute("metrics.rejected", rejected_count)
        
        logger.info(
            f"Ingested metrics: accepted={accepted_count}, rejected={rejected_count}",
            extra={
                "request_id": request_id,
                "device_id": device_info["device_id"],
                "accepted": accepted_count,
                "rejected": rejected_count
            }
        )
        
        return response

# Made with Bob
