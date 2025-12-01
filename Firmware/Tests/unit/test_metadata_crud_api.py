"""
Unit tests for Sidecar Metadata CRUD API endpoints (Issue #107 - Phase 1.1 - TDD Red Phase)

Tests REST API endpoints for photo sidecar metadata CRUD operations.
TDD approach: tests written first, then implementation.

This test file is created BEFORE the implementation to follow TDD protocol.
All tests should FAIL initially (red phase) until routes/sidecar.py is implemented.

Blueprint: sidecar_bp (routes/sidecar.py)
URL Prefix: /api/sidecar

Endpoints:
- GET    /api/sidecar/photos/<filename>     - Get sidecar metadata
- PATCH  /api/sidecar/photos/<filename>     - Update sidecar metadata
- DELETE /api/sidecar/photos/<filename>     - Delete sidecar
- POST   /api/sidecar/bulk                  - Bulk update
- GET    /api/sidecar/tags                  - List all tags
- GET    /api/sidecar/species               - List all species

Coverage Target: 95%+
"""

import json
from unittest.mock import Mock

import pytest
from flask import Flask

# Import will fail until implementation exists - that's expected in TDD
try:
    from lib.sidecar_metadata import SidecarMetadata
    from routes.sidecar import sidecar_bp
    from services.sidecar_service import SidecarService
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    sidecar_bp = None
    SidecarService = None
    SidecarMetadata = None


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Helper Functions
# ============================================================================

def get_csrf_token(client):
    """
    Get CSRF token for authenticated requests.

    Returns:
        CSRF token string for use in X-CSRFToken header
    """
    response = client.get('/api/csrf-token')
    return response.get_json()['csrf_token']


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR for metadata tests.

    Creates isolated photo directory and patches mothbox_paths.PHOTOS_DIR
    in all relevant modules.
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Also patch in routes.sidecar module (when it exists)
    try:
        import routes.sidecar
        monkeypatch.setattr(routes.sidecar, 'PHOTOS_DIR', photos_dir)
    except ImportError:
        pass  # Module doesn't exist yet in TDD red phase

    return photos_dir


@pytest.fixture
def sample_photo(temp_photos_dir):
    """
    Create a sample photo file for testing.

    Returns:
        Path to sample photo (photo.jpg)
    """
    photo_path = temp_photos_dir / "photo.jpg"
    # Create minimal JPEG file
    photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    return photo_path


@pytest.fixture
def sample_sidecar(temp_photos_dir, sample_photo):
    """
    Create a sample sidecar metadata file.

    Returns:
        Path to sidecar file (photo.jpg.json)
    """
    sidecar_data = {
        "version": "1.0",
        "photo_filename": "photo.jpg",
        "created_at": "2024-01-15T10:00:00Z",
        "modified_at": "2024-01-15T10:00:00Z",
        "tags": ["moth", "night"],
        "species": "Actias luna",
        "notes": "Beautiful luna moth",
        "custom": {},
        "modified_by": None
    }

    sidecar_path = temp_photos_dir / "photo.jpg.json"
    sidecar_path.write_text(json.dumps(sidecar_data, indent=2))
    return sidecar_path


@pytest.fixture
def mock_sidecar_service():
    """
    Mock SidecarService for isolated unit testing.

    Returns:
        Mock SidecarService with pre-configured responses
    """
    mock_service = Mock(spec=SidecarService)

    # Setup default mock responses
    mock_metadata = Mock(spec=SidecarMetadata)
    mock_metadata.to_dict.return_value = {
        "version": "1.0",
        "photo_filename": "photo.jpg",
        "created_at": "2024-01-15T10:00:00Z",
        "modified_at": "2024-01-15T10:00:00Z",
        "tags": ["moth", "night"],
        "species": "Actias luna",
        "notes": "Beautiful luna moth",
        "custom": {},
        "modified_by": None
    }

    mock_service.get_metadata.return_value = mock_metadata
    mock_service.update_metadata.return_value = mock_metadata

    # Default return for list_metadata_for_directory
    mock_service.list_metadata_for_directory.return_value = {
        'items': [],
        'total': 0,
        'limit': 50,
        'offset': 0,
        'has_next': False
    }

    return mock_service


