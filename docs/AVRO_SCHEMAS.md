# Avro Schema Definitions

This document contains all Avro schema definitions for the Health & Fitness Telemetry Ingestion API. These schemas are registered with Confluent Schema Registry and used for serializing messages to Kafka topics.

## Schema Registry Configuration

### Compatibility Mode
- **Mode**: BACKWARD
- **Rationale**: Allows consumers to read old data with new schemas
- **Evolution Rules**:
  - New fields must have defaults
  - Cannot remove required fields
  - Cannot change field types
  - Can add optional fields

### Schema Naming Convention
- **Format**: `<topic-name>-value`
- **Examples**:
  - `health.metrics.activity-value`
  - `health.metrics.heartrate-value`
  - `health.metrics.sleep-value`

### Schema Versioning
- **Initial Version**: 1
- **Version Increment**: Automatic on schema update
- **Version Strategy**: Semantic versioning in schema metadata

## Common Types

### Resource Attributes Schema
```json
{
  "type": "record",
  "name": "ResourceAttributes",
  "namespace": "com.healthmetrics.telemetry",
  "doc": "Device and user identification attributes",
  "fields": [
    {
      "name": "device_id",
      "type": "string",
      "doc": "Unique device identifier"
    },
    {
      "name": "device_type",
      "type": "string",
      "doc": "Type of device (smartwatch, fitness_band, mobile_app, etc.)"
    },
    {
      "name": "device_manufacturer",
      "type": ["null", "string"],
      "default": null,
      "doc": "Device manufacturer"
    },
    {
      "name": "device_model",
      "type": ["null", "string"],
      "default": null,
      "doc": "Device model"
    },
    {
      "name": "user_id",
      "type": "string",
      "doc": "Unique user identifier (pseudonymized)"
    },
    {
      "name": "app_version",
      "type": ["null", "string"],
      "default": null,
      "doc": "Application version"
    }
  ]
}
```

### Resource Schema
```json
{
  "type": "record",
  "name": "Resource",
  "namespace": "com.healthmetrics.telemetry",
  "doc": "Resource information following OpenTelemetry model",
  "fields": [
    {
      "name": "attributes",
      "type": "ResourceAttributes",
      "doc": "Resource attributes"
    }
  ]
}
```

### Scope Schema
```json
{
  "type": "record",
  "name": "Scope",
  "namespace": "com.healthmetrics.telemetry",
  "doc": "Instrumentation scope following OpenTelemetry model",
  "fields": [
    {
      "name": "name",
      "type": "string",
      "doc": "Scope name (e.g., health.metrics.collector)"
    },
    {
      "name": "version",
      "type": "string",
      "doc": "Scope version"
    }
  ]
}
```

### Data Point Schema
```json
{
  "type": "record",
  "name": "DataPoint",
  "namespace": "com.healthmetrics.telemetry",
  "doc": "Individual metric data point following OpenTelemetry model",
  "fields": [
    {
      "name": "attributes",
      "type": {
        "type": "map",
        "values": "string"
      },
      "default": {},
      "doc": "Additional attributes as key-value pairs"
    },
    {
      "name": "start_time_unix_nano",
      "type": ["null", "long"],
      "default": null,
      "doc": "Start time in nanoseconds (for aggregated metrics)"
    },
    {
      "name": "time_unix_nano",
      "type": "long",
      "doc": "Measurement timestamp in nanoseconds since Unix epoch"
    },
    {
      "name": "value",
      "type": "double",
      "doc": "Metric value"
    }
  ]
}
```

## Topic-Specific Schemas

### 1. Activity Metrics Schema

**Topic**: `health.metrics.activity`  
**Schema Name**: `health.metrics.activity-value`

