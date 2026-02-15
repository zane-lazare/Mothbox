"""GPS EXIF tagger API endpoints.

Provides REST API for GPS EXIF tagging operations on Mothbox photos.
Supports single-photo tagging, batch processing, and configuration management.

Blueprint: gps_exif_bp
URL Prefix: /api/gps-exif

Endpoints:
- GET    /status       - Return tagger status and statistics
- POST   /tag-photo    - Tag a single photo with GPS EXIF data
- POST   /batch-tag    - Batch tag photos in a directory
- GET    /config       - Get current tagger configuration
- PUT    /config       - Update tagger configuration

Security:
- CSRF protection (Flask-WTF) on all state-changing endpoints
- Path traversal protection on all file paths
- Input validation on all request parameters
- Sanitized error messages (no stack trace exposure)
"""

import json
import logging
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from mothbox_paths import CONFIG_DIR, PHOTOS_DIR
from webui.backend.lib.gps_coordinate_resolver import VALID_SOURCES, resolve_coordinates
from webui.backend.lib.gps_exif_lib import embed_gps_exif

logger = logging.getLogger(__name__)

gps_exif_bp = Blueprint("gps_exif", __name__)

# Default configuration for the GPS EXIF tagger
DEFAULT_CONFIG = {
    "default_sources": ["deployment", "gps"],
    "pattern": "**/*.jpg",
}


def _get_config_file() -> Path:
    """Return the path to the GPS EXIF tagger config file."""
    return CONFIG_DIR / "gps_exif_config.json"


def _load_config() -> dict:
    """Load GPS EXIF tagger config, falling back to defaults.

    Returns:
        dict with keys: default_sources, pattern
    """
    config_file = _get_config_file()
    try:
        if config_file.exists():
            with open(config_file) as f:
                saved = json.load(f)
            # Merge with defaults for any missing keys
            return {**DEFAULT_CONFIG, **saved}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load GPS EXIF config, using defaults: %s", e)

    return DEFAULT_CONFIG.copy()


def _save_config(config: dict) -> None:
    """Save GPS EXIF tagger config to disk.

    Args:
        config: Configuration dict to persist.

    Raises:
        OSError: If the file cannot be written.
    """
    config_file = _get_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)


def _validate_relative_path(user_path: str, base_dir: Path) -> Path | None:
    """Validate a user-supplied path is relative and under base_dir.

    Args:
        user_path: User-supplied relative path string.
        base_dir: Base directory the path must resolve under.

    Returns:
        Resolved Path if valid, or None if the path is invalid.
    """
    # Reject absolute paths
    if user_path.startswith(("/", "\\")):
        return None

    # Reject obvious traversal attempts
    if ".." in user_path:
        return None

    # Resolve the full path and check it stays under base_dir
    resolved = (base_dir / user_path).resolve()
    base_resolved = base_dir.resolve()

    if not resolved.is_relative_to(base_resolved):
        return None

    return resolved


# ============================================================================
# GET /status
# ============================================================================


@gps_exif_bp.route("/status", methods=["GET"])
def get_status():
    """Return GPS EXIF tagger status and statistics.

    Response:
        {
            "coordinate_sources": ["deployment", "gps", "manual"],
            "service_running": bool | null,
            "stats": { "photos_dir_exists": bool }
        }
    """
    try:
        # Check systemd service status (non-critical, return null on failure)
        service_running = None
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "gps-exif-tagger"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            service_running = result.stdout.strip() == "active"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Not on a system with systemd, or service doesn't exist
            service_running = None

        # Basic stats
        stats = {
            "photos_dir_exists": PHOTOS_DIR.exists(),
        }

        return jsonify(
            {
                "coordinate_sources": list(VALID_SOURCES),
                "service_running": service_running,
                "stats": stats,
            }
        )
    except Exception:
        logger.exception("Failed to get GPS EXIF tagger status")
        return jsonify({"error": "Failed to get GPS EXIF tagger status"}), 500


# ============================================================================
# POST /tag-photo
# ============================================================================


