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

# Initialize live view streamer
from liveview_stream import LiveViewStreamer
camera_streamer = LiveViewStreamer(socketio)

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
from routes.presets import presets_bp
from routes.preferences import preferences_bp

# Make camera_streamer accessible to routes via app config
app.config['CAMERA_STREAMER'] = camera_streamer

# Register blueprints
app.register_blueprint(system_bp, url_prefix='/api/system')
app.register_blueprint(camera_bp, url_prefix='/api/camera')
app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(gpio_bp, url_prefix='/api/gpio')
app.register_blueprint(scheduler_bp, url_prefix='/api/scheduler')
app.register_blueprint(presets_bp, url_prefix='/api/presets')
app.register_blueprint(preferences_bp, url_prefix='/api/preferences')

# Register WebSocket handlers
from websocket_handlers import register_handlers
register_handlers(socketio, camera_streamer)
print("✓ Registered WebSocket event handlers")

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
