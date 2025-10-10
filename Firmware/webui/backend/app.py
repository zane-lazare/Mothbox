#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect, CSRFError
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

# Configure CORS for cross-origin requests
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure SocketIO with proper CORS and transport settings
# WebSocket connections are exempt from CSRF by Flask-WTF
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=True,
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

# Register blueprints
app.register_blueprint(system_bp, url_prefix='/api/system')
app.register_blueprint(camera_bp, url_prefix='/api/camera')
app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(gpio_bp, url_prefix='/api/gpio')
app.register_blueprint(scheduler_bp, url_prefix='/api/scheduler')

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
    return jsonify({
        'error': 'CSRF validation failed',
        'message': str(e.description)
    }), 400

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client WebSocket connection"""
    from flask import request
    client_ip = request.remote_addr
    print(f'Client connected from {client_ip}')
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

    try:
        # Run development server
        # In development mode, allow_unsafe_werkzeug is acceptable
        # In production mode, this is a temporary measure until issue #19 is resolved
        socketio.run(
            app,
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG,
            allow_unsafe_werkzeug=config.DEBUG  # Only allow in debug/development mode
        )
    finally:
        # Cleanup camera on shutdown
        camera_streamer.cleanup()
