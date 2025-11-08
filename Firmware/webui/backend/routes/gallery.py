"""Photo gallery endpoints"""

import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

# Setup path to import mothbox_paths
import mothbox_import  # Sets up sys.path for mothbox_paths import

from services.photo_service import PaginationError, PhotoService
from services.thumbnail_cache import ThumbnailError

from mothbox_paths import PHOTOS_DIR

gallery_bp = Blueprint("gallery", __name__)


@gallery_bp.route("/photos", methods=["GET"])
def list_photos():
    """List all photos with metadata"""
    try:
        if not PHOTOS_DIR.exists():
            return jsonify({"photos": []})

        photos = []
        for photo_path in sorted(
            PHOTOS_DIR.glob("**/*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            stat = photo_path.stat()
            photos.append(
                {
                    "path": str(photo_path.relative_to(PHOTOS_DIR)),
                    "filename": photo_path.name,
                    "size": stat.st_size,
                    "timestamp": stat.st_mtime,
                    "date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return jsonify({"photos": photos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gallery_bp.route("/photo/<path:photo_path>", methods=["GET"])
def get_photo(photo_path):
    """Serve a specific photo"""
    try:
        # Use resolve() and relative_to() for robust path traversal protection
        full_path = (PHOTOS_DIR / photo_path).resolve()
        photos_dir_resolved = PHOTOS_DIR.resolve()

        # Ensure path is within PHOTOS_DIR (raises ValueError if not)
        full_path.relative_to(photos_dir_resolved)

        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        return send_file(full_path, mimetype="image/jpeg")
    except (ValueError, RuntimeError):
        # ValueError: Path is outside PHOTOS_DIR
        # RuntimeError: resolve() failed (e.g., symlink loop)
        return jsonify({"error": "Invalid path"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gallery_bp.route("/thumbnail/<path:photo_path>", methods=["GET"])
def get_thumbnail(photo_path):
    """Get thumbnail for a photo (generates if needed) with optional size parameter"""
    try:
        # Get size from query params (default: 256)
        size = request.args.get('size', 256, type=int)

        # Get cache instance from app config
        thumbnail_cache = current_app.config.get('THUMBNAIL_CACHE')

        if thumbnail_cache:
            # Use cache service
            try:
                thumbnail_path = thumbnail_cache.get_thumbnail(PHOTOS_DIR / photo_path, size)
                return send_file(thumbnail_path, mimetype="image/jpeg")
            except ThumbnailError as e:
                return jsonify({"error": str(e)}), 400
        else:
            # Fallback to original behavior if cache not available
            import io

            from PIL import Image

            # Use resolve() and relative_to() for robust path traversal protection
            full_path = (PHOTOS_DIR / photo_path).resolve()
            photos_dir_resolved = PHOTOS_DIR.resolve()

            # Ensure path is within PHOTOS_DIR (raises ValueError if not)
            full_path.relative_to(photos_dir_resolved)

            if not full_path.exists():
                return jsonify({"error": "Photo not found"}), 404

            # Generate thumbnail
            img = Image.open(full_path)
            img.thumbnail((300, 300))

            # Return as bytes
            img_io = io.BytesIO()
            img.save(img_io, "JPEG", quality=85)
            img_io.seek(0)

            return send_file(img_io, mimetype="image/jpeg")
    except (ValueError, RuntimeError):
        # ValueError: Path is outside PHOTOS_DIR
        # RuntimeError: resolve() failed (e.g., symlink loop)
        return jsonify({"error": "Invalid path"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gallery_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics"""
    thumbnail_cache = current_app.config.get('THUMBNAIL_CACHE')

    if not thumbnail_cache:
        return jsonify({"error": "Cache not available"}), 503

    stats = thumbnail_cache.get_statistics()
    return jsonify(stats)


@gallery_bp.route("/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """Manually invalidate cache entries (requires CSRF token)"""
    thumbnail_cache = current_app.config.get('THUMBNAIL_CACHE')

    if not thumbnail_cache:
        return jsonify({"error": "Cache not available"}), 503

    # Get optional photo_path from request JSON
    data = request.get_json() or {}
    photo_path = data.get('photo_path')
    size = data.get('size')

    try:
        if photo_path:
            thumbnail_cache.invalidate(PHOTOS_DIR / photo_path, size=size)
            message = f"Invalidated cache for {photo_path}"
        else:
            thumbnail_cache.invalidate()
            message = "Invalidated entire cache"

        return jsonify({"success": True, "message": message})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@gallery_bp.route("/cache/warm", methods=["POST"])
def cache_warm():
    """
    Trigger cache warming (requires CSRF token)

    Request body (JSON):
    {
        "priority": "newest|all",  // optional, default: "newest"
        "count": 100,               // optional, number of recent photos
        "sizes": [64, 128, 256],    // optional, default: all sizes
        "background": true          // optional, default: true
    }

    Response:
    {
        "task_id": "uuid-here",
        "status": "started",
        "message": "Warming 100 recent photos"
    }
    """
    cache_warmer = current_app.config.get('CACHE_WARMER')

    if not cache_warmer:
        return jsonify({"error": "Cache warmer not available"}), 503

    # Get optional parameters from request JSON
    data = request.get_json() or {}
    count = data.get('count', 100)
    sizes = data.get('sizes')  # None = all sizes
    background = data.get('background', True)

    try:
        result = cache_warmer.warm_recent(
            count=count,
            sizes=sizes,
            background=background
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@gallery_bp.route("/cache/warm/status", methods=["GET"])
@gallery_bp.route("/cache/warm/status/<task_id>", methods=["GET"])
def cache_warm_status(task_id=None):
    """
    Get warming task status

    Response:
    {
        "task_id": "...",
        "status": "running|completed|failed",
        "progress": {"current": 50, "total": 100, "percent": 50},
        "started_at": "2025-11-06T08:00:00Z",
        "photos_warmed": 50
    }
    """
    cache_warmer = current_app.config.get('CACHE_WARMER')

    if not cache_warmer:
        return jsonify({"error": "Cache warmer not available"}), 503

    try:
        status = cache_warmer.get_warming_status(task_id)
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@gallery_bp.route("/cache/warm/cancel/<task_id>", methods=["POST"])
def cache_warm_cancel(task_id):
    """Cancel a running warming task (requires CSRF token)"""
    cache_warmer = current_app.config.get('CACHE_WARMER')

    if not cache_warmer:
        return jsonify({"error": "Cache warmer not available"}), 503

    try:
        result = cache_warmer.cancel_warming(task_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@gallery_bp.route("/photos/paginated", methods=["GET"])
def list_photos_paginated():
    """
    List photos with pagination, sorting, and filtering support

    Query Parameters:
        limit (int): Maximum photos per page (1-500, default: 50)
        offset (int): Number of photos to skip (>=0, default: 0)
        sort (str): Sort order - date_desc, date_asc, filename_asc, filename_desc
                   (default: date_desc)
        start_date (str): Filter photos on/after this date (ISO format: YYYY-MM-DD)
        end_date (str): Filter photos on/before this date (ISO format: YYYY-MM-DD)

    Returns:
        JSON response with photos array and pagination metadata:
        {
            "photos": [...],
            "pagination": {
                "total": int,
                "limit": int,
                "offset": int,
                "has_next": bool,
                "has_previous": bool
            }
        }

    Error Responses:
        400: Invalid parameters (limit/offset out of range, invalid sort/date)
        500: Internal server error
    """
    try:
        # Extract query parameters with defaults
        # Note: type=int returns default if conversion fails, but we validate explicitly
        limit_str = request.args.get('limit')
        offset_str = request.args.get('offset')

        # Parse and validate limit
        if limit_str is not None:
            try:
                limit = int(limit_str)
            except ValueError:
                return jsonify({"error": f"Limit must be an integer, got '{limit_str}'"}), 400
        else:
            limit = 50

        # Parse and validate offset
        if offset_str is not None:
            try:
                offset = int(offset_str)
            except ValueError:
                return jsonify({"error": f"Offset must be an integer, got '{offset_str}'"}), 400
        else:
            offset = 0

        sort = request.args.get('sort', 'date_desc')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Parse date strings if provided
        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {"error": f"Invalid start_date format: '{start_date_str}'. Use ISO format (YYYY-MM-DD)"}
                    ),
                    400,
                )

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {"error": f"Invalid end_date format: '{end_date_str}'. Use ISO format (YYYY-MM-DD)"}
                    ),
                    400,
                )

        # Create photo service and get paginated results
        photo_service = PhotoService(PHOTOS_DIR)
        result = photo_service.list_photos(
            limit=limit,
            offset=offset,
            sort=sort,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(result)

    except PaginationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
