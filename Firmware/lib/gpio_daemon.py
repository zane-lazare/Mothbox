# lib/gpio_daemon.py
"""
GPIO daemon — sole owner of all GPIO lines on Pi 5.

Listens on a Unix socket for IPC commands from gpio_client.py.
Uses gpiod v2 for kernel-supported GPIO access.

Usage:
    python3 lib/gpio_daemon.py          # foreground (development)
    systemctl start mothbox-gpio        # via systemd (production)

IPC Protocol (newline-delimited text over Unix socket):
    SET <name> <on|off>   → OK <name> <on|off>
    GET <name>            → STATE <name> <on|off>
    READ <name>           → VALUE <name> <high|low>
    STATUS                → STATUS attract=on,flash=off,...
    PING                  → PONG
"""

import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import gpiod
    from gpiod.line import Bias, Direction, Value
except ImportError:
    print(
        "ERROR: gpiod v2 not installed. Run: sudo apt install python3-libgpiod",
        file=sys.stderr,
    )
    sys.exit(1)

from lib.gpio_protocol import (
    ACCEPT_TIMEOUT,
    CONN_TIMEOUT,
    LISTEN_BACKLOG,
    MAX_MSG_LENGTH,
    RECV_TOTAL_TIMEOUT,
    SOCKET_PATH,
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

# IPC name → config key mapping
_RELAY_NAMES = {"attract": "Relay_Ch1", "flash": "Relay_Ch2", "spare": "Relay_Ch3"}
_SWITCH_NAMES = {"off_pin", "debug_pin"}


# ---------------------------------------------------------------------------
# Config helpers (module-level for patching in tests)
# ---------------------------------------------------------------------------


def _get_gpio_pins():
    return get_gpio_pins()


def _get_switch_pins():
    return get_switch_pins()


def _is_active_low():
    try:
        controls = get_control_values(CONTROLS_FILE)
        return controls.get("relay_active_low", "false").lower() == "true"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


def _read_state() -> dict:
    """Read gpio_state.json. Returns empty dict if missing/corrupt."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read gpio_state.json: %s", exc)
        return {}


def _write_state(state: dict) -> None:
    """Write gpio_state.json atomically."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    tmp.rename(STATE_FILE)


# ---------------------------------------------------------------------------
# sd_notify (no external package needed)
# ---------------------------------------------------------------------------


def _sd_notify(state_str: str) -> None:
    """Send sd_notify datagram. No-op outside systemd."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr[0] == "@":
        addr = "\0" + addr[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.sendto(state_str.encode(), addr)


# ---------------------------------------------------------------------------
# GPIO level helper
# ---------------------------------------------------------------------------


def _level_for(on: bool, active_low: bool):
    """Return gpiod Value for the requested relay state."""
    if on:
        return Value.INACTIVE if active_low else Value.ACTIVE
    else:
        return Value.ACTIVE if active_low else Value.INACTIVE


# ---------------------------------------------------------------------------
# Daemon core
# ---------------------------------------------------------------------------


def run(stop_event: threading.Event | None = None):
    """Main daemon loop.

    Args:
        stop_event: Optional threading.Event for graceful shutdown in tests.
                    If None, daemon runs until SIGTERM/SIGINT.
    """
    if stop_event is None:
        stop_event = threading.Event()

    # --- Config ---
    gpio_pins = _get_gpio_pins()
    switch_pins = _get_switch_pins()
    active_low = _is_active_low()

    # Build pin → IPC name mapping
    pin_to_ipc = {}
    for ipc_name, config_key in _RELAY_NAMES.items():
        if config_key in gpio_pins:
            pin_to_ipc[gpio_pins[config_key]] = ipc_name
    for name in _SWITCH_NAMES:
        if name in switch_pins:
            pin_to_ipc[switch_pins[name]] = name

    ipc_to_pin = {v: k for k, v in pin_to_ipc.items()}

    # --- Restore state ---
    saved_state = _read_state()
    relay_state = {}  # IPC name → bool
    for ipc_name, config_key in _RELAY_NAMES.items():
        relay_state[ipc_name] = saved_state.get(config_key, False)

    # --- Claim GPIO lines via gpiod v2 ---
    line_config = {}

    for ipc_name, config_key in _RELAY_NAMES.items():
        if config_key in gpio_pins:
            pin = gpio_pins[config_key]
            line_config[pin] = gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=_level_for(relay_state[ipc_name], active_low),
            )

    for name in _SWITCH_NAMES:
        if name in switch_pins:
            pin = switch_pins[name]
            line_config[pin] = gpiod.LineSettings(
                direction=Direction.INPUT,
                bias=Bias.PULL_UP,
            )

    gpio_request = gpiod.request_lines(
        "/dev/gpiochip0",
        consumer="mothbox-gpio",
        config=line_config,
    )

    all_pins = list(line_config.keys())
    logger.info("GPIO daemon ready, owning lines %s", all_pins)

    # --- Bind socket ---
    sock_dir = Path(SOCKET_PATH).parent
    sock_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale socket
    sock_path = Path(SOCKET_PATH)
    if sock_path.exists():
        sock_path.unlink()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    os.chmod(str(sock_path), 0o660)  # nosec B103 — restrict socket to owner+group
    server.listen(LISTEN_BACKLOG)
    server.settimeout(ACCEPT_TIMEOUT)  # allow periodic stop_event checks

    _sd_notify("READY=1")

    # --- Health tracking ---
    started_at = time.time()
    last_command_at = None  # updated to time.time() on each command

    # --- Helper: persist relay state ---
    def _persist():
        state = {}
        for ipc_name, config_key in _RELAY_NAMES.items():
            state[config_key] = relay_state[ipc_name]
        _write_state(state)

    # --- Signal handlers (only in main thread) ---
    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down", signum)
        stop_event.set()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

    # --- Command handler ---
    def _handle_command(cmd: str) -> str:
        nonlocal last_command_at
        parts = cmd.strip().split()
        if not parts:
            return "ERR empty command"

        verb = parts[0].upper()

        if verb == "PING":
            last_command_at = time.time()
            return "PONG"

        elif verb == "HEALTH":
            uptime = time.time() - started_at
            lines_count = len(all_pins)
            if last_command_at is not None:
                last_cmd_iso = datetime.fromtimestamp(
                    last_command_at, tz=UTC
                ).isoformat()
            else:
                last_cmd_iso = "never"
            last_command_at = time.time()
            return f"HEALTH uptime={uptime:.1f} lines={lines_count} last_cmd={last_cmd_iso}"

        elif verb == "SET" and len(parts) == 3:
            name, value = parts[1], parts[2].lower()
            if name not in _RELAY_NAMES:
                return f"ERR unknown relay '{name}'"
            if value not in ("on", "off"):
                return f"ERR invalid value '{value}' (must be on|off)"

            on = value == "on"
            pin = ipc_to_pin[name]
            gpio_request.set_value(pin, _level_for(on, active_low))
            relay_state[name] = on
            _persist()
            last_command_at = time.time()
            return f"OK {name} {value}"

        elif verb == "GET" and len(parts) == 2:
            name = parts[1]
            if name not in _RELAY_NAMES:
                return f"ERR unknown relay '{name}'"
            value = "on" if relay_state[name] else "off"
            last_command_at = time.time()
            return f"STATE {name} {value}"

        elif verb == "READ" and len(parts) == 2:
            name = parts[1]
            if name not in _SWITCH_NAMES:
                return f"ERR unknown switch '{name}'"
            pin = ipc_to_pin[name]
            raw = gpio_request.get_value(pin)
            level = "low" if raw == 0 else "high"
            last_command_at = time.time()
            return f"VALUE {name} {level}"

        elif verb == "STATUS":
            pairs = []
            for ipc_name in _RELAY_NAMES:
                v = "on" if relay_state[ipc_name] else "off"
                pairs.append(f"{ipc_name}={v}")
            for name in sorted(_SWITCH_NAMES):
                if name in ipc_to_pin:
                    pin = ipc_to_pin[name]
                    raw = gpio_request.get_value(pin)
                    level = "low" if raw == 0 else "high"
                    pairs.append(f"{name}={level}")
            last_command_at = time.time()
            return "STATUS " + ",".join(pairs)

        else:
            return f"ERR unknown command '{cmd.strip()}'"

    # --- Bounded recv helper ---
    def _recv_line(conn):
        """Read one newline-terminated message, up to MAX_MSG_LENGTH bytes.

        Enforces a wall-clock total timeout (RECV_TOTAL_TIMEOUT) to prevent
        slow-drip clients from blocking the accept loop.
        """
        buf = b""
        deadline = time.monotonic() + RECV_TOTAL_TIMEOUT
        while len(buf) < MAX_MSG_LENGTH:
            if time.monotonic() > deadline:
                logger.warning("recv_line wall-clock timeout after %.1fs", RECV_TOTAL_TIMEOUT)
                break
            chunk = conn.recv(1)
            if not chunk:
                break
            buf += chunk
            if chunk == b"\n":
                break
        return buf.decode("utf-8", errors="ignore").strip()

    # --- Main loop ---
    watchdog_interval = 15  # seconds (must be < WatchdogSec/2)
    last_watchdog = time.monotonic()

    try:
        while not stop_event.is_set():
            # Periodically notify systemd watchdog
            now = time.monotonic()
            if now - last_watchdog >= watchdog_interval:
                _sd_notify("WATCHDOG=1")
                last_watchdog = now

            try:
                conn, _ = server.accept()
            except TimeoutError:
                continue
            except OSError:
                if stop_event.is_set():
                    break
                raise

            try:
                conn.settimeout(CONN_TIMEOUT)
                data = _recv_line(conn)
                response = _handle_command(data) if data else "OK"
                conn.sendall((response + "\n").encode())
            except Exception as exc:
                logger.warning("Error handling client: %s", exc)
                try:
                    conn.sendall(f"ERR internal: {exc}\n".encode())
                except OSError:
                    logger.debug("Failed to send error response to client")
            finally:
                conn.close()

    finally:
        # Cleanup
        logger.info("Saving relay state and releasing GPIO lines")
        _persist()
        gpio_request.release()
        server.close()
        if sock_path.exists():
            sock_path.unlink()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run()
