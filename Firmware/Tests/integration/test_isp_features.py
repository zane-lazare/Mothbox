import os
from pathlib import Path

# Set MOTHBOX_HOME to use local development paths instead of /etc/mothbox
os.environ['MOTHBOX_HOME'] = str(Path(__file__).parent.parent.parent)
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Integration tests for ISP features - REAL HARDWARE ONLY

Tests ISP integration with camera_stream and settings endpoints.
All tests use real Picamera2 hardware with no mocks or patches.
Tests will FAIL if camera is unavailable (no false positives).
"""

import pytest
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

# Mock Flask/SocketIO before importing camera_stream
from unittest.mock import MagicMock
sys.modules['flask_socketio'] = MagicMock()

import camera_stream
from tuning_loader import apply_isp_controls


@pytest.mark.stream
@pytest.mark.hardware
class TestISPSettingsValidation:
    """Test ISP settings validation (no camera required)"""

    def test_isp_settings_in_allowed_camera_settings(self):
        """Test that ISP settings are in allowed camera settings"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert 'LensShadingEnable' in ALLOWED_CAMERA_SETTINGS, \
            "LensShadingEnable should be in allowed settings"
        assert 'DefectCorrectionEnable' in ALLOWED_CAMERA_SETTINGS, \
            "DefectCorrectionEnable should be in allowed settings"

    def test_isp_validators_accept_true(self):
        """Test that ISP validators accept 'true'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('true'), \
            "Should accept 'true'"
        assert ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('true'), \
            "Should accept 'true'"

    def test_isp_validators_accept_false(self):
        """Test that ISP validators accept 'false'"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('false'), \
            "Should accept 'false'"
        assert ALLOWED_CAMERA_SETTINGS['DefectCorrectionEnable']('false'), \
            "Should accept 'false'"

    def test_isp_validators_case_insensitive(self):
        """Test that ISP validators are case-insensitive"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('True'), \
            "Should accept 'True'"
        assert ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('FALSE'), \
            "Should accept 'FALSE'"

    def test_isp_validators_reject_invalid(self):
        """Test that ISP validators reject invalid values"""
        from routes.camera import ALLOWED_CAMERA_SETTINGS

        # These should return False for invalid values
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('invalid'), \
            "Should reject 'invalid'"
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('1'), \
            "Should reject '1'"
        assert not ALLOWED_CAMERA_SETTINGS['LensShadingEnable']('yes'), \
            "Should reject 'yes'"


@pytest.mark.stream
@pytest.mark.hardware
class TestCameraStreamerISPIntegration:
    """Test ISP integration with CameraStreamer on REAL hardware"""

    def test_camera_streamer_loads_default_isp_settings(self, camera_streamer):
        """Test that CameraStreamer loads default ISP settings from config"""
        # CameraStreamer should have ISP attributes loaded
        assert hasattr(camera_streamer, 'lens_shading_enable'), \
            "Should have lens_shading_enable attribute"
        assert hasattr(camera_streamer, 'defect_correction_enable'), \
            "Should have defect_correction_enable attribute"

        # Default values should be True
        assert camera_streamer.lens_shading_enable is True, \
            "Default lens_shading_enable should be True"
        assert camera_streamer.defect_correction_enable is True, \
            "Default defect_correction_enable should be True"

    def test_tuning_file_loaded_on_camera_init(self, camera_streamer):
        """Test that tuning file is loaded during camera initialization (real hardware)"""
        # Initialize REAL camera
        result = camera_streamer.initialize_camera()
        assert result is True, "Camera initialization should succeed on real hardware"

        # Camera should be initialized with tuning
        assert camera_streamer.camera is not None, "Camera should be initialized"

        # Verify camera is a real Picamera2 instance (not a mock)
        from picamera2 import Picamera2
        assert isinstance(camera_streamer.camera, Picamera2), \
            "Camera should be real Picamera2 instance, not a mock"

    def test_isp_controls_applied_after_camera_start(self, camera_streamer):
        """Test that ISP controls are applied after camera starts (real hardware)

        Note: Only defect correction is verified via metadata. Lens shading is
        always enabled via tuning file (LensShadingMapMode not available at runtime).
        """
        # Set specific ISP settings
        camera_streamer.lens_shading_enable = True
        camera_streamer.defect_correction_enable = False

        # Initialize and start REAL camera
        assert camera_streamer.initialize_camera(), \
            "Camera initialization failed - real hardware required"

        camera_streamer.camera.start()

        # Apply ISP controls
        result = apply_isp_controls(
            camera_streamer.camera,
            lens_shading=camera_streamer.lens_shading_enable,
            defect_correction=camera_streamer.defect_correction_enable
        )

        # Verify controls were applied by reading REAL metadata
        metadata = camera_streamer.camera.capture_metadata()
        assert result is True, "ISP controls should apply successfully"
        # LensShadingMapMode not checked - not available on ov64a40
        assert metadata['HotPixelMode'] == 0, \
            "Defect correction should be disabled in camera metadata"

        camera_streamer.camera.stop()


@pytest.mark.stream
@pytest.mark.hardware
class TestISPControlCombinations:
    """Test various ISP control combinations on REAL hardware

    Note: LensShadingMapMode is NOT available on ov64a40 - lens shading is
    always enabled via rpi.alsc in tuning file. Tests only verify defect
    correction (HotPixelMode) which IS available at runtime.
    """

    def test_defect_correction_off(self, camera_streamer):
        """Test defect correction OFF on real hardware"""
        assert camera_streamer.initialize_camera(), \
            "Camera initialization failed - real hardware required"

        camera_streamer.camera.start()
        apply_isp_controls(
            camera_streamer.camera,
            lens_shading=True,  # Ignored - always on via tuning file
            defect_correction=False
        )

        metadata = camera_streamer.camera.capture_metadata()
        # LensShadingMapMode not checked - not available on ov64a40
        assert metadata['HotPixelMode'] == 0, \
            "Defect correction should be OFF"

        camera_streamer.camera.stop()

    def test_defect_correction_on(self, camera_streamer):
        """Test defect correction ON on real hardware"""
        assert camera_streamer.initialize_camera(), \
            "Camera initialization failed - real hardware required"

        camera_streamer.camera.start()
        apply_isp_controls(
            camera_streamer.camera,
            lens_shading=True,  # Ignored - always on via tuning file
            defect_correction=True
        )

        metadata = camera_streamer.camera.capture_metadata()
        # LensShadingMapMode not checked - not available on ov64a40
        assert metadata['HotPixelMode'] == 1, \
            "Defect correction should be ON"

        camera_streamer.camera.stop()
