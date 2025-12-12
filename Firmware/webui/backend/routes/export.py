"""
Export API routes (Issue #112)

Basic endpoints for testing export metadata service.
Full export API will be implemented in Issue #122.

Endpoints:
- GET /api/export/metadata/<path:photo_path> - Get export metadata for single photo
- POST /api/export/metadata/batch - Get export metadata for multiple photos
- GET /api/export/formats - List supported export formats
- GET /api/export/stats - Get service statistics

Security:
- Path traversal protection via validate_photo_path()
- CSRF protection (Flask-WTF) applied automatically to all POST endpoints
- Rate limiting on batch endpoint
"""

import logging

from flask import Blueprint, current_app, jsonify, request

from mothbox_paths import PHOTOS_DIR
from webui.backend.security_utils import validate_photo_path
from webui.backend.services.export_metadata_service import (
    ExportFormat,
    ExportMetadata,
)

# Rate limiter is configured in app.py
# For standalone testing, provide a no-op stub
try:
    from webui.backend.app import limiter
except ImportError:
    # Stub for unit testing when app is not fully initialized
    class _LimiterStub:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = _LimiterStub()

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


# ============================================================================
# Metadata Endpoints
# ============================================================================


@export_bp.route("/metadata/<path:photo_path>", methods=["GET"])
def get_export_metadata(photo_path: str):
    """
    Get aggregated export metadata for a single photo.

    Query Parameters:
        format (str): Output format - "json" (default) or "csv" (flat structure)

    Returns:
        200: JSON with export metadata
        400: Invalid format parameter
        403: Path traversal attempt blocked
        404: Photo not found
        500: Internal error

    Example:
        GET /api/export/metadata/moth_2024_01_15__10_00_00.jpg?format=json

        Response:
        {
            "photo_path": "/photos/moth_2024_01_15__10_00_00.jpg",
            "filename": "moth_2024_01_15__10_00_00.jpg",
            "timestamp": "2024-01-15T10:00:00",
            "latitude": 37.7749,
            "longitude": -122.4194,
            ...
        }
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

        # Validate path to prevent traversal attacks
        validated_path = validate_photo_path(photo_path, PHOTOS_DIR)
        if validated_path is None:
            return jsonify({"error": "Invalid path"}), 403

        # Get format parameter (default: json)
        format_param = request.args.get('format', 'json').lower()
        if format_param not in ('json', 'csv'):
            return jsonify({"error": "Invalid format. Use 'json' or 'csv'"}), 400

        # Get export metadata
        result = service.get_export_metadata(validated_path)

        # Check if result is an error dict
        if isinstance(result, dict) and 'error' in result:
            error_msg = result['error']
            if error_msg == 'Photo not found':
                return jsonify(result), 404
            elif error_msg == 'Permission denied':
                return jsonify(result), 403
            else:
                return jsonify(result), 500

        # Transform to requested format
        if isinstance(result, ExportMetadata):
            flat = (format_param == 'csv')
            transformed = service.transform_to_generic(result, flat=flat)
            return jsonify(transformed), 200
        else:
            return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting export metadata for {photo_path}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get export metadata"}), 500


@export_bp.route("/metadata/batch", methods=["POST"])
@limiter.limit("10 per minute")
def get_batch_export_metadata():
    """
    Get export metadata for multiple photos.

    Request Body:
        {
            "photo_paths": ["photo1.jpg", "subdir/photo2.jpg", ...],
            "format": "json"  // optional, "json" or "csv"
        }

    Returns:
        200: JSON with results array
        400: Invalid request body
        500: Internal error

    Example:
        POST /api/export/metadata/batch
        Content-Type: application/json

        {"photo_paths": ["photo1.jpg", "photo2.jpg"], "format": "json"}

        Response:
        {
            "results": [
                {"photo_path": "...", "filename": "...", ...},
                {"error": "Photo not found", "photo_path": "..."}
            ],
            "total": 2,
            "successful": 1,
            "failed": 1
        }
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

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

        # Validate all paths are non-empty strings
        if not all(isinstance(p, str) and p.strip() for p in photo_paths):
            return jsonify({"error": "All photo_paths must be non-empty strings"}), 400

        if len(photo_paths) == 0:
            return jsonify({"results": [], "total": 0, "successful": 0, "failed": 0}), 200

        # Get configurable batch size limit
        max_batch_size = current_app.config.get('EXPORT_MAX_BATCH_SIZE', 1000)

        if len(photo_paths) > max_batch_size:
            return jsonify({
                "error": f"Batch size exceeds maximum limit of {max_batch_size} photos"
            }), 400

        # Get format parameter (default: json)
        format_param = data.get('format', 'json').lower()
        if format_param not in ('json', 'csv'):
            return jsonify({"error": "Invalid format. Use 'json' or 'csv'"}), 400

        # Validate and resolve all paths with security checks
        resolved_paths = []
        for photo_path in photo_paths:
            # Path traversal protection
            validated_path = validate_photo_path(photo_path, PHOTOS_DIR)
            resolved_paths.append((photo_path, validated_path))

        # Get metadata for all photos (batch processing)
        results = []
        for original_path, validated_path in resolved_paths:
            if validated_path is None:
                # Path validation failed
                results.append({
                    "error": "Invalid path",
                    "photo_path": original_path
                })
            else:
                result = service.get_export_metadata(validated_path)

                # Transform to requested format
                if isinstance(result, ExportMetadata):
                    flat = (format_param == 'csv')
                    results.append(service.transform_to_generic(result, flat=flat))
                else:
                    # Error dict
                    results.append(result)

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
        logger.error(f"Error in batch export metadata: {e}", exc_info=True)
        return jsonify({"error": "Batch processing failed"}), 500


