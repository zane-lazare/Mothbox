"""GPIO control endpoints — thin wrappers around gpio_client."""

import logging
import time

from flask import Blueprint, jsonify, request

from lib.gpio_client import read_gpio_state, relay_off, relay_on, setup_relay
from lib.gpio_protocol import GPIODaemonError
from mothbox_paths import CONTROLS_FILE, get_control_values, get_gpio_pins

logger = logging.getLogger(__name__)

gpio_bp = Blueprint("gpio", __name__)


@gpio_bp.route("/status", methods=["GET"])
def get_gpio_status():
    """Get current GPIO pin states."""
    try:
        status = read_gpio_state()
        # Ensure all relays present in response
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
    """Control GPIO pins via daemon."""
    try:
        data = request.json
        relay = data.get("relay")
        state = data.get("state")

        if not relay or state is None:
            return jsonify({"error": "Missing relay or state parameter"}), 400
        if not isinstance(state, bool):
            return jsonify({"error": "State must be a boolean value (true/false)"}), 400

        pins = get_gpio_pins()
        if relay not in pins:
            return jsonify({"error": f"Invalid relay: {relay}"}), 400

        pin = pins[relay]
        logger.info("GPIO control: %s (pin %s) -> %s", relay, pin, state)

        setup_relay(pin)
        if state:
            relay_on(pin)
        else:
            relay_off(pin)

        return jsonify({"success": True, "relay": relay, "state": state})

    except GPIODaemonError as exc:
        logger.warning("GPIO daemon error: %s", exc)
        return jsonify({"error": "GPIO daemon not available", "details": str(exc)}), 503
    except Exception:
        logger.exception("GPIO control error")
        return jsonify({"error": "Failed to control GPIO"}), 500


@gpio_bp.route("/flash", methods=["POST"])
def trigger_flash():
    """Trigger camera flash momentarily via daemon."""
    try:
        pins = get_gpio_pins()
        flash_pin = pins["Relay_Ch2"]

        controls = get_control_values(CONTROLS_FILE)
        flash_duration_ms = int(controls.get("flash_duration_ms", 100))
        flash_duration_sec = flash_duration_ms / 1000.0

        logger.info("Triggering flash on pin %s (%sms pulse)", flash_pin, flash_duration_ms)

        setup_relay(flash_pin)
        relay_on(flash_pin)
        time.sleep(flash_duration_sec)
        relay_off(flash_pin)

        logger.info("Flash completed")
        return jsonify({"success": True})

    except GPIODaemonError as exc:
        logger.warning("GPIO daemon error: %s", exc)
        return jsonify({"error": "GPIO daemon not available", "details": str(exc)}), 503
    except Exception:
        logger.exception("Flash trigger error")
        return jsonify({"error": "Failed to trigger flash"}), 500
