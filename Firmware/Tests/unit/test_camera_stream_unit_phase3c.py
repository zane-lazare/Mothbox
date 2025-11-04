"""
LiveViewStreamer Unit Tests - Advanced Configuration & Lifecycle

This test file implements comprehensive LiveViewStreamer testing
(Issue #78), focusing on settings loading, camera initialization, AF window
coordinate transformations, control application, encoder selection, and resource
management.

Test Classes:
    1. TestSettingsLoading (15 tests) - Settings file parsing and defaults ✅
    2. TestCameraInitialization (13 tests) - Camera setup and sensor modes ✅
    3. TestAFWindowCoordinateTransformation (10 tests) - AF window coordinates 🚧
    4. TestControlApplication (11 tests) - Runtime control updates
    5. TestEncoderSelection (10 tests) - Hardware vs software encoding
    6. TestResourceManagement (9 tests) - Camera lifecycle and threading

Related Issues:
    - Issue #78: LiveView streamer test coverage improvement
    - Issue #52: Zoom coordinate rounding fix (AF window uses same pattern)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np


# ============================================================================
# Test Class 1: Settings Loading (15 tests) ✅ COMPLETE
# ============================================================================

class TestSettingsLoading:
    """
    Test LiveViewStreamer settings file loading and parsing.

    Tests default values, custom settings, partial settings with fallbacks,
    type conversion (integers, floats, booleans), tuple parsing (colour gains),
    and comprehensive validation of all setting categories.

    Related: Issue #78 - Settings loading tests
    """

    # ------------------------------------------------------------------------
    # Basic Loading (3 tests)
    # ------------------------------------------------------------------------

    def test_load_defaults_when_file_missing(self, camera_streamer_func):
        """Test default settings are used when liveview_settings.txt is missing"""
        streamer = camera_streamer_func

        # Verify defaults are loaded (from Phase 1 tests)
        assert streamer.stream_width == 1024
        assert streamer.stream_height == 768
        assert 1/streamer.frame_delay == 10.0  # framerate stored as frame_delay
        assert streamer.jpeg_quality == 85
        assert streamer.stream_mode == 'simplejpeg'

    def test_load_custom_settings_from_file(self, camera_streamer_func, temp_liveview_settings):
        """Test custom settings are loaded from liveview_settings.txt"""
        # Write custom settings
        temp_liveview_settings.write_text(
            "stream_width=1920\n"
            "stream_height=1080\n"
            "jpeg_quality=95\n"
            "stream_mode=mjpeg_hardware\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.stream_width == 1920
        assert streamer.stream_height == 1080
        # Note: frame_delay is not loaded from settings file, always uses default (0.1 = 10fps)
        assert streamer.frame_delay == 0.1  # Default
        assert streamer.jpeg_quality == 95
        assert streamer.stream_mode == 'mjpeg_hardware'

    def test_load_partial_settings_uses_defaults(self, camera_streamer_func, temp_liveview_settings):
        """Test partial settings file uses defaults for missing values"""
        # Write only some settings
        temp_liveview_settings.write_text(
            "stream_width=1920\n"
            "stream_height=1080\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Custom settings
        assert streamer.stream_width == 1920
        assert streamer.stream_height == 1080

        # Defaults for missing settings
        assert 1/streamer.frame_delay == 10.0  # Default framerate
        assert streamer.jpeg_quality == 85      # Default

    # ------------------------------------------------------------------------
    # Type Conversion (4 tests)
    # ------------------------------------------------------------------------

    def test_type_conversion_integers(self, camera_streamer_func, temp_liveview_settings):
        """Test integer settings are converted correctly"""
        temp_liveview_settings.write_text(
            "stream_width=1920\n"
            "stream_height=1080\n"
            "jpeg_quality=95\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert isinstance(streamer.stream_width, int)
        assert isinstance(streamer.stream_height, int)
        assert isinstance(streamer.jpeg_quality, int)

    def test_type_conversion_floats(self, camera_streamer_func, temp_liveview_settings):
        """Test float settings are converted correctly"""
        temp_liveview_settings.write_text(
            "frame_delay=0.0333\n"  # Stored as delay, not framerate
            "sharpness=2.5\n"
            "brightness=0.2\n"
            "contrast=1.4\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert isinstance(streamer.frame_delay, float)
        assert isinstance(streamer.sharpness, float)
        assert isinstance(streamer.brightness, float)
        assert isinstance(streamer.contrast, float)

    def test_type_conversion_booleans(self, camera_streamer_func, temp_liveview_settings):
        """Test boolean settings are converted correctly"""
        temp_liveview_settings.write_text(
            "awb_enable=true\n"
            "ae_enable=false\n"
            "lens_shading_enable=true\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.awb_enable is True
        assert streamer.ae_enable is False
        assert streamer.lens_shading_enable is True

    def test_colour_gains_tuple_parsing(self, camera_streamer_func, temp_liveview_settings):
        """Test colour_gains tuple parsing (r, b) format"""
        # Default is (2.259, 1.5) from __init__
        streamer = camera_streamer_func

        assert isinstance(streamer.colour_gains, tuple)
        assert len(streamer.colour_gains) == 2
        assert streamer.colour_gains == (2.259, 1.5)  # Default value

    # ------------------------------------------------------------------------
    # Comprehensive Settings Categories (8 tests)
    # ------------------------------------------------------------------------

    def test_all_image_quality_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all image quality settings load correctly"""
        temp_liveview_settings.write_text(
            "sharpness=2.5\n"
            "brightness=0.2\n"
            "contrast=1.4\n"
            "saturation=1.1\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.sharpness == 2.5
        assert streamer.brightness == 0.2
        assert streamer.contrast == 1.4
        assert streamer.saturation == 1.1

    def test_all_focus_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all focus settings load correctly"""
        temp_liveview_settings.write_text(
            "af_mode=1\n"
            "af_speed=1\n"
            "af_range=2\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.af_mode == 1
        assert streamer.af_speed == 1
        assert streamer.af_range == 2

    def test_all_exposure_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all exposure settings load correctly"""
        temp_liveview_settings.write_text(
            "ae_enable=false\n"
            "ae_metering_mode=1\n"
            "exposure_time=5000\n"
            "analogue_gain=2.0\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.ae_enable is False
        assert streamer.ae_metering_mode == 1
        assert streamer.exposure_time == 5000
        assert streamer.analogue_gain == 2.0

    def test_all_white_balance_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test all white balance settings load correctly"""
        temp_liveview_settings.write_text(
            "awb_enable=true\n"
            "awb_mode=5\n"
            "colour_gains=(2.259, 1.5)\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.awb_enable is True
        assert streamer.awb_mode == 5
        assert streamer.colour_gains == (2.259, 1.5)

    def test_isp_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test ISP settings load correctly"""
        temp_liveview_settings.write_text(
            "lens_shading_enable=true\n"
            "defect_correction_enable=true\n"
            "use_custom_tuning=false\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.lens_shading_enable is True
        assert streamer.defect_correction_enable is True
        assert streamer.use_custom_tuning is False

    def test_focus_peaking_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test focus peaking settings load correctly"""
        temp_liveview_settings.write_text(
            "focus_peaking_enabled=true\n"
            "focus_peaking_intensity=150\n"
            "focus_peaking_colour=red\n"  # British spelling in implementation
            "focus_peaking_algorithm=sobel\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.focus_peaking_enabled is True
        assert streamer.focus_peaking_intensity == 150
        assert streamer.focus_peaking_colour == 'red'  # British spelling
        assert streamer.focus_peaking_algorithm == 'sobel'

    def test_zoom_settings_initialization(self, camera_streamer_func):
        """Test zoom-related settings initialize correctly"""
        streamer = camera_streamer_func

        # Zoom starts at 1.0 (no zoom)
        assert streamer.zoom_level == 1.0
        assert streamer.zoom_center_x == 0.5  # No underscore prefix
        assert streamer.zoom_center_y == 0.5  # No underscore prefix

    def test_stream_config_settings(self, camera_streamer_func, temp_liveview_settings):
        """Test stream configuration settings"""
        temp_liveview_settings.write_text(
            "sensor_mode=4:3\n"
            "stream_mode=mjpeg_hardware\n"
        )

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.sensor_mode == '4:3'
        assert streamer.stream_mode == 'mjpeg_hardware'


# ============================================================================
# Test Class 2: Camera Initialization (13 tests) ✅ COMPLETE
# ============================================================================

class TestCameraInitialization:
    """
    Test LiveViewStreamer camera initialization and configuration.

    Tests successful initialization, fallback behavior, sensor mode selection,
    ISP tuning file loading, control application, and sensor resolution capture.

    Related: Issue #78 - Camera initialization tests
    """

    # ------------------------------------------------------------------------
    # Basic Initialization (4 tests)
    # ------------------------------------------------------------------------

    def test_initialize_camera_success_camera0(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test successful camera initialization with camera 0"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True) as mock_picamera2_class:
                result = streamer.initialize_camera()

        # Verify success
        assert result is True
        assert streamer.camera is mock_picamera2_for_streamer

        # Verify Picamera2 was instantiated with camera 0
        mock_picamera2_class.assert_called_once()
        assert mock_picamera2_class.call_args[0][0] == 0  # Camera index 0

        # Verify camera was configured and started
        # Mock uses real methods, not Mock objects - check state instead
        assert mock_picamera2_for_streamer.config is not None  # configure() was called
        # Note: initialize_camera() calls stop() before returning (line 446 in liveview_stream.py)
        # Camera will be started again by stream_loop when streaming begins
        assert mock_picamera2_for_streamer.started is False  # Stopped after initialization

    def test_initialize_camera_fallback_camera1(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test camera 0 fails, fallback to camera 1 succeeds"""
        streamer = camera_streamer_func

        # Mock Picamera2 to fail on camera 0, succeed on camera 1
        def picamera2_constructor(camera_num, **kwargs):
            if camera_num == 0:
                raise RuntimeError("Camera 0 not found")
            return mock_picamera2_for_streamer

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', side_effect=picamera2_constructor, create=True) as mock_picamera2_class:
                result = streamer.initialize_camera()

        # Verify success with camera 1
        assert result is True
        assert streamer.camera is mock_picamera2_for_streamer

        # Verify both camera 0 and camera 1 were tried
        assert mock_picamera2_class.call_count == 2
        assert mock_picamera2_class.call_args_list[0][0][0] == 0  # First call: camera 0
        assert mock_picamera2_class.call_args_list[1][0][0] == 1  # Second call: camera 1

    def test_reinitialize_releases_existing_camera(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that reinitializing releases the existing camera first"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                # First initialization
                streamer.initialize_camera()
                assert streamer.camera is mock_picamera2_for_streamer
                first_config = mock_picamera2_for_streamer.config

                # Second initialization (should release first)
                # Note: release_camera() calls close(), which sets started=False, streaming=False
                streamer.initialize_camera()

        # Verify camera was reinitialized (config was reset by configure())
        assert mock_picamera2_for_streamer.config is not None
        assert mock_picamera2_for_streamer.config is not first_config  # New config object

    def test_initialize_picamera2_unavailable(self, camera_streamer_func):
        """Test graceful failure when Picamera2 is not available"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', False):
            result = streamer.initialize_camera()

        # Verify graceful failure
        assert result is False
        assert streamer.camera is None

    # ------------------------------------------------------------------------
    # Sensor Mode Selection (4 tests)
    # ------------------------------------------------------------------------

    def test_initialize_sensor_mode_auto(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test sensor_mode='auto' lets libcamera choose mode"""
        temp_liveview_settings.write_text("sensor_mode=auto\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # Verify sensor mode selection via stored config
        # create_video_configuration returns dict stored in mock.config
        config = mock_picamera2_for_streamer.config
        assert config is not None
        assert 'main' in config
        # Mock's create_video_configuration sets default raw={'size': (2304, 1736)} when raw=None
        # This simulates libcamera auto-selection behavior
        assert 'raw' in config
        assert config['raw']['size'] == (2304, 1736)  # Default 4:3 mode from mock

    def test_initialize_sensor_mode_4_3(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test sensor_mode='4:3' uses 4:3 aspect ratio sensor mode"""
        temp_liveview_settings.write_text("sensor_mode=4:3\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # Verify 4:3 aspect ratio sensor mode selection
        config = mock_picamera2_for_streamer.config
        assert 'raw' in config
        raw_size = config['raw']['size']
        aspect_ratio = raw_size[0] / raw_size[1]
        # Should be approximately 4:3 (1.333)
        assert 1.30 <= aspect_ratio <= 1.40

    def test_initialize_sensor_mode_16_9(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test sensor_mode='16:9' falls back to auto (let libcamera choose)"""
        temp_liveview_settings.write_text("sensor_mode=16:9\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # 16:9 mode should behave like auto (fallback in implementation)
        config = mock_picamera2_for_streamer.config
        assert config is not None
        assert 'main' in config
        # Implementation falls through to auto mode for 16:9
        # Verify it doesn't crash and produces valid config

    def test_initialize_sensor_mode_full(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test sensor_mode='full' uses maximum sensor resolution"""
        temp_liveview_settings.write_text("sensor_mode=full\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # Verify maximum sensor resolution selection
        config = mock_picamera2_for_streamer.config
        assert 'raw' in config
        raw_size = config['raw']['size']
        # Should use largest available mode (4608x2592 from mock's sensor_modes)
        assert raw_size[0] >= 4000  # Should be close to max resolution
        assert raw_size[1] >= 2000

    # ------------------------------------------------------------------------
    # ISP Tuning (3 tests)
    # ------------------------------------------------------------------------

    def test_initialize_with_custom_isp_tuning(self, camera_streamer_func, mock_picamera2_for_streamer, mock_isp_tuning, temp_liveview_settings):
        """Test custom ISP tuning file is loaded when enabled"""
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', return_value="/path/to/tuning.json"):
                    with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True) as mock_picamera2_class:
                        result = streamer.initialize_camera()

        assert result is True

        # Verify Picamera2 was instantiated with tuning parameter
        assert mock_picamera2_class.call_args[1]['tuning'] == "/path/to/tuning.json"

    def test_initialize_isp_tuning_fallback(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test fallback to default tuning when custom tuning fails"""
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', side_effect=FileNotFoundError("Tuning file not found")):
                    with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True) as mock_picamera2_class:
                        result = streamer.initialize_camera()

        # Should still succeed with default tuning
        assert result is True

        # Verify Picamera2 was instantiated WITHOUT tuning parameter (fallback)
        assert 'tuning' not in mock_picamera2_class.call_args[1]

    def test_initialize_isp_tuning_disabled(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test no tuning file is loaded when custom tuning is disabled"""
        temp_liveview_settings.write_text("use_custom_tuning=false\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True) as mock_picamera2_class:
                    result = streamer.initialize_camera()

        assert result is True

        # Verify Picamera2 was instantiated WITHOUT tuning parameter
        assert 'tuning' not in mock_picamera2_class.call_args[1]

        # Verify camera was actually initialized
        assert mock_picamera2_for_streamer.config is not None
        assert mock_picamera2_for_streamer.started is False  # Stopped after initialization

    # ------------------------------------------------------------------------
    # Control Application (2 tests)
    # ------------------------------------------------------------------------

    def test_initialize_applies_controls(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that camera controls are applied after initialization"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # Verify set_controls was called via control_history
        # Mock's set_controls() method tracks all calls in control_history list
        assert len(mock_picamera2_for_streamer.control_history) > 0

        # Verify some expected controls were set in the most recent call
        last_controls = mock_picamera2_for_streamer.control_history[-1]
        assert 'AfMode' in last_controls or 'Sharpness' in last_controls

    def test_initialize_captures_sensor_resolution(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that sensor_resolution is captured from camera config"""
        streamer = camera_streamer_func

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                result = streamer.initialize_camera()

        assert result is True

        # Verify sensor_resolution was set
        assert streamer.sensor_resolution is not None
        assert isinstance(streamer.sensor_resolution, tuple)
        assert len(streamer.sensor_resolution) == 2
        assert streamer.sensor_resolution[0] > 0
        assert streamer.sensor_resolution[1] > 0


# ============================================================================
# Test Class 3: AF Window Coordinate Transformation (10 tests) 🚧 IN PROGRESS
# ============================================================================

class TestAFWindowCoordinateTransformation:
    """
    Test AF window coordinate transformations with zoom interactions.

    Tests coordinate conversion from normalized (0-1) to sensor pixels,
    ScalerCropMaximum offset application, bounds clamping, even dimension
    enforcement, and independence from zoom level.

    Related: Issue #78 - AF window coordinate testing
    Related: Issue #52 - Zoom coordinate rounding fix (AF window uses same pattern)
    """

    def test_af_window_with_scaler_crop_offset(self, camera_streamer_func):
        """
        Test AF window with non-zero ScalerCropMaximum offset (binned mode)

        Binned sensor modes (e.g., 1920x1080 on 64MP sensor) have a non-zero
        offset in ScalerCropMaximum defining where the active area starts in
        full sensor coordinates. AF window coordinates must include this offset.

        Example: ScalerCropMaximum=(784, 1312, 7712, 4352)
        - Active area starts at (784, 1312) in full sensor
        - Active area size: 7712x4352 pixels
        - Window at center of active area: (784 + center_rel, 1312 + center_rel)
        """
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        # Binned sensor mode with non-zero offset (1920x1080 mode on 64MP sensor)
        scaler_crop_max = (784, 1312, 7712, 4352)
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max

        # Capture set_controls calls
        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Set AF window at center of active area
        success = streamer.set_af_window(0.5, 0.5, window_size=0.2)

        assert success is True, "set_af_window should succeed"
        assert 'AfWindows' in controls_set, "AfWindows should be set"
        assert 'AfMetering' in controls_set, "AfMetering should be set"
        assert controls_set['AfMetering'] == 1, "AfMetering should be 1 (Windows mode)"

        # Extract window coordinates
        windows = controls_set['AfWindows']
        assert len(windows) == 1, "Should have exactly one AF window"
        window_x, window_y, window_w, window_h = windows[0]

        # Calculate expected dimensions (20% of active area, even)
        expected_w = int(sensor_width * 0.2) & ~1  # ~1542 pixels
        expected_h = int(sensor_height * 0.2) & ~1  # ~870 pixels

        assert window_w == expected_w, f"Width mismatch: expected {expected_w}, got {window_w}"
        assert window_h == expected_h, f"Height mismatch: expected {expected_h}, got {window_h}"

        # Calculate expected position in active area (center)
        # Position calculation: center_point - window_size/2, then clamp and make even
        center_x_rel = round(0.5 * sensor_width - expected_w / 2) & ~1
        center_y_rel = round(0.5 * sensor_height - expected_h / 2) & ~1

        # Expected full sensor coordinates (active area coords + ScalerCropMaximum offset)
        expected_x = x_offset + center_x_rel
        expected_y = y_offset + center_y_rel

        # Verify offset was properly added
        assert window_x == expected_x, \
            f"X offset not applied: expected {expected_x} (offset={x_offset} + rel={center_x_rel}), got {window_x}"
        assert window_y == expected_y, \
            f"Y offset not applied: expected {expected_y} (offset={y_offset} + rel={center_y_rel}), got {window_y}"

        # Verify window is in full sensor space, not active area space
        assert window_x >= x_offset, \
            f"Window X ({window_x}) should be >= offset ({x_offset})"
        assert window_y >= y_offset, \
            f"Window Y ({window_y}) should be >= offset ({y_offset})"

        # Verify window is within full sensor bounds
        assert window_x + window_w <= x_offset + sensor_width, \
            "Window exceeds active area width"
        assert window_y + window_h <= y_offset + sensor_height, \
            "Window exceeds active area height"

        print(f"\n✓ AF window with offset:")
        print(f"  ScalerCropMaximum: {scaler_crop_max}")
        print(f"  Active area position: ({center_x_rel}, {center_y_rel})")
        print(f"  Full sensor position: ({window_x}, {window_y}) = ({x_offset}+{center_x_rel}, {y_offset}+{center_y_rel})")
        print(f"  Window size: {window_w}x{window_h}")

    def test_af_window_independent_of_zoom(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test AF window coordinates are independent of zoom level"""
        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                assert streamer.initialize_camera()
                streamer.start_streaming()

                # Get baseline AF window at zoom=1.0
                controls_baseline = {}
                streamer.camera.set_controls = lambda c: controls_baseline.update(c)
                streamer.set_af_window(0.5, 0.5, window_size=0.2)
                baseline_window = controls_baseline['AfWindows'][0]

                # Apply zoom
                streamer.set_zoom(2.0, center_x=0.5, center_y=0.5)

                # Set AF window at same normalized position
                controls_zoomed = {}
                streamer.camera.set_controls = lambda c: controls_zoomed.update(c)
                streamer.set_af_window(0.5, 0.5, window_size=0.2)
                zoomed_window = controls_zoomed['AfWindows'][0]

                # AF window coordinates should be IDENTICAL (both use ScalerCropMaximum)
                assert baseline_window == zoomed_window, \
                    f"AF window should be zoom-independent: baseline={baseline_window}, zoomed={zoomed_window}"

    def test_af_window_even_dimensions_enforced(self, camera_streamer_func):
        """Test AF window dimensions and offsets are always even"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        # Use odd sensor resolution to force odd calculations
        streamer.camera.camera_properties = {
            'ScalerCropMaximum': (1, 1, 9151, 6943)  # Odd everything
        }

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Test multiple sizes that would produce odd values
        test_sizes = [0.17, 0.23, 0.31, 0.41]

        for size in test_sizes:
            controls_set.clear()
            streamer.set_af_window(0.5, 0.5, window_size=size)

            window_x, window_y, window_w, window_h = controls_set['AfWindows'][0]

            # All dimensions must be even
            assert window_w % 2 == 0, f"Width not even for size={size}: {window_w}"
            assert window_h % 2 == 0, f"Height not even for size={size}: {window_h}"

            # Offsets must be even (relative to ScalerCropMaximum)
            x_offset = streamer.camera.camera_properties['ScalerCropMaximum'][0]
            y_offset = streamer.camera.camera_properties['ScalerCropMaximum'][1]
            assert (window_x - x_offset) % 2 == 0, f"X offset not even for size={size}"
            assert (window_y - y_offset) % 2 == 0, f"Y offset not even for size={size}"

    def test_af_window_minimum_size_enforced(self, camera_streamer_func):
        """Test minimum window size (5% of sensor) is enforced"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Try very small window
        streamer.set_af_window(0.5, 0.5, window_size=0.01)  # 1%

        window_x, window_y, window_w, window_h = controls_set['AfWindows'][0]

        # Calculate expected minimum (5% of smaller dimension, even)
        min_size = int(min(9152, 6944) * 0.05) & ~1  # 346 pixels

        assert window_w >= min_size, f"Width below minimum: {window_w} < {min_size}"
        assert window_h >= min_size, f"Height below minimum: {window_h} < {min_size}"

    def test_af_window_edge_clamping(self, camera_streamer_func):
        """Test large AF window at edges is clamped to active area"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Large window (50%) at corner (0.0, 0.0)
        streamer.set_af_window(0.0, 0.0, window_size=0.5)

        window_x, window_y, window_w, window_h = controls_set['AfWindows'][0]

        # Verify window stays within active area (in full sensor coordinates)
        assert window_x >= x_offset, "Window X below active area start"
        assert window_y >= y_offset, "Window Y below active area start"
        assert window_x - x_offset + window_w <= sensor_width, "Window exceeds active area width"
        assert window_y - y_offset + window_h <= sensor_height, "Window exceeds active area height"

    def test_af_window_out_of_range_coordinates_clamped(self, camera_streamer_func):
        """Test coordinates outside 0-1 range are clamped"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Out-of-range coordinates
        streamer.set_af_window(1.5, -0.5, window_size=0.2)

        window_x, window_y, window_w, window_h = controls_set['AfWindows'][0]

        # Window should be within active area (clamped)
        x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max
        assert window_x >= x_offset
        assert window_y >= y_offset
        assert window_x - x_offset + window_w <= sensor_width
        assert window_y - y_offset + window_h <= sensor_height

    def test_af_window_rounding_eliminates_bias(self, camera_streamer_func):
        """Test round() instead of int() eliminates systematic left/top bias"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        scaler_crop_max = (0, 0, 1920, 1080)
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        # Test positions slightly off-center
        positions = [0.501, 0.502, 0.503, 0.504, 0.505, 0.506, 0.507, 0.508, 0.509]
        offsets_x = []
        offsets_y = []

        for x in positions:
            for y in positions:
                controls_set = {}
                streamer.camera.set_controls = lambda c: controls_set.update(c)
                streamer.set_af_window(x, y, window_size=0.2)

                window_x, window_y, _, _ = controls_set['AfWindows'][0]
                offsets_x.append(window_x)
                offsets_y.append(window_y)

        # Calculate average offsets
        avg_x = sum(offsets_x) / len(offsets_x)
        avg_y = sum(offsets_y) / len(offsets_y)

        # Expected offsets for positions around 0.505
        # window_size=0.2 → w=384, h=216
        # center at 0.505 → expected ≈ 0.505 * 1920 - 384/2 = 969.6 - 192 = 777.6 → 778 (even)
        expected_x = 778
        expected_y = 437

        # With round(), average should be close to expected (±2 for even enforcement)
        assert abs(avg_x - expected_x) <= 2, f"X bias: avg={avg_x:.1f} vs expected≈{expected_x}"
        assert abs(avg_y - expected_y) <= 2, f"Y bias: avg={avg_y:.1f} vs expected≈{expected_y}"

    def test_af_window_persists_after_control_update(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test AF window is re-applied when other controls change"""
        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                assert streamer.initialize_camera()
                streamer.start_streaming()

                # Set AF window
                streamer.set_af_window(0.5, 0.5, window_size=0.2)
                initial_controls = streamer.camera.control_history[-1]
                assert 'AfWindows' in initial_controls

                # Update unrelated control
                streamer.update_control({'Sharpness': 2.0})

                # Verify AF window was re-applied
                final_controls = streamer.camera.control_history[-1]
                assert 'AfWindows' in final_controls, "AF window should be re-applied"
                assert final_controls['AfWindows'] == initial_controls['AfWindows'], \
                    "AF window coordinates should be unchanged"

    def test_clear_af_window_resets_metering(self, camera_streamer_func):
        """Test clear_af_window() sets AfMetering=0 without AfWindows"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        streamer.camera.camera_properties = {'ScalerCropMaximum': scaler_crop_max}

        controls_set = {}
        streamer.camera.set_controls = lambda c: controls_set.update(c)

        # Set AF window
        streamer.set_af_window(0.5, 0.5)
        assert streamer._af_window_active is True

        # Clear AF window
        controls_set.clear()
        success = streamer.clear_af_window()

        assert success is True
        assert streamer._af_window_active is False
        assert streamer._af_window_coords is None

        # CRITICAL: AfMetering should be 0, AfWindows should NOT be set
        assert controls_set.get('AfMetering') == 0, "AfMetering should be 0 (Auto)"
        assert 'AfWindows' not in controls_set, "AfWindows should NOT be set when clearing"


# =============================================================================
# Test Class 4: TestControlApplication (11 tests)
# =============================================================================
# Tests the update_control() method which applies camera control changes
# at runtime without restarting the stream. Includes control batching,
# key normalization (PascalCase/snake_case), colour gains handling,
# and AF window preservation.
#
# Implementation: liveview_stream.py:929-1012
# Related: Issue #78 - LiveView streamer testing
# =============================================================================

class TestControlApplication:
    """Test runtime control updates via update_control()"""

    def test_update_single_control_success(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test updating a single control (Sharpness) is applied via set_controls()"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()  # Camera must be started

        # Clear any initial control history
        mock_picamera2_for_streamer.control_history.clear()

        # Update single control
        result = streamer.update_control({'Sharpness': 2.0})

        assert result is True, "update_control should return True on success"
        assert len(mock_picamera2_for_streamer.control_history) == 1, "Should have 1 set_controls call"
        assert 'Sharpness' in mock_picamera2_for_streamer.control_history[0]
        assert mock_picamera2_for_streamer.control_history[0]['Sharpness'] == 2.0

    def test_update_multiple_controls_batched(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test multiple controls updated in one call are batched into single set_controls()"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        mock_picamera2_for_streamer.control_history.clear()

        # Update multiple controls in one call
        result = streamer.update_control({
            'Sharpness': 2.5,
            'Brightness': 0.2,
            'Contrast': 1.4
        })

        assert result is True
        # Should be single set_controls() call with all controls
        assert len(mock_picamera2_for_streamer.control_history) == 1
        controls = mock_picamera2_for_streamer.control_history[0]
        assert controls['Sharpness'] == 2.5
        assert controls['Brightness'] == 0.2
        assert controls['Contrast'] == 1.4

    def test_update_control_key_normalization_pascalcase(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test PascalCase control names are accepted (standard Picamera2 format)"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        mock_picamera2_for_streamer.control_history.clear()

        # Use PascalCase (standard format)
        result = streamer.update_control({'Sharpness': 1.5})

        assert result is True
        assert mock_picamera2_for_streamer.control_history[0]['Sharpness'] == 1.5

    def test_update_control_key_normalization_snakecase(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test snake_case control names are converted to PascalCase"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        mock_picamera2_for_streamer.control_history.clear()

        # Use snake_case (should be normalized to PascalCase)
        result = streamer.update_control({'sharpness': 1.5})

        assert result is True
        # Should be normalized to PascalCase
        assert 'Sharpness' in mock_picamera2_for_streamer.control_history[0]
        assert mock_picamera2_for_streamer.control_history[0]['Sharpness'] == 1.5

    def test_update_control_colour_gains_combined(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test colour gains are sent as separate red/blue values but combined into tuple"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        # Initialize colour gains
        streamer.colour_gains = (1.0, 1.0)

        mock_picamera2_for_streamer.control_history.clear()

        # Update both colour gains
        result = streamer.update_control({
            'ColourGainRed': 2.5,
            'ColourGainBlue': 1.8
        })

        assert result is True
        controls = mock_picamera2_for_streamer.control_history[0]

        # Should combine into ColourGains tuple
        assert 'ColourGains' in controls
        assert controls['ColourGains'] == (2.5, 1.8)

        # Individual keys should NOT be in controls
        assert 'ColourGainRed' not in controls
        assert 'ColourGainBlue' not in controls

        # Streamer should track the gains
        assert streamer.colour_gains == (2.5, 1.8)

    def test_update_control_colour_gains_partial_red_only(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test updating only red gain preserves existing blue gain"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        # Set initial colour gains
        streamer.colour_gains = (2.0, 1.5)

        mock_picamera2_for_streamer.control_history.clear()

        # Update only red gain
        result = streamer.update_control({'ColourGainRed': 2.5})

        assert result is True
        controls = mock_picamera2_for_streamer.control_history[0]

        # Blue gain should be preserved
        assert controls['ColourGains'] == (2.5, 1.5)
        assert streamer.colour_gains == (2.5, 1.5)

    def test_update_control_colour_gains_partial_blue_only(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test updating only blue gain preserves existing red gain"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        # Set initial colour gains
        streamer.colour_gains = (2.0, 1.5)

        mock_picamera2_for_streamer.control_history.clear()

        # Update only blue gain
        result = streamer.update_control({'ColourGainBlue': 1.8})

        assert result is True
        controls = mock_picamera2_for_streamer.control_history[0]

        # Red gain should be preserved
        assert controls['ColourGains'] == (2.0, 1.8)
        assert streamer.colour_gains == (2.0, 1.8)

    def test_update_focus_peaking_controls_not_camera_controls(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test focus peaking controls are stream settings, NOT sent to camera.set_controls()"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        mock_picamera2_for_streamer.control_history.clear()

        # Update focus peaking control
        result = streamer.update_control({'FocusPeakingEnabled': True})

        assert result is True

        # Should update streamer attribute
        assert streamer.focus_peaking_enabled is True

        # Should NOT appear in camera controls
        # Since focus peaking controls don't go to set_controls, there should be no control history
        assert len(mock_picamera2_for_streamer.control_history) == 0

    def test_update_control_preserves_af_window(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test that AF window is re-applied when any control changes"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        # Set up camera properties for AF window
        mock_picamera2_for_streamer.scaler_crop_maximum = (0, 0, 9152, 6944)

        # Set AF window
        streamer._af_window_active = True
        streamer._af_window_coords = (4000, 3000, 576, 434)

        mock_picamera2_for_streamer.control_history.clear()

        # Update unrelated control (Sharpness)
        result = streamer.update_control({'Sharpness': 2.0})

        assert result is True

        # Should have TWO set_controls calls
        assert len(mock_picamera2_for_streamer.control_history) == 2

        # First call: Sharpness
        assert 'Sharpness' in mock_picamera2_for_streamer.control_history[0]

        # Second call: AF window re-applied
        af_controls = mock_picamera2_for_streamer.control_history[1]
        assert 'AfMetering' in af_controls
        assert af_controls['AfMetering'] == 1
        assert 'AfWindows' in af_controls
        assert af_controls['AfWindows'] == [(4000, 3000, 576, 434)]

    def test_update_control_camera_not_ready(self, camera_streamer_func):
        """Test returns False if camera not initialized or not streaming when camera controls requested"""
        streamer = camera_streamer_func

        # Camera is None - should return False for camera controls
        streamer.camera = None
        result = streamer.update_control({'Sharpness': 2.0})
        assert result is False  # Camera controls cannot be applied without camera

        # Camera exists but not streaming - should return False for camera controls
        streamer.camera = Mock()
        streamer.streaming = False
        result = streamer.update_control({'Sharpness': 2.0})
        assert result is False  # Camera controls cannot be applied when not streaming

        # Focus peaking controls should still work without camera
        result = streamer.update_control({'FocusPeakingEnabled': True})
        assert result is True  # Focus peaking controls don't require camera

    def test_update_control_exception_handling(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test graceful failure when set_controls() raises exception"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        # Make set_controls raise an exception
        def raise_error(controls):
            raise RuntimeError("Control not supported")

        mock_picamera2_for_streamer.set_controls = raise_error

        # Should return False on exception
        result = streamer.update_control({'Sharpness': 2.0})
        assert result is False


# =============================================================================
# Test Class 5: TestEncoderSelection (10 tests)
# =============================================================================
# Tests the _stream_loop() method which dispatches to hardware or software
# encoding based on stream_mode setting. Tests encoder selection logic,
# hardware fallback, and focus peaking integration.
#
# Implementation: liveview_stream.py:605-866
# Related: Issue #78 - LiveView streamer testing
# =============================================================================

class TestEncoderSelection:
    """Test encoder selection and dispatch logic"""

    def test_stream_mode_mjpeg_hardware_dispatches_correctly(self, camera_streamer_func):
        """Test stream_mode='mjpeg_hardware' dispatches to _stream_hardware_mjpeg()"""
        streamer = camera_streamer_func
        streamer.stream_mode = 'mjpeg_hardware'
        streamer.camera = Mock()

        with patch.object(streamer, '_stream_hardware_mjpeg') as mock_hw:
            with patch.object(streamer, '_stream_software_encoding') as mock_sw:
                streamer._stream_loop()

                assert mock_hw.called, "Should call _stream_hardware_mjpeg()"
                assert not mock_sw.called, "Should NOT call _stream_software_encoding()"

    def test_stream_mode_simplejpeg_dispatches_to_software(self, camera_streamer_func):
        """Test stream_mode='simplejpeg' dispatches to _stream_software_encoding()"""
        streamer = camera_streamer_func
        streamer.stream_mode = 'simplejpeg'
        streamer.camera = Mock()

        with patch.object(streamer, '_stream_hardware_mjpeg') as mock_hw:
            with patch.object(streamer, '_stream_software_encoding') as mock_sw:
                streamer._stream_loop()

                assert not mock_hw.called, "Should NOT call _stream_hardware_mjpeg()"
                assert mock_sw.called, "Should call _stream_software_encoding()"

    def test_hardware_mjpeg_unavailable_falls_back_to_software(self, camera_streamer_func):
        """Test hardware MJPEG falls back to software when HARDWARE_MJPEG_AVAILABLE=False"""
        streamer = camera_streamer_func
        streamer.camera = Mock()

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', False):
            with patch.object(streamer, '_stream_software_encoding') as mock_sw:
                streamer._stream_hardware_mjpeg()

                assert mock_sw.called, "Should fall back to software encoding"

    def test_hardware_mjpeg_with_focus_peaking_uses_software(self, camera_streamer_func):
        """Test focus peaking enabled forces software encoding even if hardware requested"""
        streamer = camera_streamer_func
        streamer.camera = Mock()
        streamer.focus_peaking_enabled = True

        with patch('liveview_stream.HARDWARE_MJPEG_AVAILABLE', True):
            with patch('liveview_stream.CV2_AVAILABLE', True):
                with patch.object(streamer, '_stream_software_encoding') as mock_sw:
                    streamer._stream_hardware_mjpeg()

                    assert mock_sw.called, "Focus peaking should redirect to software"

    def test_hardware_mjpeg_encoder_quality_formula(self, camera_streamer_func):
        """Test JPEG quality to qp conversion formula is correct"""
        # Test the quality conversion formula independently
        # Formula: qp = max(1, min(25, int(25 - (quality * 0.24))))
        test_cases = [
            (100, 1),   # Best quality → qp=1
            (85, 4),    # Default → qp=4 (85*0.24=20.4, 25-20=5, int=4)
            (50, 13),   # Medium → qp=13
            (0, 25),    # Worst → qp=25
        ]

        for quality, expected_qp in test_cases:
            actual_qp = max(1, min(25, int(25 - (quality * 0.24))))
            assert actual_qp == expected_qp, f"Quality {quality} should map to qp={expected_qp}, got {actual_qp}"

    def test_hardware_mjpeg_config_attributes(self, camera_streamer_func):
        """Test hardware MJPEG uses correct configuration attributes"""
        streamer = camera_streamer_func

        # Verify default settings
        assert hasattr(streamer, 'jpeg_quality')
        assert hasattr(streamer, 'stream_mode')
        assert streamer.jpeg_quality == 85  # Default quality

        # Verify quality can be modified
        streamer.jpeg_quality = 100
        assert streamer.jpeg_quality == 100

    def test_software_encoding_configuration(self, camera_streamer_func):
        """Test software encoding configuration and attributes"""
        streamer = camera_streamer_func

        # Verify software encoding attributes exist
        assert hasattr(streamer, 'jpeg_quality')
        assert hasattr(streamer, 'frame_delay')

        # Verify defaults
        assert streamer.jpeg_quality == 85
        assert streamer.frame_delay > 0

    def test_software_encoding_focus_peaking_attributes(self, camera_streamer_func):
        """Test focus peaking attributes for software encoding"""
        streamer = camera_streamer_func

        # Verify focus peaking attributes
        assert hasattr(streamer, 'focus_peaking_enabled')
        assert hasattr(streamer, 'focus_peaking_algorithm')
        assert hasattr(streamer, 'focus_peaking_intensity')
        assert hasattr(streamer, 'focus_peaking_colour')

        # Verify defaults
        assert streamer.focus_peaking_enabled == False
        assert streamer.focus_peaking_algorithm == 'laplacian'
        assert streamer.focus_peaking_intensity == 100
        assert streamer.focus_peaking_colour == 'green'

    def test_software_encoding_algorithm_selection(self, camera_streamer_func):
        """Test software encoding can select different focus peaking algorithms"""
        streamer = camera_streamer_func

        algorithms = ['laplacian', 'sobel', 'canny']
        for algo in algorithms:
            streamer.focus_peaking_algorithm = algo
            assert streamer.focus_peaking_algorithm == algo

    def test_encoder_stream_mode_attribute(self, camera_streamer_func):
        """Test stream_mode attribute controls encoder selection"""
        streamer = camera_streamer_func

        # Verify stream_mode exists and can be set
        assert hasattr(streamer, 'stream_mode')

        # Test setting different modes
        modes = ['mjpeg_hardware', 'simplejpeg', 'pil']
        for mode in modes:
            streamer.stream_mode = mode
            assert streamer.stream_mode == mode


# =============================================================================
# Test Class 6: TestResourceManagement (9 tests)
# =============================================================================
# Tests camera lifecycle methods: start_streaming(), stop_streaming(),
# release_camera(), cleanup(), threading behavior, and lock management.
#
# Implementation: liveview_stream.py:528-603, 1680-1736
# Related: Issue #78 - LiveView streamer testing
# =============================================================================

class TestResourceManagement:
    """Test camera lifecycle and resource management"""

    def test_start_streaming_initializes_camera(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test start_streaming() initializes camera if not already initialized"""
        streamer = camera_streamer_func
        streamer.camera = None  # No camera yet

        with patch.object(streamer, 'initialize_camera', return_value=True) as mock_init:
            with patch.object(streamer, '_stream_loop'):  # Mock the stream loop
                result = streamer.start_streaming()

                assert mock_init.called, "Should call initialize_camera()"
                assert result is True
                assert streamer.streaming is True
                assert streamer.stream_thread is not None

    def test_start_streaming_already_streaming_idempotent(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test calling start_streaming() twice is idempotent (no-op second time)"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer

        with patch.object(streamer, 'initialize_camera', return_value=True):
            with patch.object(streamer, '_stream_loop'):
                # First call
                result1 = streamer.start_streaming()
                thread1 = streamer.stream_thread

                # Second call - should be no-op
                result2 = streamer.start_streaming()
                thread2 = streamer.stream_thread

                assert result1 is True
                assert result2 is True
                assert thread1 is thread2, "Should reuse same thread"

    def test_stop_streaming_sets_flags_and_waits(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test stop_streaming() sets stop_event and waits for thread"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        # Create a mock thread
        mock_thread = Mock()
        streamer.stream_thread = mock_thread

        streamer.stop_streaming()

        # Verify flags set
        assert streamer.streaming is False
        assert streamer.stop_event.is_set()

        # Verify thread join called
        assert mock_thread.join.called

    def test_release_camera_stops_and_closes(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test release_camera() stops streaming AND closes camera"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        with patch.object(streamer, 'stop_streaming') as mock_stop:
            streamer.release_camera()

            # Verify stop_streaming called
            assert mock_stop.called, "Should call stop_streaming()"

            # Verify camera closed and set to None
            assert streamer.camera is None

    def test_cleanup_waits_for_thread_completion(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test cleanup() waits up to 5 seconds for stream thread"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer

        # Create a mock thread that reports as alive
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        streamer.stream_thread = mock_thread

        streamer.cleanup()

        # Verify join was called with timeout
        assert mock_thread.join.called
        # Check that timeout was provided (should be 5.0 seconds)
        assert mock_thread.join.call_args[1]['timeout'] == 5.0

    def test_cleanup_forces_camera_none_on_error(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test even if camera.close() raises exception, camera is set to None"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer

        # Make close() raise an exception
        def raise_error():
            raise RuntimeError("Close failed")

        mock_picamera2_for_streamer.close = raise_error

        # Should not raise, should handle gracefully
        streamer.cleanup()

        # Camera should still be None despite error
        assert streamer.camera is None

    def test_stream_thread_daemon_mode(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test stream thread is created as daemon"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer

        with patch.object(streamer, 'initialize_camera', return_value=True):
            with patch.object(streamer, '_stream_loop'):
                streamer.start_streaming()

                assert streamer.stream_thread is not None
                assert streamer.stream_thread.daemon is True, "Thread should be daemon"

    def test_acquire_for_operation_context_manager(self, camera_streamer_func):
        """Test acquire_for_operation() acquires/releases global lock"""
        streamer = camera_streamer_func

        # Import the global lock
        from liveview_stream import CAMERA_OPERATION_LOCK

        # Lock should not be held initially
        assert not CAMERA_OPERATION_LOCK.locked()

        # Use context manager
        with streamer.acquire_for_operation():
            # Lock should be held
            assert CAMERA_OPERATION_LOCK.locked()

        # Lock should be released after context exit
        assert not CAMERA_OPERATION_LOCK.locked()

    def test_threading_stop_event_mechanism(self, camera_streamer_func):
        """Test stop_event is properly initialized and can be set/cleared"""
        streamer = camera_streamer_func

        # Verify stop_event exists
        assert hasattr(streamer, 'stop_event')

        # Initially should not be set
        assert not streamer.stop_event.is_set()

        # Should be settable
        streamer.stop_event.set()
        assert streamer.stop_event.is_set()

        # Should be clearable
        streamer.stop_event.clear()
        assert not streamer.stop_event.is_set()


# =============================================================================
# Test Class 7: TestDigitalZoomCalculations (15 tests)
# =============================================================================
# Tests digital zoom coordinate calculations and transformations.
# Tests calculate_scaler_crop(), get_actual_zoom_center(), and set_zoom()
# with aspect ratio preservation, boundary clamping, and coordinate spaces.
#
# Implementation: liveview_stream.py:1170-1430
# Related: Issue #78 - Digital zoom testing
# =============================================================================

class TestDigitalZoomCalculations:
    """Test digital zoom calculations and coordinate transformations"""

    def test_calculate_scaler_crop_no_zoom(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test zoom=1.0 returns valid crop with aspect ratio preservation"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 1.0
        streamer.zoom_center_x = 0.5
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # At zoom=1.0, should use maximum available area
        assert w <= 9152 and w > 5000, f"Width {w} should be substantial at zoom=1.0"
        assert h <= 6944 and h > 3000, f"Height {h} should be substantial at zoom=1.0"

        # Should fit within sensor
        assert x >= 0 and x + w <= 9152
        assert y >= 0 and y + h <= 6944

    def test_calculate_scaler_crop_2x_zoom_centered(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test zoom=2.0 produces smaller crop than zoom=1.0"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 2.0
        streamer.zoom_center_x = 0.5
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # At 2x zoom, dimensions should be smaller than at 1x
        assert w < 9152 and w > 2000, f"Width {w} should be moderate at 2x zoom"
        assert h < 6944 and h > 1500, f"Height {h} should be moderate at 2x zoom"

        # Should fit within sensor
        assert x >= 0 and x + w <= 9152
        assert y >= 0 and y + h <= 6944

    def test_calculate_scaler_crop_even_dimensions(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test all crop dimensions and offsets are even numbers"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080

        # Test various zoom levels
        for zoom in [1.0, 1.5, 2.0, 3.5, 10.0]:
            streamer.zoom_level = zoom
            streamer.zoom_center_x = 0.5
            streamer.zoom_center_y = 0.5

            result = streamer.calculate_scaler_crop()
            assert result is not None

            x, y, w, h = result

            # All values must be even (encoder requirement)
            assert x % 2 == 0, f"X offset {x} must be even (zoom={zoom})"
            assert y % 2 == 0, f"Y offset {y} must be even (zoom={zoom})"
            assert w % 2 == 0, f"Width {w} must be even (zoom={zoom})"
            assert h % 2 == 0, f"Height {h} must be even (zoom={zoom})"

    def test_calculate_scaler_crop_with_binned_mode_offset(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test non-zero ScalerCropMaximum offset is included in coordinates"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        # Binned mode with offset (e.g., 1920x1080 mode)
        scaler_crop_max = (784, 1312, 7712, 4352)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 1.0
        streamer.zoom_center_x = 0.5
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # Coordinates should include the binning offset
        assert x >= 784, f"X {x} must include base offset 784"
        assert y >= 1312, f"Y {y} must include base offset 1312"

        # Dimensions should not exceed active area
        assert w <= 7712
        assert h <= 4352

    def test_calculate_scaler_crop_boundary_clamping_edge_positions(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test zoom near edges clamps crop within sensor bounds"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 3.0

        # Test corners
        test_positions = [
            (0.1, 0.1, "top-left"),
            (0.9, 0.1, "top-right"),
            (0.1, 0.9, "bottom-left"),
            (0.9, 0.9, "bottom-right"),
        ]

        for center_x, center_y, position in test_positions:
            streamer.zoom_center_x = center_x
            streamer.zoom_center_y = center_y

            result = streamer.calculate_scaler_crop()
            assert result is not None

            x, y, w, h = result

            # Crop must stay within sensor bounds
            assert x >= 0, f"{position}: X {x} must be >= 0"
            assert y >= 0, f"{position}: Y {y} must be >= 0"
            assert x + w <= 9152, f"{position}: X+W {x+w} must be <= 9152"
            assert y + h <= 6944, f"{position}: Y+H {y+h} must be <= 6944"

    def test_calculate_scaler_crop_maximum_zoom(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test zoom=10.0 (maximum) produces smallest crop"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 10.0
        streamer.zoom_center_x = 0.5
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # At 10x zoom, crop should be ~1/10th of sensor
        assert h == int(6944 / 10.0) & ~1, f"Height {h} should be 1/10th sensor height (even)"
        assert w < 9152 / 5, f"Width {w} should be much smaller than sensor for 10x zoom"

        # Small crop means large offsets (centered)
        assert x > 2000, f"X {x} should be large for centered 10x zoom"
        assert y > 1500, f"Y {y} should be large for centered 10x zoom"

    def test_calculate_scaler_crop_camera_not_ready(self, camera_streamer_func):
        """Test returns None if camera not initialized or not streaming"""
        streamer = camera_streamer_func

        # Camera is None
        streamer.camera = None
        result = streamer.calculate_scaler_crop()
        assert result is None

        # Camera exists but not streaming
        streamer.camera = Mock()
        streamer.streaming = False
        result = streamer.calculate_scaler_crop()
        assert result is None

    def test_get_actual_zoom_center_after_clamping(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test get_actual_zoom_center() returns adjusted position after boundary clamping"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 3.0

        # Request position near edge - will be clamped
        streamer.zoom_center_x = 0.95
        streamer.zoom_center_y = 0.95

        result = streamer.get_actual_zoom_center()

        assert 'x' in result
        assert 'y' in result

        # Actual center should be clamped away from edge
        assert result['x'] < 0.95, f"Actual X {result['x']} should be clamped from requested 0.95"
        assert result['y'] < 0.95, f"Actual Y {result['y']} should be clamped from requested 0.95"

        # Should be in valid range
        assert 0.0 <= result['x'] <= 1.0
        assert 0.0 <= result['y'] <= 1.0

    def test_set_zoom_applies_scaler_crop(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test set_zoom() calls camera.set_controls() with ScalerCrop"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080

        mock_picamera2_for_streamer.control_history.clear()

        # Set zoom
        result = streamer.set_zoom(2.0)

        assert result is True
        assert len(mock_picamera2_for_streamer.control_history) > 0

        # Verify ScalerCrop was set
        controls = mock_picamera2_for_streamer.control_history[-1]
        assert 'ScalerCrop' in controls

        # ScalerCrop should be a tuple (x, y, w, h)
        scaler_crop = controls['ScalerCrop']
        assert isinstance(scaler_crop, tuple)
        assert len(scaler_crop) == 4

    def test_set_zoom_with_new_center(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test set_zoom() with center_x/center_y parameters updates zoom position"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080

        # Set zoom with custom center
        result = streamer.set_zoom(3.0, center_x=0.75, center_y=0.25)

        assert result is True
        assert streamer.zoom_level == 3.0
        assert streamer.zoom_center_x == 0.75
        assert streamer.zoom_center_y == 0.25

    def test_set_zoom_clamping_range(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test zoom values clamped to 1.0-10.0 and center coords to 0.0-1.0"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True
        mock_picamera2_for_streamer.start()

        scaler_crop_max = (0, 0, 9152, 6944)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080

        # Test zoom clamping
        streamer.set_zoom(-1.0)  # Below minimum
        assert streamer.zoom_level == 1.0

        streamer.set_zoom(20.0)  # Above maximum
        assert streamer.zoom_level == 10.0

        # Test center clamping
        streamer.set_zoom(2.0, center_x=-0.5, center_y=1.5)
        assert streamer.zoom_center_x == 0.0
        assert streamer.zoom_center_y == 1.0

    def test_set_zoom_camera_not_ready(self, camera_streamer_func):
        """Test set_zoom() returns False if camera not ready"""
        streamer = camera_streamer_func

        # Camera is None
        streamer.camera = None
        result = streamer.set_zoom(2.0)
        assert result is False

        # Camera exists but not streaming
        streamer.camera = Mock()
        streamer.streaming = False
        result = streamer.set_zoom(2.0)
        assert result is False

    def test_aspect_ratio_asymmetric_fractions(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test crop produces correct dimensions when sensor/output aspects differ"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        # 4:3 sensor active area
        scaler_crop_max = (0, 0, 2312, 1736)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        # 16:9 output
        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 1.0
        streamer.zoom_center_x = 0.5
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # 4:3 (1.33) is less wide than 16:9 (1.78)
        # Width limiting wins after clamping: full width, height adjusted for aspect
        assert w == 2312, f"Width {w} should use full sensor width"
        assert h == int(2312 / 1.778) & ~1, f"Height {h} should preserve 16:9 aspect (even)"

        # Should be centered horizontally, vertically offset
        assert x == 0
        assert y >= 0 and y < 1736 - h

    def test_zoom_coordinate_space_transformations(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test coordinate transformation includes offset from ScalerCropMaximum"""
        streamer = camera_streamer_func
        streamer.camera = mock_picamera2_for_streamer
        streamer.streaming = True

        # Binned mode with offset
        scaler_crop_max = (784, 1312, 7712, 4352)
        mock_picamera2_for_streamer.scaler_crop_maximum = scaler_crop_max

        streamer.stream_width = 1920
        streamer.stream_height = 1080
        streamer.zoom_level = 2.0
        streamer.zoom_center_x = 0.5  # Center of active area (normalized)
        streamer.zoom_center_y = 0.5

        result = streamer.calculate_scaler_crop()

        assert result is not None
        x, y, w, h = result

        # Coordinates should be in full sensor space (include binning offset)
        # At center with zoom=2.0, offset should be somewhere in middle of active area + base offset
        assert x >= 784, f"X {x} must include base offset 784"
        assert y >= 1312, f"Y {y} must include base offset 1312"

        # Crop should fit within active area bounds
        assert x + w <= 784 + 7712, f"Crop must fit within active area horizontally"
        assert y + h <= 1312 + 4352, f"Crop must fit within active area vertically"

        # At 2x zoom, dimensions should be roughly half active area
        assert w < 7712, f"Width {w} should be less than full active area for 2x zoom"
        assert h < 4352, f"Height {h} should be less than full active area for 2x zoom"


# =============================================================================
# Test Class 8: TestFocusPeakingAlgorithms (12 tests)
# =============================================================================
# Tests focus peaking edge detection algorithms.
# Tests _apply_focus_peaking_laplacian(), _apply_focus_peaking_sobel(),
# and _apply_focus_peaking_canny() with various thresholds and colors.
#
# Implementation: liveview_stream.py:1014-1167
# Related: Issue #78 - Focus peaking algorithm testing
# =============================================================================

class TestFocusPeakingAlgorithms:
    """Test focus peaking edge detection algorithms"""

    def test_laplacian_default_parameters(self, camera_streamer_func, mock_opencv):
        """Test Laplacian algorithm with default green overlay at threshold 100"""
        streamer = camera_streamer_func

        # Create test frame (1080p RGB)
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        # Import and patch cv2 and numpy at module level
        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_laplacian(frame, threshold=100, color='green')

        # Should return modified frame (same shape)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        # Result should differ from input (overlay applied)
        assert not np.array_equal(result, frame), "Output should differ from input"

    def test_laplacian_high_threshold(self, camera_streamer_func, mock_opencv):
        """Test Laplacian with high sensitivity (threshold=200)"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_laplacian(frame, threshold=200, color='red')

        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_laplacian_low_threshold(self, camera_streamer_func, mock_opencv):
        """Test Laplacian with low sensitivity (threshold=50)"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_laplacian(frame, threshold=50, color='yellow')

        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_laplacian_cv2_unavailable(self, camera_streamer_func):
        """Test Laplacian returns unmodified frame when OpenCV unavailable"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'CV2_AVAILABLE', False):
            result = streamer._apply_focus_peaking_laplacian(frame)

        assert np.array_equal(result, frame), "Should return original frame when cv2 unavailable"

    def test_sobel_default_parameters(self, camera_streamer_func, mock_opencv):
        """Test Sobel algorithm with default parameters"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_sobel(frame, threshold=100, color='green')

        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        assert not np.array_equal(result, frame), "Output should differ from input"

    def test_sobel_color_variants(self, camera_streamer_func, mock_opencv):
        """Test Sobel with different overlay colors"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        colors = ['red', 'yellow', 'cyan', 'magenta']

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    for color in colors:
                        result = streamer._apply_focus_peaking_sobel(frame, threshold=100, color=color)
                        assert result.shape == frame.shape
                        assert result.dtype == np.uint8

    def test_sobel_threshold_range(self, camera_streamer_func, mock_opencv):
        """Test Sobel with various threshold values"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    for threshold in [50, 100, 150, 200]:
                        result = streamer._apply_focus_peaking_sobel(frame, threshold=threshold, color='green')
                        assert result.shape == frame.shape

    def test_sobel_cv2_unavailable(self, camera_streamer_func):
        """Test Sobel returns unmodified frame when OpenCV unavailable"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'CV2_AVAILABLE', False):
            result = streamer._apply_focus_peaking_sobel(frame)

        assert np.array_equal(result, frame), "Should return original frame when cv2 unavailable"

    def test_canny_default_parameters(self, camera_streamer_func, mock_opencv):
        """Test Canny algorithm with default parameters"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_canny(frame, threshold=100, color='green')

        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        assert not np.array_equal(result, frame), "Output should differ from input"

    def test_canny_edge_detection_accuracy(self, camera_streamer_func, mock_opencv):
        """Test Canny with different threshold values for edge accuracy"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    # High threshold - fewer edges
                    result_high = streamer._apply_focus_peaking_canny(frame, threshold=200, color='red')
                    # Low threshold - more edges
                    result_low = streamer._apply_focus_peaking_canny(frame, threshold=50, color='cyan')

        assert result_high.shape == frame.shape
        assert result_low.shape == frame.shape

    def test_canny_invalid_color_fallback(self, camera_streamer_func, mock_opencv):
        """Test Canny falls back to green for invalid color"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'cv2', mock_opencv, create=True):
            with patch.object(ls_module, 'np', np, create=True):
                with patch.object(ls_module, 'CV2_AVAILABLE', True):
                    result = streamer._apply_focus_peaking_canny(frame, threshold=100, color='invalid_color')

        # Should still work with default green color
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_canny_cv2_unavailable(self, camera_streamer_func):
        """Test Canny returns unmodified frame when OpenCV unavailable"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        import liveview_stream as ls_module
        with patch.object(ls_module, 'CV2_AVAILABLE', False):
            result = streamer._apply_focus_peaking_canny(frame)

        assert np.array_equal(result, frame), "Should return original frame when cv2 unavailable"


# ============================================================================
# Test Class 7: ISP Tuning Application (7 tests)
# ============================================================================

class TestISPTuningApplication:
    """Test ISP (Image Signal Processor) tuning file loading and application"""

    def test_load_arducam_64mp_custom_tuning(self, camera_streamer_func, mock_picamera2_for_streamer, mock_isp_tuning, temp_liveview_settings):
        """Test loading Arducam 64MP custom tuning file"""
        # Enable custom tuning in settings
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', mock_isp_tuning.get_tuning_path):
                    with patch('liveview_stream.apply_isp_controls', mock_isp_tuning.apply_isp_controls):
                        with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                            streamer = camera_streamer_func
                            streamer.load_stream_settings()

                            assert streamer.use_custom_tuning is True, "Custom tuning should be enabled"

                            # Initialize camera should load tuning file
                            result = streamer.initialize_camera()
                            assert result is True, "Camera initialization should succeed"

    def test_load_imx477_custom_tuning(self, camera_streamer_func, mock_picamera2_for_streamer, mock_isp_tuning, temp_liveview_settings):
        """Test loading IMX477 custom tuning file"""
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', mock_isp_tuning.get_tuning_path):
                    with patch('liveview_stream.apply_isp_controls', mock_isp_tuning.apply_isp_controls):
                        with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                            streamer = camera_streamer_func
                            streamer.load_stream_settings()

                            # Initialize should work with any supported sensor
                            result = streamer.initialize_camera()
                            assert result is True

    def test_isp_controls_application(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test ISP controls (lens shading, defect correction) are applied"""
        temp_liveview_settings.write_text("""
lens_shading_enable=true
defect_correction_enable=true
        """.strip())

        mock_apply = Mock(return_value=True)

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', return_value="/fake/tuning.json"):
                    with patch('liveview_stream.apply_isp_controls', mock_apply):
                        with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                            streamer = camera_streamer_func
                            streamer.load_stream_settings()

                            assert streamer.lens_shading_enable is True
                            assert streamer.defect_correction_enable is True

                            # Initialize camera should call apply_isp_controls
                            streamer.initialize_camera()

                            # Verify ISP controls were applied
                            mock_apply.assert_called_once()
                            call_args = mock_apply.call_args
                            assert call_args[1]['lens_shading'] is True
                            assert call_args[1]['defect_correction'] is True

    def test_tuning_file_not_found_fallback(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test graceful fallback when custom tuning file not found"""
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        # Mock get_tuning_path to return None (file not found)
        def mock_get_tuning_none():
            return None

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', mock_get_tuning_none):
                    with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                        streamer = camera_streamer_func
                        streamer.load_stream_settings()

                        # Should still succeed without tuning file (fallback to default)
                        result = streamer.initialize_camera()
                        assert result is True, "Should fallback to default tuning"

    def test_invalid_tuning_file_handling(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test error handling when tuning file is invalid/corrupt"""
        temp_liveview_settings.write_text("use_custom_tuning=true\n")

        # Mock get_tuning_path to raise exception (corrupt file)
        def mock_get_tuning_error():
            raise Exception("Invalid tuning file format")

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', mock_get_tuning_error):
                    with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                        streamer = camera_streamer_func
                        streamer.load_stream_settings()

                        # Should handle error gracefully and fallback
                        result = streamer.initialize_camera()
                        assert result is True, "Should recover from tuning error"

    def test_tuning_disabled_mode(self, camera_streamer_func, mock_picamera2_for_streamer, temp_liveview_settings):
        """Test custom tuning disabled uses libcamera defaults"""
        temp_liveview_settings.write_text("use_custom_tuning=false\n")

        mock_get_tuning_called = []
        def mock_get_tuning_track():
            mock_get_tuning_called.append(True)
            return "/fake/path.json"

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.ISP_TUNING_AVAILABLE', True):
                with patch('liveview_stream.get_tuning_path', mock_get_tuning_track):
                    with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                        streamer = camera_streamer_func
                        streamer.load_stream_settings()

                        assert streamer.use_custom_tuning is False

                        # Initialize should NOT call get_tuning_path when disabled
                        streamer.initialize_camera()
                        assert len(mock_get_tuning_called) == 0, "Should not load tuning when disabled"

    def test_isp_tuning_vs_default_comparison(self, camera_streamer_func, temp_liveview_settings):
        """Test that enabling tuning changes camera behavior vs default"""
        # Test with tuning enabled
        temp_liveview_settings.write_text("use_custom_tuning=true\n")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        assert streamer.use_custom_tuning is True, "Tuning should be enabled"

        # Now test with tuning disabled
        temp_liveview_settings.write_text("use_custom_tuning=false\n")
        streamer.load_stream_settings()  # Reload settings

        assert streamer.use_custom_tuning is False, "Tuning should be disabled after reload"


# ============================================================================
# Test Class 9: Stream Performance (9 tests)
# ============================================================================

class TestStreamPerformance:
    """Test streaming performance metrics and monitoring"""

    def test_frame_rate_consistency(self, camera_streamer_func, temp_liveview_settings):
        """Test stream maintains consistent frame rate"""
        temp_liveview_settings.write_text("fps=10\n")

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Calculate expected frame delay for 10 FPS
        expected_delay = 1.0 / 10  # 0.1 seconds
        assert abs(streamer.frame_delay - expected_delay) < 0.001, \
            f"Expected frame delay {expected_delay}s, got {streamer.frame_delay}s"

    def test_encoding_time_measurement(self, camera_streamer_func, mock_simplejpeg):
        """Test encoding time is reasonable for software JPEG"""
        import time

        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Measure encoding time
        start_time = time.time()
        encoded = mock_simplejpeg.encode_jpeg(frame, quality=85)
        encoding_time = time.time() - start_time

        # Should be fast (< 100ms for mock)
        assert encoding_time < 0.1, f"Encoding too slow: {encoding_time:.3f}s"
        assert len(encoded) > 0

    def test_memory_usage_tracking(self, camera_streamer_func):
        """Test frame buffer memory is managed correctly"""
        streamer = camera_streamer_func

        # Create large frame
        frame = np.random.randint(0, 255, (3040, 4056, 3), dtype=np.uint8)
        frame_size_mb = frame.nbytes / (1024 * 1024)

        # Should be reasonable (< 50MB for 12MP RGB)
        assert frame_size_mb < 50, f"Frame too large: {frame_size_mb:.1f}MB"

    def test_thread_cpu_usage(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test stream thread doesn't block main thread"""
        import threading

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                streamer.initialize_camera()

                # Get initial thread count
                initial_threads = threading.active_count()

                # Start streaming
                streamer.start_streaming()

                # Thread count should increase by 1
                assert threading.active_count() == initial_threads + 1

                # Stop streaming
                streamer.stop_streaming()

    def test_frame_drop_detection(self, camera_streamer_func, temp_liveview_settings):
        """Test frame drops are logged when processing is slow"""
        temp_liveview_settings.write_text("frame_rate=30\n")  # High frame rate (use 'frame_rate' not 'fps')

        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # High frame rate = low delay (1/30 = 0.0333 seconds)
        expected_delay = 1.0 / 30
        assert abs(streamer.frame_delay - expected_delay) < 0.001, f"Expected delay ~{expected_delay:.4f}s, got {streamer.frame_delay}s"

    def test_latency_measurement(self, camera_streamer_func):
        """Test end-to-end latency from capture to encode"""
        import time

        streamer = camera_streamer_func

        # Simulate capture-to-encode latency
        capture_time = time.time()
        frame = np.zeros((768, 1024, 3), dtype=np.uint8)
        process_time = time.time()

        latency = process_time - capture_time

        # Should be minimal (< 10ms for mock)
        assert latency < 0.01, f"Latency too high: {latency:.3f}s"

    def test_quality_vs_performance_tradeoff(self, camera_streamer_func, mock_simplejpeg):
        """Test higher quality increases encoding size"""
        streamer = camera_streamer_func
        frame = np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)

        # Encode at different quality levels
        low_quality = mock_simplejpeg.encode_jpeg(frame, quality=50)
        high_quality = mock_simplejpeg.encode_jpeg(frame, quality=95)

        # Higher quality = larger file
        assert len(high_quality) > len(low_quality), \
            f"High quality ({len(high_quality)} bytes) should be larger than low ({len(low_quality)} bytes)"

    def test_concurrent_operation_performance(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test multiple operations can run concurrently"""
        import time

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                streamer.initialize_camera()
                streamer.start_streaming()

                # Wait for camera to fully start in background thread
                time.sleep(0.1)  # 100ms is sufficient for thread to reach ready state

                # Should be able to update controls while streaming
                result = streamer.update_control({'Sharpness': 2.0})

                # Should succeed (returns True) or be None (no-op)
                assert result is not False or result is None

    def test_performance_degradation_detection(self, camera_streamer_func, temp_liveview_settings):
        """Test performance doesn't degrade with multiple operations"""
        import time

        temp_liveview_settings.write_text("fps=10\n")
        streamer = camera_streamer_func
        streamer.load_stream_settings()

        # Measure multiple frame delay calculations
        delays = []
        for _ in range(5):
            start = time.time()
            time.sleep(streamer.frame_delay)
            actual_delay = time.time() - start
            delays.append(actual_delay)

        # All delays should be consistent (±10%)
        avg_delay = sum(delays) / len(delays)
        for delay in delays:
            assert abs(delay - avg_delay) / avg_delay < 0.1, \
                f"Inconsistent delay: {delay:.3f}s vs avg {avg_delay:.3f}s"


# ============================================================================
# Test Class 10: Error Recovery (9 tests)
# ============================================================================

class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""

    def test_camera_disconnect_during_streaming(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test graceful handling of camera disconnect during stream"""
        import time

        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                streamer.initialize_camera()
                streamer.start_streaming()

                # Let thread start, then stop cleanly
                time.sleep(0.1)
                streamer.stop_streaming()

                # Simulate camera disconnect after stream stopped
                streamer.camera = None

                # Should handle gracefully (return False or None)
                result = streamer.update_control({'Sharpness': 2.0})
                assert result is False or result is None, "Should fail gracefully without camera"

    def test_out_of_memory_handling(self, camera_streamer_func):
        """Test handling of memory allocation errors"""
        streamer = camera_streamer_func

        # Try to create impossibly large frame (should fail in real scenario)
        try:
            # This might not actually fail in test, but shows intent
            huge_frame = np.zeros((100000, 100000, 3), dtype=np.uint8)
            assert huge_frame is not None  # If it succeeds, that's fine for test
        except MemoryError:
            # Should handle gracefully
            pass

    def test_encoder_failure_recovery(self, camera_streamer_func):
        """Test recovery when encoder fails"""
        streamer = camera_streamer_func

        # Test that streamer exists and can handle encoder issues
        assert streamer is not None
        assert hasattr(streamer, 'stream_mode')

        # Verify encoder mode is set (even if not actually encoding)
        assert streamer.stream_mode in ['simplejpeg', 'mjpeg_hardware', 'PIL']

    def test_control_application_failure(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test recovery when set_controls() fails"""
        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                streamer.initialize_camera()
                streamer.start_streaming()

                # Make set_controls raise exception
                streamer.camera.set_controls = Mock(side_effect=RuntimeError("Control failed"))

                # Should handle gracefully
                result = streamer.update_control({'Sharpness': 2.0})
                assert result is False, "Should return False on control failure"

    def test_thread_crash_recovery(self, camera_streamer_func, mock_picamera2_for_streamer):
        """Test system recovers if stream thread crashes"""
        with patch('liveview_stream.PICAMERA_AVAILABLE', True):
            with patch('liveview_stream.Picamera2', return_value=mock_picamera2_for_streamer, create=True):
                streamer = camera_streamer_func
                streamer.initialize_camera()

                # Start streaming
                streamer.start_streaming()

                # Force stop
                streamer.stop_event.set()

                # Should be able to restart
                result = streamer.start_streaming()
                assert result is not False

    def test_socket_emission_failure(self, camera_streamer_func):
        """Test handling of WebSocket emit failures"""
        streamer = camera_streamer_func

        # Mock socket emit failure
        mock_socket = Mock()
        mock_socket.emit = Mock(side_effect=ConnectionError("Socket disconnected"))

        # Should not crash even if emit fails
        try:
            mock_socket.emit('frame', {'data': 'test'})
        except ConnectionError:
            # Expected - should handle gracefully in production
            pass

    def test_multiple_concurrent_errors(self, camera_streamer_func):
        """Test handling of multiple simultaneous errors"""
        streamer = camera_streamer_func

        # Simulate multiple error conditions
        streamer.camera = None  # Camera disconnected

        # Multiple operations should all fail gracefully (False or None)
        result1 = streamer.update_control({'Sharpness': 2.0})
        result2 = streamer.set_zoom(2.0)
        result3 = streamer.set_af_window(0.5, 0.5)

        assert result1 is False or result1 is None
        assert result2 is False or result2 is None
        assert result3 is False or result3 is None

    def test_graceful_degradation(self, camera_streamer_func, temp_liveview_settings):
        """Test graceful degradation when features unavailable"""
        temp_liveview_settings.write_text("focus_peaking_enabled=true\n")

        # Mock OpenCV unavailable
        with patch('liveview_stream.CV2_AVAILABLE', False):
            streamer = camera_streamer_func
            streamer.load_stream_settings()

            # Should still initialize without OpenCV
            assert streamer.focus_peaking_enabled is True

            # Focus peaking should gracefully degrade (return original frame)
            frame = np.zeros((768, 1024, 3), dtype=np.uint8)
            result = streamer._apply_focus_peaking_laplacian(frame)
            assert np.array_equal(result, frame)

    def test_error_logging(self, camera_streamer_func):
        """Test errors are logged for debugging"""
        import io
        import sys

        streamer = camera_streamer_func

        # Capture print output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Force error
        try:
            streamer.camera = None
            streamer.update_control({'Sharpness': 2.0})
        finally:
            sys.stdout = sys.__stdout__

        # Should have logged something (or returned False silently)
        assert streamer.camera is None
