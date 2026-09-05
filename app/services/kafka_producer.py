"""
Kafka producer service with Avro serialization
"""

import asyncio
import struct
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from io import BytesIO

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastavro import schemaless_writer
from opentelemetry import trace

from app.config import settings
from app.core.exceptions import KafkaException
from app.core.logging import get_logger
from app.services.schema_registry import schema_registry_client
from app.utils.topic_mapper import get_topic_for_metric

# Import metrics
from app.core.metrics import metrics_manager

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


class KafkaProducerService:
    """Async Kafka producer with Avro serialization"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False
        
    async def start(self):
        """Initialize and start Kafka producer"""
        if self._started:
            return
            
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                client_id=settings.KAFKA_CLIENT_ID,
                acks=settings.KAFKA_ACKS,
                max_batch_size=settings.KAFKA_BATCH_SIZE,
                linger_ms=settings.KAFKA_LINGER_MS,
                request_timeout_ms=settings.KAFKA_REQUEST_TIMEOUT_MS,
                enable_idempotence=settings.KAFKA_ENABLE_IDEMPOTENCE,
            )
            
            await self.producer.start()
            self._started = True
            logger.info("Kafka producer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise KafkaException(f"Failed to start Kafka producer: {e}")
    
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")
    
    async def publish_metric(
        self,
        metric_name: str,
        message: Dict[str, Any],
        user_id: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> bool:
        """
        Publish a metric message to Kafka
        
        Args:
            metric_name: Name of the metric (e.g., health.activity.steps)
            message: Message payload (will be Avro-encoded)
            user_id: User ID (used as partition key)
            trace_id: OpenTelemetry trace ID
            span_id: OpenTelemetry span ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._started or self.producer is None:
            raise KafkaException("Kafka producer not started")
        
        with tracer.start_as_current_span("kafka_publish") as span:
            try:
                # Get topic for metric
                topic = get_topic_for_metric(metric_name)
                span.set_attribute("kafka.topic", topic)
                span.set_attribute("metric.name", metric_name)
                
                # Get Avro schema and schema ID
                schema_id, schema = await schema_registry_client.get_schema(topic)
                
                # Serialize message to Avro with Confluent wire format
                avro_bytes = self._serialize_avro_confluent(message, schema, schema_id)
                span.set_attribute("message.size", len(avro_bytes))
                span.set_attribute("schema.id", schema_id)
                
                # Prepare headers
                headers = [
                    ("ingestion_timestamp", str(datetime.utcnow().timestamp()).encode()),
                ]
                if trace_id:
                    headers.append(("trace_id", trace_id.encode()))
                if span_id:
                    headers.append(("span_id", span_id.encode()))
                
                # Send to Kafka
                await self.producer.send(
                    topic=topic,
                    value=avro_bytes,
                    key=user_id.encode(),
                    headers=headers
                )
                
                # Record metrics
                metrics_manager.record_kafka_message(topic, "success", len(avro_bytes))
                
                logger.debug(f"Published metric {metric_name} to topic {topic}")
                span.set_attribute("publish.success", True)
                return True
                
            except KafkaError as e:
                logger.error(f"Kafka error publishing metric: {e}")
                span.set_attribute("publish.success", False)
                span.record_exception(e)
                
                # Record failure metric
                try:
                    topic = get_topic_for_metric(metric_name)
                    metrics_manager.record_kafka_message(topic, "failure", 0)
                except:
                    pass
                
                raise KafkaException(f"Failed to publish metric: {e}")
            except Exception as e:
                logger.error(f"Error publishing metric: {e}")
                span.set_attribute("publish.success", False)
                span.record_exception(e)
                
                # Record failure metric
                try:
                    topic = get_topic_for_metric(metric_name)
                    metrics_manager.record_kafka_message(topic, "failure", 0)
                except:
                    pass
                
                return False
    
    def _serialize_avro_confluent(self, message: Dict[str, Any], schema: Dict, schema_id: int) -> bytes:
        """
        Serialize message to Avro format with Confluent wire format
        
        Confluent wire format:
        - Byte 0: Magic byte (0x00)
        - Bytes 1-4: Schema ID (big-endian 4-byte integer)
        - Bytes 5+: Avro serialized data
        """
        # Serialize message to Avro
        output = BytesIO()
        schemaless_writer(output, schema, message)
        avro_bytes = output.getvalue()
        
        # Prepend Confluent wire format header
        # Magic byte (0x00) + Schema ID (4 bytes, big-endian)
        header = struct.pack('>bI', 0, schema_id)
        
        return header + avro_bytes
    
    async def publish_batch(
        self,
        messages: list[Tuple[str, Dict[str, Any], str]],
        trace_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Publish a batch of messages
        
        Args:
            messages: List of (metric_name, message, user_id) tuples
            trace_id: OpenTelemetry trace ID
            
        Returns:
            tuple: (success_count, failure_count)
        """
        with tracer.start_as_current_span("kafka_publish_batch") as span:
            span.set_attribute("batch.size", len(messages))
            
            success_count = 0
            failure_count = 0
            
            tasks = []
            for metric_name, message, user_id in messages:
                task = self.publish_metric(
                    metric_name=metric_name,
                    message=message,
                    user_id=user_id,
                    trace_id=trace_id
                )
                logger.info(f"Metric: {metric_name} published for user {user_id}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failure_count += 1
                    logger.error(f"Batch publish error: {result}")
                elif result:
                    success_count += 1
                else:
                    failure_count += 1
            
            span.set_attribute("batch.success_count", success_count)
            span.set_attribute("batch.failure_count", failure_count)
            
            logger.info(f"Batch publish complete: {success_count} success, {failure_count} failed")
            return success_count, failure_count


# Global producer instance
kafka_producer = KafkaProducerService()

# Made with Bob
