"""
Unit tests for event detection system.
"""

import pytest
from datetime import datetime
from cabinpi.core.event_detector import EventDetector, EventRule, RuleCondition
from cabinpi.core.models import SensorReading, Event


class TestEventRule:
    """Test EventRule class."""

    def test_rule_below_threshold_triggers(self):
        """Test that rule triggers when value goes below threshold."""
        rule = EventRule("test_low", {
            "sensor": "test_sensor",
            "field": "voltage",
            "condition": "below",
            "threshold": 12.0,
            "severity": "warning",
            "notify": True
        })

        reading = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"voltage": 11.5}
        )

        event = rule.evaluate(reading)
        assert event is not None
        assert event.event_type == "test_low"
        assert event.severity == "warning"
        assert event.notify is True
        assert "below threshold" in event.message

    def test_rule_above_threshold_triggers(self):
        """Test that rule triggers when value goes above threshold."""
        rule = EventRule("test_high", {
            "sensor": "test_sensor",
            "field": "temperature",
            "condition": "above",
            "threshold": 100.0,
            "severity": "critical"
        })

        reading = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"temperature": 105.0}
        )

        event = rule.evaluate(reading)
        assert event is not None
        assert event.event_type == "test_high"
        assert "above threshold" in event.message

    def test_rule_changed_condition(self):
        """Test state change detection."""
        rule = EventRule("state_change", {
            "sensor": "test_sensor",
            "field": "mode",
            "condition": "changed",
            "severity": "info"
        })

        # First reading - no event (no previous value)
        reading1 = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"mode": "idle"}
        )
        event1 = rule.evaluate(reading1)
        assert event1 is None

        # Second reading - same value, no event
        reading2 = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"mode": "idle"}
        )
        event2 = rule.evaluate(reading2)
        assert event2 is None

        # Third reading - changed value, triggers event
        reading3 = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"mode": "active"}
        )
        event3 = rule.evaluate(reading3)
        assert event3 is not None
        assert "changed to active" in event3.message

    def test_rule_recovery_threshold(self):
        """Test recovery with hysteresis."""
        rule = EventRule("battery_low", {
            "sensor": "battery",
            "field": "voltage",
            "condition": "below",
            "threshold": 12.0,
            "recovery_threshold": 12.5,
            "severity": "warning",
            "notify": True
        })

        # Trigger alert
        reading1 = SensorReading(
            sensor_id="battery",
            timestamp=datetime.now(),
            measurements={"voltage": 11.8}
        )
        event1 = rule.evaluate(reading1)
        assert event1 is not None
        assert rule.active is True

        # Still below recovery - no new event (cooldown)
        reading2 = SensorReading(
            sensor_id="battery",
            timestamp=datetime.now(),
            measurements={"voltage": 12.2}
        )
        event2 = rule.evaluate(reading2)
        assert event2 is None  # No event, but still active

        # Above recovery - recovery event
        reading3 = SensorReading(
            sensor_id="battery",
            timestamp=datetime.now(),
            measurements={"voltage": 12.6}
        )
        event3 = rule.evaluate(reading3)
        assert event3 is not None
        assert "recovered" in event3.event_type
        assert rule.active is False

    def test_rule_cooldown(self):
        """Test alert cooldown mechanism."""
        rule = EventRule("temp_high", {
            "sensor": "temp_sensor",
            "field": "temp",
            "condition": "above",
            "threshold": 80.0,
            "cooldown_minutes": 30,
            "severity": "warning"
        })

        # First alert
        reading1 = SensorReading(
            sensor_id="temp_sensor",
            timestamp=datetime.now(),
            measurements={"temp": 85.0}
        )
        event1 = rule.evaluate(reading1)
        assert event1 is not None

        # Second reading during cooldown - suppressed
        reading2 = SensorReading(
            sensor_id="temp_sensor",
            timestamp=datetime.now(),
            measurements={"temp": 90.0}
        )
        event2 = rule.evaluate(reading2)
        assert event2 is None  # Suppressed by cooldown

    def test_rule_ignores_other_sensors(self):
        """Test that rule only evaluates readings from its sensor."""
        rule = EventRule("sensor1_rule", {
            "sensor": "sensor1",
            "field": "value",
            "condition": "above",
            "threshold": 50.0,
            "severity": "info"
        })

        # Reading from different sensor
        reading = SensorReading(
            sensor_id="sensor2",
            timestamp=datetime.now(),
            measurements={"value": 100.0}
        )

        event = rule.evaluate(reading)
        assert event is None

    def test_rule_handles_missing_field(self):
        """Test that rule handles missing measurement field."""
        rule = EventRule("test_rule", {
            "sensor": "test_sensor",
            "field": "missing_field",
            "condition": "above",
            "threshold": 50.0,
            "severity": "info"
        })

        reading = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"other_field": 100.0}
        )

        event = rule.evaluate(reading)
        assert event is None


