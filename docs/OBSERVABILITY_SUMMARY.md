# Observability Summary

## Overview

This application implements comprehensive observability using OpenTelemetry with:
- **Auto-instrumentation** for traces
- **Metrics with trace context** for metrics-to-trace correlation
- **Structured logging** with trace context
- **Unified observability** across all three pillars

## Quick Reference

### Traces

**Auto-instrumented:**
- ✅ FastAPI HTTP requests/responses
- ✅ Redis operations
- ✅ HTTP client calls (requests library)

**Custom attributes:**
```python
from app.middleware.tracing import add_span_attributes_from_request

@router.post("/endpoint")
async def handler(request: Request):
    add_span_attributes_from_request(request)  # Adds device_id, user_id, etc.
```

**Manual spans:**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("custom.attr", value)
    # Your code here
```

### Metrics

**All metrics include trace context automatically:**
```python
from app.core.metrics import metrics_manager

# Automatically includes trace_id and span_id
metrics_manager.record_http_request(method, endpoint, status, duration)
metrics_manager.record_kafka_message(topic, status, size)
metrics_manager.record_metric_ingestion(metric_type, status, count)
```

**Available metrics:**
- `http.requests.total` - HTTP request counter
- `http.request.duration` - Request duration histogram
- `kafka.messages.sent.total` - Kafka messages counter
- `kafka.message.size` - Message size histogram
- `metrics.ingested.total` - Ingested metrics counter
- `validation.errors.total` - Validation errors counter
- `auth.attempts.total` - Auth attempts counter

### Logs

**Structured logging with trace context:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Automatically includes trace_id and span_id in log context
logger.info("Processing request", extra={"user_id": user_id})
```

## Configuration

```bash
# Enable/disable OpenTelemetry
OTEL_ENABLED=true

# Service name
OTEL_SERVICE_NAME=health-metrics-ingestion-api

# OTLP collector endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Log level
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Observability Stack

### Recommended Setup

```yaml
# docker-compose.yml
services:
  # Traces
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
  
  # Metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  # Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

### Alternative: OpenTelemetry Collector

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  
  prometheus:
    endpoint: "0.0.0.0:8889"
    enable_open_metrics: true

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

## Workflows

### 1. Debug Slow Requests

```
Metrics → Traces → Logs
```

1. **Detect** slow requests in Grafana:
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_bucket[5m])) > 1.0
   ```

2. **Click exemplar** to jump to trace in Jaeger

3. **Analyze** trace spans to find bottleneck

4. **View logs** with same trace_id for detailed context

### 2. Investigate Errors

```
Metrics → Traces → Root Cause
```

1. **Alert** on error rate:
   ```promql
   rate(http_requests_total{status=~"5.."}[5m]) > 0.01
   ```

2. **View exemplars** to see sample failing requests

3. **Open trace** to see error details and stack trace

4. **Identify** failing service/operation

### 3. Monitor Business Metrics

```
Business Metrics → User Journey → Performance
```

1. **Track** metric ingestion by type:
   ```promql
   rate(metrics_ingested_total[5m])
   ```

2. **Correlate** with user activity using trace context

3. **Analyze** end-to-end latency per metric type

4. **Optimize** based on real usage patterns

## Best Practices

### ✅ Do

1. **Use auto-instrumentation** - Let OpenTelemetry handle HTTP, Redis, etc.
2. **Add business context** - Enrich spans with device_id, user_id, etc.
3. **Include trace context** - Metrics automatically include trace_id/span_id
4. **Structure logs** - Use JSON format with trace context
5. **Sample in production** - Configure sampling for high-traffic scenarios
6. **Monitor all three pillars** - Traces, metrics, and logs together

### ❌ Don't

1. **Don't create duplicate spans** - Auto-instrumentation handles most cases
2. **Don't add high-cardinality attributes** - Limit unique attribute combinations
3. **Don't ignore trace context** - Always propagate context across services
4. **Don't log sensitive data** - Sanitize PII before logging
5. **Don't over-instrument** - Focus on critical paths and errors
6. **Don't forget sampling** - Use sampling in production to reduce overhead

## Troubleshooting

### No traces appearing

```bash
# Check OTLP endpoint is accessible
curl http://localhost:4317

# Verify configuration
echo $OTEL_ENABLED
echo $OTEL_EXPORTER_OTLP_ENDPOINT

# Check application logs
grep "OpenTelemetry" app.log
```

### Metrics missing trace context

```python
# Verify span is active
from opentelemetry import trace

span = trace.get_current_span()
print(f"Span recording: {span.is_recording()}")
print(f"Trace ID: {format(span.get_span_context().trace_id, '032x')}")
```

### High cardinality issues

```python
# Limit attributes
# Bad: {"url": "/api/v1/ingest/12345", "user_id": "user123"}
# Good: {"endpoint": "/api/v1/ingest", "status": "200"}

# Use sampling
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

provider = TracerProvider(
    sampler=TraceIdRatioBased(0.1)  # Sample 10% of traces
)
```

## Performance Impact

| Component | Overhead | Notes |
|-----------|----------|-------|
| Auto-instrumentation | <1% | Minimal impact on throughput |
| Trace context propagation | <0.1% | Negligible |
| Metrics with exemplars | <0.5% | Slightly higher than plain metrics |
| Structured logging | 1-2% | JSON serialization overhead |
| **Total** | **~2-3%** | Acceptable for production |

## Documentation

- [TRACING_GUIDE.md](./TRACING_GUIDE.md) - Detailed tracing guide
- [METRICS_TO_TRACE_CORRELATION.md](./METRICS_TO_TRACE_CORRELATION.md) - Metrics-to-trace correlation
- [OPENTELEMETRY_METRICS.md](./OPENTELEMETRY_METRICS.md) - Metrics implementation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture

## Support

For issues or questions:
1. Check application logs for OpenTelemetry initialization messages
2. Verify OTLP collector is running and accessible
3. Review trace/metric data in your observability platform
4. Consult OpenTelemetry documentation: https://opentelemetry.io/docs/

## Made with Bob