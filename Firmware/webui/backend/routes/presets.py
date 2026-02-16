"""Preset management endpoints"""

import csv
import logging

# Setup path to import mothbox_paths
from flask import Blueprint, jsonify, request
from preset_manager import PresetManager

# Import validation from utils
from utils import ALLOWED_CAMERA_SETTINGS, ALLOWED_WEBUI_SETTINGS, coerce_for_csv

from mothbox_paths import (
    BUILTIN_PRESET_DIR,
    CAMERA_SETTINGS_FILE,
    LIVEVIEW_SETTINGS_FILE,
    USER_PRESET_DIR,
    get_control_values,
)
from webui.backend.lib.error_codes import (
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)

logger = logging.getLogger(__name__)

presets_bp = Blueprint("presets", __name__)

# Initialize preset manager
preset_manager = PresetManager(BUILTIN_PRESET_DIR, USER_PRESET_DIR)


@presets_bp.route("", methods=["GET"], strict_slashes=False)
def list_presets():
    """
    List all available presets (built-in + user)

    Query params:
        workflow: Filter by workflow type ('photo', 'liveview', or 'both')

    Returns:
        JSON array of preset metadata:
        [
            {
                "name": "daylight",
                "display_name": "☀️ Daylight Photography",
                "description": "...",
                "category": "built-in",
                "version": "1.0",
                "workflow": "both"
            },
            ...
        ]
    """
    try:
        presets = preset_manager.list_presets()

        # Filter by workflow if specified
        workflow_filter = request.args.get("workflow")
        if workflow_filter:
            presets = [
                p
                for p in presets
                if p.get("workflow") == workflow_filter or p.get("workflow") == "both"
            ]

        counts = preset_manager.get_preset_count()

        return jsonify({"presets": presets, "counts": counts})
    except Exception as e:
        logger.error(f"Error listing presets: {e}")
        return error_response(SERVER_ERROR, "Failed to list presets", 500)


@presets_bp.route("/<name>", methods=["GET"])
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
            return error_response(NOT_FOUND, f'Preset "{name}" not found', 404)

        return jsonify(preset_data)
    except Exception as e:
        logger.error(f"Error getting preset '{name}': {e}")
        return error_response(SERVER_ERROR, "Failed to get preset", 500)


@presets_bp.route("", methods=["POST"], strict_slashes=False)
def create_preset():
    """
    Create new user preset from request data

    Request JSON:
        {
            "name": "my_preset",
            "description": "My custom preset",
            "workflow": "photo",  // 'photo', 'liveview', or 'both'
            "from_current": true,  // If true, read current settings
            "settings": {  // Optional if from_current=true
                "camera": {...},
                "liveview": {...}
            }
        }

    Returns:
        Success/error message
    """
    try:
        data = request.json

        if not data:
            return error_response(VALIDATION_ERROR, "No data provided")

        name = data.get("name", "").strip()
        if not name:
            return error_response(VALIDATION_ERROR, "Preset name is required")

        description = data.get("description", "").strip()
        workflow = data.get("workflow", "both")
        from_current = data.get("from_current", False)

        # Get settings
        if from_current:
            # Read current camera and live view settings
            camera_settings = {}
            liveview_settings = {}

            # Read camera_settings.csv
            if CAMERA_SETTINGS_FILE.exists():
                with open(CAMERA_SETTINGS_FILE) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        setting = row["SETTING"]
                        value = row["VALUE"]
                        camera_settings[setting] = value

            # Read liveview_settings.txt
            if LIVEVIEW_SETTINGS_FILE.exists():
                liveview_settings = get_control_values(LIVEVIEW_SETTINGS_FILE)

            settings = {"camera": camera_settings, "liveview": liveview_settings}
        else:
            settings = data.get("settings", {})

            if not settings:
                return error_response(
                    VALIDATION_ERROR, "Settings are required when from_current=false"
                )

        # Save preset
        success, message = preset_manager.save_preset(
            name, settings, description, workflow=workflow
        )

        if success:
            return jsonify({"success": True, "message": message, "name": name})
        else:
            return error_response(VALIDATION_ERROR, message)

    except Exception as e:
        import traceback

        logger.error(f"Error creating preset: {e}")
        logger.error(traceback.format_exc())
        return error_response(SERVER_ERROR, "Failed to create preset", 500)


