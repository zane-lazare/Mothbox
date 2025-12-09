"""
Unit tests for Custom Fields Discovery Endpoint (Issue #XXX)

Tests the /api/sidecar/custom-fields endpoint that discovers custom metadata
fields from sidecar files and infers their types.

Coverage Target: 95%+
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata
from webui.backend.routes.sidecar import invalidate_custom_fields_cache, sidecar_bp

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create Flask app with sidecar blueprint."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SIDECAR_SERVICE'] = MagicMock()  # Mock service
    app.config['SIDECAR_AGGREGATION_CACHE_TTL'] = 300  # 5 minutes
    app.register_blueprint(sidecar_bp, url_prefix='/api/sidecar')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def photos_dir(tmp_path):
    """Create temporary photos directory."""
    photos = tmp_path / "photos"
    photos.mkdir()
    return photos


@pytest.fixture
def sample_photo(photos_dir):
    """Create sample photo file."""
    photo = photos_dir / "photo1.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    return photo


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test."""
    invalidate_custom_fields_cache()
    yield
    invalidate_custom_fields_cache()


# ============================================================================
# Test: Basic Functionality
# ============================================================================

def test_returns_empty_fields_when_no_sidecars(client, photos_dir):
    """Should return empty fields when no sidecar files exist."""
    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['fields'] == []
        assert data['total'] == 0


def test_returns_empty_when_no_custom_fields(client, photos_dir, sample_photo):
    """Should return empty when sidecars have no custom fields."""
    # Create sidecar without custom fields
    metadata = create_metadata(
        sample_photo,
        tags=["moth"],
        species="Actias luna",
        notes="Test"
    )
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['fields'] == []
        assert data['total'] == 0


def test_discovers_text_fields(client, photos_dir):
    """Should discover text fields when >20 unique values exist."""
    # Create 25 photos with unique custom field values (> 20 = text type)
    for i in range(25):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"description": f"Unique description number {i}"}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert len(data['fields']) == 1

        field = data['fields'][0]
        assert field['name'] == 'description'
        assert field['type'] == 'text'
        # Text fields should not have 'options', only sample 'values'
        assert 'options' not in field or field['options'] is None


def test_discovers_number_fields_with_min_max(client, photos_dir):
    """Should discover number fields and calculate min/max."""
    # Create multiple photos with numeric custom field
    for i, temp in enumerate([15.5, 20.0, 25.5, 18.3]):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"temperature": temp}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'temperature'
        assert field['type'] == 'number'
        assert field['min'] == 15.5
        assert field['max'] == 25.5
        assert len(field['values']) == 4


def test_discovers_select_fields_with_options(client, photos_dir):
    """Should discover select fields with limited unique values."""
    # Create photos with repeated weather values
    for i, weather in enumerate(["Sunny", "Cloudy", "Rainy", "Sunny", "Cloudy"]):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"weather": weather}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'weather'
        assert field['type'] == 'select'
        assert set(field['options']) == {"Sunny", "Cloudy", "Rainy"}
        assert len(field['values']) == 5


def test_select_field_with_20_unique_values(client, photos_dir):
    """Should treat field as select when exactly 20 unique values."""
    # Create 20 photos with unique values
    for i in range(20):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"category": f"category_{i}"}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'category'
        assert field['type'] == 'select'
        assert len(field['options']) == 20


def test_text_field_with_more_than_20_unique_values(client, photos_dir):
    """Should treat field as text when more than 20 unique values."""
    # Create 25 photos with unique values
    for i in range(25):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"description": f"description_{i}"}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'description'
        assert field['type'] == 'text'
        assert 'options' not in field  # text fields don't have options
        assert len(field['values']) <= 20  # Limited to 20 samples


# ============================================================================
# Test: Field Exclusions
# ============================================================================

def test_excludes_standard_fields(client, photos_dir, sample_photo):
    """Should exclude standard schema fields from custom fields."""
    # Create sidecar with standard fields in custom (should be ignored)
    metadata = create_metadata(sample_photo)
    metadata.custom = {
        "tags": ["should_be_ignored"],
        "species": "should_be_ignored",
        "notes": "should_be_ignored",
        "version": "should_be_ignored",
        "custom_field": "should_be_included"
    }
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['fields'][0]['name'] == 'custom_field'


def test_excludes_private_fields(client, photos_dir, sample_photo):
    """Should exclude fields starting with underscore."""
    # Create sidecar with private fields
    metadata = create_metadata(sample_photo)
    metadata.custom = {
        "_internal": "should_be_ignored",
        "_cache_key": "should_be_ignored",
        "public_field": "should_be_included"
    }
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['fields'][0]['name'] == 'public_field'


