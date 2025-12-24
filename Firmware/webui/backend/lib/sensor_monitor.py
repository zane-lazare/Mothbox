"""
Sensor monitoring for trigger-based scheduling.

Monitors GPIO inputs for motion sensors, light sensors, and temperature
sensors, dispatching events when thresholds are crossed.

Supported sensor types:
- motion: PIR motion sensor (digital input, rising edge trigger)
- light: LDR/photoresistor via I2C (BH1750 or LTR303)
- temperature: Temperature sensor via I2C (TMP102 or MCP9808)

Usage:
    from webui.backend.lib.sensor_monitor import (
        SensorMonitor,
        SensorTriggerConfig,
        SensorReading,
        get_sensor_monitor,
    )

    def on_motion(reading: SensorReading):
        print(f"Motion detected: {reading}")

    config = SensorTriggerConfig(
        sensor_type="motion",
        threshold=0.5,
        comparison="gt",
        cooldown_minutes=5,
        callback=on_motion,
    )

    monitor = get_sensor_monitor()
    monitor.register_trigger(config)
    monitor.start()
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Final

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Sensor type configuration defaults
SENSOR_CONFIGS: Final[dict] = {
    "motion": {
        "gpio_mode": "digital",
        "default_pin": 17,
        "edge_type": "rising",
        "debounce_ms": 200,
    },
    "light": {
        "gpio_mode": "analog",
        "adc_channel": 0,
        "sample_interval_ms": 1000,
    },
    "temperature": {
        "gpio_mode": "analog",
        "adc_channel": 1,
        "sample_interval_ms": 5000,
    },
}

# Supported sensor types
SENSOR_TYPES: Final[list[str]] = ["motion", "light", "temperature"]

# Supported comparison operators
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]

# Maximum readings to store in history
MAX_READINGS_HISTORY: Final[int] = 100

# Monitor loop interval in seconds
MONITOR_LOOP_INTERVAL: Final[float] = 0.1  # 100ms


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SensorReading:
    """
    A single sensor reading.

    Attributes:
        sensor_type: Type of sensor ("motion", "light", "temperature")
        value: Sensor reading value (1.0 for motion detected, lux for light, celsius for temp)
        timestamp: When the reading was taken
        triggered: Whether this reading triggered a callback
    """

    sensor_type: str
    value: float
    timestamp: datetime
    triggered: bool = False


@dataclass
class SensorTriggerConfig:
    """
    Configuration for a sensor trigger.

    Attributes:
        sensor_type: Type of sensor to monitor ("motion", "light", "temperature")
        threshold: Value threshold for triggering (ignored for motion sensors)
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
        cooldown_minutes: Minimum minutes between triggers (0-60)
        callback: Function to call when triggered, receives SensorReading
    """

    sensor_type: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    cooldown_minutes: int
    callback: Callable[[SensorReading], None]


# =============================================================================
# SENSOR MONITOR CLASS
# =============================================================================


class SensorMonitor:
    """
    Monitors sensors and dispatches trigger callbacks.

    Thread-safe monitoring with configurable cooldown periods.
    Supports motion (PIR), light (I2C), and temperature (I2C) sensors.

    Example:
        monitor = SensorMonitor()
        config = SensorTriggerConfig(
            sensor_type="motion",
            threshold=0.5,
            comparison="gt",
            cooldown_minutes=5,
            callback=my_callback,
        )
        monitor.register_trigger(config)
        monitor.start()

        # Later...
        monitor.stop()
    """

    def __init__(self):
        """Initialize the sensor monitor."""
        self._triggers: list[SensorTriggerConfig] = []
        self._last_trigger_times: dict[str, datetime] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._readings: deque[SensorReading] = deque(maxlen=MAX_READINGS_HISTORY)

        # Hardware availability flags (set during first read attempt)
        self._gpio_available: bool | None = None
        self._i2c_available: bool | None = None

    def register_trigger(self, config: SensorTriggerConfig) -> None:
        """
        Register a new sensor trigger.

        Args:
            config: Trigger configuration with sensor type, threshold, and callback
        """
        if config.sensor_type not in SENSOR_TYPES:
            logger.warning(
                f"Unknown sensor type: {config.sensor_type}. "
                f"Supported types: {SENSOR_TYPES}"
            )
            return

        if config.comparison not in SENSOR_COMPARISONS:
            logger.warning(
                f"Unknown comparison: {config.comparison}. "
                f"Supported comparisons: {SENSOR_COMPARISONS}"
            )
            return

        with self._lock:
            self._triggers.append(config)
            logger.info(
                f"Registered {config.sensor_type} trigger: "
                f"{config.comparison} {config.threshold}"
            )

    def unregister_trigger(self, sensor_type: str) -> None:
        """
        Unregister all triggers for a sensor type.

        Args:
            sensor_type: Type of sensor to unregister ("motion", "light", "temperature")
        """
        with self._lock:
            before_count = len(self._triggers)
            self._triggers = [
                t for t in self._triggers if t.sensor_type != sensor_type
            ]
            removed = before_count - len(self._triggers)
            if removed > 0:
                logger.info(f"Unregistered {removed} {sensor_type} trigger(s)")

    def start(self) -> None:
        """
        Start sensor monitoring.

        Starts a background thread that polls sensors and dispatches callbacks.
        """
        with self._lock:
            if self._running:
                logger.warning("Sensor monitor already running")
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="SensorMonitor"
            )
            self._thread.start()
            logger.info("Sensor monitoring started")

    def stop(self) -> None:
        """
        Stop sensor monitoring.

        Stops the background monitoring thread and cleans up resources.
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        logger.info("Sensor monitoring stopped")

    def get_recent_readings(self, limit: int = 10) -> list[SensorReading]:
        """
        Get recent sensor readings.

        Args:
            limit: Maximum number of readings to return (default 10)

        Returns:
            List of recent SensorReading objects, newest first
        """
        with self._lock:
            readings = list(self._readings)
            return readings[-limit:] if limit < len(readings) else readings

    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running

    def get_trigger_count(self) -> int:
        """Get the number of registered triggers."""
        with self._lock:
            return len(self._triggers)

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _monitor_loop(self) -> None:
        """
        Main monitoring loop.

        Runs in a background thread, polling sensors and dispatching callbacks.
        """
        while self._running:
            try:
                with self._lock:
                    triggers_copy = list(self._triggers)

                for trigger in triggers_copy:
                    reading = self._read_sensor(trigger.sensor_type)
                    if reading and self._check_trigger(trigger, reading):
                        self._dispatch_trigger(trigger, reading)

            except Exception as e:
                logger.error(f"Sensor monitoring error: {e}")

            time.sleep(MONITOR_LOOP_INTERVAL)

    def _read_sensor(self, sensor_type: str) -> SensorReading | None:
        """
        Read current value from sensor.

        Args:
            sensor_type: Type of sensor to read

        Returns:
            SensorReading with current value, or None if read failed
        """
        try:
            if sensor_type == "motion":
                value = self._read_motion_sensor()
            elif sensor_type == "light":
                value = self._read_light_sensor()
            elif sensor_type == "temperature":
                value = self._read_temperature_sensor()
            else:
                logger.warning(f"Unknown sensor type: {sensor_type}")
                return None

            if value is None:
                return None

            return SensorReading(
                sensor_type=sensor_type,
                value=value,
                timestamp=datetime.now(),
                triggered=False,
            )

        except Exception as e:
            logger.debug(f"Error reading {sensor_type} sensor: {e}")
            return None

    def _read_motion_sensor(self) -> float | None:
        """
        Read motion sensor (PIR) via GPIO.

        Returns:
            1.0 if motion detected, 0.0 if no motion, None if unavailable
        """
        try:
            from mothbox_paths import get_hardware_config

            hw_config = get_hardware_config()

            if not hw_config.get("motion_sensor_enabled", False):
                return None

            # Lazy check GPIO availability
            if self._gpio_available is None:
                try:
                    import RPi.GPIO as GPIO  # noqa: F401

                    self._gpio_available = True
                except (ImportError, RuntimeError):
                    self._gpio_available = False
                    logger.warning("GPIO not available for motion sensor")

            if not self._gpio_available:
                return None

            import RPi.GPIO as GPIO

            pin = hw_config.get("motion_sensor_pin", 17)

            # Ensure pin is set up as input
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(pin, GPIO.IN)

            # Read current state
            value = GPIO.input(pin)
            return 1.0 if value else 0.0

        except Exception as e:
            logger.debug(f"Motion sensor read error: {e}")
            return None

    def _read_light_sensor(self) -> float | None:
        """
        Read light sensor via I2C.

        Supports BH1750 and LTR303 sensors based on hardware config.

        Returns:
            Lux value, or None if unavailable
        """
        try:
            from mothbox_paths import get_hardware_config

            hw_config = get_hardware_config()

            if not hw_config.get("light_sensor_enabled", False):
                return None

            # Lazy check I2C availability
            if self._i2c_available is None:
                try:
                    from smbus2 import SMBus  # noqa: F401

                    self._i2c_available = True
                except ImportError:
                    self._i2c_available = False
                    logger.warning("smbus2 not available for I2C sensors")

            if not self._i2c_available:
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

    def _read_temperature_sensor(self) -> float | None:
        """
        Read temperature sensor via I2C.

        Supports TMP102 and MCP9808 sensors based on hardware config.

        Returns:
            Temperature in Celsius, or None if unavailable
        """
        try:
            from mothbox_paths import get_hardware_config

            hw_config = get_hardware_config()

            if not hw_config.get("temperature_sensor_enabled", False):
                return None

            # Lazy check I2C availability
            if self._i2c_available is None:
                try:
                    from smbus2 import SMBus  # noqa: F401

                    self._i2c_available = True
                except ImportError:
                    self._i2c_available = False
                    logger.warning("smbus2 not available for I2C sensors")

            if not self._i2c_available:
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

    def _check_trigger(
        self, trigger: SensorTriggerConfig, reading: SensorReading
    ) -> bool:
        """
        Check if reading triggers the condition.

        Args:
            trigger: Trigger configuration with threshold and comparison
            reading: Current sensor reading

        Returns:
            True if condition is met, False otherwise
        """
        value = reading.value
        threshold = trigger.threshold

        comparisons = {
            "gt": value > threshold,
            "lt": value < threshold,
            "eq": abs(value - threshold) < 0.01,
            "gte": value >= threshold,
            "lte": value <= threshold,
        }

        return comparisons.get(trigger.comparison, False)

    def _dispatch_trigger(
        self, trigger: SensorTriggerConfig, reading: SensorReading
    ) -> None:
        """
        Dispatch trigger callback if cooldown allows.

        Args:
            trigger: Trigger configuration
            reading: Sensor reading that triggered the condition
        """
        now = datetime.now()
        key = f"{trigger.sensor_type}_{trigger.comparison}_{trigger.threshold}"

        with self._lock:
            last_time = self._last_trigger_times.get(key)
            if last_time:
                elapsed_minutes = (now - last_time).total_seconds() / 60
                if elapsed_minutes < trigger.cooldown_minutes:
                    logger.debug(
                        f"Trigger {key} in cooldown "
                        f"({elapsed_minutes:.1f} < {trigger.cooldown_minutes} min)"
                    )
                    return

            # Update last trigger time
            self._last_trigger_times[key] = now
            reading.triggered = True
            self._readings.append(reading)

        # Call trigger callback outside lock to prevent deadlocks
        try:
            trigger.callback(reading)
            logger.info(
                f"Sensor trigger dispatched: {trigger.sensor_type} "
                f"= {reading.value:.2f}"
            )
        except Exception as e:
            logger.error(f"Trigger callback error: {e}")


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_sensor_monitor: SensorMonitor | None = None


def get_sensor_monitor() -> SensorMonitor:
    """
    Get the singleton SensorMonitor instance.

    Returns:
        The shared SensorMonitor instance
    """
    global _sensor_monitor
    if _sensor_monitor is None:
        _sensor_monitor = SensorMonitor()
    return _sensor_monitor


def reset_sensor_monitor() -> None:
    """
    Reset the singleton SensorMonitor instance.

    Primarily for testing purposes.
    """
    global _sensor_monitor
    if _sensor_monitor is not None:
        _sensor_monitor.stop()
    _sensor_monitor = None
