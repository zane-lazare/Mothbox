"""
Integration tests for Sensor Workflow (Issue #232).

Tests end-to-end sensor workflows including:
- Light sensor reading via I2C
- Temperature sensor reading via I2C
- Pre-condition evaluation (single and multiple)
- Environmental logging for photo metadata
- Graceful fallback when sensors unavailable
- Sensor service integration with scheduler

Run mocked tests: MOTHBOX_ENV=test pytest Tests/integration/test_sensor_workflow.py -v
Run hardware tests: pytest Tests/integration/test_sensor_workflow.py -v -m hardware

These tests are marked as @pytest.mark.integration.
Tests requiring real I2C hardware are marked with @pytest.mark.hardware.

Test structure (mocked - CI/CD compatible):
- TestLightSensorWorkflow (3 tests)
- TestTemperatureSensorWorkflow (3 tests)
- TestPreconditionEvaluationWorkflow (4 tests)
- TestSensorUnavailableWorkflow (3 tests)
- TestEnvironmentalLoggingWorkflow (3 tests)
- TestSensorServiceIntegration (2 tests)

Test structure (hardware - requires Raspberry Pi with I2C sensors):
- TestSensorWorkflowHardware (5 tests)

Total: 23 tests (18 mocked + 5 hardware)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from webui.backend.lib.sensor_reader import (
    get_environmental_readings,
    read_light_sensor,
    read_temperature_sensor,
    reset_i2c_availability,
)
from webui.backend.services.sensor_service import (
    REASON_PASSED,
    REASON_SENSOR_UNAVAILABLE,
    SensorPrecondition,
    SensorService,
)

# Mark all tests as integration tests
pytestmark = pytest.mark.integration

# =============================================================================
# TOLERANCE CONSTANTS
# =============================================================================
# These constants match COMPARISON_TOLERANCE from sensor_reader.py and provide
# consistent tolerance values across all sensor integration tests.

# Absolute tolerances for sensor readings (match sensor_reader.py)
LIGHT_SENSOR_TOLERANCE = 1.0  # ±1 lux
TEMPERATURE_SENSOR_TOLERANCE = 0.1  # ±0.1°C

# Percentage tolerance for readings where absolute value varies
# Used for calculations like: expected_value * (1 ± PERCENT_TOLERANCE)
PERCENT_TOLERANCE = 0.01  # ±1%

# LTR303 uses ratio-based calculation with higher variance due to
# channel ratio interpolation and gain/integration time compensation
LTR303_PERCENT_TOLERANCE = 0.10  # ±10%


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_sensor_state():
    """Reset sensor reader I2C state before each test."""
    reset_i2c_availability()
    yield
    reset_i2c_availability()


@pytest.fixture(autouse=True)
def reset_sensor_service_singleton():
    """Reset the singleton before each test."""
    import webui.backend.services as services_module

    services_module._sensor_service = None
    yield
    services_module._sensor_service = None


@pytest.fixture
def sensor_service():
    """Fresh SensorService instance for each test."""
    service = SensorService(max_history=100)
    yield service
    service.clear_history()
    service.reset_statistics()


@pytest.fixture
def mock_light_sensor_bh1750(mock_sensor_hardware):
    """
    Configure mock for BH1750 light sensor at specific lux value.

    BH1750 formula: lux = raw_value / 1.2

    Args:
        lux_value: Desired lux reading

    Returns:
        Configured mock_sensor_hardware dict
    """

    def _configure(lux_value: float):
        # BH1750: lux = raw / 1.2, so raw = lux * 1.2
        raw = int(lux_value * 1.2)
        high_byte = (raw >> 8) & 0xFF
        low_byte = raw & 0xFF
        mock_sensor_hardware["smbus"].read_data = [high_byte, low_byte]
        mock_sensor_hardware["hw_config"]["light_sensor_type"] = "BH1750"
        return mock_sensor_hardware

    return _configure


@pytest.fixture
def mock_light_sensor_ltr303(mock_sensor_hardware):
    """
    Configure mock for LTR303 light sensor with specific parameters.

    LTR303 uses ratio-based lux calculation from CH0/CH1 values.

    Args:
        ch1: Channel 1 raw value
        ch0: Channel 0 raw value
        gain: Gain setting (0-7)
        int_time: Integration time setting (0-7)

    Returns:
        Configured mock_sensor_hardware dict
    """

    def _configure(ch1: int, ch0: int, gain: int = 0, int_time: int = 0):
        # Register map for LTR303
        registers = {
            0x80: 0x01 | (gain << 2),  # Control reg (gain bits 2-4)
            0x85: (int_time << 3),  # Meas rate (int time bits 3-5)
            0x88: ch1 & 0xFF,  # CH1 low
            0x89: (ch1 >> 8) & 0xFF,  # CH1 high
            0x8A: ch0 & 0xFF,  # CH0 low
            0x8B: (ch0 >> 8) & 0xFF,  # CH0 high
        }
        mock_sensor_hardware["smbus"].read_byte_data = MagicMock(
            side_effect=lambda addr, reg: registers.get(reg, 0)
        )
        mock_sensor_hardware["hw_config"]["light_sensor_type"] = "LTR303"
        return mock_sensor_hardware

    return _configure


@pytest.fixture
def mock_temperature_sensor_tmp102(mock_sensor_hardware):
    """
    Configure mock for TMP102 temperature sensor at specific celsius value.

    TMP102 formula: celsius = raw_value * 0.0625 (12-bit two's complement)

    Args:
        celsius: Desired temperature reading

    Returns:
        Configured mock_sensor_hardware dict
    """

    def _configure(celsius: float):
        # TMP102: raw = celsius / 0.0625
        raw = int(celsius / 0.0625)
        if raw < 0:
            raw += 4096  # Two's complement for 12-bit
        # TMP102 format: MSB[7:0] = raw[11:4], LSB[7:4] = raw[3:0]
        msb = (raw >> 4) & 0xFF
        lsb = (raw << 4) & 0xF0
        mock_sensor_hardware["smbus"].read_data = [msb, lsb]
        mock_sensor_hardware["hw_config"]["temperature_sensor_type"] = "TMP102"
        return mock_sensor_hardware

    return _configure


@pytest.fixture
def mock_temperature_sensor_mcp9808(mock_sensor_hardware):
    """
    Configure mock for MCP9808 temperature sensor at specific celsius value.

    MCP9808 formula: celsius = raw_value * 0.0625 (13-bit with sign)

    Args:
        celsius: Desired temperature reading

    Returns:
        Configured mock_sensor_hardware dict
    """

    def _configure(celsius: float):
        # MCP9808: 13-bit data with sign bit
        if celsius >= 0:
            raw = int(celsius / 0.0625) & 0x0FFF
        else:
            raw = int(abs(celsius) / 0.0625) & 0x0FFF
            raw |= 0x1000  # Set sign bit for negative
        msb = (raw >> 8) & 0x1F
        lsb = raw & 0xFF
        mock_sensor_hardware["smbus"].read_data = [msb, lsb]
        mock_sensor_hardware["hw_config"]["temperature_sensor_type"] = "MCP9808"
        return mock_sensor_hardware

    return _configure


# =============================================================================
# TEST LIGHT SENSOR WORKFLOW
# =============================================================================


class TestLightSensorWorkflow:
    """Integration tests for light sensor I2C read workflows."""

    def test_bh1750_read_workflow_returns_lux(self, mock_light_sensor_bh1750):
        """BH1750 I2C read returns correct lux value from raw bytes."""
        # Setup: 100 lux (raw = 120 = 0x00, 0x78)
        mock_light_sensor_bh1750(100.0)

        # Execute
        result = read_light_sensor()

        # Verify lux calculation: 120 / 1.2 = 100
        assert result is not None
        expected_lux = 100.0
        assert expected_lux - LIGHT_SENSOR_TOLERANCE <= result <= expected_lux + LIGHT_SENSOR_TOLERANCE

    def test_ltr303_read_workflow_with_gain_compensation(
        self, mock_light_sensor_ltr303
    ):
        """LTR303 I2C read applies gain and integration time compensation."""
        # Setup: CH1=100, CH0=50 -> ratio = 0.5 (in [0.45, 0.64) range)
        # Formula: lux = (4.2785 * ch1 - 1.9548 * ch0) / gain_factor
        # With gain=0 (1x), int_time=0 (100ms): gain_factor = 1.0
        # lux = 4.2785*100 - 1.9548*50 = 427.85 - 97.74 = 330.11
        mock_light_sensor_ltr303(ch1=100, ch0=50, gain=0, int_time=0)

        # Execute
        result = read_light_sensor()

        # Verify ratio-based calculation
        # Expected: 4.2785*100 - 1.9548*50 = 330.11 lux
        assert result is not None
        expected_lux = 330.0
        tolerance = expected_lux * LTR303_PERCENT_TOLERANCE
        assert expected_lux - tolerance <= result <= expected_lux + tolerance

    def test_light_sensor_multiple_reads_consistent(self, mock_light_sensor_bh1750):
        """Multiple consecutive light sensor reads return consistent values."""
        expected_lux = 250.0
        mock_light_sensor_bh1750(expected_lux)

        # Execute multiple reads
        results = [read_light_sensor() for _ in range(5)]

        # All should be consistent within tolerance
        assert all(r is not None for r in results)
        # Use percentage tolerance for higher readings
        tolerance = expected_lux * PERCENT_TOLERANCE
        for result in results:
            assert expected_lux - tolerance <= result <= expected_lux + tolerance


# =============================================================================
# TEST TEMPERATURE SENSOR WORKFLOW
# =============================================================================


class TestTemperatureSensorWorkflow:
    """Integration tests for temperature sensor I2C read workflows."""

    def test_tmp102_read_workflow_returns_celsius(self, mock_temperature_sensor_tmp102):
        """TMP102 I2C read returns correct celsius value from raw bytes."""
        # Setup: 25.0C (raw = 400)
        expected_temp = 25.0
        mock_temperature_sensor_tmp102(expected_temp)

        # Execute
        result = read_temperature_sensor()

        # Verify: 400 * 0.0625 = 25.0
        assert result is not None
        assert expected_temp - TEMPERATURE_SENSOR_TOLERANCE <= result <= expected_temp + TEMPERATURE_SENSOR_TOLERANCE

    def test_mcp9808_read_workflow_returns_celsius(
        self, mock_temperature_sensor_mcp9808
    ):
        """MCP9808 I2C read returns correct celsius value from raw bytes."""
        # Setup: 30.0C
        expected_temp = 30.0
        mock_temperature_sensor_mcp9808(expected_temp)

        # Execute
        result = read_temperature_sensor()

        # Verify
        assert result is not None
        assert expected_temp - TEMPERATURE_SENSOR_TOLERANCE <= result <= expected_temp + TEMPERATURE_SENSOR_TOLERANCE

    def test_negative_temperature_workflow(self, mock_temperature_sensor_tmp102):
        """Temperature sensor handles negative temperatures via two's complement."""
        # Setup: -10.0C (two's complement)
        expected_temp = -10.0
        mock_temperature_sensor_tmp102(expected_temp)

        # Execute
        result = read_temperature_sensor()

        # Verify negative temperature
        assert result is not None
        assert expected_temp - TEMPERATURE_SENSOR_TOLERANCE <= result <= expected_temp + TEMPERATURE_SENSOR_TOLERANCE


# =============================================================================
# TEST PRECONDITION EVALUATION WORKFLOW
# =============================================================================


class TestPreconditionEvaluationWorkflow:
    """Integration tests for precondition evaluation workflows."""

    def test_empty_preconditions_returns_true(self, sensor_service):
        """Empty preconditions list should return True (vacuous truth).

        When no preconditions are specified, all conditions are trivially
        satisfied, so evaluate_preconditions([]) should return True.
        """
        # Execute with empty list
        result = sensor_service.evaluate_preconditions([])

        # Verify vacuous truth - no conditions means all conditions pass
        assert result is True

        # Verify no history entries (nothing was evaluated)
        history = sensor_service.get_evaluation_history(limit=10)
        assert len(history) == 0

    def test_single_precondition_passes_when_threshold_met(
        self, mock_light_sensor_bh1750, sensor_service
    ):
        """Single precondition passes when sensor reading meets threshold."""
        # Setup: Light at 50 lux (below 100 threshold)
        mock_light_sensor_bh1750(50.0)

        # Define precondition: light < 100 lux
        preconditions = [
            SensorPrecondition(
                sensor_type="light",
                threshold=100.0,
                comparison="lt",
                description="Capture only in low light",
            )
        ]

        # Execute
        result = sensor_service.evaluate_preconditions(preconditions)

        # Verify
        assert result is True

    def test_single_precondition_fails_when_threshold_not_met(
        self, mock_light_sensor_bh1750, sensor_service
    ):
        """Single precondition fails when sensor reading doesn't meet threshold."""
        # Setup: Light at 150 lux (above 100 threshold)
        mock_light_sensor_bh1750(150.0)

        # Define precondition: light < 100 lux
        preconditions = [
            SensorPrecondition(
                sensor_type="light",
                threshold=100.0,
                comparison="lt",
                description="Capture only in low light",
            )
        ]

        # Execute
        result = sensor_service.evaluate_preconditions(preconditions)

        # Verify
        assert result is False

    def test_multiple_preconditions_and_logic(
        self, mock_sensor_hardware, sensor_service
    ):
        """Multiple preconditions must ALL pass (AND logic)."""
        # Setup: Configure mock to return different values for light vs temp
        # Light sensor: 50 lux (raw = 60 for BH1750: 60 / 1.2 = 50)
        # Temperature sensor: 25C (raw = 400 for TMP102: 400 * 0.0625 = 25)

        # Extract I2C addresses from hardware config (not hardcoded)
        light_addr = mock_sensor_hardware["hw_config"]["light_sensor_address"]
        temp_addr = mock_sensor_hardware["hw_config"]["temperature_sensor_address"]

        def mock_read_block_side_effect(addr, reg, length):
            if addr == light_addr:  # Light sensor (from config)
                return [0x00, 0x3C]  # 60 raw = 50 lux
            elif addr == temp_addr:  # Temperature sensor (from config)
                return [0x19, 0x00]  # 400 raw = 25C
            return [0x00, 0x00]

        # Use MagicMock for built-in call tracking
        mock_read_block = MagicMock(side_effect=mock_read_block_side_effect)
        mock_sensor_hardware["smbus"].read_i2c_block_data = mock_read_block

        # Both conditions should pass
        preconditions = [
            SensorPrecondition(
                sensor_type="light", threshold=100.0, comparison="lt"
            ),  # 50 < 100 -> pass
            SensorPrecondition(
                sensor_type="temperature", threshold=30.0, comparison="lte"
            ),  # 25 <= 30 -> pass
        ]

        # Execute
        result = sensor_service.evaluate_preconditions(preconditions)

        # Verify all passed
        assert result is True

        # Verify both sensors were read (using MagicMock's built-in tracking)
        assert mock_read_block.call_count >= 2

        # Verify history shows both evaluated
        history = sensor_service.get_evaluation_history(limit=10)
        assert len(history) == 2

    def test_precondition_evaluation_records_history(
        self, mock_light_sensor_bh1750, sensor_service
    ):
        """Precondition evaluation records result in service history."""
        expected_lux = 50.0
        mock_light_sensor_bh1750(expected_lux)

        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")
        ]

        # Execute
        sensor_service.evaluate_preconditions(preconditions)

        # Verify history
        history = sensor_service.get_evaluation_history(limit=1)
        assert len(history) == 1
        assert history[0].passed is True
        assert history[0].reason == REASON_PASSED
        assert history[0].reading_value is not None
        assert expected_lux - LIGHT_SENSOR_TOLERANCE <= history[0].reading_value <= expected_lux + LIGHT_SENSOR_TOLERANCE