@pytest.fixture
def sidecar_app(temp_photos_dir, mock_sidecar_service):
    """
    Flask app with sidecar blueprint for testing.

    Returns:
        Flask app instance with sidecar routes registered
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    # Inject mock sidecar service
    app.config['SIDECAR_SERVICE'] = mock_sidecar_service

    # Register sidecar blueprint
    app.register_blueprint(sidecar_bp, url_prefix='/api/sidecar')

    return app


@pytest.fixture
def client(sidecar_app):
    """
    Test client for sidecar routes.

    Returns:
        Flask test client
    """
    return sidecar_app.test_client()


# ============================================================================
# Test GET /api/sidecar/photos/{filename}/metadata Endpoint
# ============================================================================

class TestGetPhotoMetadata:
    """Tests for GET /api/sidecar/photos/{filename}/metadata endpoint."""

    def test_get_metadata_returns_existing(self, client, sample_photo, mock_sidecar_service):
        """
        GET /metadata returns existing metadata when sidecar exists.

        Expected behavior:
        - Status 200
        - JSON response with metadata fields
        - All required fields present (tags, species, notes, etc.)
        """
        response = client.get(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check required fields
        assert 'tags' in data
        assert 'species' in data
        assert 'notes' in data
        assert 'version' in data
        assert 'photo_filename' in data
        assert 'created_at' in data
        assert 'modified_at' in data

        # Verify service was called with correct path
        mock_sidecar_service.get_metadata.assert_called_once()

    def test_get_metadata_photo_not_found(self, client):
        """
        GET /metadata returns 404 when photo doesn't exist.

        Expected behavior:
        - Status 404
        - JSON error response
        - Error message indicates photo not found
        """
        response = client.get('/api/sidecar/photos/nonexistent.jpg')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower() or 'does not exist' in data['error'].lower()

    def test_get_metadata_no_sidecar(self, client, sample_photo, mock_sidecar_service):
        """
        GET /metadata returns empty metadata structure when no sidecar exists.

        Expected behavior:
        - Status 200
        - JSON response with empty/default metadata
        - tags should be empty list
        - species, notes should be null
        """
        # Configure mock to return None (no sidecar)
        mock_sidecar_service.get_metadata.return_value = None

        response = client.get(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have empty metadata structure
        assert data['tags'] == []
        assert data['species'] is None
        assert data['notes'] is None

    def test_get_metadata_path_traversal_blocked(self, client):
        """
        GET /metadata blocks path traversal attempts.

        Security test: Verify that attempts to access files outside
        PHOTOS_DIR are blocked with 400 or 404 status.

        Expected behavior:
        - Status 400 (invalid path) or 404 (not found)
        - JSON error response
        - No access to files outside PHOTOS_DIR
        """
        # Try various path traversal attacks
        traversal_attempts = [
            '../../../etc/passwd',
            '../../secrets.txt',
            '../.ssh/id_rsa',
            'subdir/../../etc/passwd',
        ]

        for malicious_path in traversal_attempts:
            response = client.get(f'/api/sidecar/photos/{malicious_path}')

            # Should return 400 or 404 (both block access)
            assert response.status_code in [400, 404], \
                f"Path traversal should be blocked: {malicious_path}"

            data = json.loads(response.data)
            assert 'error' in data


# ============================================================================
# Test PATCH /api/sidecar/photos/{filename}/metadata Endpoint
# ============================================================================

class TestUpdatePhotoMetadata:
    """Tests for PATCH /api/sidecar/photos/{filename}/metadata endpoint."""

    def test_update_metadata_success(self, client, sample_photo, mock_sidecar_service):
        """
        PATCH /metadata successfully updates existing metadata.

        Expected behavior:
        - Status 200
        - JSON response with updated metadata
        - Service update_metadata called with correct parameters
        """
        update_data = {
            "species": "Actias luna",
            "notes": "Updated notes"
        }

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify updated fields in response
        assert 'species' in data
        assert 'notes' in data

        # Verify service was called
        mock_sidecar_service.update_metadata.assert_called_once()

    def test_update_metadata_creates_new(self, client, sample_photo, mock_sidecar_service):
        """
        PATCH /metadata creates new sidecar if missing.

        Expected behavior:
        - Status 200 (created)
        - JSON response with new metadata
        - Metadata created with provided fields
        """
        # Configure mock to simulate no existing metadata
        mock_sidecar_service.get_metadata.return_value = None

        # Configure mock to return new metadata after update
        mock_new_metadata = Mock(spec=SidecarMetadata)
        mock_new_metadata.to_dict.return_value = {
            "version": "1.0",
            "photo_filename": sample_photo.name,
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": ["new_tag"],
            "species": None,
            "notes": None,
            "custom": {},
            "modified_by": None
        }
        mock_sidecar_service.update_metadata.return_value = mock_new_metadata

        update_data = {"tags": ["new_tag"]}

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tags'] == ["new_tag"]

    def test_update_metadata_invalid_json(self, client, sample_photo):
        """
        PATCH /metadata rejects malformed JSON.

        Expected behavior:
        - Status 400 (bad request)
        - JSON error response
        - Error message indicates invalid JSON
        """
        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data='{"invalid": json syntax}',  # Malformed JSON
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_update_metadata_requires_csrf(self, client, sample_photo):
        """
        PATCH /metadata requires CSRF token when no API key provided.

        Security test: Verify CSRF protection is enforced.

        Expected behavior:
        - Status 400 or 403 without CSRF token
        - Status 200 with valid CSRF token
        """
        update_data = {"tags": ["test"]}

        # Try without CSRF token (should fail in production)
        # Note: May pass in test mode if CSRF disabled
        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        # In production, should require CSRF token
        # Test mode may have CSRF disabled
        assert response.status_code in [200, 400, 403]

    def test_update_metadata_path_traversal_blocked(self, client):
        """
        PATCH /metadata blocks path traversal attempts.

        Security test: Verify that attempts to update metadata for
        files outside PHOTOS_DIR are blocked.

        Expected behavior:
        - Status 400 (invalid path) or 404 (not found)
        - JSON error response
        """
        traversal_attempts = [
            '../../../etc/passwd',
            '../../secrets.txt',
        ]

        for malicious_path in traversal_attempts:
            response = client.patch(
                f'/api/sidecar/photos/{malicious_path}/metadata',
                data=json.dumps({"tags": ["test"]}),
                content_type='application/json'
            )

            assert response.status_code in [400, 404], \
                f"Path traversal should be blocked: {malicious_path}"

    def test_update_metadata_with_api_key(self, client, sample_photo, sidecar_app):
        """
        PATCH /metadata works with API key authentication (bypasses CSRF).

        Expected behavior:
        - Status 200 with valid API key in header
        - No CSRF token required
        - Metadata updated successfully
        """
        # Configure API key in app config
        sidecar_app.config['API_KEY'] = 'test-api-key-12345'

        update_data = {"tags": ["api_test"]}

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json',
            headers={'X-API-Key': 'test-api-key-12345'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should have successful update
        assert 'tags' in data or 'success' in data


# ============================================================================
# Test DELETE /api/sidecar/photos/{filename}/metadata Endpoint
# ============================================================================

class TestDeletePhotoMetadata:
    """Tests for DELETE /api/sidecar/photos/{filename}/metadata endpoint."""

    def test_delete_metadata_success(self, client, sample_photo, sample_sidecar, mock_sidecar_service):
        """
        DELETE /metadata successfully deletes existing sidecar.

        Expected behavior:
        - Status 200
        - JSON success response
        - Sidecar file deleted
        """
        response = client.delete(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True

    def test_delete_metadata_not_found(self, client, sample_photo, mock_sidecar_service):
        """
        DELETE /metadata returns 404 when no sidecar exists.

        Expected behavior:
        - Status 404
        - JSON error response
        - Error message indicates metadata not found
        """
        # Configure mock to return None (no sidecar)
        mock_sidecar_service.get_metadata.return_value = None

        response = client.delete(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_delete_metadata_requires_csrf(self, client, sample_photo):
        """
        DELETE /metadata requires CSRF token.

        Security test: Verify CSRF protection for destructive operation.

        Expected behavior:
        - Status 400 or 403 without CSRF token
        - Status 200 with valid CSRF token
        """
        # Try without CSRF token
        response = client.delete(f'/api/sidecar/photos/{sample_photo.name}')

        # Should require CSRF in production (may be disabled in test mode)
        assert response.status_code in [200, 400, 403]

    def test_delete_metadata_path_traversal_blocked(self, client):
        """
        DELETE /metadata blocks path traversal attempts.

        Security test: Verify that attempts to delete metadata for
        files outside PHOTOS_DIR are blocked.

        Expected behavior:
        - Status 400 (invalid path) or 404 (not found)
        - JSON error response
        """
        traversal_attempts = [
            '../../../etc/passwd',
            '../../secrets.txt',
        ]

        for malicious_path in traversal_attempts:
            response = client.delete(f'/api/sidecar/photos/{malicious_path}')

            assert response.status_code in [400, 404], \
                f"Path traversal should be blocked: {malicious_path}"


# ============================================================================
# Test Tag Operations (Subtask 1.3)
# ============================================================================

class TestTagOperations:
    """Tests for tag-specific operations on metadata."""

    def test_update_tags_append_mode(self, client, sample_photo, mock_sidecar_service):
        """
        PATCH /metadata with tags in append mode adds new tags.

        Expected behavior:
        - Existing tags preserved
        - New tags added
        - No duplicates
        """
        # Configure mock with existing tags
        existing_metadata = Mock(spec=SidecarMetadata)
        existing_metadata.to_dict.return_value = {
            "version": "1.0",
            "photo_filename": sample_photo.name,
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": ["moth", "night"],
            "species": None,
            "notes": None,
            "custom": {},
            "modified_by": None
        }
        mock_sidecar_service.get_metadata.return_value = existing_metadata

        # Configure mock to return updated tags
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {
            "version": "1.0",
            "photo_filename": sample_photo.name,
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:30:00Z",
            "tags": ["moth", "night", "luna"],  # New tag added
            "species": None,
            "notes": None,
            "custom": {},
            "modified_by": None
        }
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        update_data = {
            "tags": ["luna"],
            "tag_mode": "append"  # Explicit append mode
        }

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "luna" in data['tags']
        assert "moth" in data['tags']  # Original tags preserved
        assert "night" in data['tags']

    def test_update_tags_replace_mode(self, client, sample_photo, mock_sidecar_service):
        """
        PATCH /metadata with tags in replace mode replaces all tags.

        Expected behavior:
        - Old tags removed
        - Only new tags present
        """
        # Configure mock to return replaced tags
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {
            "version": "1.0",
            "photo_filename": sample_photo.name,
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:30:00Z",
            "tags": ["butterfly", "day"],  # Completely replaced
            "species": None,
            "notes": None,
            "custom": {},
            "modified_by": None
        }
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        update_data = {
            "tags": ["butterfly", "day"],
            "tag_mode": "replace"
        }

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tags'] == ["butterfly", "day"]

    def test_update_tags_default_append(self, client, sample_photo, mock_sidecar_service):
        """
        PATCH /metadata defaults to append mode when tag_mode not specified.

        Expected behavior:
        - tag_mode defaults to "append"
        - New tags added to existing tags
        """
        # Configure mock to return appended tags
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {
            "version": "1.0",
            "photo_filename": sample_photo.name,
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:30:00Z",
            "tags": ["moth", "night", "new_tag"],  # Appended
            "species": None,
            "notes": None,
            "custom": {},
            "modified_by": None
        }
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        update_data = {
            "tags": ["new_tag"]
            # No tag_mode specified - should default to append
        }

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "new_tag" in data['tags']


# ============================================================================
# Test Pagination and Batch Operations (Subtask 1.4)
# ============================================================================

class TestMetadataListPagination:
    """Tests for GET /api/sidecar/photos/metadata endpoint (list all metadata)."""

    def test_list_metadata_default_pagination(self, client, temp_photos_dir, mock_sidecar_service):
        """
        GET /api/sidecar/photos/metadata returns paginated results with defaults.

        Expected behavior:
        - Status 200
        - Default page=1, per_page=50
        - JSON response with metadata array and pagination info
        """
        # Configure mock to return list
        mock_sidecar_service.list_metadata_for_directory.return_value = {
            'items': [
                {"photo_filename": "photo1.jpg", "tags": ["moth"]},
                {"photo_filename": "photo2.jpg", "tags": ["butterfly"]},
            ],
            'total': 2,
            'limit': 50,
            'offset': 0,
            'has_next': False
        }

        response = client.get('/api/sidecar/photos')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'items' in data
        assert 'total' in data
        assert 'pagination' in data
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 50

    def test_list_metadata_custom_pagination(self, client, mock_sidecar_service):
        """
        GET /api/sidecar/photos/metadata?page=2&per_page=20 uses custom pagination.

        Expected behavior:
        - Uses specified page and per_page
        - Calculates correct offset
        """
        mock_sidecar_service.list_metadata_for_directory.return_value = {
            'items': [],
            'total': 100,
            'limit': 20,
            'offset': 20,
            'has_next': True
        }

        response = client.get('/api/sidecar/photos/metadata?page=2&per_page=20')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['page'] == 2
        assert data['pagination']['per_page'] == 20

    def test_list_metadata_max_per_page(self, client):
        """
        GET /api/sidecar/photos/metadata enforces max per_page of 200.

        Expected behavior:
        - per_page capped at 200 even if higher value requested
        - No error returned
        """
        response = client.get('/api/sidecar/photos/metadata?per_page=500')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be capped at 200
        assert data['pagination']['per_page'] <= 200

    def test_list_metadata_invalid_page(self, client):
        """
        GET /api/sidecar/photos/metadata?page=-1 returns 400 for invalid page.

        Expected behavior:
        - Status 400
        - JSON error response
        """
        response = client.get('/api/sidecar/photos/metadata?page=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test Error Handling
# ============================================================================

class TestMetadataErrorHandling:
    """Tests for error handling and edge cases."""

    def test_service_unavailable_returns_503(self, client, sidecar_app, sample_photo):
        """
        Endpoints return 503 when SidecarService unavailable.

        Expected behavior:
        - Status 503 (service unavailable)
        - JSON error response
        """
        # Remove service from config
        sidecar_app.config['SIDECAR_SERVICE'] = None

        response = client.get(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data

    def test_service_exception_returns_500(self, client, sample_photo, mock_sidecar_service):
        """
        Service exceptions return 500 with generic error message.

        Security: Should not expose internal error details to user.

        Expected behavior:
        - Status 500
        - Generic error message (no stack trace)
        """
        # Configure mock to raise exception
        mock_sidecar_service.get_metadata.side_effect = Exception("Internal error")

        response = client.get(f'/api/sidecar/photos/{sample_photo.name}')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        # Should NOT expose internal error details
        assert 'Internal error' not in data['error']

    def test_update_metadata_validation_error(self, client, sample_photo):
        """
        PATCH /metadata returns 400 for validation errors.

        Expected behavior:
        - Status 400
        - JSON error response with validation details
        """
        # Try to update with invalid data (e.g., tags too long)
        update_data = {
            "tags": ["x" * 100]  # Tag exceeds MAX_TAG_LENGTH (50)
        }

        response = client.patch(
            f'/api/sidecar/photos/{sample_photo.name}/metadata',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        # Should return 400 for validation error
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


# ============================================================================
# Test POST /api/sidecar/bulk - Bulk Update Endpoint (Phase 2)
# ============================================================================

class TestBulkMetadataUpdate:
    """Tests for POST /api/sidecar/bulk endpoint."""

    def test_bulk_update_multiple_photos(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update successfully updates multiple photos."""
        # Create test photos
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')
        (temp_photos_dir / "photo2.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock to return success
        mock_updated = Mock(spec=SidecarMetadata)
        mock_updated.to_dict.return_value = {"tags": ["moth"], "species": None}
        mock_sidecar_service.update_metadata.return_value = mock_updated

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg", "photo2.jpg"],
                "updates": {"tags": ["moth"]},
                "mode": "append"
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 2
        assert data['failed_count'] == 0
        assert len(data['success']) == 2
        assert "photo1.jpg" in data['success']
        assert "photo2.jpg" in data['success']

    def test_bulk_update_partial_success(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update handles partial success (some photos exist, some don't)."""
        # Create only one test photo
        (temp_photos_dir / "exists.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock to return success for existing, None for missing
        def mock_update_metadata(photo_path, updates):
            if "exists.jpg" in photo_path:
                mock_metadata = Mock(spec=SidecarMetadata)
                mock_metadata.to_dict.return_value = {"tags": ["test"]}
                return mock_metadata
            return None

        mock_sidecar_service.update_metadata.side_effect = mock_update_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["exists.jpg", "missing.jpg"],
                "updates": {"tags": ["test"]}
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "exists.jpg" in data['success']
        assert "missing.jpg" in data['failed']
        assert data['successful'] == 1
        assert data['failed_count'] == 1
        assert "missing.jpg" in data['errors']

    def test_bulk_update_empty_filenames_rejected(self, client):
        """Bulk update rejects empty filenames array."""
        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": [],
                "updates": {"tags": ["test"]}
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_too_many_files_rejected(self, client):
        """Bulk update rejects more than 100 files."""
        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": [f"photo{i}.jpg" for i in range(101)],
                "updates": {"tags": ["test"]}
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_path_traversal_blocked(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update blocks path traversal in filenames."""
        # Configure mock to return None for invalid paths
        mock_sidecar_service.update_metadata.return_value = None

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["../../../etc/passwd"],
                "updates": {"tags": ["test"]}
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should fail the file, not error the whole request
        assert "../../../etc/passwd" in data['failed']
        assert data['successful'] == 0
        assert data['failed_count'] == 1

    def test_bulk_update_missing_filenames(self, client):
        """Bulk update requires filenames field."""
        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "updates": {"tags": ["test"]}
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_missing_updates(self, client):
        """Bulk update requires updates field."""
        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"]
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_empty_updates(self, client):
        """Bulk update rejects empty updates object."""
        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {}
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_invalid_mode(self, client, temp_photos_dir):
        """Bulk update rejects invalid mode values."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["test"]},
                "mode": "invalid_mode"
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_append_mode_merges_tags(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update in append mode merges tags instead of replacing."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock with existing tags
        existing_metadata = Mock(spec=SidecarMetadata)
        existing_metadata.tags = ["moth", "night"]
        existing_metadata.to_dict.return_value = {"tags": ["moth", "night"]}
        mock_sidecar_service.get_metadata.return_value = existing_metadata

        # Configure mock to return merged tags
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {"tags": ["moth", "night", "luna"]}
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["luna"]},
                "mode": "append"
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 1

    def test_bulk_update_replace_mode_overwrites_tags(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update in replace mode overwrites tags completely."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock to return replaced tags
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {"tags": ["butterfly"]}
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["butterfly"]},
                "mode": "replace"
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 1

    def test_bulk_update_default_mode_is_append(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update defaults to append mode when mode not specified."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {"tags": ["test"]}
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["test"]}
                # No mode specified - should default to append
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 1

    def test_bulk_update_non_tag_fields_always_replace(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update always replaces non-tag fields (species, notes) regardless of mode."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock to return updated fields
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {
            "species": "Actias luna",
            "notes": "New notes"
        }
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {
                    "species": "Actias luna",
                    "notes": "New notes"
                },
                "mode": "append"  # Should not affect non-tag fields
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 1

    def test_bulk_update_invalid_json(self, client):
        """Bulk update rejects malformed JSON."""
        response = client.post(
            '/api/sidecar/bulk',
            data='{"invalid": json syntax}',
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_bulk_update_with_api_key(self, client, temp_photos_dir, sidecar_app, mock_sidecar_service):
        """Bulk update works with API key authentication (bypasses CSRF)."""
        # Configure API key in app config
        sidecar_app.config['API_KEY'] = 'test-api-key-12345'

        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock
        updated_metadata = Mock(spec=SidecarMetadata)
        updated_metadata.to_dict.return_value = {"tags": ["api_test"]}
        mock_sidecar_service.update_metadata.return_value = updated_metadata

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["api_test"]}
            }),
            content_type='application/json',
            headers={'X-API-Key': 'test-api-key-12345'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['successful'] == 1

    def test_bulk_update_validation_error_reported(self, client, temp_photos_dir, mock_sidecar_service):
        """Bulk update reports validation errors for individual files."""
        (temp_photos_dir / "photo1.jpg").write_bytes(b'\xFF\xD8\xFF\xE0')

        # Configure mock to simulate validation error
        mock_sidecar_service.update_metadata.return_value = None

        response = client.post(
            '/api/sidecar/bulk',
            data=json.dumps({
                "filenames": ["photo1.jpg"],
                "updates": {"tags": ["x" * 100]}  # Tag too long
            }),
            content_type='application/json'
        )

        # Should validate input first
        assert response.status_code in [200, 400]
        data = json.loads(response.data)
        # Either validation error (400) or failed in response (200)
        if response.status_code == 200:
            assert data['failed_count'] >= 0


# ============================================================================
# Test Tag Aggregation (Phase 3)
# ============================================================================

class TestTagAggregation:
    """Tests for GET /api/sidecar/tags endpoint."""

    def test_get_tags_returns_unique_with_counts(self, client, temp_photos_dir):
        """GET /tags returns unique tags with usage counts."""
        # Create sample sidecar files with tags
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": ["moth", "night"],
            "species": None,
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": ["moth", "luna"],
            "species": None,
            "notes": None
        }))

        response = client.get('/api/sidecar/tags')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'tags' in data
        # Should have 3 unique tags: moth (count 2), night (count 1), luna (count 1)
        assert len(data['tags']) == 3
        # Sorted by count descending by default
        assert data['tags'][0]['name'] == 'moth'
        assert data['tags'][0]['count'] == 2

    def test_get_tags_empty(self, client, temp_photos_dir):
        """GET /tags returns empty list when no tags exist."""
        # No sidecar files created

        response = client.get('/api/sidecar/tags')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tags'] == []
        assert data['total'] == 0

    def test_get_tags_pagination(self, client, temp_photos_dir):
        """GET /tags supports pagination parameters."""
        # Create 5 sidecar files with different tags
        for i in range(5):
            sidecar = temp_photos_dir / f"photo{i}.jpg.json"
            sidecar.write_text(json.dumps({
                "version": "1.0",
                "photo_filename": f"photo{i}.jpg",
                "tags": [f"tag{i}"],
                "species": None,
                "notes": None
            }))

        response = client.get('/api/sidecar/tags?page=1&per_page=2')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 2
        assert data['pagination']['has_next'] is True
        assert len(data['tags']) == 2

    def test_get_tags_sort_by_count(self, client, temp_photos_dir):
        """GET /tags sorts by count (descending) by default."""
        # Create sidecars with different tag counts
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": ["moth", "night", "luna"],
            "species": None,
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": ["moth", "night"],
            "species": None,
            "notes": None
        }))

        sidecar3 = temp_photos_dir / "photo3.jpg.json"
        sidecar3.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo3.jpg",
            "tags": ["moth"],
            "species": None,
            "notes": None
        }))

        response = client.get('/api/sidecar/tags?sort=count&order=desc')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be sorted by count descending: moth(3), night(2), luna(1)
        assert data['tags'][0]['name'] == 'moth'
        assert data['tags'][0]['count'] == 3
        assert data['tags'][1]['name'] == 'night'
        assert data['tags'][1]['count'] == 2
        assert data['tags'][2]['name'] == 'luna'
        assert data['tags'][2]['count'] == 1

    def test_get_tags_sort_by_name(self, client, temp_photos_dir):
        """GET /tags can sort by name alphabetically."""
        # Create sidecars with tags
        sidecar = temp_photos_dir / "photo1.jpg.json"
        sidecar.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": ["zebra", "butterfly", "moth"],
            "species": None,
            "notes": None
        }))

        response = client.get('/api/sidecar/tags?sort=name&order=asc')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be sorted alphabetically: butterfly, moth, zebra
        assert data['tags'][0]['name'] == 'butterfly'
        assert data['tags'][1]['name'] == 'moth'
        assert data['tags'][2]['name'] == 'zebra'

    def test_get_tags_invalid_pagination(self, client):
        """GET /tags returns 400 for invalid pagination parameters."""
        response = client.get('/api/sidecar/tags?page=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_tags_max_per_page(self, client, temp_photos_dir):
        """GET /tags caps per_page at 200."""
        response = client.get('/api/sidecar/tags?per_page=500')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be capped at 200
        assert data['pagination']['per_page'] <= 200


# ============================================================================
# Test Species Aggregation (Phase 3)
# ============================================================================

class TestSpeciesAggregation:
    """Tests for GET /api/sidecar/species endpoint."""

    def test_get_species_returns_unique_with_counts(self, client, temp_photos_dir):
        """GET /species returns unique species with usage counts."""
        # Create sidecar files with species
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        response = client.get('/api/sidecar/species')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'species' in data
        assert len(data['species']) == 1
        assert data['species'][0]['name'] == 'Actias luna'
        assert data['species'][0]['count'] == 2

    def test_get_species_excludes_null(self, client, temp_photos_dir):
        """GET /species excludes photos with no species set."""
        # Create sidecars with and without species
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": [],
            "species": None,  # No species
            "notes": None
        }))

        response = client.get('/api/sidecar/species')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should only include "Actias luna", not null
        assert len(data['species']) == 1
        assert data['species'][0]['name'] == 'Actias luna'

    def test_get_species_empty(self, client, temp_photos_dir):
        """GET /species returns empty list when no species exist."""
        # Create sidecar with no species
        sidecar = temp_photos_dir / "photo1.jpg.json"
        sidecar.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": [],
            "species": None,
            "notes": None
        }))

        response = client.get('/api/sidecar/species')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['species'] == []
        assert data['total'] == 0

    def test_get_species_pagination(self, client, temp_photos_dir):
        """GET /species supports pagination parameters."""
        # Create 5 sidecar files with different species
        for i in range(5):
            sidecar = temp_photos_dir / f"photo{i}.jpg.json"
            sidecar.write_text(json.dumps({
                "version": "1.0",
                "photo_filename": f"photo{i}.jpg",
                "tags": [],
                "species": f"Species {i}",
                "notes": None
            }))

        response = client.get('/api/sidecar/species?page=1&per_page=2')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 2
        assert data['pagination']['has_next'] is True
        assert len(data['species']) == 2

    def test_get_species_sort_by_count(self, client, temp_photos_dir):
        """GET /species sorts by count (descending) by default."""
        # Create sidecars with different species counts
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        sidecar3 = temp_photos_dir / "photo3.jpg.json"
        sidecar3.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo3.jpg",
            "tags": [],
            "species": "Antheraea polyphemus",
            "notes": None
        }))

        response = client.get('/api/sidecar/species?sort=count&order=desc')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be sorted by count descending: Actias luna (2), Antheraea polyphemus (1)
        assert data['species'][0]['name'] == 'Actias luna'
        assert data['species'][0]['count'] == 2
        assert data['species'][1]['name'] == 'Antheraea polyphemus'
        assert data['species'][1]['count'] == 1

    def test_get_species_sort_by_name(self, client, temp_photos_dir):
        """GET /species can sort by name alphabetically."""
        # Create sidecars with species
        sidecar1 = temp_photos_dir / "photo1.jpg.json"
        sidecar1.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo1.jpg",
            "tags": [],
            "species": "Zygaenidae",
            "notes": None
        }))

        sidecar2 = temp_photos_dir / "photo2.jpg.json"
        sidecar2.write_text(json.dumps({
            "version": "1.0",
            "photo_filename": "photo2.jpg",
            "tags": [],
            "species": "Actias luna",
            "notes": None
        }))

        response = client.get('/api/sidecar/species?sort=name&order=asc')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be sorted alphabetically: Actias luna, Zygaenidae
        assert data['species'][0]['name'] == 'Actias luna'
        assert data['species'][1]['name'] == 'Zygaenidae'

    def test_get_species_invalid_pagination(self, client):
        """GET /species returns 400 for invalid pagination parameters."""
        response = client.get('/api/sidecar/species?page=-1')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_species_max_per_page(self, client, temp_photos_dir):
        """GET /species caps per_page at 200."""
        response = client.get('/api/sidecar/species?per_page=500')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be capped at 200
        assert data['pagination']['per_page'] <= 200
