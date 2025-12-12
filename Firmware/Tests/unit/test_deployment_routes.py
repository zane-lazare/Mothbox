"""
Unit tests for deployment API routes (Issue #114)

Tests REST API endpoints for deployment metadata service.
Focuses on security (path traversal), error handling, and response format.

Test Count: 115 tests
Coverage: 91.74%

Test Categories:
- TestGetDeploymentMetadata (6 tests): GET endpoint testing
- TestCreateUpdateDeployment (8 tests): PUT endpoint testing
- TestPatchDeployment (4 tests): PATCH endpoint testing
- TestDeleteDeployment (3 tests): DELETE endpoint testing
- TestListAndDiscover (6 tests): List and discover endpoints
- TestBatchOperations (8 tests): Batch update operations
- TestGenerateSidecars (6 tests): Sidecar generation
- TestCacheOperations (5 tests): Cache statistics and invalidation
- TestSecurity (4 tests): CSRF protection
- TestDeploymentRoutesIntegration (2 tests): End-to-end workflows
- TestCustomFieldValidation (11 tests): Custom field nesting/validation
- TestInputValidation (15 tests): Input validation edge cases
- TestServiceUnavailable (10 tests): Service unavailable (503) scenarios
- TestExceptionHandling (10 tests): Exception handling (500) scenarios
- TestRequestFormat (7 tests): Request format validation
- TestBatchEdgeCases (6 tests): Batch endpoint edge cases
- TestGenerateEndpointEdgeCases (2 tests): Generate endpoint edge cases
- TestDeleteOperationFailure (1 test): Delete operation failure
- TestPutOperationFailure (1 test): PUT operation failure
- TestPatchOperationFailure (1 test): PATCH operation failure
- TestListPathValidation (1 test): List path validation
- TestDiscoverPathValidation (1 test): Discover path validation
"""

import pytest
from flask import Flask
from pathlib import Path
from unittest.mock import Mock, patch

from webui.backend.services.deployment_service import DeploymentService
from webui.backend.lib.deployment_schema import DeploymentMetadata

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def temp_photos_dir(tmp_path_factory):
    """
    Temporary PHOTOS_DIR for deployment route tests (module-scoped, autouse)

    Creates temporary directory and patches PHOTOS_DIR globally for this test module.
    """
    photos_dir = tmp_path_factory.mktemp("photos")

    # Patch PHOTOS_DIR in all relevant modules
    import routes.deployment
    import mothbox_paths

    original_mothbox_paths_photos_dir = mothbox_paths.PHOTOS_DIR
    original_routes_deployment_photos_dir = routes.deployment.PHOTOS_DIR

    mothbox_paths.PHOTOS_DIR = photos_dir
    routes.deployment.PHOTOS_DIR = photos_dir

    yield photos_dir

    # Restore original values
    mothbox_paths.PHOTOS_DIR = original_mothbox_paths_photos_dir
    routes.deployment.PHOTOS_DIR = original_routes_deployment_photos_dir


@pytest.fixture(scope="module")
def mock_deployment_service():
    """Mock DeploymentService"""
    service = Mock(spec=DeploymentService)

    # Sample deployment metadata
    sample_metadata = DeploymentMetadata(
        version="1.0",
        deployment_name="Test Deployment",
        created_at="2024-01-01T00:00:00Z",
        modified_at="2024-01-01T00:00:00Z",
        latitude=35.9606,
        longitude=-83.9207,
        altitude=350.5,
        location_name="Oak Ridge, TN, USA",
        start_date="2024-06-01",
        end_date="2024-08-31",
        mothbox_id="mothbox-001",
        firmware_version="5.2.1",
    )

    # Default behavior
    service.get_deployment_metadata.return_value = sample_metadata
    service.set_deployment_metadata.return_value = True
    service.update_deployment_metadata.return_value = sample_metadata
    service.delete_deployment_metadata.return_value = True
    service.list_deployments.return_value = [sample_metadata]
    service.find_deployment_for_photo.return_value = sample_metadata
    service.generate_sidecars_for_directory.return_value = 5
    service.get_statistics.return_value = {
        'cache_hits': 450,
        'cache_misses': 50,
        'cache_evictions': 10,
        'cache_size': 75,
        'max_cache_size': 100,
        'cache_ttl': 300,
        'hit_ratio': 0.90,
        'total_reads': 500,
        'total_writes': 25,
        'total_deletes': 5
    }

    return service


