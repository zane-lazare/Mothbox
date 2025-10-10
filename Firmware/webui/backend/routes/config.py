"""Configuration management endpoints"""
from flask import Blueprint, jsonify, request
import csv
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import (
    CAMERA_SETTINGS_FILE,
    SCHEDULE_SETTINGS_FILE,
    CONTROLS_FILE,
    WEBUI_SETTINGS_FILE,
    get_control_values
)

config_bp = Blueprint('config', __name__)

@config_bp.route('/controls', methods=['GET'])
def get_controls():
    """Get controls.txt configuration"""
    try:
        controls = get_control_values(CONTROLS_FILE)
        return jsonify(controls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/controls', methods=['POST'])
def update_controls():
    """Update controls.txt configuration"""
    try:
        new_controls = request.json

        with open(CONTROLS_FILE, 'w') as f:
            for key, value in new_controls.items():
                f.write(f"{key}={value}\n")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/schedule', methods=['GET'])
def get_schedule_settings():
    """Get schedule settings from CSV"""
    try:
        settings = {}
        with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                settings = row
                break

        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/schedule', methods=['POST'])
def update_schedule_settings():
    """Update schedule settings"""
    try:
        new_settings = request.json

        # Read existing headers
        with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        # Write updated settings
        with open(SCHEDULE_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(new_settings)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/webui', methods=['GET'])
def get_webui_settings():
    """Get WebUI stream settings"""
    try:
        # Default settings
        defaults = {
            'preview_width': 1024,
            'preview_height': 768,
            'frame_rate': 10,
            'jpeg_quality': 95
        }

        # Load from file if it exists
        if WEBUI_SETTINGS_FILE.exists():
            settings = get_control_values(WEBUI_SETTINGS_FILE)
            # Convert string values to integers
            for key in defaults:
                if key in settings:
                    try:
                        defaults[key] = int(settings[key])
                    except ValueError:
                        pass  # Keep default if conversion fails

        return jsonify(defaults)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_bp.route('/webui', methods=['POST'])
def update_webui_settings():
    """Update WebUI stream settings"""
    try:
        new_settings = request.json

        # Validate settings
        preview_width = int(new_settings.get('preview_width', 1024))
        preview_height = int(new_settings.get('preview_height', 768))
        frame_rate = int(new_settings.get('frame_rate', 10))
        jpeg_quality = int(new_settings.get('jpeg_quality', 95))

        # Validate ranges
        if not (320 <= preview_width <= 1920):
            return jsonify({'error': 'Width must be between 320 and 1920'}), 400
        if not (240 <= preview_height <= 1080):
            return jsonify({'error': 'Height must be between 240 and 1080'}), 400
        if not (1 <= frame_rate <= 30):
            return jsonify({'error': 'Frame rate must be between 1 and 30'}), 400
        if not (50 <= jpeg_quality <= 100):
            return jsonify({'error': 'JPEG quality must be between 50 and 100'}), 400

        # Write settings to file
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write(f"preview_width={preview_width}\n")
            f.write(f"preview_height={preview_height}\n")
            f.write(f"frame_rate={frame_rate}\n")
            f.write(f"jpeg_quality={jpeg_quality}\n")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
