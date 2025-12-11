"""
Integration tests for CabinPython v2 daemon.

These tests verify the interaction between components.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from cabinpi.daemon import SensorDaemon
from cabinpi.core.models import SensorReading, Event


class TestDaemonLifecycle:
    """Test daemon initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_daemon_initialize_minimal_config(self):
        """Test daemon initializes with minimal configuration."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False,
                "log_level": "INFO"
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {},
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 60
            }
        }

        daemon = SensorDaemon(config)

        # Should initialize without errors
        try:
            await daemon.initialize()
            # Cleanup
            await daemon.shutdown()
            success = True
        except Exception as e:
            success = False
            print(f"Initialization failed: {e}")

        assert success

    @pytest.mark.asyncio
    async def test_daemon_handles_reading(self):
        """Test daemon processes sensor readings."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)
        await daemon.initialize()

        # Simulate a sensor reading
        reading = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"value": 100}
        )

        # This should not raise an error
        daemon._handle_reading(reading)

        await daemon.shutdown()

    @pytest.mark.asyncio
    async def test_daemon_handles_event(self):
        """Test daemon processes events."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)
        await daemon.initialize()

        # Simulate an event
        event = Event(
            event_type="test_event",
            severity="info",
            timestamp=datetime.now(),
            message="Test event"
        )

        # This should not raise an error
        daemon._handle_event(event)

        await daemon.shutdown()


class TestEventDetectorIntegration:
    """Test event detector integration with daemon."""

    @pytest.mark.asyncio
    async def test_event_detection_on_reading(self):
        """Test that events are detected from sensor readings."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {
                "high_value": {
                    "sensor": "test_sensor",
                    "field": "value",
                    "condition": "above",
                    "threshold": 50.0,
                    "severity": "warning",
                    "notify": False
                }
            }
        }

        events_detected = []

        def capture_event(event):
            events_detected.append(event)

        daemon = SensorDaemon(config)
        await daemon.initialize()

        # Replace event handler to capture events
        original_handler = daemon._handle_event
        daemon._handle_event = capture_event

        # Process a reading that triggers the rule
        reading = SensorReading(
            sensor_id="test_sensor",
            timestamp=datetime.now(),
            measurements={"value": 75.0}
        )

        daemon._handle_reading(reading)

        # Give event detector time to process
        await asyncio.sleep(0.1)

        # Restore original handler and cleanup
        daemon._handle_event = original_handler
        await daemon.shutdown()

        # Verify event was detected
        assert len(events_detected) > 0
        assert events_detected[0].event_type == "high_value"


class TestHealthMonitoring:
    """Test health monitoring integration."""

    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """Test health status aggregation."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)
        await daemon.initialize()

        health = await daemon.get_health_status()

        # Verify health status structure
        assert "daemon" in health
        assert "sensors" in health
        assert "outputs" in health
        assert "active_alerts" in health

        assert health["daemon"]["running"] is True
        assert isinstance(health["sensors"], list)
        assert isinstance(health["outputs"], list)
        assert isinstance(health["active_alerts"], list)

        await daemon.shutdown()


class TestSignalHandling:
    """Test signal handling integration."""

    @pytest.mark.asyncio
    async def test_signal_handler_setup(self):
        """Test signal handlers are installed."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)

        # Should not raise
        daemon.signal_handler.setup()

        # Cleanup
        daemon.signal_handler.cleanup()

    def test_shutdown_request(self):
        """Test shutdown request handling."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)
        daemon.running = True

        # Request shutdown
        daemon._request_shutdown()

        # Verify state
        assert daemon._shutdown_requested is True
        assert daemon.running is False

    def test_reload_request(self):
        """Test reload request handling."""
        config = {
            "daemon": {
                "polling_interval": 300,
                "enable_watchdog": False
            },
            "plugins": {
                "sensors": {},
                "outputs": {}
            },
            "events": {}
        }

        daemon = SensorDaemon(config)

        # Request reload
        daemon._request_reload()

        # Verify state
        assert daemon._reload_requested is True


class TestCircuitBreaker:
    """Test circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_in_sensor_manager(self):
        """Test that sensor manager uses circuit breakers."""
        from cabinpi.managers import SensorManager
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        config = {
            "daemon": {
                "polling_interval": 300
            },
            "plugins": {
                "sensors": {}
            },
            "circuit_breaker": {
                "failure_threshold": 3,
                "recovery_timeout": 10
            }
        }

        scheduler = AsyncIOScheduler()
        manager = SensorManager(
            scheduler=scheduler,
            config=config
        )

        # Should initialize without errors
        await manager.initialize()

        # Verify circuit breakers are created
        assert hasattr(manager, 'circuit_breakers')
        assert isinstance(manager.circuit_breakers, dict)

        await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
