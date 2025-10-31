"""
Unit tests for config management routes (Issue #78)

Tests configuration management endpoints with comprehensive mocking for CI/CD compatibility.
Focus areas: security (CSV injection, whitelist enforcement), concurrency, error recovery.

Test structure:
- TestControlsEndpoints: GET/POST /api/config/controls tests
- TestScheduleEndpoints: GET/POST /api/config/schedule tests
- TestWebuiEndpoints: GET/POST /api/config/webui tests
- TestCopySettingsEndpoint: POST /api/config/copy-settings tests
- TestConfigSecurity: Security and validation tests
- TestConfigConcurrency: Concurrent operation tests
- TestConfigErrorRecovery: Error handling and backup/restore tests
"""
import pytest
import json
import csv
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestControlsEndpoints:
    """Tests for GET/POST /api/config/controls endpoints"""

    def test_get_controls_returns_all_keys(self, client, temp_controls_file):
        """GET /controls returns full controls.txt"""
        # Setup: Write known controls
        temp_controls_file.write_text("name=TestBox\nshutdown_enabled=true\nRelay_Ch1=26\n")

        response = client.get('/api/config/controls')

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'TestBox'
        assert data['shutdown_enabled'] == 'true'
        assert data['Relay_Ch1'] == '26'

    def test_post_controls_updates_file(self, client, temp_controls_file):
        """POST /controls writes to controls.txt"""
        response = client.post('/api/config/controls', json={
            'name': 'UpdatedBox',
            'shutdown_enabled': 'false'
        })

        assert response.status_code == 200

        # Verify file was updated
        controls = temp_controls_file.read_text()
        assert 'name=UpdatedBox' in controls
        assert 'shutdown_enabled=false' in controls

    def test_post_controls_validates_keys(self, client, temp_controls_file):
        """POST /controls rejects keys not in ALLOWED_CONTROLS"""
        response = client.post('/api/config/controls', json={
            'invalid_key': 'value',
            'another_bad_key': 'value2'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid keys' in data['error']
        assert 'invalid_key' in data['error']

    def test_post_controls_validates_gpio_pins(self, client, temp_controls_file):
        """POST /controls validates Relay pins are valid BCM pins"""
        # Valid pin
        response = client.post('/api/config/controls', json={'Relay_Ch1': '26'})
        assert response.status_code == 200

        # Invalid pin (not in BCM range)
        response = client.post('/api/config/controls', json={'Relay_Ch1': '50'})
        assert response.status_code == 400

        # Invalid pin (not a number)
        response = client.post('/api/config/controls', json={'Relay_Ch1': 'invalid'})
        assert response.status_code == 400

    def test_post_controls_sanitizes_values(self, client, temp_controls_file):
        """POST /controls removes newlines/CR from values"""
        response = client.post('/api/config/controls', json={
            'name': 'Box\nWith\rNewlines'
        })

        assert response.status_code == 200

        # Verify newlines were removed
        controls = temp_controls_file.read_text()
        assert 'name=BoxWithNewlines' in controls
        assert '\n\n' not in controls  # No double newlines from value

    def test_post_controls_creates_backup(self, client, temp_controls_file, tmp_path, monkeypatch):
        """POST /controls creates timestamped backup"""
        # Setup: Existing controls
        temp_controls_file.write_text("name=OriginalBox\n")

        # Patch create_backup to track if it was called
        backup_calls = []
        original_create_backup = __import__('utils').create_backup

        def mock_create_backup(file_path, keep=5):
            backup_calls.append(file_path)
            return original_create_backup(file_path, keep)

        monkeypatch.setattr('utils.create_backup', mock_create_backup)
        monkeypatch.setattr('routes.config.create_backup', mock_create_backup)

        # Update controls
        response = client.post('/api/config/controls', json={'name': 'NewBox'})

        assert response.status_code == 200
        assert len(backup_calls) > 0  # Backup was created

    def test_post_controls_validates_boolean_values(self, client, temp_controls_file):
        """POST /controls validates boolean fields"""
        # Valid boolean strings
        response = client.post('/api/config/controls', json={'shutdown_enabled': 'true'})
        assert response.status_code == 200

        response = client.post('/api/config/controls', json={'shutdown_enabled': 'false'})
        assert response.status_code == 200

        # Invalid boolean
        response = client.post('/api/config/controls', json={'shutdown_enabled': 'maybe'})
        assert response.status_code == 400

    def test_post_controls_validates_flash_duration(self, client, temp_controls_file):
        """POST /controls validates flash_duration_ms range (50-5000ms)"""
        # Valid duration
        response = client.post('/api/config/controls', json={'flash_duration_ms': '100'})
        assert response.status_code == 200

        # Too short
        response = client.post('/api/config/controls', json={'flash_duration_ms': '10'})
        assert response.status_code == 400

        # Too long
        response = client.post('/api/config/controls', json={'flash_duration_ms': '10000'})
        assert response.status_code == 400


class TestScheduleEndpoints:
    """Tests for GET/POST /api/config/schedule endpoints"""

    def test_get_schedule_returns_csv_row(self, client, tmp_path, monkeypatch):
        """GET /schedule returns first CSV row as dict"""
        # Create temporary schedule file
        schedule_file = tmp_path / "schedule_settings.csv"
        schedule_file.write_text("weekdays,hours,minutes,runtime\n1;2;3,8;9;10,30,120\n")

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', schedule_file)

        response = client.get('/api/config/schedule')

        assert response.status_code == 200
        data = response.get_json()
        assert data['weekdays'] == '1;2;3'
        assert data['hours'] == '8;9;10'
        assert data['minutes'] == '30'
        assert data['runtime'] == '120'

    def test_post_schedule_updates_csv(self, client, tmp_path, monkeypatch):
        """POST /schedule writes to schedule_settings.csv"""
        # Create temporary schedule file
        schedule_file = tmp_path / "schedule_settings.csv"
        schedule_file.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', schedule_file)

        response = client.post('/api/config/schedule', json={
            'weekdays': '1;2;3;4;5',
            'hours': '9;10',
            'minutes': '15',
            'runtime': '90'
        })

        assert response.status_code == 200

        # Verify file was updated
        with open(schedule_file) as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row['weekdays'] == '1;2;3;4;5'
            assert row['runtime'] == '90'

    def test_post_schedule_sanitizes_csv_values(self, client, tmp_path, monkeypatch):
        """POST /schedule applies sanitize_csv_value() to all fields"""
        schedule_file = tmp_path / "schedule_settings.csv"
        schedule_file.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', schedule_file)

        # Try to inject formula
        response = client.post('/api/config/schedule', json={
            'runtime': '=SUM(A1:A10)'  # CSV injection attempt
        })

        assert response.status_code == 200

        # Verify injection was sanitized
        with open(schedule_file) as f:
            content = f.read()
            assert "'=SUM" in content  # Sanitized with prefix

    def test_post_schedule_validates_fieldnames(self, client, tmp_path, monkeypatch):
        """POST /schedule rejects keys not in CSV header"""
        schedule_file = tmp_path / "schedule_settings.csv"
        schedule_file.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', schedule_file)

        response = client.post('/api/config/schedule', json={
            'invalid_field': 'value'
        })

        assert response.status_code == 400
        assert 'not in allowed fields' in response.get_json()['error'].lower()


class TestWebuiEndpoints:
    """Tests for GET/POST /api/config/webui endpoints"""

    def test_get_webui_returns_defaults(self, client, tmp_path, monkeypatch):
        """GET /webui returns default settings if file missing"""
        # Point to non-existent file
        nonexistent = tmp_path / "nonexistent.txt"

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', nonexistent)

        response = client.get('/api/config/webui')

        assert response.status_code == 200
        data = response.get_json()
        # Should have default values
        assert 'jpeg_quality' in data
        assert 'stream_width' in data

    def test_get_webui_loads_from_file(self, client, temp_webui_settings):
        """GET /webui reads liveview_settings.txt"""
        # Write known settings
        temp_webui_settings.write_text("jpeg_quality=90\nstream_width=1280\n")

        response = client.get('/api/config/webui')

        assert response.status_code == 200
        data = response.get_json()
        assert data['jpeg_quality'] == 90
        assert data['stream_width'] == 1280

    def test_get_webui_converts_types(self, client, temp_webui_settings):
        """GET /webui converts string values to correct types"""
        temp_webui_settings.write_text("jpeg_quality=85\nstream_fps=15.0\nautofocus_enabled=true\n")

        response = client.get('/api/config/webui')

        data = response.get_json()
        # Should convert to proper types
        assert isinstance(data['jpeg_quality'], int)
        assert isinstance(data['stream_fps'], float)
        assert isinstance(data['autofocus_enabled'], bool)

    def test_post_webui_validates_ranges(self, client, temp_webui_settings):
        """POST /webui enforces min/max for numeric settings"""
        # Valid range
        response = client.post('/api/config/webui', json={'jpeg_quality': 85})
        assert response.status_code == 200

        # Below minimum
        response = client.post('/api/config/webui', json={'jpeg_quality': 30})
        assert response.status_code == 400

        # Above maximum
        response = client.post('/api/config/webui', json={'jpeg_quality': 150})
        assert response.status_code == 400

    def test_post_webui_validates_enums(self, client, temp_webui_settings):
        """POST /webui validates mode values (af_mode, awb_mode, etc.)"""
        # Valid af_mode
        response = client.post('/api/config/webui', json={'af_mode': 2})
        assert response.status_code == 200

        # Invalid af_mode
        response = client.post('/api/config/webui', json={'af_mode': 99})
        assert response.status_code == 400

    def test_post_webui_validates_stream_mode(self, client, temp_webui_settings):
        """POST /webui only accepts 'simplejpeg' or 'mjpeg_hardware'"""
        # Valid modes
        response = client.post('/api/config/webui', json={'stream_mode': 'simplejpeg'})
        assert response.status_code == 200

        response = client.post('/api/config/webui', json={'stream_mode': 'mjpeg_hardware'})
        assert response.status_code == 200

        # Invalid mode
        response = client.post('/api/config/webui', json={'stream_mode': 'invalid'})
        assert response.status_code == 400

    def test_post_webui_merges_with_existing(self, client, temp_webui_settings):
        """POST /webui preserves unmodified settings"""
        # Setup: Existing settings
        temp_webui_settings.write_text("jpeg_quality=80\nstream_width=1024\nstream_fps=10.0\n")

        # Update only one setting
        response = client.post('/api/config/webui', json={'jpeg_quality': 90})

        assert response.status_code == 200

        # Verify other settings preserved
        content = temp_webui_settings.read_text()
        assert 'jpeg_quality=90' in content
        assert 'stream_width=1024' in content  # Preserved
        assert 'stream_fps=10.0' in content    # Preserved


class TestCopySettingsEndpoint:
    """Tests for POST /api/config/copy-settings endpoint"""

    def test_copy_preview_to_capture(self, client, temp_webui_settings, temp_camera_settings, tmp_path, monkeypatch):
        """POST /copy-settings direction=preview_to_capture"""
        # Setup: Preview settings (snake_case)
        temp_webui_settings.write_text("sharpness=2.5\nexposure_time=500\n")

        # Setup: Camera settings (PascalCase)
        temp_camera_settings.write_text("SETTING,VALUE,DETAILS\nExposureTime,1000,Old value\n")

        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'copied' in data
        assert 'skipped' in data

    def test_copy_capture_to_preview(self, client, temp_webui_settings, temp_camera_settings):
        """POST /copy-settings direction=capture_to_preview"""
        # Setup: Camera settings (PascalCase)
        temp_camera_settings.write_text("SETTING,VALUE,DETAILS\nSharpness,3.0,Sharp\n")

        # Setup: Preview settings (snake_case)
        temp_webui_settings.write_text("sharpness=1.0\n")

        response = client.post('/api/config/copy-settings', json={
            'direction': 'capture_to_preview'
        })

        assert response.status_code == 200

        # Verify preview was updated
        content = temp_webui_settings.read_text()
        assert 'sharpness=' in content

    def test_copy_validates_direction(self, client, temp_webui_settings, temp_camera_settings):
        """POST /copy-settings rejects invalid direction"""
        response = client.post('/api/config/copy-settings', json={
            'direction': 'invalid_direction'
        })

        assert response.status_code == 400


class TestConfigSecurity:
    """Security and validation tests"""

    def test_csv_injection_prevention_schedule(self, client, tmp_path, monkeypatch):
        """Schedule endpoint prevents =, +, -, @ injection"""
        schedule_file = tmp_path / "schedule_settings.csv"
        schedule_file.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        from Tests.conftest import patch_path_constant_everywhere
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', schedule_file)

        malicious_payloads = [
            '=SUM(A1:A10)',
            '+cmd|/C calc',
            '-2+3',
            '@SUM(1+1)'
        ]

        for payload in malicious_payloads:
            response = client.post('/api/config/schedule', json={'runtime': payload})

            # Should succeed but sanitize
            assert response.status_code == 200

            # Verify sanitization
            content = schedule_file.read_text()
            assert "'" in content  # Prefixed with '

    def test_newline_removal_controls(self, client, temp_controls_file):
        """Controls endpoint removes newlines/CR"""
        response = client.post('/api/config/controls', json={
            'name': 'Test\nBox\rName'
        })

        assert response.status_code == 200

        content = temp_controls_file.read_text()
        # Newlines within value should be removed
        assert 'name=TestBoxName' in content

    def test_whitelist_enforcement_controls(self, client, temp_controls_file):
        """Controls endpoint rejects unknown keys"""
        response = client.post('/api/config/controls', json={
            'malicious_key': 'value',
            '__import__': 'os'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid keys' in data['error']

    def test_whitelist_enforcement_webui(self, client, temp_webui_settings):
        """Webui endpoint validates all keys"""
        response = client.post('/api/config/webui', json={
            'invalid_setting': 'value'
        })

        assert response.status_code == 400


class TestConfigConcurrency:
    """Concurrency and race condition tests"""

    def test_concurrent_controls_updates(self, client, temp_controls_file):
        """Concurrent controls updates don't corrupt file"""
        results = []

        def update_control(value):
            response = client.post('/api/config/controls', json={
                'name': f'Box{value}'
            })
            results.append(response.status_code)

        # Start 5 concurrent updates
        threads = [threading.Thread(target=update_control, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert all(status == 200 for status in results)

        # File should be valid (not corrupted)
        content = temp_controls_file.read_text()
        assert 'name=Box' in content


class TestConfigErrorRecovery:
    """Error handling and backup/restore tests"""

    def test_controls_update_restores_backup_on_write_failure(self, client, temp_controls_file, monkeypatch):
        """Controls endpoint restores backup if write fails"""
        # Setup: Original controls
        original = "name=OriginalBox\nshutdown_enabled=true\n"
        temp_controls_file.write_text(original)

        # Mock file write to fail after backup
        write_count = [0]
        original_open = open

        def failing_open(path, mode='r', **kwargs):
            if mode == 'w' and 'controls.txt' in str(path) and not 'backup' in str(path):
                write_count[0] += 1
                if write_count[0] > 1:  # Fail on second write (the actual update, not backup)
                    raise IOError("Disk full")
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr('builtins.open', failing_open)

        # Try to update (should fail and restore)
        response = client.post('/api/config/controls', json={'name': 'NewBox'})

        # Should return error
        assert response.status_code == 500

        # Original content should be restored
        content = temp_controls_file.read_text()
        assert 'OriginalBox' in content

    def test_config_no_backup_created_on_validation_failure(self, client, temp_controls_file, tmp_path):
        """Backup not created if validation fails early"""
        temp_controls_file.write_text("name=OriginalBox\n")

        # Attempt update with invalid data
        response = client.post('/api/config/controls', json={
            'invalid_key': 'value'
        })

        assert response.status_code == 400

        # No backup should exist
        backups = list(temp_controls_file.parent.glob("*.backup*"))
        assert len(backups) == 0

    def test_webui_endpoint_handles_corrupted_file(self, client, temp_webui_settings):
        """GET /webui handles malformed file gracefully"""
        # Write invalid content
        temp_webui_settings.write_text("invalid\nformat\nno\nequals\n")

        response = client.get('/api/config/webui')

        # Should still return 200 with defaults
        assert response.status_code == 200
        data = response.get_json()
        assert 'jpeg_quality' in data  # Has defaults
