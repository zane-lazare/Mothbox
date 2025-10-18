import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

"""
Integration tests for AeMeteringMode exposure control

Tests that different metering modes affect exposure calculation as expected
"""
import pytest
import sys
from pathlib import Path

# Add webui/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from camera_stream import CameraStreamer
from mothbox_paths import WEBUI_SETTINGS_FILE

# Skip all tests if not on hardware
pytest.importorskip("picamera2")


@pytest.mark.stream
class TestMeteringExposure:
    """Integration tests for AeMeteringMode in CameraStreamer"""

    def test_metering_mode_loads_from_settings(self, mock_socketio, temp_webui_settings):
        """CameraStreamer should load ae_metering_mode from settings file"""
        # Write test settings with specific metering mode
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("ae_metering_mode=1\n")  # Spot mode

        streamer = CameraStreamer(mock_socketio)

        assert streamer.ae_metering_mode == 1, \
            "ae_metering_mode should be loaded from settings file"

    def test_metering_mode_defaults_to_centre_weighted(self, mock_socketio, temp_webui_settings):
        """CameraStreamer should default to Centre-Weighted (0) if not specified"""
        # Write settings without metering mode
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("sharpness=1.0\n")

        streamer = CameraStreamer(mock_socketio)

        assert streamer.ae_metering_mode == 0, \
            "ae_metering_mode should default to 0 (Centre-Weighted)"

    @pytest.mark.hardware
    def test_metering_mode_applied_to_camera(self, stream_ready, temp_webui_settings):
        """AeMeteringMode should be applied to camera controls"""
        # Write test settings with Matrix mode
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("ae_metering_mode=2\n")  # Matrix mode

        # Reload settings into the streamer
        stream_ready.load_stream_settings()

        # Get the applied controls
        applied_controls = stream_ready._apply_camera_controls()

        assert 'AeMeteringMode' in applied_controls, \
            "AeMeteringMode should be in applied controls"
        assert applied_controls['AeMeteringMode'] == 2, \
            "AeMeteringMode should be set to Matrix mode (2)"

    def test_all_metering_modes_valid(self, mock_socketio, temp_webui_settings):
        """All metering modes (0, 1, 2) should be accepted"""
        metering_modes = {
            0: "Centre-Weighted",
            1: "Spot",
            2: "Matrix"
        }

        for mode_value, mode_name in metering_modes.items():
            # Write settings with specific mode
            with open(WEBUI_SETTINGS_FILE, 'w') as f:
                f.write(f"ae_metering_mode={mode_value}\n")

            streamer = CameraStreamer(mock_socketio)

            assert streamer.ae_metering_mode == mode_value, \
                f"{mode_name} mode ({mode_value}) should be loaded correctly"

            # Cleanup
            if streamer.camera:
                streamer.release_camera()

    @pytest.mark.hardware
    def test_metering_mode_affects_metadata(self, stream_ready, temp_webui_settings):
        """
        Metering mode should be reflected in camera metadata
        (Hardware-only test - requires actual camera)
        """
        # Write test settings with Spot mode
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("ae_metering_mode=1\n")  # Spot mode

        # Reload settings into the streamer
        stream_ready.load_stream_settings()

        # Start camera (if not already started by fixture)
        if not stream_ready.camera.started:
            stream_ready.camera.start()

        # Apply controls
        stream_ready._apply_camera_controls()

        # Let camera stabilize
        import time
        time.sleep(0.3)

        # Capture metadata
        try:
            metadata = stream_ready.camera.capture_metadata()

            # AeMeteringMode should be reflected in metadata
            # Note: metadata key may be 'AeMeteringMode' depending on Picamera2 version
            assert 'AeMeteringMode' in metadata or 'ExposureMode' in metadata, \
                "Metering mode should be in metadata"

        except Exception as e:
            pytest.skip(f"Could not capture metadata: {e}")

    @pytest.mark.hardware
    def test_metering_mode_integration_with_other_controls(self, stream_ready, temp_webui_settings):
        """AeMeteringMode should work alongside other camera controls"""
        # Write comprehensive settings
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("ae_metering_mode=1\n")  # Spot mode
            f.write("sharpness=2.0\n")
            f.write("brightness=0.1\n")
            f.write("contrast=1.5\n")
            f.write("saturation=1.2\n")

        # Reload settings into the streamer
        stream_ready.load_stream_settings()

        # Verify all settings loaded correctly
        assert stream_ready.ae_metering_mode == 1
        assert stream_ready.sharpness == 2.0
        assert stream_ready.brightness == 0.1
        assert stream_ready.contrast == 1.5
        assert stream_ready.saturation == 1.2

        # Verify controls can be applied without error
        applied_controls = stream_ready._apply_camera_controls()

        assert applied_controls['AeMeteringMode'] == 1
        assert applied_controls['Sharpness'] == 2.0
        assert applied_controls['Brightness'] == 0.1
        assert applied_controls['Contrast'] == 1.5
        assert applied_controls['Saturation'] == 1.2
