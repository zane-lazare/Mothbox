"""
Unit tests for test capture endpoint (Phase 4.5)

Tests the /api/camera/test-capture endpoint that captures full-resolution
test photos using preview settings without affecting production config.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json


class TestTestCaptureEndpoint:
    """Test test capture endpoint functionality"""

    def test_test_capture_endpoint_exists(self, client):
        """Test that test capture endpoint is registered"""
        response = client.post('/api/camera/test-capture')
        # Should not return 404
        assert response.status_code != 404

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.PHOTOS_DIR')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_success(self, mock_settings_file, mock_photos_dir, mock_picamera2, client, tmp_path):
        """Test successful test capture"""
        # Mock file system
        mock_settings_file.exists.return_value = True
        mock_photos_dir.return_value = tmp_path
        mock_photos_dir.__truediv__ = lambda self, other: tmp_path / other

        # Mock get_control_values to return preview settings
        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {
                'sharpness': '2.0',
                'brightness': '0.1',
                'contrast': '1.2',
                'saturation': '1.1',
                'af_mode': '2',
                'af_speed': '0',
                'af_range': '1',
                'awb_enable': 'true',
                'awb_mode': '0'
            }

            # Mock picamera2
            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {
                'ExposureTime': 7000,
                'AnalogueGain': 2.1,
                'LensPosition': 7.84,
                'ColourTemperature': 5200
            }

            # Mock camera_streamer (no active stream)
            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'test_photo_path' in data
        assert data['test_photo_path'].startswith('test_captures/')
        assert 'settings_used' in data
        assert 'metadata' in data
        assert 'timestamp' in data

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_applies_preview_settings(self, mock_settings_file, mock_picamera2, client):
        """Test that preview settings are applied to test capture"""
        mock_settings_file.exists.return_value = True

        # Mock get_control_values with specific settings
        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {
                'sharpness': '2.5',
                'brightness': '-0.2',
                'contrast': '1.5',
                'saturation': '0.8',
                'af_mode': '0',  # Manual
                'af_speed': '1',  # Fast
                'af_range': '2',  # Full
                'awb_enable': 'false',
                'awb_mode': '5'  # Daylight
            }

            # Mock picamera2
            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {
                'ExposureTime': 5000,
                'AnalogueGain': 1.5,
                'LensPosition': 3.2,
                'ColourTemperature': 5600
            }

            # Mock camera_streamer
            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                with patch('routes.camera.PHOTOS_DIR'):
                    response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify preview settings were applied
        settings_used = data['settings_used']
        assert settings_used['Sharpness'] == 2.5
        assert settings_used['Brightness'] == -0.2
        assert settings_used['Contrast'] == 1.5
        assert settings_used['Saturation'] == 0.8
        assert settings_used['AfMode'] == 0
        assert settings_used['AfSpeed'] == 1
        assert settings_used['AfRange'] == 2
        assert settings_used['AwbEnable'] is False
        assert settings_used['AwbMode'] == 5

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.PHOTOS_DIR')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_creates_directory(self, mock_settings_file, mock_photos_dir, mock_picamera2, client, tmp_path):
        """Test that test_captures directory is created"""
        mock_settings_file.exists.return_value = True
        test_captures_dir = tmp_path / "test_captures"

        # Mock PHOTOS_DIR to use tmp_path
        mock_photos_dir.__truediv__ = lambda self, other: tmp_path / other

        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {}

            # Mock picamera2
            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {}

            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                # Simulate directory creation
                def mock_mkdir(*args, **kwargs):
                    test_captures_dir.mkdir(parents=True, exist_ok=True)

                with patch.object(Path, 'mkdir', side_effect=mock_mkdir):
                    response = client.post('/api/camera/test-capture')

        # Verify directory would be created (in mock)
        assert response.status_code == 200

    @patch('routes.camera.Picamera2')
    def test_test_capture_releases_camera_if_streaming(self, mock_picamera2, client):
        """Test that camera is released if stream is active"""
        # Mock active camera stream
        mock_streamer = Mock()
        mock_streamer.streaming = True
        mock_streamer.release_camera = Mock()
        mock_streamer.start_streaming = Mock()

        with patch('flask.current_app') as mock_app:
            mock_app.config.get.return_value = mock_streamer

            with patch('routes.camera.WEBUI_SETTINGS_FILE') as mock_settings:
                mock_settings.exists.return_value = False

                with patch('routes.camera.PHOTOS_DIR'):
                    with patch('routes.camera.get_control_values'):
                        # Mock picamera2
                        mock_camera = MagicMock()
                        mock_picamera2.return_value = mock_camera
                        mock_camera.capture_metadata.return_value = {}

                        response = client.post('/api/camera/test-capture')

        # Verify camera was released and restarted
        assert mock_streamer.release_camera.called
        assert mock_streamer.start_streaming.called

    def test_test_capture_without_picamera2(self, client):
        """Test graceful handling when picamera2 is not available"""
        with patch('routes.camera.Picamera2', side_effect=ImportError):
            response = client.post('/api/camera/test-capture')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'picamera2 not available' in data['error']

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_returns_metadata(self, mock_settings_file, mock_picamera2, client):
        """Test that capture metadata is returned"""
        mock_settings_file.exists.return_value = True

        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {}

            # Mock picamera2 with specific metadata
            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {
                'ExposureTime': 12345,
                'AnalogueGain': 3.7,
                'LensPosition': 6.2,
                'ColourTemperature': 4800
            }

            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                with patch('routes.camera.PHOTOS_DIR'):
                    response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['metadata']['exposure_time'] == 12345
        assert data['metadata']['analogue_gain'] == 3.7
        assert data['metadata']['lens_position'] == 6.2
        assert data['metadata']['colour_temperature'] == 4800

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_defaults_when_no_settings_file(self, mock_settings_file, mock_picamera2, client):
        """Test that defaults are used when webui_settings.txt doesn't exist"""
        mock_settings_file.exists.return_value = False

        # Mock picamera2
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.capture_metadata.return_value = {}

        with patch('flask.current_app') as mock_app:
            mock_app.config.get.return_value = None

            with patch('routes.camera.PHOTOS_DIR'):
                response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify default values were used
        settings = data['settings_used']
        assert settings['Sharpness'] == 1.0
        assert settings['Brightness'] == 0.0
        assert settings['Contrast'] == 1.0
        assert settings['Saturation'] == 1.0
        assert settings['AfMode'] == 2  # Continuous
        assert settings['AwbEnable'] is True

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_handles_awb_mode_correctly(self, mock_settings_file, mock_picamera2, client):
        """Test that AwbMode is only set when AWB is disabled"""
        mock_settings_file.exists.return_value = True

        # Test with AWB enabled - AwbMode should NOT be set
        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {
                'awb_enable': 'true',
                'awb_mode': '5'
            }

            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {}

            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                with patch('routes.camera.PHOTOS_DIR'):
                    response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'AwbMode' not in data['settings_used']

        # Test with AWB disabled - AwbMode SHOULD be set
        with patch('routes.camera.get_control_values') as mock_get_control:
            mock_get_control.return_value = {
                'awb_enable': 'false',
                'awb_mode': '5'
            }

            mock_camera = MagicMock()
            mock_picamera2.return_value = mock_camera
            mock_camera.capture_metadata.return_value = {}

            with patch('flask.current_app') as mock_app:
                mock_app.config.get.return_value = None

                with patch('routes.camera.PHOTOS_DIR'):
                    response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['settings_used']['AwbMode'] == 5


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
