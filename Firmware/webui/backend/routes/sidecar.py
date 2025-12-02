"""
Sidecar Metadata CRUD API Endpoints (Issue #107 - Phase 1.2-1.4, Phase 2, Phase 3)

Provides REST API for managing photo sidecar metadata (tags, species, notes).
Supports CRUD operations, pagination, bulk updates, and aggregation.

Blueprint: sidecar_bp
URL Prefix: /api/sidecar

Endpoints:
- GET    /photos/<filename>          - Get sidecar metadata
- PATCH  /photos/<filename>          - Update sidecar metadata
- DELETE /photos/<filename>          - Delete sidecar
- GET    /photos                     - List all metadata (paginated)
- POST   /bulk                       - Bulk update metadata (Phase 2)
- GET    /tags                       - List all unique tags with counts
- GET    /species                    - List all unique species with counts

Security:
- CSRF protection (Flask-WTF) OR API key authentication (X-API-Key header)
- Path traversal protection via validate_photo_path()
- Input validation (tag length, notes length, etc.)
- Sanitized error messages (no stack trace exposure)
- Rate limiting (10/minute suggested for bulk endpoint - to be enforced later)

Authentication Modes:
1. CSRF token (web UI requests): X-CSRFToken header
2. API key (programmatic access): X-API-Key header
"""

import json
import logging
import threading
import time
from collections import Counter

from flask import Blueprint, current_app, jsonify, request

from mothbox_paths import PHOTOS_DIR
from webui.backend.constants import SIDECAR_PATTERNS
from webui.backend.lib.sidecar_metadata import (
    MAX_BULK_FILES,
    MAX_NOTES_LENGTH,
    MAX_PAGINATION_LIMIT,
    MAX_TAG_LENGTH,
)
from webui.backend.security_utils import sanitize_error_message, validate_photo_path

logger = logging.getLogger(__name__)

# Blueprint setup
sidecar_bp = Blueprint("sidecar", __name__)

# ============================================================================
# Aggregation Cache (Issue #107 follow-up - Performance)
# ============================================================================
# Tags and species aggregation scans all sidecar files. This cache
# prevents repeated O(n) scans on every request.
#
# Uses RLock to allow reentrant locking and a "building" flag to prevent
# thundering herd when cache expires under concurrent load.

_tags_cache = None
_tags_cache_time = 0
_tags_cache_building = False
_species_cache = None
_species_cache_time = 0
_species_cache_building = False
_cache_lock = threading.RLock()  # Reentrant lock for nested calls
_DEFAULT_AGGREGATION_CACHE_TTL = 300  # 5 minutes


def _get_cache_ttl() -> int:
    """Get aggregation cache TTL from app config or use default."""
    return current_app.config.get('SIDECAR_AGGREGATION_CACHE_TTL', _DEFAULT_AGGREGATION_CACHE_TTL)


def invalidate_aggregation_cache():
    """
    Invalidate tags and species aggregation cache.

    Called after metadata updates (PATCH, DELETE, bulk) to ensure
    subsequent aggregation requests return fresh data.
    """
    global _tags_cache, _species_cache, _tags_cache_time, _species_cache_time
    global _tags_cache_building, _species_cache_building
    with _cache_lock:
        _tags_cache = None
        _species_cache = None
        _tags_cache_time = 0
        _species_cache_time = 0
        _tags_cache_building = False
        _species_cache_building = False
        logger.debug("Aggregation cache invalidated")


# ============================================================================
# Helper Functions
# ============================================================================

def check_api_key() -> bool:
    """
    Check if request has valid API key in X-API-Key header.

    Note: This function is defined for future use. API key authentication
    is not yet implemented - see issue #175 for tracking.

    Returns:
        True if valid API key provided, False otherwise
    """
    api_key = request.headers.get('X-API-Key')
    expected_key = current_app.config.get('API_KEY')
    return bool(api_key and expected_key and api_key == expected_key)


