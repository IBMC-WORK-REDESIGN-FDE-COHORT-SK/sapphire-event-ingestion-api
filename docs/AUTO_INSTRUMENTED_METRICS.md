# Auto-Instrumented Metrics and Trace Context

## Important Clarification

**Auto-instrumentation for metrics works differently than for traces.**

### What Auto-Instrumentation Provides

#### ✅ Traces (Fully Auto-Instrumented)
- FastAPI: HTTP request/response spans
- Redis: Redis operation spans  
- Requests: HTTP client call spans
- **Trace context is automatically propagated**

#### ⚠️ Metrics (Limited Auto-Instrumentation)
OpenTelemetry auto-instrumentation libraries **do NOT automatically create metrics** for most libraries. Here's the reality:

| Library | Auto Traces | Auto Metrics | Notes |
|---------|-------------|--------------|-------|
| FastAPI | ✅ Yes | ❌ No | Must create metrics manually |
| Redis | ✅ Yes | ❌ No | Must create metrics manually |
| Requests | ✅ Yes | ❌ No | Must create metrics manually |
| ASGI/HTTP | ✅ Yes | ⚠️ Limited | Basic HTTP metrics only |

## Current Implementation

### Our Custom Metrics (With Trace Context)

We've implemented custom metrics that **automatically include trace context**:

```python
# All these metrics include trace_id and span_id automatically
metrics_manager.record_http_request(method, endpoint, status, duration)
metrics_manager.record_kafka_message(topic, status, size)
metrics_manager.record_metric_ingestion(metric_type, status, count)
metrics_manager.record_validation_error(error_type)
metrics_manager.record_auth_attempt(status)
```

### What About Auto-Instrumented Metrics?

**The truth:** Most OpenTelemetry instrumentation libraries focus on **traces**, not metrics. To get metrics with trace context, you have two options:

## Option 1: Use Our Custom Metrics (Recommended) ✅

**This is what we've already implemented.** Our custom metrics:
- Include trace context automatically
- Cover all important application metrics
- Are optimized for our use case
- Work seamlessly with Prometheus/Grafana

```python
from app.core.metrics import metrics_manager

# These metrics automatically include trace_id and span_id
metrics_manager.record_http_request("POST", "/api/v1/ingest", 200, 0.5)
```

## Option 2: Enable ASGI Metrics (Limited)

Some instrumentation libraries provide basic metrics. Here's how to enable them:

### FastAPI/ASGI Metrics

```python
# In app/main.py
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

# This provides basic HTTP metrics (without trace context by default)
app.add_middleware(OpenTelemetryMiddleware)
```

**Limitations:**
- Basic metrics only (request count, duration)
- **No trace context by default**
- Less control over metric attributes
- May duplicate our custom metrics

### Adding Trace Context to ASGI Metrics

To add trace context to ASGI metrics, you'd need a custom metric exporter:

```python
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics import MeterProvider

# This is complex and not recommended
# Better to use our custom metrics
```

## Recommended Approach ⭐

**Use our custom metrics implementation** because:

1. ✅ **Already includes trace context** - Every metric has trace_id and span_id
2. ✅ **Business-focused** - Metrics that matter for your application
3. ✅ **Consistent naming** - Follows OpenTelemetry semantic conventions
4. ✅ **Optimized attributes** - Right level of cardinality
5. ✅ **Production-ready** - Tested and documented

## Metrics Coverage

### ✅ What We Have (With Trace Context)

```python
# HTTP Metrics
http.requests.total              # Counter with trace context
http.request.duration            # Histogram with trace context
http.requests.active             # Gauge

# Kafka Metrics  
kafka.messages.sent.total        # Counter with trace context
kafka.message.size               # Histogram with trace context

# Business Metrics
metrics.ingested.total           # Counter with trace context
validation.errors.total          # Counter with trace context
auth.attempts.total              # Counter with trace context

# Cache Metrics
schema.registry.cache.size       # Gauge
idempotency.cache.size          # Gauge
```

### ❌ What Auto-Instrumentation Doesn't Provide

- Redis operation metrics (only traces)
- HTTP client metrics (only traces)
- Business-specific metrics
- Metrics with trace context by default

