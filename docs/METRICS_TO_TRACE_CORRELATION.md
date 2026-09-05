# Metrics-to-Trace Correlation Guide

## Overview

This application implements **metrics-to-trace correlation** by attaching trace context (trace_id and span_id) to all metrics. This enables you to:

1. **Jump from metrics to traces** - Click on a metric spike and see the exact traces that contributed to it
2. **Correlate performance issues** - Link slow requests in metrics to detailed trace spans
3. **Debug with context** - Understand the full story from high-level metrics to low-level traces

## How It Works

### Automatic Exemplar Support

OpenTelemetry automatically attaches **exemplars** (trace context) to metrics when they are recorded within an active span. Exemplars are NOT regular metric attributes/labels - they are special sample data points that link metrics to traces.

**Key Difference:**
- **Attributes/Labels**: High-cardinality dimensions that create separate metric time series (e.g., `method`, `status`)
- **Exemplars**: Sample trace IDs attached to metric data points for correlation, without increasing cardinality

### Implementation

Metrics are recorded with business attributes only. OpenTelemetry automatically captures trace context as exemplars:

```python
def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
    """
    Record HTTP request metrics with automatic exemplar support.
    
    Exemplars (trace context) are automatically attached by OpenTelemetry
    when recording metrics within an active span.
    """
    # Record with business attributes only
    counter_attrs = {
        "method": method,
        "endpoint": endpoint,
        "status": str(status)
    }
    
    # Trace context automatically attached as exemplar (not as attribute)
    self.http_requests_total.add(1, counter_attrs)
```

**What happens internally:**
1. Metric is recorded within an active span
2. OpenTelemetry SDK automatically captures the current trace_id and span_id
3. These are attached as **exemplars** to the metric data point
4. Exemplars are exported via OTLP to the collector
5. Grafana/Prometheus can display exemplars and enable trace hopping

## Supported Metrics

All application metrics include trace context:

### HTTP Metrics
- `http.requests.total` - Total HTTP requests
- `http.request.duration` - Request duration histogram
- `http.requests.active` - Active requests gauge

### Kafka Metrics
- `kafka.messages.sent.total` - Total Kafka messages sent
- `kafka.message.size` - Message size histogram

### Business Metrics
- `metrics.ingested.total` - Total metrics ingested by type
- `validation.errors.total` - Validation errors
- `auth.attempts.total` - Authentication attempts

### Cache Metrics
- `schema.registry.cache.size` - Schema registry cache size
- `idempotency.cache.size` - Idempotency cache size

## Configuration

### Exemplar Filter

Control when exemplars are attached to metrics using the `OTEL_METRICS_EXEMPLAR_FILTER` environment variable:

```bash
# Development/Testing (recommended)
OTEL_METRICS_EXEMPLAR_FILTER=always_on

# Production (default)
OTEL_METRICS_EXEMPLAR_FILTER=trace_based

# Disable exemplars
OTEL_METRICS_EXEMPLAR_FILTER=always_off
```

**Filter Options:**
- **`always_on`**: Attach exemplars to ALL metrics (recommended for dev/test)
  - Every metric gets trace context attached
  - Perfect for testing trace hopping
  - Higher storage overhead
  
- **`trace_based`**: Only attach exemplars to sampled traces (recommended for production)
  - Exemplars only on sampled traces (e.g., 10% sampling = 10% of metrics have exemplars)
  - Reduces storage overhead
  - Still provides good correlation for debugging
  
- **`always_off`**: Never attach exemplars
  - No trace hopping capability
  - Not recommended

## Using in Observability Platforms

### Grafana + Tempo

1. **Set exemplar filter** in your `.env` file:
   ```bash
   OTEL_METRICS_EXEMPLAR_FILTER=always_on
   ```

2. **Query metrics** in Grafana:
   ```promql
   rate(http_requests_total{status="500"}[5m])
   ```

3. **Click on a data point** to see exemplars (sample traces)

4. **Jump to Tempo** to view the full trace

5. **Configure exemplars** in Grafana datasource:
   ```yaml
   jsonData:
     exemplarTraceIdDestinations:
       - name: traceID
         datasourceUid: <tempo-datasource-uid>
   ```

### Prometheus + Jaeger