# =============================================================================
# TEST SENSOR UNAVAILABLE WORKFLOW
# =============================================================================


class TestSensorUnavailableWorkflow:
    """Integration tests for graceful fallback when sensors unavailable."""

    def test_sensor_unavailable_precondition_fails_gracefully(
        self, mock_sensor_hardware, sensor_service
    ):
        """Disabled sensor causes precondition to fail gracefully (not exception)."""
        # Disable light sensor
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = False

        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")
        ]

        # Should not raise, should return False
        result = sensor_service.evaluate_preconditions(preconditions)

        assert result is False

        # Verify reason recorded
        history = sensor_service.get_evaluation_history(limit=1)
        assert history[0].reason == REASON_SENSOR_UNAVAILABLE

    def test_i2c_error_handled_gracefully(self, mock_sensor_hardware):
        """OSError during I2C read returns None, not exception."""
        # Make SMBus raise OSError
        mock_sensor_hardware["smbus"].read_i2c_block_data = MagicMock(
            side_effect=OSError("I2C communication error")
        )

        # Should return None, not raise
        result = read_light_sensor()

        assert result is None

    def test_mixed_availability_workflow(self, mock_sensor_hardware, sensor_service):
        """One sensor available, one unavailable - available sensor still works."""
        # Light sensor enabled, temperature disabled
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = True
        mock_sensor_hardware["hw_config"]["temperature_sensor_enabled"] = False
        mock_sensor_hardware["smbus"].read_data = [0x00, 0x78]  # 100 lux
        expected_lux = 100.0

        # Light should work
        light_result = read_light_sensor()
        assert light_result is not None
        assert expected_lux - LIGHT_SENSOR_TOLERANCE <= light_result <= expected_lux + LIGHT_SENSOR_TOLERANCE

        # Temperature should return None
        temp_result = read_temperature_sensor()
        assert temp_result is None


