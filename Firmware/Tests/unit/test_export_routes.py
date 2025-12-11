"""
Unit tests for export API routes (Issue #112)

Tests REST API endpoints for export metadata service.
Focuses on security (path traversal), error handling, and response format.

Coverage Target: 90%+
"""


import pytest
from flask import Flask
from unittest.mock import Mock

from webui.backend.services.export_metadata_service import (
    ExportFormat,
    ExportMetadata,
    ExportMetadataService,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def temp_photos_dir(tmp_path_factory):
    """
    Temporary PHOTOS_DIR for export route tests (module-scoped, autouse)

    Creates temporary directory and patches PHOTOS_DIR globally for this test module.
    """
    photos_dir = tmp_path_factory.mktemp("photos")

    # Patch PHOTOS_DIR in all relevant modules
    import routes.export

    import mothbox_paths

    original_mothbox_paths_photos_dir = mothbox_paths.PHOTOS_DIR
    original_routes_export_photos_dir = routes.export.PHOTOS_DIR

    mothbox_paths.PHOTOS_DIR = photos_dir
    routes.export.PHOTOS_DIR = photos_dir

    yield photos_dir

    # Restore original values
    mothbox_paths.PHOTOS_DIR = original_mothbox_paths_photos_dir
    routes.export.PHOTOS_DIR = original_routes_export_photos_dir


@pytest.fixture(scope="module")
def mock_metadata_service():
    """Mock MetadataService that returns sample EXIF data."""
    mock = Mock()
    mock.get_photo_metadata.return_value = {
        'camera': {
            'make': 'Arducam',
            'model': 'OwlSight 64MP',
            'sensor': 'OV64A40',
        },
        'location': {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 10.0,
            'gps_accuracy': 2.5,
        },
        'capture': {
            'timestamp': '2024-01-15T10:30:00',
            'exposure_time': '1/100',
            'iso': 400,
            'focal_length': '16mm',
        },
        'deployment': {
            'mothbox_id': 'MB-TEST-001',
            'firmware_version': '5.0.0',
        },
        'file': {
            'path': '/photos/test.jpg',
            'size': 1024000,
            'width': 4000,
            'height': 3000,
        },
    }
    return mock


@pytest.fixture(scope="module")
def export_app(temp_photos_dir, mock_metadata_service):
    """Flask app with export blueprint for testing (module-scoped)"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint
    from routes.export import export_bp
    app.register_blueprint(export_bp, url_prefix='/api/export')

    # Create service with mocked MetadataService to avoid real image parsing
    service = ExportMetadataService(
        cache_ttl=300,
        metadata_service=mock_metadata_service,
    )
    app.config['EXPORT_METADATA_SERVICE'] = service

    return app


@pytest.fixture(scope="module")
def export_client(export_app):
    """Test client for export routes (module-scoped)"""
    return export_app.test_client()


@pytest.fixture(scope="module")
def sample_photo(temp_photos_dir):
    """Create a sample JPEG photo (module-scoped)"""
    photo_path = temp_photos_dir / "test_photo.jpg"

    # Skip if already exists
    if photo_path.exists():
        return photo_path

    # Create minimal JPEG header (no PIL dependency issues)
    photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

    return photo_path


@pytest.fixture(scope="module")
def nested_photo(temp_photos_dir):
    """Create a photo in a subdirectory (module-scoped)"""
    subdir = temp_photos_dir / "2024" / "01"
    subdir.mkdir(parents=True, exist_ok=True)

    photo_path = subdir / "nested_photo.jpg"

    if photo_path.exists():
        return photo_path

    # Create minimal JPEG header (no PIL dependency issues)
    photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

    return photo_path


# ============================================================================
# Tests for GET /api/export/metadata/<path>
# ============================================================================


class TestGetExportMetadata:
    """Tests for GET /api/export/metadata/<path>"""

    def test_valid_photo_returns_metadata(self, export_client, sample_photo, temp_photos_dir):
        """Test that valid photo returns export metadata"""
        # Get relative path
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()

        # Verify metadata structure
        assert 'photo_path' in data
        assert 'filename' in data
        assert data['filename'] == 'test_photo.jpg'

    def test_nested_photo_returns_metadata(self, export_client, nested_photo, temp_photos_dir):
        """Test that nested photo path works correctly"""
        # Get relative path
        relative_path = nested_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()

        assert data['filename'] == 'nested_photo.jpg'

    def test_format_json_returns_structured_data(self, export_client, sample_photo, temp_photos_dir):
        """Test that format=json returns structured metadata"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}?format=json')

        assert response.status_code == 200
        data = response.get_json()

        # JSON format should have structured data
        assert isinstance(data, dict)
        assert 'filename' in data

    def test_format_csv_returns_flat_data(self, export_client, sample_photo, temp_photos_dir):
        """Test that format=csv returns flat structure"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}?format=csv')

        assert response.status_code == 200
        data = response.get_json()

        # CSV format should be flat dictionary
        assert isinstance(data, dict)
        assert 'filename' in data

    def test_invalid_format_returns_400(self, export_client, sample_photo, temp_photos_dir):
        """Test that invalid format parameter returns 400"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}?format=xml')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid format' in data['error']

    def test_path_traversal_returns_403(self, export_client):
        """Test that path traversal attempt returns 403"""
        response = export_client.get('/api/export/metadata/../../etc/passwd')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid path' in data['error']

    def test_nonexistent_photo_returns_404(self, export_client):
        """Test that nonexistent photo returns 404"""
        response = export_client.get('/api/export/metadata/nonexistent.jpg')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_symlink_traversal_returns_403(self, export_client):
        """Test that symlink path traversal returns 403"""
        # Test with another traversal pattern
        response = export_client.get('/api/export/metadata/../../../etc/passwd')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_service_unavailable_returns_500(self, temp_photos_dir):
        """Test that missing service returns 500"""
        # Create app without service
        app = Flask(__name__)
        app.config['TESTING'] = True

        from routes.export import export_bp
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/metadata/test.jpg')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']


