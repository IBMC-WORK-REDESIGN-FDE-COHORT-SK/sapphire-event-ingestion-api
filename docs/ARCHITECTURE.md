# Health & Fitness Telemetry Ingestion Service - Architecture

## 1. Overview

### Purpose
A scalable REST API service for ingesting health and fitness telemetry data from 10,000+ devices (smartwatches, fitness bands, mobile apps). The service follows OpenTelemetry metrics data model patterns and publishes data to Kafka topics for downstream processing.

### Key Design Decisions
- **Serialization**: Avro with Confluent Schema Registry for type safety and schema evolution
- **Authentication**: OAuth2/JWT for secure device authentication
- **Deployment**: Podman Compose for containerized local development
- **Retention**: 30-day retention for all Kafka topics
- **Compliance**: GDPR-compliant with data privacy controls
- **Throughput**: Designed for 10,000+ concurrent devices with batch ingestion

### Technology Stack
- **API Framework**: FastAPI (Python 3.11+)
- **Message Broker**: Apache Kafka 3.x
- **Schema Registry**: Confluent Schema Registry
- **Kafka Client**: aiokafka (async Python client)
- **Serialization**: fastavro (Avro)
- **Observability**: OpenTelemetry (traces + metrics)
- **Authentication**: OAuth2 with JWT tokens
- **Validation**: Pydantic v2
- **Container Runtime**: Podman Compose

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DEVICES LAYER                            │
│  (Smartwatches, Fitness Bands, Mobile Apps - 10k+ devices)      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS + JWT
                         │ Batch Requests
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY / LB                            │
│              (Rate Limiting, TLS Termination)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FASTAPI INGESTION SERVICE                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Auth Layer   │  │ Validation   │  │ OpenTelemetry      │   │
│  │ (JWT)        │→ │ (Pydantic)   │→ │ (Tracing/Metrics)  │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Kafka Producer (aiokafka + Avro)                 │  │
│  │  - Async batching                                        │  │
│  │  - Idempotency tracking                                  │  │
│  │  - Circuit breaker                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ Avro Messages
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONFLUENT SCHEMA REGISTRY                     │
│              (Schema Versioning & Validation)                    │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APACHE KAFKA CLUSTER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Broker 1     │  │ Broker 2     │  │ Broker 3     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  Topics (30-day retention):                                     │
│  - health.metrics.activity                                      │
│  - health.metrics.heartrate                                     │
│  - health.metrics.sleep                                         │
│  - health.metrics.bloodpressure                                 │
│  - health.metrics.glucose                                       │
│  - health.metrics.spo2                                          │
│  - health.metrics.workout                                       │
│  - health.metrics.nutrition                                     │
│  - health.metrics.custom                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DOWNSTREAM CONSUMERS                           │
│  (Analytics, ML Pipelines, Data Warehouse, Alerting)            │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### 1. FastAPI Ingestion Service
- **Authentication**: Validate JWT tokens, enforce device identity
- **Request Validation**: Validate incoming payloads using Pydantic models
- **Idempotency**: Track request IDs to prevent duplicate processing
- **Rate Limiting**: Per-device rate limits (e.g., 100 req/min)
- **Batch Processing**: Accept batches of metrics in single request
- **Avro Serialization**: Convert JSON to Avro using schema registry
- **Kafka Publishing**: Async publish to appropriate topics
- **Observability**: Emit traces and metrics via OpenTelemetry
- **Error Handling**: Graceful degradation, retry logic, circuit breakers

#### 2. Kafka Cluster
- **Message Persistence**: Durable storage with 30-day retention
- **Partitioning**: Distribute load across partitions by device_id
- **Replication**: 3x replication for fault tolerance
- **Ordering**: Guarantee ordering per device within partition

#### 3. Schema Registry
- **Schema Management**: Store and version Avro schemas
- **Compatibility Checking**: Enforce backward/forward compatibility
- **Schema Evolution**: Support adding optional fields

#### 4. Observability Stack
- **Traces**: Request flow through system (OpenTelemetry)
- **Metrics**: Throughput, latency, error rates (Prometheus)
- **Logs**: Structured JSON logs with correlation IDs

---

## 3. Data Flow

### Ingestion Flow

