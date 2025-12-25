"""
Integration tests for Sensor Reader Library (Issue #230).

These tests require real I2C hardware and are marked with @pytest.mark.hardware.
They will be skipped in CI/CD environments without hardware access.

Test structure:
- TestSensorReaderHardware: Real I2C sensor validation

To run these tests on a Raspberry Pi with sensors connected:
    pytest Tests/integration/test_sensor_reader_hardware.py -v -m hardware
"""

import pytest


@pytest.mark.hardware
class TestSensorReaderHardware:
    """Integration tests requiring real I2C sensors."""

    def test_light_sensor_returns_valid_reading_or_none(self):
        """
        Integration test: Read from real light sensor.

        On hardware with sensor: Returns float >= 0 (lux value)
        On hardware without sensor: Returns None (graceful failure)
        In CI (no I2C): Returns None (smbus2 unavailable)
        """
        from webui.backend.lib.sensor_reader import read_light_sensor

        result = read_light_sensor()

        # Either None (no hardware) or valid lux reading
        assert result is None or (isinstance(result, float) and result >= 0)

    def test_temperature_sensor_returns_valid_reading_or_none(self):
        """
        Integration test: Read from real temperature sensor.

        On hardware with sensor: Returns float in reasonable range (-40 to 85°C)
        On hardware without sensor: Returns None (graceful failure)
        In CI (no I2C): Returns None (smbus2 unavailable)
        """
        from webui.backend.lib.sensor_reader import read_temperature_sensor

        result = read_temperature_sensor()

        # Either None (no hardware) or valid temperature reading
        # TMP102/MCP9808 range: -40°C to +125°C
        assert result is None or (isinstance(result, float) and -50 <= result <= 130)

    def test_environmental_readings_returns_dict(self):
        """
        Integration test: Get all environmental readings.

        Always returns a dict with expected keys, even if sensors unavailable.
        """
        from webui.backend.lib.sensor_reader import get_environmental_readings

        readings = get_environmental_readings()

        assert isinstance(readings, dict)
        assert "ambient_light_lux" in readings
        assert "ambient_temperature_celsius" in readings
        assert "sensor_reading_timestamp" in readings

        # Values are either None or valid readings
        if readings["ambient_light_lux"] is not None:
            assert isinstance(readings["ambient_light_lux"], float)
            assert readings["ambient_light_lux"] >= 0

        if readings["ambient_temperature_celsius"] is not None:
            assert isinstance(readings["ambient_temperature_celsius"], float)
            assert -50 <= readings["ambient_temperature_celsius"] <= 130

    def test_precondition_check_handles_unavailable_sensor(self):
        """
        Integration test: Precondition check with unavailable sensor.

        Should return False (not crash) when sensor unavailable.
        """
        from webui.backend.lib.sensor_reader import check_precondition

        # This should not raise, even without hardware
        result = check_precondition("light", 100, "lt")

        # Either True/False based on reading, or False if unavailable
        assert isinstance(result, bool)
