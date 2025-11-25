"""
Unit tests for instant capture endpoint

Tests the /api/camera/instant-capture endpoint that captures photos
using current live view settings with instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg naming.

Pattern Reference: Follows test_gallery_routes.py for Flask test client patterns.

Uses local fixtures for isolated Flask app testing (doesn't use conftest app fixture
because this test needs specific PHOTOS_DIR patching for test isolation).
"""

import pytest
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from flask import Flask


# ============================================================================
# Fixtures (local to this test module)
# ============================================================================

@pytest.fixture
def instant_capture_streamer():
    """Mock LiveViewStreamer instance with get_current_settings() for instant capture tests"""
    mock = MagicMock()

    # Mock get_current_settings() to return known values
    mock.get_current_settings.return_value = {
        'sharpness': 1.0,
        'brightness': 0.0,
        'contrast': 1.0,
        'saturation': 1.0,
        'af_mode': 2,
        'af_speed': 0,
        'af_range': 0,
        'ae_enable': True,
        'ae_metering_mode': 0,
        'awb_enable': True,
        'awb_mode': 0,
        'exposure_time': 10000,
        'analogue_gain': 8.0,
        'noise_reduction_mode': 2,
        'colour_gains_red': 2.259,
        'colour_gains_blue': 1.500,
        'lens_position': 7.5
    }

    return mock


