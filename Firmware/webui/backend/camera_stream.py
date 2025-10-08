"""
Camera streaming module for WebSocket live preview
"""
import io
import time
import base64
from threading import Thread, Event
from PIL import Image

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except (ImportError, RuntimeError):
    PICAMERA_AVAILABLE = False
    print("Warning: picamera2 not available - camera preview disabled")


class CameraStreamer:
    """Handles live camera streaming via WebSocket"""

    def __init__(self, socketio):
        self.socketio = socketio
        self.camera = None
        self.streaming = False
        self.stream_thread = None
        self.stop_event = Event()

    def initialize_camera(self):
        """Initialize the camera for preview"""
        if not PICAMERA_AVAILABLE:
            return False

        try:
            if self.camera is None:
                # Try camera 0 first, fallback to camera 1
                try:
                    self.camera = Picamera2(0)
                except:
                    self.camera = Picamera2(1)

                # Configure for preview - 4:3 aspect ratio for better compatibility
                preview_config = self.camera.create_preview_configuration(
                    main={"size": (1024, 768), "format": "RGB888"}
                )
                self.camera.configure(preview_config)

                # Enable autofocus if available
                try:
                    self.camera.set_controls({"AfMode": 2, "AfTrigger": 0})  # Continuous autofocus
                except Exception as af_error:
                    print(f"Autofocus not available: {af_error}")

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
            except:
                pass

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
                    img.save(buffer, format='JPEG', quality=95, optimize=True)
                    buffer.seek(0)

                    # Convert to base64
                    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

                    # Emit to all connected clients
                    self.socketio.emit('camera_frame', {
                        'image': f'data:image/jpeg;base64,{img_base64}'
                    })

                    # Limit frame rate to ~10 fps
                    time.sleep(0.1)

                except Exception as e:
                    print(f"Error capturing frame: {e}")
                    time.sleep(0.5)

        finally:
            if self.camera:
                try:
                    self.camera.stop()
                except:
                    pass

    def cleanup(self):
        """Cleanup camera resources"""
        self.stop_streaming()
        if self.camera:
            try:
                self.camera.close()
            except:
                pass
            self.camera = None
