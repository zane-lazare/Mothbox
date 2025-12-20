"""
High-level Scheduler UI API routes.

Provides REST endpoints for the visual scheduler UI, including:
- Schedule preview generation
- Future: Schedule CRUD operations
- Future: Pattern management

Issue #214 - Scheduler Phase 3: Schedule Preview
"""

import logging

from flask import Blueprint, jsonify, request

from webui.backend.lib.schedule_preview import (
    DEFAULT_PREVIEW_DAYS,
    generate_preview,
    validate_coordinates,
    validate_preview_days,
    validate_timezone,
)
from webui.backend.services.scheduler_service import SchedulerService

# Rate limiter import with fallback for testing
try:
    from webui.backend.app import limiter
except ImportError:
    # Stub for testing without full app context
    class _LimiterStub:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = _LimiterStub()

# Logger
logger = logging.getLogger(__name__)

# Blueprint
scheduler_ui_bp = Blueprint("scheduler_ui", __name__)

# Service instance (lazy initialization)
_scheduler_service = None


def get_scheduler_service() -> SchedulerService:
    """Get or create SchedulerService singleton."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


# ============================================================================
# Preview Endpoints
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/preview", methods=["GET"])
@limiter.limit("30 per minute")
def get_schedule_preview(schedule_id: str):
    """
    Generate execution preview for a schedule.

    GET /api/scheduler/ui/schedules/{id}/preview

    Query Parameters:
        days: Number of days to preview (default: 7, min: 1, max: 90)
        lat: Override latitude (-90 to 90)
        lon: Override longitude (-180 to 180)
        tz: Timezone name (default: UTC)

    Returns:
        200 OK: PreviewResult as JSON
        400 Bad Request: Invalid parameters
        404 Not Found: Schedule not found

    Response Schema:
    {
        "schedule_id": "string",
        "schedule_name": "string",
        "preview_start": "ISO 8601 datetime",
        "preview_end": "ISO 8601 datetime",
        "executions": [
            {
                "start_time": "ISO 8601 datetime",
                "end_time": "ISO 8601 datetime",
                "pattern_id": "string",
                "pattern_name": "string",
                "trigger_info": "string",
                "actions": [
                    {
                        "time": "ISO 8601 datetime",
                        "action_name": "string",
                        "action_type": "string",
                        "offset_minutes": number,
                        "description": "string"
                    }
                ]
            }
        ],
        "conflicts": [...],
        "moon_phases": {
            "YYYY-MM-DD": {
                "date": "YYYY-MM-DD",
                "phase": "string",
                "phase_name": "string",
                "illumination": number
            }
        },
        "total_actions": number,
        "total_executions": number,
        "generated_at": "ISO 8601 datetime"
    }
    """
    try:
        # Parse query parameters
        days_str = request.args.get("days", str(DEFAULT_PREVIEW_DAYS))
        lat_str = request.args.get("lat")
        lon_str = request.args.get("lon")
        timezone_name = request.args.get("tz", "UTC")

        # Validate and parse days
        try:
            days = int(days_str)
        except ValueError:
            return jsonify({
                "error": "Invalid days parameter",
                "message": f"Expected integer, got '{days_str}'",
            }), 400

        valid, error = validate_preview_days(days)
        if not valid:
            return jsonify({
                "error": "Invalid days parameter",
                "message": error,
            }), 400

        # Parse latitude
        latitude = None
        if lat_str is not None:
            try:
                latitude = float(lat_str)
            except ValueError:
                return jsonify({
                    "error": "Invalid lat parameter",
                    "message": f"Expected number, got '{lat_str}'",
                }), 400

        # Parse longitude
        longitude = None
        if lon_str is not None:
            try:
                longitude = float(lon_str)
            except ValueError:
                return jsonify({
                    "error": "Invalid lon parameter",
                    "message": f"Expected number, got '{lon_str}'",
                }), 400

        # Validate coordinates
        valid, error = validate_coordinates(latitude, longitude)
        if not valid:
            return jsonify({
                "error": "Invalid coordinates",
                "message": error,
            }), 400

        # Validate timezone
        valid, error = validate_timezone(timezone_name)
        if not valid:
            return jsonify({
                "error": "Invalid timezone",
                "message": error,
            }), 400

        # Get schedule from service
        service = get_scheduler_service()
        schedule = service.get_schedule(schedule_id)

        if schedule is None:
            return jsonify({
                "error": "Schedule not found",
                "message": f"No schedule with ID '{schedule_id}'",
            }), 404

        # Generate preview
        result = generate_preview(
            schedule=schedule,
            days=days,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )

        return jsonify(result.to_dict()), 200

    except ValueError as e:
        logger.warning(f"Preview generation error: {e}")
        return jsonify({
            "error": "Preview generation failed",
            "message": str(e),
        }), 400

    except Exception as e:
        logger.error(f"Unexpected error in preview generation: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to generate preview",
        }), 500


# ============================================================================
# Future Endpoints (Placeholders)
# ============================================================================


@scheduler_ui_bp.route("/schedules", methods=["GET"])
def list_schedules():
    """
    List all schedules (summary).

    GET /api/scheduler/ui/schedules

    Query Parameters:
        include_builtin: Include built-in schedules (default: false)
        active_only: Filter to active schedule only (default: false)

    Returns:
        200 OK: List of schedule summaries
    """
    try:
        include_builtin = request.args.get("include_builtin", "false").lower() == "true"
        active_only = request.args.get("active_only", "false").lower() == "true"

        service = get_scheduler_service()
        schedules = service.list_schedules(include_builtin=include_builtin)

        # Filter to active only if requested
        if active_only:
            schedules = [s for s in schedules if s.is_active]

        # Return summaries (not full schedule objects)
        summaries = [
            {
                "schedule_id": s.schedule_id,
                "name": s.name,
                "description": s.description,
                "trigger_type": s.trigger_type,
                "enabled": s.enabled,
                "is_active": s.is_active,
                "created_at": s.created_at,
                "modified_at": s.modified_at,
            }
            for s in schedules
        ]

        return jsonify({
            "schedules": summaries,
            "total": len(summaries),
        }), 200

    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to list schedules",
        }), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["GET"])
def get_schedule(schedule_id: str):
    """
    Get full schedule details.

    GET /api/scheduler/ui/schedules/{id}

    Returns:
        200 OK: Full schedule object
        404 Not Found: Schedule not found
    """
    try:
        service = get_scheduler_service()
        schedule = service.get_schedule(schedule_id)

        if schedule is None:
            return jsonify({
                "error": "Schedule not found",
                "message": f"No schedule with ID '{schedule_id}'",
            }), 404

        return jsonify(schedule.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to get schedule",
        }), 500
