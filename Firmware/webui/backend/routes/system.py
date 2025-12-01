"""System status and monitoring endpoints"""

import shutil
import threading
import time
from pathlib import Path

# Setup path to import mothbox_paths
from config import get_config
from flask import Blueprint, jsonify

from mothbox_paths import (
    CAMERA_SETTINGS_FILE,
    CONFIG_DIR,
    CONTROLS_FILE,
    FIRMWARE_DIR,
    MOTHBOX_HOME,
    PHOTOS_DIR,
    SCHEDULE_SETTINGS_FILE,
    _installation_type,
    get_control_values,
    get_gpio_pins,
    get_hardware_config,
)
from routes.gps import _get_cached_gps_status

system_bp = Blueprint("system", __name__)

# Get configuration to check DEBUG mode
config = get_config()

# Photo count cache to avoid expensive directory scans on every request
# Cache is valid for 15 seconds (better balance between performance and freshness)
_photo_count_cache = {"count": None, "timestamp": 0, "lock": threading.Lock()}
PHOTO_COUNT_CACHE_TTL = 15  # seconds - reduced from 60 for better UX


def _get_cached_photo_count():
    """
    Get photo count with caching to avoid expensive directory scans.

    Returns cached count if less than PHOTO_COUNT_CACHE_TTL seconds old,
    otherwise performs fresh count and updates cache.

    Returns:
        int: Number of .jpg files in PHOTOS_DIR
    """
    current_time = time.time()

    with _photo_count_cache["lock"]:
        # Check if cache is still valid
        if (
            _photo_count_cache["count"] is not None
            and current_time - _photo_count_cache["timestamp"] < PHOTO_COUNT_CACHE_TTL
        ):
            return _photo_count_cache["count"]

        # Cache expired or empty, perform count
        try:
            count = len(list(PHOTOS_DIR.glob("**/*.jpg"))) if PHOTOS_DIR.exists() else 0

            # Update cache
            _photo_count_cache["count"] = count
            _photo_count_cache["timestamp"] = current_time

            return count
        except Exception as e:
            print(f"Warning: Failed to count photos: {e}")
            # Return cached value if available, otherwise 0
            return _photo_count_cache["count"] if _photo_count_cache["count"] is not None else 0


def invalidate_photo_count_cache():
    """
    Invalidate photo count cache to force refresh on next request.

    Called after photo capture to ensure count updates immediately
    without waiting for cache TTL to expire.
    """
    with _photo_count_cache["lock"]:
        _photo_count_cache["timestamp"] = 0  # Force cache miss on next read


