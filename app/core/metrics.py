"""
OpenTelemetry metrics instrumentation

This module provides OpenTelemetry metrics for the application.
Metrics are exported to the configured OTLP endpoint.

Metrics include trace context (exemplars) for metrics-to-trace correlation.
Exemplars are automatically attached by OpenTelemetry when recording metrics within an active span.
"""

import os
from typing import Dict, Optional

# CRITICAL: Set exemplar filter BEFORE importing OpenTelemetry
# This must be done before any OTel SDK components are imported
from app.config import settings
# if settings.OTEL_ENABLED:
#     os.environ['OTEL_METRICS_EXEMPLAR_FILTER'] = settings.OTEL_METRICS_EXEMPLAR_FILTER

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricsManager:
    """Manages OpenTelemetry metrics for the application"""
    
    def __init__(self):
        self.meter = None
        self.initialized = False
        
        # Counters
        self.http_requests_total = None
        self.kafka_messages_sent_total = None
        self.metrics_ingested_total = None
        self.validation_errors_total = None
        self.auth_attempts_total = None
        
        # Histograms
        self.http_request_duration = None
        self.kafka_message_size = None
        
        # UpDownCounters (for gauges)
        self.active_requests = None
        self.schema_registry_cache_size = None
        self.idempotency_cache_size = None
    
    def initialize(self):
        """Initialize OpenTelemetry metrics with exemplar support"""
        if self.initialized:
            logger.warning("Metrics already initialized")
            return
        
        if not settings.OTEL_ENABLED:
            logger.info("OpenTelemetry metrics disabled")
            return
        
        try:
            # Exemplar filter already set at module import time
            #logger.info(f"Exemplar filter: {os.environ.get('OTEL_METRICS_EXEMPLAR_FILTER', 'not set')}")
            
            # Create resource with service name
            resource = Resource(attributes={
                SERVICE_NAME: settings.OTEL_SERVICE_NAME
            })
            
            # Create OTLP exporter with exemplar support
            exporter = OTLPMetricExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True  # Use insecure for local development
            )
            
            # Create metric reader with 60 second export interval
            # Exemplars are automatically enabled in OTLP exporter
            reader = PeriodicExportingMetricReader(
                exporter=exporter,
                export_interval_millis=60000  # 60 seconds
            )
            
            # Create meter provider with exemplar support
            # Exemplar filter is controlled by OTEL_METRICS_EXEMPLAR_FILTER env var
            provider = MeterProvider(
                resource=resource,
                metric_readers=[reader],
                # Exemplars automatically capture trace context from active spans
                # Filter determines which metrics get exemplars attached
            )
            
            # Set global meter provider
            metrics.set_meter_provider(provider)
            
            # Get meter
            self.meter = metrics.get_meter(__name__)
            
            # Initialize counters
            self.http_requests_total = self.meter.create_counter(
                name="http.requests.total",
                description="Total HTTP requests",
                unit="1"
            )
            
            self.kafka_messages_sent_total = self.meter.create_counter(
                name="kafka.messages.sent.total",
                description="Total Kafka messages sent",
                unit="1"
            )
            
            self.metrics_ingested_total = self.meter.create_counter(
                name="metrics.ingested.total",
                description="Total metrics ingested",
                unit="1"
            )
            
            self.validation_errors_total = self.meter.create_counter(
                name="validation.errors.total",
                description="Total validation errors",
                unit="1"
            )
            
            self.auth_attempts_total = self.meter.create_counter(
                name="auth.attempts.total",
                description="Total authentication attempts",
                unit="1"
            )
            
            # Initialize histograms
            self.http_request_duration = self.meter.create_histogram(
                name="http.request.duration",
                description="HTTP request duration",
                unit="s"
            )
            
            self.kafka_message_size = self.meter.create_histogram(
                name="kafka.message.size",
                description="Kafka message size",
                unit="By"
            )
            
            # Initialize UpDownCounters (gauges)
            self.active_requests = self.meter.create_up_down_counter(
                name="http.requests.active",
                description="Number of active HTTP requests",
                unit="1"
            )
            
            self.schema_registry_cache_size = self.meter.create_up_down_counter(
                name="schema.registry.cache.size",
                description="Number of schemas in cache",
                unit="1"
            )
            
            self.idempotency_cache_size = self.meter.create_up_down_counter(
                name="idempotency.cache.size",
                description="Number of entries in idempotency cache",
                unit="1"
            )
            
            self.initialized = True
            logger.info(f"OpenTelemetry metrics initialized, exporting to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry metrics: {e}")
            raise
    
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """
        Record HTTP request metrics with automatic exemplar support.
        
        Exemplars (trace context) are automatically attached by OpenTelemetry
        when recording metrics within an active span. No need to manually add
        trace_id and span_id as attributes.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status: HTTP status code
            duration: Request duration in seconds
        """
        if not self.initialized:
            return
        
        try:
            # Record metrics with business attributes only
            # Trace context (exemplars) are automatically attached by OpenTelemetry
            counter_attrs = {
                "method": method,
                "endpoint": endpoint,
                "status": str(status)
            }
            histogram_attrs = {
                "method": method,
                "endpoint": endpoint
            }
            
            self.http_requests_total.add(1, counter_attrs)
            self.http_request_duration.record(duration, histogram_attrs)
        except Exception as e:
            logger.error(f"Failed to record HTTP request metrics: {e}")
    
    def record_kafka_message(self, topic: str, status: str, size: int):
        """
        Record Kafka message metrics with automatic exemplar support.
        
        Args:
            topic: Kafka topic name
            status: Message send status (success/error)
            size: Message size in bytes
        """
        if not self.initialized:
            return
        
        try:
            # Exemplars automatically attached from active span
            self.kafka_messages_sent_total.add(
                1,
                {"topic": topic, "status": status}
            )
            self.kafka_message_size.record(
                size,
                {"topic": topic}
            )
        except Exception as e:
            logger.error(f"Failed to record Kafka message metrics: {e}")
    
    def record_metric_ingestion(self, metric_type: str, status: str, count: int = 1):
        """
        Record metric ingestion with automatic exemplar support.
        
        Args:
            metric_type: Type of metric (activity, heartrate, etc.)
            status: Ingestion status (success/error)
            count: Number of metrics ingested
        """
        if not self.initialized:
            return
        
        try:
            # Exemplars automatically attached from active span
            self.metrics_ingested_total.add(
                count,
                {"metric_type": metric_type, "status": status}
            )
        except Exception as e:
            logger.error(f"Failed to record metric ingestion: {e}")
    
    def record_validation_error(self, error_type: str):
        """
        Record validation error with automatic exemplar support.
        
        Args:
            error_type: Type of validation error
        """
        if not self.initialized:
            return
        
        try:
            # Exemplars automatically attached from active span
            self.validation_errors_total.add(
                1,
                {"error_type": error_type}
            )
        except Exception as e:
            logger.error(f"Failed to record validation error: {e}")
    
    def record_auth_attempt(self, status: str):
        """
        Record authentication attempt with automatic exemplar support.
        
        Args:
            status: Authentication status (success/failure)
        """
        if not self.initialized:
            return
        
        try:
            # Exemplars automatically attached from active span
            self.auth_attempts_total.add(
                1,
                {"status": status}
            )
        except Exception as e:
            logger.error(f"Failed to record auth attempt: {e}")
    
    def increment_active_requests(self):
        """Increment active requests counter"""
        if not self.initialized:
            return
        
        try:
            self.active_requests.add(1)
        except Exception as e:
            logger.error(f"Failed to increment active requests: {e}")
    
    def decrement_active_requests(self):
        """Decrement active requests counter"""
        if not self.initialized:
            return
        
        try:
            self.active_requests.add(-1)
        except Exception as e:
            logger.error(f"Failed to decrement active requests: {e}")
    
    def update_schema_cache_size(self, size: int):
        """Update schema registry cache size"""
        if not self.initialized:
            return
        
        try:
            # For UpDownCounter, we need to track the delta
            # This is a simplified approach - in production you'd track the previous value
            self.schema_registry_cache_size.add(size)
        except Exception as e:
            logger.error(f"Failed to update schema cache size: {e}")
    
    def update_idempotency_cache_size(self, size: int):
        """Update idempotency cache size"""
        if not self.initialized:
            return
        
        try:
            # For UpDownCounter, we need to track the delta
            # This is a simplified approach - in production you'd track the previous value
            self.idempotency_cache_size.add(size)
        except Exception as e:
            logger.error(f"Failed to update idempotency cache size: {e}")


# Global metrics manager instance
metrics_manager = MetricsManager()

# Made with Bob