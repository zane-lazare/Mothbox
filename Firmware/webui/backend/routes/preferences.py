"""User preferences API endpoints"""
from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

# Setup path to import mothbox modules
sys.path.insert(0, str(Path(__file__).parent.parent))
import mothbox_import  # Sets up sys.path for mothbox

from user_preferences import preferences_manager


preferences_bp = Blueprint('preferences', __name__)


@preferences_bp.route('', methods=['GET'], strict_slashes=False)
def get_preferences():
    """
    Get all user preferences

    Returns:
        JSON object with all preference key-value pairs:
        {
            "default_capture_preset": "daylight",
            "default_preview_preset": "balanced"
        }
    """
    try:
        prefs = preferences_manager.get_preferences()
        return jsonify(prefs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('', methods=['POST'], strict_slashes=False)
def set_preference():
    """
    Set a specific preference

    Request JSON:
        {
            "key": "default_capture_preset",
            "value": "daylight"
        }

    Returns:
        Success/error message
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        key = data.get('key')
        value = data.get('value')

        if not key:
            return jsonify({'error': 'Preference key is required'}), 400

        # Value can be None (to clear a default)
        if value is not None and not isinstance(value, (str, int, float, bool, type(None))):
            return jsonify({'error': 'Invalid value type'}), 400

        # Set preference
        success = preferences_manager.set_preference(key, value)

        if success:
            return jsonify({
                'success': True,
                'message': f'Preference "{key}" updated successfully',
                'key': key,
                'value': value
            })
        else:
            return jsonify({'error': f'Failed to set preference "{key}"'}), 400

    except Exception as e:
        import traceback
        print(f"Error setting preference: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/reset', methods=['POST'])
def reset_preferences():
    """
    Reset all preferences to defaults

    Returns:
        Success/error message
    """
    try:
        success = preferences_manager.reset_preferences()

        if success:
            return jsonify({
                'success': True,
                'message': 'All preferences reset to defaults'
            })
        else:
            return jsonify({'error': 'Failed to reset preferences'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500
