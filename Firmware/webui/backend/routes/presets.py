"""Preset management endpoints"""
from flask import Blueprint, jsonify, request
import csv
from pathlib import Path
import sys

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from mothbox_paths import CAMERA_SETTINGS_FILE, WEBUI_SETTINGS_FILE, get_control_values, BUILTIN_PRESET_DIR, USER_PRESET_DIR
from preset_manager import PresetManager

# Import validation from existing routes
from routes.camera import ALLOWED_CAMERA_SETTINGS


presets_bp = Blueprint('presets', __name__)

# Initialize preset manager
preset_manager = PresetManager(BUILTIN_PRESET_DIR, USER_PRESET_DIR)


@presets_bp.route('/presets', methods=['GET'])
def list_presets():
    """
    List all available presets (built-in + user)

    Returns:
        JSON array of preset metadata:
        [
            {
                "name": "daylight",
                "display_name": "☀️ Daylight Photography",
                "description": "...",
                "category": "built-in",
                "version": "1.0"
            },
            ...
        ]
    """
    try:
        presets = preset_manager.list_presets()
        counts = preset_manager.get_preset_count()

        return jsonify({
            'presets': presets,
            'counts': counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@presets_bp.route('/presets/<name>', methods=['GET'])
def get_preset(name):
    """
    Get specific preset details by name

    Args:
        name: Preset name (e.g., 'daylight', 'my_preset_1')

    Returns:
        JSON preset data with full settings
    """
    try:
        preset_data = preset_manager.get_preset(name)

        if not preset_data:
            return jsonify({'error': f'Preset "{name}" not found'}), 404

        return jsonify(preset_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@presets_bp.route('/presets', methods=['POST'])
def create_preset():
    """
    Create new user preset from request data

    Request JSON:
        {
            "name": "my_preset",
            "description": "My custom preset",
            "from_current": true,  // If true, read current settings
            "settings": {  // Optional if from_current=true
                "camera": {...},
                "preview": {...}
            }
        }

    Returns:
        Success/error message
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Preset name is required'}), 400

        description = data.get('description', '').strip()
        from_current = data.get('from_current', False)

        # Get settings
        if from_current:
            # Read current camera and preview settings
            camera_settings = {}
            preview_settings = {}

            # Read camera_settings.csv
            if CAMERA_SETTINGS_FILE.exists():
                with open(CAMERA_SETTINGS_FILE, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        setting = row['SETTING']
                        value = row['VALUE']
                        camera_settings[setting] = value

            # Read webui_settings.txt
            if WEBUI_SETTINGS_FILE.exists():
                preview_settings = get_control_values(WEBUI_SETTINGS_FILE)

            settings = {
                'camera': camera_settings,
                'preview': preview_settings
            }
        else:
            settings = data.get('settings', {})

            if not settings:
                return jsonify({'error': 'Settings are required when from_current=false'}), 400

        # Save preset
        success, message = preset_manager.save_preset(name, settings, description)

        if success:
            return jsonify({'success': True, 'message': message, 'name': name})
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        import traceback
        print(f"Error creating preset: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@presets_bp.route('/presets/<name>/apply', methods=['POST'])
def apply_preset(name):
    """
    Apply preset to camera/preview/both settings

    Request JSON:
        {
            "apply_to": "capture" | "preview" | "both"
        }

    Returns:
        Success message with applied settings summary
    """
    try:
        data = request.json or {}
        apply_to = data.get('apply_to', 'capture')

        if apply_to not in ['capture', 'preview', 'both']:
            return jsonify({'error': 'apply_to must be "capture", "preview", or "both"'}), 400

        # Load preset
        preset_data = preset_manager.get_preset(name)

        if not preset_data:
            return jsonify({'error': f'Preset "{name}" not found'}), 404

        settings = preset_data.get('settings', {})

        if not settings:
            return jsonify({'error': 'Preset has no settings'}), 400

        camera_settings = settings.get('camera', {})
        preview_settings = settings.get('preview', {})

        applied = []

        # Apply to capture settings (camera_settings.csv)
        if apply_to in ['capture', 'both'] and camera_settings:
            # Validate all camera settings
            for key, value in camera_settings.items():
                if key not in ALLOWED_CAMERA_SETTINGS:
                    return jsonify({'error': f'Invalid camera setting: {key}'}), 400

                try:
                    if not ALLOWED_CAMERA_SETTINGS[key](value):
                        return jsonify({'error': f'Invalid value for camera setting {key}: {value}'}), 400
                except (ValueError, TypeError) as e:
                    return jsonify({'error': f'Invalid type for camera setting {key}: {value} ({str(e)})'}), 400

            # Read current camera_settings.csv
            csv_rows = []
            if CAMERA_SETTINGS_FILE.exists():
                with open(CAMERA_SETTINGS_FILE, 'r') as f:
                    reader = csv.DictReader(f)
                    csv_rows = [dict(row) for row in reader]

            # Update or add settings from preset
            for setting_name, setting_value in camera_settings.items():
                found = False
                for row in csv_rows:
                    if row['SETTING'].strip() == setting_name:
                        row['VALUE'] = str(setting_value)
                        found = True
                        break

                if not found:
                    csv_rows.append({
                        'SETTING': setting_name,
                        'VALUE': str(setting_value),
                        'DETAILS': ''
                    })

            # Write back to camera_settings.csv
            with open(CAMERA_SETTINGS_FILE, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['SETTING', 'VALUE', 'DETAILS'])
                writer.writeheader()
                writer.writerows(csv_rows)

            applied.append('capture')

        # Apply to preview settings (webui_settings.txt)
        if apply_to in ['preview', 'both'] and preview_settings:
            # Read current webui_settings.txt
            current_preview = {}
            if WEBUI_SETTINGS_FILE.exists():
                current_preview = get_control_values(WEBUI_SETTINGS_FILE)

            # Update with preset values
            current_preview.update(preview_settings)

            # Write back to webui_settings.txt
            with open(WEBUI_SETTINGS_FILE, 'w') as f:
                for key, value in current_preview.items():
                    f.write(f"{key}={value}\n")

            applied.append('preview')

        # Build response message
        if not applied:
            return jsonify({'error': 'No settings were applied (preset may be empty for selected target)'}), 400

        applied_str = ' and '.join(applied)
        message = f'Preset "{preset_data.get("display_name", name)}" applied to {applied_str} settings'

        return jsonify({
            'success': True,
            'message': message,
            'applied_to': applied,
            'preset_name': preset_data.get('display_name', name),
            'description': preset_data.get('description', '')
        })

    except Exception as e:
        import traceback
        print(f"Error applying preset: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@presets_bp.route('/presets/<name>', methods=['DELETE'])
def delete_preset(name):
    """
    Delete user preset (built-in presets are protected)

    Args:
        name: Preset name to delete

    Returns:
        Success/error message
    """
    try:
        success, message = preset_manager.delete_preset(name)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
