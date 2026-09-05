# FastAPI Implementation Skeleton

This document provides the complete FastAPI application structure and implementation skeleton for the Health & Fitness Telemetry Ingestion API.

## Project Structure

```
sapphire-event-ingestion-api/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Configuration management
│   ├── dependencies.py              # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # API v1 router
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── metrics.py       # Metrics ingestion endpoint
│   │   │       └── health.py        # Health check endpoint
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py               # Request models (Pydantic)
│   │   ├── response.py              # Response models (Pydantic)
│   │   └── avro.py                  # Avro schema models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── kafka_producer.py       # Kafka producer service
│   │   ├── schema_registry.py      # Schema registry client
│   │   ├── auth.py                 # Authentication service
│   │   ├── validation.py           # Validation service
│   │   └── idempotency.py          # Idempotency tracking
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                 # JWT authentication middleware
│   │   ├── rate_limit.py           # Rate limiting middleware
│   │   ├── logging.py              # Request logging middleware
│   │   └── tracing.py              # OpenTelemetry tracing middleware
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── logging.py              # Logging configuration
│   │   └── metrics.py              # Prometheus metrics
│   │
│   └── utils/
│       ├── __init__.py
│       ├── time.py                 # Time utilities
│       └── topic_mapper.py         # Metric to topic mapping
│
├── schemas/                         # Avro schema files
│   ├── activity_schema.avsc
│   ├── heartrate_schema.avsc
│   ├── sleep_schema.avsc
│   ├── bloodpressure_schema.avsc
│   ├── glucose_schema.avsc
│   ├── spo2_schema.avsc
│   ├── workout_schema.avsc
│   ├── nutrition_schema.avsc
│   └── custom_schema.avsc
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_integration/
│
├── scripts/
│   ├── register_schemas.py         # Schema registration script
│   └── create_topics.py            # Kafka topic creation script
│
├── podman-compose.yml              # Container orchestration
├── Dockerfile                       # Application container
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md                        # Project documentation
```

## Core Files

### 1. main.py - FastAPI Application Entry Point

```python
"""
FastAPI application entry point for Health Metrics Ingestion API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import (
    ValidationException,
    KafkaException,
    AuthenticationException,
    RateLimitException
)
from app.core.logging import setup_logging
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.tracing import TracingMiddleware
from app.services.kafka_producer import kafka_producer
from app.services.schema_registry import schema_registry_client

# Setup logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("Starting Health Metrics Ingestion API...")
    
    # Initialize Kafka producer
    await kafka_producer.start()
    print("Kafka producer initialized")
    
    # Initialize Schema Registry client
    await schema_registry_client.initialize()
    print("Schema Registry client initialized")
    
    yield
    
    # Shutdown
    print("Shutting down Health Metrics Ingestion API...")
    
    # Close Kafka producer
    await kafka_producer.stop()
    print("Kafka producer closed")

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - last added is executed first)
app.add_middleware(TracingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Include API router
app.include_router(api_router, prefix="/v1")

# Exception handlers
@app.exception_handler(ValidationException)
async def validation_exception_handler(request, exc: ValidationException):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "details": exc.details,
                "timestamp": exc.timestamp.isoformat()
            }
        }
    )

@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(request, exc: AuthenticationException):
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": str(exc),
                "timestamp": exc.timestamp.isoformat()
            }
        }
    )

@app.exception_handler(RateLimitException)
async def rate_limit_exception_handler(request, exc: RateLimitException):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": str(exc),
                "retry_after": exc.retry_after,
                "timestamp": exc.timestamp.isoformat()
            }
        },
        headers={"Retry-After": str(exc.retry_after)}
    )

@app.exception_handler(KafkaException)
async def kafka_exception_handler(request, exc: KafkaException):
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Kafka cluster temporarily unavailable",
                "retry_after": 30,
                "timestamp": exc.timestamp.isoformat()
            }
        },
        headers={"Retry-After": "30"}
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Health Metrics Ingestion API",
        "version": settings.API_VERSION,
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
```

### 2. config.py - Configuration Management

