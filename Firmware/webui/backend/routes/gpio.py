"""GPIO control endpoints"""
from flask import Blueprint, jsonify, request
import sys
import json
import fcntl
from pathlib import Path

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import get_gpio_pins, MOTHBOX_HOME, CONFIG_DIR, CONTROLS_FILE, DATA_DIR

# Startup diagnostics
pins = get_gpio_pins()
print(f"GPIO initialized - Pins: {pins}, Controls: {CONTROLS_FILE.exists()}")

gpio_bp = Blueprint('gpio', __name__)

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
    print(f"Warning: RPi.GPIO not available - {e}")

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
        test_pin = pins.get('Relay_Ch1', 26)  # Fallback to 26 if not found

        # Try to setup the pin - this will fail with PermissionError if user lacks gpio access
        # Use LOW to avoid unintended activation
        GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)

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
                print(f"Warning: GPIO cleanup failed for pin {test_pin}: {e}")

# Validate GPIO permissions on startup
GPIO_PERMISSIONS_OK, GPIO_PERMISSION_ERROR = _validate_gpio_permissions()

if GPIO_AVAILABLE and not GPIO_PERMISSIONS_OK:
    print("=" * 60)
    print("⚠️  GPIO PERMISSION WARNING")
    print("=" * 60)
    print(GPIO_PERMISSION_ERROR)
    print("=" * 60)
elif GPIO_AVAILABLE and GPIO_PERMISSIONS_OK:
    print(f"✓ GPIO permissions validated successfully")

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
            with open(STATE_FILE, 'r') as f:
                # Acquire shared lock for reading (allows multiple readers)
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to read GPIO state file: {e}")
            # Return default state on error
            return {
                'Relay_Ch1': False,
                'Relay_Ch2': False,
                'Relay_Ch3': False
            }
    else:
        # Default state - all relays off
        return {
            'Relay_Ch1': False,
            'Relay_Ch2': False,
            'Relay_Ch3': False
        }

def _save_state(status):
    """
    Save GPIO state to state file with file locking to prevent race conditions.

    Uses exclusive lock (LOCK_EX) to ensure atomic write operations and prevent
    concurrent writes from overwriting each other's changes.

    Args:
        status (dict): GPIO state dictionary to save
    """
    try:
        # Create parent directory if it doesn't exist
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Open in write mode and acquire exclusive lock
        with open(STATE_FILE, 'w') as f:
            # Acquire exclusive lock for writing (blocks all other access)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(status, f)
                f.flush()  # Ensure data is written to disk
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        print(f"Error: Failed to save GPIO state file: {e}")

@gpio_bp.route('/status', methods=['GET'])
def get_gpio_status():
    """Get current GPIO pin states"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify({
                'error': 'GPIO permission denied',
                'details': GPIO_PERMISSION_ERROR
            }), 403

        # Use saved state file rather than reading GPIO pins
        # Reading OUTPUT pins can be unreliable and may reset their state
        status = _get_state()

        # Ensure all relays are present in response
        pins = get_gpio_pins()
        for name in pins.keys():
            if name not in status:
                status[name] = False

        return jsonify(status), 200
    except Exception as e:
        import traceback
        print(f"GPIO status error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@gpio_bp.route('/control', methods=['POST'])
def control_gpio():
    """Control GPIO pins using RPi.GPIO (rate limited to prevent hardware abuse)"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify({
                'error': 'GPIO permission denied',
                'details': GPIO_PERMISSION_ERROR
            }), 403

        data = request.json
        relay = data.get('relay')  # 'Relay_Ch1', 'Relay_Ch2', or 'Relay_Ch3'
        state = data.get('state')  # True (on) or False (off)

        if not relay or state is None:
            return jsonify({'error': 'Missing relay or state parameter'}), 400

        if not isinstance(state, bool):
            return jsonify({'error': 'State must be a boolean value (true/false)'}), 400

        pins = get_gpio_pins()
        if relay not in pins:
            return jsonify({'error': f'Invalid relay: {relay}'}), 400

        pin = pins[relay]
        print(f"GPIO control: {relay} (pin {pin}) -> {state}")

        # Setup pin as output
        GPIO.setup(pin, GPIO.OUT)
        # Set state (HIGH=1/True, LOW=0/False)
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

        # Update state file
        status = _get_state()
        status[relay] = state
        _save_state(status)

        return jsonify({'success': True, 'relay': relay, 'state': state})
    except Exception as e:
        import traceback
        print(f"GPIO control error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@gpio_bp.route('/flash', methods=['POST'])
def trigger_flash():
    """Trigger camera flash momentarily using RPi.GPIO (rate limited to prevent hardware abuse)"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        if not GPIO_PERMISSIONS_OK:
            return jsonify({
                'error': 'GPIO permission denied',
                'details': GPIO_PERMISSION_ERROR
            }), 403

        import time
        pins = get_gpio_pins()
        flash_pin = pins['Relay_Ch2']

        # Get configurable flash duration from controls.txt (default: 100ms)
        from mothbox_paths import CONTROLS_FILE, get_control_values
        controls = get_control_values(CONTROLS_FILE)
        flash_duration_ms = int(controls.get('flash_duration_ms', 100))
        flash_duration_sec = flash_duration_ms / 1000.0

        print(f"Triggering flash on pin {flash_pin} ({flash_duration_ms}ms pulse)")

        # Setup pin as output
        GPIO.setup(flash_pin, GPIO.OUT)
        # Turn on
        GPIO.output(flash_pin, GPIO.HIGH)
        time.sleep(flash_duration_sec)
        # Turn off
        GPIO.output(flash_pin, GPIO.LOW)

        print("Flash completed")
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        print(f"Flash trigger error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