```json
{
  "type": "record",
  "name": "ActivityMetric",
  "namespace": "com.healthmetrics.telemetry.activity",
  "doc": "Activity metrics (steps, distance, calories)",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "ActivityMetricType",
        "symbols": [
          "health_activity_steps",
          "health_activity_distance",
          "health_activity_calories",
          "health_activity_active_minutes",
          "health_activity_floors_climbed"
        ]
      },
      "doc": "Type of activity metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (steps, m, kcal, min, floors)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 2. Heart Rate Metrics Schema

**Topic**: `health.metrics.heartrate`  
**Schema Name**: `health.metrics.heartrate-value`

```json
{
  "type": "record",
  "name": "HeartRateMetric",
  "namespace": "com.healthmetrics.telemetry.heartrate",
  "doc": "Heart rate metrics (continuous, resting, max)",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "HeartRateMetricType",
        "symbols": [
          "health_heartrate_bpm",
          "health_heartrate_resting",
          "health_heartrate_max",
          "health_heartrate_average",
          "health_heartrate_variability"
        ]
      },
      "doc": "Type of heart rate metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (beats/min or ms for HRV)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 3. Sleep Metrics Schema

**Topic**: `health.metrics.sleep`  
**Schema Name**: `health.metrics.sleep-value`

```json
{
  "type": "record",
  "name": "SleepMetric",
  "namespace": "com.healthmetrics.telemetry.sleep",
  "doc": "Sleep metrics (duration, stages, quality)",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "SleepMetricType",
        "symbols": [
          "health_sleep_duration",
          "health_sleep_stage_deep",
          "health_sleep_stage_light",
          "health_sleep_stage_rem",
          "health_sleep_stage_awake",
          "health_sleep_quality"
        ]
      },
      "doc": "Type of sleep metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (s for duration, score for quality)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 4. Blood Pressure Metrics Schema

**Topic**: `health.metrics.bloodpressure`  
**Schema Name**: `health.metrics.bloodpressure-value`

```json
{
  "type": "record",
  "name": "BloodPressureMetric",
  "namespace": "com.healthmetrics.telemetry.bloodpressure",
  "doc": "Blood pressure metrics (systolic, diastolic)",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "BloodPressureMetricType",
        "symbols": [
          "health_bloodpressure_systolic",
          "health_bloodpressure_diastolic",
          "health_bloodpressure_pulse_pressure"
        ]
      },
      "doc": "Type of blood pressure metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (mm[Hg])"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 5. Blood Glucose Metrics Schema

**Topic**: `health.metrics.glucose`  
**Schema Name**: `health.metrics.glucose-value`

```json
{
  "type": "record",
  "name": "GlucoseMetric",
  "namespace": "com.healthmetrics.telemetry.glucose",
  "doc": "Blood glucose metrics",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "GlucoseMetricType",
        "symbols": [
          "health_glucose_level",
          "health_glucose_fasting",
          "health_glucose_post_meal"
        ]
      },
      "doc": "Type of glucose metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (mg/dL or mmol/L)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 6. SpO2 Metrics Schema

**Topic**: `health.metrics.spo2`  
**Schema Name**: `health.metrics.spo2-value`

```json
{
  "type": "record",
  "name": "SpO2Metric",
  "namespace": "com.healthmetrics.telemetry.spo2",
  "doc": "Blood oxygen saturation metrics",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "SpO2MetricType",
        "symbols": [
          "health_spo2_percentage",
          "health_spo2_average",
          "health_spo2_min"
        ]
      },
      "doc": "Type of SpO2 metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (%)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 7. Workout Metrics Schema

**Topic**: `health.metrics.workout`  
**Schema Name**: `health.metrics.workout-value`

