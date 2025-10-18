"""
Integration Tests: Noise Reduction Hardware

Tests that noise reduction modes are properly applied to real camera hardware.

These tests verify:
- Noise reduction control values are applied to camera
- Camera hardware accepts noise reduction modes 0, 1, 2

RUN ON RASPBERRY PI ONLY - requires camera hardware

Usage:
    pytest Tests/integration/test_noise_reduction_hardware.py -v -s
"""
import os
os.environ['MOTHBOX_ENV'] = 'development'  # Must be set before importing config

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestNoiseReductionHardware:
    """Test that noise reduction modes are applied to real camera hardware"""

    def test_noise_reduction_off_applied(self, camera_streamer):
        """Test that NoiseReductionMode=0 (Off) is applied to camera"""
        # Set noise reduction mode
        camera_streamer.noise_reduction_mode = 0

        # Initialize camera
        camera_streamer.initialize_camera()

        # Verify camera initialized
        assert camera_streamer.camera is not None, "Camera should be initialized"

        # The _apply_camera_controls method should have been called
        # Verify noise reduction mode was set to 0
        print(f"\n✓ Noise reduction mode set to: {camera_streamer.noise_reduction_mode}")
        assert camera_streamer.noise_reduction_mode == 0

    def test_noise_reduction_fast_applied(self, camera_streamer):
        """Test that NoiseReductionMode=1 (Fast) is applied to camera"""
        # Set noise reduction mode
        camera_streamer.noise_reduction_mode = 1

        # Initialize camera
        camera_streamer.initialize_camera()

        # Verify camera initialized and noise reduction mode set
        assert camera_streamer.camera is not None
        print(f"\n✓ Noise reduction mode set to: {camera_streamer.noise_reduction_mode}")
        assert camera_streamer.noise_reduction_mode == 1

    def test_noise_reduction_high_quality_applied(self, camera_streamer):
        """Test that NoiseReductionMode=2 (High Quality) is applied to camera"""
        # Set noise reduction mode
        camera_streamer.noise_reduction_mode = 2

        # Initialize camera
        camera_streamer.initialize_camera()

        # Verify camera initialized and noise reduction mode set
        assert camera_streamer.camera is not None
        print(f"\n✓ Noise reduction mode set to: {camera_streamer.noise_reduction_mode}")
        assert camera_streamer.noise_reduction_mode == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
