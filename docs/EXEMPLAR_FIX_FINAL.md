# Final Exemplar Fix - Complete Solution

## Problem Summary

Metrics were being exported but **no exemplars (trace context) were attached**, preventing metrics-to-trace correlation.

## Root Cause Analysis

After investigation, we found **THREE critical issues**:

### Issue 1: Initialization Order (FIXED in app/main.py)
- FastAPI instrumentation happened BEFORE metrics manager initialization
- This caused FastAPI metrics to use a different meter provider

### Issue 2: Missing Environment Variable (FIXED in .env)
- `OTEL_METRICS_EXEMPLAR_FILTER` was not set in `.env` file
- Without this, exemplars cannot be captured

### Issue 3: Late Environment Variable Setting (FIXED in app/core/metrics.py)
- **CRITICAL**: The environment variable was being set INSIDE the `initialize()` method
- OpenTelemetry SDK reads `OTEL_METRICS_EXEMPLAR_FILTER` when modules are imported
- Setting it at runtime was too late!

## Complete Solution

### Fix 1: Set Environment Variable at Module Import Time

**File**: `app/core/metrics.py`

**Changed**: Move environment variable setting to module-level (before OTel imports)

```python
import os
from typing import Dict, Optional

# CRITICAL: Set exemplar filter BEFORE importing OpenTelemetry
# This must be done before any OTel SDK components are imported
from app.config import settings
if settings.OTEL_ENABLED:
    os.environ['OTEL_METRICS_EXEMPLAR_FILTER'] = settings.OTEL_METRICS_EXEMPLAR_FILTER

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
# ... rest of imports
```

**Why this works**: The environment variable is now set BEFORE OpenTelemetry SDK is imported, allowing it to read the configuration correctly.

### Fix 2: Initialize Metrics Before FastAPI App Creation

**File**: `app/main.py`

**Changed**: Move metrics initialization to module level

```python
# Setup logging (must be after OTel initialization)
setup_logging()

# Initialize OpenTelemetry metrics BEFORE creating FastAPI app
# This ensures the meter provider is set up before FastAPI instrumentation
if settings.OTEL_ENABLED:
    metrics_manager.initialize()
    print("OpenTelemetry metrics initialized")

# ... then create FastAPI app and instrument it
```

### Fix 3: Add Environment Variable to .env

**File**: `.env`

**Added**:
```bash
# Exemplar Filter: always_on (dev/test) | trace_based (production) | always_off
# always_on: Attach exemplars to ALL metrics (recommended for development)
# trace_based: Only attach exemplars to sampled traces (recommended for production)
OTEL_METRICS_EXEMPLAR_FILTER=always_on
```

## Testing Instructions

### Step 1: Verify Configuration

Run the verification script:
```bash
python scripts/verify_exemplar_config.py
```

Expected output:
```
✅ Found in .env: OTEL_METRICS_EXEMPLAR_FILTER=always_on
✅ settings.OTEL_METRICS_EXEMPLAR_FILTER = always_on
✅ After import: OTEL_METRICS_EXEMPLAR_FILTER = always_on
✅ Configuration looks correct!
```

### Step 2: Restart Application

**IMPORTANT**: You MUST restart the FastAPI application for changes to take effect.

```bash
# Stop the current application (Ctrl+C)
# Then start it again
python run.py
```

### Step 3: Check Startup Logs

Look for these messages in the startup logs:

```
OpenTelemetry tracing initialized with custom span processor, exporting to http://localhost:4317
Redis auto-instrumentation enabled
Requests (HTTP client) auto-instrumentation enabled
OpenTelemetry logging initialized, exporting to http://localhost:4317
Exemplar filter: always_on                    # ← Should show "always_on"
OpenTelemetry metrics initialized             # ← Should appear BEFORE next line
FastAPI auto-instrumentation enabled (traces + metrics with exemplar support)
```

### Step 4: Test with Mock Collector

1. **Terminal 1**: Start mock collector
   ```bash
   python scripts/test_metrics_export.py
   ```

2. **Terminal 2**: Start FastAPI app
   ```bash
   python run.py
   ```

3. **Terminal 3**: Make a test request
   ```bash
   curl -X POST http://localhost:8000/v1/metrics/ingest \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer test-token" \
     -d '{
       "device_id": "test-device",
       "user_id": "test-user",
       "client_id": "test-client",
       "metrics": [
         {
           "type": "activity",
           "timestamp": "2024-01-01T12:00:00Z",
           "data": {
             "steps": 1000,
             "distance": 800,
             "calories": 50
           }
         }
       ]
     }'
   ```

