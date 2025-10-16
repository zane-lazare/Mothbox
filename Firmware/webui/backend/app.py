#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sys
import os
import signal
import atexit
from pathlib import Path

# Load configuration based on environment
from config import get_config
config = get_config()

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import (
    MOTHBOX_HOME,
    CONFIG_DIR,
    PHOTOS_DIR,
    CAMERA_SETTINGS_FILE,
    SCHEDULE_SETTINGS_FILE,
    CONTROLS_FILE,
    get_gpio_pins,
    get_hardware_config
)

app = Flask(__name__, static_folder='../frontend/dist')

# Apply configuration
app.config.from_object(config)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Debug: Log CSRF configuration
print(f"✓ CSRF Protection initialized")
print(f"  WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
print(f"  WTF_CSRF_HEADERS: {app.config.get('WTF_CSRF_HEADERS')}")
print(f"  SECRET_KEY set: {bool(app.config.get('SECRET_KEY'))}")

# Initialize rate limiter to prevent hardware abuse
# Uses remote address for rate limiting (single user device typically has same IP)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Configure CORS for cross-origin requests
# Use restrictive origins from config (empty list = same-origin only in production)
if config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    print(f"✓ CORS enabled for origins: {config.CORS_ORIGINS}")
else:
    # No CORS configured - same-origin only (most secure for production)
    print("✓ CORS: Same-origin only (no cross-origin requests allowed)")

# Configure SocketIO with proper CORS and transport settings
# WebSocket connections are exempt from CSRF by Flask-WTF
# Use same CORS origins as REST API for consistency
# Production (no CORS_ORIGINS): empty list = reject all cross-origin connections
# Development (CORS_ORIGINS set): allow configured origins
socketio = SocketIO(
    app,
    cors_allowed_origins=config.CORS_ORIGINS if config.CORS_ORIGINS else [],
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Initialize camera streamer
from camera_stream import CameraStreamer
camera_streamer = CameraStreamer(socketio)

# Register cleanup handlers to ensure camera resources are released
# Uses both atexit and signal handlers for defense in depth
atexit.register(camera_streamer.cleanup)
print("✓ Registered atexit cleanup handler for camera")

def _signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT gracefully"""
    signame = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
    print(f"\n{signame} received - cleaning up camera resources...")
    camera_streamer.cleanup()
    print("Cleanup complete, exiting")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
print("✓ Registered signal handlers for graceful shutdown")

# Import route blueprints
from routes.system import system_bp
from routes.camera import camera_bp
from routes.gallery import gallery_bp
from routes.config import config_bp
from routes.gpio import gpio_bp
from routes.scheduler import scheduler_bp

# Make camera_streamer accessible to routes via app config
app.config['CAMERA_STREAMER'] = camera_streamer

# Register blueprints
app.register_blueprint(system_bp, url_prefix='/api/system')
app.register_blueprint(camera_bp, url_prefix='/api/camera')
app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(gpio_bp, url_prefix='/api/gpio')
app.register_blueprint(scheduler_bp, url_prefix='/api/scheduler')

# Apply rate limiting to hardware endpoints to prevent abuse
# Camera: 10 requests per minute for capture operations (prevents rapid captures)
# GPIO: 30 requests per minute for control operations (one per 2 seconds)
# GPIO: 10 requests per minute for flash operations (prevents rapid relay cycling)
# Use app.view_functions with blueprint-prefixed endpoint names
limiter.limit("10 per minute")(app.view_functions['camera.capture_photo'])
limiter.limit("30 per minute")(app.view_functions['gpio.control_gpio'])
limiter.limit("10 per minute")(app.view_functions['gpio.trigger_flash'])
print("✓ Rate limiting applied to camera and GPIO endpoints")

# CSRF token endpoint
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Return CSRF token for the session"""
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors"""
    print(f"⚠️  CSRF validation failed: {e.description}")
    print(f"   Request path: {request.path}")
    print(f"   Request method: {request.method}")
    print(f"   Request headers: {dict(request.headers)}")
    print(f"   Request cookies: {list(request.cookies.keys())}")
    return jsonify({
        'error': 'CSRF validation failed',
        'message': str(e.description)
    }), 400

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client WebSocket connection with origin validation"""
    from flask import request

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
    print('Client disconnected - stopping camera preview if active')
    camera_streamer.stop_streaming()

@socketio.on('start_preview')
def handle_start_preview():
    """Start camera preview streaming"""
    print('Received start_preview request')
    try:
        success = camera_streamer.start_streaming()
        if success:
            print('Camera preview started successfully')
            emit('preview_status', {'streaming': True, 'message': 'Preview started'})
        else:
            print('Failed to start camera preview')
            emit('preview_status', {'streaming': False, 'error': 'Failed to initialize camera'})
    except Exception as e:
        print(f'Error starting preview: {e}')
        emit('preview_status', {'streaming': False, 'error': str(e)})

@socketio.on('stop_preview')
def handle_stop_preview():
    """Stop camera preview streaming"""
    print('Received stop_preview request')
    try:
        camera_streamer.stop_streaming()
        print('Camera preview stopped')
        emit('preview_status', {'streaming': False, 'message': 'Preview stopped'})
    except Exception as e:
        print(f'Error stopping preview: {e}')
        emit('preview_status', {'streaming': False, 'error': str(e)})

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
    """
    try:
        if camera_streamer.camera and camera_streamer.streaming:
            # Camera is active - get live metadata
            md = camera_streamer.camera.capture_metadata()

            # Extract relevant metadata
            exposure_time = md.get('ExposureTime', 0)
            analogue_gain = md.get('AnalogueGain', 0.0)
            lens_position = md.get('LensPosition', 0.0)
            af_state_code = md.get('AfState', 0)
            colour_temp = md.get('ColourTemperature', 0)

            # Convert AfState code to string
            af_state = ("Idle", "Scanning", "Success", "Fail")[af_state_code] if af_state_code < 4 else "Unknown"

            emit('metadata_update', {
                'exposure_time': exposure_time,
                'analogue_gain': round(analogue_gain, 2),
                'lens_position': round(lens_position, 2),
                'af_state': af_state,
                'colour_temperature': colour_temp,
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
                'colour_temperature': 0
            })

    except Exception as e:
        print(f'Error getting metadata: {e}')
        emit('metadata_update', {
            'error': str(e),
            'exposure_time': 0,
            'analogue_gain': 0,
            'lens_position': 0,
            'af_state': 'Error',
            'colour_temperature': 0
        })

@socketio.on('update_preview_control')
def handle_update_preview_control(data):
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

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and Path(app.static_folder, path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Print startup banner with environment information
    print("\n" + "=" * 60)
    print(f"Mothbox Web UI Starting")
    print(f"Environment: {config.ENV_NAME}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Host: {config.HOST}:{config.PORT}")
    print("=" * 60)

    if config.ENV_NAME == 'production':
        print("\n⚠️  WARNING: Running with Werkzeug development server")
        print("   For production deployment, use gunicorn with eventlet worker")
        print("   See issue #19: https://github.com/zane-lazare/Mothbox/issues/19")
        print("=" * 60 + "\n")

    # Block production mode until gunicorn is implemented (issue #19)
    # Production installations should run in development mode for now
    if config.ENV_NAME == 'production' and not config.DEBUG:
        raise RuntimeError(
            "\n" + "="*60 + "\n"
            "ERROR: Production mode requires gunicorn deployment\n"
            "="*60 + "\n"
            "The Werkzeug development server is not safe for production use.\n"
            "\n"
            "For now, run in development mode:\n"
            "  export MOTHBOX_ENV=development\n"
            "\n"
            "Or wait for gunicorn implementation:\n"
            "  https://github.com/zane-lazare/Mothbox/issues/19\n"
            "="*60
        )

    try:
        # Run development server
        # Require BOTH debug mode AND development environment for werkzeug
        # This prevents accidental unsafe werkzeug in production even if DEBUG is misconfigured
        socketio.run(
            app,
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG,
            allow_unsafe_werkzeug=(config.DEBUG and config.ENV_NAME == 'development')
        )
    finally:
        # Cleanup camera on shutdown
        camera_streamer.cleanup()
