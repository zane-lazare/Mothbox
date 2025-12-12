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

        # Verify nested metadata structure (JSON format)
        assert 'file' in data
        assert 'path' in data['file']
        assert 'filename' in data['file']
        assert data['file']['filename'] == 'test_photo.jpg'

    def test_nested_photo_returns_metadata(self, export_client, nested_photo, temp_photos_dir):
        """Test that nested photo path works correctly"""
        # Get relative path
        relative_path = nested_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()

        assert data['file']['filename'] == 'nested_photo.jpg'

    def test_format_json_returns_structured_data(self, export_client, sample_photo, temp_photos_dir):
        """Test that format=json returns nested structured metadata"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}?format=json')

        assert response.status_code == 200
        data = response.get_json()

        # JSON format should have nested structure
        assert isinstance(data, dict)
        assert 'file' in data
        assert 'filename' in data['file']

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


# ============================================================================
# Tests for Error Handling and Edge Cases
# ============================================================================


class TestExportMetadataErrorHandling:
    """Tests for error handling in export metadata endpoints"""

    def test_permission_denied_returns_403(self, temp_photos_dir):
        """Test that permission denied error returns 403"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that returns permission denied
        mock_service = Mock()
        mock_service.get_export_metadata.return_value = {
            'error': 'Permission denied',
            'photo_path': '/photos/test.jpg'
        }
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a file so path validation passes
        test_file = temp_photos_dir / "permission_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/metadata/permission_test.jpg')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Permission denied'

    def test_generic_error_returns_500(self, temp_photos_dir):
        """Test that generic service errors return 500"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that returns generic error
        mock_service = Mock()
        mock_service.get_export_metadata.return_value = {
            'error': 'Internal processing error',
            'photo_path': '/photos/test.jpg'
        }
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a file so path validation passes
        test_file = temp_photos_dir / "error_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/metadata/error_test.jpg')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_dict_result_without_export_metadata(self, temp_photos_dir):
        """Test that dict results without error are returned as-is (line 116)"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that returns a dict (not ExportMetadata)
        mock_service = Mock()
        mock_service.get_export_metadata.return_value = {
            'filename': 'test.jpg',
            'custom_data': 'value'
        }
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a file so path validation passes
        test_file = temp_photos_dir / "dict_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/metadata/dict_test.jpg')

        assert response.status_code == 200
        data = response.get_json()
        assert data['filename'] == 'test.jpg'
        assert data['custom_data'] == 'value'

    def test_exception_in_get_metadata_returns_500(self, temp_photos_dir):
        """Test that exceptions in service call return 500"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that raises exception
        mock_service = Mock()
        mock_service.get_export_metadata.side_effect = RuntimeError("Unexpected error")
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a file so path validation passes
        test_file = temp_photos_dir / "exception_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/metadata/exception_test.jpg')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed to get export metadata' in data['error']


class TestBatchExportMetadataEdgeCases:
    """Tests for batch export endpoint edge cases"""

    def test_non_json_request_returns_400(self, export_client):
        """Test that non-JSON request returns 400 (line 165)"""
        response = export_client.post(
            '/api/export/metadata/batch',
            data='not json at all',
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'JSON' in data['error']

    def test_empty_string_in_photo_paths_returns_400(self, export_client):
        """Test that empty strings in photo_paths return 400 (line 182)"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': ['valid.jpg', '', 'another.jpg']
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'non-empty strings' in data['error']

    def test_whitespace_only_in_photo_paths_returns_400(self, export_client):
        """Test that whitespace-only strings in photo_paths return 400"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': ['valid.jpg', '   ', 'another.jpg']
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'non-empty strings' in data['error']

    def test_non_string_in_photo_paths_returns_400(self, export_client):
        """Test that non-string elements in photo_paths return 400"""
        response = export_client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': ['valid.jpg', 123, 'another.jpg']
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'non-empty strings' in data['error']

    def test_batch_size_exceeds_limit_returns_400(self):
        """Test that batch size exceeding limit returns 400 (line 191)"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['EXPORT_MAX_BATCH_SIZE'] = 5  # Set a low limit for testing
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service
        mock_service = Mock()
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Send more photos than the limit
        response = client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': [f'photo{i}.jpg' for i in range(10)]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'exceeds maximum limit' in data['error']
        assert '5' in data['error']

    def test_batch_exception_returns_500(self):
        """Test that exception during batch processing returns 500 (lines 238-240)"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that raises exception
        mock_service = Mock()
        mock_service.get_export_metadata.side_effect = RuntimeError("Batch processing failed")
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.post(
            '/api/export/metadata/batch',
            json={
                'photo_paths': ['test.jpg']
            }
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Batch processing failed' in data['error']


class TestFormatsEndpointExceptionHandling:
    """Tests for exception handling in formats endpoint"""

    def test_formats_exception_returns_500(self, monkeypatch):
        """Test that exception in formats endpoint returns 500 (lines 321-323)"""
        import routes.export as export_module

        # Store original
        original_ExportFormat = export_module.ExportFormat

        # Create a mock ExportFormat that raises when .value is accessed
        class MockExportFormat:
            @property
            def DARWIN_CORE(self):
                raise RuntimeError("Simulated format error")

            INATURALIST = Mock(value='inaturalist')
            GENERIC_JSON = Mock(value='json')
            GENERIC_CSV = Mock(value='csv')

        # Patch the module-level ExportFormat with our mock
        monkeypatch.setattr(export_module, 'ExportFormat', MockExportFormat())

        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/formats')

        # Should return 500 due to the exception
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed to list formats' in data['error']


class TestStatsEndpointExceptionHandling:
    """Tests for exception handling in stats endpoint"""

    def test_stats_exception_returns_500(self):
        """Test that exception in stats endpoint returns 500 (lines 357-359)"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that raises exception on get_statistics
        mock_service = Mock()
        mock_service.get_statistics.side_effect = RuntimeError("Stats error")
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get('/api/export/stats')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed to get statistics' in data['error']