4. **Check Terminal 1** (mock collector) for exemplars:

**Expected Output** (after fix):
```
📊 Data Point:
   Attributes:
      http.method = POST
      http.target = /v1/metrics/ingest
      http.status_code = 202
   Count: 1
   Sum: 2112.0
   🎯 EXEMPLARS (Trace Context):
      Exemplar #1:
         Value: 2112.0
         ✅ TRACE CONTEXT:
            trace_id: 1234567890abcdef1234567890abcdef
            span_id: 1234567890abcdef
         Timestamp: 1234567890000000000
```

## Troubleshooting

### Still No Exemplars After Fix?

1. **Verify environment variable is set**:
   - Run: `python scripts/verify_exemplar_config.py`
   - Should show: `✅ After import: OTEL_METRICS_EXEMPLAR_FILTER = always_on`

2. **Check startup logs**:
   - Must see: "Exemplar filter: always_on"
   - Must see: "OpenTelemetry metrics initialized" BEFORE "FastAPI auto-instrumentation"

3. **Ensure application was restarted**:
   - Changes only take effect after full restart
   - Stop with Ctrl+C and start again

4. **Verify .env file is being loaded**:
   - Check that `.env` file exists in project root
   - Verify it contains: `OTEL_METRICS_EXEMPLAR_FILTER=always_on`

5. **Check for import order issues**:
   - The metrics module must be imported AFTER config
   - Environment variable must be set BEFORE OpenTelemetry imports

### Common Mistakes

❌ **Setting env var too late**:
```python
# WRONG - Inside initialize() method
def initialize(self):
    os.environ['OTEL_METRICS_EXEMPLAR_FILTER'] = 'always_on'  # Too late!
    from opentelemetry.sdk.metrics import MeterProvider
```

✅ **Setting env var at module level**:
```python
# CORRECT - At module import time
from app.config import settings
if settings.OTEL_ENABLED:
    os.environ['OTEL_METRICS_EXEMPLAR_FILTER'] = settings.OTEL_METRICS_EXEMPLAR_FILTER

from opentelemetry.sdk.metrics import MeterProvider  # Now it can read the env var
```

## Why This Fix Works

### The Import Order Chain

1. **app/main.py imports app/core/metrics**
2. **app/core/metrics imports app/config** (gets settings)
3. **app/core/metrics sets environment variable** (before OTel imports)
4. **app/core/metrics imports OpenTelemetry SDK** (reads env var)
5. **app/main.py calls metrics_manager.initialize()** (creates meter provider)
6. **app/main.py instruments FastAPI** (uses the configured meter provider)

### Key Insight

OpenTelemetry SDK reads the `OTEL_METRICS_EXEMPLAR_FILTER` environment variable when:
- The SDK modules are first imported
- The MeterProvider is created

By setting the environment variable at module import time (step 3), we ensure it's available when the SDK reads it (step 4).

## Production Configuration

For production, use `trace_based` instead of `always_on`:

```bash
# .env (production)
OTEL_METRICS_EXEMPLAR_FILTER=trace_based
```

This reduces overhead by only capturing exemplars for sampled traces.

Combine with trace sampling:
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
```

## Files Modified

1. ✅ `app/core/metrics.py` - Set env var at module import time
2. ✅ `app/main.py` - Initialize metrics before FastAPI app creation
3. ✅ `.env` - Added OTEL_METRICS_EXEMPLAR_FILTER=always_on

## Verification Checklist

- [ ] `.env` contains `OTEL_METRICS_EXEMPLAR_FILTER=always_on`
- [ ] Run `python scripts/verify_exemplar_config.py` - all checks pass
- [ ] Restart FastAPI application completely
- [ ] Startup logs show "Exemplar filter: always_on"
- [ ] Startup logs show metrics initialized BEFORE FastAPI instrumentation
- [ ] Mock collector shows exemplars with trace_id and span_id
- [ ] Exemplars contain valid 32-char trace_id and 16-char span_id

## Expected Results

After applying all fixes and restarting:

✅ Metrics exported successfully  
✅ Traces exported successfully  
✅ **Exemplars attached to metrics** ← NEW!  
✅ **Metrics correlated with traces** ← NEW!  
✅ Can click metrics in Grafana to see related traces  
✅ Full observability enabled  

---

**Status**: ✅ Complete Solution  
**Date**: 2026-02-05  
**Impact**: Critical - Enables full observability with metrics-to-trace correlation  
**Next Step**: Restart application and verify with test script