@gps_exif_bp.route("/tag-photo", methods=["POST"])
def tag_photo():
    """Tag a single photo with GPS EXIF data.

    Request body:
        {
            "photo_path": "2026-02-10/photo.jpg",
            "coordinate_source": "deployment",
            "manual_coords": {"lat": ..., "lon": ...}
        }

    Response:
        {
            "success": true,
            "source_used": "deployment",
            "coordinates": {"lat": ..., "lon": ...}
        }
    """
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate photo_path is present and non-empty
    photo_path_str = data.get("photo_path")
    if not photo_path_str or not isinstance(photo_path_str, str) or not photo_path_str.strip():
        return jsonify({"error": "photo_path is required"}), 400

    photo_path_str = photo_path_str.strip()

    # Validate path (no traversal, relative, under PHOTOS_DIR)
    resolved_path = _validate_relative_path(photo_path_str, PHOTOS_DIR)
    if resolved_path is None:
        return jsonify({"error": "Invalid path: path traversal not allowed"}), 400

    # Check file exists
    if not resolved_path.exists():
        return jsonify({"error": f"Photo not found: {photo_path_str}"}), 404

    # Determine coordinate source(s)
    source_str = data.get("coordinate_source", "deployment")
    if isinstance(source_str, str):
        sources = (source_str,)
    elif isinstance(source_str, list):
        sources = tuple(source_str)
    else:
        sources = ("deployment",)

    manual_coords = data.get("manual_coords")

    # Validate manual coordinates if provided
    if manual_coords is not None:
        if not isinstance(manual_coords, dict):
            return jsonify({"error": "manual_coords must be an object with lat and lon"}), 400
        lat = manual_coords.get("lat")
        lon = manual_coords.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return jsonify({"error": "manual_coords.lat and .lon must be numbers"}), 400
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            return jsonify({"error": "lat must be -90..90, lon must be -180..180"}), 400

    try:
        # Lazy import to avoid circular dependency
        from webui.backend.services.deployment_service import DeploymentService

        deployment_service = DeploymentService()

        resolved = resolve_coordinates(
            photo_path=resolved_path,
            sources=sources,
            manual_coords=manual_coords,
            deployment_service=deployment_service,
        )

        if resolved is None:
            return (
                jsonify(
                    {
                        "error": "No coordinates available from the specified source(s)",
                        "sources_tried": list(sources),
                    }
                ),
                400,
            )

        # Embed GPS EXIF
        result = embed_gps_exif(resolved_path, gps_data=resolved["gps_data"])

        if not result["success"]:
            error_msg = result.get("error", "Unknown error during GPS EXIF embedding")
            return jsonify({"error": error_msg}), 500

        return jsonify(
            {
                "success": True,
                "source_used": resolved["source"],
                "coordinates": {
                    "lat": resolved["lat"],
                    "lon": resolved["lon"],
                },
            }
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Failed to tag photo: %s", photo_path_str)
        return jsonify({"error": "Failed to tag photo"}), 500


# ============================================================================
# POST /batch-tag
# ============================================================================


@gps_exif_bp.route("/batch-tag", methods=["POST"])
def batch_tag():
    """Batch tag photos in a directory.

    Request body:
        {
            "coordinate_sources": ["deployment", "gps"],
            "pattern": "**/*.jpg",
            "directory": "2026-02-10",
            "force": false,
            "dry_run": false
        }

    Response:
        {
            "total": N,
            "tagged": N,
            "skipped": N,
            "errors": N,
            "source_counts": {...}
        }
    """
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    # Determine target directory
    directory_str = data.get("directory")
    if directory_str:
        resolved_dir = _validate_relative_path(directory_str, PHOTOS_DIR)
        if resolved_dir is None:
            return jsonify({"error": "Invalid directory: path traversal not allowed"}), 400
        target_dir = resolved_dir
    else:
        target_dir = PHOTOS_DIR

    # Parse options
    coordinate_sources = data.get("coordinate_sources", ["deployment", "gps"])
    if not isinstance(coordinate_sources, list):
        return jsonify({"error": "coordinate_sources must be a list"}), 400

    pattern = data.get("pattern", "**/*.jpg")
    force = bool(data.get("force", False))
    dry_run = bool(data.get("dry_run", False))
    manual_coords = data.get("manual_coords")

    # Validate manual coordinates if provided
    if manual_coords is not None:
        if not isinstance(manual_coords, dict):
            return jsonify({"error": "manual_coords must be an object with lat and lon"}), 400
        lat = manual_coords.get("lat")
        lon = manual_coords.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return jsonify({"error": "manual_coords.lat and .lon must be numbers"}), 400
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            return jsonify({"error": "lat must be -90..90, lon must be -180..180"}), 400

    try:
        from webui.cli.gps_exif_tagger import batch_process_directory

        # Create a logger for the batch process
        batch_logger = logging.getLogger("gps_exif_tagger.batch")

        stats = batch_process_directory(
            target_dir,
            batch_logger,
            pattern=pattern,
            force=force,
            backup=False,
            dry_run=dry_run,
            coordinate_sources=tuple(coordinate_sources),
            manual_coords=manual_coords,
        )

        return jsonify(
            {
                "total": stats["total"],
                "tagged": stats["tagged"],
                "skipped": stats["skipped"],
                "errors": stats["errors"],
                "source_counts": stats.get("source_counts", {}),
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Batch tagging failed")
        return jsonify({"error": "Batch tagging failed"}), 500


# ============================================================================
# GET /config
# ============================================================================


@gps_exif_bp.route("/config", methods=["GET"])
def get_config():
    """Return current GPS EXIF tagger configuration.

    Response:
        {
            "default_sources": ["deployment", "gps"],
            "pattern": "**/*.jpg"
        }
    """
    try:
        config = _load_config()
        return jsonify(config)
    except Exception:
        logger.exception("Failed to get GPS EXIF config")
        return jsonify({"error": "Failed to get GPS EXIF config"}), 500


# ============================================================================
# PUT /config
# ============================================================================


@gps_exif_bp.route("/config", methods=["PUT"])
def update_config():
    """Update GPS EXIF tagger configuration.

    Request body:
        {
            "default_sources": ["gps"],
            "pattern": "**/*.jpg"
        }

    Response:
        {
            "success": true,
            "config": {...}
        }
    """
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate default_sources if provided
    if "default_sources" in data:
        sources = data["default_sources"]
        if not isinstance(sources, list) or len(sources) == 0:
            return jsonify({"error": "default_sources must be a non-empty list"}), 400

        for source in sources:
            if source not in VALID_SOURCES:
                return (
                    jsonify(
                        {
                            "error": f"Invalid source '{source}'. "
                            f"Valid sources: {', '.join(VALID_SOURCES)}"
                        }
                    ),
                    400,
                )

    # Build updated config
    current = _load_config()

    if "default_sources" in data:
        current["default_sources"] = data["default_sources"]

    if "pattern" in data:
        current["pattern"] = data["pattern"]

    try:
        _save_config(current)
    except OSError:
        logger.exception("Failed to save GPS EXIF config")
        return jsonify({"error": "Failed to save configuration"}), 500

    return jsonify({"success": True, "config": current})