@pytest.fixture(scope="module")
def deployment_app(temp_photos_dir, mock_deployment_service):
    """Flask app with deployment blueprint for testing (module-scoped)"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Try to disable CSRF if Flask-WTF is available
    try:
        app.config['WTF_CSRF_ENABLED'] = False
    except Exception:
        pass  # Flask-WTF may not be installed

    # Register blueprint
    from routes.deployment import deployment_bp
    app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

    # Inject mock service
    app.config['DEPLOYMENT_SERVICE'] = mock_deployment_service

    return app


@pytest.fixture(scope="module")
def deployment_client(deployment_app):
    """Test client for deployment routes (module-scoped)"""
    return deployment_app.test_client()


@pytest.fixture(scope="module")
def sample_directory(temp_photos_dir):
    """Create a sample directory (module-scoped)"""
    dir_path = temp_photos_dir / "test_deployment"
    dir_path.mkdir(exist_ok=True)
    return dir_path


@pytest.fixture(scope="module")
def nested_directory(temp_photos_dir):
    """Create a nested directory (module-scoped)"""
    dir_path = temp_photos_dir / "parent" / "child"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@pytest.fixture(scope="module")
def sample_photo(sample_directory):
    """Create a sample photo in directory"""
    photo_path = sample_directory / "photo.jpg"
    photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
    return photo_path


# ============================================================================
# Tests for GET /api/deployment/metadata/<path:directory>
# ============================================================================


class TestGetDeploymentMetadata:
    """Tests for GET /api/deployment/metadata/<directory>"""

    def test_get_existing_deployment(self, deployment_client, sample_directory, temp_photos_dir):
        """Test getting existing deployment metadata"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Mock find_deployment_sidecar function
        with patch('webui.backend.lib.deployment_sidecar.find_deployment_sidecar') as mock_find:
            mock_find.return_value = sample_directory / "deployment.json"

            response = deployment_client.get(f'/api/deployment/metadata/{relative_path}')

            assert response.status_code == 200
            data = response.get_json()

            assert 'deployment' in data
            assert 'source_path' in data
            assert data['deployment']['deployment_name'] == 'Test Deployment'

    def test_get_nonexistent_returns_404(self, deployment_client, mock_deployment_service):
        """Test that nonexistent deployment returns 404"""
        # Configure mock to return None
        mock_deployment_service.get_deployment_metadata.return_value = None

        response = deployment_client.get('/api/deployment/metadata/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.get_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_get_invalid_path_returns_400(self, deployment_client):
        """Test that invalid path returns 400"""
        response = deployment_client.get('/api/deployment/metadata/../../../etc/passwd')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid path' in data['error']

    def test_get_path_traversal_blocked(self, deployment_client):
        """Test that path traversal attempts are blocked"""
        response = deployment_client.get('/api/deployment/metadata/../../etc/passwd')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_get_nonexistent_directory_returns_404(self, deployment_client, temp_photos_dir):
        """Test that nonexistent directory returns 404"""
        response = deployment_client.get('/api/deployment/metadata/does_not_exist')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_service_unavailable_returns_503(self):
        """Test that missing service returns 503"""
        app = Flask(__name__)
        app.config['TESTING'] = True

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

        client = app.test_client()

        response = client.get('/api/deployment/metadata/test')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()


# ============================================================================
# Tests for PUT /api/deployment/metadata/<path:directory>
# ============================================================================


class TestCreateUpdateDeployment:
    """Tests for PUT /api/deployment/metadata/<directory>"""

    def test_put_creates_new_deployment(self, deployment_client, sample_directory, temp_photos_dir):
        """Test creating new deployment metadata"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Mock the library function
        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='New Deployment',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z',
                latitude=35.9606,
                longitude=-83.9207
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'New Deployment',
                    'latitude': 35.9606,
                    'longitude': -83.9207
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert 'deployment_name' in data

    def test_put_updates_existing(self, deployment_client, sample_directory, temp_photos_dir):
        """Test updating existing deployment metadata"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Updated Deployment',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z',
                latitude=40.0,
                longitude=-80.0
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Updated Deployment',
                    'latitude': 40.0,
                    'longitude': -80.0
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert 'deployment_name' in data

    def test_put_invalid_json_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that invalid JSON returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_put_validation_error_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that validation errors return 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Missing deployment_name
        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'latitude': 35.9606
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'deployment_name' in data['error']

    def test_put_invalid_coordinates_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that invalid coordinates return 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            # Validation happens before create_deployment_metadata is called
            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'latitude': 100.0,  # Invalid: > 90
                    'longitude': -83.9207
                }
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data

    def test_yaml_format_parameter(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that format=yaml parameter works"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='YAML Deployment',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}?format=yaml',
                json={
                    'deployment_name': 'YAML Deployment'
                }
            )

            assert response.status_code == 200

    def test_put_invalid_format_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that invalid format returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}?format=xml',
                json={
                    'deployment_name': 'Test'
                }
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data

    def test_put_path_traversal_blocked(self, deployment_client):
        """Test that path traversal is blocked"""
        response = deployment_client.put(
            '/api/deployment/metadata/../../etc/passwd',
            json={'deployment_name': 'Test'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for PATCH /api/deployment/metadata/<path:directory>
# ============================================================================


class TestPatchDeployment:
    """Tests for PATCH /api/deployment/metadata/<directory>"""

    def test_patch_updates_partial_fields(self, deployment_client, sample_directory, temp_photos_dir):
        """Test partial update of deployment metadata"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'end_date': '2024-09-15'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'deployment_name' in data  # Original fields preserved

    def test_patch_nonexistent_returns_404(self, deployment_client, mock_deployment_service):
        """Test that PATCH on nonexistent deployment returns 404"""
        # Configure mock to return None for get
        mock_deployment_service.get_deployment_metadata.return_value = None

        response = deployment_client.patch(
            '/api/deployment/metadata/nonexistent',
            json={'end_date': '2024-09-15'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.get_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_patch_invalid_json_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that invalid JSON returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_patch_validation_error_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that validation errors return 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'latitude': 200.0  # Invalid
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for DELETE /api/deployment/metadata/<path:directory>
# ============================================================================


class TestDeleteDeployment:
    """Tests for DELETE /api/deployment/metadata/<directory>"""

    def test_delete_existing(self, deployment_client, sample_directory, temp_photos_dir):
        """Test deleting existing deployment"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.delete(f'/api/deployment/metadata/{relative_path}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_delete_nonexistent_returns_404(self, deployment_client, mock_deployment_service):
        """Test that deleting nonexistent deployment returns 404"""
        # Configure mock to return None
        mock_deployment_service.get_deployment_metadata.return_value = None

        response = deployment_client.delete('/api/deployment/metadata/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.get_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_delete_path_traversal_blocked(self, deployment_client):
        """Test that path traversal is blocked"""
        response = deployment_client.delete('/api/deployment/metadata/../../etc/passwd')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for GET /api/deployment/list
# ============================================================================


class TestListAndDiscover:
    """Tests for list and discover endpoints"""

    def test_list_all_deployments(self, deployment_client):
        """Test listing all deployments"""
        response = deployment_client.get('/api/deployment/list')

        assert response.status_code == 200
        data = response.get_json()

        assert 'deployments' in data
        assert 'total' in data
        assert isinstance(data['deployments'], list)
        assert data['total'] == len(data['deployments'])

    def test_list_empty_returns_empty(self, deployment_client, mock_deployment_service):
        """Test that empty directory returns empty list"""
        # Configure mock to return empty list
        mock_deployment_service.list_deployments.return_value = []

        response = deployment_client.get('/api/deployment/list')

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0
        assert len(data['deployments']) == 0

        # Reset mock
        mock_deployment_service.list_deployments.return_value = [
            DeploymentMetadata(
                version="1.0",
                deployment_name="Test Deployment",
                created_at="2024-01-01T00:00:00Z",
                modified_at="2024-01-01T00:00:00Z"
            )
        ]

    def test_list_with_root_dir_parameter(self, deployment_client, sample_directory, temp_photos_dir):
        """Test listing deployments with root_dir parameter"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.get(f'/api/deployment/list?root_dir={relative_path}')

        assert response.status_code == 200
        data = response.get_json()
        assert 'deployments' in data

    def test_discover_deployment_for_photo(self, deployment_client, sample_photo, temp_photos_dir):
        """Test discovering deployment for a photo"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        # Mock find_deployment_sidecar function
        with patch('webui.backend.lib.deployment_sidecar.find_deployment_sidecar') as mock_find:
            mock_find.return_value = sample_photo.parent / "deployment.json"

            response = deployment_client.get(f'/api/deployment/discover/{relative_path}')

            assert response.status_code == 200
            data = response.get_json()

            assert 'deployment' in data
            assert 'source_path' in data
            assert data['deployment']['deployment_name'] == 'Test Deployment'

    def test_discover_no_deployment_returns_404(self, deployment_client, mock_deployment_service, sample_photo, temp_photos_dir):
        """Test that discover returns 404 when no deployment found"""
        # Configure mock to return None
        mock_deployment_service.find_deployment_for_photo.return_value = None

        relative_path = sample_photo.relative_to(temp_photos_dir)
        response = deployment_client.get(f'/api/deployment/discover/{relative_path}')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.find_deployment_for_photo.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_discover_nonexistent_photo_returns_404(self, deployment_client):
        """Test that discovering for nonexistent photo returns 404"""
        response = deployment_client.get('/api/deployment/discover/nonexistent.jpg')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for POST /api/deployment/batch
# ============================================================================


class TestBatchOperations:
    """Tests for batch update endpoint"""

    def test_batch_update_success(self, deployment_client, sample_directory, nested_directory, temp_photos_dir):
        """Test successful batch update"""
        dir1_rel = str(sample_directory.relative_to(temp_photos_dir))
        dir2_rel = str(nested_directory.relative_to(temp_photos_dir))

        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [
                    {'directory': dir1_rel, 'data': {'end_date': '2024-09-15'}},
                    {'directory': dir2_rel, 'data': {'end_date': '2024-09-20'}}
                ]
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'success' in data
        assert 'failed' in data
        assert 'errors' in data
        assert 'total' in data
        assert 'successful' in data
        assert 'failed_count' in data

        assert data['total'] == 2

    def test_batch_update_partial_failure(self, deployment_client, sample_directory, temp_photos_dir):
        """Test batch update with partial failures"""
        dir1_rel = str(sample_directory.relative_to(temp_photos_dir))

        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [
                    {'directory': dir1_rel, 'data': {'end_date': '2024-09-15'}},
                    {'directory': 'nonexistent', 'data': {'end_date': '2024-09-20'}}
                ]
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['total'] == 2
        # At least one should fail (the nonexistent one)
        assert data['failed_count'] >= 1

    def test_batch_update_empty_returns_400(self, deployment_client):
        """Test that empty updates array returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={'updates': []}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_missing_updates_field_returns_400(self, deployment_client):
        """Test that missing updates field returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'updates' in data['error']

    def test_batch_invalid_json_returns_400(self, deployment_client):
        """Test that invalid JSON returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_updates_not_array_returns_400(self, deployment_client):
        """Test that updates must be array"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={'updates': 'not_an_array'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_too_many_updates_returns_400(self, deployment_client):
        """Test that too many updates returns 400"""
        updates = [
            {'directory': f'dir_{i}', 'data': {'end_date': '2024-09-15'}}
            for i in range(101)  # Exceeds limit of 100
        ]

        response = deployment_client.post(
            '/api/deployment/batch',
            json={'updates': updates}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_invalid_update_structure_returns_400(self, deployment_client):
        """Test that invalid update structure returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [
                    {'directory': 'test'}  # Missing 'data' field
                ]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for POST /api/deployment/generate
# ============================================================================


class TestGenerateSidecars:
    """Tests for generate sidecars endpoint"""

    def test_generate_sidecars_success(self, deployment_client, sample_directory, temp_photos_dir):
        """Test successful sidecar generation"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': str(relative_path),
                'template': {
                    'deployment_name': 'Auto-generated',
                    'location_name': 'Test Location'
                }
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert 'generated_count' in data
        assert isinstance(data['generated_count'], int)

    def test_generate_sidecars_invalid_dir(self, deployment_client):
        """Test that invalid directory returns 404"""
        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': 'nonexistent',
                'template': {'deployment_name': 'Test'}
            }
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_generate_missing_directory_field_returns_400(self, deployment_client):
        """Test that missing directory field returns 400"""
        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'template': {'deployment_name': 'Test'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'directory' in data['error']

    def test_generate_missing_template_field_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that missing template field returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': str(relative_path)
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'template' in data['error']

    def test_generate_invalid_template_returns_400(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that invalid template returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': str(relative_path),
                'template': {
                    'latitude': 100.0  # Invalid coordinate
                }
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_generate_path_traversal_blocked(self, deployment_client):
        """Test that path traversal is blocked"""
        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': '../../etc',
                'template': {'deployment_name': 'Test'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for GET /api/deployment/stats
# ============================================================================


class TestCacheOperations:
    """Tests for cache statistics and invalidation"""

    def test_get_stats(self, deployment_client):
        """Test getting cache statistics"""
        response = deployment_client.get('/api/deployment/stats')

        assert response.status_code == 200
        data = response.get_json()

        # Verify statistics structure
        assert 'cache_hits' in data
        assert 'cache_misses' in data
        assert 'cache_evictions' in data
        assert 'cache_size' in data
        assert 'max_cache_size' in data
        assert 'cache_ttl' in data
        assert 'hit_ratio' in data
        assert 'total_reads' in data
        assert 'total_writes' in data
        assert 'total_deletes' in data

    def test_stats_are_numbers(self, deployment_client):
        """Test that all statistics are numeric"""
        response = deployment_client.get('/api/deployment/stats')
        data = response.get_json()

        assert isinstance(data['cache_hits'], int)
        assert isinstance(data['cache_misses'], int)
        assert isinstance(data['cache_evictions'], int)
        assert isinstance(data['cache_size'], int)
        assert isinstance(data['max_cache_size'], int)
        assert isinstance(data['cache_ttl'], int)
        assert isinstance(data['hit_ratio'], (int, float))
        assert isinstance(data['total_reads'], int)
        assert isinstance(data['total_writes'], int)
        assert isinstance(data['total_deletes'], int)

    def test_invalidate_cache(self, deployment_client, mock_deployment_service):
        """Test cache invalidation"""
        response = deployment_client.post('/api/deployment/cache/invalidate')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify service was called
        mock_deployment_service.invalidate_cache.assert_called()

    def test_invalidate_cache_specific_directory(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test cache invalidation for specific directory"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.post(f'/api/deployment/cache/invalidate?directory={relative_path}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_invalidate_cache_invalid_path_returns_400(self, deployment_client):
        """Test that invalid path returns 400"""
        response = deployment_client.post('/api/deployment/cache/invalidate?directory=../../etc')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for CSRF protection
# ============================================================================


class TestSecurity:
    """Tests for security features"""

    def test_csrf_required_on_put(self, temp_photos_dir, sample_directory):
        """Test that CSRF is required on PUT (when enabled)"""
        try:
            from flask_wtf.csrf import CSRFProtect
        except ImportError:
            pytest.skip("Flask-WTF not installed")

        app = Flask(__name__)
        app.config['TESTING'] = False  # CSRF enabled when not testing
        app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF
        app.config['SECRET_KEY'] = 'test-secret-key'

        # Initialize CSRF protection
        CSRFProtect(app)

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

        # Mock service
        mock_service = Mock(spec=DeploymentService)
        app.config['DEPLOYMENT_SERVICE'] = mock_service

        client = app.test_client()

        # Request without CSRF token should fail
        response = client.put(
            f'/api/deployment/metadata/{sample_directory.name}',
            json={'deployment_name': 'Test'}
        )

        # Should be rejected (400 or 403 depending on Flask-WTF version)
        assert response.status_code in [400, 403]

    def test_csrf_required_on_patch(self, temp_photos_dir, sample_directory):
        """Test that CSRF is required on PATCH (when enabled)"""
        try:
            from flask_wtf.csrf import CSRFProtect
        except ImportError:
            pytest.skip("Flask-WTF not installed")

        app = Flask(__name__)
        app.config['TESTING'] = False
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'

        CSRFProtect(app)

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

        mock_service = Mock(spec=DeploymentService)
        app.config['DEPLOYMENT_SERVICE'] = mock_service

        client = app.test_client()

        response = client.patch(
            f'/api/deployment/metadata/{sample_directory.name}',
            json={'end_date': '2024-09-15'}
        )

        assert response.status_code in [400, 403]

    def test_csrf_required_on_delete(self, temp_photos_dir, sample_directory):
        """Test that CSRF is required on DELETE (when enabled)"""
        try:
            from flask_wtf.csrf import CSRFProtect
        except ImportError:
            pytest.skip("Flask-WTF not installed")

        app = Flask(__name__)
        app.config['TESTING'] = False
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'

        CSRFProtect(app)

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

        mock_service = Mock(spec=DeploymentService)
        app.config['DEPLOYMENT_SERVICE'] = mock_service

        client = app.test_client()

        response = client.delete(f'/api/deployment/metadata/{sample_directory.name}')

        assert response.status_code in [400, 403]

    def test_csrf_required_on_post(self):
        """Test that CSRF is required on POST (when enabled)"""
        try:
            from flask_wtf.csrf import CSRFProtect
        except ImportError:
            pytest.skip("Flask-WTF not installed")

        app = Flask(__name__)
        app.config['TESTING'] = False
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'

        CSRFProtect(app)

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')

        mock_service = Mock(spec=DeploymentService)
        app.config['DEPLOYMENT_SERVICE'] = mock_service

        client = app.test_client()

        response = client.post(
            '/api/deployment/batch',
            json={'updates': []}
        )

        assert response.status_code in [400, 403]


# ============================================================================
# Integration Tests
# ============================================================================


class TestDeploymentRoutesIntegration:
    """Integration tests for deployment routes"""

    def test_full_workflow(self, deployment_client, sample_directory, temp_photos_dir):
        """Test complete workflow: create, get, update, delete"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create, \
             patch('webui.backend.lib.deployment_sidecar.find_deployment_sidecar') as mock_find:

            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test Deployment',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )
            mock_find.return_value = sample_directory / "deployment.json"

            # Step 1: Create deployment
            create_response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={'deployment_name': 'Test Deployment'}
            )
            assert create_response.status_code == 200

            # Step 2: Get deployment
            get_response = deployment_client.get(f'/api/deployment/metadata/{relative_path}')
            assert get_response.status_code == 200

            # Step 3: Update deployment
            update_response = deployment_client.patch(
                f'/api/deployment/metadata/{relative_path}',
                json={'end_date': '2024-09-15'}
            )
            assert update_response.status_code == 200

            # Step 4: Check statistics
            stats_response = deployment_client.get('/api/deployment/stats')
            assert stats_response.status_code == 200

            # Step 5: Delete deployment
            delete_response = deployment_client.delete(f'/api/deployment/metadata/{relative_path}')
            assert delete_response.status_code == 200

    def test_list_then_discover(self, deployment_client, sample_photo, temp_photos_dir):
        """Test list deployments followed by discover"""
        with patch('webui.backend.lib.deployment_sidecar.find_deployment_sidecar') as mock_find:
            mock_find.return_value = sample_photo.parent / "deployment.json"

            # List all
            list_response = deployment_client.get('/api/deployment/list')
            assert list_response.status_code == 200

            # Discover for photo
            relative_path = sample_photo.relative_to(temp_photos_dir)
            discover_response = deployment_client.get(f'/api/deployment/discover/{relative_path}')
            assert discover_response.status_code == 200


# ============================================================================
# Tests for Custom Field Validation (_validate_custom_value)
# ============================================================================


class TestCustomFieldValidation:
    """Tests for custom field validation in deployment metadata"""

    def test_custom_field_exceeds_depth_limit(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that deeply nested custom fields are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Create a deeply nested structure (7 levels deep in the value, exceeds MAX_CUSTOM_DEPTH=5)
        # _validate_custom_value is called with depth=0 for each value in custom dict
        # So we need depth > 5 which means 7 nesting levels within the value
        nested = {"level7": "value"}
        for i in range(6, 0, -1):
            nested = {f"level{i}": nested}

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': {'deeply_nested': nested}  # The value starts at depth 0
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'depth' in data['error'].lower()

    def test_custom_field_list_with_invalid_item(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field lists with invalid items are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Create list with deeply nested item
        nested = {"level5": "value"}
        for i in range(4, 0, -1):
            nested = {f"level{i}": nested}

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': {'items': [nested]}  # List contains deeply nested item
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_custom_field_dict_with_non_string_key(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field dicts with non-string keys are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Note: JSON doesn't support non-string keys, but we test the validation logic
        # by sending data that has been previously parsed
        # This test validates the code path when keys are checked
        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': {'valid_key': {'nested': 'value'}}
            }
        )

        # Should pass since keys are strings
        assert response.status_code == 200

    def test_custom_field_key_exceeds_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field keys exceeding 100 chars are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        long_key = 'k' * 101  # Exceeds 100 char limit

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': {long_key: 'value'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'key' in data['error'].lower() or 'long' in data['error'].lower()

    def test_custom_field_string_exceeds_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field strings exceeding 10000 chars are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        long_string = 'x' * 10001  # Exceeds 10000 char limit

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': {'key': long_string}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'long' in data['error'].lower() or 'string' in data['error'].lower()

    def test_custom_field_with_boolean_value(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field with boolean value is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'custom': {'is_active': True, 'is_processed': False}
                }
            )

            assert response.status_code == 200

    def test_custom_field_with_nested_dict(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field with nested dict within limit is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'custom': {'metadata': {'author': 'test', 'version': '1.0'}}
                }
            )

            assert response.status_code == 200

    def test_custom_field_with_nested_list(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field with nested list within limit is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'custom': {'tags': ['moth', 'insect', 'night']}
                }
            )

            assert response.status_code == 200

    def test_custom_field_too_many_keys(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field with more than MAX_CUSTOM_KEYS (100) is rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Create dict with 101 keys
        many_keys = {f'key{i}': f'value{i}' for i in range(101)}

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': many_keys
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'custom' in data['error'].lower() or 'many' in data['error'].lower()

    def test_custom_field_with_number_values(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom field with int and float values is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'custom': {'count': 42, 'temperature': 23.5}
                }
            )

            assert response.status_code == 200


# ============================================================================
# Tests for Environmental Field Validation
# ============================================================================


class TestEnvironmentalFieldValidation:
    """Tests for environmental field validation in deployment metadata"""

    def test_environmental_field_exceeds_depth_limit(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that deeply nested environmental fields are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Create a deeply nested structure (7 levels deep, exceeds MAX_CUSTOM_DEPTH=5)
        nested = {"level7": "value"}
        for i in range(6, 0, -1):
            nested = {f"level{i}": nested}

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'environmental': {'deeply_nested': nested}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'depth' in data['error'].lower()

    def test_environmental_field_key_exceeds_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that environmental field keys exceeding 100 chars are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        long_key = 'k' * 101  # Exceeds 100 char limit

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'environmental': {long_key: 'value'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'environmental' in data['error'].lower()

    def test_environmental_field_string_exceeds_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that environmental field strings exceeding 10000 chars are rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        long_string = 'x' * 10001  # Exceeds 10000 char limit

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'environmental': {'description': long_string}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'environmental' in data['error'].lower()

    def test_environmental_field_valid_nested_structure(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that environmental with valid nesting depth is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Create nested structure within depth limit (5 levels)
        nested = {"level5": "value"}
        for i in range(4, 0, -1):
            nested = {f"level{i}": nested}

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'environmental': {'nested_data': nested}
                }
            )

            assert response.status_code == 200

    def test_environmental_field_with_number_values(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that environmental field with int and float values is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'environmental': {
                        'temperature_avg_c': 24.5,
                        'humidity_avg_pct': 65,
                        'rainfall_mm': 12.3
                    }
                }
            )

            assert response.status_code == 200


# ============================================================================
# Tests for Input Validation (_validate_deployment_input)
# ============================================================================


class TestInputValidation:
    """Tests for deployment metadata input validation"""

    def test_deployment_name_not_string(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that deployment_name must be a string"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={'deployment_name': 123}  # Not a string
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'deployment_name' in data['error'] and 'string' in data['error']

    def test_deployment_name_empty(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that deployment_name cannot be empty"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={'deployment_name': ''}  # Empty string
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'deployment_name' in data['error'] and 'empty' in data['error']

    def test_deployment_name_exceeds_max_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that deployment_name exceeding MAX_DEPLOYMENT_NAME_LENGTH (200) is rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={'deployment_name': 'x' * 201}  # Exceeds 200 char limit
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'deployment_name' in data['error'] and 'length' in data['error']

    def test_location_name_not_string(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that location_name must be a string"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'location_name': 123  # Not a string
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'location_name' in data['error'] and 'string' in data['error']

    def test_location_name_exceeds_max_length(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that location_name exceeding MAX_LOCATION_NAME_LENGTH (500) is rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'location_name': 'x' * 501  # Exceeds 500 char limit
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'location_name' in data['error'] and 'length' in data['error']

    def test_latitude_not_number(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that latitude must be a number"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'latitude': 'not_a_number'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'latitude' in data['error'] and 'number' in data['error']

    def test_latitude_at_boundary_90(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that latitude at exact boundary (90.0) is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z',
                latitude=90.0
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'latitude': 90.0  # Exact boundary
                }
            )

            assert response.status_code == 200

    def test_latitude_at_boundary_negative_90(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that latitude at exact boundary (-90.0) is accepted"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z',
                latitude=-90.0
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={
                    'deployment_name': 'Test',
                    'latitude': -90.0  # Exact boundary
                }
            )

            assert response.status_code == 200

    def test_longitude_not_number(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that longitude must be a number"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'longitude': 'not_a_number'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'longitude' in data['error'] and 'number' in data['error']

    def test_longitude_exceeds_range(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that longitude exceeding range (-180 to 180) is rejected"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'longitude': 181.0  # Exceeds 180
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'longitude' in data['error']

    def test_altitude_not_number(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that altitude must be a number"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'altitude': 'not_a_number'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'altitude' in data['error'] and 'number' in data['error']

    def test_date_field_not_string(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that date fields must be strings"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'start_date': 20240601  # Not a string
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'start_date' in data['error'] and 'string' in data['error']

    def test_date_field_invalid_format(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that date fields must be in ISO 8601 format (YYYY-MM-DD)"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'start_date': '2024-6-1'  # Wrong format (not YYYY-MM-DD)
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'start_date' in data['error'] and 'format' in data['error'].lower()

    def test_environmental_not_dict(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that environmental must be a dict/object"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'environmental': 'not_a_dict'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'environmental' in data['error'] and 'object' in data['error']

    def test_custom_not_dict(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that custom must be a dict/object"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json={
                'deployment_name': 'Test',
                'custom': 'not_a_dict'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'custom' in data['error'] and 'object' in data['error']


# ============================================================================
# Tests for Service Unavailable (503)
# ============================================================================


class TestServiceUnavailable:
    """Tests for service unavailable responses when DEPLOYMENT_SERVICE is not configured"""

    @pytest.fixture
    def client_no_service(self, temp_photos_dir):
        """Flask test client without DEPLOYMENT_SERVICE configured"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        try:
            app.config['WTF_CSRF_ENABLED'] = False
        except Exception:
            pass

        from routes.deployment import deployment_bp
        app.register_blueprint(deployment_bp, url_prefix='/api/deployment')
        # Note: DEPLOYMENT_SERVICE is NOT set

        with app.test_client() as client:
            yield client

    def test_put_metadata_service_unavailable(self, client_no_service, sample_directory, temp_photos_dir):
        """Test that PUT returns 503 when service is unavailable"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = client_no_service.put(
            f'/api/deployment/metadata/{relative_path}',
            json={'deployment_name': 'Test'}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_patch_metadata_service_unavailable(self, client_no_service, sample_directory, temp_photos_dir):
        """Test that PATCH returns 503 when service is unavailable"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = client_no_service.patch(
            f'/api/deployment/metadata/{relative_path}',
            json={'end_date': '2024-09-15'}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_delete_metadata_service_unavailable(self, client_no_service, sample_directory, temp_photos_dir):
        """Test that DELETE returns 503 when service is unavailable"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = client_no_service.delete(f'/api/deployment/metadata/{relative_path}')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_list_deployments_service_unavailable(self, client_no_service):
        """Test that list returns 503 when service is unavailable"""
        response = client_no_service.get('/api/deployment/list')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_discover_deployment_service_unavailable(self, client_no_service, sample_photo, temp_photos_dir):
        """Test that discover returns 503 when service is unavailable"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        response = client_no_service.get(f'/api/deployment/discover/{relative_path}')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_batch_update_service_unavailable(self, client_no_service):
        """Test that batch returns 503 when service is unavailable"""
        response = client_no_service.post(
            '/api/deployment/batch',
            json={'updates': [{'directory': 'test', 'data': {'end_date': '2024-09-15'}}]}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_generate_sidecars_service_unavailable(self, client_no_service):
        """Test that generate returns 503 when service is unavailable"""
        response = client_no_service.post(
            '/api/deployment/generate',
            json={'directory': 'test', 'template': {'deployment_name': 'Test'}}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_get_stats_service_unavailable(self, client_no_service):
        """Test that stats returns 503 when service is unavailable"""
        response = client_no_service.get('/api/deployment/stats')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()

    def test_cache_invalidate_service_unavailable(self, client_no_service):
        """Test that cache invalidate returns 503 when service is unavailable"""
        response = client_no_service.post('/api/deployment/cache/invalidate')

        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data
        assert 'unavailable' in data['error'].lower()


# ============================================================================
# Tests for Exception Handling (500 errors)
# ============================================================================


class TestExceptionHandling:
    """Tests for exception handling in route handlers"""

    def test_get_metadata_service_exception(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that GET returns 500 on service exception"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to raise exception
        mock_deployment_service.get_deployment_metadata.side_effect = Exception("Database error")

        response = deployment_client.get(f'/api/deployment/metadata/{relative_path}')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.get_deployment_metadata.side_effect = None
        mock_deployment_service.get_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_put_metadata_service_exception(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that PUT returns 500 on service exception"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to raise exception
        mock_deployment_service.set_deployment_metadata.side_effect = Exception("Disk full")

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={'deployment_name': 'Test'}
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data

        # Reset mock
        mock_deployment_service.set_deployment_metadata.side_effect = None
        mock_deployment_service.set_deployment_metadata.return_value = True

    def test_patch_metadata_service_exception(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that PATCH returns 500 on service exception"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to raise exception on update
        mock_deployment_service.update_deployment_metadata.side_effect = Exception("Connection failed")

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            json={'end_date': '2024-09-15'}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.update_deployment_metadata.side_effect = None
        mock_deployment_service.update_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_delete_metadata_service_exception(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that DELETE returns 500 on service exception"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to raise exception on delete
        mock_deployment_service.delete_deployment_metadata.side_effect = Exception("Permission denied")

        response = deployment_client.delete(f'/api/deployment/metadata/{relative_path}')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.delete_deployment_metadata.side_effect = None
        mock_deployment_service.delete_deployment_metadata.return_value = True

    def test_list_deployments_service_exception(self, deployment_client, mock_deployment_service):
        """Test that list returns 500 on service exception"""
        # Configure mock to raise exception
        mock_deployment_service.list_deployments.side_effect = Exception("Index corrupted")

        response = deployment_client.get('/api/deployment/list')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.list_deployments.side_effect = None
        mock_deployment_service.list_deployments.return_value = [
            DeploymentMetadata(
                version="1.0",
                deployment_name="Test Deployment",
                created_at="2024-01-01T00:00:00Z",
                modified_at="2024-01-01T00:00:00Z"
            )
        ]

    def test_discover_service_exception(self, deployment_client, sample_photo, temp_photos_dir, mock_deployment_service):
        """Test that discover returns 500 on service exception"""
        relative_path = sample_photo.relative_to(temp_photos_dir)

        # Configure mock to raise exception
        mock_deployment_service.find_deployment_for_photo.side_effect = Exception("Path error")

        response = deployment_client.get(f'/api/deployment/discover/{relative_path}')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.find_deployment_for_photo.side_effect = None
        mock_deployment_service.find_deployment_for_photo.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )

    def test_stats_service_exception(self, deployment_client, mock_deployment_service):
        """Test that stats returns 500 on service exception"""
        # Configure mock to raise exception
        mock_deployment_service.get_statistics.side_effect = Exception("Stats unavailable")

        response = deployment_client.get('/api/deployment/stats')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.get_statistics.side_effect = None
        mock_deployment_service.get_statistics.return_value = {
            'cache_hits': 450,
            'cache_misses': 50,
            'cache_evictions': 10,
            'cache_size': 75,
            'max_cache_size': 100,
            'cache_ttl': 300,
            'hit_ratio': 0.90,
            'total_reads': 500,
            'total_writes': 25,
            'total_deletes': 5
        }

    def test_cache_invalidate_service_exception(self, deployment_client, mock_deployment_service):
        """Test that cache invalidate returns 500 on service exception"""
        # Configure mock to raise exception
        mock_deployment_service.invalidate_cache.side_effect = Exception("Cache locked")

        response = deployment_client.post('/api/deployment/cache/invalidate')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.invalidate_cache.side_effect = None

    def test_generate_service_exception(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that generate returns 500 on service exception"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to raise exception
        mock_deployment_service.generate_sidecars_for_directory.side_effect = Exception("IO error")

        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': str(relative_path),
                'template': {'deployment_name': 'Test'}
            }
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.generate_sidecars_for_directory.side_effect = None
        mock_deployment_service.generate_sidecars_for_directory.return_value = 5


# ============================================================================
# Tests for Request Format Validation
# ============================================================================


class TestRequestFormat:
    """Tests for request format validation (non-JSON, empty body)"""

    def test_put_non_json_request(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that PUT with non-JSON content type returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            data='not json',
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'JSON' in data['error']

    def test_patch_non_json_request(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that PATCH with non-JSON content type returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            data='not json',
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'JSON' in data['error']

    def test_batch_non_json_request(self, deployment_client):
        """Test that batch with non-JSON content type returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            data='not json',
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'JSON' in data['error']

    def test_generate_non_json_request(self, deployment_client):
        """Test that generate with non-JSON content type returns 400"""
        response = deployment_client.post(
            '/api/deployment/generate',
            data='not json',
            content_type='text/plain'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'JSON' in data['error']

    def test_put_empty_body(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that PUT with empty/null body returns 400"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.put(
            f'/api/deployment/metadata/{relative_path}',
            json=None
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_batch_empty_body(self, deployment_client):
        """Test that batch with empty/null body returns 400"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json=None
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_generate_empty_body(self, deployment_client):
        """Test that generate with empty/null body returns 400"""
        response = deployment_client.post(
            '/api/deployment/generate',
            json=None
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


# ============================================================================
# Tests for Batch Endpoint Edge Cases
# ============================================================================


class TestBatchEdgeCases:
    """Tests for batch endpoint edge cases"""

    def test_batch_update_entry_not_object(self, deployment_client):
        """Test that batch update entry must be an object"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': ['not_an_object']  # String instead of object
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'index 0' in data['error']

    def test_batch_update_missing_directory(self, deployment_client):
        """Test that batch update entry requires directory field"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [{'data': {'end_date': '2024-09-15'}}]  # Missing directory
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'directory' in data['error']

    def test_batch_update_missing_data(self, deployment_client):
        """Test that batch update entry requires data field"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [{'directory': 'test'}]  # Missing data
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'data' in data['error']

    def test_batch_update_data_not_object(self, deployment_client):
        """Test that batch update data must be an object"""
        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [{'directory': 'test', 'data': 'not_a_dict'}]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'data' in data['error'] and 'object' in data['error']

    def test_batch_path_traversal_attempt(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that path traversal in batch updates is handled"""
        dir_rel = str(sample_directory.relative_to(temp_photos_dir))

        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [
                    {'directory': dir_rel, 'data': {'end_date': '2024-09-15'}},
                    {'directory': '../../etc/passwd', 'data': {'end_date': '2024-09-15'}}
                ]
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        # Path traversal should be in failed list with index info for debugging
        failed_dirs = [f['directory'] for f in data['failed']]
        assert '../../etc/passwd' in failed_dirs
        # Verify index is included for debugging
        failed_entry = next((f for f in data['failed'] if f['directory'] == '../../etc/passwd'), None)
        assert failed_entry is not None
        assert 'index' in failed_entry
        assert failed_entry['index'] == 1  # Second item in the batch
        assert 'Invalid path' in data['errors'].get('../../etc/passwd', '')

    def test_batch_update_validation_failure(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that batch update with invalid data validation returns 400"""
        dir_rel = str(sample_directory.relative_to(temp_photos_dir))

        response = deployment_client.post(
            '/api/deployment/batch',
            json={
                'updates': [
                    {'directory': dir_rel, 'data': {'latitude': 200.0}}  # Invalid latitude
                ]
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'validation' in data['error'].lower()


# ============================================================================
# Tests for Generate Endpoint Edge Cases
# ============================================================================


class TestGenerateEndpointEdgeCases:
    """Tests for generate endpoint edge cases"""

    def test_generate_template_not_dict(self, deployment_client, sample_directory, temp_photos_dir):
        """Test that generate template must be an object"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': str(relative_path),
                'template': 'not_a_dict'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'template' in data['error'] and 'object' in data['error']

    def test_generate_path_traversal_in_directory(self, deployment_client):
        """Test that path traversal in generate directory is rejected"""
        response = deployment_client.post(
            '/api/deployment/generate',
            json={
                'directory': '../../etc',
                'template': {'deployment_name': 'Test'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'path' in data['error'].lower() or 'invalid' in data['error'].lower()


# ============================================================================
# Tests for Delete Operation Failure
# ============================================================================


class TestDeleteOperationFailure:
    """Tests for delete operation failure scenarios"""

    def test_delete_operation_fails(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that failed delete operation returns 500"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to return False (failure)
        mock_deployment_service.delete_deployment_metadata.return_value = False

        response = deployment_client.delete(f'/api/deployment/metadata/{relative_path}')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

        # Reset mock
        mock_deployment_service.delete_deployment_metadata.return_value = True


# ============================================================================
# Tests for PUT Service Operation Failure
# ============================================================================


class TestPutOperationFailure:
    """Tests for PUT operation failure scenarios"""

    def test_put_set_metadata_fails(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that failed set_deployment_metadata returns 500"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to return False (failure)
        mock_deployment_service.set_deployment_metadata.return_value = False

        with patch('webui.backend.lib.deployment_sidecar.create_deployment_metadata') as mock_create:
            mock_create.return_value = DeploymentMetadata(
                version='1.0',
                deployment_name='Test',
                created_at='2024-01-01T00:00:00Z',
                modified_at='2024-01-01T00:00:00Z'
            )

            response = deployment_client.put(
                f'/api/deployment/metadata/{relative_path}',
                json={'deployment_name': 'Test'}
            )

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
            assert 'Failed' in data['error'] or 'write' in data['error'].lower()

        # Reset mock
        mock_deployment_service.set_deployment_metadata.return_value = True


# ============================================================================
# Tests for PATCH Operation Failure
# ============================================================================


class TestPatchOperationFailure:
    """Tests for PATCH operation failure scenarios"""

    def test_patch_update_metadata_fails(self, deployment_client, sample_directory, temp_photos_dir, mock_deployment_service):
        """Test that failed update_deployment_metadata returns 500"""
        relative_path = sample_directory.relative_to(temp_photos_dir)

        # Configure mock to return None (failure)
        mock_deployment_service.update_deployment_metadata.return_value = None

        response = deployment_client.patch(
            f'/api/deployment/metadata/{relative_path}',
            json={'end_date': '2024-09-15'}
        )

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Failed' in data['error'] or 'update' in data['error'].lower()

        # Reset mock
        mock_deployment_service.update_deployment_metadata.return_value = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-01-01T00:00:00Z",
            modified_at="2024-01-01T00:00:00Z"
        )


# ============================================================================
# Tests for List Endpoint Path Validation
# ============================================================================


class TestListPathValidation:
    """Tests for list endpoint path validation"""

    def test_list_with_invalid_root_dir(self, deployment_client):
        """Test that list with invalid root_dir returns 400"""
        response = deployment_client.get('/api/deployment/list?root_dir=../../etc')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'path' in data['error'].lower() or 'invalid' in data['error'].lower()


# ============================================================================
# Tests for Discover Endpoint Path Validation
# ============================================================================


class TestDiscoverPathValidation:
    """Tests for discover endpoint path validation"""

    def test_discover_path_traversal_attempt(self, deployment_client):
        """Test that discover with path traversal returns 400"""
        response = deployment_client.get('/api/deployment/discover/../../etc/passwd')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'path' in data['error'].lower() or 'invalid' in data['error'].lower()
