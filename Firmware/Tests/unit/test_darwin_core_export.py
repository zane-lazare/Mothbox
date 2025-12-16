"""
Unit tests for Darwin Core export functionality (Issue #116)

Tests the Darwin Core field mapping module and export service integration.

Coverage Target: 85%+
"""

import pytest

from webui.backend.lib.darwin_core_mapping import (
    CONFIDENCE_TO_QUALIFIER,
    DARWIN_CORE_CONSTANTS,
    DARWIN_CORE_CSV_COLUMN_ORDER,
    DARWIN_CORE_FIELD_MAPPINGS,
    DARWIN_CORE_RECOMMENDED_FIELDS,
    DARWIN_CORE_REQUIRED_FIELDS,
    DarwinCoreFieldMapping,
    generate_occurrence_id,
    get_csv_headers,
    is_valid_for_export,
    map_species_confidence_to_qualifier,
    transform_metadata_to_darwin_core,
    transform_to_csv_row,
)
from webui.backend.services.export_metadata_service import (
    ExportFormat,
    ExportMetadata,
    ExportMetadataService,
    ValidationResult,
)


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


@pytest.fixture
def export_service():
    """Create ExportMetadataService for testing."""
    return ExportMetadataService(cache_ttl=60)


# ============================================================================
# Tests for Darwin Core Constants
# ============================================================================


class TestDarwinCoreConstants:
    """Tests for Darwin Core constant definitions."""

    def test_required_fields_defined(self):
        """Required fields list should contain essential Darwin Core terms."""
        assert "occurrenceID" in DARWIN_CORE_REQUIRED_FIELDS
        assert "basisOfRecord" in DARWIN_CORE_REQUIRED_FIELDS
        assert "eventDate" in DARWIN_CORE_REQUIRED_FIELDS
        assert "decimalLatitude" in DARWIN_CORE_REQUIRED_FIELDS
        assert "decimalLongitude" in DARWIN_CORE_REQUIRED_FIELDS
        assert "geodeticDatum" in DARWIN_CORE_REQUIRED_FIELDS

    def test_recommended_fields_defined(self):
        """Recommended fields list should contain important Darwin Core terms."""
        assert "scientificName" in DARWIN_CORE_RECOMMENDED_FIELDS
        assert "recordedBy" in DARWIN_CORE_RECOMMENDED_FIELDS
        assert "occurrenceStatus" in DARWIN_CORE_RECOMMENDED_FIELDS

    def test_csv_column_order_includes_required(self):
        """CSV column order should include all required fields."""
        for field in DARWIN_CORE_REQUIRED_FIELDS:
            assert field in DARWIN_CORE_CSV_COLUMN_ORDER

    def test_constants_values(self):
        """Darwin Core constants should have correct values."""
        assert DARWIN_CORE_CONSTANTS["basisOfRecord"] == "MachineObservation"
        assert DARWIN_CORE_CONSTANTS["geodeticDatum"] == "WGS84"
        assert DARWIN_CORE_CONSTANTS["occurrenceStatus"] == "present"

    def test_confidence_mapping(self):
        """Confidence to qualifier mapping should be complete."""
        assert CONFIDENCE_TO_QUALIFIER["certain"] == ""
        assert CONFIDENCE_TO_QUALIFIER["probable"] == "cf."
        assert CONFIDENCE_TO_QUALIFIER["possible"] == "aff."
        assert CONFIDENCE_TO_QUALIFIER["unknown"] == "?"


# ============================================================================
# Tests for Field Mapping Configuration
# ============================================================================


