"""GPIO control endpoints"""

import fcntl
import json
import logging

# Setup path to import mothbox_paths
from flask import Blueprint, jsonify, request

from lib.gpio_helpers import relay_off, relay_on, setup_relay
from mothbox_paths import CONTROLS_FILE, DATA_DIR, get_gpio_pins

logger = logging.getLogger(__name__)

# Startup diagnostics
pins = get_gpio_pins()
logger.info(f"GPIO initialized - Pins: {pins}, Controls: {CONTROLS_FILE.exists()}")

gpio_bp = Blueprint("gpio", __name__)

# Use RPi.GPIO (works on Pi 4 and Pi 5 via rpi-lgpio compatibility layer)
GPIO_AVAILABLE = False
GPIO_PERMISSION_ERROR = None

try:
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    GPIO_AVAILABLE = False
    GPIO_PERMISSION_ERROR = f"RPi.GPIO import failed: {e}"
    logger.warning("RPi.GPIO not available - GPIO hardware features disabled")
    logger.warning(f"Reason: {e}")
    logger.warning("Impact: GPIO controls and flash trigger will not function")
    if isinstance(e, PermissionError):
        logger.warning("Hint: User may need to be in 'gpio' group: sudo usermod -a -G gpio $USER")
    elif isinstance(e, ImportError):
        logger.warning("Hint: Install system package: sudo apt-get install python3-rpi-lgpio")


def _validate_gpio_permissions():
    """
    Validate that we have actual GPIO access by testing setup on a pin.

    This catches permission issues that occur when:
    - User was added to gpio group but hasn't logged out/in
    - Service started before group membership became active
    - User lacks GPIO permissions

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    if not GPIO_AVAILABLE:
        return False, GPIO_PERMISSION_ERROR

    test_pin = None
    try:
        # Test GPIO access on a safe pin that we're likely to use
        # Use the first relay pin from config
        pins = get_gpio_pins()
        test_pin = pins.get("Relay_Ch1", 26)  # Fallback to 26 if not found

        # Try to setup the pin - this will fail with PermissionError if user lacks gpio access
        # Use LOW to avoid unintended activation
        GPIO.setup(test_pin, GPIO.IN)
        GPIO.input(test_pin)  # Read to verify access

        # If we got here, permissions are OK
        return True, None

    except PermissionError as e:
        error_msg = (
            f"Permission denied accessing GPIO pins: {e}. "
            "The user may not be in the 'gpio' group or group membership hasn't taken effect yet. "
            "Try: sudo systemctl restart mothbox-webui.service (or log out and back in)"
        )
        return False, error_msg
    except Exception as e:
        error_msg = f"GPIO validation failed: {e}"
        return False, error_msg
    finally:
        # Cleanup: Restore pin to input mode to avoid side effects
        if test_pin is not None:
            try:
                GPIO.cleanup(test_pin)
            except Exception as e:
                # Don't fail validation if cleanup fails
                logger.warning(f"GPIO cleanup failed for pin {test_pin}: {e}")


# Validate GPIO permissions on startup
GPIO_PERMISSIONS_OK, GPIO_PERMISSION_ERROR = _validate_gpio_permissions()

if GPIO_AVAILABLE and not GPIO_PERMISSIONS_OK:
    logger.warning("=" * 60)
    logger.warning("GPIO PERMISSION WARNING")
    logger.warning("=" * 60)
    logger.warning(GPIO_PERMISSION_ERROR)
    logger.warning("=" * 60)
elif GPIO_AVAILABLE and GPIO_PERMISSIONS_OK:
    logger.info("GPIO permissions validated successfully")

# State file to track GPIO status
# Use DATA_DIR for persistent, properly-permissioned storage (not /tmp)
STATE_FILE = DATA_DIR / "gpio_state.json"


def _get_state():
    """
    Read GPIO state from state file with file locking to prevent race conditions.

    Uses shared lock (LOCK_SH) to allow multiple concurrent reads but prevent
    reads during writes.

    Returns:
        dict: GPIO state dictionary with relay states
    """
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                # Acquire shared lock for reading (allows multiple readers)
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read GPIO state file: {e}")
            # Return default state on error
            return {"Relay_Ch1": False, "Relay_Ch2": False, "Relay_Ch3": False}
    else:
        # Default state - all relays off
        return {"Relay_Ch1": False, "Relay_Ch2": False, "Relay_Ch3": False}


def _save_state(status):
    """
    Save GPIO state to state file with file locking to prevent race conditions.

    Uses exclusive lock (LOCK_EX) to ensure atomic write operations and prevent
    concurrent writes from overwriting each other's changes.

    Args:
        status (dict): GPIO state dictionary to save

    Raises:
        IOError: If state file cannot be written (disk full, permissions, etc.)
    """
    try:
        # Create parent directory if it doesn't exist
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Open in write mode and acquire exclusive lock
        with open(STATE_FILE, "w") as f:
            # Acquire exclusive lock for writing (blocks all other access)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(status, f)
                f.flush()  # Ensure data is written to disk
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        logger.error(f"Failed to save GPIO state file: {e}")
        # Propagate error - state file persistence is critical for data integrity
        raise


@gpio_bp.route("/status", methods=["GET"])
def get_gpio_status():
    """Get current GPIO pin states"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({"error": "GPIO not available"}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify(
                {"error": "GPIO permission denied", "details": GPIO_PERMISSION_ERROR}
            ), 403

        # Use saved state file rather than reading GPIO pins
        # Reading OUTPUT pins can be unreliable and may reset their state
        status = _get_state()

        # Ensure all relays are present in response
        pins = get_gpio_pins()
        for name in pins:
            if name not in status:
                status[name] = False

        return jsonify(status), 200
    except Exception:
        logger.exception("GPIO status error")
        return jsonify({"error": "Failed to get GPIO status"}), 500