def test_excludes_v11_species_fields(client, photos_dir, sample_photo):
    """Should exclude v1.1 species schema fields."""
    # Create sidecar with v1.1 species fields in custom
    metadata = create_metadata(sample_photo)
    metadata.custom = {
        "species_confidence": "should_be_ignored",
        "species_common_name": "should_be_ignored",
        "species_reference_url": "should_be_ignored",
        "custom_field": "should_be_included"
    }
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['fields'][0]['name'] == 'custom_field'


# ============================================================================
# Test: Multiple Fields
# ============================================================================

def test_discovers_multiple_fields_different_types(client, photos_dir):
    """Should discover multiple fields with different types."""
    # Create photo with text, number, and select fields
    photo = photos_dir / "photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    metadata = create_metadata(photo)
    metadata.custom = {
        "location": "Forest",
        "temperature": 22.5,
        "weather": "Sunny"
    }
    write_metadata(photo, metadata)

    # Create second photo with same fields
    photo2 = photos_dir / "photo2.jpg"
    photo2.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    metadata2 = create_metadata(photo2)
    metadata2.custom = {
        "location": "Meadow",
        "temperature": 25.0,
        "weather": "Cloudy"
    }
    write_metadata(photo2, metadata2)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 3

        # Check fields are sorted by name
        field_names = [f['name'] for f in data['fields']]
        assert field_names == sorted(field_names)

        # Check individual fields
        location_field = next(f for f in data['fields'] if f['name'] == 'location')
        assert location_field['type'] == 'select'
        assert set(location_field['options']) == {"Forest", "Meadow"}

        temp_field = next(f for f in data['fields'] if f['name'] == 'temperature')
        assert temp_field['type'] == 'number'
        assert temp_field['min'] == 22.5
        assert temp_field['max'] == 25.0

        weather_field = next(f for f in data['fields'] if f['name'] == 'weather')
        assert weather_field['type'] == 'select'


# ============================================================================
# Test: Caching
# ============================================================================

def test_caches_results(client, photos_dir, sample_photo):
    """Should cache results and reuse on subsequent requests."""
    metadata = create_metadata(sample_photo)
    metadata.custom = {"location": "Forest"}
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        # First request - should build cache
        response1 = client.get('/api/sidecar/custom-fields')
        assert response1.status_code == 200

        # Second request - should use cache
        response2 = client.get('/api/sidecar/custom-fields')
        assert response2.status_code == 200

        # Results should be identical
        assert response1.get_json() == response2.get_json()


def test_cache_invalidation(client, photos_dir, sample_photo):
    """Should invalidate cache when metadata changes."""
    metadata = create_metadata(sample_photo)
    metadata.custom = {"location": "Forest"}
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        # First request
        response1 = client.get('/api/sidecar/custom-fields')
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['total'] == 1

        # Invalidate cache
        invalidate_custom_fields_cache()

        # Add new custom field
        photo2 = photos_dir / "photo2.jpg"
        photo2.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata2 = create_metadata(photo2)
        metadata2.custom = {"weather": "Sunny"}
        write_metadata(photo2, metadata2)

        # Second request should see new field
        response2 = client.get('/api/sidecar/custom-fields')
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['total'] == 2


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_handles_invalid_sidecar_data(client, photos_dir, sample_photo):
    """Should skip invalid sidecar files gracefully."""
    # Create valid sidecar
    metadata = create_metadata(sample_photo)
    metadata.custom = {"location": "Forest"}
    write_metadata(sample_photo, metadata)

    # Create invalid sidecar (malformed JSON)
    invalid_photo = photos_dir / "invalid.jpg"
    invalid_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    invalid_sidecar = photos_dir / "invalid.jpg.json"
    invalid_sidecar.write_text("{ invalid json")

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        # Should still find the valid field
        assert data['total'] == 1
        assert data['fields'][0]['name'] == 'location'


def test_handles_non_dict_custom_field(client, photos_dir, sample_photo):
    """Should skip sidecars where custom is not a dict."""
    # Create sidecar with custom as list (invalid)
    sidecar_path = photos_dir / f"{sample_photo.name}.json"
    sidecar_data = {
        "version": "1.0",
        "photo_filename": sample_photo.name,
        "created_at": "2024-01-01T00:00:00Z",
        "modified_at": "2024-01-01T00:00:00Z",
        "tags": [],
        "species": None,
        "notes": None,
        "custom": ["not", "a", "dict"],  # Invalid
        "modified_by": None
    }
    sidecar_path.write_text(json.dumps(sidecar_data))

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0  # Should skip invalid custom field


