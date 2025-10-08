#!/usr/bin/env python3
"""
Mothbox Web UI Backend
Flask API server for Mothbox control and monitoring
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
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
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and Path(app.static_folder, path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
