"""
Camera streaming module for WebSocket live preview
"""
import io
import time
import base64
from threading import Thread, Event, Lock
from contextlib import contextmanager
from PIL import Image
from pathlib import Path
import sys

# Setup path for mothbox imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values

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

# Default camera stream configuration constants
DEFAULT_PREVIEW_WIDTH = 1024
DEFAULT_PREVIEW_HEIGHT = 768
DEFAULT_PREVIEW_FORMAT = "BGR888"  # BGR888 produces true RGB order for correct colors
DEFAULT_FRAME_DELAY = 0.1  # seconds (10 fps)
DEFAULT_JPEG_QUALITY = 85  # Balanced quality - faster encoding, smaller files

# Global lock to prevent concurrent camera operations (autofocus, calibration, etc.)
# Picamera2 enforces exclusive hardware access - only one instance can exist at a time
CAMERA_OPERATION_LOCK = Lock()


class CameraStreamer:
    """Handles live camera streaming via WebSocket"""

    def __init__(self, socketio):
        self.socketio = socketio
        self.camera = None
        self.streaming = False
        self.stream_thread = None
        self.stop_event = Event()
        self.load_stream_settings()

    def load_stream_settings(self):
        """Load stream settings from configuration file"""
        self.preview_width = DEFAULT_PREVIEW_WIDTH
        self.preview_height = DEFAULT_PREVIEW_HEIGHT
        self.preview_format = DEFAULT_PREVIEW_FORMAT
        self.frame_delay = DEFAULT_FRAME_DELAY
        self.jpeg_quality = DEFAULT_JPEG_QUALITY
        self.stream_mode = 'simplejpeg'  # Default: fast software encoding

        # Image quality controls (Phase 2.1)
        self.sharpness = 1.0
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0

        # Focus controls (Phase 2.1)
        self.af_mode = 2  # Continuous autofocus by default
        self.af_speed = 0  # Normal speed
        self.af_range = 0  # Normal range

        # White balance controls (Phase 2.1)
        self.awb_enable = True
        self.awb_mode = 0  # Auto
        # ColourGains: Fixed gains for LED illumination (from TakePhoto.py calibration)
        # Important: These values lock down color balance under white LED flash
        self.colour_gains = (2.259, 1.500)  # (red, blue)

        # Digital zoom / ROI controls
        self.zoom_level = 1.0  # 1.0 = no zoom, 4.0 = 4x zoom
        self.zoom_center_x = 0.5  # Normalized 0-1, 0.5 = center
        self.zoom_center_y = 0.5  # Normalized 0-1, 0.5 = center
        self.sensor_resolution = None  # Will be set after camera initialization

        try:
            if WEBUI_SETTINGS_FILE.exists():
                settings = get_control_values(WEBUI_SETTINGS_FILE)

                # Load and validate settings
                if 'preview_width' in settings:
                    self.preview_width = int(settings['preview_width'])
                if 'preview_height' in settings:
                    self.preview_height = int(settings['preview_height'])
                if 'frame_rate' in settings:
                    fps = int(settings['frame_rate'])
                    self.frame_delay = 1.0 / fps if fps > 0 else DEFAULT_FRAME_DELAY
                if 'jpeg_quality' in settings:
                    self.jpeg_quality = int(settings['jpeg_quality'])
                if 'stream_mode' in settings:
                    self.stream_mode = settings['stream_mode']

                # Image quality settings (Phase 2.1)
                if 'sharpness' in settings:
                    self.sharpness = float(settings['sharpness'])
                if 'brightness' in settings:
                    self.brightness = float(settings['brightness'])
                if 'contrast' in settings:
                    self.contrast = float(settings['contrast'])
                if 'saturation' in settings:
                    self.saturation = float(settings['saturation'])

                # Focus settings (Phase 2.1)
                if 'af_mode' in settings:
                    self.af_mode = int(settings['af_mode'])
                if 'af_speed' in settings:
                    self.af_speed = int(settings['af_speed'])
                if 'af_range' in settings:
                    self.af_range = int(settings['af_range'])

                # White balance settings (Phase 2.1)
                if 'awb_enable' in settings:
                    self.awb_enable = settings['awb_enable'].lower() == 'true'
                if 'awb_mode' in settings:
                    self.awb_mode = int(settings['awb_mode'])

                # Colour gains (load red/blue separately if present)
                if 'colour_gains_red' in settings and 'colour_gains_blue' in settings:
                    self.colour_gains = (float(settings['colour_gains_red']),
                                        float(settings['colour_gains_blue']))

                print(f"Stream settings loaded: {self.preview_width}x{self.preview_height}, "
                      f"FPS: {1/self.frame_delay:.1f}, Quality: {self.jpeg_quality}, Mode: {self.stream_mode}")
                print(f"  Image quality: Sharp={self.sharpness}, Bright={self.brightness}, "
                      f"Contrast={self.contrast}, Sat={self.saturation}")
                print(f"  Focus: Mode={self.af_mode}, Speed={self.af_speed}, Range={self.af_range}")
                print(f"  White balance: AWB={self.awb_enable}, Mode={self.awb_mode}, ColourGains={self.colour_gains}")
        except Exception as e:
            print(f"Error loading stream settings, using defaults: {e}")

    def initialize_camera(self):
        """Initialize the camera for preview"""
        if not PICAMERA_AVAILABLE:
            return False

        try:
            if self.camera is None:
                # Try camera 0 first, fallback to camera 1
                try:
                    self.camera = Picamera2(0)
                    print("Using camera 0")
                except Exception as e:
                    print(f"Camera 0 unavailable ({e}), trying camera 1...")
                    self.camera = Picamera2(1)
                    print("Using camera 1")

                # Get sensor resolution for zoom calculations
                self.sensor_resolution = self.camera.camera_properties['PixelArraySize']
                print(f"Sensor resolution: {self.sensor_resolution}")

                # Configure for preview - 4:3 aspect ratio for better compatibility
                preview_config = self.camera.create_preview_configuration(
                    main={"size": (self.preview_width, self.preview_height), "format": self.preview_format}
                )
                self.camera.configure(preview_config)

                # Start camera to set controls
                self.camera.start()

                # Apply camera controls (Phase 2.1: expanded from basic AF to full controls)
                try:
                    controls_dict = {
                        # Focus controls
                        "AfMode": self.af_mode,
                        "AfSpeed": self.af_speed,
                        "AfRange": self.af_range,
                        "AfMetering": 0,  # Auto metering

                        # Image quality controls
                        "Sharpness": self.sharpness,
                        "Brightness": self.brightness,
                        "Contrast": self.contrast,
                        "Saturation": self.saturation,

                        # White balance controls
                        "AwbEnable": self.awb_enable,
                        # ColourGains: Critical for locking color balance under LED illumination
                        # Note: Must be set even with AwbEnable to lock white balance (TakePhoto.py:519)
                        "ColourGains": self.colour_gains,
                    }

                    # Only set AwbMode if AWB is disabled (manual mode)
                    if not self.awb_enable:
                        controls_dict["AwbMode"] = self.awb_mode

                    self.camera.set_controls(controls_dict)
                    print(f"Camera controls applied: AF Mode {self.af_mode}, "
                          f"Sharpness {self.sharpness}, AWB {'On' if self.awb_enable else 'Off'}, "
                          f"ColourGains {self.colour_gains}")
                except Exception as controls_error:
                    print(f"Camera controls configuration: {controls_error}")

                # Stop camera - will be started again by stream_loop
                self.camera.stop()

            return True
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
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

        Automatically falls back to software encoding if hardware encoder is unavailable.
        """
        if not HARDWARE_MJPEG_AVAILABLE:
            print("⚠ Hardware MJPEG not available, falling back to software encoding")
            self.socketio.emit('stream_warning', {
                'message': 'Hardware MJPEG unavailable, using software fallback'
            })
            return self._stream_software_encoding()

        try:
            # Create hardware MJPEG encoder with quality settings
            encoder = MJPEGEncoder(q=self.jpeg_quality)

            # Create custom output handler for WebSocket streaming
            class WebSocketOutput(FileOutput):
                """Custom output that emits MJPEG frames to WebSocket"""
                def __init__(self, socketio, frame_delay):
                    self.socketio = socketio
                    self.frame_delay = frame_delay
                    self.last_emit = 0
                    super().__init__()

                def outputframe(self, frame, keyframe=True, timestamp=None):
                    """Called by encoder for each MJPEG frame"""
                    current_time = time.time()

                    # Rate limit based on frame_delay
                    if current_time - self.last_emit < self.frame_delay:
                        return

                    self.last_emit = current_time

                    # Convert JPEG bytes to base64
                    img_base64 = base64.b64encode(frame).decode('utf-8')

                    # Emit to WebSocket
                    self.socketio.emit('camera_frame', {
                        'image': f'data:image/jpeg;base64,{img_base64}'
                    })

            # Configure camera for video (required for encoder)
            video_config = self.camera.create_video_configuration(
                main={"size": (self.preview_width, self.preview_height)},
                encode="main"
            )
            self.camera.configure(video_config)

            # Create WebSocket output handler
            output = WebSocketOutput(self.socketio, self.frame_delay)

            # Start encoder and camera
            self.camera.start_recording(encoder, output)
            print(f"✓ Hardware MJPEG streaming started at {self.preview_width}x{self.preview_height}")

            # Keep streaming until stopped
            while self.streaming and not self.stop_event.is_set():
                time.sleep(0.1)

        except Exception as e:
            print(f"⚠ Hardware MJPEG encoder failed: {e}")
            print("Falling back to software encoding...")
            self.socketio.emit('stream_warning', {
                'message': f'Hardware MJPEG error: {e}. Using software fallback.'
            })

            # Stop recording if started
            try:
                self.camera.stop_recording()
            except:
                pass

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
            self.camera.start()
            print(f"✓ Software encoding streaming started (mode: {'simplejpeg' if SIMPLEJPEG_AVAILABLE else 'PIL'})")

            while self.streaming and not self.stop_event.is_set():
                try:
                    # Capture frame
                    frame = self.camera.capture_array()

                    # Encode as JPEG using fastest available method
                    if SIMPLEJPEG_AVAILABLE:
                        # Fast path: simplejpeg (5-7x faster than PIL)
                        jpeg_bytes = simplejpeg.encode_jpeg(
                            frame,
                            quality=self.jpeg_quality,
                            colorspace='RGB'
                        )
                    else:
                        # Fallback path: PIL (slower, remove optimize=True for speed)
                        img = Image.fromarray(frame)
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=self.jpeg_quality)
                        buffer.seek(0)
                        jpeg_bytes = buffer.read()

                    # Convert to base64
                    img_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')

                    # Emit to all connected clients
                    self.socketio.emit('camera_frame', {
                        'image': f'data:image/jpeg;base64,{img_base64}'
                    })

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
            if self.stream_mode == 'mjpeg_hardware':
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
                    frame,
                    quality=self.jpeg_quality,
                    colorspace='RGB'
                )
            else:
                # Fallback to PIL
                img = Image.fromarray(frame)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=self.jpeg_quality)
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
        Update camera control(s) without restarting stream (Phase 2.1)

        Args:
            control_dict: Dictionary of control names and values
                          e.g., {"Sharpness": 2.0, "Brightness": 0.1}

        Returns:
            bool: True if successful, False if camera not ready
        """
        if self.camera and self.streaming:
            try:
                self.camera.set_controls(control_dict)
                print(f"Updated controls: {control_dict}")
                return True
            except Exception as e:
                print(f"Error updating controls: {e}")
                return False
        return False

    def calculate_scaler_crop(self):
        """
        Calculate ScalerCrop rectangle for current zoom level and center point.

        ScalerCrop uses absolute pixel coordinates relative to the full sensor resolution.
        Format: (offset_x, offset_y, width, height) in sensor pixels

        Returns:
            tuple: (x, y, width, height) ScalerCrop coordinates, or None if sensor not initialized

        Example:
            For 2x zoom centered on sensor:
            - Sensor: 4056x3040
            - Cropped size: 2028x1520 (50% of sensor)
            - Offset: (1014, 760) to center the crop
            - ScalerCrop: (1014, 760, 2028, 1520)
        """
        if not self.sensor_resolution:
            return None

        sensor_width, sensor_height = self.sensor_resolution

        # Calculate cropped dimensions (inverse of zoom level)
        # zoom=1.0 -> 100% of sensor, zoom=2.0 -> 50% of sensor, zoom=4.0 -> 25% of sensor
        crop_width = int(sensor_width / self.zoom_level)
        crop_height = int(sensor_height / self.zoom_level)

        # Ensure even dimensions (required by some encoders)
        crop_width = crop_width & ~1  # Clear lowest bit to make even
        crop_height = crop_height & ~1

        # Calculate offsets based on zoom center point
        # Center point is normalized (0-1), where 0.5,0.5 = center of sensor
        offset_x = int((sensor_width - crop_width) * self.zoom_center_x)
        offset_y = int((sensor_height - crop_height) * self.zoom_center_y)

        # Clamp offsets to valid range
        offset_x = max(0, min(offset_x, sensor_width - crop_width))
        offset_y = max(0, min(offset_y, sensor_height - crop_height))

        # Ensure even offsets (required by some encoders)
        offset_x = offset_x & ~1
        offset_y = offset_y & ~1

        return (offset_x, offset_y, crop_width, crop_height)

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
            print(f"✓ Zoom applied: {self.zoom_level:.2f}x at ({self.zoom_center_x:.2f}, {self.zoom_center_y:.2f})")
            print(f"  ScalerCrop: {scaler_crop}")
            return True
        except Exception as e:
            print(f"⚠ Error setting zoom: {e}")
            return False

    def cleanup(self):
        """
        Cleanup camera resources with timeout protection.

        Called by:
        - atexit handler (registered in app.py)
        - Signal handlers (SIGTERM/SIGINT in app.py)
        - Finally block (app.py main)
        """
        print("Cleaning up camera resources...")

        # Stop streaming gracefully
        self.stop_streaming()

        # Close camera with timeout protection
        if self.camera:
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.camera.close)
                    try:
                        future.result(timeout=2.0)
                        print("✓ Camera closed successfully")
                    except TimeoutError:
                        print("⚠ Camera close timed out - forcing cleanup")
                    except Exception as e:
                        print(f"⚠ Error closing camera: {e}")

            except Exception as e:
                # Catch any errors in the cleanup mechanism itself
                print(f"⚠ Error during camera cleanup: {e}")
            finally:
                self.camera = None
                print("✓ Camera cleanup complete")
