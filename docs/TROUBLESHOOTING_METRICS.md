# Troubleshooting: Verify Metrics are Sent to OTEL Collector

## ✅ Quick Test: Use the Mock Collector Script

The easiest way to verify metrics export is to use our test script that acts as a mock OTEL collector:

### Step 1: Start the Mock Collector

```bash
# Terminal 1: Start the mock collector
python scripts/test_metrics_export.py
```

You should see:
```
================================================================================
🚀 Mock OpenTelemetry Collector started
📡 Listening on [::]:4317
================================================================================

Waiting for metrics exports from your application...
Start your FastAPI app and make some requests to generate metrics.
```

### Step 2: Start Your Application

```bash
# Terminal 2: Start your FastAPI application
python run.py
```

### Step 3: Generate Some Traffic

```bash
# Terminal 3: Make some API requests
curl -X GET http://localhost:8000/v1/health

# Or use the health check endpoint
curl http://localhost:8000/v1/health/ready
```

### Step 4: Check the Mock Collector Output

In Terminal 1, you should see metrics being received every 60 seconds:

```
================================================================================
📊 Received metrics export request #1
================================================================================

🏷️  Resource Attributes:
   service.name = health-metrics-ingestion-api

📦 Scope: app.core.metrics

📈 Metric: http.requests.total
   Description: Total HTTP requests
   Unit: 1
   Type: Sum (aggregation_temporality=2)
   Is Monotonic: True

   📊 Data Point:
      Attributes:
         method = GET
         endpoint = /v1/health
         status = 200
         🔗 TRACE CONTEXT FOUND:
            ✅ trace_id: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
            ✅ span_id: x1y2z3w4v5u6t7s8
      Value: 1

📈 Metric: http.server.duration
   Description: HTTP request duration
   Unit: s
   Type: Histogram

   📊 Data Point:
      Attributes:
         method = GET
         http.route = /v1/health
         status_code = 200
      Count: 1
      Sum: 0.025
      Buckets: 15

================================================================================
✅ Total metrics exports received: 1
✅ Total data points received: 5
================================================================================
```

### What to Look For

✅ **Success Indicators:**
- Mock collector receives metric export requests (every 60 seconds)
- **Custom metrics** with trace context:
  - `http.requests.total` (with trace_id, span_id)
  - `kafka.messages.sent.total` (with trace_id, span_id)
  - `metrics.ingested.total` (with trace_id, span_id)
- **Auto-instrumented metrics** without trace context:
  - `http.server.duration`
  - `http.server.active_requests`
- Data points have expected values
- Resource attributes include service.name

❌ **Failure Indicators:**
- No metrics received after 60 seconds
- Connection errors in application logs
- Missing trace context in custom metrics
- Only auto-instrumented metrics (no custom metrics)
- Error messages in mock collector

## Common Issues and Solutions

### Issue 1: No Metrics Received

**Symptoms:**
- Mock collector shows no output after 60+ seconds
- Application starts but no metrics appear

**Solutions:**

1. **Check OTEL is enabled:**
   ```bash
   # In .env file
   OTEL_ENABLED=true
   ```

2. **Verify endpoint configuration:**
   ```bash
   # In .env file
   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   ```

3. **Check application logs for errors:**
   ```bash
   python run.py 2>&1 | grep -i "otel\|metric"
   ```

4. **Verify metrics manager is initialized:**
   ```python
   # Should see in logs:
   # "OpenTelemetry metrics initialized, exporting to http://localhost:4317"
   ```

### Issue 2: Connection Refused

**Symptoms:**
- Application logs show: `Connection refused` or `Failed to export metrics`

**Solutions:**

1. **Ensure mock collector is running first:**
   ```bash
   # Start mock collector BEFORE starting the app
   python scripts/test_metrics_export.py
   ```

2. **Check port is not in use:**
   ```bash
   # On Linux/Mac
   lsof -i :4317
   
   # On Windows
   netstat -ano | findstr :4317
   ```

3. **Try different endpoint:**
   ```bash
   # In .env
   OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
   ```

### Issue 3: Missing Trace Context

**Symptoms:**
- Metrics are received but don't show "🔗 TRACE CONTEXT FOUND"
- Only auto-instrumented metrics appear

**Solutions:**

1. **Verify custom metrics are being recorded:**
   ```python
   # Check that your code calls:
   metrics_manager.record_http_request(...)
   metrics_manager.record_kafka_message(...)
   ```

2. **Ensure spans are active:**
   ```python
   from opentelemetry import trace
   span = trace.get_current_span()
   print(f"Span recording: {span.is_recording()}")
   ```

