"""
Unit tests for sidecar metadata library (Issue #102 - Phase 4)

Tests JSON sidecar metadata system for storing photo-level metadata.
TDD approach: tests written first, then implementation.

Coverage Target: 85%+

Design Decisions:
- File naming: {photo}.json (e.g., photo.jpg.json)
- Tags: lowercase normalized to prevent duplicates
- Schema version: Return None for unsupported versions (fail safe)
- Cache: Two-level (L1 memory + L2 file) - tested in service tests
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
# Expected Interface (TDD - define before implementation)
# ============================================================================

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.lib.sidecar_metadata import (
        # Data classes
        SidecarMetadata,
        # Constants
        SCHEMA_VERSION,
        BACKUP_EXTENSION,
        # Path utilities
        get_sidecar_path,
        photo_has_sidecar,
        list_photos_with_sidecars,
        # Schema validation
        validate_schema,
        ValidationError,
        # CRUD operations
        read_metadata,
        write_metadata,
        create_metadata,
        update_metadata,
        delete_metadata,
        # Tag operations
        add_tag,
        remove_tag,
        normalize_tag,
        # File locking
        FileLock,
        LockTimeoutError,
        # Cleanup utilities
        cleanup_temp_files,
        # Constants for testing
        MAX_CUSTOM_DEPTH,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    # Define stubs for test discovery
    SidecarMetadata = None
    SCHEMA_VERSION = None
    BACKUP_EXTENSION = None
    get_sidecar_path = None
    photo_has_sidecar = None
    list_photos_with_sidecars = None
    validate_schema = None
    ValidationError = None
    read_metadata = None
    write_metadata = None
    create_metadata = None
    update_metadata = None
    delete_metadata = None
    add_tag = None
    remove_tag = None
    normalize_tag = None
    FileLock = None
    LockTimeoutError = None
    cleanup_temp_files = None
    MAX_CUSTOM_DEPTH = 5


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_photo(tmp_path):
    """Create a sample photo file for testing."""
    photo = tmp_path / "test_photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Minimal JPEG header
    return photo


@pytest.fixture
def sample_photos(tmp_path):
    """Create multiple sample photos for batch testing."""
    photos = []
    for i in range(10):
        photo = tmp_path / f"photo_{i:03d}.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        photos.append(photo)
    return photos


@pytest.fixture
def sample_metadata():
    """Create sample metadata dictionary."""
    return {
        "version": "1.0",
        "photo_filename": "test_photo.jpg",
        "created_at": "2024-11-06T10:30:00Z",
        "modified_at": "2024-11-06T10:30:00Z",
        "modified_by": None,
        "tags": ["moth", "night"],
        "species": "Actias luna",
        "notes": "Large specimen near UV light",
        "custom": {"weather": "clear", "temperature": 18.5}
    }


@pytest.fixture
def photo_with_sidecar(tmp_path, sample_metadata):
    """Create a photo with existing sidecar file."""
    photo = tmp_path / "test_photo.jpg"
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

    sidecar = tmp_path / "test_photo.jpg.json"
    sidecar.write_text(json.dumps(sample_metadata, indent=2))

    return photo


# ============================================================================
# Test SidecarMetadata Data Class
# ============================================================================

class TestSidecarMetadataDataClass:
    """Tests for SidecarMetadata data class structure."""

    def test_sidecar_metadata_has_required_fields(self):
        """SidecarMetadata should have all required fields."""
        metadata = SidecarMetadata(
            version="1.0",
            photo_filename="test.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
            tags=["moth"],
            species="Luna moth",
            notes="Test notes",
            custom={"key": "value"},
            modified_by=None
        )
        assert metadata.version == "1.0"
        assert metadata.photo_filename == "test.jpg"
        assert metadata.created_at == "2024-11-06T10:30:00Z"
        assert metadata.modified_at == "2024-11-06T10:30:00Z"
        assert metadata.tags == ["moth"]
        assert metadata.species == "Luna moth"
        assert metadata.notes == "Test notes"
        assert metadata.custom == {"key": "value"}
        assert metadata.modified_by is None

    def test_sidecar_metadata_to_dict(self):
        """SidecarMetadata.to_dict() should return valid dictionary."""
        metadata = SidecarMetadata(
            version="1.0",
            photo_filename="test.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
            tags=["moth"],
            species=None,
            notes=None,
            custom={},
            modified_by=None
        )
        d = metadata.to_dict()

        assert isinstance(d, dict)
        assert d["version"] == "1.0"
        assert d["photo_filename"] == "test.jpg"
        assert d["tags"] == ["moth"]
        assert "created_at" in d
        assert "modified_at" in d

    def test_sidecar_metadata_from_dict(self, sample_metadata):
        """SidecarMetadata.from_dict() should create instance from dictionary."""
        metadata = SidecarMetadata.from_dict(sample_metadata)

        assert metadata.version == "1.0"
        assert metadata.photo_filename == "test_photo.jpg"
        assert metadata.tags == ["moth", "night"]
        assert metadata.species == "Actias luna"

    def test_sidecar_metadata_roundtrip(self):
        """to_dict() then from_dict() should preserve all data."""
        original = SidecarMetadata(
            version="1.0",
            photo_filename="test.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T11:45:00Z",
            tags=["moth", "night", "luna"],
            species="Actias luna",
            notes="Some notes here",
            custom={"weather": "clear", "temp": 20},
            modified_by="user123"
        )

        d = original.to_dict()
        restored = SidecarMetadata.from_dict(d)

        assert restored.version == original.version
        assert restored.photo_filename == original.photo_filename
        assert restored.tags == original.tags
        assert restored.species == original.species
        assert restored.notes == original.notes
        assert restored.custom == original.custom
        assert restored.modified_by == original.modified_by


# ============================================================================
# Test Schema Version Constant
# ============================================================================

class TestSchemaVersion:
    """Tests for schema version constant."""

    def test_schema_version_is_string(self):
        """SCHEMA_VERSION should be a string."""
        assert isinstance(SCHEMA_VERSION, str)

    def test_schema_version_is_1_1(self):
        """SCHEMA_VERSION should be '1.1' for current release (Issue #109)."""
        assert SCHEMA_VERSION == "1.1"

    def test_backup_extension_constant(self):
        """BACKUP_EXTENSION should be '.bak'."""
        assert BACKUP_EXTENSION == ".bak"


# ============================================================================
# Test Schema v1.1 New Fields (Issue #109 - TDD)
# ============================================================================

class TestSchemaV11NewFields:
    """Tests for new fields in schema version 1.1 (Issue #109)."""

    def test_schema_accepts_species_confidence(self, sample_photo):
        """Schema should accept species_confidence field with valid enum values."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species": "Actias luna",
            "species_confidence": "certain"
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_schema_accepts_common_name(self, sample_photo):
        """Schema should accept species_common_name field."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species_common_name": "Luna Moth"
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_schema_accepts_reference_url(self, sample_photo):
        """Schema should accept species_reference_url field with valid URL."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species_reference_url": "https://inaturalist.org/taxa/47921"
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_schema_rejects_invalid_confidence(self, sample_photo):
        """Schema should reject species_confidence with invalid enum value."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species_confidence": "maybe"  # Invalid - not in enum
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(metadata_dict)
        assert "species_confidence" in str(exc_info.value).lower()

    def test_schema_rejects_invalid_reference_url(self, sample_photo):
        """Schema should reject species_reference_url with non-http URL."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species_reference_url": "ftp://example.com"  # Invalid - not http/https
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(metadata_dict)
        assert "reference_url" in str(exc_info.value).lower()

    def test_confidence_enum_values(self, sample_photo):
        """All valid species_confidence enum values should be accepted."""
        valid_values = ["certain", "probable", "possible", "unknown"]

        for confidence in valid_values:
            metadata_dict = {
                "version": "1.1",
                "photo_filename": "test.jpg",
                "created_at": "2024-11-06T10:30:00Z",
                "modified_at": "2024-11-06T10:30:00Z",
                "tags": [],
                "custom": {},
                "species_confidence": confidence
            }
            # Should not raise ValidationError for any valid enum value
            assert validate_schema(metadata_dict) is True

    def test_schema_version_1_1(self, sample_photo):
        """Schema should accept version field with '1.1'."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {}
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_all_v11_fields_together(self, sample_photo):
        """Schema should accept all v1.1 fields together."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": ["moth"],
            "species": "Actias luna",
            "species_confidence": "certain",
            "species_common_name": "Luna Moth",
            "species_reference_url": "https://inaturalist.org/taxa/47921",
            "custom": {"location": "backyard"}
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_v11_fields_are_optional(self, sample_photo):
        """New v1.1 fields should be optional."""
        # Minimal v1.1 metadata without new fields
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {}
        }
        # Should not raise ValidationError
        assert validate_schema(metadata_dict) is True

    def test_common_name_max_length(self, sample_photo):
        """species_common_name should respect max length constraint."""
        metadata_dict = {
            "version": "1.1",
            "photo_filename": "test.jpg",
            "created_at": "2024-11-06T10:30:00Z",
            "modified_at": "2024-11-06T10:30:00Z",
            "tags": [],
            "custom": {},
            "species_common_name": "a" * 201  # Exceeds 200 char limit
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(metadata_dict)
        assert "common_name" in str(exc_info.value).lower()


# ============================================================================
# Test Path Utilities
# ============================================================================

class TestGetSidecarPath:
    """Tests for get_sidecar_path() function."""

    def test_get_sidecar_path_basic(self, sample_photo):
        """get_sidecar_path should return {photo}.json path."""
        sidecar_path = get_sidecar_path(sample_photo)
        assert sidecar_path == sample_photo.parent / "test_photo.jpg.json"

    def test_get_sidecar_path_preserves_directory(self, tmp_path):
        """Sidecar should be in same directory as photo."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        photo = subdir / "photo.jpg"

        sidecar_path = get_sidecar_path(photo)
        assert sidecar_path.parent == subdir

    def test_get_sidecar_path_handles_string(self, tmp_path):
        """get_sidecar_path should accept string paths."""
        photo_str = str(tmp_path / "photo.jpg")
        sidecar_path = get_sidecar_path(photo_str)
        assert sidecar_path.name == "photo.jpg.json"

    def test_get_sidecar_path_different_extensions(self, tmp_path):
        """get_sidecar_path should work with various image extensions."""
        test_cases = [
            ("photo.jpg", "photo.jpg.json"),
            ("photo.JPG", "photo.JPG.json"),
            ("photo.jpeg", "photo.jpeg.json"),
            ("photo.png", "photo.png.json"),
        ]
        for photo_name, expected_name in test_cases:
            photo = tmp_path / photo_name
            sidecar = get_sidecar_path(photo)
            assert sidecar.name == expected_name


class TestPhotoHasSidecar:
    """Tests for photo_has_sidecar() function."""

    def test_photo_has_sidecar_true(self, photo_with_sidecar):
        """Should return True when sidecar exists."""
        assert photo_has_sidecar(photo_with_sidecar) is True

    def test_photo_has_sidecar_false(self, sample_photo):
        """Should return False when sidecar doesn't exist."""
        assert photo_has_sidecar(sample_photo) is False

    def test_photo_has_sidecar_handles_string(self, photo_with_sidecar):
        """Should accept string paths."""
        assert photo_has_sidecar(str(photo_with_sidecar)) is True


class TestListPhotosWithSidecars:
    """Tests for list_photos_with_sidecars() function."""

    def test_list_photos_empty_directory(self, tmp_path):
        """Should return empty list for empty directory."""
        result = list_photos_with_sidecars(tmp_path)
        assert result == []

    def test_list_photos_with_some_sidecars(self, tmp_path, sample_metadata):
        """Should return only photos that have sidecars."""
        # Create 3 photos, only 2 with sidecars
        for i in range(3):
            photo = tmp_path / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

            if i < 2:  # Only first 2 get sidecars
                sidecar = tmp_path / f"photo_{i}.jpg.json"
                sidecar.write_text(json.dumps(sample_metadata))

        result = list_photos_with_sidecars(tmp_path)
        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)