1. **Enable exemplars** in Prometheus scrape config:
   ```yaml
   scrape_configs:
     - job_name: 'health-metrics-api'
       scrape_interval: 15s
       metrics_path: '/metrics'
       static_configs:
         - targets: ['localhost:8000']
   ```

2. **Query with exemplars**:
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_bucket[5m]))
   ```

3. **View exemplars** in Prometheus UI or Grafana

4. **Link to Jaeger** using trace_id from exemplar

### OpenTelemetry Collector

The OTLP exporter automatically includes exemplars when exporting metrics:

```yaml
exporters:
  otlp:
    endpoint: "localhost:4317"
    
  prometheus:
    endpoint: "0.0.0.0:8889"
    enable_open_metrics: true  # Enables exemplar support
```

## Example Workflow

### 1. Detect Issue in Metrics

You notice a spike in error rate:
```promql
rate(http_requests_total{status="500"}[5m]) > 0.1
```

### 2. View Exemplars

Click on the spike to see sample traces that contributed to the error rate. Each exemplar shows:
- `trace_id`: Link to the full trace
- `span_id`: Specific span within the trace
- Metric value at that point

### 3. Jump to Trace

Click the trace_id to open the full trace in your tracing backend (Jaeger/Tempo):
- See the complete request flow
- Identify the failing service/operation
- View error messages and stack traces
- Analyze timing and dependencies

### 4. Root Cause Analysis

With the trace, you can:
- See which database query failed
- Identify slow external API calls
- View the exact error message
- Understand the request context (user_id, device_id, etc.)

## Custom Metrics with Exemplar Support

To add exemplar support to your own custom metrics, simply record them within an active span:

```python
from opentelemetry import metrics, trace

# Get meter
meter = metrics.get_meter(__name__)

# Create custom counter
custom_counter = meter.create_counter(
    name="custom.operations.total",
    description="Custom operations counter",
    unit="1"
)

# Record within an active span - exemplars automatically attached
def record_custom_operation(operation_type: str):
    # Ensure this is called within an active span (e.g., HTTP request handler)
    # OpenTelemetry will automatically attach trace context as exemplar
    custom_counter.add(
        1,
        {
            "operation_type": operation_type
            # NO need to manually add trace_id/span_id
        }
    )
```

**Important**: Exemplars are only attached when recording metrics within an active span. If no span is active, the metric is still recorded but without exemplar data.

## Best Practices

### 1. Record Metrics Within Active Spans

Exemplars are only attached when metrics are recorded within an active span:
```python
# Good - Within HTTP request handler (auto-instrumented span)
@router.post("/ingest")
async def ingest_data(...):
    metrics_manager.record_metric_ingestion("activity", "success")
    # Exemplar automatically attached

# Also Good - Within custom span
with tracer.start_as_current_span("custom_operation"):
    metrics_manager.record_custom_metric(...)
    # Exemplar automatically attached
```

### 2. Don't Add Trace IDs as Attributes

**WRONG** - This creates high cardinality and doesn't enable trace hopping:
```python
# ❌ DON'T DO THIS
counter.add(1, {
    "method": "POST",
    "trace_id": "abc123...",  # Wrong! Creates separate time series
    "span_id": "def456..."     # Wrong! High cardinality
})
```

**CORRECT** - Let OpenTelemetry handle exemplars automatically:
```python
# ✅ DO THIS
counter.add(1, {
    "method": "POST",
    "status": "200"
    # Trace context automatically attached as exemplar
})
```

### 3. Use Low-Cardinality Attributes

Keep metric attributes to low-cardinality dimensions:
```python
# Good - Limited cardinality
{"method": "POST", "status": "500", "endpoint": "/api/v1/ingest"}

