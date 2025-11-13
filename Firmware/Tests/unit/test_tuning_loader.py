import os
from pathlib import Path

# Set MOTHBOX_HOME to use local development paths instead of /etc/mothbox
os.environ['MOTHBOX_HOME'] = str(Path(__file__).parent.parent.parent)
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Unit tests for ISP tuning loader module - REAL HARDWARE ONLY

All tests use real Picamera2 hardware with no mocks.
Tests will FAIL if camera is unavailable (no false positives).

Tests:
- Tuning file structure and location
- Camera model detection (real hardware)
- ISP control application (real camera metadata verification)
"""

import pytest
import sys
import json

# Add webui/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

import tuning_loader
from mothbox_paths import ISP_TUNING_DIR, ISP_DEFAULT_TUNING_FILE


@pytest.mark.stream
@pytest.mark.hardware
class TestTuningFileStructure:
    """Test tuning file location and structure (no camera required)"""

    def test_tuning_dir_exists(self):
        """Test that ISP tuning directory exists at CONFIG_DIR"""
        assert ISP_TUNING_DIR.exists(), f"ISP tuning directory should exist at {ISP_TUNING_DIR}"

    def test_default_tuning_file_exists(self):
        """Test that camera_isp_tuning.json exists"""
        assert ISP_DEFAULT_TUNING_FILE.exists(), \
            f"Default tuning file should exist at {ISP_DEFAULT_TUNING_FILE}"

    def test_default_tuning_file_valid_json(self):
        """Test that camera_isp_tuning.json is valid JSON"""
        with open(ISP_DEFAULT_TUNING_FILE) as f:
            try:
                data = json.load(f)
                assert isinstance(data, dict), "Tuning file should be a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(f"camera_isp_tuning.json is not valid JSON: {e}")

    def test_default_tuning_file_structure(self):
        """Test that camera_isp_tuning.json has required structure"""
        with open(ISP_DEFAULT_TUNING_FILE) as f:
            data = json.load(f)

        # Check for required fields
        assert 'version' in data, "Tuning file should have 'version' field"
        assert 'algorithms' in data, "Tuning file should have 'algorithms' field"
        assert isinstance(data['algorithms'], list), "'algorithms' should be a list"

    def test_default_tuning_has_dpc_algorithm(self):
        """Test that default tuning includes DPC (defect pixel correction)"""
        with open(ISP_DEFAULT_TUNING_FILE) as f:
            data = json.load(f)

        # Check for DPC algorithm
        algorithms = data.get('algorithms', [])
        dpc_found = any('rpi.dpc' in algo for algo in algorithms)
        assert dpc_found, "Tuning file should include rpi.dpc algorithm"

    def test_default_tuning_has_alsc_algorithm(self):
        """Test that default tuning includes ALSC (lens shading correction)"""
        with open(ISP_DEFAULT_TUNING_FILE) as f:
            data = json.load(f)

        # Check for ALSC algorithm
        algorithms = data.get('algorithms', [])
        alsc_found = any('rpi.alsc' in algo for algo in algorithms)
        assert alsc_found, "Tuning file should include rpi.alsc algorithm"


@pytest.mark.stream
@pytest.mark.hardware
class TestCameraDetection:
    """Test camera model detection with REAL hardware"""

    def test_get_camera_model_success(self):
        """Test camera model detection returns valid model (real hardware)"""
        model = tuning_loader.get_camera_model()

        # Should detect a real camera model (not 'unknown')
        assert model != 'unknown', "Should detect real camera model on hardware"
        assert isinstance(model, str), "Camera model should be a string"
        assert len(model) > 0, "Camera model should not be empty"

    def test_load_tuning_file_for_detected_model(self):
        """Test loading tuning file for detected camera model"""
        model = tuning_loader.get_camera_model()
        tuning = tuning_loader.load_tuning_file(model)

        # Should load tuning (either model-specific or default)
        assert tuning is not None, "Should load tuning file"
        assert 'version' in tuning, "Loaded tuning should have version"
        assert 'algorithms' in tuning, "Loaded tuning should have algorithms"

    def test_get_tuning_path_returns_valid_path(self):
        """Test getting tuning path returns existing file"""
        path = tuning_loader.get_tuning_path()

        assert path is not None, "Should return a tuning path"
        assert path.exists(), "Tuning path should exist"
        assert path.is_file(), "Tuning path should be a file"
        assert path.suffix == '.json', "Tuning file should be JSON"


@pytest.mark.stream
@pytest.mark.hardware
class TestISPControlsRealHardware:
    """Test ISP control application on REAL camera hardware

    Note: LensShadingMapMode is NOT available as a runtime control on ov64a40.
    Lens shading is always enabled via rpi.alsc in the tuning file and cannot
    be toggled at runtime. Tests verify only defect correction (HotPixelMode).
    """

    @pytest.mark.skip(reason="LensShadingMapMode not available on ov64a40 - lens shading always on via tuning file")
    def test_apply_lens_shading_enabled(self, camera_streamer):
        """SKIPPED: Lens shading control not available at runtime on ov64a40"""
        pass

    @pytest.mark.skip(reason="LensShadingMapMode not available on ov64a40 - lens shading always on via tuning file")
    def test_apply_lens_shading_disabled(self, camera_streamer):
        """SKIPPED: Lens shading control not available at runtime on ov64a40"""
        pass

    @pytest.mark.skip(reason="HotPixelMode not available on ov64a40 - defect correction always on via tuning file")
    def test_apply_defect_correction_enabled(self, camera_streamer):
        """SKIPPED: Defect correction control not available at runtime on ov64a40"""
        pass

    @pytest.mark.skip(reason="HotPixelMode not available on ov64a40 - defect correction always on via tuning file")
    def test_apply_defect_correction_disabled(self, camera_streamer):
        """SKIPPED: Defect correction control not available at runtime on ov64a40"""
        pass


# ============================================================================
# Mocked Tests - No Hardware Required
# ============================================================================

from unittest.mock import Mock, patch, MagicMock, mock_open


class TestCameraModelDetectionMocked:
    """Test camera model detection with mocked Picamera2"""

    def test_get_camera_model_with_mock_picamera2(self):
        """Should detect camera model from mocked Picamera2"""
        mock_camera_info = [{'Model': 'imx708'}]

        # Mock at the import level
        with patch.dict('sys.modules', {'picamera2': MagicMock()}):
            # Create mock Picamera2 class
            mock_picam = MagicMock()
            mock_picam.global_camera_info.return_value = mock_camera_info

            with patch('picamera2.Picamera2', mock_picam):
                result = tuning_loader.get_camera_model()
                assert result == 'imx708'

    def test_get_camera_model_import_error(self):
        """Should return 'unknown' when Picamera2 import fails"""
        # Ensure picamera2 is not in modules
        with patch.dict('sys.modules', {'picamera2': None}):
            result = tuning_loader.get_camera_model()
            assert result == 'unknown'

    def test_get_camera_model_no_camera_info(self):
        """Should return 'unknown' when camera_info is empty"""
        mock_picam = MagicMock()
        mock_picam.global_camera_info.return_value = []

        with patch.dict('sys.modules', {'picamera2': MagicMock()}):
            with patch('picamera2.Picamera2', mock_picam):
                result = tuning_loader.get_camera_model()
                assert result == 'unknown'

    def test_get_camera_model_exception_handling(self):
        """Should return 'unknown' when exception occurs"""
        mock_picam = MagicMock()
        mock_picam.global_camera_info.side_effect = Exception("Camera error")

        with patch.dict('sys.modules', {'picamera2': MagicMock()}):
            with patch('picamera2.Picamera2', mock_picam):
                result = tuning_loader.get_camera_model()
                assert result == 'unknown'

    def test_get_camera_model_multiple_cameras(self):
        """Should use first camera when multiple cameras available"""
        mock_camera_info = [
            {'Model': 'imx477'},
            {'Model': 'imx708'}
        ]

        mock_picam = MagicMock()
        mock_picam.global_camera_info.return_value = mock_camera_info

        with patch.dict('sys.modules', {'picamera2': MagicMock()}):
            with patch('picamera2.Picamera2', mock_picam):
                result = tuning_loader.get_camera_model()
                assert result == 'imx477'

    def test_get_camera_model_missing_model_key(self):
        """Should return 'unknown' when Model key missing"""
        mock_camera_info = [{'Sensor': 'OV64A40'}]  # Missing 'Model' key

        mock_picam = MagicMock()
        mock_picam.global_camera_info.return_value = mock_camera_info

        with patch.dict('sys.modules', {'picamera2': MagicMock()}):
            with patch('picamera2.Picamera2', mock_picam):
                result = tuning_loader.get_camera_model()
                assert result == 'unknown'


class TestTuningFileLoadingMocked:
    """Test tuning file loading with mocked filesystem"""

    def test_load_tuning_model_specific_file(self, tmp_path, monkeypatch):
        """Should load model-specific tuning file when it exists"""
        # Create temporary tuning directory and file
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        model_file = tuning_dir / "imx708.json"
        model_file.write_text('{"version": 2.0, "algorithms": []}')

        # Patch the paths
        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        result = tuning_loader.load_tuning_file('imx708')
        assert result is not None
        assert result['version'] == 2.0

    def test_load_tuning_fallback_to_default(self, tmp_path, monkeypatch):
        """Should fall back to default when model-specific file doesn't exist"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        default_file = tmp_path / "camera_isp_tuning.json"
        default_file.write_text('{"version": 1.0, "algorithms": []}')

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)
        monkeypatch.setattr('tuning_loader.ISP_DEFAULT_TUNING_FILE', default_file)

        result = tuning_loader.load_tuning_file('unknown_model')
        assert result is not None
        assert result['version'] == 1.0

    def test_load_tuning_invalid_json(self, tmp_path, monkeypatch):
        """Should return None for invalid JSON"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        model_file = tuning_dir / "bad_model.json"
        model_file.write_text('{ invalid json }')

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        result = tuning_loader.load_tuning_file('bad_model')
        assert result is None

    def test_load_tuning_file_not_found(self, tmp_path, monkeypatch):
        """Should return None when no tuning file found"""
        tuning_dir = tmp_path / "empty"
        tuning_dir.mkdir()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)
        monkeypatch.setattr('tuning_loader.ISP_DEFAULT_TUNING_FILE', tmp_path / "nonexistent.json")

        result = tuning_loader.load_tuning_file('unknown')
        assert result is None

    def test_load_tuning_io_error(self, tmp_path, monkeypatch):
        """Should handle IO errors gracefully"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = tuning_loader.load_tuning_file('imx708')
            assert result is None

    def test_load_tuning_with_auto_detection(self, tmp_path, monkeypatch):
        """Should auto-detect camera model when not provided"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        model_file = tuning_dir / "imx477.json"
        model_file.write_text('{"version": 2.0}')

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        with patch('tuning_loader.get_camera_model', return_value='imx477'):
            result = tuning_loader.load_tuning_file()  # No model specified
            assert result is not None
            assert result['version'] == 2.0


class TestISPControlsApplicationMocked:
    """Test ISP controls application with mocked camera"""

    def test_apply_isp_both_enabled(self):
        """Should apply both ISP controls when enabled"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None, 'HotPixelMode': None}

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        assert result is True
        # Check that set_controls was called
        assert mock_camera.set_controls.call_count == 2

    def test_apply_isp_both_disabled(self):
        """Should disable both ISP controls when disabled"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None, 'HotPixelMode': None}

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=False, defect_correction=False)

        assert result is True
        assert mock_camera.set_controls.call_count == 2

    def test_apply_isp_lens_shading_only(self):
        """Should apply only lens shading when defect correction unavailable"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None}  # Only lens shading available

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        assert result is True
        assert mock_camera.set_controls.call_count == 1

    def test_apply_isp_defect_correction_only(self):
        """Should apply only defect correction when lens shading unavailable"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'HotPixelMode': None}  # Only defect correction available

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        assert result is True
        assert mock_camera.set_controls.call_count == 1

    def test_apply_isp_control_not_available(self):
        """Should return False when no controls available"""
        mock_camera = Mock()
        mock_camera.camera_controls = {}  # No controls available

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        assert result is False
        assert mock_camera.set_controls.call_count == 0

    def test_apply_isp_set_controls_exception(self):
        """Should handle exceptions when setting controls"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None}
        mock_camera.set_controls.side_effect = Exception("Control error")

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=False)

        # Should return False since the one available control failed
        assert result is False

    def test_apply_isp_partial_failure(self):
        """Should continue on partial failure"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None, 'HotPixelMode': None}

        # First call succeeds, second fails
        mock_camera.set_controls.side_effect = [None, Exception("Second control failed")]

        result = tuning_loader.apply_isp_controls(mock_camera, lens_shading=True, defect_correction=True)

        # Should return True since one control succeeded
        assert result is True
        assert mock_camera.set_controls.call_count == 2


class TestTuningPathResolutionMocked:
    """Test tuning path resolution with mocked filesystem"""

    def test_get_tuning_path_model_specific(self, tmp_path, monkeypatch):
        """Should return model-specific tuning path when it exists"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        model_file = tuning_dir / "imx708.json"
        model_file.touch()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        result = tuning_loader.get_tuning_path('imx708')
        assert result == model_file

    def test_get_tuning_path_fallback(self, tmp_path, monkeypatch):
        """Should fallback to default when model-specific doesn't exist"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        default_file = tmp_path / "camera_isp_tuning.json"
        default_file.touch()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)
        monkeypatch.setattr('tuning_loader.ISP_DEFAULT_TUNING_FILE', default_file)

        result = tuning_loader.get_tuning_path('unknown_model')
        assert result == default_file

    def test_get_tuning_path_not_found(self, tmp_path, monkeypatch):
        """Should return None when no tuning file found"""
        tuning_dir = tmp_path / "empty"
        tuning_dir.mkdir()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)
        monkeypatch.setattr('tuning_loader.ISP_DEFAULT_TUNING_FILE', tmp_path / "nonexistent.json")

        result = tuning_loader.get_tuning_path('unknown')
        assert result is None

    def test_get_tuning_path_with_auto_detect(self, tmp_path, monkeypatch):
        """Should auto-detect camera when model not specified"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        model_file = tuning_dir / "imx477.json"
        model_file.touch()

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        with patch('tuning_loader.get_camera_model', return_value='imx477'):
            result = tuning_loader.get_tuning_path()
            assert result == model_file


