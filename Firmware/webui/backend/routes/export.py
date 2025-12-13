"""
Export API routes (Issues #112, #116, #118)

Endpoints for export metadata service with Darwin Core CSV and iNaturalist ZIP support.

Endpoints:
- GET /api/export/metadata/<path:photo_path> - Get export metadata for single photo
- POST /api/export/metadata/batch - Get export metadata for multiple photos
- POST /api/export/darwin-core/batch - Batch Darwin Core CSV export
- GET /api/export/darwin-core/deployment/<path> - Export deployment as Darwin Core CSV
- POST /api/export/inaturalist/batch - Batch iNaturalist ZIP export
- GET /api/export/inaturalist/deployment/<path> - Export deployment as iNaturalist ZIP
- POST /api/export/inaturalist/preview - Preview iNaturalist export (dry run)
- GET /api/export/formats - List supported export formats
- GET /api/export/stats - Get service statistics

Security:
- Path traversal protection via validate_photo_path()
- CSRF protection (Flask-WTF) applied automatically to all POST endpoints
- Rate limiting on batch endpoints
"""

import csv
import io
import logging
from datetime import UTC, datetime

from flask import Blueprint, Response, current_app, jsonify, request

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
        format (str): Output format - "json" (default), "csv" (flat), or "darwin_core"

    Returns:
        200: JSON with export metadata
        400: Invalid format parameter or Darwin Core validation failed
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

        GET /api/export/metadata/moth_2024_01_15__10_00_00.jpg?format=darwin_core

        Response:
        {
            "occurrenceID": "mothbox:deployment:a1b2c3d4",
            "basisOfRecord": "MachineObservation",
            "eventDate": "2024-01-15T10:00:00",
            "decimalLatitude": 37.7749,
            "decimalLongitude": -122.4194,
            "geodeticDatum": "WGS84",
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
        if format_param not in ('json', 'csv', 'darwin_core'):
            return jsonify({"error": "Invalid format. Use 'json', 'csv', or 'darwin_core'"}), 400

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
            if format_param == 'darwin_core':
                # Validate for Darwin Core first
                validation = service.validate_for_format(result, ExportFormat.DARWIN_CORE)
                if not validation.is_valid:
                    return jsonify({
                        "error": "Darwin Core validation failed",
                        "missing_fields": validation.missing_fields,
                        "warnings": validation.warnings,
                    }), 400

                transformed = service.transform_to_darwin_core(result)
                # Include warnings if any
                if validation.warnings:
                    transformed["_warnings"] = validation.warnings
                return jsonify(transformed), 200
            else:
                flat = (format_param == 'csv')
                transformed = service.transform_to_generic(result, flat=flat)
                return jsonify(transformed), 200
        else:
            return jsonify(result), 200

    except Exception as e:
        logger.error("Error getting export metadata for %s: %s", photo_path, e, exc_info=True)
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
        logger.error("Error in batch export metadata: %s", e, exc_info=True)
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
                    "description": "Biodiversity standard format (GBIF)",
                    "implemented": true
                },
                {
                    "id": "inaturalist",
                    "name": "iNaturalist ZIP",
                    "description": "iNaturalist-compatible ZIP with XMP sidecars",
                    "implemented": true
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
                "description": "Biodiversity standard format (DwC) for GBIF",
                "implemented": True,
            },
            {
                "id": ExportFormat.INATURALIST.value,
                "name": "iNaturalist ZIP",
                "description": "iNaturalist-compatible ZIP with XMP sidecars",
                "implemented": True,
                "features": [
                    "XMP sidecar files",
                    "Hierarchical taxonomy keywords",
                    "GPS coordinates",
                    "Observation notes",
                    "License information",
                    "CSV summary",
                    "JSON manifest"
                ]
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
        logger.error("Error listing formats: %s", e, exc_info=True)
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
        logger.error("Error getting export stats: %s", e, exc_info=True)
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
        logger.error("Error resetting export stats: %s", e, exc_info=True)
        return jsonify({"error": "Failed to reset statistics"}), 500


# ============================================================================
# Darwin Core Export Endpoints
# ============================================================================


def _generate_csv_response(headers: list[str], rows: list[list[str]], filename: str) -> Response:
    """Generate a CSV file response.

    Args:
        headers: CSV column headers
        rows: CSV data rows
        filename: Filename for Content-Disposition header

    Returns:
        Flask Response with CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(rows)

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/csv; charset=utf-8',
        }
    )


def _generate_json_csv_response(
    headers: list[str],
    rows: list[list[str]],
    stats: dict,
) -> dict:
    """Generate JSON response containing CSV data.

    Args:
        headers: CSV column headers
        rows: CSV data rows
        stats: Export statistics

    Returns:
        Dictionary with CSV data and metadata
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(rows)

    csv_content = output.getvalue()
    output.close()

    return {
        "csv_data": csv_content,
        "headers": headers,
        "row_count": len(rows),
        **stats
    }


@export_bp.route("/darwin-core/batch", methods=["POST"])
@limiter.limit("5 per minute")
def export_darwin_core_batch():
    """
    Export multiple photos as Darwin Core CSV.

    Supports dual response format based on Accept header:
    - Accept: text/csv → CSV file download
    - Accept: application/json → JSON with CSV data as string

    Request Body:
        {
            "photo_paths": ["photo1.jpg", "subdir/photo2.jpg", ...],
            "validate": true,  // Optional, default true - skip invalid records
            "include_warnings": false  // Optional - include validation warnings
        }

    Returns:
        200: CSV file or JSON with CSV data
        400: Invalid request body or validation errors
        500: Internal error

    Example:
        POST /api/export/darwin-core/batch
        Content-Type: application/json
        Accept: text/csv

        {"photo_paths": ["photo1.jpg", "photo2.jpg"]}

        Response: CSV file download
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
            return jsonify({
                "error": "No photos provided",
                "csv_data": "",
                "headers": [],
                "row_count": 0
            }), 400

        # Get configurable batch size limit
        max_batch_size = current_app.config.get('EXPORT_MAX_BATCH_SIZE', 1000)

        if len(photo_paths) > max_batch_size:
            return jsonify({
                "error": f"Batch size exceeds maximum limit of {max_batch_size} photos"
            }), 400

        # Options
        validate = data.get('validate', True)
        include_warnings = data.get('include_warnings', False)

        # Collect metadata for all photos
        metadata_list = []
        validation_errors = []
        warnings = []

        for photo_path in photo_paths:
            # Path traversal protection
            validated_path = validate_photo_path(photo_path, PHOTOS_DIR)
            if validated_path is None:
                validation_errors.append({
                    "photo_path": photo_path,
                    "error": "Invalid path"
                })
                continue

            result = service.get_export_metadata(validated_path)

            if isinstance(result, dict) and 'error' in result:
                validation_errors.append({
                    "photo_path": photo_path,
                    "error": result['error']
                })
                continue

            if isinstance(result, ExportMetadata):
                # Validate for Darwin Core
                validation = service.validate_for_format(result, ExportFormat.DARWIN_CORE)

                if not validation.is_valid:
                    if validate:
                        # Skip invalid records (GBIF strict mode)
                        validation_errors.append({
                            "photo_path": photo_path,
                            "error": "Darwin Core validation failed",
                            "missing_fields": validation.missing_fields
                        })
                        continue
                    else:
                        # Include invalid records anyway
                        pass

                if include_warnings and validation.warnings:
                    warnings.extend([
                        {"photo_path": photo_path, "warning": w}
                        for w in validation.warnings
                    ])

                metadata_list.append(result)

        # Transform to Darwin Core CSV
        headers, rows = service.transform_batch_to_darwin_core_csv(
            metadata_list,
            filter_invalid=False  # Already filtered above
        )

        # Stats
        stats = {
            "total_requested": len(photo_paths),
            "exported": len(rows),
            "skipped": len(validation_errors),
            "validation_errors": validation_errors if validation_errors else [],
        }

        if include_warnings:
            stats["warnings"] = warnings

        # Determine response format based on Accept header
        accept = request.headers.get('Accept', 'application/json')

        if 'text/csv' in accept:
            # CSV file download
            timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
            filename = f"darwin_core_export_{timestamp}.csv"
            return _generate_csv_response(headers, rows, filename)
        else:
            # JSON with CSV data
            response_data = _generate_json_csv_response(headers, rows, stats)
            return jsonify(response_data), 200

    except Exception as e:
        logger.error("Error in Darwin Core batch export: %s", e, exc_info=True)
        return jsonify({"error": "Darwin Core batch export failed"}), 500


@export_bp.route("/darwin-core/deployment/<path:deployment_path>", methods=["GET"])
@limiter.limit("5 per minute")
def export_deployment_darwin_core(deployment_path: str):
    """
    Export all photos in a deployment directory as Darwin Core CSV.

    Supports dual response format based on Accept header:
    - Accept: text/csv → CSV file download
    - Accept: application/json → JSON with CSV data as string

    Query Parameters:
        validate (bool): If true (default), skip photos without GPS coordinates
        include_warnings (bool): If true, include validation warnings

    Returns:
        200: CSV file or JSON with CSV data
        400: Validation errors
        403: Path traversal attempt blocked
        404: Deployment directory not found
        500: Internal error

    Example:
        GET /api/export/darwin-core/deployment/2024/oak-ridge?validate=true
        Accept: text/csv

        Response: CSV file download with all valid photos from deployment
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

        # Validate path to prevent traversal attacks
        from pathlib import Path
        validated_path = validate_photo_path(deployment_path, PHOTOS_DIR)
        if validated_path is None:
            return jsonify({"error": "Invalid path"}), 403

        deployment_dir = Path(validated_path)

        # Check if directory exists
        if not deployment_dir.exists():
            return jsonify({"error": "Deployment directory not found"}), 404

        if not deployment_dir.is_dir():
            return jsonify({"error": "Path is not a directory"}), 400

        # Query parameters
        validate = request.args.get('validate', 'true').lower() == 'true'
        include_warnings = request.args.get('include_warnings', 'false').lower() == 'true'

        # Get all photos in deployment (jpg, jpeg, png)
        photo_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        photo_paths = [
            p for p in deployment_dir.rglob('*')
            if p.is_file() and p.suffix in photo_extensions
        ]

        if not photo_paths:
            return jsonify({
                "error": "No photos found in deployment directory",
                "csv_data": "",
                "headers": [],
                "row_count": 0
            }), 400

        # Collect metadata for all photos
        metadata_list = []
        validation_errors = []
        warnings = []

        for photo_path in photo_paths:
            result = service.get_export_metadata(photo_path)

            if isinstance(result, dict) and 'error' in result:
                validation_errors.append({
                    "photo_path": str(photo_path.relative_to(PHOTOS_DIR)),
                    "error": result['error']
                })
                continue

            if isinstance(result, ExportMetadata):
                # Validate for Darwin Core
                validation = service.validate_for_format(result, ExportFormat.DARWIN_CORE)

                if not validation.is_valid and validate:
                    # Skip invalid records (GBIF strict mode)
                    validation_errors.append({
                        "photo_path": str(photo_path.relative_to(PHOTOS_DIR)),
                        "error": "Darwin Core validation failed",
                        "missing_fields": validation.missing_fields
                    })
                    continue

                if include_warnings and validation.warnings:
                    rel_path = str(photo_path.relative_to(PHOTOS_DIR))
                    warnings.extend([
                        {"photo_path": rel_path, "warning": w}
                        for w in validation.warnings
                    ])

                metadata_list.append(result)

        # Transform to Darwin Core CSV
        headers, rows = service.transform_batch_to_darwin_core_csv(
            metadata_list,
            filter_invalid=False  # Already filtered above
        )

        # Stats
        stats = {
            "deployment_path": deployment_path,
            "total_photos": len(photo_paths),
            "exported": len(rows),
            "skipped": len(validation_errors),
            "validation_errors": validation_errors if validation_errors else [],
        }

        if include_warnings:
            stats["warnings"] = warnings

        # Determine response format based on Accept header
        accept = request.headers.get('Accept', 'application/json')

        if 'text/csv' in accept:
            # CSV file download
            timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
            # Sanitize deployment path for filename
            safe_name = deployment_path.replace('/', '_').replace('\\', '_')
            filename = f"darwin_core_{safe_name}_{timestamp}.csv"
            return _generate_csv_response(headers, rows, filename)
        else:
            # JSON with CSV data
            response_data = _generate_json_csv_response(headers, rows, stats)
            return jsonify(response_data), 200

    except Exception as e:
        logger.error("Error in Darwin Core deployment export: %s", e, exc_info=True)
        return jsonify({"error": "Darwin Core deployment export failed"}), 500


# ============================================================================
# iNaturalist Export Endpoints
# ============================================================================


@export_bp.route("/inaturalist/batch", methods=["POST"])
@limiter.limit("5 per minute")
def export_inaturalist_batch():
    """
    Export multiple photos as iNaturalist ZIP with XMP sidecars.

    Supports dual response format based on Accept header:
    - Accept: application/zip → ZIP file download
    - Accept: application/json → JSON with status and file path

    Request Body:
        {
            "photo_paths": ["photo1.jpg", "subdir/photo2.jpg", ...],
            "options": {
                "include_xmp_sidecars": true,
                "include_manifest": true,
                "include_csv_summary": true,
                "flatten_structure": false
            }
        }

    Returns:
        200: ZIP file or JSON with status
        400: Invalid request body
        500: Internal error

    Response (JSON):
        {
            "success": true,
            "zip_path": "/tmp/export_123.zip",
            "zip_size_bytes": 12500000,
            "photo_count": 50,
            "xmp_count": 50,
            "took_ms": 3500.5
        }

    Error Response:
        {
            "error": "No photos specified",
            "details": "photo_paths array is required and must not be empty"
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
            return jsonify({
                "error": "No photos specified",
                "details": "photo_paths array is required and must not be empty"
            }), 400

        photo_paths = data['photo_paths']

        if not isinstance(photo_paths, list):
            return jsonify({"error": "'photo_paths' must be an array"}), 400

        # Validate all paths are non-empty strings
        if not all(isinstance(p, str) and p.strip() for p in photo_paths):
            return jsonify({"error": "All photo_paths must be non-empty strings"}), 400

        if len(photo_paths) == 0:
            return jsonify({
                "error": "No photos specified",
                "details": "photo_paths array is required and must not be empty"
            }), 400

        # Get configurable batch size limit
        max_batch_size = current_app.config.get('EXPORT_MAX_BATCH_SIZE', 1000)

        if len(photo_paths) > max_batch_size:
            return jsonify({
                "error": f"Batch size exceeds maximum limit of {max_batch_size} photos"
            }), 400

        # Parse options
        from webui.backend.lib.zip_export import ZipExportOptions

        options_data = data.get('options', {})
        options = ZipExportOptions(
            include_xmp_sidecars=options_data.get('include_xmp_sidecars', True),
            include_manifest=options_data.get('include_manifest', True),
            include_csv_summary=options_data.get('include_csv_summary', True),
            flatten_structure=options_data.get('flatten_structure', False),
        )

        # Validate and resolve all paths with security checks
        from pathlib import Path
        resolved_paths = []
        for photo_path in photo_paths:
            # Path traversal protection
            validated_path = validate_photo_path(photo_path, PHOTOS_DIR)
            if validated_path is None:
                return jsonify({
                    "error": "Invalid path",
                    "details": f"Path validation failed for: {photo_path}"
                }), 403
            resolved_paths.append(Path(validated_path))

        # Create temporary ZIP file
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.zip', prefix='inaturalist_export_')
        import os
        os.close(temp_fd)  # Close file descriptor
        output_path = Path(temp_path)

        try:
            # Generate ZIP export
            result = service.transform_batch_to_inaturalist_zip(
                resolved_paths,
                output_path,
                options
            )

            if not result.success:
                return jsonify({
                    "error": "ZIP export failed",
                    "details": result.errors
                }), 500

            # Determine response format based on Accept header
            accept = request.headers.get('Accept', 'application/json')

            if 'application/zip' in accept:
                # ZIP file download
                from flask import send_file
                timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
                filename = f"inaturalist_export_{timestamp}.zip"

                return send_file(
                    output_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=filename,
                )
            else:
                # JSON with status
                return jsonify({
                    "success": result.success,
                    "zip_path": str(result.zip_path),
                    "zip_size_bytes": result.zip_size_bytes,
                    "photo_count": result.photo_count,
                    "xmp_count": result.xmp_count,
                    "errors": result.errors,
                    "took_ms": result.took_ms,
                }), 200

        except Exception as e:
            logger.error("Error creating iNaturalist ZIP: %s", e, exc_info=True)
            # Clean up temp file on error
            if output_path.exists():
                output_path.unlink()
            return jsonify({"error": "ZIP export failed"}), 500

    except Exception as e:
        logger.error("Error in iNaturalist batch export: %s", e, exc_info=True)
        return jsonify({"error": "iNaturalist batch export failed"}), 500


@export_bp.route("/inaturalist/deployment/<path:deployment_path>", methods=["GET"])
@limiter.limit("5 per minute")
def export_deployment_inaturalist(deployment_path: str):
    """
    Export all photos in a deployment directory as iNaturalist ZIP.

    Supports dual response format based on Accept header:
    - Accept: application/zip → ZIP file download
    - Accept: application/json → JSON with status and file path

    Path Parameters:
        deployment_path: Path to deployment directory (relative to PHOTOS_DIR)

    Query Parameters:
        include_xmp (bool): Include XMP sidecars (default: true)
        include_manifest (bool): Include manifest.json (default: true)
        include_csv_summary (bool): Include summary.csv (default: true)

    Returns:
        200: ZIP file or JSON with status
        403: Path traversal attempt blocked
        404: Deployment directory not found
        500: Internal error

    Example:
        GET /api/export/inaturalist/deployment/2024/oak-ridge?include_xmp=true
        Accept: application/zip

        Response: ZIP file download with all photos from deployment
    """
    try:
        # Get service from app config
        service = current_app.config.get('EXPORT_METADATA_SERVICE')
        if service is None:
            return jsonify({"error": "Export service not available"}), 500

        # Validate path to prevent traversal attacks
        from pathlib import Path
        validated_path = validate_photo_path(deployment_path, PHOTOS_DIR)
        if validated_path is None:
            return jsonify({"error": "Invalid path"}), 403

        deployment_dir = Path(validated_path)

        # Check if directory exists
        if not deployment_dir.exists():
            return jsonify({"error": "Deployment directory not found"}), 404

        if not deployment_dir.is_dir():
            return jsonify({"error": "Path is not a directory"}), 400

        # Query parameters
        include_xmp = request.args.get('include_xmp', 'true').lower() == 'true'
        include_manifest = request.args.get('include_manifest', 'true').lower() == 'true'
        include_csv_summary = request.args.get('include_csv_summary', 'true').lower() == 'true'

        # Get all photos in deployment (jpg, jpeg, png)
        photo_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        photo_paths = [
            p for p in deployment_dir.rglob('*')
            if p.is_file() and p.suffix in photo_extensions
        ]

        if not photo_paths:
            return jsonify({
                "error": "No photos found in deployment directory"
            }), 400

        # Create export options
        from webui.backend.lib.zip_export import ZipExportOptions

        options = ZipExportOptions(
            include_xmp_sidecars=include_xmp,
            include_manifest=include_manifest,
            include_csv_summary=include_csv_summary,
            flatten_structure=False,
        )

        # Create temporary ZIP file
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.zip', prefix='inaturalist_deployment_')
        import os
        os.close(temp_fd)  # Close file descriptor
        output_path = Path(temp_path)

        try:
            # Generate ZIP export
            result = service.transform_batch_to_inaturalist_zip(
                photo_paths,
                output_path,
                options
            )

            if not result.success:
                return jsonify({
                    "error": "ZIP export failed",
                    "details": result.errors
                }), 500

            # Determine response format based on Accept header
            accept = request.headers.get('Accept', 'application/json')

            if 'application/zip' in accept:
                # ZIP file download
                from flask import send_file
                timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
                # Sanitize deployment path for filename
                safe_name = deployment_path.replace('/', '_').replace('\\', '_')
                filename = f"inaturalist_{safe_name}_{timestamp}.zip"

                return send_file(
                    output_path,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=filename,
                )
            else:
                # JSON with status
                return jsonify({
                    "success": result.success,
                    "zip_path": str(result.zip_path),
                    "zip_size_bytes": result.zip_size_bytes,
                    "photo_count": result.photo_count,
                    "xmp_count": result.xmp_count,
                    "errors": result.errors,
                    "took_ms": result.took_ms,
                }), 200

        except Exception as e:
            logger.error("Error creating iNaturalist ZIP: %s", e, exc_info=True)
            # Clean up temp file on error
            if output_path.exists():
                output_path.unlink()
            return jsonify({"error": "ZIP export failed"}), 500

    except Exception as e:
        logger.error("Error in iNaturalist deployment export: %s", e, exc_info=True)
        return jsonify({"error": "iNaturalist deployment export failed"}), 500


@export_bp.route("/inaturalist/preview", methods=["POST"])
def preview_inaturalist_export():
    """
    Preview iNaturalist export without creating ZIP (dry run).

    Validates photos and generates sample XMP to help users verify
    metadata before creating the full export.

    Request Body:
        {
            "photo_paths": ["photo1.jpg", "subdir/photo2.jpg", ...]
        }

    Returns:
        200: JSON with validation results
        400: Invalid request body
        500: Internal error

    Response:
        {
            "valid_photos": 45,
            "invalid_photos": 5,
            "estimated_zip_size_bytes": 125000000,
            "validation_results": [
                {
                    "photo": "photo1.jpg",
                    "is_valid": true,
                    "missing_required": [],
                    "warnings": ["Missing species name"]
                },
                {
                    "photo": "photo2.jpg",
                    "is_valid": false,
                    "missing_required": ["latitude", "longitude"],
                    "warnings": []
                }
            ],
            "sample_xmp": "<?xpacket...?>..."
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
            return jsonify({"error": "No photos provided"}), 400

        # Get configurable batch size limit
        max_batch_size = current_app.config.get('EXPORT_MAX_BATCH_SIZE', 1000)

        if len(photo_paths) > max_batch_size:
            return jsonify({
                "error": f"Batch size exceeds maximum limit of {max_batch_size} photos"
            }), 400

        # Validate and resolve paths
        from pathlib import Path

        from webui.backend.lib.zip_export import estimate_zip_size

        resolved_paths = []
        validation_results = []
        valid_count = 0
        invalid_count = 0

        for photo_path in photo_paths:
            # Path traversal protection
            validated_path = validate_photo_path(photo_path, PHOTOS_DIR)
            if validated_path is None:
                validation_results.append({
                    'photo': photo_path,
                    'is_valid': False,
                    'missing_required': ['path'],
                    'warnings': [],
                    'error': 'Invalid path'
                })
                invalid_count += 1
                continue

            path = Path(validated_path)
            if not path.exists():
                validation_results.append({
                    'photo': photo_path,
                    'is_valid': False,
                    'missing_required': ['file'],
                    'warnings': [],
                    'error': 'File not found'
                })
                invalid_count += 1
                continue

            # Get metadata and validate
            metadata = service.get_export_metadata(path)

            if isinstance(metadata, dict) and 'error' in metadata:
                validation_results.append({
                    'photo': photo_path,
                    'is_valid': False,
                    'missing_required': ['metadata'],
                    'warnings': [],
                    'error': metadata['error']
                })
                invalid_count += 1
                continue

            # Validate for iNaturalist
            validation = service.validate_for_format(metadata, ExportFormat.INATURALIST)

            validation_results.append({
                'photo': photo_path,
                'is_valid': validation.is_valid,
                'missing_required': validation.missing_fields,
                'warnings': validation.warnings,
            })

            if validation.is_valid:
                valid_count += 1
                resolved_paths.append(path)
            else:
                invalid_count += 1

        # Estimate ZIP size
        estimated_size = estimate_zip_size(resolved_paths, include_xmp=True)

        # Generate sample XMP from first valid photo
        sample_xmp = None
        if resolved_paths:
            from webui.backend.lib.xmp_sidecar import generate_xmp_xml
            first_metadata = service.get_export_metadata(resolved_paths[0])
            if not isinstance(first_metadata, dict) or 'error' not in first_metadata:
                sample_xmp = generate_xmp_xml(first_metadata)

        return jsonify({
            'valid_photos': valid_count,
            'invalid_photos': invalid_count,
            'estimated_zip_size_bytes': estimated_size,
            'validation_results': validation_results,
            'sample_xmp': sample_xmp,
        }), 200

    except Exception as e:
        logger.error("Error in iNaturalist preview: %s", e, exc_info=True)
        return jsonify({"error": "Preview failed"}), 500
