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

    def test_autofocus_success(self):
        """Successfully run autofocus cycle"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_autofocus_camera_busy(self):
        """Handle camera busy during autofocus"""
        # TODO: Implement in Phase 2H (requires mock_camera_streamer)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_autofocus_camera_acquire_retry(self):
        """Autofocus succeeds after camera retry"""
        # TODO: Implement in Phase 2H (requires mock_picamera2)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_autofocus_manual_focus_lock(self):
        """Verify manual focus mode is locked after autofocus"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_autofocus_metadata_extraction(self):
        """Verify focus metadata is extracted and saved"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_autofocus_stream_restart(self):
        """Verify stream restarts after autofocus"""
        # TODO: Implement in Phase 2H (requires mock_camera_streamer)
        pytest.skip("Phase 2H: Autofocus & Calibration")


# ============================================================================
# POST /api/camera/calibrate-photo - Run photo calibration
# ============================================================================

class TestCalibratePhotoEndpoint:
    """Tests for POST /api/camera/calibrate-photo endpoint"""

    def test_calibrate_success(self):
        """Successfully run photo calibration"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_subprocess_timeout(self):
        """Handle calibration subprocess timeout"""
        # TODO: Implement in Phase 2H (requires mock_subprocess_run)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_subprocess_failure(self):
        """Handle calibration subprocess failure"""
        # TODO: Implement in Phase 2H (requires mock_subprocess_run)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_csv_parsing(self):
        """Parse and validate calibration CSV output"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_csv_parsing_invalid_format(self):
        """Handle invalid CSV format from calibration"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_settings_comparison(self):
        """Compare before/after settings during calibration"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_progress_emission(self):
        """Verify calibration progress WebSocket emissions"""
        # TODO: Implement in Phase 2H (requires mock_socketio_emit)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_camera_busy(self):
        """Handle camera busy during calibration"""
        # TODO: Implement in Phase 2H (requires mock_camera_streamer)
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_permission_error(self):
        """Handle permission errors during calibration"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")

    def test_calibrate_file_not_found(self):
        """Handle missing calibration script"""
        # TODO: Implement in Phase 2H
        pytest.skip("Phase 2H: Autofocus & Calibration")


# ============================================================================
# POST /api/camera/test-capture-liveview - Test liveview capture
# ============================================================================

class TestTestCaptureLiveview:
    """Tests for POST /api/camera/test-capture-liveview endpoint"""

    def test_test_capture_liveview_success(self):
        """Successfully test liveview capture"""
        # TODO: Implement in Phase 2I
        pytest.skip("Phase 2I: Test Capture Workflows")

    def test_test_capture_liveview_camera_busy(self):
        """Handle camera busy during test capture"""
        # TODO: Implement in Phase 2I (requires mock_camera_streamer)
        pytest.skip("Phase 2I: Test Capture Workflows")

    def test_test_capture_liveview_file_save_error(self):
        """Handle file save errors during test capture"""
        # TODO: Implement in Phase 2I
        pytest.skip("Phase 2I: Test Capture Workflows")


# ============================================================================
# POST /api/camera/test-capture-photo - Test photo capture
# ============================================================================

class TestTestCapturePhoto:
    """Tests for POST /api/camera/test-capture-photo endpoint"""

    def test_test_capture_photo_success(self):
        """Successfully test photo capture"""
        # TODO: Implement in Phase 2I
        pytest.skip("Phase 2I: Test Capture Workflows")

    def test_test_capture_photo_camera_busy(self):
        """Handle camera busy during test capture"""
        # TODO: Implement in Phase 2I (requires mock_camera_streamer)
        pytest.skip("Phase 2I: Test Capture Workflows")

    def test_test_capture_photo_subprocess_failure(self):
        """Handle subprocess failure during test capture"""
        # TODO: Implement in Phase 2I (requires mock_subprocess_run)
        pytest.skip("Phase 2I: Test Capture Workflows")

    def test_test_capture_photo_file_save_error(self):
        """Handle file save errors during test capture"""
        # TODO: Implement in Phase 2I
        pytest.skip("Phase 2I: Test Capture Workflows")


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
