"""
Core components for CabinPython v2 daemon.

This package contains core data models, protocols, and the event detection engine.
"""

from cabinpi.core.models import SensorReading, Event, HealthStatus, SensorType
from cabinpi.core.protocols import SensorPlugin, OutputPlugin
from cabinpi.core.event_detector import EventDetector, EventRule, RuleCondition

__all__ = [
    "SensorReading",
    "Event",
    "HealthStatus",
    "SensorType",
    "SensorPlugin",
    "OutputPlugin",
    "EventDetector",
    "EventRule",
    "RuleCondition",
]