# =============================================================================
# TEST ENVIRONMENTAL LOGGING WORKFLOW
# =============================================================================


class TestEnvironmentalLoggingWorkflow:
    """Integration tests for environmental sensor data capture for photo metadata."""

    def test_environmental_readings_captures_all_sensors(self, mock_sensor_hardware):
        """get_environmental_readings() returns dict with all sensor data."""
        # Setup both sensors
        mock_sensor_hardware["smbus"].read_data = [0x00, 0x78]  # ~100 lux / 25C-ish

        # Execute
        readings = get_environmental_readings()

        # Verify structure
        assert "ambient_light_lux" in readings
        assert "ambient_temperature_celsius" in readings
        assert "sensor_reading_timestamp" in readings

        # Verify light reading present
        assert readings["ambient_light_lux"] is not None
        assert isinstance(readings["ambient_light_lux"], float)

    def test_environmental_readings_with_partial_availability(
        self, mock_sensor_hardware
    ):
        """One sensor unavailable returns None for that sensor, not error."""
        # Disable temperature sensor
        mock_sensor_hardware["hw_config"]["temperature_sensor_enabled"] = False
        mock_sensor_hardware["smbus"].read_data = [0x00, 0x78]

        # Execute
        readings = get_environmental_readings()

        # Light should work
        assert readings["ambient_light_lux"] is not None

        # Temperature should be None (graceful fallback)
        assert readings["ambient_temperature_celsius"] is None

        # Timestamp still present
        assert readings["sensor_reading_timestamp"] is not None

    def test_environmental_readings_format_for_metadata(self, mock_sensor_hardware):
        """Environmental readings format is compatible with photo metadata."""
        mock_sensor_hardware["smbus"].read_data = [0x00, 0x78]

        # Execute
        readings = get_environmental_readings()

        # Verify types
        assert isinstance(
            readings["ambient_light_lux"], (float, type(None))
        )
        assert isinstance(
            readings["ambient_temperature_celsius"], (float, type(None))
        )

        # Verify timestamp is valid ISO 8601 format
        timestamp = readings["sensor_reading_timestamp"]
        assert timestamp is not None
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp)  # Will raise if invalid


