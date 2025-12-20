"""
High-level Scheduler UI API routes.

Provides REST endpoints for the visual scheduler UI, including:
- Schedule preview generation
- Event pattern management (Issue #217)
- Future: Schedule CRUD operations

Issue #214 - Scheduler Phase 3: Schedule Preview
Issue #217 - Event Pattern API
"""

import json
import logging
import threading
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

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
    validate_event_pattern,
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

# Maximum number of built-in schedule files to process (safety limit)
MAX_BUILTIN_SCHEDULE_FILES = 20

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
            return jsonify({"error": "Invalid days parameter", "message": error}), 400

        # Parse coordinates
        latitude, error = parse_and_validate_coordinate(lat_str, "lat")
        if error:
            return jsonify({"error": "Invalid lat parameter", "message": error}), 400

        longitude, error = parse_and_validate_coordinate(lon_str, "lon")
        if error:
            return jsonify({"error": "Invalid lon parameter", "message": error}), 400

        # Validate coordinate ranges
        valid, error = validate_coordinates(latitude, longitude)
        if not valid:
            return jsonify({"error": "Invalid coordinates", "message": error}), 400

        # Validate timezone
        valid, error = validate_timezone(timezone_name)
        if not valid:
            return jsonify({"error": "Invalid timezone", "message": error}), 400

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

                    # Skip duplicates - only patterns with non-empty pattern_id are tracked
                    # Patterns without pattern_id are always included (cannot deduplicate)
                    if pattern_id:
                        if pattern_id in seen_ids:
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

        # Cache the result for subsequent calls
        _builtin_patterns_cache = patterns
        return patterns


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
