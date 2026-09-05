# OpenTelemetry Tracing Guide

## Overview

This application uses OpenTelemetry auto-instrumentation for distributed tracing. The tracing setup automatically captures:

- **HTTP requests** via FastAPI auto-instrumentation
- **Redis operations** via Redis auto-instrumentation
- **HTTP client requests** via Requests library auto-instrumentation
- **Custom business attributes** via custom span processor

## Architecture

### Auto-Instrumentation

The application uses OpenTelemetry's auto-instrumentation libraries which automatically:
- Create spans for incoming HTTP requests
- Capture request/response metadata (method, URL, status code, headers)
- Propagate trace context across service boundaries
- Create spans for Redis operations and HTTP client calls

### Custom Span Processor

A custom `CustomAttributesSpanProcessor` is registered to add business-specific logging and debugging capabilities.

## Adding Custom Attributes to Spans

### In Route Handlers

To add custom attributes (device_id, user_id, client_id, request_id) to spans:

```python
from fastapi import Request
from app.middleware.tracing import add_span_attributes_from_request

@router.post("/ingest")
async def ingest_data(request: Request, ...):
    # Add custom attributes from request state
    add_span_attributes_from_request(request)
    
    # Your handler logic here
    ...
```

### Adding Custom Attributes Manually

```python
from opentelemetry import trace

@router.post("/ingest")
async def ingest_data(...):
    span = trace.get_current_span()
    
    # Add custom attributes
    span.set_attribute("custom.metric_type", metric_type)
    span.set_attribute("custom.device_count", len(devices))
    
    # Your handler logic here
    ...
```

### Creating Child Spans

For detailed tracing of specific operations:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_data(data):
    with tracer.start_as_current_span("process_data") as span:
        span.set_attribute("data.size", len(data))
        
        # Process data
        result = await some_operation(data)
        
        span.set_attribute("result.count", len(result))
        return result
```

## Adding Trace Headers to Responses

To include trace context in response headers:

```python
from fastapi.responses import JSONResponse
from app.middleware.tracing import get_trace_headers

@router.post("/ingest")
async def ingest_data(...):
    # Process request
    result = {"status": "success"}
    
    # Get trace headers
    headers = get_trace_headers()
    
    return JSONResponse(content=result, headers=headers)
```

This adds `X-Trace-ID` and `X-Span-ID` headers to the response for correlation.

## Configuration

Tracing is configured via environment variables:

```bash
# Enable/disable tracing
OTEL_ENABLED=true

# Service name for traces
OTEL_SERVICE_NAME=health-metrics-ingestion-api

# OTLP collector endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Viewing Traces

Traces are exported to the configured OTLP endpoint (typically Jaeger or Tempo). Access the UI to view:

- Request traces with timing information
- Service dependencies
- Error traces with exception details
- Custom attributes and business context

### Jaeger UI

If using Jaeger, access the UI at: `http://localhost:16686`

## Best Practices

1. **Use Auto-Instrumentation**: Let OpenTelemetry automatically create spans for HTTP, Redis, and external calls
2. **Add Business Context**: Use `add_span_attributes_from_request()` to enrich spans with business data
3. **Create Child Spans**: For complex operations, create child spans to show detailed timing
4. **Set Span Status**: Mark spans as error when exceptions occur (auto-instrumentation does this)
5. **Propagate Context**: Trace context is automatically propagated in HTTP headers
6. **Include Trace IDs**: Add trace headers to responses for client-side correlation

## Migration from Custom Middleware

The previous `TracingMiddleware` has been replaced with auto-instrumentation to:
- Eliminate duplicate spans
- Reduce maintenance overhead
- Leverage community-maintained instrumentations
- Improve performance

Custom attributes are now added via:
- `add_span_attributes_from_request()` helper function
- Direct span manipulation in route handlers
- Custom span processor for cross-cutting concerns

## Troubleshooting

### No Traces Appearing

1. Check `OTEL_ENABLED=true` in environment
2. Verify OTLP endpoint is accessible
3. Check application logs for instrumentation errors

### Missing Custom Attributes

1. Ensure `add_span_attributes_from_request()` is called in route handler
2. Verify `request.state.device_info` is set by auth middleware
3. Check span is recording: `span.is_recording()`

### Performance Impact

Auto-instrumentation has minimal overhead (<1% in most cases). To reduce:
- Use sampling (configure in trace provider)
- Disable instrumentation for health check endpoints
- Adjust batch processor settings

## Example: Complete Route Handler

```python
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from opentelemetry import trace
from app.middleware.tracing import add_span_attributes_from_request, get_trace_headers

router = APIRouter()
tracer = trace.get_tracer(__name__)

@router.post("/ingest/{metric_type}")
async def ingest_metric(
    request: Request,
    metric_type: str,
    data: dict
):
    # Add custom attributes from request
    add_span_attributes_from_request(request)
    
    # Get current span for additional attributes
    span = trace.get_current_span()
    span.set_attribute("metric.type", metric_type)
    span.set_attribute("data.size", len(str(data)))
    
    # Create child span for processing
    with tracer.start_as_current_span("validate_and_process") as child_span:
        child_span.set_attribute("validation.schema", metric_type)
        
        # Validate and process
        result = await process_metric(metric_type, data)
        
        child_span.set_attribute("processing.status", "success")
    
    # Return response with trace headers
    headers = get_trace_headers()
    return JSONResponse(
        content={"status": "success", "result": result},
        headers=headers
    )
```

## Metrics-to-Trace Correlation

All metrics automatically include trace context (trace_id and span_id) as attributes, enabling you to jump from metrics to traces. See [METRICS_TO_TRACE_CORRELATION.md](./METRICS_TO_TRACE_CORRELATION.md) for detailed information.

### Quick Example

When you record a metric, trace context is automatically included:

```python
from app.core.metrics import metrics_manager

# This metric will include trace_id and span_id from the current span
metrics_manager.record_metric_ingestion(
    metric_type="heartrate",
    status="success",
    count=1
)
```

In your observability platform (Grafana/Prometheus), you can:
1. Query the metric: `rate(metrics_ingested_total[5m])`
2. Click on a data point to see exemplars (sample traces)
3. Jump directly to the trace in Jaeger/Tempo
4. Analyze the full request context

This enables powerful workflows like:
- **Detect** a spike in error metrics
- **View** sample traces that contributed to the spike
- **Analyze** the root cause in the trace details
- **Correlate** metrics and traces for complete observability

## Related Documentation

- [Metrics-to-Trace Correlation Guide](./METRICS_TO_TRACE_CORRELATION.md) - Detailed guide on metrics-to-trace correlation
- [OpenTelemetry Metrics](./OPENTELEMETRY_METRICS.md) - Metrics implementation details
- [Architecture](./ARCHITECTURE.md) - Overall system architecture

## Made with Bob