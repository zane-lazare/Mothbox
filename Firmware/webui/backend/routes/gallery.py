"""Photo gallery endpoints"""

import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

# Setup path to import mothbox_paths
sys.path.insert(0, str(Path(__file__).parent.parent))

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