# ============================================================================
# Test Schema Validation
# ============================================================================

class TestValidateSchema:
    """Tests for validate_schema() function."""

    def test_validate_valid_metadata(self, sample_metadata):
        """Should return True for valid metadata."""
        assert validate_schema(sample_metadata) is True

    def test_validate_missing_version(self, sample_metadata):
        """Should raise ValidationError for missing version."""
        del sample_metadata["version"]
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "version" in str(exc_info.value).lower()

    def test_validate_missing_photo_filename(self, sample_metadata):
        """Should raise ValidationError for missing photo_filename."""
        del sample_metadata["photo_filename"]
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "photo_filename" in str(exc_info.value).lower()

    def test_validate_unsupported_version(self, sample_metadata):
        """Should raise ValidationError for unsupported schema version."""
        sample_metadata["version"] = "99.0"  # Future version
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "version" in str(exc_info.value).lower()

    def test_validate_tags_must_be_list(self, sample_metadata):
        """Tags must be a list, not a string."""
        sample_metadata["tags"] = "not a list"
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "tags" in str(exc_info.value).lower()

    def test_validate_tag_length_limit(self, sample_metadata):
        """Tags should be max 50 characters."""
        sample_metadata["tags"] = ["a" * 51]  # 51 chars
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "tag" in str(exc_info.value).lower()

    def test_validate_species_length_limit(self, sample_metadata):
        """Species should be max 200 characters."""
        sample_metadata["species"] = "a" * 201
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "species" in str(exc_info.value).lower()

    def test_validate_notes_length_limit(self, sample_metadata):
        """Notes should be max 10000 characters."""
        sample_metadata["notes"] = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "notes" in str(exc_info.value).lower()

    def test_validate_custom_must_be_dict(self, sample_metadata):
        """Custom field must be a dictionary."""
        sample_metadata["custom"] = ["not", "a", "dict"]
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "custom" in str(exc_info.value).lower()

    def test_validate_custom_max_keys(self, sample_metadata):
        """Custom field should have max 100 keys."""
        sample_metadata["custom"] = {f"key_{i}": i for i in range(101)}
        with pytest.raises(ValidationError) as exc_info:
            validate_schema(sample_metadata)
        assert "custom" in str(exc_info.value).lower()


