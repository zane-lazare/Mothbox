"""
Unit tests for iNaturalist field mapping (Issue #118)

Tests the iNaturalist field mapping module for transforming Mothbox metadata
to iNaturalist-compatible format with XMP sidecar integration.

Coverage Target: 95%+
"""

import pytest

from webui.backend.lib.inaturalist_mapping import (
    CONFIDENCE_TO_QUALITY_GRADE,
    DEFAULT_CREATOR,
    DEFAULT_LICENSE,
    INATURALIST_RECOMMENDED_FIELDS,
    INATURALIST_REQUIRED_FIELDS,
    TAXONOMY_KEYWORD_PREFIX,
    INaturalistFieldMapping,
    ValidationResult,
    build_taxonomy_keywords,
    format_observation_notes,
    format_observation_title,
    get_xmp_field_mappings,
    is_valid_for_inaturalist_export,
    map_species_confidence_to_quality_grade,
    transform_metadata_to_inaturalist,
    validate_for_inaturalist,
)
from webui.backend.services.export_metadata_service import ExportMetadata

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_metadata():
    """Create a sample ExportMetadata with all fields populated."""
    return ExportMetadata(
        photo_path="/photos/moth_2024_01_15.jpg",
        filename="moth_2024_01_15.jpg",
        timestamp="2024-01-15T10:30:00",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=10.0,
        gps_accuracy=2.5,
        camera_make="Arducam",
        camera_model="OwlSight 64MP",
        exposure_time="1/100",
        iso=400,
        focal_length="16mm",
        species="Actias luna",
        species_common_name="Luna Moth",
        species_confidence="certain",
        tags=["nocturnal", "lepidoptera"],
        notes="Beautiful specimen",
        mothbox_id="MB-001",
        firmware_version="5.0.0",
        deployment_name="oak-ridge-2024",
        deployment_location_name="Oak Ridge, TN",
        deployment_start_date="2024-01-01",
        deployment_end_date="2024-12-31",
        environmental_conditions={"temperature": 20.5},
        series_type=None,
        series_index=None,
        series_count=None,
        file_size=1024000,
        width=4000,
        height=3000,
    )


@pytest.fixture
def minimal_metadata():
    """Create ExportMetadata with only required fields."""
    return ExportMetadata(
        photo_path="/photos/minimal.jpg",
        filename="minimal.jpg",
        timestamp="2024-01-15T10:30:00",
        latitude=37.7749,
        longitude=-122.4194,
    )


@pytest.fixture
def metadata_without_gps():
    """Create ExportMetadata without GPS coordinates."""
    return ExportMetadata(
        photo_path="/photos/no_gps.jpg",
        filename="no_gps.jpg",
        timestamp="2024-01-15T10:30:00",
        latitude=None,
        longitude=None,
    )


# ============================================================================
# Tests for iNaturalist Constants
# ============================================================================


class TestINaturalistConstants:
    """Tests for iNaturalist constant definitions."""

    def test_required_fields_defined(self):
        """Required fields list should contain essential iNaturalist fields."""
        assert "latitude" in INATURALIST_REQUIRED_FIELDS
        assert "longitude" in INATURALIST_REQUIRED_FIELDS
        assert "timestamp" in INATURALIST_REQUIRED_FIELDS

    def test_recommended_fields_defined(self):
        """Recommended fields list should contain important iNaturalist fields."""
        assert "species" in INATURALIST_RECOMMENDED_FIELDS
        assert "species_common_name" in INATURALIST_RECOMMENDED_FIELDS
        assert "species_confidence" in INATURALIST_RECOMMENDED_FIELDS
        assert "notes" in INATURALIST_RECOMMENDED_FIELDS

    def test_confidence_to_quality_grade_mapping(self):
        """Confidence to quality grade mapping should be complete."""
        assert CONFIDENCE_TO_QUALITY_GRADE["certain"] == "research"
        assert CONFIDENCE_TO_QUALITY_GRADE["probable"] == "needs_id"
        assert CONFIDENCE_TO_QUALITY_GRADE["possible"] == "needs_id"
        assert CONFIDENCE_TO_QUALITY_GRADE["unknown"] == "casual"

    def test_default_values(self):
        """Default values should be defined."""
        assert DEFAULT_LICENSE == "CC BY-NC 4.0"
        assert DEFAULT_CREATOR == "Mothbox"

    def test_taxonomy_prefix(self):
        """Taxonomy keyword prefix should be defined."""
        assert TAXONOMY_KEYWORD_PREFIX == "taxonomy:"


