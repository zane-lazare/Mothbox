"""User preferences API endpoints"""

import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

# Setup path to import mothbox modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from preset_manager import PresetManager
from user_preferences import preferences_manager

from mothbox_paths import BUILTIN_PRESET_DIR, USER_PRESET_DIR

preferences_bp = Blueprint("preferences", __name__)

# Initialize preset manager for validation
preset_manager = PresetManager(BUILTIN_PRESET_DIR, USER_PRESET_DIR)


@preferences_bp.route("", methods=["GET"], strict_slashes=False)
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
        return jsonify({"error": str(e)}), 500


@preferences_bp.route("", methods=["POST"], strict_slashes=False)
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
            return jsonify({"error": "No data provided"}), 400

        key = data.get("key")
        value = data.get("value")

        if not key:
            return jsonify({"error": "Preference key is required"}), 400

        # Value can be None (to clear a default)
        if value is not None and not isinstance(value, (str, int, float, bool, type(None))):
            return jsonify({"error": "Invalid value type"}), 400

        # Set preference
        success = preferences_manager.set_preference(key, value)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f'Preference "{key}" updated successfully',
                    "key": key,
                    "value": value,
                }
            )
        else:
            return jsonify({"error": f'Failed to set preference "{key}"'}), 400

    except Exception as e:
        import traceback

        print(f"Error setting preference: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@preferences_bp.route("/reset", methods=["POST"])
def reset_preferences():
    """
    Reset all preferences to defaults

    Returns:
        Success/error message
    """
    try:
        success = preferences_manager.reset_preferences()

        if success:
            return jsonify({"success": True, "message": "All preferences reset to defaults"})
        else:
            return jsonify({"error": "Failed to reset preferences"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@preferences_bp.route("/validate", methods=["POST"])
def validate_preferences():
    """
    Validate preset references and clean up deleted preset references

    Returns:
        Validation results with cleaned preferences
    """
    try:
        result = preferences_manager.validate_preset_references(preset_manager)

        if result["cleaned"]:
            message = f"Cleaned {len(result['removed_references'])} invalid preset reference(s)"
            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "cleaned": True,
                    "removed_references": [
                        {"key": key, "invalid_value": value}
                        for key, value in result["removed_references"]
                    ],
                    "preferences": result["preferences"],
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "message": "All preset references are valid",
                    "cleaned": False,
                    "preferences": result["preferences"],
                }
            )

    except Exception as e:
        import traceback

        print(f"Error validating preferences: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
