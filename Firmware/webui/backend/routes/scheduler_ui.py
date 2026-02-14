"""
High-level Scheduler UI API routes.

Provides REST endpoints for the visual scheduler UI, including:
- Schedule CRUD operations (Issue #218)
- Schedule activation/deactivation
- Schedule preview generation (Issue #214)
- Conflict validation
- Cron expression validation (Issue #233)

Issue #214 - Scheduler Phase 3: Schedule Preview
Issue #218 - Schedule Pattern API
Issue #233 - Cron Validation
Issue #310 - API terminology update (Schema 3.0)
"""

import logging
import re
import subprocess
from datetime import UTC, datetime
from functools import wraps
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from mothbox_paths import CONTROLS_FILE, get_control_values
from webui.backend.lib.cron_bridge import (
    CronEntry,
    calculate_next_waketime,
    cron_to_human_readable,
)
from webui.backend.lib.schedule_preview import (
    DEFAULT_PREVIEW_DAYS,
    generate_preview,
    parse_and_validate_coordinate,
    parse_and_validate_days,
    validate_coordinates,
    validate_timezone,
)
from webui.backend.lib.schedule_schema import (
    MAX_PATTERN_NAME_LENGTH,
    MoonPhaseTrigger,
    Routine,
    Schedule,
    ScheduleActivationError,
    ScheduleConflictError,
    ScheduleValidationError,
    SolarTrigger,
)
from webui.backend.lib.schedule_storage import is_builtin_schedule
from webui.backend.lib.timezone_coordinates import get_fallback_coordinates
from webui.backend.services.scheduler_service import SchedulerService

# Standardized error codes for frontend handling (Issue #385 review)
# These codes are used by the frontend to display user-friendly error messages
ERROR_CODES = {
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "NOT_FOUND": "NOT_FOUND",
    "CONFLICT_ERROR": "CONFLICT_ERROR",
    "ACTIVATION_ERROR": "ACTIVATION_ERROR",
    "SERVER_ERROR": "SERVER_ERROR",
}

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


def _validate_location_params(
    latitude: float | None,
    longitude: float | None,
    timezone_name: str | None,
) -> tuple[dict | None, int | None]:
    """Validate location parameters for schedule operations.

    Consolidates coordinate and timezone validation logic (Issue #385 review fix).

    Args:
        latitude: Latitude value to validate
        longitude: Longitude value to validate
        timezone_name: Optional timezone name to validate

    Returns:
        Tuple of (error_dict, status_code) if validation fails, or (None, None) if valid.
    """
    valid, coord_error = validate_coordinates(latitude, longitude)
    if not valid:
        # Return sanitized error - coord_error doesn't include user input
        safe_error = _sanitize_error_message(coord_error)
        return {"error": f"Invalid coordinates: {safe_error}"}, 400

    if timezone_name:
        valid, tz_error = validate_timezone(timezone_name)
        if not valid:
            # Don't reflect user input in error - use generic message
            # Original error logged for debugging, sanitized version returned
            return {
                "error": "Invalid timezone: Use IANA timezone names "
                "(e.g., 'America/New_York', 'Europe/London', 'UTC')"
            }, 400

    return None, None


def _sanitize_error_message(message: str | None, max_length: int = 200) -> str:
    """
    Sanitize error message for safe display to users.

    Prevents XSS by stripping HTML tags, redacts internal file paths,
    and truncates long messages. This is defense-in-depth - Flask's
    jsonify escapes by default, but we strip tags and redact paths
    to prevent information disclosure and frontend rendering issues.

    Args:
        message: Raw error message (may contain user input)
        max_length: Maximum length before truncation

    Returns:
        Sanitized error message safe for display

    Issue #385 security fix: Reflected XSS prevention + path redaction
    """
    if not message:
        return "An error occurred"

    msg = str(message)

    # Strip HTML tags iteratively (handles nested/malformed tags)
    prev_len = -1
    while len(msg) != prev_len:
        prev_len = len(msg)
        msg = re.sub(r"<[^>]*>", "", msg)
        msg = re.sub(r"<[^>]*$", "", msg)  # Incomplete tags

    # Redact internal file paths to prevent information disclosure
    # Matches Unix-style absolute paths (e.g., /etc/secrets/file.txt)
    msg = re.sub(r"/(?:etc|var|home|opt|usr|tmp|root)/[^\s'\"]*", "[path]", msg)

    if len(msg) > max_length:
        msg = msg[: max_length - 3] + "..."

    return msg.strip() or "An error occurred"


def _requires_coordinates(routines: list[Routine]) -> bool:
    """Check if any routine has a solar or moon phase trigger requiring coordinates.

    Args:
        routines: List of Routine objects to check

    Returns:
        True if any routine requires coordinates for solar/moon calculations
    """
    for routine in routines:
        if isinstance(routine.trigger, (SolarTrigger, MoonPhaseTrigger)):
            return True
    return False


def get_system_timezone() -> str:
    """Get system timezone name from timedatectl or /etc/timezone.

    Returns:
        Timezone name (e.g., "Pacific/Auckland") or "UTC" as fallback.
    """
    # Try timedatectl first (most reliable on systemd systems)
    try:
        result = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--value"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass

    # Fallback: read /etc/timezone
    try:
        with open("/etc/timezone") as f:
            tz = f.read().strip()
            if tz:
                return tz
    except OSError:
        pass

    return "UTC"


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


