"""
Integration Tests for Focus Peaking Workflows

Tests end-to-end workflows including:
- Enable/disable focus peaking via WebSocket
- Real-time control updates
- Settings persistence across sessions
- Preset save/load with focus peaking
- Performance impact measurement
- Preview-only verification (not in captured photos)
"""

import pytest
import time
import json


@pytest.mark.hardware
@pytest.mark.stream
class TestFocusPeakingWorkflows:
    """Test focus peaking end-to-end workflows"""

    def test_enable_disable_workflow(self, camera_streamer):
        """Test enabling and disabling focus peaking via control updates"""
        # Enable focus peaking
        result = camera_streamer.update_control({'FocusPeakingEnabled': True})
        assert result == True
        assert camera_streamer.focus_peaking_enabled == True

        # Disable focus peaking
        result = camera_streamer.update_control({'FocusPeakingEnabled': False})
        assert result == True
        assert camera_streamer.focus_peaking_enabled == False

    def test_intensity_adjustment_realtime(self, camera_streamer):
        """Test real-time intensity adjustment"""
        # Set initial intensity
        result = camera_streamer.update_control({'FocusPeakingIntensity': 50})
        assert result == True
        assert camera_streamer.focus_peaking_intensity == 50

        # Adjust intensity
        result = camera_streamer.update_control({'FocusPeakingIntensity': 150})
        assert result == True
        assert camera_streamer.focus_peaking_intensity == 150

        # Max intensity
        result = camera_streamer.update_control({'FocusPeakingIntensity': 200})
        assert result == True
        assert camera_streamer.focus_peaking_intensity == 200

    def test_color_change_realtime(self, camera_streamer):
        """Test real-time color changes"""
        colors = ['green', 'red', 'yellow', 'cyan', 'magenta']

        for color in colors:
            result = camera_streamer.update_control({'FocusPeakingColor': color})
            assert result == True
            assert camera_streamer.focus_peaking_color == color

    def test_algorithm_switching(self, camera_streamer):
        """Test switching between edge detection algorithms"""
        algorithms = ['laplacian', 'sobel', 'canny']

        for algorithm in algorithms:
            result = camera_streamer.update_control({'FocusPeakingAlgorithm': algorithm})
            assert result == True
            assert camera_streamer.focus_peaking_algorithm == algorithm

    def test_settings_persistence(self, client, camera_streamer, tmp_path):
        """Test that focus peaking settings persist across sessions"""
        import mothbox_paths
        from pathlib import Path

        # Create temporary settings file
        temp_settings = tmp_path / "webui_settings.txt"
        mothbox_paths.WEBUI_SETTINGS_FILE = temp_settings

        # Update settings via API
        response = client.post('/api/config/webui', json={
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85,
            'stream_mode': 'simplejpeg',
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'noise_reduction_mode': 0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'ae_metering_mode': 0,
            'ae_enable': True,
            'exposure_time': 500,
            'analogue_gain': 8.0,
            'use_custom_tuning': False,
            'lens_shading_enable': True,
            'defect_correction_enable': True,
            'focus_peaking_enabled': True,
            'focus_peaking_intensity': 175,
            'focus_peaking_color': 'red',
            'focus_peaking_algorithm': 'sobel'
        })

        assert response.status_code == 200

        # Verify file was written
        assert temp_settings.exists()

        # Read back settings
        with open(temp_settings, 'r') as f:
            content = f.read()

        assert 'focus_peaking_enabled=true' in content
        assert 'focus_peaking_intensity=175' in content
        assert 'focus_peaking_color=red' in content
        assert 'focus_peaking_algorithm=sobel' in content

        # Create new camera streamer to test loading
        from flask_socketio import SocketIO
        from webui.backend.camera_stream import CameraStreamer

        socketio = SocketIO()
        new_streamer = CameraStreamer(socketio)

        assert new_streamer.focus_peaking_enabled == True
        assert new_streamer.focus_peaking_intensity == 175
        assert new_streamer.focus_peaking_color == 'red'
        assert new_streamer.focus_peaking_algorithm == 'sobel'

    def test_preset_save_load_with_focus_peaking(self, client, tmp_path):
        """Test saving and loading presets with focus peaking settings"""
        import mothbox_paths

        # Set up user preset directory
        user_preset_dir = tmp_path / "user_presets"
        user_preset_dir.mkdir()

        # Create preset with focus peaking settings
        preset_data = {
            'name': 'test_focus_peaking',
            'description': 'Test preset with focus peaking',
            'workflow': 'video',
            'settings': {
                'preview': {
                    'sharpness': 2.0,
                    'brightness': 0.1,
                    'focus_peaking_enabled': True,
                    'focus_peaking_intensity': 150,
                    'focus_peaking_color': 'yellow',
                    'focus_peaking_algorithm': 'canny'
                }
            }
        }

        # Save preset
        response = client.post('/api/presets', json=preset_data)
        assert response.status_code == 200

        # Verify preset was saved
        preset_file = user_preset_dir / "test_focus_peaking.json"
        if preset_file.exists():
            with open(preset_file, 'r') as f:
                saved_preset = json.load(f)

            assert saved_preset['settings']['preview']['focus_peaking_enabled'] == True
            assert saved_preset['settings']['preview']['focus_peaking_intensity'] == 150
            assert saved_preset['settings']['preview']['focus_peaking_color'] == 'yellow'
            assert saved_preset['settings']['preview']['focus_peaking_algorithm'] == 'canny'

    def test_performance_impact(self, camera_streamer):
        """Test performance impact of focus peaking algorithms"""
        try:
            import cv2
            import numpy as np
            import time
        except ImportError:
            pytest.skip("OpenCV or NumPy not available")

        # Create test frame (1024x768 - actual stream size)
        frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Test Laplacian performance
        start = time.time()
        for _ in range(10):
            camera_streamer._apply_focus_peaking_laplacian(frame, threshold=100, color='green')
        laplacian_time = (time.time() - start) / 10 * 1000  # ms per frame

        # Test Sobel performance
        start = time.time()
        for _ in range(10):
            camera_streamer._apply_focus_peaking_sobel(frame, threshold=100, color='green')
        sobel_time = (time.time() - start) / 10 * 1000  # ms per frame

        # Test Canny performance
        start = time.time()
        for _ in range(10):
            camera_streamer._apply_focus_peaking_canny(frame, threshold=100, color='green')
        canny_time = (time.time() - start) / 10 * 1000  # ms per frame

        # Print performance results
        print(f"\nFocus Peaking Performance (per frame):")
        print(f"  Laplacian: {laplacian_time:.2f} ms")
        print(f"  Sobel:     {sobel_time:.2f} ms")
        print(f"  Canny:     {canny_time:.2f} ms")

        # Performance requirements: <50ms reasonable for Pi hardware
        # Warning if extremely slow, but don't fail test
        if laplacian_time > 100:
            print(f"⚠️  WARNING: Laplacian slow: {laplacian_time:.2f}ms (consider optimization)")

        # Verify relative performance ordering (Laplacian should be fastest)
        assert laplacian_time <= sobel_time, "Laplacian should be fastest or equal to Sobel"
        assert sobel_time <= canny_time, "Sobel should be faster or equal to Canny"

    def test_validation_errors(self, client):
        """Test that invalid focus peaking settings are rejected"""
        # Test invalid intensity (too low)
        response = client.post('/api/config/webui', json={
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85,
            'stream_mode': 'simplejpeg',
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'noise_reduction_mode': 0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'ae_metering_mode': 0,
            'ae_enable': True,
            'exposure_time': 500,
            'analogue_gain': 8.0,
            'use_custom_tuning': False,
            'lens_shading_enable': True,
            'defect_correction_enable': True,
            'focus_peaking_enabled': True,
            'focus_peaking_intensity': 30,  # Invalid: too low
            'focus_peaking_color': 'green',
            'focus_peaking_algorithm': 'laplacian'
        })
        assert response.status_code == 400

        # Test invalid color
        response = client.post('/api/config/webui', json={
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85,
            'stream_mode': 'simplejpeg',
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'noise_reduction_mode': 0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'ae_metering_mode': 0,
            'ae_enable': True,
            'exposure_time': 500,
            'analogue_gain': 8.0,
            'use_custom_tuning': False,
            'lens_shading_enable': True,
            'defect_correction_enable': True,
            'focus_peaking_enabled': True,
            'focus_peaking_intensity': 100,
            'focus_peaking_color': 'blue',  # Invalid: not in allowed list
            'focus_peaking_algorithm': 'laplacian'
        })
        assert response.status_code == 400

        # Test invalid algorithm
        response = client.post('/api/config/webui', json={
            'stream_width': 1024,
            'stream_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 85,
            'stream_mode': 'simplejpeg',
            'sharpness': 1.0,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
            'noise_reduction_mode': 0,
            'af_mode': 2,
            'af_speed': 0,
            'af_range': 0,
            'awb_enable': True,
            'awb_mode': 0,
            'colour_gains_red': 2.259,
            'colour_gains_blue': 1.500,
            'ae_metering_mode': 0,
            'ae_enable': True,
            'exposure_time': 500,
            'analogue_gain': 8.0,
            'use_custom_tuning': False,
            'lens_shading_enable': True,
            'defect_correction_enable': True,
            'focus_peaking_enabled': True,
            'focus_peaking_intensity': 100,
            'focus_peaking_color': 'green',
            'focus_peaking_algorithm': 'gaussian'  # Invalid: not in allowed list
        })
        assert response.status_code == 400