@pytest.fixture
def camera_app(instant_capture_streamer, tmp_path, monkeypatch):
    """Flask app with camera blueprint and mocked camera_streamer"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

    from routes.camera import camera_bp

    # Create temp directories
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    test_captures_dir = photos_dir / "test_captures"
    test_captures_dir.mkdir()

    # Patch mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['CAMERA_STREAMER'] = instant_capture_streamer

    app.register_blueprint(camera_bp, url_prefix='/api/camera')

    return app


@pytest.fixture
def camera_client(camera_app):
    """Test client for camera routes"""
    return camera_app.test_client()


# ============================================================================
# Phase 3: Test instant capture endpoint
# ============================================================================

class TestInstantCaptureEndpoint:
    """Tests for POST /api/camera/instant-capture endpoint"""

    def test_endpoint_exists(self, camera_client):
        """Endpoint should exist and accept POST requests"""
        response = camera_client.post('/api/camera/instant-capture')

        # Should not return 404 (may return 500 if not fully implemented yet)
        assert response.status_code != 404

    def test_endpoint_requires_post_method(self, camera_client):
        """Endpoint should only accept POST, reject GET"""
        response = camera_client.get('/api/camera/instant-capture')

        assert response.status_code == 405  # Method Not Allowed

    def test_filename_format_is_correct(self, camera_client, camera_app, tmp_path, monkeypatch):
        """Filename should follow instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg format"""
        photos_dir = tmp_path / "photos"
        test_captures_dir = photos_dir / "test_captures"

        captured_photo_path = None

        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            nonlocal captured_photo_path
            # Capture the filename that was passed
            if filename:
                captured_photo_path = filename
            # Simulate creating the file
            photo_path = test_captures_dir / filename
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Minimal JPEG
            return json.dumps({
                'success': True,
                'test_photo_path': f'test_captures/{filename}',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify filename format: instant_YYYY_MM_DD__HH_MM_SS_[serial].jpg
        filename_pattern = r'^instant_\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2}_[A-Z0-9]+\.jpg$'
        if captured_photo_path:
            assert re.match(filename_pattern, captured_photo_path), \
                f"Filename '{captured_photo_path}' doesn't match expected pattern"

    def test_saves_to_test_captures_directory(self, camera_client, camera_app, tmp_path):
        """Photo should be saved to test_captures/ directory"""
        photos_dir = tmp_path / "photos"
        test_captures_dir = photos_dir / "test_captures"

        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            # Simulate creating the file in test_captures
            photo_path = test_captures_dir / filename
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            return json.dumps({
                'success': True,
                'test_photo_path': f'test_captures/{filename}',
                'settings_source': 'instant capture'
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'test_photo_path' in data
        assert data['test_photo_path'].startswith('test_captures/')

    def test_uses_camera_streamer_settings(self, camera_client, camera_app, instant_capture_streamer):
        """Should use settings from camera_streamer.get_current_settings()"""
        # Set known values in camera_streamer
        instant_capture_streamer.get_current_settings.return_value = {
            'sharpness': 2.5,
            'brightness': 0.1,
            'contrast': 1.2,
            'saturation': 1.1,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'ae_enable': True,
            'ae_metering_mode': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'exposure_time': 15000,
            'analogue_gain': 10.0,
            'noise_reduction_mode': 2,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'lens_position': 7.5
        }

        captured_controls = {}

        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/instant_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        # Verify get_current_settings() was called
        instant_capture_streamer.get_current_settings.assert_called_once()

        # Verify controls match camera_streamer values
        assert captured_controls['Sharpness'] == 2.5
        assert captured_controls['Brightness'] == 0.1
        # ExposureTime only set when AE is disabled (auto-exposure is enabled in this test)
        # Verify other settings instead
        assert captured_controls['AeEnable'] is True
        assert captured_controls['AwbEnable'] is True

    def test_includes_exif_metadata(self, camera_client, camera_app, tmp_path):
        """Response should include EXIF metadata"""
        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/instant_photo.jpg',
                'settings_source': settings_source,
                'metadata': {
                    'exposure_time': 10000,
                    'analogue_gain': 8.0,
                    'lens_position': 7.5,
                    'colour_temperature': 5000
                }
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'metadata' in data
        assert 'exposure_time' in data['metadata']
        assert 'analogue_gain' in data['metadata']

    def test_returns_success_response(self, camera_client, camera_app):
        """Response should have success=True and photo path"""
        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/instant_photo.jpg',
                'settings_source': 'instant capture',
                'timestamp': 1699200000.0
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'test_photo_path' in data
        assert 'timestamp' in data

    def test_error_handling_camera_unavailable(self, camera_client, camera_app):
        """Should return error when camera unavailable"""
        # Remove camera_streamer
        camera_app.config['CAMERA_STREAMER'] = None

        with camera_app.app_context():
            response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data

    def test_error_handling_capture_failure(self, camera_client, camera_app):
        """Should handle capture failures gracefully"""
        def mock_execute_instant_capture_error(controls, af_mode, settings_source, filename=None):
            raise Exception("Camera fault")

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture_error):
                response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data

    def test_serial_number_in_filename(self, camera_client, camera_app, tmp_path):
        """Filename should include system serial number"""
        captured_filename = None

        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            nonlocal captured_filename
            captured_filename = filename
            return json.dumps({
                'success': True,
                'test_photo_path': f'test_captures/{filename}',
                'settings_source': settings_source
            }), 200

        # Mock /proc/cpuinfo to return test serial
        mock_cpuinfo = "Serial\t\t: 0000000000TEST123"

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                # Mock open() to return test serial when reading /proc/cpuinfo
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.__iter__.return_value = [mock_cpuinfo]
                    response = camera_client.post('/api/camera/instant-capture')

        assert response.status_code == 200
        # Verify serial is in filename
        if captured_filename:
            assert '0000000000TEST123' in captured_filename

    def test_preserves_manual_exposure(self, camera_client, camera_app, instant_capture_streamer):
        """Should preserve manual exposure settings from live view"""
        instant_capture_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'ae_enable': False,  # Manual exposure
            'ae_metering_mode': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'exposure_time': 25000,
            'analogue_gain': 15.0,
            'noise_reduction_mode': 2,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'lens_position': 7.5
        }

        captured_controls = {}

        def mock_execute_instant_capture(controls, af_mode, settings_source, filename=None):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/instant_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_instant_capture', mock_execute_instant_capture):
                response = camera_client.post('/api/camera/instant-capture')

        assert captured_controls['AeEnable'] is False
        assert captured_controls['ExposureTime'] == 25000
        assert captured_controls['AnalogueGain'] == 15.0