```json
{
  "type": "record",
  "name": "WorkoutMetric",
  "namespace": "com.healthmetrics.telemetry.workout",
  "doc": "Workout session metrics",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "WorkoutMetricType",
        "symbols": [
          "health_workout_duration",
          "health_workout_distance",
          "health_workout_calories",
          "health_workout_elevation_gain",
          "health_workout_pace",
          "health_workout_power"
        ]
      },
      "doc": "Type of workout metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (s, m, kcal, min/km, W)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 8. Nutrition Metrics Schema

**Topic**: `health.metrics.nutrition`  
**Schema Name**: `health.metrics.nutrition-value`

```json
{
  "type": "record",
  "name": "NutritionMetric",
  "namespace": "com.healthmetrics.telemetry.nutrition",
  "doc": "Nutrition intake metrics",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": {
        "type": "enum",
        "name": "NutritionMetricType",
        "symbols": [
          "health_nutrition_calories",
          "health_nutrition_protein",
          "health_nutrition_carbohydrates",
          "health_nutrition_fat",
          "health_nutrition_fiber",
          "health_nutrition_water",
          "health_nutrition_sodium",
          "health_nutrition_sugar"
        ]
      },
      "doc": "Type of nutrition metric"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (kcal, g, mL, mg)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

### 9. Custom Metrics Schema

**Topic**: `health.metrics.custom`  
**Schema Name**: `health.metrics.custom-value`

```json
{
  "type": "record",
  "name": "CustomMetric",
  "namespace": "com.healthmetrics.telemetry.custom",
  "doc": "User-defined custom health metrics",
  "fields": [
    {
      "name": "request_id",
      "type": "string",
      "doc": "Original request ID for idempotency tracking"
    },
    {
      "name": "resource",
      "type": "com.healthmetrics.telemetry.Resource",
      "doc": "Resource information"
    },
    {
      "name": "scope",
      "type": "com.healthmetrics.telemetry.Scope",
      "doc": "Instrumentation scope"
    },
    {
      "name": "metric_name",
      "type": "string",
      "doc": "Custom metric name (must start with health.custom.)"
    },
    {
      "name": "unit",
      "type": "string",
      "doc": "Metric unit (user-defined)"
    },
    {
      "name": "data_points",
      "type": {
        "type": "array",
        "items": "com.healthmetrics.telemetry.DataPoint"
      },
      "doc": "Array of data points"
    },
    {
      "name": "ingestion_timestamp",
      "type": "long",
      "doc": "Timestamp when message was ingested by API (Unix nano)"
    },
    {
      "name": "schema_version",
      "type": "int",
      "default": 1,
      "doc": "Schema version"
    }
  ]
}
```

## Schema Evolution Examples

### Adding Optional Field (BACKWARD Compatible)

**Version 1**:
```json
{
  "type": "record",
  "name": "ActivityMetric",
  "fields": [
    {"name": "request_id", "type": "string"},
    {"name": "metric_name", "type": "string"}
  ]
}
```

**Version 2** (adds optional field):
```json
{
  "type": "record",
  "name": "ActivityMetric",
  "fields": [
    {"name": "request_id", "type": "string"},
    {"name": "metric_name", "type": "string"},
    {
      "name": "quality_score",
      "type": ["null", "int"],
      "default": null,
      "doc": "Data quality score (0-100)"
    }
  ]
}
```

### Adding Enum Value (FORWARD Compatible)

**Version 1**:
```json
{
  "type": "enum",
  "name": "ActivityMetricType",
  "symbols": ["health_activity_steps", "health_activity_distance"]
}
```

**Version 2** (adds new symbol):
```json
{
  "type": "enum",
  "name": "ActivityMetricType",
  "symbols": [
    "health_activity_steps",
    "health_activity_distance",
    "health_activity_elevation"
  ]
}
```

## Schema Registration Script

### Python Script for Registering Schemas

