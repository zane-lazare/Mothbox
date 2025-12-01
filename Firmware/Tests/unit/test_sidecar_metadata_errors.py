"""
Unit tests for sidecar_metadata.py error handling and edge cases.

Tests corrupted JSON, missing fields, type validation, backup recovery, and permission errors.

Run with: MOTHBOX_ENV=test pytest Tests/unit/test_sidecar_metadata_errors.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from webui.backend.lib.sidecar_metadata import (
    read_metadata,
    write_metadata,
    create_metadata,
    update_metadata,
    validate_schema,
    ValidationError,
    SCHEMA_VERSION,
)


class TestCorruptedJsonHandling:
    """Tests for graceful handling of corrupted JSON files."""

    def test_truncated_json_returns_none(self, tmp_path):
        """Truncated JSON file should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        # Write truncated JSON
        sidecar.write_text('{"version": "1.0", "photo_filename": "photo.jpg"')

        result = read_metadata(photo)
        assert result is None, "Truncated JSON should return None"

    def test_empty_file_returns_none(self, tmp_path):
        """Empty sidecar file should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        # Create empty file
        sidecar.write_text('')

        result = read_metadata(photo)
        assert result is None, "Empty file should return None"

    def test_binary_garbage_returns_none(self, tmp_path):
        """Binary garbage data should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        # Write binary garbage
        sidecar.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd\xfc')

        result = read_metadata(photo)
        assert result is None, "Binary garbage should return None"

    def test_partially_valid_json_returns_none(self, tmp_path):
        """Partially valid JSON (missing required fields) should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        # Valid JSON but incomplete schema
        partial_data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            # Missing created_at, modified_at, tags, custom
        }
        sidecar.write_text(json.dumps(partial_data))

        result = read_metadata(photo)
        assert result is None, "Incomplete schema should return None"

    def test_invalid_json_syntax_returns_none(self, tmp_path):
        """Invalid JSON syntax should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        # Invalid JSON (trailing comma)
        sidecar.write_text('{"version": "1.0", "tags": ["moth",],}')

        result = read_metadata(photo)
        assert result is None, "Invalid JSON syntax should return None"

    def test_null_json_returns_none(self, tmp_path):
        """JSON null value should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()
        sidecar = tmp_path / "photo.jpg.json"

        sidecar.write_text('null')

        result = read_metadata(photo)
        assert result is None, "JSON null should return None"


class TestMissingFieldsValidation:
    """Tests for validation of missing required fields."""

    def test_missing_version_raises_error(self):
        """Missing version field should raise ValidationError."""
        data = {
            # Missing version
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Missing required field: version"):
            validate_schema(data)

    def test_missing_photo_filename_raises_error(self):
        """Missing photo_filename should raise ValidationError."""
        data = {
            "version": "1.0",
            # Missing photo_filename
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Missing required field: photo_filename"):
            validate_schema(data)

    def test_missing_created_at_raises_error(self):
        """Missing created_at should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            # Missing created_at
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Missing required field: created_at"):
            validate_schema(data)

    def test_missing_modified_at_raises_error(self):
        """Missing modified_at should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            # Missing modified_at
            "tags": [],
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Missing required field: modified_at"):
            validate_schema(data)

    def test_missing_tags_raises_error(self):
        """Missing tags should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            # Missing tags
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Missing required field: tags"):
            validate_schema(data)

    def test_missing_custom_raises_error(self):
        """Missing custom field should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": []
            # Missing custom
        }

        with pytest.raises(ValidationError, match="Missing required field: custom"):
            validate_schema(data)


class TestTypeValidationErrors:
    """Tests for type validation in schema."""

    def test_tags_as_string_raises_error(self):
        """tags as string instead of array should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": "moth,night",  # String instead of list
            "custom": {}
        }

        with pytest.raises(ValidationError, match="tags must be a list"):
            validate_schema(data)

    def test_tags_as_dict_raises_error(self):
        """tags as dict should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": {"tag1": "moth"},  # Dict instead of list
            "custom": {}
        }

        with pytest.raises(ValidationError, match="tags must be a list"):
            validate_schema(data)

    def test_tags_as_number_raises_error(self):
        """tags as number should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": 42,  # Number instead of list
            "custom": {}
        }

        with pytest.raises(ValidationError, match="tags must be a list"):
            validate_schema(data)

    def test_custom_as_list_raises_error(self):
        """custom as list instead of dict should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": ["key1", "value1"]  # List instead of dict
        }

        with pytest.raises(ValidationError, match="custom must be a dictionary"):
            validate_schema(data)

    def test_custom_as_string_raises_error(self):
        """custom as string should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": "some string"  # String instead of dict
        }

        with pytest.raises(ValidationError, match="custom must be a dictionary"):
            validate_schema(data)

    def test_version_wrong_value_raises_error(self):
        """Unsupported version should raise ValidationError."""
        data = {
            "version": "2.0",  # Unsupported version
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Unsupported schema version: 2.0"):
            validate_schema(data)

    def test_tag_exceeds_max_length_raises_error(self):
        """Tag exceeding max length should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": ["a" * 51],  # Exceeds MAX_TAG_LENGTH (50)
            "custom": {}
        }

        with pytest.raises(ValidationError, match="Tag exceeds maximum length"):
            validate_schema(data)

    def test_species_exceeds_max_length_raises_error(self):
        """Species exceeding max length should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "species": "a" * 201,  # Exceeds MAX_SPECIES_LENGTH (200)
            "custom": {}
        }

        with pytest.raises(ValidationError, match="species exceeds maximum length"):
            validate_schema(data)

    def test_notes_exceeds_max_length_raises_error(self):
        """Notes exceeding max length should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "notes": "a" * 10001,  # Exceeds MAX_NOTES_LENGTH (10000)
            "custom": {}
        }

        with pytest.raises(ValidationError, match="notes exceeds maximum length"):
            validate_schema(data)

    def test_custom_exceeds_max_keys_raises_error(self):
        """Custom with too many keys should raise ValidationError."""
        data = {
            "version": "1.0",
            "photo_filename": "photo.jpg",
            "created_at": "2024-01-15T10:00:00Z",
            "modified_at": "2024-01-15T10:00:00Z",
            "tags": [],
            "custom": {f"key{i}": f"value{i}" for i in range(101)}  # Exceeds MAX_CUSTOM_KEYS (100)
        }

        with pytest.raises(ValidationError, match="custom exceeds maximum keys"):
            validate_schema(data)


class TestBackupRecovery:
    """Tests for .bak file recovery logic."""

    def test_backup_created_on_write(self, tmp_path):
        """Backup file should be created when overwriting existing sidecar."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata1 = create_metadata(photo, tags=["moth"])
        write_metadata(photo, metadata1, backup=True)

        # Overwrite with new metadata
        metadata2 = create_metadata(photo, tags=["butterfly"])
        write_metadata(photo, metadata2, backup=True)

        # Backup should exist
        backup_path = tmp_path / "photo.jpg.json.bak"
        assert backup_path.exists(), "Backup file should be created"

        # Backup should contain old data
        backup_data = json.loads(backup_path.read_text())
        assert "moth" in backup_data['tags']
        assert "butterfly" not in backup_data['tags']

    def test_no_backup_when_disabled(self, tmp_path):
        """No backup file should be created when backup=False."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata1 = create_metadata(photo, tags=["moth"])
        write_metadata(photo, metadata1, backup=False)

        # Overwrite with backup disabled
        metadata2 = create_metadata(photo, tags=["butterfly"])
        write_metadata(photo, metadata2, backup=False)

        # Backup should NOT exist
        backup_path = tmp_path / "photo.jpg.json.bak"
        assert not backup_path.exists(), "Backup should not be created when disabled"

    def test_corrupted_main_file_reads_none(self, tmp_path):
        """Corrupted main file should return None (implementation doesn't auto-recover from .bak)."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create valid backup
        metadata = create_metadata(photo, tags=["moth"])
        backup_path = tmp_path / "photo.jpg.json.bak"
        backup_path.write_text(json.dumps(metadata.to_dict()))

        # Create corrupted main file
        sidecar = tmp_path / "photo.jpg.json"
        sidecar.write_text('corrupted json{{{')

        # read_metadata should return None (doesn't auto-recover)
        result = read_metadata(photo)
        assert result is None, "Corrupted main file should return None"

    def test_both_main_and_backup_corrupted(self, tmp_path):
        """Both main and backup corrupted should return None."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create corrupted main file
        sidecar = tmp_path / "photo.jpg.json"
        sidecar.write_text('corrupted json{{{')

        # Create corrupted backup
        backup_path = tmp_path / "photo.jpg.json.bak"
        backup_path.write_text('also corrupted{{{')

        result = read_metadata(photo)
        assert result is None, "Both corrupted should return None"

    def test_backup_preserves_original_content(self, tmp_path):
        """Backup should preserve exact original content."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata with specific content
        metadata1 = create_metadata(photo, tags=["moth", "night"], species="Actias luna")
        write_metadata(photo, metadata1, backup=False)  # No backup on first write

        # Read back to get exact timestamps
        read1 = read_metadata(photo)

        # Update metadata with backup enabled
        metadata2 = create_metadata(photo, tags=["butterfly"], species="Updated species")
        write_metadata(photo, metadata2, backup=True)

        # Backup should contain original metadata (from before second write)
        backup_path = tmp_path / "photo.jpg.json.bak"
        backup_data = json.loads(backup_path.read_text())

        assert backup_data['tags'] == ["moth", "night"]
        assert backup_data['species'] == "Actias luna"
        assert backup_data['created_at'] == read1.created_at
        assert backup_data['modified_at'] == read1.modified_at


class TestPermissionErrors:
    """Tests for permission-related errors."""

    def test_read_only_sidecar_file_write_succeeds_via_atomic_write(self, tmp_path):
        """Atomic write via temp file succeeds even with read-only sidecar (by design)."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create sidecar
        metadata = create_metadata(photo, tags=["moth"])
        sidecar = tmp_path / "photo.jpg.json"
        sidecar.write_text(json.dumps(metadata.to_dict()))

        # Make sidecar read-only
        sidecar.chmod(0o444)

        try:
            # Atomic write via temp file + replace will succeed
            # (This is actually desirable behavior - temp file bypasses permissions)
            metadata2 = create_metadata(photo, tags=["butterfly"])
            result = write_metadata(photo, metadata2, backup=False)

            # On most systems, atomic write succeeds (replaces file)
            # This is expected behavior for atomic writes
            assert result is True, "Atomic write should succeed by replacing file"

            # Verify content was updated
            read_back = read_metadata(photo)
            assert "butterfly" in read_back.tags
        finally:
            # Restore permissions for cleanup
            sidecar.chmod(0o644)

    def test_read_only_directory_write_fails(self, tmp_path):
        """Writing to read-only directory should return False."""
        # Create subdirectory
        subdir = tmp_path / "readonly_dir"
        subdir.mkdir()

        photo = subdir / "photo.jpg"
        photo.touch()

        # Make directory read-only
        subdir.chmod(0o555)

        try:
            # Try to create sidecar in read-only directory
            metadata = create_metadata(photo, tags=["moth"])
            result = write_metadata(photo, metadata, backup=True)
            assert result is False, "Writing to read-only directory should fail"
        finally:
            # Restore permissions for cleanup
            subdir.chmod(0o755)

    def test_permission_error_on_backup_creation(self, tmp_path):
        """Permission error during backup creation should fail gracefully."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create initial metadata
        metadata = create_metadata(photo, tags=["moth"])
        write_metadata(photo, metadata, backup=False)

        # Mock shutil operations to simulate permission error
        with patch('pathlib.Path.read_text', side_effect=PermissionError("Permission denied")):
            # Try to write with backup (should fail during backup read)
            metadata2 = create_metadata(photo, tags=["butterfly"])
            result = write_metadata(photo, metadata2, backup=True)
            assert result is False, "Should fail when backup creation fails"

    def test_atomic_write_cleanup_on_error(self, tmp_path):
        """Temp file should be cleaned up when atomic write fails."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, tags=["moth"])

        # Mock json.dump to fail
        with patch('json.dump', side_effect=OSError("Disk full")):
            result = write_metadata(photo, metadata, backup=False)
            assert result is False, "Write should fail"

        # Check for orphaned temp files
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0, f"Temp file should be cleaned up: {temp_files}"


class TestEdgeCases:
    """Test boundary conditions and edge cases."""

    def test_empty_tags_array_valid(self, tmp_path):
        """Empty tags array should be valid."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, tags=[])
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert read_back.tags == []

    def test_null_optional_fields_valid(self, tmp_path):
        """Null optional fields should be valid."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, species=None, notes=None, modified_by=None)
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert read_back.species is None
        assert read_back.notes is None
        assert read_back.modified_by is None

    def test_unicode_in_tags(self, tmp_path):
        """Unicode characters in tags should work."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, tags=["🦋", "émoji", "日本語"])
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert "🦋" in read_back.tags
        assert "émoji" in read_back.tags
        assert "日本語" in read_back.tags

    def test_very_long_valid_notes(self, tmp_path):
        """Notes at max length should be valid."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create notes at exactly max length (10000 chars)
        long_notes = "a" * 10000
        metadata = create_metadata(photo, notes=long_notes)

        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert len(read_back.notes) == 10000

    def test_maximum_custom_keys(self, tmp_path):
        """Custom dict with max keys (100) should be valid."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        # Create custom dict with exactly 100 keys
        custom = {f"key{i}": f"value{i}" for i in range(100)}
        metadata = create_metadata(photo, custom=custom)

        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert len(read_back.custom) == 100

    def test_nonexistent_photo_path(self, tmp_path):
        """Reading metadata for nonexistent photo should return None."""
        nonexistent = tmp_path / "nonexistent.jpg"

        result = read_metadata(nonexistent)
        assert result is None

    def test_sidecar_without_photo(self, tmp_path):
        """Sidecar exists but photo doesn't - should still read."""
        photo = tmp_path / "photo.jpg"
        # Don't create photo

        # Create sidecar anyway
        metadata = create_metadata(photo, tags=["orphan"])
        sidecar = tmp_path / "photo.jpg.json"
        sidecar.write_text(json.dumps(metadata.to_dict()))

        # Should read successfully (doesn't validate photo existence)
        result = read_metadata(photo)
        assert result is not None
        assert "orphan" in result.tags

    def test_special_characters_in_species(self, tmp_path):
        """Special characters in species name should work."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, species="Actias luna (L'Héritier, 1789)")
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert "L'Héritier" in read_back.species

    def test_newlines_in_notes(self, tmp_path):
        """Newlines in notes should be preserved."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        notes_with_newlines = "Line 1\nLine 2\nLine 3"
        metadata = create_metadata(photo, notes=notes_with_newlines)
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert read_back.notes == notes_with_newlines
        assert read_back.notes.count('\n') == 2

    def test_empty_custom_dict_valid(self, tmp_path):
        """Empty custom dict should be valid."""
        photo = tmp_path / "photo.jpg"
        photo.touch()

        metadata = create_metadata(photo, custom={})
        result = write_metadata(photo, metadata)
        assert result is True

        read_back = read_metadata(photo)
        assert read_back.custom == {}
