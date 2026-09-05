"""
Utility to map metric names to Kafka topics
"""

from typing import Dict, List


# Metric name prefix to topic mapping
METRIC_TO_TOPIC: Dict[str, str] = {
    "health.activity": "health.metrics.activity",
    "health.heartrate": "health.metrics.heartrate",
    "health.sleep": "health.metrics.sleep",
    "health.bloodpressure": "health.metrics.bloodpressure",
    "health.glucose": "health.metrics.glucose",
    "health.spo2": "health.metrics.spo2",
    "health.workout": "health.metrics.workout",
    "health.nutrition": "health.metrics.nutrition",
    "health.custom": "health.metrics.custom",
}


def get_topic_for_metric(metric_name: str) -> str:
    """
    Get Kafka topic for a metric name
    
    Args:
        metric_name: Metric name (e.g., health.activity.steps)
        
    Returns:
        str: Kafka topic name
        
    Raises:
        ValueError: If metric name doesn't match any known pattern
    """
    # Extract category from metric name (e.g., health.activity from health.activity.steps)
    parts = metric_name.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid metric name format: {metric_name}")
    
    category = f"{parts[0]}.{parts[1]}"
    
    topic = METRIC_TO_TOPIC.get(category)
    if not topic:
        raise ValueError(f"Unknown metric category: {category}")
    
    return topic


def get_all_topics() -> List[str]:
    """Get list of all Kafka topics"""
    return list(set(METRIC_TO_TOPIC.values()))

# Made with Bob
