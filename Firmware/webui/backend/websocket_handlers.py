"""
WebSocket Event Handlers for Mothbox Web UI

Provides WebSocket event handlers for real-time camera control and monitoring.
Handlers are registered with Flask-SocketIO and handle events like:
- Connection management (connect, disconnect)
- Live view streaming (start_liveview, stop_liveview)
- Live controls (update_liveview_control, set_zoom, set_af_window)
- Metadata polling (get_metadata)

This module is imported by both app.py (production) and conftest.py (testing).

Architecture:
    The register_handlers() function takes a SocketIO instance and LiveViewStreamer
    instance and registers all event handlers. This allows both production and test
    code to use the exact same handlers, eliminating duplication and ensuring tests
    accurately reflect production behavior.

Usage:
    # In app.py (production)
    from websocket_handlers import register_handlers
    register_handlers(socketio, liveview_streamer)

    # In conftest.py (testing)
    from websocket_handlers import register_handlers
    register_handlers(socketio, liveview_streamer)
"""

# Import camera control mapping
from camera_control_mapping import from_picamera_metadata
from flask_socketio import emit


def register_handlers(socketio, camera_streamer):
    """
    Register all WebSocket event handlers with SocketIO instance

    Args:
        socketio: Flask-SocketIO instance
        camera_streamer: LiveViewStreamer instance for live view operations

    Registers the following event handlers:
        - connect: Handle client WebSocket connection with origin validation
        - disconnect: Handle client WebSocket disconnection
        - start_liveview: Start live view streaming
        - stop_liveview: Stop live view streaming
        - reload_stream_settings: Reload live view stream settings from config file
        - get_metadata: Get current camera metadata
        - update_liveview_control: Update a single camera control without restarting stream
        - set_zoom: Set digital zoom level and optionally reposition zoom center
        - set_af_window: Set autofocus window to focus on a specific region

    Usage:
        # In app.py
        from websocket_handlers import register_handlers
        register_handlers(socketio, liveview_streamer)

        # In conftest.py
        from websocket_handlers import register_handlers
        register_handlers(socketio, liveview_streamer)
    """

    @socketio.on("connect")
    def handle_connect(auth=None):
        """Handle client WebSocket connection with origin validation"""
        # Get config for CORS validation
        from config import get_config
        from flask import request

        config = get_config()

        # Validate Origin header to prevent cross-site WebSocket hijacking
        # This protects against malicious websites attempting to control GPIO hardware
        origin = request.headers.get("Origin")

        if origin:
            # Determine allowed origins based on configuration
            if config.CORS_ORIGINS:
                # Development/testing: use configured CORS origins
                allowed_origins = config.CORS_ORIGINS
            else:
                # Production: enforce same-origin policy
                # Build same-origin URL from request Host header
                host = request.headers.get("Host")
                scheme = "https" if request.is_secure else "http"
                allowed_origins = [f"{scheme}://{host}"]

            # Check if origin is allowed
            # Special case: '*' means allow all origins (wildcard)
            if allowed_origins == "*":
                # Wildcard: allow any origin
                pass
            elif origin not in allowed_origins:
                # Not in allowed list: reject connection
                print(f"⚠ WebSocket connection rejected from unauthorized origin: {origin}")
                print(f"  Allowed origins: {allowed_origins}")
                return False  # Reject connection

        # Origin validated (or no origin header - local connections like curl)
        client_ip = request.remote_addr
        print(f"✓ Client connected from {client_ip}")
        emit("connected", {"status": "connected", "message": "Successfully connected to Mothbox"})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client WebSocket disconnection"""
        print("Client disconnected - stopping live view if active")
        camera_streamer.stop_streaming()

    # New event names
    @socketio.on("start_liveview")
    def handle_start_liveview():
        """Start live view streaming"""
        print("Received start_liveview request")
        try:
            success = camera_streamer.start_streaming()
            if success:
                print("Live view started successfully")
                emit("liveview_status", {"streaming": True, "message": "Live view started"})
            else:
                print("Failed to start live view")
                emit(
                    "liveview_status", {"streaming": False, "error": "Failed to initialize camera"}
                )
        except Exception as e:
            print(f"Error starting live view: {e}")
            emit("liveview_status", {"streaming": False, "error": str(e)})

    @socketio.on("stop_liveview")
    def handle_stop_liveview():
        """Stop live view streaming"""
        print("Received stop_liveview request")
        try:
            camera_streamer.stop_streaming()
            print("Live view stopped")
            emit("liveview_status", {"streaming": False, "message": "Live view stopped"})
        except Exception as e:
            print(f"Error stopping live view: {e}")
            emit("liveview_status", {"streaming": False, "error": str(e)})

    # Deprecated event names (backward compatibility - will be removed in future release)
    @socketio.on("start_preview")
    def handle_start_preview_deprecated():
        """[DEPRECATED] Use start_liveview instead"""
        print("⚠️  DEPRECATED: start_preview event - use start_liveview instead")
        handle_start_liveview()

    @socketio.on("stop_preview")
    def handle_stop_preview_deprecated():
        """[DEPRECATED] Use stop_liveview instead"""
        print("⚠️  DEPRECATED: stop_preview event - use stop_liveview instead")
        handle_stop_liveview()

    @socketio.on("reload_stream_settings")
    def handle_reload_stream_settings():
        """Reload camera stream settings from config file"""
        print("Received reload_stream_settings request")
        try:
            camera_streamer.load_stream_settings()
            print("Stream settings reloaded successfully")
            emit(
                "settings_reloaded",
                {
                    "success": True,
                    "message": "Settings reloaded. Changes will apply to new preview sessions.",
                },
            )
        except Exception as e:
            print(f"Error reloading settings: {e}")
            emit("settings_reloaded", {"success": False, "error": str(e)})

    @socketio.on("get_metadata")
    def handle_get_metadata():
        """
        Get current camera metadata

        Returns real-time camera metadata for display in UI:
        - ExposureTime (µs)
        - AnalogueGain (ISO)
        - LensPosition (diopters)
        - AfState (Idle/Scanning/Success/Fail)
        - ColourTemperature (Kelvin)
        - DigitalGain (software amplification)
        - FocusFoM (Focus Figure of Merit - sharpness score)
        - SensorTimestamp (microseconds)
        - ColourGains (red/blue gains)
        - FrameDuration (actual frame time in microseconds)
        - SensorBlackLevel (dark current offset)
        - SensorTemperature (if available)
        - ScalerCrop (digital zoom crop coordinates)
        - AeLocked (auto-exposure lock state)
        - AwbLocked (auto white balance lock state)
        - LuxValue (scene brightness estimate)
        - Saturation (applied saturation value)
        - Contrast (applied contrast value)
        - Sharpness (applied sharpness value)
        - Brightness (applied brightness value)
        """
        try:
            if camera_streamer.camera and camera_streamer.streaming:
                # Camera is active - get live metadata
                # Note: During hardware MJPEG recording, capture_request() returns stale
                # ExposureTime and ColourTemperature. Use capture_metadata() instead.
                try:
                    # Use capture_metadata which works better during hardware MJPEG
                    md = camera_streamer.camera.capture_metadata()
                except Exception as e:
                    print(f"Failed to get metadata via capture_metadata: {e}")
                    # Fallback: try request-based metadata
                    try:
                        request = camera_streamer.camera.capture_request()
                        md = request.get_metadata()
                        request.release()
                    except Exception as e2:
                        print(f"Failed to get metadata via capture_request: {e2}")
                        raise

                # Use centralized mapping from camera_control_mapping.py
                # This eliminates manual PascalCase → snake_case conversion (30+ fields)
                metadata_snake = from_picamera_metadata(md)

                # Convert AfState code to string (keep existing logic)
                af_state_code = metadata_snake.get("af_state", 0)
                af_state = (
                    ("Idle", "Scanning", "Success", "Fail")[af_state_code]
                    if af_state_code < 4
                    else "Unknown"
                )

                # ========================================
                # Coordinate Transformation System
                # ========================================
                # The following calculations provide the frontend with a coordinate transformation
                # matrix consisting of 4 values: actual_zoom_center_x/y and crop_fraction_x/y.
                # These enable accurate bidirectional transformation between viewport and sensor coordinates.
                #
                # Coordinate Systems:
                #   1. Viewport Space: (0-1) normalized to visible frame on screen
                #      - What the user sees and interacts with (click positions)
                #   2. Sensor Space: (0-1) normalized to ScalerCropMaximum active area
                #      - Internal camera coordinate system for zoom/focus operations
                #   3. Full Sensor Space: pixel coordinates in ScalerCropMaximum system
                #      - Hardware-level coordinates used by libcamera
                #
                # Transformation Flow:
                #   User clicks viewport (0.75, 0.5)
                #   → Frontend transforms to sensor coords using crop fractions
                #   → Backend applies to hardware (set_zoom, set_af_window)
                #   → Hardware returns actual crop position via ScalerCrop
                #   → Backend calculates actual center + fractions
                #   → Frontend uses these to position the marker overlay
                #
                # Why 4 values are needed:
                #   - actual_zoom_center_x/y: Where crop ACTUALLY ended up (may differ from requested)
                #     * Accounts for boundary clamping (zooming near edges)
                #     * Accounts for even dimension enforcement (pixel alignment)
                #     * Accounts for aspect ratio preservation (may shift position)
                #   - crop_fraction_x/y: How much of sensor is visible (for inverse transform)
                #     * Symmetric when sensor and output have same aspect ratio (16:9 → 16:9)
                #     * Asymmetric when aspect ratios differ (4:3 → 16:9)
                #     * Required for accurate viewport ↔ sensor coordinate conversion
                #
                # Example: 4:3 sensor (2312x1736) → 16:9 output (1920x1080) at 1.0x zoom
                #   crop_fraction_x ≈ 1.0 (full width used)
                #   crop_fraction_y ≈ 0.75 (height cropped to maintain 16:9, prevents distortion)
                #   Frontend click at viewport (0.5, 0.5) correctly maps to sensor (0.5, 0.5)
                #   Without separate fractions, Y coordinate would be wrong by ~15%
                #
                # Fallback Behavior:
                #   If camera not initialized or ScalerCrop unavailable:
                #   - actual_zoom_center falls back to (0.5, 0.5)
                #   - crop_fractions fall back to symmetric (1.0 / zoom_level)
                #   This is less accurate but prevents UI breakage during initialization
                #
                # See also:
                #   - calculate_scaler_crop() in liveview_stream.py: Calculates the crop
                #   - get_actual_zoom_center() in liveview_stream.py: Calculates actual center
                #   - handleImageClick() in Camera.jsx: Forward transform (viewport → sensor)
                #   - Marker rendering in Camera.jsx: Inverse transform (sensor → viewport)

                # Get actual zoom center (accounts for aspect ratio preservation and clamping)
                # This tells the frontend where the area of interest marker should actually be displayed
                try:
                    actual_zoom_center = camera_streamer.get_actual_zoom_center()
                except Exception as e:
                    print(f"Warning: Failed to get actual zoom center: {e}")
                    actual_zoom_center = {"x": 0.5, "y": 0.5}  # Fallback to center

                # Calculate crop fractions for accurate coordinate transformation
                # These account for aspect ratio preservation (e.g., 4:3 sensor → 16:9 output)
                try:
                    scaler_crop_result = camera_streamer.calculate_scaler_crop()
                    scaler_crop_max = camera_streamer.camera.camera_properties.get(
                        "ScalerCropMaximum"
                    )

                    if scaler_crop_result and scaler_crop_max:
                        _, _, sensor_width, sensor_height = scaler_crop_max
                        _, _, crop_width, crop_height = scaler_crop_result

                        # Calculate actual visible fractions (handles asymmetric crops)
                        crop_fraction_x = crop_width / sensor_width if sensor_width > 0 else 1.0
                        crop_fraction_y = crop_height / sensor_height if sensor_height > 0 else 1.0
                    else:
                        # Fallback: assume no aspect ratio preservation
                        crop_fraction_x = 1.0 / camera_streamer.zoom_level
                        crop_fraction_y = 1.0 / camera_streamer.zoom_level
                except Exception as e:
                    print(f"Warning: Failed to calculate crop fractions: {e}")
                    crop_fraction_x = 1.0 / camera_streamer.zoom_level
                    crop_fraction_y = 1.0 / camera_streamer.zoom_level

                # Apply rounding to specific fields
                rounded_metadata = {
                    **metadata_snake,
                    "af_state": af_state,  # Use converted string
                    "analogue_gain": round(metadata_snake.get("analogue_gain", 0.0), 2),
                    "lens_position": round(metadata_snake.get("lens_position", 0.0), 2),
                    "digital_gain": round(metadata_snake.get("digital_gain", 0.0), 2),
                    "focus_fom": round(metadata_snake.get("focus_fom", 0), 3)
                    if metadata_snake.get("focus_fom")
                    else 0,  # Figure of Merit - autofocus quality metric (higher = sharper)
                    "colour_gains": tuple(
                        round(g, 2) for g in metadata_snake.get("colour_gains", (0.0, 0.0))
                    )
                    if metadata_snake.get("colour_gains")
                    else (0.0, 0.0),
                    "sensor_temperature": round(metadata_snake.get("sensor_temperature", 0), 1)
                    if metadata_snake.get("sensor_temperature") is not None
                    else None,
                    "saturation": round(metadata_snake.get("saturation", 0.0), 2),
                    "contrast": round(metadata_snake.get("contrast", 0.0), 2),
                    "sharpness": round(metadata_snake.get("sharpness", 0.0), 2),
                    "brightness": round(metadata_snake.get("brightness", 0.0), 2),
                    # Zoom metadata
                    "actual_zoom_center_x": round(actual_zoom_center["x"], 4),
                    "actual_zoom_center_y": round(actual_zoom_center["y"], 4),
                    "crop_fraction_x": round(crop_fraction_x, 4),
                    "crop_fraction_y": round(crop_fraction_y, 4),
                    "timestamp": __import__("time").time(),
                }

                emit("metadata_update", rounded_metadata)

            else:
                # Camera not active - return unavailable status
                emit(
                    "metadata_update",
                    {
                        "error": "Camera not streaming",
                        "exposure_time": 0,
                        "analogue_gain": 0,
                        "lens_position": 0,
                        "af_state": "Unavailable",
                        "colour_temperature": 0,
                        "digital_gain": 0,
                        "focus_fom": 0,  # Figure of Merit - autofocus quality/sharpness indicator
                        "sensor_timestamp": 0,
                        "colour_gains": (0.0, 0.0),
                        "frame_duration": 0,
                        "sensor_black_level": 0,
                        "sensor_temperature": None,
                        "scaler_crop": (0, 0, 0, 0),
                        "ae_locked": False,
                        "awb_locked": False,
                        "lux": 0,
                        "saturation": 0,
                        "contrast": 0,
                        "sharpness": 0,
                        "brightness": 0,
                        "actual_zoom_center_x": 0.5,
                        "actual_zoom_center_y": 0.5,
                        "crop_fraction_x": 1.0,
                        "crop_fraction_y": 1.0,
                    },
                )

        except Exception as e:
            print(f"Error getting metadata: {e}")
            emit(
                "metadata_update",
                {
                    "error": str(e),
                    "exposure_time": 0,
                    "analogue_gain": 0,
                    "lens_position": 0,
                    "af_state": "Error",
                    "colour_temperature": 0,
                    "digital_gain": 0,
                    "focus_fom": 0,  # Figure of Merit - autofocus quality/sharpness indicator
                    "sensor_timestamp": 0,
                    "colour_gains": (0.0, 0.0),
                    "frame_duration": 0,
                    "sensor_black_level": 0,
                    "sensor_temperature": None,
                    "scaler_crop": (0, 0, 0, 0),
                    "ae_locked": False,
                    "awb_locked": False,
                    "lux": 0,
                    "saturation": 0,
                    "contrast": 0,
                    "sharpness": 0,
                    "brightness": 0,
                    "actual_zoom_center_x": 0.5,
                    "actual_zoom_center_y": 0.5,
                },
            )

    @socketio.on("update_liveview_control")
    def handle_update_liveview_control(data):
        """
        Update a single camera control without restarting stream

        Args:
            data: dict with control name and value, e.g., {'Sharpness': 2.0}
        """
        try:
            if not isinstance(data, dict):
                emit(
                    "control_updated",
                    {"success": False, "error": "Invalid data format - expected dict"},
                )
                return

            success = camera_streamer.update_control(data)

            if success:
                emit(
                    "control_updated",
                    {
                        "success": True,
                        "control": data,
                        "message": f"Updated {list(data.keys())[0]}",
                    },
                )
            else:
                emit(
                    "control_updated",
                    {"success": False, "error": "Camera not streaming or control update failed"},
                )

        except Exception as e:
            print(f"Error updating control: {e}")
            emit("control_updated", {"success": False, "error": str(e)})

    # Deprecated event name (backward compatibility)
    @socketio.on("update_preview_control")
    def handle_update_preview_control_deprecated(data):
        """[DEPRECATED] Use update_liveview_control instead"""
        print("⚠️  DEPRECATED: update_preview_control event - use update_liveview_control instead")
        handle_update_liveview_control(data)

    @socketio.on("set_zoom")
    def handle_set_zoom(data):
        """
        Set digital zoom level and optionally reposition zoom center (ROI feature)

        Args:
            data: dict with zoom parameters:
                - zoom_level (float): Zoom level, 1.0 = no zoom, 4.0 = 4x zoom
                - center_x (float, optional): Normalized horizontal center (0-1), 0.5 = center
                - center_y (float, optional): Normalized vertical center (0-1), 0.5 = center

        Example:
            {'zoom_level': 2.0}  # 2x zoom, centered
            {'zoom_level': 3.0, 'center_x': 0.25, 'center_y': 0.25}  # 3x zoom, upper-left
        """
        try:
            if not isinstance(data, dict):
                emit(
                    "zoom_updated",
                    {"success": False, "error": "Invalid data format - expected dict"},
                )
                return

            zoom_level = data.get("zoom_level", 1.0)
            center_x = data.get("center_x")
            center_y = data.get("center_y")

            success = camera_streamer.set_zoom(zoom_level, center_x, center_y)

            if success:
                emit(
                    "zoom_updated",
                    {
                        "success": True,
                        "zoom_level": camera_streamer.zoom_level,
                        "center_x": camera_streamer.zoom_center_x,
                        "center_y": camera_streamer.zoom_center_y,
                        "message": f"Zoom set to {camera_streamer.zoom_level:.2f}x",
                    },
                )
            else:
                emit(
                    "zoom_updated",
                    {"success": False, "error": "Camera not streaming or zoom failed"},
                )

        except Exception as e:
            print(f"Error setting zoom: {e}")
            emit("zoom_updated", {"success": False, "error": str(e)})

    @socketio.on("set_af_window")
    def handle_set_af_window(data):
        """
        Set autofocus window to focus on a specific region (click-to-focus feature)

        Args:
            data: dict with AF window parameters:
                - x (float): Normalized horizontal center (0-1), 0.5 = center
                - y (float): Normalized vertical center (0-1), 0.5 = center
                - window_size (float, optional): Window size as fraction of frame (default 0.2)

        Example:
            {'x': 0.5, 'y': 0.5}  # Focus on center
            {'x': 0.25, 'y': 0.25, 'window_size': 0.15}  # Focus on upper-left, 15% window
            {'x': None, 'y': None}  # Clear AF window (reset to auto metering)
        """
        try:
            if not isinstance(data, dict):
                emit(
                    "af_window_updated",
                    {"success": False, "error": "Invalid data format - expected dict"},
                )
                return

            x = data.get("x")
            y = data.get("y")
            window_size = data.get("window_size", 0.2)

            success = camera_streamer.set_af_window(x, y, window_size)

            if success:
                # Send success response with window coordinates
                response = {"success": True, "x": x, "y": y, "window_size": window_size}

                # Add message based on whether window was set or cleared
                if x is None or y is None:
                    response["message"] = "AF window cleared - using auto metering"
                else:
                    response["message"] = f"AF window set at ({x:.2f}, {y:.2f})"

                emit("af_window_updated", response)
            else:
                emit(
                    "af_window_updated",
                    {"success": False, "error": "Camera not streaming or AF window update failed"},
                )

        except Exception as e:
            print(f"Error setting AF window: {e}")
            emit("af_window_updated", {"success": False, "error": str(e)})
