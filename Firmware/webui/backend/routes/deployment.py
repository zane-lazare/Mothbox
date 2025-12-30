"""
Deployment Metadata CRUD API Endpoints

Provides REST API for managing deployment-level metadata for photo collections.
Deployment metadata describes entire collections: location, time period, environmental conditions.

Blueprint: deployment_bp
URL Prefix: /api/deployment

Endpoints:
- GET    /metadata/<path:directory>     - Get deployment metadata for directory
- PUT    /metadata/<path:directory>     - Create/replace deployment metadata
- PATCH  /metadata/<path:directory>     - Partial update deployment metadata
- DELETE /metadata/<path:directory>     - Delete deployment metadata
- GET    /list                          - List all deployments
- GET    /discover/<path:photo_path>    - Find deployment for photo
- POST   /batch                         - Batch update operations
- POST   /generate                      - Generate sidecars for directory
- GET    /stats                         - Service statistics
- POST   /cache/invalidate              - Invalidate cache

Security:
- CSRF protection (Flask-WTF) on all state-changing endpoints
- Path traversal protection via validate_photo_path()
- Input validation (coordinate ranges, date formats, etc.)
- Sanitized error messages (no stack trace exposure)
- Rate limiting (10/minute for batch operations)

Performance:
- LRU cache with configurable TTL (default: 5 minutes)
- Cache hit rate target: >80%
- Cache hit latency: <10ms
- Disk read latency: <50ms
"""

import logging

from flask import Blueprint, current_app, jsonify, request

# Rate limiting
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

from mothbox_paths import PHOTOS_DIR
from webui.backend.lib.api_key_auth import require_api_key_or_csrf
from webui.backend.lib.deployment_schema import (
    MAX_CUSTOM_DEPTH,
    MAX_CUSTOM_KEYS,
    MAX_DEPLOYMENT_NAME_LENGTH,
    MAX_LATITUDE,
    MAX_LOCATION_NAME_LENGTH,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    SUPPORTED_FORMATS,
)
from webui.backend.security_utils import sanitize_error_message, validate_photo_path

logger = logging.getLogger(__name__)

