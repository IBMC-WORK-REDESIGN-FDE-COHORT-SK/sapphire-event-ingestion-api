"""
Logging configuration with JSON formatting and OpenTelemetry integration
"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.sdk._logs import LoggingHandler
from app.config import settings


def setup_logging():
    """Configure application logging with OpenTelemetry"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler (for local debugging)
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.LOG_FORMAT.lower() == "json":
        # JSON formatter with trace context
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s %(span_id)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        # Standard formatter with trace context
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(trace_id)s span_id=%(span_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add OpenTelemetry logging handler (push logs to collector)
    if settings.OTEL_ENABLED:
        try:
            from opentelemetry._logs import get_logger_provider
            logger_provider = get_logger_provider()
            if logger_provider:
                otel_handler = LoggingHandler(
                    level=logging.NOTSET,
                    logger_provider=logger_provider
                )
                logger.addHandler(otel_handler)
        except Exception as e:
            print(f"Warning: Failed to add OpenTelemetry logging handler: {e}")
    
    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("kafka").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with trace context"""
    logger = logging.getLogger(name)
    
    # Add trace context filter
    class TraceContextFilter(logging.Filter):
        def filter(self, record):
            # Add trace context to log records
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                ctx = span.get_span_context()
                record.trace_id = format(ctx.trace_id, '032x')
                record.span_id = format(ctx.span_id, '016x')
            else:
                record.trace_id = '0' * 32
                record.span_id = '0' * 16
            return True
    
    # Add filter if not already present
    if not any(isinstance(f, TraceContextFilter) for f in logger.filters):
        logger.addFilter(TraceContextFilter())
    
    return logger

# Made with Bob