```python
#!/usr/bin/env python3
"""
Script to register Avro schemas with Confluent Schema Registry
"""

import json
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema

# Schema Registry configuration
SCHEMA_REGISTRY_URL = "http://localhost:8081"

# Initialize client
schema_registry_client = SchemaRegistryClient({
    'url': SCHEMA_REGISTRY_URL
})

def register_schema(subject: str, schema_str: str):
    """Register a schema with the Schema Registry"""
    schema = Schema(schema_str, schema_type="AVRO")
    schema_id = schema_registry_client.register_schema(
        subject_name=subject,
        schema=schema
    )
    print(f"Registered schema '{subject}' with ID: {schema_id}")
    return schema_id

def set_compatibility(subject: str, compatibility: str = "BACKWARD"):
    """Set compatibility mode for a subject"""
    schema_registry_client.set_compatibility(
        subject_name=subject,
        level=compatibility
    )
    print(f"Set compatibility for '{subject}' to: {compatibility}")

# Schema definitions
schemas = {
    "health.metrics.activity-value": "activity_schema.avsc",
    "health.metrics.heartrate-value": "heartrate_schema.avsc",
    "health.metrics.sleep-value": "sleep_schema.avsc",
    "health.metrics.bloodpressure-value": "bloodpressure_schema.avsc",
    "health.metrics.glucose-value": "glucose_schema.avsc",
    "health.metrics.spo2-value": "spo2_schema.avsc",
    "health.metrics.workout-value": "workout_schema.avsc",
    "health.metrics.nutrition-value": "nutrition_schema.avsc",
    "health.metrics.custom-value": "custom_schema.avsc"
}

def main():
    """Register all schemas"""
    for subject, schema_file in schemas.items():
        with open(f"schemas/{schema_file}", "r") as f:
            schema_str = f.read()
        
        # Register schema
        register_schema(subject, schema_str)
        
        # Set compatibility mode
        set_compatibility(subject, "BACKWARD")

if __name__ == "__main__":
    main()
```

## Schema Validation

### Validation Rules

1. **Required Fields**: All non-nullable fields must be present
2. **Type Checking**: Values must match declared types
3. **Enum Validation**: Enum values must be in declared symbols
4. **Array Validation**: Arrays must contain valid items
5. **Map Validation**: Map values must match declared type

### Example Validation Code

```python
from fastavro import validate
from fastavro.schema import load_schema

def validate_message(schema_file: str, message: dict) -> bool:
    """Validate a message against an Avro schema"""
    schema = load_schema(schema_file)
    try:
        validate(message, schema)
        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False
```

## Performance Considerations

### Serialization Performance

| Format | Serialization Speed | Deserialization Speed | Size |
|--------|-------------------|---------------------|------|
| JSON | Baseline (1x) | Baseline (1x) | Baseline (1x) |
| Avro | 2-3x faster | 3-4x faster | 30-50% smaller |

### Best Practices

1. **Reuse Schema Objects**: Cache parsed schemas to avoid repeated parsing
2. **Batch Serialization**: Serialize multiple messages together
3. **Schema Caching**: Cache schema registry lookups
4. **Connection Pooling**: Reuse HTTP connections to schema registry
5. **Compression**: Use Snappy compression for Kafka messages

## Monitoring Schema Registry

### Key Metrics

- Schema registration rate
- Schema lookup latency
- Schema compatibility check failures
- Schema registry availability

### Health Check

```bash
# Check Schema Registry health
curl http://localhost:8081/subjects

# Get schema by ID
curl http://localhost:8081/schemas/ids/1

# Get latest schema version
curl http://localhost:8081/subjects/health.metrics.activity-value/versions/latest
```

## Troubleshooting

### Common Issues

1. **Incompatible Schema**: Check compatibility mode and evolution rules
2. **Schema Not Found**: Verify schema is registered and subject name is correct
3. **Serialization Error**: Validate message structure matches schema
4. **Connection Timeout**: Check Schema Registry connectivity and health

### Debug Commands

```bash
# List all subjects
curl http://localhost:8081/subjects

# Get schema versions
curl http://localhost:8081/subjects/health.metrics.activity-value/versions

# Get specific version
curl http://localhost:8081/subjects/health.metrics.activity-value/versions/1

# Check compatibility
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "..."}' \
  http://localhost:8081/compatibility/subjects/health.metrics.activity-value/versions/latest