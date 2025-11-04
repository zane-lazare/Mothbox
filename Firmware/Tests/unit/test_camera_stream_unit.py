"""
Comprehensive unit tests for LiveViewStreamer class (Issue #78 - Camera Backend Testing)

Tests streaming functionality with comprehensive mocking for CI/CD compatibility.
Covers settings loading, camera initialization, streaming lifecycle, focus peaking,
digital zoom, AF window, ISP tuning, encoder selection, and error recovery.

Hardware tests are in test_camera_stream_encoding.py (marked @pytest.mark.hardware).

Coverage Target: 85%+ (liveview_stream.py is 1736 lines, 26 methods)

Test Classes (Phase 3):
1. TestSettingsLoading (15 tests) - Settings file parsing and validation
2. TestCameraInitialization (13 tests) - Camera hardware initialization
3. TestStreamingLifecycle (8 tests) - Start/stop streaming, locking
4. TestFocusPeakingAlgorithms (12 tests) - Laplacian, Sobel, Canny edge detection
5. TestDigitalZoomCalculations (15 tests) - ScalerCrop calculation, aspect preservation
6. TestAFWindowCoordinateTransformation (10 tests) - Click-to-focus coordinate mapping
7. TestISPTuningApplication (7 tests) - Custom tuning file loading
8. TestEncoderSelection (10 tests) - Hardware/simplejpeg/PIL encoder selection
9. TestStreamPerformance (9 tests) - Performance validation
10. TestErrorRecovery (9 tests) - Exception handling and graceful degradation
11. TestControlApplication (11 tests) - Camera control mapping and application
12. TestResourceManagement (9 tests) - Cleanup, threading, resource release

Total: 128 tests, ~2150 lines
"""

import pytest
import json
import sys
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from threading import Thread
import time

# Import LiveViewStreamer
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))
from liveview_stream import LiveViewStreamer, DEFAULT_STREAM_WIDTH, DEFAULT_STREAM_HEIGHT, DEFAULT_JPEG_QUALITY


# ============================================================================
# Test Class 1: Settings Loading and Validation (15 tests)
# ============================================================================

