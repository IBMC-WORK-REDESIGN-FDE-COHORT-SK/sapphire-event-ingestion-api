# Health & Fitness Telemetry Ingestion API

A scalable REST API service for ingesting health and fitness telemetry data from devices (smartwatches, fitness bands, mobile apps). Built with FastAPI, Kafka, and OpenTelemetry patterns.

## 🎯 Overview

This service provides a high-throughput, fault-tolerant ingestion pipeline for health metrics following OpenTelemetry data model patterns. It supports 9 metric categories with batch ingestion, idempotency guarantees, and comprehensive observability.

### Key Features

- ✅ **High Throughput**: Handles concurrent devices
- ✅ **Batch Ingestion**: Process multiple metrics in single request
- ✅ **Idempotency**: Duplicate request detection and handling
- ✅ **Schema Evolution**: Avro schemas with backward compatibility
- ✅ **Observability**: OpenTelemetry tracing and Prometheus metrics
- ✅ **Security**: OAuth2/JWT authentication

### Supported Metric Types

1. **Activity Metrics**: Steps, distance, calories, active minutes
2. **Heart Rate**: Continuous, resting, max, variability
3. **Sleep Data**: Duration, stages (deep, light, REM), quality
4. **Blood Pressure**: Systolic, diastolic
5. **Blood Glucose**: Fasting, post-meal levels
6. **SpO2**: Blood oxygen saturation
7. **Workout Sessions**: Duration, distance, calories, heart rate
8. **Nutrition**: Calories, macros, water intake
9. **Custom Metrics**: User-defined health metrics

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Complete system architecture, data flow, and design decisions
- **[PYDANTIC_MODELS.md](docs/PYDANTIC_MODELS.md)**: Request/response models and validation rules
- **[AVRO_SCHEMAS.md](docs/AVRO_SCHEMAS.md)**: Kafka message schemas and Schema Registry configuration
- **[FASTAPI_IMPLEMENTATION.md](docs/FASTAPI_IMPLEMENTATION.md)**: FastAPI application structure and implementation
- **[OPENTELEMETRY_METRICS.md](docs/OPENTELEMETRY_METRICS.md)**: OpenTelemetry metrics instrumentation and configuration
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Deployment guide with Podman Compose and Kubernetes
- **[IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)**: Step-by-step implementation roadmap

## 🏗️ Architecture

```
Devices -> FastAPI Service → Kafka Cluster → Downstream Consumers
                                      ↓
                              Schema Registry
```

### Technology Stack

- **API Framework**: FastAPI (Python 3.11+)
- **Message Broker**: Apache Kafka 3.x (3 brokers)
- **Schema Registry**: Confluent Schema Registry
- **Serialization**: Avro
- **Observability**: OpenTelemetry (traces + metrics)
- **Authentication**: OAuth2 with JWT
- **Container Runtime**: Podman Compose

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Podman or Docker
- Podman Compose or Docker Compose

### 1. Clone Repository

```bash
git clone <repository-url>
cd sapphire-event-ingestion-api
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY
```

### 3. Start Services

```bash
python -m venv venv
.\venv\Scripts\activate
python ./run.py
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/v1/health

# API documentation
open http://localhost:8000/docs
```

## 📡 API Usage

### Authentication

Obtain JWT token:

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "device-12345",
    "client_secret": "secret"
  }'
```

### Ingest Metrics

```bash
curl -X POST http://localhost:8000/v1/metrics/ingest \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-12345",
    "resource": {
      "attributes": {
        "device_id": "watch-12345",
        "device_type": "smartwatch",
        "user_id": "user-67890"
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
          "data_points": [
            {
              "time_unix_nano": 1706432700000000000,
              "value": 450,
              "attributes": {
                "aggregation.window": "5m"
              }
            }
          ]
        }
      }
    ]
  }'
```

### Response

```json
{
  "request_id": "req-12345",
  "status": "accepted",
  "accepted_count": 1,
  "rejected_count": 0,
  "timestamp": "2024-01-28T10:30:00Z"
}
```

## 📊 Monitoring

### OpenTelemetry Collector

The application exports metrics to an OpenTelemetry Collector via OTLP (gRPC on port 4317).

Configure the collector endpoint in `.env`:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### Available Metrics

- `http.requests.total`: Total HTTP requests
- `http.request.duration`: Request latency histogram
- `http.requests.active`: Active requests gauge
- `kafka.messages.sent.total`: Kafka messages sent
- `kafka.message.size`: Kafka message size histogram
- `metrics.ingested.total`: Total metrics ingested
- `validation.errors.total`: Validation errors
- `auth.attempts.total`: Authentication attempts

See [OPENTELEMETRY_METRICS.md](docs/OPENTELEMETRY_METRICS.md) for complete metrics documentation.

### Kafka UI

Access Kafka UI at: http://localhost:8080

### Grafana Dashboards

Access Grafana at: http://localhost:3000 (admin/admin)

Configure Grafana to query metrics from your OpenTelemetry Collector's Prometheus exporter.

## 🔧 Development

### Project Structure

```
sapphire-event-ingestion-api/
├── app/                    # FastAPI application
│   ├── api/               # API endpoints
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   ├── middleware/        # Custom middleware
│   └── core/              # Core utilities
├── schemas/               # Avro schemas
├── scripts/               # Utility scripts
├── tests/                 # Test suite
└── docs/                  # Additional documentation
```

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

## 🔐 Security

### Authentication

- OAuth2 with JWT tokens
- Token expiration: 60 minutes
- Device-based authentication

## 📝 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/metrics/ingest` | Ingest batch of metrics |
| GET | `/v1/health` | Health check |
| GET | `/v1/metrics` | List available metric types |
| GET | `/docs` | OpenAPI documentation |
| GET | `/redoc` | ReDoc documentation |

### Response Codes

| Code | Description |
|------|-------------|
| 202 | Accepted - Metrics queued for processing |
| 400 | Bad Request - Validation error |
| 401 | Unauthorized - Invalid/expired token |
| 429 | Too Many Requests - Rate limit exceeded |
| 503 | Service Unavailable - Kafka unavailable |
