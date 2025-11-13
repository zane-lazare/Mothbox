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

    def test_get_schedule_returns_csv_row(self, client, temp_schedule_settings):
        """GET /schedule returns first CSV row as dict"""
        # Write test data
        temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\n1;2;3,8;9;10,30,120\n")

        response = client.get('/api/config/schedule')

        assert response.status_code == 200
        data = response.get_json()
        assert data['weekdays'] == '1;2;3'
        assert data['hours'] == '8;9;10'
        assert data['minutes'] == '30'
        assert data['runtime'] == '120'

    def test_post_schedule_updates_csv(self, client, temp_schedule_settings):
        """POST /schedule writes to schedule_settings.csv"""
        # Setup: Existing data
        temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        response = client.post('/api/config/schedule', json={
            'weekdays': '1;2;3;4;5',
            'hours': '9;10',
            'minutes': '15',
            'runtime': '90'
        })

        assert response.status_code == 200

        # Verify file was updated
        with open(temp_schedule_settings) as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row['weekdays'] == '1;2;3;4;5'
            assert row['runtime'] == '90'

    def test_post_schedule_sanitizes_csv_values(self, client, temp_schedule_settings):
        """POST /schedule applies sanitize_csv_value() to all fields"""
        temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        # Try to inject formula
        response = client.post('/api/config/schedule', json={
            'runtime': '=SUM(A1:A10)'  # CSV injection attempt
        })

        assert response.status_code == 200

        # Verify injection was sanitized
        with open(temp_schedule_settings) as f:
            content = f.read()
            assert "'=SUM" in content  # Sanitized with prefix

    def test_post_schedule_validates_fieldnames(self, client, temp_schedule_settings):
        """POST /schedule rejects keys not in CSV header"""
        temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

        response = client.post('/api/config/schedule', json={
            'invalid_field': 'value'
        })

        assert response.status_code == 400
        assert 'invalid keys' in response.get_json()['error'].lower()


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
        temp_webui_settings.write_text("jpeg_quality=85\nframe_rate=15\nae_enable=true\n")

        response = client.get('/api/config/webui')

        data = response.get_json()
        # Should convert to proper types
        assert isinstance(data['jpeg_quality'], int)
        assert isinstance(data['frame_rate'], int)  # frame_rate is int, not float
        assert isinstance(data['ae_enable'], bool)

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
        temp_webui_settings.write_text("jpeg_quality=80\nstream_width=1024\nframe_rate=10\n")

        # Update only one setting
        response = client.post('/api/config/webui', json={'jpeg_quality': 90})

        assert response.status_code == 200

        # Verify other settings preserved
        content = temp_webui_settings.read_text()
        assert 'jpeg_quality=90' in content
        assert 'stream_width=1024' in content  # Preserved
        assert 'frame_rate=10' in content      # Preserved

    def test_get_webui_handles_invalid_types_gracefully(self, client, temp_webui_settings):
        """GET /webui keeps defaults when type conversion fails"""
        # Write settings with invalid values that can't convert
        temp_webui_settings.write_text(
            "sharpness=not_a_float\n"
            "noise_reduction_mode=not_an_int\n"
            "exposure_time=invalid_int\n"
        )

        response = client.get('/api/config/webui')

        assert response.status_code == 200
        data = response.get_json()
        # Should fall back to defaults when conversion fails
        assert data['sharpness'] == 1.0  # Default
        assert data['noise_reduction_mode'] == 0  # Default
        assert data['exposure_time'] == 500  # Default

    def test_post_webui_validates_boolean_types(self, client, temp_webui_settings):
        """POST /webui validates boolean type settings after conversion"""
        # awb_enable - After string conversion, if it's still not a bool (e.g., a list), it should fail
        # Strings get converted to bool, so we need non-convertible types
        response = client.post('/api/config/webui', json={'awb_enable': ['list', 'value']})
        assert response.status_code == 400
        assert 'AwbEnable must be a boolean' in response.get_json()['error']

        # ae_enable must be boolean (non-string, non-bool type)
        response = client.post('/api/config/webui', json={'ae_enable': {'dict': 'value'}})
        assert response.status_code == 400
        assert 'ae_enable must be a boolean' in response.get_json()['error']

        # use_custom_tuning must be boolean (non-string, non-bool type)
        response = client.post('/api/config/webui', json={'use_custom_tuning': 123})
        assert response.status_code == 400
        assert 'use_custom_tuning must be a boolean' in response.get_json()['error']

        # lens_shading_enable must be boolean (non-string, non-bool type)
        response = client.post('/api/config/webui', json={'lens_shading_enable': 1.5})
        assert response.status_code == 400
        assert 'lens_shading_enable must be a boolean' in response.get_json()['error']

        # defect_correction_enable must be boolean (non-string, non-bool type)
        response = client.post('/api/config/webui', json={'defect_correction_enable': None})
        assert response.status_code == 400
        assert 'defect_correction_enable must be a boolean' in response.get_json()['error']

    def test_post_webui_validates_string_types(self, client, temp_webui_settings):
        """POST /webui validates string type settings"""
        # sensor_mode must be string
        response = client.post('/api/config/webui', json={'sensor_mode': 123})
        assert response.status_code == 400
        assert 'sensor_mode must be a string' in response.get_json()['error']

        # focus_peaking_colour must be string
        response = client.post('/api/config/webui', json={'focus_peaking_colour': 123})
        assert response.status_code == 400
        assert 'focus_peaking_colour must be a string' in response.get_json()['error']

        # focus_peaking_algorithm must be string
        response = client.post('/api/config/webui', json={'focus_peaking_algorithm': ['list']})
        assert response.status_code == 400
        assert 'focus_peaking_algorithm must be a string' in response.get_json()['error']

    def test_post_webui_validates_type_conversion_errors(self, client, temp_webui_settings):
        """POST /webui returns 400 on type conversion failures"""
        # Stream settings - invalid types
        response = client.post('/api/config/webui', json={'stream_width': 'not_an_int'})
        assert response.status_code == 400
        assert 'Invalid stream setting type' in response.get_json()['error']

        # Image quality - invalid types
        response = client.post('/api/config/webui', json={'sharpness': 'not_a_float'})
        assert response.status_code == 400
        assert 'Invalid image quality setting type' in response.get_json()['error']

        # Noise reduction - invalid type
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 'not_an_int'})
        assert response.status_code == 400
        assert 'Invalid noise_reduction_mode type' in response.get_json()['error']

        # Noise reduction - float when int required
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 1.5})
        assert response.status_code == 400
        assert 'noise_reduction_mode must be an integer' in response.get_json()['error']

        # Focus controls - invalid type
        response = client.post('/api/config/webui', json={'af_mode': 'invalid'})
        assert response.status_code == 400
        assert 'Invalid focus control type' in response.get_json()['error']

        # White balance - invalid type
        response = client.post('/api/config/webui', json={'awb_mode': 'invalid'})
        assert response.status_code == 400
        assert 'Invalid white balance mode type' in response.get_json()['error']

        # Colour gains - invalid type
        response = client.post('/api/config/webui', json={'colour_gains_red': 'invalid'})
        assert response.status_code == 400
        assert 'Invalid colour gains type' in response.get_json()['error']

        # Exposure controls - invalid type
        response = client.post('/api/config/webui', json={'exposure_time': 'invalid'})
        assert response.status_code == 400
        assert 'Invalid exposure settings type' in response.get_json()['error']

        # ae_metering_mode - float when int required
        response = client.post('/api/config/webui', json={'ae_metering_mode': 1.7})
        assert response.status_code == 400
        assert 'ae_metering_mode must be an integer' in response.get_json()['error']

        # Focus peaking intensity - invalid type
        response = client.post('/api/config/webui', json={'focus_peaking_intensity': 'invalid'})
        assert response.status_code == 400
        assert 'Invalid focus_peaking_intensity type' in response.get_json()['error']

    def test_post_webui_validates_all_numeric_ranges(self, client, temp_webui_settings):
        """POST /webui validates all numeric setting ranges"""
        # Sharpness range (0.0-4.0)
        response = client.post('/api/config/webui', json={'sharpness': 5.0})
        assert response.status_code == 400
        assert 'Sharpness must be between' in response.get_json()['error']

        # Brightness range (-1.0-1.0)
        response = client.post('/api/config/webui', json={'brightness': -2.0})
        assert response.status_code == 400
        assert 'Brightness must be between' in response.get_json()['error']

        # Contrast range (0.0-4.0)
        response = client.post('/api/config/webui', json={'contrast': 4.5})
        assert response.status_code == 400
        assert 'Contrast must be between' in response.get_json()['error']

        # Saturation range (0.0-4.0)
        response = client.post('/api/config/webui', json={'saturation': -0.1})
        assert response.status_code == 400
        assert 'Saturation must be between' in response.get_json()['error']

        # awb_mode range (0-7)
        response = client.post('/api/config/webui', json={'awb_mode': 8})
        assert response.status_code == 400
        assert 'AwbMode must be between' in response.get_json()['error']

        # colour_gains_red range (0.0-8.0)
        response = client.post('/api/config/webui', json={'colour_gains_red': 8.5})
        assert response.status_code == 400
        assert 'Red colour gain must be between' in response.get_json()['error']

        # colour_gains_blue range (0.0-8.0)
        response = client.post('/api/config/webui', json={'colour_gains_blue': -0.1})
        assert response.status_code == 400
        assert 'Blue colour gain must be between' in response.get_json()['error']

        # exposure_time range (100-200000 microseconds)
        response = client.post('/api/config/webui', json={'exposure_time': 50})
        assert response.status_code == 400
        assert 'exposure_time must be between' in response.get_json()['error']

        # analogue_gain range (1.0-16.0)
        response = client.post('/api/config/webui', json={'analogue_gain': 20.0})
        assert response.status_code == 400
        assert 'analogue_gain must be between' in response.get_json()['error']

        # af_speed enum (0 or 1)
        response = client.post('/api/config/webui', json={'af_speed': 2})
        assert response.status_code == 400
        assert 'AfSpeed must be' in response.get_json()['error']

        # af_range enum (0, 1, or 2)
        response = client.post('/api/config/webui', json={'af_range': 3})
        assert response.status_code == 400
        assert 'AfRange must be' in response.get_json()['error']

        # sensor_mode enum validation
        response = client.post('/api/config/webui', json={'sensor_mode': 'invalid_mode'})
        assert response.status_code == 400
        assert 'sensor_mode must be' in response.get_json()['error']


