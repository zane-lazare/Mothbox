"""
Unit tests for lib/gpio_client.py — GPIO daemon client.

Tests the client with a mocked Unix socket. The client preserves the
exact same public API as gpio_helpers.py but talks to the daemon via IPC.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.gpio_protocol import GPIODaemonError


class MockDaemonSocket:
    """Simulates the daemon side of a Unix socket connection."""

    def __init__(self, response="PONG\n"):
        self.response = response.encode() if isinstance(response, str) else response
        self.sent = b""
        self.connected_to = None
        self._closed = False

    def connect(self, addr):
        self.connected_to = addr

    def settimeout(self, t):
        pass

    def sendall(self, data):
        self.sent += data

    def recv(self, bufsize):
        return self.response

    def close(self):
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def sample_gpio_pins():
    """Patch get_gpio_pins to return 5.x production pin mapping."""
    pins = {"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9}
    with patch("lib.gpio_client.get_gpio_pins", return_value=pins):
        yield pins


@pytest.fixture
def sample_switch_pins():
    """Patch get_switch_pins to return standard switch pin mapping."""
    pins = {"off_pin": 16, "debug_pin": 12}
    with patch("lib.gpio_client.get_switch_pins", return_value=pins):
        yield pins


@pytest.fixture
def active_high_config():
    """Patch get_control_values to return active-high config."""
    with patch(
        "lib.gpio_client.get_control_values",
        return_value={"relay_active_low": "false"},
    ):
        yield


@pytest.fixture
def active_low_config():
    """Patch get_control_values to return active-low config."""
    with patch(
        "lib.gpio_client.get_control_values",
        return_value={"relay_active_low": "true"},
    ):
        yield


from lib.gpio_client import (
    _pin_to_ipc_name,
    _pin_to_relay_name,
    get_relay_level,
    health,
    read_gpio_state,
    read_switch,
    relay_off,
    relay_on,
    setup_relay,
)


@pytest.mark.unit
class TestHealth:
    """health() queries daemon for health status."""

    def test_parses_health_response(self):
        mock = MockDaemonSocket(
            "HEALTH uptime=120.5 lines=5 last_cmd=2026-02-18T10:00:00+00:00\n"
        )
        with patch("socket.socket", return_value=mock):
            result = health()
        assert result["reachable"] is True
        assert result["uptime_seconds"] == 120.5
        assert result["managed_lines"] == 5
        assert result["last_command_at"] == "2026-02-18T10:00:00+00:00"
        assert mock.sent == b"HEALTH\n"

    def test_parses_health_with_never_last_cmd(self):
        mock = MockDaemonSocket("HEALTH uptime=0.1 lines=5 last_cmd=never\n")
        with patch("socket.socket", return_value=mock):
            result = health()
        assert result["reachable"] is True
        assert result["uptime_seconds"] == 0.1
        assert result["managed_lines"] == 5
        assert result["last_command_at"] == "never"

    def test_raises_on_daemon_unreachable(self):
        with (
            patch("socket.socket", side_effect=ConnectionRefusedError),
            pytest.raises(GPIODaemonError, match="not running"),
        ):
            health()


@pytest.mark.unit
class TestSetupRelay:
    """setup_relay() is a no-op — daemon owns pin setup."""

    def test_noop_returns_none(self):
        result = setup_relay(5)
        assert result is None

    def test_does_not_open_socket(self):
        with patch("socket.socket") as mock_sock:
            setup_relay(5)
            mock_sock.assert_not_called()


@pytest.mark.unit
class TestRelayOn:
    """relay_on() sends SET <name> on to daemon."""

    def test_sends_set_command(self, sample_gpio_pins):
        mock = MockDaemonSocket("OK attract on\n")
        with patch("socket.socket", return_value=mock):
            relay_on(5)
        assert mock.sent == b"SET attract on\n"

    def test_sends_correct_name_for_flash(self, sample_gpio_pins):
        mock = MockDaemonSocket("OK flash on\n")
        with patch("socket.socket", return_value=mock):
            relay_on(19)
        assert mock.sent == b"SET flash on\n"

    def test_sends_correct_name_for_spare(self, sample_gpio_pins):
        mock = MockDaemonSocket("OK spare on\n")
        with patch("socket.socket", return_value=mock):
            relay_on(9)
        assert mock.sent == b"SET spare on\n"

    def test_raises_on_err_response(self, sample_gpio_pins):
        mock = MockDaemonSocket("ERR unknown pin\n")
        with (
            patch("socket.socket", return_value=mock),
            pytest.raises(GPIODaemonError, match="unknown pin"),
        ):
            relay_on(5)

    def test_raises_on_connection_refused(self, sample_gpio_pins):
        with patch("socket.socket") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(
                side_effect=ConnectionRefusedError("refused")
            )
            with pytest.raises(GPIODaemonError, match="not running"):
                relay_on(5)


@pytest.mark.unit
class TestRelayOff:
    """relay_off() sends SET <name> off to daemon."""

    def test_sends_set_off_command(self, sample_gpio_pins):
        mock = MockDaemonSocket("OK attract off\n")
        with patch("socket.socket", return_value=mock):
            relay_off(5)
        assert mock.sent == b"SET attract off\n"

    def test_raises_on_err_response(self, sample_gpio_pins):
        mock = MockDaemonSocket("ERR hardware fault\n")
        with (
            patch("socket.socket", return_value=mock),
            pytest.raises(GPIODaemonError, match="hardware fault"),
        ):
            relay_off(5)


@pytest.mark.unit
class TestGetRelayLevel:
    """get_relay_level() — polarity logic preserved from gpio_helpers."""

    def test_active_high_on(self, active_high_config):
        assert get_relay_level(on=True) == 1

    def test_active_high_off(self, active_high_config):
        assert get_relay_level(on=False) == 0

    def test_active_low_on(self, active_low_config):
        assert get_relay_level(on=True) == 0

    def test_active_low_off(self, active_low_config):
        assert get_relay_level(on=False) == 1


@pytest.mark.unit
class TestReadGpioState:
    """read_gpio_state() queries daemon, falls back to file."""

    def test_parses_status_response(self, sample_gpio_pins):
        mock = MockDaemonSocket("STATUS attract=on,flash=off,spare=off\n")
        with patch("socket.socket", return_value=mock):
            result = read_gpio_state()
        assert result == {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": False}

    def test_falls_back_to_file_on_error(self, tmp_path, sample_gpio_pins):
        state_file = tmp_path / "gpio_state.json"
        state_file.write_text(json.dumps({"Relay_Ch1": True}))
        with (
            patch("socket.socket", side_effect=ConnectionRefusedError),
            patch("lib.gpio_client.STATE_FILE", state_file),
        ):
            result = read_gpio_state()
        assert result == {"Relay_Ch1": True}

    def test_returns_empty_dict_when_both_fail(self, tmp_path, sample_gpio_pins):
        with (
            patch("socket.socket", side_effect=ConnectionRefusedError),
            patch("lib.gpio_client.STATE_FILE", tmp_path / "missing.json"),
        ):
            result = read_gpio_state()
        assert result == {}


@pytest.mark.unit
class TestReadSwitch:
    """read_switch() sends READ command to daemon."""

    def test_reads_off_pin(self, sample_gpio_pins, sample_switch_pins):
        mock = MockDaemonSocket("VALUE off_pin low\n")
        with patch("socket.socket", return_value=mock):
            result = read_switch(16)
        assert result is True
        assert mock.sent == b"READ off_pin\n"

    def test_reads_debug_pin_high(self, sample_gpio_pins, sample_switch_pins):
        mock = MockDaemonSocket("VALUE debug_pin high\n")
        with patch("socket.socket", return_value=mock):
            result = read_switch(12)
        assert result is False

    def test_raises_on_daemon_error(self, sample_gpio_pins, sample_switch_pins):
        with (
            patch("socket.socket", side_effect=ConnectionRefusedError),
            pytest.raises(GPIODaemonError),
        ):
            read_switch(16)


@pytest.mark.unit
class TestPinToIpcName:
    """BCM pin to IPC name mapping."""

    def test_relay_pins(self, sample_gpio_pins, sample_switch_pins):
        assert _pin_to_ipc_name(5) == "attract"
        assert _pin_to_ipc_name(19) == "flash"
        assert _pin_to_ipc_name(9) == "spare"

    def test_switch_pins(self, sample_gpio_pins, sample_switch_pins):
        assert _pin_to_ipc_name(16) == "off_pin"
        assert _pin_to_ipc_name(12) == "debug_pin"

    def test_unknown_pin_raises(self, sample_gpio_pins, sample_switch_pins):
        with pytest.raises(GPIODaemonError, match="Unknown pin"):
            _pin_to_ipc_name(99)


@pytest.mark.unit
class TestPinToRelayName:
    """BCM pin to Relay_ChN name mapping."""

    def test_resolves_known_pins(self, sample_gpio_pins):
        assert _pin_to_relay_name(5) == "Relay_Ch1"
        assert _pin_to_relay_name(19) == "Relay_Ch2"
        assert _pin_to_relay_name(9) == "Relay_Ch3"

    def test_unknown_pin_returns_string(self, sample_gpio_pins):
        assert _pin_to_relay_name(99) == "99"
