"""
Export preset management endpoints.

Provides REST API for managing export presets:
- GET /api/export/presets - List all presets
- GET /api/export/presets/<name> - Get preset details
- POST /api/export/presets - Create user preset (rate limited: 10/min)
- DELETE /api/export/presets/<name> - Delete user preset

CSRF Protection:
    All state-changing endpoints (POST, DELETE) require CSRF token validation.
    GET endpoints are read-only and exempt from CSRF.
    Clients must include X-CSRFToken header with valid token from /api/csrf-token.
"""

import logging

from flask import Blueprint, current_app, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from webui.backend.lib.error_codes import (
    NOT_FOUND,
    SERVER_ERROR,
    VALIDATION_ERROR,
    error_response,
)
from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

logger = logging.getLogger(__name__)

export_presets_bp = Blueprint("export_presets", __name__)

# Rate limiter for preset endpoints
limiter = Limiter(key_func=get_remote_address)


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
    except Exception:
        logger.exception("Error listing export presets")
        return error_response(SERVER_ERROR, "Failed to list export presets", 500)


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
            return error_response(NOT_FOUND, f"Preset '{name}' not found", 404)

        # Convert ExportPreset to dict for JSON response
        return jsonify(preset.to_dict())
    except Exception:
        logger.exception("Error getting export preset '%s'", name)
        return error_response(SERVER_ERROR, "Failed to get export preset", 500)


@export_presets_bp.route("", methods=["POST"], strict_slashes=False)
@limiter.limit("10 per minute")
def create_export_preset():
    """
    Create new user export preset.

    Rate limited to 10 requests per minute per IP.

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
            return error_response(VALIDATION_ERROR, "No data provided")

        # Validate required fields
        name = data.get("name", "").strip()
        if not name:
            return error_response(VALIDATION_ERROR, "Preset name is required")

        display_name = data.get("display_name", "").strip()
        if not display_name:
            return error_response(VALIDATION_ERROR, "Preset display_name is required")

        export_format_str = data.get("export_format", "").strip()
        if not export_format_str:
            return error_response(VALIDATION_ERROR, "Preset export_format is required")

        # Validate export format
        try:
            export_format = ExportJobFormat(export_format_str)
        except ValueError:
            valid_formats = [f.value for f in ExportJobFormat]
            return error_response(
                VALIDATION_ERROR,
                f"Invalid export_format. Must be one of: {valid_formats}",
            )

        # Reject built-in category
        if data.get("category") == "built-in":
            return error_response(VALIDATION_ERROR, "Cannot create preset with built-in category")

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
            return error_response(VALIDATION_ERROR, message)

    except Exception:
        logger.exception("Error creating export preset")
        return error_response(SERVER_ERROR, "Failed to create export preset", 500)


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
                return error_response(NOT_FOUND, message, 404)
            elif "built-in" in message.lower():
                return error_response(VALIDATION_ERROR, message)
            else:
                return error_response(VALIDATION_ERROR, message)

    except Exception:
        logger.exception("Error deleting export preset '%s'", name)
        return error_response(SERVER_ERROR, "Failed to delete export preset", 500)
