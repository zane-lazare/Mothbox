"""GPIO control endpoints"""
from flask import Blueprint, jsonify, request
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from mothbox_paths import get_gpio_pins

gpio_bp = Blueprint('gpio', __name__)

# Try to import lgpio (works on Pi 4 and Pi 5)
try:
    import lgpio
    GPIO_AVAILABLE = True
    # Open GPIO chip
    gpio_chip = lgpio.gpiochip_open(0)
except (ImportError, Exception) as e:
    GPIO_AVAILABLE = False
    gpio_chip = None
    print(f"Warning: lgpio not available - {e}")

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
                # Read current state
                state = lgpio.gpio_read(gpio_chip, pin)
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
    """Control GPIO pins using lgpio"""
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

        # Claim pin as output and set state
        try:
            lgpio.gpio_claim_output(gpio_chip, pin)
        except:
            pass  # Pin might already be claimed

        lgpio.gpio_write(gpio_chip, pin, 1 if state else 0)

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
    """Trigger camera flash momentarily using lgpio"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        import time
        pins = get_gpio_pins()
        flash_pin = pins['Relay_Ch2']

        print(f"Triggering flash on pin {flash_pin} (100ms pulse)")

        # Claim pin as output
        try:
            lgpio.gpio_claim_output(gpio_chip, flash_pin)
        except:
            pass  # Pin might already be claimed

        # Turn on
        lgpio.gpio_write(gpio_chip, flash_pin, 1)
        time.sleep(0.1)  # 100ms
        # Turn off
        lgpio.gpio_write(gpio_chip, flash_pin, 0)

        print("Flash completed")
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        print(f"Flash trigger error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
