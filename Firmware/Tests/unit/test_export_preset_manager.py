"""
Unit tests for export preset manager.

Tests the ExportPresetManager class following TDD principles.
Tests are written before implementation.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_preset_dirs(tmp_path):
    """Create temporary preset directories for testing."""
    builtin_dir = tmp_path / "built-in" / "export"
    user_dir = tmp_path / "user" / "export"
    builtin_dir.mkdir(parents=True)
    user_dir.mkdir(parents=True)
    return builtin_dir, user_dir


@pytest.fixture
def sample_builtin_preset():
    """Sample built-in preset data."""
    return {
        "name": "gbif_biodiversity",
        "display_name": "GBIF Biodiversity Export",
        "export_format": "darwin_core",
        "description": "Export for GBIF submission",
        "version": "1.0",
        "created_at": "2024-12-14T00:00:00Z",
        "author": "system",
        "category": "built-in",
        "filter": {"has_species": True},
        "options": {"validate": True},
    }


@pytest.fixture
def sample_user_preset():
    """Sample user preset data."""
    return {
        "name": "my_preset",
        "display_name": "My Custom Preset",
        "export_format": "json",
        "description": "My custom export settings",
        "version": "1.0",
        "created_at": "2024-12-14T12:00:00Z",
        "author": "user",
        "category": "user",
        "filter": {"tags": ["moth"]},
        "options": {},
    }


@pytest.fixture
def preset_manager(temp_preset_dirs):
    """Create ExportPresetManager with temp directories."""
    from webui.backend.export_preset_manager import ExportPresetManager

    builtin_dir, user_dir = temp_preset_dirs
    return ExportPresetManager(builtin_dir, user_dir)


@pytest.fixture
def preset_manager_with_presets(temp_preset_dirs, sample_builtin_preset, sample_user_preset):
    """Create ExportPresetManager with sample presets."""
    from webui.backend.export_preset_manager import ExportPresetManager

    builtin_dir, user_dir = temp_preset_dirs

    # Write built-in preset
    builtin_path = builtin_dir / "gbif_biodiversity.json"
    with open(builtin_path, "w") as f:
        json.dump(sample_builtin_preset, f)

    # Write user preset
    user_path = user_dir / "my_preset.json"
    with open(user_path, "w") as f:
        json.dump(sample_user_preset, f)

    return ExportPresetManager(builtin_dir, user_dir)


class TestExportPresetManagerInit:
    """Tests for ExportPresetManager initialization."""

    def test_creates_user_directory(self, tmp_path):
        """User directory is created if it doesn't exist."""
        from webui.backend.export_preset_manager import ExportPresetManager

        builtin_dir = tmp_path / "built-in" / "export"
        user_dir = tmp_path / "user" / "export"
        builtin_dir.mkdir(parents=True)

        assert not user_dir.exists()

        ExportPresetManager(builtin_dir, user_dir)

        assert user_dir.exists()

    def test_accepts_path_objects(self, temp_preset_dirs):
        """Accepts Path objects for directories."""
        from webui.backend.export_preset_manager import ExportPresetManager

        builtin_dir, user_dir = temp_preset_dirs
        manager = ExportPresetManager(builtin_dir, user_dir)

        assert manager.builtin_dir == builtin_dir
        assert manager.user_dir == user_dir