# Blueprint setup
deployment_bp = Blueprint("deployment", __name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _validate_custom_value(value, depth: int = 0) -> tuple[bool, str | None]:
    """
    Recursively validate a custom field value.

    Args:
        value: The value to validate
        depth: Current nesting depth (max MAX_CUSTOM_DEPTH)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if depth > MAX_CUSTOM_DEPTH:
        return False, f"Custom field nesting exceeds maximum depth ({MAX_CUSTOM_DEPTH})"

    if value is None:
        return True, None
    if isinstance(value, bool):
        return True, None
    if isinstance(value, (int, float)):
        return True, None
    if isinstance(value, str):
        if len(value) > 10000:  # Same as MAX_NOTES_LENGTH
            return False, "Custom field string value too long (max 10000)"
        return True, None
    if isinstance(value, list):
        for item in value:
            valid, err = _validate_custom_value(item, depth + 1)
            if not valid:
                return False, err
        return True, None
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                return False, "Custom field dict keys must be strings"
            if len(k) > 100:
                return False, f"Custom field key too long: {k[:50]}..."
            valid, err = _validate_custom_value(v, depth + 1)
            if not valid:
                return False, err
        return True, None

    return False, f"Invalid custom field value type: {type(value).__name__}"


def _validate_deployment_input(data: dict) -> tuple[bool, str | None]:
    """
    Validate deployment metadata input data.

    Args:
        data: Deployment metadata dictionary

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    # Validate deployment_name (required for PUT, optional for PATCH)
    if 'deployment_name' in data:
        if not isinstance(data['deployment_name'], str):
            return False, "deployment_name must be a string"
        if len(data['deployment_name']) == 0:
            return False, "deployment_name cannot be empty"
        if len(data['deployment_name']) > MAX_DEPLOYMENT_NAME_LENGTH:
            return False, f"deployment_name exceeds maximum length ({MAX_DEPLOYMENT_NAME_LENGTH})"

    # Validate location_name
    if 'location_name' in data and data['location_name'] is not None:
        if not isinstance(data['location_name'], str):
            return False, "location_name must be a string"
        if len(data['location_name']) > MAX_LOCATION_NAME_LENGTH:
            return False, f"location_name exceeds maximum length ({MAX_LOCATION_NAME_LENGTH})"

    # Validate coordinates
    if 'latitude' in data and data['latitude'] is not None:
        if not isinstance(data['latitude'], (int, float)):
            return False, "latitude must be a number"
        if not MIN_LATITUDE <= data['latitude'] <= MAX_LATITUDE:
            return False, f"latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}"

    if 'longitude' in data and data['longitude'] is not None:
        if not isinstance(data['longitude'], (int, float)):
            return False, "longitude must be a number"
        if not MIN_LONGITUDE <= data['longitude'] <= MAX_LONGITUDE:
            return False, f"longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}"

    if 'altitude' in data and data['altitude'] is not None and not isinstance(data['altitude'], (int, float)):
        return False, "altitude must be a number"

    # Validate date fields (basic check - ISO 8601 format YYYY-MM-DD)
    for field in ['start_date', 'end_date']:
        if field in data and data[field] is not None:
            if not isinstance(data[field], str):
                return False, f"{field} must be a string (ISO 8601 format: YYYY-MM-DD)"
            # Basic length check for YYYY-MM-DD format
            if len(data[field]) != 10:
                return False, f"{field} must be in ISO 8601 format (YYYY-MM-DD)"

    # Validate environmental dict (same constraints as custom fields)
    if 'environmental' in data and data['environmental'] is not None:
        if not isinstance(data['environmental'], dict):
            return False, "environmental must be an object"
        for key, value in data['environmental'].items():
            if not isinstance(key, str):
                return False, "environmental field names must be strings"
            if len(key) > 100:
                return False, f"environmental field name too long: {key[:50]}..."
            valid, err = _validate_custom_value(value)
            if not valid:
                return False, err.replace("Custom field", "environmental field")

    # Validate custom fields
    if 'custom' in data:
        if not isinstance(data['custom'], dict):
            return False, "custom fields must be an object"
        if len(data['custom']) > MAX_CUSTOM_KEYS:
            return False, f"Too many custom fields (max {MAX_CUSTOM_KEYS})"
        for key, value in data['custom'].items():
            if not isinstance(key, str):
                return False, "Custom field names must be strings"
            if len(key) > 100:
                return False, f"Custom field name too long: {key[:50]}..."
            valid, err = _validate_custom_value(value)
            if not valid:
                return False, err

    return True, None


# ============================================================================
# GET /metadata/<path:directory> - Get deployment metadata
# ============================================================================

@deployment_bp.route("/metadata/<path:directory>", methods=["GET"])
def get_deployment_metadata(directory: str):
    """
    Get deployment metadata for a directory.

    Returns existing metadata if deployment sidecar exists, or 404 if not found.

    Args:
        directory: Directory path (relative to PHOTOS_DIR)

    Returns:
        JSON response with deployment metadata

    Status Codes:
        200: Success
        400: Invalid path (path traversal attempt)
        404: Deployment not found
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/deployment/metadata/forest_2024

        Response:
        {
            "deployment": {
                "version": "1.0",
                "deployment_name": "Forest Survey 2024",
                "latitude": 35.9606,
                "longitude": -83.9207,
                "location_name": "Oak Ridge, TN, USA",
                "start_date": "2024-06-01",
                "end_date": "2024-08-31",
                ...
            },
            "source_path": "/var/lib/mothbox/photos/forest_2024/deployment.json"
        }
    """
    try:
        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(directory, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if directory exists
        if not full_path.exists() or not full_path.is_dir():
            return jsonify({"error": "Directory not found"}), 404

        # Get metadata from service
        metadata = service.get_deployment_metadata(full_path)

        if metadata is None:
            return jsonify({"error": "Deployment not found"}), 404

        # Find source path for response
        from webui.backend.lib.deployment_sidecar import find_deployment_sidecar
        source_path = find_deployment_sidecar(full_path)

        return jsonify({
            "deployment": metadata.to_dict(),
            "source_path": str(source_path) if source_path else None
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get deployment metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# PUT /metadata/<path:directory> - Create/replace deployment metadata
# ============================================================================

@deployment_bp.route("/metadata/<path:directory>", methods=["PUT"])
def create_deployment_metadata(directory: str):
    """
    Create or replace deployment metadata for a directory.

    Requires CSRF token OR valid API key in X-API-Key header.

    Args:
        directory: Directory path (relative to PHOTOS_DIR)

    Query Parameters:
        format: File format ("json" or "yaml", default: "json")

    Request Body (JSON):
        {
            "deployment_name": "Forest Survey 2024",  // required
            "latitude": 35.9606,                       // optional
            "longitude": -83.9207,                     // optional
            "altitude": 350.5,                         // optional
            "location_name": "Oak Ridge, TN, USA",     // optional
            "start_date": "2024-06-01",                // optional (ISO 8601)
            "end_date": "2024-08-31",                  // optional (ISO 8601)
            "environmental": {...},                    // optional
            "mothbox_id": "mothbox-001",               // optional
            "firmware_version": "5.2.1",               // optional
            "custom": {...},                           // optional
            "modified_by": "user123"                   // optional
        }

    Returns:
        JSON response with created/updated metadata

    Status Codes:
        200: Success (created or replaced)
        400: Invalid input (validation error, missing required fields)
        403: Invalid path or authentication failure
        404: Directory not found
        500: Internal server error
        503: Service unavailable

    Example:
        PUT /api/deployment/metadata/forest_2024?format=json
        Content-Type: application/json
        X-CSRFToken: <token>

        {"deployment_name": "Forest Survey 2024", "latitude": 35.9606}

        Response:
        {
            "version": "1.0",
            "deployment_name": "Forest Survey 2024",
            "latitude": 35.9606,
            ...
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.
        # API key auth not yet implemented - see issue #175 for tracking.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(directory, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if directory exists
        if not full_path.exists() or not full_path.is_dir():
            return jsonify({"error": "Directory not found"}), 404

        # Validate request body
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({"error": "Invalid JSON in request body"}), 400

        if data is None:
            return jsonify({"error": "Request body is required"}), 400

        # Validate required field
        if 'deployment_name' not in data:
            return jsonify({"error": "Field 'deployment_name' is required"}), 400

        # Validate input
        is_valid, error_msg = _validate_deployment_input(data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Get format from query params
        format = request.args.get('format', 'json')
        if format not in SUPPORTED_FORMATS:
            return jsonify({"error": f"Invalid format. Supported: {', '.join(SUPPORTED_FORMATS)}"}), 400

        # Create metadata object
        from webui.backend.lib.deployment_sidecar import create_deployment_metadata as lib_create

        metadata = lib_create(
            directory=full_path,
            name=data['deployment_name'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            altitude=data.get('altitude'),
            location_name=data.get('location_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            environmental=data.get('environmental'),
            mothbox_id=data.get('mothbox_id'),
            firmware_version=data.get('firmware_version'),
            custom=data.get('custom'),
            modified_by=data.get('modified_by'),
        )

        # Write to disk via service (handles cache)
        success = service.set_deployment_metadata(full_path, metadata, format=format)

        if not success:
            return jsonify({"error": "Failed to write deployment metadata"}), 500

        return jsonify(metadata.to_dict()), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to create deployment metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# PATCH /metadata/<path:directory> - Partial update deployment metadata
# ============================================================================

@deployment_bp.route("/metadata/<path:directory>", methods=["PATCH"])
@require_api_key_or_csrf
def update_deployment_metadata(directory: str):
    """
    Partial update of deployment metadata for a directory.

    Updates existing deployment metadata or returns 404 if not found.

    Requires CSRF token OR valid API key in X-API-Key header.

    Args:
        directory: Directory path (relative to PHOTOS_DIR)

    Request Body (JSON):
        {
            "end_date": "2024-09-15",                  // optional
            "location_name": "Updated Location",       // optional
            "environmental": {...},                    // optional
            ... any other fields to update
        }

    Returns:
        JSON response with updated metadata

    Status Codes:
        200: Success
        400: Invalid input (validation error)
        403: Invalid path or authentication failure
        404: Deployment not found
        500: Internal server error
        503: Service unavailable

    Example:
        PATCH /api/deployment/metadata/forest_2024
        Content-Type: application/json
        X-CSRFToken: <token>

        {"end_date": "2024-09-15", "location_name": "Updated"}

        Response:
        {
            "version": "1.0",
            "deployment_name": "Forest Survey 2024",
            "end_date": "2024-09-15",
            "location_name": "Updated",
            ...
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(directory, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if directory exists
        if not full_path.exists() or not full_path.is_dir():
            return jsonify({"error": "Directory not found"}), 404

        # Check if deployment exists
        existing = service.get_deployment_metadata(full_path)
        if existing is None:
            return jsonify({"error": "Deployment not found"}), 404

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
        is_valid, error_msg = _validate_deployment_input(data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Update metadata via service
        updated_metadata = service.update_deployment_metadata(full_path, data)

        if updated_metadata is None:
            return jsonify({"error": "Failed to update deployment metadata"}), 500

        return jsonify(updated_metadata.to_dict()), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to update deployment metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# DELETE /metadata/<path:directory> - Delete deployment metadata
# ============================================================================

@deployment_bp.route("/metadata/<path:directory>", methods=["DELETE"])
@require_api_key_or_csrf
def delete_deployment_metadata(directory: str):
    """
    Delete deployment metadata for a directory.

    Requires CSRF token OR valid API key in X-API-Key header.

    Args:
        directory: Directory path (relative to PHOTOS_DIR)

    Returns:
        JSON response with success status

    Status Codes:
        200: Success
        403: Invalid path or authentication failure
        404: Deployment not found
        500: Internal server error
        503: Service unavailable

    Example:
        DELETE /api/deployment/metadata/forest_2024
        X-CSRFToken: <token>

        Response:
        {"success": true}
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(directory, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if deployment exists
        metadata = service.get_deployment_metadata(full_path)
        if metadata is None:
            return jsonify({"error": "Deployment not found"}), 404

        # Delete via service (handles cache invalidation and file deletion)
        delete_success = service.delete_deployment_metadata(full_path)
        if not delete_success:
            return jsonify({"error": "Failed to delete deployment metadata"}), 500

        return jsonify({"success": True}), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to delete deployment metadata")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /list - List all deployments
# ============================================================================

@deployment_bp.route("/list", methods=["GET"])
def list_all_deployments():
    """
    List all deployments under PHOTOS_DIR.

    Query Parameters:
        root_dir (str): Optional root directory to search (relative to PHOTOS_DIR)

    Returns:
        JSON response with:
        - deployments: List of deployment metadata dictionaries
        - total: Total number of deployments found

    Status Codes:
        200: Success
        400: Invalid path
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/deployment/list

        Response:
        {
            "deployments": [
                {
                    "version": "1.0",
                    "deployment_name": "Forest Survey 2024",
                    "latitude": 35.9606,
                    ...
                },
                {
                    "version": "1.0",
                    "deployment_name": "Meadow Survey 2024",
                    ...
                }
            ],
            "total": 2
        }
    """
    try:
        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Get optional root_dir parameter
        root_dir_param = request.args.get('root_dir')

        if root_dir_param:
            # Validate path
            root_dir = validate_photo_path(root_dir_param, PHOTOS_DIR)
            if root_dir is None:
                return jsonify({"error": "Invalid path: Access denied"}), 400
        else:
            root_dir = None  # Use default (PHOTOS_DIR)

        # List deployments via service
        deployments = service.list_deployments(root_dir)

        # Convert to dict for JSON response
        deployment_dicts = [d.to_dict() for d in deployments]

        return jsonify({
            "deployments": deployment_dicts,
            "total": len(deployment_dicts)
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to list deployments")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /discover/<path:photo_path> - Find deployment for photo
# ============================================================================

@deployment_bp.route("/discover/<path:photo_path>", methods=["GET"])
def discover_deployment_for_photo(photo_path: str):
    """
    Find nearest deployment metadata by walking up directory tree.

    Searches current directory and all parent directories up to PHOTOS_DIR root.

    Args:
        photo_path: Photo file path (relative to PHOTOS_DIR)

    Returns:
        JSON response with deployment metadata if found

    Status Codes:
        200: Success (deployment found)
        400: Invalid path
        404: Photo or deployment not found
        500: Internal server error
        503: Service unavailable

    Example:
        GET /api/deployment/discover/forest_2024/subdir/photo.jpg

        Response:
        {
            "deployment": {
                "version": "1.0",
                "deployment_name": "Forest Survey 2024",
                ...
            },
            "source_path": "/var/lib/mothbox/photos/forest_2024/deployment.json"
        }
    """
    try:
        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Path traversal protection
        full_path = validate_photo_path(photo_path, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if photo exists
        if not full_path.exists():
            return jsonify({"error": "Photo not found"}), 404

        # Find deployment via service
        metadata = service.find_deployment_for_photo(full_path)

        if metadata is None:
            return jsonify({"error": "Deployment not found"}), 404

        # Find source path for response
        from webui.backend.lib.deployment_sidecar import find_deployment_sidecar
        source_path = find_deployment_sidecar(full_path)

        return jsonify({
            "deployment": metadata.to_dict(),
            "source_path": str(source_path) if source_path else None
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to discover deployment")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# POST /batch - Batch update operations
# ============================================================================

@deployment_bp.route("/batch", methods=["POST"])
@limiter.limit("10 per minute")
@require_api_key_or_csrf
def batch_update_deployments():
    """
    Update multiple deployments' metadata.

    Processes each directory independently, allowing partial success.
    Failed updates are reported but do not stop processing of other directories.

    Requires CSRF token OR valid API key in X-API-Key header.

    Request Body (JSON):
        {
            "updates": [
                {
                    "directory": "forest_2024",
                    "data": {"end_date": "2024-09-15"}
                },
                {
                    "directory": "meadow_2024",
                    "data": {"end_date": "2024-09-20"}
                }
            ]
        }

    Returns:
        JSON response with:
        - success: List of successfully updated directory paths (str)
        - failed: List of failed directory paths (str)
        - errors: Dictionary mapping failed paths to error messages
        - total: Total number of updates attempted
        - successful: Number of successful updates
        - failed_count: Number of failed updates

    Status Codes:
        200: Success (even with partial failures - check response for details)
        400: Invalid request (missing fields, validation error)
        500: Internal server error
        503: Service unavailable

    Rate Limiting:
        - 10 requests per minute

    Example:
        POST /api/deployment/batch
        Content-Type: application/json
        X-CSRFToken: <token>

        {
            "updates": [
                {"directory": "forest_2024", "data": {"end_date": "2024-09-15"}},
                {"directory": "meadow_2024", "data": {"end_date": "2024-09-20"}}
            ]
        }

        Response:
        {
            "success": ["forest_2024"],
            "failed": ["meadow_2024"],
            "errors": {"meadow_2024": "Deployment not found"},
            "total": 2,
            "successful": 1,
            "failed_count": 1
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
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
        if 'updates' not in data:
            return jsonify({"error": "Field 'updates' is required"}), 400

        updates = data['updates']

        # Validate updates
        if not isinstance(updates, list):
            return jsonify({"error": "Field 'updates' must be an array"}), 400

        if len(updates) == 0:
            return jsonify({"error": "Field 'updates' cannot be empty"}), 400

        if len(updates) > 100:  # Same limit as sidecar bulk operations
            return jsonify({"error": "Maximum 100 updates per request"}), 400

        # Validate each update entry
        for i, update in enumerate(updates):
            if not isinstance(update, dict):
                return jsonify({"error": f"Update at index {i} must be an object"}), 400
            if 'directory' not in update:
                return jsonify({"error": f"Update at index {i} missing 'directory' field"}), 400
            if 'data' not in update:
                return jsonify({"error": f"Update at index {i} missing 'data' field"}), 400
            if not isinstance(update['data'], dict):
                return jsonify({"error": f"Update at index {i} 'data' must be an object"}), 400

            # Validate update data
            is_valid, error_msg = _validate_deployment_input(update['data'])
            if not is_valid:
                return jsonify({"error": f"Update at index {i} validation failed: {error_msg}"}), 400

        # Process each update independently
        success_list = []
        failed_list = []
        error_dict = {}

        for index, update in enumerate(updates):
            directory = update['directory']
            update_data = update['data']

            try:
                # Path traversal protection
                full_path = validate_photo_path(directory, PHOTOS_DIR)
                if full_path is None:
                    failed_list.append({
                        "index": index,
                        "directory": directory,
                        "error": "Invalid path: Access denied"
                    })
                    error_dict[directory] = "Invalid path: Access denied"
                    continue

                # Check if directory exists
                if not full_path.exists() or not full_path.is_dir():
                    failed_list.append({
                        "index": index,
                        "directory": directory,
                        "error": "Directory not found"
                    })
                    error_dict[directory] = "Directory not found"
                    continue

                # Update via service
                metadata = service.update_deployment_metadata(full_path, update_data)

                if metadata is None:
                    failed_list.append({
                        "index": index,
                        "directory": directory,
                        "error": "Failed to update deployment metadata"
                    })
                    error_dict[directory] = "Failed to update deployment metadata"
                    continue

                # Success
                success_list.append(directory)

            except Exception as e:
                # Log error but continue processing other updates
                logger.warning(f"Error updating deployment for {directory}: {e}")
                failed_list.append({
                    "index": index,
                    "directory": directory,
                    "error": "Update failed"
                })
                error_dict[directory] = "Update failed"

        # Build response
        return jsonify({
            "success": success_list,
            "failed": failed_list,
            "errors": error_dict,
            "total": len(updates),
            "successful": len(success_list),
            "failed_count": len(failed_list)
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to batch update deployments")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# POST /generate - Generate deployment sidecars for directory
# ============================================================================

@deployment_bp.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
@require_api_key_or_csrf
def generate_deployment_sidecars():
    """
    Generate deployment sidecars for subdirectories using a template.

    Creates deployment metadata for each subdirectory that doesn't already
    have one, using the template as a base and customizing with subdirectory name.

    Requires CSRF token OR valid API key in X-API-Key header.

    Request Body (JSON):
        {
            "directory": "root_directory",
            "template": {
                "deployment_name": "Auto-generated",
                "location_name": "Default Location",
                "latitude": 35.9606,
                "longitude": -83.9207,
                ... other template fields
            }
        }

    Returns:
        JSON response with:
        - generated_count: Number of sidecars created

    Status Codes:
        200: Success
        400: Invalid request (missing fields, validation error)
        403: Invalid path or authentication failure
        404: Directory not found
        500: Internal server error
        503: Service unavailable

    Rate Limiting:
        - 10 requests per minute

    Example:
        POST /api/deployment/generate
        Content-Type: application/json
        X-CSRFToken: <token>

        {
            "directory": "surveys_2024",
            "template": {
                "deployment_name": "Auto-generated",
                "location_name": "Oak Ridge"
            }
        }

        Response:
        {
            "generated_count": 5
        }
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
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
        if 'directory' not in data:
            return jsonify({"error": "Field 'directory' is required"}), 400

        if 'template' not in data:
            return jsonify({"error": "Field 'template' is required"}), 400

        directory = data['directory']
        template = data['template']

        # Validate template
        if not isinstance(template, dict):
            return jsonify({"error": "Field 'template' must be an object"}), 400

        # Validate template data
        is_valid, error_msg = _validate_deployment_input(template)
        if not is_valid:
            return jsonify({"error": f"Template validation failed: {error_msg}"}), 400

        # Path traversal protection
        full_path = validate_photo_path(directory, PHOTOS_DIR)
        if full_path is None:
            return jsonify({"error": "Invalid path: Access denied"}), 400

        # Check if directory exists
        if not full_path.exists() or not full_path.is_dir():
            return jsonify({"error": "Directory not found"}), 404

        # Generate sidecars via service
        generated_count = service.generate_sidecars_for_directory(full_path, template)

        return jsonify({
            "generated_count": generated_count
        }), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to generate deployment sidecars")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# GET /stats - Service statistics
# ============================================================================

@deployment_bp.route("/stats", methods=["GET"])
def get_deployment_stats():
    """
    Get deployment service cache statistics.

    Returns:
        JSON response with cache metrics:
        - cache_hits: Number of cache hits
        - cache_misses: Number of cache misses
        - cache_evictions: Number of LRU evictions
        - cache_size: Current cache size
        - max_cache_size: Maximum cache size
        - cache_ttl: Cache TTL in seconds
        - hit_ratio: Cache hit ratio (0.0 to 1.0)
        - total_reads: Total read operations
        - total_writes: Total write operations
        - total_deletes: Total delete operations

    Status Codes:
        200: Success
        503: Service unavailable

    Example:
        GET /api/deployment/stats

        Response:
        {
            "cache_hits": 450,
            "cache_misses": 50,
            "cache_evictions": 10,
            "cache_size": 75,
            "max_cache_size": 100,
            "cache_ttl": 300,
            "hit_ratio": 0.90,
            "total_reads": 500,
            "total_writes": 25,
            "total_deletes": 5
        }
    """
    try:
        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Get statistics
        stats = service.get_statistics()

        return jsonify(stats), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to get statistics")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# POST /cache/invalidate - Invalidate cache
# ============================================================================

@deployment_bp.route("/cache/invalidate", methods=["POST"])
@require_api_key_or_csrf
def invalidate_deployment_cache():
    """
    Invalidate deployment service cache.

    Query Parameters:
        directory (str): Optional directory to invalidate (relative to PHOTOS_DIR)
                        If not provided, invalidates entire cache

    Requires CSRF token OR valid API key in X-API-Key header.

    Returns:
        JSON response with success status

    Status Codes:
        200: Success
        400: Invalid path
        503: Service unavailable

    Example:
        POST /api/deployment/cache/invalidate
        X-CSRFToken: <token>

        Response:
        {"success": true}

        POST /api/deployment/cache/invalidate?directory=forest_2024
        X-CSRFToken: <token>

        Response:
        {"success": true}
    """
    try:
        # Authentication: CSRF protection is enforced by Flask-WTF automatically.

        # Get deployment service
        service = current_app.config.get('DEPLOYMENT_SERVICE')
        if service is None:
            return jsonify({"error": "Service unavailable"}), 503

        # Get optional directory parameter
        directory_param = request.args.get('directory')

        if directory_param:
            # Validate path
            full_path = validate_photo_path(directory_param, PHOTOS_DIR)
            if full_path is None:
                return jsonify({"error": "Invalid path: Access denied"}), 400

            # Invalidate specific entry
            service.invalidate_cache(full_path)
        else:
            # Invalidate entire cache
            service.invalidate_cache()

        return jsonify({"success": True}), 200

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to invalidate cache")
        return jsonify({"error": error_msg}), 500


# ============================================================================
# Module exports
# ============================================================================

__all__ = ['deployment_bp']
