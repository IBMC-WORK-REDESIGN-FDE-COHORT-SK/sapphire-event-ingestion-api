# Exemplar Fix - Metrics to Trace Correlation

## Problem

Metrics were being exported successfully, but **no exemplars (trace context) were being attached** to the metrics. This prevented metrics-to-trace correlation in observability tools like Grafana.

### Symptoms
- ✅ Metrics exported successfully
- ✅ Traces exported successfully  
- ❌ No exemplars in metrics data points
- ❌ Cannot correlate metrics to traces

### Root Causes

Two critical issues were identified:

#### 1. Initialization Order Problem

**Issue**: FastAPI auto-instrumentation was happening BEFORE the metrics manager was initialized.

**Location**: `app/main.py`

**Problem Code**:
```python
# Metrics initialized in lifespan (line 102)
@asynccontextmanager
async def lifespan(app: FastAPI):
    metrics_manager.initialize()  # ❌ Too late!
    ...

# FastAPI instrumented earlier (line 152)
if settings.OTEL_ENABLED:
    FastAPIInstrumentor.instrument_app(
        app,
        meter_provider=metrics.get_meter_provider(),  # ❌ Gets default provider
    )
```

**Impact**: FastAPI's auto-instrumented metrics used a different meter provider without exemplar support.

#### 2. Missing Environment Variable

**Issue**: `OTEL_METRICS_EXEMPLAR_FILTER` was not set in `.env` file.

**Location**: `.env`

**Impact**: Even with correct initialization, exemplars wouldn't be captured without this setting.

## Solution

### Fix 1: Correct Initialization Order

**Changed**: Moved metrics initialization BEFORE FastAPI app creation and instrumentation.

**File**: `app/main.py`

```python
# Setup logging (must be after OTel initialization)
setup_logging()

# Initialize OpenTelemetry metrics BEFORE creating FastAPI app
# This ensures the meter provider is set up before FastAPI instrumentation
if settings.OTEL_ENABLED:
    metrics_manager.initialize()
    print("OpenTelemetry metrics initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("Starting Health Metrics Ingestion API...")
    
    # Initialize Kafka producer (metrics already initialized)
    await kafka_producer.start()
    ...
```

**Key Changes**:
- ✅ Metrics initialized at module level (before app creation)
- ✅ FastAPI instrumentation now uses the correct meter provider
- ✅ Exemplar filter configuration is applied to all metrics

### Fix 2: Add Exemplar Filter Configuration

**Added**: `OTEL_METRICS_EXEMPLAR_FILTER` to `.env` file.

**File**: `.env`

```bash
# Exemplar Filter: always_on (dev/test) | trace_based (production) | always_off
# always_on: Attach exemplars to ALL metrics (recommended for development)
# trace_based: Only attach exemplars to sampled traces (recommended for production)
OTEL_METRICS_EXEMPLAR_FILTER=always_on
```

**Options**:
- `always_on`: Attach exemplars to ALL metrics (development/testing)
- `trace_based`: Only attach exemplars to sampled traces (production)
- `always_off`: Disable exemplars completely

## How Exemplars Work

### Automatic Capture

When a metric is recorded within an active span, OpenTelemetry automatically:

1. **Captures trace context** from the current span
2. **Attaches it as an exemplar** to the metric data point
3. **Exports it** with the metric to the collector

### Example Flow

```
HTTP Request → Span Created → Metric Recorded → Exemplar Attached
                    ↓              ↓                    ↓
              trace_id=abc    duration=0.5s    {trace_id: abc, span_id: xyz}
              span_id=xyz
```

### Exemplar Data Structure

```json
{
  "metric": "http.request.duration",
  "value": 0.5,
  "attributes": {
    "method": "POST",
    "endpoint": "/v1/ingest",
    "status": "200"
  },
  "exemplar": {
    "trace_id": "abc123...",
    "span_id": "xyz789...",
    "timestamp": 1234567890
  }
}
```