# ============================================================================
# Test Tag Normalization
# ============================================================================

class TestTagNormalization:
    """Tests for tag normalization (lowercase)."""

    def test_normalize_tag_lowercase(self):
        """normalize_tag should convert to lowercase."""
        assert normalize_tag("Moth") == "moth"
        assert normalize_tag("LUNA_MOTH") == "luna_moth"
        assert normalize_tag("Night") == "night"

    def test_normalize_tag_strips_whitespace(self):
        """normalize_tag should strip leading/trailing whitespace."""
        assert normalize_tag("  moth  ") == "moth"
        assert normalize_tag("\tmoth\n") == "moth"

    def test_normalize_tag_already_lowercase(self):
        """normalize_tag should not modify already lowercase tags."""
        assert normalize_tag("moth") == "moth"

    def test_normalize_tag_preserves_underscores(self):
        """normalize_tag should preserve underscores and hyphens."""
        assert normalize_tag("Luna_Moth") == "luna_moth"
        assert normalize_tag("Large-Moth") == "large-moth"


# ============================================================================
# Test Read Operations
# ============================================================================

class TestReadMetadata:
    """Tests for read_metadata() function."""

    def test_read_metadata_existing_sidecar(self, photo_with_sidecar):
        """Should read metadata from existing sidecar."""
        metadata = read_metadata(photo_with_sidecar)

        assert metadata is not None
        assert isinstance(metadata, SidecarMetadata)
        assert metadata.version == "1.0"
        assert metadata.tags == ["moth", "night"]

    def test_read_metadata_no_sidecar(self, sample_photo):
        """Should return None when no sidecar exists."""
        result = read_metadata(sample_photo)
        assert result is None

    def test_read_metadata_corrupted_json(self, sample_photo):
        """Should return None for corrupted JSON (graceful degradation)."""
        sidecar = get_sidecar_path(sample_photo)
        sidecar.write_text("{ invalid json }")

        result = read_metadata(sample_photo)
        assert result is None

    def test_read_metadata_invalid_schema(self, sample_photo):
        """Should return None for invalid schema."""
        sidecar = get_sidecar_path(sample_photo)
        sidecar.write_text('{"invalid": "schema"}')

        result = read_metadata(sample_photo)
        assert result is None

    def test_read_metadata_future_version(self, sample_photo, sample_metadata):
        """Should return None for unsupported future version (fail safe)."""
        sample_metadata["version"] = "99.0"
        sidecar = get_sidecar_path(sample_photo)
        sidecar.write_text(json.dumps(sample_metadata))

        result = read_metadata(sample_photo)
        assert result is None


