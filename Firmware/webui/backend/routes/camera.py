"""Camera control endpoints"""
from flask import Blueprint, jsonify, request
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from mothbox_paths import get_script_path, PHOTOS_DIR

camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/capture', methods=['POST'])
def capture_photo():
    """Trigger a photo capture"""
    try:
        # Run TakePhoto.py script
        script_path = get_script_path('TakePhoto.py')
        result = subprocess.run(
            ['python3', str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Find the most recent photo
            photos = sorted(PHOTOS_DIR.glob('**/*.jpg'), key=lambda p: p.stat().st_mtime, reverse=True)
            latest_photo = str(photos[0].relative_to(PHOTOS_DIR)) if photos else None

            return jsonify({
                'success': True,
                'latest_photo': latest_photo,
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Photo capture timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

        # Read existing headers
        with open(CAMERA_SETTINGS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        # Write updated settings
        with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(new_settings)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