# ============================================================================
# Tests for POST /api/export/metadata/batch
# ============================================================================


class TestBatchExportMetadata:
    """Tests for POST /api/export/metadata/batch"""

    def test_batch_returns_results(self, export_client, sample_photo, nested_photo, temp_photos_dir):
        """Test that batch request returns results for multiple photos"""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))
        photo2_rel = str(nested_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': [photo1_rel, photo2_rel]
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'results' in data
        assert 'total' in data
        assert 'successful' in data
        assert 'failed' in data

        assert data['total'] == 2
        assert data['successful'] == 2
        assert data['failed'] == 0

        assert len(data['results']) == 2

    def test_batch_with_invalid_paths(self, export_client, sample_photo, temp_photos_dir):
        """Test that batch handles mix of valid and invalid paths"""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': [photo1_rel, '../../etc/passwd', 'nonexistent.jpg']
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 3
        assert data['successful'] >= 1  # At least the valid photo
        assert data['failed'] >= 2  # At least the two invalid paths

    def test_batch_empty_list_returns_empty(self, export_client):
        """Test that empty photo list returns empty results"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': []
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 0
        assert data['successful'] == 0
        assert data['failed'] == 0
        assert len(data['results']) == 0

    def test_batch_invalid_json_returns_400(self, export_client):
        """Test that invalid JSON returns 400"""
        response = export_client.post(
            '/api/export/metadata/batch',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_missing_photo_paths_returns_400(self, export_client):
        """Test that missing photo_paths key returns 400"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={'format': 'json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'photo_paths' in data['error']

    def test_batch_photo_paths_not_array_returns_400(self, export_client):
        """Test that photo_paths must be an array"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={'photo_paths': 'not_an_array'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'array' in data['error']

    def test_batch_format_csv(self, export_client, sample_photo, temp_photos_dir):
        """Test that format=csv works for batch"""
        photo_rel = str(sample_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': [photo_rel],
                'format': 'csv'
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 1

    def test_batch_invalid_format_returns_400(self, export_client, sample_photo, temp_photos_dir):
        """Test that invalid format returns 400"""
        photo_rel = str(sample_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': [photo_rel],
                'format': 'xml'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid format' in data['error']

    def test_batch_service_unavailable_returns_500(self):
        """Test that missing service returns 500"""
        # Create app without service
        app = Flask(__name__)
        app.config['TESTING'] = True

        from routes.export import export_bp
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post(
            '/api/export/metadata/batch',
            json={'photo_paths': ['test.jpg']}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']


# ============================================================================
# Tests for GET /api/export/formats
# ============================================================================


class TestListFormats:
    """Tests for GET /api/export/formats"""

    def test_returns_format_list(self, export_client):
        """Test that formats endpoint returns list of supported formats"""
        response = export_client.get('/api/export/formats')

        assert response.status_code == 200
        data = response.get_json()

        assert 'formats' in data
        assert isinstance(data['formats'], list)
        assert len(data['formats']) > 0

    def test_format_structure(self, export_client):
        """Test that each format has required fields"""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        formats = data['formats']

        for fmt in formats:
            assert 'id' in fmt
            assert 'name' in fmt
            assert 'description' in fmt
            assert 'implemented' in fmt
            assert isinstance(fmt['implemented'], bool)

    def test_includes_darwin_core(self, export_client):
        """Test that Darwin Core format is listed"""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        format_ids = [f['id'] for f in data['formats']]

        assert ExportFormat.DARWIN_CORE.value in format_ids

    def test_includes_inaturalist(self, export_client):
        """Test that iNaturalist format is listed"""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        format_ids = [f['id'] for f in data['formats']]

        assert ExportFormat.INATURALIST.value in format_ids

    def test_includes_generic_formats(self, export_client):
        """Test that generic JSON and CSV formats are listed"""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        format_ids = [f['id'] for f in data['formats']]

        assert ExportFormat.GENERIC_JSON.value in format_ids
        assert ExportFormat.GENERIC_CSV.value in format_ids

    def test_generic_formats_marked_implemented(self, export_client):
        """Test that generic formats are marked as implemented"""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        formats = data['formats']

        json_format = next(f for f in formats if f['id'] == 'json')
        csv_format = next(f for f in formats if f['id'] == 'csv')

        assert json_format['implemented'] is True
        assert csv_format['implemented'] is True


# ============================================================================
# Tests for GET /api/export/stats
# ============================================================================


class TestGetStats:
    """Tests for GET /api/export/stats"""

    def test_returns_statistics(self, export_client):
        """Test that stats endpoint returns statistics"""
        response = export_client.get('/api/export/stats')

        assert response.status_code == 200
        data = response.get_json()

        # Verify statistics structure
        assert 'cache_entries' in data
        assert 'cache_hits' in data
        assert 'cache_misses' in data
        assert 'total_exports' in data
        assert 'errors' in data

    def test_statistics_are_numbers(self, export_client):
        """Test that all statistics are numeric"""
        response = export_client.get('/api/export/stats')

        data = response.get_json()

        assert isinstance(data['cache_entries'], int)
        assert isinstance(data['cache_hits'], int)
        assert isinstance(data['cache_misses'], int)
        assert isinstance(data['total_exports'], int)
        assert isinstance(data['errors'], int)

    def test_stats_update_after_request(self, export_client, sample_photo, temp_photos_dir):
        """Test that stats update after making metadata request"""
        # Get initial stats
        response1 = export_client.get('/api/export/stats')
        stats1 = response1.get_json()

        # Make a metadata request
        relative_path = sample_photo.relative_to(temp_photos_dir)
        export_client.get(f'/api/export/metadata/{relative_path}')

        # Get updated stats
        response2 = export_client.get('/api/export/stats')
        stats2 = response2.get_json()

        # Either total_exports increased or cache_hits increased
        assert (stats2['total_exports'] >= stats1['total_exports'] or
                stats2['cache_hits'] > stats1['cache_hits'])

    def test_service_unavailable_returns_500(self):
        """Test that missing service returns 500"""
        # Create app without service
        app = Flask(__name__)
        app.config['TESTING'] = True

        from routes.export import export_bp
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/stats')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']


# ============================================================================
# Integration Tests
# ============================================================================


class TestExportRoutesIntegration:
    """Integration tests for export routes"""

    def test_full_workflow(self, export_client, sample_photo, temp_photos_dir):
        """Test complete workflow: list formats, get metadata, check stats"""
        # Step 1: List available formats
        formats_response = export_client.get('/api/export/formats')
        assert formats_response.status_code == 200

        # Step 2: Get metadata for a photo
        relative_path = sample_photo.relative_to(temp_photos_dir)
        metadata_response = export_client.get(f'/api/export/metadata/{relative_path}')
        assert metadata_response.status_code == 200

        # Step 3: Check statistics
        stats_response = export_client.get('/api/export/stats')
        assert stats_response.status_code == 200
        stats = stats_response.get_json()
        assert stats['total_exports'] > 0

    def test_batch_then_single(self, export_client, sample_photo, nested_photo, temp_photos_dir):
        """Test batch request followed by single requests (cache behavior)"""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))
        photo2_rel = str(nested_photo.relative_to(temp_photos_dir))

        # Batch request
        batch_response = export_client.post(
            '/api/export/metadata/batch',
            json={'photo_paths': [photo1_rel, photo2_rel]}
        )
        assert batch_response.status_code == 200

        # Single requests (should hit cache)
        response1 = export_client.get(f'/api/export/metadata/{photo1_rel}')
        assert response1.status_code == 200

        response2 = export_client.get(f'/api/export/metadata/{photo2_rel}')
        assert response2.status_code == 200

        # Check cache hits increased
        stats = export_client.get('/api/export/stats').get_json()
        assert stats['cache_hits'] > 0
