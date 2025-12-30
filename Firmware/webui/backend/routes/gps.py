"""GPS module control endpoints"""

import fcntl
import logging
import subprocess
import threading
import time

# Setup path to import mothbox_paths
from flask import Blueprint, jsonify, request

from mothbox_paths import CONTROLS_FILE, get_control_values, get_hardware_config, get_script_path

logger = logging.getLogger(__name__)

gps_bp = Blueprint("gps", __name__)

# GPS status cache to avoid excessive file I/O (similar to photo count cache in system.py)
# Cache is valid for 2 seconds to balance freshness with performance
_gps_status_cache = {"data": None, "timestamp": 0, "lock": threading.Lock()}
GPS_STATUS_CACHE_TTL = 2  # seconds


def calculate_adaptive_timeout(gpstime, hw_config):
    """
    Determine appropriate GPS timeout based on last sync time.

    GPS modules have different Time To First Fix (TTFF) depending on how long
    since last sync:
    - Hot start (< 4 hours): ~1 second TTFF
    - Warm start (4 hours - 6 days): ~26 seconds TTFF
    - Cold start (6-28 days): 26-57 seconds TTFF
    - Almanac expired (> 28 days): 12-20 minutes worst case

    Args:
        gpstime: Unix timestamp of last successful GPS sync (0 if never synced)
        hw_config: Hardware configuration dict containing timeout settings

    Returns:
        tuple: (timeout_seconds, gps_state_string)
        where gps_state is one of: "hot_start", "warm_start", "cold_start", "almanac_expired"
    """
    if gpstime == 0:
        # Never synced - assume almanac expired
        return (hw_config["gps_timeout_almanac"], "almanac_expired")

    hours_since_sync = (time.time() - gpstime) / 3600

    if hours_since_sync < 4:
        # Hot start: GPS has valid ephemeris, almanac, and recent position
        return (hw_config["gps_timeout_hot"], "hot_start")
    elif hours_since_sync < 144:  # 6 days
        # Warm start: Has almanac but needs fresh ephemeris
        return (hw_config["gps_timeout_warm"], "warm_start")
    elif hours_since_sync < 672:  # 28 days
        # Cold start: Needs to download ephemeris
        return (hw_config["gps_timeout_cold"], "cold_start")
    else:
        # Almanac expired: Needs to download full almanac (12-20 minutes worst case)
        return (hw_config["gps_timeout_almanac"], "almanac_expired")


def _get_cached_gps_status():
    """
    Get GPS status with caching to avoid excessive file I/O.

    Returns cached status if less than GPS_STATUS_CACHE_TTL seconds old,
    otherwise performs fresh read and updates cache.

    Returns:
        dict: GPS status dictionary
    """
    current_time = time.time()

    with _gps_status_cache["lock"]:
        # Check if cache is still valid
        if (
            _gps_status_cache["data"] is not None
            and current_time - _gps_status_cache["timestamp"] < GPS_STATUS_CACHE_TTL
        ):
            return _gps_status_cache["data"]

        # Cache expired or empty, perform read
        try:
            # Get hardware config
            hw_config = get_hardware_config()

            # Get current GPS data from controls.txt
            control_values = get_control_values(CONTROLS_FILE)

            latitude = control_values.get("lat", "n/a")
            longitude = control_values.get("lon", "n/a")
            gpstime = control_values.get("gpstime", "0")
            utc_offset = control_values.get("UTCoff", "0")

            # GPS quality metrics
            fix_mode = control_values.get("gps_fix_mode", "0")
            satellites_visible = control_values.get("gps_satellites_visible", "0")
            satellites_used = control_values.get("gps_satellites_used", "0")
            hdop = control_values.get("gps_hdop", "99.99")
            pdop = control_values.get("gps_pdop", "99.99")

            # Get last known position data
            last_known_lat = control_values.get("last_known_lat", "n/a")
            last_known_lon = control_values.get("last_known_lon", "n/a")
            last_position_time = control_values.get("last_position_time", "0")

            # Validate and parse gpstime (must be non-negative Unix timestamp)
            gpstime_val = int(gpstime) if gpstime.isdigit() else 0
            if gpstime_val < 0:
                gpstime_val = 0

            # Validate and parse last_position_time
            last_position_time_val = int(last_position_time) if last_position_time.isdigit() else 0
            if last_position_time_val < 0:
                last_position_time_val = 0

            # Validate and parse UTC offset (must be between -12 and +14 hours)
            utc_offset_val = int(utc_offset) if utc_offset.lstrip("-").isdigit() else 0
            if utc_offset_val < -12 or utc_offset_val > 14:
                utc_offset_val = 0

            # Determine if we have a valid GPS fix
            has_fix = latitude != "n/a" and longitude != "n/a"
            has_last_known_position = last_known_lat != "n/a" and last_known_lon != "n/a"

            status_dict = {
                "enabled": hw_config["gps_enabled"],
                "latitude": latitude,
                "longitude": longitude,
                "gpstime": gpstime_val,
                "utc_offset": utc_offset_val,
                "has_fix": has_fix,
                "fix_mode": int(fix_mode) if fix_mode.isdigit() else 0,
                "satellites_visible": int(satellites_visible)
                if satellites_visible.isdigit()
                else 0,
                "satellites_used": int(satellites_used) if satellites_used.isdigit() else 0,
                "hdop": float(hdop) if hdop.replace(".", "", 1).isdigit() else 99.99,
                "pdop": float(pdop) if pdop.replace(".", "", 1).isdigit() else 99.99,
                "last_known_lat": last_known_lat,
                "last_known_lon": last_known_lon,
                "last_position_time": last_position_time_val,
                "has_last_known_position": has_last_known_position,
            }

            # Update cache
            _gps_status_cache["data"] = status_dict
            _gps_status_cache["timestamp"] = current_time

            return status_dict
        except Exception:
            # On error, return cached value if available, otherwise minimal status
            if _gps_status_cache["data"] is not None:
                return _gps_status_cache["data"]
            raise


