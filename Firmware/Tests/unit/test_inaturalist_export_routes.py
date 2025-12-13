"""
Unit tests for iNaturalist export API routes (Issue #118)

Tests REST API endpoints for iNaturalist ZIP export functionality.
Focuses on security (path traversal), error handling, and response formats.

Coverage Target: 90%+
"""

import io
import json
import zipfile
from unittest.mock import Mock

import pytest
from flask import Flask

from webui.backend.services.export_metadata_service import (
    ExportMetadataService,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def temp_photos_dir(tmp_path_factory):
    """
    Temporary PHOTOS_DIR for iNaturalist export route tests (module-scoped, autouse)

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
            'width': 4000,
            'height': 3000,
        },
        'deployment': {
            'mothbox_id': 'MB-TEST-001',
            'firmware_version': '5.0.0',
        },
        'file': {
            'path': '/photos/test.jpg',
            'size': 1024000,
        },
    }
    return mock


@pytest.fixture(scope="module")
def inaturalist_app(temp_photos_dir, mock_metadata_service):
    """Flask app with export blueprint for testing (module-scoped)"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint
    from routes.export import export_bp
    app.register_blueprint(export_bp, url_prefix='/api/export')

    # Create service with mocked MetadataService
    service = ExportMetadataService(
        cache_ttl=300,
        metadata_service=mock_metadata_service,
    )
    app.config['EXPORT_METADATA_SERVICE'] = service

    return app


@pytest.fixture(scope="module")
def client(inaturalist_app):
    """Test client for iNaturalist export routes (module-scoped)"""
    return inaturalist_app.test_client()


@pytest.fixture(scope="module")
def sample_photos(temp_photos_dir):
    """Create multiple sample JPEG photos (module-scoped)"""
    photos = []
    for i in range(3):
        photo_path = temp_photos_dir / f"test_photo_{i}.jpg"
        if not photo_path.exists():
            # Create minimal JPEG header
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
        photos.append(photo_path)
    return photos


@pytest.fixture(scope="module")
def deployment_dir(temp_photos_dir):
    """Create a deployment directory with photos (module-scoped)"""
    deploy_dir = temp_photos_dir / "deployment_2024"
    deploy_dir.mkdir(exist_ok=True)

    # Create photos in deployment
    for i in range(2):
        photo_path = deploy_dir / f"deploy_photo_{i}.jpg"
        if not photo_path.exists():
            photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

    return deploy_dir


# ============================================================================
# Tests for POST /api/export/inaturalist/batch
# ============================================================================


class TestExportINaturalistBatch:
    """Tests for POST /api/export/inaturalist/batch endpoint."""

    def test_export_batch_returns_zip(self, client, sample_photos, temp_photos_dir):
        """Test batch export returns valid ZIP when Accept: application/zip."""
        # Get relative paths
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': relative_paths},
            headers={'Accept': 'application/zip'}
        )

        assert response.status_code == 200
        assert response.content_type == 'application/zip'

        # Verify ZIP is valid
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer) as zf:
            # testzip() returns None if no corrupt files
            assert zf.testzip() is None

            # Check ZIP contains photos
            namelist = zf.namelist()
            assert len([n for n in namelist if n.endswith('.jpg')]) > 0

    def test_export_batch_returns_json(self, client, sample_photos, temp_photos_dir):
        """Test batch export returns JSON status when Accept: application/json."""
        # Get relative paths
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': relative_paths},
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'photo_count' in data
        assert 'zip_size_bytes' in data
        assert 'took_ms' in data
        # zip_path not returned since temp file is cleaned up after response

    def test_export_batch_requires_photos(self, client):
        """Test batch export fails without photo_paths."""
        response = client.post(
            '/api/export/inaturalist/batch',
            json={},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No photos specified' in data['error']

    def test_export_batch_empty_array(self, client):
        """Test batch export fails with empty photo_paths array."""
        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': []},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_export_batch_validates_paths(self, client):
        """Test batch export validates photo paths (path traversal protection)."""
        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': ['../../etc/passwd']},
        )
        assert response.status_code in [400, 403]
        data = response.get_json()
        assert 'error' in data

    def test_export_batch_respects_options(self, client, sample_photos, temp_photos_dir):
        """Test batch export respects custom options."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={
                'photo_paths': relative_paths,
                'options': {
                    'include_xmp_sidecars': False,
                    'include_manifest': True,
                    'include_csv_summary': True,
                }
            },
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # With include_xmp_sidecars=False, xmp_count should be 0
        assert data['xmp_count'] == 0

    def test_export_batch_invalid_json(self, client):
        """Test batch export handles invalid JSON."""
        response = client.post(
            '/api/export/inaturalist/batch',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_export_batch_non_json_request(self, client):
        """Test batch export requires JSON content type."""
        response = client.post(
            '/api/export/inaturalist/batch',
            data='photo_paths=test.jpg',
        )
        assert response.status_code == 400

    def test_export_batch_photo_paths_not_array(self, client):
        """Test batch export validates photo_paths is array."""
        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': 'test.jpg'},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'must be an array' in data['error']

    def test_export_batch_photo_paths_non_strings(self, client):
        """Test batch export validates photo_paths contains strings."""
        response = client.post(
            '/api/export/inaturalist/batch',
            json={'photo_paths': [123, 456]},
        )
        assert response.status_code == 400

    def test_export_batch_with_xmp_sidecars(self, client, sample_photos, temp_photos_dir):
        """Test batch export includes XMP sidecars when enabled."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={
                'photo_paths': relative_paths,
                'options': {'include_xmp_sidecars': True}
            },
            headers={'Accept': 'application/zip'}
        )

        assert response.status_code == 200

        # Verify ZIP contains XMP files
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer) as zf:
            namelist = zf.namelist()
            xmp_files = [n for n in namelist if n.endswith('.xmp')]
            assert len(xmp_files) > 0

    def test_export_batch_includes_manifest(self, client, sample_photos, temp_photos_dir):
        """Test batch export includes manifest.json when enabled."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={
                'photo_paths': relative_paths,
                'options': {'include_manifest': True}
            },
            headers={'Accept': 'application/zip'}
        )

        assert response.status_code == 200

        # Verify ZIP contains manifest.json
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer) as zf:
            namelist = zf.namelist()
            assert 'manifest.json' in namelist

            # Verify manifest is valid JSON
            manifest_data = zf.read('manifest.json')
            manifest = json.loads(manifest_data)
            assert 'version' in manifest
            assert 'generator' in manifest
            assert manifest['generator'] == 'Mothbox'

    def test_export_batch_includes_csv_summary(self, client, sample_photos, temp_photos_dir):
        """Test batch export includes summary.csv when enabled."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/batch',
            json={
                'photo_paths': relative_paths,
                'options': {'include_csv_summary': True}
            },
            headers={'Accept': 'application/zip'}
        )

        assert response.status_code == 200

        # Verify ZIP contains summary.csv
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer) as zf:
            namelist = zf.namelist()
            assert 'summary.csv' in namelist


