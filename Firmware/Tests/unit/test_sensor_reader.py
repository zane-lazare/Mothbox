"""
Unit tests for Sensor Reader Library (Issue #230).

Tests stateless sensor reading functions with comprehensive mocking for CI/CD.
Covers: dataclasses, constants, light sensor, temperature sensor, preconditions.

Test structure:
- TestSensorReading (3 tests)
- TestConstants (2 tests)
- TestReadLightSensor (5 tests)
- TestReadTemperatureSensor (5 tests)
- TestCheckPrecondition (7 tests)
- TestGetEnvironmentalReadings (2 tests)
- TestGetSensorReading (2 tests)
- TestResetI2CAvailability (1 test)

Total: 27 tests (exceeds 20+ requirement)
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from webui.backend.lib.sensor_reader import (
    SENSOR_COMPARISONS,
    SENSOR_TYPES,
    SensorReading,
    check_precondition,
    get_environmental_readings,
    get_sensor_reading,
    read_light_sensor,
    read_temperature_sensor,
    reset_i2c_availability,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_i2c_state():
    """Reset I2C availability state before each test."""
    reset_i2c_availability()
    yield
    reset_i2c_availability()


# =============================================================================
# TEST SENSOR READING DATACLASS
# =============================================================================


class TestSensorReading:
    """Tests for SensorReading dataclass."""

    def test_sensor_reading_creation(self):
        """Test creating a SensorReading with all fields."""
        now = datetime.now()
        reading = SensorReading(
            sensor_type="light",
            value=500.0,
            timestamp=now,
            unit="lux",
        )

        assert reading.sensor_type == "light"
        assert reading.value == 500.0
        assert reading.timestamp == now
        assert reading.unit == "lux"

    def test_sensor_reading_temperature(self):
        """Test creating a temperature SensorReading."""
        now = datetime.now()
        reading = SensorReading(
            sensor_type="temperature",
            value=22.5,
            timestamp=now,
            unit="celsius",
        )

        assert reading.sensor_type == "temperature"
        assert reading.value == 22.5
        assert reading.unit == "celsius"

    def test_sensor_reading_all_sensor_types(self):
        """Test creating readings for all sensor types."""
        units = {"light": "lux", "temperature": "celsius"}
        for sensor_type in SENSOR_TYPES:
            reading = SensorReading(
                sensor_type=sensor_type,
                value=100.0,
                timestamp=datetime.now(),
                unit=units[sensor_type],
            )
            assert reading.sensor_type == sensor_type


# =============================================================================
# TEST CONSTANTS
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_sensor_types_defined(self):
        """Test that only light and temperature sensors are defined (no motion)."""
        assert "light" in SENSOR_TYPES
        assert "temperature" in SENSOR_TYPES
        assert "motion" not in SENSOR_TYPES  # Explicitly no motion
        assert len(SENSOR_TYPES) == 2

    def test_sensor_comparisons_defined(self):
        """Test that all comparison operators are defined."""
        assert "gt" in SENSOR_COMPARISONS
        assert "lt" in SENSOR_COMPARISONS
        assert "eq" in SENSOR_COMPARISONS
        assert "gte" in SENSOR_COMPARISONS
        assert "lte" in SENSOR_COMPARISONS
        assert len(SENSOR_COMPARISONS) == 5


# =============================================================================
# TEST READ LIGHT SENSOR
# =============================================================================


class TestReadLightSensor:
    """Tests for read_light_sensor function."""

    def test_read_light_sensor_disabled(self, mock_sensor_hardware):
        """Test reading light sensor when disabled returns None."""
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = False

        result = read_light_sensor()

        assert result is None

    def test_read_light_sensor_bh1750(self, mock_sensor_hardware):
        """Test reading BH1750 light sensor returns lux value."""
        # MockSMBus returns [0x00, 0x64] by default = 100 raw = ~83.3 lux
        result = read_light_sensor()

        assert result is not None
        # (0x00 << 8 | 0x64) / 1.2 = 100 / 1.2 ≈ 83.33
        assert 83.0 <= result <= 84.0

    def test_read_light_sensor_ltr303(self, mock_sensor_hardware):
        """Test reading LTR303 light sensor returns lux value."""
        mock_sensor_hardware["hw_config"]["light_sensor_type"] = "LTR303"
        # MockSMBus read_byte_data returns 0x64 = 100, so ch1 = (100 << 8) | 100 = 25700
        # lux = 25700 * 0.5 = 12850
        mock_sensor_hardware["smbus"].read_byte_data = MagicMock(return_value=100)

        result = read_light_sensor()

        assert result is not None
        assert result == 12850.0  # ch1 * 0.5

    def test_read_light_sensor_unknown_type(self, mock_sensor_hardware):
        """Test reading unknown light sensor type returns None."""
        mock_sensor_hardware["hw_config"]["light_sensor_type"] = "UNKNOWN"

        result = read_light_sensor()

        assert result is None

    def test_read_light_sensor_i2c_unavailable(self, mock_sensor_hardware, monkeypatch):
        """Test reading light sensor when I2C unavailable returns None."""
        # Remove smbus2 from sys.modules to simulate unavailability
        import sys

        if "smbus2" in sys.modules:
            del sys.modules["smbus2"]

        # Patch the import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "smbus2":
                raise ImportError("No module named 'smbus2'")
            return original_import(name, *args, **kwargs)

        import builtins

        original_import = builtins.__import__
        monkeypatch.setattr(builtins, "__import__", mock_import)

        reset_i2c_availability()
        result = read_light_sensor()

        assert result is None


# =============================================================================
# TEST READ TEMPERATURE SENSOR
# =============================================================================


class TestReadTemperatureSensor:
    """Tests for read_temperature_sensor function."""

    def test_read_temperature_sensor_disabled(self, mock_sensor_hardware):
        """Test reading temperature sensor when disabled returns None."""
        mock_sensor_hardware["hw_config"]["temperature_sensor_enabled"] = False

        result = read_temperature_sensor()

        assert result is None

    def test_read_temperature_sensor_tmp102(self, mock_sensor_hardware):
        """Test reading TMP102 temperature sensor returns celsius."""
        # Configure mock to return 25°C reading
        # TMP102: raw = (data[0] << 4) | (data[1] >> 4), celsius = raw * 0.0625
        # For 25°C: raw = 400, so data[0] = 0x19, data[1] = 0x00
        mock_sensor_hardware["smbus"].read_data = [0x19, 0x00]

        result = read_temperature_sensor()

        assert result is not None
        # (0x19 << 4) | (0x00 >> 4) = 0x190 = 400, 400 * 0.0625 = 25.0
        assert result == 25.0

    def test_read_temperature_sensor_mcp9808(self, mock_sensor_hardware):
        """Test reading MCP9808 temperature sensor returns celsius."""
        mock_sensor_hardware["hw_config"]["temperature_sensor_type"] = "MCP9808"
        # MCP9808: raw = (data[0] << 8) | data[1], celsius = raw / 16.0
        # For 25°C: raw = 400, so data = [0x01, 0x90]
        mock_sensor_hardware["smbus"].read_data = [0x01, 0x90]

        result = read_temperature_sensor()

        assert result is not None
        # (0x01 << 8 | 0x90) & 0x1FFF = 400, 400 / 16.0 = 25.0
        assert result == 25.0

    def test_read_temperature_sensor_unknown_type(self, mock_sensor_hardware):
        """Test reading unknown temperature sensor type returns None."""
        mock_sensor_hardware["hw_config"]["temperature_sensor_type"] = "UNKNOWN"

        result = read_temperature_sensor()

        assert result is None

    def test_read_temperature_sensor_negative(self, mock_sensor_hardware):
        """Test reading negative temperature from TMP102."""
        # TMP102 negative: raw > 2047, celsius = (raw - 4096) * 0.0625
        # For -10°C: raw = 4096 - 160 = 3936, so data[0] = 0xF6, data[1] = 0x00
        mock_sensor_hardware["smbus"].read_data = [0xF6, 0x00]

        result = read_temperature_sensor()

        assert result is not None
        # (0xF6 << 4) | 0 = 0xF60 = 3936, 3936 > 2047, so (3936 - 4096) * 0.0625 = -10.0
        assert result == -10.0


# =============================================================================
# TEST CHECK PRECONDITION
# =============================================================================


class TestCheckPrecondition:
    """Tests for check_precondition function."""

    def test_check_precondition_gt(self, mock_sensor_hardware):
        """Test greater than comparison."""
        # MockSMBus returns ~83 lux
        assert check_precondition("light", 50, "gt") is True
        assert check_precondition("light", 100, "gt") is False

    def test_check_precondition_lt(self, mock_sensor_hardware):
        """Test less than comparison."""
        # MockSMBus returns ~83 lux
        assert check_precondition("light", 100, "lt") is True
        assert check_precondition("light", 50, "lt") is False

    def test_check_precondition_eq(self, mock_sensor_hardware):
        """Test equality comparison with tolerance."""
        # Configure for exact value test
        mock_sensor_hardware["smbus"].read_data = [0x00, 0x78]  # 120 raw = 100 lux
        reset_i2c_availability()

        assert check_precondition("light", 100.0, "eq") is True
        assert check_precondition("light", 50.0, "eq") is False

    def test_check_precondition_gte(self, mock_sensor_hardware):
        """Test greater than or equal comparison."""
        # ~83 lux
        assert check_precondition("light", 83, "gte") is True
        assert check_precondition("light", 100, "gte") is False

    def test_check_precondition_lte(self, mock_sensor_hardware):
        """Test less than or equal comparison."""
        # ~83 lux
        assert check_precondition("light", 83.5, "lte") is True
        assert check_precondition("light", 50, "lte") is False

    def test_check_precondition_invalid_sensor_type(self, mock_sensor_hardware):
        """Test precondition with invalid sensor type returns False."""
        assert check_precondition("motion", 0.5, "gt") is False
        assert check_precondition("invalid", 100, "lt") is False

    def test_check_precondition_invalid_comparison(self, mock_sensor_hardware):
        """Test precondition with invalid comparison returns False."""
        assert check_precondition("light", 100, "invalid") is False
        assert check_precondition("light", 100, "ne") is False


# =============================================================================
# TEST GET ENVIRONMENTAL READINGS
# =============================================================================


class TestGetEnvironmentalReadings:
    """Tests for get_environmental_readings function."""

    def test_get_environmental_readings_all_enabled(self, mock_sensor_hardware):
        """Test getting readings when all sensors enabled."""
        # Configure temperature sensor data
        mock_sensor_hardware["smbus"].read_data = [0x19, 0x00]  # 25°C

        readings = get_environmental_readings()

        assert "ambient_light_lux" in readings
        assert "ambient_temperature_celsius" in readings
        assert "sensor_reading_timestamp" in readings
        assert readings["ambient_light_lux"] is not None
        assert readings["ambient_temperature_celsius"] is not None

    def test_get_environmental_readings_sensors_disabled(self, mock_sensor_hardware):
        """Test getting readings when sensors disabled returns None values."""
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = False
        mock_sensor_hardware["hw_config"]["temperature_sensor_enabled"] = False

        readings = get_environmental_readings()

        assert readings["ambient_light_lux"] is None
        assert readings["ambient_temperature_celsius"] is None
        assert readings["sensor_reading_timestamp"] is not None


# =============================================================================
# TEST GET SENSOR READING
# =============================================================================


class TestGetSensorReading:
    """Tests for get_sensor_reading function."""

    def test_get_sensor_reading_light(self, mock_sensor_hardware):
        """Test getting full SensorReading for light sensor."""
        reading = get_sensor_reading("light")

        assert reading is not None
        assert reading.sensor_type == "light"
        assert reading.unit == "lux"
        assert isinstance(reading.value, float)
        assert isinstance(reading.timestamp, datetime)

    def test_get_sensor_reading_invalid_type(self, mock_sensor_hardware):
        """Test getting SensorReading for invalid type returns None."""
        reading = get_sensor_reading("motion")

        assert reading is None


# =============================================================================
# TEST RESET I2C AVAILABILITY
# =============================================================================


class TestResetI2CAvailability:
    """Tests for reset_i2c_availability function."""

    def test_reset_i2c_availability(self, mock_sensor_hardware):
        """Test that reset_i2c_availability clears the flag."""
        # First read sets the flag
        read_light_sensor()

        # Reset should clear it (allows re-check)
        reset_i2c_availability()

        # This should work without error
        result = read_light_sensor()
        assert result is not None
