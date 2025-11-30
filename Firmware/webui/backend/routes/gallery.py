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
- GET /series - List photo series (HDR/Focus Bracket) with pagination
- GET /series/<series_id> - Get specific series details
- GET /series/stats - Get series cache statistics
- POST /series/cache/invalidate - Invalidate series cache
- GET /locations - Get photos with GPS coordinates for map display
- POST /locations/cache/invalidate - Invalidate locations cache
- GET /locations/stats - Get locations cache statistics
- GET /locations/clustered - Get clustered photo locations (Issue #115)
- GET /locations/clustered/stats - Get clustering cache statistics
- POST /locations/clustered/cache/invalidate - Invalidate clustering cache
"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

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
# Import security utilities
from security_utils import validate_photo_path
from services.locations_service import LocationsService
from services.metadata_cache import MetadataCache
from services.metadata_service import MetadataService
from services.photo_service import PaginationError, PhotoService
from services.thumbnail_cache import ThumbnailError

# Import mothbox paths
from mothbox_paths import DATA_DIR, PHOTOS_DIR

logger = logging.getLogger(__name__)

# Blueprint setup (no prefix - will be added by app.py)
gallery_bp = Blueprint("gallery", __name__)

# Module-level cache instance (singleton) with thread-safety
_metadata_cache = None
_cache_lock = threading.Lock()

# Initialize locations service with 5-minute cache
_locations_service = LocationsService(cache_ttl=300)


def get_metadata_cache() -> MetadataCache:
    """
    Get or create metadata cache singleton with thread-safe initialization.

    Uses double-checked locking pattern to ensure only one cache instance
    is created even under concurrent access from multiple threads.

    Returns:
        MetadataCache: Singleton cache instance
    """
    global _metadata_cache

    # First check without lock (fast path for already-initialized case)
    if _metadata_cache is not None:
        return _metadata_cache

    # Acquire lock for initialization
    with _cache_lock:
        # Second check with lock (only one thread initializes)
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
        print(f"Error in list_photos: {e}")
        return jsonify({"error": "Failed to list photos"}), 500


@gallery_bp.route("/photo/<path:photo_path>", methods=["GET"])
def get_photo(photo_path):
    """Serve a specific photo"""
    try:
        # Validate path with security_utils (CodeQL requirement)
        full_path = validate_photo_path(photo_path, PHOTOS_DIR)

        if full_path is None:
            return jsonify({"error": "Invalid path"}), 400

        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        return send_file(full_path, mimetype="image/jpeg")
    except Exception as e:
        logger.error(f"Error serving photo {photo_path}: {e}", exc_info=True)
        return jsonify({"error": "Failed to serve photo"}), 500


@gallery_bp.route("/thumbnail/<path:photo_path>", methods=["GET"])
def get_thumbnail(photo_path):
    """Get thumbnail for a photo (generates if needed) with optional size parameter"""
    try:
        # Validate path with security_utils (CodeQL requirement)
        full_photo_path = validate_photo_path(photo_path, PHOTOS_DIR)

        if full_photo_path is None:
            return jsonify({"error": "Invalid path"}), 400

        # Get size from query params (default: 256)
        size = request.args.get('size', 256, type=int)

        # Get cache instance from app config
        thumbnail_cache = current_app.config.get('THUMBNAIL_CACHE')

        if thumbnail_cache:
            # Use cache service
            try:
                thumbnail_path = thumbnail_cache.get_thumbnail(full_photo_path, size)
                return send_file(thumbnail_path, mimetype="image/jpeg")
            except ThumbnailError as e:
                current_app.logger.error(f"ThumbnailError: {e}")
                return jsonify({"error": "Failed to generate thumbnail"}), 400
        else:
            # Fallback to original behavior if cache not available
            import io

            from PIL import Image

            # Path already validated above via validate_photo_path()
            full_path = full_photo_path

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
        print(f"Error listing photos: {e}")  # Log server-side only
        return jsonify({"error": "Internal server error"}), 500


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
        # Log full error details server-side (CodeQL security requirement)
        logger.error(f"Pagination error: {e}", exc_info=True)
        # Return generic message to user (don't expose internal details)
        return jsonify({"error": "Invalid pagination parameters"}), 400
    except Exception as e:
        # Log full error details server-side
        logger.error(f"Unexpected error in list_photos_paginated: {e}", exc_info=True)
        # Return generic message to user
        return jsonify({"error": "Internal server error"}), 500


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
    requested_categories = {cat.strip() for cat in categories_param.split(",")}

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
            # Log full error details server-side (CodeQL security requirement)
            logger.error(
                f"Metadata extraction failed for {photo_path}: {e}", exc_info=True
            )
            # Return generic message to user (don't expose internal details)
            return jsonify(
                {"success": False, "error": "Failed to read metadata"}
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
    Clear metadata cache for a specific photo (requires CSRF token).

    Security: CSRF protection enforced by Flask-WTF CSRFProtect.
    DELETE is a state-changing operation and requires X-CSRFToken header.

    Returns:
        JSON response with:
        - success (bool): True if successful
        - message (str): Status message
        - photo_id (str): Photo identifier
        - was_cached (bool): Whether photo was in cache

    Example:
        DELETE /photos/2024-01-15/photo.jpg/cache
        Headers: X-CSRFToken: <token>

    Status Codes:
        200: Success
        400: CSRF token missing or invalid
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


def _resolve_photo_path(photo_id: str) -> Path | None:
    """
    Resolve photo ID to absolute path with security checks.

    Protects against path traversal attacks by using validate_photo_path()
    from security_utils which provides CodeQL-compliant path validation.

    Args:
        photo_id: Photo identifier (relative path from PHOTOS_DIR)

    Returns:
        Absolute Path if valid and exists, None otherwise
    """
    # Input validation - BEFORE any Path operations (CodeQL security requirement)
    if not photo_id:
        logger.warning("Empty photo_id provided")
        return None

    # Use security_utils validation (CodeQL-compliant)
    photo_path = validate_photo_path(photo_id, PHOTOS_DIR)

    if photo_path is None:
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
    photo_path_str = data.get('photo_path')
    size = data.get('size')

    try:
        if photo_path_str:
            # Validate path with security_utils (CodeQL requirement)
            photo_path = validate_photo_path(photo_path_str, PHOTOS_DIR)

            if photo_path is None:
                return jsonify({"error": "Invalid path"}), 400

            thumbnail_cache.invalidate(photo_path, size=size)
            message = f"Invalidated cache for {photo_path_str}"
        else:
            thumbnail_cache.invalidate()
            message = "Invalidated entire cache"

        return jsonify({"success": True, "message": message})

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}", exc_info=True)
        return jsonify({"error": "Cache invalidation failed"}), 400


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
        print(f"Error starting cache warming: {e}")
        return jsonify({"error": "Failed to start cache warming"}), 400


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
        print(f"Error getting warming status: {e}")
        return jsonify({"error": "Failed to get warming status"}), 400


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
        print(f"Error cancelling cache warming: {e}")  # Log server-side only
        return jsonify({"error": "Failed to cancel warming task"}), 400


# For testing: allow resetting the cache singleton
def _reset_cache():
    """
    Reset cache singleton (for testing only).

    Thread-safe reset that ensures no concurrent initialization
    can occur during reset.
    """
    global _metadata_cache
    with _cache_lock:
        _metadata_cache = None


# ============================================================================
# Series Endpoints (Issue #110 - Phase 3)
# ============================================================================

# Valid series types for filtering
VALID_SERIES_TYPES = {"hdr", "focus_bracket"}


@gallery_bp.route("/series", methods=["GET"])
def list_series():
    """
    List photo series (HDR and Focus Bracket) with pagination and filtering.

    Query Parameters:
        page (int): Page number (1-indexed, default: 1)
        per_page (int): Items per page (1-100, default: 50)
        type (str): Filter by series type (hdr, focus_bracket)

    Returns:
        JSON response with:
        - series: List of series objects
        - pagination: Pagination metadata

    Example:
        GET /series?page=1&per_page=50&type=hdr

    Status Codes:
        200: Success
        400: Invalid parameters
        503: Series service unavailable
    """
    # Get series service from app config
    series_service = current_app.config.get('SERIES_SERVICE')

    if not series_service:
        return jsonify({"error": "Series service not available"}), 503

    # Parse pagination parameters
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        if page < 1:
            return jsonify({"error": "Page must be >= 1"}), 400
        if per_page < 1 or per_page > 100:
            return jsonify({"error": "per_page must be 1-100"}), 400

    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid pagination parameter: {e}"}), 400

    # Parse type filter
    series_type_filter = request.args.get('type')
    if series_type_filter and series_type_filter not in VALID_SERIES_TYPES:
        return jsonify({
            "error": f"Invalid type: {series_type_filter}. Valid: {', '.join(sorted(VALID_SERIES_TYPES))}"
        }), 400

    try:
        # Get all series from directory
        series_list = series_service.get_series_for_directory(PHOTOS_DIR)

        # Apply type filter if specified
        if series_type_filter:
            series_list = [s for s in series_list if s.series_type == series_type_filter]

        # Calculate pagination
        total = len(series_list)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_series = series_list[start_idx:end_idx]

        # Convert to JSON-serializable format
        series_data = []
        for series in paginated_series:
            # Convert paths to relative strings
            photos_relative = [
                str(p.relative_to(PHOTOS_DIR)) if p.is_relative_to(PHOTOS_DIR) else p.name
                for p in series.photos
            ]
            cover_relative = (
                str(series.cover_photo.relative_to(PHOTOS_DIR))
                if series.cover_photo.is_relative_to(PHOTOS_DIR)
                else series.cover_photo.name
            )

            series_data.append({
                "series_id": series.series_id,
                "series_type": series.series_type,
                "base_name": series.base_name,
                "count": series.count,
                "cover_photo": cover_relative,
                "photos": photos_relative,
            })

        return jsonify({
            "series": series_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "has_next": end_idx < total,
                "has_previous": page > 1,
            }
        })

    except Exception as e:
        logger.error(f"Error listing series: {e}", exc_info=True)
        return jsonify({"error": "Failed to list series"}), 500


