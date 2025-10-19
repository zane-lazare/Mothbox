"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

Integration tests for ISP features

Tests ISP integration with camera_stream and settings endpoints.
These tests verify that ISP settings flow correctly through the system.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

# Mock Flask/SocketIO before importing camera_stream
sys.modules['flask_socketio'] = MagicMock()

import camera_stream


@pytest.mark.stream
@pytest.mark.hardware
class TestISPIntegration:
    """Integration tests for ISP features"""

    @patch('camera_stream.PICAMERA_AVAILABLE', False)
    def test_camera_streamer_loads_isp_settings(self, camera_streamer):
        """Test that CameraStreamer loads ISP settings from config"""
        streamer = camera_streamer

        # Default ISP settings should be loaded
        assert hasattr(streamer, 'lens_shading_enable')
        assert hasattr(streamer, 'defect_correction_enable')

        # Default values should be True
        assert streamer.lens_shading_enable
        assert streamer.defect_correction_enable

    @patch('camera_stream.PICAMERA_AVAILABLE', False)
    @patch('camera_stream.WEBUI_SETTINGS_FILE')
    @patch('camera_stream.get_control_values')
    def test_camera_streamer_loads_custom_isp_settings(self, mock_get_values, mock_settings_file):
        """Test that CameraStreamer loads custom ISP settings"""
        mock_settings_file.exists.return_value = True
        mock_get_values.return_value = {
            'lens_shading_enable': 'false',
            'defect_correction_enable': 'true',
            'stream_width': '1024',
            'stream_height': '768',
        }

        # Create mock socketio
        class MockSocketIO:
            def emit(self, event, data, **kwargs):
                pass

        streamer = camera_stream.CameraStreamer(MockSocketIO())

        # Custom ISP settings should be loaded
        assert not streamer.lens_shading_enable
        assert streamer.defect_correction_enable

    def test_isp_settings_in_allowed_camera_settings(self):
        """Test that ISP settings are in allowed camera settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert 'LensShadingEnable' in ALLOWED_CAMERA_SETTINGS
        assert 'DefectCorrectionEnable' in ALLOWED_CAMERA_SETTINGS

    def test_isp_validators_accept_true(self):
        """Test that ISP validators accept 'true'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('true')
        assert ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('true')

    def test_isp_validators_accept_false(self):
        """Test that ISP validators accept 'false'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('false')
        assert ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('false')

    def test_isp_validators_case_insensitive(self):
        """Test that ISP validators are case-insensitive"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('True')
        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('FALSE')

    def test_isp_validators_reject_invalid(self):
        """Test that ISP validators reject invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # These should return False for invalid values
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('invalid')
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('1')
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('yes')

    @patch('camera_stream.ISP_TUNING_AVAILABLE', True)
    @patch('camera_stream.PICAMERA_AVAILABLE', True)
    @patch('camera_stream.Picamera2')
    @patch('camera_stream.get_tuning_path')
    def test_tuning_file_loaded_on_camera_init(self, mock_get_tuning, mock_picam2, *args):
        """Test that tuning file is loaded during camera initialization"""
        # Setup mocks
        mock_tuning_path = Path('/fake/tuning/path.json')
        mock_get_tuning.return_value = mock_tuning_path

        mock_camera = Mock()
        mock_camera.camera_properties = {'PixelArraySize': (4056, 3040)}
        mock_picam2.return_value = mock_camera
        mock_picam2.load_tuning_file.return_value = {'version': 2.0}

        # Create mock socketio
        class MockSocketIO:
            def emit(self, event, data, **kwargs):
                pass

        streamer = camera_stream.CameraStreamer(MockSocketIO())

        # Initialize camera
        result = streamer.initialize_camera()

        # Should have tried to load tuning file
        mock_get_tuning.assert_called()
        mock_picam2.load_tuning_file.assert_called_with(str(mock_tuning_path))

    @patch('camera_stream.ISP_TUNING_AVAILABLE', True)
    @patch('camera_stream.PICAMERA_AVAILABLE', True)
    @patch('camera_stream.Picamera2')
    @patch('camera_stream.apply_isp_controls')
    def test_isp_controls_applied_after_camera_start(self, mock_apply_isp, mock_picam2, *args):
        """Test that ISP controls are applied after camera starts"""
        # Setup mocks
        mock_camera = Mock()
        mock_camera.camera_properties = {'PixelArraySize': (4056, 3040)}
        mock_picam2.return_value = mock_camera

        # Create mock socketio
        class MockSocketIO:
            def emit(self, event, data, **kwargs):
                pass

        streamer = camera_stream.CameraStreamer(MockSocketIO())
        streamer.lens_shading_enable = True
        streamer.defect_correction_enable = False

        # Initialize camera
        result = streamer.initialize_camera()

        # ISP controls should have been applied
        mock_apply_isp.assert_called_once()

        # Check arguments
        call_args = mock_apply_isp.call_args
        assert call_args[0][0] == mock_camera  # First arg is camera
        assert call_args[1]['lens_shading'] == True
        assert call_args[1]['defect_correction'] == False


@pytest.mark.stream
@pytest.mark.hardware
class TestTuningFileStructure:
    """Test tuning file structure and validity"""

    def test_default_tuning_has_dpc_algorithm(self):
        """Test that default tuning includes DPC (defect pixel correction)"""
        import json

        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        default_file = tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for DPC algorithm
        algorithms = data.get('algorithms', [])
        dpc_found = False

        for algo in algorithms:
            if 'rpi.dpc' in algo:
                dpc_found = True
                break

        assert dpc_found, "Tuning file should include rpi.dpc algorithm"

    def test_default_tuning_has_alsc_algorithm(self):
        """Test that default tuning includes ALSC (lens shading correction)"""
        import json

        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        default_file = tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for ALSC algorithm
        algorithms = data.get('algorithms', [])
        alsc_found = False

        for algo in algorithms:
            if 'rpi.alsc' in algo:
                alsc_found = True
                break

        assert alsc_found, "Tuning file should include rpi.alsc algorithm"
