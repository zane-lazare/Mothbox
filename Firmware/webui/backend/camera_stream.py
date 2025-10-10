"""
Camera streaming module for WebSocket live preview
"""
import io
import time
import base64
from threading import Thread, Event
from PIL import Image
from pathlib import Path
import sys

# Setup path for mothbox imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import WEBUI_SETTINGS_FILE, get_control_values

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except (ImportError, RuntimeError):
    PICAMERA_AVAILABLE = False
    print("Warning: picamera2 not available - camera preview disabled")

# Default camera stream configuration constants
DEFAULT_PREVIEW_WIDTH = 1024
DEFAULT_PREVIEW_HEIGHT = 768
DEFAULT_PREVIEW_FORMAT = "RGB888"
DEFAULT_FRAME_DELAY = 0.1  # seconds (10 fps)
DEFAULT_JPEG_QUALITY = 95


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

                print(f"Stream settings loaded: {self.preview_width}x{self.preview_height}, "
                      f"FPS: {1/self.frame_delay:.1f}, Quality: {self.jpeg_quality}")
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

                # Configure for preview - 4:3 aspect ratio for better compatibility
                preview_config = self.camera.create_preview_configuration(
                    main={"size": (self.preview_width, self.preview_height), "format": self.preview_format}
                )
                self.camera.configure(preview_config)

                # Start camera to set controls
                self.camera.start()

                # Enable continuous autofocus for Arducam Owlsight
                try:
                    # AfMode: 2 = Continuous autofocus
                    # AfSpeed: 0 = Normal (1 = Fast)
                    self.camera.set_controls({
                        "AfMode": 2,
                        "AfSpeed": 0,
                        "AfMetering": 0  # Auto metering
                    })
                    print("Autofocus enabled: Continuous mode")
                except Exception as af_error:
                    print(f"Autofocus configuration: {af_error}")

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

    def _stream_loop(self):
        """Main streaming loop - captures and emits frames"""
        try:
            self.camera.start()

            while self.streaming and not self.stop_event.is_set():
                try:
                    # Capture frame
                    frame = self.camera.capture_array()

                    # Convert to PIL Image
                    img = Image.fromarray(frame)

                    # Encode as JPEG with higher quality
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=self.jpeg_quality, optimize=True)
                    buffer.seek(0)

                    # Convert to base64
                    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

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
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError("Camera close operation timed out")

                # Set 2-second timeout for camera.close()
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(2)

                try:
                    self.camera.close()
                    print("✓ Camera closed successfully")
                except TimeoutError:
                    print("⚠ Camera close timed out - forcing cleanup")
                except Exception as e:
                    print(f"⚠ Error closing camera: {e}")
                finally:
                    signal.alarm(0)  # Cancel alarm
                    signal.signal(signal.SIGALRM, old_handler)  # Restore handler

            except Exception as e:
                # Catch any errors in the timeout mechanism itself
                print(f"⚠ Error during camera cleanup: {e}")
            finally:
                self.camera = None
                print("✓ Camera cleanup complete")