```
1. Device → API: POST /v1/metrics/ingest
   - Headers: Authorization: Bearer <JWT>
   - Body: Batch of metrics (JSON)

2. API Gateway:
   - TLS termination
   - Rate limiting check
   - Forward to FastAPI service

3. FastAPI Service:
   a. JWT validation (extract device_id, user_id)
   b. Request validation (Pydantic)
   c. Idempotency check (request_id in cache)
   d. OpenTelemetry span creation
   
4. For each metric in batch:
   a. Determine metric type → topic mapping
   b. Fetch Avro schema from registry
   c. Serialize to Avro format
   d. Prepare Kafka message:
      - Key: device_id (for partitioning)
      - Value: Avro-encoded metric
      - Headers: trace_id, span_id, timestamp
   
5. Kafka Producer:
   a. Batch messages (up to 100ms or 1000 messages)
   b. Async send to topic
   c. Handle acks (wait for all replicas)
   
6. Response to Device:
   - 202 Accepted (async processing)
   - Response body: { "request_id", "accepted_count", "rejected_count" }
```

### Error Handling Flow

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Validation     │──── Fail ───→ 400 Bad Request
└──────┬──────────┘
       │ Pass
       ▼
┌─────────────────┐
│ Kafka Publish   │
└──────┬──────────┘
       │
       ├─── Success ───→ 202 Accepted
       │
       ├─── Retriable Error (network) ───→ Retry (3x) ───→ 503 Service Unavailable
       │
       └─── Non-Retriable Error ───→ 500 Internal Server Error
```

---

## 4. Data Model (OpenTelemetry-Inspired)

### Core Structure

Following OpenTelemetry metrics model with health-specific adaptations:

```python
{
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "device.type": "smartwatch",
      "device.manufacturer": "FitBrand",
      "device.model": "FitWatch Pro",
      "user.id": "user-67890",
      "app.version": "2.1.0"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.activity.steps",
      "description": "Step count aggregated over time window",
      "unit": "steps",
      "data": {
        "data_points": [
          {
            "attributes": {
              "aggregation.window": "5m",
              "activity.type": "walking"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706432700000000000,
            "value": 450
          }
        ]
      }
    }
  ]
}
```

### Metric Naming Convention

Format: `health.<category>.<metric_name>`

Examples:
- `health.activity.steps`
- `health.activity.distance`
- `health.activity.calories`
- `health.heartrate.bpm`
- `health.heartrate.resting`
- `health.heartrate.max`
- `health.sleep.duration`
- `health.sleep.stage.deep`
- `health.bloodpressure.systolic`
- `health.bloodpressure.diastolic`
- `health.glucose.level`
- `health.spo2.percentage`
- `health.workout.duration`
- `health.nutrition.calories`
- `health.custom.<user_defined>`

### Units

Standard units following UCUM (Unified Code for Units of Measure):

| Metric Type | Unit | UCUM Code |
|-------------|------|-----------|
| Steps | steps | {steps} |
| Distance | meters | m |
| Calories | kilocalories | kcal |
| Heart Rate | beats per minute | {beats}/min |
| Sleep Duration | seconds | s |
| Blood Pressure | millimeters of mercury | mm[Hg] |
| Blood Glucose | milligrams per deciliter | mg/dL |
| SpO2 | percentage | % |
| Workout Duration | seconds | s |

---

## 5. API Specification

### Base URL
```
https://api.healthmetrics.example.com/v1
```

### Authentication
All endpoints require OAuth2 JWT token in Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

JWT Claims:
```json
{
  "sub": "user-67890",
  "device_id": "watch-12345",
  "scope": "metrics:write",
  "exp": 1706443200,
  "iat": 1706432400
}
```

### Endpoints

#### POST /v1/metrics/ingest

Ingest batch of health metrics.

**Request Headers:**
```
Authorization: Bearer <JWT>
Content-Type: application/json
X-Request-ID: <UUID> (optional, for idempotency)
X-Device-Timezone: America/Los_Angeles (optional)
```

**Request Body:**
```json
{
  "request_id": "req-uuid-12345",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "device.type": "smartwatch",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.activity.steps",
      "unit": "steps",
      "data": {
        "data_points": [...]
      }
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "request_id": "req-uuid-12345",
  "status": "accepted",
  "accepted_count": 15,
  "rejected_count": 0,
  "timestamp": "2024-01-28T10:30:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid metric format",
    "details": [
      {
        "field": "metrics[0].data.data_points[0].value",
        "issue": "Value must be a positive number"
      }
    ],
    "request_id": "req-uuid-12345",
    "timestamp": "2024-01-28T10:30:00Z"
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired JWT token",
    "timestamp": "2024-01-28T10:30:00Z"
  }
}
```

**Response (429 Too Many Requests):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 100 requests per minute",
    "retry_after": 45,
    "timestamp": "2024-01-28T10:30:00Z"
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Kafka cluster temporarily unavailable",
    "retry_after": 30,
    "timestamp": "2024-01-28T10:30:00Z"
  }
}
```