@system_bp.route("/status", methods=["GET"])
def get_system_status():
    """Get overall system status"""
    try:
        # CPU temperature
        temp_file = Path("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = float(temp_file.read_text().strip()) / 1000 if temp_file.exists() else None

        # Disk usage
        disk_usage = shutil.disk_usage("/")
        disk_free_gb = disk_usage.free / (1024**3)
        disk_total_gb = disk_usage.total / (1024**3)
        disk_used_percent = (disk_usage.used / disk_usage.total) * 100

        # Photo count (cached for performance)
        photo_count = _get_cached_photo_count()

        # Hardware config
        hw_config = get_hardware_config()

        # GPS data from cached status (reduces duplicate file I/O)
        gps_status = _get_cached_gps_status()

        return jsonify(
            {
                "cpu_temp": cpu_temp,
                "disk": {
                    "free_gb": round(disk_free_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "used_percent": round(disk_used_percent, 2),
                },
                "photo_count": photo_count,
                "hardware": {
                    "ina260_enabled": hw_config.get("ina260_enabled", False),
                    "gps_enabled": hw_config.get("gps_enabled", False),
                    "epaper_enabled": hw_config.get("epaper_enabled", False),
                },
                "gps": {
                    "enabled": gps_status["enabled"],
                    "latitude": gps_status["latitude"],
                    "longitude": gps_status["longitude"],
                    "last_sync": gps_status["gpstime"],
                    "utc_offset": gps_status["utc_offset"],
                    "has_fix": gps_status["has_fix"],
                },
            }
        )
    except Exception as e:
        print(f"Error getting storage info: {e}")
        return jsonify({"error": "Failed to get storage info"}), 500


@system_bp.route("/power", methods=["GET"])
def get_power_status():
    """Get power metrics from INA260 if available"""
    try:
        hw_config = get_hardware_config()
        if not hw_config.get("ina260_enabled"):
            return jsonify({"enabled": False})

        # TODO: Implement power monitoring
        # See: https://github.com/zane-lazare/Mothbox/issues/73
        return jsonify({"enabled": True, "voltage": None, "current": None, "power": None})
    except Exception as e:
        print(f"Error getting power status: {e}")
        return jsonify({"error": "Failed to get power status"}), 500


@system_bp.route("/info", methods=["GET"])
def get_system_info():
    """Get system installation and configuration info"""
    try:
        # Get GPIO pins configuration
        gpio_pins = get_gpio_pins()

        # Get controls values
        controls = get_control_values(CONTROLS_FILE)
        firmware_version = controls.get("softwareversion", "unknown")

        # Check if GPIO pins are defined in controls.txt
        has_gpio_in_config = all(key in controls for key in ["Relay_Ch1", "Relay_Ch2", "Relay_Ch3"])
        gpio_source = "controls.txt" if has_gpio_in_config else "defaults"

        return jsonify(
            {
                "installation_type": _installation_type,
                "firmware_version": firmware_version,
                "mothbox_home": str(MOTHBOX_HOME),
                "config_dir": str(CONFIG_DIR),
                "firmware_dir": str(FIRMWARE_DIR),
                "gpio_pins": gpio_pins,
                "gpio_source": gpio_source,
            }
        )
    except Exception:
        import traceback

        # Log full traceback server-side for debugging
        # Server logs are only accessible to administrators
        print("Error in /api/system/info:")
        print(traceback.format_exc())

        # Build error response - never include traceback in API response
        # Tracebacks reveal internal paths, versions, and code structure
        # even in development mode, as the API may be accessible from network
        return jsonify({"error": "Failed to get system info"}), 500


@system_bp.route("/diagnostic", methods=["GET"])
def get_diagnostic_info():
    """Get detailed diagnostic information for troubleshooting"""
    try:
        # Check path existence
        controls = get_control_values(CONTROLS_FILE)
        controls_size = CONTROLS_FILE.stat().st_size if CONTROLS_FILE.exists() else 0

        # Count raw lines in controls.txt
        raw_lines = 0
        if CONTROLS_FILE.exists():
            with open(CONTROLS_FILE) as f:
                raw_lines = len(f.readlines())

        # Get hardware config
        hw_config = get_hardware_config()

        # Check for GPIO pins in config
        has_gpio_pins = all(key in controls for key in ["Relay_Ch1", "Relay_Ch2", "Relay_Ch3"])

        return jsonify(
            {
                "paths": {
                    "mothbox_home": str(MOTHBOX_HOME),
                    "mothbox_home_exists": MOTHBOX_HOME.exists(),
                    "config_dir": str(CONFIG_DIR),
                    "config_dir_exists": CONFIG_DIR.exists(),
                    "firmware_dir": str(FIRMWARE_DIR),
                    "firmware_dir_exists": FIRMWARE_DIR.exists(),
                    "controls_file": str(CONTROLS_FILE),
                    "controls_file_exists": CONTROLS_FILE.exists(),
                    "controls_file_size": controls_size,
                    "camera_settings_file": str(CAMERA_SETTINGS_FILE),
                    "camera_settings_file_exists": CAMERA_SETTINGS_FILE.exists(),
                    "schedule_settings_file": str(SCHEDULE_SETTINGS_FILE),
                    "schedule_settings_file_exists": SCHEDULE_SETTINGS_FILE.exists(),
                },
                "controls_content": {
                    "raw_lines": raw_lines,
                    "parsed_keys": list(controls.keys()),
                    "has_gpio_pins": has_gpio_pins,
                    "sample_values": {
                        "softwareversion": controls.get("softwareversion", "not found"),
                        "name": controls.get("name", "not found"),
                        "Relay_Ch1": controls.get("Relay_Ch1", "not found"),
                        "Relay_Ch2": controls.get("Relay_Ch2", "not found"),
                        "Relay_Ch3": controls.get("Relay_Ch3", "not found"),
                    },
                },
                "hardware_config": {
                    "ina260_enabled": hw_config.get("ina260_enabled", False),
                    "gps_enabled": hw_config.get("gps_enabled", False),
                    "epaper_enabled": hw_config.get("epaper_enabled", False),
                    "relay_enabled": hw_config.get("relay_enabled", True),
                    "light_sensor_enabled": hw_config.get("light_sensor_enabled", False),
                    "pca9536_enabled": hw_config.get("pca9536_enabled", False),
                    "mux_enabled": hw_config.get("mux_enabled", False),
                },
                "gpio_pins": get_gpio_pins(),
            }
        )
    except Exception:
        import traceback

        # Log full traceback server-side for debugging
        print("Error in /api/system/diagnostic:")
        print(traceback.format_exc())

        # Return generic error - traceback already logged server-side
        return jsonify({"error": "Failed to get diagnostic info"}), 500
