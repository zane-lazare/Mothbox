"""
Diagnostic test to print all available metadata fields from camera
Run with: pytest Tests/integration/test_metadata_debug.py -v -s
"""

import pytest
import time
from pathlib import Path
import sys

# Add webui backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))


@pytest.mark.integration
@pytest.mark.hardware
@pytest.mark.stream
class TestMetadataDebug:
    """Diagnostic tests to examine available metadata fields"""

    def test_print_all_metadata_fields(self, app):
        """Print all metadata fields available from the camera"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            # Start streaming
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)  # Wait for stream to stabilize

            # Get metadata directly from camera
            metadata = camera_streamer.camera.capture_metadata()

            print("\n" + "=" * 80)
            print("ALL METADATA FIELDS AVAILABLE FROM CAMERA:")
            print("=" * 80)
            print(f"Total fields: {len(metadata)}")
            print("=" * 80)

            for key in sorted(metadata.keys()):
                value = metadata[key]
                value_type = type(value).__name__

                # Format value for display
                if isinstance(value, (tuple, list)):
                    value_display = f"{value_type} len={len(value)} {repr(value)}"
                elif isinstance(value, (int, float)):
                    value_display = f"{value_type} {value}"
                else:
                    value_display = f"{value_type} {repr(value)}"

                print(f"{key:30} = {value_display}")

            print("=" * 80)

            # Also test that we can successfully get metadata
            assert metadata is not None
            assert len(metadata) > 0

        finally:
            camera_streamer.stop_streaming()

    def test_check_specific_extended_fields(self, app):
        """Check which extended metadata fields we're looking for actually exist"""
        camera_streamer = app.config['CAMERA_STREAMER']

        if not camera_streamer.camera:
            camera_streamer.initialize_camera()
            time.sleep(1.0)

        try:
            if not camera_streamer.start_streaming():
                pytest.skip("Camera not available")

            time.sleep(2)
            metadata = camera_streamer.camera.capture_metadata()

            # Fields we're testing for
            fields_to_check = [
                'DigitalGain',
                'FocusFoM',
                'SensorTimestamp',
                'ColourGains',
                'FrameDuration',
                'SensorBlackLevels',
                'SensorTemperature',
                'ScalerCrop',
                'AeLocked',
                'AwbLocked',
                'Lux',
                'Saturation',
                'Contrast',
                'Sharpness',
                'Brightness',
            ]

            print("\n" + "=" * 80)
            print("CHECKING EXTENDED METADATA FIELDS:")
            print("=" * 80)

            for field in fields_to_check:
                exists = field in metadata
                status = "✓ EXISTS" if exists else "✗ MISSING"
                value = metadata.get(field, "N/A")
                print(f"{status:12} {field:30} = {repr(value)}")

            print("=" * 80)

        finally:
            camera_streamer.stop_streaming()
