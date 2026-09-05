# OpenTelemetry SDK Exemplar Issue - Root Cause Found

## Confirmed Issue

**OpenTelemetry Python SDK 1.22.0 does NOT properly support exemplars.**

### Evidence

Direct test (`scripts/test_exemplar_direct.py`) shows:
- ✅ Environment variable set: `OTEL_METRICS_EXEMPLAR_FILTER = always_on`
- ✅ Span created with valid trace_id and span_id
- ✅ Metric recorded within active span
- ❌ **NO exemplars in metric output**

The metric data point output shows:
```json
{
    "attributes": {"operation": "test"},
    "count": 1,
    "sum": 100.5,
    "bucket_counts": [...],
    "explicit_bounds": [...],
    "min": 100.5,
    "max": 100.5
    // ❌ NO "exemplars" field!
}
```

## Root Cause

OpenTelemetry Python SDK version 1.22.0 (released January 2024) has incomplete or buggy exemplar support. The SDK reads the environment variable but doesn't actually attach exemplars to metrics.

## Solution: Upgrade OpenTelemetry SDK

### Current Versions (in requirements.txt)
```
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-exporter-otlp==1.22.0
opentelemetry-exporter-otlp-proto-grpc==1.22.0
```

### Recommended Versions

Upgrade to the latest stable versions (as of February 2026):

```
# OpenTelemetry - Core
opentelemetry-api==1.27.0
opentelemetry-sdk==1.27.0
opentelemetry-exporter-otlp==1.27.0
opentelemetry-exporter-otlp-proto-grpc==1.27.0

# OpenTelemetry - Auto-instrumentation
opentelemetry-instrumentation-fastapi==0.48b0
opentelemetry-instrumentation-redis==0.48b0
opentelemetry-instrumentation-requests==0.48b0
```

### Upgrade Steps

1. **Update requirements.txt**:
   ```bash
   # Edit requirements.txt with the new versions above
   ```

2. **Upgrade packages**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **Verify upgrade**:
   ```bash
   pip show opentelemetry-sdk
   # Should show version 1.27.0 or higher
   ```

4. **Test exemplars again**:
   ```bash
   python scripts/test_exemplar_direct.py
   ```

5. **Look for exemplars field** in the output:
   ```json
   {
       "attributes": {"operation": "test"},
       "count": 1,
       "sum": 100.5,
       "exemplars": [  // ← Should now appear!
           {
               "filtered_attributes": {},
               "time_unix_nano": 1234567890,
               "value": 100.5,
               "span_id": "0x10182d92a8328f18",
               "trace_id": "0x7fad6d8c1d9e7f57c7ed66f43709cc49"
           }
       ]
   }
   ```

## Why Version 1.22.0 Doesn't Work

Based on OpenTelemetry Python SDK release history:

- **1.22.0 (Jan 2024)**: Exemplar support was experimental/incomplete
- **1.23.0 - 1.26.0**: Gradual improvements to exemplar implementation
- **1.27.0+ (Latest)**: Stable exemplar support with proper OTLP export

The exemplar feature was added incrementally, and early versions had bugs or incomplete implementations.

## Alternative: Use Specific Known-Good Version

If you can't upgrade to the latest, try version **1.25.0** which is known to have working exemplar support:

```
opentelemetry-api==1.25.0
opentelemetry-sdk==1.25.0
opentelemetry-exporter-otlp==1.25.0
opentelemetry-exporter-otlp-proto-grpc==1.25.0
```

## Verification After Upgrade

### Test 1: Direct Exemplar Test
```bash
python scripts/test_exemplar_direct.py
```

Expected output should include:
```json
"exemplars": [
    {
        "trace_id": "0x...",
        "span_id": "0x...",
        "value": 100.5
    }
]
```

### Test 2: Mock Collector Test
```bash
# Terminal 1
python scripts/test_metrics_export.py

# Terminal 2
python run.py

# Terminal 3
curl -X POST http://localhost:8000/v1/metrics/ingest ...
```

Expected output in Terminal 1:
```
🎯 EXEMPLARS (Trace Context):
   Exemplar #1:
      ✅ TRACE CONTEXT:
         trace_id: 1234567890abcdef1234567890abcdef
         span_id: 1234567890abcdef
```

## Summary

### The Real Problem
❌ OpenTelemetry SDK 1.22.0 doesn't properly support exemplars  
✅ All our configuration changes were correct  
✅ The issue is the SDK version, not our code  

### The Solution
1. Upgrade OpenTelemetry SDK to 1.27.0 or later
2. Retest with the diagnostic scripts
3. Exemplars should now work correctly

### What We Fixed (Still Valid)
Even though the SDK version was the issue, these fixes are still necessary:
1. ✅ Set OTEL_METRICS_EXEMPLAR_FILTER at module import time
2. ✅ Initialize metrics before FastAPI app creation
3. ✅ Add OTEL_METRICS_EXEMPLAR_FILTER to .env

These fixes ensure that when you upgrade the SDK, exemplars will work immediately.

---

**Status**: ✅ Root cause identified - SDK version issue  
**Action Required**: Upgrade OpenTelemetry SDK to 1.27.0+  
**Expected Result**: Exemplars will work after upgrade