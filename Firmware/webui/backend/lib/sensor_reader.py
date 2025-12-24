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
from typing import Final

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Supported sensor types (NO motion - scheduler preconditions only)
SENSOR_TYPES: Final[list[str]] = ["light", "temperature"]

# Supported comparison operators for pre-conditions
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]

# Module-level I2C availability flag (lazy check on first read)
_i2c_available: bool | None = None


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
# SENSOR READING FUNCTIONS
# =============================================================================


def read_light_sensor() -> float | None:
    """
    Read current lux value from light sensor (BH1750 or LTR303).

    Performs a one-shot I2C read. Returns None if sensor is disabled,
    unavailable, or if an error occurs.

    Returns:
        Lux value as float, or None if unavailable
    """
    global _i2c_available

    try:
        from mothbox_paths import get_hardware_config

        hw_config = get_hardware_config()

        if not hw_config.get("light_sensor_enabled", False):
            return None

        # Lazy check I2C availability
        if _i2c_available is None:
            try:
                from smbus2 import SMBus  # noqa: F401

                _i2c_available = True
            except ImportError:
                _i2c_available = False
                logger.warning("smbus2 not available for I2C sensors")

        if not _i2c_available:
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("light_sensor_type", "BH1750")
        address = hw_config.get("light_sensor_address", 0x23)

        with SMBus(1) as bus:
            if sensor_type == "BH1750":
                # BH1750 one-time high resolution mode (0x20)
                bus.write_byte(address, 0x20)
                time.sleep(0.2)  # Wait for measurement
                data = bus.read_i2c_block_data(address, 0x00, 2)
                raw_val = (data[0] << 8) | data[1]
                lux = raw_val / 1.2
                return lux

            elif sensor_type == "LTR303":
                # LTR303 ambient light sensor
                # Enable sensor
                bus.write_byte_data(address, 0x80, 0x01)
                time.sleep(0.1)
                # Read channel 1 (visible + IR)
                ch1_low = bus.read_byte_data(address, 0x88)
                ch1_high = bus.read_byte_data(address, 0x89)
                ch1 = (ch1_high << 8) | ch1_low
                # Approximate lux calculation
                lux = ch1 * 0.5  # Simplified conversion
                return lux

            else:
                logger.warning(f"Unknown light sensor type: {sensor_type}")
                return None

    except Exception as e:
        logger.debug(f"Light sensor read error: {e}")
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
        from mothbox_paths import get_hardware_config

        hw_config = get_hardware_config()

        if not hw_config.get("temperature_sensor_enabled", False):
            return None

        # Lazy check I2C availability
        if _i2c_available is None:
            try:
                from smbus2 import SMBus  # noqa: F401

                _i2c_available = True
            except ImportError:
                _i2c_available = False
                logger.warning("smbus2 not available for I2C sensors")

        if not _i2c_available:
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("temperature_sensor_type", "TMP102")
        address = hw_config.get("temperature_sensor_address", 0x48)

        with SMBus(1) as bus:
            if sensor_type == "TMP102":
                # TMP102 temperature register
                data = bus.read_i2c_block_data(address, 0x00, 2)
                raw = (data[0] << 4) | (data[1] >> 4)
                if raw > 2047:  # Negative temperature
                    raw -= 4096
                celsius = raw * 0.0625
                return celsius

            elif sensor_type == "MCP9808":
                # MCP9808 ambient temperature register
                data = bus.read_i2c_block_data(address, 0x05, 2)
                raw = (data[0] << 8) | data[1]
                raw &= 0x1FFF
                if raw > 4095:  # Negative temperature
                    raw -= 8192
                celsius = raw / 16.0
                return celsius

            else:
                logger.warning(f"Unknown temperature sensor type: {sensor_type}")
                return None

    except Exception as e:
        logger.debug(f"Temperature sensor read error: {e}")
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
        logger.warning(
            f"Unknown comparison: {comparison}. Valid: {SENSOR_COMPARISONS}"
        )
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

    # Perform comparison
    comparisons = {
        "gt": value > threshold,
        "lt": value < threshold,
        "eq": abs(value - threshold) < 0.01,  # Tolerance for float equality
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
    now = datetime.now()

    return {
        "ambient_light_lux": read_light_sensor(),
        "ambient_temperature_celsius": read_temperature_sensor(),
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