#### GET /v1/health

Health check endpoint (no auth required).

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "kafka": "healthy",
    "schema_registry": "healthy"
  },
  "timestamp": "2024-01-28T10:30:00Z"
}
```

#### GET /v1/metrics

Get available metric types and schemas (requires auth).

**Response (200 OK):**
```json
{
  "metric_types": [
    {
      "name": "health.activity.steps",
      "category": "activity",
      "unit": "steps",
      "description": "Step count",
      "schema_version": 1
    }
  ]
}
```

---

## 6. Kafka Design

### Topic Naming Convention

Format: `health.metrics.<category>`

All topics use:
- **Namespace**: `health.metrics`
- **Category**: Metric category (activity, heartrate, sleep, etc.)
- **Environment**: Prefix with env for multi-env (e.g., `prod.health.metrics.activity`)

### Topic Configuration

| Metric Type | Topic Name | Partitions | Replication | Retention | Key |
|-------------|------------|------------|-------------|-----------|-----|
| Activity | `health.metrics.activity` | 12 | 3 | 30 days | device_id |
| Heart Rate | `health.metrics.heartrate` | 12 | 3 | 30 days | device_id |
| Sleep | `health.metrics.sleep` | 6 | 3 | 30 days | device_id |
| Blood Pressure | `health.metrics.bloodpressure` | 6 | 3 | 30 days | device_id |
| Blood Glucose | `health.metrics.glucose` | 6 | 3 | 30 days | device_id |
| SpO2 | `health.metrics.spo2` | 6 | 3 | 30 days | device_id |
| Workout | `health.metrics.workout` | 12 | 3 | 30 days | device_id |
| Nutrition | `health.metrics.nutrition` | 6 | 3 | 30 days | device_id |
| Custom | `health.metrics.custom` | 12 | 3 | 30 days | device_id |

**Partitioning Strategy:**
- **Key**: `device_id` ensures all metrics from same device go to same partition
- **Ordering**: Guarantees ordering per device
- **Partition Count**: Based on expected throughput (activity/workout higher)
- **Scaling**: Can increase partitions without downtime

### Message Format

**Kafka Message Structure:**
```
Key: device_id (string)
Value: Avro-encoded metric payload
Headers:
  - trace_id: OpenTelemetry trace ID
  - span_id: OpenTelemetry span ID
  - request_id: Original request ID (idempotency)
  - timestamp: Message creation timestamp
  - schema_version: Avro schema version
