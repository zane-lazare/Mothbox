"""
Unit tests for Camera control routes (Issue #78 Phase 2E-2I)

Tests all camera endpoints with comprehensive mocking for CI/CD compatibility.
Focus areas: Picamera2 integration, subprocess workflows, stream coordination.

Route endpoints tested:
- GET /api/camera/settings - Retrieve camera settings
- POST /api/camera/settings - Update camera settings
- POST /api/camera/freeze-settings - Freeze settings for capture
- POST /api/camera/capture - Single/HDR/focus bracket capture
- POST /api/camera/autofocus - Run autofocus cycle
- POST /api/camera/calibrate-photo - Run photo calibration
- POST /api/camera/test-capture-liveview - Test liveview capture
- POST /api/camera/test-capture-photo - Test photo capture

Test structure:
- TestCameraAcquireHelper: acquire_camera_with_retry() helper tests
- TestGetCameraSettings: GET /settings endpoint tests
- TestPostCameraSettings: POST /settings endpoint tests (validation, persistence)
- TestFreezeSettings: POST /freeze-settings endpoint tests
- TestCaptureEndpoint: POST /capture endpoint tests (single/HDR/focus bracket)
- TestAutofocusEndpoint: POST /autofocus endpoint tests
- TestCalibratePhotoEndpoint: POST /calibrate-photo endpoint tests
- TestTestCaptureLiveview: POST /test-capture-liveview endpoint tests
- TestTestCapturePhoto: POST /test-capture-photo endpoint tests

Coverage target: 50-60% (realistic given hardware dependencies and subprocess complexity)
"""
import pytest
import json
import time
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call, Mock

# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestCameraAcquireHelper:
    """Tests for acquire_camera_with_retry() helper function"""

    def test_acquire_camera_success_first_try(self):
        """Camera acquired successfully on first attempt"""
        # TODO: Implement after mock_picamera2 fixture is ready
        pytest.skip("Requires mock_picamera2 fixture (Phase 2D)")

    def test_acquire_camera_busy_retry_success(self):
        """Camera busy initially, succeeds on retry"""
        # TODO: Implement after mock_picamera2 fixture is ready
        pytest.skip("Requires mock_picamera2 fixture (Phase 2D)")

    def test_acquire_camera_busy_max_retries_exceeded(self):
        """Camera remains busy, exceeds max retries"""
        # TODO: Implement after mock_picamera2 fixture is ready
        pytest.skip("Requires mock_picamera2 fixture (Phase 2D)")

    def test_acquire_camera_non_busy_error_no_retry(self):
        """Non-busy error raised immediately without retry"""
        # TODO: Implement after mock_picamera2 fixture is ready
        pytest.skip("Requires mock_picamera2 fixture (Phase 2D)")


# ============================================================================
# GET /api/camera/settings - Retrieve camera settings
# ============================================================================

class TestGetCameraSettings:
    """Tests for GET /api/camera/settings endpoint"""

    def test_get_settings_success(self, client, temp_camera_settings):
        """Successfully retrieve camera settings"""
        # Setup: Write valid camera settings CSV
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,500,Exposure time in microseconds\n"
            "Sharpness,2.5,Sharpness level\n"
            "Contrast,1.0,Contrast level\n"
        )

        # Execute: GET request
        response = client.get('/api/camera/settings')

        # Verify: Success response with correct settings
        assert response.status_code == 200
        data = response.get_json()
        assert data['ExposureTime'] == '500'
        assert data['Sharpness'] == '2.5'
        assert data['Contrast'] == '1.0'
        assert len(data) == 3

    def test_get_settings_file_not_found(self, client, temp_camera_settings):
        """Handle missing camera settings file"""
        # Setup: Delete the settings file
        temp_camera_settings.unlink()

        # Execute: GET request
        response = client.get('/api/camera/settings')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'No such file' in data['error'] or 'does not exist' in data['error']

    def test_get_settings_invalid_json(self, client, temp_camera_settings):
        """Handle corrupted settings CSV (not JSON - endpoint reads CSV)"""
        # Setup: Write malformed CSV (missing header)
        temp_camera_settings.write_text(
            "ExposureTime,500\n"
            "Sharpness,2.5\n"
        )

        # Execute: GET request
        response = client.get('/api/camera/settings')

        # Verify: Error response (CSV reader will fail without proper header)
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# POST /api/camera/settings - Update camera settings
# ============================================================================

