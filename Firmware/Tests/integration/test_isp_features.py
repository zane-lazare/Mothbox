"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

Integration tests for ISP features

Tests ISP integration with camera_stream and settings endpoints.
These tests verify that ISP settings flow correctly through the system.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

# Mock Flask/SocketIO before importing camera_stream
sys.modules['flask_socketio'] = MagicMock()

import camera_stream


class TestISPIntegration(unittest.TestCase):
    """Integration tests for ISP features"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock socketio
        self.mock_socketio = Mock()

    @patch('camera_stream.PICAMERA_AVAILABLE', False)
    def test_camera_streamer_loads_isp_settings(self):
        """Test that CameraStreamer loads ISP settings from config"""
        streamer = camera_stream.CameraStreamer(self.mock_socketio)

        # Default ISP settings should be loaded
        self.assertTrue(hasattr(streamer, 'lens_shading_enable'))
        self.assertTrue(hasattr(streamer, 'defect_correction_enable'))

        # Default values should be True
        self.assertTrue(streamer.lens_shading_enable)
        self.assertTrue(streamer.defect_correction_enable)

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

        streamer = camera_stream.CameraStreamer(self.mock_socketio)

        # Custom ISP settings should be loaded
        self.assertFalse(streamer.lens_shading_enable)
        self.assertTrue(streamer.defect_correction_enable)

    def test_isp_settings_in_allowed_camera_settings(self):
        """Test that ISP settings are in allowed camera settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        self.assertIn('LensShadingEnable', ALLOWED_CAMERA_SETTINGS)
        self.assertIn('DefectCorrectionEnable', ALLOWED_CAMERA_SETTINGS)

    def test_isp_validators_accept_true(self):
        """Test that ISP validators accept 'true'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        self.assertTrue(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('true'))
        self.assertTrue(ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('true'))

    def test_isp_validators_accept_false(self):
        """Test that ISP validators accept 'false'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        self.assertTrue(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('false'))
        self.assertTrue(ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('false'))

    def test_isp_validators_case_insensitive(self):
        """Test that ISP validators are case-insensitive"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        self.assertTrue(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('True'))
        self.assertTrue(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('FALSE'))

    def test_isp_validators_reject_invalid(self):
        """Test that ISP validators reject invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # These should return False for invalid values
        self.assertFalse(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('invalid'))
        self.assertFalse(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('1'))
        self.assertFalse(ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('yes'))

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

        streamer = camera_stream.CameraStreamer(self.mock_socketio)

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

        streamer = camera_stream.CameraStreamer(self.mock_socketio)
        streamer.lens_shading_enable = True
        streamer.defect_correction_enable = False

        # Initialize camera
        result = streamer.initialize_camera()

        # ISP controls should have been applied
        mock_apply_isp.assert_called_once()

        # Check arguments
        call_args = mock_apply_isp.call_args
        self.assertEqual(call_args[0][0], mock_camera)  # First arg is camera
        self.assertEqual(call_args[1]['lens_shading'], True)
        self.assertEqual(call_args[1]['defect_correction'], False)


class TestTuningFileStructure(unittest.TestCase):
    """Test tuning file structure and validity"""

    def setUp(self):
        """Set up test fixtures"""
        self.tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'

    def test_default_tuning_has_dpc_algorithm(self):
        """Test that default tuning includes DPC (defect pixel correction)"""
        import json

        default_file = self.tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for DPC algorithm
        algorithms = data.get('algorithms', [])
        dpc_found = False

        for algo in algorithms:
            if 'rpi.dpc' in algo:
                dpc_found = True
                break

        self.assertTrue(dpc_found, "Tuning file should include rpi.dpc algorithm")

    def test_default_tuning_has_alsc_algorithm(self):
        """Test that default tuning includes ALSC (lens shading correction)"""
        import json

        default_file = self.tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for ALSC algorithm
        algorithms = data.get('algorithms', [])
        alsc_found = False

        for algo in algorithms:
            if 'rpi.alsc' in algo:
                alsc_found = True
                break

        self.assertTrue(alsc_found, "Tuning file should include rpi.alsc algorithm")


if __name__ == '__main__':
    unittest.main()
