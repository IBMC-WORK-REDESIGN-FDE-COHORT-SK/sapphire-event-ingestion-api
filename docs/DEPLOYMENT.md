# Deployment Guide

This document provides comprehensive deployment and configuration guidelines for the Health & Fitness Telemetry Ingestion API.

## Podman Compose Configuration

### podman-compose.yml

```yaml
version: '3.8'

services:
  # Zookeeper for Kafka
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    volumes:
      - zookeeper-data:/var/lib/zookeeper/data
      - zookeeper-logs:/var/lib/zookeeper/log
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Kafka Broker 1
  kafka-1:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka-1
    depends_on:
      zookeeper:
        condition: service_healthy
    ports:
      - "9092:9092"
      - "19092:19092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-1:9092,PLAINTEXT_HOST://localhost:19092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_RETENTION_HOURS: 720  # 30 days
      KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB
      KAFKA_COMPRESSION_TYPE: snappy
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - kafka-1-data:/var/lib/kafka/data
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 5

  # Kafka Broker 2
  kafka-2:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka-2
    depends_on:
      zookeeper:
        condition: service_healthy
    ports:
      - "9093:9093"
      - "19093:19093"
    environment:
      KAFKA_BROKER_ID: 2
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-2:9093,PLAINTEXT_HOST://localhost:19093
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_RETENTION_HOURS: 720
      KAFKA_LOG_SEGMENT_BYTES: 1073741824
      KAFKA_COMPRESSION_TYPE: snappy
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - kafka-2-data:/var/lib/kafka/data
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9093"]
      interval: 10s
      timeout: 10s
      retries: 5

  # Kafka Broker 3
  kafka-3:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka-3
    depends_on:
      zookeeper:
        condition: service_healthy
    ports:
      - "9094:9094"
      - "19094:19094"
    environment:
      KAFKA_BROKER_ID: 3
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-3:9094,PLAINTEXT_HOST://localhost:19094
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_RETENTION_HOURS: 720
      KAFKA_LOG_SEGMENT_BYTES: 1073741824
      KAFKA_COMPRESSION_TYPE: snappy
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - kafka-3-data:/var/lib/kafka/data
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9094"]
      interval: 10s
      timeout: 10s
      retries: 5

  # Schema Registry
  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    container_name: schema-registry
    depends_on:
      kafka-1:
        condition: service_healthy
      kafka-2:
        condition: service_healthy
      kafka-3:
        condition: service_healthy
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka-1:9092,kafka-2:9093,kafka-3:9094
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
      SCHEMA_REGISTRY_SCHEMA_COMPATIBILITY_LEVEL: BACKWARD
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/subjects"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for rate limiting and idempotency
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - health-metrics-network
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: health-metrics-api
    depends_on:
      kafka-1:
        condition: service_healthy
      kafka-2:
        condition: service_healthy
      kafka-3:
        condition: service_healthy
      schema-registry:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      # API Settings
      API_TITLE: "Health Metrics Ingestion API"
      API_VERSION: "1.0.0"
      DEBUG: "false"
      
      # Kafka Settings
      KAFKA_BOOTSTRAP_SERVERS: "kafka-1:9092,kafka-2:9093,kafka-3:9094"
      KAFKA_CLIENT_ID: "health-ingestion-api"
      
      # Schema Registry
      SCHEMA_REGISTRY_URL: "http://schema-registry:8081"
      
      # Redis
      REDIS_URL: "redis://redis:6379/0"
      
      # Authentication
      JWT_SECRET_KEY: "${JWT_SECRET_KEY}"
      
      # OpenTelemetry
      OTEL_ENABLED: "true"
      OTEL_SERVICE_NAME: "health-metrics-ingestion-api"
      OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
    volumes:
      - ./app:/app/app
      - ./schemas:/app/schemas
    networks:
      - health-metrics-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Kafka UI (optional, for development)
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    depends_on:
      - kafka-1
      - kafka-2
      - kafka-3
      - schema-registry
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: health-metrics-cluster
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka-1:9092,kafka-2:9093,kafka-3:9094
      KAFKA_CLUSTERS_0_SCHEMAREGISTRY: http://schema-registry:8081
      KAFKA_CLUSTERS_0_METRICS_PORT: 9997
    networks:
      - health-metrics-network

  # OpenTelemetry Collector (optional)
  otel-collector:
    image: otel/opentelemetry-collector:latest
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC receiver
      - "4318:4318"  # OTLP HTTP receiver
      - "8888:8888"  # Prometheus metrics
    networks:
      - health-metrics-network

  # Prometheus (optional, for metrics)
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - health-metrics-network

  # Grafana (optional, for visualization)
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    depends_on:
      - prometheus
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - health-metrics-network

networks:
  health-metrics-network:
    driver: bridge

volumes:
  zookeeper-data:
  zookeeper-logs:
  kafka-1-data:
  kafka-2-data:
  kafka-3-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

## Dockerfile

```dockerfile
# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    librdkafka1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY ./app /app/app
COPY ./schemas /app/schemas

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment Configuration

