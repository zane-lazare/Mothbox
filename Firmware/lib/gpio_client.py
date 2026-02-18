"""
GPIO daemon client — drop-in replacement for gpio_helpers.py.

Same public API, socket backend. Mutations raise GPIODaemonError on failure.
Queries (read_gpio_state) fall back to gpio_state.json if daemon unreachable.

Usage::

    from lib.gpio_client import setup_relay, relay_on, relay_off, read_switch

    setup_relay(5)  # no-op — daemon owns setup
    relay_on(5)  # sends SET attract on to daemon
    relay_off(5)  # sends SET attract off to daemon

    if read_switch(16):  # sends READ off_pin to daemon
        print("OFF switch is grounded")
"""

import json
import logging
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.gpio_protocol import (
    RECV_BUFFER_SIZE,
    SOCKET_PATH,
    SOCKET_TIMEOUT,
    GPIODaemonError,
)
from mothbox_paths import (
    CONTROLS_FILE,
    DATA_DIR,
    get_control_values,
    get_gpio_pins,
    get_switch_pins,
)

logger = logging.getLogger(__name__)

STATE_FILE = DATA_DIR / "gpio_state.json"

# IPC name mapping: Relay config key → IPC name
_RELAY_TO_IPC = {"Relay_Ch1": "attract", "Relay_Ch2": "flash", "Relay_Ch3": "spare"}
_IPC_TO_RELAY = {v: k for k, v in _RELAY_TO_IPC.items()}


def _pin_to_relay_name(pin: int) -> str:
    """Resolve BCM pin number to relay name (e.g. 5 -> 'Relay_Ch1').
    Falls back to str(pin) if no match found.
    """
    try:
        pins = get_gpio_pins()
        for name, p in pins.items():
            if p == pin:
                return name
    except Exception:
        pass
    return str(pin)


def _pin_to_ipc_name(pin: int) -> str:
    """Map BCM pin number to IPC name (e.g. 5 -> 'attract', 16 -> 'off_pin').
    Raises GPIODaemonError if pin is not in the current configuration.
    """
    try:
        pins = get_gpio_pins()
        for name, p in pins.items():
            if p == pin and name in _RELAY_TO_IPC:
                return _RELAY_TO_IPC[name]
    except Exception:
        pass

    try:
        switch_pins = get_switch_pins()
        for name, p in switch_pins.items():
            if p == pin:
                return name
    except Exception:
        pass

    raise GPIODaemonError(f"Unknown pin {pin} — not in relay or switch config")


def _is_active_low() -> bool:
    """Return True when relays use active-LOW logic (LOW = ON)."""
    try:
        controls = get_control_values(CONTROLS_FILE)
        return controls.get("relay_active_low", "false").lower() == "true"
    except Exception:
        return False


def _send_command(command: str) -> str:
    """Send a command to the GPIO daemon and return the response line.
    Raises GPIODaemonError on connection failure, timeout, or ERR response.
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect(SOCKET_PATH)
            sock.sendall((command + "\n").encode())
            response = sock.recv(RECV_BUFFER_SIZE).decode("utf-8", errors="ignore").strip()
    except ConnectionRefusedError:
        raise GPIODaemonError(f"GPIO daemon not running at {SOCKET_PATH}") from None
    except TimeoutError:
        raise GPIODaemonError(f"GPIO daemon not responding within {SOCKET_TIMEOUT}s") from None
    except OSError as exc:
        raise GPIODaemonError(f"GPIO daemon connection failed: {exc}") from None

    if response.startswith("ERR "):
        raise GPIODaemonError(response[4:])

    return response


def health():
    """Query daemon health status.

    Returns:
        dict with reachable, uptime_seconds, managed_lines, last_command_at

    Raises:
        GPIODaemonError: if daemon is unreachable or returns ERR
    """
    response = _send_command("HEALTH")
    result = {"reachable": True}
    for part in response.split():
        if "=" in part:
            key, value = part.split("=", 1)
            if key == "uptime":
                result["uptime_seconds"] = float(value)
            elif key == "lines":
                result["managed_lines"] = int(value)
            elif key == "last_cmd":
                result["last_command_at"] = value
            elif key == "commands":
                result["total_commands"] = int(value)
            elif key == "errors":
                result["total_errors"] = int(value)
            elif key == "memory_kb":
                result["memory_kb"] = int(value)
    return result


def setup_relay(pin: int) -> None:
    """No-op. Daemon owns GPIO setup. Kept for API compatibility."""


def relay_on(pin: int) -> None:
    """Send SET <name> on to daemon.
    Raises GPIODaemonError if daemon is unreachable or returns error.
    """
    name = _pin_to_ipc_name(pin)
    _send_command(f"SET {name} on")
    logger.info("relay_on(%s) [%s] — OK", pin, name)


def relay_off(pin: int) -> None:
    """Send SET <name> off to daemon.
    Raises GPIODaemonError if daemon is unreachable or returns error.
    """
    name = _pin_to_ipc_name(pin)
    _send_command(f"SET {name} off")
    logger.info("relay_off(%s) [%s] — OK", pin, name)


def get_relay_level(on: bool) -> int:
    """Return GPIO level for requested relay state.
    Pure logic — no daemon call. Reads relay_active_low from controls.txt.
    """
    active_low = _is_active_low()
    if on:
        return 0 if active_low else 1
    else:
        return 1 if active_low else 0


def read_gpio_state() -> dict:
    """Query daemon for all relay states. Falls back to gpio_state.json.
    Returns dict mapping relay names to bool (True = ON).
    Empty dict if both daemon and file unavailable.
    """
    try:
        response = _send_command("STATUS")
        if response.startswith("STATUS "):
            state = {}
            for pair in response[7:].split(","):
                name, value = pair.split("=")
                name = name.strip()
                if name in _IPC_TO_RELAY:
                    state[_IPC_TO_RELAY[name]] = value.strip() == "on"
            return state
    except GPIODaemonError:
        logger.warning("Daemon unreachable, falling back to gpio_state.json")

    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read gpio_state.json: %s", exc)
    return {}


def write_gpio_state(pin_states: dict) -> None:
    """Send SET commands for each entry in pin_states.
    Raises GPIODaemonError if daemon unreachable.
    """
    for relay_name, on in pin_states.items():
        if relay_name in _RELAY_TO_IPC:
            ipc_name = _RELAY_TO_IPC[relay_name]
            _send_command(f"SET {ipc_name} {'on' if on else 'off'}")


def read_switch(pin: int) -> bool:
    """Read switch pin state via daemon.
    Returns True if pin is LOW (grounded / switch activated).
    Raises GPIODaemonError if daemon unreachable.
    """
    name = _pin_to_ipc_name(pin)
    response = _send_command(f"READ {name}")
    if response.startswith("VALUE "):
        parts = response.split()
        if len(parts) >= 3:
            return parts[2] == "low"
    raise GPIODaemonError(f"Unexpected READ response: {response}")
