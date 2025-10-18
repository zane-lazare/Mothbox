"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

Unit tests for ISP tuning loader module

Tests:
- Tuning file loading
- Camera model detection
- Tuning path resolution
- ISP control application
"""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add webui/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

import tuning_loader


class TestTuningLoader(unittest.TestCase):
    """Test suite for tuning_loader module"""

    def setUp(self):
        """Set up test fixtures"""
        self.tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'

    def test_tuning_dir_exists(self):
        """Test that tuning directory exists"""
        self.assertTrue(self.tuning_dir.exists(), f"Tuning directory should exist at {self.tuning_dir}")

    def test_default_tuning_file_exists(self):
        """Test that default.json exists"""
        default_file = self.tuning_dir / 'default.json'
        self.assertTrue(default_file.exists(), "default.json should exist in tuning directory")

    def test_default_tuning_file_valid_json(self):
        """Test that default.json is valid JSON"""
        default_file = self.tuning_dir / 'default.json'
        with open(default_file) as f:
            try:
                data = json.load(f)
                self.assertIsInstance(data, dict, "Tuning file should be a JSON object")
            except json.JSONDecodeError as e:
                self.fail(f"default.json is not valid JSON: {e}")

    def test_default_tuning_file_structure(self):
        """Test that default.json has required structure"""
        default_file = self.tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for required fields
        self.assertIn('version', data, "Tuning file should have 'version' field")
        self.assertIn('algorithms', data, "Tuning file should have 'algorithms' field")
        self.assertIsInstance(data['algorithms'], list, "'algorithms' should be a list")

    def test_load_tuning_file_default(self):
        """Test loading default tuning file"""
        tuning = tuning_loader.load_tuning_file('unknown_camera')
        self.assertIsNotNone(tuning, "Should load default tuning for unknown camera")
        self.assertIn('version', tuning, "Loaded tuning should have version")

    def test_load_tuning_file_none_camera(self):
        """Test loading tuning with None camera (auto-detect)"""
        # Mock the camera detection to avoid requiring hardware
        with patch('tuning_loader.get_camera_model', return_value='unknown'):
            tuning = tuning_loader.load_tuning_file(None)
            self.assertIsNotNone(tuning, "Should load tuning with auto-detect")

    def test_get_tuning_path_default(self):
        """Test getting tuning path for unknown camera"""
        path = tuning_loader.get_tuning_path('unknown_camera')
        self.assertIsNotNone(path, "Should return default tuning path")
        self.assertTrue(path.exists(), "Tuning path should exist")
        self.assertEqual(path.name, 'default.json', "Should return default.json for unknown camera")

    def test_get_tuning_path_none_camera(self):
        """Test getting tuning path with None camera (auto-detect)"""
        with patch('tuning_loader.get_camera_model', return_value='unknown'):
            path = tuning_loader.get_tuning_path(None)
            self.assertIsNotNone(path, "Should return path with auto-detect")

    @patch('tuning_loader.Picamera2')
    def test_get_camera_model_success(self, mock_picam):
        """Test successful camera model detection"""
        mock_picam.global_camera_info.return_value = [
            {'Model': 'imx708'}
        ]

        model = tuning_loader.get_camera_model()
        self.assertEqual(model, 'imx708', "Should detect camera model")

    @patch('tuning_loader.Picamera2')
    def test_get_camera_model_failure(self, mock_picam):
        """Test camera model detection failure"""
        mock_picam.global_camera_info.side_effect = Exception("No camera")

        model = tuning_loader.get_camera_model()
        self.assertEqual(model, 'unknown', "Should return 'unknown' on failure")

    def test_apply_isp_controls_lens_shading(self):
        """Test applying lens shading control"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=False)

        self.assertTrue(result, "Should return True on success")
        mock_camera.set_controls.assert_called_once()

        # Check that correct controls were set
        controls = mock_camera.set_controls.call_args[0][0]
        self.assertIn('LensShadingMapMode', controls)
        self.assertEqual(controls['LensShadingMapMode'], 1, "Lens shading should be enabled")

    def test_apply_isp_controls_defect_correction(self):
        """Test applying defect correction control"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=False, defect_correction=True)

        self.assertTrue(result, "Should return True on success")

        # Check that correct controls were set
        controls = mock_camera.set_controls.call_args[0][0]
        self.assertIn('HotPixelMode', controls)
        self.assertEqual(controls['HotPixelMode'], 1, "Defect correction should be enabled (Fast mode)")

    def test_apply_isp_controls_both_disabled(self):
        """Test applying ISP controls with both features disabled"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=False, defect_correction=False)

        self.assertTrue(result, "Should return True on success")

        # Check that controls were set to 0 (off)
        controls = mock_camera.set_controls.call_args[0][0]
        self.assertEqual(controls['LensShadingMapMode'], 0)
        self.assertEqual(controls['HotPixelMode'], 0)

    def test_apply_isp_controls_error(self):
        """Test handling of errors when applying ISP controls"""
        mock_camera = Mock()
        mock_camera.set_controls.side_effect = Exception("Control error")

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        self.assertFalse(result, "Should return False on error")


if __name__ == '__main__':
    unittest.main()
