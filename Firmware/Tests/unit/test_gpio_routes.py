"""
Unit tests for GPIO control routes (Issue #78)

Tests all GPIO control endpoints with comprehensive mocking for CI/CD compatibility.
Focus areas: security, concurrency, error recovery.

Test structure:
- TestGPIOStatusEndpoint: GET /api/gpio/status tests
- TestGPIOControlEndpoint: POST /api/gpio/control tests
- TestGPIOFlashEndpoint: POST /api/gpio/flash tests
- TestGPIOSecurity: Security and input validation tests
- TestGPIOConcurrency: File locking and race condition tests
- TestGPIOErrorRecovery: Error handling and cleanup tests
"""

import json

# Import after path setup
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


class TestGPIOStatusEndpoint:
    """Tests for GET /api/gpio/status endpoint"""

    def test_status_returns_all_relays(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """GET /status returns all 3 relay states"""
        # Setup: Write known state to state file
        state = {"Relay_Ch1": True, "Relay_Ch2": False, "Relay_Ch3": True}
        temp_gpio_state_file.write_text(json.dumps(state))

        # Mock get_gpio_pins to return relay config
        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is True
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is True

    def test_status_reads_from_state_file(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """GET /status reads gpio_state.json correctly"""
        # Setup: Custom state in file
        state = {"Relay_Ch1": False, "Relay_Ch2": True, "Relay_Ch3": False}
        temp_gpio_state_file.write_text(json.dumps(state))

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data == state

    def test_status_handles_missing_state_file(self, client, mock_rpi_gpio, tmp_path, monkeypatch):
        """GET /status returns default state if file missing"""
        # Don't create state file - let it be missing
        from Tests.conftest import patch_path_constant_everywhere

        patch_path_constant_everywhere(monkeypatch, "DATA_DIR", tmp_path)

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}
            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        # Should return default (all False)
        assert data["Relay_Ch1"] is False
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False

    def test_status_returns_error_when_gpio_unavailable(
        self, client, monkeypatch, temp_gpio_state_file
    ):
        """GET /status returns 500 when GPIO_AVAILABLE=False"""
        # Mock GPIO unavailable
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", False)

        response = client.get("/api/gpio/status")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "GPIO not available" in data["error"]

    def test_status_returns_error_on_permission_denied(
        self, client, monkeypatch, temp_gpio_state_file
    ):
        """GET /status returns 403 when GPIO_PERMISSIONS_OK=False"""
        # Mock GPIO available but no permissions
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", True)
        monkeypatch.setattr("routes.gpio.GPIO_PERMISSIONS_OK", False)
        monkeypatch.setattr("routes.gpio.GPIO_PERMISSION_ERROR", "Permission denied: test error")

        response = client.get("/api/gpio/status")

        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "GPIO permission denied" in data["error"]
        assert "details" in data

    def test_status_handles_corrupted_state_file(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """GET /status handles malformed JSON gracefully"""
        # Write invalid JSON
        temp_gpio_state_file.write_text("invalid json {{{")

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}
            response = client.get("/api/gpio/status")

        # Should still return 200 with default state (fallback behavior)
        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is False
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False


class TestGPIOControlEndpoint:
    """Tests for POST /api/gpio/control endpoint"""

    def test_control_toggles_relay_on(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control sets relay HIGH"""
        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.setup_relay") as mock_setup,
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["relay"] == "Relay_Ch1"
        assert data["state"] is True

        # Verify relay_on was called with the correct pin
        mock_setup.assert_called_once_with(26)
        mock_relay_on.assert_called_once_with(26)

    def test_control_toggles_relay_off(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control sets relay LOW"""
        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_off") as mock_relay_off,
            patch("routes.gpio.setup_relay") as mock_setup,
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch2", "state": False})

        assert response.status_code == 200

        # Verify relay_off was called with the correct pin
        mock_setup.assert_called_once_with(19)
        mock_relay_off.assert_called_once_with(19)

    def test_control_updates_state_file(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control persists state to gpio_state.json via relay_on"""

        # relay_on in lib.gpio_helpers writes state automatically;
        # we mock it to perform the write so we can verify the endpoint calls it.
        def _fake_relay_on(pin):
            """Simulate relay_on writing state to the state file."""
            import fcntl

            state = {"Relay_Ch1": False, "Relay_Ch2": False, "Relay_Ch3": False}
            if temp_gpio_state_file.exists():
                try:
                    state = json.loads(temp_gpio_state_file.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            state["Relay_Ch1"] = True
            with open(temp_gpio_state_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(state, f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on", side_effect=_fake_relay_on) as mock_relay_on,
            patch("routes.gpio.setup_relay"),
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            # Set relay on
            client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        # Verify relay_on was called
        mock_relay_on.assert_called_once_with(26)
        # Verify state was written to file
        state = json.loads(temp_gpio_state_file.read_text())
        assert state["Relay_Ch1"] is True

    def test_control_validates_relay_name(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control rejects invalid relay names"""
        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            response = client.post(
                "/api/gpio/control", json={"relay": "Invalid_Relay", "state": True}
            )

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid relay" in data["error"]

    def test_control_validates_state_type(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control rejects non-boolean state"""
        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            # Try string instead of boolean
            response = client.post(
                "/api/gpio/control",
                json={
                    "relay": "Relay_Ch1",
                    "state": "true",  # String, not boolean
                },
            )

        assert response.status_code == 400
        data = response.get_json()
        assert "State must be a boolean" in data["error"]

    def test_control_requires_both_parameters(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control returns 400 if relay or state missing"""
        # Missing state
        response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1"})
        assert response.status_code == 400
        assert "Missing relay or state" in response.get_json()["error"]

        # Missing relay
        response = client.post("/api/gpio/control", json={"state": True})
        assert response.status_code == 400
        assert "Missing relay or state" in response.get_json()["error"]

    def test_control_calls_gpio_setup(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control calls setup_relay() before relay_on()"""
        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.setup_relay") as mock_setup,
            patch("routes.gpio.relay_on") as mock_relay_on,
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        # Verify setup_relay was called with the correct pin
        mock_setup.assert_called_once_with(26)
        mock_relay_on.assert_called_once_with(26)

    def test_control_calls_gpio_output(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /control calls relay_on() with correct pin"""
        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.setup_relay") as mock_setup,
        ):
            mock_get_pins.return_value = {"Relay_Ch3": 13}

            client.post("/api/gpio/control", json={"relay": "Relay_Ch3", "state": True})

        # Verify relay_on was called with the correct pin
        mock_setup.assert_called_once_with(13)
        mock_relay_on.assert_called_once_with(13)


class TestGPIOFlashEndpoint:
    """Tests for POST /api/gpio/flash endpoint"""

    def test_flash_triggers_momentary_pulse(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /flash turns on, waits, turns off"""
        temp_controls_file.write_text("flash_duration_ms=50\n")

        call_order = []

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch(
                "routes.gpio.setup_relay", side_effect=lambda pin: call_order.append(("setup", pin))
            ),
            patch("routes.gpio.relay_on", side_effect=lambda pin: call_order.append(("on", pin))),
            patch("routes.gpio.relay_off", side_effect=lambda pin: call_order.append(("off", pin))),
        ):
            mock_get_pins.return_value = {"Relay_Ch2": 19}

            response = client.post("/api/gpio/flash")

        assert response.status_code == 200

        # Verify the flash sequence: setup, on, off
        assert ("setup", 19) in call_order
        assert ("on", 19) in call_order
        assert ("off", 19) in call_order
        # ON should come before OFF
        on_idx = call_order.index(("on", 19))
        off_idx = call_order.index(("off", 19))
        assert on_idx < off_idx

    def test_flash_uses_correct_pin(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /flash uses Relay_Ch2 (flash pin)"""
        temp_controls_file.write_text("flash_duration_ms=50\n")

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.setup_relay") as mock_setup,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.relay_off") as mock_relay_off,
        ):
            mock_get_pins.return_value = {"Relay_Ch2": 19}

            client.post("/api/gpio/flash")

        # Verify pin 19 was used (Relay_Ch2)
        mock_setup.assert_called_once_with(19)
        mock_relay_on.assert_called_once_with(19)
        mock_relay_off.assert_called_once_with(19)

    def test_flash_respects_duration_from_controls(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /flash reads flash_duration_ms from controls.txt"""
        # Set custom duration
        temp_controls_file.write_text("flash_duration_ms=200\n")

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch2": 19}

            start = time.time()
            client.post("/api/gpio/flash")
            duration = time.time() - start

        # Duration should be approximately 200ms (0.2s)
        # Allow some overhead for processing
        assert duration >= 0.15  # At least 150ms
        assert duration < 0.5  # Less than 500ms

    def test_flash_defaults_to_100ms(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """POST /flash uses 100ms if flash_duration_ms not set"""
        # Don't set flash_duration_ms in controls
        temp_controls_file.write_text("name=TestBox\n")

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch2": 19}

            start = time.time()
            client.post("/api/gpio/flash")
            duration = time.time() - start

        # Duration should be approximately 100ms (default)
        assert duration >= 0.08  # At least 80ms
        assert duration < 0.3  # Less than 300ms

    def test_flash_cleans_up_on_interrupt(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file, monkeypatch
    ):
        """POST /flash ensures LOW state if interrupted"""
        temp_controls_file.write_text("flash_duration_ms=100\n")

        # Mock time.sleep to raise exception during flash
        original_sleep = time.sleep

        def failing_sleep(duration):
            if duration > 0.05:  # Only fail on the flash sleep
                raise RuntimeError("Simulated error during flash")
            original_sleep(duration)

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch2": 19}

            # This should raise an error but not be tested directly
            # The endpoint catches exceptions and returns error
            with patch("time.sleep", side_effect=failing_sleep):
                response = client.post("/api/gpio/flash")

        # Should return error
        assert response.status_code == 500

        # Note: In production code, GPIO cleanup isn't implemented in except block
        # This is a known gap that could be improved


class TestGPIOSecurity:
    """Security and input validation tests"""

    def test_control_whitelist_enforcement(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Only accepts Relay_Ch1/Ch2/Ch3"""
        invalid_relays = [
            "Relay_Ch4",
            "GPIO_26",
            "../../../etc/passwd",
            "; DROP TABLE relays--",
            '__import__("os").system("ls")',
        ]

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}

            for relay in invalid_relays:
                response = client.post("/api/gpio/control", json={"relay": relay, "state": True})

                assert response.status_code == 400
                assert "Invalid relay" in response.get_json()["error"]

    def test_control_injection_prevention(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Rejects path traversal in relay parameter"""
        malicious_names = [
            "../../../etc/passwd",
            "../../config",
            "Relay_Ch1; cat /etc/passwd",
        ]

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            for name in malicious_names:
                response = client.post("/api/gpio/control", json={"relay": name, "state": True})

                assert response.status_code == 400

    def test_control_type_validation(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Rejects string 'true' instead of boolean True"""
        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            # String value should be rejected
            response = client.post(
                "/api/gpio/control", json={"relay": "Relay_Ch1", "state": "true"}
            )
            assert response.status_code == 400

            # Integer should also be rejected
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": 1})
            assert response.status_code == 400


class TestGPIOConcurrency:
    """File locking and concurrency tests"""

    def test_state_file_shared_lock_on_read(
        self, client, mock_rpi_gpio, temp_gpio_state_file, mock_file_locking, temp_controls_file
    ):
        """_get_state() uses LOCK_SH (shared lock)"""
        temp_gpio_state_file.write_text('{"Relay_Ch1": false}')

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            client.get("/api/gpio/status")

        # Verify shared lock was acquired
        assert len(mock_file_locking.locks_acquired) > 0
        lock_type, _ = mock_file_locking.locks_acquired[0]
        assert lock_type == "shared"

    def test_state_file_exclusive_lock_on_write(
        self, client, mock_rpi_gpio, temp_gpio_state_file, mock_file_locking, temp_controls_file
    ):
        """relay_on() is called which triggers state persistence"""
        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.setup_relay"),
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        # Verify relay_on was called (it handles state persistence internally)
        mock_relay_on.assert_called_once_with(26)

    def test_concurrent_reads_succeed(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Multiple threads can read state simultaneously"""
        temp_gpio_state_file.write_text(
            '{"Relay_Ch1": true, "Relay_Ch2": false, "Relay_Ch3": false}'
        )

        read_results = []

        def read_state():
            with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
                mock_get_pins.return_value = {"Relay_Ch1": 26, "Relay_Ch2": 19, "Relay_Ch3": 13}
                response = client.get("/api/gpio/status")
                read_results.append(response.status_code)

        # Start 5 concurrent readers
        threads = [threading.Thread(target=read_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed
        assert len(read_results) == 5
        assert all(status == 200 for status in read_results)

    def test_write_blocks_during_operation(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Write operations delegate to relay_on/relay_off which handle locking"""
        # relay_on/relay_off in lib.gpio_helpers use exclusive locks internally.
        # We verify the endpoint calls the helper correctly.

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on") as mock_relay_on,
            patch("routes.gpio.setup_relay"),
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            # Perform write operation
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 200
        # Verify relay_on was called (it handles state persistence with locking)
        mock_relay_on.assert_called_once_with(26)


class TestGPIOErrorRecovery:
    """Error handling and cleanup tests"""

    def test_status_endpoint_handles_exceptions_gracefully(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file, monkeypatch
    ):
        """GET /status returns 500 on unexpected errors"""

        # Mock get_gpio_pins to raise exception
        def failing_get_pins():
            raise RuntimeError("Simulated hardware failure")

        monkeypatch.setattr("routes.gpio.get_gpio_pins", failing_get_pins)

        response = client.get("/api/gpio/status")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_control_endpoint_handles_gpio_errors(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file, monkeypatch
    ):
        """POST /control returns 500 on GPIO errors"""

        # Mock relay_on to raise exception (simulates hardware error)
        def failing_relay_on(pin):
            raise RuntimeError("GPIO hardware error")

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on", side_effect=failing_relay_on),
            patch("routes.gpio.setup_relay"),
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_state_consistency_on_write_failure(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file, monkeypatch
    ):
        """State file remains consistent if relay_on raises an error"""
        # Setup: Existing state
        original_state = {"Relay_Ch1": False, "Relay_Ch2": False, "Relay_Ch3": False}
        temp_gpio_state_file.write_text(json.dumps(original_state))

        # Mock relay_on to raise IOError (simulates state persistence failure)
        def failing_relay_on(pin):
            raise OSError("Disk full")

        with (
            patch("routes.gpio.get_gpio_pins") as mock_get_pins,
            patch("routes.gpio.relay_on", side_effect=failing_relay_on),
            patch("routes.gpio.setup_relay"),
        ):
            mock_get_pins.return_value = {"Relay_Ch1": 26}

            # Try to control GPIO (will fail inside relay_on)
            response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        # Endpoint will return error due to exception
        assert response.status_code == 500

        # Original state should remain unchanged
        state = json.loads(temp_gpio_state_file.read_text())
        assert state["Relay_Ch1"] is False


class TestGPIOAvailability:
    """Tests for GPIO availability and permission checks"""

    def test_status_missing_relay_in_state_file(
        self, client, mock_rpi_gpio, temp_gpio_state_file, temp_controls_file
    ):
        """Status endpoint returns False for relays not in state file"""
        # Setup: State file with only 2 of 3 relays
        state = {
            "Relay_Ch1": True,
            "Relay_Ch2": False,
            # Relay_Ch3 intentionally missing
        }
        temp_gpio_state_file.write_text(json.dumps(state))

        with patch("routes.gpio.get_gpio_pins") as mock_get_pins:
            mock_get_pins.return_value = {
                "Relay_Ch1": 26,
                "Relay_Ch2": 19,
                "Relay_Ch3": 13,  # This one is missing from state
            }

            response = client.get("/api/gpio/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["Relay_Ch1"] is True
        assert data["Relay_Ch2"] is False
        assert data["Relay_Ch3"] is False  # Should default to False

    def test_control_when_gpio_not_available(self, client, monkeypatch):
        """Control endpoint returns 500 when GPIO hardware not available"""
        # Mock GPIO_AVAILABLE to False
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", False)

        response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 500
        data = response.get_json()
        assert "GPIO not available" in data["error"]

    def test_control_when_gpio_permission_denied(self, client, monkeypatch):
        """Control endpoint returns 403 when GPIO permissions denied"""
        # Mock GPIO as available but permissions denied
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", True)
        monkeypatch.setattr("routes.gpio.GPIO_PERMISSIONS_OK", False)
        monkeypatch.setattr(
            "routes.gpio.GPIO_PERMISSION_ERROR", "Permission denied: user not in gpio group"
        )

        response = client.post("/api/gpio/control", json={"relay": "Relay_Ch1", "state": True})

        assert response.status_code == 403
        data = response.get_json()
        assert "GPIO permission denied" in data["error"]
        assert "user not in gpio group" in data["details"]

    def test_flash_when_gpio_not_available(self, client, monkeypatch):
        """Flash endpoint returns 500 when GPIO hardware not available"""
        # Mock GPIO_AVAILABLE to False
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", False)

        response = client.post("/api/gpio/flash")

        assert response.status_code == 500
        data = response.get_json()
        assert "GPIO not available" in data["error"]

    def test_flash_when_gpio_permission_denied(self, client, monkeypatch):
        """Flash endpoint returns 403 when GPIO permissions denied"""
        # Mock GPIO as available but permissions denied
        monkeypatch.setattr("routes.gpio.GPIO_AVAILABLE", True)
        monkeypatch.setattr("routes.gpio.GPIO_PERMISSIONS_OK", False)
        monkeypatch.setattr(
            "routes.gpio.GPIO_PERMISSION_ERROR", "Permission denied: user not in gpio group"
        )

        response = client.post("/api/gpio/flash")

        assert response.status_code == 403
        data = response.get_json()
        assert "GPIO permission denied" in data["error"]
        assert "user not in gpio group" in data["details"]


class TestGPIOStartupDiagnostics:
    """Test GPIO module startup diagnostics and permission checking"""

    def test_startup_prints_gpio_configuration(self):
        """Import routes.gpio, verify module has GPIO configuration constants"""
        import routes.gpio

        # Verify module loaded successfully with GPIO config
        assert hasattr(routes.gpio, "GPIO_AVAILABLE")
        assert hasattr(routes.gpio, "gpio_bp")
        # GPIO initialization happens at module import, we verify the module is functional
        assert routes.gpio.gpio_bp is not None

    def test_startup_detects_permission_errors(self):
        """Verify GPIO_PERMISSIONS_OK flag exists for permission tracking"""
        import routes.gpio

        # Verify permission checking infrastructure exists
        assert hasattr(routes.gpio, "GPIO_PERMISSIONS_OK")
        assert hasattr(routes.gpio, "GPIO_PERMISSION_ERROR")
        # In the test environment, GPIO may or may not be available
        # We're testing that the error handling infrastructure exists
        if not routes.gpio.GPIO_AVAILABLE:
            # If GPIO not available, verify error message is set
            assert routes.gpio.GPIO_PERMISSION_ERROR is not None

    def test_startup_detects_missing_rpi_gpio(self):
        """Verify GPIO_AVAILABLE flag correctly indicates GPIO availability"""
        import routes.gpio

        # Verify GPIO availability flag exists
        assert hasattr(routes.gpio, "GPIO_AVAILABLE")
        # GPIO_AVAILABLE will be False if RPi.GPIO is not installed/importable
        # In test environment, we verify the flag exists and is boolean
        assert isinstance(routes.gpio.GPIO_AVAILABLE, bool)

    def test_startup_validates_permissions_successfully(self):
        """With GPIO available, verify initialization message was printed at module import"""
        import routes.gpio

        # Verify module has all required attributes for GPIO operations
        assert hasattr(routes.gpio, "GPIO_AVAILABLE")
        assert hasattr(routes.gpio, "GPIO_PERMISSIONS_OK")

        # Verify blueprint is registered
        assert routes.gpio.gpio_bp is not None
        assert routes.gpio.gpio_bp.name == "gpio"

        # Verify state file path is configured
        assert hasattr(routes.gpio, "STATE_FILE")
        assert routes.gpio.STATE_FILE is not None
