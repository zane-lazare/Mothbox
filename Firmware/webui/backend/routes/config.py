"""Configuration management endpoints"""
from flask import Blueprint, jsonify, request
import csv
import shutil
from datetime import datetime
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

# Valid BCM GPIO pins (BCM mode: GPIO 2-27)
VALID_BCM_GPIO_PINS = [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27]

config_bp = Blueprint('config', __name__)

def _create_backup(file_path, keep=5):
    """
    Create a timestamped backup of a configuration file.

    Args:
        file_path: Path to the file to backup
        keep: Number of backups to retain (default: 5)

    Returns:
        Path to the backup file
    """
    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f'{file_path.suffix}.backup.{timestamp}')

    try:
        shutil.copy2(file_path, backup_path)

        # Cleanup old backups - keep only the most recent 'keep' backups
        backup_pattern = f"{file_path.name}.backup.*"
        backups = sorted(file_path.parent.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        # Remove old backups beyond the keep limit
        for old_backup in backups[keep:]:
            try:
                old_backup.unlink()
            except Exception as e:
                print(f"Warning: Could not delete old backup {old_backup}: {e}")

        return backup_path
    except Exception as e:
        print(f"Warning: Failed to create backup of {file_path}: {e}")
        return None

# Whitelist of allowed controls.txt keys with validation functions
ALLOWED_CONTROLS = {
    'shutdown_enabled': lambda v: str(v).lower() in ['true', 'false'],
    'OnlyFlash': lambda v: str(v).lower() in ['true', 'false'],
    'LastCalibration': lambda v: str(v).replace('-', '').isdigit(),  # Allow negative numbers
    'nextWake': lambda v: str(v).replace('-', '').isdigit(),
    'name': lambda v: len(str(v)) <= 100 and '\n' not in str(v) and '\r' not in str(v),
    'softwareversion': lambda v: len(str(v)) <= 20 and '\n' not in str(v),
    'gpstime': lambda v: str(v).replace('-', '').replace('.', '').isdigit() or str(v) == '0',
    'UTCoff': lambda v: str(v).lstrip('-').isdigit() and -12 <= int(v) <= 14,
    'lat': lambda v: len(str(v)) <= 50 and '\n' not in str(v),
    'lon': lambda v: len(str(v)) <= 50 and '\n' not in str(v),
    'weekdays': lambda v: all(c in '0123456789;' for c in str(v)),
    'hours': lambda v: all(c in '0123456789;' for c in str(v)),
    'minutes': lambda v: str(v).isdigit() or all(c in '0123456789;' for c in str(v)),
    'runtime': lambda v: str(v).isdigit(),
    'Relay_Ch1': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'Relay_Ch2': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'Relay_Ch3': lambda v: str(v).isdigit() and int(v) in VALID_BCM_GPIO_PINS,
    'relay_enabled': lambda v: str(v).lower() in ['true', 'false'],
    'flash_duration_ms': lambda v: str(v).isdigit() and 50 <= int(v) <= 5000,  # 50ms to 5s flash duration
}

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
    """Update controls.txt configuration (with backup)"""
    backup_path = None
    try:
        new_controls = request.json

        if not isinstance(new_controls, dict):
            return jsonify({'error': 'Invalid request format'}), 400

        # Validate all keys are allowed
        invalid_keys = set(new_controls.keys()) - set(ALLOWED_CONTROLS.keys())
        if invalid_keys:
            return jsonify({'error': f'Invalid keys: {", ".join(invalid_keys)}'}), 400

        # Validate all values
        for key, value in new_controls.items():
            try:
                if not ALLOWED_CONTROLS[key](value):
                    return jsonify({'error': f'Invalid value for {key}: {value}'}), 400
            except (ValueError, TypeError) as e:
                return jsonify({'error': f'Invalid value for {key}: {value}'}), 400

        # Sanitize values - remove newlines and carriage returns
        sanitized = {
            k: str(v).replace('\n', '').replace('\r', '')
            for k, v in new_controls.items()
        }

        # Create backup before modification
        backup_path = _create_backup(CONTROLS_FILE)

        # Write new configuration
        with open(CONTROLS_FILE, 'w') as f:
            for key, value in sanitized.items():
                f.write(f"{key}={value}\n")

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, CONTROLS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
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

def _sanitize_csv_value(value):
    """Sanitize value to prevent CSV injection attacks"""
    str_value = str(value)

    # Prevent CSV formula injection by prefixing with single quote if starts with dangerous chars
    if str_value.startswith(('=', '+', '-', '@', '\t', '\r')):
        str_value = "'" + str_value

    # Remove newlines and carriage returns to prevent multi-line injection
    str_value = str_value.replace('\n', ' ').replace('\r', ' ')

    # Limit length to prevent DoS
    if len(str_value) > 1000:
        str_value = str_value[:1000]

    return str_value

@config_bp.route('/schedule', methods=['POST'])
def update_schedule_settings():
    """Update schedule settings (with backup)"""
    backup_path = None
    try:
        new_settings = request.json

        if not isinstance(new_settings, dict):
            return jsonify({'error': 'Invalid request format'}), 400

        # Read existing headers
        with open(SCHEDULE_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        # Validate that all keys match existing fieldnames
        invalid_keys = set(new_settings.keys()) - set(fieldnames)
        if invalid_keys:
            return jsonify({'error': f'Invalid keys: {", ".join(invalid_keys)}'}), 400

        # Sanitize all values to prevent CSV injection
        sanitized_settings = {
            k: _sanitize_csv_value(v)
            for k, v in new_settings.items()
        }

        # Create backup before modification
        backup_path = _create_backup(SCHEDULE_SETTINGS_FILE)

        # Write updated settings
        with open(SCHEDULE_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(sanitized_settings)

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, SCHEDULE_SETTINGS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
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
    """Update WebUI stream settings (with backup)"""
    backup_path = None
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

        # Create backup before modification
        backup_path = _create_backup(WEBUI_SETTINGS_FILE)

        # Write settings to file
        with open(WEBUI_SETTINGS_FILE, 'w') as f:
            f.write(f"preview_width={preview_width}\n")
            f.write(f"preview_height={preview_height}\n")
            f.write(f"frame_rate={frame_rate}\n")
            f.write(f"jpeg_quality={jpeg_quality}\n")

        return jsonify({'success': True})
    except Exception as e:
        # Restore backup if write failed
        if backup_path and backup_path.exists():
            try:
                shutil.copy2(backup_path, WEBUI_SETTINGS_FILE)
                print(f"Restored backup from {backup_path} after error")
            except Exception as restore_error:
                print(f"Failed to restore backup: {restore_error}")
        return jsonify({'error': str(e)}), 500