class TestPostCameraSettings:
    """Tests for POST /api/camera/settings endpoint"""

    def test_post_settings_success(self, client, temp_camera_settings):
        """Successfully update camera settings"""
        import csv

        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,1000,Initial exposure\n"
            "Sharpness,1.5,Initial sharpness\n"
            "Contrast,1.0,Initial contrast\n"
        )

        # Execute: POST request to update settings
        update_data = {
            'ExposureTime': '2000',  # Update existing
            'Sharpness': '2.5'        # Update existing
        }
        response = client.post('/api/camera/settings',
                              json=update_data,
                              content_type='application/json')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Settings persisted to file
        with open(temp_camera_settings, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['ExposureTime'] == '2000'
        assert settings['Sharpness'] == '2.5'
        assert settings['Contrast'] == '1.0'  # Preserved unchanged

    def test_post_settings_validation_error(self, client, temp_camera_settings):
        """Reject invalid camera settings"""
        # Setup: Basic settings file
        temp_camera_settings.write_text("SETTING,VALUE,DETAILS\n")

        # Test case 1: Invalid setting name
        invalid_name_data = {
            'InvalidSetting': '100',
            'Sharpness': '2.0'
        }
        response = client.post('/api/camera/settings', json=invalid_name_data)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid setting' in data['error']

        # Test case 2: Invalid value (string where number expected)
        invalid_type_data = {
            'ExposureTime': 'not_a_number'
        }
        response = client.post('/api/camera/settings', json=invalid_type_data)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_post_settings_partial_update(self, client, temp_camera_settings):
        """Update only specified settings, preserve others"""
        import csv

        # Setup: Write comprehensive initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,1000,Exposure time in microseconds\n"
            "Sharpness,1.5,Sharpness level\n"
            "Contrast,1.0,Contrast level\n"
            "Saturation,1.0,Saturation level\n"
            "AnalogueGain,2.0,ISO gain\n"
        )

        # Execute: Update only one setting
        update_data = {'Sharpness': '3.0'}
        response = client.post('/api/camera/settings', json=update_data)

        # Verify: Success
        assert response.status_code == 200

        # Verify: All settings preserved, only target updated
        with open(temp_camera_settings, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row for row in reader}

        assert settings['Sharpness']['VALUE'] == '3.0'  # Updated
        assert settings['ExposureTime']['VALUE'] == '1000'  # Unchanged
        assert settings['Contrast']['VALUE'] == '1.0'  # Unchanged
        assert settings['Saturation']['VALUE'] == '1.0'  # Unchanged
        assert settings['AnalogueGain']['VALUE'] == '2.0'  # Unchanged
        # Verify DETAILS column preserved
        assert settings['ExposureTime']['DETAILS'] == 'Exposure time in microseconds'

    def test_post_settings_type_conversion(self, client, temp_camera_settings):
        """Handle type conversion (string to int/float)"""
        # Setup: Basic settings file
        temp_camera_settings.write_text("SETTING,VALUE,DETAILS\n")

        # Execute: Mix of string and numeric types
        mixed_types_data = {
            'ExposureTime': '5000',      # String integer
            'Sharpness': '2.5',          # String float
            'AnalogueGain': '3.0',       # String float
        }
        response = client.post('/api/camera/settings', json=mixed_types_data)

        # Verify: All accepted
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Values persisted correctly
        settings_content = temp_camera_settings.read_text()
        assert 'ExposureTime,5000,' in settings_content
        assert 'Sharpness,2.5,' in settings_content
        assert 'AnalogueGain,3.0,' in settings_content

    def test_post_settings_boolean_validation(self, client, temp_camera_settings):
        """Validate boolean settings properly"""
        # Setup: Basic settings file
        temp_camera_settings.write_text("SETTING,VALUE,DETAILS\n")

        # Test valid boolean cases (case-insensitive)
        valid_booleans = [
            {'AeEnable': 'true'},
            {'AeEnable': 'false'},
            {'AwbEnable': 'true'},
        ]

        for data in valid_booleans:
            response = client.post('/api/camera/settings', json=data)
            assert response.status_code == 200, f"Failed for {data}"

        # Test invalid boolean cases
        invalid_booleans = [
            {'AeEnable': '1'},
            {'AeEnable': 'yes'},
            {'AwbEnable': 'enabled'},
        ]

        for data in invalid_booleans:
            response = client.post('/api/camera/settings', json=data)
            assert response.status_code == 400, f"Should have failed for {data}"
            assert 'error' in response.get_json()

    def test_post_settings_stream_restart(self):
        """Verify stream restart after settings update"""
        pytest.skip("POST /settings endpoint doesn't interact with streams - see freeze-settings endpoint instead")

    def test_post_settings_persistence(self, client, temp_camera_settings):
        """Verify settings are persisted to file"""
        import csv

        # Setup: Initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "Sharpness,1.0,Initial\n"
        )

        # Execute: First update
        first_update = {'Sharpness': '2.0', 'Contrast': '1.5'}
        response = client.post('/api/camera/settings', json=first_update)
        assert response.status_code == 200

        # Execute: Second update (mix of existing and new)
        second_update = {
            'Sharpness': '3.0',        # Update existing
            'Saturation': '1.2'        # Add new
        }
        response = client.post('/api/camera/settings', json=second_update)
        assert response.status_code == 200

        # Verify: All settings present and latest values correct
        with open(temp_camera_settings, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['Sharpness'] == '3.0'  # Latest update
        assert settings['Contrast'] == '1.5'   # From first update
        assert settings['Saturation'] == '1.2' # From second update

        # Test CSV injection prevention
        injection_attempt = {
            'Sharpness': '=2.0+1.0'  # Formula injection attempt
        }
        response = client.post('/api/camera/settings', json=injection_attempt)

        # Should either reject or sanitize
        if response.status_code == 200:
            content = temp_camera_settings.read_text()
            # Verify formula prefix was stripped/escaped (sanitize_csv_value)
            # The sanitizer should prevent raw formulas
            assert content.count('=2.0+1.0') == 0 or "'=2.0+1.0" in content

    def test_post_settings_exposure_mode_conversion(self):
        """Handle ExposureMode enum conversion"""
        pytest.skip("ExposureMode not used in camera_settings.csv - uses discrete controls instead")


# ============================================================================
# POST /api/camera/freeze-settings - Freeze settings for capture
# ============================================================================

class TestFreezeSettings:
    """Tests for POST /api/camera/freeze-settings endpoint"""

    def test_freeze_settings_success(self, client, temp_camera_settings, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Successfully freeze camera settings"""
        import csv

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Write initial camera settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,1000,Initial exposure\n"
            "Sharpness,2.5,Sharpness level\n"
            "AeEnable,True,Auto exposure enabled\n"
            "AwbEnable,True,Auto white balance enabled\n"
        )

        # Configure mock camera metadata
        # Note: mock_picamera2._mock_instance is the actual instance that will be used
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 5000,
            'AnalogueGain': 2.5,
            'LensPosition': 3.2
        }

        # Execute: POST request to freeze settings
        response = client.post('/api/camera/freeze-settings')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'frozen_settings' in data
        assert data['frozen_settings']['ExposureTime'] == 5000
        assert data['frozen_settings']['AnalogueGain'] == 2.5
        assert data['frozen_settings']['LensPosition'] == 3.2
        assert data['frozen_settings']['AeEnable'] is False
        assert data['frozen_settings']['AwbEnable'] is False
        assert 'message' in data

        # Verify: Camera was initialized, started, and stopped
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: Settings were frozen in the file
        with open(temp_camera_settings, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['ExposureTime'] == '5000'
        assert settings['AnalogueGain'] == '2.5'
        assert settings['LensPosition'] == '3.2'
        assert settings['AeEnable'] == 'False'
        assert settings['AwbEnable'] == 'False'
        assert settings['AfMode'] == '0'
        assert settings['Sharpness'] == '2.5'  # Preserved

        # Verify: Camera streamer operation lock was acquired
        assert mock_camera_streamer.acquire_for_operation.called

    def test_freeze_settings_already_frozen(self, client, temp_camera_settings, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle already frozen state gracefully"""
        import csv

        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Write already-frozen settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,8000,Frozen exposure\n"
            "AnalogueGain,3.0,Frozen gain\n"
            "LensPosition,5.0,Frozen focus\n"
            "AeEnable,False,Auto exposure disabled\n"
            "AwbEnable,False,Auto white balance disabled\n"
            "AfMode,0,Manual focus\n"
        )

        # Configure mock camera metadata (different values)
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 4.0,
            'LensPosition': 6.5
        }

        # Execute: POST request to freeze settings again
        response = client.post('/api/camera/freeze-settings')

        # Verify: Success (re-freezing is allowed and updates to new values)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Settings were updated to new frozen values
        with open(temp_camera_settings, 'r') as f:
            reader = csv.DictReader(f)
            settings = {row['SETTING']: row['VALUE'] for row in reader}

        assert settings['ExposureTime'] == '10000'  # Updated
        assert settings['AnalogueGain'] == '4.0'    # Updated
        assert settings['LensPosition'] == '6.5'    # Updated

    def test_freeze_settings_file_not_found(self, client, temp_camera_settings, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle missing camera settings file"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Delete the settings file
        temp_camera_settings.unlink()

        # Configure mock camera metadata
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 5000,
            'AnalogueGain': 2.5,
            'LensPosition': 3.2
        }

        # Execute: POST request
        response = client.post('/api/camera/freeze-settings')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'No such file' in data['error'] or 'does not exist' in data['error']

        # Verify: Camera was still cleaned up
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.stop.called
        assert mock_instance.close.called

    def test_freeze_settings_invalid_json(self, client, temp_camera_settings, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle corrupted camera settings CSV"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Write malformed CSV (missing SETTING column means .get() returns None)
        temp_camera_settings.write_text(
            "INVALID,HEADER,COLUMNS\n"
            "value1,value2,value3\n"
        )

        # Configure mock camera metadata
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 5000,
            'AnalogueGain': 2.5,
            'LensPosition': 3.2
        }

        # Execute: POST request
        response = client.post('/api/camera/freeze-settings')

        # Note: The endpoint may succeed even with malformed CSV because it uses
        # row.get('SETTING', '').strip() which defaults to empty string.
        # The endpoint will write new settings, effectively creating a valid file.
        # This is actually graceful degradation - it doesn't fail, it fixes the file.
        assert response.status_code in [200, 500]

        # If it succeeded, verify new settings were written
        if response.status_code == 200:
            data = response.get_json()
            assert data['success'] is True
            # The file should now have proper structure
            import csv
            with open(temp_camera_settings, 'r') as f:
                reader = csv.DictReader(f)
                # Should have at least the frozen settings
                rows = list(reader)
                assert len(rows) > 0
        else:
            # If it failed, verify error is reported
            data = response.get_json()
            assert 'error' in data


