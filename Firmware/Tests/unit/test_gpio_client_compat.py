"""
Compatibility tests for lib/gpio_client.py pure-logic functions.

Adapted from the original test_gpio_helpers.py (Issue #399). These tests
verify that the pure-logic functions migrated to gpio_client preserve
identical behaviour:

- get_relay_level(): polarity-aware GPIO level selection
- _is_active_low(): config reading for relay polarity
- _pin_to_relay_name(): BCM pin to relay name resolution
- read_gpio_state(): file fallback when daemon is unreachable

Functions that dealt with RPi.GPIO directly (setup_relay, relay_on,
relay_off, write_gpio_state) are tested via mock socket in
test_gpio_client.py instead.
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import lib.gpio_client as gpio_client_module
from lib.gpio_client import (
    _is_active_low,
    _pin_to_relay_name,
    get_relay_level,
    read_gpio_state,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_file(tmp_path):
    """Provide a temporary gpio_state.json path and patch STATE_FILE."""
    sf = tmp_path / "gpio_state.json"
    with patch.object(gpio_client_module, "STATE_FILE", sf):
        yield sf


@pytest.fixture
def daemon_unreachable():
    """Make socket.socket raise ConnectionRefusedError so read_gpio_state
    falls back to reading the state file."""
    with patch("socket.socket", side_effect=ConnectionRefusedError):
        yield


@pytest.fixture
def active_high_config():
    """Patch get_control_values to return active-high config."""
    with patch.object(
        gpio_client_module,
        "get_control_values",
        return_value={"relay_active_low": "false"},
    ):
        yield


@pytest.fixture
def active_low_config():
    """Patch get_control_values to return active-low config."""
    with patch.object(
        gpio_client_module,
        "get_control_values",
        return_value={"relay_active_low": "true"},
    ):
        yield


@pytest.fixture
def no_polarity_config():
    """Patch get_control_values to return config without relay_active_low."""
    with patch.object(gpio_client_module, "get_control_values", return_value={}):
        yield


@pytest.fixture
def sample_gpio_pins():
    """Patch get_gpio_pins to return a standard 5.x pin mapping."""
    pins = {"Relay_Ch1": 5, "Relay_Ch2": 6, "Relay_Ch3": 13}
    with patch.object(gpio_client_module, "get_gpio_pins", return_value=pins):
        yield pins


# ---------------------------------------------------------------------------
# get_relay_level() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRelayLevelActiveHigh:
    """get_relay_level() with active-HIGH polarity (relay_active_low=false)."""

    def test_on_returns_high(self, active_high_config):
        """Active-HIGH: ON should return 1 (GPIO.HIGH)."""
        assert get_relay_level(on=True) == 1

    def test_off_returns_low(self, active_high_config):
        """Active-HIGH: OFF should return 0 (GPIO.LOW)."""
        assert get_relay_level(on=False) == 0


@pytest.mark.unit
class TestGetRelayLevelActiveLow:
    """get_relay_level() with active-LOW polarity (relay_active_low=true)."""

    def test_on_returns_low(self, active_low_config):
        """Active-LOW: ON should return 0 (GPIO.LOW)."""
        assert get_relay_level(on=True) == 0

    def test_off_returns_high(self, active_low_config):
        """Active-LOW: OFF should return 1 (GPIO.HIGH)."""
        assert get_relay_level(on=False) == 1


@pytest.mark.unit
class TestGetRelayLevelDefaults:
    """get_relay_level() when config is missing or has unexpected values."""

    def test_missing_config_defaults_to_active_high_on(self, no_polarity_config):
        """Missing relay_active_low should default to active-HIGH: ON=1."""
        assert get_relay_level(on=True) == 1

    def test_missing_config_defaults_to_active_high_off(self, no_polarity_config):
        """Missing relay_active_low should default to active-HIGH: OFF=0."""
        assert get_relay_level(on=False) == 0

    def test_exception_in_config_defaults_to_active_high(self):
        """If get_control_values raises, should default to active-HIGH."""
        with patch.object(
            gpio_client_module,
            "get_control_values",
            side_effect=FileNotFoundError("controls.txt not found"),
        ):
            # _is_active_low() catches exceptions and returns False
            assert get_relay_level(on=True) == 1
            assert get_relay_level(on=False) == 0


# ---------------------------------------------------------------------------
# _is_active_low() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsActiveLow:
    """_is_active_low() internal helper reads relay_active_low from config."""

    def test_true_when_config_says_true(self, active_low_config):
        """Returns True when relay_active_low=true."""
        assert _is_active_low() is True

    def test_false_when_config_says_false(self, active_high_config):
        """Returns False when relay_active_low=false."""
        assert _is_active_low() is False

    def test_false_when_config_missing(self, no_polarity_config):
        """Returns False (active-high default) when key is absent."""
        assert _is_active_low() is False

    def test_false_on_exception(self):
        """Returns False when get_control_values raises an exception."""
        with patch.object(
            gpio_client_module,
            "get_control_values",
            side_effect=OSError("disk error"),
        ):
            assert _is_active_low() is False


# ---------------------------------------------------------------------------
# read_gpio_state() file fallback tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadGpioStateFileFallback:
    """read_gpio_state() file fallback when daemon is unreachable.

    gpio_client's read_gpio_state() first tries the daemon via socket.
    When the daemon is unreachable (ConnectionRefusedError), it falls
    back to reading gpio_state.json directly. These tests verify that
    file fallback path.
    """

    def test_returns_empty_dict_when_file_missing(self, daemon_unreachable, state_file):
        """Returns {} when gpio_state.json does not exist."""
        assert not state_file.exists()
        result = read_gpio_state()
        assert result == {}

    def test_returns_parsed_json(self, daemon_unreachable, state_file):
        """Returns parsed dict from existing gpio_state.json."""
        expected = {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": True}
        state_file.write_text(json.dumps(expected))
        result = read_gpio_state()
        assert result == expected

    def test_returns_empty_dict_on_invalid_json(self, daemon_unreachable, state_file, caplog):
        """Returns {} and logs warning on corrupt JSON."""
        state_file.write_text("not valid json {{{")
        with caplog.at_level(logging.WARNING):
            result = read_gpio_state()
        assert result == {}
        assert any("Failed to read gpio_state.json" in msg for msg in caplog.messages)

    def test_returns_empty_dict_on_empty_file(self, daemon_unreachable, state_file, caplog):
        """Returns {} when file exists but is empty."""
        state_file.write_text("")
        with caplog.at_level(logging.WARNING):
            result = read_gpio_state()
        assert result == {}


# ---------------------------------------------------------------------------
# _pin_to_relay_name() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPinToRelayName:
    """_pin_to_relay_name() resolves BCM pin to relay name."""

    def test_resolves_known_pin(self, sample_gpio_pins):
        """Returns relay name for a known pin mapping."""
        assert _pin_to_relay_name(5) == "Relay_Ch1"
        assert _pin_to_relay_name(6) == "Relay_Ch2"
        assert _pin_to_relay_name(13) == "Relay_Ch3"

    def test_unknown_pin_returns_string_number(self, sample_gpio_pins):
        """Returns string of pin number when no relay matches."""
        assert _pin_to_relay_name(99) == "99"

    def test_falls_back_on_exception(self):
        """Returns string of pin number when get_gpio_pins raises."""
        with patch.object(
            gpio_client_module,
            "get_gpio_pins",
            side_effect=RuntimeError("no config"),
        ):
            assert _pin_to_relay_name(5) == "5"