class TestListPresets:
    """Tests for list_presets method."""

    def test_returns_empty_list_when_no_presets(self, preset_manager):
        """Returns empty list when no presets exist."""
        result = preset_manager.list_presets()
        assert result == []

    def test_lists_builtin_presets(self, preset_manager_with_presets):
        """Lists built-in presets."""
        result = preset_manager_with_presets.list_presets()

        builtin = [p for p in result if p["category"] == "built-in"]
        assert len(builtin) == 1
        assert builtin[0]["name"] == "gbif_biodiversity"
        assert builtin[0]["display_name"] == "GBIF Biodiversity Export"

    def test_lists_user_presets(self, preset_manager_with_presets):
        """Lists user presets."""
        result = preset_manager_with_presets.list_presets()

        user = [p for p in result if p["category"] == "user"]
        assert len(user) == 1
        assert user[0]["name"] == "my_preset"
        assert user[0]["display_name"] == "My Custom Preset"

    def test_lists_both_builtin_and_user(self, preset_manager_with_presets):
        """Lists both built-in and user presets."""
        result = preset_manager_with_presets.list_presets()
        assert len(result) == 2

    def test_filter_by_format(self, preset_manager_with_presets):
        """Can filter presets by export format."""
        result = preset_manager_with_presets.list_presets(format_filter="darwin_core")

        assert len(result) == 1
        assert result[0]["name"] == "gbif_biodiversity"

    def test_filter_by_format_returns_empty(self, preset_manager_with_presets):
        """Returns empty list when no presets match format filter."""
        result = preset_manager_with_presets.list_presets(format_filter="csv")
        assert result == []

    def test_skips_invalid_json_files(self, temp_preset_dirs):
        """Skips files with invalid JSON."""
        from webui.backend.export_preset_manager import ExportPresetManager

        builtin_dir, user_dir = temp_preset_dirs

        # Write invalid JSON
        invalid_path = builtin_dir / "invalid.json"
        with open(invalid_path, "w") as f:
            f.write("{ invalid json }")

        manager = ExportPresetManager(builtin_dir, user_dir)
        result = manager.list_presets()

        assert result == []


class TestCorruptedPresetHandling:
    """Tests for handling corrupted/malformed preset files."""

    def test_list_presets_skips_corrupted_user_preset(self, preset_manager):
        """Corrupted user preset files are skipped without crashing."""
        # Create a corrupted JSON file
        corrupt_file = preset_manager.user_dir / "corrupt.json"
        corrupt_file.write_text("{invalid json")

        presets = preset_manager.list_presets()

        # Should not crash and should not include corrupt preset
        assert "corrupt" not in [p["name"] for p in presets]

    def test_list_presets_skips_corrupted_builtin_preset(self, preset_manager):
        """Corrupted built-in preset files are skipped without crashing."""
        # Create a corrupted JSON file in builtin directory
        corrupt_file = preset_manager.builtin_dir / "corrupt_builtin.json"
        corrupt_file.write_text("not valid json at all {{{")

        presets = preset_manager.list_presets()

        # Should not crash and should not include corrupt preset
        assert "corrupt_builtin" not in [p["name"] for p in presets]

    def test_list_presets_returns_valid_presets_when_some_corrupted(
        self, preset_manager, sample_user_preset
    ):
        """Valid presets are still returned when some files are corrupted."""
        # Create a valid preset
        valid_file = preset_manager.user_dir / "valid_preset.json"
        with open(valid_file, "w") as f:
            json.dump(sample_user_preset, f)

        # Create a corrupted preset
        corrupt_file = preset_manager.user_dir / "corrupt.json"
        corrupt_file.write_text("{truncated")

        presets = preset_manager.list_presets()

        # Should include valid preset but not corrupt one
        preset_names = [p["name"] for p in presets]
        assert "my_preset" in preset_names
        assert "corrupt" not in preset_names

    def test_get_preset_returns_none_for_corrupted_file(self, preset_manager):
        """get_preset returns None for corrupted preset files."""
        # Create a corrupted JSON file
        corrupt_file = preset_manager.user_dir / "bad_preset.json"
        corrupt_file.write_text("{incomplete json")

        result = preset_manager.get_preset("bad_preset")

        assert result is None

    def test_get_preset_handles_truncated_json(self, preset_manager):
        """get_preset handles truncated JSON gracefully."""
        # Simulate file truncated mid-write
        truncated_file = preset_manager.user_dir / "truncated.json"
        truncated_file.write_text('{"name": "truncated", "display_name": "Test", "export_for')

        result = preset_manager.get_preset("truncated")

        assert result is None

    def test_get_preset_handles_empty_file(self, preset_manager):
        """get_preset handles empty files gracefully."""
        empty_file = preset_manager.user_dir / "empty.json"
        empty_file.write_text("")

        result = preset_manager.get_preset("empty")

        assert result is None

    def test_list_presets_handles_binary_garbage(self, preset_manager):
        """list_presets handles files with binary garbage."""
        garbage_file = preset_manager.user_dir / "garbage.json"
        garbage_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        presets = preset_manager.list_presets()

        # Should not crash and should not include garbage file
        assert "garbage" not in [p["name"] for p in presets]


