# Auto-Instrumented Metrics: The Complete Picture

## Yes, Auto-Instrumented Metrics ARE Available! ✅

You're absolutely correct! `FastAPIInstrumentor` **does provide automatic HTTP metrics**. Here's what's actually available:

## Auto-Instrumented HTTP Metrics from FastAPI

When you call `FastAPIInstrumentor.instrument_app(app)`, you automatically get:

### 📊 Available Metrics

| Metric Name | Type | Description | Attributes |
|-------------|------|-------------|------------|
| `http.server.duration` | Histogram | HTTP request duration | method, status_code, http.route, http.scheme |
| `http.server.active_requests` | UpDownCounter | Active HTTP requests | method, http.scheme, http.flavor |
| `http.server.request.size` | Histogram | HTTP request body size | method, status_code, http.route |
| `http.server.response.size` | Histogram | HTTP response body size | method, status_code, http.route |

### 🎯 What This Means

```python
# When you do this:
FastAPIInstrumentor.instrument_app(app)

# You automatically get these metrics for FREE:
# - Request count (from histogram)
# - Latency/Duration (http.server.duration)
# - HTTP status codes (as attributes)
# - Error rates (status_code >= 400)
# - Active requests (http.server.active_requests)
```

## Current Implementation Status

### ✅ What We Have Now

```python
# In app/main.py
if settings.OTEL_ENABLED:
    FastAPIInstrumentor.instrument_app(
        app,
        meter_provider=metrics.get_meter_provider()
    )
```

This gives us:
1. **Auto traces** - All HTTP requests
2. **Auto metrics** - HTTP duration, active requests, sizes
3. **Standard attributes** - method, status_code, route, scheme

### ⚠️ What's Missing: Trace Context (Exemplars)

The auto-instrumented metrics **do NOT include trace context by default**. This means:

```python
# Auto metric looks like this:
http.server.duration{
    method="POST",
    status_code="200",
    http.route="/api/v1/ingest"
}

# Missing:
# trace_id="a1b2c3d4..."  ❌
# span_id="x1y2z3..."     ❌
```

## Solution: Hybrid Approach (Best of Both Worlds)

### Option 1: Use Both Auto + Custom Metrics (Recommended) ⭐

```python
# Auto-instrumented metrics (no trace context)
# - http.server.duration
# - http.server.active_requests
# - http.server.request.size
# - http.server.response.size

# Custom metrics (WITH trace context)
# - http.requests.total (with trace_id, span_id)
# - kafka.messages.sent.total (with trace_id, span_id)
# - metrics.ingested.total (with trace_id, span_id)
```

**Benefits:**
- ✅ Standard HTTP metrics from auto-instrumentation
- ✅ Business metrics with trace context from custom implementation
- ✅ Best of both worlds

**Trade-off:**
- Some overlap in HTTP metrics (but different use cases)

### Option 2: Add Trace Context to Auto Metrics (Complex)

To add trace context to auto-instrumented metrics, you need a custom `MetricReader`:

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry import trace

class TraceContextMetricReader(MetricReader):
    """Custom metric reader that adds trace context to all metrics"""
    
    def collect(self, timeout_millis: float = 10_000) -> Iterable[Metric]:
        # Get current span
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            # Add trace_id and span_id to metric attributes
            # This is complex and requires modifying metric data points
        
        return super().collect(timeout_millis)
```

**This is complex and not recommended** because:
- Requires custom metric reader implementation
- May impact performance
- Harder to maintain
- Our custom metrics already provide this

## Recommended Architecture

### Layer 1: Auto-Instrumented Metrics (Standard HTTP)

```
FastAPIInstrumentor
    ↓
Automatic HTTP Metrics:
- http.server.duration (latency)
- http.server.active_requests (concurrency)
- http.server.request.size
- http.server.response.size

Attributes:
- method, status_code, http.route, http.scheme
```

**Use for:**
- Overall HTTP performance monitoring
- Request/response size analysis
- Active connection monitoring
- Standard dashboards

### Layer 2: Custom Metrics (Business + Trace Context)

```
Custom MetricsManager
    ↓
Business Metrics with Trace Context:
- http.requests.total (with trace_id, span_id)
- kafka.messages.sent.total (with trace_id, span_id)
- metrics.ingested.total (with trace_id, span_id)
- validation.errors.total (with trace_id, span_id)