# ============================================================================
# Test Write Operations
# ============================================================================

class TestWriteMetadata:
    """Tests for write_metadata() function."""

    def test_write_metadata_creates_sidecar(self, sample_photo):
        """write_metadata should create sidecar file."""
        metadata = SidecarMetadata(
            version="1.0",
            photo_filename="test_photo.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T10:30:00Z",
            tags=["moth"],
            species=None,
            notes=None,
            custom={},
            modified_by=None
        )

        result = write_metadata(sample_photo, metadata)

        assert result is True
        sidecar = get_sidecar_path(sample_photo)
        assert sidecar.exists()

        # Verify contents
        with open(sidecar) as f:
            data = json.load(f)
        assert data["tags"] == ["moth"]

    def test_write_metadata_creates_backup(self, photo_with_sidecar):
        """write_metadata should create .bak backup by default."""
        original_content = get_sidecar_path(photo_with_sidecar).read_text()

        new_metadata = SidecarMetadata(
            version="1.0",
            photo_filename="test_photo.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T12:00:00Z",
            tags=["updated"],
            species=None,
            notes=None,
            custom={},
            modified_by=None
        )

        write_metadata(photo_with_sidecar, new_metadata, backup=True)

        # Check backup exists
        backup_path = get_sidecar_path(photo_with_sidecar).with_suffix(".json.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

    def test_write_metadata_no_backup(self, photo_with_sidecar):
        """write_metadata should skip backup when backup=False."""
        new_metadata = SidecarMetadata(
            version="1.0",
            photo_filename="test_photo.jpg",
            created_at="2024-11-06T10:30:00Z",
            modified_at="2024-11-06T12:00:00Z",
            tags=["updated"],
            species=None,
            notes=None,
            custom={},
            modified_by=None
        )

        write_metadata(photo_with_sidecar, new_metadata, backup=False)

        backup_path = get_sidecar_path(photo_with_sidecar).with_suffix(".json.bak")
        assert not backup_path.exists()


# ============================================================================
# Test Create Metadata
# ============================================================================

class TestCreateMetadata:
    """Tests for create_metadata() function."""

    def test_create_metadata_minimal(self, sample_photo):
        """create_metadata should create with minimal required fields."""
        metadata = create_metadata(sample_photo)

        assert metadata.version == SCHEMA_VERSION
        assert metadata.photo_filename == sample_photo.name
        assert metadata.tags == []
        assert metadata.species is None
        assert metadata.notes is None
        assert metadata.custom == {}

    def test_create_metadata_with_tags(self, sample_photo):
        """create_metadata should accept tags parameter."""
        metadata = create_metadata(sample_photo, tags=["moth", "Night"])

        # Tags should be normalized to lowercase
        assert metadata.tags == ["moth", "night"]

    def test_create_metadata_with_species(self, sample_photo):
        """create_metadata should accept species parameter."""
        metadata = create_metadata(sample_photo, species="Actias luna")
        assert metadata.species == "Actias luna"

    def test_create_metadata_sets_timestamps(self, sample_photo):
        """create_metadata should set created_at and modified_at."""
        before = datetime.now(timezone.utc)
        metadata = create_metadata(sample_photo)
        after = datetime.now(timezone.utc)

        # Parse timestamps and verify they're within expected range
        created = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
        modified = datetime.fromisoformat(metadata.modified_at.replace('Z', '+00:00'))

        assert before <= created <= after
        assert created == modified  # Should be same on creation


# ============================================================================
# Test Update Operations
# ============================================================================

class TestUpdateMetadata:
    """Tests for update_metadata() function."""

    def test_update_metadata_adds_field(self, photo_with_sidecar):
        """update_metadata should add new field values."""
        result = update_metadata(photo_with_sidecar, {"notes": "New note"})

        assert result is not None
        assert result.notes == "New note"
        # Original fields preserved
        assert result.tags == ["moth", "night"]

    def test_update_metadata_modifies_field(self, photo_with_sidecar):
        """update_metadata should modify existing fields."""
        result = update_metadata(photo_with_sidecar, {"species": "Different species"})

        assert result.species == "Different species"

    def test_update_metadata_normalizes_tags(self, photo_with_sidecar):
        """update_metadata should normalize tags to lowercase."""
        result = update_metadata(photo_with_sidecar, {"tags": ["MOTH", "Luna"]})

        assert result.tags == ["moth", "luna"]

    def test_update_metadata_updates_modified_at(self, photo_with_sidecar):
        """update_metadata should update modified_at timestamp."""
        original = read_metadata(photo_with_sidecar)

        import time
        time.sleep(0.01)  # Ensure different timestamp

        result = update_metadata(photo_with_sidecar, {"notes": "Updated"})

        assert result.modified_at != original.modified_at

    def test_update_metadata_no_sidecar_creates_new(self, sample_photo):
        """update_metadata on photo without sidecar should create new."""
        result = update_metadata(sample_photo, {"tags": ["moth"]})

        assert result is not None
        assert result.tags == ["moth"]
        assert photo_has_sidecar(sample_photo)


# ============================================================================
# Test Delete Operations
# ============================================================================

class TestDeleteMetadata:
    """Tests for delete_metadata() function."""

    def test_delete_metadata_removes_sidecar(self, photo_with_sidecar):
        """delete_metadata should remove sidecar file."""
        assert photo_has_sidecar(photo_with_sidecar)

        result = delete_metadata(photo_with_sidecar)

        assert result is True
        assert not photo_has_sidecar(photo_with_sidecar)

    def test_delete_metadata_creates_backup(self, photo_with_sidecar):
        """delete_metadata should create backup by default."""
        sidecar = get_sidecar_path(photo_with_sidecar)
        original_content = sidecar.read_text()

        delete_metadata(photo_with_sidecar, backup=True)

        backup_path = sidecar.with_suffix(".json.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

    def test_delete_metadata_no_backup(self, photo_with_sidecar):
        """delete_metadata should skip backup when backup=False."""
        delete_metadata(photo_with_sidecar, backup=False)

        backup_path = get_sidecar_path(photo_with_sidecar).with_suffix(".json.bak")
        assert not backup_path.exists()

    def test_delete_metadata_nonexistent(self, sample_photo):
        """delete_metadata should return False for nonexistent sidecar."""
        result = delete_metadata(sample_photo)
        assert result is False


# ============================================================================
# Test Tag Operations
# ============================================================================

class TestAddTag:
    """Tests for add_tag() function."""

    def test_add_tag_to_existing(self, photo_with_sidecar):
        """add_tag should add tag to existing metadata."""
        result = add_tag(photo_with_sidecar, "new_tag")

        assert "new_tag" in result.tags
        assert "moth" in result.tags  # Original preserved
        assert "night" in result.tags

    def test_add_tag_normalizes(self, photo_with_sidecar):
        """add_tag should normalize tag to lowercase."""
        result = add_tag(photo_with_sidecar, "NEW_TAG")

        assert "new_tag" in result.tags
        assert "NEW_TAG" not in result.tags

    def test_add_tag_no_duplicates(self, photo_with_sidecar):
        """add_tag should not add duplicate tags."""
        result = add_tag(photo_with_sidecar, "moth")  # Already exists

        assert result.tags.count("moth") == 1

    def test_add_tag_creates_sidecar(self, sample_photo):
        """add_tag on photo without sidecar should create new."""
        result = add_tag(sample_photo, "new_tag")

        assert result is not None
        assert "new_tag" in result.tags
        assert photo_has_sidecar(sample_photo)


class TestRemoveTag:
    """Tests for remove_tag() function."""

    def test_remove_tag_existing(self, photo_with_sidecar):
        """remove_tag should remove existing tag."""
        result = remove_tag(photo_with_sidecar, "moth")

        assert "moth" not in result.tags
        assert "night" in result.tags  # Other tags preserved

    def test_remove_tag_normalizes(self, photo_with_sidecar):
        """remove_tag should normalize tag before removal."""
        result = remove_tag(photo_with_sidecar, "MOTH")

        assert "moth" not in result.tags

    def test_remove_tag_nonexistent(self, photo_with_sidecar):
        """remove_tag should handle nonexistent tag gracefully."""
        result = remove_tag(photo_with_sidecar, "nonexistent")

        assert result is not None
        assert result.tags == ["moth", "night"]  # Unchanged


# ============================================================================
# Test File Locking
# ============================================================================

class TestFileLock:
    """Tests for FileLock context manager."""

    def test_file_lock_exclusive(self, sample_photo):
        """FileLock should acquire exclusive lock for writing."""
        sidecar = get_sidecar_path(sample_photo)
        sidecar.write_text("{}")

        with FileLock(sidecar, exclusive=True) as f:
            assert f is not None
            # File should be locked for writing

    def test_file_lock_shared(self, photo_with_sidecar):
        """FileLock should acquire shared lock for reading."""
        sidecar = get_sidecar_path(photo_with_sidecar)

        with FileLock(sidecar, exclusive=False) as f:
            assert f is not None
            content = f.read()
            assert "version" in content

    def test_file_lock_timeout(self, sample_photo):
        """FileLock should timeout and raise LockTimeoutError."""
        # This test needs careful setup - we'd need to hold a lock
        # in another process/thread. For now, test the exception exists.
        assert LockTimeoutError is not None
        assert issubclass(LockTimeoutError, Exception)


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_tags_list(self, sample_photo):
        """Should handle empty tags list."""
        metadata = create_metadata(sample_photo, tags=[])
        assert metadata.tags == []

    def test_none_optional_fields(self, sample_photo):
        """Should handle None for optional fields."""
        metadata = create_metadata(
            sample_photo,
            species=None,
            notes=None
        )
        assert metadata.species is None
        assert metadata.notes is None

    def test_unicode_in_tags(self, sample_photo):
        """Should handle Unicode characters in tags."""
        metadata = create_metadata(sample_photo, tags=["papillon", "nacht"])
        assert "papillon" in metadata.tags
        assert "nacht" in metadata.tags

    def test_unicode_in_notes(self, sample_photo):
        """Should handle Unicode characters in notes."""
        metadata = create_metadata(sample_photo, notes="Beautiful specimen")
        assert metadata.notes == "Beautiful specimen"

    def test_special_characters_in_filename(self, tmp_path):
        """Should handle special characters in photo filename."""
        photo = tmp_path / "photo_with-special.chars_123.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        metadata = create_metadata(photo)
        assert metadata.photo_filename == photo.name

    def test_very_deep_nested_path(self, tmp_path):
        """Should handle deeply nested paths."""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        photo = deep_path / "photo.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        sidecar_path = get_sidecar_path(photo)
        assert sidecar_path.parent == deep_path


# ============================================================================
# Performance Baseline Tests
# ============================================================================

class TestPerformanceBaseline:
    """Basic performance tests (detailed tests in test_sidecar_performance.py)."""

    def test_read_metadata_under_10ms(self, photo_with_sidecar):
        """Single read should complete in under 10ms."""
        import time

        start = time.perf_counter()
        read_metadata(photo_with_sidecar)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 50  # Allow 50ms for CI variability, target is 10ms

    def test_write_metadata_under_50ms(self, sample_photo):
        """Single write should complete in under 50ms."""
        import time

        metadata = create_metadata(sample_photo, tags=["test"])

        start = time.perf_counter()
        write_metadata(sample_photo, metadata)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100  # Allow 100ms for CI variability, target is 50ms


# ============================================================================
# Path Traversal Protection Tests (Issue #102 Bug Fix)
# ============================================================================

class TestPathTraversalProtection:
    """Tests for path traversal protection in get_sidecar_path."""

    def test_path_is_resolved(self, tmp_path):
        """get_sidecar_path should resolve paths to absolute."""
        photo_path = tmp_path / "photo.jpg"
        sidecar_path = get_sidecar_path(photo_path)

        # Should be absolute path
        assert sidecar_path.is_absolute()

    def test_relative_path_resolved_to_cwd(self):
        """Relative paths should be resolved against current working directory."""
        sidecar_path = get_sidecar_path("photo.jpg")

        # Should be absolute (resolved)
        assert sidecar_path.is_absolute()
        assert sidecar_path.name == "photo.jpg.json"

    def test_path_traversal_normalized(self, tmp_path):
        """Path with .. should be normalized."""
        # Create path with traversal sequence
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Path that goes up and back down
        traversal_path = subdir / ".." / "photo.jpg"
        sidecar_path = get_sidecar_path(traversal_path)

        # Should normalize to tmp_path/photo.jpg.json, not subdir/../photo.jpg.json
        assert ".." not in str(sidecar_path)
        assert sidecar_path.is_absolute()


# ============================================================================
# Custom Value Validation Tests (Issue #102 Bug Fix)
# ============================================================================

class TestCustomValueValidation:
    """Tests for custom value type validation in validate_schema."""

    def test_valid_simple_custom_values(self, tmp_path):
        """Valid simple types in custom should pass."""
        valid_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "tags": [],
            "custom": {
                "string_val": "hello",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "none_val": None,
            }
        }

        # Should not raise
        assert validate_schema(valid_data) is True

    def test_valid_nested_custom_values(self, tmp_path):
        """Valid nested structures in custom should pass."""
        valid_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "tags": [],
            "custom": {
                "nested_dict": {"key": "value", "num": 123},
                "nested_list": [1, 2, "three", True],
                "mixed": {"list": [1, 2, 3], "dict": {"a": "b"}}
            }
        }

        # Should not raise
        assert validate_schema(valid_data) is True

    def test_invalid_custom_value_type_raises(self, tmp_path):
        """Invalid types in custom should raise ValidationError."""
        # Using a set (not JSON-serializable type)
        invalid_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "tags": [],
            "custom": {
                "bad_value": {1, 2, 3}  # set is not allowed
            }
        }

        with pytest.raises(ValidationError, match="custom value type not allowed"):
            validate_schema(invalid_data)

    def test_deeply_nested_custom_rejected(self, tmp_path):
        """Custom values nested deeper than MAX_CUSTOM_DEPTH should be rejected."""
        # Build deeply nested structure
        deep_nested = "value"
        for _ in range(MAX_CUSTOM_DEPTH + 2):  # Go beyond the limit
            deep_nested = {"level": deep_nested}

        invalid_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "tags": [],
            "custom": {
                "deep": deep_nested
            }
        }

        with pytest.raises(ValidationError, match="custom value type not allowed"):
            validate_schema(invalid_data)

    def test_non_string_custom_key_raises(self, tmp_path):
        """Non-string keys in custom should raise ValidationError."""
        # Note: In Python, dict keys can be ints, but JSON requires strings
        # This test checks our validation catches non-string keys
        invalid_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-01T00:00:00Z",
            "modified_at": "2024-01-01T00:00:00Z",
            "tags": [],
            "custom": {
                123: "value"  # int key not allowed
            }
        }

        with pytest.raises(ValidationError, match="custom key must be string"):
            validate_schema(invalid_data)