@presets_bp.route("/<name>/apply", methods=["POST"])
def apply_preset(name):
    """
    Apply preset to camera/liveview/both settings

    Request JSON:
        {
            "apply_to": "capture" | "liveview" | "both"
        }

    Returns:
        Success message with applied settings summary
    """
    try:
        data = request.json or {}
        apply_to = data.get("apply_to", "capture")

        if apply_to not in ["capture", "liveview", "both"]:
            return error_response(
                VALIDATION_ERROR, 'apply_to must be "capture", "liveview", or "both"'
            )

        # Load preset
        preset_data = preset_manager.get_preset(name)

        if not preset_data:
            return error_response(NOT_FOUND, f'Preset "{name}" not found', 404)

        settings = preset_data.get("settings", {})

        if not settings:
            return error_response(VALIDATION_ERROR, "Preset has no settings")

        # Check preset workflow compatibility
        preset_workflow = preset_data.get("workflow", "both")
        camera_settings = settings.get("camera", {})
        liveview_settings = settings.get("liveview", {})

        # Validate workflow compatibility before attempting to apply
        if apply_to == "capture":
            if not camera_settings:
                if preset_workflow == "liveview":
                    return error_response(
                        VALIDATION_ERROR,
                        f'Cannot apply liveview-only preset "{name}" to capture workflow. This preset only contains liveview/preview settings.',
                    )
                else:
                    return error_response(
                        VALIDATION_ERROR,
                        f'Preset "{name}" has no camera settings. '
                        f"This may indicate a corrupted preset file. "
                        f'Try re-saving the preset using "Save As" to recreate it.',
                    )
        elif apply_to == "liveview":
            if not liveview_settings:
                if preset_workflow == "photo":
                    return error_response(
                        VALIDATION_ERROR,
                        f'Cannot apply photo-only preset "{name}" to liveview workflow. This preset only contains camera/capture settings.',
                    )
                else:
                    return error_response(
                        VALIDATION_ERROR,
                        f'Preset "{name}" has no liveview settings. '
                        f"This may indicate a corrupted preset file. "
                        f'Try re-saving the preset using "Save As" to recreate it.',
                    )
        elif apply_to == "both" and not camera_settings and not liveview_settings:
            return error_response(
                VALIDATION_ERROR, f'Preset "{name}" has no settings for either workflow'
            )

        applied = []

        # Apply to capture settings (camera_settings.csv)
        if apply_to in ["capture", "both"] and camera_settings:
            # Validate all camera settings
            for key, value in camera_settings.items():
                # Accept both picamera2 settings and webui workflow settings
                # (HDR, FocusBracket, etc.) — TakePhoto.py reads all from
                # camera_settings.csv and pops workflow keys before set_controls()
                if key in ALLOWED_CAMERA_SETTINGS:
                    validator = ALLOWED_CAMERA_SETTINGS[key]
                elif key in ALLOWED_WEBUI_SETTINGS:
                    validator = ALLOWED_WEBUI_SETTINGS[key]
                else:
                    return error_response(VALIDATION_ERROR, f"Invalid camera setting: {key}")

                try:
                    if not validator(value):
                        return error_response(
                            VALIDATION_ERROR,
                            f"Invalid value for camera setting {key}: {value}",
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid type for camera setting {key}: {value} - {e}")
                    return error_response(
                        VALIDATION_ERROR,
                        f"Invalid type for camera setting {key}: {value}",
                    )

            # Read current camera_settings.csv
            csv_rows = []
            if CAMERA_SETTINGS_FILE.exists():
                with open(CAMERA_SETTINGS_FILE) as f:
                    reader = csv.DictReader(f)
                    csv_rows = [dict(row) for row in reader]

            # Update or add settings from preset
            for setting_name, setting_value in camera_settings.items():
                found = False
                for row in csv_rows:
                    if row["SETTING"].strip() == setting_name:
                        row["VALUE"] = coerce_for_csv(setting_name, setting_value)
                        found = True
                        break

                if not found:
                    csv_rows.append(
                        {
                            "SETTING": setting_name,
                            "VALUE": coerce_for_csv(setting_name, setting_value),
                            "DETAILS": "",
                        }
                    )

            # Write back to camera_settings.csv
            with open(CAMERA_SETTINGS_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["SETTING", "VALUE", "DETAILS"])
                writer.writeheader()
                writer.writerows(csv_rows)

            applied.append("capture")

        # Apply to live view settings (liveview_settings.txt)
        if apply_to in ["liveview", "both"] and liveview_settings:
            # Read current liveview_settings.txt
            current_liveview = {}
            if LIVEVIEW_SETTINGS_FILE.exists():
                current_liveview = get_control_values(LIVEVIEW_SETTINGS_FILE)

            # Update with preset values
            current_liveview.update(liveview_settings)

            # Write back to liveview_settings.txt
            with open(LIVEVIEW_SETTINGS_FILE, "w") as f:
                for key, value in current_liveview.items():
                    f.write(f"{key}={value}\n")

            applied.append("liveview")

        # Build response message
        if not applied:
            return error_response(
                VALIDATION_ERROR,
                "No settings were applied (preset may be empty for selected target)",
            )

        applied_str = " and ".join(applied)
        message = (
            f'Preset "{preset_data.get("display_name", name)}" applied to {applied_str} settings'
        )

        return jsonify(
            {
                "success": True,
                "message": message,
                "applied_to": applied,
                "preset_name": preset_data.get("display_name", name),
                "description": preset_data.get("description", ""),
            }
        )

    except Exception as e:
        import traceback

        logger.error(f"Error applying preset: {e}")
        logger.error(traceback.format_exc())
        return error_response(SERVER_ERROR, "Failed to apply preset", 500)


@presets_bp.route("/<name>", methods=["DELETE"])
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
            return jsonify({"success": True, "message": message})
        else:
            return error_response(VALIDATION_ERROR, message)

    except Exception as e:
        logger.error(f"Error deleting preset '{name}': {e}")
        return error_response(SERVER_ERROR, "Failed to delete preset", 500)