# ============================================================================
# Tests for Field Mapping Configuration
# ============================================================================


class TestFieldMappingConfiguration:
    """Tests for INaturalistFieldMapping dataclass."""

    def test_field_mapping_dataclass(self):
        """INaturalistFieldMapping should store all required attributes."""
        mapping = INaturalistFieldMapping(
            inat_field="testField",
            source_field="test_field",
            default_value="default",
            is_required=True,
            xmp_field="dc:test",
            description="Test description",
        )
        assert mapping.inat_field == "testField"
        assert mapping.source_field == "test_field"
        assert mapping.default_value == "default"
        assert mapping.is_required is True
        assert mapping.xmp_field == "dc:test"
        assert mapping.description == "Test description"


# ============================================================================
# Tests for Species Confidence Mapping
# ============================================================================


class TestSpeciesConfidenceMapping:
    """Tests for map_species_confidence_to_quality_grade() function."""

    def test_certain_maps_to_research(self):
        """Certain confidence should map to research quality grade."""
        assert map_species_confidence_to_quality_grade("certain") == "research"

    def test_probable_maps_to_needs_id(self):
        """Probable confidence should map to needs_id quality grade."""
        assert map_species_confidence_to_quality_grade("probable") == "needs_id"

    def test_possible_maps_to_needs_id(self):
        """Possible confidence should map to needs_id quality grade."""
        assert map_species_confidence_to_quality_grade("possible") == "needs_id"

    def test_unknown_maps_to_casual(self):
        """Unknown confidence should map to casual quality grade."""
        assert map_species_confidence_to_quality_grade("unknown") == "casual"

    def test_none_returns_default(self):
        """None confidence should return default quality grade."""
        assert map_species_confidence_to_quality_grade(None) == "needs_id"

    def test_case_insensitive(self):
        """Mapping should be case insensitive."""
        assert map_species_confidence_to_quality_grade("CERTAIN") == "research"
        assert map_species_confidence_to_quality_grade("Probable") == "needs_id"

    def test_invalid_returns_default(self):
        """Invalid confidence values should return default quality grade."""
        assert map_species_confidence_to_quality_grade("invalid") == "needs_id"


# ============================================================================
# Tests for Taxonomy Keywords
# ============================================================================