class TestFieldMappingConfiguration:
    """Tests for DarwinCoreFieldMapping dataclass and mappings."""

    def test_field_mapping_dataclass(self):
        """DarwinCoreFieldMapping should store all required attributes."""
        mapping = DarwinCoreFieldMapping(
            dwc_term="testTerm",
            source_field="test_field",
            default_value="default",
            is_required=True,
            description="Test description"
        )
        assert mapping.dwc_term == "testTerm"
        assert mapping.source_field == "test_field"
        assert mapping.default_value == "default"
        assert mapping.is_required is True
        assert mapping.description == "Test description"

    def test_all_required_fields_mapped(self):
        """All required Darwin Core fields should have mappings."""
        mapped_terms = {m.dwc_term for m in DARWIN_CORE_FIELD_MAPPINGS}
        for field in DARWIN_CORE_REQUIRED_FIELDS:
            assert field in mapped_terms, f"Missing mapping for {field}"

    def test_required_field_mappings_flagged(self):
        """Mappings for required fields should have is_required=True."""
        for mapping in DARWIN_CORE_FIELD_MAPPINGS:
            if mapping.dwc_term in DARWIN_CORE_REQUIRED_FIELDS:
                assert mapping.is_required is True, f"{mapping.dwc_term} should be required"


# ============================================================================
# Tests for Occurrence ID Generation
# ============================================================================


class TestOccurrenceIdGeneration:
    """Tests for generate_occurrence_id() function."""

    def test_occurrence_id_format(self, sample_metadata):
        """Occurrence ID should follow mothbox:{deployment}:{hash} format."""
        occ_id = generate_occurrence_id(sample_metadata)
        assert occ_id.startswith("mothbox:")
        parts = occ_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "mothbox"

    def test_occurrence_id_deterministic(self, sample_metadata):
        """Same metadata should generate same occurrence ID."""
        id1 = generate_occurrence_id(sample_metadata)
        id2 = generate_occurrence_id(sample_metadata)
        assert id1 == id2

    def test_occurrence_id_unique_per_photo(self, sample_metadata):
        """Different photos should have different occurrence IDs."""
        id1 = generate_occurrence_id(sample_metadata)

        # Create a copy with different filename
        other_metadata = ExportMetadata(
            photo_path="/photos/other.jpg",
            filename="other.jpg",
            deployment_name=sample_metadata.deployment_name,
        )
        id2 = generate_occurrence_id(other_metadata)

        assert id1 != id2

    def test_occurrence_id_without_deployment(self):
        """Occurrence ID should handle missing deployment name."""
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            deployment_name=None,
        )
        occ_id = generate_occurrence_id(metadata)
        assert "unknown" in occ_id

    def test_occurrence_id_sanitizes_deployment_name(self):
        """Occurrence ID should sanitize deployment name."""
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            deployment_name="Oak Ridge 2024 (Summer)",
        )
        occ_id = generate_occurrence_id(metadata)
        # Should not contain spaces or parentheses
        assert " " not in occ_id
        assert "(" not in occ_id
        assert ")" not in occ_id


# ============================================================================
# Tests for Species Confidence Mapping
# ============================================================================


class TestSpeciesConfidenceMapping:
    """Tests for map_species_confidence_to_qualifier() function."""

    def test_certain_maps_to_empty(self):
        """Certain confidence should map to empty qualifier."""
        assert map_species_confidence_to_qualifier("certain") == ""

    def test_probable_maps_to_cf(self):
        """Probable confidence should map to 'cf.' qualifier."""
        assert map_species_confidence_to_qualifier("probable") == "cf."

    def test_possible_maps_to_aff(self):
        """Possible confidence should map to 'aff.' qualifier."""
        assert map_species_confidence_to_qualifier("possible") == "aff."

    def test_unknown_maps_to_question(self):
        """Unknown confidence should map to '?' qualifier."""
        assert map_species_confidence_to_qualifier("unknown") == "?"

    def test_none_returns_empty(self):
        """None confidence should return empty string."""
        assert map_species_confidence_to_qualifier(None) == ""

    def test_case_insensitive(self):
        """Mapping should be case insensitive."""
        assert map_species_confidence_to_qualifier("CERTAIN") == ""
        assert map_species_confidence_to_qualifier("Probable") == "cf."

    def test_invalid_returns_empty(self):
        """Invalid confidence values should return empty string."""
        assert map_species_confidence_to_qualifier("invalid") == ""


# ============================================================================
# Tests for CSV Headers
# ============================================================================


