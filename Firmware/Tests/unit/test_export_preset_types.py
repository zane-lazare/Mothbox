"""
Unit tests for export preset type definitions.

Tests the ExportPreset dataclass and ExportPresetCategory enum
following TDD principles - these tests are written before implementation.
"""

import pytest
from datetime import datetime


class TestExportPresetCategory:
    """Tests for ExportPresetCategory enum."""

    def test_builtin_value(self):
        """BUILT_IN enum has correct string value."""
        from webui.backend.lib.export_preset_types import ExportPresetCategory

        assert ExportPresetCategory.BUILT_IN.value == "built-in"

    def test_user_value(self):
        """USER enum has correct string value."""
        from webui.backend.lib.export_preset_types import ExportPresetCategory

        assert ExportPresetCategory.USER.value == "user"

    def test_enum_from_string(self):
        """Can create enum from string value."""
        from webui.backend.lib.export_preset_types import ExportPresetCategory

        assert ExportPresetCategory("built-in") == ExportPresetCategory.BUILT_IN
        assert ExportPresetCategory("user") == ExportPresetCategory.USER

    def test_invalid_string_raises(self):
        """Invalid string raises ValueError."""
        from webui.backend.lib.export_preset_types import ExportPresetCategory

        with pytest.raises(ValueError):
            ExportPresetCategory("invalid")


class TestExportPresetDataclass:
    """Tests for ExportPreset dataclass."""

    def test_required_fields(self):
        """Preset requires name, display_name, and export_format."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat

        preset = ExportPreset(
            name="test_preset",
            display_name="Test Preset",
            export_format=ExportJobFormat.JSON,
        )

        assert preset.name == "test_preset"
        assert preset.display_name == "Test Preset"
        assert preset.export_format == ExportJobFormat.JSON

    def test_default_values(self):
        """Preset has correct default values for optional fields."""
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )
        from webui.backend.lib.export_job_types import ExportJobFormat

        preset = ExportPreset(
            name="test_preset",
            display_name="Test Preset",
            export_format=ExportJobFormat.JSON,
        )

        assert preset.description == ""
        assert preset.version == "1.0"
        assert preset.created_at == ""
        assert preset.author == "user"
        assert preset.category == ExportPresetCategory.USER
        assert preset.filter is not None
        assert preset.options == {}

    def test_all_export_formats_supported(self):
        """All ExportJobFormat values work as export_format."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat

        for fmt in ExportJobFormat:
            preset = ExportPreset(
                name=f"test_{fmt.value}",
                display_name=f"Test {fmt.value}",
                export_format=fmt,
            )
            assert preset.export_format == fmt

    def test_filter_default_is_empty_filter(self):
        """Default filter is an empty ExportJobFilter."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        preset = ExportPreset(
            name="test_preset",
            display_name="Test Preset",
            export_format=ExportJobFormat.JSON,
        )

        # Should be an ExportJobFilter with all None defaults
        assert isinstance(preset.filter, ExportJobFilter)
        assert preset.filter.date_start is None
        assert preset.filter.date_end is None
        assert preset.filter.has_species is None

    def test_custom_filter(self):
        """Can set custom filter values."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        custom_filter = ExportJobFilter(
            has_species=True,
            tags=["moth", "butterfly"],
        )

        preset = ExportPreset(
            name="test_preset",
            display_name="Test Preset",
            export_format=ExportJobFormat.DARWIN_CORE,
            filter=custom_filter,
        )

        assert preset.filter.has_species is True
        assert preset.filter.tags == ["moth", "butterfly"]


