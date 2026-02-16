"""User preferences API endpoints"""

import logging

from flask import Blueprint, jsonify, request

# Setup path to import mothbox modules
from preset_manager import PresetManager
from user_preferences import preferences_manager

from mothbox_paths import BUILTIN_PRESET_DIR, USER_PRESET_DIR
from webui.backend.lib.error_codes import (
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)

logger = logging.getLogger(__name__)

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
    except Exception:
        logger.exception("Failed to get preferences")
        return error_response(SERVER_ERROR, "Failed to get preferences", 500)


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
            return error_response(VALIDATION_ERROR, "No data provided")

        key = data.get("key")
        value = data.get("value")

        if not key:
            return error_response(VALIDATION_ERROR, "Preference key is required")

        # Value can be None (to clear a default)
        if value is not None and not isinstance(value, (str, int, float, bool, type(None))):
            return error_response(VALIDATION_ERROR, "Invalid value type")

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
            return error_response(VALIDATION_ERROR, f'Failed to set preference "{key}"')

    except Exception:
        logger.exception("Error setting preference")
        return error_response(SERVER_ERROR, "Failed to set preference", 500)


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
            return error_response(SERVER_ERROR, "Failed to reset preferences", 500)

    except Exception:
        logger.exception("Error resetting preferences")
        return error_response(SERVER_ERROR, "Failed to reset preferences", 500)


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

    except Exception:
        logger.exception("Error validating preferences")
        return error_response(SERVER_ERROR, "Failed to validate preferences", 500)