class TestCsvHeaders:
    """Tests for get_csv_headers() function."""

    def test_returns_list(self):
        """get_csv_headers() should return a list."""
        headers = get_csv_headers()
        assert isinstance(headers, list)

    def test_headers_match_column_order(self):
        """Headers should match DARWIN_CORE_CSV_COLUMN_ORDER."""
        headers = get_csv_headers()
        assert headers == DARWIN_CORE_CSV_COLUMN_ORDER

    def test_headers_is_copy(self):
        """get_csv_headers() should return a copy, not the original."""
        headers = get_csv_headers()
        headers.append("test")
        assert "test" not in get_csv_headers()

    def test_required_fields_first(self):
        """Required fields should appear first in headers."""
        headers = get_csv_headers()
        for i, field in enumerate(DARWIN_CORE_REQUIRED_FIELDS):
            assert field in headers[:10], f"Required field {field} not in first 10 headers"


# ============================================================================
# Tests for Metadata Transformation
# ============================================================================


class TestMetadataTransformation:
    """Tests for transform_metadata_to_darwin_core() function."""

    def test_transforms_complete_metadata(self, sample_metadata):
        """Complete metadata should transform to Darwin Core dict."""
        dwc = transform_metadata_to_darwin_core(sample_metadata)

        assert isinstance(dwc, dict)
        assert dwc["basisOfRecord"] == "MachineObservation"
        assert dwc["eventDate"] == "2024-01-15T10:30:00"
        assert dwc["decimalLatitude"] == 37.7749
        assert dwc["decimalLongitude"] == -122.4194
        assert dwc["geodeticDatum"] == "WGS84"
        assert dwc["scientificName"] == "Actias luna"
        assert dwc["vernacularName"] == "Luna Moth"
        assert dwc["coordinateUncertaintyInMeters"] == 2.5

    def test_transforms_minimal_metadata(self, minimal_metadata):
        """Minimal metadata should still produce valid Darwin Core dict."""
        dwc = transform_metadata_to_darwin_core(minimal_metadata)

        assert dwc["eventDate"] == "2024-01-15T10:30:00"
        assert dwc["decimalLatitude"] == 37.7749
        assert dwc["decimalLongitude"] == -122.4194
        assert dwc["basisOfRecord"] == "MachineObservation"
        assert dwc["geodeticDatum"] == "WGS84"

    def test_null_values_use_defaults(self, minimal_metadata):
        """Null source values should use default values."""
        dwc = transform_metadata_to_darwin_core(minimal_metadata)

        # scientificName defaults to empty string
        assert dwc["scientificName"] == ""
        assert dwc["vernacularName"] == ""

    def test_occurrence_id_generated(self, sample_metadata):
        """Occurrence ID should be generated automatically."""
        dwc = transform_metadata_to_darwin_core(sample_metadata)
        assert "occurrenceID" in dwc
        assert dwc["occurrenceID"].startswith("mothbox:")

    def test_confidence_transformed(self, sample_metadata):
        """Species confidence should be transformed to qualifier."""
        dwc = transform_metadata_to_darwin_core(sample_metadata)
        # "certain" -> ""
        assert dwc["identificationQualifier"] == ""

        # Test with probable confidence
        sample_metadata.species_confidence = "probable"
        dwc = transform_metadata_to_darwin_core(sample_metadata)
        assert dwc["identificationQualifier"] == "cf."

    def test_all_csv_columns_present(self, sample_metadata):
        """Transformed dict should have all CSV column keys."""
        dwc = transform_metadata_to_darwin_core(sample_metadata)
        for column in DARWIN_CORE_CSV_COLUMN_ORDER:
            assert column in dwc, f"Missing column: {column}"

    def test_transform_without_deployment_uses_photo_gps(self):
        """Darwin Core export should use photo GPS even without deployment.

        This test verifies Issue #200 - GPS coordinates come from photo EXIF,
        not deployment metadata. Darwin Core export works correctly when
        deployment is None.
        """
        # Create metadata with GPS from EXIF but no deployment
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            timestamp="2024-01-15T10:30:00",
            latitude=35.9606,  # From photo EXIF
            longitude=-83.9207,  # From photo EXIF
            altitude=350.5,
            gps_accuracy=2.5,
            # No deployment fields
            deployment_name=None,
            deployment_location_name=None,
            deployment_start_date=None,
            deployment_end_date=None,
        )

        dwc = transform_metadata_to_darwin_core(metadata)

        # GPS coordinates should be present from photo EXIF
        assert dwc["decimalLatitude"] == 35.9606
        assert dwc["decimalLongitude"] == -83.9207
        assert dwc["coordinateUncertaintyInMeters"] == 2.5

        # Deployment-related fields should use defaults
        assert dwc["collectionCode"] == ""  # deployment_name -> collectionCode
        assert dwc["occurrenceID"] == generate_occurrence_id(metadata)
        assert "unknown" in dwc["occurrenceID"]  # Uses "unknown" when no deployment

        # Should still be valid for export (has GPS)
        assert is_valid_for_export(metadata) is True

    def test_transform_with_deployment_still_uses_photo_gps(self):
        """GPS coordinates should come from photo EXIF even when deployment exists.

        This verifies that deployment metadata does NOT override GPS coordinates
        from the photo. Both can coexist.
        """
        # Create metadata with GPS from EXIF AND deployment metadata
        metadata = ExportMetadata(
            photo_path="/photos/test.jpg",
            filename="test.jpg",
            timestamp="2024-01-15T10:30:00",
            latitude=35.9606,  # From photo EXIF
            longitude=-83.9207,  # From photo EXIF
            altitude=350.5,
            # Deployment provides location name, but NOT GPS override
            deployment_name="oak-ridge-2024",
            deployment_location_name="Oak Ridge, TN, USA",
        )

        dwc = transform_metadata_to_darwin_core(metadata)

        # GPS coordinates should be from photo EXIF
        assert dwc["decimalLatitude"] == 35.9606
        assert dwc["decimalLongitude"] == -83.9207

        # Deployment name should be in collectionCode
        assert dwc["collectionCode"] == "oak-ridge-2024"