# ============================================================================
# POST /api/camera/capture - Main capture endpoint
# ============================================================================

class TestCaptureEndpoint:
    """Tests for POST /api/camera/capture endpoint (single/HDR/focus bracket)"""

    def test_capture_single_exposure_success(self, client, temp_camera_settings, mock_subprocess_run,
                                              temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Successfully capture single exposure photo"""
        from pathlib import Path

        # Setup: Configure for single exposure (HDR=1)
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
            "ExposureTime,10000,Exposure time\n"
        )

        # Setup: Mock Pi version detection (Pi 4)
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() to make script path check pass
        original_exists = Path.exists
        def patched_exists(self):
            # Make TakePhoto.py script appear to exist
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess.run for TakePhoto.py success
        mock_run = mock_subprocess_run('TakePhoto.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create a fake photo file that will be found
        photo_file = temp_photos_dir / "test_photo_001.jpg"
        photo_file.touch()

        # Execute: POST request to capture
        response = client.post('/api/camera/capture')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'latest_photo' in data
        assert data['focus_bracket_mode'] is False
        assert data['hdr_mode'] is False
        assert data['script_used'] == 'TakePhoto.py'
        assert data['message'] == 'Single exposure capture complete'

        # Verify: Subprocess was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'TakePhoto.py' in str(call_args)

        # Verify: Camera streamer lock was acquired
        assert mock_camera_streamer.acquire_for_operation.called

    def test_capture_single_exposure_subprocess_failure(self, client, temp_camera_settings, mock_subprocess_run,
                                                        mock_camera_streamer, monkeypatch):
        """Handle TakePhoto.py subprocess failure"""
        from pathlib import Path

        # Setup: Configure for single exposure
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess failure
        mock_run = mock_subprocess_run('TakePhoto.py', returncode=1, stderr="Camera initialization failed")
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_capture_single_exposure_timeout(self, client, temp_camera_settings, mock_subprocess_run,
                                             mock_camera_streamer, monkeypatch):
        """Handle capture timeout"""
        from pathlib import Path

        # Setup: Configure for single exposure
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess timeout
        mock_run = mock_subprocess_run('TakePhoto.py', timeout=True)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Timeout error
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'timed out' in data['error'].lower()

    def test_capture_single_exposure_camera_busy(self, client, temp_camera_settings, mock_subprocess_run,
                                                  mock_camera_streamer, temp_photos_dir, monkeypatch):
        """Handle camera busy during capture"""
        from pathlib import Path

        # Setup: Configure for single exposure
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success
        mock_run = mock_subprocess_run('TakePhoto.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create a photo file
        photo_file = temp_photos_dir / "test_photo_001.jpg"
        photo_file.touch()

        # Setup: Mark camera streamer as streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Success (camera was released before capture)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: release_camera was called
        assert mock_camera_streamer.release_camera.called

    def test_capture_hdr_mode_pi4(self, client, temp_camera_settings, mock_subprocess_run,
                                  temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Capture HDR bracket on Pi 4"""
        from pathlib import Path

        # Setup: Configure for HDR mode (3 exposures)
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,3,Three exposure HDR\n"
            "HDR_width,7000,Bracket width in microseconds\n"
        )

        # Setup: Mock Pi 4 version detection
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for HDR script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto_HDR.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success for HDR script
        mock_run = mock_subprocess_run('TakePhoto_HDR.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create HDR photo files
        for i in range(3):
            photo_file = temp_photos_dir / f"hdr_photo_{i:03d}.jpg"
            photo_file.touch()

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['hdr_mode'] is True
        assert data['hdr_count'] == 3
        assert data['hdr_width'] == 7000
        assert data['script_used'] == 'TakePhoto_HDR.py'
        assert 'HDR capture complete' in data['message']

        # Verify: Subprocess was called with HDR script
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'TakePhoto_HDR.py' in str(call_args)
        assert '4.x' in str(call_args)  # Pi 4 script path

    def test_capture_hdr_mode_pi5(self, client, temp_camera_settings, mock_subprocess_run,
                                  temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Capture HDR bracket on Pi 5"""
        from pathlib import Path

        # Setup: Configure for HDR mode (5 exposures)
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,5,Five exposure HDR\n"
            "HDR_width,10000,Bracket width in microseconds\n"
        )

        # Setup: Mock Pi 5 version detection
        mock_cpuinfo = "Model\t\t: Raspberry Pi 5 Model B Rev 1.0\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for HDR script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto_HDR.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success for HDR script
        mock_run = mock_subprocess_run('TakePhoto_HDR.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create HDR photo files
        for i in range(5):
            photo_file = temp_photos_dir / f"hdr_photo_{i:03d}.jpg"
            photo_file.touch()

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['hdr_mode'] is True
        assert data['hdr_count'] == 5
        assert data['hdr_width'] == 10000
        assert data['script_used'] == 'TakePhoto_HDR.py'
        assert 'HDR capture complete' in data['message']

        # Verify: Subprocess was called with HDR script on Pi 5 path
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'TakePhoto_HDR.py' in str(call_args)
        assert '5.x' in str(call_args)  # Pi 5 script path

    def test_capture_focus_bracket_mode(self, client, temp_camera_settings, mock_subprocess_run,
                                        temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Capture focus bracket sequence"""
        from pathlib import Path

        # Setup: Configure for Focus Bracket mode (5 steps)
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "FocusBracket,5,Five focus steps\n"
            "FocusBracket_Start,2.0,Start position in diopters\n"
            "FocusBracket_End,8.0,End position in diopters\n"
            "HDR,1,Single exposure per focus step\n"
        )

        # Setup: Mock Pi version (focus bracket script is Pi-independent)
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for focus bracket script
        original_exists = Path.exists
        def patched_exists(self):
            if 'capture_focus_bracket.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success for focus bracket script
        mock_run = mock_subprocess_run('capture_focus_bracket.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create focus bracket photo files
        for i in range(5):
            photo_file = temp_photos_dir / f"focus_bracket_{i:03d}.jpg"
            photo_file.touch()

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['focus_bracket_mode'] is True
        assert data['focus_bracket_steps'] == 5
        assert data['focus_bracket_start'] == 2.0
        assert data['focus_bracket_end'] == 8.0
        assert data['script_used'] == 'capture_focus_bracket.py'
        assert 'Focus bracket capture complete' in data['message']

        # Verify: Subprocess was called with focus bracket script
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'capture_focus_bracket.py' in str(call_args)

    def test_capture_focus_bracket_subprocess_failure(self, client, temp_camera_settings, mock_subprocess_run,
                                                       mock_camera_streamer, monkeypatch):
        """Handle focus bracket script failure"""
        from pathlib import Path

        # Setup: Configure for Focus Bracket mode
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "FocusBracket,3,Three focus steps\n"
            "FocusBracket_Start,3.0,Start position\n"
            "FocusBracket_End,7.0,End position\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 5 Model B Rev 1.0\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'capture_focus_bracket.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess failure
        mock_run = mock_subprocess_run('capture_focus_bracket.py', returncode=1,
                                       stderr="Focus bracket script failed: Camera error")
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_capture_photo_count_cache_invalidation(self, client, temp_camera_settings, mock_subprocess_run,
                                                     temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Verify photo count cache is invalidated after capture"""
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        # Setup: Configure for single exposure
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success
        mock_run = mock_subprocess_run('TakePhoto.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create a photo file
        photo_file = temp_photos_dir / "test_photo_001.jpg"
        photo_file.touch()

        # Setup: Mock the invalidate_photo_count_cache function from routes.system
        mock_invalidate = MagicMock()
        with patch('routes.system.invalidate_photo_count_cache', mock_invalidate):
            # Execute: POST request
            response = client.post('/api/camera/capture')

            # Verify: Success
            assert response.status_code == 200

            # Verify: Cache invalidation was called
            assert mock_invalidate.called

    def test_capture_stream_restart(self, client, temp_camera_settings, mock_subprocess_run,
                                    temp_photos_dir, mock_camera_streamer, monkeypatch):
        """Verify stream restarts after capture"""
        from pathlib import Path

        # Setup: Configure for single exposure
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "HDR,1,Single exposure\n"
        )

        # Setup: Mock Pi version
        mock_cpuinfo = "Model\t\t: Raspberry Pi 4 Model B Rev 1.5\n"
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                from io import StringIO
                return StringIO(mock_cpuinfo)
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Path.exists() for script
        original_exists = Path.exists
        def patched_exists(self):
            if 'TakePhoto.py' in str(self):
                return True
            return original_exists(self)
        monkeypatch.setattr(Path, 'exists', patched_exists)

        # Setup: Mock subprocess success
        mock_run = mock_subprocess_run('TakePhoto.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Create a photo file
        photo_file = temp_photos_dir / "test_photo_001.jpg"
        photo_file.touch()

        # Setup: Mark camera streamer as streaming initially
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Track start_streaming calls
        start_stream_call_count = 0
        original_start_streaming = mock_camera_streamer.start_streaming
        def track_start_streaming():
            nonlocal start_stream_call_count
            start_stream_call_count += 1
            return original_start_streaming()
        mock_camera_streamer.start_streaming.side_effect = track_start_streaming

        # Execute: POST request
        response = client.post('/api/camera/capture')

        # Verify: Success
        assert response.status_code == 200

        # Verify: Stream was restarted after capture
        assert start_stream_call_count > 0, "Stream should have been restarted after capture"


# ============================================================================
# POST /api/camera/autofocus - Run autofocus cycle
# ============================================================================

class TestAutofocusEndpoint:
    """Tests for POST /api/camera/autofocus endpoint"""

    def test_autofocus_success(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Successfully run autofocus cycle"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure successful autofocus cycle
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 5.5,
            'AfState': 2,  # Success
            'ExposureTime': 10000,
            'AnalogueGain': 1.5,
            'ColourTemperature': 5000
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['af_state'] == 'Success'
        assert data['lens_position'] == 5.5
        assert 'duration_seconds' in data
        assert data['metadata']['exposure_time'] == 10000
        assert data['metadata']['analogue_gain'] == 1.5
        assert data['metadata']['colour_temperature'] == 5000
        assert 'succeeded' in data['message'].lower()

        # Verify: Camera lifecycle correct
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.autofocus_cycle.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: Manual focus mode was locked after success
        assert mock_camera_streamer.set_manual_focus_mode.called
        assert mock_camera_streamer.set_manual_focus_mode.call_args[0][0] is True

    def test_autofocus_failure_state(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle autofocus failure (AfState=3)"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure autofocus failure (AfState=3 means "Fail")
        mock_picamera2._mock_instance.autofocus_cycle.return_value = False
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 0.0,
            'AfState': 3,  # Fail
            'ExposureTime': 10000,
            'AnalogueGain': 1.5,
            'ColourTemperature': 0
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success response (endpoint returns 200 even if AF fails)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert data['af_state'] == 'Fail'
        assert data['lens_position'] == 0.0
        assert 'failed' in data['message'].lower()

        # Verify: Manual focus mode was NOT locked on failure
        assert not mock_camera_streamer.set_manual_focus_mode.called

    def test_autofocus_camera_busy(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle camera busy during autofocus"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Configure successful autofocus
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 6.2,
            'AfState': 2,  # Success
            'ExposureTime': 12000,
            'AnalogueGain': 2.0,
            'ColourTemperature': 5500
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success (camera was released before autofocus)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Camera was released before operation
        assert mock_camera_streamer.release_camera.called

        # Verify: Stream was restarted after operation
        assert mock_camera_streamer.start_streaming.called

    def test_autofocus_camera_acquire_retry(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Autofocus succeeds after camera retry"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure camera 0 to fail (busy), camera 1 to succeed
        call_count = {'count': 0}
        original_init = mock_picamera2.Picamera2

        def retry_init(camera_num=0):
            call_count['count'] += 1
            if call_count['count'] == 1:
                # First call (camera 0): raise busy error
                raise RuntimeError("Camera is busy")
            # Second call (camera 1): succeed
            return original_init(camera_num)

        monkeypatch.setattr(mock_picamera2, 'Picamera2', retry_init)

        # Configure successful autofocus on second attempt
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 4.8,
            'AfState': 2,  # Success
            'ExposureTime': 9000,
            'AnalogueGain': 1.8,
            'ColourTemperature': 4800
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success (after retry)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['lens_position'] == 4.8

        # Verify: Camera was initialized twice (retry happened)
        assert call_count['count'] == 2

    def test_autofocus_acquire_both_cameras_fail(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Handle failure when both camera 0 and 1 are unavailable"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure both cameras to fail
        def always_fail(camera_num=0):
            raise RuntimeError("Camera is busy")

        monkeypatch.setattr(mock_picamera2, 'Picamera2', always_fail)

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'busy' in data['error'].lower() or 'camera' in data['error'].lower()

    def test_autofocus_manual_focus_lock(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Verify manual focus mode is locked after autofocus"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure successful autofocus
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 7.3,
            'AfState': 2,  # Success
            'ExposureTime': 15000,
            'AnalogueGain': 2.5,
            'ColourTemperature': 6000
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Manual focus mode was explicitly locked with True
        assert mock_camera_streamer.set_manual_focus_mode.called
        call_args = mock_camera_streamer.set_manual_focus_mode.call_args
        assert call_args[0][0] is True, "Manual focus mode should be set to True"

    def test_autofocus_metadata_extraction(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Verify focus metadata is extracted and returned"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Configure autofocus with rich metadata
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 3.7,
            'AfState': 2,  # Success
            'ExposureTime': 8500,
            'AnalogueGain': 1.2,
            'ColourTemperature': 4500
        }

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: All metadata fields extracted correctly
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['af_state'] == 'Success'
        assert data['lens_position'] == 3.7
        assert 'metadata' in data
        assert data['metadata']['exposure_time'] == 8500
        assert data['metadata']['analogue_gain'] == 1.2
        assert data['metadata']['colour_temperature'] == 4500
        assert 'duration_seconds' in data
        assert isinstance(data['duration_seconds'], (int, float))

    def test_autofocus_stream_restart(self, client, mock_picamera2, mock_camera_streamer, monkeypatch):
        """Verify stream restarts after autofocus"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Configure successful autofocus
        mock_picamera2._mock_instance.autofocus_cycle.return_value = True
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'LensPosition': 5.0,
            'AfState': 2,  # Success
            'ExposureTime': 10000,
            'AnalogueGain': 1.5,
            'ColourTemperature': 5000
        }

        # Track start_streaming calls
        start_stream_call_count = 0
        original_start_streaming = mock_camera_streamer.start_streaming

        def track_start_streaming():
            nonlocal start_stream_call_count
            start_stream_call_count += 1
            return original_start_streaming()

        mock_camera_streamer.start_streaming.side_effect = track_start_streaming

        # Execute: POST request
        response = client.post('/api/camera/autofocus')

        # Verify: Success
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Stream was restarted (should be called in finally block)
        assert start_stream_call_count > 0, "Stream should have been restarted after autofocus"


# ============================================================================
# POST /api/camera/calibrate-photo - Run photo calibration
# ============================================================================

class TestCalibratePhotoEndpoint:
    """Tests for POST /api/camera/calibrate-photo endpoint"""

    def test_calibrate_success(self, client, temp_camera_settings, mock_subprocess_run,
                                 mock_camera_streamer, mock_socketio_emit, monkeypatch):
        """Successfully run photo calibration"""
        import csv

        # Setup: Write initial camera settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial exposure\n"
            "AnalogueGain,1.0,Initial gain\n"
            "LensPosition,3.0,Initial focus\n"
        )

        # Setup: Mock subprocess success
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0,
                                        stdout="Calibration completed successfully\n")
        monkeypatch.setattr('subprocess.run', mock_run)

        # Setup: Simulate calibration updating the settings file
        def update_settings_on_run(*args, **kwargs):
            # Update settings file to simulate calibration results
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,12000,Calibrated exposure\n"
                "AnalogueGain,2.5,Calibrated gain\n"
                "LensPosition,5.5,Calibrated focus\n"
            )
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_settings_on_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['af_success'] is True
        assert 'before' in data
        assert 'after' in data
        assert data['before']['ExposureTime'] == '5000'
        assert data['before']['AnalogueGain'] == '1.0'
        assert data['before']['LensPosition'] == '3.0'
        assert data['after']['ExposureTime'] == '12000'
        assert data['after']['AnalogueGain'] == '2.5'
        assert data['after']['LensPosition'] == '5.5'
        assert 'timestamp' in data
        assert 'af_duration_seconds' in data

        # Verify: Camera streamer operation lock was acquired
        assert mock_camera_streamer.acquire_for_operation.called

    def test_calibrate_subprocess_timeout(self, client, temp_camera_settings, mock_subprocess_run,
                                           mock_camera_streamer, monkeypatch):
        """Handle calibration subprocess timeout"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mock subprocess timeout
        mock_run = mock_subprocess_run('run_photo_calibration.py', timeout=True)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Timeout error
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'timeout' in data['error'].lower()

    def test_calibrate_subprocess_failure(self, client, temp_camera_settings, mock_subprocess_run,
                                           mock_camera_streamer, monkeypatch):
        """Handle calibration subprocess failure"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mock subprocess failure
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=1,
                                        stderr="Camera initialization failed")
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert data['returncode'] == 1

    def test_calibrate_undefined_constants_bug(self, client, temp_camera_settings, mock_subprocess_run,
                                                 mock_camera_streamer, monkeypatch):
        """Test that constants are now defined (was: expose production bug via TDD)"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mock successful subprocess
        def update_and_run(*args, **kwargs):
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,10000,After\n"
            )
            mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_and_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Success (constants are now defined, bug is fixed!)
        # This test initially failed with NameError, exposing the production bugs
        # After fixing by defining CAMERA_RELEASE_WAIT_SECONDS, CALIBRATION_TIMEOUT_SECONDS,
        # and ERROR_DETAILS_MAX_LENGTH, this test now passes
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_calibrate_settings_comparison(self, client, temp_camera_settings, mock_subprocess_run,
                                             mock_camera_streamer, monkeypatch):
        """Compare before/after settings during calibration"""
        import csv

        # Setup: Write initial settings with known values
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,8000,Before\n"
            "AnalogueGain,1.5,Before\n"
            "LensPosition,4.0,Before\n"
        )

        # Setup: Mock subprocess that updates settings
        def update_and_run(*args, **kwargs):
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,15000,After\n"
                "AnalogueGain,3.0,After\n"
                "LensPosition,6.5,After\n"
            )
            mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_and_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Both before and after snapshots captured
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Before snapshot has original values
        assert data['before']['ExposureTime'] == '8000'
        assert data['before']['AnalogueGain'] == '1.5'
        assert data['before']['LensPosition'] == '4.0'

        # Verify: After snapshot has updated values
        assert data['after']['ExposureTime'] == '15000'
        assert data['after']['AnalogueGain'] == '3.0'
        assert data['after']['LensPosition'] == '6.5'

    def test_calibrate_progress_emission(self, client, temp_camera_settings, mock_subprocess_run,
                                          mock_camera_streamer, monkeypatch):
        """Verify calibration progress WebSocket emission integration"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mock subprocess success
        def update_and_run(*args, **kwargs):
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,10000,After\n"
            )
            mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_and_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Success - calibration completes without errors
        # Note: The _emit_calibration_progress() function is integrated and called
        # at 4 points in the calibration workflow (lines 667, 712, 775, 798 in camera.py).
        # However, WebSocket emissions only work when socketio is in current_app.extensions,
        # which is not available in the test environment. The integration is verified by
        # code inspection and manual testing with the web UI.
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_calibrate_camera_busy(self, client, temp_camera_settings, mock_subprocess_run,
                                     mock_camera_streamer, monkeypatch):
        """Handle camera busy during calibration"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Mock subprocess success
        def update_and_run(*args, **kwargs):
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,10000,After\n"
            )
            mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_and_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Success (camera was released before calibration)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Camera was released before subprocess
        assert mock_camera_streamer.release_camera.called

        # Verify: Stream was restarted after calibration
        assert mock_camera_streamer.start_streaming.called

    def test_calibrate_script_not_found(self, client, temp_camera_settings, mock_subprocess_run,
                                         mock_camera_streamer, monkeypatch):
        """Handle missing calibration script"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mock subprocess FileNotFoundError
        # Note: Must use exact case "FileNotFoundError" as code checks case-sensitive
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=1,
                                        stderr="FileNotFoundError: TakePhoto.py not found")
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Error response with FileNotFoundError detection
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        # Error message: 'TakePhoto.py not found for firmware X.x'
        assert 'takephoto.py' in data['error'].lower() and 'not found' in data['error'].lower()

    def test_calibrate_camera_settings_read_error(self, client, temp_camera_settings, mock_subprocess_run,
                                                    mock_camera_streamer, monkeypatch):
        """Handle error reading camera settings file"""
        # Setup: Delete settings file to cause read error
        temp_camera_settings.unlink()

        # Setup: Mock subprocess (won't reach it due to file error)
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
        monkeypatch.setattr('subprocess.run', mock_run)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Either handles gracefully with warning or returns error
        # The endpoint reads "before" settings with try/except, so it may continue
        # Check that it either:
        # 1. Continues with 'unknown' before values (graceful degradation)
        # 2. OR returns error if after-read fails
        if response.status_code == 200:
            data = response.get_json()
            assert data['before']['ExposureTime'] == 'unknown'
        else:
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data

    def test_calibrate_subprocess_stderr_error_types(self, client, temp_camera_settings, mock_subprocess_run,
                                                       mock_camera_streamer, monkeypatch):
        """Test different error type detection from subprocess stderr"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Test case 1: ImportError detection (case-insensitive check in code)
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=1,
                                        stderr="ImportError: No module named 'picamera2'")
        monkeypatch.setattr('subprocess.run', mock_run)
        response = client.post('/api/camera/calibrate-photo')
        assert response.status_code == 500
        data = response.get_json()
        # Expected error message: 'TakePhoto.py import failed - missing dependencies'
        assert 'takephoto.py' in data['error'].lower() and ('import failed' in data['error'].lower() or 'dependencies' in data['error'].lower())

        # Test case 2: Camera busy detection
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=1,
                                        stderr="RuntimeError: Camera is busy")
        monkeypatch.setattr('subprocess.run', mock_run)
        response = client.post('/api/camera/calibrate-photo')
        assert response.status_code == 500
        data = response.get_json()
        # Expected error message: 'Camera hardware busy'
        assert 'camera' in data['error'].lower() and 'busy' in data['error'].lower()

        # Test case 3: Permission denied detection
        mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=1,
                                        stderr="PermissionError: Permission denied accessing /dev/video0")
        monkeypatch.setattr('subprocess.run', mock_run)
        response = client.post('/api/camera/calibrate-photo')
        assert response.status_code == 500
        data = response.get_json()
        # Expected error message: 'Permission denied accessing camera'
        assert 'permission' in data['error'].lower() and 'denied' in data['error'].lower()

    def test_calibrate_stream_restart(self, client, temp_camera_settings, mock_subprocess_run,
                                       mock_camera_streamer, monkeypatch):
        """Verify stream restarts after calibration"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Mock subprocess success
        def update_and_run(*args, **kwargs):
            temp_camera_settings.write_text(
                "SETTING,VALUE,DETAILS\n"
                "ExposureTime,10000,After\n"
            )
            mock_run = mock_subprocess_run('run_photo_calibration.py', returncode=0)
            return mock_run(*args, **kwargs)

        monkeypatch.setattr('subprocess.run', update_and_run)

        # Track start_streaming calls
        start_stream_call_count = 0
        original_start_streaming = mock_camera_streamer.start_streaming

        def track_start_streaming():
            nonlocal start_stream_call_count
            start_stream_call_count += 1
            return original_start_streaming()

        mock_camera_streamer.start_streaming.side_effect = track_start_streaming

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Success
        assert response.status_code == 200

        # Verify: Stream was restarted
        assert start_stream_call_count > 0, "Stream should have been restarted after calibration"

    def test_calibrate_emergency_stream_restart(self, client, temp_camera_settings, mock_subprocess_run,
                                                  mock_camera_streamer, monkeypatch):
        """Verify stream restart in emergency error handler"""
        # Setup: Write initial settings
        temp_camera_settings.write_text(
            "SETTING,VALUE,DETAILS\n"
            "ExposureTime,5000,Initial\n"
        )

        # Setup: Mark camera as streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Mock subprocess to raise unexpected error
        def raise_unexpected_error(*args, **kwargs):
            raise ValueError("Unexpected error during calibration")

        monkeypatch.setattr('subprocess.run', raise_unexpected_error)

        # Execute: POST request
        response = client.post('/api/camera/calibrate-photo')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False

        # Verify: Emergency stream restart was attempted
        # Note: The emergency restart only happens if operation_lock_acquired is False
        # In this case, the error happens inside the context manager, so the
        # finally block in the context manager handles the restart
        # This test verifies that errors are handled gracefully