3. **Check trace context helper:**
   ```python
   from app.core.metrics import get_trace_context_attributes
   attrs = get_trace_context_attributes()
   print(f"Trace attrs: {attrs}")  # Should have trace_id and span_id
   ```

### Issue 4: Metrics Export Interval Too Long

**Symptoms:**
- Metrics take too long to appear (60 seconds default)

**Solutions:**

1. **Reduce export interval for testing:**
   ```python
   # In app/core/metrics.py, change:
   reader = PeriodicExportingMetricReader(
       exporter=exporter,
       export_interval_millis=10000  # 10 seconds instead of 60
   )
   ```

2. **Force flush metrics:**
   ```python
   from opentelemetry import metrics
   meter_provider = metrics.get_meter_provider()
   meter_provider.force_flush()
   ```

## Detailed Verification Steps

### Step 1: Check Application Logs

Look for OpenTelemetry initialization messages:

```bash
python run.py

# Expected output:
OpenTelemetry tracing initialized with custom span processor, exporting to http://localhost:4317
Redis auto-instrumentation enabled
Requests (HTTP client) auto-instrumentation enabled
OpenTelemetry logging initialized, exporting to http://localhost:4317
OpenTelemetry metrics initialized, exporting to http://localhost:4317  # ← Important!
FastAPI auto-instrumentation enabled (traces + metrics)
```

### Step 2: Verify Configuration

```python
# Quick config check
from app.config import settings
print(f"OTEL Enabled: {settings.OTEL_ENABLED}")
print(f"Service Name: {settings.OTEL_SERVICE_NAME}")
print(f"OTEL Endpoint: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
```

### Step 3: Test with Real OTEL Collector

If using a real OTEL collector:

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
  logging:
    loglevel: debug  # Shows metrics in collector logs
  
  prometheus:
    endpoint: "0.0.0.0:8889"
    enable_open_metrics: true  # For exemplar support

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [logging, prometheus]
    
    traces:
      receivers: [otlp]
      exporters: [logging]
```

Start collector:
```bash
docker run -p 4317:4317 -p 4318:4318 -p 8889:8889 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector:latest \
  --config=/etc/otel-collector-config.yaml
```

### Step 4: Check Prometheus Endpoint

If using Prometheus exporter:

```bash
# Check metrics are available
curl http://localhost:8889/metrics

# Look for your custom metrics
curl http://localhost:8889/metrics | grep "http_requests_total"
curl http://localhost:8889/metrics | grep "trace_id"  # Check for exemplars
```

### Step 5: Enable Debug Logging

For detailed troubleshooting:

```bash
# Set environment variable
export OTEL_LOG_LEVEL=debug
python run.py
```

Or in code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Expected Metrics

### Custom Metrics (With Trace Context)

These should include `trace_id` and `span_id` attributes:

- `http.requests.total` - HTTP request counter
- `http.request.duration` - Request duration histogram
- `kafka.messages.sent.total` - Kafka message counter
- `kafka.message.size` - Message size histogram
- `metrics.ingested.total` - Ingested metrics counter
- `validation.errors.total` - Validation error counter
- `auth.attempts.total` - Auth attempt counter

### Auto-Instrumented Metrics (Without Trace Context)

These come from FastAPI instrumentation:

- `http.server.duration` - HTTP request duration
- `http.server.active_requests` - Active HTTP requests
- `http.server.request.size` - Request body size
- `http.server.response.size` - Response body size

## Testing Checklist

- [ ] Mock collector starts successfully on port 4317
- [ ] Application starts without errors
- [ ] Application logs show "OpenTelemetry metrics initialized"
- [ ] Mock collector receives metrics within 60 seconds
- [ ] Custom metrics include trace_id and span_id
- [ ] Auto-instrumented metrics are present
- [ ] Resource attributes include service.name
- [ ] Data point values are reasonable
- [ ] No connection errors in logs

## Need More Help?

1. **Check application logs** for OpenTelemetry errors
2. **Run mock collector** with the test script
3. **Enable debug logging** for detailed output
4. **Verify configuration** in .env file
5. **Review documentation**:
   - [METRICS_TO_TRACE_CORRELATION.md](./METRICS_TO_TRACE_CORRELATION.md)
   - [AUTO_INSTRUMENTED_METRICS_REALITY.md](./AUTO_INSTRUMENTED_METRICS_REALITY.md)
   - [OBSERVABILITY_SUMMARY.md](./OBSERVABILITY_SUMMARY.md)

## Made with Bob