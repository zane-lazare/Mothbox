"""
Unit tests for Sensor Monitor Library (Issue #230).

Tests sensor monitoring with comprehensive mocking for CI/CD compatibility.
Covers: dataclasses, initialization, registration, threshold, cooldown, monitor loop.

Test structure:
- TestSensorReading (3 tests)
- TestSensorTriggerConfig (3 tests)
- TestSensorMonitorInit (4 tests)
- TestRegisterTrigger (5 tests)
- TestCheckTrigger (5 tests)
- TestDispatchTrigger (4 tests)
- TestMonitorLoop (3 tests)
- TestGetRecentReadings (2 tests)
- TestConstants (3 tests)

Total: 32 tests (exceeds 25+ requirement)
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from webui.backend.lib.sensor_monitor import (
    SENSOR_COMPARISONS,
    SENSOR_CONFIGS,
    SENSOR_TYPES,
    SensorMonitor,
    SensorReading,
    SensorTriggerConfig,
    get_sensor_monitor,
    reset_sensor_monitor,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sensor_monitor():
    """Create a fresh SensorMonitor instance for each test."""
    reset_sensor_monitor()
    monitor = SensorMonitor()
    yield monitor
    monitor.stop()


@pytest.fixture
def mock_callback():
    """Create a mock callback function for testing triggers."""
    return MagicMock()


@pytest.fixture
def sample_reading():
    """Create a sample SensorReading for testing."""
    return SensorReading(
        sensor_type="motion",
        value=1.0,
        timestamp=datetime.now(),
        triggered=False,
    )


@pytest.fixture
def sample_trigger_config(mock_callback):
    """Create a sample SensorTriggerConfig for testing."""
    return SensorTriggerConfig(
        sensor_type="motion",
        threshold=0.5,
        comparison="gt",
        cooldown_minutes=5,
        callback=mock_callback,
    )


# =============================================================================
# TEST SENSOR READING DATACLASS
# =============================================================================


class TestSensorReading:
    """Tests for SensorReading dataclass."""

    def test_sensor_reading_creation(self):
        """Test creating a SensorReading with all fields."""
        now = datetime.now()
        reading = SensorReading(
            sensor_type="motion",
            value=1.0,
            timestamp=now,
            triggered=True,
        )

        assert reading.sensor_type == "motion"
        assert reading.value == 1.0
        assert reading.timestamp == now
        assert reading.triggered is True

    def test_sensor_reading_default_triggered(self):
        """Test that triggered defaults to False."""
        reading = SensorReading(
            sensor_type="light",
            value=500.0,
            timestamp=datetime.now(),
        )

        assert reading.triggered is False

    def test_sensor_reading_all_sensor_types(self):
        """Test creating readings for all sensor types."""
        for sensor_type in SENSOR_TYPES:
            reading = SensorReading(
                sensor_type=sensor_type,
                value=100.0,
                timestamp=datetime.now(),
            )
            assert reading.sensor_type == sensor_type


# =============================================================================
# TEST SENSOR TRIGGER CONFIG DATACLASS
# =============================================================================


class TestSensorTriggerConfig:
    """Tests for SensorTriggerConfig dataclass."""

    def test_sensor_trigger_config_creation(self, mock_callback):
        """Test creating a SensorTriggerConfig with all fields."""
        config = SensorTriggerConfig(
            sensor_type="temperature",
            threshold=30.0,
            comparison="gte",
            cooldown_minutes=10,
            callback=mock_callback,
        )

        assert config.sensor_type == "temperature"
        assert config.threshold == 30.0
        assert config.comparison == "gte"
        assert config.cooldown_minutes == 10
        assert config.callback is mock_callback

    def test_sensor_trigger_config_callback_is_callable(self, mock_callback):
        """Test that callback is stored correctly."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=100.0,
            comparison="lt",
            cooldown_minutes=1,
            callback=mock_callback,
        )

        # Callback should be callable
        reading = SensorReading("light", 50.0, datetime.now())
        config.callback(reading)
        mock_callback.assert_called_once_with(reading)

    def test_sensor_trigger_config_all_comparisons(self, mock_callback):
        """Test that all comparison types are valid."""
        for comparison in SENSOR_COMPARISONS:
            config = SensorTriggerConfig(
                sensor_type="light",
                threshold=100.0,
                comparison=comparison,
                cooldown_minutes=5,
                callback=mock_callback,
            )
            assert config.comparison == comparison