# ============================================================================
# Tests for CSV Row Transformation
# ============================================================================


class TestCsvRowTransformation:
    """Tests for transform_to_csv_row() function."""

    def test_returns_list(self, sample_metadata):
        """transform_to_csv_row() should return a list."""
        row = transform_to_csv_row(sample_metadata)
        assert isinstance(row, list)

    def test_row_matches_headers_length(self, sample_metadata):
        """Row should have same length as headers."""
        headers = get_csv_headers()
        row = transform_to_csv_row(sample_metadata)
        assert len(row) == len(headers)

    def test_all_values_are_strings(self, sample_metadata):
        """All row values should be strings."""
        row = transform_to_csv_row(sample_metadata)
        for value in row:
            assert isinstance(value, str), f"Non-string value: {value} ({type(value)})"

    def test_none_converts_to_empty(self, minimal_metadata):
        """None values should convert to empty strings."""
        row = transform_to_csv_row(minimal_metadata)
        # Check that there are no "None" strings
        assert "None" not in row


# ============================================================================
# Tests for Export Validity Check
# ============================================================================


class TestExportValidityCheck:
    """Tests for is_valid_for_export() function."""

    def test_valid_with_gps(self, sample_metadata):
        """Metadata with valid GPS should be valid for export."""
        assert is_valid_for_export(sample_metadata) is True

    def test_invalid_without_latitude(self, metadata_without_gps):
        """Metadata without latitude should be invalid."""
        assert is_valid_for_export(metadata_without_gps) is False

    def test_invalid_without_longitude(self, sample_metadata):
        """Metadata without longitude should be invalid."""
        sample_metadata.longitude = None
        assert is_valid_for_export(sample_metadata) is False

    def test_invalid_latitude_range(self, sample_metadata):
        """Latitude outside valid range should be invalid."""
        sample_metadata.latitude = 91.0
        assert is_valid_for_export(sample_metadata) is False

        sample_metadata.latitude = -91.0
        assert is_valid_for_export(sample_metadata) is False

    def test_invalid_longitude_range(self, sample_metadata):
        """Longitude outside valid range should be invalid."""
        sample_metadata.longitude = 181.0
        assert is_valid_for_export(sample_metadata) is False

        sample_metadata.longitude = -181.0
        assert is_valid_for_export(sample_metadata) is False

    def test_valid_at_boundaries(self, sample_metadata):
        """Coordinates at boundaries should be valid."""
        sample_metadata.latitude = 90.0
        sample_metadata.longitude = 180.0
        assert is_valid_for_export(sample_metadata) is True

        sample_metadata.latitude = -90.0
        sample_metadata.longitude = -180.0
        assert is_valid_for_export(sample_metadata) is True


