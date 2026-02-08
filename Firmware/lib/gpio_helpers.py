"""
GPIO relay helpers with polarity-aware control and state persistence.

Centralizes relay ON/OFF logic so all scripts use the correct GPIO level
based on the ``relay_active_low`` setting in controls.txt.

Usage::

    from lib.gpio_helpers import setup_relay, relay_on, relay_off

    from mothbox_paths import get_gpio_pins

    pins = get_gpio_pins()

    setup_relay(pins["Relay_Ch1"])
    relay_on(pins["Relay_Ch1"])  # drives to correct level for ON
    relay_off(pins["Relay_Ch1"])  # drives to correct level for OFF
"""

import fcntl
import json
import logging
import sys
from pathlib import Path

# Add parent directory so mothbox_paths is importable when running from any location
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import CONTROLS_FILE, DATA_DIR, get_control_values, get_gpio_pins

logger = logging.getLogger(__name__)

# --- GPIO availability guard (mirrors webui/backend/routes/gpio.py) ----------

GPIO_AVAILABLE = False

try:
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

# --- State file ---------------------------------------------------------------

STATE_FILE = DATA_DIR / "gpio_state.json"


# --- Internal helpers ---------------------------------------------------------


def _pin_to_relay_name(pin: int) -> str:
    """Resolve a BCM pin number to its relay name (e.g. 5 -> 'Relay_Ch1').

    Falls back to the string representation of the pin number if no
    matching relay name is found in the current configuration.
    """
    try:
        pins = get_gpio_pins()
        for name, p in pins.items():
            if p == pin:
                return name
    except Exception:
        pass
    return str(pin)


# --- Polarity helpers ---------------------------------------------------------


def _is_active_low() -> bool:
    """Return True when relays use active-LOW logic (LOW = ON)."""
    try:
        controls = get_control_values(CONTROLS_FILE)
        return controls.get("relay_active_low", "false").lower() == "true"
    except Exception:
        return False  # default: active-HIGH


def get_relay_level(on: bool) -> int:
    """
    Return the GPIO level for the requested relay state.

    Args:
        on: True for relay ON, False for relay OFF.

    Returns:
        ``GPIO.HIGH`` or ``GPIO.LOW`` (1 or 0) accounting for polarity.
    """
    active_low = _is_active_low()
    if on:
        return 0 if active_low else 1  # LOW when active-low, HIGH when active-high
    else:
        return 1 if active_low else 0  # HIGH when active-low, LOW when active-high


# --- State persistence --------------------------------------------------------


def read_gpio_state() -> dict:
    """
    Read ``gpio_state.json`` with a shared file lock.

    Returns:
        dict mapping relay names to bool (True = ON).
        Empty dict if the file is missing or unreadable.
    """
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read gpio_state.json: %s", exc)
        return {}


def write_gpio_state(pin_states: dict) -> None:
    """
    Atomic read-merge-write of ``gpio_state.json`` with an exclusive lock.

    Args:
        pin_states: dict of ``{relay_name: bool}`` entries to merge into
                    the existing state file.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE, "r+") if STATE_FILE.exists() else open(STATE_FILE, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                # Read existing
                existing = {}
                if f.readable() and f.seekable():
                    f.seek(0)
                    content = f.read()
                    if content:
                        existing = json.loads(content)

                # Merge
                existing.update(pin_states)

                # Write
                f.seek(0)
                f.truncate()
                json.dump(existing, f)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        logger.error("Failed to write gpio_state.json: %s", exc)
        raise


# --- Relay control ------------------------------------------------------------


def setup_relay(pin: int) -> None:
    """
    Configure *pin* as a GPIO output with the OFF level.

    Safe to call even when GPIO is unavailable (logs a warning).
    """
    if not GPIO_AVAILABLE:
        logger.warning("GPIO not available — skipping setup_relay(%s)", pin)
        return
    off_level = get_relay_level(on=False)
    GPIO.setup(pin, GPIO.OUT, initial=off_level)


def relay_on(pin: int) -> None:
    """Drive *pin* to the ON level and persist state."""
    if not GPIO_AVAILABLE:
        logger.warning("GPIO not available — skipping relay_on(%s)", pin)
        return
    GPIO.output(pin, get_relay_level(on=True))
    write_gpio_state({_pin_to_relay_name(pin): True})


def relay_off(pin: int) -> None:
    """Drive *pin* to the OFF level and persist state."""
    if not GPIO_AVAILABLE:
        logger.warning("GPIO not available — skipping relay_off(%s)", pin)
        return
    GPIO.output(pin, get_relay_level(on=False))
    write_gpio_state({_pin_to_relay_name(pin): False})