def test_handles_null_values(client, photos_dir):
    """Should handle fields with all null values."""
    photo = photos_dir / "photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    metadata = create_metadata(photo)
    metadata.custom = {"nullable_field": None}
    write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'nullable_field'
        assert field['type'] == 'text'
        assert field['values'] == []


def test_handles_mixed_null_values(client, photos_dir):
    """Should handle fields with some null values."""
    for i, value in enumerate([None, 15.5, None, 20.0]):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"temperature": value}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'temperature'
        assert field['type'] == 'number'
        assert field['min'] == 15.5
        assert field['max'] == 20.0


def test_limits_sample_values_to_20(client, photos_dir):
    """Should limit sample values to 20 entries."""
    # Create 30 photos with unique text values
    for i in range(30):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"description": f"description_{i}"}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert len(field['values']) == 20


def test_handles_integer_numbers(client, photos_dir, sample_photo):
    """Should treat integers as numbers."""
    metadata = create_metadata(sample_photo)
    metadata.custom = {"count": 42}
    write_metadata(sample_photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['name'] == 'count'
        assert field['type'] == 'number'
        assert field['min'] == 42
        assert field['max'] == 42


def test_handles_mixed_numeric_types(client, photos_dir):
    """Should handle mix of integers and floats."""
    for i, value in enumerate([10, 15.5, 20, 22.3]):
        photo = photos_dir / f"photo{i}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        metadata.custom = {"value": value}
        write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1

        field = data['fields'][0]
        assert field['type'] == 'number'
        assert field['min'] == 10
        assert field['max'] == 22.3


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_returns_503_when_service_unavailable(client, photos_dir):
    """Should return 503 when sidecar service is not available."""
    # Remove service from config
    client.application.config['SIDECAR_SERVICE'] = None

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 503
        data = response.get_json()
        assert 'error' in data


def test_handles_file_read_errors(client, photos_dir, sample_photo):
    """Should handle file read errors gracefully."""
    # Create valid sidecar
    metadata = create_metadata(sample_photo)
    metadata.custom = {"location": "Forest"}
    write_metadata(sample_photo, metadata)

    # Create sidecar with read permission issue (simulate with mock)
    photo2 = photos_dir / "photo2.jpg"
    photo2.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
    sidecar2 = photos_dir / "photo2.jpg.json"
    sidecar2.write_text('{"custom": {"weather": "Sunny"}}')

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        # Mock read_text to raise OSError for second file
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if self.name == "photo2.jpg.json":
                raise OSError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            response = client.get('/api/sidecar/custom-fields')
            assert response.status_code == 200
            data = response.get_json()
            # Should still find the first field
            assert data['total'] == 1
            assert data['fields'][0]['name'] == 'location'


# ============================================================================
# Test: Response Format
# ============================================================================

def test_response_format_structure(client, photos_dir):
    """Should return correctly structured response."""
    # Create photo with all field types
    photo = photos_dir / "photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    metadata = create_metadata(photo)
    metadata.custom = {
        "location": "Forest",
        "temperature": 22.5,
        "weather": "Sunny"
    }
    write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()

        # Check top-level structure
        assert 'fields' in data
        assert 'total' in data
        assert isinstance(data['fields'], list)
        assert isinstance(data['total'], int)

        # Check field structure
        for field in data['fields']:
            assert 'name' in field
            assert 'type' in field
            assert 'values' in field
            assert field['type'] in ['text', 'number', 'select']

            if field['type'] == 'number':
                assert 'min' in field
                assert 'max' in field
            elif field['type'] == 'select':
                assert 'options' in field


def test_fields_sorted_alphabetically(client, photos_dir):
    """Should return fields sorted alphabetically by name."""
    photo = photos_dir / "photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    metadata = create_metadata(photo)
    metadata.custom = {
        "zebra": "value",
        "alpha": "value",
        "beta": "value"
    }
    write_metadata(photo, metadata)

    with patch('webui.backend.routes.sidecar.PHOTOS_DIR', photos_dir):
        response = client.get('/api/sidecar/custom-fields')
        assert response.status_code == 200
        data = response.get_json()

        field_names = [f['name'] for f in data['fields']]
        assert field_names == ['alpha', 'beta', 'zebra']
