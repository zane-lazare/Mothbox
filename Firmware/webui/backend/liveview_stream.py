"""
Live view streaming module for WebSocket camera feed
"""

import base64
import io
import time
from contextlib import contextmanager
from threading import Event, Lock, Thread

# Lazy import PIL - only needed when actually encoding images
# This allows tests to import this module without PIL installed
PIL_Image = None


def _get_pil_image():
    global PIL_Image
    if PIL_Image is None:
        try:
            from PIL import Image as PIL_Image_module

            PIL_Image = PIL_Image_module
        except ImportError as err:
            raise ImportError(
                "PIL/Pillow is required for image encoding but not installed"
            ) from err
    return PIL_Image


# Setup path for mothbox imports
import mothbox_paths
from mothbox_paths import get_control_values

# Import ISP tuning loader
try:
    from tuning_loader import apply_isp_controls, get_tuning_path

    ISP_TUNING_AVAILABLE = True
except ImportError:
    ISP_TUNING_AVAILABLE = False
    print("Warning: ISP tuning loader not available")

# Import camera control mapping
from camera_control_mapping import (
    build_picamera_controls,
    handle_colour_gains,
    normalize_control_key,
)

try:
    from picamera2 import Picamera2
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput

    PICAMERA_AVAILABLE = True
    HARDWARE_MJPEG_AVAILABLE = True
except (ImportError, RuntimeError):
    PICAMERA_AVAILABLE = False
    HARDWARE_MJPEG_AVAILABLE = False
    print("Warning: picamera2 not available - camera preview disabled")

# Try to import simplejpeg for fast JPEG encoding (5-7x faster than PIL)
try:
    import simplejpeg

    SIMPLEJPEG_AVAILABLE = True
    print("✓ simplejpeg available for fast JPEG encoding")
except ImportError:
    SIMPLEJPEG_AVAILABLE = False
    print("⚠ simplejpeg not available - using PIL (slower)")

# Try to import OpenCV for focus peaking overlay
try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
    print("✓ OpenCV available for focus peaking")
except ImportError:
    CV2_AVAILABLE = False
    print("⚠ OpenCV not available - focus peaking disabled")

# Default camera stream configuration constants
DEFAULT_STREAM_WIDTH = 1024
DEFAULT_STREAM_HEIGHT = 768
DEFAULT_STREAM_FORMAT = "BGR888"  # BGR888 produces true RGB order for correct colors
DEFAULT_FRAME_DELAY = 0.1  # seconds (10 fps)
DEFAULT_JPEG_QUALITY = 85  # Balanced quality - faster encoding, smaller files

# Global lock to prevent concurrent camera operations (autofocus, calibration, etc.)
# Picamera2 enforces exclusive hardware access - only one instance can exist at a time
CAMERA_OPERATION_LOCK = Lock()


