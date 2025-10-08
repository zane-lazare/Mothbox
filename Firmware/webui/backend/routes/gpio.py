"""GPIO control endpoints"""
from flask import Blueprint, jsonify, request
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from mothbox_paths import get_gpio_pins

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

gpio_bp = Blueprint('gpio', __name__)

@gpio_bp.route('/status', methods=['GET'])
def get_gpio_status():
    """Get current GPIO pin states"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        pins = get_gpio_pins()
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)  # Suppress warnings about pins already in use

        status = {}
        for name, pin in pins.items():
            # Only setup if not already configured
            try:
                GPIO.setup(pin, GPIO.OUT)
            except Exception as setup_error:
                print(f"GPIO setup error for {name} (pin {pin}): {setup_error}")

            try:
                status[name] = bool(GPIO.input(pin))
            except Exception as read_error:
                print(f"GPIO read error for {name} (pin {pin}): {read_error}")
                status[name] = False

        return jsonify(status), 200
    except Exception as e:
        import traceback
        print(f"GPIO status error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@gpio_bp.route('/control', methods=['POST'])
def control_gpio():
    """Control GPIO pins (attract lights, flash, UV)"""
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
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

        return jsonify({'success': True, 'relay': relay, 'state': state})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gpio_bp.route('/flash', methods=['POST'])
def trigger_flash():
    """Trigger camera flash momentarily"""
    try:
        if not GPIO_AVAILABLE:
            return jsonify({'error': 'GPIO not available'}), 500

        import time
        pins = get_gpio_pins()
        flash_pin = pins['Relay_Ch2']

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(flash_pin, GPIO.OUT)
        GPIO.output(flash_pin, GPIO.HIGH)
        time.sleep(0.1)  # Flash for 100ms
        GPIO.output(flash_pin, GPIO.LOW)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
