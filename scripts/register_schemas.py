#!/usr/bin/env python3
"""
Script to register Avro schemas with Confluent Schema Registry
"""

import json
import os
import sys
from pathlib import Path
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema

# Schema Registry configuration
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")

# Schema files mapping
SCHEMAS = {
    "health.metrics.activity-value": "activity_schema.avsc",
    "health.metrics.heartrate-value": "heartrate_schema.avsc",
    "health.metrics.sleep-value": "sleep_schema.avsc",
    "health.metrics.bloodpressure-value": "bloodpressure_schema.avsc",
    "health.metrics.glucose-value": "glucose_schema.avsc",
    "health.metrics.spo2-value": "spo2_schema.avsc",
    "health.metrics.workout-value": "workout_schema.avsc",
}


def get_schema_registry_client():
    """Initialize Schema Registry client"""
    return SchemaRegistryClient({'url': SCHEMA_REGISTRY_URL})


def register_schema(client: SchemaRegistryClient, subject: str, schema_file: str) -> int:
    """
    Register a schema with the Schema Registry
    
    Args:
        client: Schema Registry client
        subject: Schema subject name
        schema_file: Path to schema file
        
    Returns:
        int: Schema ID
    """
    # Get project root directory
    project_root = Path(__file__).parent.parent
    schema_path = project_root / "schemas" / schema_file
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    # Read schema
    with open(schema_path, 'r') as f:
        schema_str = f.read()
    
    # Validate JSON
    try:
        json.loads(schema_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {schema_file}: {e}")
    
    # Register schema
    schema = Schema(schema_str, schema_type="AVRO")
    schema_id = client.register_schema(
        subject_name=subject,
        schema=schema
    )
    
    print(f"✓ Registered schema '{subject}' with ID: {schema_id}")
    return schema_id


def set_compatibility(client: SchemaRegistryClient, subject: str, compatibility: str = "BACKWARD"):
    """
    Set compatibility mode for a subject
    
    Args:
        client: Schema Registry client
        subject: Schema subject name
        compatibility: Compatibility mode (BACKWARD, FORWARD, FULL, NONE)
    """
    try:
        client.set_compatibility(
            subject_name=subject,
            level=compatibility
        )
        print(f"  Set compatibility for '{subject}' to: {compatibility}")
    except Exception as e:
        print(f"  Warning: Could not set compatibility for '{subject}': {e}")


def check_schema_registry_health():
    """Check if Schema Registry is accessible"""
    import requests
    try:
        response = requests.get(f"{SCHEMA_REGISTRY_URL}/subjects", timeout=5)
        response.raise_for_status()
        print(f"✓ Schema Registry is accessible at {SCHEMA_REGISTRY_URL}")
        return True
    except Exception as e:
        print(f"✗ Schema Registry is not accessible at {SCHEMA_REGISTRY_URL}")
        print(f"  Error: {e}")
        return False


def list_registered_schemas(client: SchemaRegistryClient):
    """List all registered schemas"""
    try:
        subjects = client.get_subjects()
        if subjects:
            print("\nCurrently registered schemas:")
            for subject in subjects:
                try:
                    latest = client.get_latest_version(subject)
                    print(f"  - {subject} (ID: {latest.schema_id}, Version: {latest.version})")
                except Exception as e:
                    print(f"  - {subject} (Error: {e})")
        else:
            print("\nNo schemas currently registered.")
    except Exception as e:
        print(f"\nCould not list schemas: {e}")


def main():
    """Register all schemas"""
    print("=" * 70)
    print("Avro Schema Registration Tool")
    print("=" * 70)
    print(f"\nSchema Registry URL: {SCHEMA_REGISTRY_URL}\n")
    
    # Check Schema Registry health
    if not check_schema_registry_health():
        print("\n✗ Cannot proceed. Please ensure Schema Registry is running.")
        sys.exit(1)
    
    # Initialize client
    try:
        client = get_schema_registry_client()
    except Exception as e:
        print(f"\n✗ Failed to initialize Schema Registry client: {e}")
        sys.exit(1)
    
    # List existing schemas
    list_registered_schemas(client)
    
    # Register schemas
    print(f"\nRegistering {len(SCHEMAS)} schemas...")
    print("-" * 70)
    
    success_count = 0
    failure_count = 0
    
    for subject, schema_file in SCHEMAS.items():
        try:
            schema_id = register_schema(client, subject, schema_file)
            set_compatibility(client, subject, "BACKWARD")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to register '{subject}': {e}")
            failure_count += 1
    
    # Summary
    print("-" * 70)
    print(f"\nRegistration Summary:")
    print(f"  ✓ Success: {success_count}")
    print(f"  ✗ Failed:  {failure_count}")
    
    # List schemas after registration
    list_registered_schemas(client)
    
    print("\n" + "=" * 70)
    
    if failure_count > 0:
        sys.exit(1)
    else:
        print("✓ All schemas registered successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()

# Made with Bob
