"""
FastAPI application entry point for Health Metrics Ingestion API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# OpenTelemetry Traces
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# OpenTelemetry Logs
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# OpenTelemetry Resources
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import (
    ValidationException,
    KafkaException,
    AuthenticationException,
)
from app.core.logging import setup_logging, get_logger
from app.core.metrics import metrics_manager
from app.middleware.auth import AuthMiddleware
from app.middleware.tracing import CustomAttributesSpanProcessor
from app.services.kafka_producer import kafka_producer
from app.services.schema_registry import schema_registry_client

# Initialize OpenTelemetry (Traces and Logs)
if settings.OTEL_ENABLED:
    # Create resource
    resource = Resource(attributes={
        SERVICE_NAME: settings.OTEL_SERVICE_NAME
    })
    
    # Initialize Traces
    trace_provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter for sending traces
    otlp_span_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    
    # Add custom span processor for business attributes
    trace_provider.add_span_processor(CustomAttributesSpanProcessor())
    
    trace.set_tracer_provider(trace_provider)
    print(f"OpenTelemetry tracing initialized with custom span processor, exporting to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
    
    # Initialize auto-instrumentation for libraries
    # These will automatically create spans for Redis and HTTP requests
    try:
        RedisInstrumentor().instrument()
        print("Redis auto-instrumentation enabled")
    except Exception as e:
        print(f"Warning: Could not enable Redis instrumentation: {e}")
    
    try:
        RequestsInstrumentor().instrument()
        print("Requests (HTTP client) auto-instrumentation enabled")
    except Exception as e:
        print(f"Warning: Could not enable Requests instrumentation: {e}")
    
    # Initialize Logs
    logger_provider = LoggerProvider(resource=resource)
    otlp_log_exporter = OTLPLogExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    set_logger_provider(logger_provider)
    print(f"OpenTelemetry logging initialized, exporting to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")

# Setup logging (must be after OTel initialization)
setup_logging()

# Initialize OpenTelemetry metrics BEFORE creating FastAPI app
# This ensures the meter provider is set up before FastAPI instrumentation
if settings.OTEL_ENABLED:
    metrics_manager.initialize()
    print("OpenTelemetry metrics initialized")


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
# Convert CORS_ORIGINS string to list
cors_origins = [settings.CORS_ORIGINS] if settings.CORS_ORIGINS == "*" else settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - last added is executed first)
app.add_middleware(AuthMiddleware)

# Instrument with OpenTelemetry auto-instrumentation
# This automatically creates:
# - Spans for all HTTP requests
# - Metrics: http.server.request.duration, http.server.active_requests, etc.
# IMPORTANT: This must happen AFTER metrics_manager.initialize() so that
# the meter provider with exemplar support is already configured
if settings.OTEL_ENABLED:
    FastAPIInstrumentor.instrument_app(
        app,
        # Use the global meter provider (already configured with exemplar support)
        meter_provider=metrics.get_meter_provider(),
        # Metrics will include standard HTTP attributes
        # Exemplars (trace context) are automatically attached via the configured exemplar filter
    )
    print("FastAPI auto-instrumentation enabled (traces + metrics with exemplar support)")

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

# Made with Bob