## Verification

### Test with Mock Collector

1. **Start the mock collector**:
   ```bash
   python scripts/test_metrics_export.py
   ```

2. **Start the FastAPI application**:
   ```bash
   python run.py
   ```

3. **Make a test request**:
   ```bash
   curl -X POST http://localhost:8000/v1/ingest \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer test-token" \
     -d '{"device_id": "test", "metrics": []}'
   ```

4. **Check the mock collector output** for:
   ```
   🎯 EXEMPLARS (Trace Context):
      Exemplar #1:
         ✅ TRACE CONTEXT:
            trace_id: abc123...
            span_id: xyz789...
   ```

### Expected Output

**Before Fix**:
```
ℹ️  No exemplars attached to this data point
   Possible reasons:
   - No active span when metric was recorded
   - OTEL_METRICS_EXEMPLAR_FILTER not set to 'always_on'
```

**After Fix**:
```
🎯 EXEMPLARS (Trace Context):
   Exemplar #1:
      Value: 0.5
      ✅ TRACE CONTEXT:
         trace_id: 1234567890abcdef1234567890abcdef
         span_id: 1234567890abcdef
      Timestamp: 1234567890000000000
```

## Benefits

With exemplars properly configured:

1. **Metrics → Traces**: Click on a metric spike in Grafana to see related traces
2. **Traces → Metrics**: See metric values in trace context
3. **Root Cause Analysis**: Quickly identify which requests caused metric anomalies
4. **Performance Investigation**: Correlate slow requests with high latency metrics

## Production Considerations

### Exemplar Filter Settings

**Development/Testing**:
```bash
OTEL_METRICS_EXEMPLAR_FILTER=always_on
```
- Captures exemplars for ALL metrics
- Best for debugging and testing
- Higher overhead

**Production**:
```bash
OTEL_METRICS_EXEMPLAR_FILTER=trace_based
```
- Only captures exemplars for sampled traces
- Reduces overhead
- Still provides correlation for important requests

### Sampling Strategy

In production, combine with trace sampling:

```python
# Example: Sample 10% of traces
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1)  # 10% sampling
```

With `trace_based` filter:
- Only sampled traces get exemplars
- Reduces storage and processing overhead
- Still provides correlation for representative requests

## Troubleshooting

### No Exemplars After Fix

1. **Check environment variable**:
   ```bash
   echo $OTEL_METRICS_EXEMPLAR_FILTER
   # Should output: always_on
   ```

2. **Verify metrics initialization**:
   - Check startup logs for "OpenTelemetry metrics initialized"
   - Should appear BEFORE "FastAPI auto-instrumentation enabled"

3. **Confirm active spans**:
   - Exemplars only attach when metrics are recorded within active spans
   - FastAPI auto-instrumentation creates spans for all HTTP requests

4. **Check OTLP exporter**:
   - Ensure using OTLP exporter (not Prometheus)
   - Prometheus exporter doesn't support exemplars in all versions

### Exemplars in Attributes Instead

If you see `trace_id` and `span_id` in metric attributes:
- ❌ Wrong: These should be in exemplars, not attributes
- ✅ Fix: Ensure using the corrected code (don't manually add trace context)

## References

- [OpenTelemetry Metrics Specification](https://opentelemetry.io/docs/specs/otel/metrics/)
- [Exemplars Specification](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exemplars)
- [Grafana Exemplars Documentation](https://grafana.com/docs/grafana/latest/fundamentals/exemplars/)

## Related Files

- `app/main.py` - Application initialization and instrumentation
- `app/core/metrics.py` - Metrics manager with exemplar support
- `.env` - Environment configuration
- `scripts/test_metrics_export.py` - Mock collector for testing

---

**Status**: ✅ Fixed  
**Date**: 2026-02-05  
**Impact**: High - Enables full observability with metrics-to-trace correlation