class TestGetPreset:
    """Tests for get_preset method."""

    def test_gets_builtin_preset(self, preset_manager_with_presets):
        """Gets built-in preset by name."""
        result = preset_manager_with_presets.get_preset("gbif_biodiversity")

        assert result is not None
        assert result.name == "gbif_biodiversity"
        assert result.export_format.value == "darwin_core"

    def test_gets_user_preset(self, preset_manager_with_presets):
        """Gets user preset by name."""
        result = preset_manager_with_presets.get_preset("my_preset")

        assert result is not None
        assert result.name == "my_preset"
        assert result.export_format.value == "json"

    def test_returns_none_for_missing(self, preset_manager):
        """Returns None for non-existent preset."""
        result = preset_manager.get_preset("nonexistent")
        assert result is None

    def test_builtin_takes_precedence(self, temp_preset_dirs, sample_builtin_preset, sample_user_preset):
        """Built-in preset takes precedence over user preset with same name."""
        from webui.backend.export_preset_manager import ExportPresetManager

        builtin_dir, user_dir = temp_preset_dirs

        # Write both with same name
        builtin_preset = {**sample_builtin_preset, "name": "same_name"}
        user_preset = {**sample_user_preset, "name": "same_name", "description": "User version"}

        with open(builtin_dir / "same_name.json", "w") as f:
            json.dump(builtin_preset, f)

        with open(user_dir / "same_name.json", "w") as f:
            json.dump(user_preset, f)

        manager = ExportPresetManager(builtin_dir, user_dir)
        result = manager.get_preset("same_name")

        # Built-in should be returned
        assert result.description == "Export for GBIF submission"


