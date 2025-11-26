"""
Unit tests for POST /api/camera/instant-capture endpoint

Tests the instant capture functionality which captures photos using current
live view settings and saves them with instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg
naming convention.

Coverage areas:
1. Serial number extraction from /proc/cpuinfo
2. Settings extraction from camera_streamer (get_current_settings)
3. Lens position locking (AfMode=0) for instant capture
4. EXIF MakerNote with capture_type="instant"
5. Filename format validation (instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg)
6. Error handling scenarios (camera busy, capture failure, invalid settings)
7. GPS embedding when available
8. Response format validation

Related files:
- webui/backend/routes/camera.py: instant_capture() function (lines 1414-1556)
- webui/backend/routes/camera.py: _execute_instant_capture() function (lines 1559-1834)

Test structure follows existing patterns from test_camera_routes.py.
Uses mocking extensively to run without hardware.
"""
import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call, Mock
from io import StringIO
import sys

# Import after path setup
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


# ============================================================================
# Test Class: POST /api/camera/instant-capture
# ============================================================================

@pytest.mark.unit
class TestInstantCaptureEndpoint:
    """Tests for POST /api/camera/instant-capture endpoint"""

    # ========================================================================
    # Success Path Tests
    # ========================================================================

    def test_instant_capture_success_basic(self, client, mock_picamera2, mock_camera_streamer,
                                          temp_photos_dir, monkeypatch):
        """Successfully capture instant photo with default settings"""
        # Setup: Inject Picamera2 mock
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock serial number extraction
        mock_cpuinfo = "Serial\t\t: 1000000012345678\n"
        def mock_open_cpuinfo(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO(mock_cpuinfo)
            raise FileNotFoundError(f"Mock open: {file}")

        # Setup: Configure camera_streamer with live settings
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.5,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'af_mode': 2,  # Continuous AF
            'af_speed': 0,
            'af_range': 0,
            'lens_position': 5.5,
            'awb_enable': True,
            'ae_enable': True,
            'noise_reduction_mode': 2,
        }

        # Setup: Configure Picamera2 mock for capture
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 2.5,
            'LensPosition': 5.5,
            'ColourTemperature': 5500,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        # Setup: Mock controls.txt for mothbox name
        temp_controls = temp_photos_dir.parent / "controls.txt"
        temp_controls.write_text("name=TestMothbox\n")

        # Mock file operations
        original_open = open
        def patched_open(file, *args, **kwargs):
            file_str = str(file)
            if file_str == "/proc/cpuinfo":
                return StringIO(mock_cpuinfo)
            elif file_str.endswith("controls.txt"):
                return StringIO("name=TestMothbox\n")
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Image.fromarray and save
        mock_image = MagicMock()
        mock_pil_module = MagicMock()
        mock_pil_module.Image.fromarray.return_value = mock_image
        monkeypatch.setitem(sys.modules, 'PIL.Image', mock_pil_module.Image)
        monkeypatch.setitem(sys.modules, 'PIL', mock_pil_module)

        # Setup: Mock piexif
        mock_piexif = MagicMock()
        mock_piexif.dump.return_value = b'EXIF_DATA'
        monkeypatch.setitem(sys.modules, 'piexif', mock_piexif)

        # Execute: POST request
        response = client.post('/api/camera/instant-capture')

        # Verify: Success response
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'photo_path' in data
        assert 'instant_' in data['photo_path']
        assert '1000000012345678' in data['photo_path']  # Serial number in filename
        assert data['settings_source'] == 'instant capture'

        # Verify: Metadata returned
        assert 'metadata' in data
        assert data['metadata']['exposure_time'] == 10000
        assert data['metadata']['analogue_gain'] == 2.5
        assert data['metadata']['lens_position'] == 5.5
        assert data['metadata']['colour_temperature'] == 5500

        # Verify: Lens position was locked (AfMode=0)
        assert mock_instance.set_controls.called
        controls = mock_instance.set_controls.call_args[0][0]
        assert controls['AfMode'] == 0  # Manual AF to lock lens position
        assert controls['LensPosition'] == 5.5

    def test_instant_capture_serial_extraction_success(self, client, mock_camera_streamer, monkeypatch):
        """Serial number correctly extracted from /proc/cpuinfo"""
        # Setup: Mock cpuinfo with serial number
        mock_cpuinfo = (
            "processor\t: 0\n"
            "Model\t\t: Raspberry Pi 5 Model B Rev 1.0\n"
            "Serial\t\t: 10000000abcdef12\n"
        )

        # Setup: Mock camera_streamer (minimal for this test)
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Mock all file operations
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO(mock_cpuinfo)
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")

        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock entire capture flow to focus on serial extraction
        with patch('routes.camera._execute_instant_capture') as mock_execute:
            mock_execute.return_value = (
                {'success': True, 'photo_path': 'test_instant_2025_01_15__12_30_45_10000000abcdef12.jpg'},
                200
            )

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Serial number passed to execute function
            assert mock_execute.called
            call_args = mock_execute.call_args[0]
            filename_arg = call_args[3]  # 4th argument is filename
            assert '10000000abcdef12' in filename_arg

    def test_instant_capture_serial_extraction_fallback(self, client, mock_camera_streamer, monkeypatch):
        """Serial number falls back to 'UNKNOWN' when /proc/cpuinfo unavailable"""
        # Setup: Mock cpuinfo file not found
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                raise OSError("File not found")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")

        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock execute to verify fallback
        with patch('routes.camera._execute_instant_capture') as mock_execute:
            mock_execute.return_value = (
                {'success': True, 'photo_path': 'test_instant_2025_01_15__12_30_45_UNKNOWN.jpg'},
                200
            )

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: UNKNOWN serial in filename
            assert mock_execute.called
            filename_arg = mock_execute.call_args[0][3]
            assert 'UNKNOWN' in filename_arg

    def test_instant_capture_lens_position_locking(self, client, mock_picamera2, mock_camera_streamer,
                                                   temp_photos_dir, monkeypatch):
        """Lens position is locked by forcing AfMode=0 when lens_position is set"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Camera streamer returns settings with lens position
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 2,  # Continuous AF (should be overridden to Manual)
            'lens_position': 7.2,  # Locked focus position
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo and controls
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: 1234567890abcdef\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2 and PIL
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 5000,
            'AnalogueGain': 1.5,
            'LensPosition': 7.2,
            'ColourTemperature': 5000,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', return_value=b'EXIF'):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: AfMode forced to 0 (Manual) and LensPosition preserved
            assert mock_instance.set_controls.called
            controls = mock_instance.set_controls.call_args[0][0]
            assert controls['AfMode'] == 0, "AfMode should be forced to 0 (Manual) to lock lens position"
            assert controls['LensPosition'] == 7.2, "Lens position should be preserved"

    def test_instant_capture_filename_format(self, client, mock_camera_streamer, monkeypatch):
        """Filename format is instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg"""
        import re
        from datetime import datetime

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: 1000000099aabbcc\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock execute to capture filename
        captured_filename = None
        def mock_execute(controls, af_mode, source, filename):
            nonlocal captured_filename
            captured_filename = filename
            return (
                {'success': True, 'photo_path': f'test_captures/{filename}'},
                200
            )

        with patch('routes.camera._execute_instant_capture', side_effect=mock_execute):
            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Filename format matches instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg
            assert captured_filename is not None
            pattern = r'^instant_(\d{4})_(\d{2})_(\d{2})__(\d{2})_(\d{2})_(\d{2})_([0-9a-fA-F]+)\.jpg$'
            match = re.match(pattern, captured_filename)
            assert match is not None, f"Filename '{captured_filename}' doesn't match expected format"

            # Verify: Timestamp is reasonable (within 5 seconds of now)
            year, month, day, hour, minute, second, serial = match.groups()
            file_time = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
            now = datetime.now()
            time_diff = abs((now - file_time).total_seconds())
            assert time_diff < 5, f"Timestamp {file_time} too far from current time {now}"

            # Verify: Serial number is correct
            assert serial == '1000000099aabbcc'

    def test_instant_capture_exif_makernote_capture_type(self, client, mock_picamera2,
                                                         mock_camera_streamer, temp_photos_dir,
                                                         monkeypatch):
        """EXIF MakerNote contains capture_type='instant'"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Create temp controls file with mothbox name
        temp_controls = temp_photos_dir.parent / "controls.txt"
        temp_controls.write_text("name=TestBox\n")

        # Setup: Mock file operations
        original_open = open
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: testserial\n")
            return original_open(file, *args, **kwargs)
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 8000,
            'AnalogueGain': 2.0,
            'LensPosition': 6.0,
            'ColourTemperature': 5200,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        # Setup: Capture piexif.dump call to verify MakerNote
        captured_exif_dict = None
        def mock_dump(exif_dict):
            nonlocal captured_exif_dict
            captured_exif_dict = exif_dict
            return b'EXIF_DATA'

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', side_effect=mock_dump):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: EXIF dict was captured
            assert captured_exif_dict is not None

            # Verify: MakerNote contains capture_type="instant"
            assert 'Exif' in captured_exif_dict
            exif_ifd = captured_exif_dict['Exif']

            # MakerNote is piexif.ExifIFD.MakerNote (37500)
            # It contains JSON-encoded data with capture_type
            assert 37500 in exif_ifd, "MakerNote should be in EXIF IFD"

            maker_note_bytes = exif_ifd[37500]
            maker_note_str = maker_note_bytes.decode('utf-8')
            maker_note_data = json.loads(maker_note_str)

            assert maker_note_data['capture_type'] == 'instant'
            # Mothbox name may be 'mothbox' or 'TestBox' depending on controls.txt access
            assert 'mothbox_name' in maker_note_data
            assert maker_note_data['mothbox_name'] in ['TestBox', 'mothbox']
            assert 'sensor' in maker_note_data
            assert 'focus_mode' in maker_note_data
            assert 'lens_position' in maker_note_data

    def test_instant_capture_gps_embedding_when_available(self, client, mock_picamera2,
                                                          mock_camera_streamer, temp_photos_dir,
                                                          temp_controls_file, monkeypatch):
        """GPS EXIF is embedded when GPS fix is available in controls.txt"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Write GPS data to controls.txt
        temp_controls_file.write_text(
            "name=GPSBox\n"
            "lat=37.7749\n"
            "lon=-122.4194\n"
            "gps_fix_mode=3\n"
            "alt=50\n"
            "gpstime=2025-01-15T12:30:45Z\n"
        )

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo only
        mock_cpuinfo_content = "Serial\t\t: gpstest123\n"

        original_open = open
        def patched_open(file_path, *args, **kwargs):
            if "/proc/cpuinfo" in str(file_path):
                return StringIO(mock_cpuinfo_content)
            return original_open(file_path, *args, **kwargs)

        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 1.8,
            'LensPosition': 5.0,
            'ColourTemperature': 5500,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        # Setup: Capture EXIF dict to verify GPS IFD
        captured_exif_dict = None
        def mock_dump(exif_dict):
            nonlocal captured_exif_dict
            captured_exif_dict = exif_dict
            return b'EXIF_WITH_GPS'

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', side_effect=mock_dump):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Response success
            assert response.status_code == 200

            # Verify: GPS IFD was added to EXIF dict
            assert captured_exif_dict is not None
            assert 'GPS' in captured_exif_dict, "GPS IFD should be in EXIF dict when GPS fix available"

            gps_ifd = captured_exif_dict['GPS']
            assert len(gps_ifd) > 0, "GPS IFD should contain GPS tags"

            # GPS IFD should contain essential tags (exact tags depend on GPS fix quality)
            # Common tags: GPSVersionID=0, GPSLatitudeRef=1, GPSLatitude=2, GPSLongitudeRef=3, GPSLongitude=4
            # The gps_exif_lib module should have embedded at least latitude/longitude
            # Just verify GPS IFD exists and has tags - specific tag validation is in gps_exif_lib tests
            assert len(gps_ifd) >= 4, f"GPS IFD should have at least 4 tags, got {len(gps_ifd)} tags"

    def test_instant_capture_no_gps_when_unavailable(self, client, mock_picamera2,
                                                     mock_camera_streamer, temp_photos_dir,
                                                     temp_controls_file, monkeypatch):
        """GPS EXIF is not embedded when GPS fix is unavailable"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Write controls.txt WITHOUT GPS fix
        temp_controls_file.write_text(
            "name=NoGPSBox\n"
            "gps_fix_mode=0\n"
        )

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo only
        mock_cpuinfo_content = "Serial\t\t: nogps456\n"

        original_open = open
        def patched_open(file_path, *args, **kwargs):
            if "/proc/cpuinfo" in str(file_path):
                return StringIO(mock_cpuinfo_content)
            return original_open(file_path, *args, **kwargs)

        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 7000,
            'AnalogueGain': 1.2,
            'LensPosition': 4.5,
            'ColourTemperature': 5000,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        # Setup: Capture EXIF dict
        captured_exif_dict = None
        def mock_dump(exif_dict):
            nonlocal captured_exif_dict
            captured_exif_dict = exif_dict
            return b'EXIF_NO_GPS'

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', side_effect=mock_dump):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Response success
            assert response.status_code == 200

            # Verify: GPS IFD should be empty or missing
            assert captured_exif_dict is not None
            if 'GPS' in captured_exif_dict:
                assert len(captured_exif_dict['GPS']) == 0, "GPS IFD should be empty when no fix"

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_instant_capture_camera_streamer_not_initialized(self, client, monkeypatch):
        """Error when camera_streamer is not initialized"""
        # Setup: No camera_streamer in config
        # (client fixture should have it, so we need to remove it)
        from flask import current_app

        # Execute: POST request (camera_streamer will be None from mock)
        with client.application.app_context():
            current_app.config['CAMERA_STREAMER'] = None
            response = client.post('/api/camera/instant-capture')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'Camera streamer not initialized' in data['error']

    def test_instant_capture_camera_busy_error(self, client, mock_picamera2, mock_camera_streamer,
                                               monkeypatch):
        """Error when camera is busy and cannot be acquired"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: busy123\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Picamera2 constructor raises busy error
        mock_picamera2.Picamera2.side_effect = RuntimeError("Camera is busy")

        # Execute: POST request
        response = client.post('/api/camera/instant-capture')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_instant_capture_capture_failure(self, client, mock_picamera2, mock_camera_streamer,
                                            monkeypatch):
        """Error when capture fails during image acquisition"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: capture_fail\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Picamera2 capture_array raises exception
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_array.side_effect = RuntimeError("Capture failed - hardware error")

        # Execute: POST request
        response = client.post('/api/camera/instant-capture')

        # Verify: Error response
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_instant_capture_stream_restart_after_success(self, client, mock_picamera2,
                                                          mock_camera_streamer, temp_photos_dir,
                                                          monkeypatch):
        """Stream is restarted after successful capture if it was streaming before"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Camera was streaming before capture
        mock_camera_streamer.camera = MagicMock()  # Camera initialized
        mock_camera_streamer.streaming = True  # Was streaming

        # Setup: Mock camera_streamer settings
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo and controls
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: restart_test\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 10000,
            'AnalogueGain': 1.5,
            'LensPosition': 5.0,
            'ColourTemperature': 5500,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', return_value=b'EXIF'):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Stream restart was called
            assert mock_camera_streamer.release_camera.called, "release_camera should be called before capture"
            assert mock_camera_streamer.start_streaming.called, "start_streaming should be called after capture"

    def test_instant_capture_stream_restart_after_error(self, client, mock_picamera2,
                                                        mock_camera_streamer, monkeypatch):
        """Stream is restarted after capture error if it was streaming before"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Camera was streaming
        mock_camera_streamer.camera = MagicMock()
        mock_camera_streamer.streaming = True

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: error_restart\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Capture fails
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_array.side_effect = RuntimeError("Capture error")

        # Execute: POST request (will fail)
        response = client.post('/api/camera/instant-capture')

        # Verify: Stream restart was attempted even after error
        assert mock_camera_streamer.start_streaming.called, "Stream should be restarted even after error"

    # ========================================================================
    # Settings Extraction Tests
    # ========================================================================

    def test_instant_capture_settings_from_camera_streamer(self, client, mock_camera_streamer, monkeypatch):
        """Settings are extracted from camera_streamer.get_current_settings()"""
        # Setup: Configure camera_streamer with specific settings
        test_settings = {
            'sharpness': 2.5,
            'brightness': -0.3,
            'contrast': 1.2,
            'saturation': 0.9,
            'af_mode': 1,  # Auto AF
            'af_speed': 1,  # Fast
            'af_range': 2,  # Full
            'lens_position': 6.8,
            'awb_enable': False,
            'awb_mode': 3,  # Daylight
            'ae_enable': False,
            'exposure_time': 15000,
            'analogue_gain': 2.8,
            'noise_reduction_mode': 1,  # Fast
            'colour_gains_red': 2.5,
            'colour_gains_blue': 1.8,
        }
        mock_camera_streamer.get_current_settings.return_value = test_settings

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: settings_test\n")
            elif "controls.txt" in str(file):
                return StringIO("name=test\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock execute to verify settings passed
        captured_controls = None
        def mock_execute(controls, af_mode, source, filename):
            nonlocal captured_controls
            captured_controls = controls
            return (
                {'success': True, 'photo_path': f'test/{filename}'},
                200
            )

        with patch('routes.camera._execute_instant_capture', side_effect=mock_execute):
            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Settings were passed correctly
            assert captured_controls is not None
            assert captured_controls['Sharpness'] == 2.5
            assert captured_controls['Brightness'] == -0.3
            assert captured_controls['Contrast'] == 1.2
            assert captured_controls['Saturation'] == 0.9
            assert captured_controls['AfMode'] == 0  # Should be forced to 0 due to lens_position
            assert captured_controls['LensPosition'] == 6.8
            assert captured_controls['NoiseReductionMode'] == 1

            # AWB disabled, so manual settings applied
            assert captured_controls['AwbEnable'] is False
            assert captured_controls['AwbMode'] == 3
            assert 'ColourGains' in captured_controls
            assert captured_controls['ColourGains'] == (2.5, 1.8)

            # AE disabled, so manual exposure settings applied
            assert captured_controls['AeEnable'] is False
            assert captured_controls['ExposureTime'] == 15000
            assert captured_controls['AnalogueGain'] == 2.8

    def test_instant_capture_response_format(self, client, mock_picamera2, mock_camera_streamer,
                                            temp_photos_dir, monkeypatch):
        """Response contains all required fields in correct format"""
        # Setup: Inject mocks
        monkeypatch.setitem(sys.modules, 'picamera2', mock_picamera2)

        # Setup: Mock camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'af_mode': 0,
            'awb_enable': True,
            'ae_enable': True,
        }

        # Setup: Mock cpuinfo
        def patched_open(file, *args, **kwargs):
            if str(file) == "/proc/cpuinfo":
                return StringIO("Serial\t\t: format_test\n")
            elif "controls.txt" in str(file):
                return StringIO("name=FormatBox\n")
            raise FileNotFoundError(f"Mock: {file}")
        monkeypatch.setattr('builtins.open', patched_open)

        # Setup: Mock Picamera2
        mock_instance = mock_picamera2._mock_instance
        mock_instance.capture_metadata.return_value = {
            'ExposureTime': 12000,
            'AnalogueGain': 2.2,
            'LensPosition': 5.8,
            'ColourTemperature': 5400,
        }
        mock_instance.camera_properties = {'Model': 'ov64a40'}

        mock_image = MagicMock()
        with patch('PIL.Image.fromarray', return_value=mock_image), \
             patch('piexif.dump', return_value=b'EXIF'):

            # Execute: POST request
            response = client.post('/api/camera/instant-capture')

            # Verify: Response format
            assert response.status_code == 200
            data = response.get_json()

            # Required fields
            assert 'success' in data
            assert 'photo_path' in data
            assert 'settings_used' in data
            assert 'settings_source' in data
            assert 'metadata' in data
            assert 'timestamp' in data

            # Field types and values
            assert data['success'] is True
            assert isinstance(data['photo_path'], str)
            assert data['settings_source'] == 'instant capture'
            assert isinstance(data['settings_used'], dict)
            assert isinstance(data['metadata'], dict)
            assert isinstance(data['timestamp'], (int, float))

            # Metadata fields
            metadata = data['metadata']
            assert 'exposure_time' in metadata
            assert 'analogue_gain' in metadata
            assert 'lens_position' in metadata
            assert 'colour_temperature' in metadata
            assert metadata['exposure_time'] == 12000
            assert metadata['analogue_gain'] == 2.2
            assert metadata['lens_position'] == 5.8
            assert metadata['colour_temperature'] == 5400
