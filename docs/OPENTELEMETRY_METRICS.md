# OpenTelemetry Metrics Guide

This document describes how metrics are collected and exported using OpenTelemetry in the Health Metrics Ingestion API.

## Overview

The application uses **OpenTelemetry Metrics API** to collect application metrics and exports them to an OpenTelemetry Collector via OTLP (OpenTelemetry Protocol) over gRPC.

Unlike Prometheus which requires a `/metrics` endpoint that gets scraped, OpenTelemetry **pushes** metrics to the collector at regular intervals (default: 60 seconds).

## Architecture

```
┌─────────────────────────────────────┐
│   FastAPI Application               │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  OpenTelemetry Metrics API   │  │
│  │  - Counters                  │  │
│  │  - Histograms                │  │
│  │  - UpDownCounters            │  │
│  └──────────────────────────────┘  │
│              │                      │
│              ▼                      │
│  ┌──────────────────────────────┐  │
│  │  OTLP Metric Exporter        │  │
│  │  (gRPC, 60s interval)        │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   OpenTelemetry Collector           │
│   (localhost:4317)                  │
│                                     │
│   Receivers: OTLP                   │
│   Processors: Batch, Memory Limiter │
│   Exporters: Prometheus, etc.       │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   Observability Backend             │
│   - Prometheus                      │
│   - Grafana                         │
│   - Other OTLP-compatible systems   │
└─────────────────────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Enable/disable OpenTelemetry
OTEL_ENABLED=true

# Service name for metrics
OTEL_SERVICE_NAME=health-metrics-ingestion-api

# OTLP endpoint (gRPC)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### Application Configuration

Metrics are initialized in `app/main.py` during application startup:

```python
from app.core.metrics import metrics_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize OpenTelemetry metrics
    metrics_manager.initialize()
    
    # ... other initialization
    yield
```

## Available Metrics

### HTTP Metrics

#### `http.requests.total` (Counter)
Total number of HTTP requests received.

**Labels:**
- `method`: HTTP method (GET, POST, etc.)
- `endpoint`: API endpoint path
- `status`: HTTP status code

**Example:**
```python
metrics_manager.record_http_request("POST", "/v1/ingest", 200, 0.123)
```

#### `http.request.duration` (Histogram)
HTTP request duration in seconds.

**Labels:**
- `method`: HTTP method
- `endpoint`: API endpoint path

**Unit:** seconds (s)

#### `http.requests.active` (UpDownCounter)
Number of currently active HTTP requests.

**Example:**
```python
metrics_manager.increment_active_requests()
# ... process request ...
metrics_manager.decrement_active_requests()
```

### Kafka Metrics

#### `kafka.messages.sent.total` (Counter)
Total number of Kafka messages sent.

**Labels:**
- `topic`: Kafka topic name
- `status`: success or failure

**Example:**
```python
metrics_manager.record_kafka_message("health.activity", "success", 1024)
```

#### `kafka.message.size` (Histogram)
Size of Kafka messages in bytes.

**Labels:**
- `topic`: Kafka topic name

**Unit:** bytes (By)

### Application Metrics

#### `metrics.ingested.total` (Counter)
Total number of health metrics ingested.

**Labels:**
- `metric_type`: Type of metric (activity, heartrate, etc.)
- `status`: success or failure

**Example:**
```python
metrics_manager.record_metric_ingestion("activity", "success", count=5)
```

#### `validation.errors.total` (Counter)
Total number of validation errors.

**Labels:**
- `error_type`: Type of validation error

**Example:**
```python
metrics_manager.record_validation_error("invalid_timestamp")
```

#### `auth.attempts.total` (Counter)
Total number of authentication attempts.

**Labels:**
- `status`: success or failure

**Example:**
```python
metrics_manager.record_auth_attempt("success")
```

### Cache Metrics

#### `schema.registry.cache.size` (UpDownCounter)
Number of schemas cached in memory.

#### `idempotency.cache.size` (UpDownCounter)
Number of entries in the idempotency cache.

## OpenTelemetry Collector Configuration

### Basic Configuration

Create `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
  
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  # Export to Prometheus
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: health_metrics
  
  # Export to logging (for debugging)
  logging:
    loglevel: debug

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus, logging]
```

### Running the Collector

Using Docker:

```bash
docker run -d \
  --name otel-collector \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 8889:8889 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector:latest \
  --config=/etc/otel-collector-config.yaml