# =============================================================================
# TEST SENSOR MONITOR INITIALIZATION
# =============================================================================


class TestSensorMonitorInit:
    """Tests for SensorMonitor initialization."""

    def test_sensor_monitor_init_defaults(self, sensor_monitor):
        """Test SensorMonitor initializes with correct defaults."""
        assert sensor_monitor.is_running() is False
        assert sensor_monitor.get_trigger_count() == 0
        assert sensor_monitor.get_recent_readings() == []

    def test_sensor_monitor_init_internal_state(self, sensor_monitor):
        """Test SensorMonitor internal state is properly initialized."""
        assert sensor_monitor._triggers == []
        assert sensor_monitor._last_trigger_times == {}
        assert sensor_monitor._running is False
        assert sensor_monitor._thread is None

    def test_get_sensor_monitor_singleton(self):
        """Test get_sensor_monitor returns same instance."""
        reset_sensor_monitor()
        monitor1 = get_sensor_monitor()
        monitor2 = get_sensor_monitor()

        assert monitor1 is monitor2
        reset_sensor_monitor()

    def test_reset_sensor_monitor_clears_singleton(self):
        """Test reset_sensor_monitor creates new instance."""
        reset_sensor_monitor()
        monitor1 = get_sensor_monitor()
        reset_sensor_monitor()
        monitor2 = get_sensor_monitor()

        assert monitor1 is not monitor2


# =============================================================================
# TEST REGISTER TRIGGER
# =============================================================================