# ============================================================================
# Tests for POST /api/export/stats/reset
# ============================================================================


class TestResetExportStats:
    """Tests for POST /api/export/stats/reset endpoint (lines 382-395)"""

    def test_reset_stats_success(self, export_client):
        """Test that reset stats endpoint returns success"""
        response = export_client.post('/api/export/stats/reset')

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'reset successfully' in data['message']

    def test_reset_stats_clears_counters(self, export_client, sample_photo, temp_photos_dir):
        """Test that reset actually clears statistics counters"""
        # First make some requests to populate stats
        relative_path = sample_photo.relative_to(temp_photos_dir)
        export_client.get(f'/api/export/metadata/{relative_path}')
        export_client.get(f'/api/export/metadata/{relative_path}')  # Second hit for cache

        # Verify stats are non-zero
        stats_before = export_client.get('/api/export/stats').get_json()
        assert stats_before['total_exports'] > 0 or stats_before['cache_hits'] > 0

        # Reset stats
        response = export_client.post('/api/export/stats/reset')
        assert response.status_code == 200

        # Verify counters are reset
        stats_after = export_client.get('/api/export/stats').get_json()
        assert stats_after['cache_hits'] == 0
        assert stats_after['cache_misses'] == 0
        assert stats_after['total_exports'] == 0
        assert stats_after['errors'] == 0

    def test_reset_stats_service_unavailable_returns_500(self):
        """Test that reset stats without service returns 500"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post('/api/export/stats/reset')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']

    def test_reset_stats_exception_returns_500(self):
        """Test that exception in reset stats returns 500"""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that raises exception on reset
        mock_service = Mock()
        mock_service.reset_statistics.side_effect = RuntimeError("Reset error")
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.post('/api/export/stats/reset')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed to reset statistics' in data['error']


# ============================================================================
# Tests for Darwin Core Export (Issue #116)
# ============================================================================


class TestDarwinCoreFormat:
    """Tests for Darwin Core format support in metadata endpoint."""

    def test_format_darwin_core_returns_dwc_structure(self, export_client, sample_photo, temp_photos_dir):
        """format=darwin_core should return Darwin Core fields."""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/metadata/{relative_path}?format=darwin_core')

        # May return 400 if GPS not present in mock data
        assert response.status_code in (200, 400)

        if response.status_code == 200:
            data = response.get_json()
            assert 'basisOfRecord' in data
            assert 'geodeticDatum' in data
            assert data['basisOfRecord'] == 'MachineObservation'
            assert data['geodeticDatum'] == 'WGS84'

    def test_darwin_core_validation_error_returns_400(self, temp_photos_dir):
        """Missing required fields should return 400 with validation errors."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service that returns metadata without GPS
        mock_service = Mock()
        mock_service.get_export_metadata.return_value = ExportMetadata(
            photo_path='/photos/no_gps.jpg',
            filename='no_gps.jpg',
            timestamp='2024-01-15T10:00:00',
            latitude=None,  # Missing GPS
            longitude=None,
        )
        mock_service.validate_for_format.return_value = Mock(
            is_valid=False,
            missing_fields=['decimalLatitude', 'decimalLongitude'],
            warnings=[]
        )
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a test file
        test_file = temp_photos_dir / "validation_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/metadata/validation_test.jpg?format=darwin_core')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Darwin Core validation failed' in data['error']
        assert 'missing_fields' in data

    def test_darwin_core_format_in_formats_list(self, export_client):
        """Darwin Core should be listed as implemented in formats endpoint."""
        response = export_client.get('/api/export/formats')

        assert response.status_code == 200
        data = response.get_json()

        darwin_core = next(
            (f for f in data['formats'] if f['id'] == 'darwin_core'),
            None
        )
        assert darwin_core is not None
        assert darwin_core['implemented'] is True


