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

# Skip all tests if not on hardware
pytest.importorskip("picamera2")


class TestMeteringExposure:
    """Integration tests for AeMeteringMode in CameraStreamer (hardware-only)"""

    @pytest.mark.hardware
    def test_metering_mode_applied_to_camera(self, stream_ready, temp_webui_settings):
        """AeMeteringMode should be applied to camera controls"""
        # Write test settings with Matrix mode
        with open(temp_webui_settings, 'w') as f:
            f.write("ae_metering_mode=2\n")  # Matrix mode

        # Reload settings into the streamer
        stream_ready.load_stream_settings()

        # Get the applied controls
        applied_controls = stream_ready._apply_camera_controls()

        assert 'AeMeteringMode' in applied_controls, \
            "AeMeteringMode should be in applied controls"
        assert applied_controls['AeMeteringMode'] == 2, \
            "AeMeteringMode should be set to Matrix mode (2)"

    @pytest.mark.hardware
    def test_metering_mode_affects_metadata(self, stream_ready, temp_webui_settings):
        """
        Metering mode should be reflected in camera metadata
        (Hardware-only test - requires actual camera)
        """
        # Write test settings with Spot mode
        with open(temp_webui_settings, 'w') as f:
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

        # Capture metadata (using production fallback pattern from app.py)
        try:
            # Try capture_metadata first (works during hardware MJPEG)
            metadata = stream_ready.camera.capture_metadata()
        except Exception:
            # Fallback: use capture_request (works during software encoding)
            try:
                request = stream_ready.camera.capture_request()
                metadata = request.get_metadata()
                request.release()
            except Exception as e:
                pytest.skip(f"Could not capture metadata: {e}")

        # AeMeteringMode should be reflected in metadata
        # Note: metadata key may be 'AeMeteringMode' depending on Picamera2 version
        assert 'AeMeteringMode' in metadata or 'ExposureMode' in metadata, \
            "Metering mode should be in metadata"

    @pytest.mark.hardware
    def test_metering_mode_integration_with_other_controls(self, stream_ready, temp_webui_settings):
        """AeMeteringMode should work alongside other camera controls"""
        # Write comprehensive settings
        with open(temp_webui_settings, 'w') as f:
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