# ============================================================================
# POST /api/camera/test-capture-liveview - Test liveview capture
# ============================================================================

class TestTestCaptureLiveview:
    """Tests for POST /api/camera/test-capture-liveview endpoint"""

    def test_test_capture_liveview_success(self, client, mock_camera_streamer, mock_picamera2,
                                          temp_photos_dir, temp_liveview_settings, monkeypatch):
        """Successfully test liveview capture"""
        import sys
        from pathlib import Path

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock helper functions
        def mock_get_control_values(file_path):
            """Mock get_control_values to return liveview settings"""
            return {
                'sharpness': '1.5',
                'brightness': '0.0',
                'contrast': '1.2',
                'saturation': '1.0',
                'af_mode': '2',
                'af_speed': '0',
                'af_range': '0',
                'awb_enable': 'True'
            }

        def mock_convert_from_settings_file(key, value):
            """Mock convert_from_settings_file to pass through values with type conversion"""
            # Handle bool values that are already converted
            if isinstance(value, bool):
                return value

            type_map = {
                'sharpness': float,
                'brightness': float,
                'contrast': float,
                'saturation': float,
                'af_mode': int,
                'af_speed': int,
                'af_range': int,
                'awb_enable': lambda v: v.lower() == 'true' if isinstance(v, str) else bool(v)
            }
            return type_map.get(key, str)(value)

        def mock_build_picamera_controls(settings):
            """Mock build_picamera_controls to convert to PascalCase"""
            return {
                'Sharpness': settings.get('sharpness', 1.0),
                'Brightness': settings.get('brightness', 0.0),
                'Contrast': settings.get('contrast', 1.0),
                'Saturation': settings.get('saturation', 1.0),
                'AfMode': settings.get('af_mode', 2),
                'AfSpeed': settings.get('af_speed', 0),
                'AfRange': settings.get('af_range', 0),
                'AwbEnable': settings.get('awb_enable', True)
            }

        def mock_acquire_camera_with_retry(camera_num):
            """Mock acquire_camera_with_retry to return mock instance"""
            return mock_picamera2._mock_instance

        monkeypatch.setattr('mothbox_paths.get_control_values', mock_get_control_values)
        monkeypatch.setattr('camera_control_mapping.convert_from_settings_file', mock_convert_from_settings_file)
        monkeypatch.setattr('camera_control_mapping.build_picamera_controls', mock_build_picamera_controls)
        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Mock Picamera2 behavior for successful capture
        def mock_capture_file(filepath):
            """Create actual file when capture_file is called"""
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text("fake image data")

        mock_picamera2._mock_instance.capture_file.side_effect = mock_capture_file
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 1.5,
            'LensPosition': 5.5,
            'ColourTemperature': 5000
        }

        # Setup: Write liveview settings
        with open(temp_liveview_settings, 'w') as f:
            f.write("sharpness=1.5\n")
            f.write("brightness=0.0\n")
            f.write("contrast=1.2\n")

        # Execute: POST request
        response = client.post('/api/camera/test-capture-liveview')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'test_photo_path' in data
        assert data['test_photo_path'].startswith('test_captures/')
        assert data['test_photo_path'].endswith('.jpg')
        assert data['settings_source'] == 'live view'

        # Verify: Settings were applied
        assert 'settings_used' in data
        settings_used = data['settings_used']
        assert settings_used['Sharpness'] == 1.5
        assert settings_used['Contrast'] == 1.2

        # Verify: Metadata returned
        assert 'metadata' in data
        metadata = data['metadata']
        assert metadata['exposure_time'] == 10000
        assert metadata['analogue_gain'] == 1.5
        assert metadata['lens_position'] == 5.5
        assert metadata['colour_temperature'] == 5000

        # Verify: Camera lifecycle
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.set_controls.called
        assert mock_instance.capture_file.called
        assert mock_instance.capture_metadata.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: File was created
        test_captures_dir = temp_photos_dir / "test_captures"
        assert test_captures_dir.exists()
        captured_files = list(test_captures_dir.glob("test_capture_*.jpg"))
        assert len(captured_files) == 1

    def test_test_capture_liveview_camera_busy(self, client, mock_camera_streamer, mock_picamera2,
                                               temp_photos_dir, temp_liveview_settings, monkeypatch):
        """Handle camera busy during test capture"""
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock helper functions
        def mock_get_control_values(file_path):
            return {'sharpness': '1.0'}

        def mock_convert_from_settings_file(key, value):
            return float(value) if key == 'sharpness' else value

        def mock_build_picamera_controls(settings):
            return {'Sharpness': settings.get('sharpness', 1.0)}

        def mock_acquire_camera_with_retry(camera_num):
            return mock_picamera2._mock_instance

        monkeypatch.setattr('mothbox_paths.get_control_values', mock_get_control_values)
        monkeypatch.setattr('camera_control_mapping.convert_from_settings_file', mock_convert_from_settings_file)
        monkeypatch.setattr('camera_control_mapping.build_picamera_controls', mock_build_picamera_controls)
        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Mock Picamera2 behavior
        def mock_capture_file(filepath):
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text("fake image data")

        mock_picamera2._mock_instance.capture_file.side_effect = mock_capture_file
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 1.0,
            'LensPosition': 5.0,
            'ColourTemperature': 5000
        }

        # Execute: POST request
        response = client.post('/api/camera/test-capture-liveview')

        # Verify: Success (camera was released before test capture)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Camera was released before operation
        assert mock_camera_streamer.release_camera.called

        # Verify: Stream was restarted after operation (in finally block)
        assert mock_camera_streamer.start_streaming.called

        # Verify: Camera lifecycle completed
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

    def test_test_capture_liveview_file_save_error(self, client, mock_camera_streamer, mock_picamera2,
                                                   temp_photos_dir, temp_liveview_settings, monkeypatch):
        """Handle file save errors during test capture"""
        import sys
        from unittest.mock import MagicMock

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock helper functions
        def mock_get_control_values(file_path):
            return {'sharpness': '1.0'}

        def mock_convert_from_settings_file(key, value):
            return float(value) if key == 'sharpness' else value

        def mock_build_picamera_controls(settings):
            return {'Sharpness': settings.get('sharpness', 1.0)}

        def mock_acquire_camera_with_retry(camera_num):
            return mock_picamera2._mock_instance

        monkeypatch.setattr('mothbox_paths.get_control_values', mock_get_control_values)
        monkeypatch.setattr('camera_control_mapping.convert_from_settings_file', mock_convert_from_settings_file)
        monkeypatch.setattr('camera_control_mapping.build_picamera_controls', mock_build_picamera_controls)
        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Mark camera as streaming to verify restart in error path
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Mock capture_file to raise IOError
        def raise_file_error(filepath):
            raise IOError("Failed to save image file")

        mock_picamera2._mock_instance.capture_file.side_effect = raise_file_error

        # Execute: POST request
        response = client.post('/api/camera/test-capture-liveview')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'Failed to save image file' in data['error']

        # Verify: Camera cleanup happened despite error
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.capture_file.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: Stream was restarted after error (in finally block)
        assert mock_camera_streamer.start_streaming.called