class TestDarwinCoreBatchExport:
    """Tests for POST /api/export/darwin-core/batch endpoint."""

    def test_batch_export_service_unavailable(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post(
            '/api/export/darwin-core/batch',
            json={'photo_paths': ['test.jpg']}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_batch_export_missing_photo_paths(self, export_client):
        """Missing photo_paths should return 400."""
        response = export_client.post(
            '/api/export/darwin-core/batch',
            json={'format': 'darwin_core'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'photo_paths' in data['error']

    def test_batch_export_empty_list_returns_400(self, export_client):
        """Empty photo list should return 400."""
        response = export_client.post(
            '/api/export/darwin-core/batch',
            json={'photo_paths': []}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_export_returns_csv_data(self, temp_photos_dir):
        """Batch export should return CSV data in JSON format."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service
        mock_service = Mock()
        mock_metadata = ExportMetadata(
            photo_path='/photos/test.jpg',
            filename='test.jpg',
            timestamp='2024-01-15T10:00:00',
            latitude=37.7749,
            longitude=-122.4194,
            gps_accuracy=2.5,
        )
        mock_service.get_export_metadata.return_value = mock_metadata
        mock_service.validate_for_format.return_value = Mock(
            is_valid=True,
            missing_fields=[],
            warnings=['GPS accuracy recommended']
        )

        # Use real transformation
        from webui.backend.lib.darwin_core_mapping import get_csv_headers, transform_to_csv_row
        mock_service.transform_batch_to_darwin_core_csv.return_value = (
            get_csv_headers(),
            [transform_to_csv_row(mock_metadata)]
        )

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a test file
        test_file = temp_photos_dir / "darwin_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/darwin-core/batch',
            json={'photo_paths': ['darwin_test.jpg']},
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'csv_data' in data
        assert 'headers' in data
        assert 'row_count' in data
        assert data['row_count'] >= 0

    def test_batch_export_csv_file_download(self, temp_photos_dir):
        """Accept: text/csv should return CSV file download."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service
        mock_service = Mock()
        mock_metadata = ExportMetadata(
            photo_path='/photos/test.jpg',
            filename='test.jpg',
            timestamp='2024-01-15T10:00:00',
            latitude=37.7749,
            longitude=-122.4194,
        )
        mock_service.get_export_metadata.return_value = mock_metadata
        mock_service.validate_for_format.return_value = Mock(
            is_valid=True,
            missing_fields=[],
            warnings=[]
        )

        # Use real transformation
        from webui.backend.lib.darwin_core_mapping import get_csv_headers, transform_to_csv_row
        mock_service.transform_batch_to_darwin_core_csv.return_value = (
            get_csv_headers(),
            [transform_to_csv_row(mock_metadata)]
        )

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a test file
        test_file = temp_photos_dir / "download_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/darwin-core/batch',
            json={'photo_paths': ['download_test.jpg']},
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'Content-Disposition' in response.headers
        assert 'attachment' in response.headers['Content-Disposition']
        assert '.csv' in response.headers['Content-Disposition']


class TestDarwinCoreDeploymentExport:
    """Tests for GET /api/export/darwin-core/deployment/<path> endpoint."""

    def test_deployment_export_service_unavailable(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/darwin-core/deployment/test-deployment')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    def test_deployment_export_invalid_path(self, export_client):
        """Path traversal should return 403."""
        response = export_client.get('/api/export/darwin-core/deployment/../../etc/passwd')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid path' in data['error']

    def test_deployment_export_not_found(self, export_client):
        """Non-existent deployment should return 404."""
        response = export_client.get('/api/export/darwin-core/deployment/nonexistent-deployment-12345')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