class TestTaxonomyKeywords:
    """Tests for build_taxonomy_keywords() function."""

    def test_builds_keywords_for_binomial(self):
        """Should build hierarchical taxonomy keywords for binomial name."""
        keywords = build_taxonomy_keywords("Actias luna")

        # Should contain taxonomy keywords
        assert any(kw.startswith("taxonomy:") for kw in keywords)

        # Should contain genus
        assert "taxonomy:genus=Actias" in keywords

        # Should contain species
        assert "taxonomy:species=Actias luna" in keywords

    def test_builds_keywords_for_trinomial(self):
        """Should build hierarchical taxonomy keywords for trinomial name."""
        keywords = build_taxonomy_keywords("Papilio glaucus glaucus")

        assert "taxonomy:genus=Papilio" in keywords
        assert "taxonomy:species=Papilio glaucus" in keywords
        # Subspecies would be: "taxonomy:subspecies=Papilio glaucus glaucus"

    def test_empty_for_none(self):
        """Should return empty list for None species."""
        keywords = build_taxonomy_keywords(None)
        assert keywords == []

    def test_empty_for_empty_string(self):
        """Should return empty list for empty species."""
        keywords = build_taxonomy_keywords("")
        assert keywords == []

    def test_handles_single_word(self):
        """Should handle single-word species name (genus only)."""
        keywords = build_taxonomy_keywords("Actias")

        assert "taxonomy:genus=Actias" in keywords

    def test_includes_kingdom(self):
        """Should include kingdom=Animalia for all species."""
        keywords = build_taxonomy_keywords("Actias luna")

        assert "taxonomy:kingdom=Animalia" in keywords

    def test_includes_phylum(self):
        """Should include phylum=Arthropoda for all species."""
        keywords = build_taxonomy_keywords("Actias luna")

        assert "taxonomy:phylum=Arthropoda" in keywords

    def test_includes_class(self):
        """Should include class=Insecta for all species."""
        keywords = build_taxonomy_keywords("Actias luna")

        assert "taxonomy:class=Insecta" in keywords

    def test_includes_order(self):
        """Should include order=Lepidoptera for all species."""
        keywords = build_taxonomy_keywords("Actias luna")

        assert "taxonomy:order=Lepidoptera" in keywords


# ============================================================================
# Tests for Observation Title Formatting
# ============================================================================


class TestObservationTitleFormatting:
    """Tests for format_observation_title() function."""

    def test_formats_with_both_names(self, sample_metadata):
        """Should format as 'Common Name (Scientific Name)' when both present."""
        title = format_observation_title(sample_metadata)
        assert title == "Luna Moth (Actias luna)"

    def test_formats_with_scientific_only(self, minimal_metadata):
        """Should format as 'Scientific Name' when only species present."""
        minimal_metadata.species = "Actias luna"
        title = format_observation_title(minimal_metadata)
        assert title == "Actias luna"

    def test_formats_with_common_only(self, minimal_metadata):
        """Should format as 'Common Name' when only common name present."""
        minimal_metadata.species_common_name = "Luna Moth"
        title = format_observation_title(minimal_metadata)
        assert title == "Luna Moth"

    def test_returns_unknown_when_neither(self, minimal_metadata):
        """Should return 'Unknown' when neither name is present."""
        title = format_observation_title(minimal_metadata)
        assert title == "Unknown"

    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            species=None,
            species_common_name=None,
        )
        title = format_observation_title(metadata)
        assert title == "Unknown"


# ============================================================================
# Tests for Observation Notes Formatting
# ============================================================================


class TestObservationNotesFormatting:
    """Tests for format_observation_notes() function."""

    def test_combines_notes_and_tags(self, sample_metadata):
        """Should combine notes and tags into observation notes."""
        notes = format_observation_notes(sample_metadata)

        assert "Beautiful specimen" in notes
        assert "nocturnal" in notes
        assert "lepidoptera" in notes

    def test_includes_deployment_info(self, sample_metadata):
        """Should include deployment information in notes."""
        notes = format_observation_notes(sample_metadata)

        assert "oak-ridge-2024" in notes or "Oak Ridge, TN" in notes

    def test_handles_only_notes(self, minimal_metadata):
        """Should handle metadata with only notes."""
        minimal_metadata.notes = "Test note"
        notes = format_observation_notes(minimal_metadata)

        assert "Test note" in notes

    def test_handles_only_tags(self, minimal_metadata):
        """Should handle metadata with only tags."""
        minimal_metadata.tags = ["tag1", "tag2"]
        notes = format_observation_notes(minimal_metadata)

        assert "tag1" in notes
        assert "tag2" in notes

    def test_returns_empty_when_no_data(self, minimal_metadata):
        """Should return empty string when no notes/tags/deployment."""
        notes = format_observation_notes(minimal_metadata)
        assert notes == ""

    def test_formats_tags_as_comma_list(self, sample_metadata):
        """Should format tags as comma-separated list."""
        notes = format_observation_notes(sample_metadata)

        # Tags should be comma-separated
        assert "nocturnal, lepidoptera" in notes or "nocturnal,lepidoptera" in notes