class TestRegisterTrigger:
    """Tests for trigger registration."""

    def test_register_trigger_success(self, sensor_monitor, sample_trigger_config):
        """Test registering a valid trigger."""
        sensor_monitor.register_trigger(sample_trigger_config)

        assert sensor_monitor.get_trigger_count() == 1

    def test_register_multiple_triggers(self, sensor_monitor, mock_callback):
        """Test registering multiple triggers."""
        for sensor_type in SENSOR_TYPES:
            config = SensorTriggerConfig(
                sensor_type=sensor_type,
                threshold=50.0,
                comparison="gt",
                cooldown_minutes=5,
                callback=mock_callback,
            )
            sensor_monitor.register_trigger(config)

        assert sensor_monitor.get_trigger_count() == 3

    def test_register_invalid_sensor_type(self, sensor_monitor, mock_callback):
        """Test registering with invalid sensor type logs warning."""
        config = SensorTriggerConfig(
            sensor_type="invalid_type",
            threshold=50.0,
            comparison="gt",
            cooldown_minutes=5,
            callback=mock_callback,
        )

        sensor_monitor.register_trigger(config)

        # Should not add invalid trigger
        assert sensor_monitor.get_trigger_count() == 0

    def test_unregister_trigger(self, sensor_monitor, mock_callback):
        """Test unregistering a trigger by sensor type."""
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=5,
            callback=mock_callback,
        )
        sensor_monitor.register_trigger(config)
        assert sensor_monitor.get_trigger_count() == 1

        sensor_monitor.unregister_trigger("motion")
        assert sensor_monitor.get_trigger_count() == 0

    def test_register_invalid_comparison(self, sensor_monitor, mock_callback):
        """Test registering with invalid comparison logs warning."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=50.0,
            comparison="invalid",  # Not in SENSOR_COMPARISONS
            cooldown_minutes=5,
            callback=mock_callback,
        )

        sensor_monitor.register_trigger(config)

        # Should not add invalid comparison trigger
        assert sensor_monitor.get_trigger_count() == 0


# =============================================================================
# TEST CHECK TRIGGER
# =============================================================================


class TestCheckTrigger:
    """Tests for threshold checking logic."""

    def test_check_trigger_gt(self, sensor_monitor, mock_callback):
        """Test greater than comparison."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=100.0,
            comparison="gt",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        reading_above = SensorReading("light", 150.0, datetime.now())
        reading_at = SensorReading("light", 100.0, datetime.now())
        reading_below = SensorReading("light", 50.0, datetime.now())

        assert sensor_monitor._check_trigger(config, reading_above) is True
        assert sensor_monitor._check_trigger(config, reading_at) is False
        assert sensor_monitor._check_trigger(config, reading_below) is False

    def test_check_trigger_lt(self, sensor_monitor, mock_callback):
        """Test less than comparison."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=100.0,
            comparison="lt",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        reading_above = SensorReading("light", 150.0, datetime.now())
        reading_at = SensorReading("light", 100.0, datetime.now())
        reading_below = SensorReading("light", 50.0, datetime.now())

        assert sensor_monitor._check_trigger(config, reading_above) is False
        assert sensor_monitor._check_trigger(config, reading_at) is False
        assert sensor_monitor._check_trigger(config, reading_below) is True

    def test_check_trigger_eq(self, sensor_monitor, mock_callback):
        """Test equality comparison (with tolerance)."""
        config = SensorTriggerConfig(
            sensor_type="temperature",
            threshold=25.0,
            comparison="eq",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        reading_equal = SensorReading("temperature", 25.005, datetime.now())
        reading_not_equal = SensorReading("temperature", 25.02, datetime.now())

        assert sensor_monitor._check_trigger(config, reading_equal) is True
        assert sensor_monitor._check_trigger(config, reading_not_equal) is False

    def test_check_trigger_gte(self, sensor_monitor, mock_callback):
        """Test greater than or equal comparison."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=100.0,
            comparison="gte",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        reading_above = SensorReading("light", 150.0, datetime.now())
        reading_at = SensorReading("light", 100.0, datetime.now())
        reading_below = SensorReading("light", 50.0, datetime.now())

        assert sensor_monitor._check_trigger(config, reading_above) is True
        assert sensor_monitor._check_trigger(config, reading_at) is True
        assert sensor_monitor._check_trigger(config, reading_below) is False

    def test_check_trigger_lte(self, sensor_monitor, mock_callback):
        """Test less than or equal comparison."""
        config = SensorTriggerConfig(
            sensor_type="light",
            threshold=100.0,
            comparison="lte",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        reading_above = SensorReading("light", 150.0, datetime.now())
        reading_at = SensorReading("light", 100.0, datetime.now())
        reading_below = SensorReading("light", 50.0, datetime.now())

        assert sensor_monitor._check_trigger(config, reading_above) is False
        assert sensor_monitor._check_trigger(config, reading_at) is True
        assert sensor_monitor._check_trigger(config, reading_below) is True


# =============================================================================
# TEST DISPATCH TRIGGER
# =============================================================================


class TestDispatchTrigger:
    """Tests for trigger dispatch with cooldown."""

    def test_dispatch_trigger_calls_callback(self, sensor_monitor, mock_callback):
        """Test that dispatch calls the callback with reading."""
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=0,
            callback=mock_callback,
        )
        reading = SensorReading("motion", 1.0, datetime.now())

        sensor_monitor._dispatch_trigger(config, reading)

        mock_callback.assert_called_once()
        call_arg = mock_callback.call_args[0][0]
        assert call_arg.sensor_type == "motion"
        assert call_arg.value == 1.0
        assert call_arg.triggered is True

    def test_dispatch_trigger_respects_cooldown(self, sensor_monitor, mock_callback):
        """Test that dispatch respects cooldown period."""
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=5,  # 5 minute cooldown
            callback=mock_callback,
        )
        reading = SensorReading("motion", 1.0, datetime.now())

        # First dispatch should succeed
        sensor_monitor._dispatch_trigger(config, reading)
        assert mock_callback.call_count == 1

        # Second dispatch immediately should be blocked by cooldown
        sensor_monitor._dispatch_trigger(config, reading)
        assert mock_callback.call_count == 1  # Still 1

    def test_dispatch_trigger_allows_after_cooldown(self, sensor_monitor, mock_callback):
        """Test that dispatch allows after cooldown expires."""
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=0,  # No cooldown
            callback=mock_callback,
        )
        reading = SensorReading("motion", 1.0, datetime.now())

        # Both dispatches should succeed with no cooldown
        sensor_monitor._dispatch_trigger(config, reading)
        sensor_monitor._dispatch_trigger(config, reading)

        assert mock_callback.call_count == 2

    def test_dispatch_trigger_handles_callback_exception(
        self, sensor_monitor, mock_callback
    ):
        """Test that dispatch handles callback exceptions gracefully."""
        mock_callback.side_effect = Exception("Callback error")
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=0,
            callback=mock_callback,
        )
        reading = SensorReading("motion", 1.0, datetime.now())

        # Should not raise, just log error
        sensor_monitor._dispatch_trigger(config, reading)

        mock_callback.assert_called_once()