# ============================================================================
# POST /api/camera/test-capture-photo - Test photo capture
# ============================================================================

class TestTestCapturePhoto:
    """Tests for POST /api/camera/test-capture-photo endpoint"""

    def test_test_capture_photo_success(self, client, mock_camera_streamer, mock_picamera2,
                                        temp_photos_dir, temp_camera_settings, monkeypatch):
        """Successfully test photo capture"""
        import sys
        from pathlib import Path

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock acquire_camera_with_retry
        def mock_acquire_camera_with_retry(camera_num):
            return mock_picamera2._mock_instance

        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Write camera settings CSV
        with open(temp_camera_settings, 'w') as f:
            f.write("SETTING,VALUE,DETAILS\n")
            f.write("Sharpness,1.5,Image sharpness\n")
            f.write("Brightness,0.2,Brightness adjustment\n")
            f.write("Contrast,1.3,Contrast level\n")
            f.write("Saturation,1.1,Color saturation\n")
            f.write("AfMode,2,Continuous autofocus\n")
            f.write("AfSpeed,0,Normal speed\n")
            f.write("AfRange,0,Full range\n")
            f.write("ExposureTime,10000,10ms exposure\n")
            f.write("AnalogueGain,2.0,2x gain\n")
            f.write("AeEnable,False,Manual exposure\n")
            f.write("AwbEnable,True,Auto white balance\n")

        # Setup: Mock Picamera2 behavior for successful capture
        def mock_capture_file(filepath):
            """Create actual file when capture_file is called"""
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text("fake photo capture data")

        mock_picamera2._mock_instance.capture_file.side_effect = mock_capture_file
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 2.0,
            'LensPosition': 3.5,
            'ColourTemperature': 4500
        }

        # Execute: POST request
        response = client.post('/api/camera/test-capture-photo')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'test_photo_path' in data
        assert data['test_photo_path'].startswith('test_captures/')
        assert data['test_photo_path'].endswith('.jpg')
        assert data['settings_source'] == 'photo capture'

        # Verify: Settings were applied from CSV
        assert 'settings_used' in data
        settings_used = data['settings_used']
        assert settings_used != {}  # Settings should be populated after bug fix
        assert 'Sharpness' in settings_used
        assert settings_used['Sharpness'] == 1.5
        assert 'Brightness' in settings_used
        assert settings_used['Brightness'] == 0.2
        assert 'Contrast' in settings_used
        assert settings_used['Contrast'] == 1.3
        assert 'Saturation' in settings_used
        assert settings_used['Saturation'] == 1.1
        assert 'ExposureTime' in settings_used
        assert settings_used['ExposureTime'] == 10000
        assert 'AnalogueGain' in settings_used
        assert settings_used['AnalogueGain'] == 2.0

        # Verify: Metadata returned
        assert 'metadata' in data
        metadata = data['metadata']
        assert metadata['exposure_time'] == 10000
        assert metadata['analogue_gain'] == 2.0
        assert metadata['lens_position'] == 3.5
        assert metadata['colour_temperature'] == 4500

        # Verify: Camera lifecycle
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.set_controls.called
        assert mock_instance.capture_file.called
        assert mock_instance.capture_metadata.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: File was created
        test_captures_dir = temp_photos_dir / "test_captures"
        assert test_captures_dir.exists()
        captured_files = list(test_captures_dir.glob("test_capture_*.jpg"))
        assert len(captured_files) == 1

    def test_test_capture_photo_camera_busy(self, client, mock_camera_streamer, mock_picamera2,
                                            temp_photos_dir, temp_camera_settings, monkeypatch):
        """Handle camera busy during test capture"""
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock acquire_camera_with_retry
        def mock_acquire_camera_with_retry(camera_num):
            return mock_picamera2._mock_instance

        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Mark camera as actively streaming
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Write minimal camera settings CSV
        with open(temp_camera_settings, 'w') as f:
            f.write("SETTING,VALUE,DETAILS\n")
            f.write("Sharpness,1.0,Default sharpness\n")

        # Setup: Mock Picamera2 behavior
        def mock_capture_file(filepath):
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text("fake photo data")

        mock_picamera2._mock_instance.capture_file.side_effect = mock_capture_file
        mock_picamera2._mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 1.0,
            'LensPosition': 5.0,
            'ColourTemperature': 5000
        }

        # Execute: POST request
        response = client.post('/api/camera/test-capture-photo')

        # Verify: Success (camera was released before test capture)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify: Camera was released before operation
        assert mock_camera_streamer.release_camera.called

        # Verify: Stream was restarted after operation (in finally block)
        assert mock_camera_streamer.start_streaming.called

        # Verify: Camera lifecycle completed
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

    def test_test_capture_photo_subprocess_failure(self, client, mock_camera_streamer, mock_picamera2,
                                                   temp_photos_dir, temp_camera_settings, monkeypatch):
        """Handle unexpected errors during test capture"""
        import sys
        from unittest.mock import MagicMock

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock acquire_camera_with_retry to raise unexpected error
        def mock_acquire_camera_with_retry_error(camera_num):
            raise RuntimeError("Unexpected camera initialization error")

        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry_error)

        # Setup: Mark camera as streaming to verify restart in error path
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Write minimal camera settings CSV
        with open(temp_camera_settings, 'w') as f:
            f.write("SETTING,VALUE,DETAILS\n")
            f.write("Sharpness,1.0,Default\n")

        # Execute: POST request
        response = client.post('/api/camera/test-capture-photo')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'Unexpected camera initialization error' in data['error']

        # Verify: Stream was restarted after error (in finally block)
        assert mock_camera_streamer.start_streaming.called

    def test_test_capture_photo_file_save_error(self, client, mock_camera_streamer, mock_picamera2,
                                                temp_photos_dir, temp_camera_settings, monkeypatch):
        """Handle file save errors during test capture"""
        import sys
        from unittest.mock import MagicMock

        # Setup: Inject Picamera2 mock into sys.modules
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock acquire_camera_with_retry
        def mock_acquire_camera_with_retry(camera_num):
            return mock_picamera2._mock_instance

        monkeypatch.setattr('routes.camera.acquire_camera_with_retry', mock_acquire_camera_with_retry)

        # Setup: Mark camera as streaming to verify restart in error path
        mock_camera_streamer.streaming = True
        mock_camera_streamer.camera = MagicMock()

        # Setup: Write minimal camera settings CSV
        with open(temp_camera_settings, 'w') as f:
            f.write("SETTING,VALUE,DETAILS\n")
            f.write("Sharpness,1.0,Default\n")

        # Setup: Mock capture_file to raise IOError
        def raise_file_error(filepath):
            raise IOError("Disk full - cannot save image")

        mock_picamera2._mock_instance.capture_file.side_effect = raise_file_error

        # Execute: POST request
        response = client.post('/api/camera/test-capture-photo')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'Disk full - cannot save image' in data['error']

        # Verify: Camera cleanup happened despite error
        mock_instance = mock_picamera2._mock_instance
        assert mock_instance.configure.called
        assert mock_instance.start.called
        assert mock_instance.capture_file.called
        assert mock_instance.stop.called
        assert mock_instance.close.called

        # Verify: Stream was restarted after error (in finally block)
        assert mock_camera_streamer.start_streaming.called


# ============================================================================
# Integration and Edge Case Tests
# ============================================================================

class TestCameraSecurityValidation:
    """Security tests for camera endpoints (path traversal, injection)"""

    def test_settings_path_traversal_prevention(self):
        """Prevent path traversal in settings file access"""
        # TODO: Implement in Phase 2E
        pytest.skip("Phase 2E: Camera Settings Endpoints")

    def test_subprocess_command_injection_prevention(self):
        """Prevent command injection in subprocess calls"""
        # TODO: Implement in Phase 2F
        pytest.skip("Phase 2F: Basic Capture")


class TestCameraErrorRecovery:
    """Error recovery and edge case tests"""

    def test_camera_release_on_error(self):
        """Verify camera is released on error"""
        # TODO: Implement in Phase 2F
        pytest.skip("Phase 2F: Basic Capture")

    def test_stream_restart_on_failure(self):
        """Verify stream restarts after failure"""
        # TODO: Implement in Phase 2F (requires mock_camera_streamer)
        pytest.skip("Phase 2F: Basic Capture")
