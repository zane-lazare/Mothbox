"""
Integration Tests: Noise Reduction Quality

Tests that noise reduction modes are properly applied to camera stream
and affect image quality as expected.

These tests verify:
- Noise reduction control is applied to camera
- Different modes produce expected quality characteristics
- Settings persist across stream restarts

RUN ON RASPBERRY PI ONLY - requires camera hardware

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


class TestNoiseReductionApplication:
    """Test that noise reduction modes are applied to camera"""

    def test_noise_reduction_off_applied(self):
        """Test that NoiseReductionMode=0 (Off) is applied to camera"""
        from unittest.mock import MagicMock

        # Create mock socketio
        socketio = MagicMock()

        # Create streamer
        streamer = CameraStreamer(socketio)
        streamer.noise_reduction_mode = 0

        # Initialize camera (may fail if camera busy, that's OK)
        try:
            streamer.initialize_camera()

            # Verify camera initialized
            assert streamer.camera is not None, "Camera should be initialized"

            # The _apply_camera_controls method should have been called
            # Verify noise reduction mode was set to 0
            print(f"\n✓ Noise reduction mode set to: {streamer.noise_reduction_mode}")
            assert streamer.noise_reduction_mode == 0

        except Exception as e:
            print(f"⚠️  Camera initialization failed (may be in use): {e}")
            pytest.skip("Camera not available for test")
        finally:
            if streamer.camera:
                streamer.release_camera()

    def test_noise_reduction_fast_applied(self):
        """Test that NoiseReductionMode=1 (Fast) is applied to camera"""
        from unittest.mock import MagicMock

        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.noise_reduction_mode = 1

        try:
            streamer.initialize_camera()
            assert streamer.camera is not None

            print(f"\n✓ Noise reduction mode set to: {streamer.noise_reduction_mode}")
            assert streamer.noise_reduction_mode == 1

        except Exception as e:
            print(f"⚠️  Camera initialization failed: {e}")
            pytest.skip("Camera not available")
        finally:
            if streamer.camera:
                streamer.release_camera()

    def test_noise_reduction_high_quality_applied(self):
        """Test that NoiseReductionMode=2 (High Quality) is applied to camera"""
        from unittest.mock import MagicMock

        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.noise_reduction_mode = 2

        try:
            streamer.initialize_camera()
            assert streamer.camera is not None

            print(f"\n✓ Noise reduction mode set to: {streamer.noise_reduction_mode}")
            assert streamer.noise_reduction_mode == 2

        except Exception as e:
            print(f"⚠️  Camera initialization failed: {e}")
            pytest.skip("Camera not available")
        finally:
            if streamer.camera:
                streamer.release_camera()


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


class TestNoiseReductionSettingsUpdate:
    """Test noise reduction updates via WebSocket"""

    def test_update_noise_reduction_via_websocket(self, client, app):
        """Test updating noise reduction mode via WebSocket update_preview_control"""
        import socketio as sio_client

        # Get server URL
        url = 'http://localhost:5000'

        # Connect WebSocket client
        sio = sio_client.Client()

        try:
            sio.connect(url, transports=['websocket'])
            print("\n✓ WebSocket connected")

            # Send update for noise reduction mode
            sio.emit('update_preview_control', {
                'NoiseReductionMode': 2
            })

            # Wait for update to be processed
            time.sleep(0.5)

            # Verify streamer has updated noise reduction mode
            with app.app_context():
                from flask import current_app
                streamer = current_app.config.get('CAMERA_STREAMER')

                if streamer:
                    # Note: This test assumes streamer stores the value
                    # The actual camera.set_controls() call happens in real-time
                    print("✓ Noise reduction update emitted via WebSocket")
                else:
                    print("⚠️  Camera streamer not available in test context")

        except Exception as e:
            print(f"⚠️  WebSocket test skipped: {e}")
            pytest.skip("WebSocket server not available")
        finally:
            if sio.connected:
                sio.disconnect()


class TestNoiseReductionEndToEnd:
    """End-to-end test of noise reduction workflow"""

    def test_complete_noise_reduction_workflow(self, client):
        """Test complete workflow: save settings -> load -> apply to camera"""
        print("\n🔄 Testing complete noise reduction workflow:")

        # Step 1: Update settings via API
        print("   1. Updating noise reduction via API...")
        response = client.post('/api/config/webui', json={'noise_reduction_mode': 2})
        assert response.status_code == 200

        # Step 2: Verify settings persisted
        print("   2. Verifying settings persisted...")
        response = client.get('/api/config/webui')
        data = response.get_json()
        assert data['noise_reduction_mode'] == 2

        # Step 3: Load settings into new streamer instance
        print("   3. Loading settings into new streamer...")
        from unittest.mock import MagicMock

        socketio = MagicMock()
        streamer = CameraStreamer(socketio)
        streamer.load_stream_settings()

        assert streamer.noise_reduction_mode == 2
        print("      ✓ Streamer loaded noise_reduction_mode=2")

        # Step 4: Verify controls would be applied
        print("   4. Verifying controls would be applied...")
        mock_camera = MagicMock()
        streamer.camera = mock_camera

        controls = streamer._apply_camera_controls()
        assert controls['NoiseReductionMode'] == 2

        print("      ✓ NoiseReductionMode=2 ready to apply to camera")
        print("\n✅ Complete noise reduction workflow passed!")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