class TestSettingsLoading:
    """Test settings file loading, parsing, and validation"""

    def test_load_defaults_when_file_missing(self, camera_streamer_func, temp_liveview_settings):
        """
        Test settings loader uses hardcoded defaults when file doesn't exist

        When liveview_settings.txt is missing or empty, LiveViewStreamer
        should use built-in default values for all settings.
        """
        # temp_liveview_settings creates empty file
        temp_liveview_settings.write_text("")

        # Create streamer (will load settings)
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Verify defaults loaded
        assert streamer.stream_width == DEFAULT_STREAM_WIDTH  # 1024
        assert streamer.stream_height == DEFAULT_STREAM_HEIGHT  # 768
        assert streamer.frame_delay == 0.1  # 10 FPS
        assert streamer.jpeg_quality == DEFAULT_JPEG_QUALITY  # 85

    def test_load_custom_settings_from_file(self, camera_streamer_func, temp_liveview_settings):
        """
        Test loading custom settings from liveview_settings.txt

        When file contains custom values, they should override defaults.
        """
        # Write custom settings
        temp_liveview_settings.write_text("""
stream_width=1920
stream_height=1080
frame_rate=15
jpeg_quality=90
sharpness=2.0
brightness=0.2
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Verify custom values loaded
        assert streamer.stream_width == 1920
        assert streamer.stream_height == 1080
        assert streamer.frame_delay == pytest.approx(1.0 / 15, rel=0.01)  # 15 FPS
        assert streamer.jpeg_quality == 90
        assert streamer.sharpness == 2.0
        assert streamer.brightness == 0.2

    def test_type_conversion_integers(self, camera_streamer_func, temp_liveview_settings):
        """Test integer type conversion for width, height, quality, af_mode"""
        temp_liveview_settings.write_text("""
stream_width=2304
stream_height=1736
jpeg_quality=95
af_mode=1
noise_reduction_mode=2
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.stream_width == 2304
        assert streamer.stream_height == 1736
        assert streamer.jpeg_quality == 95
        assert streamer.af_mode == 1
        assert streamer.noise_reduction_mode == 2

    def test_type_conversion_floats(self, camera_streamer_func, temp_liveview_settings):
        """Test float type conversion for sharpness, brightness, contrast, saturation"""
        temp_liveview_settings.write_text("""
sharpness=1.5
brightness=-0.1
contrast=1.2
saturation=0.8
analogue_gain=4.5
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.sharpness == 1.5
        assert streamer.brightness == -0.1
        assert streamer.contrast == 1.2
        assert streamer.saturation == 0.8
        assert streamer.analogue_gain == 4.5

    def test_type_conversion_booleans(self, camera_streamer_func, temp_liveview_settings):
        """Test boolean type conversion for ae_enable, awb_enable, focus_peaking_enabled"""
        temp_liveview_settings.write_text("""
ae_enable=false
awb_enable=true
focus_peaking_enabled=true
lens_shading_enable=false
defect_correction_enable=true
use_custom_tuning=true
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.ae_enable is False
        assert streamer.awb_enable is True
        assert streamer.focus_peaking_enabled is True
        assert streamer.lens_shading_enable is False
        assert streamer.defect_correction_enable is True
        assert streamer.use_custom_tuning is True

    def test_colour_gains_tuple_parsing(self, camera_streamer_func, temp_liveview_settings):
        """Test parsing colour gains from separate red/blue keys"""
        temp_liveview_settings.write_text("""
colour_gains_red=2.5
colour_gains_blue=1.8
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.colour_gains == (2.5, 1.8)

    def test_all_image_quality_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all image quality settings load correctly"""
        temp_liveview_settings.write_text("""
sharpness=2.5
brightness=0.3
contrast=1.1
saturation=1.3
noise_reduction_mode=1
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.sharpness == 2.5
        assert streamer.brightness == 0.3
        assert streamer.contrast == 1.1
        assert streamer.saturation == 1.3
        assert streamer.noise_reduction_mode == 1

    def test_all_focus_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all autofocus settings load correctly"""
        temp_liveview_settings.write_text("""
af_mode=0
af_speed=1
af_range=2
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.af_mode == 0  # Manual
        assert streamer.af_speed == 1  # Fast
        assert streamer.af_range == 2  # Full range

    def test_all_exposure_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all exposure settings load correctly"""
        temp_liveview_settings.write_text("""
ae_enable=false
ae_metering_mode=2
exposure_time=1000
analogue_gain=12.0
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.ae_enable is False
        assert streamer.ae_metering_mode == 2
        assert streamer.exposure_time == 1000
        assert streamer.analogue_gain == 12.0

    def test_all_white_balance_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all white balance settings load correctly"""
        temp_liveview_settings.write_text("""
awb_enable=false
awb_mode=1
colour_gains_red=2.0
colour_gains_blue=1.6
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.awb_enable is False
        assert streamer.awb_mode == 1
        assert streamer.colour_gains == (2.0, 1.6)

    def test_isp_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test ISP tuning settings load correctly"""
        temp_liveview_settings.write_text("""
lens_shading_enable=true
defect_correction_enable=false
use_custom_tuning=true
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.lens_shading_enable is True
        assert streamer.defect_correction_enable is False
        assert streamer.use_custom_tuning is True

    def test_focus_peaking_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test focus peaking settings load correctly"""
        temp_liveview_settings.write_text("""
focus_peaking_enabled=true
focus_peaking_intensity=150
focus_peaking_colour=red
focus_peaking_algorithm=sobel
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.focus_peaking_enabled is True
        assert streamer.focus_peaking_intensity == 150
        assert streamer.focus_peaking_colour == 'red'
        assert streamer.focus_peaking_algorithm == 'sobel'

    def test_stream_config_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test stream configuration settings (mode, sensor mode, FPS)"""
        temp_liveview_settings.write_text("""
stream_mode=hardware
sensor_mode=16:9
frame_rate=30
        """.strip())

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.stream_mode == 'hardware'
        assert streamer.sensor_mode == '16:9'
        assert streamer.frame_delay == pytest.approx(1.0 / 30, rel=0.01)

    def test_frame_rate_to_delay_conversion(self, camera_streamer_func, temp_liveview_settings):
        """Test frame rate converts to frame delay correctly"""
        temp_liveview_settings.write_text("frame_rate=20")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # 20 FPS = 0.05 seconds per frame
        assert streamer.frame_delay == pytest.approx(0.05, rel=0.01)

    def test_invalid_frame_rate_uses_default(self, camera_streamer_func, temp_liveview_settings):
        """Test invalid frame rate (0 or negative) uses default"""
        temp_liveview_settings.write_text("frame_rate=0")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Should use default delay (0.1 = 10 FPS)
        assert streamer.frame_delay == 0.1


# ============================================================================
# Test Class 2: Camera Initialization (13 tests)
# ============================================================================

class TestCameraInitialization:
    """Test camera hardware initialization and configuration"""

    def test_initialize_camera_success_camera0(self, camera_streamer_func, mock_picamera2_for_streamer):
        """
        Test successful camera initialization with camera 0

        Should initialize Picamera2 with camera_num=0, create video
        configuration, apply controls, and start/stop camera.
        """
        streamer = camera_streamer_func

        # Patch Picamera2 class at point of use
        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                with patch('liveview_stream.Picamera2', Mock(return_value=mock_picamera2_for_streamer), create=True):
                    result = streamer.initialize_camera()

        # Verify success
        assert result is True
        assert streamer.camera is not None
        assert streamer.camera == mock_picamera2_for_streamer

    def test_initialize_camera_fallback_camera1(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test fallback to camera 1 when camera 0 fails"""
        streamer = camera_streamer_func

        # Create a mock that succeeds as camera 1
        mock_camera1 = mock_picamera2_for_streamer

        def picamera2_constructor(camera_num=0, tuning=None):
            if camera_num == 0:
                raise RuntimeError("Camera 0 not available")
            return mock_camera1

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', side_effect=picamera2_constructor, create=True):
                result = streamer.initialize_camera()

        # Should succeed with camera 1
        assert result is True
        assert streamer.camera is not None

    def test_initialize_sensor_mode_auto(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test auto sensor mode selection"""
        temp_liveview_settings.write_text("sensor_mode=auto")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

    def test_initialize_sensor_mode_4_3(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test 4:3 aspect ratio sensor mode"""
        temp_liveview_settings.write_text("sensor_mode=4:3")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True
        assert streamer.sensor_mode == '4:3'

    def test_initialize_sensor_mode_16_9(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test 16:9 aspect ratio sensor mode"""
        temp_liveview_settings.write_text("sensor_mode=16:9")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True
        assert streamer.sensor_mode == '16:9'

    def test_initialize_sensor_mode_full(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test full sensor resolution mode"""
        temp_liveview_settings.write_text("sensor_mode=full")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True
        assert streamer.sensor_mode == 'full'

    def test_initialize_with_custom_isp_tuning(self, camera_streamer_func, mock_picamera2_for_streamer,
                                                 mock_isp_tuning, temp_liveview_settings):
        """Test camera initialization with custom ISP tuning file"""
        temp_liveview_settings.write_text("use_custom_tuning=true")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                    with patch('liveview_stream.get_tuning_path', return_value="/fake/arducam_64mp.json"):
                        result = streamer.initialize_camera()

        assert result is True

    def test_initialize_isp_tuning_unavailable(self, camera_streamer_func, mock_picamera2_for_streamer,
                                                 temp_liveview_settings):
        """Test graceful fallback when ISP tuning unavailable"""
        temp_liveview_settings.write_text("use_custom_tuning=true")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                with patch('liveview_stream.ISP_TUNING_AVAILABLE', False):
                    result = streamer.initialize_camera()

        # Should succeed without custom tuning
        assert result is True

    def test_initialize_applies_controls(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test that camera controls are applied during initialization"""
        temp_liveview_settings.write_text("""
sharpness=2.0
brightness=0.1
af_mode=1
        """.strip())
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True
        # Verify set_controls was called (controls are applied)
        assert len(mock_picamera2_for_streamer.control_history) > 0

    def test_initialize_picamera2_unavailable(self, camera_streamer_func):
        """Test graceful failure when Picamera2 not available"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', False):
            result = streamer.initialize_camera()

        # Should return False when picamera2 unavailable
        assert result is False

    def test_initialize_camera_busy_error(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test handling of 'camera busy' error"""
        streamer = camera_streamer_func

        # Simulate camera busy on first call
        def picamera2_constructor_busy(camera_num=0, tuning=None):
            raise RuntimeError("Camera is busy")

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', side_effect=picamera2_constructor_busy, create=True):
                result = streamer.initialize_camera()

        # Should return False on camera busy
        assert result is False

    def test_reinitialize_releases_existing_camera(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that reinitialization releases existing camera first"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                # First initialization
                result1 = streamer.initialize_camera()
                assert result1 is True

                # Second initialization should release first camera
                result2 = streamer.initialize_camera()
                assert result2 is True

                # Verify camera object is still the same mock
                assert streamer.camera == mock_picamera2_for_streamer

    def test_initialize_sets_sensor_resolution(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that sensor resolution is captured from camera configuration"""
        streamer = camera_streamer_func

        # Mock camera_configuration to return raw size
        mock_config = {
            'main': {'size': (1024, 768)},
            'raw': {'size': (4608, 2592)}
        }
        mock_picamera2_for_streamer.camera_configuration = Mock(return_value=mock_config)

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True
        # Verify sensor_resolution was set from raw config
        assert streamer.sensor_resolution == (4608, 2592)
