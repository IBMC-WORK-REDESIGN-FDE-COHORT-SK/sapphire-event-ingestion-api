"""
OpenTelemetry tracing configuration with custom span processor
"""

from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.context import Context
from app.core.logging import get_logger

logger = get_logger(__name__)


class CustomAttributesSpanProcessor(SpanProcessor):
    """
    Custom span processor to add business-specific attributes to spans.
    This processor enriches spans created by auto-instrumentation with
    custom attributes like device_id, user_id, client_id, and request_id.
    """
    
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """
        Called when a span is started. Add custom attributes here.
        
        Note: FastAPI auto-instrumentation creates spans with the request object
        available in the context. We can access it to add custom attributes.
        """
        # The span will be enriched by FastAPIInstrumentor automatically
        # Additional attributes can be added in route handlers using:
        # span = trace.get_current_span()
        # span.set_attribute("custom.attribute", value)
        pass
    
    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span is ended. Can be used for logging or metrics.
        """
        # Log span completion for debugging (optional)
        if logger.isEnabledFor(10):  # DEBUG level
            logger.debug(
                f"Span completed: {span.name}",
                extra={
                    "trace_id": format(span.get_span_context().trace_id, '032x'),
                    "span_id": format(span.get_span_context().span_id, '016x'),
                    "duration_ms": (span.end_time - span.start_time) / 1_000_000 if span.end_time else 0
                }
            )
    
    def shutdown(self) -> None:
        """Called when the tracer provider is shut down."""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered spans."""
        return True


def add_span_attributes_from_request(request, span: Optional[Span] = None):
    """
    Helper function to add custom attributes to the current span from request state.
    Call this from route handlers or dependencies to enrich spans with business data.
    
    Args:
        request: FastAPI Request object
        span: Optional span to add attributes to. If None, uses current span.
    
    Example usage in a route handler:
        from app.middleware.tracing import add_span_attributes_from_request
        
        @router.post("/ingest")
        async def ingest_data(request: Request, ...):
            add_span_attributes_from_request(request)
            # ... rest of handler
    """
    if span is None:
        span = trace.get_current_span()
    
    if not span or not span.is_recording():
        return
    
    # Add device info if available
    if hasattr(request.state, "device_info"):
        device_info = request.state.device_info
        span.set_attribute("device.id", device_info.get("device_id", ""))
        span.set_attribute("user.id", device_info.get("user_id", ""))
        span.set_attribute("client.id", device_info.get("client_id", ""))
    
    # Add request ID if present
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        span.set_attribute("request.id", request_id)
    
    # Add trace context to response headers (if response is available)
    # This will be handled by a response middleware or in the route handler


def get_trace_headers(span: Optional[Span] = None) -> dict:
    """
    Get trace context headers to add to responses.
    
    Args:
        span: Optional span to get context from. If None, uses current span.
    
    Returns:
        Dictionary with X-Trace-ID and X-Span-ID headers
    
    Example usage in a route handler:
        from app.middleware.tracing import get_trace_headers
        
        @router.post("/ingest")
        async def ingest_data(...):
            # ... process request
            headers = get_trace_headers()
            return JSONResponse(content=result, headers=headers)
    """
    if span is None:
        span = trace.get_current_span()
    
    if not span or not span.is_recording():
        return {}
    
    span_context = span.get_span_context()
    return {
        "X-Trace-ID": format(span_context.trace_id, '032x'),
        "X-Span-ID": format(span_context.span_id, '016x')
    }

# Made with Bob