@gps_bp.route("/status", methods=["GET"])
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
        - fix_mode: GPS fix mode (0=no fix, 2=2D, 3=3D)
        - satellites_visible: Number of satellites visible
        - satellites_used: Number of satellites used in fix
        - hdop: Horizontal dilution of precision
        - pdop: Position dilution of precision
        - last_known_lat: Last known valid latitude or "n/a"
        - last_known_lon: Last known valid longitude or "n/a"
        - last_position_time: Unix timestamp when position was last acquired
        - has_last_known_position: Boolean indicating if last known position exists
    """
    try:
        # Use cached status to reduce file I/O
        status = _get_cached_gps_status()
        return jsonify(status)
    except Exception:
        logger.exception("Failed to get GPS status")
        return jsonify({"error": "Failed to get GPS status"}), 500


@gps_bp.route("/config", methods=["GET"])
def get_gps_config():
    """
    Get GPS hardware configuration

    Returns:
        JSON with GPS configuration:
        - enabled: Whether GPS is enabled
        - device: GPS device path (e.g., /dev/ttyAMA0)
        - baudrate: GPS serial baudrate
        - timeout: GPS sync timeout in seconds (legacy/fallback)
        - timeout_hot: Hot start timeout (< 4 hours)
        - timeout_warm: Warm start timeout (4h - 6 days)
        - timeout_cold: Cold start timeout (6 - 28 days)
        - timeout_almanac: Almanac expired timeout (> 28 days)
    """
    try:
        hw_config = get_hardware_config()

        return jsonify(
            {
                "enabled": hw_config["gps_enabled"],
                "device": hw_config["gps_device"],
                "baudrate": hw_config["gps_baudrate"],
                "timeout": hw_config["gps_timeout"],
                "timeout_hot": hw_config["gps_timeout_hot"],
                "timeout_warm": hw_config["gps_timeout_warm"],
                "timeout_cold": hw_config["gps_timeout_cold"],
                "timeout_almanac": hw_config["gps_timeout_almanac"],
            }
        )
    except Exception:
        logger.exception("Failed to get GPS configuration")
        return jsonify({"error": "Failed to get GPS configuration"}), 500


@gps_bp.route("/config", methods=["PUT"])
def update_gps_config():
    """
    Update GPS configuration in controls.txt

    Expected JSON body:
        - gps_enabled: Boolean
        - gps_device: String (device path)
        - gps_baudrate: Integer (4800, 9600, 19200, 38400, etc.)
        - gps_timeout: Integer (5-60 seconds, legacy/fallback)
        - gps_timeout_hot: Integer (5-60 seconds)
        - gps_timeout_warm: Integer (30-180 seconds)
        - gps_timeout_cold: Integer (60-300 seconds)
        - gps_timeout_almanac: Integer (300-1800 seconds)

    Returns:
        JSON with success status
    """
    # Handle JSON parsing separately to return proper 400 errors
    try:
        data = request.get_json()
    except Exception:
        data = None

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate all inputs first (before any operations that can fail)
    if "gps_enabled" in data and not isinstance(data["gps_enabled"], bool):
        return jsonify({"error": "gps_enabled must be a boolean"}), 400

    if "gps_baudrate" in data:
        valid_baudrates = [4800, 9600, 19200, 38400, 57600, 115200]
        if data["gps_baudrate"] not in valid_baudrates:
            return jsonify({"error": f"Invalid baudrate. Must be one of: {valid_baudrates}"}), 400

    if "gps_timeout" in data:
        timeout = data["gps_timeout"]
        if not isinstance(timeout, int) or timeout < 5 or timeout > 60:
            return jsonify({"error": "gps_timeout must be an integer between 5 and 60"}), 400

    if "gps_timeout_hot" in data:
        timeout = data["gps_timeout_hot"]
        if not isinstance(timeout, int) or timeout < 5 or timeout > 60:
            return jsonify({"error": "gps_timeout_hot must be an integer between 5 and 60"}), 400

    if "gps_timeout_warm" in data:
        timeout = data["gps_timeout_warm"]
        if not isinstance(timeout, int) or timeout < 30 or timeout > 180:
            return jsonify({"error": "gps_timeout_warm must be an integer between 30 and 180"}), 400

    if "gps_timeout_cold" in data:
        timeout = data["gps_timeout_cold"]
        if not isinstance(timeout, int) or timeout < 60 or timeout > 300:
            return jsonify({"error": "gps_timeout_cold must be an integer between 60 and 300"}), 400

    if "gps_timeout_almanac" in data:
        timeout = data["gps_timeout_almanac"]
        if not isinstance(timeout, int) or timeout < 300 or timeout > 1800:
            return jsonify(
                {
                    "error": "gps_timeout_almanac must be an integer between 300 and 1800 (5-30 minutes)"
                }
            ), 400

    if "gps_device" in data:
        device = data["gps_device"]
        if not device.startswith("/dev/"):
            return jsonify({"error": "gps_device must start with /dev/"}), 400
        # Prevent path traversal attacks (e.g., /dev/../etc/passwd)
        import os

        normalized_path = os.path.normpath(device)
        if not normalized_path.startswith("/dev/"):
            return jsonify({"error": "gps_device must start with /dev/"}), 400

    # Now wrap file I/O and subprocess operations in try/except for 500 errors
    try:
        # Check if device or baudrate changed (requires gpsd restart)
        hw_config = get_hardware_config()
        device_changed = "gps_device" in data and data["gps_device"] != hw_config["gps_device"]
        baudrate_changed = (
            "gps_baudrate" in data and data["gps_baudrate"] != hw_config["gps_baudrate"]
        )
        gpsd_restart_needed = device_changed or baudrate_changed

        # Update controls.txt
        _update_controls_file(data)

        # Update gpsd configuration and restart service if device or baudrate changed
        gpsd_restarted = False
        if gpsd_restart_needed:
            try:
                new_device = data.get("gps_device", hw_config["gps_device"])
                new_baudrate = data.get("gps_baudrate", hw_config["gps_baudrate"])
                _update_gpsd_config(new_device, new_baudrate)
                gpsd_restarted = True
            except subprocess.CalledProcessError as e:
                return jsonify(
                    {
                        "error": "Failed to update gpsd configuration",
                        "message": f"Sudo command failed: {str(e)}. Check WebUI has sudo permissions.",
                    }
                ), 500
            except Exception:
                logger.exception("Failed to restart GPS service")
                return jsonify({"error": "Failed to restart GPS service"}), 500

        return jsonify(
            {
                "success": True,
                "message": "GPS configuration updated successfully",
                "gpsd_restarted": gpsd_restarted,
            }
        )
    except Exception:
        logger.exception("Failed to update GPS configuration")
        return jsonify({"error": "Failed to update GPS configuration"}), 500


@gps_bp.route("/sync", methods=["POST"])
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
        if not hw_config["gps_enabled"]:
            return jsonify(
                {
                    "error": "GPS is disabled",
                    "message": "Enable GPS in configuration before syncing",
                }
            ), 400

        # Get path to GPS.py script
        gps_script = get_script_path("GPS.py")

        if not gps_script.exists():
            return jsonify(
                {
                    "error": "GPS script not found",
                    "message": "GPS script not found in firmware directory",
                }
            ), 500

        # Calculate adaptive timeout based on last GPS sync time
        control_values = get_control_values(CONTROLS_FILE)
        last_gpstime = (
            int(control_values.get("gpstime", "0"))
            if control_values.get("gpstime", "0").isdigit()
            else 0
        )
        gps_timeout, gps_state = calculate_adaptive_timeout(last_gpstime, hw_config)

        # Add 20 seconds overhead for subprocess execution
        timeout = gps_timeout + 20

        logger.info(f"Running GPS sync: {gps_script} (timeout: {timeout}s, state: {gps_state})")

        # Note: subprocess.run() blocks the Flask worker thread during GPS sync.
        # This is acceptable because:
        # 1. GPS sync is infrequent (user-triggered or scheduled)
        # 2. Rate limiting (5 req/min) prevents worker starvation
        # 3. Other WebUI endpoints remain responsive (separate requests use different workers)
        # For high-frequency operations, consider using Celery or background tasks.
        result = subprocess.run(
            ["python3", str(gps_script)], capture_output=True, text=True, timeout=timeout
        )

        # Read updated values from controls.txt
        control_values = get_control_values(CONTROLS_FILE)
        latitude = control_values.get("lat", "n/a")
        longitude = control_values.get("lon", "n/a")
        gpstime = control_values.get("gpstime", "0")
        utc_offset = control_values.get("UTCoff", "0")

        # Determine success based on whether we got a fix
        success = latitude != "n/a" and longitude != "n/a"

        # Invalidate GPS status cache to force fresh read on next request
        with _gps_status_cache["lock"]:
            _gps_status_cache["timestamp"] = 0

        return jsonify(
            {
                "success": success,
                "latitude": latitude,
                "longitude": longitude,
                "gpstime": int(gpstime) if gpstime.isdigit() else 0,
                "utc_offset": int(utc_offset) if utc_offset.lstrip("-").isdigit() else 0,
                "gps_state": gps_state,
                "timeout_used": gps_timeout,
                "output": result.stdout,
                "returncode": result.returncode,
            }
        )

    except subprocess.TimeoutExpired:
        return jsonify(
            {
                "error": "GPS sync timeout",
                "message": f"GPS sync did not complete within {timeout} seconds",
            }
        ), 408
    except Exception:
        logger.exception("GPS sync failed")
        return jsonify({"error": "GPS sync failed"}), 500


def _update_gpsd_config(device, baudrate):
    """
    Update /etc/default/gpsd with new device and baud rate settings, then restart gpsd.

    This function updates the gpsd daemon configuration to apply new GPS device
    or baud rate settings. It requires sudo permissions to write to /etc/default/gpsd
    and restart the systemd service.

    Args:
        device: GPS device path (e.g., /dev/ttyAMA0)
        baudrate: GPS baud rate (e.g., 9600)

    Raises:
        subprocess.CalledProcessError: If sudo commands fail
        PermissionError: If user doesn't have sudo permissions

    Note:
        This causes a brief interruption to GPS data as gpsd restarts.
        Any GPS sync in progress will be interrupted.
    """
    gpsd_config_content = f"""# Mothbox GPS Configuration
