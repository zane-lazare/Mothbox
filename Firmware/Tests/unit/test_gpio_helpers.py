"""
Unit tests for lib/gpio_helpers.py (Issue #399)

Tests the polarity-aware GPIO relay helper module that centralizes
relay ON/OFF logic based on the relay_active_low setting in controls.txt.

Test structure:
- TestGetRelayLevelActiveHigh: active-high polarity (default)
- TestGetRelayLevelActiveLow: active-low polarity
- TestGetRelayLevelDefaults: missing/fallback config behavior
- TestIsActiveLow: _is_active_low() internal helper
- TestSetupRelay: GPIO pin setup with correct initial level
- TestRelayOn: relay_on() drives correct level and writes state
- TestRelayOff: relay_off() drives correct level and writes state
- TestReadGpioState: gpio_state.json reading and error handling
- TestWriteGpioState: gpio_state.json atomic merge-write
- TestPinToRelayName: BCM pin to relay name resolution
- TestGpioUnavailable: graceful degradation when RPi.GPIO not installed
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Create a mock GPIO module before importing gpio_helpers
mock_gpio = MagicMock()
mock_gpio.BCM = 11
mock_gpio.OUT = 0
mock_gpio.IN = 1
mock_gpio.HIGH = 1
mock_gpio.LOW = 0
mock_gpio.setmode = MagicMock()
mock_gpio.setwarnings = MagicMock()
mock_gpio.setup = MagicMock()
mock_gpio.output = MagicMock()

# Patch RPi.GPIO before importing gpio_helpers
with patch.dict(sys.modules, {"RPi": MagicMock(), "RPi.GPIO": mock_gpio}):
    import lib.gpio_helpers as gpio_helpers_module
    from lib.gpio_helpers import (
        _is_active_low,
        _pin_to_relay_name,
        get_relay_level,
        read_gpio_state,
        relay_off,
        relay_on,
        setup_relay,
        write_gpio_state,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_gpio_mock():
    """Reset mock GPIO call history before each test."""
    mock_gpio.setup.reset_mock()
    mock_gpio.output.reset_mock()
    mock_gpio.setmode.reset_mock()
    mock_gpio.setwarnings.reset_mock()


@pytest.fixture
def state_file(tmp_path):
    """Provide a temporary gpio_state.json path and patch STATE_FILE."""
    sf = tmp_path / "gpio_state.json"
    with patch.object(gpio_helpers_module, "STATE_FILE", sf):
        yield sf


@pytest.fixture
def gpio_available():
    """Patch GPIO_AVAILABLE to True and provide the mock GPIO object."""
    with (
        patch.object(gpio_helpers_module, "GPIO_AVAILABLE", True),
        patch.object(gpio_helpers_module, "GPIO", mock_gpio),
    ):
        yield mock_gpio


@pytest.fixture
def gpio_unavailable():
    """Patch GPIO_AVAILABLE to False."""
    with patch.object(gpio_helpers_module, "GPIO_AVAILABLE", False):
        yield


@pytest.fixture
def active_high_config():
    """Patch get_control_values to return active-high config."""
    with patch.object(
        gpio_helpers_module,
        "get_control_values",
        return_value={"relay_active_low": "false"},
    ):
        yield


@pytest.fixture
def active_low_config():
    """Patch get_control_values to return active-low config."""
    with patch.object(
        gpio_helpers_module,
        "get_control_values",
        return_value={"relay_active_low": "true"},
    ):
        yield


@pytest.fixture
def no_polarity_config():
    """Patch get_control_values to return config without relay_active_low."""
    with patch.object(gpio_helpers_module, "get_control_values", return_value={}):
        yield


@pytest.fixture
def sample_gpio_pins():
    """Patch get_gpio_pins to return a standard 5.x pin mapping."""
    pins = {"Relay_Ch1": 5, "Relay_Ch2": 6, "Relay_Ch3": 13}
    with patch.object(gpio_helpers_module, "get_gpio_pins", return_value=pins):
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
            gpio_helpers_module,
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
            gpio_helpers_module,
            "get_control_values",
            side_effect=OSError("disk error"),
        ):
            assert _is_active_low() is False


# ---------------------------------------------------------------------------
# setup_relay() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetupRelay:
    """setup_relay() configures pin as GPIO output with OFF level."""

    def test_active_high_initial_low(self, gpio_available, active_high_config):
        """Active-HIGH: setup_relay() should initialize pin to LOW (OFF)."""
        setup_relay(5)
        mock_gpio.setup.assert_called_once_with(5, mock_gpio.OUT, initial=0)

    def test_active_low_initial_high(self, gpio_available, active_low_config):
        """Active-LOW: setup_relay() should initialize pin to HIGH (OFF)."""
        setup_relay(5)
        mock_gpio.setup.assert_called_once_with(5, mock_gpio.OUT, initial=1)

    def test_different_pin_numbers(self, gpio_available, active_high_config):
        """setup_relay() passes the correct pin number to GPIO.setup."""
        setup_relay(19)
        mock_gpio.setup.assert_called_once_with(19, mock_gpio.OUT, initial=0)

        mock_gpio.setup.reset_mock()
        setup_relay(26)
        mock_gpio.setup.assert_called_once_with(26, mock_gpio.OUT, initial=0)


# ---------------------------------------------------------------------------
# relay_on() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelayOn:
    """relay_on() drives pin to ON level and writes state file."""

    def test_active_high_drives_high(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """Active-HIGH: relay_on() should call GPIO.output(pin, HIGH)."""
        relay_on(5)
        mock_gpio.output.assert_called_once_with(5, 1)

    def test_active_low_drives_low(
        self, gpio_available, active_low_config, state_file, sample_gpio_pins
    ):
        """Active-LOW: relay_on() should call GPIO.output(pin, LOW)."""
        relay_on(5)
        mock_gpio.output.assert_called_once_with(5, 0)

    def test_writes_true_to_state_file(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_on() should write {relay_name: True} to gpio_state.json."""
        relay_on(5)
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is True

    def test_writes_correct_relay_name_for_ch2(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_on(pin_for_ch2) writes Relay_Ch2 to state file."""
        relay_on(6)
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch2"] is True

    def test_preserves_existing_state(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_on() merges with existing state, not overwrites."""
        state_file.write_text(json.dumps({"Relay_Ch1": False, "Relay_Ch3": True}))
        relay_on(6)  # Relay_Ch2
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is False
        assert state["Relay_Ch2"] is True
        assert state["Relay_Ch3"] is True


# ---------------------------------------------------------------------------
# relay_off() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelayOff:
    """relay_off() drives pin to OFF level and writes state file."""

    def test_active_high_drives_low(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """Active-HIGH: relay_off() should call GPIO.output(pin, LOW)."""
        relay_off(5)
        mock_gpio.output.assert_called_once_with(5, 0)

    def test_active_low_drives_high(
        self, gpio_available, active_low_config, state_file, sample_gpio_pins
    ):
        """Active-LOW: relay_off() should call GPIO.output(pin, HIGH)."""
        relay_off(5)
        mock_gpio.output.assert_called_once_with(5, 1)

    def test_writes_false_to_state_file(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_off() should write {relay_name: False} to gpio_state.json."""
        relay_off(5)
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is False

    def test_preserves_existing_state(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_off() merges with existing state."""
        state_file.write_text(json.dumps({"Relay_Ch1": True, "Relay_Ch2": True}))
        relay_off(5)  # Relay_Ch1
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is False
        assert state["Relay_Ch2"] is True


# ---------------------------------------------------------------------------
# read_gpio_state() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadGpioState:
    """read_gpio_state() reads gpio_state.json with error handling."""

    def test_returns_empty_dict_when_file_missing(self, state_file):
        """Returns {} when gpio_state.json does not exist."""
        assert not state_file.exists()
        result = read_gpio_state()
        assert result == {}

    def test_returns_parsed_json(self, state_file):
        """Returns parsed dict from existing gpio_state.json."""
        expected = {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": True}
        state_file.write_text(json.dumps(expected))
        result = read_gpio_state()
        assert result == expected

    def test_returns_empty_dict_on_invalid_json(self, state_file, caplog):
        """Returns {} and logs warning on corrupt JSON."""
        state_file.write_text("not valid json {{{")
        with caplog.at_level(logging.WARNING):
            result = read_gpio_state()
        assert result == {}
        assert any("Failed to read gpio_state.json" in msg for msg in caplog.messages)

    def test_returns_empty_dict_on_empty_file(self, state_file, caplog):
        """Returns {} when file exists but is empty."""
        state_file.write_text("")
        with caplog.at_level(logging.WARNING):
            result = read_gpio_state()
        assert result == {}


# ---------------------------------------------------------------------------
# write_gpio_state() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteGpioState:
    """write_gpio_state() atomic merge-write to gpio_state.json."""

    def test_creates_file_when_missing(self, state_file):
        """Creates gpio_state.json when it does not exist."""
        assert not state_file.exists()
        write_gpio_state({"Relay_Ch1": True})
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state == {"Relay_Ch1": True}

    def test_merges_with_existing_state(self, state_file):
        """Merges new entries into existing state."""
        state_file.write_text(json.dumps({"Relay_Ch1": False, "Relay_Ch2": True}))
        write_gpio_state({"Relay_Ch3": True})
        state = json.loads(state_file.read_text())
        assert state == {"Relay_Ch1": False, "Relay_Ch2": True, "Relay_Ch3": True}

    def test_overwrites_existing_key(self, state_file):
        """Updating an existing key replaces its value."""
        state_file.write_text(json.dumps({"Relay_Ch1": False}))
        write_gpio_state({"Relay_Ch1": True})
        state = json.loads(state_file.read_text())
        assert state["Relay_Ch1"] is True

    def test_creates_parent_directory(self, tmp_path):
        """Creates parent directories if they do not exist."""
        nested_file = tmp_path / "subdir" / "gpio_state.json"
        with patch.object(gpio_helpers_module, "STATE_FILE", nested_file):
            write_gpio_state({"Relay_Ch1": True})
        assert nested_file.exists()
        state = json.loads(nested_file.read_text())
        assert state == {"Relay_Ch1": True}

    def test_multiple_writes_accumulate(self, state_file):
        """Sequential writes merge correctly."""
        write_gpio_state({"Relay_Ch1": True})
        write_gpio_state({"Relay_Ch2": False})
        write_gpio_state({"Relay_Ch3": True})
        state = json.loads(state_file.read_text())
        assert state == {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": True}


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
            gpio_helpers_module,
            "get_gpio_pins",
            side_effect=RuntimeError("no config"),
        ):
            assert _pin_to_relay_name(5) == "5"


# ---------------------------------------------------------------------------
# GPIO unavailable tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGpioUnavailable:
    """Graceful degradation when RPi.GPIO is not installed."""

    def test_setup_relay_logs_warning_and_returns(self, gpio_unavailable, caplog):
        """setup_relay() should log a warning and return without error."""
        with caplog.at_level(logging.WARNING):
            setup_relay(5)
        assert any("GPIO not available" in msg for msg in caplog.messages)
        assert "setup_relay" in caplog.text
        # GPIO.setup should NOT be called
        mock_gpio.setup.assert_not_called()

    def test_relay_on_logs_warning_and_returns(self, gpio_unavailable, caplog):
        """relay_on() should log a warning and return without error."""
        with caplog.at_level(logging.WARNING):
            relay_on(5)
        assert any("GPIO not available" in msg for msg in caplog.messages)
        assert "relay_on" in caplog.text
        mock_gpio.output.assert_not_called()

    def test_relay_off_logs_warning_and_returns(self, gpio_unavailable, caplog):
        """relay_off() should log a warning and return without error."""
        with caplog.at_level(logging.WARNING):
            relay_off(5)
        assert any("GPIO not available" in msg for msg in caplog.messages)
        assert "relay_off" in caplog.text
        mock_gpio.output.assert_not_called()

    def test_relay_on_does_not_write_state(self, gpio_unavailable, state_file):
        """relay_on() should not write state when GPIO unavailable."""
        relay_on(5)
        assert not state_file.exists()

    def test_relay_off_does_not_write_state(self, gpio_unavailable, state_file):
        """relay_off() should not write state when GPIO unavailable."""
        relay_off(5)
        assert not state_file.exists()


# ---------------------------------------------------------------------------
# Integration-style: relay_on/relay_off round-trip through state file
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelayStateRoundTrip:
    """End-to-end: relay operations produce correct state file contents."""

    def test_on_then_off_reflects_in_state(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """relay_on then relay_off should leave state as False."""
        relay_on(5)
        state = read_gpio_state()
        assert state["Relay_Ch1"] is True

        relay_off(5)
        state = read_gpio_state()
        assert state["Relay_Ch1"] is False

    def test_multiple_relays_independent(
        self, gpio_available, active_high_config, state_file, sample_gpio_pins
    ):
        """Operating on different relays updates only their own state."""
        relay_on(5)  # Ch1 ON
        relay_on(6)  # Ch2 ON
        relay_off(5)  # Ch1 OFF

        state = read_gpio_state()
        assert state["Relay_Ch1"] is False
        assert state["Relay_Ch2"] is True

    def test_active_low_polarity_levels_correct(
        self, gpio_available, active_low_config, state_file, sample_gpio_pins
    ):
        """Under active-low config, GPIO levels are inverted but state is logical."""
        relay_on(5)
        # GPIO should be driven LOW for active-low ON
        mock_gpio.output.assert_called_with(5, 0)
        # But state file should record logical True (relay is ON)
        state = read_gpio_state()
        assert state["Relay_Ch1"] is True

        mock_gpio.output.reset_mock()
        relay_off(5)
        # GPIO should be driven HIGH for active-low OFF
        mock_gpio.output.assert_called_with(5, 1)
        state = read_gpio_state()
        assert state["Relay_Ch1"] is False
