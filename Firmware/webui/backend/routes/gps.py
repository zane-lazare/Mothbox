"""GPS module control endpoints"""
from flask import Blueprint, jsonify, request
import subprocess
from pathlib import Path
import sys
import time
import fcntl
import threading

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

# GPS status cache to avoid excessive file I/O (similar to photo count cache in system.py)
# Cache is valid for 2 seconds to balance freshness with performance
_gps_status_cache = {
    'data': None,
    'timestamp': 0,
    'lock': threading.Lock()
}
GPS_STATUS_CACHE_TTL = 2  # seconds


def _get_cached_gps_status():
    """
    Get GPS status with caching to avoid excessive file I/O.

    Returns cached status if less than GPS_STATUS_CACHE_TTL seconds old,
    otherwise performs fresh read and updates cache.

    Returns:
        dict: GPS status dictionary
    """
    current_time = time.time()

    with _gps_status_cache['lock']:
        # Check if cache is still valid
        if (_gps_status_cache['data'] is not None and
            current_time - _gps_status_cache['timestamp'] < GPS_STATUS_CACHE_TTL):
            return _gps_status_cache['data']

        # Cache expired or empty, perform read
        try:
            # Get hardware config
            hw_config = get_hardware_config()

            # Get current GPS data from controls.txt
            control_values = get_control_values(CONTROLS_FILE)

            latitude = control_values.get('lat', 'n/a')
            longitude = control_values.get('lon', 'n/a')
            gpstime = control_values.get('gpstime', '0')
            utc_offset = control_values.get('UTCoff', '0')

            # Validate and parse gpstime (must be non-negative Unix timestamp)
            gpstime_val = int(gpstime) if gpstime.isdigit() else 0
            if gpstime_val < 0:
                gpstime_val = 0

            # Validate and parse UTC offset (must be between -12 and +14 hours)
            utc_offset_val = int(utc_offset) if utc_offset.lstrip('-').isdigit() else 0
            if utc_offset_val < -12 or utc_offset_val > 14:
                utc_offset_val = 0

            # Determine if we have a valid GPS fix
            has_fix = latitude != 'n/a' and longitude != 'n/a'

            status_dict = {
                'enabled': hw_config['gps_enabled'],
                'latitude': latitude,
                'longitude': longitude,
                'gpstime': gpstime_val,
                'utc_offset': utc_offset_val,
                'has_fix': has_fix
            }

            # Update cache
            _gps_status_cache['data'] = status_dict
            _gps_status_cache['timestamp'] = current_time

            return status_dict
        except Exception as e:
            # On error, return cached value if available, otherwise minimal status
            if _gps_status_cache['data'] is not None:
                return _gps_status_cache['data']
            raise


@gps_bp.route('/status', methods=['GET'])
def get_gps_status():
    """
    Get current GPS status and coordinates from controls.txt (with caching)

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
        # Use cached status to reduce file I/O
        status = _get_cached_gps_status()
        return jsonify(status)
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
    print("🔍 GPS sync endpoint called")
    try:
        # Check if GPS is enabled
        print("🔍 Getting hardware config...")
        hw_config = get_hardware_config()
        print(f"🔍 GPS enabled: {hw_config.get('gps_enabled')}")
        if not hw_config['gps_enabled']:
            return jsonify({
                'error': 'GPS is disabled',
                'message': 'Enable GPS in configuration before syncing'
            }), 400

        # Get path to GPS.py script
        gps_script = get_script_path('GPS.py')

        if not gps_script.exists():
            return jsonify({
                'error': 'GPS script not found',
                'message': 'GPS script not found in firmware directory'
            }), 500

        # Run GPS.py with timeout (GPS timeout + 20 seconds overhead)
        timeout = hw_config['gps_timeout'] + 20

        print(f"📡 Running GPS sync: {gps_script} (timeout: {timeout}s)")

        # Note: subprocess.run() blocks the Flask worker thread during GPS sync.
        # This is acceptable because:
        # 1. GPS sync is infrequent (user-triggered or scheduled)
        # 2. Rate limiting (5 req/min) prevents worker starvation
        # 3. Other WebUI endpoints remain responsive (separate requests use different workers)
        # For high-frequency operations, consider using Celery or background tasks.
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

        # Invalidate GPS status cache to force fresh read on next request
        with _gps_status_cache['lock']:
            _gps_status_cache['timestamp'] = 0

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
        # Log full traceback for debugging
        import traceback
        print(f"❌ GPS sync failed with exception:")
        print(traceback.format_exc())
        return jsonify({
            'error': 'GPS sync failed',
            'message': str(e)
        }), 500


def _update_controls_file(config_updates):
    """
    Update GPS settings in controls.txt with file locking to prevent race conditions

    Args:
        config_updates: Dictionary with configuration updates

    Raises:
        IOError: If file locking fails or file operations fail

    Note on file locking:
        This function uses fcntl file locking to prevent race conditions when accessing
        controls.txt. The GPS.py script (in 5.x/GPS.py) also uses fcntl file locking
        for its write operations, ensuring both WebUI and GPS.py coordinate access to
        the shared configuration file.

        Since POSIX file locks are advisory, both implementations must use locks for
        this protection to work. Race conditions are prevented by:
        - Both WebUI and GPS.py using fcntl.flock(LOCK_EX) for writes
        - GPS sync is rate-limited (5 requests/minute)
        - GPS status cache reduces file I/O
    """
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

    # Open file for read/write and acquire exclusive lock
    with open(CONTROLS_FILE, 'r+') as f:
        try:
            # Acquire exclusive lock (blocks until lock is available)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            # Read current contents
            lines = f.readlines()

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
            f.seek(0)
            f.truncate()
            f.writelines(updated_lines)
            f.flush()

        finally:
            # Release lock (automatically released when file closes, but explicit is better)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