# ============================================================================
# Tests for GET /api/export/inaturalist/deployment/<path>
# ============================================================================


class TestExportDeploymentINaturalist:
    """Tests for GET /api/export/inaturalist/deployment/<path> endpoint."""

    def test_export_deployment_returns_zip(self, client, deployment_dir, temp_photos_dir):
        """Test deployment export returns valid ZIP."""
        relative_path = deployment_dir.relative_to(temp_photos_dir)

        response = client.get(
            f'/api/export/inaturalist/deployment/{relative_path}',
            headers={'Accept': 'application/zip'}
        )

        assert response.status_code == 200
        assert response.content_type == 'application/zip'

        # Verify ZIP is valid
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer) as zf:
            assert zf.testzip() is None

    def test_export_deployment_returns_json(self, client, deployment_dir, temp_photos_dir):
        """Test deployment export returns JSON status when requested."""
        relative_path = deployment_dir.relative_to(temp_photos_dir)

        response = client.get(
            f'/api/export/inaturalist/deployment/{relative_path}',
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'photo_count' in data
        # zip_path not returned since temp file is cleaned up after response

    def test_export_deployment_invalid_path(self, client):
        """Test deployment export validates path (path traversal protection)."""
        response = client.get(
            '/api/export/inaturalist/deployment/../../etc',
        )
        assert response.status_code in [400, 403, 404]

    def test_export_deployment_not_found(self, client):
        """Test deployment export returns 404 for non-existent directory."""
        response = client.get(
            '/api/export/inaturalist/deployment/nonexistent_dir',
        )
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_export_deployment_query_params(self, client, deployment_dir, temp_photos_dir):
        """Test deployment export respects query parameters."""
        relative_path = deployment_dir.relative_to(temp_photos_dir)

        response = client.get(
            f'/api/export/inaturalist/deployment/{relative_path}?include_xmp=false',
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # With include_xmp=false, xmp_count should be 0
        assert data['xmp_count'] == 0

    def test_export_deployment_empty_directory(self, client, temp_photos_dir):
        """Test deployment export handles empty directory."""
        empty_dir = temp_photos_dir / "empty_deployment"
        empty_dir.mkdir(exist_ok=True)

        response = client.get(
            f'/api/export/inaturalist/deployment/{empty_dir.name}',
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'No photos found' in data['error']

    def test_export_deployment_file_not_directory(self, client, sample_photos, temp_photos_dir):
        """Test deployment export validates path is directory."""
        # Try to export a file instead of directory
        relative_path = sample_photos[0].relative_to(temp_photos_dir)

        response = client.get(
            f'/api/export/inaturalist/deployment/{relative_path}',
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'not a directory' in data['error']


# ============================================================================
# Tests for POST /api/export/inaturalist/preview
# ============================================================================


class TestPreviewINaturalistExport:
    """Tests for POST /api/export/inaturalist/preview endpoint."""

    def test_preview_returns_validation_results(self, client, sample_photos, temp_photos_dir):
        """Test preview returns validation for each photo."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': relative_paths},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'valid_photos' in data
        assert 'invalid_photos' in data
        assert 'validation_results' in data
        assert 'estimated_zip_size_bytes' in data

        # Should have validation result for each photo
        assert len(data['validation_results']) == len(sample_photos)

    def test_preview_includes_sample_xmp(self, client, sample_photos, temp_photos_dir):
        """Test preview includes sample XMP from first photo."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': relative_paths},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'sample_xmp' in data
        # sample_xmp can be None if no valid photos, or a string
        if data['sample_xmp'] is not None:
            assert '<?xpacket' in data['sample_xmp']

    def test_preview_validation_structure(self, client, sample_photos, temp_photos_dir):
        """Test preview validation results have expected structure."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos[:1]]

        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': relative_paths},
        )

        assert response.status_code == 200
        data = response.get_json()
        validation = data['validation_results'][0]

        # Check validation result structure
        assert 'photo' in validation
        assert 'is_valid' in validation
        assert 'missing_required' in validation
        assert 'warnings' in validation

    def test_preview_handles_invalid_paths(self, client):
        """Test preview handles invalid photo paths."""
        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': ['../../etc/passwd']},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['invalid_photos'] > 0
        assert len(data['validation_results']) > 0
        assert data['validation_results'][0]['is_valid'] is False

    def test_preview_handles_missing_files(self, client):
        """Test preview handles non-existent files."""
        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': ['nonexistent.jpg']},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['invalid_photos'] > 0

    def test_preview_requires_photos(self, client):
        """Test preview fails without photo_paths."""
        response = client.post(
            '/api/export/inaturalist/preview',
            json={},
        )
        assert response.status_code == 400

    def test_preview_empty_array(self, client):
        """Test preview fails with empty photo_paths array."""
        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': []},
        )
        assert response.status_code == 400

    def test_preview_estimated_size(self, client, sample_photos, temp_photos_dir):
        """Test preview provides estimated ZIP size."""
        relative_paths = [str(p.relative_to(temp_photos_dir)) for p in sample_photos]

        response = client.post(
            '/api/export/inaturalist/preview',
            json={'photo_paths': relative_paths},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['estimated_zip_size_bytes'] > 0


# ============================================================================
# Tests for GET /api/export/formats
# ============================================================================


class TestListExportFormats:
    """Tests for export format listing with iNaturalist."""

    def test_inaturalist_format_is_implemented(self, client):
        """Test iNaturalist format shows as implemented."""
        response = client.get('/api/export/formats')
        assert response.status_code == 200
        data = response.get_json()

        # Find iNaturalist format
        inaturalist = next(
            (f for f in data['formats'] if f['id'] == 'inaturalist'),
            None
        )
        assert inaturalist is not None
        assert inaturalist['implemented'] is True
        assert inaturalist['name'] == 'iNaturalist ZIP'
        assert 'features' in inaturalist

    def test_inaturalist_features_listed(self, client):
        """Test iNaturalist format lists expected features."""
        response = client.get('/api/export/formats')
        assert response.status_code == 200
        data = response.get_json()

        inaturalist = next(
            (f for f in data['formats'] if f['id'] == 'inaturalist'),
            None
        )

        expected_features = [
            'XMP sidecar files',
            'Hierarchical taxonomy keywords',
            'GPS coordinates',
            'Observation notes',
            'License information',
            'CSV summary',
            'JSON manifest'
        ]

        for feature in expected_features:
            assert feature in inaturalist['features']