@gallery_bp.route("/series/<series_id>", methods=["GET"])
def get_series(series_id):
    """
    Get details for a specific photo series.

    Path Parameters:
        series_id: Series identifier (e.g., "hdr_moth_2024_01_15__10_00_00")

    Returns:
        JSON response with series details including all photo paths.

    Example:
        GET /series/hdr_moth_2024_01_15__10_00_00

    Status Codes:
        200: Success
        404: Series not found
        503: Series service unavailable
    """
    series_service = current_app.config.get('SERIES_SERVICE')

    if not series_service:
        return jsonify({"error": "Series service not available"}), 503

    try:
        # First ensure directory is scanned
        series_service.get_series_for_directory(PHOTOS_DIR)

        # Get series by ID
        series = series_service.get_series_by_id(series_id)

        if not series:
            return jsonify({"error": "Series not found", "series_id": series_id}), 404

        # Convert paths to relative strings
        photos_relative = [
            str(p.relative_to(PHOTOS_DIR)) if p.is_relative_to(PHOTOS_DIR) else p.name
            for p in series.photos
        ]
        cover_relative = (
            str(series.cover_photo.relative_to(PHOTOS_DIR))
            if series.cover_photo.is_relative_to(PHOTOS_DIR)
            else series.cover_photo.name
        )

        return jsonify({
            "series_id": series.series_id,
            "series_type": series.series_type,
            "base_name": series.base_name,
            "count": series.count,
            "cover_photo": cover_relative,
            "photos": photos_relative,
        })

    except Exception as e:
        logger.error(f"Error getting series {series_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get series"}), 500


