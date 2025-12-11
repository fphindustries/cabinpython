"""
Event detection and rule engine for CabinPython v2.

This module detects events based on sensor readings and configured rules.
Supports threshold-based detection, state change tracking, and alert cooldowns.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from cabinpi.core.models import SensorReading, Event

logger = logging.getLogger(__name__)


class RuleCondition(Enum):
    """Event rule condition types."""
    ABOVE = "above"
    BELOW = "below"
    EQUALS = "equals"
    CHANGED = "changed"


class EventRule:
    """
    Event detection rule.

    Defines conditions for generating events from sensor data.
    """

    def __init__(self, rule_id: str, config: Dict[str, Any]) -> None:
        """
        Initialize an event rule.

        Args:
            rule_id: Unique rule identifier
            config: Rule configuration dict with:
                - sensor: Sensor ID to monitor
                - field: Measurement field to check
                - condition: Condition type (above, below, equals, changed)
                - threshold: Threshold value (for above/below/equals)
                - recovery_threshold: Optional threshold for recovery
                - cooldown_minutes: Minutes between repeated alerts
                - severity: Event severity (info, warning, error, critical)
                - notify: Whether to send notifications (default: false)
                - log_only: Only log, don't store event (default: false)
                - depends_on: Optional rule ID that must be active
                - message: Optional custom message template
        """
        self.rule_id = rule_id
        self.sensor_id = config.get("sensor", "")
        self.field = config.get("field", "")
        self.condition = RuleCondition(config.get("condition", "above"))
        self.threshold = config.get("threshold")
        self.recovery_threshold = config.get("recovery_threshold")
        self.cooldown_minutes = config.get("cooldown_minutes", 0)
        self.severity = config.get("severity", "info")
        self.notify = config.get("notify", False)
        self.log_only = config.get("log_only", False)
        self.depends_on = config.get("depends_on")
        self.message_template = config.get("message", "")

        # Runtime state
        self.active = False
        self.last_alert_time: Optional[datetime] = None
        self.last_value: Optional[Any] = None

    def evaluate(self, reading: SensorReading) -> Optional[Event]:
        """
        Evaluate rule against a sensor reading.

        Args:
            reading: SensorReading to evaluate

        Returns:
            Event if rule triggered, None otherwise
        """
        # Check if this rule applies to this sensor
        if reading.sensor_id != self.sensor_id:
            return None

        # Get the field value
        value = reading.measurements.get(self.field)
        if value is None:
            return None

        # Evaluate condition
        triggered = False
        recovered = False

        if self.condition == RuleCondition.CHANGED:
            # State change detection
            if self.last_value is not None and value != self.last_value:
                triggered = True
            self.last_value = value

        elif self.condition == RuleCondition.ABOVE:
            if value > self.threshold:
                triggered = True
                if not self.active:
                    self.active = True
            elif self.recovery_threshold and value <= self.recovery_threshold:
                if self.active:
                    recovered = True
                    self.active = False

        elif self.condition == RuleCondition.BELOW:
            if value < self.threshold:
                triggered = True
                if not self.active:
                    self.active = True
            elif self.recovery_threshold and value >= self.recovery_threshold:
                if self.active:
                    recovered = True
                    self.active = False

        elif self.condition == RuleCondition.EQUALS:
            if value == self.threshold:
                triggered = True

        # Check if we should generate an event
        if recovered:
            # Always generate recovery events
            return self._create_event(
                event_type=f"{self.rule_id}_recovered",
                reading=reading,
                value=value,
                message=f"Condition recovered: {self.field} = {value}"
            )

        if triggered:
            # Check cooldown
            if self._is_in_cooldown():
                logger.debug(f"Rule {self.rule_id} in cooldown, suppressing alert")
                return None

            # Update last alert time
            self.last_alert_time = datetime.now()

            return self._create_event(
                event_type=self.rule_id,
                reading=reading,
                value=value,
                message=self._format_message(value)
            )

        return None

    def _is_in_cooldown(self) -> bool:
        """Check if rule is in cooldown period."""
        if self.cooldown_minutes == 0:
            return False

        if self.last_alert_time is None:
            return False

        cooldown_end = self.last_alert_time + timedelta(minutes=self.cooldown_minutes)
        return datetime.now() < cooldown_end

    def _format_message(self, value: Any) -> str:
        """Format event message with value."""
        if self.message_template:
            return self.message_template.format(value=value, field=self.field)

        # Default message
        if self.condition == RuleCondition.CHANGED:
            return f"{self.field} changed to {value}"
        elif self.condition == RuleCondition.ABOVE:
            return f"{self.field} ({value}) above threshold {self.threshold}"
        elif self.condition == RuleCondition.BELOW:
            return f"{self.field} ({value}) below threshold {self.threshold}"
        elif self.condition == RuleCondition.EQUALS:
            return f"{self.field} equals {value}"
        else:
            return f"{self.field} = {value}"

    def _create_event(
        self,
        event_type: str,
        reading: SensorReading,
        value: Any,
        message: str
    ) -> Event:
        """Create an Event from rule evaluation."""
        return Event(
            event_type=event_type,
            severity=self.severity,
            timestamp=reading.timestamp,
            sensor_id=reading.sensor_id,
            message=message,
            data={
                "rule_id": self.rule_id,
                "field": self.field,
                "value": value,
                "threshold": self.threshold,
                "condition": self.condition.value
            },
            notify=self.notify
        )


class EventDetector:
    """
    Event detection engine.

    Evaluates sensor readings against configured rules and generates events.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        on_event: Optional[Callable[[Event], None]] = None
    ) -> None:
        """
        Initialize the event detector.

        Args:
            config: Configuration dict with 'events' section
            on_event: Callback for generated events
        """
        self.on_event = on_event
        self.rules: Dict[str, EventRule] = {}
        self._state_file = Path.home() / ".cabinpython" / "event_state.json"
        self._load_rules(config)
        self._load_state()

    def _load_rules(self, config: Dict[str, Any]) -> None:
        """Load event rules from configuration."""
        events_config = config.get("events", {})

        for rule_id, rule_config in events_config.items():
            try:
                rule = EventRule(rule_id, rule_config)
                self.rules[rule_id] = rule
                logger.info(
                    f"Loaded event rule: {rule_id} "
                    f"({rule.sensor_id}.{rule.field} {rule.condition.value})"
                )
            except Exception as e:
                logger.error(f"Failed to load rule {rule_id}: {e}")

        logger.info(f"Event detector initialized with {len(self.rules)} rules")

    def _load_state(self) -> None:
        """Load persistent state from disk."""
        if not self._state_file.exists():
            return

        try:
            with open(self._state_file, 'r') as f:
                state = json.load(f)

            for rule_id, rule_state in state.items():
                if rule_id not in self.rules:
                    continue

                rule = self.rules[rule_id]
                rule.active = rule_state.get("active", False)
                rule.last_value = rule_state.get("last_value")

                last_alert_str = rule_state.get("last_alert_time")
                if last_alert_str:
                    rule.last_alert_time = datetime.fromisoformat(last_alert_str)

            logger.info(f"Loaded event detector state from {self._state_file}")

        except Exception as e:
            logger.warning(f"Failed to load event state: {e}")

    def _save_state(self) -> None:
        """Save persistent state to disk."""
        try:
            # Ensure directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {}
            for rule_id, rule in self.rules.items():
                state[rule_id] = {
                    "active": rule.active,
                    "last_value": rule.last_value,
                    "last_alert_time": (
                        rule.last_alert_time.isoformat()
                        if rule.last_alert_time else None
                    )
                }

            with open(self._state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save event state: {e}")

    def process_reading(self, reading: SensorReading) -> List[Event]:
        """
        Process a sensor reading and detect events.

        Args:
            reading: SensorReading to evaluate

        Returns:
            List of generated events
        """
        events = []

        for rule in self.rules.values():
            try:
                event = rule.evaluate(reading)
                if event:
                    # Check dependencies
                    if rule.depends_on:
                        dep_rule = self.rules.get(rule.depends_on)
                        if not dep_rule or not dep_rule.active:
                            logger.debug(
                                f"Rule {rule.rule_id} skipped: "
                                f"dependency {rule.depends_on} not active"
                            )
                            continue

                    events.append(event)

                    # Emit event
                    if self.on_event and not rule.log_only:
                        self.on_event(event)

                    logger.info(
                        f"Event detected: {event.event_type} ({event.severity}) - "
                        f"{event.message}"
                    )

            except Exception as e:
                logger.exception(f"Error evaluating rule {rule.rule_id}: {e}")

        # Save state after processing
        if events:
            self._save_state()

        return events

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active alerts.

        Returns:
            List of active alert information
        """
        active = []
        for rule in self.rules.values():
            if rule.active:
                active.append({
                    "rule_id": rule.rule_id,
                    "sensor_id": rule.sensor_id,
                    "field": rule.field,
                    "condition": rule.condition.value,
                    "threshold": rule.threshold,
                    "last_alert_time": (
                        rule.last_alert_time.isoformat()
                        if rule.last_alert_time else None
                    )
                })
        return active

    def clear_cooldowns(self) -> None:
        """Clear all cooldown timers (for testing/debugging)."""
        for rule in self.rules.values():
            rule.last_alert_time = None
        logger.info("Cleared all event cooldowns")
