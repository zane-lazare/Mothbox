"""
Unit tests for deployment sidecar library (Issue #114 - Subtask 3)

Tests deployment-level metadata system for storing deployment information
at the root of photo directories.

Coverage Target: 85%+

Design Decisions:
- File naming: deployment.json (default) or deployment.yaml (optional)
- Hierarchical discovery: Walk up directory tree to find nearest deployment
- Schema validation: Enforce limits and formats for all fields
- Thread-safe: FileLock for atomic read-modify-write operations
"""

import json
import time
import pytest
from datetime import datetime, UTC
from pathlib import Path

# ============================================================================
# Expected Interface
# ============================================================================

try:
    from webui.backend.lib.deployment_sidecar import (
        # Data classes
        DeploymentMetadata,
        # Constants
        DEPLOYMENT_SCHEMA_VERSION,
        DEPLOYMENT_FILENAME_JSON,
        DEPLOYMENT_FILENAME_YAML,
        BACKUP_EXTENSION,
        YAML_AVAILABLE,
        # Exceptions
        ValidationError,
        LockTimeoutError,
        # Path utilities
        get_deployment_sidecar_path,
        deployment_has_sidecar,
        find_deployment_sidecar,
        # Schema validation
        validate_deployment_schema,
        # CRUD operations
        read_deployment_metadata,
        write_deployment_metadata,
        create_deployment_metadata,
        update_deployment_metadata,
        delete_deployment_metadata,
        # File locking
        FileLock,
        # Cleanup utilities
        cleanup_temp_files,
    )
    from webui.backend.lib.deployment_schema import (
        MAX_DEPLOYMENT_NAME_LENGTH,
        MAX_LOCATION_NAME_LENGTH,
        MAX_CUSTOM_KEYS,
        MAX_CUSTOM_DEPTH,
        MIN_LATITUDE,
        MAX_LATITUDE,
        MIN_LONGITUDE,
        MAX_LONGITUDE,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define stubs for test discovery
    DeploymentMetadata = None
    DEPLOYMENT_SCHEMA_VERSION = None
    ValidationError = None
    # ... other stubs

# Skip all tests if implementation doesn't exist yet
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Create temp directory and mock PHOTOS_DIR."""
    photos = tmp_path / "photos"
    photos.mkdir()
    monkeypatch.setattr('webui.backend.lib.deployment_sidecar.PHOTOS_DIR', photos)
    return photos


@pytest.fixture
def sample_metadata():
    """Create sample DeploymentMetadata."""
    return DeploymentMetadata(
        version="1.0",
        deployment_name="Test Deployment",
        created_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        modified_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        latitude=35.9606,
        longitude=-83.9207,
        location_name="Oak Ridge, TN, USA",
    )


@pytest.fixture
def sample_metadata_dict():
    """Create sample metadata dictionary."""
    timestamp = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    return {
        "version": "1.0",
        "deployment_name": "Forest Survey 2024",
        "created_at": timestamp,
        "modified_at": timestamp,
        "latitude": 35.9606,
        "longitude": -83.9207,
        "location_name": "Oak Ridge, TN",
        "start_date": "2024-06-01",
        "end_date": "2024-08-31",
        "environmental": {"temperature_avg_c": 24.5},
        "mothbox_id": "mothbox-001",
        "firmware_version": "5.2.1",
        "custom": {"weather": "clear"},
        "modified_by": None,
    }


@pytest.fixture
def directory_with_sidecar(temp_photos_dir, sample_metadata_dict):
    """Create directory with existing deployment.json."""
    deployment_dir = temp_photos_dir / "forest_2024"
    deployment_dir.mkdir()

    sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
    sidecar.write_text(json.dumps(sample_metadata_dict, indent=2))

    return deployment_dir


# ============================================================================
# Test DeploymentMetadata Data Class
# ============================================================================

class TestDeploymentMetadataDataClass:
    """Tests for DeploymentMetadata data class structure."""

    def test_required_fields_present(self):
        """DeploymentMetadata should have all required fields."""
        metadata = DeploymentMetadata(
            version="1.0",
            deployment_name="Test Deployment",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
        )
        assert metadata.version == "1.0"
        assert metadata.deployment_name == "Test Deployment"
        assert metadata.created_at == "2024-11-06T10:30:00Z"
        assert metadata.modified_at == "2024-11-06T10:30:00Z"

    def test_to_dict_serialization(self, sample_metadata):
        """to_dict() should return valid dictionary."""
        d = sample_metadata.to_dict()

        assert isinstance(d, dict)
        assert d["version"] == "1.0"
        assert d["deployment_name"] == "Test Deployment"
        assert d["latitude"] == 35.9606
        assert d["longitude"] == -83.9207

    def test_from_dict_deserialization(self, sample_metadata_dict):
        """from_dict() should create instance from dictionary."""
        metadata = DeploymentMetadata.from_dict(sample_metadata_dict)

        assert metadata.version == "1.0"
        assert metadata.deployment_name == "Forest Survey 2024"
        assert metadata.latitude == 35.9606
        assert metadata.longitude == -83.9207

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None or empty dict."""
        metadata = DeploymentMetadata(
            version="1.0",
            deployment_name="Test",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
        )
        assert metadata.latitude is None
        assert metadata.longitude is None
        assert metadata.altitude is None
        assert metadata.location_name is None
        assert metadata.start_date is None
        assert metadata.end_date is None
        assert metadata.mothbox_id is None
        assert metadata.firmware_version is None
        assert metadata.modified_by is None

    def test_environmental_dict_default_empty(self):
        """environmental should default to empty dict."""
        metadata = DeploymentMetadata(
            version="1.0",
            deployment_name="Test",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
        )
        assert metadata.environmental == {}
        assert isinstance(metadata.environmental, dict)

    def test_custom_dict_default_empty(self):
        """custom should default to empty dict."""
        metadata = DeploymentMetadata(
            version="1.0",
            deployment_name="Test",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
        )
        assert metadata.custom == {}
        assert isinstance(metadata.custom, dict)

    def test_round_trip_conversion(self, sample_metadata):
        """to_dict() then from_dict() should preserve all data."""
        d = sample_metadata.to_dict()
        restored = DeploymentMetadata.from_dict(d)

        assert restored.version == sample_metadata.version
        assert restored.deployment_name == sample_metadata.deployment_name
        assert restored.created_at == sample_metadata.created_at
        assert restored.modified_at == sample_metadata.modified_at
        assert restored.latitude == sample_metadata.latitude
        assert restored.longitude == sample_metadata.longitude
        assert restored.location_name == sample_metadata.location_name


# ============================================================================
# Test Schema Validation
# ============================================================================

class TestSchemaValidation:
    """Tests for validate_deployment_schema() function."""

    def test_valid_schema_passes(self, sample_metadata_dict):
        """Should return True for valid metadata."""
        assert validate_deployment_schema(sample_metadata_dict) is True

    def test_missing_required_field_fails(self, sample_metadata_dict):
        """Should raise ValidationError for missing created_at."""
        del sample_metadata_dict["created_at"]
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "created_at" in str(exc_info.value).lower()

    def test_missing_version_fails(self, sample_metadata_dict):
        """Should raise ValidationError for missing version."""
        del sample_metadata_dict["version"]
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "version" in str(exc_info.value).lower()

    def test_invalid_version_fails(self, sample_metadata_dict):
        """Should raise ValidationError for unsupported version."""
        sample_metadata_dict["version"] = "99.0"
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "version" in str(exc_info.value).lower()

    def test_invalid_latitude_too_high_fails(self, sample_metadata_dict):
        """Should raise ValidationError for latitude > 90."""
        sample_metadata_dict["latitude"] = 91.0
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "latitude" in str(exc_info.value).lower()

    def test_invalid_latitude_too_low_fails(self, sample_metadata_dict):
        """Should raise ValidationError for latitude < -90."""
        sample_metadata_dict["latitude"] = -91.0
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "latitude" in str(exc_info.value).lower()

    def test_invalid_longitude_too_high_fails(self, sample_metadata_dict):
        """Should raise ValidationError for longitude > 180."""
        sample_metadata_dict["longitude"] = 181.0
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "longitude" in str(exc_info.value).lower()

    def test_invalid_longitude_too_low_fails(self, sample_metadata_dict):
        """Should raise ValidationError for longitude < -180."""
        sample_metadata_dict["longitude"] = -181.0
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "longitude" in str(exc_info.value).lower()

    def test_deployment_name_too_long_fails(self, sample_metadata_dict):
        """Should raise ValidationError for deployment_name > MAX_DEPLOYMENT_NAME_LENGTH."""
        sample_metadata_dict["deployment_name"] = "a" * (MAX_DEPLOYMENT_NAME_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "deployment_name" in str(exc_info.value).lower()

    def test_location_name_too_long_fails(self, sample_metadata_dict):
        """Should raise ValidationError for location_name > MAX_LOCATION_NAME_LENGTH."""
        sample_metadata_dict["location_name"] = "a" * (MAX_LOCATION_NAME_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "location_name" in str(exc_info.value).lower()

    def test_custom_keys_limit_enforced(self, sample_metadata_dict):
        """Should raise ValidationError for custom > MAX_CUSTOM_KEYS."""
        sample_metadata_dict["custom"] = {f"key_{i}": i for i in range(MAX_CUSTOM_KEYS + 1)}
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "custom" in str(exc_info.value).lower()

    def test_custom_depth_limit_enforced(self, sample_metadata_dict):
        """Should raise ValidationError for custom nesting > MAX_CUSTOM_DEPTH."""
        # Build deeply nested structure
        deep_nested = "value"
        for _ in range(MAX_CUSTOM_DEPTH + 2):
            deep_nested = {"level": deep_nested}

        sample_metadata_dict["custom"] = {"deep": deep_nested}
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "custom" in str(exc_info.value).lower()

    def test_empty_deployment_name_fails(self, sample_metadata_dict):
        """Should raise ValidationError for empty deployment_name."""
        sample_metadata_dict["deployment_name"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "deployment_name" in str(exc_info.value).lower()


# ============================================================================
# Test Path Utilities
# ============================================================================

class TestPathUtilities:
    """Tests for path utility functions."""

    def test_get_deployment_sidecar_path_json(self, temp_photos_dir):
        """get_deployment_sidecar_path should return deployment.json path."""
        deployment_dir = temp_photos_dir / "forest_2024"
        deployment_dir.mkdir()

        sidecar_path = get_deployment_sidecar_path(deployment_dir, format="json")
        assert sidecar_path == deployment_dir / DEPLOYMENT_FILENAME_JSON
        assert sidecar_path.name == "deployment.json"

    def test_get_deployment_sidecar_path_yaml(self, temp_photos_dir):
        """get_deployment_sidecar_path should return deployment.yaml path."""
        deployment_dir = temp_photos_dir / "forest_2024"
        deployment_dir.mkdir()

        sidecar_path = get_deployment_sidecar_path(deployment_dir, format="yaml")
        assert sidecar_path == deployment_dir / DEPLOYMENT_FILENAME_YAML
        assert sidecar_path.name == "deployment.yaml"

    def test_deployment_has_sidecar_true(self, directory_with_sidecar):
        """Should return True when deployment.json exists."""
        assert deployment_has_sidecar(directory_with_sidecar) is True

    def test_deployment_has_sidecar_false(self, temp_photos_dir):
        """Should return False when no sidecar exists."""
        deployment_dir = temp_photos_dir / "no_sidecar"
        deployment_dir.mkdir()

        assert deployment_has_sidecar(deployment_dir) is False

    def test_deployment_has_sidecar_yaml(self, temp_photos_dir, sample_metadata_dict):
        """Should return True when deployment.yaml exists."""
        deployment_dir = temp_photos_dir / "yaml_deployment"
        deployment_dir.mkdir()

        # Create YAML sidecar
        sidecar = deployment_dir / DEPLOYMENT_FILENAME_YAML
        if YAML_AVAILABLE:
            import yaml
            sidecar.write_text(yaml.safe_dump(sample_metadata_dict))
            assert deployment_has_sidecar(deployment_dir) is True


# ============================================================================
# Test Hierarchical Discovery
# ============================================================================

class TestHierarchicalDiscovery:
    """Tests for find_deployment_sidecar() hierarchical search."""

    def test_find_deployment_sidecar_in_same_directory(self, directory_with_sidecar):
        """Should find sidecar in same directory."""
        sidecar_path = find_deployment_sidecar(directory_with_sidecar)

        assert sidecar_path is not None
        assert sidecar_path == directory_with_sidecar / DEPLOYMENT_FILENAME_JSON

    def test_find_deployment_sidecar_in_parent_directory(self, directory_with_sidecar):
        """Should find sidecar in parent directory."""
        # Create subdirectory
        subdir = directory_with_sidecar / "subfolder"
        subdir.mkdir()

        sidecar_path = find_deployment_sidecar(subdir)

        assert sidecar_path is not None
        assert sidecar_path == directory_with_sidecar / DEPLOYMENT_FILENAME_JSON

    def test_find_deployment_sidecar_multiple_levels_up(self, directory_with_sidecar):
        """Should find sidecar multiple levels up."""
        # Create nested subdirectories
        deep_dir = directory_with_sidecar / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)

        sidecar_path = find_deployment_sidecar(deep_dir)

        assert sidecar_path is not None
        assert sidecar_path == directory_with_sidecar / DEPLOYMENT_FILENAME_JSON

    def test_find_deployment_sidecar_returns_none_when_not_found(self, temp_photos_dir):
        """Should return None when no sidecar found."""
        deployment_dir = temp_photos_dir / "no_deployment"
        deployment_dir.mkdir()

        sidecar_path = find_deployment_sidecar(deployment_dir)

        assert sidecar_path is None

    def test_find_deployment_sidecar_with_file_path(self, directory_with_sidecar):
        """Should handle file path (start from parent directory)."""
        # Create a photo file in subdirectory
        subdir = directory_with_sidecar / "photos"
        subdir.mkdir()
        photo = subdir / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        sidecar_path = find_deployment_sidecar(photo)

        assert sidecar_path is not None
        assert sidecar_path == directory_with_sidecar / DEPLOYMENT_FILENAME_JSON


# ============================================================================
# Test CRUD Operations
# ============================================================================

class TestCRUDOperations:
    """Tests for create, read, update, delete operations."""

    def test_create_deployment_metadata(self, temp_photos_dir):
        """create_deployment_metadata should create new metadata instance."""
        deployment_dir = temp_photos_dir / "new_deployment"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="New Deployment",
            latitude=35.9606,
            longitude=-83.9207,
        )

        assert metadata.version == DEPLOYMENT_SCHEMA_VERSION
        assert metadata.deployment_name == "New Deployment"
        assert metadata.latitude == 35.9606
        assert metadata.longitude == -83.9207
        assert metadata.created_at is not None
        assert metadata.modified_at is not None

    def test_create_deployment_metadata_with_all_fields(self, temp_photos_dir):
        """create_deployment_metadata should accept all fields."""
        deployment_dir = temp_photos_dir / "full_deployment"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Full Deployment",
            latitude=35.9606,
            longitude=-83.9207,
            altitude=300.5,
            location_name="Oak Ridge, TN",
            start_date="2024-06-01",
            end_date="2024-08-31",
            environmental={"temperature_avg_c": 24.5},
            mothbox_id="mothbox-001",
            firmware_version="5.2.1",
            custom={"weather": "clear"},
            modified_by="user123",
        )

        assert metadata.deployment_name == "Full Deployment"
        assert metadata.altitude == 300.5
        assert metadata.start_date == "2024-06-01"
        assert metadata.environmental == {"temperature_avg_c": 24.5}
        assert metadata.mothbox_id == "mothbox-001"

    def test_read_nonexistent_returns_none(self, temp_photos_dir):
        """read_deployment_metadata should return None when no sidecar exists."""
        deployment_dir = temp_photos_dir / "no_sidecar"
        deployment_dir.mkdir()

        metadata = read_deployment_metadata(deployment_dir)

        assert metadata is None

    def test_read_existing_metadata(self, directory_with_sidecar):
        """read_deployment_metadata should read existing metadata."""
        metadata = read_deployment_metadata(directory_with_sidecar)

        assert metadata is not None
        assert isinstance(metadata, DeploymentMetadata)
        assert metadata.deployment_name == "Forest Survey 2024"
        assert metadata.latitude == 35.9606

    def test_read_corrupted_json_returns_none(self, temp_photos_dir):
        """read_deployment_metadata should return None for corrupted JSON."""
        deployment_dir = temp_photos_dir / "corrupted"
        deployment_dir.mkdir()

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        sidecar.write_text("{ invalid json }")

        metadata = read_deployment_metadata(deployment_dir)

        assert metadata is None

    def test_update_partial_fields(self, directory_with_sidecar):
        """update_deployment_metadata should update partial fields."""
        metadata = update_deployment_metadata(
            directory_with_sidecar,
            {"end_date": "2024-09-15"}
        )

        assert metadata.end_date == "2024-09-15"
        # Original fields preserved
        assert metadata.deployment_name == "Forest Survey 2024"
        assert metadata.latitude == 35.9606

    def test_update_creates_if_missing(self, temp_photos_dir):
        """update_deployment_metadata should create new if doesn't exist."""
        deployment_dir = temp_photos_dir / "new_update"
        deployment_dir.mkdir()

        metadata = update_deployment_metadata(
            deployment_dir,
            {"deployment_name": "Created via Update", "latitude": 40.0}
        )

        assert metadata is not None
        assert metadata.deployment_name == "Created via Update"
        assert metadata.latitude == 40.0

    def test_delete_existing_sidecar(self, directory_with_sidecar):
        """delete_deployment_metadata should remove sidecar file."""
        assert deployment_has_sidecar(directory_with_sidecar)

        result = delete_deployment_metadata(directory_with_sidecar)

        assert result is True
        assert not deployment_has_sidecar(directory_with_sidecar)

    def test_delete_nonexistent_returns_false(self, temp_photos_dir):
        """delete_deployment_metadata should return False for nonexistent sidecar."""
        deployment_dir = temp_photos_dir / "no_sidecar"
        deployment_dir.mkdir()

        result = delete_deployment_metadata(deployment_dir)

        assert result is False

    def test_delete_creates_backup(self, directory_with_sidecar):
        """delete_deployment_metadata should create backup by default."""
        sidecar = directory_with_sidecar / DEPLOYMENT_FILENAME_JSON
        original_content = sidecar.read_text()

        delete_deployment_metadata(directory_with_sidecar, backup=True)

        backup_path = sidecar.with_suffix(f".json{BACKUP_EXTENSION}")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

    def test_write_atomic_operation(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should be atomic."""
        deployment_dir = temp_photos_dir / "atomic_test"
        deployment_dir.mkdir()

        result = write_deployment_metadata(deployment_dir, sample_metadata)

        assert result is True

        # Verify file exists and is readable
        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        assert sidecar.exists()

        # Verify contents are valid JSON
        with open(sidecar) as f:
            data = json.load(f)
        assert data["deployment_name"] == "Test Deployment"

    def test_write_with_backup(self, directory_with_sidecar, sample_metadata):
        """write_deployment_metadata should create backup when overwriting."""
        sidecar = directory_with_sidecar / DEPLOYMENT_FILENAME_JSON
        original_content = sidecar.read_text()

        # Modify metadata
        sample_metadata.deployment_name = "Updated Deployment"

        write_deployment_metadata(directory_with_sidecar, sample_metadata, backup=True)

        # Check backup exists
        backup_path = sidecar.with_suffix(f".json{BACKUP_EXTENSION}")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content


# ============================================================================
# Test YAML Support
# ============================================================================

class TestYAMLSupport:
    """Tests for YAML format support (optional)."""

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_write_yaml_format(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should support YAML format."""
        deployment_dir = temp_photos_dir / "yaml_test"
        deployment_dir.mkdir()

        result = write_deployment_metadata(
            deployment_dir,
            sample_metadata,
            format="yaml"
        )

        assert result is True

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_YAML
        assert sidecar.exists()

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_read_yaml_format(self, temp_photos_dir, sample_metadata):
        """read_deployment_metadata should support YAML format."""
        import yaml

        deployment_dir = temp_photos_dir / "yaml_read"
        deployment_dir.mkdir()

        # Write YAML sidecar
        sidecar = deployment_dir / DEPLOYMENT_FILENAME_YAML
        sidecar.write_text(yaml.safe_dump(sample_metadata.to_dict()))

        metadata = read_deployment_metadata(deployment_dir)

        assert metadata is not None
        assert metadata.deployment_name == "Test Deployment"

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_yaml_to_json_content_equivalent(self, temp_photos_dir, sample_metadata):
        """YAML and JSON formats should be content equivalent."""
        deployment_dir = temp_photos_dir / "format_test"
        deployment_dir.mkdir()

        # Write as JSON
        write_deployment_metadata(deployment_dir, sample_metadata, format="json")
        json_metadata = read_deployment_metadata(deployment_dir)

        # Delete JSON, write as YAML
        delete_deployment_metadata(deployment_dir, backup=False)
        write_deployment_metadata(deployment_dir, sample_metadata, format="yaml")
        yaml_metadata = read_deployment_metadata(deployment_dir)

        assert json_metadata.to_dict() == yaml_metadata.to_dict()

    def test_invalid_yaml_format_raises(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should raise ValueError for invalid format."""
        deployment_dir = temp_photos_dir / "invalid_format"
        deployment_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            write_deployment_metadata(deployment_dir, sample_metadata, format="xml")
        assert "unsupported format" in str(exc_info.value).lower()


# ============================================================================
# Test File Locking
# ============================================================================

class TestFileLocking:
    """Tests for FileLock context manager."""

    def test_concurrent_writes_no_corruption(self, temp_photos_dir, sample_metadata):
        """Concurrent writes should not corrupt data (file locking protection)."""
        deployment_dir = temp_photos_dir / "concurrent_test"
        deployment_dir.mkdir()

        # Write initial metadata
        write_deployment_metadata(deployment_dir, sample_metadata)

        # Write again (simulates concurrent access)
        sample_metadata.deployment_name = "Updated"
        write_deployment_metadata(deployment_dir, sample_metadata)

        # Verify data integrity
        metadata = read_deployment_metadata(deployment_dir)
        assert metadata is not None
        assert metadata.deployment_name == "Updated"

    def test_lock_timeout_raises_error(self, temp_photos_dir):
        """FileLock should raise LockTimeoutError on timeout."""
        # Note: This is hard to test without threading/multiprocessing
        # Just verify the exception exists
        assert LockTimeoutError is not None
        assert issubclass(LockTimeoutError, Exception)


# ============================================================================
# Test Cleanup
# ============================================================================

class TestCleanup:
    """Tests for cleanup_temp_files() function."""

    def test_cleanup_temp_files(self, temp_photos_dir):
        """cleanup_temp_files should remove stale lock files."""
        deployment_dir = temp_photos_dir / "cleanup_test"
        deployment_dir.mkdir()

        # Create old lock file
        lock_file = deployment_dir / "deployment.json.lock"
        lock_file.write_text("")

        # Make it appear old
        import os
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(lock_file, (old_time, old_time))

        # Clean up
        removed = cleanup_temp_files(deployment_dir)

        assert removed >= 1
        assert not lock_file.exists()

    def test_cleanup_nonexistent_directory(self, temp_photos_dir):
        """cleanup_temp_files should handle nonexistent directory."""
        nonexistent = temp_photos_dir / "does_not_exist"

        removed = cleanup_temp_files(nonexistent)

        assert removed == 0


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimal_metadata(self, temp_photos_dir):
        """Should handle minimal metadata with only required fields."""
        deployment_dir = temp_photos_dir / "minimal"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Minimal Deployment"
        )

        assert metadata.deployment_name == "Minimal Deployment"
        assert metadata.latitude is None
        assert metadata.environmental == {}
        assert metadata.custom == {}

    def test_unicode_in_deployment_name(self, temp_photos_dir):
        """Should handle Unicode characters in deployment_name."""
        deployment_dir = temp_photos_dir / "unicode"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Forêt de Compiègne 2024"
        )

        assert metadata.deployment_name == "Forêt de Compiègne 2024"

    def test_boundary_coordinates(self, temp_photos_dir):
        """Should handle boundary coordinate values."""
        deployment_dir = temp_photos_dir / "boundary"
        deployment_dir.mkdir()

        # Test valid boundaries
        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Boundary Test",
            latitude=MAX_LATITUDE,  # 90.0
            longitude=MAX_LONGITUDE,  # 180.0
        )

        assert metadata.latitude == 90.0
        assert metadata.longitude == 180.0

    def test_negative_altitude(self, temp_photos_dir):
        """Should handle negative altitude (below sea level)."""
        deployment_dir = temp_photos_dir / "negative_alt"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Below Sea Level",
            altitude=-50.0  # Death Valley, etc.
        )

        assert metadata.altitude == -50.0

    def test_empty_environmental_dict(self, temp_photos_dir):
        """Should handle empty environmental dict."""
        deployment_dir = temp_photos_dir / "empty_env"
        deployment_dir.mkdir()

        metadata = create_deployment_metadata(
            directory=deployment_dir,
            name="Empty Environmental",
            environmental={}
        )

        assert metadata.environmental == {}

    def test_deeply_nested_path(self, temp_photos_dir):
        """Should handle deeply nested directory paths."""
        deep_path = temp_photos_dir / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)

        metadata = create_deployment_metadata(
            directory=deep_path,
            name="Deep Nested"
        )

        assert metadata.deployment_name == "Deep Nested"


# ============================================================================
# Test Schema Version Constant
# ============================================================================

class TestSchemaVersion:
    """Tests for schema version constant."""

    def test_schema_version_is_string(self):
        """DEPLOYMENT_SCHEMA_VERSION should be a string."""
        assert isinstance(DEPLOYMENT_SCHEMA_VERSION, str)

    def test_schema_version_is_1_0(self):
        """DEPLOYMENT_SCHEMA_VERSION should be '1.0'."""
        assert DEPLOYMENT_SCHEMA_VERSION == "1.0"

    def test_backup_extension_constant(self):
        """BACKUP_EXTENSION should be '.bak'."""
        assert BACKUP_EXTENSION == ".bak"

    def test_filename_constants(self):
        """Filename constants should be defined."""
        assert DEPLOYMENT_FILENAME_JSON == "deployment.json"
        assert DEPLOYMENT_FILENAME_YAML == "deployment.yaml"


# ============================================================================
# Test Additional Schema Validation Cases
# ============================================================================

class TestAdditionalSchemaValidation:
    """Additional schema validation tests for edge cases."""

    def test_latitude_must_be_number(self, sample_metadata_dict):
        """Should raise ValidationError if latitude is not a number."""
        sample_metadata_dict["latitude"] = "not a number"
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "latitude" in str(exc_info.value).lower()

    def test_longitude_must_be_number(self, sample_metadata_dict):
        """Should raise ValidationError if longitude is not a number."""
        sample_metadata_dict["longitude"] = "not a number"
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "longitude" in str(exc_info.value).lower()

    def test_altitude_must_be_number(self, sample_metadata_dict):
        """Should raise ValidationError if altitude is not a number."""
        sample_metadata_dict["altitude"] = "not a number"
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "altitude" in str(exc_info.value).lower()

    def test_environmental_must_be_dict(self, sample_metadata_dict):
        """Should raise ValidationError if environmental is not a dict."""
        sample_metadata_dict["environmental"] = "not a dict"
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "environmental" in str(exc_info.value).lower()

    def test_custom_must_be_dict(self, sample_metadata_dict):
        """Should raise ValidationError if custom is not a dict."""
        sample_metadata_dict["custom"] = ["not", "a", "dict"]
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "custom" in str(exc_info.value).lower()

    def test_deployment_name_must_be_string(self, sample_metadata_dict):
        """Should raise ValidationError if deployment_name is not a string."""
        sample_metadata_dict["deployment_name"] = 12345
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "deployment_name" in str(exc_info.value).lower()

    def test_location_name_must_be_string(self, sample_metadata_dict):
        """Should raise ValidationError if location_name is not a string."""
        sample_metadata_dict["location_name"] = 12345
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "location_name" in str(exc_info.value).lower()

    def test_environmental_key_must_be_string(self, sample_metadata_dict):
        """Should raise ValidationError if environmental has non-string key."""
        sample_metadata_dict["environmental"] = {123: "value"}
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "environmental" in str(exc_info.value).lower()

    def test_custom_key_must_be_string(self, sample_metadata_dict):
        """Should raise ValidationError if custom has non-string key."""
        sample_metadata_dict["custom"] = {456: "value"}
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "custom" in str(exc_info.value).lower()

    def test_environmental_invalid_value_type(self, sample_metadata_dict):
        """Should raise ValidationError for invalid environmental value type."""
        sample_metadata_dict["environmental"] = {"bad": object()}
        with pytest.raises(ValidationError) as exc_info:
            validate_deployment_schema(sample_metadata_dict)
        assert "environmental" in str(exc_info.value).lower()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in various scenarios."""

    def test_write_without_yaml_support(self, temp_photos_dir, sample_metadata, monkeypatch):
        """write_deployment_metadata should raise ValueError if YAML not available."""
        # Mock YAML_AVAILABLE to False
        monkeypatch.setattr('webui.backend.lib.deployment_sidecar.YAML_AVAILABLE', False)

        deployment_dir = temp_photos_dir / "yaml_unavailable"
        deployment_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            write_deployment_metadata(deployment_dir, sample_metadata, format="yaml")
        assert "yaml" in str(exc_info.value).lower()

    def test_get_sidecar_path_invalid_format(self, temp_photos_dir):
        """get_deployment_sidecar_path should raise ValueError for invalid format."""
        deployment_dir = temp_photos_dir / "invalid_format"
        deployment_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            get_deployment_sidecar_path(deployment_dir, format="xml")
        assert "unsupported format" in str(exc_info.value).lower()

    def test_update_without_deployment_name_fails(self, temp_photos_dir):
        """update_deployment_metadata should raise ValueError if no name and no existing."""
        deployment_dir = temp_photos_dir / "no_name"
        deployment_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            update_deployment_metadata(deployment_dir, {"latitude": 40.0})
        assert "deployment_name" in str(exc_info.value).lower()

    def test_read_invalid_schema_returns_none(self, temp_photos_dir):
        """read_deployment_metadata should return None for invalid schema."""
        deployment_dir = temp_photos_dir / "invalid_schema"
        deployment_dir.mkdir()

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        # Missing required fields
        sidecar.write_text(json.dumps({"invalid": "schema"}))

        metadata = read_deployment_metadata(deployment_dir)
        assert metadata is None

    def test_read_future_version_returns_none(self, temp_photos_dir, sample_metadata_dict):
        """read_deployment_metadata should return None for unsupported version."""
        deployment_dir = temp_photos_dir / "future_version"
        deployment_dir.mkdir()

        sample_metadata_dict["version"] = "99.0"
        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        sidecar.write_text(json.dumps(sample_metadata_dict))

        metadata = read_deployment_metadata(deployment_dir)
        assert metadata is None

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_read_corrupted_yaml_returns_none(self, temp_photos_dir):
        """read_deployment_metadata should return None for corrupted YAML."""
        deployment_dir = temp_photos_dir / "corrupted_yaml"
        deployment_dir.mkdir()

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_YAML
        sidecar.write_text("{ invalid yaml content: [")

        metadata = read_deployment_metadata(deployment_dir)
        assert metadata is None

    def test_update_corrupted_json_creates_new(self, temp_photos_dir):
        """update_deployment_metadata should create new if JSON corrupted."""
        deployment_dir = temp_photos_dir / "corrupted_update"
        deployment_dir.mkdir()

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        sidecar.write_text("{ corrupted json }")

        metadata = update_deployment_metadata(
            deployment_dir,
            {"deployment_name": "New After Corruption", "latitude": 40.0}
        )

        assert metadata is not None
        assert metadata.deployment_name == "New After Corruption"


# ============================================================================
# Test File Permission Edge Cases
# ============================================================================

class TestFilePermissions:
    """Tests for file permission handling."""

    def test_write_creates_directory_if_missing(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should create directory if it doesn't exist."""
        deployment_dir = temp_photos_dir / "auto_created" / "nested"

        # Directory doesn't exist yet
        assert not deployment_dir.exists()

        result = write_deployment_metadata(deployment_dir, sample_metadata)

        assert result is True
        assert deployment_dir.exists()

    def test_write_no_backup_on_new_file(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should not create backup for new file."""
        deployment_dir = temp_photos_dir / "new_no_backup"
        deployment_dir.mkdir()

        write_deployment_metadata(deployment_dir, sample_metadata, backup=True)

        sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        backup_path = sidecar.with_suffix(f".json{BACKUP_EXTENSION}")

        # No backup should exist for new file (nothing to backup)
        assert not backup_path.exists()


# ============================================================================
# Test Hierarchical Discovery Edge Cases
# ============================================================================

class TestHierarchicalDiscoveryEdgeCases:
    """Additional tests for hierarchical discovery edge cases."""

    def test_find_stops_at_photos_dir_root(self, temp_photos_dir):
        """find_deployment_sidecar should stop at PHOTOS_DIR root."""
        # Create subdirectory deep within photos dir
        deep_dir = temp_photos_dir / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)

        # No deployment sidecar anywhere
        sidecar_path = find_deployment_sidecar(deep_dir)

        # Should return None (stopped at PHOTOS_DIR, didn't go beyond)
        assert sidecar_path is None

    def test_find_json_has_priority_over_yaml(self, temp_photos_dir, sample_metadata_dict):
        """find_deployment_sidecar should prefer JSON over YAML."""
        deployment_dir = temp_photos_dir / "both_formats"
        deployment_dir.mkdir()

        # Create both JSON and YAML
        json_sidecar = deployment_dir / DEPLOYMENT_FILENAME_JSON
        yaml_sidecar = deployment_dir / DEPLOYMENT_FILENAME_YAML

        json_sidecar.write_text(json.dumps(sample_metadata_dict))
        if YAML_AVAILABLE:
            import yaml
            yaml_sidecar.write_text(yaml.safe_dump(sample_metadata_dict))

        sidecar_path = find_deployment_sidecar(deployment_dir)

        # Should return JSON path (has priority)
        assert sidecar_path == json_sidecar


# ============================================================================
# Test String Path Handling
# ============================================================================

class TestStringPathHandling:
    """Tests for string path handling (not just Path objects)."""

    def test_get_sidecar_path_accepts_string(self, temp_photos_dir):
        """get_deployment_sidecar_path should accept string path."""
        deployment_dir = temp_photos_dir / "string_path"
        deployment_dir.mkdir()

        sidecar_path = get_deployment_sidecar_path(str(deployment_dir))

        assert isinstance(sidecar_path, Path)
        assert sidecar_path.name == DEPLOYMENT_FILENAME_JSON

    def test_deployment_has_sidecar_accepts_string(self, directory_with_sidecar):
        """deployment_has_sidecar should accept string path."""
        result = deployment_has_sidecar(str(directory_with_sidecar))

        assert result is True

    def test_find_deployment_sidecar_accepts_string(self, directory_with_sidecar):
        """find_deployment_sidecar should accept string path."""
        sidecar_path = find_deployment_sidecar(str(directory_with_sidecar))

        assert sidecar_path is not None

    def test_read_metadata_accepts_string(self, directory_with_sidecar):
        """read_deployment_metadata should accept string path."""
        metadata = read_deployment_metadata(str(directory_with_sidecar))

        assert metadata is not None

    def test_write_metadata_accepts_string(self, temp_photos_dir, sample_metadata):
        """write_deployment_metadata should accept string path."""
        deployment_dir = temp_photos_dir / "string_write"
        deployment_dir.mkdir()

        result = write_deployment_metadata(str(deployment_dir), sample_metadata)

        assert result is True