def validate_metadata_input(data: dict) -> tuple[bool, str | None]:
    """
    Validate metadata input data.

    Args:
        data: Metadata update dictionary

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    # Validate tags
    if 'tags' in data:
        if not isinstance(data['tags'], list):
            return False, "Tags must be an array"

        for tag in data['tags']:
            if not isinstance(tag, str):
                return False, "Each tag must be a string"
            if len(tag) > MAX_TAG_LENGTH:
                return False, f"Tag exceeds maximum length ({MAX_TAG_LENGTH} characters): {tag}"

    # Validate notes
    if 'notes' in data and data['notes'] is not None:
        if not isinstance(data['notes'], str):
            return False, "Notes must be a string"
        if len(data['notes']) > MAX_NOTES_LENGTH:
            return False, f"Notes exceeds maximum length ({MAX_NOTES_LENGTH} characters)"

    return True, None


# ============================================================================
# GET /photos/<filename> - Get sidecar metadata
# ============================================================================

@sidecar_bp.route("/photos/<path:filename>", methods=["GET"])
def get_photo_metadata(filename: str):
    """
    Get sidecar metadata for a photo.

    Returns existing metadata from sidecar if exists, or empty metadata
    structure if no sidecar. Returns 404 if photo doesn't exist.

    Args:
        filename: Photo filename (relative to PHOTOS_DIR)

    Returns:
        JSON response with:
        - version: Schema version
        - photo_filename: Photo filename
        - created_at: Creation timestamp (or null)
        - modified_at: Modification timestamp (or null)
        - tags: List of tags (or empty list)
        - species: Species identification (or null)
        - notes: User notes (or null)
        - custom: Custom metadata dict (or empty dict)
        - modified_by: User identifier (or null)

    Status Codes:
        200: Success (returns metadata or empty structure)
        403: Invalid path (path traversal attempt)
        404: Photo not found
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/sidecar/photos/photo.jpg

        Response (with sidecar):
        {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": ["moth", "night"],
            "species": "Actias luna",
            "notes": "Beautiful specimen",
            "custom": {},
            "modified_by": null
        }

        Response (without sidecar):
        {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": null,
            "modified_at": null,
            "tags": [],
            "species": null,
            "notes": null,
            "custom": {},
            "modified_by": null
        }
    """
    try:
        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(filename, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if photo exists
        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        # Get metadata from service
        metadata = service.get_metadata(str(full_path))

        # If no sidecar, return empty structure
        if metadata is None:
            return jsonify({
                "version": "1.0",
                "photo_filename": full_path.name,
                "created_at": None,
                "modified_at": None,
                "tags": [],
                "species": None,
                "notes": None,
                "custom": {},
                "modified_by": None
            }), 200

        # Return existing metadata
        return jsonify(metadata.to_dict()), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# PATCH /photos/<filename> - Update sidecar metadata
# ============================================================================

@sidecar_bp.route("/photos/<path:filename>", methods=["PATCH"])
def update_photo_metadata(filename: str):
    """
    Update sidecar metadata for a photo.

    Updates existing sidecar or creates new one if doesn't exist.
    Supports append or replace mode for tags (default: append).

    Requires CSRF token OR valid API key in X-API-Key header.

    Args:
        filename: Photo filename (relative to PHOTOS_DIR)

    Request Body (JSON):
        {
            "tags": ["moth", "night"],        // optional
            "tag_mode": "append",              // optional: "append" or "replace" (default: "append")
            "species": "Actias luna",          // optional
            "notes": "Beautiful specimen",     // optional
            "custom": {"key": "value"},        // optional
            "modified_by": "user123"           // optional
        }

    Returns:
        JSON response with updated metadata

    Status Codes:
        200: Success
        400: Invalid input (malformed JSON, validation error)
        403: Invalid path or authentication failure
        404: Photo not found
        500: Internal server error
        503: Service unavailable

    Example:
        PATCH /api/sidecar/photos/photo.jpg
        Content-Type: application/json
        X-CSRFToken: <token>

        {"species": "Actias luna", "notes": "Updated"}

        Response:
        {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "tags": ["moth"],
            "species": "Actias luna",
            "notes": "Updated",
            ...
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.
        # API key auth not yet implemented - see issue #175 for tracking.

        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(filename, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if photo exists
        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        # Validate request body
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({"error": "Invalid JSON in request body"}), 400

        if data is None:
            data = {}

        # Validate input
        is_valid, error_msg = validate_metadata_input(data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Handle tag_mode (append vs replace)
        tag_mode = data.pop('tag_mode', 'append')  # Default to append

        if tag_mode not in ['append', 'replace']:
            return jsonify({"error": "tag_mode must be 'append' or 'replace'"}), 400

        # If append mode and tags provided, merge with existing tags
        if tag_mode == 'append' and 'tags' in data:
            existing_metadata = service.get_metadata(str(full_path))
            if existing_metadata:
                # Combine existing and new tags (preserve order, remove duplicates)
                new_tags = data['tags']
                # Start with existing tags
                combined_tags = existing_metadata.tags.copy() if hasattr(existing_metadata, 'tags') and existing_metadata.tags else []
                # Add new tags that aren't already present
                for tag in new_tags:
                    if tag not in combined_tags:
                        combined_tags.append(tag)
                data['tags'] = combined_tags

        # Update metadata via service
        updated_metadata = service.update_metadata(str(full_path), data)

        if updated_metadata is None:
            return jsonify({"error": "Failed to update metadata"}), 500

        # Invalidate aggregation cache since tags/species may have changed
        invalidate_aggregation_cache()

        return jsonify(updated_metadata.to_dict()), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to update metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# DELETE /photos/<filename> - Delete sidecar
# ============================================================================

@sidecar_bp.route("/photos/<path:filename>", methods=["DELETE"])
def delete_photo_metadata(filename: str):
    """
    Delete sidecar metadata for a photo.

    Requires CSRF token OR valid API key in X-API-Key header.

    Args:
        filename: Photo filename (relative to PHOTOS_DIR)

    Returns:
        JSON response with success status

    Status Codes:
        200: Success
        403: Invalid path or authentication failure
        404: Sidecar not found
        500: Internal server error
        503: Service unavailable

    Example:
        DELETE /api/sidecar/photos/photo.jpg
        X-CSRFToken: <token>

        Response:
        {"success": true}
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.
        # API key auth not yet implemented - see issue #175 for tracking.

        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(filename, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if sidecar exists
        metadata = service.get_metadata(str(full_path))
        if metadata is None:
            return jsonify({"error": "Metadata not found"}), 404

        # Delete via service (handles cache invalidation and file deletion)
        delete_success = service.delete_metadata(str(full_path))
        if not delete_success:
            return jsonify({"error": "Failed to delete metadata"}), 500

        # Invalidate aggregation cache since tags/species may have changed
        invalidate_aggregation_cache()

        return jsonify({"success": True}), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to delete metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /photos - List all metadata (paginated)
# ============================================================================

@sidecar_bp.route("/photos", methods=["GET"])
def list_all_metadata():
    """
    List all sidecar metadata with pagination.

    Query Parameters:
        page (int): Page number (1-indexed, default: 1)
        per_page (int): Items per page (1-200, default: 50, max: 200)

    Returns:
        JSON response with:
        - items: List of metadata dictionaries
        - total: Total number of photos with sidecars
        - pagination: Pagination metadata

    Status Codes:
        200: Success
        400: Invalid pagination parameters
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/sidecar/photos?page=1&per_page=50

        Response:
        {
            "items": [
                {"photo_filename": "photo1.jpg", "tags": ["moth"], ...},
                {"photo_filename": "photo2.jpg", "tags": ["butterfly"], ...}
            ],
            "total": 2,
            "pagination": {
                "page": 1,
                "per_page": 50,
                "has_next": false,
                "has_previous": false
            }
        }
    """
    try:
        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Parse pagination parameters
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid pagination parameter"}), 400

        # Validate pagination
        if page < 1:
            return jsonify({"error": "Page must be >= 1"}), 400

        if per_page < 1:
            return jsonify({"error": "per_page must be >= 1"}), 400

        # Cap per_page at maximum
        if per_page > MAX_PAGINATION_LIMIT:
            per_page = MAX_PAGINATION_LIMIT

        # Calculate offset
        offset = (page - 1) * per_page

        # Get metadata from service
        result = service.list_metadata_for_directory(
            directory=PHOTOS_DIR,
            limit=per_page,
            offset=offset
        )

        # Build pagination metadata
        total = result['total']
        has_next = result['has_next']
        has_previous = page > 1

        return jsonify({
            "items": result['items'],
            "total": total,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to list metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# POST /bulk - Bulk update metadata (Phase 2)
# ============================================================================

@sidecar_bp.route("/bulk", methods=["POST"])
def bulk_update_metadata():
    """
    Bulk update metadata for multiple photos.

    Processes each file independently, allowing partial success.
    Failed files are reported but do not stop processing of other files.

    Requires CSRF token OR valid API key in X-API-Key header.

    Request Body (JSON):
        {
            "filenames": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
            "updates": {
                "tags": ["moth", "night"],
                "species": "Actias luna"
            },
            "mode": "append"  // or "replace" - default is "append"
        }

    Mode behavior:
        - "append" (default): Merges tags with existing tags, replaces other fields
        - "replace": Replaces all fields including tags

    Returns:
        JSON response with:
        - success: List of successfully updated filenames
        - failed: List of failed filenames
        - errors: Dict mapping failed filenames to error messages
        - total: Total number of files requested
        - successful: Count of successful updates
        - failed_count: Count of failed updates

    Status Codes:
        200: Success (even with partial failures - check response for details)
        400: Invalid request (missing fields, validation error, too many files)
        500: Internal server error
        503: Service unavailable

    Validation:
        - filenames: required, non-empty array, max 100 items
        - updates: required, non-empty object
        - mode: optional, "append" or "replace", defaults to "append"

    Rate Limiting:
        - Suggested: 10 requests/minute (to be enforced later)

    Example:
        POST /api/sidecar/bulk
        Content-Type: application/json
        X-CSRFToken: <token>

        {
            "filenames": ["photo1.jpg", "photo2.jpg"],
            "updates": {"species": "Actias luna"},
            "mode": "append"
        }

        Response:
        {
            "success": ["photo1.jpg"],
            "failed": ["photo2.jpg"],
            "errors": {
                "photo2.jpg": "Photo not found"
            },
            "total": 2,
            "successful": 1,
            "failed_count": 1
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.
        # API key auth not yet implemented - see issue #175 for tracking.

        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Validate request body
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({"error": "Invalid JSON in request body"}), 400

        if data is None:
            return jsonify({"error": "Request body is required"}), 400

        # Validate required fields
        if 'filenames' not in data:
            return jsonify({"error": "Field 'filenames' is required"}), 400

        if 'updates' not in data:
            return jsonify({"error": "Field 'updates' is required"}), 400

        filenames = data['filenames']
        updates = data['updates']
        mode = data.get('mode', 'append')  # Default to append

        # Validate filenames
        if not isinstance(filenames, list):
            return jsonify({"error": "Field 'filenames' must be an array"}), 400

        if len(filenames) == 0:
            return jsonify({"error": "Field 'filenames' cannot be empty"}), 400

        if len(filenames) > MAX_BULK_FILES:
            return jsonify({"error": f"Maximum {MAX_BULK_FILES} files per request"}), 400

        # Validate updates
        if not isinstance(updates, dict):
            return jsonify({"error": "Field 'updates' must be an object"}), 400

        if len(updates) == 0:
            return jsonify({"error": "Field 'updates' cannot be empty"}), 400

        # Validate mode
        if mode not in ['append', 'replace']:
            return jsonify({"error": "Field 'mode' must be 'append' or 'replace'"}), 400

        # Validate updates content
        is_valid, error_msg = validate_metadata_input(updates)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Process each file independently
        success_list = []
        failed_list = []
        error_dict = {}

        for filename in filenames:
            try:
                # Path traversal protection
                full_path = validate_photo_path(filename, PHOTOS_DIR)
                if full_path is None:
                    failed_list.append(filename)
                    error_dict[filename] = "Invalid path: Access denied"
                    continue

                # Check if photo exists
                if not full_path.exists():
                    failed_list.append(filename)
                    error_dict[filename] = "Photo not found"
                    continue

                # Prepare updates for this file
                file_updates = updates.copy()

                # Handle tag mode (append vs replace)
                if mode == 'append' and 'tags' in file_updates:
                    existing_metadata = service.get_metadata(str(full_path))
                    if existing_metadata:
                        # Merge tags
                        existing_tags = existing_metadata.tags if hasattr(existing_metadata, 'tags') and existing_metadata.tags else []
                        new_tags = file_updates['tags']
                        # Combine existing and new tags (preserve order, remove duplicates)
                        combined_tags = existing_tags.copy()
                        for tag in new_tags:
                            if tag not in combined_tags:
                                combined_tags.append(tag)
                        file_updates['tags'] = combined_tags

                # Update metadata via service
                updated_metadata = service.update_metadata(str(full_path), file_updates)

                if updated_metadata is None:
                    failed_list.append(filename)
                    error_dict[filename] = "Failed to update metadata"
                    continue

                # Success
                success_list.append(filename)

            except Exception as e:
                # Log error but continue processing other files
                logger.warning(f"Error updating metadata for {filename}: {e}")
                failed_list.append(filename)
                error_dict[filename] = "Update failed"

        # Invalidate aggregation cache if any updates succeeded
        if success_list:
            invalidate_aggregation_cache()

        # Build response
        return jsonify({
            "success": success_list,
            "failed": failed_list,
            "errors": error_dict,
            "total": len(filenames),
            "successful": len(success_list),
            "failed_count": len(failed_list)
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to bulk update metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /tags - List all unique tags with counts (Phase 3)
# ============================================================================

@sidecar_bp.route("/tags", methods=["GET"])
def get_all_tags():
    """
    List all unique tags with usage counts.

    Aggregates tags across all sidecar files in PHOTOS_DIR.

    Query Parameters:
        page (int): Page number (1-indexed, default: 1)
        per_page (int): Items per page (1-200, default: 50, max: 200)
        sort (str): Sort by "count" (default) or "name"
        order (str): Sort order "desc" (default) or "asc"

    Returns:
        JSON response with:
        - tags: List of {name, count} dictionaries
        - total: Total number of unique tags
        - pagination: Pagination metadata

    Status Codes:
        200: Success
        400: Invalid pagination parameters
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/sidecar/tags?page=1&per_page=50&sort=count&order=desc

        Response:
        {
            "tags": [
                {"name": "moth", "count": 45},
                {"name": "night", "count": 32},
                {"name": "luna", "count": 12}
            ],
            "total": 3,
            "pagination": {
                "page": 1,
                "per_page": 50,
                "has_next": false,
                "has_previous": false
            }
        }
    """
    try:
        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Parse query parameters
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            sort_by = request.args.get('sort', 'count', type=str)
            order = request.args.get('order', 'desc', type=str)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid query parameter"}), 400

        # Validate pagination
        if page < 1:
            return jsonify({"error": "Page must be >= 1"}), 400

        if per_page < 1:
            return jsonify({"error": "per_page must be >= 1"}), 400

        # Cap per_page at maximum
        if per_page > MAX_PAGINATION_LIMIT:
            per_page = MAX_PAGINATION_LIMIT

        # Validate sort parameters
        if sort_by not in ['count', 'name']:
            return jsonify({"error": "sort must be 'count' or 'name'"}), 400

        if order not in ['asc', 'desc']:
            return jsonify({"error": "order must be 'asc' or 'desc'"}), 400

        # Use cached aggregation data if available and fresh
        # Uses building flag to prevent thundering herd on cache expiry
        global _tags_cache, _tags_cache_time, _tags_cache_building
        all_tags = None

        with _cache_lock:
            cache_age = time.time() - _tags_cache_time
            if _tags_cache is not None and cache_age < _get_cache_ttl():
                all_tags = _tags_cache.copy()
                logger.debug(f"Tags cache hit (age: {cache_age:.1f}s)")
            elif _tags_cache_building:
                # Another thread is building, return stale data if available
                if _tags_cache is not None:
                    all_tags = _tags_cache.copy()
                    logger.debug("Tags cache building by another thread, using stale data")
            else:
                # Mark as building to prevent thundering herd
                _tags_cache_building = True

        # Build cache outside the lock if needed
        if all_tags is None:
            try:
                # Aggregate tags from all sidecar files
                tag_counter = Counter()

                for pattern in SIDECAR_PATTERNS:
                    for sidecar_path in PHOTOS_DIR.rglob(pattern):
                        try:
                            sidecar_data = json.loads(sidecar_path.read_text())
                            for tag in sidecar_data.get('tags', []):
                                tag_counter[tag] += 1
                        except (OSError, json.JSONDecodeError, KeyError) as e:
                            logger.debug(f"Skipping invalid sidecar {sidecar_path}: {e}")
                            continue

                # Convert to list of {name, count} dicts
                all_tags = [{"name": tag, "count": count} for tag, count in tag_counter.items()]

                # Cache the result
                with _cache_lock:
                    _tags_cache = all_tags.copy()
                    _tags_cache_time = time.time()
                    _tags_cache_building = False
                logger.debug(f"Tags cache miss - scanned {len(tag_counter)} unique tags")
            except Exception:
                # Reset building flag on error
                with _cache_lock:
                    _tags_cache_building = False
                raise

        # Sort
        if sort_by == 'count':
            all_tags.sort(key=lambda x: x['count'], reverse=(order == 'desc'))
        else:  # sort by name
            all_tags.sort(key=lambda x: x['name'], reverse=(order == 'desc'))

        # Paginate
        total = len(all_tags)
        offset = (page - 1) * per_page
        tags_page = all_tags[offset:offset + per_page]

        has_next = (offset + per_page) < total
        has_previous = page > 1

        return jsonify({
            "tags": tags_page,
            "total": total,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get tags")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /species - List all unique species with counts (Phase 3)
# ============================================================================

@sidecar_bp.route("/species", methods=["GET"])
def get_all_species():
    """
    List all unique species with usage counts.

    Aggregates species identifications across all sidecar files in PHOTOS_DIR.
    Excludes photos with no species set (null values).

    Query Parameters:
        page (int): Page number (1-indexed, default: 1)
        per_page (int): Items per page (1-200, default: 50, max: 200)
        sort (str): Sort by "count" (default) or "name"
        order (str): Sort order "desc" (default) or "asc"

    Returns:
        JSON response with:
        - species: List of {name, count} dictionaries
        - total: Total number of unique species
        - pagination: Pagination metadata

    Status Codes:
        200: Success
        400: Invalid pagination parameters
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/sidecar/species?page=1&per_page=50&sort=count&order=desc

        Response:
        {
            "species": [
                {"name": "Actias luna", "count": 12},
                {"name": "Antheraea polyphemus", "count": 8}
            ],
            "total": 2,
            "pagination": {
                "page": 1,
                "per_page": 50,
                "has_next": false,
                "has_previous": false
            }
        }
    """
    try:
        # Get sidecar service
        service = current_app.config.get('SIDECAR_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Parse query parameters
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            sort_by = request.args.get('sort', 'count', type=str)
            order = request.args.get('order', 'desc', type=str)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid query parameter"}), 400

        # Validate pagination
        if page < 1:
            return jsonify({"error": "Page must be >= 1"}), 400

        if per_page < 1:
            return jsonify({"error": "per_page must be >= 1"}), 400

        # Cap per_page at maximum
        if per_page > MAX_PAGINATION_LIMIT:
            per_page = MAX_PAGINATION_LIMIT

        # Validate sort parameters
        if sort_by not in ['count', 'name']:
            return jsonify({"error": "sort must be 'count' or 'name'"}), 400

        if order not in ['asc', 'desc']:
            return jsonify({"error": "order must be 'asc' or 'desc'"}), 400

        # Use cached aggregation data if available and fresh
        # Uses building flag to prevent thundering herd on cache expiry
        global _species_cache, _species_cache_time, _species_cache_building
        all_species = None

        with _cache_lock:
            cache_age = time.time() - _species_cache_time
            if _species_cache is not None and cache_age < _get_cache_ttl():
                all_species = _species_cache.copy()
                logger.debug(f"Species cache hit (age: {cache_age:.1f}s)")
            elif _species_cache_building:
                # Another thread is building, return stale data if available
                if _species_cache is not None:
                    all_species = _species_cache.copy()
                    logger.debug("Species cache building by another thread, using stale data")
            else:
                # Mark as building to prevent thundering herd
                _species_cache_building = True

        # Build cache outside the lock if needed
        if all_species is None:
            try:
                # Aggregate species from all sidecar files
                species_counter = Counter()

                for pattern in SIDECAR_PATTERNS:
                    for sidecar_path in PHOTOS_DIR.rglob(pattern):
                        try:
                            sidecar_data = json.loads(sidecar_path.read_text())
                            species_name = sidecar_data.get('species')

                            # Only count non-null species
                            if species_name is not None:
                                species_counter[species_name] += 1
                        except (OSError, json.JSONDecodeError, KeyError) as e:
                            logger.debug(f"Skipping invalid sidecar {sidecar_path}: {e}")
                            continue

                # Convert to list of {name, count} dicts
                all_species = [{"name": species, "count": count} for species, count in species_counter.items()]

                # Cache the result
                with _cache_lock:
                    _species_cache = all_species.copy()
                    _species_cache_time = time.time()
                    _species_cache_building = False
                logger.debug(f"Species cache miss - scanned {len(species_counter)} unique species")
            except Exception:
                # Reset building flag on error
                with _cache_lock:
                    _species_cache_building = False
                raise

        # Sort
        if sort_by == 'count':
            all_species.sort(key=lambda x: x['count'], reverse=(order == 'desc'))
        else:  # sort by name
            all_species.sort(key=lambda x: x['name'], reverse=(order == 'desc'))

        # Paginate
        total = len(all_species)
        offset = (page - 1) * per_page
        species_page = all_species[offset:offset + per_page]

        has_next = (offset + per_page) < total
        has_previous = page > 1

        return jsonify({
            "species": species_page,
            "total": total,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get species")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# Module exports
# ============================================================================

__all__ = ['sidecar_bp']
