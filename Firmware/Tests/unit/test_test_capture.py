"""
Unit tests for test capture endpoint (Phase 4.5)

Tests the /api/camera/test-capture endpoint that captures full-resolution
test photos using preview settings without affecting production config.

RUN ON RASPBERRY PI ONLY - tests Flask routes
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestTestCaptureEndpoint:
    """Test test capture endpoint functionality"""

    def test_test_capture_endpoint_exists(self):
        """Test that test capture endpoint is registered"""
        from routes.camera import camera_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(camera_bp, url_prefix='/api/camera')

        with app.test_client() as client:
            response = client.post('/api/camera/test-capture')
            # Should not return 404
            assert response.status_code != 404
            print(f"\n✓ Test capture endpoint exists")

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.PHOTOS_DIR')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_success(self, mock_settings_file, mock_photos_dir, mock_picamera2, tmp_path):
        """Test successful test capture"""
        from routes.camera import camera_bp
        from flask import Flask

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

                app = Flask(__name__)
                app.register_blueprint(camera_bp, url_prefix='/api/camera')

                with app.test_client() as client:
                    response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'test_photo_path' in data
        assert data['test_photo_path'].startswith('test_captures/')
        assert 'settings_used' in data
        assert 'metadata' in data
        assert 'timestamp' in data
        print(f"\n✓ Test capture successful: {data['test_photo_path']}")

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_applies_preview_settings(self, mock_settings_file, mock_picamera2):
        """Test that preview settings are applied to test capture"""
        from routes.camera import camera_bp
        from flask import Flask

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
                    app = Flask(__name__)
                    app.register_blueprint(camera_bp, url_prefix='/api/camera')

                    with app.test_client() as client:
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
        print(f"\n✓ Preview settings applied: Sharpness={settings_used['Sharpness']}, AfMode={settings_used['AfMode']}")

    @patch('routes.camera.Picamera2')
    def test_test_capture_releases_camera_if_streaming(self, mock_picamera2):
        """Test that camera is released if stream is active"""
        from routes.camera import camera_bp
        from flask import Flask

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

                        app = Flask(__name__)
                        app.register_blueprint(camera_bp, url_prefix='/api/camera')

                        with app.test_client() as client:
                            response = client.post('/api/camera/test-capture')

        # Verify camera was released and restarted
        assert mock_streamer.release_camera.called
        assert mock_streamer.start_streaming.called
        print(f"\n✓ Camera released before capture and restarted after")

    def test_test_capture_without_picamera2(self):
        """Test graceful handling when picamera2 is not available"""
        from routes.camera import camera_bp
        from flask import Flask

        with patch('routes.camera.Picamera2', side_effect=ImportError):
            app = Flask(__name__)
            app.register_blueprint(camera_bp, url_prefix='/api/camera')

            with app.test_client() as client:
                response = client.post('/api/camera/test-capture')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'picamera2 not available' in data['error']
        print(f"\n✓ Graceful handling when picamera2 unavailable")

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_returns_metadata(self, mock_settings_file, mock_picamera2):
        """Test that capture metadata is returned"""
        from routes.camera import camera_bp
        from flask import Flask

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
                    app = Flask(__name__)
                    app.register_blueprint(camera_bp, url_prefix='/api/camera')

                    with app.test_client() as client:
                        response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['metadata']['exposure_time'] == 12345
        assert data['metadata']['analogue_gain'] == 3.7
        assert data['metadata']['lens_position'] == 6.2
        assert data['metadata']['colour_temperature'] == 4800
        print(f"\n✓ Metadata returned: exposure={data['metadata']['exposure_time']}µs")

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_defaults_when_no_settings_file(self, mock_settings_file, mock_picamera2):
        """Test that defaults are used when webui_settings.txt doesn't exist"""
        from routes.camera import camera_bp
        from flask import Flask

        mock_settings_file.exists.return_value = False

        # Mock picamera2
        mock_camera = MagicMock()
        mock_picamera2.return_value = mock_camera
        mock_camera.capture_metadata.return_value = {}

        with patch('flask.current_app') as mock_app:
            mock_app.config.get.return_value = None

            with patch('routes.camera.PHOTOS_DIR'):
                app = Flask(__name__)
                app.register_blueprint(camera_bp, url_prefix='/api/camera')

                with app.test_client() as client:
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
        print(f"\n✓ Defaults used: Sharpness={settings['Sharpness']}, AfMode={settings['AfMode']}")

    @patch('routes.camera.Picamera2')
    @patch('routes.camera.WEBUI_SETTINGS_FILE')
    def test_test_capture_handles_awb_mode_correctly(self, mock_settings_file, mock_picamera2):
        """Test that AwbMode is only set when AWB is disabled"""
        from routes.camera import camera_bp
        from flask import Flask

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
                    app = Flask(__name__)
                    app.register_blueprint(camera_bp, url_prefix='/api/camera')

                    with app.test_client() as client:
                        response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'AwbMode' not in data['settings_used']
        print(f"\n✓ AWB enabled: AwbMode not set (correct)")

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
                    app = Flask(__name__)
                    app.register_blueprint(camera_bp, url_prefix='/api/camera')

                    with app.test_client() as client:
                        response = client.post('/api/camera/test-capture')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['settings_used']['AwbMode'] == 5
        print(f"\n✓ AWB disabled: AwbMode={data['settings_used']['AwbMode']} (correct)")
