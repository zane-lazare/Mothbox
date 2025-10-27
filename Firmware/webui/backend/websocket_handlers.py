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

    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle client WebSocket connection with origin validation"""
        from flask import request

        # Get config for CORS validation
        from config import get_config
        config = get_config()

        # Validate Origin header to prevent cross-site WebSocket hijacking
        # This protects against malicious websites attempting to control GPIO hardware
        origin = request.headers.get('Origin')

        if origin:
            # Determine allowed origins based on configuration
            if config.CORS_ORIGINS:
                # Development/testing: use configured CORS origins
                allowed_origins = config.CORS_ORIGINS
            else:
                # Production: enforce same-origin policy
                # Build same-origin URL from request Host header
                host = request.headers.get('Host')
                scheme = 'https' if request.is_secure else 'http'
                allowed_origins = [f"{scheme}://{host}"]

            # Check if origin is allowed
            # Special case: '*' means allow all origins (wildcard)
            if allowed_origins == '*':
                # Wildcard: allow any origin
                pass
            elif origin not in allowed_origins:
                # Not in allowed list: reject connection
                print(f"⚠ WebSocket connection rejected from unauthorized origin: {origin}")
                print(f"  Allowed origins: {allowed_origins}")
                return False  # Reject connection

        # Origin validated (or no origin header - local connections like curl)
        client_ip = request.remote_addr
        print(f'✓ Client connected from {client_ip}')
        emit('connected', {'status': 'connected', 'message': 'Successfully connected to Mothbox'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client WebSocket disconnection"""
        print('Client disconnected - stopping live view if active')
        camera_streamer.stop_streaming()

    # New event names
    @socketio.on('start_liveview')
    def handle_start_liveview():
        """Start live view streaming"""
        print('Received start_liveview request')
        try:
            success = camera_streamer.start_streaming()
            if success:
                print('Live view started successfully')
                emit('liveview_status', {'streaming': True, 'message': 'Live view started'})
            else:
                print('Failed to start live view')
                emit('liveview_status', {'streaming': False, 'error': 'Failed to initialize camera'})
        except Exception as e:
            print(f'Error starting live view: {e}')
            emit('liveview_status', {'streaming': False, 'error': str(e)})

    @socketio.on('stop_liveview')
    def handle_stop_liveview():
        """Stop live view streaming"""
        print('Received stop_liveview request')
        try:
            camera_streamer.stop_streaming()
            print('Live view stopped')
            emit('liveview_status', {'streaming': False, 'message': 'Live view stopped'})
        except Exception as e:
            print(f'Error stopping live view: {e}')
            emit('liveview_status', {'streaming': False, 'error': str(e)})

    # Deprecated event names (backward compatibility - will be removed in future release)
    @socketio.on('start_preview')
    def handle_start_preview_deprecated():
        """[DEPRECATED] Use start_liveview instead"""
        print('⚠️  DEPRECATED: start_preview event - use start_liveview instead')
        handle_start_liveview()

    @socketio.on('stop_preview')
    def handle_stop_preview_deprecated():
        """[DEPRECATED] Use stop_liveview instead"""
        print('⚠️  DEPRECATED: stop_preview event - use stop_liveview instead')
        handle_stop_liveview()

    @socketio.on('reload_stream_settings')
    def handle_reload_stream_settings():
        """Reload camera stream settings from config file"""
        print('Received reload_stream_settings request')
        try:
            camera_streamer.load_stream_settings()
            print('Stream settings reloaded successfully')
            emit('settings_reloaded', {'success': True, 'message': 'Settings reloaded. Changes will apply to new preview sessions.'})
        except Exception as e:
            print(f'Error reloading settings: {e}')
            emit('settings_reloaded', {'success': False, 'error': str(e)})

    @socketio.on('get_metadata')
    def handle_get_metadata():
        """
        Get current camera metadata (Phase 2.2)

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

                # Extract primary metadata fields (existing)
                exposure_time = md.get('ExposureTime', 0)
                analogue_gain = md.get('AnalogueGain', 0.0)
                lens_position = md.get('LensPosition', 0.0)
                af_state_code = md.get('AfState', 0)
                colour_temp = md.get('ColourTemperature', 0)

                # Extract extended metadata fields (new)
                digital_gain = md.get('DigitalGain', 0.0)
                focus_fom = md.get('FocusFoM', 0)
                sensor_timestamp = md.get('SensorTimestamp', 0)
                colour_gains = md.get('ColourGains', (0.0, 0.0))
                frame_duration = md.get('FrameDuration', 0)
                sensor_black_level = md.get('SensorBlackLevel', 0)
                sensor_temperature = md.get('SensorTemperature', None)
                scaler_crop = md.get('ScalerCrop', (0, 0, 0, 0))
                ae_locked = md.get('AeLocked', False)
                awb_locked = md.get('AwbLocked', False)
                lux = md.get('Lux', 0)
                saturation = md.get('Saturation', 0.0)
                contrast = md.get('Contrast', 0.0)
                sharpness = md.get('Sharpness', 0.0)
                brightness = md.get('Brightness', 0.0)

                # Convert AfState code to string
                af_state = ("Idle", "Scanning", "Success", "Fail")[af_state_code] if af_state_code < 4 else "Unknown"

                # Get actual zoom center (accounts for aspect ratio preservation and clamping)
                # This tells the frontend where the crosshair should actually be displayed
                actual_zoom_center = camera_streamer.get_actual_zoom_center()

                emit('metadata_update', {
                    # Primary metadata (existing)
                    'exposure_time': exposure_time,
                    'analogue_gain': round(analogue_gain, 2),
                    'lens_position': round(lens_position, 2),
                    'af_state': af_state,
                    'colour_temperature': colour_temp,
                    # Extended metadata (new)
                    'digital_gain': round(digital_gain, 2),
                    'focus_fom': round(focus_fom, 3) if focus_fom else 0,
                    'sensor_timestamp': sensor_timestamp,
                    'colour_gains': (round(colour_gains[0], 2), round(colour_gains[1], 2)) if len(colour_gains) >= 2 else (0.0, 0.0),
                    'frame_duration': frame_duration,
                    'sensor_black_level': sensor_black_level,
                    'sensor_temperature': round(sensor_temperature, 1) if sensor_temperature is not None else None,
                    'scaler_crop': scaler_crop if scaler_crop else (0, 0, 0, 0),
                    'ae_locked': ae_locked,
                    'awb_locked': awb_locked,
                    'lux': lux,
                    'saturation': round(saturation, 2),
                    'contrast': round(contrast, 2),
                    'sharpness': round(sharpness, 2),
                    'brightness': round(brightness, 2),
                    # Zoom metadata (Issue #52 fix)
                    'actual_zoom_center_x': round(actual_zoom_center['x'], 4),
                    'actual_zoom_center_y': round(actual_zoom_center['y'], 4),
                    'timestamp': __import__('time').time()
                })

            else:
                # Camera not active - return unavailable status
                emit('metadata_update', {
                    'error': 'Camera not streaming',
                    'exposure_time': 0,
                    'analogue_gain': 0,
                    'lens_position': 0,
                    'af_state': 'Unavailable',
                    'colour_temperature': 0,
                    'digital_gain': 0,
                    'focus_fom': 0,
                    'sensor_timestamp': 0,
                    'colour_gains': (0.0, 0.0),
                    'frame_duration': 0,
                    'sensor_black_level': 0,
                    'sensor_temperature': None,
                    'scaler_crop': (0, 0, 0, 0),
                    'ae_locked': False,
                    'awb_locked': False,
                    'lux': 0,
                    'saturation': 0,
                    'contrast': 0,
                    'sharpness': 0,
                    'brightness': 0,
                    'actual_zoom_center_x': 0.5,
                    'actual_zoom_center_y': 0.5
                })

        except Exception as e:
            print(f'Error getting metadata: {e}')
            emit('metadata_update', {
                'error': str(e),
                'exposure_time': 0,
                'analogue_gain': 0,
                'lens_position': 0,
                'af_state': 'Error',
                'colour_temperature': 0,
                'digital_gain': 0,
                'focus_fom': 0,
                'sensor_timestamp': 0,
                'colour_gains': (0.0, 0.0),
                'frame_duration': 0,
                'sensor_black_level': 0,
                'sensor_temperature': None,
                'scaler_crop': (0, 0, 0, 0),
                'ae_locked': False,
                'awb_locked': False,
                'lux': 0,
                'saturation': 0,
                'contrast': 0,
                'sharpness': 0,
                'brightness': 0,
                'actual_zoom_center_x': 0.5,
                'actual_zoom_center_y': 0.5
            })

    @socketio.on('update_liveview_control')
    def handle_update_liveview_control(data):
        """
        Update a single camera control without restarting stream (Phase 2.2)

        Args:
            data: dict with control name and value, e.g., {'Sharpness': 2.0}
        """
        try:
            if not isinstance(data, dict):
                emit('control_updated', {
                    'success': False,
                    'error': 'Invalid data format - expected dict'
                })
                return

            success = camera_streamer.update_control(data)

            if success:
                emit('control_updated', {
                    'success': True,
                    'control': data,
                    'message': f'Updated {list(data.keys())[0]}'
                })
            else:
                emit('control_updated', {
                    'success': False,
                    'error': 'Camera not streaming or control update failed'
                })

        except Exception as e:
            print(f'Error updating control: {e}')
            emit('control_updated', {
                'success': False,
                'error': str(e)
            })

    # Deprecated event name (backward compatibility)
    @socketio.on('update_preview_control')
    def handle_update_preview_control_deprecated(data):
        """[DEPRECATED] Use update_liveview_control instead"""
        print('⚠️  DEPRECATED: update_preview_control event - use update_liveview_control instead')
        handle_update_liveview_control(data)

    @socketio.on('set_zoom')
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
                emit('zoom_updated', {
                    'success': False,
                    'error': 'Invalid data format - expected dict'
                })
                return

            zoom_level = data.get('zoom_level', 1.0)
            center_x = data.get('center_x')
            center_y = data.get('center_y')

            success = camera_streamer.set_zoom(zoom_level, center_x, center_y)

            if success:
                emit('zoom_updated', {
                    'success': True,
                    'zoom_level': camera_streamer.zoom_level,
                    'center_x': camera_streamer.zoom_center_x,
                    'center_y': camera_streamer.zoom_center_y,
                    'message': f'Zoom set to {camera_streamer.zoom_level:.2f}x'
                })
            else:
                emit('zoom_updated', {
                    'success': False,
                    'error': 'Camera not streaming or zoom failed'
                })

        except Exception as e:
            print(f'Error setting zoom: {e}')
            emit('zoom_updated', {
                'success': False,
                'error': str(e)
            })

    @socketio.on('set_af_window')
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
                emit('af_window_updated', {
                    'success': False,
                    'error': 'Invalid data format - expected dict'
                })
                return

            x = data.get('x')
            y = data.get('y')
            window_size = data.get('window_size', 0.2)

            success = camera_streamer.set_af_window(x, y, window_size)

            if success:
                # Send success response with window coordinates
                response = {
                    'success': True,
                    'x': x,
                    'y': y,
                    'window_size': window_size
                }

                # Add message based on whether window was set or cleared
                if x is None or y is None:
                    response['message'] = 'AF window cleared - using auto metering'
                else:
                    response['message'] = f'AF window set at ({x:.2f}, {y:.2f})'

                emit('af_window_updated', response)
            else:
                emit('af_window_updated', {
                    'success': False,
                    'error': 'Camera not streaming or AF window update failed'
                })

        except Exception as e:
            print(f'Error setting AF window: {e}')
            emit('af_window_updated', {
                'success': False,
                'error': str(e)
            })
