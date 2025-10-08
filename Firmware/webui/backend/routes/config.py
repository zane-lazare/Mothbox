"""Configuration management endpoints"""
from flask import Blueprint, jsonify, request
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from mothbox_paths import (
    CAMERA_SETTINGS_FILE,
    SCHEDULE_SETTINGS_FILE,
    CONTROLS_FILE,
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
