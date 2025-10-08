"""GPIO control endpoints"""
from flask import Blueprint, jsonify, request
import sys
import json
from pathlib import Path

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import get_gpio_pins

gpio_bp = Blueprint('gpio', __name__)

# Use RPi.GPIO (works on Pi 4 and Pi 5 via rpi-lgpio compatibility layer)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
except (ImportError, RuntimeError) as e:
    GPIO_AVAILABLE = False
    print(f"Warning: RPi.GPIO not available - {e}")

# State file to track GPIO status
STATE_FILE = Path("/tmp/mothbox_gpio_state.json")

def _get_state():
    """Read GPIO state from state file"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default state - all relays off
        return {
            'Relay_Ch1': False,
            'Relay_Ch2': False,
            'Relay_Ch3': False
        }

def _save_state(status):
    """Save GPIO state to state file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(status, f)

@gpio_bp.route('/status', methods=['GET'])
def get_gpio_status():
    """Get current GPIO pin states"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        pins = get_gpio_pins()
        status = {}

        for name, pin in pins.items():
            try:
                # Setup pin as output if not already
                GPIO.setup(pin, GPIO.OUT)
                # Read current state
                state = GPIO.input(pin)
                status[name] = bool(state)
            except Exception as read_error:
                print(f"Error reading {name} (pin {pin}): {read_error}")
                # Fall back to saved state
                saved_status = _get_state()
                status[name] = saved_status.get(name, False)

        return jsonify(status), 200
    except Exception as e:
        import traceback
        print(f"GPIO status error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@gpio_bp.route('/control', methods=['POST'])
def control_gpio():
    """Control GPIO pins using RPi.GPIO"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        data = request.json
        relay = data.get('relay')  # 'Relay_Ch1', 'Relay_Ch2', or 'Relay_Ch3'
        state = data.get('state')  # True (on) or False (off)

        if not relay or state is None:
            return jsonify({'error': 'Missing relay or state parameter'}), 400

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
    """Trigger camera flash momentarily using RPi.GPIO"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        import time
        pins = get_gpio_pins()
        flash_pin = pins['Relay_Ch2']

        print(f"Triggering flash on pin {flash_pin} (100ms pulse)")

        # Setup pin as output
        GPIO.setup(flash_pin, GPIO.OUT)
        # Turn on
        GPIO.output(flash_pin, GPIO.HIGH)
        time.sleep(0.1)  # 100ms
        # Turn off
        GPIO.output(flash_pin, GPIO.LOW)

        print("Flash completed")
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        print(f"Flash trigger error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
