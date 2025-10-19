"""
Integration Tests: Noise Reduction Quality

Tests noise reduction settings persistence and control integration.

These tests verify:
- Settings persist across stream restarts
- Noise reduction mode is included in camera controls dict
- All noise reduction modes (0, 1, 2) work in controls

NOTE: Hardware tests moved to test_noise_reduction_hardware.py
      API tests moved to test_noise_reduction_api.py

Usage:
    pytest Tests/integration/test_noise_reduction_quality.py -v -s
"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

import pytest
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from camera_stream import CameraStreamer
from mothbox_paths import WEBUI_SETTINGS_FILE


@pytest.mark.stream
class TestNoiseReductionPersistence:
    """Test that noise reduction settings persist"""

    def test_noise_reduction_loads_from_settings(self):
        """Test that noise reduction mode loads from webui_settings.txt"""
        from mothbox_paths import get_control_values
        from unittest.mock import MagicMock

        # Write test setting
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("noise_reduction_mode=2\n")
            f.write("sharpness=1.0\n")

        # Create streamer and load settings
        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.load_stream_settings()

        # Verify noise reduction loaded
        assert streamer.noise_reduction_mode == 2
        print("\n✓ Noise reduction mode loaded from settings: 2 (High Quality)")

    def test_noise_reduction_defaults_when_missing(self):
        """Test that noise reduction defaults to 0 when not in settings"""
        from unittest.mock import MagicMock

        # Write settings without noise_reduction_mode
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write("sharpness=1.5\n")

        # Create streamer and load settings
        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.load_stream_settings()

        # Should default to 0 (Off)
        assert streamer.noise_reduction_mode == 0
        print("\n✓ Noise reduction mode defaulted to 0 (Off) when not in settings")


@pytest.mark.stream
class TestNoiseReductionControlsIntegration:
    """Test noise reduction integration with _apply_camera_controls"""

    def test_controls_dict_includes_noise_reduction(self):
        """Test that _apply_camera_controls includes NoiseReductionMode"""
        from unittest.mock import MagicMock, patch

        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.noise_reduction_mode = 1

        # Mock camera and set_controls
        mock_camera = MagicMock()
        streamer.camera = mock_camera

        # Call _apply_camera_controls
        controls = streamer._apply_camera_controls()

        # Verify NoiseReductionMode is in controls dict
        assert 'NoiseReductionMode' in controls
        assert controls['NoiseReductionMode'] == 1

        # Verify set_controls was called with noise reduction
        assert mock_camera.set_controls.called
        call_args = mock_camera.set_controls.call_args[0][0]
        assert 'NoiseReductionMode' in call_args
        assert call_args['NoiseReductionMode'] == 1

        print("\n✓ NoiseReductionMode included in camera controls")
        print(f"   Applied controls: {controls}")

    def test_all_noise_reduction_modes_in_controls(self):
        """Test that all three noise reduction modes work in controls"""
        from unittest.mock import MagicMock

        socketio = MagicMock()

        for mode in [0, 1, 2]:
            streamer = CameraStreamer(socketio)
            streamer.noise_reduction_mode = mode

            mock_camera = MagicMock()
            streamer.camera = mock_camera

            controls = streamer._apply_camera_controls()

            assert controls['NoiseReductionMode'] == mode
            print(f"✓ NoiseReductionMode={mode} applied in controls")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