```

### Avro Schema Strategy

**Schema Naming**: `<topic-name>-value` (e.g., `health.metrics.activity-value`)

**Compatibility Mode**: BACKWARD (consumers can read old data with new schema)

**Evolution Rules**:
- New fields must have defaults
- Cannot remove required fields
- Cannot change field types
- Can add optional fields

### Producer Configuration

```python
producer_config = {
    'bootstrap_servers': 'kafka:9092',
    'client_id': 'health-ingestion-api',
    'acks': 'all',  # Wait for all replicas
    'retries': 3,
    'max_in_flight_requests_per_connection': 5,
    'enable_idempotence': True,  # Exactly-once semantics
    'compression_type': 'snappy',
    'batch_size': 16384,  # 16KB
    'linger_ms': 100,  # Wait up to 100ms to batch
    'request_timeout_ms': 30000,
    'delivery_timeout_ms': 120000
}
```

### Error Handling & Retry Strategy

**Retriable Errors:**
- Network timeouts
- Broker not available
- Leader not available

**Retry Policy:**
- Max retries: 3
- Backoff: Exponential (100ms, 200ms, 400ms)
- Circuit breaker: Open after 5 consecutive failures

**Non-Retriable Errors:**
- Invalid schema
- Serialization errors
- Authorization failures

**Dead Letter Queue:**
- Topic: `health.metrics.dlq`
- Store failed messages with error metadata
- Manual review and reprocessing

---

## 7. Example Payloads

### 1. Activity Metrics (Steps)

**Request:**
```json
{
  "request_id": "req-act-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "device.type": "smartwatch",
      "device.manufacturer": "FitBrand",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.activity.steps",
      "description": "Step count in 5-minute window",
      "unit": "steps",
      "data": {
        "data_points": [
          {
            "attributes": {
              "aggregation.window": "5m",
              "activity.type": "walking"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706432700000000000,
            "value": 450
          },
          {
            "attributes": {
              "aggregation.window": "5m",
              "activity.type": "running"
            },
            "start_time_unix_nano": 1706432700000000000,
            "time_unix_nano": 1706433000000000000,
            "value": 820
          }
        ]
      }
    },
    {
      "name": "health.activity.distance",
      "description": "Distance traveled",
      "unit": "m",
      "data": {
        "data_points": [
          {
            "attributes": {
              "aggregation.window": "5m"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706432700000000000,
            "value": 350.5
          }
        ]
      }
    },
    {
      "name": "health.activity.calories",
      "description": "Calories burned",
      "unit": "kcal",
      "data": {
        "data_points": [
          {
            "attributes": {
              "aggregation.window": "5m"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706432700000000000,
            "value": 25.3
          }
        ]
      }
    }
  ]
}
```

### 2. Heart Rate

**Request:**
```json
{
  "request_id": "req-hr-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.heartrate.bpm",
      "description": "Continuous heart rate measurements",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.type": "continuous",
              "activity.state": "resting"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 68
          },
          {
            "attributes": {
              "measurement.type": "continuous",
              "activity.state": "active"
            },
            "time_unix_nano": 1706432460000000000,
            "value": 125
          }
        ]
      }
    },
    {
      "name": "health.heartrate.resting",
      "description": "Resting heart rate (daily)",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.period": "daily"
            },
            "start_time_unix_nano": 1706400000000000000,
            "time_unix_nano": 1706432400000000000,
            "value": 62
          }
        ]
      }
    },
    {
      "name": "health.heartrate.max",
      "description": "Maximum heart rate in period",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.period": "1h"
            },
            "start_time_unix_nano": 1706428800000000000,
            "time_unix_nano": 1706432400000000000,
            "value": 165
          }
        ]
      }
    }
  ]
}
```

### 3. Sleep Data

**Request:**
```json
{
  "request_id": "req-sleep-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.sleep.duration",
      "description": "Total sleep duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "sleep.session_id": "sleep-20240128"
            },
            "start_time_unix_nano": 1706396400000000000,
            "time_unix_nano": 1706425200000000000,
            "value": 28800
          }
        ]
      }
    },
    {
      "name": "health.sleep.stage.deep",
      "description": "Deep sleep duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "sleep.session_id": "sleep-20240128",
              "sleep.stage": "deep"
            },
            "start_time_unix_nano": 1706396400000000000,
            "time_unix_nano": 1706425200000000000,
            "value": 7200
          }
        ]
      }
    },
    {
      "name": "health.sleep.stage.rem",
      "description": "REM sleep duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "sleep.session_id": "sleep-20240128",
              "sleep.stage": "rem"
            },
            "start_time_unix_nano": 1706396400000000000,
            "time_unix_nano": 1706425200000000000,
            "value": 6480
          }
        ]
      }
    },
    {
      "name": "health.sleep.stage.light",
      "description": "Light sleep duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "sleep.session_id": "sleep-20240128",
              "sleep.stage": "light"
            },
            "start_time_unix_nano": 1706396400000000000,
            "time_unix_nano": 1706425200000000000,
            "value": 14400
          }
        ]
      }
    },
    {
      "name": "health.sleep.quality",
      "description": "Sleep quality score (0-100)",
      "unit": "{score}",
      "data": {
        "data_points": [
          {
            "attributes": {
              "sleep.session_id": "sleep-20240128"
            },
            "start_time_unix_nano": 1706396400000000000,
            "time_unix_nano": 1706425200000000000,
            "value": 85
          }
        ]
      }
    }
  ]
}
```

### 4. Blood Pressure

**Request:**
```json
{
  "request_id": "req-bp-001",
  "resource": {
    "attributes": {
      "device.id": "bp-monitor-789",
      "device.type": "blood_pressure_monitor",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.bloodpressure.systolic",
      "description": "Systolic blood pressure",
      "unit": "mm[Hg]",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.position": "sitting",
              "measurement.arm": "left"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 118
          }
        ]
      }
    },
    {
      "name": "health.bloodpressure.diastolic",
      "description": "Diastolic blood pressure",
      "unit": "mm[Hg]",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.position": "sitting",
              "measurement.arm": "left"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 76
          }
        ]
      }
    },
    {
      "name": "health.heartrate.bpm",
      "description": "Heart rate during BP measurement",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.context": "blood_pressure"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 72
          }
        ]
      }
    }
  ]
}
```

### 5. Blood Glucose

**Request:**
```json
{
  "request_id": "req-glucose-001",
  "resource": {
    "attributes": {
      "device.id": "glucometer-456",
      "device.type": "glucose_meter",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.glucose.level",
      "description": "Blood glucose level",
      "unit": "mg/dL",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.timing": "fasting",
              "measurement.method": "fingerstick"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 95
          },
          {
            "attributes": {
              "measurement.timing": "post_meal",
              "measurement.method": "fingerstick",
              "meal.type": "breakfast"
            },
            "time_unix_nano": 1706439600000000000,
            "value": 142
          }
        ]
      }
    }
  ]
}
```

### 6. SpO2 (Blood Oxygen)

**Request:**
```json
{
  "request_id": "req-spo2-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.spo2.percentage",
      "description": "Blood oxygen saturation",
      "unit": "%",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.type": "spot_check",
              "activity.state": "resting"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 98
          },
          {
            "attributes": {
              "measurement.type": "continuous",
              "activity.state": "sleeping"
            },
            "time_unix_nano": 1706396400000000000,
            "value": 96
          }
        ]
      }
    }
  ]
}
```

### 7. Workout Session

**Request:**
```json
{
  "request_id": "req-workout-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.workout.duration",
      "description": "Workout session duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "workout.type": "running",
              "workout.session_id": "workout-20240128-001",
              "workout.intensity": "moderate"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706436000000000000,
            "value": 3600
          }
        ]
      }
    },
    {
      "name": "health.workout.distance",
      "description": "Distance covered in workout",
      "unit": "m",
      "data": {
        "data_points": [
          {
            "attributes": {
              "workout.session_id": "workout-20240128-001"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706436000000000000,
            "value": 8500
          }
        ]
      }
    },
    {
      "name": "health.workout.calories",
      "description": "Calories burned during workout",
      "unit": "kcal",
      "data": {
        "data_points": [
          {
            "attributes": {
              "workout.session_id": "workout-20240128-001"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706436000000000000,
            "value": 485
          }
        ]
      }
    },
    {
      "name": "health.heartrate.average",
      "description": "Average heart rate during workout",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "workout.session_id": "workout-20240128-001"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706436000000000000,
            "value": 152
          }
        ]
      }
    },
    {
      "name": "health.heartrate.max",
      "description": "Maximum heart rate during workout",
      "unit": "{beats}/min",
      "data": {
        "data_points": [
          {
            "attributes": {
              "workout.session_id": "workout-20240128-001"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706436000000000000,
            "value": 178
          }
        ]
      }
    }
  ]
}
```

### 8. Nutrition Log

**Request:**
```json
{
  "request_id": "req-nutrition-001",
  "resource": {
    "attributes": {
      "device.id": "phone-app-999",
      "device.type": "mobile_app",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.nutrition.calories",
      "description": "Caloric intake",
      "unit": "kcal",
      "data": {
        "data_points": [
          {
            "attributes": {
              "meal.type": "breakfast",
              "meal.id": "meal-20240128-001"
            },
            "time_unix_nano": 1706425200000000000,
            "value": 450
          }
        ]
      }
    },
    {
      "name": "health.nutrition.protein",
      "description": "Protein intake",
      "unit": "g",
      "data": {
        "data_points": [
          {
            "attributes": {
              "meal.id": "meal-20240128-001"
            },
            "time_unix_nano": 1706425200000000000,
            "value": 25
          }
        ]
      }
    },
    {
      "name": "health.nutrition.carbohydrates",
      "description": "Carbohydrate intake",
      "unit": "g",
      "data": {
        "data_points": [
          {
            "attributes": {
              "meal.id": "meal-20240128-001"
            },
            "time_unix_nano": 1706425200000000000,
            "value": 55
          }
        ]
      }
    },
    {
      "name": "health.nutrition.fat",
      "description": "Fat intake",
      "unit": "g",
      "data": {
        "data_points": [
          {
            "attributes": {
              "meal.id": "meal-20240128-001"
            },
            "time_unix_nano": 1706425200000000000,
            "value": 18
          }
        ]
      }
    },
    {
      "name": "health.nutrition.water",
      "description": "Water intake",
      "unit": "mL",
      "data": {
        "data_points": [
          {
            "attributes": {
              "intake.type": "water"
            },
            "time_unix_nano": 1706425200000000000,
            "value": 250
          }
        ]
      }
    }
  ]
}
```

### 9. Custom Metric

**Request:**
```json
{
  "request_id": "req-custom-001",
  "resource": {
    "attributes": {
      "device.id": "watch-12345",
      "user.id": "user-67890"
    }
  },
  "scope": {
    "name": "health.metrics.collector",
    "version": "1.0.0"
  },
  "metrics": [
    {
      "name": "health.custom.stress_level",
      "description": "User-reported stress level",
      "unit": "{score}",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.method": "user_input",
              "scale.min": "0",
              "scale.max": "10"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 6
          }
        ]
      }
    },
    {
      "name": "health.custom.mood",
      "description": "User-reported mood",
      "unit": "{category}",
      "data": {
        "data_points": [
          {
            "attributes": {
              "measurement.method": "user_input",
              "mood.category": "happy"
            },
            "time_unix_nano": 1706432400000000000,
            "value": 1
          }
        ]
      }
    },
    {
      "name": "health.custom.meditation_duration",
      "description": "Meditation session duration",
      "unit": "s",
      "data": {
        "data_points": [
          {
            "attributes": {
              "session.type": "guided",
              "session.id": "meditation-001"
            },
            "start_time_unix_nano": 1706432400000000000,
            "time_unix_nano": 1706433300000000000,
            "value": 900
          }
        ]
      }
    }
  ]
}
```

---

## 8. Security & Compliance

### Authentication & Authorization

**OAuth2 Flow:**
```
1. Device Registration:
   - Device registers with auth service
   - Receives client_id and client_secret