class TestCopySettingsEndpoint:
    """Tests for POST /api/config/copy-settings endpoint"""

    def test_copy_preview_to_capture(self, client, temp_webui_settings, temp_camera_settings):
        """POST /copy-settings direction=preview_to_capture"""
        # Setup: Preview settings (snake_case)
        temp_webui_settings.write_text("sharpness=2.5\nexposure_time=500\n")

        # Setup: Camera settings (PascalCase) - already has header from fixture
        with open(temp_camera_settings, 'a') as f:
            f.write("ExposureTime,1000,Old value\n")

        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'copied' in data
        assert 'skipped' in data

    def test_copy_capture_to_preview(self, client, temp_webui_settings, temp_camera_settings):
        """POST /copy-settings direction=capture_to_preview"""
        # Setup: Camera settings (PascalCase) - already has header from fixture
        with open(temp_camera_settings, 'a') as f:
            f.write("Sharpness,3.0,Sharp\n")

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

    def test_copy_preview_to_capture_missing_file(self, client, tmp_path, monkeypatch):
        """POST /copy-settings returns 404 if preview settings missing"""
        from Tests.conftest import patch_path_constant_everywhere

        # Point to non-existent preview file
        missing_file = tmp_path / "missing_preview.txt"
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', missing_file)

        # Camera settings file exists
        camera_file = tmp_path / "camera_settings.csv"
        camera_file.write_text("SETTING,VALUE,DETAILS\nSharpness,1.0,Default\n")
        patch_path_constant_everywhere(monkeypatch, 'CAMERA_SETTINGS_FILE', camera_file)

        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 404
        data = response.get_json()
        assert 'webui_settings.txt not found' in data['error']

    def test_copy_handles_type_conversion_in_preview(self, client, temp_webui_settings, temp_camera_settings):
        """POST /copy-settings handles type conversion for preview settings"""
        # Setup: Preview settings with values that need type conversion
        temp_webui_settings.write_text(
            "sharpness=2.5\n"
            "af_mode=1\n"
            "awb_enable=false\n"
        )

        # Setup: Camera settings CSV
        with open(temp_camera_settings, 'a') as f:
            f.write("Sharpness,1.0,Original\n")
            f.write("AfMode,2,Original\n")
            f.write("AwbEnable,1,Original\n")

        response = client.post('/api/config/copy-settings', json={
            'direction': 'preview_to_capture'
        })

        assert response.status_code == 200
        data = response.get_json()
        # Should have copied some settings
        assert 'copied' in data
        assert isinstance(data['copied'], list)

    def test_copy_capture_to_preview_creates_file_if_missing(self, client, tmp_path, temp_camera_settings, monkeypatch):
        """POST /copy-settings capture_to_preview creates preview file if missing"""
        from Tests.conftest import patch_path_constant_everywhere

        # Setup: Camera settings exist
        with open(temp_camera_settings, 'a') as f:
            f.write("Sharpness,2.0,Test\n")

        # Preview settings file doesn't exist
        preview_file = tmp_path / "new_preview.txt"
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', preview_file)

        response = client.post('/api/config/copy-settings', json={
            'direction': 'capture_to_preview'
        })

        assert response.status_code == 200

        # File should be created
        assert preview_file.exists()