def require_json(f):
    """
    Decorator that validates request has valid JSON body.

    Passes the parsed JSON data to the wrapped function as `json_data` kwarg.
    Returns 400 Bad Request if JSON is missing, invalid, or not an object.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        return f(*args, json_data=data, **kwargs)

    return decorated


def _schedule_to_summary(schedule: Schedule) -> dict:
    """
    Convert Schedule to summary dict for list endpoints.

    Returns schedule summary with routines for list views, enabling
    frontend to display trigger icons, action dots, and auto-generated
    descriptions. Used by list_schedules() and list_builtin_schedules().

    Note: trigger_type removed in Schema 3.0 (moved to routine level).
    """
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "description": schedule.description,
        "enabled": schedule.enabled,
        "is_active": schedule.is_active,
        "routines": [r.to_dict() for r in schedule.routines],
        "routine_count": len(schedule.routines),
        "created_at": schedule.created_at,
        "modified_at": schedule.modified_at,
    }


# ============================================================================
# Preview Endpoints
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/preview", methods=["GET"])
@limiter.limit("30 per minute")
def get_schedule_preview(schedule_id: str) -> tuple[Response, int]:
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

        # Parse and validate days
        days, error = parse_and_validate_days(days_str)
        if error:
            logger.debug(f"Invalid days parameter '{days_str}': {error}")
            return jsonify({"error": "Invalid days parameter"}), 400

        # Parse coordinates
        latitude, error = parse_and_validate_coordinate(lat_str, "lat")
        if error:
            logger.debug(f"Invalid lat parameter '{lat_str}': {error}")
            return jsonify({"error": "Invalid lat parameter"}), 400

        longitude, error = parse_and_validate_coordinate(lon_str, "lon")
        if error:
            logger.debug(f"Invalid lon parameter '{lon_str}': {error}")
            return jsonify({"error": "Invalid lon parameter"}), 400

        # Validate coordinate ranges
        valid, _error = validate_coordinates(latitude, longitude)
        if not valid:
            logger.debug("Invalid coordinate range provided")
            return jsonify({"error": "Invalid coordinates"}), 400

        # Validate timezone
        valid, error = validate_timezone(timezone_name)
        if not valid:
            logger.debug(f"Invalid timezone: {error}")
            return jsonify({"error": "Invalid timezone"}), 400

        # Get schedule from service
        service = get_scheduler_service()
        schedule = service.get_schedule(schedule_id)

        if schedule is None:
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

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
        return jsonify(
            {
                "error": "Preview generation failed",
            }
        ), 400

    except Exception as e:
        logger.error(f"Unexpected error in preview generation: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to generate preview",
            }
        ), 500


# ============================================================================
# Future Endpoints (Placeholders)
# ============================================================================


@scheduler_ui_bp.route("/schedules", methods=["GET"])
def list_schedules() -> tuple[Response, int]:
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
        summaries = [_schedule_to_summary(s) for s in schedules]

        return jsonify(
            {
                "schedules": summaries,
                "total": len(summaries),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error listing schedules: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to list schedules",
            }
        ), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["GET"])
def get_schedule(schedule_id: str) -> tuple[Response, int]:
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
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

        return jsonify(schedule.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


@scheduler_ui_bp.route("/schedules/active", methods=["GET"])
def get_active_schedule() -> tuple[Response, int]:
    """
    Get the currently active schedule.

    GET /api/scheduler/ui/schedules/active

    Returns:
        200 OK: {
            "active_schedule": {...} or null,
            "coordinates_source": "explicit" | "gps" | "timezone" | null,
            "latitude": number | null,
            "longitude": number | null,
            "timezone_name": string | null  // Only set when source="timezone"
        }
    """
    try:
        service = get_scheduler_service()
        schedule = service.get_active_schedule()
        coordinates_source = service.get_active_coordinates_source()
        coordinates = service.get_active_coordinates()
        timezone_name = service.get_active_timezone_name()

        if schedule is None:
            return jsonify(
                {
                    "active_schedule": None,
                    "coordinates_source": None,
                    "latitude": None,
                    "longitude": None,
                    "timezone_name": None,
                }
            ), 200

        return jsonify(
            {
                "active_schedule": schedule.to_dict(),
                "coordinates_source": coordinates_source,
                "latitude": coordinates[0] if coordinates else None,
                "longitude": coordinates[1] if coordinates else None,
                "timezone_name": timezone_name,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting active schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to get active schedule",
            }
        ), 500


@scheduler_ui_bp.route("/active/next-actions", methods=["GET"])
def get_next_actions() -> tuple[Response, int]:
    """
    Get upcoming actions for the active schedule.

    Reads pre-expanded cron entries from persistent storage, filtering
    to future actions only. This avoids recalculating solar times via
    the preview API.

    GET /api/scheduler/ui/active/next-actions

    Query Parameters:
        limit: Maximum number of actions to return (default: 5, max: 100)

    Returns:
        200 OK: {
            "actions": [
                {
                    "time": "ISO 8601 datetime",
                    "action_name": "Attract On",
                    "action_type": "attract_on",
                    "routine_id": "routine-123"
                },
                ...
            ],
            "schedule_id": "string" | null,
            "coordinates_source": "gps" | "timezone" | "explicit" | null,
            "total_stored": number
        }
        400 Bad Request: Invalid limit parameter

    Issue #331: Store cron entries in active_state.json
    """
    try:
        # Parse and validate limit parameter
        limit_str = request.args.get("limit", "5")
        try:
            limit = int(limit_str)
            if limit < 1:
                limit = 1
            elif limit > 100:
                limit = 100
        except ValueError:
            return jsonify({"error": "Invalid limit parameter"}), 400

        service = get_scheduler_service()
        schedule_id = service.get_active_schedule_id()
        coordinates_source = service.get_active_coordinates_source()

        # Get next actions from persisted entries
        next_actions = service.get_next_actions(limit=limit)
        total_stored = len(service.get_active_entries())

        # Format actions for response
        actions = [
            {
                "time": entry.execution_time.isoformat() if entry.execution_time else None,
                "action_name": entry.action_name,
                "action_type": entry.action_type,
                "routine_id": entry.routine_id,
            }
            for entry in next_actions
        ]

        return jsonify(
            {
                "actions": actions,
                "schedule_id": schedule_id,
                "coordinates_source": coordinates_source,
                "total_stored": total_stored,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting next actions: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to get next actions",
            }
        ), 500


@scheduler_ui_bp.route("/schedules/builtin", methods=["GET"])
def list_builtin_schedules() -> tuple[Response, int]:
    """
    List all built-in schedules.

    GET /api/scheduler/ui/schedules/builtin

    Returns:
        200 OK: {
            "schedules": [...],
            "total": number
        }

    Note:
        Built-in schedules cannot be modified or deleted.
    """
    try:
        service = get_scheduler_service()
        # Get all schedules including built-in
        schedules = service.list_schedules(include_builtin=True)

        # Filter to built-in only
        builtin = [s for s in schedules if is_builtin_schedule(s.schedule_id)]

        # Return summaries
        summaries = [_schedule_to_summary(s) for s in builtin]

        return jsonify(
            {
                "schedules": summaries,
                "total": len(summaries),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error listing built-in schedules: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to list built-in schedules",
            }
        ), 500


# ============================================================================
# Schedule CRUD Endpoints (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules", methods=["POST"])
@limiter.limit("30 per minute")
@require_json
def create_schedule(json_data: dict) -> tuple[Response, int]:
    """
    Create a new schedule.

    POST /api/scheduler/ui/schedules

    Request Body:
        Complete schedule JSON with embedded event patterns.
        See schedule_schema.py for full structure.

    Returns:
        201 Created: {
            "message": "Schedule created",
            "schedule_id": "...",
            "schedule": {...}
        }
        400 Bad Request: Validation error
        500 Internal Server Error: Creation failed
    """
    try:
        # Convert to Schedule object
        try:
            schedule = Schedule.from_dict(json_data)
        except KeyError as e:
            logger.warning(f"Missing required field in schedule: {e}")
            return jsonify(
                {
                    "error": "Missing required field in schedule",
                }
            ), 400
        except Exception as e:
            logger.error(f"Invalid schedule format: {e}", exc_info=True)
            return jsonify(
                {
                    "error": "Invalid schedule format",
                }
            ), 400

        # Create via service (validates internally)
        service = get_scheduler_service()
        try:
            success = service.create_schedule(schedule)
        except ScheduleValidationError as e:
            logger.debug(f"Schedule validation failed: {e}")
            return jsonify(
                {
                    "error": "Schedule validation failed",
                    "code": ERROR_CODES["VALIDATION_ERROR"],
                }
            ), 400

        if not success:
            return jsonify(
                {
                    "error": "Failed to create schedule",
                }
            ), 500

        return jsonify(
            {
                "message": "Schedule created",
                "schedule_id": schedule.schedule_id,
                "schedule": schedule.to_dict(),
            }
        ), 201

    except Exception as e:
        logger.error(f"Error creating schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to create schedule",
            }
        ), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_json
def update_schedule(schedule_id: str, json_data: dict) -> tuple[Response, int]:
    """
    Update a schedule.

    PUT /api/scheduler/ui/schedules/{id}

    Request Body:
        Partial or complete schedule update data.

    Special handling for 'enabled' field:
        The 'enabled' state is stored in active_state.json (single source of truth),
        not in schedule JSON files. This ensures firmware updates don't cause
        inconsistent state. When 'enabled' is in the request, we call
        set_enabled_schedule() instead of passing it to storage.

    Returns:
        200 OK: {
            "message": "Schedule updated",
            "schedule": {...}
        }
        400 Bad Request: Validation error
        403 Forbidden: Cannot modify built-in schedule
        404 Not Found: Schedule not found
        500 Internal Server Error: Update failed
    """
    try:
        service = get_scheduler_service()

        # Check if schedule exists
        existing = service.get_schedule(schedule_id)
        if existing is None:
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

        # Handle 'enabled' field separately (Issue #331 fix)
        # enabled/is_active are stored in active_state.json, not schedule JSON files
        if "enabled" in json_data:
            enabled_value = json_data.pop("enabled")
            try:
                if enabled_value:
                    service.set_enabled_schedule(schedule_id)
                elif service.get_enabled_schedule_id() == schedule_id:
                    service.set_enabled_schedule(None)
            except ValueError:
                logger.exception("Failed to set enabled state")
                return jsonify({"error": "Invalid schedule state"}), 400

        # If only 'enabled' was being updated, we're done
        if not json_data:
            # Re-fetch to get updated enabled state
            updated = service.get_schedule(schedule_id)
            return jsonify(
                {
                    "message": "Schedule updated",
                    "schedule": updated.to_dict(),
                }
            ), 200

        # Update remaining fields via service (handles built-in check)
        try:
            updated = service.update_schedule(schedule_id, json_data)
        except ValueError as e:
            # Built-in schedule protection - intentionally returns generic message
            # (not str(e)) to avoid exposing internal details
            logger.warning(f"Update blocked for built-in schedule: {e}")
            return jsonify(
                {
                    "error": "Cannot modify built-in schedule",
                }
            ), 403
        except ScheduleValidationError as e:
            logger.warning(f"Schedule validation failed: {e}")
            return jsonify(
                {
                    "error": "Validation failed",
                    "code": ERROR_CODES["VALIDATION_ERROR"],
                }
            ), 400

        if updated is None:
            return jsonify(
                {
                    "error": "Failed to update schedule",
                }
            ), 500

        return jsonify(
            {
                "message": "Schedule updated",
                "schedule": updated.to_dict(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error updating schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
def delete_schedule(schedule_id: str) -> tuple[Response, int]:
    """
    Delete a schedule.

    DELETE /api/scheduler/ui/schedules/{id}

    Returns:
        200 OK: {
            "message": "Schedule deleted",
            "schedule_id": "..."
        }
        403 Forbidden: Cannot delete built-in schedule
        404 Not Found: Schedule not found
        500 Internal Server Error: Deletion failed
    """
    try:
        service = get_scheduler_service()

        # Check if schedule exists
        existing = service.get_schedule(schedule_id)
        if existing is None:
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

        # Delete via service (handles built-in check)
        try:
            success = service.delete_schedule(schedule_id)
        except ValueError as e:
            # Built-in schedule protection
            logger.warning(f"Delete blocked for built-in schedule: {e}")
            return jsonify(
                {
                    "error": "Cannot delete built-in schedule",
                }
            ), 403

        if not success:
            return jsonify(
                {
                    "error": "Failed to delete schedule",
                }
            ), 500

        return jsonify(
            {
                "message": "Schedule deleted",
                "schedule_id": schedule_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error deleting schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>/clone", methods=["POST"])
@limiter.limit("30 per minute")
def clone_schedule(schedule_id: str) -> tuple[Response, int]:
    """
    Clone a schedule to a new user-owned schedule.

    POST /api/scheduler/ui/schedules/{id}/clone

    Works for both built-in and user schedules. Creates a deep copy with:
    - New schedule_id (UUID)
    - New routine_id for each routine (UUID)
    - Name with " (Copy)" suffix or custom name from request body
    - is_active = False
    - Fresh timestamps

    Request Body (optional):
        {
            "name": "Custom name for the copy"
        }

    Returns:
        201 Created: {
            "message": "Schedule cloned",
            "schedule_id": "new-uuid",
            "schedule": {...}
        }
        400 Bad Request: Invalid name
        404 Not Found: Schedule not found
        500 Internal Server Error: Clone failed

    Issue #320 - Built-in Schedule Immutability Enforcement
    """
    try:
        service = get_scheduler_service()

        # Get original schedule
        original = service.get_schedule(schedule_id)
        if original is None:
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

        # Parse optional request body for custom name
        data = request.get_json(silent=True) or {}
        custom_name = data.get("name")

        # Validate custom name if provided
        if custom_name is not None:
            if not isinstance(custom_name, str):
                return jsonify(
                    {
                        "error": "Name must be a string",
                    }
                ), 400
            if not custom_name.strip():
                return jsonify(
                    {
                        "error": "Name cannot be empty",
                    }
                ), 400
            new_name = custom_name.strip()
            if len(new_name) > MAX_PATTERN_NAME_LENGTH:
                return jsonify(
                    {
                        "error": f"Name exceeds {MAX_PATTERN_NAME_LENGTH} characters",
                    }
                ), 400
        else:
            new_name = f"{original.name} (Copy)"
            # Truncate if default name exceeds max length
            if len(new_name) > MAX_PATTERN_NAME_LENGTH:
                suffix = " (Copy)"
                max_original_len = MAX_PATTERN_NAME_LENGTH - len(suffix)
                new_name = f"{original.name[:max_original_len]}{suffix}"

        # Deep copy routines with new IDs
        cloned_routines = []
        for routine in original.routines:
            routine_dict = routine.to_dict()
            # Remove computed fields that get regenerated
            routine_dict.pop("display_name", None)
            routine_dict.pop("duration_minutes", None)
            # Set empty routine_id to trigger UUID generation in __post_init__
            routine_dict["routine_id"] = ""
            cloned_routines.append(Routine.from_dict(routine_dict))

        # Create new schedule with fresh IDs and timestamps
        now = datetime.now(UTC).isoformat()
        new_schedule = Schedule(
            schedule_id=str(uuid4()),
            name=new_name,
            description=original.description,
            routines=cloned_routines,
            deployment_id=None,  # Clear deployment link
            create_deployment=original.create_deployment,
            enabled=original.enabled,
            is_active=False,  # Clone is never active
            created_at=now,
            modified_at=now,
            modified_by=None,  # Reset - clone has no modifier yet
        )

        # Create via service
        try:
            success = service.create_schedule(new_schedule)
        except ScheduleValidationError as e:
            logger.warning(f"Cloned schedule validation failed: {e}")
            return jsonify(
                {
                    "error": "Validation failed",
                    "code": ERROR_CODES["VALIDATION_ERROR"],
                }
            ), 400

        if not success:
            return jsonify(
                {
                    "error": "Failed to create cloned schedule",
                }
            ), 500

        return jsonify(
            {
                "message": "Schedule cloned",
                "schedule_id": new_schedule.schedule_id,
                "schedule": new_schedule.to_dict(),
            }
        ), 201

    except Exception as e:
        logger.error(f"Error cloning schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


# ============================================================================
# Schedule Activation Endpoints (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/activate", methods=["POST"])
@limiter.limit("10 per minute")
def activate_schedule(schedule_id: str) -> tuple[Response, int]:
    """
    Activate a schedule.

    POST /api/scheduler/ui/schedules/{id}/activate

    Activates the specified schedule. Any currently active schedule will be
    deactivated first. Optionally checks for scheduling conflicts before
    activation.

    Request Body (optional):
        {
            "check_conflicts": true,  // default: true
            "latitude": 0.0,          // for solar calculations
            "longitude": 0.0,         // for solar calculations
            "timezone": "UTC"         // timezone for time resolution
        }

    Returns:
        200 OK: {
            "message": "Schedule activated",
            "schedule_id": "..."
        }
        400 Bad Request: Schedule is disabled or activation failed
        404 Not Found: Schedule not found
        409 Conflict: Schedule has blocking conflicts
        500 Internal Server Error: Unexpected error
    """
    try:
        # Parse optional request body (silent=True allows empty body)
        data = request.get_json(silent=True) or {}
        check_conflicts = data.get("check_conflicts", True)

        # Check if coordinates were explicitly provided in request
        lat_provided = "latitude" in data
        lon_provided = "longitude" in data

        # Require both coordinates or neither
        if lat_provided != lon_provided:
            return jsonify(
                {
                    "error": "Both latitude and longitude must be provided together",
                }
            ), 400

        # Determine coordinates with fallback chain (Issue #331)
        # Priority: 1) explicit request, 2) device GPS, 3) timezone approximation
        coordinates_source = "explicit"  # "explicit", "gps", or "timezone"

        if lat_provided:
            # Coordinates explicitly provided in request
            try:
                latitude = float(data["latitude"])
                longitude = float(data["longitude"])
                coordinates_source = "explicit"
            except (ValueError, TypeError):
                return jsonify(
                    {
                        "error": "Coordinates must be numeric",
                    }
                ), 400
        else:
            # Try device GPS from controls.txt
            control_values = get_control_values(CONTROLS_FILE)
            device_lat = control_values.get("lat", "n/a")
            device_lon = control_values.get("lon", "n/a")

            # Initialize fallback timezone (set when using timezone fallback)
            fallback_timezone = None

            if device_lat != "n/a" and device_lon != "n/a":
                try:
                    latitude = float(device_lat)
                    longitude = float(device_lon)
                    coordinates_source = "gps"
                    logger.debug("Using device GPS coordinates (redacted for privacy)")
                except (ValueError, TypeError):
                    # GPS values invalid, fall back to timezone
                    latitude, longitude, fallback_timezone = get_fallback_coordinates()
                    coordinates_source = "timezone"
                    logger.debug(
                        f"GPS values invalid, using timezone fallback: {fallback_timezone}"
                    )
            else:
                # No GPS, fall back to timezone
                latitude, longitude, fallback_timezone = get_fallback_coordinates()
                coordinates_source = "timezone"
                logger.debug(f"No GPS available, using timezone fallback: {fallback_timezone}")

        # Determine timezone:
        # 1. If using timezone fallback, use that timezone
        # 2. If explicitly provided in request, use that
        # 3. Otherwise, use system timezone (especially important for GPS coords)
        if coordinates_source == "timezone" and fallback_timezone:
            timezone_name = fallback_timezone
        elif "timezone" in data and data["timezone"]:
            timezone_name = data["timezone"]
        else:
            # Use system timezone - critical for GPS-based activation
            # Without this, solar times would be calculated in UTC!
            timezone_name = get_system_timezone()
            logger.info(f"Using system timezone: {timezone_name}")

        # Validate coordinate ranges and timezone (Issue #385 review fix)
        # Coordinates may come from explicit request, GPS, or timezone fallback -
        # all sources should be validated to catch invalid controls.txt values
        error, status = _validate_location_params(latitude, longitude, timezone_name)
        if error:
            return jsonify(error), status

        service = get_scheduler_service()

        # Get socketio for progress events (may be None in tests)
        socketio = current_app.extensions.get("socketio")

        def emit_progress(phase: str, progress: int) -> None:
            """Emit activation progress event via WebSocket."""
            if socketio:
                socketio.emit(
                    "schedule:activation_progress",
                    {
                        "schedule_id": schedule_id,
                        "phase": phase,
                        "progress": progress,
                    },
                )

        # Enable and activate schedule via service
        # set_enabled_schedule() must be called before activate_schedule()
        # to update the internal enabled state (Issue #331)
        try:
            # Deactivate and disable any currently active/enabled schedule first
            current_enabled = service.get_enabled_schedule_id()
            if current_enabled and current_enabled != schedule_id:
                service.deactivate_schedule()
                service.set_enabled_schedule(None)

            # Enable the new schedule
            service.set_enabled_schedule(schedule_id)
            service.activate_schedule(
                schedule_id,
                check_conflicts=check_conflicts,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                progress_callback=emit_progress,
                coordinates_source=coordinates_source,
            )
        except ScheduleConflictError as e:
            # Log conflict details, return generic message
            logger.info(f"Schedule conflict detected: {e}")
            return jsonify(
                {
                    "error": "Schedule conflict detected",
                    "code": ERROR_CODES["CONFLICT_ERROR"],
                    "conflict": True,
                }
            ), 409
        except ScheduleActivationError as e:
            # Log detailed error, return generic message
            logger.warning(f"Schedule activation failed: {e}")
            return jsonify(
                {
                    "error": "Schedule activation failed",
                    "code": ERROR_CODES["ACTIVATION_ERROR"],
                }
            ), 400

        # Include coordinates_source in response for UI notification (Issue #331)
        # Check for entry count warning (approaching system limit)
        entry_warning = service.get_entry_count_warning()

        response = {
            "message": "Schedule activated",
            "schedule_id": schedule_id,
            "coordinates_source": coordinates_source,
            "latitude": latitude,
            "longitude": longitude,
        }

        if entry_warning:
            response["warning"] = entry_warning

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error activating schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


@scheduler_ui_bp.route("/schedules/deactivate", methods=["POST"])
@limiter.limit("10 per minute")
def deactivate_current_schedule() -> tuple[Response, int]:
    """
    Deactivate the currently active schedule and clear system crontab.

    Always clears crontab entries, even if no schedule is tracked as active.
    This handles orphaned cron entries from crashes/restarts (Issue #331).

    POST /api/scheduler/ui/schedules/deactivate

    Returns:
        200 OK: {
            "message": "Schedule deactivated" or "Cleared orphaned cron entries",
            "was_active": true/false,
            "schedule_id": "..." or null
        }
        500 Internal Server Error: Failed to clear crontab
    """
    try:
        service = get_scheduler_service()

        # Check if there's an active schedule (before deactivation)
        active = service.get_active_schedule()

        # ALWAYS call deactivate - clears orphaned cron entries too (Issue #331)
        success = service.deactivate_schedule()

        if not success:
            return jsonify(
                {
                    "error": "Failed to clear crontab",
                    "message": "Cron entries may still be active",
                }
            ), 500

        if active is None:
            return jsonify(
                {
                    "message": "Cleared orphaned cron entries",
                    "was_active": False,
                    "schedule_id": None,
                }
            ), 200

        return jsonify(
            {
                "message": "Schedule deactivated",
                "was_active": True,
                "schedule_id": active.schedule_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error deactivating schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
                "message": "Failed to deactivate schedule",
            }
        ), 500


# ============================================================================
# Schedule Validation Endpoint (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/validate", methods=["POST"])
@limiter.limit("30 per minute")
def validate_schedule_endpoint(schedule_id: str) -> tuple[Response, int]:
    """
    Validate a schedule for conflicts without activating.

    POST /api/scheduler/ui/schedules/{id}/validate

    Request Body (optional):
        {
            "days": 7,           // preview days (default: 7)
            "latitude": 0.0,     // for solar calculations
            "longitude": 0.0,    // for solar calculations
            "timezone": "UTC"    // timezone for time resolution
        }

    Returns:
        200 OK: {
            "schedule_id": "...",
            "valid": true/false,
            "has_warnings": true/false,
            "conflicts": [...],
            "total_conflicts": number,
            "blocking_conflicts": number
        }
        404 Not Found: Schedule not found
        500 Internal Server Error: Validation failed
    """
    try:
        # Parse optional request body (silent=True allows empty body)
        data = request.get_json(silent=True) or {}
        preview_days = data.get("days", 7)

        # Check if coordinates were explicitly provided in request
        lat_provided = "latitude" in data
        lon_provided = "longitude" in data

        # Require both coordinates or neither
        if lat_provided != lon_provided:
            return jsonify(
                {
                    "error": "Both latitude and longitude must be provided together",
                }
            ), 400

        # Type validation for coordinates
        try:
            latitude = float(data["latitude"]) if lat_provided else 0.0
            longitude = float(data["longitude"]) if lon_provided else 0.0
        except (ValueError, TypeError):
            return jsonify(
                {
                    "error": "Coordinates must be numeric",
                }
            ), 400

        timezone_name = data.get("timezone", "UTC")

        # Validate coordinate ranges if explicitly provided (including 0.0, 0.0)
        # Use helper with timezone_name=None to skip timezone validation (Issue #385)
        if lat_provided and lon_provided:
            error, status = _validate_location_params(latitude, longitude, None)
            if error:
                return jsonify(error), status

        service = get_scheduler_service()

        # Check if schedule exists
        schedule = service.get_schedule(schedule_id)
        if schedule is None:
            return jsonify(
                {
                    "error": "Schedule not found",
                    "code": ERROR_CODES["NOT_FOUND"],
                }
            ), 404

        # Check if coordinates required but not provided (solar/moon triggers)
        if not lat_provided and _requires_coordinates(schedule.routines):
            return jsonify(
                {
                    "error": "Coordinates required for schedules with solar or moon triggers",
                }
            ), 400

        # Get cached conflict report
        report = service.get_cached_conflict_report(
            schedule,
            preview_days=preview_days,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )

        # Count total and blocking conflicts
        total_conflicts = len(report.conflicts)
        try:
            from webui.backend.lib.schedule_conflict import SEVERITY_ERROR

            blocking_count = len([c for c in report.conflicts if c.severity == SEVERITY_ERROR])
        except ImportError:
            blocking_count = 0

        return jsonify(
            {
                "schedule_id": schedule_id,
                "valid": not report.has_blocking_conflicts,
                "has_warnings": total_conflicts > 0 and not report.has_blocking_conflicts,
                "conflicts": [c.to_dict() for c in report.conflicts],
                "total_conflicts": total_conflicts,
                "blocking_conflicts": blocking_count,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error validating schedule: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


@scheduler_ui_bp.route("/schedules/validate-draft", methods=["POST"])
@limiter.limit("30 per minute")
@require_json
def validate_draft_routines(json_data: dict) -> tuple[Response, int]:
    """
    Validate draft routines for conflicts without requiring a saved schedule.

    POST /api/scheduler/ui/schedules/validate-draft

    Useful for previewing conflicts in the schedule editor before saving.

    Request Body:
        {
            "routines": [...],       // required: array of routine objects
            "days": 7,               // optional: preview days (default: 7)
            "latitude": 0.0,         // optional: for solar calculations
            "longitude": 0.0,        // optional: for solar calculations
            "timezone": "UTC"        // optional: timezone (default: UTC)
        }

    Returns:
        200 OK: {
            "valid": true/false,
            "has_warnings": true/false,
            "conflicts": [...],
            "total_conflicts": number,
            "blocking_conflicts": number,
            "estimated_entries": number  // total scheduled executions in preview period
        }
        400 Bad Request: Invalid parameters or routines
    """
    try:
        # Validate routines field exists
        if "routines" not in json_data:
            return jsonify({"error": "routines array required"}), 400

        routines_data = json_data["routines"]
        if not isinstance(routines_data, list):
            return jsonify({"error": "routines must be an array"}), 400

        # Empty routines is valid - no conflicts possible
        if not routines_data:
            return jsonify(
                {
                    "valid": True,
                    "has_warnings": False,
                    "conflicts": [],
                    "total_conflicts": 0,
                    "blocking_conflicts": 0,
                    "estimated_entries": 0,
                }
            ), 200

        # Parse routines
        try:
            routines = [Routine.from_dict(r) for r in routines_data]
        except (KeyError, ValueError, TypeError) as e:
            logger.debug(f"Invalid routine format: {e}")
            return jsonify({"error": "Invalid routine format"}), 400

        # Parse optional parameters
        preview_days = json_data.get("days", DEFAULT_PREVIEW_DAYS)
        try:
            preview_days = min(max(int(preview_days), 1), 90)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid days parameter"}), 400

        # Check if coordinates were explicitly provided in request
        lat_provided = "latitude" in json_data
        lon_provided = "longitude" in json_data

        # Require both coordinates or neither
        if lat_provided != lon_provided:
            return jsonify({"error": "Both latitude and longitude must be provided together"}), 400

        # Type validation for coordinates
        try:
            latitude = float(json_data["latitude"]) if lat_provided else 0.0
            longitude = float(json_data["longitude"]) if lon_provided else 0.0
        except (ValueError, TypeError):
            return jsonify({"error": "Coordinates must be numeric"}), 400

        timezone_name = json_data.get("timezone", "UTC")

        # Validate coordinate ranges if explicitly provided
        if lat_provided and lon_provided:
            valid, coord_error = validate_coordinates(latitude, longitude)
            if not valid:
                # Sanitize error - coord_error doesn't include user input but sanitize anyway
                safe_error = _sanitize_error_message(coord_error)
                return jsonify({"error": f"Invalid coordinates: {safe_error}"}), 400

        # Validate timezone
        valid, tz_error = validate_timezone(timezone_name)
        if not valid:
            # Don't reflect user input in error - use generic message (Issue #385 security fix)
            return jsonify(
                {
                    "error": "Invalid timezone: Use IANA timezone names "
                    "(e.g., 'America/New_York', 'Europe/London', 'UTC')"
                }
            ), 400

        # Check if coordinates required but not provided (solar/moon triggers)
        # Use same fallback chain as activation: device GPS → timezone approximation
        if not lat_provided and _requires_coordinates(routines):
            control_values = get_control_values(CONTROLS_FILE)
            device_lat = control_values.get("lat", "n/a")
            device_lon = control_values.get("lon", "n/a")

            if device_lat != "n/a" and device_lon != "n/a":
                try:
                    latitude = float(device_lat)
                    longitude = float(device_lon)
                except (ValueError, TypeError):
                    latitude, longitude, _ = get_fallback_coordinates()
            else:
                latitude, longitude, _ = get_fallback_coordinates()

        # Create temporary schedule for conflict detection
        temp_schedule = Schedule(
            schedule_id="draft-validation",
            name="Draft Schedule",
            routines=routines,
        )

        # Import and run conflict detection
        from webui.backend.lib.schedule_conflict import SEVERITY_ERROR, detect_conflicts

        report = detect_conflicts(
            schedule=temp_schedule,
            preview_days=preview_days,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )

        # Count total and blocking conflicts
        total_conflicts = len(report.conflicts)
        blocking_count = len([c for c in report.conflicts if c.severity == SEVERITY_ERROR])

        return jsonify(
            {
                "valid": not report.has_blocking_conflicts,
                "has_warnings": total_conflicts > 0 and not report.has_blocking_conflicts,
                "conflicts": [c.to_dict() for c in report.conflicts],
                "total_conflicts": total_conflicts,
                "blocking_conflicts": blocking_count,
                "estimated_entries": report.total_executions,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error validating draft routines: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "code": ERROR_CODES["SERVER_ERROR"],
            }
        ), 500


# ============================================================================
# Cron Validation Endpoint (Issue #233 - Phase 1)
# ============================================================================


@scheduler_ui_bp.route("/cron/validate", methods=["POST"])
@limiter.limit("30 per minute")
@require_json
def validate_cron_expression(json_data: dict) -> tuple[Response, int]:
    """
    Validate a cron expression and preview next executions.

    POST /api/scheduler/ui/cron/validate

    Request Body:
    {
        "expression": "*/5 * * * *",  // required, max 100 chars
        "count": 5                    // optional, 1-20 (default: 5)
    }

    Returns:
        200 OK: {
            "valid": true,
            "expression": "*/5 * * * *",
            "next_executions": ["2025-12-26T10:05:00", ...],
            "human_readable": "Every 5 minutes"
        }
        400 Bad Request: {
            "valid": false,
            "error": "Invalid cron expression: ..."
        }
    """
    try:
        # Extract and validate expression field
        expression = json_data.get("expression")

        if expression is None:
            return jsonify(
                {
                    "valid": False,
                    "error": "Missing required field: expression",
                }
            ), 400

        # Type validation
        if not isinstance(expression, str):
            return jsonify(
                {
                    "valid": False,
                    "error": "Expression must be a string",
                }
            ), 400

        # Empty string check
        if not expression or not expression.strip():
            return jsonify(
                {
                    "valid": False,
                    "error": "Expression cannot be empty",
                }
            ), 400

        # Length validation (security check)
        if len(expression) > 100:
            return jsonify(
                {
                    "valid": False,
                    "error": "Expression too long (max 100 characters)",
                }
            ), 400

        # Get count parameter (default 5, range 1-20)
        count = json_data.get("count", 5)

        # Validate count type
        if not isinstance(count, int):
            return jsonify(
                {
                    "valid": False,
                    "error": "Count must be an integer",
                }
            ), 400

        # Validate count range
        if count < 1 or count > 20:
            return jsonify(
                {
                    "valid": False,
                    "error": "Count must be between 1 and 20",
                }
            ), 400

        # Validate cron expression syntax
        if not CronEntry.is_valid_expression(expression):
            return jsonify(
                {
                    "valid": False,
                    "error": "Invalid cron expression syntax",
                }
            ), 400

        # Calculate next execution times
        next_executions = []
        current_time = datetime.now(UTC)

        try:
            for _ in range(count):
                next_time = calculate_next_waketime(expression, current_time)
                next_executions.append(datetime.fromtimestamp(next_time, UTC).isoformat())
                # Advance time by 1 second to get next occurrence
                current_time = datetime.fromtimestamp(next_time + 1, UTC)
        except ValueError as e:
            logger.debug(f"Failed to calculate next execution times: {e}")
            return jsonify(
                {
                    "valid": False,
                    "error": "Invalid cron expression: cannot calculate execution times",
                }
            ), 400

        # Get human-readable description
        human_readable = cron_to_human_readable(expression)

        return jsonify(
            {
                "valid": True,
                "expression": expression,
                "next_executions": next_executions,
                "human_readable": human_readable,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error validating cron expression: {e}", exc_info=True)
        return jsonify(
            {
                "valid": False,
                "error": "Internal server error during validation",
            }
        ), 500
