# Tests/unit/test_gpio_daemon.py
"""
Unit tests for lib/gpio_daemon.py — GPIO daemon.

Tests the daemon with mocked gpiod and a real Unix socket in a temp directory.
The daemon runs in a background thread for each test.

Test structure:
- TestDaemonPing: PING health check
- TestSetCommand: relay control via IPC
- TestGetCommand: relay state query
- TestStatusCommand: all-pin status dump
- TestReadCommand: switch pin reads
- TestStateRestore: state restoration on startup
"""

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
# Helper: talk to daemon
# ---------------------------------------------------------------------------


def send_to_daemon(sock_path: str, command: str, timeout: float = 2.0) -> str:
    """Send a command to the daemon and return the response."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(sock_path)
        s.sendall((command + "\n").encode())
        return s.recv(4096).decode().strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def daemon_env(tmp_path):
    """Set up a temp environment for the daemon: socket path, state file, config."""
    sock_path = str(tmp_path / "gpio.sock")
    state_file = tmp_path / "gpio_state.json"
    return {
        "sock_path": sock_path,
        "state_file": state_file,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def mock_gpiod():
    """Mock gpiod v2 module."""
    mock = MagicMock()
    # Mock line values
    mock.line.Value.ACTIVE = 1
    mock.line.Value.INACTIVE = 0
    mock.line.Direction.OUTPUT = "output"
    mock.line.Direction.INPUT = "input"
    mock.line.Bias.PULL_UP = "pull_up"

    # Mock LineSettings
    mock.LineSettings = MagicMock

    # Mock request_lines to return a mock request object
    mock_request = MagicMock()
    mock_request.get_value = MagicMock(return_value=1)  # default: HIGH
    mock_request.set_value = MagicMock()
    mock.request_lines = MagicMock(return_value=mock_request)

    return mock, mock_request


@pytest.fixture
def sample_pins():
    """Standard 5.x pin configuration patches."""
    gpio_pins = {"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9}
    switch_pins = {"off_pin": 16, "debug_pin": 12}
    return gpio_pins, switch_pins


@pytest.fixture
def running_daemon(daemon_env, mock_gpiod, sample_pins):
    """Start the daemon in a background thread with mocked gpiod.

    Yields (sock_path, state_file, mock_request) and stops daemon on teardown.
    """
    mock_gpiod_module, mock_request = mock_gpiod
    gpio_pins, switch_pins = sample_pins

    # Import daemon module with mocked gpiod
    # Must also mock gpiod.line so "from gpiod.line import ..." works
    with patch.dict(
        sys.modules,
        {"gpiod": mock_gpiod_module, "gpiod.line": mock_gpiod_module.line},
    ):
        # Force reimport to pick up mock
        if "lib.gpio_daemon" in sys.modules:
            del sys.modules["lib.gpio_daemon"]

        import lib.gpio_daemon as daemon_module

        # Patch daemon internals
        with (
            patch.object(daemon_module, "SOCKET_PATH", daemon_env["sock_path"]),
            patch.object(daemon_module, "STATE_FILE", daemon_env["state_file"]),
            patch.object(daemon_module, "_get_gpio_pins", return_value=gpio_pins),
            patch.object(daemon_module, "_get_switch_pins", return_value=switch_pins),
            patch.object(daemon_module, "_is_active_low", return_value=False),
        ):
            stop_event = threading.Event()
            daemon_thread = threading.Thread(
                target=daemon_module.run,
                kwargs={"stop_event": stop_event},
                daemon=True,
            )
            daemon_thread.start()

            # Wait for socket to appear and be ready to accept connections
            for _ in range(50):
                if Path(daemon_env["sock_path"]).exists():
                    try:
                        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                            s.settimeout(0.5)
                            s.connect(daemon_env["sock_path"])
                            s.sendall(b"PING\n")
                            s.recv(64)
                        break
                    except (ConnectionRefusedError, OSError):
                        pass
                time.sleep(0.05)

            yield daemon_env["sock_path"], daemon_env["state_file"], mock_request

            stop_event.set()
            daemon_thread.join(timeout=3)
            sys.modules.pop("lib.gpio_daemon", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDaemonPing:
    """PING health check."""

    def test_ping_returns_pong(self, running_daemon):
        sock_path, _, _ = running_daemon
        assert send_to_daemon(sock_path, "PING") == "PONG"


@pytest.mark.unit
class TestHealthCommand:
    """HEALTH command — daemon status reporting."""

    def test_health_returns_expected_fields(self, running_daemon):
        """HEALTH response contains uptime, lines, and last_cmd fields."""
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "HEALTH")
        assert response.startswith("HEALTH ")
        assert "uptime=" in response
        assert "lines=" in response
        assert "last_cmd=" in response

    def test_health_uptime_is_positive(self, running_daemon):
        """Uptime should be a positive float (daemon has been running)."""
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "HEALTH")
        # Parse uptime value
        for part in response.split():
            if part.startswith("uptime="):
                uptime = float(part.split("=", 1)[1])
                assert uptime >= 0.0
                break
        else:
            pytest.fail("uptime= not found in HEALTH response")

    def test_health_lines_count(self, running_daemon):
        """Lines count should match total relay + switch pins (5)."""
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "HEALTH")
        for part in response.split():
            if part.startswith("lines="):
                lines = int(part.split("=", 1)[1])
                # 3 relay pins + 2 switch pins = 5
                assert lines == 5
                break
        else:
            pytest.fail("lines= not found in HEALTH response")

    def test_health_last_cmd_after_ping(self, running_daemon):
        """After a PING, last_cmd should be an ISO timestamp (not 'never')."""
        sock_path, _, _ = running_daemon
        send_to_daemon(sock_path, "PING")
        response = send_to_daemon(sock_path, "HEALTH")
        for part in response.split():
            if part.startswith("last_cmd="):
                last_cmd = part.split("=", 1)[1]
                assert last_cmd != "never"
                # Should be an ISO timestamp containing 'T'
                assert "T" in last_cmd
                break
        else:
            pytest.fail("last_cmd= not found in HEALTH response")

    def test_health_does_not_crash_daemon(self, running_daemon):
        """Daemon remains responsive after HEALTH command."""
        sock_path, _, _ = running_daemon
        send_to_daemon(sock_path, "HEALTH")
        assert send_to_daemon(sock_path, "PING") == "PONG"


@pytest.mark.unit
class TestSetCommand:
    """SET <name> <on|off> commands."""

    def test_set_attract_on(self, running_daemon):
        sock_path, _, mock_request = running_daemon
        response = send_to_daemon(sock_path, "SET attract on")
        assert response == "OK attract on"

    def test_set_flash_off(self, running_daemon):
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "SET flash off")
        assert response == "OK flash off"

    def test_set_invalid_name(self, running_daemon):
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "SET bogus on")
        assert response.startswith("ERR")

    def test_set_persists_state(self, running_daemon):
        sock_path, state_file, _ = running_daemon
        send_to_daemon(sock_path, "SET attract on")
        # State file should be updated
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is True


@pytest.mark.unit
class TestGetCommand:
    """GET <name> queries."""

    def test_get_after_set(self, running_daemon):
        sock_path, _, _ = running_daemon
        send_to_daemon(sock_path, "SET attract on")
        response = send_to_daemon(sock_path, "GET attract")
        assert response == "STATE attract on"

    def test_get_default_off(self, running_daemon):
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "GET spare")
        assert response == "STATE spare off"


@pytest.mark.unit
class TestStatusCommand:
    """STATUS — all pin states."""

    def test_status_all_off(self, running_daemon):
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "STATUS")
        assert response.startswith("STATUS ")
        assert "attract=off" in response
        assert "flash=off" in response
        assert "spare=off" in response

    def test_status_reflects_set(self, running_daemon):
        sock_path, _, _ = running_daemon
        send_to_daemon(sock_path, "SET attract on")
        response = send_to_daemon(sock_path, "STATUS")
        assert "attract=on" in response
        assert "flash=off" in response


@pytest.mark.unit
class TestReadCommand:
    """READ <name> — switch pin input."""

    def test_read_off_pin(self, running_daemon):
        sock_path, _, mock_request = running_daemon
        # Mock returns HIGH (1) = not grounded
        mock_request.get_value.return_value = 1
        response = send_to_daemon(sock_path, "READ off_pin")
        assert response == "VALUE off_pin high"

    def test_read_unknown_name(self, running_daemon):
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "READ bogus")
        assert response.startswith("ERR")


@pytest.mark.unit
class TestStateRestore:
    """State restoration from gpio_state.json on startup."""

    @pytest.fixture
    def restored_daemon(self, daemon_env, mock_gpiod, sample_pins):
        """Start daemon with pre-populated state file.

        Writes {"Relay_Ch1": true} before starting the daemon so it
        restores the attract relay to ON at startup.
        """
        mock_gpiod_module, mock_request = mock_gpiod
        gpio_pins, switch_pins = sample_pins

        # Pre-populate state file BEFORE starting daemon
        daemon_env["state_file"].parent.mkdir(parents=True, exist_ok=True)
        daemon_env["state_file"].write_text(json.dumps({"Relay_Ch1": True}))

        with patch.dict(
            sys.modules,
            {"gpiod": mock_gpiod_module, "gpiod.line": mock_gpiod_module.line},
        ):
            if "lib.gpio_daemon" in sys.modules:
                del sys.modules["lib.gpio_daemon"]

            import lib.gpio_daemon as daemon_module

            with (
                patch.object(daemon_module, "SOCKET_PATH", daemon_env["sock_path"]),
                patch.object(daemon_module, "STATE_FILE", daemon_env["state_file"]),
                patch.object(daemon_module, "_get_gpio_pins", return_value=gpio_pins),
                patch.object(daemon_module, "_get_switch_pins", return_value=switch_pins),
                patch.object(daemon_module, "_is_active_low", return_value=False),
            ):
                stop_event = threading.Event()
                daemon_thread = threading.Thread(
                    target=daemon_module.run,
                    kwargs={"stop_event": stop_event},
                    daemon=True,
                )
                daemon_thread.start()

                for _ in range(50):
                    if Path(daemon_env["sock_path"]).exists():
                        try:
                            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                                s.settimeout(0.5)
                                s.connect(daemon_env["sock_path"])
                                s.sendall(b"PING\n")
                                s.recv(64)
                            break
                        except (ConnectionRefusedError, OSError):
                            pass
                    time.sleep(0.05)

                yield daemon_env["sock_path"], daemon_env["state_file"], mock_request

                stop_event.set()
                daemon_thread.join(timeout=3)
                sys.modules.pop("lib.gpio_daemon", None)

    def test_relay_restored_on_startup(self, restored_daemon):
        sock_path, _, _ = restored_daemon
        response = send_to_daemon(sock_path, "GET attract")
        assert response == "STATE attract on"


@pytest.mark.unit
class TestDaemonHardening:
    """Tests for daemon robustness fixes."""

    def test_empty_command_returns_ok(self, running_daemon):
        """Send bare newline → expect OK response (not a timeout)."""
        sock_path, _, _ = running_daemon
        response = send_to_daemon(sock_path, "")
        assert response == "OK"

    def test_oversized_message_handled(self, running_daemon):
        """Send >256 bytes without newline → daemon truncates and still serves."""
        sock_path, _, _ = running_daemon
        # Send 300 bytes of 'A' without a newline — daemon reads up to MAX_MSG_LENGTH
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect(sock_path)
            s.sendall(b"A" * 300)
            s.shutdown(socket.SHUT_WR)
            response = s.recv(4096).decode().strip()
        # Daemon should respond with an error (unknown command) rather than crash
        assert response.startswith("ERR")
        # Verify daemon is still alive by sending a PING
        assert send_to_daemon(sock_path, "PING") == "PONG"

    def test_slow_client_doesnt_block_daemon(self, running_daemon):
        """Connect but don't send → daemon still serves other clients after timeout."""
        sock_path, _, _ = running_daemon
        # Open a connection but never send anything
        slow_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        slow_sock.connect(sock_path)
        # Wait for the CONN_TIMEOUT (2s) to expire, plus a bit of margin
        time.sleep(3.0)
        slow_sock.close()
        # Daemon should still be responsive
        assert send_to_daemon(sock_path, "PING") == "PONG"