2. Token Acquisition:
   POST /oauth/token
   {
     "grant_type": "client_credentials",
     "client_id": "device-12345",
     "client_secret": "secret",
     "scope": "metrics:write"
   }
   
   Response:
   {
     "access_token": "eyJhbGc...",
     "token_type": "Bearer",
     "expires_in": 3600
   }

3. API Request:
   Authorization: Bearer eyJhbGc...
```

**JWT Token Structure:**
```json
{
  "sub": "user-67890",
  "device_id": "watch-12345",
  "scope": "metrics:write",
  "iss": "https://auth.healthmetrics.example.com",
  "aud": "https://api.healthmetrics.example.com",
  "exp": 1706443200,
  "iat": 1706432400,
  "jti": "token-uuid-123"
}
```

### Rate Limiting

**Per-Device Limits:**
- 100 requests per minute
- 1000 requests per hour
- 10,000 requests per day

**Implementation:**
- Redis-backed sliding window counter
- Return 429 with Retry-After header
- Exponential backoff recommended

### Data Privacy (GDPR)

**Personal Data Handling:**
1. **Pseudonymization**: Use device_id and user_id (not PII)
2. **Encryption at Rest**: Kafka data encrypted (AES-256)
3. **Encryption in Transit**: TLS 1.3 for all connections
4. **Data Minimization**: Only collect necessary attributes
5. **Right to Erasure**: Support deletion requests via separate API
6. **Data Portability**: Export API for user data
7. **Consent Management**: Track consent in user profile
8. **Audit Logging**: Log all data access

**GDPR Compliance Checklist:**
- [ ] Data Processing Agreement (DPA) with users
- [ ] Privacy Policy clearly states data usage
- [ ] Consent mechanism for data collection
- [ ] Data retention policy (30 days in Kafka)
- [ ] Deletion API for right to be forgotten
- [ ] Data export API for portability
- [ ] Audit logs for data access
- [ ] Encryption at rest and in transit
- [ ] Pseudonymization of identifiers
- [ ] Data breach notification process

### HIPAA Considerations

While primarily GDPR-focused, consider these HIPAA elements:

1. **PHI Protection**: Health data is PHI under HIPAA
2. **Access Controls**: Role-based access to data
3. **Audit Trails**: Comprehensive logging
4. **Encryption**: End-to-end encryption
5. **Business Associate Agreements**: Required for vendors
6. **Breach Notification**: 60-day notification requirement

---

## 9. Observability

### OpenTelemetry Integration

**Traces:**
```python
# Trace structure
Trace: /v1/metrics/ingest
├─ Span: validate_jwt
├─ Span: validate_request
├─ Span: serialize_to_avro
│  ├─ Span: fetch_schema
│  └─ Span: encode_message
└─ Span: publish_to_kafka
   ├─ Span: send_to_topic_activity
   └─ Span: send_to_topic_heartrate
