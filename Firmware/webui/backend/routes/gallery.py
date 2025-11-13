"""
Gallery routes with metadata endpoint and caching (Issue #100).

Provides photo gallery endpoints including metadata retrieval with
two-level LRU caching for performance optimization.

Endpoints:
- GET /api/gallery/photos/<photo_id>/metadata - Get photo metadata with caching
- DELETE /api/gallery/photos/<photo_id>/cache - Clear photo metadata cache
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
from typing import Optional
import time
import logging

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

# Import mothbox paths
import sys
from pathlib import Path as PathlibPath

sys.path.insert(0, str(PathlibPath(__file__).parent.parent.parent.parent))
from mothbox_paths import DATA_DIR, PHOTOS_DIR

# Add backend to path for services
backend_path = PathlibPath(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from services.metadata_cache import MetadataCache  # noqa: E402
from services.metadata_service import MetadataService  # noqa: E402

logger = logging.getLogger(__name__)

# Blueprint setup
gallery_bp = Blueprint("gallery", __name__, url_prefix="/api/gallery")

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
        GET /api/gallery/photos/2024-01-15/photo.jpg/metadata?categories=camera,location

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

    Requires CSRF token (DELETE is state-changing).

    Returns:
        JSON response with:
        - success (bool): True if successful
        - message (str): Status message
        - photo_id (str): Photo identifier

    Example:
        DELETE /api/gallery/photos/2024-01-15/photo.jpg/cache

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
def get_cache_statistics():
    """
    Get cache performance statistics.

    Returns:
        JSON response with cache statistics

    Example:
        GET /api/gallery/cache/statistics

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


# For testing: allow resetting the cache singleton
def _reset_cache():
    """Reset cache singleton (for testing only)"""
    global _metadata_cache
    _metadata_cache = None
