"""
Metadata API endpoints (Issue #99)

Provides REST API for extracting comprehensive EXIF metadata from photos.
Supports single photo and batch metadata extraction.

Endpoints:
- GET /api/metadata/photo/<path:photo_path>/metadata - Get metadata for single photo
- POST /api/metadata/batch/metadata - Get metadata for multiple photos (batch)

Security:
- Path traversal protection via validate_photo_path() with multiple security layers
- CSRF protection (Flask-WTF) applied automatically to all POST endpoints
- Input validation on photo paths
- Sanitized error messages (no stack trace exposure)
"""

from flask import Blueprint, jsonify, request
from security_utils import sanitize_error_message, validate_photo_path
from services.metadata_service import MetadataService

from mothbox_paths import PHOTOS_DIR

metadata_bp = Blueprint("metadata", __name__)

# Initialize metadata service (stateless)
metadata_service = MetadataService()


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
        if 'error' in metadata:
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

        if not data or 'photo_paths' not in data:
            return jsonify({"error": "Missing 'photo_paths' in request body"}), 400

        photo_paths = data['photo_paths']

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
                results.append({
                    "error": "Invalid path",
                    "file": {"path": photo_paths[i]}
                })
            else:
                metadata = metadata_service.get_photo_metadata(resolved_path)
                results.append(metadata)

        # Calculate statistics
        successful = sum(1 for r in results if 'error' not in r)
        failed = len(results) - successful

        return jsonify({
            "results": results,
            "total": len(results),
            "successful": successful,
            "failed": failed
        }), 200

    except Exception as e:
        # Log full error, return sanitized message
        error_msg = sanitize_error_message(e, "Batch processing failed")
        return jsonify({"error": error_msg}), 500