# ============================================================================
# Tests for ExportMetadataService Darwin Core Integration
# ============================================================================


class TestExportServiceDarwinCore:
    """Tests for ExportMetadataService Darwin Core methods."""

    def test_transform_to_darwin_core(self, export_service, sample_metadata):
        """Service should transform metadata to Darwin Core format."""
        dwc = export_service.transform_to_darwin_core(sample_metadata)

        assert isinstance(dwc, dict)
        assert dwc["basisOfRecord"] == "MachineObservation"
        assert dwc["geodeticDatum"] == "WGS84"

    def test_batch_transform_filters_invalid(self, export_service, sample_metadata, metadata_without_gps):
        """Batch transform should filter invalid metadata by default."""
        metadata_list = [sample_metadata, metadata_without_gps]

        headers, rows = export_service.transform_batch_to_darwin_core_csv(
            metadata_list,
            filter_invalid=True
        )

        # Only valid metadata should be included
        assert len(rows) == 1

    def test_batch_transform_includes_invalid(self, export_service, sample_metadata, metadata_without_gps):
        """Batch transform can include invalid metadata when filter=False."""
        metadata_list = [sample_metadata, metadata_without_gps]

        headers, rows = export_service.transform_batch_to_darwin_core_csv(
            metadata_list,
            filter_invalid=False
        )

        # Both should be included
        assert len(rows) == 2

    def test_batch_transform_returns_headers(self, export_service, sample_metadata):
        """Batch transform should return correct headers."""
        headers, rows = export_service.transform_batch_to_darwin_core_csv([sample_metadata])

        assert headers == DARWIN_CORE_CSV_COLUMN_ORDER


# ============================================================================
# Tests for Darwin Core Validation
# ============================================================================


class TestDarwinCoreValidation:
    """Tests for Darwin Core validation in ExportMetadataService."""

    def test_valid_metadata_passes(self, export_service, sample_metadata):
        """Complete metadata should pass validation."""
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is True
        assert len(result.missing_fields) == 0

    def test_missing_latitude_fails(self, export_service, sample_metadata):
        """Missing latitude should fail validation."""
        sample_metadata.latitude = None
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert any("latitude" in f.lower() for f in result.missing_fields)

    def test_missing_longitude_fails(self, export_service, sample_metadata):
        """Missing longitude should fail validation."""
        sample_metadata.longitude = None
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert any("longitude" in f.lower() for f in result.missing_fields)

    def test_invalid_latitude_range_fails(self, export_service, sample_metadata):
        """Invalid latitude range should fail validation."""
        sample_metadata.latitude = 95.0
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert any("latitude" in f.lower() and "range" in f.lower() for f in result.missing_fields)

    def test_invalid_longitude_range_fails(self, export_service, sample_metadata):
        """Invalid longitude range should fail validation."""
        sample_metadata.longitude = 200.0
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert any("longitude" in f.lower() and "range" in f.lower() for f in result.missing_fields)

    def test_missing_timestamp_fails(self, export_service, sample_metadata):
        """Missing timestamp should fail validation."""
        sample_metadata.timestamp = None
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert any("eventdate" in f.lower() or "timestamp" in f.lower() for f in result.missing_fields)

    def test_warning_for_missing_species(self, export_service, minimal_metadata):
        """Missing species should generate warning."""
        result = export_service.validate_for_format(minimal_metadata, ExportFormat.DARWIN_CORE)

        # Should be valid (species not required) but have warning
        assert result.is_valid is True
        assert any("scientificName" in w for w in result.warnings)

    def test_warning_for_missing_gps_accuracy(self, export_service, sample_metadata):
        """Missing GPS accuracy should generate warning."""
        sample_metadata.gps_accuracy = None
        result = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is True
        assert any("coordinateUncertaintyInMeters" in w for w in result.warnings)