# ============================================================================
# Tests for Metadata Transformation
# ============================================================================


class TestMetadataTransformation:
    """Tests for transform_metadata_to_inaturalist() function."""

    def test_transforms_complete_metadata(self, sample_metadata):
        """Complete metadata should transform to iNaturalist dict."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert isinstance(inat, dict)
        assert inat["latitude"] == 37.7749
        assert inat["longitude"] == -122.4194
        assert inat["timestamp"] == "2024-01-15T10:30:00"
        assert inat["species"] == "Actias luna"
        assert inat["common_name"] == "Luna Moth"

    def test_transforms_minimal_metadata(self, minimal_metadata):
        """Minimal metadata should still produce valid iNaturalist dict."""
        inat = transform_metadata_to_inaturalist(minimal_metadata)

        assert inat["latitude"] == 37.7749
        assert inat["longitude"] == -122.4194
        assert inat["timestamp"] == "2024-01-15T10:30:00"

    def test_includes_title(self, sample_metadata):
        """Should include formatted title."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "title" in inat
        assert inat["title"] == "Luna Moth (Actias luna)"

    def test_includes_notes(self, sample_metadata):
        """Should include formatted notes."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "notes" in inat
        assert len(inat["notes"]) > 0

    def test_includes_quality_grade(self, sample_metadata):
        """Should include quality grade mapped from confidence."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "quality_grade" in inat
        assert inat["quality_grade"] == "research"

    def test_includes_taxonomy_keywords(self, sample_metadata):
        """Should include taxonomy keywords."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "keywords" in inat
        assert any(kw.startswith("taxonomy:") for kw in inat["keywords"])

    def test_includes_license(self, sample_metadata):
        """Should include default license."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "license" in inat
        assert inat["license"] == DEFAULT_LICENSE

    def test_includes_creator(self, sample_metadata):
        """Should include creator/observer."""
        inat = transform_metadata_to_inaturalist(sample_metadata)

        assert "creator" in inat or "observer" in inat

    def test_transform_applies_gps_precision(self, sample_metadata):
        """transform_metadata_to_inaturalist applies GPS precision."""
        sample_metadata.latitude = 37.774900123456
        sample_metadata.longitude = -122.419400123456

        inat = transform_metadata_to_inaturalist(sample_metadata, gps_precision=2)
        assert inat["latitude"] == 37.77
        assert inat["longitude"] == -122.42

    def test_transform_gps_precision_zero(self, sample_metadata):
        """GPS precision 0 rounds to whole numbers."""
        sample_metadata.latitude = 37.774900123456
        sample_metadata.longitude = -122.419400123456

        inat = transform_metadata_to_inaturalist(sample_metadata, gps_precision=0)
        assert inat["latitude"] == 38.0  # round(37.77..., 0) = 38.0
        assert inat["longitude"] == -122.0

    def test_transform_gps_precision_none_preserves_full(self, sample_metadata):
        """GPS precision None preserves full precision."""
        sample_metadata.latitude = 37.774900123456
        sample_metadata.longitude = -122.419400123456

        inat = transform_metadata_to_inaturalist(sample_metadata, gps_precision=None)
        assert inat["latitude"] == 37.774900123456
        assert inat["longitude"] == -122.419400123456


# ============================================================================
# Tests for XMP Field Mappings
# ============================================================================


