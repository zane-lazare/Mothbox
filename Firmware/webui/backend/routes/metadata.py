"""
Metadata API endpoints

Provides REST API for extracting comprehensive EXIF metadata from photos
and tag autocomplete functionality.

Endpoints:
- GET /api/metadata/photo/<path:photo_path>/metadata - Get metadata for single photo
- POST /api/metadata/batch/metadata - Get metadata for multiple photos (batch)
- GET /api/metadata/tags/autocomplete - Tag autocomplete with fuzzy matching

Security:
- Path traversal protection via validate_photo_path() with multiple security layers
- CSRF protection (Flask-WTF) applied automatically to all POST endpoints
- Input validation on photo paths and query parameters
- Sanitized error messages (no stack trace exposure)
"""

import logging

from flask import Blueprint, current_app, jsonify, request
from security_utils import sanitize_error_message, validate_photo_path
from services.metadata_service import MetadataService

from mothbox_paths import PHOTOS_DIR

logger = logging.getLogger(__name__)

metadata_bp = Blueprint("metadata", __name__)

# Initialize metadata service (stateless)
metadata_service = MetadataService()

# Constants for tag autocomplete
MAX_AUTOCOMPLETE_LIMIT = 50
DEFAULT_AUTOCOMPLETE_LIMIT = 10


