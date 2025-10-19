"""
Integration Tests: Noise Reduction Hardware

Tests that noise reduction modes work with real camera hardware through API.

These tests verify:
- Noise reduction settings persist and load correctly
- Camera operations work with different noise reduction modes
- Settings are applied to real hardware through standard workflows

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


@pytest.mark.stream
class TestNoiseReductionHardware:
    """Test that noise reduction modes work with real camera hardware"""

    def test_noise_reduction_off_applied_to_hardware(self, client, app):
        """Test that NoiseReductionMode=0 (Off) is applied to real camera hardware"""
        print("\n🔍 Testing NoiseReductionMode=0 on hardware...")

        # Set noise reduction mode to Off via API
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 0})
        assert response.status_code == 200
        print("   ✓ Setting saved: noise_reduction_mode=0")

        # Get camera_streamer from app context
        with app.app_context():
            from flask import current_app
            streamer = current_app.config.get('CAMERA_STREAMER')
            assert streamer is not None

            # Load settings from file (includes noise_reduction_mode)
            streamer.load_stream_settings()
            assert streamer.noise_reduction_mode == 0
            print("   ✓ Setting loaded into streamer")

            # Initialize camera if needed, then verify controls can be applied
            if not streamer.camera:
                success = streamer.initialize_camera()
                assert success, "Camera should initialize"
                print("   ✓ Camera initialized")

            # Verify NoiseReductionMode can be applied to camera controls
            controls = streamer._apply_camera_controls()
            assert controls['NoiseReductionMode'] == 0
            print("   ✓ NoiseReductionMode=0 applied to camera controls")

    def test_noise_reduction_fast_applied_to_hardware(self, client, app):
        """Test that NoiseReductionMode=1 (Fast) is applied to real camera hardware"""
        print("\n🔍 Testing NoiseReductionMode=1 on hardware...")

        # Set noise reduction mode to Fast via API
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 1})
        assert response.status_code == 200
        print("   ✓ Setting saved: noise_reduction_mode=1")

        # Get camera_streamer from app context
        with app.app_context():
            from flask import current_app
            streamer = current_app.config.get('CAMERA_STREAMER')
            assert streamer is not None

            # Reload settings to pick up the new value
            streamer.load_stream_settings()
            assert streamer.noise_reduction_mode == 1
            print("   ✓ Setting loaded into streamer")

            # Verify camera is already initialized (from previous test)
            # and can apply new noise reduction mode
            if streamer.camera:
                controls = streamer._apply_camera_controls()
                assert controls['NoiseReductionMode'] == 1
                print("   ✓ NoiseReductionMode=1 applied to camera controls")

    def test_noise_reduction_high_quality_applied_to_hardware(self, client, app):
        """Test that NoiseReductionMode=2 (High Quality) is applied to real camera hardware"""
        print("\n🔍 Testing NoiseReductionMode=2 on hardware...")

        # Set noise reduction mode to High Quality via API
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 2})
        assert response.status_code == 200
        print("   ✓ Setting saved: noise_reduction_mode=2")

        # Get camera_streamer from app context
        with app.app_context():
            from flask import current_app
            streamer = current_app.config.get('CAMERA_STREAMER')
            assert streamer is not None

            # Reload settings to pick up the new value
            streamer.load_stream_settings()
            assert streamer.noise_reduction_mode == 2
            print("   ✓ Setting loaded into streamer")

            # Verify camera can apply noise reduction mode
            if streamer.camera:
                controls = streamer._apply_camera_controls()
                assert controls['NoiseReductionMode'] == 2
                print("   ✓ NoiseReductionMode=2 applied to camera controls")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