## How to Add More Metrics

If you need additional metrics with trace context:

```python
from opentelemetry import metrics
from app.core.metrics import get_trace_context_attributes

# Get meter
meter = metrics.get_meter(__name__)

# Create metric
custom_counter = meter.create_counter(
    name="custom.operations.total",
    description="Custom operations",
    unit="1"
)

# Record with trace context
def record_operation(operation_type: str):
    trace_attrs = get_trace_context_attributes()
    
    custom_counter.add(
        1,
        {
            "operation_type": operation_type,
            **trace_attrs  # Automatically includes trace_id and span_id
        }
    )
```

## Comparison: Auto vs Custom Metrics

### Auto-Instrumented Metrics (If Available)

**Pros:**
- No code changes needed
- Standardized metric names
- Maintained by community

**Cons:**
- Limited availability (mostly just traces)
- No trace context by default
- Less control over attributes
- May not cover business metrics

### Custom Metrics (Our Implementation)

**Pros:**
- ✅ Trace context included automatically
- ✅ Business-focused metrics
- ✅ Full control over attributes
- ✅ Optimized for our use case
- ✅ Production-ready

**Cons:**
- Requires manual instrumentation (already done!)
- Need to maintain metric definitions

## Real-World Example

### What Happens in Practice

```python
@router.post("/ingest/{metric_type}")
async def ingest_metric(request: Request, metric_type: str, data: dict):
    # 1. Auto-instrumentation creates a trace span (automatic)
    #    - Span includes: method, url, status_code
    #    - Trace context: trace_id, span_id
    
    # 2. Add custom span attributes (manual)
    add_span_attributes_from_request(request)
    span = trace.get_current_span()
    span.set_attribute("metric.type", metric_type)
    
    # 3. Process the request
    result = await process_metric(metric_type, data)
    
    # 4. Record custom metrics WITH trace context (automatic)
    metrics_manager.record_metric_ingestion(
        metric_type=metric_type,
        status="success",
        count=1
    )
    # This metric includes:
    # - metric_type: "heartrate"
    # - status: "success"
    # - trace_id: "a1b2c3d4..." (from current span)
    # - span_id: "x1y2z3..." (from current span)
    
    return {"status": "success"}
```

### In Your Observability Platform

```
Grafana Dashboard:
┌─────────────────────────────────────┐
│ Metrics Ingested (rate)             │
│ ▁▂▃▅▇█▇▅▃▂▁                        │
│                                     │
│ Click spike → View Exemplars       │
│ ├─ trace_id: a1b2c3d4...          │
│ ├─ span_id: x1y2z3...             │
│ └─ Click → Jump to Jaeger         │
└─────────────────────────────────────┘
                ↓
Jaeger Trace View:
┌─────────────────────────────────────┐
│ Trace: a1b2c3d4...                  │
│ ├─ POST /ingest/heartrate (200ms)  │
│ │  ├─ validate_schema (50ms)       │
│ │  ├─ kafka_send (100ms) ← SLOW!  │
│ │  └─ redis_cache (10ms)           │
│ └─ Attributes:                      │
│    ├─ metric.type: heartrate       │
│    ├─ device.id: device-123        │
│    └─ user.id: user-456            │
└─────────────────────────────────────┘
```

## Summary

### ✅ What We Have

1. **Auto-instrumented traces** for FastAPI, Redis, Requests
2. **Custom metrics with trace context** for all application metrics
3. **Seamless metrics-to-trace correlation** in Grafana/Prometheus
4. **Production-ready implementation** with minimal overhead

### ❌ What We Don't Need

1. Auto-instrumented metrics (limited availability, no trace context)
2. ASGI middleware metrics (duplicates our custom metrics)
3. Complex metric exporters (our implementation is simpler)

### 🎯 Bottom Line

**Our custom metrics implementation is the right approach** because:
- Auto-instrumentation focuses on **traces** (which we have)
- Custom metrics give us **trace context** (which we need)
- We have **full control** over what we measure
- It's **production-ready** and well-documented

The combination of **auto-instrumented traces** + **custom metrics with trace context** gives you the best of both worlds! 🎉

## Made with Bob