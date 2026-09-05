"""
Health check endpoint
"""

from datetime import datetime
from fastapi import APIRouter

from app.models.response import HealthCheckResponse
from app.config import settings
from app.services.kafka_producer import kafka_producer
from app.services.schema_registry import schema_registry_client
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check the health status of the API and its dependencies"
)
async def health_check():
    """
    Health check endpoint
    
    Returns the health status of:
    - API service
    - Kafka producer
    - Schema Registry
    """
    
    checks = {}
    overall_status = "healthy"
    
    # Check Kafka producer
    try:
        if kafka_producer._started:
            checks["kafka"] = "healthy"
        else:
            checks["kafka"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        checks["kafka"] = "unhealthy"
        overall_status = "degraded"
    
    # Check Schema Registry
    try:
        if schema_registry_client.client is not None:
            checks["schema_registry"] = "healthy"
        else:
            checks["schema_registry"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        logger.error(f"Schema Registry health check failed: {e}")
        checks["schema_registry"] = "unhealthy"
        overall_status = "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.API_VERSION,
        checks=checks,
        timestamp=datetime.utcnow()
    )

# Made with Bob
