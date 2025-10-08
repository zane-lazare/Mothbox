#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sys
from pathlib import Path

# Add parent directories to path to import mothbox modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
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

# Configure CORS for cross-origin requests
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure SocketIO with proper CORS and transport settings
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

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and Path(app.static_folder, path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    finally:
        # Cleanup camera on shutdown
        camera_streamer.cleanup()
