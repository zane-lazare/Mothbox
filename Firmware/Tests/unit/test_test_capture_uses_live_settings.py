"""
Unit tests for test_capture_liveview endpoint using camera_streamer.get_current_settings()

Tests that test_capture_liveview() reads settings from camera_streamer instance
instead of from liveview_settings.txt file, ensuring test photos reflect actual
live view slider values.

Pattern Reference: Follows test_gallery_routes.py for Flask test client patterns.

TDD Phase: Phase 2 - Test FIRST, then implement
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from flask import Flask


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_camera_streamer():
    """Mock LiveViewStreamer instance with get_current_settings()"""
    mock = MagicMock()

    # Mock get_current_settings() to return known values
    mock.get_current_settings.return_value = {
        'sharpness': 2.5,
        'brightness': 0.1,
        'contrast': 1.2,
        'saturation': 1.1,
        'af_mode': 2,  # Continuous
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

    return mock


@pytest.fixture
def camera_app(mock_camera_streamer, tmp_path, monkeypatch):
    """Flask app with camera blueprint and mocked camera_streamer"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

    from routes.camera import camera_bp

    # Create temp directories
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    test_captures_dir = photos_dir / "test_captures"
    test_captures_dir.mkdir()

    liveview_settings_file = tmp_path / "liveview_settings.txt"
    liveview_settings_file.write_text("")  # Empty file

    # Patch mothbox_paths (since routes.camera imports from there)
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)
    monkeypatch.setattr(mothbox_paths, 'LIVEVIEW_SETTINGS_FILE', liveview_settings_file)

    # Create Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['CAMERA_STREAMER'] = mock_camera_streamer

    app.register_blueprint(camera_bp, url_prefix='/api/camera')

    return app


@pytest.fixture
def camera_client(camera_app):
    """Test client for camera routes"""
    return camera_app.test_client()


# ============================================================================
# Phase 2: Test that test_capture_liveview uses camera_streamer.get_current_settings()
# ============================================================================

