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

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add webui/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

import tuning_loader


@pytest.mark.stream
@pytest.mark.hardware
class TestTuningLoader:
    """Test suite for tuning_loader module"""

    def test_tuning_dir_exists(self):
        """Test that tuning directory exists"""
        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        assert tuning_dir.exists(), f"Tuning directory should exist at {tuning_dir}"

    def test_default_tuning_file_exists(self):
        """Test that default.json exists"""
        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        default_file = tuning_dir / 'default.json'
        assert default_file.exists(), "default.json should exist in tuning directory"

    def test_default_tuning_file_valid_json(self):
        """Test that default.json is valid JSON"""
        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        default_file = tuning_dir / 'default.json'
        with open(default_file) as f:
            try:
                data = json.load(f)
                assert isinstance(data, dict), "Tuning file should be a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(f"default.json is not valid JSON: {e}")

    def test_default_tuning_file_structure(self):
        """Test that default.json has required structure"""
        tuning_dir = Path(__file__).parent.parent.parent / '5.x' / 'tuning'
        default_file = tuning_dir / 'default.json'
        with open(default_file) as f:
            data = json.load(f)

        # Check for required fields
        assert 'version' in data, "Tuning file should have 'version' field"
        assert 'algorithms' in data, "Tuning file should have 'algorithms' field"
        assert isinstance(data['algorithms'], list), "'algorithms' should be a list"

    def test_load_tuning_file_default(self):
        """Test loading default tuning file"""
        tuning = tuning_loader.load_tuning_file('unknown_camera')
        assert tuning is not None, "Should load default tuning for unknown camera"
        assert 'version' in tuning, "Loaded tuning should have version"

    def test_load_tuning_file_none_camera(self):
        """Test loading tuning with None camera (auto-detect)"""
        # Mock the camera detection to avoid requiring hardware
        with patch('tuning_loader.get_camera_model', return_value='unknown'):
            tuning = tuning_loader.load_tuning_file(None)
            assert tuning is not None, "Should load tuning with auto-detect"

    def test_get_tuning_path_default(self):
        """Test getting tuning path for unknown camera"""
        path = tuning_loader.get_tuning_path('unknown_camera')
        assert path is not None, "Should return default tuning path"
        assert path.exists(), "Tuning path should exist"
        assert path.name == 'default.json', "Should return default.json for unknown camera"

    def test_get_tuning_path_none_camera(self):
        """Test getting tuning path with None camera (auto-detect)"""
        with patch('tuning_loader.get_camera_model', return_value='unknown'):
            path = tuning_loader.get_tuning_path(None)
            assert path is not None, "Should return path with auto-detect"

    @patch('tuning_loader.Picamera2')
    def test_get_camera_model_success(self, mock_picam):
        """Test successful camera model detection"""
        mock_picam.global_camera_info.return_value = [
            {'Model': 'imx708'}
        ]

        model = tuning_loader.get_camera_model()
        assert model == 'imx708', "Should detect camera model"

    @patch('tuning_loader.Picamera2')
    def test_get_camera_model_failure(self, mock_picam):
        """Test camera model detection failure"""
        mock_picam.global_camera_info.side_effect = Exception("No camera")

        model = tuning_loader.get_camera_model()
        assert model == 'unknown', "Should return 'unknown' on failure"

    def test_apply_isp_controls_lens_shading(self):
        """Test applying lens shading control"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=False)

        assert result, "Should return True on success"
        mock_camera.set_controls.assert_called_once()

        # Check that correct controls were set
        controls = mock_camera.set_controls.call_args[0][0]
        assert 'LensShadingMapMode' in controls
        assert controls['LensShadingMapMode'] == 1, "Lens shading should be enabled"

    def test_apply_isp_controls_defect_correction(self):
        """Test applying defect correction control"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=False, defect_correction=True)

        assert result, "Should return True on success"

        # Check that correct controls were set
        controls = mock_camera.set_controls.call_args[0][0]
        assert 'HotPixelMode' in controls
        assert controls['HotPixelMode'] == 1, "Defect correction should be enabled (Fast mode)"

    def test_apply_isp_controls_both_disabled(self):
        """Test applying ISP controls with both features disabled"""
        mock_camera = Mock()

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=False, defect_correction=False)

        assert result, "Should return True on success"

        # Check that controls were set to 0 (off)
        controls = mock_camera.set_controls.call_args[0][0]
        assert controls['LensShadingMapMode'] == 0
        assert controls['HotPixelMode'] == 0

    def test_apply_isp_controls_error(self):
        """Test handling of errors when applying ISP controls"""
        mock_camera = Mock()
        mock_camera.set_controls.side_effect = Exception("Control error")

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        assert not result, "Should return False on error"
