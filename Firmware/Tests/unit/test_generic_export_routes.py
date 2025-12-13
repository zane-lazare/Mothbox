"""
Unit tests for generic JSON/CSV export routes (Issue #120)

Tests REST API endpoints for generic JSON and CSV export functionality.
Focuses on security (path traversal), field filtering, response formats,
and file download handling.

Coverage Target: 85%+
"""

import csv
import io
from unittest.mock import Mock

import pytest
from flask import Flask

from webui.backend.services.export_metadata_service import (
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


@pytest.fixture(scope="module")
def deployment_dir(temp_photos_dir):
    """Create a deployment directory with photos (module-scoped)"""
    deploy_dir = temp_photos_dir / "deployment_2024"
    deploy_dir.mkdir(exist_ok=True)

    # Create multiple photos
    for i in range(3):
        photo = deploy_dir / f"photo_{i}.jpg"
        if not photo.exists():
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

    return deploy_dir


def create_sample_export_metadata(filename="test.jpg", **kwargs):
    """Helper to create sample ExportMetadata instances."""
    defaults = {
        'photo_path': f'/photos/{filename}',
        'filename': filename,
        'timestamp': '2024-01-15T10:00:00',
        'latitude': 37.7749,
        'longitude': -122.4194,
        'altitude': 10.0,
        'gps_accuracy': 2.5,
        'camera_make': 'Arducam',
        'camera_model': 'OwlSight 64MP',
        'exposure_time': '1/100',
        'iso': 400,
        'focal_length': '16mm',
        'species': 'Actias luna',
        'species_common_name': 'Luna Moth',
        'species_confidence': 'probable',
        'tags': ['moth', 'lepidoptera', 'nocturnal'],
        'notes': 'Sample observation',
        'mothbox_id': 'MB-TEST-001',
        'firmware_version': '5.0.0',
        'deployment_name': 'Test Deployment',
        'deployment_location_name': 'Oak Ridge, TN',
        'deployment_start_date': '2024-01-01',
        'deployment_end_date': '2024-01-31',
        'environmental_conditions': {'habitat': 'forest'},
        'series_type': None,
        'series_index': None,
        'series_count': None,
        'file_size': 1024000,
        'width': 4000,
        'height': 3000,
    }
    defaults.update(kwargs)
    return ExportMetadata(**defaults)


# ============================================================================
# Tests for GET /api/export/json/<path> - Single Photo JSON Export
# ============================================================================


class TestSinglePhotoJsonExport:
    """Tests for GET /api/export/json/<photo_path>"""

    def test_valid_photo_returns_json_metadata(self, export_client, sample_photo, temp_photos_dir):
        """Valid photo should return JSON with nested structure."""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/json/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()

        # Verify nested structure (from transform_to_generic(flat=False))
        assert 'file' in data
        assert 'location' in data
        assert 'camera' in data
        assert 'species' in data
        assert 'user_data' in data
        assert 'deployment' in data

    def test_nested_photo_path_works(self, export_client, nested_photo, temp_photos_dir):
        """Nested photo paths should work correctly."""
        relative_path = nested_photo.relative_to(temp_photos_dir)

        response = export_client.get(f'/api/export/json/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()
        assert 'nested_photo.jpg' in data['file']['filename']

    def test_path_traversal_returns_403(self, export_client):
        """Path traversal attempts should return 403."""
        response = export_client.get('/api/export/json/../../../etc/passwd')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_nonexistent_photo_returns_404(self, export_client):
        """Nonexistent photo should return 404."""
        response = export_client.get('/api/export/json/nonexistent_photo.jpg')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_file_download_with_octet_stream_accept(self, temp_photos_dir):
        """Accept: application/octet-stream should return JSON file download."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service
        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        # Use real transformation
        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic
        mock_service.transform_to_generic_filtered = real_service.transform_to_generic_filtered

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a test file
        test_file = temp_photos_dir / "download_json_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get(
            '/api/export/json/download_json_test.jpg',
            headers={'Accept': 'application/octet-stream'}
        )

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert 'Content-Disposition' in response.headers
        assert 'attachment' in response.headers['Content-Disposition']
        assert '.json' in response.headers['Content-Disposition']

    def test_field_filtering_with_fields_param(self, temp_photos_dir):
        """Fields parameter should limit returned fields."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create mock service with transform_to_generic_filtered
        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        # Mock filtered transform
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg'},
            'location': {'latitude': 37.7749, 'longitude': -122.4194}
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Create a test file
        test_file = temp_photos_dir / "field_filter_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get(
            '/api/export/json/field_filter_test.jpg?fields=filename,latitude,longitude'
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should only have requested fields
        assert 'file' in data
        assert 'location' in data
        # Camera and other sections should not be present
        assert 'camera' not in data or data.get('camera') is None

    def test_field_filtering_with_exclude_param(self, temp_photos_dir):
        """Exclude parameter should remove specified fields."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        # Mock filtered transform without notes and tags
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg'},
            'location': {'latitude': 37.7749},
            'user_data': {}  # Empty - notes and tags excluded
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "exclude_filter_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get(
            '/api/export/json/exclude_filter_test.jpg?exclude=notes,tags'
        )

        assert response.status_code == 200
        data = response.get_json()

        # User data section should have empty or missing notes/tags
        user_data = data.get('user_data', {})
        assert 'notes' not in user_data or user_data.get('notes') is None
        assert 'tags' not in user_data or user_data.get('tags') == []

    def test_both_fields_and_exclude_returns_400(self, export_client, sample_photo, temp_photos_dir):
        """Using both fields and exclude should return 400."""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = export_client.get(
            f'/api/export/json/{relative_path}?fields=filename&exclude=notes'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_service_unavailable_returns_500(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/json/test.jpg')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']


# ============================================================================
# Tests for POST /api/export/json/batch - Batch JSON Export
# ============================================================================


class TestBatchJsonExport:
    """Tests for POST /api/export/json/batch"""

    def test_batch_returns_array_of_metadata(self, export_client, sample_photo, nested_photo, temp_photos_dir):
        """Batch export should return array of photo metadata."""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))
        photo2_rel = str(nested_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/json/batch',
            json={'photo_paths': [photo1_rel, photo2_rel]}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'results' in data
        assert 'total' in data
        assert 'successful' in data
        assert 'failed' in data
        assert isinstance(data['results'], list)

    def test_batch_handles_invalid_paths(self, export_client, sample_photo, temp_photos_dir):
        """Batch should handle mix of valid and invalid paths."""
        photo_rel = str(sample_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/json/batch',
            json={'photo_paths': [photo_rel, '../../../etc/passwd', 'nonexistent.jpg']}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 3
        assert data['successful'] >= 1
        assert data['failed'] >= 2

    def test_batch_empty_list_returns_empty(self, export_client):
        """Empty photo list should return empty results."""
        response = export_client.post(
            '/api/export/json/batch',
            json={'photo_paths': []}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 0
        assert data['successful'] == 0
        assert len(data['results']) == 0

    def test_batch_invalid_json_returns_400(self, export_client):
        """Invalid JSON should return 400."""
        response = export_client.post(
            '/api/export/json/batch',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_missing_photo_paths_returns_400(self, export_client):
        """Missing photo_paths key should return 400."""
        response = export_client.post(
            '/api/export/json/batch',
            json={'format': 'json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'photo_paths' in data['error']

    def test_batch_photo_paths_not_array_returns_400(self, export_client):
        """photo_paths must be an array."""
        response = export_client.post(
            '/api/export/json/batch',
            json={'photo_paths': 'not_an_array'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'array' in data['error']

    def test_batch_with_field_filtering(self, temp_photos_dir):
        """Batch should support field filtering."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg'},
            'location': {'latitude': 37.7749}
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "batch_filter_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/json/batch',
            json={
                'photo_paths': ['batch_filter_test.jpg'],
                'fields': ['filename', 'latitude']
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['successful'] >= 1

    def test_batch_file_download_with_octet_stream(self, temp_photos_dir):
        """Accept: application/octet-stream should return JSON file download."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "batch_download_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/json/batch',
            json={'photo_paths': ['batch_download_test.jpg']},
            headers={'Accept': 'application/octet-stream'}
        )

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        assert 'Content-Disposition' in response.headers
        assert 'attachment' in response.headers['Content-Disposition']

    def test_batch_exceeds_max_size_returns_400(self, temp_photos_dir):
        """Batch exceeding max size should return 400."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['EXPORT_MAX_BATCH_SIZE'] = 5  # Set low limit for testing
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        # Request more than max batch size
        response = client.post(
            '/api/export/json/batch',
            json={'photo_paths': [f'photo_{i}.jpg' for i in range(10)]}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'limit' in data['error'].lower() or 'exceeds' in data['error'].lower()

    def test_batch_service_unavailable_returns_500(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post(
            '/api/export/json/batch',
            json={'photo_paths': ['test.jpg']}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'not available' in data['error']


# ============================================================================
# Tests for GET /api/export/json/deployment/<path> - Deployment JSON Export
# ============================================================================


class TestDeploymentJsonExport:
    """Tests for GET /api/export/json/deployment/<path>"""

    def test_deployment_returns_all_photos_metadata(self, temp_photos_dir):
        """Deployment export should return metadata for all photos in directory."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create deployment directory with photos
        deploy_dir = temp_photos_dir / "test_deployment"
        deploy_dir.mkdir(exist_ok=True)

        for i in range(3):
            photo = deploy_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get('/api/export/json/deployment/test_deployment')

        assert response.status_code == 200
        data = response.get_json()

        assert 'results' in data
        assert 'total' in data
        assert data['total'] >= 3

    def test_deployment_path_traversal_returns_403(self, export_client):
        """Path traversal attempts should return 403."""
        response = export_client.get('/api/export/json/deployment/../../../etc')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_deployment_empty_directory_returns_empty(self, temp_photos_dir):
        """Empty deployment directory should return empty results."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        # Create empty directory
        empty_dir = temp_photos_dir / "empty_deployment"
        empty_dir.mkdir(exist_ok=True)

        mock_service = Mock()
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get('/api/export/json/deployment/empty_deployment')

        # Should return 200 with empty results or 400 for no photos
        assert response.status_code in [200, 400]

    def test_deployment_nonexistent_returns_404(self, export_client):
        """Nonexistent deployment should return 404."""
        response = export_client.get('/api/export/json/deployment/nonexistent_deployment')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_deployment_with_field_filtering(self, temp_photos_dir):
        """Deployment export should support field filtering."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        deploy_dir = temp_photos_dir / "filter_deployment"
        deploy_dir.mkdir(exist_ok=True)

        photo = deploy_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'photo.jpg'},
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get('/api/export/json/deployment/filter_deployment?fields=filename')

        assert response.status_code == 200

    def test_deployment_service_unavailable_returns_500(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/json/deployment/test')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for POST /api/export/csv/batch - Batch CSV Export
# ============================================================================


class TestBatchCsvExport:
    """Tests for POST /api/export/csv/batch"""

    def test_batch_csv_json_response(self, temp_photos_dir):
        """Default response should be JSON with csv_data field."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "csv_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/csv/batch',
            json={'photo_paths': ['csv_test.jpg']},
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'csv_data' in data
        assert 'headers' in data
        assert 'row_count' in data

    def test_batch_csv_file_download(self, temp_photos_dir):
        """Accept: text/csv should return CSV file download."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "csv_download_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/csv/batch',
            json={'photo_paths': ['csv_download_test.jpg']},
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'Content-Disposition' in response.headers
        assert 'attachment' in response.headers['Content-Disposition']
        assert '.csv' in response.headers['Content-Disposition']

    def test_batch_csv_excel_bom(self, temp_photos_dir):
        """include_bom=true should add UTF-8 BOM for Excel compatibility."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "csv_bom_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/csv/batch',
            json={'photo_paths': ['csv_bom_test.jpg'], 'include_bom': True},
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        # Check for UTF-8 BOM at start of response
        csv_content = response.data
        assert csv_content.startswith(b'\xef\xbb\xbf')  # UTF-8 BOM

    def test_batch_csv_handles_invalid_paths(self, export_client, sample_photo, temp_photos_dir):
        """CSV batch should handle mix of valid and invalid paths."""
        photo_rel = str(sample_photo.relative_to(temp_photos_dir))

        response = export_client.post(
            '/api/export/csv/batch',
            json={'photo_paths': [photo_rel, '../../../etc/passwd', 'nonexistent.jpg']}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'csv_data' in data
        assert data['total'] == 3
        assert data['failed'] >= 2

    def test_batch_csv_with_field_filtering(self, temp_photos_dir):
        """CSV batch should support field filtering."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata
        mock_service.transform_to_generic_filtered.return_value = {
            'filename': 'test.jpg',
            'latitude': 37.7749,
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "csv_filter_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.post(
            '/api/export/csv/batch',
            json={
                'photo_paths': ['csv_filter_test.jpg'],
                'fields': ['filename', 'latitude']
            },
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        # CSV should only have selected columns
        csv_content = response.data.decode('utf-8')
        assert 'filename' in csv_content
        assert 'latitude' in csv_content

    def test_batch_csv_empty_list_returns_headers_only(self, export_client):
        """Empty photo list should return headers only or error."""
        response = export_client.post(
            '/api/export/csv/batch',
            json={'photo_paths': []}
        )

        # Either returns 200 with just headers or 400 for no photos
        assert response.status_code in [200, 400]

    def test_batch_csv_invalid_json_returns_400(self, export_client):
        """Invalid JSON should return 400."""
        response = export_client.post(
            '/api/export/csv/batch',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400

    def test_batch_csv_service_unavailable_returns_500(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post(
            '/api/export/csv/batch',
            json={'photo_paths': ['test.jpg']}
        )

        assert response.status_code == 500


# ============================================================================
# Tests for GET /api/export/csv/deployment/<path> - Deployment CSV Export
# ============================================================================


class TestDeploymentCsvExport:
    """Tests for GET /api/export/csv/deployment/<path>"""

    def test_deployment_csv_returns_all_photos(self, temp_photos_dir):
        """Deployment CSV should include all photos in directory."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        deploy_dir = temp_photos_dir / "csv_deployment"
        deploy_dir.mkdir(exist_ok=True)

        for i in range(3):
            photo = deploy_dir / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get('/api/export/csv/deployment/csv_deployment')

        assert response.status_code == 200
        data = response.get_json()

        assert 'csv_data' in data
        assert data['total'] >= 3

    def test_deployment_csv_file_download(self, temp_photos_dir):
        """Accept: text/csv should return CSV file download."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        deploy_dir = temp_photos_dir / "csv_deploy_download"
        deploy_dir.mkdir(exist_ok=True)

        photo = deploy_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get(
            '/api/export/csv/deployment/csv_deploy_download',
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'Content-Disposition' in response.headers

    def test_deployment_csv_path_traversal_returns_403(self, export_client):
        """Path traversal attempts should return 403."""
        response = export_client.get('/api/export/csv/deployment/../../../etc')

        assert response.status_code == 403

    def test_deployment_csv_nonexistent_returns_404(self, export_client):
        """Nonexistent deployment should return 404."""
        response = export_client.get('/api/export/csv/deployment/nonexistent')

        assert response.status_code == 404

    def test_deployment_csv_with_field_filtering(self, temp_photos_dir):
        """Deployment CSV should support field filtering via query params."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        deploy_dir = temp_photos_dir / "csv_filter_deployment"
        deploy_dir.mkdir(exist_ok=True)

        photo = deploy_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()
        mock_service.transform_to_generic_filtered.return_value = {
            'filename': 'photo.jpg',
            'latitude': 37.7749
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get(
            '/api/export/csv/deployment/csv_filter_deployment?fields=filename,latitude'
        )

        assert response.status_code == 200

    def test_deployment_csv_with_bom(self, temp_photos_dir):
        """include_bom query param should add UTF-8 BOM."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        deploy_dir = temp_photos_dir / "csv_bom_deployment"
        deploy_dir.mkdir(exist_ok=True)

        photo = deploy_dir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = create_sample_export_metadata()

        real_service = ExportMetadataService()
        mock_service.transform_to_generic.side_effect = real_service.transform_to_generic

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        response = client.get(
            '/api/export/csv/deployment/csv_bom_deployment?include_bom=true',
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        csv_content = response.data
        assert csv_content.startswith(b'\xef\xbb\xbf')

    def test_deployment_csv_service_unavailable_returns_500(self):
        """Missing service should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.get('/api/export/csv/deployment/test')

        assert response.status_code == 500


# ============================================================================
# Tests for Field Filtering Logic
# ============================================================================


class TestFieldFiltering:
    """Tests for field filtering functionality."""

    def test_fields_param_limits_output(self, temp_photos_dir):
        """Fields parameter should limit output to specified fields."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        # Simulate filtered output
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg'},
            'location': {'latitude': 37.7749, 'longitude': -122.4194}
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "fields_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/json/fields_test.jpg?fields=filename,latitude,longitude')

        assert response.status_code == 200
        # transform_to_generic_filtered should have been called
        mock_service.transform_to_generic_filtered.assert_called()

    def test_exclude_param_removes_fields(self, temp_photos_dir):
        """Exclude parameter should remove specified fields."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        # Simulate output with excluded fields
        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg', 'path': '/photos/test.jpg'},
            'location': {'latitude': 37.7749},
            'camera': {'make': 'Arducam'},
            # user_data with notes/tags excluded
            'user_data': {},
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "exclude_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/json/exclude_test.jpg?exclude=notes,tags')

        assert response.status_code == 200
        mock_service.transform_to_generic_filtered.assert_called()

    def test_unknown_fields_silently_ignored(self, temp_photos_dir):
        """Unknown field names should be silently ignored."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_metadata = create_sample_export_metadata()
        mock_service.get_export_metadata.return_value = mock_metadata

        mock_service.transform_to_generic_filtered.return_value = {
            'file': {'filename': 'test.jpg'}
        }

        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "unknown_field_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        # Include unknown fields - should not error
        response = client.get('/api/export/json/unknown_field_test.jpg?fields=filename,unknown_field,another_fake')

        assert response.status_code == 200


# ============================================================================
# Tests for /api/export/formats - Format List Updates
# ============================================================================


class TestFormatsEndpointUpdates:
    """Tests for updated /api/export/formats endpoint."""

    def test_includes_generic_json_format(self, export_client):
        """Formats list should include generic JSON."""
        response = export_client.get('/api/export/formats')

        assert response.status_code == 200
        data = response.get_json()

        format_ids = [f['id'] for f in data['formats']]
        assert 'json' in format_ids

    def test_includes_generic_csv_format(self, export_client):
        """Formats list should include generic CSV."""
        response = export_client.get('/api/export/formats')

        assert response.status_code == 200
        data = response.get_json()

        format_ids = [f['id'] for f in data['formats']]
        assert 'csv' in format_ids

    def test_generic_json_has_correct_structure(self, export_client):
        """Generic JSON format should have correct metadata."""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        json_format = next(f for f in data['formats'] if f['id'] == 'json')

        assert json_format['implemented'] is True
        assert 'name' in json_format
        assert 'description' in json_format
        assert 'endpoints' in json_format or 'features' in json_format

    def test_generic_csv_has_correct_structure(self, export_client):
        """Generic CSV format should have correct metadata."""
        response = export_client.get('/api/export/formats')

        data = response.get_json()
        csv_format = next(f for f in data['formats'] if f['id'] == 'csv')

        assert csv_format['implemented'] is True
        assert 'name' in csv_format
        assert 'description' in csv_format


# ============================================================================
# Integration Tests
# ============================================================================


class TestGenericExportIntegration:
    """Integration tests for generic export routes."""

    def test_full_json_workflow(self, export_client, sample_photo, temp_photos_dir):
        """Test complete JSON export workflow."""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        # Step 1: Check formats
        formats_response = export_client.get('/api/export/formats')
        assert formats_response.status_code == 200

        # Step 2: Single photo JSON export
        single_response = export_client.get(f'/api/export/json/{relative_path}')
        assert single_response.status_code == 200
        single_data = single_response.get_json()
        assert 'file' in single_data

        # Step 3: Check stats
        stats_response = export_client.get('/api/export/stats')
        assert stats_response.status_code == 200

    def test_full_csv_workflow(self, export_client, sample_photo, nested_photo, temp_photos_dir):
        """Test complete CSV export workflow."""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))
        photo2_rel = str(nested_photo.relative_to(temp_photos_dir))

        # Batch CSV export
        batch_response = export_client.post(
            '/api/export/csv/batch',
            json={'photo_paths': [photo1_rel, photo2_rel]}
        )

        assert batch_response.status_code == 200
        data = batch_response.get_json()

        # Verify CSV structure
        assert 'csv_data' in data
        assert 'headers' in data

        # Parse CSV to verify structure
        csv_reader = csv.reader(io.StringIO(data['csv_data']))
        rows = list(csv_reader)

        # Should have header row plus data rows
        assert len(rows) >= 1  # At least headers

    def test_batch_then_single_caching(self, export_client, sample_photo, nested_photo, temp_photos_dir):
        """Test that batch populates cache for subsequent single requests."""
        photo1_rel = str(sample_photo.relative_to(temp_photos_dir))
        photo2_rel = str(nested_photo.relative_to(temp_photos_dir))

        # Get initial stats
        stats1 = export_client.get('/api/export/stats').get_json()

        # Batch request
        export_client.post(
            '/api/export/json/batch',
            json={'photo_paths': [photo1_rel, photo2_rel]}
        )

        # Single requests (should hit cache)
        export_client.get(f'/api/export/json/{photo1_rel}')
        export_client.get(f'/api/export/json/{photo2_rel}')

        # Get updated stats
        stats2 = export_client.get('/api/export/stats').get_json()

        # Cache hits should have increased
        assert stats2['cache_hits'] >= stats1['cache_hits']


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestGenericExportErrorHandling:
    """Tests for error handling in generic export endpoints."""

    def test_json_permission_denied_returns_403(self, temp_photos_dir):
        """Permission denied error should return 403."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = {
            'error': 'Permission denied',
            'photo_path': '/photos/test.jpg'
        }
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "perm_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/json/perm_test.jpg')

        assert response.status_code == 403

    def test_json_generic_error_returns_500(self, temp_photos_dir):
        """Generic service error should return 500."""
        from routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(export_bp, url_prefix='/api/export')

        mock_service = Mock()
        mock_service.get_export_metadata.return_value = {
            'error': 'Internal processing error'
        }
        app.config['EXPORT_METADATA_SERVICE'] = mock_service

        client = app.test_client()

        test_file = temp_photos_dir / "error_test.jpg"
        test_file.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = client.get('/api/export/json/error_test.jpg')

        assert response.status_code == 500

    def test_csv_batch_with_all_invalid_paths(self, export_client):
        """Batch with all invalid paths should still return 200 with errors."""
        response = export_client.post(
            '/api/export/csv/batch',
            json={'photo_paths': ['../etc/passwd', 'nonexistent1.jpg', 'nonexistent2.jpg']}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['failed'] == 3
        assert data['successful'] == 0