class TestCaptureUsesLiveSettings:
    """Tests for test_capture_liveview endpoint using camera_streamer"""

    def test_endpoint_calls_get_current_settings(self, camera_client, camera_app, mock_camera_streamer, monkeypatch):
        """test_capture_liveview should call camera_streamer.get_current_settings()"""
        # Mock _execute_test_capture to avoid actual photo capture
        mock_execute = MagicMock(return_value=(
            json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': 'live view'
            }),
            200
        ))

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                response = camera_client.post('/api/camera/test-capture-liveview')

        # Verify get_current_settings() was called
        mock_camera_streamer.get_current_settings.assert_called_once()

    def test_endpoint_uses_settings_from_camera_streamer(self, camera_client, camera_app, mock_camera_streamer, monkeypatch):
        """test_capture_liveview should use settings from camera_streamer, not file"""
        # Set known values in camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 3.0,  # Different from file
            'brightness': 0.2,
            'contrast': 1.5,
            'saturation': 1.3,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'ae_enable': False,  # Manual exposure
            'ae_metering_mode': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'exposure_time': 20000,
            'analogue_gain': 12.0,
            'noise_reduction_mode': 2,
            'colour_gains_red': 2.5,
            'colour_gains_blue': 1.8,
            'lens_position': 8.0
        }

        # Track what controls were passed to _execute_test_capture
        captured_controls = {}

        def mock_execute(controls, af_mode, settings_source):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                response = camera_client.post('/api/camera/test-capture-liveview')

        # Verify controls match camera_streamer values
        assert captured_controls['Sharpness'] == 3.0
        assert captured_controls['Brightness'] == 0.2
        assert captured_controls['Contrast'] == 1.5
        assert captured_controls['Saturation'] == 1.3
        assert captured_controls['ExposureTime'] == 20000  # Manual exposure
        assert captured_controls['AnalogueGain'] == 12.0

    def test_endpoint_fallback_to_file_when_no_camera_streamer(self, camera_app, tmp_path, monkeypatch):
        """Should fall back to liveview_settings.txt when camera_streamer unavailable"""
        # Remove camera_streamer from app config
        camera_app.config['CAMERA_STREAMER'] = None

        # Write settings to file
        liveview_settings_file = tmp_path / "liveview_settings.txt"
        liveview_settings_file.write_text("""
sharpness=1.5
brightness=0.0
exposure_time=10000
analogue_gain=8.0
""")

        # Patch LIVEVIEW_SETTINGS_FILE in mothbox_paths (it's imported inside the function)
        import mothbox_paths
        monkeypatch.setattr(mothbox_paths, 'LIVEVIEW_SETTINGS_FILE', liveview_settings_file)

        captured_controls = {}

        def mock_execute(controls, af_mode, settings_source):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                # get_control_values is imported locally, so patch it at mothbox_paths
                with patch('mothbox_paths.get_control_values', return_value={
                    'sharpness': '1.5',
                    'brightness': '0.0',
                    'exposure_time': '10000',
                    'analogue_gain': '8.0'
                }):
                    client = camera_app.test_client()
                    response = client.post('/api/camera/test-capture-liveview')

        # Should have used file values
        assert response.status_code == 200
        # Verify file was read as fallback
        assert captured_controls.get('Sharpness') == 1.5

    def test_endpoint_preserves_manual_exposure_from_live_view(self, camera_client, camera_app, mock_camera_streamer):
        """Should preserve manual exposure settings from live view"""
        # Set manual exposure in camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
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

        def mock_execute(controls, af_mode, settings_source):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                response = camera_client.post('/api/camera/test-capture-liveview')

        # Verify manual exposure was preserved
        assert captured_controls['AeEnable'] is False
        assert captured_controls['ExposureTime'] == 25000
        assert captured_controls['AnalogueGain'] == 15.0

    def test_endpoint_preserves_manual_focus_from_live_view(self, camera_client, camera_app, mock_camera_streamer):
        """Should preserve manual focus settings from live view"""
        # Set manual focus in camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'af_mode': 0,  # Manual focus
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
            'lens_position': 5.5  # Manual lens position
        }

        captured_controls = {}

        def mock_execute(controls, af_mode, settings_source):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                response = camera_client.post('/api/camera/test-capture-liveview')

        # Verify manual focus was preserved
        assert captured_controls['AfMode'] == 0
        assert captured_controls['LensPosition'] == 5.5

    def test_endpoint_preserves_manual_white_balance_from_live_view(self, camera_client, camera_app, mock_camera_streamer):
        """Should preserve manual white balance settings from live view"""
        # Set manual white balance in camera_streamer
        mock_camera_streamer.get_current_settings.return_value = {
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'ae_enable': True,
            'ae_metering_mode': 0,
            'awb_enable': False,  # Manual white balance
            'awb_mode': 1,
            'exposure_time': 10000,
            'analogue_gain': 8.0,
            'noise_reduction_mode': 2,
            'colour_gains_red': 1.8,  # Custom gains
            'colour_gains_blue': 2.2,
            'lens_position': 7.5
        }

        captured_controls = {}

        def mock_execute(controls, af_mode, settings_source):
            captured_controls.update(controls)
            return json.dumps({
                'success': True,
                'test_photo_path': 'test_captures/test_photo.jpg',
                'settings_source': settings_source
            }), 200

        with camera_app.app_context():
            with patch('routes.camera._execute_test_capture', mock_execute):
                response = camera_client.post('/api/camera/test-capture-liveview')

        # Verify manual white balance was preserved
        assert captured_controls['AwbEnable'] is False
        assert captured_controls['AwbMode'] == 1
        assert captured_controls['ColourGains'] == (1.8, 2.2)

    def test_endpoint_error_handling_when_get_current_settings_fails(self, camera_client, camera_app, mock_camera_streamer):
        """Should handle errors gracefully if get_current_settings() fails"""
        # Make get_current_settings() raise an exception
        mock_camera_streamer.get_current_settings.side_effect = Exception("Camera fault")

        with camera_app.app_context():
            response = camera_client.post('/api/camera/test-capture-liveview')

        # Should return error response
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
