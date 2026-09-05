"""
Schema Registry client service
"""

from typing import Dict, Optional
import json
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from app.config import settings
from app.core.exceptions import SchemaRegistryException
from app.core.logging import get_logger

logger = get_logger(__name__)


class SchemaRegistryService:
    """Service for interacting with Confluent Schema Registry"""
    
    def __init__(self):
        self.client: Optional[SchemaRegistryClient] = None
        self.schema_cache: Dict[str, tuple[int, Dict]] = {}
        self.cache_capacity = settings.SCHEMA_CACHE_CAPACITY
    
    async def initialize(self):
        """Initialize Schema Registry client"""
        try:
            self.client = SchemaRegistryClient({
                'url': settings.SCHEMA_REGISTRY_URL
            })
            logger.info(f"Schema Registry client initialized: {settings.SCHEMA_REGISTRY_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize Schema Registry client: {e}")
            raise SchemaRegistryException(f"Failed to initialize Schema Registry: {e}")
    
    async def get_schema(self, topic: str) -> tuple[int, Dict]:
        """
        Get Avro schema and schema ID for a topic
        
        Args:
            topic: Kafka topic name
            
        Returns:
            tuple: (schema_id, parsed_schema_dict)
            
        Raises:
            SchemaRegistryException: If schema cannot be retrieved
        """
        if self.client is None:
            raise SchemaRegistryException("Schema Registry client not initialized")
        
        # Check cache first
        cache_key = f"{topic}-value"
        if cache_key in self.schema_cache:
            logger.debug(f"Schema cache hit for {cache_key}")
            return self.schema_cache[cache_key]
        
        try:
            # Get latest schema version
            subject = f"{topic}-value"
            schema_obj = self.client.get_latest_version(subject)
            
            # Parse schema
            schema_dict = json.loads(schema_obj.schema.schema_str)
            schema_id = schema_obj.schema_id
            
            # Cache schema with ID (with size limit)
            if len(self.schema_cache) >= self.cache_capacity:
                # Remove oldest entry (simple FIFO)
                self.schema_cache.pop(next(iter(self.schema_cache)))
            
            self.schema_cache[cache_key] = (schema_id, schema_dict)
            logger.debug(f"Cached schema for {cache_key} with ID {schema_id}")
            
            return schema_id, schema_dict
            
        except Exception as e:
            logger.error(f"Failed to get schema for topic {topic}: {e}")
            raise SchemaRegistryException(f"Failed to get schema for topic {topic}: {e}")
    
    async def register_schema(self, subject: str, schema_str: str) -> int:
        """
        Register a new schema
        
        Args:
            subject: Schema subject name
            schema_str: Avro schema as JSON string
            
        Returns:
            int: Schema ID
            
        Raises:
            SchemaRegistryException: If registration fails
        """
        if self.client is None:
            raise SchemaRegistryException("Schema Registry client not initialized")
        
        try:
            schema = Schema(schema_str, schema_type="AVRO")
            schema_id = self.client.register_schema(
                subject_name=subject,
                schema=schema
            )
            logger.info(f"Registered schema '{subject}' with ID: {schema_id}")
            return schema_id
            
        except Exception as e:
            logger.error(f"Failed to register schema {subject}: {e}")
            raise SchemaRegistryException(f"Failed to register schema: {e}")
    
    async def check_compatibility(self, subject: str, schema_str: str) -> bool:
        """
        Check if schema is compatible with existing versions
        
        Args:
            subject: Schema subject name
            schema_str: Avro schema as JSON string
            
        Returns:
            bool: True if compatible
        """
        if self.client is None:
            return False
        
        try:
            schema = Schema(schema_str, schema_type="AVRO")
            is_compatible = self.client.test_compatibility(
                subject_name=subject,
                schema=schema
            )
            return is_compatible
            
        except Exception as e:
            logger.error(f"Failed to check compatibility for {subject}: {e}")
            return False
    
    def clear_cache(self):
        """Clear schema cache"""
        self.schema_cache.clear()
        logger.info("Schema cache cleared")


# Global schema registry client instance
schema_registry_client = SchemaRegistryService()

# Made with Bob