# Automatically generated by WebUI

# Start gpsd automatically
START_DAEMON="true"

# GPS device(s)
DEVICES="{device}"

# gpsd options
# -n: Don't wait for client to connect
# -s: Set GPS speed/baudrate (configures the GPS module)
GPSD_OPTIONS="-n -s {baudrate}"

# Listen on all interfaces (for Web UI access)
GPSD_SOCKET="/var/run/gpsd.sock"
"""

    try:
        # Write config file (requires sudo)
        logger.info(f"Updating gpsd configuration: {device} @ {baudrate} baud")
        subprocess.run(
            ["sudo", "tee", "/etc/default/gpsd"],
            input=gpsd_config_content,
            text=True,
            capture_output=True,
            check=True,
        )

        # Restart gpsd service to apply changes
        logger.info("Restarting gpsd service...")
        subprocess.run(["sudo", "systemctl", "restart", "gpsd"], check=True)
        logger.info("gpsd configuration updated and service restarted")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update gpsd configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating gpsd: {e}")
        raise


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
    if "gps_enabled" in config_updates:
        updates["gps_enabled"] = "true" if config_updates["gps_enabled"] else "false"
    if "gps_device" in config_updates:
        updates["gps_device"] = config_updates["gps_device"]
    if "gps_baudrate" in config_updates:
        updates["gps_baudrate"] = str(config_updates["gps_baudrate"])
    if "gps_timeout" in config_updates:
        updates["gps_timeout"] = str(config_updates["gps_timeout"])
    if "gps_timeout_hot" in config_updates:
        updates["gps_timeout_hot"] = str(config_updates["gps_timeout_hot"])
    if "gps_timeout_warm" in config_updates:
        updates["gps_timeout_warm"] = str(config_updates["gps_timeout_warm"])
    if "gps_timeout_cold" in config_updates:
        updates["gps_timeout_cold"] = str(config_updates["gps_timeout_cold"])
    if "gps_timeout_almanac" in config_updates:
        updates["gps_timeout_almanac"] = str(config_updates["gps_timeout_almanac"])

    # Open file for read/write and acquire exclusive lock
    with open(CONTROLS_FILE, "r+") as f:
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
                if stripped and "=" in stripped and not stripped.startswith("#"):
                    key = stripped.split("=", 1)[0]
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