@gallery_bp.route("/series/stats", methods=["GET"])
def get_series_stats():
    """
    Get series cache statistics.

    Returns:
        JSON response with cache statistics.

    Status Codes:
        200: Success
        503: Series service unavailable
    """
    series_service = current_app.config.get('SERIES_SERVICE')

    if not series_service:
        return jsonify({"error": "Series service not available"}), 503

    try:
        stats = series_service.get_statistics()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting series stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get statistics"}), 500


@gallery_bp.route("/series/cache/invalidate", methods=["POST"])
def invalidate_series_cache():
    """
    Invalidate series cache (requires CSRF token).

    Request body (JSON, optional):
        directory (str): Specific directory to invalidate (optional)

    Returns:
        JSON response with success status.

    Status Codes:
        200: Success
        503: Series service unavailable
    """
    series_service = current_app.config.get('SERIES_SERVICE')

    if not series_service:
        return jsonify({"error": "Series service not available"}), 503

    try:
        data = request.get_json() or {}
        directory = data.get('directory')

        if directory:
            # Validate path security
            dir_path = validate_photo_path(directory, PHOTOS_DIR)
            if dir_path is None:
                return jsonify({"error": "Invalid directory path"}), 400
            series_service.invalidate_cache(dir_path)
            message = f"Invalidated series cache for {directory}"
        else:
            series_service.invalidate_cache()
            message = "Invalidated entire series cache"

        return jsonify({"success": True, "message": message})

    except Exception as e:
        logger.error(f"Error invalidating series cache: {e}", exc_info=True)
        return jsonify({"error": "Failed to invalidate cache"}), 500