### .env.example

```bash
# API Settings
API_TITLE="Health Metrics Ingestion API"
API_DESCRIPTION="REST API for ingesting health and fitness telemetry data"
API_VERSION="1.0.0"
DEBUG=false
ENABLE_DOCS=true

# CORS Settings
CORS_ORIGINS=["*"]

# Kafka Settings
KAFKA_BOOTSTRAP_SERVERS="kafka-1:9092,kafka-2:9093,kafka-3:9094"
KAFKA_CLIENT_ID="health-ingestion-api"
KAFKA_ACKS="all"
KAFKA_RETRIES=3
KAFKA_COMPRESSION_TYPE="snappy"
KAFKA_BATCH_SIZE=16384
KAFKA_LINGER_MS=100
KAFKA_REQUEST_TIMEOUT_MS=30000
KAFKA_ENABLE_IDEMPOTENCE=true

# Schema Registry Settings
SCHEMA_REGISTRY_URL="http://schema-registry:8081"
SCHEMA_CACHE_CAPACITY=1000

# Authentication Settings
JWT_SECRET_KEY="your-super-secret-key-change-this-in-production"
JWT_ALGORITHM="HS256"
JWT_EXPIRATION_MINUTES=60

# Rate Limiting Settings
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# Redis Settings
REDIS_URL="redis://redis:6379/0"
REDIS_MAX_CONNECTIONS=50

# Validation Settings
MAX_METRICS_PER_REQUEST=100
MAX_DATAPOINTS_PER_METRIC=1000
TIMESTAMP_TOLERANCE_MINUTES=5
TIMESTAMP_MAX_AGE_DAYS=7

# OpenTelemetry Settings
OTEL_ENABLED=true
OTEL_SERVICE_NAME="health-metrics-ingestion-api"
OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4317"

# Logging Settings
LOG_LEVEL="INFO"
LOG_FORMAT="json"
```

## Initialization Scripts

### scripts/create_topics.sh

```bash
#!/bin/bash
# Script to create Kafka topics

set -e

KAFKA_BROKER="kafka-1:9092"
REPLICATION_FACTOR=3
RETENTION_MS=2592000000  # 30 days in milliseconds

echo "Creating Kafka topics..."

# Topic configuration
declare -A TOPICS=(
    ["health.metrics.activity"]=12
    ["health.metrics.heartrate"]=12
    ["health.metrics.sleep"]=6
    ["health.metrics.bloodpressure"]=6
    ["health.metrics.glucose"]=6
    ["health.metrics.spo2"]=6
    ["health.metrics.workout"]=12
    ["health.metrics.nutrition"]=6
    ["health.metrics.custom"]=12
)

for topic in "${!TOPICS[@]}"; do
    partitions=${TOPICS[$topic]}
    
    echo "Creating topic: $topic with $partitions partitions"
    
    kafka-topics --create \
        --bootstrap-server $KAFKA_BROKER \
        --topic $topic \
        --partitions $partitions \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$RETENTION_MS \
        --config compression.type=snappy \
        --config min.insync.replicas=2 \
        --if-not-exists
done

echo "All topics created successfully!"

# List topics
echo -e "\nListing all topics:"
kafka-topics --list --bootstrap-server $KAFKA_BROKER
```

