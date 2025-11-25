"""
Unit tests for LiveViewStreamer.get_current_settings() method

Tests that the get_current_settings() method correctly exports
all current camera settings from the live instance (not from file).

Uses camera_streamer_unit fixture from conftest.py which provides
a LiveViewStreamer with fully mocked Picamera2 for CI compatibility.
"""

import pytest
from unittest.mock import MagicMock


class TestGetCurrentSettings:
    """Test LiveViewStreamer.get_current_settings() method"""

    def test_get_current_settings_returns_dict(self, camera_streamer_unit):
        """Should return a dictionary"""
        settings = camera_streamer_unit.get_current_settings()

        assert isinstance(settings, dict)
        assert len(settings) > 0

    def test_get_current_settings_returns_all_controls(self, camera_streamer_unit):
        """Should return complete dict of current camera settings"""
        settings = camera_streamer_unit.get_current_settings()

        # Verify all required keys present
        required_keys = [
            'sharpness',
            'brightness',
            'contrast',
            'saturation',
            'af_mode',
            'af_speed',
            'af_range',
            'ae_enable',
            'ae_metering_mode',
            'awb_enable',
            'awb_mode',
            'exposure_time',
            'analogue_gain',
            'noise_reduction_mode',
            'colour_gains_red',
            'colour_gains_blue',
        ]

        for key in required_keys:
            assert key in settings, f"Missing key: {key}"

    def test_get_current_settings_returns_correct_types(self, camera_streamer_unit):
        """All returned values should have correct types"""
        settings = camera_streamer_unit.get_current_settings()

        assert isinstance(settings['sharpness'], float)
        assert isinstance(settings['brightness'], float)
        assert isinstance(settings['contrast'], float)
        assert isinstance(settings['saturation'], float)
        assert isinstance(settings['af_mode'], int)
        assert isinstance(settings['af_speed'], int)
        assert isinstance(settings['af_range'], int)
        assert isinstance(settings['ae_enable'], bool)
        assert isinstance(settings['ae_metering_mode'], int)
        assert isinstance(settings['awb_enable'], bool)
        assert isinstance(settings['awb_mode'], int)
        assert isinstance(settings['exposure_time'], int)
        assert isinstance(settings['analogue_gain'], float)
        assert isinstance(settings['noise_reduction_mode'], int)
        assert isinstance(settings['colour_gains_red'], float)
        assert isinstance(settings['colour_gains_blue'], float)

    def test_get_current_settings_includes_colour_gains_tuple(self, camera_streamer_unit):
        """ColourGains should be split into red/blue components"""
        camera_streamer_unit.colour_gains = (2.5, 1.8)
        settings = camera_streamer_unit.get_current_settings()

        assert settings['colour_gains_red'] == 2.5
        assert settings['colour_gains_blue'] == 1.8

    def test_get_current_settings_reflects_instance_values(self, camera_streamer_unit):
        """Settings should reflect current instance variable values"""
        # Set known values
        camera_streamer_unit.sharpness = 2.5
        camera_streamer_unit.brightness = 0.1
        camera_streamer_unit.exposure_time = 15000
        camera_streamer_unit.analogue_gain = 12.0

        settings = camera_streamer_unit.get_current_settings()

        # Verify values match instance variables
        assert settings['sharpness'] == 2.5
        assert settings['brightness'] == 0.1
        assert settings['exposure_time'] == 15000
        assert settings['analogue_gain'] == 12.0

    def test_get_current_settings_after_update_control(self, camera_streamer_unit):
        """Settings should reflect updates from update_control()"""
        # Simulate control update
        camera_streamer_unit.sharpness = 3.0
        camera_streamer_unit.exposure_time = 20000

        settings = camera_streamer_unit.get_current_settings()

        # Should reflect updated values
        assert settings['sharpness'] == 3.0
        assert settings['exposure_time'] == 20000

    def test_get_current_settings_when_camera_not_started(self, camera_streamer_unit):
        """Should return settings even if camera not active"""
        camera_streamer_unit.camera = None

        settings = camera_streamer_unit.get_current_settings()

        # Should return default/configured values
        assert settings is not None
        assert isinstance(settings, dict)
        assert 'sharpness' in settings
        assert 'exposure_time' in settings

    def test_get_current_settings_with_camera_active(self, camera_streamer_unit):
        """Should include lens_position from camera metadata when camera active"""
        # Create mock camera with metadata
        mock_camera = MagicMock()
        mock_camera.capture_metadata.return_value = {
            'LensPosition': 5.2,
            'ExposureTime': 10000,
        }
        camera_streamer_unit.camera = mock_camera

        settings = camera_streamer_unit.get_current_settings()

        # Should include lens position from camera metadata
        assert 'lens_position' in settings
        assert settings['lens_position'] == 5.2

    def test_get_current_settings_lens_position_fallback(self, camera_streamer_unit):
        """Should fall back to configured lens_position if camera metadata unavailable"""
        # Camera active but metadata query fails
        mock_camera = MagicMock()
        mock_camera.capture_metadata.side_effect = Exception("Metadata not available")
        camera_streamer_unit.camera = mock_camera
        camera_streamer_unit.lens_position = 7.5

        settings = camera_streamer_unit.get_current_settings()

        # Should fall back to configured value
        assert 'lens_position' in settings
        assert settings['lens_position'] == 7.5

    def test_get_current_settings_handles_missing_lens_position(self, camera_streamer_unit):
        """Should gracefully handle missing lens_position attribute"""
        # Camera not available and no lens_position attribute
        camera_streamer_unit.camera = None
        if hasattr(camera_streamer_unit, 'lens_position'):
            delattr(camera_streamer_unit, 'lens_position')

        settings = camera_streamer_unit.get_current_settings()

        # Should still return valid dict (lens_position may be absent)
        assert isinstance(settings, dict)
        assert 'sharpness' in settings

    def test_get_current_settings_with_af_mode_override(self, camera_streamer_unit):
        """Should use af_mode_override when present"""
        camera_streamer_unit.af_mode = 2  # Continuous
        camera_streamer_unit._af_mode_override = 0  # Manual override

        settings = camera_streamer_unit.get_current_settings()

        # Should use override value
        assert settings['af_mode'] == 0

    def test_get_current_settings_without_af_mode_override(self, camera_streamer_unit):
        """Should use regular af_mode when no override"""
        camera_streamer_unit.af_mode = 2  # Continuous
        camera_streamer_unit._af_mode_override = None

        settings = camera_streamer_unit.get_current_settings()

        # Should use regular value
        assert settings['af_mode'] == 2

    def test_get_current_settings_handles_exception_gracefully(self, camera_streamer_unit):
        """Should not raise exception even if internal error occurs"""
        # This test verifies defensive programming
        # Even with broken camera, should return something useful
        camera_streamer_unit.camera = MagicMock()
        camera_streamer_unit.camera.capture_metadata.side_effect = RuntimeError("Camera fault")

        try:
            settings = camera_streamer_unit.get_current_settings()
            # Should succeed (with fallback values)
            assert isinstance(settings, dict)
        except Exception as e:
            pytest.fail(f"get_current_settings() should not raise exception: {e}")

    def test_get_current_settings_with_manual_exposure(self, camera_streamer_unit):
        """Should correctly export manual exposure settings"""
        camera_streamer_unit.ae_enable = False
        camera_streamer_unit.exposure_time = 25000
        camera_streamer_unit.analogue_gain = 15.0

        settings = camera_streamer_unit.get_current_settings()

        assert settings['ae_enable'] is False
        assert settings['exposure_time'] == 25000
        assert settings['analogue_gain'] == 15.0

    def test_get_current_settings_with_manual_white_balance(self, camera_streamer_unit):
        """Should correctly export manual white balance settings"""
        camera_streamer_unit.awb_enable = False
        camera_streamer_unit.colour_gains = (1.8, 2.2)

        settings = camera_streamer_unit.get_current_settings()

        assert settings['awb_enable'] is False
        assert settings['colour_gains_red'] == 1.8
        assert settings['colour_gains_blue'] == 2.2

    def test_get_current_settings_exports_af_metering(self, camera_streamer_unit):
        """Should export af_metering based on AF window state"""
        # Test with no AF window (default)
        camera_streamer_unit._af_window_active = False
        settings = camera_streamer_unit.get_current_settings()
        assert 'af_metering' in settings
        assert settings['af_metering'] == 0

        # Test with AF window active
        camera_streamer_unit._af_window_active = True
        settings = camera_streamer_unit.get_current_settings()
        assert settings['af_metering'] == 1