class TestEventDetector:
    """Test EventDetector class."""

    def test_detector_initialization(self):
        """Test detector loads rules from config."""
        config = {
            "events": {
                "rule1": {
                    "sensor": "sensor1",
                    "field": "value",
                    "condition": "above",
                    "threshold": 100.0,
                    "severity": "warning"
                },
                "rule2": {
                    "sensor": "sensor2",
                    "field": "temp",
                    "condition": "below",
                    "threshold": 0.0,
                    "severity": "critical"
                }
            }
        }

        detector = EventDetector(config)
        assert len(detector.rules) == 2
        assert "rule1" in detector.rules
        assert "rule2" in detector.rules

    def test_detector_processes_reading(self):
        """Test detector evaluates all rules against reading."""
        config = {
            "events": {
                "high_temp": {
                    "sensor": "temp_sensor",
                    "field": "temperature",
                    "condition": "above",
                    "threshold": 100.0,
                    "severity": "warning"
                }
            }
        }

        events_emitted = []

        def on_event(event):
            events_emitted.append(event)

        detector = EventDetector(config, on_event=on_event)

        reading = SensorReading(
            sensor_id="temp_sensor",
            timestamp=datetime.now(),
            measurements={"temperature": 105.0}
        )

        detected_events = detector.process_reading(reading)
        assert len(detected_events) == 1
        assert detected_events[0].event_type == "high_temp"
        assert len(events_emitted) == 1  # Callback invoked

    def test_detector_dependency_check(self):
        """Test that dependent rules only trigger when dependency is active."""
        config = {
            "events": {
                "alert": {
                    "sensor": "sensor1",
                    "field": "value",
                    "condition": "below",
                    "threshold": 10.0,
                    "severity": "warning"
                },
                "recovery": {
                    "sensor": "sensor1",
                    "field": "value",
                    "condition": "above",
                    "threshold": 15.0,
                    "depends_on": "alert",
                    "severity": "info"
                }
            }
        }

        detector = EventDetector(config)

        # Recovery should not trigger when dependency not active
        reading1 = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"value": 20.0}
        )
        events1 = detector.process_reading(reading1)
        assert len(events1) == 0  # No events

        # Trigger alert
        reading2 = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"value": 8.0}
        )
        events2 = detector.process_reading(reading2)
        assert len(events2) == 1
        assert events2[0].event_type == "alert"

        # Now recovery can trigger
        reading3 = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"value": 20.0}
        )
        events3 = detector.process_reading(reading3)
        assert len(events3) == 1
        assert events3[0].event_type == "recovery"

    def test_detector_log_only_flag(self):
        """Test that log_only events don't invoke callback."""
        config = {
            "events": {
                "state_change": {
                    "sensor": "sensor1",
                    "field": "state",
                    "condition": "changed",
                    "log_only": True,
                    "severity": "info"
                }
            }
        }

        events_emitted = []

        def on_event(event):
            events_emitted.append(event)

        detector = EventDetector(config, on_event=on_event)

        # First reading
        reading1 = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"state": "idle"}
        )
        detector.process_reading(reading1)

        # State change
        reading2 = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"state": "active"}
        )
        events = detector.process_reading(reading2)

        assert len(events) == 1  # Event detected
        assert len(events_emitted) == 0  # But callback not invoked (log_only)

    def test_get_active_alerts(self):
        """Test getting list of active alerts."""
        config = {
            "events": {
                "alert1": {
                    "sensor": "sensor1",
                    "field": "value",
                    "condition": "below",
                    "threshold": 10.0,
                    "recovery_threshold": 15.0,
                    "severity": "warning"
                }
            }
        }

        detector = EventDetector(config)

        # No active alerts initially
        assert len(detector.get_active_alerts()) == 0

        # Trigger alert
        reading = SensorReading(
            sensor_id="sensor1",
            timestamp=datetime.now(),
            measurements={"value": 5.0}
        )
        detector.process_reading(reading)

        # Now we have one active alert
        active = detector.get_active_alerts()
        assert len(active) == 1
        assert active[0]["rule_id"] == "alert1"
        assert active[0]["sensor_id"] == "sensor1"
