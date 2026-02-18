"""
Unit tests for GPIO control routes — daemon-backed version.

Tests all GPIO control endpoints. Routes delegate to gpio_client which
communicates with the GPIO daemon via Unix socket. GPIODaemonError from
the client maps to HTTP 503.

Test structure:
- TestGPIOStatusEndpoint: GET /api/gpio/status tests
- TestGPIOControlEndpoint: POST /api/gpio/control tests
- TestGPIOFlashEndpoint: POST /api/gpio/flash tests
- TestGPIOSecurity: Security and input validation tests
- TestGPIOErrorRecovery: Error handling and cleanup tests
- TestGPIODaemonError: Daemon unreachable returns HTTP 503
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

_firmware_root = str(Path(__file__).parent.parent.parent)
# Firmware root must be first so top-level lib/ is found before webui/backend/lib/
if _firmware_root not in sys.path:
    sys.path.insert(0, _firmware_root)
_backend_dir = str(Path(__file__).parent.parent.parent / "webui" / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(1, _backend_dir)

from lib.gpio_protocol import GPIODaemonError


@pytest.mark.unit
class TestGPIOHealthEndpoint:
    """Tests for GET /api/gpio/health endpoint"""

    def test_health_returns_200_when_daemon_reachable(self, client, temp_controls_file):
        """GET /health returns 200 with health data when daemon is up."""
        mock_health = {
            "reachable": True,
            "uptime_seconds": 120.5,
            "managed_lines": 5,
            "last_command_at": "2026-02-18T10:00:00+00:00",
        }

        with patch("routes.gpio.health", return_value=mock_health):
            response = client.get("/api/gpio/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["reachable"] is True
        assert data["uptime_seconds"] == 120.5
        assert data["managed_lines"] == 5
        assert data["last_command_at"] == "2026-02-18T10:00:00+00:00"

    def test_health_returns_503_on_daemon_error(self, client, temp_controls_file):
        """GET /health returns 503 when daemon is unreachable."""
        with patch(
            "routes.gpio.health",
            side_effect=GPIODaemonError("not running"),
        ):
            response = client.get("/api/gpio/health")

        assert response.status_code == 503
        data = response.get_json()
        assert "daemon" in data["error"].lower()

    def test_health_returns_500_on_unexpected_error(self, client, temp_controls_file):
        """GET /health returns 500 on non-daemon errors."""
        with patch(
            "routes.gpio.health",
            side_effect=RuntimeError("Unexpected failure"),
        ):
            response = client.get("/api/gpio/health")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


@pytest.mark.unit
class TestGPIOStatusEndpoint:
    """Tests for GET /api/gpio/status endpoint"""

    def test_status_returns_all_relays(self, client, temp_controls_file):
        """GET /status returns all 3 relay states from daemon."""
        mock_state = {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": True}

        with (
            patch("routes.gpio.read_gpio_state", return_value=mock_state),
            patch(
                "routes.gpio.get_gpio_pins",
                return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
            ),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is True
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is True

    def test_status_fills_missing_relays(self, client, temp_controls_file):
        """GET /status defaults missing relays to False."""
        # Daemon returns only one relay
        mock_state = {"Relay_Ch1": True}

        with (
            patch("routes.gpio.read_gpio_state", return_value=mock_state),
            patch(
                "routes.gpio.get_gpio_pins",
                return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
            ),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is True
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False

    def test_status_handles_empty_state(self, client, temp_controls_file):
        """GET /status returns default state when daemon returns empty dict."""
        with (
            patch("routes.gpio.read_gpio_state", return_value={}),
            patch(
                "routes.gpio.get_gpio_pins",
                return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
            ),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is False
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False

    def test_status_returns_500_on_exception(self, client, temp_controls_file):
        """GET /status returns 500 on unexpected errors."""
        with patch(
            "routes.gpio.read_gpio_state",
            side_effect=RuntimeError("Unexpected failure"),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


@pytest.mark.unit
class TestGPIOControlEndpoint:
    """Tests for POST /api/gpio/control endpoint"""

    def test_control_toggles_relay_on(self, client, temp_controls_file):
        """POST /control calls relay_on with correct pin."""
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch("routes.gpio.setup_relay") as mock_setup,
            patch("routes.gpio.relay_on") as mock_relay_on,
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["relay"] == "Relay_Ch1"
        assert data["state"] is True
        mock_setup.assert_called_once_with(5)
        mock_relay_on.assert_called_once_with(5)

    def test_control_toggles_relay_off(self, client, temp_controls_file):
        """POST /control calls relay_off with correct pin."""
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay") as mock_setup,
            patch("routes.gpio.relay_off") as mock_relay_off,
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch2", "state": False})

        assert response.status_code == 200
        mock_setup.assert_called_once_with(19)
        mock_relay_off.assert_called_once_with(19)

    def test_control_validates_relay_name(self, client, temp_controls_file):
        """POST /control rejects invalid relay names."""
        with patch(
            "routes.gpio.get_gpio_pins",
            return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
        ):
            response = client.post(
                "/api/gpio/control", json={"relay": "Invalid_Relay", "state": True}
            )

        assert response.status_code == 400
        assert "Invalid relay" in response.get_json()["error"]

    def test_control_validates_state_type(self, client, temp_controls_file):
        """POST /control rejects non-boolean state."""
        with patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}):
            response = client.post(
                "/api/gpio/control",
                json={"relay": "Relay_Ch1", "state": "true"},
            )

        assert response.status_code == 400
        assert "State must be a boolean" in response.get_json()["error"]

    def test_control_requires_both_parameters(self, client, temp_controls_file):
        """POST /control returns 400 if relay or state missing."""
        # Missing state
        response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1"})
        assert response.status_code == 400
        assert "Missing relay or state" in response.get_json()["error"]

        # Missing relay
        response = client.post("/api/gpio/control", json={"state": True})
        assert response.status_code == 400
        assert "Missing relay or state" in response.get_json()["error"]

    def test_control_calls_setup_before_relay_on(self, client, temp_controls_file):
        """POST /control calls setup_relay() before relay_on()."""
        call_order = []

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch(
                "routes.gpio.setup_relay",
                side_effect=lambda pin: call_order.append(("setup", pin)),
            ),
            patch(
                "routes.gpio.relay_on",
                side_effect=lambda pin: call_order.append(("on", pin)),
            ),
        ):
            client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert call_order == [("setup", 5), ("on", 5)]


@pytest.mark.unit
class TestGPIOFlashEndpoint:
    """Tests for POST /api/gpio/flash endpoint"""

    def test_flash_triggers_momentary_pulse(self, client, temp_controls_file):
        """POST /flash turns on, waits, turns off."""
        temp_controls_file.write_text("flash_duration_ms=50\n")
        call_order = []

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch(
                "routes.gpio.setup_relay",
                side_effect=lambda pin: call_order.append(("setup", pin)),
            ),
            patch(
                "routes.gpio.relay_on",
                side_effect=lambda pin: call_order.append(("on", pin)),
            ),
            patch(
                "routes.gpio.relay_off",
                side_effect=lambda pin: call_order.append(("off", pin)),
            ),
        ):
            response = client.post("/api/gpio/flash")

        assert response.status_code == 200

        # Verify the flash sequence: setup, on, off
        assert ("setup", 19) in call_order
        assert ("on", 19) in call_order
        assert ("off", 19) in call_order
        on_idx = call_order.index(("on", 19))
        off_idx = call_order.index(("off", 19))
        assert on_idx < off_idx

    def test_flash_uses_correct_pin(self, client, temp_controls_file):
        """POST /flash uses Relay_Ch2 (flash pin)."""
        temp_controls_file.write_text("flash_duration_ms=50\n")

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay") as mock_setup,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.relay_off") as mock_relay_off,
        ):
            client.post("/api/gpio/flash")

        mock_setup.assert_called_once_with(19)
        mock_relay_on.assert_called_once_with(19)
        mock_relay_off.assert_called_once_with(19)

    def test_flash_respects_duration_from_controls(self, client, temp_controls_file):
        """POST /flash reads flash_duration_ms from controls.txt."""
        temp_controls_file.write_text("flash_duration_ms=200\n")

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay"),
            patch("routes.gpio.relay_on"),
            patch("routes.gpio.relay_off"),
        ):
            start = time.time()
            client.post("/api/gpio/flash")
            duration = time.time() - start

        # Duration should be approximately 200ms (0.2s)
        assert duration >= 0.15
        assert duration < 0.5

    def test_flash_defaults_to_100ms(self, client, temp_controls_file):
        """POST /flash uses 100ms if flash_duration_ms not set."""
        temp_controls_file.write_text("name=TestBox\n")

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay"),
            patch("routes.gpio.relay_on"),
            patch("routes.gpio.relay_off"),
        ):
            start = time.time()
            client.post("/api/gpio/flash")
            duration = time.time() - start

        # Duration should be approximately 100ms (default)
        assert duration >= 0.08
        assert duration < 0.3

    def test_flash_cleans_up_on_interrupt(self, client, temp_controls_file):
        """POST /flash returns 500 if error during sleep."""
        temp_controls_file.write_text("flash_duration_ms=100\n")

        original_sleep = time.sleep

        def failing_sleep(duration):
            if duration > 0.05:
                raise RuntimeError("Simulated error during flash")
            original_sleep(duration)

        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay"),
            patch("routes.gpio.relay_on"),
            patch("routes.gpio.relay_off"),
            patch("time.sleep", side_effect=failing_sleep),
        ):
            response = client.post("/api/gpio/flash")

        assert response.status_code == 500


@pytest.mark.unit
class TestGPIOSecurity:
    """Security and input validation tests"""

    def test_control_whitelist_enforcement(self, client, temp_controls_file):
        """Only accepts valid relay names from config."""
        invalid_relays = [
            "Relay_Ch4",
            "GPIO_26",
            "../../../etc/passwd",
            "; DROP TABLE relays--",
            '__import__("os").system("ls")',
        ]

        with patch(
            "routes.gpio.get_gpio_pins",
            return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
        ):
            for relay in invalid_relays:
                response = client.post("/api/gpio/control", json={"relay": relay, "state": True})
                assert response.status_code == 400
                assert "Invalid relay" in response.get_json()["error"]

    def test_control_injection_prevention(self, client, temp_controls_file):
        """Rejects path traversal in relay parameter."""
        malicious_names = [
            "../../../etc/passwd",
            "../../config",
            "Relay_Ch1; cat /etc/passwd",
        ]

        with patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}):
            for name in malicious_names:
                response = client.post("/api/gpio/control", json={"relay": name, "state": True})
                assert response.status_code == 400

    def test_control_type_validation(self, client, temp_controls_file):
        """Rejects string 'true' and integer 1 instead of boolean."""
        with patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}):
            # String value should be rejected
            response = client.post(
                "/api/gpio/control", json={"relay": "Relay_Ch1", "state": "true"}
            )
            assert response.status_code == 400

            # Integer should also be rejected
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": 1})
            assert response.status_code == 400


@pytest.mark.unit
class TestGPIOErrorRecovery:
    """Error handling and cleanup tests"""

    def test_status_endpoint_handles_exceptions_gracefully(self, client, temp_controls_file):
        """GET /status returns 500 on unexpected errors."""
        with patch(
            "routes.gpio.read_gpio_state",
            side_effect=RuntimeError("Simulated hardware failure"),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 500
        assert "error" in response.get_json()

    def test_control_endpoint_handles_runtime_errors(self, client, temp_controls_file):
        """POST /control returns 500 on non-daemon errors."""
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch("routes.gpio.setup_relay"),
            patch(
                "routes.gpio.relay_on",
                side_effect=RuntimeError("GPIO hardware error"),
            ),
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 500
        assert "error" in response.get_json()

    def test_status_missing_relay_in_state(self, client, temp_controls_file):
        """Status endpoint returns False for relays not returned by daemon."""
        mock_state = {"Relay_Ch1": True, "Relay_Ch2": False}

        with (
            patch("routes.gpio.read_gpio_state", return_value=mock_state),
            patch(
                "routes.gpio.get_gpio_pins",
                return_value={"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9},
            ),
        ):
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is True
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False  # Should default to False


@pytest.mark.unit
class TestGPIODaemonError:
    """Tests that GPIODaemonError from client returns HTTP 503."""

    def test_control_returns_503_on_daemon_error(self, client, temp_controls_file):
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch(
                "routes.gpio.relay_on",
                side_effect=GPIODaemonError("not running"),
            ),
            patch("routes.gpio.setup_relay"),
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})
        assert response.status_code == 503
        assert "daemon" in response.get_json()["error"].lower()

    def test_control_off_returns_503_on_daemon_error(self, client, temp_controls_file):
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch(
                "routes.gpio.relay_off",
                side_effect=GPIODaemonError("not running"),
            ),
            patch("routes.gpio.setup_relay"),
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": False})
        assert response.status_code == 503
        assert "daemon" in response.get_json()["error"].lower()

    def test_flash_returns_503_on_daemon_error(self, client, temp_controls_file):
        temp_controls_file.write_text("flash_duration_ms=50\n")
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch2": 19}),
            patch("routes.gpio.setup_relay"),
            patch(
                "routes.gpio.relay_on",
                side_effect=GPIODaemonError("not running"),
            ),
        ):
            response = client.post("/api/gpio/flash")
        assert response.status_code == 503

    def test_daemon_error_no_details_leaked(self, client, temp_controls_file):
        """503 response does not leak internal error details."""
        with (
            patch("routes.gpio.get_gpio_pins", return_value={"Relay_Ch1": 5}),
            patch("routes.gpio.setup_relay"),
            patch(
                "routes.gpio.relay_on",
                side_effect=GPIODaemonError("socket /run/mothbox/gpio.sock not found"),
            ),
        ):
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})
        assert response.status_code == 503
        data = response.get_json()
        assert "details" not in data
        assert data["error"] == "GPIO daemon not available"