class TestXmpFieldMappings:
    """Tests for get_xmp_field_mappings() function."""

    def test_returns_dict(self):
        """get_xmp_field_mappings() should return a dict."""
        mappings = get_xmp_field_mappings()
        assert isinstance(mappings, dict)

    def test_includes_dublin_core_mappings(self):
        """Should include Dublin Core namespace mappings."""
        mappings = get_xmp_field_mappings()

        # Should have at least some dc: mappings
        dc_fields = [k for k in mappings if mappings[k].startswith("dc:")]
        assert len(dc_fields) > 0

    def test_includes_xmp_mappings(self):
        """Should include XMP namespace mappings."""
        mappings = get_xmp_field_mappings()

        # Should have at least some xmp: mappings
        xmp_fields = [k for k in mappings if mappings[k].startswith("xmp:")]
        assert len(xmp_fields) > 0

    def test_maps_latitude_to_exif(self):
        """Should map latitude to EXIF GPS namespace."""
        mappings = get_xmp_field_mappings()

        assert "latitude" in mappings
        assert "exif:GPSLatitude" in mappings["latitude"]

    def test_maps_longitude_to_exif(self):
        """Should map longitude to EXIF GPS namespace."""
        mappings = get_xmp_field_mappings()

        assert "longitude" in mappings
        assert "exif:GPSLongitude" in mappings["longitude"]


# ============================================================================
# Tests for Export Validity Check
# ============================================================================


class TestExportValidityCheck:
    """Tests for is_valid_for_inaturalist_export() function."""

    def test_valid_with_gps_and_timestamp(self, sample_metadata):
        """Metadata with GPS and timestamp should be valid for export."""
        assert is_valid_for_inaturalist_export(sample_metadata) is True

    def test_invalid_without_latitude(self, metadata_without_gps):
        """Metadata without latitude should be invalid."""
        assert is_valid_for_inaturalist_export(metadata_without_gps) is False

    def test_invalid_without_longitude(self, sample_metadata):
        """Metadata without longitude should be invalid."""
        sample_metadata.longitude = None
        assert is_valid_for_inaturalist_export(sample_metadata) is False

    def test_invalid_without_timestamp(self, sample_metadata):
        """Metadata without timestamp should be invalid."""
        sample_metadata.timestamp = None
        assert is_valid_for_inaturalist_export(sample_metadata) is False

    def test_invalid_latitude_range(self, sample_metadata):
        """Latitude outside valid range should be invalid."""
        sample_metadata.latitude = 91.0
        assert is_valid_for_inaturalist_export(sample_metadata) is False

        sample_metadata.latitude = -91.0
        assert is_valid_for_inaturalist_export(sample_metadata) is False

    def test_invalid_longitude_range(self, sample_metadata):
        """Longitude outside valid range should be invalid."""
        sample_metadata.longitude = 181.0
        assert is_valid_for_inaturalist_export(sample_metadata) is False

        sample_metadata.longitude = -181.0
        assert is_valid_for_inaturalist_export(sample_metadata) is False

    def test_valid_at_boundaries(self, sample_metadata):
        """Coordinates at boundaries should be valid."""
        sample_metadata.latitude = 90.0
        sample_metadata.longitude = 180.0
        assert is_valid_for_inaturalist_export(sample_metadata) is True

        sample_metadata.latitude = -90.0
        sample_metadata.longitude = -180.0
        assert is_valid_for_inaturalist_export(sample_metadata) is True


# ============================================================================
# Tests for Comprehensive Validation
# ============================================================================


