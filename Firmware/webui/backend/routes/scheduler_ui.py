"""
High-level Scheduler UI API routes.

Provides REST endpoints for the visual scheduler UI, including:
- Schedule CRUD operations (Issue #218)
- Schedule activation/deactivation
- Schedule preview generation (Issue #214)
- Event pattern management (Issue #217)
- Conflict validation

Issue #214 - Scheduler Phase 3: Schedule Preview
Issue #217 - Event Pattern API
Issue #218 - Schedule Pattern API
"""

import json
import logging
import threading
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

from webui.backend.constants import MAX_BUILTIN_SCHEDULE_FILES
from webui.backend.lib.schedule_preview import (
    DEFAULT_PREVIEW_DAYS,
    generate_preview,
    parse_and_validate_coordinate,
    parse_and_validate_days,
    validate_coordinates,
    validate_timezone,
)
from webui.backend.lib.schedule_schema import (
    EventPattern,
    Schedule,
    ScheduleActivationError,
    ScheduleConflictError,
    ScheduleValidationError,
    validate_event_pattern,
)
from webui.backend.lib.schedule_storage import is_builtin_schedule
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

# Built-in patterns cache (populated on first request)
_builtin_patterns_cache: list[dict] | None = None
_builtin_patterns_cache_lock = threading.Lock()


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
            return jsonify({
                "error": "Schedule not found",
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
            }), 404

        return jsonify(schedule.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
        }), 500


@scheduler_ui_bp.route("/schedules/active", methods=["GET"])
def get_active_schedule():
    """
    Get the currently active schedule.

    GET /api/scheduler/ui/schedules/active

    Returns:
        200 OK: {
            "active": true/false,
            "schedule": {...} or null
        }
    """
    try:
        service = get_scheduler_service()
        schedule = service.get_active_schedule()

        if schedule is None:
            return jsonify({
                "active": False,
                "schedule": None,
            }), 200

        return jsonify({
            "active": True,
            "schedule": schedule.to_dict(),
        }), 200

    except Exception as e:
        logger.error(f"Error getting active schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to get active schedule",
        }), 500


@scheduler_ui_bp.route("/schedules/builtin", methods=["GET"])
def list_builtin_schedules():
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
            for s in builtin
        ]

        return jsonify({
            "schedules": summaries,
            "total": len(summaries),
        }), 200

    except Exception as e:
        logger.error(f"Error listing built-in schedules: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to list built-in schedules",
        }), 500


# ============================================================================
# Schedule CRUD Endpoints (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules", methods=["POST"])
@limiter.limit("30 per minute")
@require_json
def create_schedule(json_data: dict):
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
            logger.debug(f"Missing required field in schedule: {e}")
            return jsonify({
                "error": f"Missing required field: {e}",
            }), 400
        except Exception as e:
            logger.error(f"Invalid schedule format: {e}", exc_info=True)
            return jsonify({
                "error": "Invalid schedule format",
            }), 400

        # Create via service (validates internally)
        service = get_scheduler_service()
        try:
            success = service.create_schedule(schedule)
        except ScheduleValidationError as e:
            logger.debug(f"Schedule validation failed: {e}")
            return jsonify({
                "error": "Schedule validation failed",
            }), 400

        if not success:
            return jsonify({
                "error": "Failed to create schedule",
            }), 500

        return jsonify({
            "message": "Schedule created",
            "schedule_id": schedule.schedule_id,
            "schedule": schedule.to_dict(),
        }), 201

    except Exception as e:
        logger.error(f"Error creating schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to create schedule",
        }), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_json
