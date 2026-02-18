# Tests/integration/test_gpio_daemon_integration.py
"""
Integration tests for GPIO daemon IPC.

Starts a real daemon in a background thread (with mocked gpiod) and exercises
the full IPC path via raw Unix socket sends.  Unlike the unit tests, these
tests validate the end-to-end daemon lifecycle including state persistence
across daemon restarts.

Test structure:
- TestDaemonClientRoundtrip: Full IPC roundtrip through raw sockets
- TestStatePersistence: State survives daemon stop → restart
"""

import importlib
import json
import socket
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Raw socket helper
# ---------------------------------------------------------------------------


def _send_raw(sock_path: str, command: str, timeout: float = 2.0) -> str:
    """Send a command string over a raw Unix socket and return the response."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(sock_path)
        s.sendall((command + "\n").encode())
        return s.recv(4096).decode("utf-8", errors="ignore").strip()


# ---------------------------------------------------------------------------
# Mock factory
# ---------------------------------------------------------------------------


def _make_mock_gpiod():
    """Create a mock gpiod v2 module with line constants and request object."""
    mock_module = MagicMock()
    mock_module.line.Value.ACTIVE = 1
    mock_module.line.Value.INACTIVE = 0
    mock_module.line.Direction.OUTPUT = "output"
    mock_module.line.Direction.INPUT = "input"
    mock_module.line.Bias.PULL_UP = "pull_up"
    mock_module.LineSettings = MagicMock

    mock_request = MagicMock()
    mock_request.get_value = MagicMock(return_value=1)  # default: HIGH
    mock_request.set_value = MagicMock()
    mock_module.request_lines = MagicMock(return_value=mock_request)

    return mock_module, mock_request


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_GPIO_PINS = {"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9}
SAMPLE_SWITCH_PINS = {"off_pin": 16, "debug_pin": 12}


def _wait_for_daemon(sock_path: str, retries: int = 60, delay: float = 0.05):
    """Block until the daemon socket is accepting connections."""
    for _ in range(retries):
        if Path(sock_path).exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(sock_path)
                    s.sendall(b"PING\n")
                    resp = s.recv(64)
                    if resp:
                        return
            except (ConnectionRefusedError, OSError):
                pass
        time.sleep(delay)
    raise RuntimeError(f"Daemon did not start within {retries * delay}s")


def _start_daemon(sock_path, state_file):
    """Start a daemon in a background thread. Returns (stop_event, thread, module, mock_request)."""
    mock_gpiod_module, mock_request = _make_mock_gpiod()

    with patch.dict(
        sys.modules,
        {"gpiod": mock_gpiod_module, "gpiod.line": mock_gpiod_module.line},
    ):
        # Force fresh import so module-level gpiod import picks up the mock
        sys.modules.pop("lib.gpio_daemon", None)
        import lib.gpio_daemon as daemon_module

        importlib.reload(daemon_module)

    # Patch daemon internals
    patcher_socket = patch.object(daemon_module, "SOCKET_PATH", str(sock_path))
    patcher_state = patch.object(daemon_module, "STATE_FILE", state_file)
    patcher_gpio = patch.object(
        daemon_module, "_get_gpio_pins", return_value=SAMPLE_GPIO_PINS
    )
    patcher_switch = patch.object(
        daemon_module, "_get_switch_pins", return_value=SAMPLE_SWITCH_PINS
    )
    patcher_active = patch.object(
        daemon_module, "_is_active_low", return_value=False
    )
    patcher_notify = patch.object(daemon_module, "_sd_notify")

    patcher_socket.start()
    patcher_state.start()
    patcher_gpio.start()
    patcher_switch.start()
    patcher_active.start()
    patcher_notify.start()

    stop_event = threading.Event()
    daemon_thread = threading.Thread(
        target=daemon_module.run,
        kwargs={"stop_event": stop_event},
        daemon=True,
    )
    daemon_thread.start()
    _wait_for_daemon(str(sock_path))

    patchers = [
        patcher_socket,
        patcher_state,
        patcher_gpio,
        patcher_switch,
        patcher_active,
        patcher_notify,
    ]
    return stop_event, daemon_thread, daemon_module, mock_request, patchers


def _stop_daemon(stop_event, daemon_thread, patchers):
    """Gracefully stop a daemon thread and clean up patches."""
    stop_event.set()
    daemon_thread.join(timeout=5)
    for p in patchers:
        p.stop()
    sys.modules.pop("lib.gpio_daemon", None)


@pytest.fixture
def running_daemon(tmp_path):
    """Start the daemon in a background thread with mocked gpiod.

    Yields (sock_path, state_file, mock_request).
    """
    sock_path = tmp_path / "gpio.sock"
    state_file = tmp_path / "gpio_state.json"

    stop_event, daemon_thread, _, mock_request, patchers = _start_daemon(
        sock_path, state_file
    )

    yield str(sock_path), state_file, mock_request

    _stop_daemon(stop_event, daemon_thread, patchers)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDaemonClientRoundtrip:
    """Full IPC roundtrip tests through raw Unix sockets."""

    def test_ping_pong(self, running_daemon):
        """PING command returns PONG."""
        sock_path, _, _ = running_daemon
        assert _send_raw(sock_path, "PING") == "PONG"

    def test_set_attract_on_then_get(self, running_daemon):
        """SET attract on, then GET attract returns on."""
        sock_path, _, _ = running_daemon

        resp_set = _send_raw(sock_path, "SET attract on")
        assert resp_set == "OK attract on"

        resp_get = _send_raw(sock_path, "GET attract")
        assert resp_get == "STATE attract on"

    def test_set_flash_on_off_then_get(self, running_daemon):
        """SET flash on, SET flash off, GET flash returns off."""
        sock_path, _, _ = running_daemon

        _send_raw(sock_path, "SET flash on")
        resp = _send_raw(sock_path, "GET flash")
        assert resp == "STATE flash on"

        _send_raw(sock_path, "SET flash off")
        resp = _send_raw(sock_path, "GET flash")
        assert resp == "STATE flash off"

    def test_status_shows_all_relay_states(self, running_daemon):
        """STATUS command reports all relay and switch states."""
        sock_path, _, _ = running_daemon

        # Set some state first
        _send_raw(sock_path, "SET attract on")
        _send_raw(sock_path, "SET flash off")

        resp = _send_raw(sock_path, "STATUS")
        assert resp.startswith("STATUS ")

        # Parse the status line
        pairs = resp[len("STATUS "):].split(",")
        status_map = {}
        for pair in pairs:
            key, val = pair.split("=")
            status_map[key.strip()] = val.strip()

        assert status_map["attract"] == "on"
        assert status_map["flash"] == "off"
        assert status_map["spare"] == "off"
        # Switch pins should also be present
        assert "off_pin" in status_map
        assert "debug_pin" in status_map

    def test_read_switch_pin(self, running_daemon):
        """READ switch pin returns VALUE with high/low."""
        sock_path, _, mock_request = running_daemon

        # Mock the switch pin to return HIGH (1)
        mock_request.get_value.return_value = 1
        resp = _send_raw(sock_path, "READ off_pin")
        assert resp == "VALUE off_pin high"

        # Mock the switch pin to return LOW (0)
        mock_request.get_value.return_value = 0
        resp = _send_raw(sock_path, "READ debug_pin")
        assert resp == "VALUE debug_pin low"

    def test_invalid_command_returns_err(self, running_daemon):
        """Unknown command returns ERR response."""
        sock_path, _, _ = running_daemon

        resp = _send_raw(sock_path, "FROBNICATE")
        assert resp.startswith("ERR")
        assert "FROBNICATE" in resp

        # Daemon should still be responsive after an invalid command
        assert _send_raw(sock_path, "PING") == "PONG"


@pytest.mark.integration
class TestStatePersistence:
    """Daemon persists relay state across restarts."""

    def test_state_survives_restart(self, tmp_path):
        """SET attract on, stop daemon, start new daemon, GET attract returns on."""
        sock_path = tmp_path / "gpio.sock"
        state_file = tmp_path / "gpio_state.json"

        # --- First daemon: set state and stop ---
        stop1, thread1, _, _, patchers1 = _start_daemon(sock_path, state_file)

        resp = _send_raw(str(sock_path), "SET attract on")
        assert resp == "OK attract on"

        # Verify state file was written
        _stop_daemon(stop1, thread1, patchers1)

        assert state_file.exists(), "gpio_state.json should have been written"
        saved = json.loads(state_file.read_text())
        assert saved.get("Relay_Ch1") is True

        # Remove stale socket file (daemon cleanup should have done this, but
        # be defensive in case the thread was killed before cleanup)
        if sock_path.exists():
            sock_path.unlink()

        # --- Second daemon: verify state was restored ---
        stop2, thread2, _, _, patchers2 = _start_daemon(sock_path, state_file)

        resp = _send_raw(str(sock_path), "GET attract")
        assert resp == "STATE attract on", (
            "Relay state should be restored from gpio_state.json after restart"
        )

        # Other relays should still be off
        resp = _send_raw(str(sock_path), "GET flash")
        assert resp == "STATE flash off"

        _stop_daemon(stop2, thread2, patchers2)
