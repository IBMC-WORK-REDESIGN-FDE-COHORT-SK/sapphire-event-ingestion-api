"""
Application configuration using Pydantic Settings
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_TITLE: str = "Health Metrics Ingestion API"
    API_DESCRIPTION: str = "REST API for ingesting health and fitness telemetry data"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENABLE_DOCS: bool = True
    
    # CORS Settings
    CORS_ORIGINS: str = "*"  # Use comma-separated string or "*" for all origins
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "health-ingestion-api"
    KAFKA_ACKS: str = "all"
    KAFKA_RETRIES: int = 3
    KAFKA_COMPRESSION_TYPE: str = "snappy"
    KAFKA_BATCH_SIZE: int = 16384
    KAFKA_LINGER_MS: int = 100
    KAFKA_REQUEST_TIMEOUT_MS: int = 30000
    KAFKA_ENABLE_IDEMPOTENCE: bool = True
    
    # Schema Registry Settings
    SCHEMA_REGISTRY_URL: str = "http://localhost:8081"
    SCHEMA_CACHE_CAPACITY: int = 1000
    
    # Authentication Settings (Keycloak)
    KEYCLOAK_JWKS_URL: str = "http://localhost:8090/realms/saphhire-ui/protocol/openid-connect/certs"
    KEYCLOAK_ISSUER: str = "http://localhost:8090/realms/saphhire-ui"
    KEYCLOAK_AUDIENCE: str = "account"  # Default Keycloak audience
    JWT_ALGORITHM: str = "RS256"  # Keycloak uses RS256
    
    # Legacy JWT settings (for backward compatibility)
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_EXPIRATION_MINUTES: int = 60
    OAUTH2_TOKEN_URL: str = "http://localhost:8090/realms/saphhire-ui/protocol/openid-connect/token"
    
    # Redis Settings (for idempotency)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Validation Settings
    MAX_METRICS_PER_REQUEST: int = 100
    MAX_DATAPOINTS_PER_METRIC: int = 1000
    TIMESTAMP_TOLERANCE_MINUTES: int = 5
    TIMESTAMP_MAX_AGE_DAYS: int = 7
    
    # OpenTelemetry Settings
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "health-metrics-ingestion-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    # OTEL_METRICS_EXEMPLAR_FILTER: str = "always_on"  # always_on | trace_based | always_off
    
    # Rate Limiting Settings (FR-002a)
    RATE_LIMIT_RPM: int = 60  # Max requests per device per minute

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Made with Bob