# ============================================================================
# Photo Locations Endpoint (Issue #113 - Subtask 2)
# ============================================================================

@gallery_bp.route("/locations", methods=["GET"])
@limiter.limit("60 per minute")
def get_photo_locations():
    """
    Get photos with GPS coordinates for map display.

    Query Parameters:
        limit (int): Maximum photos to return (1-10000, default: 1000)

    Returns:
        JSON response with:
        - locations: List of photos with GPS data
        - total_with_gps: Count of photos with GPS
        - total_without_gps: Count of photos without GPS

    Example:
        GET /locations?limit=100

    Status Codes:
        200: Success
        400: Invalid limit parameter
        500: Internal server error
    """
    try:
        # Parse and validate limit parameter
        limit_str = request.args.get('limit')
        if limit_str is not None:
            try:
                limit = int(limit_str)
            except ValueError:
                return jsonify({"error": "Limit parameter must be a valid integer"}), 400
            if limit <= 0:
                return jsonify({"error": "Limit must be greater than 0"}), 400
            if limit > 10000:
                return jsonify({"error": "Limit must be 10000 or less"}), 400
        else:
            limit = 1000

        # Use LocationsService (cached, efficient)
        result = _locations_service.get_locations(PHOTOS_DIR, limit=limit)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting photo locations: {e}", exc_info=True)
        return jsonify({"error": "Failed to get photo locations"}), 500


@gallery_bp.route("/locations/cache/invalidate", methods=["POST"])
def invalidate_locations_cache():
    """
    Invalidate the locations cache (requires CSRF token).

    Request body (JSON, optional):
        directory (str): Specific directory to invalidate (optional)

    Returns:
        JSON response with success status.

    Status Codes:
        200: Success
        400: Invalid directory path
    """
    try:
        data = request.get_json() or {}
        directory = data.get('directory')

        if directory:
            # Validate path security
            dir_path = validate_photo_path(directory, PHOTOS_DIR)
            if dir_path is None:
                return jsonify({"error": "Invalid directory path"}), 400
            _locations_service.invalidate_cache(dir_path)
            message = f"Invalidated locations cache for {directory}"
        else:
            _locations_service.invalidate_cache()
            message = "Invalidated entire locations cache"

        return jsonify({"status": "ok", "message": message})

    except Exception as e:
        logger.error(f"Error invalidating locations cache: {e}", exc_info=True)
        return jsonify({"error": "Failed to invalidate cache"}), 500