### scripts/register_schemas.py

```python
#!/usr/bin/env python3
"""
Script to register Avro schemas with Confluent Schema Registry
"""

import json
import os
from pathlib import Path
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema

# Configuration
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

# Initialize Schema Registry client
client = SchemaRegistryClient({'url': SCHEMA_REGISTRY_URL})

# Schema files mapping
SCHEMA_FILES = {
    "health.metrics.activity-value": "activity_schema.avsc",
    "health.metrics.heartrate-value": "heartrate_schema.avsc",
    "health.metrics.sleep-value": "sleep_schema.avsc",
    "health.metrics.bloodpressure-value": "bloodpressure_schema.avsc",
    "health.metrics.glucose-value": "glucose_schema.avsc",
    "health.metrics.spo2-value": "spo2_schema.avsc",
    "health.metrics.workout-value": "workout_schema.avsc",
    "health.metrics.nutrition-value": "nutrition_schema.avsc",
    "health.metrics.custom-value": "custom_schema.avsc",
}

def register_schema(subject: str, schema_file: Path):
    """Register a schema with the Schema Registry"""
    try:
        with open(schema_file, 'r') as f:
            schema_str = f.read()
        
        schema = Schema(schema_str, schema_type="AVRO")
        schema_id = client.register_schema(subject_name=subject, schema=schema)
        
        print(f"✓ Registered schema '{subject}' with ID: {schema_id}")
        return schema_id
    except Exception as e:
        print(f"✗ Failed to register schema '{subject}': {e}")
        return None

def set_compatibility(subject: str, compatibility: str = "BACKWARD"):
    """Set compatibility mode for a subject"""
    try:
        client.set_compatibility(subject_name=subject, level=compatibility)
        print(f"✓ Set compatibility for '{subject}' to: {compatibility}")
    except Exception as e:
        print(f"✗ Failed to set compatibility for '{subject}': {e}")

def main():
    """Register all schemas"""
    print(f"Registering schemas from: {SCHEMAS_DIR}")
    print(f"Schema Registry URL: {SCHEMA_REGISTRY_URL}\n")
    
    success_count = 0
    failure_count = 0
    
    for subject, filename in SCHEMA_FILES.items():
        schema_file = SCHEMAS_DIR / filename
        
        if not schema_file.exists():
            print(f"✗ Schema file not found: {schema_file}")
            failure_count += 1
            continue
        
        schema_id = register_schema(subject, schema_file)
        if schema_id:
            set_compatibility(subject, "BACKWARD")
            success_count += 1
        else:
            failure_count += 1
    
    print(f"\n{'='*60}")
    print(f"Registration complete: {success_count} succeeded, {failure_count} failed")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
```

## Deployment Steps

### Local Development with Podman Compose

```bash
# 1. Clone repository
git clone <repository-url>
cd sapphire-event-ingestion-api

# 2. Create .env file
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY

# 3. Start infrastructure services
podman-compose up -d zookeeper kafka-1 kafka-2 kafka-3 schema-registry redis

# 4. Wait for services to be healthy (check with)
podman-compose ps

# 5. Create Kafka topics
podman-compose exec kafka-1 bash /app/scripts/create_topics.sh

# 6. Register Avro schemas
python scripts/register_schemas.py

# 7. Start API service
podman-compose up -d api

# 8. Check API health
curl http://localhost:8000/v1/health

# 9. View logs
podman-compose logs -f api

# 10. Access Kafka UI (optional)
# Open browser: http://localhost:8080
```

