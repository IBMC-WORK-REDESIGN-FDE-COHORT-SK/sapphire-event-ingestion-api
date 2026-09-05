# Testing Schema Validation

This directory contains tests for validating that the event ingestion API properly handles messages that don't conform to Avro schemas.

## Setup

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all schema validation tests:

```bash
pytest tests/test_schema_validation.py -v
```

### Run specific test:

```bash
pytest tests/test_schema_validation.py::TestSchemaValidationErrors::test_missing_required_field -v
```

### Run with coverage:

```bash
pytest tests/test_schema_validation.py --cov=app.services --cov-report=html
```

### Skip integration tests (requires running Kafka/Schema Registry):

```bash
pytest tests/test_schema_validation.py -v -m "not integration"
```

## Test Categories

### 1. Schema Validation Errors (`TestSchemaValidationErrors`)

Tests that verify Avro serialization fails when messages don't conform to schema:

- **test_missing_required_field**: Tests that missing required fields cause serialization errors
- **test_wrong_field_type**: Tests that incorrect field types (e.g., string instead of long) cause errors
- **test_invalid_enum_value**: Tests that invalid enum values are rejected
- **test_extra_field_not_in_schema**: Tests that extra fields are ignored (Avro behavior)
- **test_nested_field_missing**: Tests that missing nested required fields cause errors
- **test_valid_message_serializes_successfully**: Tests that valid messages serialize correctly
- **test_kafka_producer_handles_serialization_error**: Tests that the producer handles serialization errors gracefully
- **test_array_field_wrong_type**: Tests that wrong types in array fields cause errors

### 2. Schema Registry Errors (`TestSchemaRegistryErrors`)

Tests for Schema Registry connection and retrieval issues:

- **test_schema_not_found_in_registry**: Tests handling when schema doesn't exist
- **test_schema_registry_unavailable**: Tests handling when Schema Registry is down

### 3. Integration Tests

- **test_end_to_end_invalid_message_rejection**: Full pipeline test with running infrastructure

## Common Schema Validation Errors

### Missing Required Field

```python
# This will fail - missing 'request_id'
invalid_message = {
    "resource": {...},
    "scope": {...},
    # "request_id": "req-123",  # Missing!
    ...
}
```

### Wrong Field Type

```python
# This will fail - time_unix_nano should be long, not string
invalid_message = {
    "request_id": "req-123",
    "data_points": [
        {
            "time_unix_nano": "not-a-number",  # Wrong type!
            "value": 1000.0
        }
    ],
    ...
}
```

### Invalid Enum Value

```python
# This will fail - metric_name must be one of the defined enum symbols
invalid_message = {
    "request_id": "req-123",
    "metric_name": "invalid_metric_name",  # Not in enum!
    ...
}
```

## Manual Testing with Scripts

You can also test schema validation manually using the provided scripts:

### Test with invalid data:

```bash
# Create a test script with invalid data
python scripts/test_invalid_message.py
```

## Expected Behavior

When an invalid message is sent:

1. **Avro Serialization**: The `fastavro.schemaless_writer` will raise an exception
2. **Kafka Producer**: The `publish_metric` method will catch the exception and return `False`
3. **API Response**: The API will return an error response (500 or 503)
4. **Metrics**: A failure metric will be recorded
5. **Logs**: Error will be logged with details

## Debugging Tips

1. **Check Avro Schema**: Ensure your message structure matches the schema in `schemas/`
2. **Check Field Types**: Verify all field types match (long vs int, string vs enum, etc.)
3. **Check Required Fields**: Ensure all required fields are present
4. **Check Nested Structures**: Verify nested objects match the schema structure
5. **Check Enum Values**: Ensure enum fields use valid symbol values

## Schema Files

The Avro schemas are located in the `schemas/` directory:

- `activity_schema.avsc` - Activity metrics (steps, distance, calories)
- `heartrate_schema.avsc` - Heart rate metrics
- `bloodpressure_schema.avsc` - Blood pressure metrics
- `sleep_schema.avsc` - Sleep metrics
- `glucose_schema.avsc` - Glucose metrics
- `spo2_schema.avsc` - SpO2 metrics
- `workout_schema.avsc` - Workout metrics

Each schema defines:
- Required fields
- Field types (string, long, double, enum, etc.)
- Nested structures
- Default values
- Documentation