Attributes:
- Business attributes + trace_id + span_id
```

**Use for:**
- Metrics-to-trace correlation
- Business-specific monitoring
- Debugging specific requests
- Root cause analysis

## Complete Metrics Inventory

### 🤖 Auto-Instrumented (From FastAPI)

```promql
# Request duration (latency)
http_server_duration_bucket{method="POST", status_code="200"}

# Active requests
http_server_active_requests{method="POST"}

# Request size
http_server_request_size_bucket{method="POST"}

# Response size
http_server_response_size_bucket{method="POST"}
```

### 🎯 Custom (With Trace Context)

```promql
# HTTP requests with trace context
http_requests_total{method="POST", endpoint="/api/v1/ingest", trace_id="...", span_id="..."}

# Kafka messages with trace context
kafka_messages_sent_total{topic="heartrate", status="success", trace_id="...", span_id="..."}

# Business metrics with trace context
metrics_ingested_total{metric_type="heartrate", status="success", trace_id="...", span_id="..."}
```

## Grafana Dashboard Example

### Panel 1: Overall HTTP Performance (Auto Metrics)

```promql
# P95 latency
histogram_quantile(0.95, 
  rate(http_server_duration_bucket[5m])
)

# Request rate by status code
sum by (status_code) (
  rate(http_server_duration_count[5m])
)

# Active requests
http_server_active_requests
```

### Panel 2: Business Metrics with Trace Correlation (Custom Metrics)

```promql
# Metrics ingested with exemplars
rate(metrics_ingested_total[5m])

# Click on spike → View exemplars → Jump to trace
```

## System Metrics (CPU, Memory)

For system metrics, you need additional instrumentation:

```bash
# Install system metrics instrumentation
pip install opentelemetry-instrumentation-system-metrics
```

```python
# In app/main.py
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

if settings.OTEL_ENABLED:
    # Enable system metrics
    SystemMetricsInstrumentor().instrument()
```

This provides:
- `system.cpu.utilization`
- `system.memory.usage`
- `system.memory.utilization`
- `system.network.io`
- `system.disk.io`

## Summary: What You Get

### ✅ Out of the Box (Auto-Instrumented)

| Metric | Source | Trace Context |
|--------|--------|---------------|
| HTTP duration | FastAPI | ❌ No |
| HTTP active requests | FastAPI | ❌ No |
| HTTP request/response size | FastAPI | ❌ No |
| Request count | FastAPI (histogram count) | ❌ No |
| Error rate | FastAPI (status_code attr) | ❌ No |

### ✅ Custom Implementation (With Trace Context)

| Metric | Source | Trace Context |
|--------|--------|---------------|
| HTTP requests total | Custom | ✅ Yes |
| Kafka messages | Custom | ✅ Yes |
| Metrics ingested | Custom | ✅ Yes |
| Validation errors | Custom | ✅ Yes |
| Auth attempts | Custom | ✅ Yes |

### 🔧 Optional (Requires Additional Setup)

| Metric | Source | Installation |
|--------|--------|--------------|
| System CPU/Memory | system-metrics | `pip install opentelemetry-instrumentation-system-metrics` |
| Redis operations | redis | Auto-instrumented (traces only) |
| HTTP client calls | requests | Auto-instrumented (traces only) |

## Best Practice Recommendation

### Use Both! 🎯

1. **Keep auto-instrumented metrics** for standard HTTP monitoring
2. **Keep custom metrics** for business logic and trace correlation
3. **Add system metrics** if you need CPU/memory monitoring

```python
# This gives you everything:
if settings.OTEL_ENABLED:
    # 1. Auto HTTP metrics (standard)
    FastAPIInstrumentor.instrument_app(app, meter_provider=metrics.get_meter_provider())
    
    # 2. Auto traces for Redis, Requests
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    
    # 3. Custom metrics with trace context (already initialized)
    metrics_manager.initialize()
    
    # 4. Optional: System metrics
    # SystemMetricsInstrumentor().instrument()
```

## Conclusion

**You were right!** Auto-instrumented metrics ARE available from FastAPI. The key points:

1. ✅ **Auto metrics exist** - HTTP duration, active requests, sizes
2. ⚠️ **No trace context** - Auto metrics don't include trace_id/span_id by default
3. ✅ **Hybrid approach** - Use both auto metrics (standard) + custom metrics (trace context)
4. 🎯 **Best of both worlds** - Standard monitoring + metrics-to-trace correlation

Our implementation gives you **comprehensive observability** with both automatic and custom metrics! 🎉

## Made with Bob