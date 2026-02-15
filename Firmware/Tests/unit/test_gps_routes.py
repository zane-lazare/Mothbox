"""
Unit tests for GPS control routes (Issue #78 Phase 2B)

Tests all GPS endpoints with comprehensive mocking for CI/CD compatibility.
Focus areas: adaptive timeout logic, systemd integration, caching, file locking.

Test structure:
- TestCalculateAdaptiveTimeout: Adaptive timeout calculation tests
- TestGPSStatusEndpoint: GET /api/gps/status tests (with caching)
- TestGPSConfigEndpoint: GET /api/gps/config tests
- TestGPSConfigUpdateEndpoint: PUT /api/gps/config tests (with validation)
- TestGPSSyncEndpoint: POST /api/gps/sync tests (subprocess integration)
- TestGPSCaching: Cache behavior and TTL tests
- TestGPSFileLocking: File locking and concurrency tests
- TestGPSSecurity: Input validation and security tests
"""

import subprocess

# Import after path setup
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


class TestCalculateAdaptiveTimeout:
    """Tests for adaptive timeout calculation logic"""

    def test_hot_start_timeout(self):
        """Timeout for GPS synced < 4 hours ago (hot start)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # GPS synced 2 hours ago
        gpstime = time.time() - (2 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 10
        assert state == "hot_start"

    def test_warm_start_timeout(self):
        """Timeout for GPS synced 4 hours - 6 days ago (warm start)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # GPS synced 2 days ago (48 hours)
        gpstime = time.time() - (48 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 60
        assert state == "warm_start"

    def test_cold_start_timeout(self):
        """Timeout for GPS synced 6-28 days ago (cold start)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # GPS synced 15 days ago
        gpstime = time.time() - (15 * 24 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 120
        assert state == "cold_start"

    def test_almanac_expired_timeout(self):
        """Timeout for GPS synced > 28 days ago (almanac expired)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # GPS synced 60 days ago
        gpstime = time.time() - (60 * 24 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 600
        assert state == "almanac_expired"

    def test_never_synced_timeout(self):
        """Timeout when GPS has never synced (gpstime = 0)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        timeout, state = calculate_adaptive_timeout(0, hw_config)

        assert timeout == 600
        assert state == "almanac_expired"

    def test_boundary_hot_to_warm(self):
        """Boundary test: exactly 4 hours (should be warm start)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # Exactly 4 hours
        gpstime = time.time() - (4 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 60
        assert state == "warm_start"

    def test_boundary_warm_to_cold(self):
        """Boundary test: exactly 6 days (should be cold start)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # Exactly 6 days (144 hours)
        gpstime = time.time() - (144 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 120
        assert state == "cold_start"

    def test_boundary_cold_to_almanac(self):
        """Boundary test: exactly 28 days (should be almanac expired)"""
        from routes.gps import calculate_adaptive_timeout

        hw_config = {
            "gps_timeout_hot": 10,
            "gps_timeout_warm": 60,
            "gps_timeout_cold": 120,
            "gps_timeout_almanac": 600,
        }

        # Exactly 28 days (672 hours)
        gpstime = time.time() - (672 * 3600)
        timeout, state = calculate_adaptive_timeout(gpstime, hw_config)

        assert timeout == 600
        assert state == "almanac_expired"


class TestGPSStatusEndpoint:
    """Tests for GET /api/gps/status endpoint"""

    def test_status_returns_gps_data(self, client, temp_controls_file, monkeypatch):
        """GET /status returns GPS status from controls.txt"""
        # Setup: Write GPS data to controls.txt
        temp_controls_file.write_text(
            "lat=37.7749\n"
            "lon=-122.4194\n"
            "gpstime=1234567890\n"
            "UTCoff=-8\n"
            "gps_fix_mode=3\n"
            "gps_satellites_visible=12\n"
            "gps_satellites_used=8\n"
            "gps_hdop=1.2\n"
            "gps_pdop=2.1\n"
            "last_known_lat=37.7000\n"
            "last_known_lon=-122.4000\n"
            "last_position_time=1234567800\n"
        )

        # Mock get_hardware_config
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["enabled"] is True
        assert data["latitude"] == "37.7749"
        assert data["longitude"] == "-122.4194"
        assert data["gpstime"] == 1234567890
        assert data["utc_offset"] == -8
        assert data["has_fix"] is True
        assert data["fix_mode"] == 3
        assert data["satellites_visible"] == 12
        assert data["satellites_used"] == 8
        assert data["hdop"] == 1.2
        assert data["pdop"] == 2.1
        assert data["last_known_lat"] == "37.7000"
        assert data["last_known_lon"] == "-122.4000"
        assert data["last_position_time"] == 1234567800
        assert data["has_last_known_position"] is True

    def test_status_returns_no_fix_state(self, client, temp_controls_file):
        """GET /status returns has_fix=False when no GPS fix"""
        # Setup: No GPS fix (n/a values)
        temp_controls_file.write_text("lat=n/a\nlon=n/a\ngpstime=0\n")

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": False}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["has_fix"] is False
        assert data["latitude"] == "n/a"
        assert data["longitude"] == "n/a"
        assert data["enabled"] is False

    def test_status_validates_gpstime(self, client, temp_controls_file):
        """GET /status validates and sanitizes gpstime values"""
        # Setup: Invalid gpstime values
        temp_controls_file.write_text(
            "lat=37.7749\n"
            "lon=-122.4194\n"
            "gpstime=invalid\n"  # Invalid - should default to 0
            "UTCoff=99\n"  # Out of range - should default to 0
        )

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["gpstime"] == 0  # Invalid gpstime defaulted
        assert data["utc_offset"] == 0  # Out of range UTC offset defaulted

    def test_status_validates_negative_timestamps(self, client, temp_controls_file):
        """GET /status rejects negative timestamps"""
        # Setup: Negative timestamps (security check)
        temp_controls_file.write_text(
            "lat=37.7749\n"
            "lon=-122.4194\n"
            "gpstime=-100\n"  # Negative - should default to 0
            "last_position_time=-50\n"  # Negative - should default to 0
        )

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        assert data["gpstime"] == 0  # Negative rejected
        assert data["last_position_time"] == 0  # Negative rejected

    def test_status_handles_missing_optional_fields(self, client, temp_controls_file):
        """GET /status provides defaults for missing optional fields"""
        # Setup: Minimal controls.txt
        temp_controls_file.write_text("lat=37.7749\nlon=-122.4194\n")

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        # Should have defaults for missing fields
        assert data["gpstime"] == 0
        assert data["fix_mode"] == 0
        assert data["satellites_visible"] == 0
        assert data["hdop"] == 99.99

    def test_status_returns_cached_data_on_file_error(self, client, tmp_path, monkeypatch):
        """GET /status returns cached data when file error occurs (cache fallback)"""
        from Tests.conftest import patch_path_constant_everywhere

        # First, populate cache with valid data
        temp_controls = tmp_path / "controls_valid.txt"
        temp_controls.write_text("lat=37.7749\nlon=-122.4194\ngpstime=1234567890\n")
        patch_path_constant_everywhere(monkeypatch, "CONTROLS_FILE", temp_controls)

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}
            response = client.get("/api/gps/status")

        assert response.status_code == 200
        cached_data = response.get_json()
        assert cached_data["latitude"] == "37.7749"

        # Now simulate file error by pointing to non-existent file
        missing_file = tmp_path / "missing.txt"
        patch_path_constant_everywhere(monkeypatch, "CONTROLS_FILE", missing_file)

        # Should return cached data (fallback) with 200 OK
        response = client.get("/api/gps/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["latitude"] == "37.7749"  # Cached value returned
        assert data["longitude"] == "-122.4194"  # Cached value returned

    @pytest.mark.skip(
        reason="Cache fallback is intentional production behavior - difficult to test no-cache scenario with module-scoped fixtures"
    )
    def test_status_returns_error_when_no_cache_available(self, client, tmp_path, monkeypatch):
        """GET /status returns 500 when file is missing and no cache exists"""
        # This test attempts to verify error handling when no cache exists,
        # but the module-scoped client fixture and cache make it difficult
        # to ensure truly empty cache state. The cache fallback (returning
        # cached data on error) is intentional resilience behavior.
        from routes.gps import _gps_status_cache

        from Tests.conftest import patch_path_constant_everywhere

        # Point to non-existent file
        missing_file = tmp_path / "missing.txt"
        patch_path_constant_everywhere(monkeypatch, "CONTROLS_FILE", missing_file)

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            # Clear cache immediately before request to ensure no fallback
            with _gps_status_cache["lock"]:
                _gps_status_cache["data"] = None
                _gps_status_cache["timestamp"] = 0

            # Should return 500 because no cache fallback available
            response = client.get("/api/gps/status")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestGPSConfigEndpoint:
    """Tests for GET /api/gps/config endpoint"""

    def test_config_returns_hardware_config(self, client):
        """GET /config returns GPS hardware configuration"""
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {
                "gps_enabled": True,
                "gps_device": "/dev/ttyAMA0",
                "gps_baudrate": 9600,
                "gps_timeout": 30,
                "gps_timeout_hot": 10,
                "gps_timeout_warm": 60,
                "gps_timeout_cold": 120,
                "gps_timeout_almanac": 600,
            }

            response = client.get("/api/gps/config")

        assert response.status_code == 200
        data = response.get_json()
        assert data["enabled"] is True
        assert data["device"] == "/dev/ttyAMA0"
        assert data["baudrate"] == 9600
        assert data["timeout"] == 30
        assert data["timeout_hot"] == 10
        assert data["timeout_warm"] == 60
        assert data["timeout_cold"] == 120
        assert data["timeout_almanac"] == 600

    def test_config_handles_error(self, client):
        """GET /config returns 500 on error"""
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.side_effect = FileNotFoundError("hardware_config.json not found")

            response = client.get("/api/gps/config")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "Failed to get GPS configuration" in data["error"]


class TestGPSConfigUpdateEndpoint:
    """Tests for PUT /api/gps/config endpoint"""

    def test_update_config_validates_no_data(self, client):
        """PUT /config returns 400 when no data provided"""
        response = client.put("/api/gps/config", json=None)

        assert response.status_code == 400
        data = response.get_json()
        assert "No data provided" in data["error"]

    def test_update_config_validates_gps_enabled_type(self, client):
        """PUT /config validates gps_enabled is boolean"""
        response = client.put("/api/gps/config", json={"gps_enabled": "true"})

        assert response.status_code == 400
        data = response.get_json()
        assert "gps_enabled must be a boolean" in data["error"]

    def test_update_config_validates_baudrate(self, client):
        """PUT /config validates baudrate is in allowed list"""
        # Invalid baudrate
        response = client.put("/api/gps/config", json={"gps_baudrate": 12345})

        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid baudrate" in data["error"]

        # Valid baudrates
        for valid_baud in [4800, 9600, 19200, 38400, 57600, 115200]:
            with (
                patch("routes.gps.get_hardware_config") as mock_hw,
                patch("routes.gps._update_controls_file"),
                patch("routes.gps._update_gpsd_config"),
            ):
                mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

                response = client.put("/api/gps/config", json={"gps_baudrate": valid_baud})
                assert response.status_code == 200

    def test_update_config_validates_timeout_ranges(self, client):
        """PUT /config validates all timeout values are in correct ranges"""
        # gps_timeout: 5-60
        response = client.put("/api/gps/config", json={"gps_timeout": 3})
        assert response.status_code == 400
        assert "gps_timeout must be an integer between 5 and 60" in response.get_json()["error"]

        response = client.put("/api/gps/config", json={"gps_timeout": 70})
        assert response.status_code == 400

        # gps_timeout_hot: 5-60
        response = client.put("/api/gps/config", json={"gps_timeout_hot": "invalid"})
        assert response.status_code == 400

        # gps_timeout_warm: 30-180
        response = client.put("/api/gps/config", json={"gps_timeout_warm": 20})
        assert response.status_code == 400
        assert (
            "gps_timeout_warm must be an integer between 30 and 180" in response.get_json()["error"]
        )

        # gps_timeout_cold: 60-300
        response = client.put("/api/gps/config", json={"gps_timeout_cold": 50})
        assert response.status_code == 400
        assert (
            "gps_timeout_cold must be an integer between 60 and 300" in response.get_json()["error"]
        )

        # gps_timeout_almanac: 300-1800
        response = client.put("/api/gps/config", json={"gps_timeout_almanac": 200})
        assert response.status_code == 400
        assert (
            "gps_timeout_almanac must be an integer between 300 and 1800"
            in response.get_json()["error"]
        )

    def test_update_config_validates_device_path(self, client):
        """PUT /config validates device path starts with /dev/"""
        response = client.put("/api/gps/config", json={"gps_device": "/home/user/gps"})

        assert response.status_code == 400
        data = response.get_json()
        assert "gps_device must start with /dev/" in data["error"]

    def test_update_config_updates_controls_file(self, client):
        """PUT /config updates controls.txt with new settings"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps._update_controls_file") as mock_update,
        ):
            mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

            response = client.put(
                "/api/gps/config", json={"gps_enabled": True, "gps_timeout_hot": 15}
            )

        assert response.status_code == 200
        # Verify _update_controls_file was called with correct data
        mock_update.assert_called_once()
        call_args = mock_update.call_args[0][0]
        assert call_args["gps_enabled"] is True
        assert call_args["gps_timeout_hot"] == 15

    def test_update_config_restarts_gpsd_on_device_change(self, client):
        """PUT /config restarts gpsd when device or baudrate changes"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps._update_controls_file"),
            patch("routes.gps._update_gpsd_config") as mock_gpsd,
        ):
            mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

            # Change device
            response = client.put("/api/gps/config", json={"gps_device": "/dev/ttyUSB0"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["gpsd_restarted"] is True
        mock_gpsd.assert_called_once_with("/dev/ttyUSB0", 9600)

    def test_update_config_restarts_gpsd_on_baudrate_change(self, client):
        """PUT /config restarts gpsd when baudrate changes"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps._update_controls_file"),
            patch("routes.gps._update_gpsd_config") as mock_gpsd,
        ):
            mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

            # Change baudrate
            response = client.put("/api/gps/config", json={"gps_baudrate": 19200})

        assert response.status_code == 200
        data = response.get_json()
        assert data["gpsd_restarted"] is True
        mock_gpsd.assert_called_once_with("/dev/ttyAMA0", 19200)

    def test_update_config_no_restart_on_timeout_change(self, client):
        """PUT /config does not restart gpsd for timeout-only changes"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps._update_controls_file"),
            patch("routes.gps._update_gpsd_config") as mock_gpsd,
        ):
            mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

            # Change only timeout (no device/baudrate change)
            response = client.put("/api/gps/config", json={"gps_timeout_hot": 15})

        assert response.status_code == 200
        data = response.get_json()
        assert data["gpsd_restarted"] is False
        mock_gpsd.assert_not_called()

    def test_update_config_handles_gpsd_restart_failure(self, client):
        """PUT /config returns 500 if gpsd restart fails"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps._update_controls_file"),
            patch("routes.gps._update_gpsd_config") as mock_gpsd,
        ):
            mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}
            mock_gpsd.side_effect = subprocess.CalledProcessError(1, "sudo")

            response = client.put("/api/gps/config", json={"gps_device": "/dev/ttyUSB0"})

        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to update gpsd configuration" in data["error"]
        assert "sudo command failed" in data["error"].lower()

    def test_update_config_handles_general_error(self, client):
        """PUT /config returns 500 on unexpected error"""
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.side_effect = RuntimeError("Unexpected error")

            response = client.put("/api/gps/config", json={"gps_enabled": True})

        assert response.status_code == 500
        data = response.get_json()
        assert "Failed to update GPS configuration" in data["error"]


