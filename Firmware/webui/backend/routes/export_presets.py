"""
Export preset management endpoints.

Provides REST API for managing export presets:
- GET /api/export/presets - List all presets
- GET /api/export/presets/<name> - Get preset details
- POST /api/export/presets - Create user preset
- DELETE /api/export/presets/<name> - Delete user preset
"""

import logging

from flask import Blueprint, current_app, jsonify, request

from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

logger = logging.getLogger(__name__)

export_presets_bp = Blueprint("export_presets", __name__)


def _get_preset_manager():
    """Get ExportPresetManager from app config."""
    return current_app.config.get("EXPORT_PRESET_MANAGER")


@export_presets_bp.route("", methods=["GET"], strict_slashes=False)
def list_export_presets():
    """
    List all available export presets (built-in + user).

    Query params:
        format: Filter by export format (darwin_core, inaturalist, json, csv)

    Returns:
        JSON object with:
        - presets: Array of preset metadata
        - counts: Preset counts by category
    """
    try:
        preset_manager = _get_preset_manager()

        # Get optional format filter
        format_filter = request.args.get("format")

        presets = preset_manager.list_presets(format_filter=format_filter)
        counts = preset_manager.get_preset_count()

        return jsonify({"presets": presets, "counts": counts})
    except Exception as e:
        logger.error(f"Error listing export presets: {e}")
        return jsonify({"error": "Failed to list export presets"}), 500


@export_presets_bp.route("/<name>", methods=["GET"])
def get_export_preset(name: str):
    """
    Get specific export preset by name.

    Args:
        name: Preset name (without .json extension)

    Returns:
        JSON preset data with full configuration
    """
    try:
        preset_manager = _get_preset_manager()
        preset = preset_manager.get_preset(name)

        if not preset:
            return jsonify({"error": f"Preset '{name}' not found"}), 404

        # Convert ExportPreset to dict for JSON response
        return jsonify(preset.to_dict())
    except Exception as e:
        logger.error(f"Error getting export preset '{name}': {e}")
        return jsonify({"error": "Failed to get export preset"}), 500


@export_presets_bp.route("", methods=["POST"], strict_slashes=False)
def create_export_preset():
    """
    Create new user export preset.

    Request JSON:
        {
            "name": "my_preset",
            "display_name": "My Preset",
            "export_format": "json",
            "description": "My custom preset",
            "filter": {
                "has_species": true,
                "tags": ["moth"]
            },
            "options": {}
        }

    Returns:
        Success/error message with preset name
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Preset name is required"}), 400

        display_name = data.get("display_name", "").strip()
        if not display_name:
            return jsonify({"error": "Preset display_name is required"}), 400

        export_format_str = data.get("export_format", "").strip()
        if not export_format_str:
            return jsonify({"error": "Preset export_format is required"}), 400

        # Validate export format
        try:
            export_format = ExportJobFormat(export_format_str)
        except ValueError:
            valid_formats = [f.value for f in ExportJobFormat]
            return jsonify(
                {"error": f"Invalid export_format. Must be one of: {valid_formats}"}
            ), 400

        # Reject built-in category
        if data.get("category") == "built-in":
            return jsonify({"error": "Cannot create preset with built-in category"}), 400

        # Build filter from request
        filter_data = data.get("filter", {})
        filter_obj = ExportJobFilter.from_dict(filter_data)

        # Build preset
        preset = ExportPreset(
            name=name,
            display_name=display_name,
            export_format=export_format,
            description=data.get("description", ""),
            filter=filter_obj,
            options=data.get("options", {}),
            category=ExportPresetCategory.USER,
        )

        # Save preset
        preset_manager = _get_preset_manager()
        success, message = preset_manager.save_preset(preset)

        if success:
            return jsonify({"success": True, "message": message, "name": name}), 201
        else:
            return jsonify({"error": message}), 400

    except Exception as e:
        logger.error(f"Error creating export preset: {e}")
        return jsonify({"error": "Failed to create export preset"}), 500


@export_presets_bp.route("/<name>", methods=["DELETE"])
def delete_export_preset(name: str):
    """
    Delete user export preset (built-in presets are protected).

    Args:
        name: Preset name to delete

    Returns:
        Success/error message
    """
    try:
        preset_manager = _get_preset_manager()
        success, message = preset_manager.delete_preset(name)

        if success:
            return jsonify({"success": True, "message": message})
        else:
            # Determine appropriate status code
            if "not found" in message.lower():
                return jsonify({"error": message}), 404
            elif "built-in" in message.lower():
                return jsonify({"error": message}), 400
            else:
                return jsonify({"error": message}), 400

    except Exception as e:
        logger.error(f"Error deleting export preset '{name}': {e}")
        return jsonify({"error": "Failed to delete export preset"}), 500
