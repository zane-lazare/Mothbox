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

from mothbox_paths import (
    PHOTOS_DIR,
    get_hardware_config,
    get_gpio_pins,
    get_control_values,
    MOTHBOX_HOME,
    CONFIG_DIR,
    FIRMWARE_DIR,
    CONTROLS_FILE,
    CAMERA_SETTINGS_FILE,
    SCHEDULE_SETTINGS_FILE,
    _installation_type
)

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

@system_bp.route('/info', methods=['GET'])
def get_system_info():
    """Get system installation and configuration info"""
    try:
        # Get GPIO pins configuration
        gpio_pins = get_gpio_pins()

        # Get controls values
        controls = get_control_values(CONTROLS_FILE)
        firmware_version = controls.get('softwareversion', 'unknown')

        # Check if GPIO pins are defined in controls.txt
        has_gpio_in_config = all(key in controls for key in ['Relay_Ch1', 'Relay_Ch2', 'Relay_Ch3'])
        gpio_source = 'controls.txt' if has_gpio_in_config else 'defaults'

        return jsonify({
            'installation_type': _installation_type,
            'firmware_version': firmware_version,
            'mothbox_home': str(MOTHBOX_HOME),
            'config_dir': str(CONFIG_DIR),
            'firmware_dir': str(FIRMWARE_DIR),
            'gpio_pins': gpio_pins,
            'gpio_source': gpio_source
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_bp.route('/diagnostic', methods=['GET'])
def get_diagnostic_info():
    """Get detailed diagnostic information for troubleshooting"""
    try:
        # Check path existence
        controls = get_control_values(CONTROLS_FILE)
        controls_size = CONTROLS_FILE.stat().st_size if CONTROLS_FILE.exists() else 0

        # Count raw lines in controls.txt
        raw_lines = 0
        if CONTROLS_FILE.exists():
            with open(CONTROLS_FILE, 'r') as f:
                raw_lines = len(f.readlines())

        # Get hardware config
        hw_config = get_hardware_config()

        # Check for GPIO pins in config
        has_gpio_pins = all(key in controls for key in ['Relay_Ch1', 'Relay_Ch2', 'Relay_Ch3'])

        return jsonify({
            'paths': {
                'mothbox_home': str(MOTHBOX_HOME),
                'mothbox_home_exists': MOTHBOX_HOME.exists(),
                'config_dir': str(CONFIG_DIR),
                'config_dir_exists': CONFIG_DIR.exists(),
                'firmware_dir': str(FIRMWARE_DIR),
                'firmware_dir_exists': FIRMWARE_DIR.exists(),
                'controls_file': str(CONTROLS_FILE),
                'controls_file_exists': CONTROLS_FILE.exists(),
                'controls_file_size': controls_size,
                'camera_settings_file': str(CAMERA_SETTINGS_FILE),
                'camera_settings_file_exists': CAMERA_SETTINGS_FILE.exists(),
                'schedule_settings_file': str(SCHEDULE_SETTINGS_FILE),
                'schedule_settings_file_exists': SCHEDULE_SETTINGS_FILE.exists()
            },
            'controls_content': {
                'raw_lines': raw_lines,
                'parsed_keys': list(controls.keys()),
                'has_gpio_pins': has_gpio_pins,
                'sample_values': {
                    'softwareversion': controls.get('softwareversion', 'not found'),
                    'name': controls.get('name', 'not found'),
                    'Relay_Ch1': controls.get('Relay_Ch1', 'not found'),
                    'Relay_Ch2': controls.get('Relay_Ch2', 'not found'),
                    'Relay_Ch3': controls.get('Relay_Ch3', 'not found')
                }
            },
            'hardware_config': {
                'ina260_enabled': hw_config.get('ina260_enabled', False),
                'gps_enabled': hw_config.get('gps_enabled', False),
                'epaper_enabled': hw_config.get('epaper_enabled', False),
                'relay_enabled': hw_config.get('relay_enabled', True),
                'light_sensor_enabled': hw_config.get('light_sensor_enabled', False),
                'pca9536_enabled': hw_config.get('pca9536_enabled', False),
                'mux_enabled': hw_config.get('mux_enabled', False)
            },
            'gpio_pins': get_gpio_pins()
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