```

Using Docker Compose:

```yaml
version: '3.8'

services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
      - "8889:8889"  # Prometheus exporter
```

## Prometheus Integration

Once the OTel Collector is exporting to Prometheus format, configure Prometheus to scrape it:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['localhost:8889']
```

## Grafana Dashboards

### Example Queries

**Request Rate:**
```promql
rate(http_requests_total[5m])
```

**Request Duration (p95):**
```promql
histogram_quantile(0.95, rate(http_request_duration_bucket[5m]))
```

**Kafka Message Rate:**
```promql
rate(kafka_messages_sent_total{status="success"}[5m])
```

**Error Rate:**
```promql
rate(validation_errors_total[5m])
```

## Adding New Metrics

### 1. Define the Metric

In `app/core/metrics.py`, add the metric definition in the `initialize()` method:

```python
self.my_new_counter = self.meter.create_counter(
    name="my.new.counter",
    description="Description of the metric",
    unit="1"
)
```

### 2. Create a Recording Method

```python
def record_my_metric(self, label_value: str, count: int = 1):
    """Record my custom metric"""
    if not self.initialized:
        return
    
    try:
        self.my_new_counter.add(
            count,
            {"label_name": label_value}
        )
    except Exception as e:
        logger.error(f"Failed to record metric: {e}")
```

### 3. Use the Metric

```python
from app.core.metrics import metrics_manager

# In your code
metrics_manager.record_my_metric("some_value", count=1)
```

## Metric Types

### Counter
Always increases. Use for counting events (requests, errors, etc.).

```python
counter = meter.create_counter(
    name="events.total",
    description="Total events",
    unit="1"
)
counter.add(1, {"type": "event_type"})
```

### Histogram
Records distribution of values. Use for durations, sizes, etc.

```python
histogram = meter.create_histogram(
    name="request.duration",
    description="Request duration",
    unit="s"
)
histogram.record(0.123, {"endpoint": "/api"})
```

### UpDownCounter
Can increase or decrease. Use for gauges (active connections, queue size, etc.).

```python
gauge = meter.create_up_down_counter(
    name="active.connections",
    description="Active connections",
    unit="1"
)
gauge.add(1)   # Increment
gauge.add(-1)  # Decrement
```

## Best Practices

1. **Use Semantic Naming**: Follow OpenTelemetry semantic conventions
   - Use dots for namespacing: `http.requests.total`
   - Use underscores within words: `request_duration`

2. **Add Meaningful Labels**: But don't overdo it
   - Good: `status`, `method`, `endpoint`
   - Avoid: `user_id`, `request_id` (high cardinality)

3. **Choose Appropriate Units**:
   - Time: seconds (s), milliseconds (ms)
   - Size: bytes (By), kilobytes (KB)
   - Count: 1 (dimensionless)

4. **Handle Errors Gracefully**: Metrics recording should never crash the application

5. **Export Interval**: Balance between freshness and overhead (default: 60s)

## Troubleshooting

### Metrics Not Appearing

1. **Check if OTel is enabled:**
   ```bash
   echo $OTEL_ENABLED
   ```

2. **Verify collector is running:**
   ```bash
   curl http://localhost:4317
   ```

3. **Check application logs:**
   ```
   OpenTelemetry metrics initialized, exporting to http://localhost:4317
   ```

4. **Test collector endpoint:**
   ```bash
   docker logs otel-collector
   ```

### High Memory Usage

- Reduce export interval
- Enable memory limiter in collector
- Reduce metric cardinality (fewer label combinations)

### Network Issues

- Ensure collector endpoint is accessible
- Check firewall rules for port 4317
- Use `insecure=True` for local development

## References

- [OpenTelemetry Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

---

Made with Bob