```python
"""
Application configuration using Pydantic Settings
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_TITLE: str = "Health Metrics Ingestion API"
    API_DESCRIPTION: str = "REST API for ingesting health and fitness telemetry data"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENABLE_DOCS: bool = True
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CLIENT_ID: str = "health-ingestion-api"
    KAFKA_ACKS: str = "all"
    KAFKA_RETRIES: int = 3
    KAFKA_COMPRESSION_TYPE: str = "snappy"
    KAFKA_BATCH_SIZE: int = 16384
    KAFKA_LINGER_MS: int = 100
    KAFKA_REQUEST_TIMEOUT_MS: int = 30000
    KAFKA_ENABLE_IDEMPOTENCE: bool = True
    
    # Schema Registry Settings
    SCHEMA_REGISTRY_URL: str = "http://schema-registry:8081"
    SCHEMA_CACHE_CAPACITY: int = 1000
    
    # Authentication Settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # Rate Limiting Settings
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000
    
    # Redis Settings (for rate limiting and idempotency)
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Validation Settings
    MAX_METRICS_PER_REQUEST: int = 100
    MAX_DATAPOINTS_PER_METRIC: int = 1000
    TIMESTAMP_TOLERANCE_MINUTES: int = 5
    TIMESTAMP_MAX_AGE_DAYS: int = 7
    
    # OpenTelemetry Settings
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "health-metrics-ingestion-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Global settings instance
settings = Settings()
```

### 3. services/kafka_producer.py - Kafka Producer Service

```python
"""
Kafka producer service with Avro serialization
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastavro import schemaless_writer
from io import BytesIO

from app.config import settings
from app.core.exceptions import KafkaException
from app.core.logging import get_logger
from app.services.schema_registry import schema_registry_client
from app.utils.topic_mapper import get_topic_for_metric

logger = get_logger(__name__)

class KafkaProducerService:
    """Async Kafka producer with Avro serialization"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False
        
    async def start(self):
        """Initialize and start Kafka producer"""
        if self._started:
            return
            
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                client_id=settings.KAFKA_CLIENT_ID,
                acks=settings.KAFKA_ACKS,
                retries=settings.KAFKA_RETRIES,
                compression_type=settings.KAFKA_COMPRESSION_TYPE,
                max_batch_size=settings.KAFKA_BATCH_SIZE,
                linger_ms=settings.KAFKA_LINGER_MS,
                request_timeout_ms=settings.KAFKA_REQUEST_TIMEOUT_MS,
                enable_idempotence=settings.KAFKA_ENABLE_IDEMPOTENCE,
            )
            
            await self.producer.start()
            self._started = True
            logger.info("Kafka producer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise KafkaException(f"Failed to start Kafka producer: {e}")
    
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")
    
    async def publish_metric(
        self,
        metric_name: str,
        message: Dict[str, Any],
        device_id: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> bool:
        """
        Publish a metric message to Kafka
        
        Args:
            metric_name: Name of the metric (e.g., health.activity.steps)
            message: Message payload (will be Avro-encoded)
            device_id: Device ID (used as partition key)
            trace_id: OpenTelemetry trace ID
            span_id: OpenTelemetry span ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._started:
            raise KafkaException("Kafka producer not started")
        
        try:
            # Get topic for metric
            topic = get_topic_for_metric(metric_name)
            
            # Get Avro schema
            schema = await schema_registry_client.get_schema(topic)
            
            # Serialize message to Avro
            avro_bytes = self._serialize_avro(message, schema)
            
            # Prepare headers
            headers = [
                ("ingestion_timestamp", str(datetime.utcnow().timestamp()).encode()),
            ]
            if trace_id:
                headers.append(("trace_id", trace_id.encode()))
            if span_id:
                headers.append(("span_id", span_id.encode()))
            
            # Send to Kafka
            await self.producer.send(
                topic=topic,
                value=avro_bytes,
                key=device_id.encode(),
                headers=headers
            )
            
            logger.debug(f"Published metric {metric_name} to topic {topic}")
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error publishing metric: {e}")
            raise KafkaException(f"Failed to publish metric: {e}")
        except Exception as e:
            logger.error(f"Error publishing metric: {e}")
            return False
    
    def _serialize_avro(self, message: Dict[str, Any], schema: Dict) -> bytes:
        """Serialize message to Avro format"""
        output = BytesIO()
        schemaless_writer(output, schema, message)
        return output.getvalue()
    
    async def publish_batch(
        self,
        messages: list[tuple[str, Dict[str, Any], str]],
        trace_id: Optional[str] = None
    ) -> tuple[int, int]:
        """
        Publish a batch of messages
        
        Args:
            messages: List of (metric_name, message, device_id) tuples
            trace_id: OpenTelemetry trace ID
            
        Returns:
            tuple: (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0
        
        tasks = []
        for metric_name, message, device_id in messages:
            task = self.publish_metric(
                metric_name=metric_name,
                message=message,
                device_id=device_id,
                trace_id=trace_id
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failure_count += 1
            elif result:
                success_count += 1
            else:
                failure_count += 1
        
        return success_count, failure_count

# Global producer instance
kafka_producer = KafkaProducerService()
```