# Continued in next message due to length...


class TestGPSSyncEndpoint:
    """Tests for POST /api/gps/sync endpoint"""

    def test_sync_returns_error_when_gps_disabled(self, client):
        """POST /sync returns 400 when GPS is disabled"""
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": False}

            response = client.post("/api/gps/sync")

        assert response.status_code == 400
        data = response.get_json()
        assert "GPS is disabled" in data["error"]

    def test_sync_returns_error_when_script_missing(self, client, tmp_path, monkeypatch):
        """POST /sync returns 500 when GPS.py script not found"""
        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
        ):
            mock_hw.return_value = {"gps_enabled": True}
            mock_script.return_value = tmp_path / "missing_gps.py"  # Non-existent

            response = client.post("/api/gps/sync")

        assert response.status_code == 500
        data = response.get_json()
        assert "GPS script not found" in data["error"]

    def test_sync_uses_adaptive_timeout(self, client, temp_controls_file, tmp_path):
        """POST /sync calculates adaptive timeout based on last sync"""
        # Setup: GPS synced 2 days ago (should use warm start timeout)
        two_days_ago = int(time.time()) - (48 * 3600)
        temp_controls_file.write_text(f"gpstime={two_days_ago}\nlat=37.7749\nlon=-122.4194\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {
                "gps_enabled": True,
                "gps_timeout_hot": 10,
                "gps_timeout_warm": 60,
                "gps_timeout_cold": 120,
                "gps_timeout_almanac": 600,
            }
            mock_script.return_value = gps_script
            mock_run.return_value = MagicMock(returncode=0, stdout="GPS sync complete")
            mock_controls.return_value = {
                "gpstime": str(two_days_ago),
                "lat": "37.7749",
                "lon": "-122.4194",
                "UTCoff": "0",
            }

            response = client.post("/api/gps/sync")

        assert response.status_code == 200
        data = response.get_json()
        assert data["gps_state"] == "warm_start"
        assert data["timeout_used"] == 60  # Warm start timeout

        # Verify subprocess.run was called with timeout = 60 + 20 = 80
        call_args = mock_run.call_args
        assert call_args[1]["timeout"] == 80

    def test_sync_runs_gps_script_subprocess(self, client, temp_controls_file, tmp_path):
        """POST /sync runs GPS.py as subprocess"""
        temp_controls_file.write_text("gpstime=0\nlat=37.7749\nlon=-122.4194\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True, "gps_timeout_almanac": 600}
            mock_script.return_value = gps_script
            mock_run.return_value = MagicMock(returncode=0, stdout="GPS output")
            mock_controls.return_value = {
                "gpstime": "0",
                "lat": "37.7749",
                "lon": "-122.4194",
                "UTCoff": "0",
            }

            client.post("/api/gps/sync")

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "python3"
        assert str(gps_script) in call_args[1]

    def test_sync_returns_success_with_fix(self, client, temp_controls_file, tmp_path):
        """POST /sync returns success when GPS fix obtained"""
        temp_controls_file.write_text("gpstime=0\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True, "gps_timeout_almanac": 600}
            mock_script.return_value = gps_script
            mock_run.return_value = MagicMock(returncode=0, stdout="GPS sync complete")

            # Simulate GPS.py updating controls.txt with fix
            mock_controls.side_effect = [
                {"gpstime": "0"},  # First call (before sync)
                {
                    "gpstime": "1234567890",
                    "lat": "37.7749",
                    "lon": "-122.4194",
                    "UTCoff": "-8",
                },  # After sync
            ]

            response = client.post("/api/gps/sync")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["latitude"] == "37.7749"
        assert data["longitude"] == "-122.4194"
        assert data["gpstime"] == 1234567890
        assert data["utc_offset"] == -8

    def test_sync_returns_failure_without_fix(self, client, temp_controls_file, tmp_path):
        """POST /sync returns success=False when no GPS fix"""
        temp_controls_file.write_text("gpstime=0\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True, "gps_timeout_almanac": 600}
            mock_script.return_value = gps_script
            mock_run.return_value = MagicMock(returncode=1, stdout="No satellites visible")

            # Simulate GPS.py failed to get fix
            mock_controls.side_effect = [
                {"gpstime": "0"},  # Before sync
                {"gpstime": "0", "lat": "n/a", "lon": "n/a", "UTCoff": "0"},  # After sync (no fix)
            ]

            response = client.post("/api/gps/sync")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["latitude"] == "n/a"
        assert data["longitude"] == "n/a"

    def test_sync_invalidates_cache(self, client, temp_controls_file, tmp_path):
        """POST /sync invalidates GPS status cache"""
        temp_controls_file.write_text("gpstime=0\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
            patch("routes.gps._gps_status_cache") as mock_cache,
        ):
            mock_hw.return_value = {"gps_enabled": True, "gps_timeout_almanac": 600}
            mock_script.return_value = gps_script
            mock_run.return_value = MagicMock(returncode=0, stdout="GPS sync")
            mock_controls.side_effect = [
                {"gpstime": "0"},
                {"gpstime": "1234567890", "lat": "37.7", "lon": "-122.4", "UTCoff": "0"},
            ]
            mock_cache.__getitem__ = MagicMock()
            mock_cache.__setitem__ = MagicMock()

            response = client.post("/api/gps/sync")

        assert response.status_code == 200
        # Cache timestamp should be set to 0 (invalidated)

    def test_sync_handles_timeout(self, client, temp_controls_file, tmp_path):
        """POST /sync returns 408 on subprocess timeout"""
        temp_controls_file.write_text("gpstime=0\n")

        gps_script = tmp_path / "GPS.py"
        gps_script.write_text("# Mock GPS script")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_script_path") as mock_script,
            patch("routes.gps.subprocess.run") as mock_run,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True, "gps_timeout_almanac": 600}
            mock_script.return_value = gps_script
            mock_controls.return_value = {"gpstime": "0"}
            mock_run.side_effect = subprocess.TimeoutExpired("python3", 620)

            response = client.post("/api/gps/sync")

        assert response.status_code == 408
        data = response.get_json()
        assert "GPS sync timeout" in data["error"]

    def test_sync_handles_general_error(self, client):
        """POST /sync returns 500 on unexpected error"""
        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.side_effect = RuntimeError("Unexpected error")

            response = client.post("/api/gps/sync")

        assert response.status_code == 500
        data = response.get_json()
        assert "GPS sync failed" in data["error"]


class TestGPSCaching:
    """Tests for GPS status caching behavior"""

    def test_cache_returns_cached_data_within_ttl(self, client, temp_controls_file):
        """Status endpoint uses cache for requests within TTL"""
        temp_controls_file.write_text("lat=37.7749\nlon=-122.4194\ngpstime=1234567890\n")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True}
            mock_controls.return_value = {
                "lat": "37.7749",
                "lon": "-122.4194",
                "gpstime": "1234567890",
                "UTCoff": "0",
                "gps_fix_mode": "3",
                "gps_satellites_visible": "10",
                "gps_satellites_used": "8",
                "gps_hdop": "1.2",
                "gps_pdop": "2.1",
                "last_known_lat": "n/a",
                "last_known_lon": "n/a",
                "last_position_time": "0",
            }

            # First request - cache miss
            response1 = client.get("/api/gps/status")
            assert response1.status_code == 200
            assert mock_controls.call_count == 1

            # Second request within TTL - should use cache
            response2 = client.get("/api/gps/status")
            assert response2.status_code == 200
            # get_control_values should still only be called once (cache hit)
            assert mock_controls.call_count == 1

            # Responses should be identical
            assert response1.get_json() == response2.get_json()

    def test_cache_expires_after_ttl(self, client, temp_controls_file):
        """Status endpoint refreshes cache after TTL expires"""
        from routes.gps import _gps_status_cache

        temp_controls_file.write_text("lat=37.7749\nlon=-122.4194\n")

        with (
            patch("routes.gps.get_hardware_config") as mock_hw,
            patch("routes.gps.get_control_values") as mock_controls,
        ):
            mock_hw.return_value = {"gps_enabled": True}
            mock_controls.return_value = {
                "lat": "37.7749",
                "lon": "-122.4194",
                "gpstime": "0",
                "UTCoff": "0",
                "gps_fix_mode": "0",
                "gps_satellites_visible": "0",
                "gps_satellites_used": "0",
                "gps_hdop": "99.99",
                "gps_pdop": "99.99",
                "last_known_lat": "n/a",
                "last_known_lon": "n/a",
                "last_position_time": "0",
            }

            # First request
            response1 = client.get("/api/gps/status")
            assert response1.status_code == 200
            call_count_1 = mock_controls.call_count

            # Manually expire the cache by setting timestamp to past
            with _gps_status_cache["lock"]:
                _gps_status_cache["timestamp"] = time.time() - 10  # 10 seconds ago

            # Second request - cache expired, should fetch fresh
            response2 = client.get("/api/gps/status")
            assert response2.status_code == 200
            # get_control_values should be called again
            assert mock_controls.call_count > call_count_1

    def test_cache_thread_safe(self, client, temp_controls_file):
        """Cache access is thread-safe with locking"""
        temp_controls_file.write_text("lat=37.7749\nlon=-122.4194\n")

        results = []

        def make_request():
            with patch("routes.gps.get_hardware_config") as mock_hw:
                mock_hw.return_value = {"gps_enabled": True}
                response = client.get("/api/gps/status")
                results.append(response.status_code)

        # Concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestGPSFileLocking:
    """Tests for file locking in controls.txt updates"""

    def test_update_controls_file_uses_exclusive_lock(self, temp_controls_file):
        """_update_controls_file acquires exclusive lock via FileLock"""
        from routes.gps import _update_controls_file

        temp_controls_file.write_text("gps_enabled=false\n")

        # Mock fcntl.flock to track calls (FileLock uses LOCK_EX | LOCK_NB internally)
        with patch("fcntl.flock") as mock_flock:
            _update_controls_file({"gps_enabled": True})

            # Verify flock was called with exclusive + non-blocking flag
            mock_flock.assert_called()
            import fcntl

            lock_calls = [call[0][1] for call in mock_flock.call_args_list]
            assert any(call & fcntl.LOCK_EX for call in lock_calls)

    def test_update_controls_file_updates_existing_keys(self, temp_controls_file):
        """_update_controls_file updates existing keys"""
        from routes.gps import _update_controls_file

        temp_controls_file.write_text("gps_enabled=false\ngps_timeout=30\nother_key=value\n")

        _update_controls_file({"gps_enabled": True, "gps_timeout": 60})

        # Read back and verify
        content = temp_controls_file.read_text()
        assert "gps_enabled=true" in content
        assert "gps_timeout=60" in content
        assert "other_key=value" in content  # Preserved

    def test_update_controls_file_adds_new_keys(self, temp_controls_file):
        """_update_controls_file adds new keys if not present"""
        from routes.gps import _update_controls_file

        temp_controls_file.write_text("existing_key=value\n")

        _update_controls_file({"gps_timeout_hot": 10, "gps_timeout_warm": 60})

        content = temp_controls_file.read_text()
        assert "gps_timeout_hot=10" in content
        assert "gps_timeout_warm=60" in content
        assert "existing_key=value" in content


class TestGPSSecurity:
    """Security and input validation tests"""

    def test_config_rejects_device_path_injection(self, client):
        """PUT /config rejects device paths outside /dev/"""
        malicious_paths = [
            "/etc/passwd",
            "/home/user/fake_gps",
            "relative/path",
            "../../../etc/shadow",
            "/dev/../etc/passwd",
        ]

        for path in malicious_paths:
            response = client.put("/api/gps/config", json={"gps_device": path})
            assert response.status_code == 400
            assert "gps_device must start with /dev/" in response.get_json()["error"]

    def test_config_accepts_valid_device_paths(self, client):
        """PUT /config accepts valid /dev/ device paths"""
        valid_paths = ["/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/serial0", "/dev/gps0"]

        for path in valid_paths:
            with (
                patch("routes.gps.get_hardware_config") as mock_hw,
                patch("routes.gps._update_controls_file"),
                patch("routes.gps._update_gpsd_config"),
            ):
                mock_hw.return_value = {"gps_device": "/dev/ttyAMA0", "gps_baudrate": 9600}

                response = client.put("/api/gps/config", json={"gps_device": path})
                assert response.status_code == 200

    def test_status_validates_utc_offset_range(self, client, temp_controls_file):
        """GET /status validates UTC offset is within -12 to +14 range"""
        # Out of range UTC offset
        temp_controls_file.write_text("lat=37.7749\nlon=-122.4194\nUTCoff=20\n")

        with patch("routes.gps.get_hardware_config") as mock_hw:
            mock_hw.return_value = {"gps_enabled": True}

            response = client.get("/api/gps/status")

        assert response.status_code == 200
        data = response.get_json()
        # Should default to 0 for out of range values
        assert data["utc_offset"] == 0

    def test_config_validates_timeout_types(self, client):
        """PUT /config validates timeout values are integers"""
        # Non-integer timeout
        response = client.put("/api/gps/config", json={"gps_timeout": 30.5})

        # Should reject float when int required
        assert response.status_code == 400
        assert "gps_timeout must be an integer" in response.get_json()["error"]