@gpio_bp.route("/control", methods=["POST"])
def control_gpio():
    """Control GPIO pins using RPi.GPIO (rate limited to prevent hardware abuse)"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({"error": "GPIO not available"}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify(
                {"error": "GPIO permission denied", "details": GPIO_PERMISSION_ERROR}
            ), 403

        data = request.json
        relay = data.get("relay")  # 'Relay_Ch1', 'Relay_Ch2', or 'Relay_Ch3'
        state = data.get("state")  # True (on) or False (off)

        if not relay or state is None:
            return jsonify({"error": "Missing relay or state parameter"}), 400

        if not isinstance(state, bool):
            return jsonify({"error": "State must be a boolean value (true/false)"}), 400

        pins = get_gpio_pins()
        if relay not in pins:
            return jsonify({"error": f"Invalid relay: {relay}"}), 400

        pin = pins[relay]
        logger.info(f"GPIO control: {relay} (pin {pin}) -> {state}")

        setup_relay(pin)
        if state:
            relay_on(pin)
        else:
            relay_off(pin)

        return jsonify({"success": True, "relay": relay, "state": state})
    except Exception:
        logger.exception("GPIO control error")
        return jsonify({"error": "Failed to control GPIO"}), 500


@gpio_bp.route("/flash", methods=["POST"])
def trigger_flash():
    """Trigger camera flash momentarily using RPi.GPIO (rate limited to prevent hardware abuse)"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({"error": "GPIO not available"}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify(
                {"error": "GPIO permission denied", "details": GPIO_PERMISSION_ERROR}
            ), 403

        import time

        pins = get_gpio_pins()
        flash_pin = pins["Relay_Ch2"]

        # Get configurable flash duration from controls.txt (default: 100ms)
        from mothbox_paths import CONTROLS_FILE, get_control_values

        controls = get_control_values(CONTROLS_FILE)
        flash_duration_ms = int(controls.get("flash_duration_ms", 100))
        flash_duration_sec = flash_duration_ms / 1000.0

        logger.info(f"Triggering flash on pin {flash_pin} ({flash_duration_ms}ms pulse)")

        setup_relay(flash_pin)
        relay_on(flash_pin)
        time.sleep(flash_duration_sec)
        relay_off(flash_pin)

        logger.info("Flash completed")
        return jsonify({"success": True})
    except Exception:
        logger.exception("Flash trigger error")
        return jsonify({"error": "Failed to trigger flash"}), 500