# ============================================================================
# Integration Tests
# ============================================================================


class TestDarwinCoreIntegration:
    """Integration tests for Darwin Core export workflow."""

    def test_full_export_workflow(self, export_service, sample_metadata):
        """Test complete export workflow: validate -> transform -> CSV row."""
        # Validate
        validation = export_service.validate_for_format(sample_metadata, ExportFormat.DARWIN_CORE)
        assert validation.is_valid is True

        # Transform
        dwc = export_service.transform_to_darwin_core(sample_metadata)
        assert "occurrenceID" in dwc

        # CSV row
        row = transform_to_csv_row(sample_metadata)
        assert len(row) == len(get_csv_headers())

    def test_batch_export_workflow(self, export_service, sample_metadata, minimal_metadata):
        """Test batch export workflow."""
        metadata_list = [sample_metadata, minimal_metadata]

        headers, rows = export_service.transform_batch_to_darwin_core_csv(metadata_list)

        assert len(headers) == len(DARWIN_CORE_CSV_COLUMN_ORDER)
        assert len(rows) == 2
        assert all(len(row) == len(headers) for row in rows)

    def test_gbif_strict_mode_excludes_invalid(self, export_service, sample_metadata, metadata_without_gps):
        """GBIF strict mode should exclude photos without GPS."""
        metadata_list = [sample_metadata, metadata_without_gps]

        # With filtering (GBIF strict mode)
        headers, rows = export_service.transform_batch_to_darwin_core_csv(
            metadata_list,
            filter_invalid=True
        )

        assert len(rows) == 1  # Only valid photo included


# ============================================================================
# Tests for Country Code in Darwin Core
# ============================================================================


class TestCountryCodeInDarwinCore:
    """Tests for countryCode field in Darwin Core export."""

    def test_country_code_mapped_to_darwin_core(self, sample_metadata):
        """countryCode should be mapped from ExportMetadata.country_code."""
        sample_metadata.country_code = "US"
        dwc = transform_metadata_to_darwin_core(sample_metadata)

        assert "countryCode" in dwc
        assert dwc["countryCode"] == "US"

    def test_country_code_empty_when_none(self, minimal_metadata):
        """countryCode should be empty string when country_code is None."""
        minimal_metadata.country_code = None
        dwc = transform_metadata_to_darwin_core(minimal_metadata)

        assert dwc["countryCode"] == ""

    def test_country_code_in_csv_row(self, sample_metadata):
        """countryCode should appear in CSV row."""
        sample_metadata.country_code = "GB"
        headers = get_csv_headers()
        row = transform_to_csv_row(sample_metadata)

        country_idx = headers.index("countryCode")
        assert row[country_idx] == "GB"

    def test_country_code_in_csv_column_order(self):
        """countryCode should be in CSV column order."""
        assert "countryCode" in DARWIN_CORE_CSV_COLUMN_ORDER

    def test_country_code_is_recommended_field(self):
        """countryCode should be in recommended fields list."""
        assert "countryCode" in DARWIN_CORE_RECOMMENDED_FIELDS

    def test_country_code_mapping_exists(self):
        """countryCode should have a field mapping configured."""
        mapping = None
        for m in DARWIN_CORE_FIELD_MAPPINGS:
            if m.dwc_term == "countryCode":
                mapping = m
                break

        assert mapping is not None
        assert mapping.source_field == "country_code"
        assert mapping.is_required is False