```

**Metrics to Collect:**
- `http_requests_total` (counter): Total requests by endpoint, status
- `http_request_duration_seconds` (histogram): Request latency
- `kafka_messages_published_total` (counter): Messages by topic
- `kafka_publish_errors_total` (counter): Errors by topic, error_type
- `kafka_publish_duration_seconds` (histogram): Publish latency
- `validation_errors_total` (counter): Validation errors by field
- `active_devices` (gauge): Currently active devices
- `request_batch_size` (histogram): Metrics per request

**Logs:**
```json
{
  "timestamp": "2024-01-28T10:30:00Z",
  "level": "INFO",
  "message": "Metrics ingested successfully",
  "trace_id": "abc123",
  "span_id": "def456",
  "request_id": "req-uuid-12345",
  "device_id": "watch-12345",
  "user_id": "user-67890",
  "metrics_count": 15,
  "topics": ["health.metrics.activity", "health.metrics.heartrate"],
  "duration_ms": 45
}
```

### Monitoring Dashboards

**Key Metrics:**
1. Request rate (req/s)
2. Error rate (%)
3. P50, P95, P99 latency
4. Kafka publish success rate
5. Active devices
6. Topic throughput
7. Schema registry latency

**Alerts:**
- Error rate > 1% for 5 minutes
- P99 latency > 1s for 5 minutes
- Kafka publish failures > 10 in 1 minute
- Schema registry unavailable

---

## 10. Scalability & Performance

### Horizontal Scaling

**API Service:**
- Stateless design (no local state)
- Scale pods based on CPU/memory
- Target: 70% CPU utilization
- Min replicas: 3
- Max replicas: 20

**Kafka Cluster:**
- Add brokers for increased throughput
- Rebalance partitions automatically
- Monitor disk usage (alert at 70%)

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Request Latency (P95) | < 200ms | End-to-end API response |
| Request Latency (P99) | < 500ms | End-to-end API response |
| Throughput | 10,000 req/s | Sustained load |
| Kafka Publish Latency | < 50ms | Producer ack time |
| Error Rate | < 0.1% | Failed requests / total |
| Availability | 99.9% | Uptime per month |

### Backpressure Handling

**Strategy:**
1. **Circuit Breaker**: Open after 5 consecutive Kafka failures
2. **Graceful Degradation**: Return 503 when circuit open
3. **Queue Depth Monitoring**: Alert when Kafka lag > 10k messages
4. **Rate Limiting**: Protect service from overload
5. **Async Processing**: Non-blocking Kafka publish

**Circuit Breaker States:**
```
CLOSED (normal) → OPEN (failures) → HALF_OPEN (testing) → CLOSED
```

---

## 11. Operational Considerations

### Deployment

**Container Images:**
- Base: `python:3.11-slim`
- Multi-stage build for smaller images
- Security scanning with Trivy
- Image registry: Private registry or Docker Hub

**Environment Variables:**
```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_SECURITY_PROTOCOL