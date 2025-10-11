"""Camera control endpoints"""
from flask import Blueprint, jsonify, request
import subprocess
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import MOTHBOX_HOME, PHOTOS_DIR

# Allowed camera settings with validation functions
ALLOWED_CAMERA_SETTINGS = {
    'ExposureTime': lambda v: str(v).isdigit() and 0 < int(v) < 1000000,
    'AnalogGain': lambda v: 1.0 <= float(v) <= 16.0,
    'Contrast': lambda v: -1.0 <= float(v) <= 1.0,
    'Brightness': lambda v: -1.0 <= float(v) <= 1.0,
    'Saturation': lambda v: -1.0 <= float(v) <= 1.0,
    'Sharpness': lambda v: 0.0 <= float(v) <= 16.0,
}

camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/capture', methods=['POST'])
def capture_photo():
    """Trigger a photo capture"""
    try:
        # Determine Pi version to find correct TakePhoto.py
        import platform
        from mothbox_paths import MOTHBOX_HOME

        print(f"Photo capture requested. MOTHBOX_HOME: {MOTHBOX_HOME}")

        # Check if Pi 4 or Pi 5
        pi_version = None
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("Model"):
                        if "Pi 4" in line:
                            pi_version = "4"
                        elif "Pi 5" in line:
                            pi_version = "5"
                        break
        except Exception as cpu_error:
            print(f"Error reading /proc/cpuinfo: {cpu_error}")

        # Default to 4.x if can't determine
        if not pi_version:
            pi_version = "4"
            print(f"Could not detect Pi version, defaulting to {pi_version}")
        else:
            print(f"Detected Pi version: {pi_version}")

        script_path = MOTHBOX_HOME / f"{pi_version}.x" / "TakePhoto.py"
        print(f"Looking for TakePhoto.py at: {script_path}")

        if not script_path.exists():
            error_msg = f'TakePhoto.py not found at {script_path}'
            print(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500

        print(f"Running: python3 {script_path}")
        result = subprocess.run(
            ['python3', str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"TakePhoto.py exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        if result.returncode == 0:
            # Find the most recent photo
            photos = sorted(PHOTOS_DIR.glob('**/*.jpg'), key=lambda p: p.stat().st_mtime, reverse=True)
            latest_photo = str(photos[0].relative_to(PHOTOS_DIR)) if photos else None

            # Invalidate photo count cache so dashboard shows updated count immediately
            from routes.system import invalidate_photo_count_cache
            invalidate_photo_count_cache()

            return jsonify({
                'success': True,
                'latest_photo': latest_photo,
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr or result.stdout
            }), 500

    except subprocess.TimeoutExpired:
        error_msg = 'Photo capture timed out'
        print(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Photo capture error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': error_msg}), 500

@camera_bp.route('/settings', methods=['GET'])
def get_camera_settings():
    """Get camera settings from CSV"""
    try:
        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        settings = {}
        with open(CAMERA_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                settings = row
                break

        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@camera_bp.route('/settings', methods=['POST'])
def update_camera_settings():
    """Update camera settings"""
    try:
        from mothbox_paths import CAMERA_SETTINGS_FILE
        import csv

        new_settings = request.json

        # Validate camera settings
        for key, value in new_settings.items():
            if key not in ALLOWED_CAMERA_SETTINGS:
                return jsonify({'error': f'Invalid setting: {key}'}), 400
            try:
                if not ALLOWED_CAMERA_SETTINGS[key](value):
                    return jsonify({'error': f'Invalid value for {key}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid type for {key}'}), 400

        # Read existing headers
        with open(CAMERA_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        # Sanitize values to prevent CSV injection (defense in depth)
        # Lazy import to avoid circular dependency with app.py
        from routes.config import _sanitize_csv_value
        sanitized_settings = {k: _sanitize_csv_value(v) for k, v in new_settings.items()}

        # Write updated settings
        with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(sanitized_settings)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
