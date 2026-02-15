"""GPIO control endpoints — thin wrappers around gpio_client."""

import logging
import time

from flask import Blueprint, jsonify, request

from lib.gpio_client import read_gpio_state, relay_off, relay_on, setup_relay
from lib.gpio_protocol import GPIODaemonError
from mothbox_paths import CONTROLS_FILE, get_control_values, get_gpio_pins
from webui.backend.lib.error_codes import (
    HARDWARE_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)

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
        return error_response(SERVER_ERROR, "Failed to get GPIO status", 500)


@gpio_bp.route("/control", methods=["POST"])
def control_gpio():
    """Control GPIO pins via daemon."""
    try:
        data = request.json
        relay = data.get("relay")
        state = data.get("state")

        if not relay or state is None:
            return error_response(VALIDATION_ERROR, "Missing relay or state parameter")
        if not isinstance(state, bool):
            return error_response(VALIDATION_ERROR, "State must be a boolean value (true/false)")

        pins = get_gpio_pins()
        if relay not in pins:
            return error_response(VALIDATION_ERROR, f"Invalid relay: {relay}")

        pin = pins[relay]
        logger.info("GPIO control: %s (pin %s) -> %s", relay, pin, state)

        setup_relay(pin)
        if state:
            relay_on(pin)
        else:
            relay_off(pin)

        return jsonify({"success": True, "relay": relay, "state": state})

    except GPIODaemonError:
        logger.exception("GPIO daemon error")
        return error_response(HARDWARE_ERROR, "GPIO daemon not available", 503)
    except Exception:
        logger.exception("GPIO control error")
        return error_response(SERVER_ERROR, "Failed to control GPIO", 500)


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
        try:
            time.sleep(flash_duration_sec)
        finally:
            try:
                relay_off(flash_pin)
            except Exception:
                logger.exception("Failed to turn off flash relay")

        logger.info("Flash completed")
        return jsonify({"success": True})

    except GPIODaemonError:
        logger.exception("GPIO daemon error")
        return error_response(HARDWARE_ERROR, "GPIO daemon not available", 503)
    except Exception:
        logger.exception("Flash trigger error")
        return error_response(SERVER_ERROR, "Failed to trigger flash", 500)