# =============================================================================
# TEST MONITOR LOOP
# =============================================================================


class TestMonitorLoop:
    """Tests for the background monitoring loop."""

    def test_start_creates_thread(self, sensor_monitor):
        """Test that start creates a background thread."""
        assert sensor_monitor._thread is None

        sensor_monitor.start()

        assert sensor_monitor._thread is not None
        assert sensor_monitor._thread.is_alive()
        assert sensor_monitor.is_running() is True

    def test_stop_stops_thread(self, sensor_monitor):
        """Test that stop terminates the background thread."""
        sensor_monitor.start()
        assert sensor_monitor.is_running() is True

        sensor_monitor.stop()

        assert sensor_monitor.is_running() is False
        # Thread should be cleaned up
        assert sensor_monitor._thread is None

    def test_start_is_idempotent(self, sensor_monitor):
        """Test that calling start multiple times is safe."""
        sensor_monitor.start()
        thread1 = sensor_monitor._thread

        sensor_monitor.start()  # Second call
        thread2 = sensor_monitor._thread

        # Should be same thread
        assert thread1 is thread2


# =============================================================================
# TEST GET RECENT READINGS
# =============================================================================


class TestGetRecentReadings:
    """Tests for retrieving recent readings."""

    def test_get_recent_readings_empty(self, sensor_monitor):
        """Test getting readings when none exist."""
        readings = sensor_monitor.get_recent_readings()
        assert readings == []

    def test_get_recent_readings_with_limit(self, sensor_monitor, mock_callback):
        """Test getting readings with limit."""
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=0,
            callback=mock_callback,
        )

        # Add multiple readings via dispatch
        for _ in range(5):
            reading = SensorReading("motion", 1.0, datetime.now())
            sensor_monitor._dispatch_trigger(config, reading)

        # Get only 3
        readings = sensor_monitor.get_recent_readings(limit=3)
        assert len(readings) == 3


# =============================================================================
# TEST CONSTANTS AND CONFIGURATION
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_sensor_types_defined(self):
        """Test that all sensor types are defined."""
        assert "motion" in SENSOR_TYPES
        assert "light" in SENSOR_TYPES
        assert "temperature" in SENSOR_TYPES

    def test_sensor_comparisons_defined(self):
        """Test that all comparison operators are defined."""
        assert "gt" in SENSOR_COMPARISONS
        assert "lt" in SENSOR_COMPARISONS
        assert "eq" in SENSOR_COMPARISONS
        assert "gte" in SENSOR_COMPARISONS
        assert "lte" in SENSOR_COMPARISONS

    def test_sensor_configs_defined(self):
        """Test that sensor configs have expected structure."""
        assert "motion" in SENSOR_CONFIGS
        assert "light" in SENSOR_CONFIGS
        assert "temperature" in SENSOR_CONFIGS

        assert SENSOR_CONFIGS["motion"]["gpio_mode"] == "digital"
        assert SENSOR_CONFIGS["light"]["gpio_mode"] == "analog"
        assert SENSOR_CONFIGS["temperature"]["gpio_mode"] == "analog"