# Bad - High cardinality (use exemplars/traces for this)
{"method": "POST", "url": "/api/v1/ingest/12345", "user_id": "user123"}
```

### 4. Exemplar Sampling

OpenTelemetry automatically samples exemplars to reduce storage. The OTLP exporter handles this:
```python
# Exemplar sampling is automatic with OTLP exporter
exporter = OTLPMetricExporter(
    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    insecure=True
)
# Exemplars are sampled and exported automatically
```

### 5. Verify Exemplar Support

Ensure your observability backend supports exemplars:
- **Grafana + Tempo**: Full support ✅
- **Prometheus 2.26+**: Exemplar support ✅
- **Grafana Cloud**: Full support ✅
- **Older Prometheus versions**: No exemplar support ❌

## Troubleshooting

### No Exemplars in Metrics

**Problem**: Metrics don't have exemplars attached

**Solutions**:
1. **Set exemplar filter to `always_on`** for testing:
   ```bash
   OTEL_METRICS_EXEMPLAR_FILTER=always_on
   ```
2. Verify OpenTelemetry tracing is enabled: `OTEL_ENABLED=true`
3. Check that auto-instrumentation is working (spans are being created)
4. Ensure metrics are recorded **within an active span**
5. Verify OTLP exporter is configured correctly
6. Check that your observability backend supports exemplars

### Exemplars Not Showing in Grafana

**Problem**: Can't see exemplars or trace hopping doesn't work

**Solutions**:
1. **Check Prometheus version**: Use Prometheus 2.26+ (exemplar support required)
2. **Enable exemplars in datasource**:
   ```yaml
   # Grafana datasource config
   jsonData:
     exemplarTraceIdDestinations:
       - name: traceID
         datasourceUid: <tempo-datasource-uid>
   ```
3. **Use histogram/counter queries**: Exemplars work with all metric types but are most visible in histograms
4. **Verify OTLP export**: Check that metrics are exported via OTLP (not Prometheus scraping)
5. **Check Grafana version**: Use Grafana 7.4+ for exemplar support

### High Cardinality Issues

**Problem**: Too many unique metric time series

**Solutions**:
1. **Remove trace IDs from attributes**: They should be exemplars, not attributes!
2. Limit the number of attributes per metric to low-cardinality dimensions
3. Use exemplars for high-cardinality data (user_id, request_id, etc.)
4. Consider using logs or traces for very high-cardinality data

**Key Point**: If you're seeing high cardinality due to trace_id/span_id, you're adding them as attributes instead of letting OpenTelemetry handle them as exemplars.

## Architecture Diagram

```
┌─────────────────┐
│  HTTP Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Auto-Instr.    │────▶│  Trace Span  │
│  (FastAPI)      │     │  (Active)    │
└────────┬────────┘     └──────┬───────┘
         │                     │
         │                     │ get_trace_context_attributes()
         │                     │
         ▼                     ▼
┌─────────────────┐     ┌──────────────┐
│  Route Handler  │────▶│  Metrics     │
│                 │     │  + Trace ID  │
└─────────────────┘     └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  OTLP Export │
                        │  (Exemplars) │
                        └──────┬───────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
         ┌─────────────┐              ┌─────────────┐
         │  Prometheus │              │    Tempo    │
         │  (Metrics)  │◀────link────▶│  (Traces)   │
         └─────────────┘              └─────────────┘
                │                             │
                └──────────────┬──────────────┘
                               ▼
                        ┌─────────────┐
                        │   Grafana   │
                        │  (Unified)  │
                        └─────────────┘
```

## Example: Complete Integration

```python
from fastapi import APIRouter, Request
from opentelemetry import trace
from app.core.metrics import metrics_manager
from app.middleware.tracing import add_span_attributes_from_request

router = APIRouter()

@router.post("/ingest/{metric_type}")
async def ingest_metric(request: Request, metric_type: str, data: dict):
    # Add custom span attributes
    add_span_attributes_from_request(request)
    
    # Get current span for additional context
    span = trace.get_current_span()
    span.set_attribute("metric.type", metric_type)
    span.set_attribute("data.size", len(str(data)))
    
    try:
        # Process the metric
        result = await process_metric(metric_type, data)
        
        # Record success metric with trace context (automatic)
        metrics_manager.record_metric_ingestion(
            metric_type=metric_type,
            status="success",
            count=1
        )
        
        return {"status": "success", "result": result}
        
    except ValidationError as e:
        # Record error metric with trace context (automatic)
        metrics_manager.record_validation_error(error_type=type(e).__name__)
        
        # Span automatically marked as error by auto-instrumentation
        raise
```

In this example:
1. **Trace** captures the full request flow
2. **Metrics** record success/error counts with trace_id
3. **Correlation** allows jumping from metric spike to specific failing traces
4. **Context** preserved across metrics and traces

## Made with Bob