class TestSavePreset:
    """Tests for save_preset method."""

    def test_saves_new_preset(self, preset_manager):
        """Saves new user preset successfully."""
        from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="new_preset",
            display_name="New Preset",
            export_format=ExportJobFormat.CSV,
            description="A new preset",
            filter=ExportJobFilter(has_species=True),
        )

        success, message = preset_manager.save_preset(preset)

        assert success is True
        assert "saved" in message.lower()

        # Verify file was created
        preset_file = preset_manager.user_dir / "new_preset.json"
        assert preset_file.exists()

    def test_validates_preset_name_alphanumeric(self, preset_manager):
        """Rejects invalid preset names."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="invalid-name!",  # Invalid characters
            display_name="Invalid",
            export_format=ExportJobFormat.JSON,
        )

        success, message = preset_manager.save_preset(preset)

        assert success is False
        assert "alphanumeric" in message.lower() or "letters" in message.lower()

    def test_allows_underscore_in_name(self, preset_manager):
        """Allows underscores in preset names."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="my_custom_preset",
            display_name="My Custom Preset",
            export_format=ExportJobFormat.JSON,
        )

        success, message = preset_manager.save_preset(preset)

        assert success is True

    def test_rejects_builtin_category(self, preset_manager):
        """Cannot save preset with built-in category."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )

        preset = ExportPreset(
            name="fake_builtin",
            display_name="Fake Built-in",
            export_format=ExportJobFormat.JSON,
            category=ExportPresetCategory.BUILT_IN,
        )

        success, message = preset_manager.save_preset(preset)

        assert success is False
        assert "built-in" in message.lower()

    def test_overwrites_existing_user_preset(self, preset_manager_with_presets):
        """Can overwrite existing user preset."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="my_preset",  # Same name as existing
            display_name="Updated Preset",
            export_format=ExportJobFormat.CSV,
            description="Updated description",
        )

        success, message = preset_manager_with_presets.save_preset(preset)

        assert success is True

        # Verify it was updated
        loaded = preset_manager_with_presets.get_preset("my_preset")
        assert loaded.description == "Updated description"
        assert loaded.export_format.value == "csv"

    def test_saved_preset_contains_timestamp(self, preset_manager):
        """Saved preset contains created_at timestamp."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="timestamped",
            display_name="Timestamped",
            export_format=ExportJobFormat.JSON,
        )

        preset_manager.save_preset(preset)

        # Read the file directly
        preset_file = preset_manager.user_dir / "timestamped.json"
        with open(preset_file) as f:
            data = json.load(f)

        assert "created_at" in data
        assert data["created_at"]  # Not empty


class TestDeletePreset:
    """Tests for delete_preset method."""

    def test_deletes_user_preset(self, preset_manager_with_presets):
        """Deletes user preset successfully."""
        success, message = preset_manager_with_presets.delete_preset("my_preset")

        assert success is True
        assert "deleted" in message.lower()

        # Verify file was removed
        preset_file = preset_manager_with_presets.user_dir / "my_preset.json"
        assert not preset_file.exists()

    def test_protects_builtin_presets(self, preset_manager_with_presets):
        """Cannot delete built-in presets."""
        success, message = preset_manager_with_presets.delete_preset("gbif_biodiversity")

        assert success is False
        assert "built-in" in message.lower()

        # Verify file still exists
        preset_file = preset_manager_with_presets.builtin_dir / "gbif_biodiversity.json"
        assert preset_file.exists()

    def test_returns_error_for_nonexistent(self, preset_manager):
        """Returns error for non-existent preset."""
        success, message = preset_manager.delete_preset("nonexistent")

        assert success is False
        assert "not found" in message.lower()


class TestValidatePreset:
    """Tests for validate_preset method."""

    def test_valid_preset_passes(self, preset_manager, sample_user_preset):
        """Valid preset passes validation."""
        valid, message = preset_manager.validate_preset(sample_user_preset)

        assert valid is True

    def test_missing_name_fails(self, preset_manager):
        """Preset without name fails validation."""
        data = {
            "display_name": "Test",
            "export_format": "json",
        }

        valid, message = preset_manager.validate_preset(data)

        assert valid is False
        assert "name" in message.lower()

    def test_missing_display_name_fails(self, preset_manager):
        """Preset without display_name fails validation."""
        data = {
            "name": "test",
            "export_format": "json",
        }

        valid, message = preset_manager.validate_preset(data)

        assert valid is False
        assert "display_name" in message.lower()

    def test_missing_export_format_fails(self, preset_manager):
        """Preset without export_format fails validation."""
        data = {
            "name": "test",
            "display_name": "Test",
        }

        valid, message = preset_manager.validate_preset(data)

        assert valid is False
        assert "export_format" in message.lower() or "format" in message.lower()

    def test_invalid_export_format_fails(self, preset_manager):
        """Invalid export_format fails validation."""
        data = {
            "name": "test",
            "display_name": "Test",
            "export_format": "invalid_format",
        }

        valid, message = preset_manager.validate_preset(data)

        assert valid is False
        assert "format" in message.lower()


class TestNormalizePreset:
    """Tests for normalize_preset method."""

    def test_adds_missing_defaults(self, preset_manager):
        """Adds missing optional fields with defaults."""
        data = {
            "name": "minimal",
            "display_name": "Minimal",
            "export_format": "json",
        }

        result = preset_manager.normalize_preset(data)

        assert result["description"] == ""
        assert result["version"] == "1.0"
        assert result["author"] == "user"
        assert result["category"] == "user"
        assert "filter" in result
        assert "options" in result

    def test_preserves_existing_values(self, preset_manager, sample_user_preset):
        """Preserves existing values when normalizing."""
        result = preset_manager.normalize_preset(sample_user_preset)

        assert result["name"] == "my_preset"
        assert result["description"] == "My custom export settings"
        assert result["filter"]["tags"] == ["moth"]


class TestFileLocking:
    """Tests for file locking during save operations."""

    def test_concurrent_saves_dont_corrupt(self, preset_manager):
        """Concurrent save operations don't corrupt files."""
        import threading

        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        errors = []
        success_count = [0]

        def save_preset(name):
            try:
                preset = ExportPreset(
                    name=name,
                    display_name=f"Preset {name}",
                    export_format=ExportJobFormat.JSON,
                )
                success, _ = preset_manager.save_preset(preset)
                if success:
                    success_count[0] += 1
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(10):
            t = threading.Thread(target=save_preset, args=(f"concurrent_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All saves should succeed
        assert len(errors) == 0
        assert success_count[0] == 10

        # All files should be valid JSON
        for i in range(10):
            preset_file = preset_manager.user_dir / f"concurrent_{i}.json"
            assert preset_file.exists()
            with open(preset_file) as f:
                data = json.load(f)  # Should not raise
                assert data["name"] == f"concurrent_{i}"


class TestGetPresetCount:
    """Tests for get_preset_count method."""

    def test_empty_directories(self, preset_manager):
        """Returns zero counts for empty directories."""
        counts = preset_manager.get_preset_count()

        assert counts["built_in"] == 0
        assert counts["user"] == 0
        assert counts["total"] == 0

    def test_counts_presets(self, preset_manager_with_presets):
        """Counts presets correctly."""
        counts = preset_manager_with_presets.get_preset_count()

        assert counts["built_in"] == 1
        assert counts["user"] == 1
        assert counts["total"] == 2


class TestBuiltinPresets:
    """Tests for the actual built-in export presets shipped with Mothbox."""

    @pytest.fixture
    def builtin_preset_manager(self):
        """Manager pointing to real built-in presets directory."""
        from webui.backend.export_preset_manager import ExportPresetManager

        # Point to actual built-in presets
        builtin_dir = Path(__file__).parent.parent.parent / "webui" / "backend" / "presets_builtin" / "export"
        user_dir = Path("/tmp/test_export_user_presets")
        user_dir.mkdir(parents=True, exist_ok=True)

        return ExportPresetManager(builtin_dir, user_dir)

    def test_gbif_biodiversity_preset_loads(self, builtin_preset_manager):
        """GBIF biodiversity preset loads and validates."""
        preset = builtin_preset_manager.get_preset("gbif_biodiversity")

        assert preset is not None
        assert preset.name == "gbif_biodiversity"
        assert preset.export_format.value == "darwin_core"
        assert preset.filter.has_species is True

    def test_inaturalist_upload_preset_loads(self, builtin_preset_manager):
        """iNaturalist upload preset loads and validates."""
        preset = builtin_preset_manager.get_preset("inaturalist_upload")

        assert preset is not None
        assert preset.name == "inaturalist_upload"
        assert preset.export_format.value == "inaturalist"

    def test_simple_json_preset_loads(self, builtin_preset_manager):
        """Simple JSON preset loads and validates."""
        preset = builtin_preset_manager.get_preset("simple_json")

        assert preset is not None
        assert preset.name == "simple_json"
        assert preset.export_format.value == "json"

    def test_simple_csv_preset_loads(self, builtin_preset_manager):
        """Simple CSV preset loads and validates."""
        preset = builtin_preset_manager.get_preset("simple_csv")

        assert preset is not None
        assert preset.name == "simple_csv"
        assert preset.export_format.value == "csv"

    def test_hdr_series_preset_loads(self, builtin_preset_manager):
        """HDR series preset loads and validates."""
        preset = builtin_preset_manager.get_preset("hdr_series")

        assert preset is not None
        assert preset.name == "hdr_series"
        assert preset.export_format.value == "json"
        # Check filter for series_type
        filter_dict = preset.filter.to_dict()
        assert filter_dict.get("series_type") == "hdr"

    def test_focus_bracket_series_preset_loads(self, builtin_preset_manager):
        """Focus bracket series preset loads and validates."""
        preset = builtin_preset_manager.get_preset("focus_bracket_series")

        assert preset is not None
        assert preset.name == "focus_bracket_series"
        assert preset.export_format.value == "json"
        # Check filter for series_type
        filter_dict = preset.filter.to_dict()
        assert filter_dict.get("series_type") == "focus_bracket"

    def test_all_builtin_presets_have_descriptions(self, builtin_preset_manager):
        """All built-in presets have meaningful descriptions."""
        presets = builtin_preset_manager.list_presets()

        for preset in presets:
            assert preset["description"], f"Preset {preset['name']} has no description"
            assert len(preset["description"]) > 20, f"Preset {preset['name']} description too short"

    def test_lists_all_six_builtin_presets(self, builtin_preset_manager):
        """Lists all 6 built-in export presets."""
        presets = builtin_preset_manager.list_presets()
        builtin_presets = [p for p in presets if p["category"] == "built-in"]

        assert len(builtin_presets) == 6
        preset_names = {p["name"] for p in builtin_presets}
        expected_names = {
            "gbif_biodiversity",
            "inaturalist_upload",
            "simple_json",
            "simple_csv",
            "hdr_series",
            "focus_bracket_series",
        }
        assert preset_names == expected_names
