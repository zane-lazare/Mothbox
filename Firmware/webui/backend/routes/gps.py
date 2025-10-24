"""GPS module control endpoints"""
from flask import Blueprint, jsonify, request
import subprocess
from pathlib import Path
import sys
import time

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import (
    MOTHBOX_HOME,
    CONTROLS_FILE,
    get_hardware_config,
    get_control_values,
    get_script_path
)

gps_bp = Blueprint('gps', __name__)


@gps_bp.route('/status', methods=['GET'])
def get_gps_status():
    """
    Get current GPS status and coordinates from controls.txt

    Returns:
        JSON with GPS status:
        - enabled: Whether GPS is enabled
        - latitude: Current latitude or "n/a"
        - longitude: Current longitude or "n/a"
        - gpstime: Unix timestamp of last GPS sync
        - utc_offset: UTC offset in hours
        - has_fix: Boolean indicating if valid GPS fix exists
    """
    try:
        # Get hardware config
        hw_config = get_hardware_config()

        # Get current GPS data from controls.txt
        control_values = get_control_values(CONTROLS_FILE)

        latitude = control_values.get('lat', 'n/a')
        longitude = control_values.get('lon', 'n/a')
        gpstime = control_values.get('gpstime', '0')
        utc_offset = control_values.get('UTCoff', '0')

        # Determine if we have a valid GPS fix
        has_fix = latitude != 'n/a' and longitude != 'n/a'

        return jsonify({
            'enabled': hw_config['gps_enabled'],
            'latitude': latitude,
            'longitude': longitude,
            'gpstime': int(gpstime) if gpstime.isdigit() else 0,
            'utc_offset': int(utc_offset) if utc_offset.lstrip('-').isdigit() else 0,
            'has_fix': has_fix
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to get GPS status',
            'message': str(e)
        }), 500


@gps_bp.route('/config', methods=['GET'])
def get_gps_config():
    """
    Get GPS hardware configuration

    Returns:
        JSON with GPS configuration:
        - enabled: Whether GPS is enabled
        - device: GPS device path (e.g., /dev/ttyAMA0)
        - baudrate: GPS serial baudrate
        - timeout: GPS sync timeout in seconds
    """
    try:
        hw_config = get_hardware_config()

        return jsonify({
            'enabled': hw_config['gps_enabled'],
            'device': hw_config['gps_device'],
            'baudrate': hw_config['gps_baudrate'],
            'timeout': hw_config['gps_timeout']
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to get GPS configuration',
            'message': str(e)
        }), 500


@gps_bp.route('/config', methods=['PUT'])
def update_gps_config():
    """
    Update GPS configuration in controls.txt

    Expected JSON body:
        - gps_enabled: Boolean
        - gps_device: String (device path)
        - gps_baudrate: Integer (4800, 9600, 19200, 38400, etc.)
        - gps_timeout: Integer (5-60 seconds)

    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate inputs
        if 'gps_enabled' in data:
            if not isinstance(data['gps_enabled'], bool):
                return jsonify({'error': 'gps_enabled must be a boolean'}), 400

        if 'gps_baudrate' in data:
            valid_baudrates = [4800, 9600, 19200, 38400, 57600, 115200]
            if data['gps_baudrate'] not in valid_baudrates:
                return jsonify({'error': f'Invalid baudrate. Must be one of: {valid_baudrates}'}), 400

        if 'gps_timeout' in data:
            timeout = data['gps_timeout']
            if not isinstance(timeout, int) or timeout < 5 or timeout > 60:
                return jsonify({'error': 'gps_timeout must be an integer between 5 and 60'}), 400

        if 'gps_device' in data:
            device = data['gps_device']
            if not device.startswith('/dev/'):
                return jsonify({'error': 'gps_device must start with /dev/'}), 400

        # Update controls.txt
        _update_controls_file(data)

        return jsonify({
            'success': True,
            'message': 'GPS configuration updated successfully'
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to update GPS configuration',
            'message': str(e)
        }), 500


@gps_bp.route('/sync', methods=['POST'])
def sync_gps():
    """
    Trigger GPS sync by running GPS.py script

    This follows the TakePhoto.py pattern:
    - Runs GPS.py as a subprocess
    - GPS.py writes results to controls.txt
    - Returns the results after completion

    Returns:
        JSON with sync results:
        - success: Boolean
        - latitude: Synced latitude or "n/a"
        - longitude: Synced longitude or "n/a"
        - gpstime: Unix timestamp of sync
        - output: Script output for debugging
    """
    try:
        # Check if GPS is enabled
        hw_config = get_hardware_config()
        if not hw_config['gps_enabled']:
            return jsonify({
                'error': 'GPS is disabled',
                'message': 'Enable GPS in configuration before syncing'
            }), 400

        # Get path to GPS.py script
        gps_script = get_script_path('5.x/GPS.py')

        if not gps_script.exists():
            return jsonify({
                'error': 'GPS script not found',
                'message': f'GPS.py not found at {gps_script}'
            }), 500

        # Run GPS.py with timeout (GPS timeout + 20 seconds overhead)
        timeout = hw_config['gps_timeout'] + 20

        print(f"📡 Running GPS sync: {gps_script} (timeout: {timeout}s)")

        result = subprocess.run(
            ['python3', str(gps_script)],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Read updated values from controls.txt
        control_values = get_control_values(CONTROLS_FILE)
        latitude = control_values.get('lat', 'n/a')
        longitude = control_values.get('lon', 'n/a')
        gpstime = control_values.get('gpstime', '0')
        utc_offset = control_values.get('UTCoff', '0')

        # Determine success based on whether we got a fix
        success = latitude != 'n/a' and longitude != 'n/a'

        return jsonify({
            'success': success,
            'latitude': latitude,
            'longitude': longitude,
            'gpstime': int(gpstime) if gpstime.isdigit() else 0,
            'utc_offset': int(utc_offset) if utc_offset.lstrip('-').isdigit() else 0,
            'output': result.stdout,
            'returncode': result.returncode
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'GPS sync timeout',
            'message': f'GPS sync did not complete within {timeout} seconds'
        }), 408
    except Exception as e:
        return jsonify({
            'error': 'GPS sync failed',
            'message': str(e)
        }), 500


def _update_controls_file(config_updates):
    """
    Update GPS settings in controls.txt

    Args:
        config_updates: Dictionary with configuration updates
    """
    # Read current controls.txt
    with open(CONTROLS_FILE, 'r') as f:
        lines = f.readlines()

    # Prepare updates mapping
    updates = {}
    if 'gps_enabled' in config_updates:
        updates['gps_enabled'] = 'true' if config_updates['gps_enabled'] else 'false'
    if 'gps_device' in config_updates:
        updates['gps_device'] = config_updates['gps_device']
    if 'gps_baudrate' in config_updates:
        updates['gps_baudrate'] = str(config_updates['gps_baudrate'])
    if 'gps_timeout' in config_updates:
        updates['gps_timeout'] = str(config_updates['gps_timeout'])

    # Update lines
    updated_lines = []
    updated_keys = set()

    for line in lines:
        stripped = line.strip()
        if stripped and '=' in stripped and not stripped.startswith('#'):
            key = stripped.split('=', 1)[0]
            if key in updates:
                updated_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Add any new keys that weren't in the file
    for key, value in updates.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")

    # Write back to file
    with open(CONTROLS_FILE, 'w') as f:
        f.writelines(updated_lines)