@metadata_bp.route("/photo/<path:photo_path>/metadata", methods=["GET"])
def get_photo_metadata(photo_path: str):
    """
    Get comprehensive EXIF metadata for a single photo.

    Args:
        photo_path: Path to photo relative to PHOTOS_DIR

    Returns:
        JSON: Metadata dictionary with 5 categories:
              - camera: Hardware information
              - location: GPS coordinates and quality
              - capture: Photo settings
              - deployment: Mothbox information
              - file: File system metadata

    Example:
        GET /api/metadata/photo/mothbox_2024_10_15__14_30_00.jpg/metadata

        Response:
        {
            "camera": {"make": "Arducam", "model": "OwlSight 64MP", ...},
            "location": {"latitude": 37.7917, "longitude": -122.42, ...},
            "capture": {"timestamp": "2024-10-15T14:30:00", "iso": 400, ...},
            "deployment": {"mothbox_id": "mothbox", "firmware_version": "5.0", ...},
            "file": {"filename": "...", "size": 12345, ...}
        }
    """
    try:
        # Path traversal protection with multiple security layers
        full_path = validate_photo_path(photo_path, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 403

        # Check if photo exists
        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        # Extract metadata
        metadata = metadata_service.get_photo_metadata(full_path)

        # Check if metadata extraction failed
        if "error" in metadata:
            return jsonify({"error": "Failed to extract metadata"}), 500

        return jsonify(metadata), 200

    except (RuntimeError, OSError) as e:
        # Log full error, return sanitized message
        error_msg = sanitize_error_message(e, "File system error occurred")
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        # Log full error, return sanitized message
        error_msg = sanitize_error_message(e, "Internal server error")
        return jsonify({"error": error_msg}), 500


@metadata_bp.route("/batch/metadata", methods=["POST"])
def get_batch_metadata():
    """
    Get metadata for multiple photos in a single request.

    Batch processing is more efficient than making individual requests
    for each photo. Failed photos return error information without
    stopping the entire batch.

    Request Body:
        {
            "photo_paths": [
                "photo1.jpg",
                "2024/10/photo2.jpg",
                "photo3.jpg"
            ]
        }

    Returns:
        JSON: Array of metadata objects, one per photo
              Failed photos include 'error' key

    Example:
        POST /api/metadata/batch/metadata
        Content-Type: application/json

        {"photo_paths": ["photo1.jpg", "photo2.jpg"]}

        Response:
        {
            "results": [
                {"camera": {...}, "location": {...}, ...},
                {"error": "Photo not found", "file": {"path": "..."}}
            ],
            "total": 2,
            "successful": 1,
            "failed": 1
        }
    """
    try:
        # Validate request body
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({"error": "Invalid JSON in request body"}), 400

        if not data or "photo_paths" not in data:
            return jsonify({"error": "Missing 'photo_paths' in request body"}), 400

        photo_paths = data["photo_paths"]

        if not isinstance(photo_paths, list):
            return jsonify({"error": "'photo_paths' must be an array"}), 400

        if len(photo_paths) == 0:
            return jsonify({"results": [], "total": 0, "successful": 0, "failed": 0}), 200

        # Validate and resolve all paths with security checks
        resolved_paths = []

        for photo_path in photo_paths:
            # Path traversal protection with multiple security layers
            full_path = validate_photo_path(photo_path, PHOTOS_DIR)
            resolved_paths.append(full_path)

        # Extract metadata for all photos (batch processing)
        results = []
        for i, resolved_path in enumerate(resolved_paths):
            if resolved_path is None:
                # Path validation failed
                results.append({"error": "Invalid path", "file": {"path": photo_paths[i]}})
            else:
                metadata = metadata_service.get_photo_metadata(resolved_path)
                results.append(metadata)

        # Calculate statistics
        successful = sum(1 for r in results if "error" not in r)
        failed = len(results) - successful

        return jsonify(
            {"results": results, "total": len(results), "successful": successful, "failed": failed}
        ), 200

    except Exception as e:
        # Log full error, return sanitized message
        error_msg = sanitize_error_message(e, "Batch processing failed")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /tags/autocomplete - Tag autocomplete
# ============================================================================


@metadata_bp.route("/tags/autocomplete", methods=["GET"])
def get_tag_autocomplete():
    """
    Get tag autocomplete suggestions with fuzzy matching.

    Query Parameters:
        q (str): Search query (required)
        limit (int): Maximum number of suggestions (default: 10, max: 50)
        exclude_tags (str): Comma-separated list of tags to exclude from results

    Returns:
        JSON response with:
        - suggestions: List of suggestion dictionaries with tag, count, last_used, match_score
        - query: The search query
        - total: Number of suggestions returned

    Status Codes:
        200: Success
        400: Missing required parameter
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/metadata/tags/autocomplete?q=moth&limit=10

        Response:
        {
            "suggestions": [
                {
                    "tag": "luna_moth",
                    "count": 45,
                    "last_used": "2024-11-05T10:30:00Z",
                    "match_score": 0.95
                },
                {
                    "tag": "sphinx_moth",
                    "count": 23,
                    "last_used": "2024-11-01T08:00:00Z",
                    "match_score": 0.82
                }
            ],
            "query": "moth",
            "total": 2
        }
    """
    try:
        # Get autocomplete engine
        engine = current_app.config.get("TAG_AUTOCOMPLETE_ENGINE")
        if engine is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Get query parameter (required)
        query = request.args.get("q")
        if query is None:
            return jsonify({"error": "Missing required parameter: q"}), 400

        # Get limit parameter (optional, default: 10, max: 50)
        try:
            limit = request.args.get("limit", DEFAULT_AUTOCOMPLETE_LIMIT, type=int)
        except (ValueError, TypeError):
            # If conversion fails, use default
            limit = DEFAULT_AUTOCOMPLETE_LIMIT

        # Validate and cap limit
        if limit < 1:
            limit = DEFAULT_AUTOCOMPLETE_LIMIT
        if limit > MAX_AUTOCOMPLETE_LIMIT:
            limit = MAX_AUTOCOMPLETE_LIMIT

        # Get exclude_tags parameter (optional)
        exclude_tags_param = request.args.get("exclude_tags", "")
        excluded_tags = (
            {tag.strip().lower() for tag in exclude_tags_param.split(",") if tag.strip()}
            if exclude_tags_param
            else set()
        )

        # Search for suggestions
        suggestions = engine.search(query, limit=limit)

        # Filter out excluded tags
        if excluded_tags:
            suggestions = [s for s in suggestions if s.tag.lower() not in excluded_tags]

        # Format response
        formatted_suggestions = []
        for suggestion in suggestions:
            formatted_suggestions.append(
                {
                    "tag": suggestion.tag,
                    "count": suggestion.count,
                    "last_used": suggestion.last_used.isoformat() if suggestion.last_used else None,
                    "match_score": suggestion.match_score,
                }
            )

        return jsonify(
            {
                "suggestions": formatted_suggestions,
                "query": query,
                "total": len(formatted_suggestions),
            }
        ), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get tag suggestions")
        logger.error(f"Tag autocomplete error: {e}")
        return jsonify({"error": error_msg}), 500