@gallery_bp.route("/locations/stats", methods=["GET"])
def get_locations_stats():
    """
    Get locations cache statistics.

    Returns:
        JSON response with cache statistics including:
        - cache_entries: Number of cached directory/limit combinations
        - cache_hits: Total cache hit count
        - cache_misses: Total cache miss count
        - total_locations: Total locations across all cached entries

    Status Codes:
        200: Success
    """
    try:
        stats = _locations_service.get_statistics()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting locations stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get statistics"}), 500


# ============================================================================
# Clustering Endpoints (Issue #115 - Subtask 3)
# ============================================================================

@gallery_bp.route("/locations/clustered", methods=["GET"])
@limiter.limit("60 per minute")
def get_clustered_locations():
    """
    Get clustered photo locations for map display.

    Query Parameters:
        radius (int): Clustering radius in meters (default: 100)
        min_size (int): Minimum photos per cluster (default: 2)
        enabled (bool): Enable clustering (default: true)

    Returns:
        JSON response with:
        - clusters: List of photo clusters
        - unclustered: Photos not in any cluster
        - metadata: Clustering metadata (total_photos, total_clusters, etc.)

    Example:
        GET /locations/clustered?radius=100&min_size=2&enabled=true

    Status Codes:
        200: Success
        400: Invalid parameters
        503: Clustering service unavailable
        500: Internal server error
    """
    # Get clustering service from app config
    clustering_service = current_app.config.get('CLUSTERING_SERVICE')

    if not clustering_service:
        return jsonify({"error": "Clustering service not available"}), 503

    try:
        # Parse query parameters
        radius_str = request.args.get('radius')
        min_size_str = request.args.get('min_size')
        enabled_str = request.args.get('enabled', 'true').lower()

        # Parse and validate radius
        if radius_str is not None:
            try:
                radius = int(radius_str)
            except ValueError:
                return jsonify({"error": "Radius parameter must be a valid integer"}), 400

            if radius < 0:
                return jsonify({"error": "Radius must be non-negative"}), 400
        else:
            radius = None  # Use service default

        # Parse and validate min_size
        if min_size_str is not None:
            try:
                min_size = int(min_size_str)
            except ValueError:
                return jsonify({"error": "min_size parameter must be a valid integer"}), 400

            if min_size < 0:
                return jsonify({"error": "min_size must be non-negative"}), 400
        else:
            min_size = None  # Use service default

        # Parse enabled flag
        clustering_enabled = enabled_str in ('true', '1', 'yes')

        # If clustering disabled, return all photos as unclustered
        if not clustering_enabled:
            # Get locations without clustering
            locations_result = _locations_service.get_locations(PHOTOS_DIR, limit=10000)
            locations = locations_result.get('locations', [])

            # Convert to PhotoLocation-like format
            unclustered = []
            for loc in locations:
                unclustered.append({
                    'path': loc['path'],
                    'lat': loc['latitude'],
                    'lon': loc['longitude'],
                    'timestamp': loc.get('timestamp')
                })

            return jsonify({
                'clusters': [],
                'unclustered': unclustered,
                'metadata': {
                    'total_photos': len(unclustered),
                    'total_clusters': 0,
                    'clustering_enabled': False,
                    'radius_m': radius or 100,
                    'processing_time_ms': 0.0,
                    'partial_result': False,
                    'warning': None
                }
            })

        # Perform clustering
        result = clustering_service.get_clustered_locations(
            directory=PHOTOS_DIR,
            radius_m=radius,
            min_cluster_size=min_size
        )

        # Convert ClusteringResult to JSON-serializable format
        clusters_data = []
        for cluster in result.clusters:
            # Convert photos to dict format
            photos_data = []
            for photo in cluster.photos:
                photos_data.append({
                    'path': photo.path,
                    'lat': photo.lat,
                    'lon': photo.lon,
                    'timestamp': photo.timestamp,
                    'tags': photo.tags  # Issue #117: Include tags
                })

            # Build cluster object
            cluster_data = {
                'cluster_id': cluster.cluster_id,
                'center': {
                    'lat': cluster.center_lat,
                    'lon': cluster.center_lon
                },
                'count': cluster.count,
                'photos': photos_data,
                'date_range': {
                    'earliest': cluster.date_range[0],
                    'latest': cluster.date_range[1]
                },
                'radius_m': cluster.radius_m
            }
            clusters_data.append(cluster_data)

        # Convert unclustered photos to dict format
        unclustered_data = []
        for photo in result.unclustered:
            unclustered_data.append({
                'path': photo.path,
                'lat': photo.lat,
                'lon': photo.lon,
                'timestamp': photo.timestamp,
                'tags': photo.tags  # Issue #117: Include tags
            })

        # Build response
        response_data = {
            'clusters': clusters_data,
            'unclustered': unclustered_data,
            'metadata': {
                'total_photos': result.total_photos,
                'total_clusters': result.total_clusters,
                'clustering_enabled': True,
                'radius_m': result.radius_m,
                'processing_time_ms': result.processing_time_ms,
                'partial_result': result.partial_result,
                'warning': result.warning
            }
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting clustered locations: {e}", exc_info=True)
        return jsonify({"error": "Failed to get clustered locations"}), 500


@gallery_bp.route("/locations/clustered/stats", methods=["GET"])
def get_clustered_locations_stats():
    """
    Get clustering cache statistics.

    Returns:
        JSON response with cache statistics including:
        - cache_entries: Number of cached configurations
        - cache_hits: Total cache hit count
        - cache_misses: Total cache miss count
        - total_clustering_time_ms: Total time spent clustering

    Status Codes:
        200: Success
        503: Clustering service unavailable
    """
    clustering_service = current_app.config.get('CLUSTERING_SERVICE')

    if not clustering_service:
        return jsonify({"error": "Clustering service not available"}), 503

    try:
        stats = clustering_service.get_statistics()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting clustering stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get statistics"}), 500


@gallery_bp.route("/locations/clustered/cache/invalidate", methods=["POST"])
def invalidate_clustered_locations_cache():
    """
    Invalidate clustering cache (requires CSRF token).

    Request body (JSON, optional):
        directory (str): Specific directory to invalidate (optional)

    Returns:
        JSON response with success status.

    Status Codes:
        200: Success
        400: CSRF token missing or invalid
        503: Clustering service unavailable
    """
    clustering_service = current_app.config.get('CLUSTERING_SERVICE')

    if not clustering_service:
        return jsonify({"error": "Clustering service not available"}), 503

    try:
        # Handle missing or empty JSON body gracefully
        data = {}
        if request.is_json:
            data = request.get_json(silent=True) or {}
        directory = data.get('directory')

        if directory:
            # Validate path security
            dir_path = validate_photo_path(directory, PHOTOS_DIR)
            if dir_path is None:
                return jsonify({"error": "Invalid directory path"}), 400
            clustering_service.invalidate_cache(dir_path)
            message = f"Invalidated clustering cache for {directory}"
        else:
            clustering_service.invalidate_cache()
            message = "Invalidated entire clustering cache"

        return jsonify({"success": True, "message": message})

    except Exception as e:
        logger.error(f"Error invalidating clustering cache: {e}", exc_info=True)
        return jsonify({"error": "Failed to invalidate cache"}), 500