### Production Deployment (Kubernetes)

For production deployment on Kubernetes, see the separate Kubernetes manifests in the `k8s/` directory.

## Monitoring and Observability

### Prometheus Configuration (prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'health-metrics-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-1:9997', 'kafka-2:9997', 'kafka-3:9997']

  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8888']
```

### OpenTelemetry Collector Configuration (otel-collector-config.yaml)

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

exporters:
  prometheus:
    endpoint: "0.0.0.0:8888"
  
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
    
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, logging]
```

## Maintenance Tasks

### Backup Kafka Data

```bash
# Backup Kafka topics
kafka-mirror-maker \
  --consumer.config consumer.properties \
  --producer.config producer.properties \
  --whitelist "health.metrics.*"
```

### Monitor Kafka Lag

```bash
# Check consumer lag
kafka-consumer-groups \
  --bootstrap-server kafka-1:9092 \
  --describe \
  --group <consumer-group-id>
```

### Scale API Service

```bash
# Scale to 5 replicas
podman-compose up -d --scale api=5
```

### Update Schemas

```bash
# 1. Update schema file in schemas/
# 2. Re-register schema
python scripts/register_schemas.py

# 3. Verify compatibility
curl http://localhost:8081/subjects/health.metrics.activity-value/versions
```

## Troubleshooting

### Common Issues

1. **Kafka Connection Refused**
   ```bash
   # Check Kafka broker status
   podman-compose ps kafka-1
   
   # Check Kafka logs
   podman-compose logs kafka-1
   ```

2. **Schema Registry Unavailable**
   ```bash
   # Check Schema Registry health
   curl http://localhost:8081/subjects
   
   # Restart Schema Registry
   podman-compose restart schema-registry
   ```

3. **API Not Responding**
   ```bash
   # Check API logs
   podman-compose logs api
   
   # Check API health
   curl http://localhost:8000/v1/health
   ```

4. **High Memory Usage**
   ```bash
   # Check container stats
   podman stats
   
   # Adjust memory limits in podman-compose.yml
   ```

### Debug Mode

```bash
# Run API in debug mode
podman-compose run --rm -e DEBUG=true api

# Access container shell
podman-compose exec api bash

# View real-time logs
podman-compose logs -f --tail=100 api
```

## Security Considerations

### Production Checklist

- [ ] Change default JWT_SECRET_KEY
- [ ] Enable TLS for Kafka brokers
- [ ] Enable TLS for Schema Registry
- [ ] Configure firewall rules
- [ ] Set up network policies
- [ ] Enable authentication for Kafka
- [ ] Enable authentication for Schema Registry
- [ ] Configure Redis password
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts
- [ ] Review and harden container images
- [ ] Implement secrets management (Vault, etc.)
- [ ] Enable audit logging
- [ ] Configure rate limiting per client

## Performance Tuning

### Kafka Tuning

```properties
# Increase throughput
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Optimize for latency
linger.ms=0
compression.type=lz4
```

### API Tuning

```bash
# Increase worker processes
gunicorn app.main:app \
  --workers 8 \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-connections 1000 \
  --max-requests 10000 \
  --max-requests-jitter 1000
```

### Redis Tuning

```bash
# Optimize for caching
maxmemory 2gb
maxmemory-policy allkeys-lru
save ""  # Disable persistence for cache-only use
```

## Disaster Recovery

### Backup Strategy

1. **Kafka Data**: Replicated across 3 brokers
2. **Schema Registry**: Backed up to S3/object storage
3. **Redis Data**: Periodic snapshots
4. **Application Config**: Version controlled in Git

### Recovery Procedures

```bash
# 1. Restore Kafka cluster
# 2. Restore Schema Registry
python scripts/register_schemas.py

# 3. Recreate topics
bash scripts/create_topics.sh

# 4. Restart API services
podman-compose up -d api