# =============================================================================
# TEST SENSOR SERVICE INTEGRATION
# =============================================================================


class TestSensorServiceIntegration:
    """Integration tests for sensor service layer integration."""

    def test_service_statistics_track_pass_fail_rates(
        self, mock_light_sensor_bh1750, mock_sensor_hardware, sensor_service
    ):
        """Service statistics accurately count passed/failed/unavailable."""
        # Pass: low light
        mock_light_sensor_bh1750(50.0)
        sensor_service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")]
        )

        # Fail: high light
        mock_light_sensor_bh1750(150.0)
        sensor_service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")]
        )

        # Unavailable
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = False
        sensor_service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")]
        )

        # Re-enable for next tests
        mock_sensor_hardware["hw_config"]["light_sensor_enabled"] = True

        # Verify statistics
        stats = sensor_service.get_statistics()
        assert stats["total_evaluations"] == 3
        assert stats["passed_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["unavailable_count"] == 1

    def test_concurrent_evaluations_thread_safe(
        self, mock_light_sensor_bh1750, sensor_service
    ):
        """Multiple threads evaluating preconditions maintain data integrity."""
        mock_light_sensor_bh1750(50.0)

        preconditions = [
            SensorPrecondition(sensor_type="light", threshold=100.0, comparison="lt")
        ]

        num_threads = 10
        evaluations_per_thread = 20

        def evaluate_many():
            results = []
            for _ in range(evaluations_per_thread):
                result = sensor_service.evaluate_preconditions(preconditions)
                results.append(result)
            return results

        # Run concurrent evaluations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(evaluate_many) for _ in range(num_threads)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        # All should have passed
        total_evaluations = num_threads * evaluations_per_thread
        assert len(all_results) == total_evaluations
        assert all(r is True for r in all_results)

        # Statistics should match
        stats = sensor_service.get_statistics()
        assert stats["total_evaluations"] == total_evaluations
        assert stats["passed_count"] == total_evaluations


# =============================================================================
# TEST SENSOR WORKFLOW WITH REAL HARDWARE
# =============================================================================


@pytest.mark.hardware
class TestSensorWorkflowHardware:
    """
    Integration tests requiring real I2C sensors on Raspberry Pi.

    These tests verify end-to-end sensor workflow on actual hardware.
    They are skipped in CI/CD and on non-Pi systems.

    To run: pytest Tests/integration/test_sensor_workflow.py -v -m hardware
    """

    def test_precondition_service_with_real_light_sensor(self):
        """
        Full workflow: Real light sensor -> SensorService evaluation.

        Tests that the service layer correctly integrates with real I2C hardware.
        """
        from webui.backend.lib.sensor_reader import read_light_sensor
        from webui.backend.services.sensor_service import SensorService

        # First check if sensor is available
        reading = read_light_sensor()

        if reading is None:
            pytest.skip("Light sensor not available on this hardware")

        # Create service and evaluate precondition
        service = SensorService(max_history=10)

        # Use current reading + buffer as threshold to ensure pass
        threshold = reading + 50.0
        preconditions = [
            SensorPrecondition(
                sensor_type="light",
                threshold=threshold,
                comparison="lt",
                description="Current ambient light check",
            )
        ]

        result = service.evaluate_preconditions(preconditions)

        # Should pass since we set threshold above current reading
        assert result is True

        # Verify history was recorded
        history = service.get_evaluation_history(limit=1)
        assert len(history) == 1
        assert history[0].passed is True
        assert history[0].reading_value is not None
        # Reading should be close to what we measured
        assert abs(history[0].reading_value - reading) < 10.0  # Allow for variance

    def test_precondition_service_with_real_temperature_sensor(self):
        """
        Full workflow: Real temperature sensor -> SensorService evaluation.

        Tests that the service layer correctly integrates with real I2C hardware.
        """
        from webui.backend.lib.sensor_reader import read_temperature_sensor
        from webui.backend.services.sensor_service import SensorService

        # First check if sensor is available
        reading = read_temperature_sensor()

        if reading is None:
            pytest.skip("Temperature sensor not available on this hardware")

        # Create service and evaluate precondition
        service = SensorService(max_history=10)

        # Use current reading + buffer as threshold to ensure pass
        threshold = reading + 10.0
        preconditions = [
            SensorPrecondition(
                sensor_type="temperature",
                threshold=threshold,
                comparison="lte",
                description="Current ambient temperature check",
            )
        ]

        result = service.evaluate_preconditions(preconditions)

        # Should pass since we set threshold above current reading
        assert result is True

        # Verify history was recorded
        history = service.get_evaluation_history(limit=1)
        assert len(history) == 1
        assert history[0].passed is True

    def test_multiple_preconditions_with_real_sensors(self):
        """
        Full workflow: Multiple real sensors -> combined precondition evaluation.

        Tests AND logic with real sensor readings.
        """
        from webui.backend.lib.sensor_reader import (
            read_light_sensor,
            read_temperature_sensor,
        )
        from webui.backend.services.sensor_service import SensorService

        light = read_light_sensor()
        temp = read_temperature_sensor()

        # Need at least one sensor for this test
        if light is None and temp is None:
            pytest.skip("No sensors available on this hardware")

        service = SensorService(max_history=10)
        preconditions = []

        if light is not None:
            preconditions.append(
                SensorPrecondition(
                    sensor_type="light",
                    threshold=light + 100.0,
                    comparison="lt",
                )
            )

        if temp is not None:
            preconditions.append(
                SensorPrecondition(
                    sensor_type="temperature",
                    threshold=temp + 20.0,
                    comparison="lte",
                )
            )

        result = service.evaluate_preconditions(preconditions)

        # Should pass since thresholds are set above current readings
        assert result is True

        # All preconditions should be in history
        history = service.get_evaluation_history(limit=len(preconditions))
        assert len(history) == len(preconditions)
        assert all(h.passed for h in history)

    def test_environmental_logging_workflow_real_hardware(self):
        """
        Full workflow: Real sensors -> environmental readings for photo metadata.

        Tests that environmental data can be captured and formatted correctly.
        """
        from webui.backend.lib.sensor_reader import get_environmental_readings

        readings = get_environmental_readings()

        # Should always return a properly structured dict
        assert isinstance(readings, dict)
        assert "ambient_light_lux" in readings
        assert "ambient_temperature_celsius" in readings
        assert "sensor_reading_timestamp" in readings

        # Timestamp should always be present and valid
        timestamp = readings["sensor_reading_timestamp"]
        assert timestamp is not None
        datetime.fromisoformat(timestamp)

        # If sensors are available, values should be reasonable
        if readings["ambient_light_lux"] is not None:
            assert 0 <= readings["ambient_light_lux"] <= 100000  # Reasonable lux range

        if readings["ambient_temperature_celsius"] is not None:
            assert -40 <= readings["ambient_temperature_celsius"] <= 85  # Sensor range

    def test_service_statistics_with_real_hardware(self):
        """
        Full workflow: Real sensor evaluations -> accurate statistics tracking.

        Tests that statistics are correctly maintained across real evaluations.
        """
        from webui.backend.lib.sensor_reader import read_light_sensor
        from webui.backend.services.sensor_service import SensorService

        reading = read_light_sensor()

        if reading is None:
            pytest.skip("Light sensor not available on this hardware")

        service = SensorService(max_history=10)

        # Do several evaluations with different thresholds
        # Some should pass, some should fail
        pass_threshold = reading + 50.0  # Should pass
        fail_threshold = reading - 50.0 if reading > 50 else 0.1  # Should fail

        # Evaluate passing condition
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=pass_threshold, comparison="lt")]
        )

        # Evaluate failing condition
        service.evaluate_preconditions(
            [SensorPrecondition(sensor_type="light", threshold=fail_threshold, comparison="lt")]
        )

        stats = service.get_statistics()

        assert stats["total_evaluations"] == 2
        assert stats["passed_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["unavailable_count"] == 0