### 4. api/v1/endpoints/metrics.py - Metrics Ingestion Endpoint

```python
"""
Metrics ingestion endpoint
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from opentelemetry import trace

from app.models.request import MetricsIngestionRequest
from app.models.response import MetricsIngestionResponse
from app.services.kafka_producer import kafka_producer
from app.services.idempotency import idempotency_service
from app.services.validation import validation_service
from app.dependencies import get_current_device
from app.core.logging import get_logger
from app.utils.topic_mapper import get_topic_for_metric

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
                    "resource": request.resource.model_dump(),
                    "scope": request.scope.model_dump(),
                    "metric_name": metric.name.replace(".", "_"),
                    "unit": metric.unit,
                    "data_points": [
                        dp.model_dump() for dp in metric.data.data_points
                    ],
                    "ingestion_timestamp": int(datetime.utcnow().timestamp() * 1e9),
                    "schema_version": 1
                }
                
                messages.append((
                    metric.name,
                    message,
                    device_info["device_id"]
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
```

### 5. utils/topic_mapper.py - Metric to Topic Mapping

```python
"""
Utility to map metric names to Kafka topics
"""

from typing import Dict

# Metric name prefix to topic mapping
METRIC_TO_TOPIC: Dict[str, str] = {
    "health.activity": "health.metrics.activity",
    "health.heartrate": "health.metrics.heartrate",
    "health.sleep": "health.metrics.sleep",
    "health.bloodpressure": "health.metrics.bloodpressure",
    "health.glucose": "health.metrics.glucose",
    "health.spo2": "health.metrics.spo2",
    "health.workout": "health.metrics.workout",
    "health.nutrition": "health.metrics.nutrition",
    "health.custom": "health.metrics.custom",
}

def get_topic_for_metric(metric_name: str) -> str:
    """
    Get Kafka topic for a metric name
    
    Args:
        metric_name: Metric name (e.g., health.activity.steps)
        
    Returns:
        str: Kafka topic name
        
    Raises:
        ValueError: If metric name doesn't match any known pattern
    """
    # Extract category from metric name (e.g., health.activity from health.activity.steps)
    parts = metric_name.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid metric name format: {metric_name}")
    
    category = f"{parts[0]}.{parts[1]}"
    
    topic = METRIC_TO_TOPIC.get(category)
    if not topic:
        raise ValueError(f"Unknown metric category: {category}")
    
    return topic

def get_all_topics() -> list[str]:
    """Get list of all Kafka topics"""
    return list(set(METRIC_TO_TOPIC.values()))
```

## Dependencies

### requirements.txt

```txt
# FastAPI and ASGI server
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Pydantic
pydantic==2.5.3
pydantic-settings==2.1.0

# Kafka
aiokafka==0.10.0
confluent-kafka[avro,schema-registry]==2.3.0
fastavro==1.9.3

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Redis (for rate limiting and idempotency)
redis==5.0.1
aioredis==2.0.1

# OpenTelemetry
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-fastapi==0.43b0
opentelemetry-exporter-otlp==1.22.0

# Prometheus metrics
prometheus-client==0.19.0

# Logging
python-json-logger==2.0.7

# Utilities
python-dateutil==2.8.2
pytz==2023.3
```

## Running the Application

### Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET_KEY="your-secret-key"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export SCHEMA_REGISTRY_URL="http://localhost:8081"
export REDIS_URL="redis://localhost:6379/0"

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Run with Gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Testing

### Unit Tests

```python
# tests/test_api/test_metrics.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ingest_metrics_success():
    """Test successful metrics ingestion"""
    payload = {
        "request_id": "test-req-001",
        "resource": {
            "attributes": {
                "device_id": "test-device-001",
                "device_type": "smartwatch",
                "user_id": "test-user-001"
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
    
    response = client.post(
        "/v1/metrics/ingest",
        json=payload,
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
```

## Next Steps

1. Implement remaining middleware (auth, rate limiting, tracing)
2. Implement service classes (schema registry, idempotency, validation)
3. Add comprehensive error handling
4. Implement health check endpoint
5. Add integration tests
6. Set up CI/CD pipeline
7. Create deployment manifests