# ============================================================================
# Temp File Cleanup Tests (Issue #102 Bug Fix)
# ============================================================================

class TestTempFileCleanup:
    """Tests for cleanup_temp_files function."""

    def test_cleanup_removes_old_tmp_files(self, tmp_path):
        """cleanup_temp_files should remove .tmp files older than max_age."""
        import time

        # Create old temp file
        old_tmp = tmp_path / "old.json.tmp"
        old_tmp.write_text("{}")

        # Make it appear old by setting mtime to past
        import os
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(old_tmp, (old_time, old_time))

        # Clean up files older than 1 hour
        removed = cleanup_temp_files(tmp_path, max_age_seconds=3600)

        assert removed == 1
        assert not old_tmp.exists()

    def test_cleanup_keeps_recent_tmp_files(self, tmp_path):
        """cleanup_temp_files should keep recent .tmp files."""
        # Create recent temp file
        recent_tmp = tmp_path / "recent.json.tmp"
        recent_tmp.write_text("{}")

        # Clean up files older than 1 hour
        removed = cleanup_temp_files(tmp_path, max_age_seconds=3600)

        assert removed == 0
        assert recent_tmp.exists()

    def test_cleanup_ignores_non_tmp_files(self, tmp_path):
        """cleanup_temp_files should not remove non-.tmp files."""
        import time
        import os

        # Create old regular JSON file
        old_json = tmp_path / "old.json"
        old_json.write_text("{}")

        # Make it appear old
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(old_json, (old_time, old_time))

        # Clean up
        removed = cleanup_temp_files(tmp_path, max_age_seconds=3600)

        assert removed == 0
        assert old_json.exists()

    def test_cleanup_empty_directory(self, tmp_path):
        """cleanup_temp_files should handle empty directory."""
        removed = cleanup_temp_files(tmp_path)

        assert removed == 0

    def test_cleanup_nonexistent_directory(self, tmp_path):
        """cleanup_temp_files should handle non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"

        removed = cleanup_temp_files(nonexistent)

        assert removed == 0


# ============================================================================
# File Permission Tests (Issue #102 Bug Fix)
# ============================================================================

class TestFilePermissions:
    """Tests for file permission handling in write_metadata."""

    def test_sidecar_has_readable_permissions(self, sample_photo):
        """Written sidecar files should be readable by owner and group."""
        import stat

        metadata = create_metadata(sample_photo, tags=["test"])
        write_metadata(sample_photo, metadata)

        sidecar_path = get_sidecar_path(sample_photo)
        mode = sidecar_path.stat().st_mode

        # Should be readable by owner (at minimum)
        assert mode & stat.S_IRUSR

        # Should be readable by group (0o644 sets this)
        assert mode & stat.S_IRGRP