class LiveViewStreamer:
    """Handles live view camera streaming via WebSocket"""

    def __init__(self, socketio):
        self.socketio = socketio
        self.camera = None
        self.streaming = False
        self.stream_thread = None
        self.stop_event = Event()
        self._cached_lens_position = None  # Cache lens position from streaming metadata
        self.load_stream_settings()

    def load_stream_settings(self):
        """Load stream settings from configuration file"""
        self.stream_width = DEFAULT_STREAM_WIDTH
        self.stream_height = DEFAULT_STREAM_HEIGHT
        self.stream_format = DEFAULT_STREAM_FORMAT
        self.frame_delay = DEFAULT_FRAME_DELAY
        self.jpeg_quality = DEFAULT_JPEG_QUALITY
        self.stream_mode = "simplejpeg"  # Default: fast software encoding
        self.sensor_mode = "auto"  # auto, 4:3, 16:9, full - controls field of view

        # Image quality controls
        self.sharpness = 1.0
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0

        # Noise reduction control
        self.noise_reduction_mode = 0  # 0=Off, 1=Fast, 2=High Quality

        # Focus controls
        self.af_mode = 2  # Continuous autofocus by default
        self.af_speed = 0  # Normal speed
        self.af_range = 0  # Normal range

        # Exposure controls
        self.ae_enable = True  # Auto exposure enabled by default
        self.ae_metering_mode = 0  # Centre-weighted by default
        self.exposure_time = 500  # Microseconds (for manual mode)
        self.analogue_gain = 8.0  # ISO gain (for manual mode)

        # White balance controls
        self.awb_enable = True
        self.awb_mode = 0  # Auto
        # ColourGains: Fixed gains for LED illumination (from TakePhoto.py calibration)
        # Important: These values lock down colour balance under white LED flash
        self.colour_gains = (2.259, 1.500)  # (red, blue)

        # Digital zoom / ROI controls
        self.zoom_level = 1.0  # 1.0 = no zoom, 4.0 = 4x zoom
        self.zoom_center_x = 0.5  # Normalized 0-1, 0.5 = center
        self.zoom_center_y = 0.5  # Normalized 0-1, 0.5 = center
        self.sensor_resolution = None  # Will be set after camera initialization

        # Autofocus override (set by autofocus button to preserve manual focus)
        self._af_mode_override = None  # None = use configured mode, 0 = force manual

        # AF window state tracking (click-to-focus feature)
        self._af_window_active = False  # True when AF window is set
        self._af_window_coords = (
            None  # Stores (x, y, w, h) in pixel coordinates relative to ScalerCropMaximum
        )

        # ISP feature toggles
        # Note: Lens shading changes require camera restart - no runtime control available
        self.lens_shading_enable = True
        self.defect_correction_enable = True
        self.use_custom_tuning = False  # Load custom tuning file (disabled by default)

        # Focus peaking controls (preview-only overlay)
        self.focus_peaking_enabled = False
        self.focus_peaking_intensity = 100  # 50-200 range
        self.focus_peaking_colour = "green"  # green, red, yellow, cyan, magenta
        self.focus_peaking_algorithm = "laplacian"  # laplacian, sobel, canny

        try:
            if mothbox_paths.LIVEVIEW_SETTINGS_FILE.exists():
                settings = get_control_values(mothbox_paths.LIVEVIEW_SETTINGS_FILE)

                # Load and validate settings
                if "stream_width" in settings:
                    self.stream_width = int(settings["stream_width"])
                if "stream_height" in settings:
                    self.stream_height = int(settings["stream_height"])
                if "frame_rate" in settings:
                    fps = int(settings["frame_rate"])
                    self.frame_delay = 1.0 / fps if fps > 0 else DEFAULT_FRAME_DELAY
                if "jpeg_quality" in settings:
                    self.jpeg_quality = int(settings["jpeg_quality"])
                if "stream_mode" in settings:
                    self.stream_mode = settings["stream_mode"]
                if "sensor_mode" in settings:
                    self.sensor_mode = settings["sensor_mode"]

                # Image quality settings
                if "sharpness" in settings:
                    self.sharpness = float(settings["sharpness"])
                if "brightness" in settings:
                    self.brightness = float(settings["brightness"])
                if "contrast" in settings:
                    self.contrast = float(settings["contrast"])
                if "saturation" in settings:
                    self.saturation = float(settings["saturation"])

                # Noise reduction setting
                if "noise_reduction_mode" in settings:
                    self.noise_reduction_mode = int(settings["noise_reduction_mode"])

                # Focus settings
                if "af_mode" in settings:
                    self.af_mode = int(settings["af_mode"])
                if "af_speed" in settings:
                    self.af_speed = int(settings["af_speed"])
                if "af_range" in settings:
                    self.af_range = int(settings["af_range"])

                # Exposure settings
                if "ae_enable" in settings:
                    self.ae_enable = settings["ae_enable"].lower() == "true"
                if "ae_metering_mode" in settings:
                    self.ae_metering_mode = int(settings["ae_metering_mode"])
                if "exposure_time" in settings:
                    self.exposure_time = int(settings["exposure_time"])
                if "analogue_gain" in settings:
                    self.analogue_gain = float(settings["analogue_gain"])

                # White balance settings
                if "awb_enable" in settings:
                    self.awb_enable = settings["awb_enable"].lower() == "true"
                if "awb_mode" in settings:
                    self.awb_mode = int(settings["awb_mode"])

                # Colour gains (load red/blue separately if present)
                if "colour_gains_red" in settings and "colour_gains_blue" in settings:
                    self.colour_gains = (
                        float(settings["colour_gains_red"]),
                        float(settings["colour_gains_blue"]),
                    )

                # ISP settings
                if "lens_shading_enable" in settings:
                    self.lens_shading_enable = settings["lens_shading_enable"].lower() == "true"
                if "defect_correction_enable" in settings:
                    self.defect_correction_enable = (
                        settings["defect_correction_enable"].lower() == "true"
                    )
                if "use_custom_tuning" in settings:
                    self.use_custom_tuning = settings["use_custom_tuning"].lower() == "true"

                # Focus peaking settings
                if "focus_peaking_enabled" in settings:
                    self.focus_peaking_enabled = settings["focus_peaking_enabled"].lower() == "true"
                if "focus_peaking_intensity" in settings:
                    self.focus_peaking_intensity = int(settings["focus_peaking_intensity"])
                if "focus_peaking_colour" in settings:
                    self.focus_peaking_colour = settings["focus_peaking_colour"]
                if "focus_peaking_algorithm" in settings:
                    self.focus_peaking_algorithm = settings["focus_peaking_algorithm"]

                print(
                    f"Stream settings loaded: {self.stream_width}x{self.stream_height}, "
                    f"FPS: {1 / self.frame_delay:.1f}, Quality: {self.jpeg_quality}, Mode: {self.stream_mode}, Sensor: {self.sensor_mode}"
                )
                print(
                    f"  Image quality: Sharp={self.sharpness}, Bright={self.brightness}, "
                    f"Contrast={self.contrast}, Sat={self.saturation}"
                )
                print(f"  Focus: Mode={self.af_mode}, Speed={self.af_speed}, Range={self.af_range}")
                print(
                    f"  White balance: AWB={self.awb_enable}, Mode={self.awb_mode}, ColourGains={self.colour_gains}"
                )
                print(
                    f"  ISP: LensShading={self.lens_shading_enable}, DefectCorrection={self.defect_correction_enable}, CustomTuning={self.use_custom_tuning}"
                )
                print(
                    f"  Focus peaking: Enabled={self.focus_peaking_enabled}, Intensity={self.focus_peaking_intensity}, Color={self.focus_peaking_colour}, Algorithm={self.focus_peaking_algorithm}"
                )
        except Exception as e:
            print(f"Error loading stream settings, using defaults: {e}")

    def get_current_settings(self):
        """
        Get current camera settings from live instance (not from file)

        This method exports all current camera controls from the running LiveViewStreamer
        instance. Settings reflect real-time changes made via WebSocket controls,
        including unsaved slider adjustments.

        Use this instead of reading from liveview_settings.txt to ensure test captures
        match exactly what the user sees in the live stream viewport.

        Returns:
            dict: Camera settings with snake_case keys, ready for test capture:
                {
                    'sharpness': float,
                    'brightness': float,
                    'contrast': float,
                    'saturation': float,
                    'af_mode': int (0=Manual, 1=Single, 2=Continuous),
                    'af_speed': int (0=Normal, 1=Fast),
                    'af_range': int (0=Normal, 1=Macro, 2=Full),
                    'ae_enable': bool,
                    'ae_metering_mode': int (0=Centre, 1=Spot, 2=Matrix, 3=Custom),
                    'awb_enable': bool,
                    'awb_mode': int (0=Auto, 1-7=various presets),
                    'exposure_time': int (microseconds),
                    'analogue_gain': float,
                    'noise_reduction_mode': int (0=Off, 1=Fast, 2=HighQuality),
                    'colour_gains_red': float,
                    'colour_gains_blue': float,
                    'lens_position': float (diopters, when available),
                }
        """
        # Read from instance variables (these reflect current camera state)
        settings = {
            # Image quality controls
            'sharpness': self.sharpness,
            'brightness': self.brightness,
            'contrast': self.contrast,
            'saturation': self.saturation,

            # Focus controls - use override if set, otherwise configured value
            'af_mode': self._af_mode_override if self._af_mode_override is not None else self.af_mode,
            'af_speed': self.af_speed,
            'af_range': self.af_range,

            # Exposure controls
            'ae_enable': self.ae_enable,
            'ae_metering_mode': self.ae_metering_mode,
            'exposure_time': self.exposure_time,
            'analogue_gain': self.analogue_gain,

            # White balance controls - split colour_gains tuple into components
            'awb_enable': self.awb_enable,
            'awb_mode': self.awb_mode,
            'colour_gains_red': self.colour_gains[0],
            'colour_gains_blue': self.colour_gains[1],

            # Noise reduction
            'noise_reduction_mode': self.noise_reduction_mode,

            # AF metering mode (for click-to-focus AF window feature)
            'af_metering': 1 if self._af_window_active else 0,
        }

        # Include lens_position from camera metadata if camera is active
        # This gives us the ACTUAL current focus position, not configured value
        if self.camera is not None:
            try:
                metadata = self.camera.capture_metadata()
                if 'LensPosition' in metadata:
                    lens_pos = metadata['LensPosition']
                    settings['lens_position'] = lens_pos
                    self._cached_lens_position = lens_pos  # Cache for future use
            except Exception as e:
                # Camera metadata query failed - use cached value if available
                if self._cached_lens_position is not None:
                    settings['lens_position'] = self._cached_lens_position
                    print(f"Using cached lens position {self._cached_lens_position:.2f} (metadata query failed: {e})")
                else:
                    print(f"Warning: Could not read lens position from camera metadata: {e}")
                if hasattr(self, 'lens_position'):
                    settings['lens_position'] = self.lens_position
        else:
            # Camera not active - use configured value if available
            if hasattr(self, 'lens_position'):
                settings['lens_position'] = self.lens_position

        return settings

    def initialize_camera(self):
        """Initialize camera hardware and configure for streaming"""
        if not PICAMERA_AVAILABLE:
            return False

        try:
            # If camera already exists, release it first to allow reinitialization
            # This enables error recovery and allows tests to reinitialize
            if self.camera is not None:
                self.release_camera()

            # Get ISP tuning file path if custom tuning is enabled
            # Pass path as STRING to avoid temp file creation/deletion issues
            tuning_path = None
            if ISP_TUNING_AVAILABLE and self.use_custom_tuning:
                try:
                    tuning_path = get_tuning_path()
                    if tuning_path:
                        print(f"Using custom ISP tuning file: {tuning_path}")
                except Exception as tuning_error:
                    print(f"Warning: Could not load custom tuning file: {tuning_error}")
                    print("Falling back to libcamera default tuning")
            elif ISP_TUNING_AVAILABLE and not self.use_custom_tuning:
                print("Custom tuning disabled - using libcamera default tuning")

            # Try camera 0 first, fallback to camera 1
            try:
                if tuning_path:
                    # Pass path as STRING - Picamera2 will set LIBCAMERA_RPI_TUNING_FILE env var
                    # This avoids temp file creation and works correctly on reinitialization
                    self.camera = Picamera2(0, tuning=str(tuning_path))
                else:
                    self.camera = Picamera2(0)
                print("Using camera 0")
            except Exception as e:
                print(f"Camera 0 unavailable ({e}), trying camera 1...")
                if tuning_path:
                    self.camera = Picamera2(1, tuning=str(tuning_path))
                else:
                    self.camera = Picamera2(1)
                print("Using camera 1")

            # Query available sensor modes for diagnostics and optimal selection
            print("\n📷 Available sensor modes:")
            sensor_modes = self.camera.sensor_modes
            max_resolution_mode = None
            max_pixels = 0
            best_4_3_mode = None
            best_4_3_pixels = 0

            for idx, mode in enumerate(sensor_modes):
                width = mode["size"][0]
                height = mode["size"][1]
                pixels = width * height
                aspect = width / height

                print(f"   [{idx}] {width}×{height} ({pixels / 1e6:.1f}MP, {aspect:.2f}:1 aspect)")

                # Find maximum resolution mode (for "full" mode)
                if pixels > max_pixels:
                    max_pixels = pixels
                    max_resolution_mode = mode

                # Find best 4:3 mode (aspect ratio between 1.30 and 1.35)
                if (
                    1.30 <= aspect <= 1.35  # 4:3 is 1.333...
                    and pixels > best_4_3_pixels
                    and pixels < max_pixels * 0.5  # Not the full sensor
                ):
                    best_4_3_pixels = pixels
                    best_4_3_mode = mode

            if max_resolution_mode:
                print(
                    f"   → Maximum resolution: {max_resolution_mode['size'][0]}×{max_resolution_mode['size'][1]} ({max_pixels / 1e6:.1f}MP)"
                )
            if best_4_3_mode:
                print(
                    f"   → Best 4:3 intermediate: {best_4_3_mode['size'][0]}×{best_4_3_mode['size'][1]} ({best_4_3_pixels / 1e6:.1f}MP)"
                )
            print()

            # Configure camera with video_config for both encoding paths:
            # - Hardware MJPEG: Requires video_config for start_recording() with encoder
            # - Software encoding: Works fine with video_config + capture_array()
            # Using video_config universally eliminates need to reconfigure between modes.

            # Apply sensor mode based on user preference (controls field of view)
            if self.sensor_mode == "4:3":
                # Use best available 4:3 sensor mode for wider field of view
                # Useful when output is 16:9 (1920x1080) but user wants wider vertical coverage
                if best_4_3_mode:
                    raw_size = best_4_3_mode["size"]
                    print(
                        f"📷 Sensor mode: Using 4:3 aspect {raw_size[0]}×{raw_size[1]} ({best_4_3_pixels / 1e6:.1f}MP) for wider field of view"
                    )
                    video_config = self.camera.create_video_configuration(
                        main={
                            "size": (self.stream_width, self.stream_height),
                            "format": self.stream_format,
                        },
                        raw={"size": raw_size},
                        encode="main",
                    )
                else:
                    # Fallback to hardcoded 4:3 if no suitable mode found
                    print(
                        "📷 Sensor mode: Using fallback 4:3 aspect (2304x1728) for wider field of view"
                    )
                    video_config = self.camera.create_video_configuration(
                        main={
                            "size": (self.stream_width, self.stream_height),
                            "format": self.stream_format,
                        },
                        raw={"size": (2304, 1728)},
                        encode="main",
                    )
            elif self.sensor_mode == "full":
                # Use maximum sensor resolution for widest possible field of view
                # Most downscaling, highest quality, most processing
                if max_resolution_mode:
                    raw_size = max_resolution_mode["size"]
                    print(
                        f"📷 Sensor mode: Using FULL sensor {raw_size[0]}×{raw_size[1]} ({max_pixels / 1e6:.1f}MP) for maximum field of view"
                    )
                    video_config = self.camera.create_video_configuration(
                        main={
                            "size": (self.stream_width, self.stream_height),
                            "format": self.stream_format,
                        },
                        raw={"size": raw_size},
                        encode="main",
                    )
                else:
                    print("⚠ Full sensor mode requested but no sensor modes found, using auto")
                    video_config = self.camera.create_video_configuration(
                        main={
                            "size": (self.stream_width, self.stream_height),
                            "format": self.stream_format,
                        },
                        encode="main",
                    )
            else:  # 'auto' or '16:9' or unknown
                # Let libcamera choose sensor mode based on output resolution
                # For 1920x1080 output, this typically selects 1920x1080 sensor mode (16:9)
                print("📷 Sensor mode: Auto (libcamera will select based on output resolution)")
                video_config = self.camera.create_video_configuration(
                    main={
                        "size": (self.stream_width, self.stream_height),
                        "format": self.stream_format,
                    },
                    encode="main",  # Required for encoder support
                )
            self.camera.configure(video_config)

            # Get actual sensor mode resolution (NOT PixelArraySize which is max sensor size)
            # AfWindows coordinates must be relative to the actual sensor mode being used
            config = self.camera.camera_configuration()
            if "raw" in config and "size" in config["raw"]:
                self.sensor_resolution = config["raw"]["size"]
                pixels = self.sensor_resolution[0] * self.sensor_resolution[1]
                aspect = self.sensor_resolution[0] / self.sensor_resolution[1]
                print(
                    f"✓ Selected sensor mode: {self.sensor_resolution[0]}×{self.sensor_resolution[1]} ({pixels / 1e6:.1f}MP, {aspect:.2f}:1 aspect)"
                )
                print(f"  Output resolution: {self.stream_width}×{self.stream_height}")
                print(
                    f"  ISP downscale factor: {pixels / (self.stream_width * self.stream_height):.1f}x"
                )
            else:
                # Fallback: use PixelArraySize (may cause issues with AF windows)
                self.sensor_resolution = self.camera.camera_properties["PixelArraySize"]
                print(f"⚠ Sensor resolution (fallback to PixelArraySize): {self.sensor_resolution}")

            # Start camera to apply controls
            self.camera.start()

            # DIAGNOSTIC: List all available camera controls to debug AF window support
            print("\n" + "=" * 60)
            print("CAMERA CONTROLS DIAGNOSTIC")
            print("=" * 60)
            try:
                controls = self.camera.camera_controls
                af_controls = {k: v for k, v in controls.items() if "Af" in k or "Focus" in k}
                print(f"AF-related controls available: {list(af_controls.keys())}")

                # Check specifically for AfWindows and AfMetering
                if "AfWindows" in controls:
                    print(f"  ✓ AfWindows supported: {controls['AfWindows']}")
                else:
                    print("  ✗ AfWindows NOT available")

                if "AfMetering" in controls:
                    print(f"  ✓ AfMetering supported: {controls['AfMetering']}")
                else:
                    print("  ✗ AfMetering NOT available")

                # Get sample metadata to see what's actually reported
                metadata = self.camera.capture_metadata()
                af_metadata = {
                    k: v for k, v in metadata.items() if "Af" in k or "Focus" in k or "Lens" in k
                }
                print(f"AF-related metadata keys: {list(af_metadata.keys())}")
            except Exception as diag_err:
                print(f"Diagnostic failed: {diag_err}")
            print("=" * 60 + "\n")

            # Apply camera controls
            # CRITICAL: Must be called after configure() as configure() resets controls to defaults
            applied_controls = self._apply_camera_controls()

            # Apply ISP controls
            # Must be done after camera.start() as ISP controls require running camera
            # Note: Lens shading changes require camera restart - LensShadingMapMode not available at runtime
            if ISP_TUNING_AVAILABLE:
                try:
                    apply_isp_controls(
                        self.camera,
                        lens_shading=self.lens_shading_enable,
                        defect_correction=self.defect_correction_enable,
                    )
                except Exception as isp_error:
                    print(f"Warning: Could not apply ISP controls: {isp_error}")

            # Log applied controls for debugging
            print(
                f"✓ Camera controls applied: AF Mode {applied_controls['AfMode']}, "
                f"Speed {applied_controls['AfSpeed']}, Range {applied_controls['AfRange']}, "
                f"Sharpness {applied_controls['Sharpness']}, "
                f"AWB {'Enabled' if applied_controls['AwbEnable'] else 'Disabled'}"
            )

            # Stop camera - will be started again by stream_loop
            self.camera.stop()

            return True
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            return False

    def _apply_camera_controls(self):
        """
        Apply camera controls (autofocus, quality, white balance).

        CRITICAL: Must be called after any camera.configure() call.
        Picamera2's configure() method resets all controls to defaults.
        This is not well-documented but causes controls to be lost if not re-applied
        after every configure() call. This helper ensures controls are always applied
        consistently after configuration changes.

        Returns:
            dict: Applied controls for verification logging
        """
        # Use AF mode override if set (e.g., after autofocus button locks focus)
        af_mode_to_use = (
            self._af_mode_override if self._af_mode_override is not None else self.af_mode
        )

        # Use centralized mapping from camera_control_mapping.py
        # This eliminates implicit snake_case → PascalCase conversion
        settings = {
            # Focus controls
            "af_mode": af_mode_to_use,
            "af_speed": self.af_speed,
            "af_range": self.af_range,
            # Use Windows mode (1) if AF window is active, otherwise Auto (0)
            "af_metering": 1 if self._af_window_active else 0,
            # Image quality controls
            "sharpness": self.sharpness,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            # Exposure controls
            "ae_enable": self.ae_enable,
            "ae_metering_mode": self.ae_metering_mode,
            # Noise reduction control
            "noise_reduction_mode": self.noise_reduction_mode,
            # White balance controls
            "awb_enable": self.awb_enable,
            # ColourGains: Critical for locking colour balance under LED illumination
            # Note: Must be set even with AwbEnable to lock white balance (TakePhoto.py:519)
            "colour_gains": self.colour_gains,
        }

        # Build base controls with PascalCase keys
        controls_dict = build_picamera_controls(settings)

        # Only set AwbMode if AWB is disabled (manual mode)
        if not self.awb_enable:
            controls_dict.update(build_picamera_controls({"awb_mode": self.awb_mode}))

        # Only set manual exposure values if auto exposure is disabled
        if not self.ae_enable:
            controls_dict.update(
                build_picamera_controls(
                    {"exposure_time": self.exposure_time, "analogue_gain": self.analogue_gain}
                )
            )

        self.camera.set_controls(controls_dict)

        # Re-apply AF window if active (ensures window persists after configure/reinit)
        self._reapply_af_window_if_active()

        # Small delay to allow controls to settle
        time.sleep(0.05)

        return controls_dict

    def _reapply_af_window_if_active(self):
        """
        Re-apply AF window controls if an AF window is currently active.

        This helper ensures AF window persistence across control updates.
        Should be called after any set_controls() call that might interfere
        with AF window settings.

        Called by:
        - _apply_camera_controls() - after camera initialization
        - update_control() - after control updates
        - set_zoom() - after zoom changes
        - set_manual_focus_mode() - after AF mode changes

        Returns:
            bool: True if AF window was re-applied, False if not active
        """
        if self._af_window_active and self._af_window_coords:
            try:
                self.camera.set_controls(
                    {
                        "AfMetering": 1,  # Windows mode
                        "AfWindows": [self._af_window_coords],
                    }
                )
                return True
            except Exception as e:
                print(f"⚠ Error re-applying AF window: {e}")
                return False
        return False

    def start_streaming(self):
        """Start streaming camera frames"""
        if self.streaming:
            return True

        if not self.initialize_camera():
            return False

        self.streaming = True
        self.stop_event.clear()
        self.stream_thread = Thread(target=self._stream_loop)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        return True

    def stop_streaming(self):
        """Stop streaming camera frames"""
        self.streaming = False
        self.stop_event.set()

        if self.stream_thread:
            self.stream_thread.join(timeout=2)

        if self.camera:
            try:
                self.camera.stop()
            except Exception as e:
                # Camera may already be stopped, which is fine
                print(f"Note: Error stopping camera (already stopped?): {e}")

    def release_camera(self):
        """
        Temporarily release camera hardware for external use.

        This fully closes the camera, releasing the hardware lock so other
        code can create a new Picamera2 instance (e.g., for autofocus/calibration).

        Call start_streaming() afterward to re-initialize and resume streaming.
        """
        print("Releasing camera hardware...")
        self.stop_streaming()

        if self.camera:
            try:
                self.camera.close()
                print("✓ Camera hardware released")
            except Exception as e:
                print(f"Warning: Error closing camera: {e}")
            finally:
                self.camera = None

    @contextmanager
    def acquire_for_operation(self):
        """
        Context manager for exclusive camera operations (autofocus, calibration, etc.)

        Acquires the global camera operation lock to prevent concurrent access.
        Automatically releases the lock on exit, even if an exception occurs.

        Usage:
            with camera_streamer.acquire_for_operation():
                # Perform camera operation
                picam2 = Picamera2(0)
                # ... use camera ...

        Raises:
            Any exception from the wrapped code is propagated after lock release
        """
        print("🔒 Acquiring camera operation lock...")
        CAMERA_OPERATION_LOCK.acquire()
        try:
            print("✓ Camera operation lock acquired")
            yield
        finally:
            CAMERA_OPERATION_LOCK.release()
            print("🔓 Camera operation lock released")

    def _stream_hardware_mjpeg(self):
        """
        Hardware-accelerated MJPEG streaming using Picamera2's MJPEGEncoder.

        This method leverages the hardware ISP (Image Signal Processor) to encode
        JPEG frames directly, reducing CPU usage from ~40% to <10% compared to
        software encoding (simplejpeg/PIL).

        The encoder outputs pre-encoded JPEG data, eliminating the need for CPU-based
        compression. Frames are emitted via WebSocket as base64-encoded data.

        If focus peaking is enabled, uses hybrid mode with periodic frame overlay
        to apply focus peaking while maintaining hardware encoding efficiency.

        Automatically falls back to software encoding if hardware encoder is unavailable.
        """
        if not HARDWARE_MJPEG_AVAILABLE:
            print("⚠ Hardware MJPEG not available, falling back to software encoding")
            self.socketio.emit(
                "stream_warning", {"message": "Hardware MJPEG unavailable, using software fallback"}
            )
            return self._stream_software_encoding()

        # If focus peaking is enabled, use software encoding with overlay
        if self.focus_peaking_enabled and CV2_AVAILABLE:
            print("⚡ Focus peaking enabled - using software encoding")
            return self._stream_software_encoding()

        try:
            # Ensure sensor resolution is captured (defensive programming for zoom feature)
            if not self.sensor_resolution and self.camera:
                try:
                    config = self.camera.camera_configuration()
                    if "raw" in config and "size" in config["raw"]:
                        self.sensor_resolution = config["raw"]["size"]
                        print(f"📷 Captured sensor mode resolution: {self.sensor_resolution}")
                    else:
                        self.sensor_resolution = self.camera.camera_properties["PixelArraySize"]
                        print(f"📷 Captured sensor resolution (fallback): {self.sensor_resolution}")
                except Exception as e:
                    print(f"⚠ Could not capture sensor resolution: {e}")

            # Create hardware MJPEG encoder with quality settings
            # Convert JPEG quality (0-100, higher=better) to qp (1-25, lower=better)
            # Hardware MJPEG is sensitive - qp > 20 produces poor quality
            # Formula: qp = 25 - (quality * 0.24) maps quality to good qp range
            # Examples: quality 100 → qp 1, quality 85 → qp 5, quality 50 → qp 13
            qp_value = max(1, min(25, int(25 - (self.jpeg_quality * 0.24))))
            encoder = MJPEGEncoder(qp=qp_value)
            print(f"Hardware MJPEG: quality={self.jpeg_quality}% → qp={qp_value}")

            # Create custom output handler for WebSocket streaming
            class WebSocketOutput(FileOutput):
                """Custom output that emits MJPEG frames to WebSocket"""

                def __init__(self, socketio, frame_delay):
                    self.socketio = socketio
                    self.frame_delay = frame_delay
                    self.last_emit = 0
                    super().__init__()

                def outputframe(
                    self, frame, keyframe=True, timestamp=None, packet=None, audio=None
                ):
                    """Called by encoder for each MJPEG frame"""
                    current_time = time.time()

                    # Rate limit based on frame_delay
                    if current_time - self.last_emit < self.frame_delay:
                        return

                    self.last_emit = current_time

                    # Convert JPEG bytes to base64
                    img_base64 = base64.b64encode(frame).decode("utf-8")

                    # Emit to WebSocket
                    self.socketio.emit(
                        "camera_frame", {"image": f"data:image/jpeg;base64,{img_base64}"}
                    )

            # Create WebSocket output handler
            output = WebSocketOutput(self.socketio, self.frame_delay)

            # Start encoder and camera (already configured with video_config in initialize_camera)
            self.camera.start_recording(encoder, output)
            print(f"✓ Hardware MJPEG streaming started at {self.stream_width}x{self.stream_height}")

            # Self-test: Verify autofocus is functioning (if configured for continuous AF)
            if self.af_mode == 2 and self._af_mode_override is None:
                print("Running hardware MJPEG self-test...")
                time.sleep(0.5)  # Wait for camera to stabilize

                try:
                    # Try to get metadata to verify AF is working
                    request = self.camera.capture_request()
                    md = request.get_metadata()
                    request.release()

                    af_state = md.get("AfState", 0)
                    af_state_name = (
                        ("Idle", "Scanning", "Focused", "Failed")[af_state]
                        if af_state < 4
                        else "Unknown"
                    )

                    print(f"Self-test: AfState = {af_state_name}")

                    # If stuck at Idle, controls may not have been applied
                    if af_state == 0:
                        print("⚠ Warning: Autofocus appears idle. Controls may not be active.")
                        self.socketio.emit(
                            "stream_warning",
                            {
                                "message": "Autofocus may not be functioning. Try restarting the stream."
                            },
                        )
                except Exception as e:
                    print(f"Self-test failed (non-critical): {e}")

            # Keep streaming until stopped
            while self.streaming and not self.stop_event.is_set():
                time.sleep(0.1)

        except Exception as e:
            print(f"⚠ Hardware MJPEG encoder failed: {e}")
            print("Falling back to software encoding...")
            self.socketio.emit(
                "stream_warning",
                {"message": f"Hardware MJPEG error: {e}. Using software fallback."},
            )

            # Stop recording if started
            try:
                self.camera.stop_recording()
            except Exception as e:
                # Recording may not have started or camera may be in invalid state
                print(f"Note: Error stopping recording during fallback: {e}")

            # Fall back to software encoding
            return self._stream_software_encoding()

        finally:
            # Clean up encoder
            try:
                if self.camera:
                    self.camera.stop_recording()
                    print("✓ Hardware MJPEG encoder stopped")
            except Exception as e:
                print(f"Note: Error stopping encoder: {e}")

    def _stream_software_encoding(self):
        """
        Software-based JPEG encoding using simplejpeg or PIL.

        This method uses CPU to encode frames. It's the fallback when hardware
        MJPEG is unavailable and was the default streaming method before
        hardware acceleration was implemented.

        Performance:
        - simplejpeg: ~40% CPU @ 10fps on Pi 4 (5-7x faster than PIL)
        - PIL: ~60-80% CPU @ 10fps on Pi 4 (slowest, but most compatible)
        """
        try:
            # Ensure sensor resolution is captured (defensive programming for zoom feature)
            # This handles the case where hardware MJPEG fails and falls back to software encoding
            if not self.sensor_resolution and self.camera:
                try:
                    config = self.camera.camera_configuration()
                    if "raw" in config and "size" in config["raw"]:
                        self.sensor_resolution = config["raw"]["size"]
                        print(f"📷 Captured sensor mode resolution: {self.sensor_resolution}")
                    else:
                        self.sensor_resolution = self.camera.camera_properties["PixelArraySize"]
                        print(f"📷 Captured sensor resolution (fallback): {self.sensor_resolution}")
                except Exception as e:
                    print(f"⚠ Could not capture sensor resolution: {e}")

            self.camera.start()
            print(
                f"✓ Software encoding streaming started (mode: {'simplejpeg' if SIMPLEJPEG_AVAILABLE else 'PIL'})"
            )

            while self.streaming and not self.stop_event.is_set():
                try:
                    # Capture frame from camera
                    frame = self.camera.capture_array()

                    # Apply focus peaking overlay if enabled (preview only)
                    if self.focus_peaking_enabled and CV2_AVAILABLE:
                        # Route to selected algorithm
                        if self.focus_peaking_algorithm == "sobel":
                            frame = self._apply_focus_peaking_sobel(
                                frame,
                                threshold=self.focus_peaking_intensity,
                                color=self.focus_peaking_colour,
                            )
                        elif self.focus_peaking_algorithm == "canny":
                            frame = self._apply_focus_peaking_canny(
                                frame,
                                threshold=self.focus_peaking_intensity,
                                color=self.focus_peaking_colour,
                            )
                        else:  # Default to laplacian
                            frame = self._apply_focus_peaking_laplacian(
                                frame,
                                threshold=self.focus_peaking_intensity,
                                color=self.focus_peaking_colour,
                            )

                    # Encode as JPEG using fastest available method
                    if SIMPLEJPEG_AVAILABLE:
                        # Fast path: simplejpeg (5-7x faster than PIL)
                        jpeg_bytes = simplejpeg.encode_jpeg(
                            frame, quality=self.jpeg_quality, colorspace="RGB"
                        )
                    else:
                        # Fallback path: PIL (slower, remove optimize=True for speed)
                        Image = _get_pil_image()  # noqa: N806 - matches PIL.Image class name
                        img = Image.fromarray(frame)
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=self.jpeg_quality)
                        buffer.seek(0)
                        jpeg_bytes = buffer.read()

                    # Convert to base64
                    img_base64 = base64.b64encode(jpeg_bytes).decode("utf-8")

                    # Emit to all connected clients
                    self.socketio.emit(
                        "camera_frame", {"image": f"data:image/jpeg;base64,{img_base64}"}
                    )

                    # Limit frame rate
                    time.sleep(self.frame_delay)

                except Exception as e:
                    print(f"Error capturing frame: {e}")
                    time.sleep(0.5)

        finally:
            if self.camera:
                try:
                    self.camera.stop()
                except Exception as e:
                    # Camera may already be stopped, which is fine
                    print(f"Note: Error stopping camera in stream cleanup: {e}")

    def _stream_loop(self):
        """
        Main streaming loop - dispatches to hardware or software encoding.

        Checks the configured stream_mode and routes to the appropriate encoder:
        - 'mjpeg_hardware': Hardware-accelerated MJPEG (low CPU, <10%)
        - 'simplejpeg' or other: Software encoding (higher CPU, 40-80%)

        Hardware MJPEG automatically falls back to software if unavailable.
        """
        try:
            # Route to appropriate encoder based on configuration
            if self.stream_mode == "mjpeg_hardware":
                print(f"Attempting hardware MJPEG mode (configured: {self.stream_mode})")
                self._stream_hardware_mjpeg()
            else:
                print(f"Using software encoding mode (configured: {self.stream_mode})")
                self._stream_software_encoding()

        finally:
            if self.camera:
                try:
                    self.camera.stop()
                except Exception as e:
                    # Camera may already be stopped, which is fine
                    print(f"Note: Error stopping camera in stream cleanup: {e}")

    def capture_frame(self):
        """
        Capture a single frame for testing purposes (Test utility method)

        This method is used by automated tests to capture and analyze image quality
        metrics (sharpness, contrast, brightness). It's NOT for production use.

        Returns:
            bytes: JPEG-encoded image data

        Raises:
            RuntimeError: If camera initialization fails

        Note:
            - Camera must be initialized first (call initialize_camera())
            - Returns raw JPEG bytes, not base64 encoded
            - Uses same quality/encoding as streaming
        """
        if not self.camera:
            raise RuntimeError("Camera not initialized. Call initialize_camera() first.")

        try:
            # Start camera if not already started
            was_started = False
            try:
                self.camera.start()
                was_started = True
            except RuntimeError:
                # Camera already started, that's fine
                pass

            # Capture single frame
            frame = self.camera.capture_array()

            # Encode as JPEG using same method as streaming
            if SIMPLEJPEG_AVAILABLE:
                jpeg_bytes = simplejpeg.encode_jpeg(
                    frame, quality=self.jpeg_quality, colorspace="RGB"
                )
            else:
                # Fallback to PIL
                Image = _get_pil_image()  # noqa: N806 - matches PIL.Image class name
                img = Image.fromarray(frame)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=self.jpeg_quality)
                buffer.seek(0)
                jpeg_bytes = buffer.read()

            # Stop camera if we started it
            if was_started:
                self.camera.stop()

            return jpeg_bytes

        except Exception as e:
            print(f"Error capturing frame: {e}")
            raise

    def update_control(self, control_dict):
        """
        Update camera control(s) without restarting stream

        Args:
            control_dict: Dictionary of control names and values
                          e.g., {"Sharpness": 2.0, "Brightness": 0.1}
                          Also supports focus peaking controls:
                          {"FocusPeakingEnabled": True, "FocusPeakingIntensity": 150}
                          Also supports colour gains:
                          {"ColourGainRed": 2.259, "ColourGainBlue": 1.500}

        Returns:
            bool: True if successful, False if camera not ready
        """
        # Handle focus peaking controls separately (these are stream settings, not camera controls)
        focus_peaking_controls = {}
        camera_controls = {}

        # Track colour gains separately - need to combine into tuple
        colour_gain_red = None
        colour_gain_blue = None

        # Use centralized mapping for dual naming support (PascalCase or snake_case)
        for key, value in control_dict.items():
            # Normalize key to PascalCase for consistent handling
            normalized_key = normalize_control_key(key)

            if normalized_key == "FocusPeakingEnabled":
                self.focus_peaking_enabled = (
                    value if isinstance(value, bool) else str(value).lower() == "true"
                )
                focus_peaking_controls[key] = value
            elif normalized_key == "FocusPeakingIntensity":
                self.focus_peaking_intensity = int(value)
                focus_peaking_controls[key] = value
            elif normalized_key == "FocusPeakingColour":
                self.focus_peaking_colour = str(value)
                focus_peaking_controls[key] = value
            elif normalized_key == "FocusPeakingAlgorithm":
                self.focus_peaking_algorithm = str(value)
                focus_peaking_controls[key] = value
            elif normalized_key == "ColourGainRed":
                # Handle both PascalCase (camera settings) and snake_case (liveview settings)
                colour_gain_red = float(value)
                # Store for persistence
                self.colour_gains = (colour_gain_red, self.colour_gains[1])
            elif normalized_key == "ColourGainBlue":
                # Handle both PascalCase (camera settings) and snake_case (liveview settings)
                colour_gain_blue = float(value)
                # Store for persistence
                self.colour_gains = (self.colour_gains[0], colour_gain_blue)
            else:
                # Use normalized PascalCase key for camera controls
                camera_controls[normalized_key] = value

        # If colour gains were updated, add them to camera controls using helper
        if colour_gain_red is not None or colour_gain_blue is not None:
            camera_controls.update(
                handle_colour_gains(
                    red=colour_gain_red, blue=colour_gain_blue, current=self.colour_gains
                )
            )

        # Apply camera controls if any
        if camera_controls:
            # Return False if camera is not available for camera-specific controls
            if not self.camera or not self.streaming:
                print(
                    f"Cannot update camera controls - camera not ready (camera={self.camera is not None}, streaming={self.streaming})"
                )
                return False

            try:
                self.camera.set_controls(camera_controls)

                # Re-apply AF window if active (preserve window when other controls change)
                self._reapply_af_window_if_active()

                print(f"Updated camera controls: {camera_controls}")
            except Exception as e:
                print(f"Error updating camera controls: {e}")
                return False

        # Log focus peaking control updates
        if focus_peaking_controls:
            print(f"Updated focus peaking controls: {focus_peaking_controls}")

        return True

    def _apply_focus_peaking_laplacian(self, frame, threshold=100, color="green"):
        """
        Apply focus peaking overlay using Laplacian edge detection

        Laplacian is the fastest method - detects edges using second derivative.
        Best for: General use, fast performance

        Args:
            frame: BGR888 numpy array (height, width, 3)
            threshold: Edge detection sensitivity (50-200, higher = more sensitive)
            color: Overlay colour ('green', 'red', 'yellow', 'cyan', 'magenta')

        Returns:
            Modified BGR888 frame with focus peaking overlay
        """
        if not CV2_AVAILABLE:
            return frame

        # Color mapping (RGB format - picamera2 BGR888 is actually RGB)
        colour_map = {
            "green": (0, 255, 0),
            "red": (255, 0, 0),  # RGB not BGR
            "yellow": (255, 255, 0),  # RGB not BGR
            "cyan": (0, 255, 255),  # RGB not BGR
            "magenta": (255, 0, 255),
        }
        overlay_colour = colour_map.get(color, (0, 255, 0))  # Default to green

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Laplacian edge detection (ksize=3 for speed)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        laplacian = np.abs(laplacian)

        # Threshold for sharp edges (inverted: high intensity = more edges)
        inverted_threshold = 250 - threshold  # 200→50, 100→150, 50→200
        edge_mask = (laplacian > inverted_threshold).astype(np.uint8) * 255

        # Morphological closing to connect nearby edges (3x3 ellipse kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, kernel)

        # Create colored overlay
        overlay = np.zeros_like(frame)
        overlay[edge_mask.astype(bool)] = overlay_colour

        # Blend with original (60% overlay visibility)
        result = cv2.addWeighted(frame, 1.0, overlay, 0.6, 0)

        return result

    def _apply_focus_peaking_sobel(self, frame, threshold=100, color="green"):
        """
        Apply focus peaking overlay using Sobel edge detection

        Sobel detects directional edges (horizontal and vertical separately).
        Best for: Better directional accuracy, moderate performance

        Args:
            frame: BGR888 numpy array (height, width, 3)
            threshold: Edge detection sensitivity (50-200, higher = more sensitive)
            color: Overlay colour ('green', 'red', 'yellow', 'cyan', 'magenta')

        Returns:
            Modified BGR888 frame with focus peaking overlay
        """
        if not CV2_AVAILABLE:
            return frame

        # Color mapping (RGB format - picamera2 BGR888 is actually RGB)
        colour_map = {
            "green": (0, 255, 0),
            "red": (255, 0, 0),  # RGB not BGR
            "yellow": (255, 255, 0),  # RGB not BGR
            "cyan": (0, 255, 255),  # RGB not BGR
            "magenta": (255, 0, 255),
        }
        overlay_colour = colour_map.get(color, (0, 255, 0))  # Default to green

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Sobel edge detection in both directions
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        # Combine gradients (magnitude) - use np.hypot for numeric stability
        sobel_mag = np.hypot(sobel_x, sobel_y)

        # Threshold for sharp edges (inverted: high intensity = more edges)
        inverted_threshold = 250 - threshold  # 200→50, 100→150, 50→200
        edge_mask = (sobel_mag > inverted_threshold).astype(np.uint8) * 255

        # Morphological closing to connect nearby edges (3x3 ellipse kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, kernel)

        # Create colored overlay
        overlay = np.zeros_like(frame)
        overlay[edge_mask.astype(bool)] = overlay_colour

        # Blend with original (60% overlay visibility)
        result = cv2.addWeighted(frame, 1.0, overlay, 0.6, 0)

        return result

    def _apply_focus_peaking_canny(self, frame, threshold=100, color="green"):
        """
        Apply focus peaking overlay using Canny edge detection

        Canny is the most accurate - multi-stage algorithm with hysteresis thresholding.
        Best for: Maximum accuracy, slower performance

        Args:
            frame: BGR888 numpy array (height, width, 3)
            threshold: Edge detection sensitivity (50-200, higher = more sensitive)
            color: Overlay colour ('green', 'red', 'yellow', 'cyan', 'magenta')

        Returns:
            Modified BGR888 frame with focus peaking overlay
        """
        if not CV2_AVAILABLE:
            return frame

        # Color mapping (RGB format - picamera2 BGR888 is actually RGB)
        colour_map = {
            "green": (0, 255, 0),
            "red": (255, 0, 0),  # RGB not BGR
            "yellow": (255, 255, 0),  # RGB not BGR
            "cyan": (0, 255, 255),  # RGB not BGR
            "magenta": (255, 0, 255),
        }
        overlay_colour = colour_map.get(color, (0, 255, 0))  # Default to green

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection (inverted: high intensity = more edges)
        # Use threshold as lower bound, upper bound = threshold * 2 (standard practice)
        inverted_threshold = 250 - threshold  # 200→50, 100→150, 50→200
        edge_mask = cv2.Canny(gray, inverted_threshold, inverted_threshold * 2)

        # Morphological closing to connect nearby edges (3x3 ellipse kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, kernel)

        # Create colored overlay
        overlay = np.zeros_like(frame)
        overlay[edge_mask.astype(bool)] = overlay_colour

        # Blend with original (60% overlay visibility)
        result = cv2.addWeighted(frame, 1.0, overlay, 0.6, 0)

        return result

    def calculate_scaler_crop(self):
        """
        Calculate ScalerCrop rectangle for current zoom level and center point.

        CRITICAL: ScalerCrop coordinates must be in FULL SENSOR coordinate space,
        NOT sensor mode coordinates. This is defined by ScalerCropMaximum.

        ScalerCropMaximum format: (x_offset, y_offset, active_width, active_height)
        - For full sensor mode: (0, 0, 9152, 6944) - offset is zero
        - For binned modes (e.g., 1920x1080): (784, 1312, 7712, 4352) - offset defines
          where the active area starts in full sensor space

        Aspect Ratio Preservation:
        When the sensor active area and output stream have different aspect ratios
        (e.g., 4:3 sensor → 16:9 output), the crop dimensions must be adjusted to
        prevent image distortion. This creates ASYMMETRIC crop fractions.

        Why this is necessary:
        - Without aspect preservation: 4:3 sensor data would be squashed into 16:9 output
        - Result: Horizontal stretching or vertical compression
        - Solution: Crop sensor to match output aspect ratio BEFORE scaling

        Example: 2312x1736 sensor (4:3) → 1920x1080 output (16:9) at zoom=1.0
          - Active area aspect: 2312/1736 = 1.33 (4:3)
          - Output aspect: 1920/1080 = 1.78 (16:9)
          - Output is WIDER than sensor → crop HEIGHT to match
          - Crop dimensions: 2312×1301 (full width, reduced height)
          - Crop fractions: X=1.0 (100% width), Y=0.75 (75% height)
          - Result: Image fills frame without distortion

        Impact on coordinate transformations:
        These asymmetric fractions are sent to the frontend via metadata
        (crop_fraction_x, crop_fraction_y) so coordinate transformations remain accurate.
        Without separate X/Y fractions, viewport→sensor coordinate mapping would be
        wrong by ~15% in one axis for 4:3→16:9 conversion.

        Returns:
            tuple: (x, y, width, height) ScalerCrop coordinates in full sensor space,
                   or None if camera not ready

        See also:
            - get_actual_zoom_center(): Inverse transformation (pixels → normalized)
            - set_zoom(): Applies the calculated ScalerCrop to camera hardware
            - websocket_handlers.py (line 235): Metadata emission with crop fractions

        Example:
            ScalerCropMaximum = (784, 1312, 7712, 4352)  # 1920x1080 sensor mode
            2x zoom centered -> crop 7712/2 = 3856 pixels of the 7712px active area
            Position in active area: (1928, 1248)
            Position in full sensor: (784+1928, 1312+1248) = (2712, 2560)
            ScalerCrop: (2712, 2560, 3856, 2176)
        """
        if not self.camera or not self.streaming:
            return None

        # Get full sensor coordinate system from ScalerCropMaximum
        # ScalerCrop coordinates MUST be in this coordinate space
        scaler_crop_max = self.camera.camera_properties.get("ScalerCropMaximum")
        if not scaler_crop_max:
            print("⚠ Cannot calculate ScalerCrop - ScalerCropMaximum not available")
            return None

        # Extract active area dimensions AND offset from ScalerCropMaximum
        # The offset defines where the active area starts in full sensor coordinates
        x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max

        # Calculate cropped dimensions that preserve OUTPUT aspect ratio
        # This applies even at zoom=1.0 to prevent distortion when active area
        # and output have different aspect ratios (e.g., 4:3 sensor → 16:9 output)
        # This prevents distortion when ScalerCropMaximum and output have different aspects
        # Example: 4:3 sensor mode (2312x1736) with 16:9 output (1920x1080)
        output_aspect = self.stream_width / self.stream_height
        active_aspect = sensor_width / sensor_height

        # Determine which dimension limits the crop
        if active_aspect >= output_aspect:
            # Active area is wider/equal than output - width is the limiting factor
            # Calculate crop width from zoom, then derive height from output aspect
            crop_width = int(sensor_width / self.zoom_level)
            crop_height = int(crop_width / output_aspect)
        else:
            # Active area is taller than output - height is the limiting factor
            # Calculate crop height from zoom, then derive width from output aspect
            crop_height = int(sensor_height / self.zoom_level)
            crop_width = int(crop_height * output_aspect)

        # Ensure crop fits within active area (safety clamp)
        # If clamped, recalculate other dimension to maintain aspect ratio
        if crop_width > sensor_width:
            crop_width = sensor_width
            crop_height = int(crop_width / output_aspect)
        if crop_height > sensor_height:
            crop_height = sensor_height
            crop_width = int(crop_height * output_aspect)

        # Ensure even dimensions (required by some encoders)
        crop_width = crop_width & ~1  # Clear lowest bit to make even
        crop_height = crop_height & ~1

        # Calculate position RELATIVE to active area
        # zoom_center is normalized (0-1), where 0.5 = center of active area
        # Formula: position_in_active_area = (center_position - crop_size/2)
        # Use round() instead of int() to avoid systematic left/top bias from truncation
        offset_x_rel = round(self.zoom_center_x * sensor_width - crop_width / 2)
        offset_y_rel = round(self.zoom_center_y * sensor_height - crop_height / 2)

        # Clamp to valid range within active area
        offset_x_rel = max(0, min(offset_x_rel, sensor_width - crop_width))
        offset_y_rel = max(0, min(offset_y_rel, sensor_height - crop_height))

        # Ensure even offsets (required by some encoders)
        offset_x_rel = offset_x_rel & ~1
        offset_y_rel = offset_y_rel & ~1

        # Convert to FULL SENSOR coordinates by adding ScalerCropMaximum offset
        # This is the key fix: we must convert from active area coords to full sensor coords
        offset_x_pixels = x_offset + offset_x_rel
        offset_y_pixels = y_offset + offset_y_rel

        return (offset_x_pixels, offset_y_pixels, crop_width, crop_height)

    def get_actual_zoom_center(self):
        """
        Get the actual zoom center position after aspect ratio preservation and clamping.

        This returns where the crop ACTUALLY ended up, accounting for:
        - Aspect ratio preservation (may shift crop position)
        - Boundary clamping (when zooming near edges)
        - Even dimension enforcement (pixel alignment)

        Coordinate Transformation Flow:
        ┌─────────────────────────────────────────────────────────────┐
        │ 1. User Request (Normalized 0-1 coords in active area)     │
        │    e.g., click at (0.75, 0.5) = 75% right, 50% down        │
        └──────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 2. calculate_scaler_crop() applies:                        │
        │    • Aspect ratio preservation (crop size)                 │
        │    • Boundary clamping (position)                          │
        │    • Even enforcement (alignment)                          │
        │    → Produces ScalerCrop in FULL SENSOR coordinates        │
        └──────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ 3. get_actual_zoom_center() reverses transformation:       │
        │    Full Sensor Pixels → Active Area Pixels → Normalized    │
        │    (offset_x, offset_y, w, h) → (center_x, center_y)       │
        │    → Returns actual center in 0-1 coords                   │
        └─────────────────────────────────────────────────────────────┘

        Example Coordinate Spaces:
            Full Sensor:     (0, 0) to (3280, 2464) pixels
            Active Area:     (768, 692) to (3048, 2156) pixels  [within full sensor]
            Normalized:      (0.0, 0.0) to (1.0, 1.0)          [within active area]

        Returns:
            dict: {'x': float, 'y': float} - Normalized coordinates (0-1) of actual crop center
                  Returns requested center if calculation fails (graceful fallback)

        Example:
            User clicks at (0.5, 0.5) with 4:3 sensor → 16:9 output at zoom=1.0
            - Requested center: (0.5, 0.5)
            - Actual crop: vertically centered but height reduced to maintain 16:9
            - Actual center: (0.5, 0.5) - same because symmetric centering

            User clicks at (0.75, 0.25) near top-right edge with zoom=3.0
            - Requested center: (0.75, 0.25)
            - Actual crop: clamped to stay within bounds
            - Actual center: (0.68, 0.28) - shifted due to boundary clamping
        """
        # Default to requested center (graceful fallback)
        fallback = {"x": self.zoom_center_x, "y": self.zoom_center_y}

        if not self.camera or not self.streaming:
            return fallback

        # Get ScalerCropMaximum for coordinate space
        scaler_crop_max = self.camera.camera_properties.get("ScalerCropMaximum")
        if not scaler_crop_max:
            return fallback

        # Calculate actual ScalerCrop
        scaler_crop = self.calculate_scaler_crop()
        if not scaler_crop:
            return fallback

        # Extract coordinates
        x_offset_max, y_offset_max, sensor_width, sensor_height = scaler_crop_max
        offset_x_pixels, offset_y_pixels, crop_width, crop_height = scaler_crop

        # Calculate actual center in full sensor coordinates
        actual_center_x_pixels = offset_x_pixels + crop_width / 2
        actual_center_y_pixels = offset_y_pixels + crop_height / 2

        # Convert from full sensor coordinates back to normalized active area coordinates
        # Remove the ScalerCropMaximum offset to get position within active area
        actual_center_x_rel = actual_center_x_pixels - x_offset_max
        actual_center_y_rel = actual_center_y_pixels - y_offset_max

        # Normalize to 0-1 range relative to active area
        actual_center_x_normalized = actual_center_x_rel / sensor_width if sensor_width > 0 else 0.5
        actual_center_y_normalized = (
            actual_center_y_rel / sensor_height if sensor_height > 0 else 0.5
        )

        # Clamp to valid range (should already be valid, but defensive programming)
        actual_center_x_normalized = max(0.0, min(1.0, actual_center_x_normalized))
        actual_center_y_normalized = max(0.0, min(1.0, actual_center_y_normalized))

        return {"x": actual_center_x_normalized, "y": actual_center_y_normalized}

    def set_zoom(self, zoom_level, center_x=None, center_y=None):
        """
        Set digital zoom level and optionally reposition zoom center.

        Args:
            zoom_level (float): Zoom level, 1.0 = no zoom, 4.0 = 4x zoom
            center_x (float, optional): Normalized horizontal center (0-1), 0.5 = center
            center_y (float, optional): Normalized vertical center (0-1), 0.5 = center

        Returns:
            bool: True if successful, False if camera not ready

        Example:
            # 2x zoom centered
            set_zoom(2.0)

            # 3x zoom focused on upper-left quadrant
            set_zoom(3.0, center_x=0.25, center_y=0.25)
        """
        if not self.camera or not self.streaming:
            return False

        # Update zoom state
        self.zoom_level = max(1.0, min(zoom_level, 10.0))  # Clamp between 1x and 10x

        if center_x is not None:
            self.zoom_center_x = max(0.0, min(center_x, 1.0))  # Clamp 0-1
        if center_y is not None:
            self.zoom_center_y = max(0.0, min(center_y, 1.0))  # Clamp 0-1

        # Calculate ScalerCrop coordinates
        scaler_crop = self.calculate_scaler_crop()
        if not scaler_crop:
            print("⚠ Cannot calculate ScalerCrop - sensor resolution not available")
            return False

        # Apply ScalerCrop control
        try:
            self.camera.set_controls({"ScalerCrop": scaler_crop})

            # Re-apply AF window if active (preserve window when zoom changes)
            # AF window coordinates are in full sensor space (ScalerCropMaximum),
            # so they remain valid regardless of zoom level (ScalerCrop)
            self._reapply_af_window_if_active()

            print(
                f"✓ Zoom applied: {self.zoom_level:.2f}x at ({self.zoom_center_x:.2f}, {self.zoom_center_y:.2f})"
            )
            print(f"  ScalerCrop: {scaler_crop}")
            return True
        except Exception as e:
            print(f"⚠ Error setting zoom: {e}")
            return False

    def set_af_window(self, x, y, window_size=0.2):
        """
        Set autofocus window to focus on a specific region (click-to-focus feature)

        This method sets an AF window for continuous autofocus, directing focus
        to a specific area of the frame without interrupting the stream. Works
        with continuous AF (AfMode=2) to maintain focus on the selected region.

        Args:
            x (float): Normalized horizontal center (0-1), 0.5 = center
            y (float): Normalized vertical center (0-1), 0.5 = center
            window_size (float): Window size as fraction of frame (default 0.2 = 20%)

        Returns:
            bool: True if successful, False if camera not ready

        Example:
            # Focus on center of frame
            set_af_window(0.5, 0.5)

            # Focus on upper-left quadrant
            set_af_window(0.25, 0.25)

            # Clear AF window (reset to auto metering)
            set_af_window(None, None)
        """
        if not self.camera or not self.streaming:
            print("⚠ Cannot set AF window - camera not streaming")
            return False

        try:
            # Clear AF window if coordinates are None (reset to auto metering)
            if x is None or y is None:
                # IMPORTANT: Don't set AfWindows to empty list - causes libcamera assertion failure!
                # Setting AfMetering to Auto (0) is sufficient to reset to full-frame AF
                # libcamera will automatically ignore any previously set AfWindows
                self.camera.set_controls(
                    {
                        "AfMetering": 0  # Auto metering - resets to full frame AF
                    }
                )
                # Clear stored state
                self._af_window_active = False
                self._af_window_coords = None
                print("✓ AF window cleared - using auto metering")
                return True

            # Get full sensor coordinate system from ScalerCropMaximum
            # AfWindows uses absolute pixel coordinates referenced against ScalerCropMaximum
            # ScalerCropMaximum format: (x_offset, y_offset, width, height)
            # For full sensor: (0, 0, 9152, 6944) on Arducam 64MP
            # For sensor modes: (offset_x, offset_y, active_width, active_height)
            scaler_crop_max = self.camera.camera_properties.get("ScalerCropMaximum")
            if not scaler_crop_max:
                print("⚠ Cannot set AF window - ScalerCropMaximum not available")
                return False

            # Extract sensor dimensions AND offset from ScalerCropMaximum
            # The offset defines where the active area starts in full sensor coordinates
            x_offset, y_offset, sensor_width, sensor_height = scaler_crop_max

            # Clamp normalized coordinates to valid range
            x = max(0.0, min(x, 1.0))
            y = max(0.0, min(y, 1.0))

            # Calculate window dimensions in pixels (in PixelArraySize coordinate space)
            window_w_pixels = int(sensor_width * window_size)
            window_h_pixels = int(sensor_height * window_size)

            # Ensure minimum window size (at least 5% of frame)
            min_size_pixels = int(min(sensor_width, sensor_height) * 0.05)
            window_w_pixels = max(window_w_pixels, min_size_pixels)
            window_h_pixels = max(window_h_pixels, min_size_pixels)

            # Ensure even dimensions (required by some encoders)
            window_w_pixels = window_w_pixels & ~1
            window_h_pixels = window_h_pixels & ~1

            # Calculate window position relative to active area (top-left corner centered on click point)
            # Use round() instead of int() to avoid systematic left/top bias from truncation
            window_x_rel = round((x * sensor_width) - (window_w_pixels / 2))
            window_y_rel = round((y * sensor_height) - (window_h_pixels / 2))

            # Clamp position to active area bounds
            window_x_rel = max(0, min(window_x_rel, sensor_width - window_w_pixels))
            window_y_rel = max(0, min(window_y_rel, sensor_height - window_h_pixels))

            # Ensure even offsets (required by some encoders)
            window_x_rel = window_x_rel & ~1
            window_y_rel = window_y_rel & ~1

            # Add ScalerCropMaximum offset to convert to full sensor coordinates
            # The offset defines where the active area starts in the full sensor space
            # Example: ScalerCropMaximum=(784, 1312, 7712, 4352) means active area
            # starts at (784, 1312) in full sensor coordinates
            window_x_pixels = x_offset + window_x_rel
            window_y_pixels = y_offset + window_y_rel

            # Use absolute pixel coordinates as per libcamera specification
            # AfWindows expects (x, y, width, height) in sensor pixel coordinates
            # referenced against ScalerCropMaximum (NOT normalized 0-65535!)
            # For Arducam 64MP: center 20% window would be ~(3660, 2777, 1830, 1388) in pixels
            self._af_window_coords = (
                window_x_pixels,
                window_y_pixels,
                window_w_pixels,
                window_h_pixels,
            )
            self._af_window_active = True

            print(f"✓ AF window calculated: center=({x:.2f}, {y:.2f}) normalized")
            print(
                f"  ScalerCropMaximum: {scaler_crop_max} (offset={x_offset},{y_offset}, size={sensor_width}x{sensor_height})"
            )
            print(f"  Position in active area: ({window_x_rel}, {window_y_rel})")
            print(
                f"  Position in full sensor: ({window_x_pixels}, {window_y_pixels}) [with offset added]"
            )
            print(f"  Window size: {window_w_pixels}x{window_h_pixels}")
            print(f"  Full window coordinates: {self._af_window_coords}")

            # Apply controls in separate steps to verify each one
            # Step 1: Set AfMetering to Windows mode
            try:
                print("  → Setting AfMetering to Windows mode (1)...")
                self.camera.set_controls({"AfMetering": 1})
                time.sleep(0.05)  # Let control settle
                print("  ✓ AfMetering set successfully")
            except Exception as e:
                print(f"  ❌ ERROR setting AfMetering: {e}")
                import traceback

                traceback.print_exc()
                return False

            # Step 2: Set AfWindows with calculated coordinates
            try:
                print(f"  → Setting AfWindows: {self._af_window_coords}...")
                self.camera.set_controls({"AfWindows": [self._af_window_coords]})
                print("  ✓ AfWindows set successfully")
            except Exception as e:
                print(f"  ❌ ERROR setting AfWindows: {e}")
                import traceback

                traceback.print_exc()
                return False

            print("✓ AF window controls applied successfully")

            # DIAGNOSTIC: Verify controls were actually applied
            try:
                time.sleep(0.15)  # Let controls fully settle
                metadata = self.camera.capture_metadata()

                # Check what AF-related metadata is available
                af_state = metadata.get("AfState", "N/A")
                af_pause_state = metadata.get("AfPauseState", "N/A")
                lens_pos = metadata.get("LensPosition", "N/A")
                focus_fom = metadata.get("FocusFoM", "N/A")

                # CRITICAL: Check if AfMetering is actually being applied
                # If AfMetering isn't in metadata, the hardware may not support window mode
                # OR it might be a write-only control (driver limitation)
                af_metering = metadata.get("AfMetering", "N/A")

                # Decode AfState: 0=Idle, 1=Scanning, 2=Focused, 3=Failed
                af_state_name = {0: "Idle", 1: "Scanning", 2: "Focused", 3: "Failed"}.get(
                    af_state, af_state
                )
                # Decode AfPauseState: 0=Running, 1=Pausing, 2=Paused
                af_pause_name = {0: "Running", 1: "Pausing", 2: "Paused"}.get(
                    af_pause_state, af_pause_state
                )
                # Decode AfMetering: 0=Auto (full-frame), 1=Windows mode
                af_metering_name = {0: "Auto/FullFrame", 1: "Windows"}.get(af_metering, af_metering)

                print(
                    f"🔍 DIAGNOSTIC: AfState={af_state_name} ({af_state}), AfPauseState={af_pause_name} ({af_pause_state})"
                )
                print(
                    f"🔍 DIAGNOSTIC: AfMetering={af_metering_name} ({af_metering}) ← Should be 'Windows (1)'!"
                )
                print(f"🔍 DIAGNOSTIC: LensPosition={lens_pos}, FocusFoM={focus_fom}")

                if af_metering == "N/A":
                    print("⚠️  AfMetering not in metadata - may be write-only control")
                    print("ℹ️  To check for driver errors: dmesg | grep -i 'libcamera\\|pisp\\|af'")
                elif af_metering != 1:
                    print(f"❌ WARNING: AfMetering is {af_metering}, not 1 (Windows mode)!")
                    print("   This means windowed AF is NOT active - camera is using full-frame AF")
                    print("ℹ️  Possible causes:")
                    print("   - Driver/hardware limitation in this sensor mode")
                    print("   - Window coordinates rejected (check dmesg)")
                    print("   - AfMetering being overridden by another control")
                else:
                    print("✓ AfMetering = Windows mode - windowed AF should be active!")

            except Exception as diag_error:
                print(f"⚠️  Diagnostic read failed: {diag_error}")
                import traceback

                traceback.print_exc()

            return True

        except Exception as e:
            print(f"⚠ Error setting AF window: {e}")
            import traceback

            traceback.print_exc()
            return False

    def clear_af_window(self):
        """
        Clear active AF window and return to full-frame autofocus

        This is a convenience method that calls set_af_window(None, None)
        to reset autofocus metering to Auto mode (full frame).

        Returns:
            bool: True if successful, False if camera not ready

        Example:
            # Clear AF window and return to normal AF
            camera_streamer.clear_af_window()
        """
        return self.set_af_window(None, None)

    def set_manual_focus_mode(self, enabled=True):
        """
        Enable or disable manual focus mode override for AF preservation

        This method sets an AF mode override that persists across camera restarts.
        Used by the autofocus button to lock focus after autofocus completes.

        Args:
            enabled (bool): True to force manual focus (AfMode 0), False to use configured mode

        Returns:
            bool: True if override was set successfully

        Example:
            # After autofocus succeeds, preserve manual focus
            camera_streamer.set_manual_focus_mode(True)

            # Reset to configured AF mode from settings
            camera_streamer.set_manual_focus_mode(False)

        Note:
            The override takes effect on the next camera initialization (start_streaming).
            If camera is already streaming, the mode change applies immediately.
        """
        if enabled:
            self._af_mode_override = 0  # Manual focus (AfMode 0)
            print("✓ Manual focus mode override enabled (AfMode 0)")
        else:
            self._af_mode_override = None  # Use configured mode from settings
            print("✓ AF mode override cleared - using configured mode")

        # If camera is active, apply the change immediately
        if self.camera and self.streaming:
            try:
                af_mode_to_use = (
                    self._af_mode_override if self._af_mode_override is not None else self.af_mode
                )
                self.camera.set_controls({"AfMode": af_mode_to_use})

                # Re-apply AF window if active (preserve window state)
                # Note: AF window has no effect in manual focus mode (AfMode=0),
                # but we preserve it so it's ready when switching back to continuous AF
                self._reapply_af_window_if_active()

                print(f"✓ Applied AF mode change immediately: AfMode {af_mode_to_use}")
                return True
            except Exception as e:
                print(f"⚠ Error applying AF mode change: {e}")
                return False

        return True

    def cleanup(self):
        """
        Cleanup camera resources with timeout protection

        Improvements:
        - Waits for stream thread to fully stop before closing camera
        - Forces camera to None even on error to prevent state pollution
        - Increased timeout for camera close operation
        - Idempotent: Safe to call multiple times

        Called by:
        - atexit handler (registered in app.py)
        - Signal handlers (SIGTERM/SIGINT in app.py)
        - Test fixtures (conftest.py)
        """
        print("Cleaning up camera resources...")

        # Stop streaming gracefully
        self.stop_streaming()

        # Wait for stream thread to actually finish
        if self.stream_thread and self.stream_thread.is_alive():
            print("⏳ Waiting for stream thread to stop...")
            self.stream_thread.join(timeout=5.0)

            if self.stream_thread.is_alive():
                print("⚠️  Warning: Stream thread did not stop gracefully")

        # Close camera with timeout protection
        if self.camera:
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError

                # Check if camera is started before trying to stop
                try:
                    if hasattr(self.camera, "started") and self.camera.started:
                        self.camera.stop()
                except Exception as e:
                    print(f"⚠️  Note: Camera stop failed (may already be stopped): {e}")

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.camera.close)
                    try:
                        future.result(timeout=3.0)  # Increased from 2.0s
                        print("✓ Camera closed successfully")
                    except TimeoutError:
                        print("⚠️  Camera close timed out - forcing cleanup")
                    except Exception as e:
                        print(f"⚠️  Error closing camera: {e}")

            except Exception as e:
                # Catch any errors in the cleanup mechanism itself
                print(f"⚠️  Error during camera cleanup: {e}")
            finally:
                # ALWAYS set to None, even on error
                self.camera = None
                print("✓ Camera cleanup complete")