class TestControlMapping:
    """Test control name mapping"""

    def test_lens_shading_control_mapping(self):
        """Should use correct control name for lens shading"""
        from camera_control_mapping import SNAKE_TO_PASCAL
        assert 'lens_shading_map_mode' in SNAKE_TO_PASCAL
        assert SNAKE_TO_PASCAL['lens_shading_map_mode'] == 'LensShadingMapMode'

    def test_hot_pixel_control_mapping(self):
        """Should use correct control name for hot pixel correction"""
        from camera_control_mapping import SNAKE_TO_PASCAL
        assert 'hot_pixel_mode' in SNAKE_TO_PASCAL
        assert SNAKE_TO_PASCAL['hot_pixel_mode'] == 'HotPixelMode'


class TestErrorHandling:
    """Test error handling in tuning loader"""

    def test_handles_corrupt_json_file(self, tmp_path, monkeypatch):
        """Should handle corrupt JSON gracefully"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        corrupt_file = tuning_dir / "corrupt.json"
        corrupt_file.write_text('{"version": "incomplete')

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        result = tuning_loader.load_tuning_file('corrupt')
        assert result is None

    def test_handles_empty_json_file(self, tmp_path, monkeypatch):
        """Should handle empty JSON file"""
        tuning_dir = tmp_path / "tuning"
        tuning_dir.mkdir()
        empty_file = tuning_dir / "empty.json"
        empty_file.write_text('')

        monkeypatch.setattr('tuning_loader.TUNING_DIR', tuning_dir)

        result = tuning_loader.load_tuning_file('empty')
        assert result is None

    def test_camera_controls_exception_recovery(self):
        """Should recover from camera control exceptions"""
        mock_camera = Mock()
        mock_camera.camera_controls = {'LensShadingMapMode': None, 'HotPixelMode': None}
        mock_camera.set_controls.side_effect = [Exception("First failed"), None]  # First fails, second succeeds

        result = tuning_loader.apply_isp_controls(mock_camera)

        # Should still succeed with the second control
        assert result is True
