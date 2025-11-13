"""
Photo gallery endpoints with metadata caching support.

Provides gallery endpoints for photo listing, serving, thumbnails, and metadata
extraction with two-level LRU caching for performance optimization.

Endpoints:
- GET /photos - List all photos
- GET /photo/<path> - Serve specific photo
- GET /thumbnail/<path> - Get/generate thumbnail
- GET /photos/<photo_id>/metadata - Get photo metadata with caching
- DELETE /photos/<photo_id>/cache - Clear photo metadata cache
- GET /cache/stats - Get thumbnail cache statistics
- GET /cache/statistics - Get metadata cache statistics
- POST /cache/invalidate - Invalidate thumbnail cache
- POST /cache/warm - Trigger cache warming
- GET /cache/warm/status - Get warming task status
- POST /cache/warm/cancel/<task_id> - Cancel warming task
- GET /photos/paginated - List photos with pagination
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import time
import logging

from flask import Blueprint, current_app, jsonify, request, send_file

# Import will be available when app.py is created
# For now, using a simple limiter stub
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    # Stub for testing without flask_limiter
    class LimiterStub:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

    limiter = LimiterStub()

# Import services
from services.photo_service import PaginationError, PhotoService
from services.thumbnail_cache import ThumbnailError
from services.metadata_cache import MetadataCache
from services.metadata_service import MetadataService

# Import mothbox paths
from mothbox_paths import DATA_DIR, PHOTOS_DIR

logger = logging.getLogger(__name__)

# Blueprint setup (no prefix - will be added by app.py)
gallery_bp = Blueprint("gallery", __name__)

# Module-level cache instance (singleton)
_metadata_cache = None


def get_metadata_cache() -> MetadataCache:
    """Get or create metadata cache singleton"""
    global _metadata_cache
    if _metadata_cache is None:
        cache_dir = DATA_DIR / "cache" / "metadata"
        _metadata_cache = MetadataCache(
            cache_dir=cache_dir,
            l1_max_size=1000,
            l2_max_size=10000,
            cache_version="1.0",
        )
    return _metadata_cache


# Valid metadata categories
VALID_CATEGORIES = {"camera", "location", "capture", "deployment", "file", "all"}


# ============================================================================
# Photo Listing and Serving Endpoints
# ============================================================================

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
                full_photo_path = PHOTOS_DIR / photo_path
                thumbnail_path = thumbnail_cache.get_thumbnail(full_photo_path, size)
                return send_file(thumbnail_path, mimetype="image/jpeg")
            except ThumbnailError as e:
                current_app.logger.error(f"ThumbnailError: {e}")
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


# ============================================================================
# Metadata Endpoints (Issue #100)
# ============================================================================

@gallery_bp.route("/photos/<path:photo_id>/metadata", methods=["GET"])
@limiter.limit("60 per minute")
def get_photo_metadata(photo_id):
    """
    Get metadata for a photo with optional category filtering.

    Query Parameters:
        categories (str): Comma-separated list of categories
                         (camera, location, capture, deployment, file, all)
                         Default: 'all'

    Returns:
        JSON response with:
        - success (bool): True if successful
        - photo_id (str): Photo identifier
        - metadata (dict): Photo metadata
        - cache_info (dict): Cache hit information

    Example:
        GET /photos/2024-01-15/photo.jpg/metadata?categories=camera,location

    Status Codes:
        200: Success
        400: Invalid category
        404: Photo not found
        500: Metadata extraction failed
    """
    # 1. Parse and validate category filter
    categories_param = request.args.get("categories", "all")
    requested_categories = set(cat.strip() for cat in categories_param.split(","))

    invalid = requested_categories - VALID_CATEGORIES
    if invalid:
        return jsonify(
            {
                "success": False,
                "error": f"Invalid category: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_CATEGORIES))}",
            }
        ), 400

    # 2. Resolve photo path with security checks
    photo_path = _resolve_photo_path(photo_id)
    if not photo_path:
        return jsonify(
            {"success": False, "error": "Photo not found", "photo_id": photo_id}
        ), 404

    # 3. Try cache first
    cache = get_metadata_cache()
    start_time = time.time()
    cached_metadata = cache.get(str(photo_path))
    cache_lookup_time = (time.time() - start_time) * 1000

    cache_info = {
        "cached": False,
        "cache_level": None,
        "age_seconds": 0,
        "lookup_time_ms": cache_lookup_time,
    }

    if cached_metadata:
        metadata = cached_metadata
        stats = cache.get_statistics()

        # Determine cache level based on lookup time
        if cache_lookup_time < 10:
            cache_level = "l1_memory"
        elif cache_lookup_time < 50:
            cache_level = "l2_disk"
        else:
            cache_level = "unknown"

        cache_info = {
            "cached": True,
            "cache_level": cache_level,
            "age_seconds": int(
                time.time() - metadata.get("_cache_timestamp", time.time())
            ),
            "lookup_time_ms": round(cache_lookup_time, 2),
            "cache_hit_ratio": round(stats.hit_ratio, 3),
        }
    else:
        # 4. Cache miss - fetch from MetadataService
        try:
            service = MetadataService()
            metadata = service.get_photo_metadata(photo_path)

            # Store in cache with timestamp
            metadata["_cache_timestamp"] = time.time()
            cache.set(str(photo_path), metadata)

            cache_info["cached"] = False
            cache_info["lookup_time_ms"] = round(cache_lookup_time, 2)

        except Exception as e:
            logger.error(
                f"Metadata extraction failed for {photo_path}: {e}", exc_info=True
            )
            return jsonify(
                {"success": False, "error": f"Failed to read metadata: {str(e)}"}
            ), 500

    # 5. Apply category filtering
    if "all" not in requested_categories:
        metadata = {
            k: v
            for k, v in metadata.items()
            if k in requested_categories or k.startswith("_")
        }

    # 6. Remove internal fields before returning
    metadata = {k: v for k, v in metadata.items() if not k.startswith("_")}

    return jsonify(
        {
            "success": True,
            "photo_id": photo_id,
            "metadata": metadata,
            "cache_info": cache_info,
        }
    )


@gallery_bp.route("/photos/<path:photo_id>/cache", methods=["DELETE"])
@limiter.limit("10 per minute")
def clear_photo_metadata_cache(photo_id):
    """
    Clear metadata cache for a specific photo.

    TODO: Add CSRF protection (DELETE is state-changing).
    Note: CSRF protection is handled at the application level by Flask-WTF.

    Returns:
        JSON response with:
        - success (bool): True if successful
        - message (str): Status message
        - photo_id (str): Photo identifier

    Example:
        DELETE /photos/2024-01-15/photo.jpg/cache

    Status Codes:
        200: Success
        404: Photo not found
    """
    # Resolve photo path
    photo_path = _resolve_photo_path(photo_id)
    if not photo_path:
        return jsonify(
            {"success": False, "error": "Photo not found", "photo_id": photo_id}
        ), 404

    # Invalidate cache
    cache = get_metadata_cache()
    removed = cache.invalidate(str(photo_path))

    return jsonify(
        {
            "success": True,
            "message": "Cache cleared for photo" if removed else "Photo was not cached",
            "photo_id": photo_id,
            "was_cached": removed,
        }
    )


@gallery_bp.route("/cache/statistics", methods=["GET"])
def get_metadata_cache_statistics():
    """
    Get metadata cache performance statistics.

    Returns:
        JSON response with cache statistics

    Example:
        GET /cache/statistics

    Status Codes:
        200: Success
    """
    cache = get_metadata_cache()
    stats = cache.get_statistics()

    return jsonify(
        {
            "success": True,
            "statistics": {
                "l1_hits": stats.l1_hits,
                "l1_misses": stats.l1_misses,
                "l2_hits": stats.l2_hits,
                "l2_misses": stats.l2_misses,
                "total_hits": stats.total_hits,
                "total_misses": stats.total_misses,
                "hit_ratio": round(stats.hit_ratio, 3),
                "avg_response_time_ms": round(stats.avg_response_time_ms, 2),
            },
        }
    )


def _resolve_photo_path(photo_id: str) -> Optional[Path]:
    """
    Resolve photo ID to absolute path with security checks.

    Protects against path traversal attacks.

    Args:
        photo_id: Photo identifier (relative path from PHOTOS_DIR)

    Returns:
        Absolute Path if valid and exists, None otherwise
    """
    # Path traversal protection
    if ".." in photo_id or photo_id.startswith("/"):
        logger.warning(f"Path traversal attempt detected: {photo_id}")
        return None

    photo_path = PHOTOS_DIR / photo_id

    # Canonical path check (prevents symlink attacks)
    try:
        photo_path = photo_path.resolve()
        photos_dir_resolved = PHOTOS_DIR.resolve()

        # Ensure path is within PHOTOS_DIR
        if not str(photo_path).startswith(str(photos_dir_resolved)):
            logger.warning(f"Photo path outside PHOTOS_DIR: {photo_path}")
            return None
    except Exception as e:
        logger.warning(f"Failed to resolve photo path {photo_id}: {e}")
        return None

    # Check if file exists and is a regular file
    if not photo_path.exists() or not photo_path.is_file():
        return None

    return photo_path


# ============================================================================
# Thumbnail Cache Endpoints
# ============================================================================

@gallery_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get thumbnail cache statistics"""
    thumbnail_cache = current_app.config.get('THUMBNAIL_CACHE')

    if not thumbnail_cache:
        return jsonify({"error": "Cache not available"}), 503

    stats = thumbnail_cache.get_statistics()
    return jsonify(stats)


@gallery_bp.route("/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """Manually invalidate thumbnail cache entries (requires CSRF token)"""
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


# For testing: allow resetting the cache singleton
def _reset_cache():
    """Reset cache singleton (for testing only)"""
    global _metadata_cache
    _metadata_cache = None
