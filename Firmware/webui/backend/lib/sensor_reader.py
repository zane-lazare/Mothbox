"""
Sensor reading library for I2C-based environmental sensors.

Simple one-shot read functions for light and temperature sensors.
Used for:
1. Pre-condition checks at scheduled capture time
2. Environmental logging (recording ambient conditions with photos)

Supported sensors (I2C only):
- light: BH1750 (0x23) or LTR303 (0x29) ambient light sensor
- temperature: TMP102 (0x48) or MCP9808 (0x18) temperature sensor

NOTE: This is NOT a real-time monitoring daemon. Sensors are read
on-demand at capture time, making it compatible with cron-based
scheduling and power-saving modes.

Usage:
    from webui.backend.lib.sensor_reader import (
        read_light_sensor,
        read_temperature_sensor,
        check_precondition,
        get_environmental_readings,
    )

    # One-shot read
    lux = read_light_sensor()  # Returns float or None if unavailable

    # Pre-condition check
    if check_precondition("light", threshold=100, comparison="lt"):
        # Light is less than 100 lux, proceed with capture
        pass

    # Get readings for photo metadata
    readings = get_environmental_readings()
    # {'ambient_light_lux': 50.0, 'ambient_temperature_celsius': 22.5, ...}
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Final

from mothbox_paths import get_hardware_config

logger = logging.getLogger(__name__)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "SensorReading",
    "read_light_sensor",
    "read_temperature_sensor",
    "check_precondition",
    "get_environmental_readings",
    "get_sensor_reading",
    # Constants (for type checking and validation)
    "SENSOR_TYPES",
    "SENSOR_COMPARISONS",
    # Cache management (for testing)
    "clear_hw_config_cache",
    "reset_i2c_availability",
]

# =============================================================================
# CONSTANTS
# =============================================================================

# Supported sensor types (NO motion - scheduler preconditions only)
SENSOR_TYPES: Final[list[str]] = ["light", "temperature"]

# Supported comparison operators for pre-conditions
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]

# Module-level I2C availability flag (lazy check on first read)
_i2c_available: bool | None = None

# TMP102 constants
TMP102_RESOLUTION: Final[float] = 0.0625  # 12-bit resolution: 1/16°C per LSB
TMP102_NEGATIVE_THRESHOLD: Final[int] = 2047  # 12-bit sign boundary
TMP102_TWOS_COMPLEMENT: Final[int] = 4096  # 2^12 for negative conversion

# MCP9808 constants
MCP9808_RESOLUTION: Final[float] = 1 / 16.0  # 0.0625°C per LSB
MCP9808_DATA_MASK: Final[int] = 0x1FFF  # 13-bit data mask
MCP9808_NEGATIVE_THRESHOLD: Final[int] = 4095  # 13-bit sign boundary
MCP9808_TWOS_COMPLEMENT: Final[int] = 8192  # 2^13 for negative conversion
MCP9808_AMBIENT_TEMP_REG: Final[int] = 0x05  # Ambient temperature register

# TMP102 register
TMP102_TEMP_REG: Final[int] = 0x00  # Temperature register

# BH1750 constants
BH1750_ONE_TIME_HIGH_RES: Final[int] = 0x20  # One-time high resolution mode

# LTR303 constants (registers and calibration data)
LTR303_CONTROL_REG: Final[int] = 0x80  # ALS control register
LTR303_MEAS_RATE_REG: Final[int] = 0x85  # ALS measurement rate register
LTR303_CH1_LOW: Final[int] = 0x88  # ALS data CH1 low byte
LTR303_CH1_HIGH: Final[int] = 0x89  # ALS data CH1 high byte
LTR303_CH0_LOW: Final[int] = 0x8A  # ALS data CH0 low byte
LTR303_CH0_HIGH: Final[int] = 0x8B  # ALS data CH0 high byte
LTR303_ENABLE: Final[int] = 0x01  # Enable ALS in active mode

# LTR303 gain values (bits 2-4 of control register)
# Key = gain bits value, Value = gain multiplier
LTR303_GAIN_MAP: Final[dict[int, int]] = {
    0: 1,    # 1x gain (default)
    1: 2,    # 2x gain
    2: 4,    # 4x gain
    3: 8,    # 8x gain
    6: 48,   # 48x gain
    7: 96,   # 96x gain
}

# LTR303 integration time values (bits 3-5 of meas rate register)
# Key = int time bits value, Value = integration time in ms
LTR303_INT_TIME_MAP: Final[dict[int, int]] = {
    0: 100,   # 100ms (default)
    1: 50,    # 50ms
    2: 200,   # 200ms
    3: 400,   # 400ms
    4: 150,   # 150ms
    5: 250,   # 250ms
    6: 300,   # 300ms
    7: 350,   # 350ms
}

# Comparison tolerance for sensor values
COMPARISON_TOLERANCE: Final[dict[str, float]] = {
    "light": 1.0,  # 1 lux tolerance
    "temperature": 0.1,  # 0.1°C tolerance
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SensorReading:
    """
    A single sensor reading.

    Attributes:
        sensor_type: Type of sensor ("light" or "temperature")
        value: Sensor reading value (lux for light, celsius for temperature)
        timestamp: When the reading was taken
        unit: Unit of measurement ("lux" or "celsius")
    """

    sensor_type: str
    value: float
    timestamp: datetime
    unit: str


# =============================================================================
# HARDWARE CONFIG CACHING
# =============================================================================


@lru_cache(maxsize=1)
def _get_cached_hw_config():
    """
    Get hardware configuration with caching.

    Uses LRU cache to avoid parsing controls.txt on every sensor read.
    Cache is cleared manually when config changes.

    Returns:
        Hardware configuration dictionary
    """
    return get_hardware_config()


def clear_hw_config_cache():
    """Clear hardware config cache. Call when config changes."""
    _get_cached_hw_config.cache_clear()


def _check_i2c_available() -> bool:
    """
    Check if I2C/smbus2 is available on this system.

    Performs a lazy check on first call and caches the result.
    Used by sensor reading functions to early-exit if I2C unavailable.

    Returns:
        True if smbus2 is importable, False otherwise
    """
    global _i2c_available
    if _i2c_available is None:
        try:
            from smbus2 import SMBus  # noqa: F401

            _i2c_available = True
        except ImportError:
            _i2c_available = False
            logger.warning("smbus2 not available for I2C sensors")
    return _i2c_available


# =============================================================================
# SENSOR READING FUNCTIONS
# =============================================================================


def read_light_sensor() -> float | None:
    """
    Read current lux value from light sensor (BH1750 or LTR303).

    Performs a one-shot I2C read. Returns None if sensor is disabled,
    unavailable, or if an error occurs.

    WARNING: LTR303 lux calculation is approximate and based on simplified
    conversion. For accurate measurements, use BH1750 or implement full
    LTR303 calibration algorithm with integration time compensation.

    Returns:
        Lux value as float, or None if unavailable
    """
    global _i2c_available

    try:
        hw_config = _get_cached_hw_config()

        if not hw_config.get("light_sensor_enabled", False):
            return None

        # Check I2C availability (lazy check with caching)
        if not _check_i2c_available():
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("light_sensor_type", "BH1750")
        address = hw_config.get("light_sensor_address", 0x23)
        i2c_bus = hw_config.get("i2c_bus", 1)

        with SMBus(i2c_bus) as bus:
            if sensor_type == "BH1750":
                # BH1750 one-time high resolution mode
                bus.write_byte(address, BH1750_ONE_TIME_HIGH_RES)
                time.sleep(0.2)  # Wait for measurement
                data = bus.read_i2c_block_data(address, 0x00, 2)
                raw_val = (data[0] << 8) | data[1]
                lux = raw_val / 1.2
                return lux

            elif sensor_type == "LTR303":
                # LTR303 ambient light sensor - proper lux calculation
                # Enable sensor in active mode
                bus.write_byte_data(address, LTR303_CONTROL_REG, LTR303_ENABLE)
                time.sleep(0.1)  # Wait for measurement

                # Read gain setting from control register (bits 2-4)
                control = bus.read_byte_data(address, LTR303_CONTROL_REG)
                gain_bits = (control >> 2) & 0x07
                gain = LTR303_GAIN_MAP.get(gain_bits, 1)

                # Read integration time from measurement rate register (bits 3-5)
                meas_rate = bus.read_byte_data(address, LTR303_MEAS_RATE_REG)
                int_time_bits = (meas_rate >> 3) & 0x07
                int_time_ms = LTR303_INT_TIME_MAP.get(int_time_bits, 100)

                # Read channel 1 (visible + IR) and channel 0 (IR only)
                ch1_low = bus.read_byte_data(address, LTR303_CH1_LOW)
                ch1_high = bus.read_byte_data(address, LTR303_CH1_HIGH)
                ch1 = (ch1_high << 8) | ch1_low

                ch0_low = bus.read_byte_data(address, LTR303_CH0_LOW)
                ch0_high = bus.read_byte_data(address, LTR303_CH0_HIGH)
                ch0 = (ch0_high << 8) | ch0_low

                # Calculate lux using ratio method (per LTR303 datasheet)
                # Normalize by gain and integration time
                if ch1 == 0:
                    return 0.0

                ratio = ch0 / ch1 if ch1 > 0 else 0
                int_time_factor = int_time_ms / 100.0  # Normalize to 100ms

                # Apply ratio-based formula (simplified from datasheet)
                if ratio < 0.45:
                    lux = (1.7743 * ch1 + 1.1059 * ch0) / (gain * int_time_factor)
                elif ratio < 0.64:
                    lux = (4.2785 * ch1 - 1.9548 * ch0) / (gain * int_time_factor)
                elif ratio < 0.85:
                    lux = (0.5926 * ch1 + 0.1185 * ch0) / (gain * int_time_factor)
                else:
                    lux = 0.0  # High IR ratio indicates dark/invalid

                return max(0.0, lux)

            else:
                logger.warning(f"Unknown light sensor type: {sensor_type}")
                return None

    except OSError as e:  # I2C communication errors
        logger.debug(f"Light sensor read error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading light sensor: {e}", exc_info=True)
        return None


def read_temperature_sensor() -> float | None:
    """
    Read current temperature from sensor (TMP102 or MCP9808).

    Performs a one-shot I2C read. Returns None if sensor is disabled,
    unavailable, or if an error occurs.

    Returns:
        Temperature in Celsius as float, or None if unavailable
    """
    global _i2c_available

    try:
        hw_config = _get_cached_hw_config()

        if not hw_config.get("temperature_sensor_enabled", False):
            return None

        # Check I2C availability (lazy check with caching)
        if not _check_i2c_available():
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("temperature_sensor_type", "TMP102")
        address = hw_config.get("temperature_sensor_address", 0x48)
        i2c_bus = hw_config.get("i2c_bus", 1)

        with SMBus(i2c_bus) as bus:
            if sensor_type == "TMP102":
                # TMP102 temperature register
                data = bus.read_i2c_block_data(address, TMP102_TEMP_REG, 2)
                raw = (data[0] << 4) | (data[1] >> 4)
                if raw > TMP102_NEGATIVE_THRESHOLD:  # Negative temperature
                    raw -= TMP102_TWOS_COMPLEMENT
                celsius = raw * TMP102_RESOLUTION
                return celsius

            elif sensor_type == "MCP9808":
                # MCP9808 ambient temperature register
                data = bus.read_i2c_block_data(address, MCP9808_AMBIENT_TEMP_REG, 2)
                raw = (data[0] << 8) | data[1]
                raw &= MCP9808_DATA_MASK
                if raw > MCP9808_NEGATIVE_THRESHOLD:  # Negative temperature
                    raw -= MCP9808_TWOS_COMPLEMENT
                celsius = raw * MCP9808_RESOLUTION
                return celsius

            else:
                logger.warning(f"Unknown temperature sensor type: {sensor_type}")
                return None

    except OSError as e:  # I2C communication errors
        logger.debug(f"Temperature sensor read error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading temperature sensor: {e}", exc_info=True)
        return None


# =============================================================================
# PRE-CONDITION CHECKING
# =============================================================================


def check_precondition(sensor_type: str, threshold: float, comparison: str) -> bool:
    """
    Check if sensor reading meets threshold condition.

    Evaluated at scheduled capture time - NOT real-time triggers.
    If sensor is unavailable or reading fails, returns False.

    Args:
        sensor_type: Sensor type ("light" or "temperature")
        threshold: Value to compare against
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")

    Returns:
        True if condition is met, False otherwise (including if sensor unavailable)

    Example:
        # Capture only if light < 100 lux
        if check_precondition("light", 100, "lt"):
            take_photo()
    """
    if sensor_type not in SENSOR_TYPES:
        logger.warning(f"Unknown sensor type: {sensor_type}. Valid: {SENSOR_TYPES}")
        return False

    if comparison not in SENSOR_COMPARISONS:
        logger.warning(f"Unknown comparison: {comparison}. Valid: {SENSOR_COMPARISONS}")
        return False

    # Read sensor value
    if sensor_type == "light":
        value = read_light_sensor()
    elif sensor_type == "temperature":
        value = read_temperature_sensor()
    else:
        return False

    # If sensor unavailable, precondition fails
    if value is None:
        logger.debug(f"Precondition check failed: {sensor_type} sensor unavailable")
        return False

    # Get sensor-type-aware tolerance for equality comparisons
    tolerance = COMPARISON_TOLERANCE.get(sensor_type, 0.01)

    # Perform comparison
    comparisons = {
        "gt": value > threshold,
        "lt": value < threshold,
        "eq": abs(value - threshold) < tolerance,  # Sensor-specific tolerance
        "gte": value >= threshold,
        "lte": value <= threshold,
    }

    result = comparisons.get(comparison, False)
    logger.debug(
        f"Precondition check: {sensor_type} {value:.2f} {comparison} {threshold} = {result}"
    )
    return result


# =============================================================================
# ENVIRONMENTAL READINGS FOR METADATA
# =============================================================================


def get_environmental_readings() -> dict:
    """
    Get current environmental sensor readings for photo metadata.

    Returns a dict suitable for embedding in photo EXIF or sidecar metadata.
    Missing sensors return None for their values.

    Returns:
        Dict with keys:
        - ambient_light_lux: float or None
        - ambient_temperature_celsius: float or None
        - sensor_reading_timestamp: ISO 8601 timestamp
    """
    light = read_light_sensor()
    temp = read_temperature_sensor()
    now = datetime.now()  # After reads for accuracy

    return {
        "ambient_light_lux": light,
        "ambient_temperature_celsius": temp,
        "sensor_reading_timestamp": now.isoformat(),
    }


def get_sensor_reading(sensor_type: str) -> SensorReading | None:
    """
    Get a full SensorReading object for a sensor type.

    Args:
        sensor_type: "light" or "temperature"

    Returns:
        SensorReading with value, timestamp, and unit, or None if unavailable
    """
    if sensor_type not in SENSOR_TYPES:
        logger.warning(f"Unknown sensor type: {sensor_type}. Valid: {SENSOR_TYPES}")
        return None

    if sensor_type == "light":
        value = read_light_sensor()
        unit = "lux"
    elif sensor_type == "temperature":
        value = read_temperature_sensor()
        unit = "celsius"
    else:
        return None

    if value is None:
        return None

    return SensorReading(
        sensor_type=sensor_type,
        value=value,
        timestamp=datetime.now(),
        unit=unit,
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def reset_i2c_availability() -> None:
    """
    Reset the I2C availability flag.

    Primarily for testing purposes - forces re-check on next read.
    """
    global _i2c_available
    _i2c_available = None