def update_schedule(schedule_id: str, json_data: dict):
    """
    Update a schedule.

    PUT /api/scheduler/ui/schedules/{id}

    Request Body:
        Partial or complete schedule update data.

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
            return jsonify({
                "error": "Schedule not found",
            }), 404

        # Update via service (handles built-in check)
        try:
            updated = service.update_schedule(schedule_id, json_data)
        except ValueError as e:
            # Built-in schedule protection
            logger.warning(f"Update blocked for built-in schedule: {e}")
            return jsonify({
                "error": "Cannot modify built-in schedule",
            }), 403
        except ScheduleValidationError as e:
            logger.warning(f"Schedule validation failed: {e}")
            return jsonify({
                "error": "Validation failed",
            }), 400

        if updated is None:
            return jsonify({
                "error": "Failed to update schedule",
            }), 500

        return jsonify({
            "message": "Schedule updated",
            "schedule": updated.to_dict(),
        }), 200

    except Exception as e:
        logger.error(f"Error updating schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
        }), 500


@scheduler_ui_bp.route("/schedules/<schedule_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
def delete_schedule(schedule_id: str):
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
            return jsonify({
                "error": "Schedule not found",
            }), 404

        # Delete via service (handles built-in check)
        try:
            success = service.delete_schedule(schedule_id)
        except ValueError as e:
            # Built-in schedule protection
            logger.warning(f"Delete blocked for built-in schedule: {e}")
            return jsonify({
                "error": "Cannot delete built-in schedule",
            }), 403

        if not success:
            return jsonify({
                "error": "Failed to delete schedule",
            }), 500

        return jsonify({
            "message": "Schedule deleted",
            "schedule_id": schedule_id,
        }), 200

    except Exception as e:
        logger.error(f"Error deleting schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
        }), 500


# ============================================================================
# Schedule Activation Endpoints (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/activate", methods=["POST"])
@limiter.limit("10 per minute")
def activate_schedule(schedule_id: str):
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
        coords_provided = "latitude" in data or "longitude" in data
        latitude = data.get("latitude", 0.0)
        longitude = data.get("longitude", 0.0)
        timezone_name = data.get("timezone", "UTC")

        # Validate coordinates if explicitly provided (including 0.0, 0.0)
        # This ensures Null Island coordinates are validated rather than skipped
        if coords_provided:
            valid, coord_error = validate_coordinates(latitude, longitude)
            if not valid:
                return jsonify({
                    "error": f"Invalid coordinates: {coord_error}",
                }), 400

        # Validate timezone
        valid, tz_error = validate_timezone(timezone_name)
        if not valid:
            return jsonify({
                "error": f"Invalid timezone: {tz_error}",
            }), 400

        service = get_scheduler_service()

        # Activate via service (handles existence check internally)
        try:
            service.activate_schedule(
                schedule_id,
                check_conflicts=check_conflicts,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
            )
        except ScheduleConflictError as e:
            # Log conflict details, return generic message
            logger.info(f"Schedule conflict detected: {e}")
            return jsonify({
                "error": "Schedule conflict detected",
                "conflict": True,
            }), 409
        except ScheduleActivationError as e:
            # Log detailed error, return generic message
            logger.warning(f"Schedule activation failed: {e}")
            return jsonify({
                "error": "Schedule activation failed",
            }), 400

        return jsonify({
            "message": "Schedule activated",
            "schedule_id": schedule_id,
        }), 200

    except Exception as e:
        logger.error(f"Error activating schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
        }), 500


@scheduler_ui_bp.route("/schedules/deactivate", methods=["POST"])
@limiter.limit("10 per minute")
def deactivate_current_schedule():
    """
    Deactivate the currently active schedule.

    POST /api/scheduler/ui/schedules/deactivate

    Returns:
        200 OK: {
            "message": "Schedule deactivated" or "No active schedule",
            "was_active": true/false,
            "schedule_id": "..." or null
        }
        500 Internal Server Error: Unexpected error
    """
    try:
        service = get_scheduler_service()

        # Check if there's an active schedule
        active = service.get_active_schedule()
        if active is None:
            return jsonify({
                "message": "No active schedule to deactivate",
                "was_active": False,
                "schedule_id": None,
            }), 200

        # Deactivate
        success = service.deactivate_schedule()

        if not success:
            return jsonify({
                "error": "Failed to deactivate schedule",
            }), 500

        return jsonify({
            "message": "Schedule deactivated",
            "was_active": True,
            "schedule_id": active.schedule_id,
        }), 200

    except Exception as e:
        logger.error(f"Error deactivating schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to deactivate schedule",
        }), 500


# ============================================================================
# Schedule Validation Endpoint (Issue #218)
# ============================================================================


@scheduler_ui_bp.route("/schedules/<schedule_id>/validate", methods=["POST"])
@limiter.limit("30 per minute")
def validate_schedule_endpoint(schedule_id: str):
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
        coords_provided = "latitude" in data or "longitude" in data
        latitude = data.get("latitude", 0.0)
        longitude = data.get("longitude", 0.0)
        timezone_name = data.get("timezone", "UTC")

        # Validate coordinates if explicitly provided (including 0.0, 0.0)
        if coords_provided:
            valid, coord_error = validate_coordinates(latitude, longitude)
            if not valid:
                return jsonify({
                    "error": f"Invalid coordinates: {coord_error}",
                }), 400

        service = get_scheduler_service()

        # Check if schedule exists
        schedule = service.get_schedule(schedule_id)
        if schedule is None:
            return jsonify({
                "error": "Schedule not found",
            }), 404

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

        return jsonify({
            "schedule_id": schedule_id,
            "valid": not report.has_blocking_conflicts,
            "has_warnings": total_conflicts > 0 and not report.has_blocking_conflicts,
            "conflicts": [c.to_dict() for c in report.conflicts],
            "total_conflicts": total_conflicts,
            "blocking_conflicts": blocking_count,
        }), 200

    except Exception as e:
        logger.error(f"Error validating schedule: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
        }), 500


# ============================================================================
# Event Pattern Endpoints (Issue #217)
# ============================================================================


def list_builtin_patterns() -> list[dict]:
    """
    Extract unique event patterns from built-in schedules.

    Each pattern includes:
    - pattern_id: Unique identifier
    - name: Pattern name
    - description: Pattern description
    - actions: List of PatternAction dicts
    - category: Always "built-in"
    - tags: Pattern tags
    - source_schedule: Name of schedule containing this pattern
    - duration_minutes: Computed from max action offset

    Returns:
        List of pattern dictionaries with source_schedule and duration_minutes added

    Note:
        Results are cached at module level for performance using thread-safe
        double-check locking. The cache is populated on first request and
        persists for the lifetime of the process. Built-in patterns are static
        files that don't change at runtime.

        If built-in schedule files are modified, a service restart is required
        to refresh the cache.
    """
    global _builtin_patterns_cache

    # Fast path: cache already populated (no lock needed)
    if _builtin_patterns_cache is not None:
        return _builtin_patterns_cache

    # Slow path: acquire lock and populate cache
    with _builtin_patterns_cache_lock:
        # Double-check after acquiring lock
        if _builtin_patterns_cache is not None:
            return _builtin_patterns_cache

        patterns = []
        seen_ids: set[str] = set()

        # Path to built-in schedules directory
        builtin_dir = Path(__file__).parent.parent / "presets_builtin" / "schedules"

        if not builtin_dir.exists():
            logger.warning(f"Built-in schedules directory not found: {builtin_dir}")
            _builtin_patterns_cache = patterns
            return patterns

        schedule_files = sorted(builtin_dir.glob("*.json"))

        # Safety limit on number of files to process
        if len(schedule_files) > MAX_BUILTIN_SCHEDULE_FILES:
            logger.warning(
                f"Found {len(schedule_files)} schedule files in {builtin_dir}, "
                f"processing only first {MAX_BUILTIN_SCHEDULE_FILES}"
            )
            schedule_files = schedule_files[:MAX_BUILTIN_SCHEDULE_FILES]

        for schedule_file in schedule_files:
            try:
                schedule_data = json.loads(schedule_file.read_text())
                schedule_name = schedule_data.get("name", schedule_file.stem)

                for pattern in schedule_data.get("event_patterns", []):
                    pattern_id = pattern.get("pattern_id")

                    # Deduplicate patterns with pattern_id
                    # Patterns without pattern_id are always included (cannot be deduplicated reliably)
                    if pattern_id:
                        if pattern_id in seen_ids:
                            logger.debug(f"Skipping duplicate pattern_id: {pattern_id}")
                            continue
                        seen_ids.add(pattern_id)

                    # Create a copy with additional fields
                    pattern_copy = dict(pattern)
                    pattern_copy["source_schedule"] = schedule_name

                    # Compute duration_minutes from max action offset
                    actions = pattern.get("actions", [])
                    if actions:
                        pattern_copy["duration_minutes"] = max(
                            a.get("offset_minutes", 0) for a in actions
                        )
                    else:
                        pattern_copy["duration_minutes"] = 0

                    patterns.append(pattern_copy)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse schedule file {schedule_file}: {e}")
            except Exception as e:
                logger.error(f"Error processing schedule file {schedule_file}: {e}")

        # Log warning if no patterns found (possible misconfiguration)
        if not patterns and builtin_dir.exists():
            logger.warning(
                f"No patterns found in {builtin_dir}. "
                "Check schedule files for valid event_patterns."
            )

        # Cache the result for subsequent calls
        _builtin_patterns_cache = patterns
        return patterns


def invalidate_builtin_patterns_cache():
    """Clear the built-in patterns cache.

    Useful for testing or after updating built-in schedule files.
    In production, a service restart is the preferred method.
    """
    global _builtin_patterns_cache
    with _builtin_patterns_cache_lock:
        _builtin_patterns_cache = None
        logger.info("Built-in patterns cache invalidated")


@scheduler_ui_bp.route("/patterns/builtin", methods=["GET"])
def list_builtin_patterns_endpoint():
    """
    List all built-in event patterns.

    GET /api/scheduler/ui/patterns/builtin

    Returns:
        200 OK: List of built-in pattern objects

    Response Schema:
    [
        {
            "pattern_id": "string",
            "name": "string",
            "description": "string",
            "actions": [...],
            "category": "built-in",
            "tags": [...],
            "source_schedule": "string",
            "duration_minutes": number
        }
    ]
    """
    try:
        patterns = list_builtin_patterns()
        return jsonify(patterns), 200

    except Exception as e:
        logger.error(f"Error listing built-in patterns: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Failed to list built-in patterns",
        }), 500


@scheduler_ui_bp.route("/patterns/validate", methods=["POST"])
@limiter.limit("30 per minute")
def validate_pattern_endpoint():
    """
    Validate an event pattern structure.

    POST /api/scheduler/ui/patterns/validate

    Request Body:
    {
        "name": "Pattern Name",      // required, max 200 chars
        "description": "...",        // optional, max 2000 chars
        "actions": [                 // required, 1-20 actions
            {
                "action_type": "gpio|camera|gps_sync|service",
                "action_name": "attract_on|takephoto|...",
                "offset_minutes": 0, // 0-1440
                "parameters": {},
                "description": ""
            }
        ],
        "category": "user",          // optional, "user" or "built-in"
        "tags": []                   // optional
    }

    Returns:
        200 OK: {"valid": true, "pattern": {...}}
        400 Bad Request: {"valid": false, "error": "..."}
    """
    try:
        # Handle missing or invalid JSON body
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify({
                "valid": False,
                "error": "Request body must be valid JSON",
            }), 400

        if data is None:
            return jsonify({
                "valid": False,
                "error": "Request body must be valid JSON",
            }), 400

        if not isinstance(data, dict):
            return jsonify({
                "valid": False,
                "error": "Request body must be a JSON object",
            }), 400

        # Convert dict to EventPattern for validation
        try:
            pattern = EventPattern.from_dict(data)
        except KeyError as e:
            return jsonify({
                "valid": False,
                "error": f"Missing required field: {e}",
            }), 400
        except Exception as e:
            # Log the detailed error server-side, but return a generic message to the client
            logger.error(f"Invalid pattern structure: {e}", exc_info=True)
            return jsonify({
                "valid": False,
                "error": "Invalid pattern structure",
            }), 400

        # Validate using existing validation function
        valid, error = validate_event_pattern(pattern)

        if valid:
            return jsonify({
                "valid": True,
                "pattern": pattern.to_dict(),
            }), 200
        else:
            return jsonify({
                "valid": False,
                "error": error,
            }), 400

    except Exception as e:
        logger.error(f"Error validating pattern: {e}", exc_info=True)
        return jsonify({
            "valid": False,
            "error": "Internal server error during validation",
        }), 500
