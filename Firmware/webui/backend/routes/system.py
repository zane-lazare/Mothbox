"""System status and monitoring endpoints"""
from flask import Blueprint, jsonify
import subprocess
import os
import shutil
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import PHOTOS_DIR, get_hardware_config

system_bp = Blueprint('system', __name__)

@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    try:
        # CPU temperature
        temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
        cpu_temp = float(temp_file.read_text().strip()) / 1000 if temp_file.exists() else None

        # Disk usage
        disk_usage = shutil.disk_usage('/')
        disk_free_gb = disk_usage.free / (1024**3)
        disk_total_gb = disk_usage.total / (1024**3)
        disk_used_percent = (disk_usage.used / disk_usage.total) * 100

        # Photo count
        photo_count = len(list(PHOTOS_DIR.glob('**/*.jpg'))) if PHOTOS_DIR.exists() else 0

        # Hardware config
        hw_config = get_hardware_config()

        return jsonify({
            'cpu_temp': cpu_temp,
            'disk': {
                'free_gb': round(disk_free_gb, 2),
                'total_gb': round(disk_total_gb, 2),
                'used_percent': round(disk_used_percent, 2)
            },
            'photo_count': photo_count,
            'hardware': {
                'ina260_enabled': hw_config.get('ina260_enabled', False),
                'gps_enabled': hw_config.get('gps_enabled', False),
                'epaper_enabled': hw_config.get('epaper_enabled', False)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@system_bp.route('/power', methods=['GET'])
def get_power_status():
    """Get power metrics from INA260 if available"""
    try:
        hw_config = get_hardware_config()
        if not hw_config.get('ina260_enabled'):
            return jsonify({'enabled': False})

        # Try to get power stats (would need to import INA260 module)
        # For now, return placeholder
        return jsonify({
            'enabled': True,
            'voltage': None,
            'current': None,
            'power': None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
