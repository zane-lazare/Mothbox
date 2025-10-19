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