class TestComprehensiveValidation:
    """Tests for validate_for_inaturalist() function."""

    def test_valid_metadata_passes(self, sample_metadata):
        """Complete metadata should pass validation."""
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is True
        assert len(result.missing_required) == 0

    def test_missing_latitude_fails(self, sample_metadata):
        """Missing latitude should fail validation."""
        sample_metadata.latitude = None
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is False
        assert "latitude" in result.missing_required

    def test_missing_longitude_fails(self, sample_metadata):
        """Missing longitude should fail validation."""
        sample_metadata.longitude = None
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is False
        assert "longitude" in result.missing_required

    def test_missing_timestamp_fails(self, sample_metadata):
        """Missing timestamp should fail validation."""
        sample_metadata.timestamp = None
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is False
        assert "timestamp" in result.missing_required

    def test_invalid_latitude_range_fails(self, sample_metadata):
        """Invalid latitude range should fail validation."""
        sample_metadata.latitude = 95.0
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is False
        assert any("latitude" in field.lower() for field in result.missing_required)

    def test_invalid_longitude_range_fails(self, sample_metadata):
        """Invalid longitude range should fail validation."""
        sample_metadata.longitude = 200.0
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is False
        assert any("longitude" in field.lower() for field in result.missing_required)

    def test_warning_for_missing_species(self, minimal_metadata):
        """Missing species should generate warning."""
        result = validate_for_inaturalist(minimal_metadata)

        # Should be valid (species not required) but have warning
        assert result.is_valid is True
        assert len(result.missing_recommended) > 0
        assert "species" in result.missing_recommended

    def test_warning_for_missing_common_name(self, sample_metadata):
        """Missing common name should generate warning."""
        sample_metadata.species_common_name = None
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is True
        assert "species_common_name" in result.missing_recommended

    def test_no_warnings_for_complete_metadata(self, sample_metadata):
        """Complete metadata should have no warnings."""
        result = validate_for_inaturalist(sample_metadata)

        assert result.is_valid is True
        assert len(result.missing_recommended) == 0
        assert len(result.warnings) == 0


# ============================================================================
# Tests for ValidationResult Structure
# ============================================================================


class TestValidationResultStructure:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_fields(self):
        """ValidationResult should have expected fields."""
        result = ValidationResult(
            is_valid=True,
            missing_required=["field1"],
            missing_recommended=["field2"],
            warnings=["warning1"],
        )

        assert result.is_valid is True
        assert result.missing_required == ["field1"]
        assert result.missing_recommended == ["field2"]
        assert result.warnings == ["warning1"]

    def test_validation_result_defaults(self):
        """ValidationResult should have default empty lists."""
        result = ValidationResult(is_valid=True)

        assert result.missing_required == []
        assert result.missing_recommended == []
        assert result.warnings == []


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_unusual_species_names(self):
        """Should handle unusual species name formats."""
        # Single word (genus only)
        assert len(build_taxonomy_keywords("Actias")) > 0

        # Multiple words (subspecies)
        assert len(build_taxonomy_keywords("Papilio glaucus glaucus")) > 0

        # With author citation (should strip)
        keywords = build_taxonomy_keywords("Actias luna (Linnaeus, 1758)")
        assert "taxonomy:species=Actias luna" in keywords

    def test_handles_none_notes(self, minimal_metadata):
        """Should handle None notes gracefully."""
        minimal_metadata.notes = None
        notes = format_observation_notes(minimal_metadata)
        assert isinstance(notes, str)

    def test_handles_empty_tags(self, minimal_metadata):
        """Should handle empty tags list gracefully."""
        minimal_metadata.tags = []
        notes = format_observation_notes(minimal_metadata)
        assert isinstance(notes, str)

    def test_handles_unicode_in_notes(self):
        """Should handle Unicode characters in notes."""
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            notes="Beautiful moth with unique patterns: 🦋",
            timestamp="2024-01-15T10:30:00",
            latitude=37.7749,
            longitude=-122.4194,
        )

        notes = format_observation_notes(metadata)
        assert "🦋" in notes

    def test_handles_special_characters_in_species(self):
        """Should handle special characters in species names."""
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            species="Actias-luna",  # Hyphen in name
            timestamp="2024-01-15T10:30:00",
            latitude=37.7749,
            longitude=-122.4194,
        )

        inat = transform_metadata_to_inaturalist(metadata)
        assert inat["species"] == "Actias-luna"

    def test_handles_species_with_only_parentheses(self):
        """Should handle species names that are only author citations."""
        # Edge case: species name is only author citation "(Linnaeus, 1758)"
        keywords = build_taxonomy_keywords("(Linnaeus, 1758)")
        assert keywords == []  # Should return empty after cleaning