class TestConfigSecurity:
    """Security and validation tests"""

    def test_csv_injection_prevention_schedule(self, client, temp_schedule_settings):
        """Schedule endpoint prevents =, +, -, @ injection"""
        temp_schedule_settings.write_text("weekdays,hours,minutes,runtime\n1,8,0,60\n")

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
            content = temp_schedule_settings.read_text()
            assert "'" in content  # Prefixed with '

    def test_newline_rejection_controls(self, client, temp_controls_file):
        """Controls endpoint rejects values with newlines/CR (validation before sanitization)"""
        response = client.post('/api/config/controls', json={
            'name': 'Test\nBox\rName'
        })

        # Should reject due to validation (newlines not allowed in name field)
        assert response.status_code == 400

        # Valid value without newlines should work
        response = client.post('/api/config/controls', json={
            'name': 'TestBoxName'
        })
        assert response.status_code == 200

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


class TestConfigEndpointErrors:
    """Error handling tests for endpoint exceptions"""

    def test_get_controls_handles_file_read_error(self, client, tmp_path, monkeypatch):
        """GET /controls returns 500 on file read error"""
        from Tests.conftest import patch_path_constant_everywhere

        # Point to a file that will cause an error when read
        bad_path = tmp_path / "unreadable.txt"
        bad_path.write_text("test")
        bad_path.chmod(0o000)  # Make unreadable

        patch_path_constant_everywhere(monkeypatch, 'CONTROLS_FILE', bad_path)

        response = client.get('/api/config/controls')

        # Should return 500 error
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Cleanup
        bad_path.chmod(0o644)

    def test_get_schedule_handles_file_error(self, client, tmp_path, monkeypatch):
        """GET /schedule returns 500 on file read error"""
        from Tests.conftest import patch_path_constant_everywhere

        # Point to non-existent file
        missing_file = tmp_path / "missing_schedule.csv"
        patch_path_constant_everywhere(monkeypatch, 'SCHEDULE_SETTINGS_FILE', missing_file)

        response = client.get('/api/config/schedule')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_get_webui_handles_file_error(self, client, tmp_path, monkeypatch):
        """GET /webui returns 500 on unexpected error"""
        from Tests.conftest import patch_path_constant_everywhere

        # Mock get_control_values to raise an exception
        def mock_get_control_values(file_path):
            raise RuntimeError("Unexpected error reading file")

        monkeypatch.setattr('routes.config.get_control_values', mock_get_control_values)

        # Setup valid file to trigger the mocked function
        valid_file = tmp_path / "liveview_settings.txt"
        valid_file.write_text("test=value\n")
        patch_path_constant_everywhere(monkeypatch, 'LIVEVIEW_SETTINGS_FILE', valid_file)

        response = client.get('/api/config/webui')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_post_schedule_restores_backup_on_write_failure(self, client, temp_schedule_settings, monkeypatch):
        """Schedule endpoint restores backup if write fails"""
        # Setup: Original schedule
        original = "weekdays,hours,minutes,runtime\n1,8,0,60\n"
        temp_schedule_settings.write_text(original)

        # Track backup restoration
        restore_called = []
        original_copy2 = __import__('shutil').copy2

        def mock_copy2(src, dst):
            restore_called.append((src, dst))
            return original_copy2(src, dst)

        monkeypatch.setattr('shutil.copy2', mock_copy2)

        # Mock csv.DictWriter to fail during writerow
        original_dictwriter = __import__('csv').DictWriter

        class FailingDictWriter(original_dictwriter):
            def writerow(self, row):
                raise IOError("Disk full")

        monkeypatch.setattr('csv.DictWriter', FailingDictWriter)

        # Attempt update (should fail and restore)
        response = client.post('/api/config/schedule', json={'runtime': '90'})

        assert response.status_code == 500

        # Verify backup was restored (copy2 called for restore)
        assert any('backup' in str(src).lower() for src, dst in restore_called if dst == temp_schedule_settings)


class TestConfigErrorRecovery:
    """Error handling and backup/restore tests"""

    def test_controls_update_restores_backup_on_write_failure(self, client, temp_controls_file, monkeypatch):
        """Controls endpoint restores backup if write fails"""
        # Setup: Original controls
        original = "name=OriginalBox\nshutdown_enabled=true\n"
        temp_controls_file.write_text(original)

        # Mock file write to fail on main file (after backup succeeds)
        original_open = open

        def failing_open(path, mode='r', **kwargs):
            # Allow all reads and backup writes to succeed
            if mode == 'r' or 'backup' in str(path):
                return original_open(path, mode, **kwargs)

            # Fail writes to main controls.txt (simulates disk full after backup created)
            if mode == 'w' and 'controls.txt' in str(path):
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