class TestExportPresetSerialization:
    """Tests for ExportPreset to_dict/from_dict serialization."""

    def test_to_dict_basic(self):
        """to_dict returns correct dictionary structure."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat

        preset = ExportPreset(
            name="test_preset",
            display_name="Test Preset",
            export_format=ExportJobFormat.JSON,
        )

        result = preset.to_dict()

        assert result["name"] == "test_preset"
        assert result["display_name"] == "Test Preset"
        assert result["export_format"] == "json"
        assert result["description"] == ""
        assert result["version"] == "1.0"
        assert result["author"] == "user"
        assert result["category"] == "user"
        assert "filter" in result
        assert "options" in result

    def test_to_dict_with_all_fields(self):
        """to_dict preserves all fields including custom values."""
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        preset = ExportPreset(
            name="gbif_export",
            display_name="GBIF Export",
            export_format=ExportJobFormat.DARWIN_CORE,
            description="Export for GBIF submission",
            version="2.0",
            created_at="2024-12-14T10:00:00Z",
            author="system",
            category=ExportPresetCategory.BUILT_IN,
            filter=ExportJobFilter(has_species=True),
            options={"validate": True},
        )

        result = preset.to_dict()

        assert result["name"] == "gbif_export"
        assert result["display_name"] == "GBIF Export"
        assert result["export_format"] == "darwin_core"
        assert result["description"] == "Export for GBIF submission"
        assert result["version"] == "2.0"
        assert result["created_at"] == "2024-12-14T10:00:00Z"
        assert result["author"] == "system"
        assert result["category"] == "built-in"
        assert result["filter"]["has_species"] is True
        assert result["options"]["validate"] is True

    def test_from_dict_basic(self):
        """from_dict creates preset from dictionary."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat

        data = {
            "name": "test_preset",
            "display_name": "Test Preset",
            "export_format": "json",
        }

        preset = ExportPreset.from_dict(data)

        assert preset.name == "test_preset"
        assert preset.display_name == "Test Preset"
        assert preset.export_format == ExportJobFormat.JSON

    def test_from_dict_with_all_fields(self):
        """from_dict handles all fields correctly."""
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )
        from webui.backend.lib.export_job_types import ExportJobFormat

        data = {
            "name": "gbif_export",
            "display_name": "GBIF Export",
            "export_format": "darwin_core",
            "description": "Export for GBIF submission",
            "version": "2.0",
            "created_at": "2024-12-14T10:00:00Z",
            "author": "system",
            "category": "built-in",
            "filter": {"has_species": True},
            "options": {"validate": True},
        }

        preset = ExportPreset.from_dict(data)

        assert preset.name == "gbif_export"
        assert preset.display_name == "GBIF Export"
        assert preset.export_format == ExportJobFormat.DARWIN_CORE
        assert preset.description == "Export for GBIF submission"
        assert preset.version == "2.0"
        assert preset.created_at == "2024-12-14T10:00:00Z"
        assert preset.author == "system"
        assert preset.category == ExportPresetCategory.BUILT_IN
        assert preset.filter.has_species is True
        assert preset.options["validate"] is True

    def test_from_dict_missing_optional_fields(self):
        """from_dict uses defaults for missing optional fields."""
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )
        from webui.backend.lib.export_job_types import ExportJobFormat

        data = {
            "name": "minimal_preset",
            "display_name": "Minimal",
            "export_format": "csv",
        }

        preset = ExportPreset.from_dict(data)

        assert preset.name == "minimal_preset"
        assert preset.display_name == "Minimal"
        assert preset.export_format == ExportJobFormat.CSV
        assert preset.description == ""
        assert preset.version == "1.0"
        assert preset.created_at == ""
        assert preset.author == "user"
        assert preset.category == ExportPresetCategory.USER
        assert preset.options == {}

    def test_roundtrip_serialization(self):
        """to_dict followed by from_dict preserves all data."""
        from webui.backend.lib.export_preset_types import (
            ExportPreset,
            ExportPresetCategory,
        )
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        original = ExportPreset(
            name="roundtrip_test",
            display_name="Roundtrip Test",
            export_format=ExportJobFormat.INATURALIST,
            description="Testing roundtrip",
            version="1.5",
            created_at="2024-12-14T12:00:00Z",
            author="test_user",
            category=ExportPresetCategory.USER,
            filter=ExportJobFilter(tags=["test"], series_type="hdr"),
            options={"include_xmp": True},
        )

        serialized = original.to_dict()
        restored = ExportPreset.from_dict(serialized)

        assert restored.name == original.name
        assert restored.display_name == original.display_name
        assert restored.export_format == original.export_format
        assert restored.description == original.description
        assert restored.version == original.version
        assert restored.created_at == original.created_at
        assert restored.author == original.author
        assert restored.category == original.category
        assert restored.filter.tags == original.filter.tags
        assert restored.options == original.options

    def test_from_dict_invalid_format_raises(self):
        """from_dict raises ValueError for invalid export_format."""
        from webui.backend.lib.export_preset_types import ExportPreset

        data = {
            "name": "bad_preset",
            "display_name": "Bad Preset",
            "export_format": "invalid_format",
        }

        with pytest.raises(ValueError):
            ExportPreset.from_dict(data)

    def test_from_dict_invalid_category_raises(self):
        """from_dict raises ValueError for invalid category."""
        from webui.backend.lib.export_preset_types import ExportPreset

        data = {
            "name": "bad_preset",
            "display_name": "Bad Preset",
            "export_format": "json",
            "category": "invalid_category",
        }

        with pytest.raises(ValueError):
            ExportPreset.from_dict(data)


class TestExportPresetFilterIntegration:
    """Tests for ExportPreset integration with ExportJobFilter."""

    def test_filter_with_series_type_hdr(self):
        """Filter with HDR series type works correctly."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter
        from webui.backend.lib.series_detection import SeriesType

        preset = ExportPreset(
            name="hdr_preset",
            display_name="HDR Preset",
            export_format=ExportJobFormat.JSON,
            filter=ExportJobFilter(series_type=SeriesType.HDR),
        )

        assert preset.filter.series_type == SeriesType.HDR

        # Verify serialization handles enum
        serialized = preset.to_dict()
        assert serialized["filter"]["series_type"] == "hdr"

    def test_filter_with_series_type_focus_bracket(self):
        """Filter with focus bracket series type works correctly."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter
        from webui.backend.lib.series_detection import SeriesType

        preset = ExportPreset(
            name="fb_preset",
            display_name="Focus Bracket Preset",
            export_format=ExportJobFormat.JSON,
            filter=ExportJobFilter(series_type=SeriesType.FOCUS_BRACKET),
        )

        assert preset.filter.series_type == SeriesType.FOCUS_BRACKET

        # Verify serialization handles enum
        serialized = preset.to_dict()
        assert serialized["filter"]["series_type"] == "focus_bracket"

    def test_filter_with_date_range(self):
        """Filter with date range works correctly."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        preset = ExportPreset(
            name="date_range_preset",
            display_name="Date Range Preset",
            export_format=ExportJobFormat.CSV,
            filter=ExportJobFilter(
                date_start="2024-01-01",
                date_end="2024-12-31",
            ),
        )

        assert preset.filter.date_start == "2024-01-01"
        assert preset.filter.date_end == "2024-12-31"

    def test_filter_with_deployment(self):
        """Filter with deployment path works correctly."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        preset = ExportPreset(
            name="deployment_preset",
            display_name="Deployment Preset",
            export_format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(deployment="/photos/forest_2024"),
        )

        assert preset.filter.deployment == "/photos/forest_2024"