# ============================================================================
# Format and Statistics Endpoints
# ============================================================================


@export_bp.route("/formats", methods=["GET"])
def list_export_formats():
    """
    List supported export formats.

    Returns:
        200: JSON with format details

    Example:
        GET /api/export/formats

        Response:
        {
            "formats": [
                {
                    "id": "darwin_core",
                    "name": "Darwin Core",
                    "description": "Biodiversity standard format",
                    "implemented": false
                },
                {
                    "id": "inaturalist",
                    "name": "iNaturalist CSV",
                    "description": "iNaturalist observation format",
                    "implemented": false
                },
                {
                    "id": "json",
                    "name": "Generic JSON",
                    "description": "Generic JSON format with all metadata",
                    "implemented": true
                },
                {
                    "id": "csv",
                    "name": "Generic CSV",
                    "description": "Generic CSV format with flat structure",
                    "implemented": true
                }
            ]
        }
    """
    try:
        formats = [
            {
                "id": ExportFormat.DARWIN_CORE.value,
                "name": "Darwin Core",
                "description": "Biodiversity standard format (DwC)",
                "implemented": False,
                "note": "Will be implemented in Issue #116"
            },
            {
                "id": ExportFormat.INATURALIST.value,
                "name": "iNaturalist CSV",
                "description": "iNaturalist observation format",
                "implemented": False,
                "note": "Will be implemented in Issue #118"
            },
            {
                "id": ExportFormat.GENERIC_JSON.value,
                "name": "Generic JSON",
                "description": "Generic JSON format with all metadata",
                "implemented": True
            },
            {
                "id": ExportFormat.GENERIC_CSV.value,
                "name": "Generic CSV",
                "description": "Generic CSV format with flat structure",
                "implemented": True
            }
        ]

        return jsonify({"formats": formats}), 200

    except Exception as e:
        logger.error(f"Error listing formats: {e}", exc_info=True)
        return jsonify({"error": "Failed to list formats"}), 500


@export_bp.route("/stats", methods=["GET"])
def get_export_stats():
    """
    Get export service statistics.

    Returns:
        200: JSON with cache stats

    Example:
        GET /api/export/stats

        Response:
        {
            "cache_entries": 150,
            "cache_hits": 450,
            "cache_misses": 200,
            "total_exports": 650,
            "errors": 5
        }
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

        # Get statistics
        stats = service.get_statistics()

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting export stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get statistics"}), 500


@export_bp.route("/stats/reset", methods=["POST"])
def reset_export_stats():
    """
    Reset export service statistics.

    Resets all counters (cache_hits, cache_misses, total_exports, errors) to zero.
    Cache entries count is preserved as it reflects actual cache state.

    Returns:
        200: JSON with success message
        500: Export service not available

    Example:
        POST /api/export/stats/reset

        Response:
        {
            "message": "Statistics reset successfully"
        }
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

        # Reset statistics
        service.reset_statistics()

        return jsonify({"message": "Statistics reset successfully"}), 200

    except Exception as e:
        logger.error(f"Error resetting export stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to reset statistics"}), 500
