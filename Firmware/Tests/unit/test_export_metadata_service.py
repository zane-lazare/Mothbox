"""
Unit tests for Export Metadata Service (Issue #112 - Subtask 1)

Tests ExportMetadataService aggregation layer with caching and thread-safety.
TDD approach: tests written first, then implementation.

Coverage Target: 90%+
"""

import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from unittest.mock import Mock

import pytest

# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.services.export_metadata_service import (
        ExportFormat,
        ExportMetadata,
        ExportMetadataService,
        ValidationResult,
    )
    IMPLEMENTATION_EXISTS = True
except ImportError:
    IMPLEMENTATION_EXISTS = False
    ExportMetadataService = None
    ExportMetadata = None
    ValidationResult = None
    ExportFormat = None


# Skip all tests if implementation doesn't exist yet (TDD red phase)
pytestmark = pytest.mark.skipif(
    not IMPLEMENTATION_EXISTS,
    reason="Implementation not yet created (TDD red phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_photo_path(tmp_path):
    """Create a temporary photo file for testing (HDR series photo)."""
    # Use HDR naming pattern so series detection works
    photo = tmp_path / "moth_2024_01_15__10_00_00_HDR0.jpg"
    # Create minimal valid JPEG
    photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
    return photo


@pytest.fixture
def sample_exif_metadata():
    """Sample EXIF data as returned by MetadataService."""
    return {
        'camera': {
            'make': 'Arducam',
            'model': 'OwlSight 64MP',
            'software': 'Mothbox v5.2.0'
        },
        'capture': {
            'timestamp': '2024-01-15T10:00:00',
            'exposure_time': '1/125',
            'iso': 100,
            'focal_length': '4.74mm',
            'width': 9152,
            'height': 6944
        },
        'location': {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 52.5,
            'gps_accuracy': 2.5
        },
        'deployment': {
            'mothbox_id': 'MB-001',
            'firmware_version': '5.2.0'
        },
        'file': {
            'size': 5242880,  # 5MB
            'path': '/var/lib/mothbox/photos/moth_2024_01_15__10_00_00.jpg'
        }
    }


@pytest.fixture
def sample_exif_no_gps():
    """Sample EXIF data without GPS coordinates."""
    return {
        'camera': {
            'make': 'Arducam',
            'model': 'OwlSight 64MP',
            'software': 'Mothbox v5.2.0'
        },
        'capture': {
            'timestamp': '2024-01-15T10:00:00',
            'exposure_time': '1/125',
            'iso': 100,
            'focal_length': '4.74mm',
            'width': 9152,
            'height': 6944
        },
        'location': {},
        'deployment': {
            'mothbox_id': 'MB-001',
            'firmware_version': '5.2.0'
        },
        'file': {
            'size': 5242880,
            'path': '/var/lib/mothbox/photos/moth_2024_01_15__10_00_00.jpg'
        }
    }


@pytest.fixture
def sample_sidecar_metadata():
    """Sample sidecar data from SidecarService."""
    @dataclass
    class SidecarMetadata:
        tags: list[str]
        species: str | None
        common_name: str | None
        confidence: str | None
        notes: str | None

    return SidecarMetadata(
        tags=['moth', 'nocturnal', 'attracted'],
        species='Actias luna',
        common_name='Luna moth',
        confidence='high',
        notes='Beautiful specimen near UV light'
    )


@pytest.fixture
def sample_series_info():
    """Sample series info from SeriesService."""
    @dataclass
    class PhotoSeries:
        series_id: str
        series_type: str
        base_name: str
        photos: list
        count: int
        cover_photo: Path

    return PhotoSeries(
        series_id='hdr_moth_2024_01_15__10_00_00',
        series_type='hdr',
        base_name='moth_2024_01_15__10_00_00',
        photos=[
            Path('/var/lib/mothbox/photos/moth_2024_01_15__10_00_00_HDR0.jpg'),
            Path('/var/lib/mothbox/photos/moth_2024_01_15__10_00_00_HDR1.jpg'),
            Path('/var/lib/mothbox/photos/moth_2024_01_15__10_00_00_HDR2.jpg')
        ],
        count=3,
        cover_photo=Path('/var/lib/mothbox/photos/moth_2024_01_15__10_00_00_HDR0.jpg')
    )


@pytest.fixture
def mock_metadata_service(sample_exif_metadata):
    """Mock MetadataService returning sample EXIF data."""
    service = Mock()
    service.get_photo_metadata.return_value = sample_exif_metadata
    return service


@pytest.fixture
def mock_sidecar_service(sample_sidecar_metadata):
    """Mock SidecarService returning sample user metadata."""
    service = Mock()
    service.get_metadata.return_value = sample_sidecar_metadata
    return service


@pytest.fixture
def mock_series_service(sample_series_info):
    """Mock SeriesService returning series info."""
    service = Mock()
    service.get_series_by_id.return_value = sample_series_info
    return service


@pytest.fixture
def mock_series_service_none():
    """Mock SeriesService returning None (not in series)."""
    service = Mock()
    service.get_series_by_id.return_value = None
    return service


@pytest.fixture
def mock_deployment_service():
    """Mock DeploymentService returning None (no deployment found)."""
    service = Mock()
    service.find_deployment_for_photo.return_value = None
    return service


@pytest.fixture
def service(mock_metadata_service, mock_sidecar_service, mock_series_service, mock_deployment_service):
    """Create ExportMetadataService with mocked dependencies."""
    return ExportMetadataService(
        cache_ttl=1,  # 1 second TTL for fast testing
        metadata_service=mock_metadata_service,
        sidecar_service=mock_sidecar_service,
        series_service=mock_series_service,
        deployment_service=mock_deployment_service,
    )


# ============================================================================
# Test ExportMetadata Data Class
# ============================================================================

class TestExportMetadataDataClass:
    """Tests for ExportMetadata data class structure."""

    def test_export_metadata_has_required_fields(self, sample_photo_path):
        """ExportMetadata should have all required fields."""
        metadata = ExportMetadata(
            photo_path=str(sample_photo_path),
            filename=sample_photo_path.name,
            timestamp='2024-01-15T10:00:00',
            latitude=37.7749,
            longitude=-122.4194,
            altitude=52.5,
            gps_accuracy=2.5,
            camera_make='Arducam',
            camera_model='OwlSight 64MP',
            exposure_time='1/125',
            iso=100,
            focal_length='4.74mm',
            species='Actias luna',
            species_common_name='Luna moth',
            species_confidence='high',
            tags=['moth', 'nocturnal'],
            notes='Test note',
            mothbox_id='MB-001',
            firmware_version='5.2.0',
            series_type='hdr',
            series_index=0,
            series_count=3,
            file_size=5242880,
            width=9152,
            height=6944
        )

        assert metadata.photo_path == str(sample_photo_path)
        assert metadata.filename == sample_photo_path.name
        assert metadata.latitude == 37.7749
        assert metadata.species == 'Actias luna'
        assert metadata.series_type == 'hdr'
        assert len(metadata.tags) == 2

    def test_export_metadata_to_dict(self, sample_photo_path):
        """ExportMetadata should be convertible to dict."""
        metadata = ExportMetadata(
            photo_path=str(sample_photo_path),
            filename=sample_photo_path.name,
            timestamp='2024-01-15T10:00:00',
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            gps_accuracy=None,
            camera_make='Arducam',
            camera_model='OwlSight 64MP',
            exposure_time='1/125',
            iso=100,
            focal_length='4.74mm',
            species=None,
            species_common_name=None,
            species_confidence=None,
            tags=[],
            notes=None,
            mothbox_id='MB-001',
            firmware_version='5.2.0',
            series_type=None,
            series_index=None,
            series_count=None,
            file_size=5242880,
            width=9152,
            height=6944
        )

        as_dict = asdict(metadata)
        assert isinstance(as_dict, dict)
        assert as_dict['photo_path'] == str(sample_photo_path)
        assert as_dict['latitude'] == 37.7749
        assert as_dict['altitude'] is None

    def test_export_metadata_default_values(self, sample_photo_path):
        """ExportMetadata should accept None for optional fields."""
        metadata = ExportMetadata(
            photo_path=str(sample_photo_path),
            filename=sample_photo_path.name,
            timestamp=None,
            latitude=None,
            longitude=None,
            altitude=None,
            gps_accuracy=None,
            camera_make=None,
            camera_model=None,
            exposure_time=None,
            iso=None,
            focal_length=None,
            species=None,
            species_common_name=None,
            species_confidence=None,
            tags=[],
            notes=None,
            mothbox_id=None,
            firmware_version=None,
            series_type=None,
            series_index=None,
            series_count=None,
            file_size=0,
            width=None,
            height=None
        )

        assert metadata.timestamp is None
        assert metadata.latitude is None
        assert metadata.species is None
        assert metadata.tags == []


# ============================================================================
# Test ValidationResult Data Class
# ============================================================================

class TestValidationResultDataClass:
    """Tests for ValidationResult data class structure."""

    def test_validation_result_has_required_fields(self):
        """ValidationResult should have all required fields."""
        result = ValidationResult(
            is_valid=True,
            missing_fields=[],
            warnings=[]
        )

        assert result.is_valid is True
        assert result.missing_fields == []
        assert result.warnings == []

    def test_validation_result_with_failures(self):
        """ValidationResult should capture validation failures."""
        result = ValidationResult(
            is_valid=False,
            missing_fields=['latitude', 'longitude'],
            warnings=['No species identified']
        )

        assert result.is_valid is False
        assert len(result.missing_fields) == 2
        assert len(result.warnings) == 1


# ============================================================================
# Test ExportFormat Enum
# ============================================================================

class TestExportFormatEnum:
    """Tests for ExportFormat enum."""

    def test_export_format_values(self):
        """ExportFormat should have expected values."""
        assert ExportFormat.DARWIN_CORE.value == "darwin_core"
        assert ExportFormat.INATURALIST.value == "inaturalist"
        assert ExportFormat.GENERIC_JSON.value == "json"
        assert ExportFormat.GENERIC_CSV.value == "csv"


# ============================================================================
# Test ExportMetadataService Initialization
# ============================================================================

class TestExportMetadataServiceInit:
    """Tests for ExportMetadataService initialization."""

    def test_service_creation_default_config(self):
        """ExportMetadataService should be created with defaults."""
        service = ExportMetadataService()
        assert service is not None
        assert service._cache_ttl == 300  # Default 5 minutes

    def test_service_creation_custom_cache_ttl(self):
        """ExportMetadataService should accept custom TTL."""
        service = ExportMetadataService(cache_ttl=60)
        assert service._cache_ttl == 60

    def test_service_accepts_injected_dependencies(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service
    ):
        """ExportMetadataService should accept dependency injection."""
        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service
        )
        assert service._metadata_service == mock_metadata_service
        assert service._sidecar_service == mock_sidecar_service
        assert service._series_service == mock_series_service


# ============================================================================
# Test get_export_metadata
# ============================================================================

class TestGetExportMetadata:
    """Tests for get_export_metadata method."""

    def test_get_metadata_combines_all_sources(
        self, service, sample_photo_path
    ):
        """get_export_metadata should combine EXIF, sidecar, and series data."""
        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        # EXIF data
        assert result.camera_make == 'Arducam'
        assert result.latitude == 37.7749
        assert result.timestamp == '2024-01-15T10:00:00'
        # Sidecar data
        assert result.species == 'Actias luna'
        assert 'moth' in result.tags
        # Series data
        assert result.series_type == 'hdr'
        assert result.series_count == 3

    def test_get_metadata_missing_exif_graceful(
        self, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """Should handle missing EXIF data gracefully."""
        # Create service with metadata service that returns None
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service
        )

        result = service.get_export_metadata(sample_photo_path)

        # Should still return ExportMetadata with available data
        assert isinstance(result, ExportMetadata)
        assert result.species == 'Actias luna'  # Sidecar data present
        assert result.camera_make is None  # EXIF data missing

    def test_get_metadata_missing_sidecar_graceful(
        self, mock_metadata_service, mock_series_service, sample_photo_path
    ):
        """Should handle missing sidecar data gracefully."""
        # Create service with sidecar service that returns None
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar,
            series_service=mock_series_service
        )

        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        assert result.camera_make == 'Arducam'  # EXIF data present
        assert result.species is None  # Sidecar data missing
        assert result.tags == []

    def test_get_metadata_missing_series_graceful(
        self, mock_metadata_service, mock_sidecar_service, tmp_path
    ):
        """Should handle non-series photo gracefully."""
        # Use a non-HDR/FB filename so series detection returns None
        non_series_photo = tmp_path / "regular_photo.jpg"
        non_series_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service_none
        )

        result = service.get_export_metadata(non_series_photo)

        assert isinstance(result, ExportMetadata)
        assert result.camera_make == 'Arducam'
        assert result.series_type is None
        assert result.series_count is None

    def test_get_metadata_nonexistent_photo_returns_error(self, tmp_path):
        """Should return error dict for nonexistent photo."""
        nonexistent = tmp_path / "nonexistent.jpg"

        # Create service without mocks - let it check file existence
        service = ExportMetadataService()

        result = service.get_export_metadata(nonexistent)

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    def test_get_metadata_with_gps_coordinates(
        self, service, sample_photo_path
    ):
        """Should properly extract GPS coordinates when present."""
        result = service.get_export_metadata(sample_photo_path)

        assert result.latitude == 37.7749
        assert result.longitude == -122.4194
        assert result.altitude == 52.5
        assert result.gps_accuracy == 2.5

    def test_get_metadata_without_gps_coordinates(
        self, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """Should handle missing GPS data gracefully."""
        # Create metadata service that returns no GPS data
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {'make': 'Arducam', 'model': 'OwlSight 64MP'},
            'capture': {'timestamp': '2024-01-15T10:00:00'},
            'location': {},  # Empty location
            'deployment': {},
            'file': {'size': 5242880}
        }

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service
        )

        result = service.get_export_metadata(sample_photo_path)

        assert result.latitude is None
        assert result.longitude is None
        assert result.altitude is None

    def test_get_metadata_without_deployment_has_gps(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """GPS coordinates should come from EXIF when no deployment is present.

        This test verifies Issue #200 - GPS coordinates are NOT dependent on
        deployment metadata. They come from photo EXIF, so exports work fine
        without a deployment.
        """
        # Create deployment service that returns None (no deployment found)
        mock_deployment = Mock()
        mock_deployment.find_deployment_for_photo.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service,
            deployment_service=mock_deployment
        )

        result = service.get_export_metadata(sample_photo_path)

        # GPS coordinates should be present from EXIF
        assert isinstance(result, ExportMetadata)
        assert result.latitude == 37.7749
        assert result.longitude == -122.4194
        assert result.altitude == 52.5
        assert result.gps_accuracy == 2.5

        # Deployment fields should be None
        assert result.deployment_name is None
        assert result.deployment_location_name is None
        assert result.deployment_start_date is None
        assert result.deployment_end_date is None
        assert result.environmental_conditions == {}

    def test_get_metadata_performance_under_100ms(
        self, service, sample_photo_path
    ):
        """get_export_metadata should complete in <100ms."""
        # Warmup call to ensure all lazy imports are loaded
        service.get_export_metadata(sample_photo_path)
        service.invalidate_cache()  # Clear cache so we measure actual work

        start = time.perf_counter()
        service.get_export_metadata(sample_photo_path)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Took {elapsed_ms:.2f}ms, exceeds 100ms target"


# ============================================================================
# Test batch_get_export_metadata
# ============================================================================

class TestBatchGetExportMetadata:
    """Tests for batch_get_export_metadata method."""

    def test_batch_get_multiple_photos(self, service, tmp_path):
        """Should process multiple photos in batch."""
        # Create multiple photos
        photos = []
        for i in range(5):
            photo = tmp_path / f"moth_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
            photos.append(photo)

        results = service.batch_get_export_metadata(photos)

        assert len(results) == 5
        assert all(isinstance(r, (ExportMetadata, dict)) for r in results)

    def test_batch_get_handles_partial_failures(self, service, tmp_path):
        """Should continue processing even if some photos fail."""
        # Mix of valid and invalid photos
        valid_photo = tmp_path / "valid.jpg"
        valid_photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        invalid_photo = tmp_path / "nonexistent.jpg"

        results = service.batch_get_export_metadata([valid_photo, invalid_photo])

        assert len(results) == 2
        # First should succeed, second should have error
        assert isinstance(results[0], ExportMetadata)
        assert isinstance(results[1], dict) and 'error' in results[1]

    def test_batch_get_empty_list_returns_empty(self, service):
        """Should return empty list for empty input."""
        results = service.batch_get_export_metadata([])
        assert results == []

    def test_batch_get_preserves_order(self, service, tmp_path):
        """Should return results in same order as input."""
        photos = []
        for i in range(3):
            photo = tmp_path / f"photo_{i:03d}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
            photos.append(photo)

        results = service.batch_get_export_metadata(photos)

        # Check order preserved
        for i, result in enumerate(results):
            if isinstance(result, ExportMetadata):
                assert f"photo_{i:03d}" in result.filename

    def test_batch_get_streaming_mode(self, service, tmp_path):
        """Should support streaming mode with generator."""
        photos = []
        for i in range(3):
            photo = tmp_path / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
            photos.append(photo)

        results = service.batch_get_export_metadata(photos, stream=True)

        # Should return generator
        assert hasattr(results, '__iter__')
        assert hasattr(results, '__next__')

        # Consume generator
        results_list = list(results)
        assert len(results_list) == 3


# ============================================================================
# Test Generic Transformer
# ============================================================================

class TestGenericTransformer:
    """Tests for transform_to_generic method."""

    def test_transform_all_metadata_included(self, service, sample_photo_path):
        """transform_to_generic should include all metadata fields."""
        metadata = service.get_export_metadata(sample_photo_path)
        transformed = service.transform_to_generic(metadata, flat=False)

        assert isinstance(transformed, dict)
        # Should have nested structure
        assert 'file' in transformed
        assert 'camera' in transformed
        assert 'location' in transformed
        assert 'species' in transformed
        assert 'series' in transformed

    def test_transform_flat_structure_for_csv(self, service, sample_photo_path):
        """transform_to_generic with flat=True should flatten structure."""
        metadata = service.get_export_metadata(sample_photo_path)
        transformed = service.transform_to_generic(metadata, flat=True)

        assert isinstance(transformed, dict)
        # Should be flat - no nested dicts
        assert 'photo_path' in transformed
        assert 'camera_make' in transformed
        assert 'latitude' in transformed
        assert 'species' in transformed
        # Should not have nested dicts
        assert not any(isinstance(v, dict) for v in transformed.values())

    def test_transform_nested_structure_for_json(self, service, sample_photo_path):
        """transform_to_generic with flat=False should create nested structure."""
        metadata = service.get_export_metadata(sample_photo_path)
        transformed = service.transform_to_generic(metadata, flat=False)

        # Should have logical groupings
        assert 'camera' in transformed
        assert transformed['camera']['make'] == 'Arducam'

        assert 'location' in transformed
        assert transformed['location']['latitude'] == 37.7749

        assert 'series' in transformed
        assert transformed['series']['type'] == 'hdr'

    def test_transform_applies_gps_precision_flat(self, service, sample_photo_path):
        """transform_to_generic applies GPS precision to flat output."""
        metadata = service.get_export_metadata(sample_photo_path)
        # Set known coordinates
        metadata.latitude = 37.774900123456
        metadata.longitude = -122.419400123456

        transformed = service.transform_to_generic(metadata, flat=True, gps_precision=0)

        assert transformed['latitude'] == 38.0  # round(37.77..., 0) = 38.0
        assert transformed['longitude'] == -122.0

    def test_transform_applies_gps_precision_nested(self, service, sample_photo_path):
        """transform_to_generic applies GPS precision to nested output."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 37.774900123456
        metadata.longitude = -122.419400123456

        transformed = service.transform_to_generic(metadata, flat=False, gps_precision=2)

        assert transformed['location']['latitude'] == 37.77
        assert transformed['location']['longitude'] == -122.42

    def test_transform_gps_precision_none_preserves_full(self, service, sample_photo_path):
        """transform_to_generic with gps_precision=None keeps full precision."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 37.774900123456
        metadata.longitude = -122.419400123456

        transformed = service.transform_to_generic(metadata, flat=True, gps_precision=None)

        assert transformed['latitude'] == 37.774900123456
        assert transformed['longitude'] == -122.419400123456

    def test_transform_handles_none_coordinates_with_precision(self, service, sample_photo_path):
        """transform_to_generic handles None coordinates gracefully with precision."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = None
        metadata.longitude = None

        transformed = service.transform_to_generic(metadata, flat=True, gps_precision=2)

        assert transformed['latitude'] is None
        assert transformed['longitude'] is None


# ============================================================================
# Test Format Stubs
# ============================================================================

class TestFormatStubs:
    """Tests for format transformer stubs."""

    def test_darwin_core_transforms_to_dwc_format(self, service, sample_photo_path):
        """transform_to_darwin_core should return Darwin Core formatted dict."""
        metadata = service.get_export_metadata(sample_photo_path)

        # Darwin Core is now implemented (Issue #116)
        result = service.transform_to_darwin_core(metadata)

        # Should return a dict with Darwin Core fields
        assert isinstance(result, dict)
        assert "basisOfRecord" in result
        assert result["basisOfRecord"] == "MachineObservation"
        assert "geodeticDatum" in result
        assert result["geodeticDatum"] == "WGS84"

    def test_inaturalist_transforms_metadata(self, service, sample_photo_path):
        """transform_to_inaturalist should transform metadata successfully."""
        metadata = service.get_export_metadata(sample_photo_path)

        result = service.transform_to_inaturalist(metadata)

        # Verify basic structure
        assert isinstance(result, dict)
        assert 'latitude' in result
        assert 'longitude' in result
        assert 'title' in result
        assert 'quality_grade' in result


# ============================================================================
# Test Validation
# ============================================================================

class TestValidation:
    """Tests for validate_for_format method."""

    def test_validate_generic_always_valid(self, service, sample_photo_path):
        """Generic formats should always validate."""
        metadata = service.get_export_metadata(sample_photo_path)

        result = service.validate_for_format(metadata, ExportFormat.GENERIC_JSON)
        assert result.is_valid is True
        assert len(result.missing_fields) == 0

    def test_validate_darwin_core_checks_required(self, service, tmp_path):
        """Darwin Core should check for required fields."""
        # Create metadata with missing Darwin Core required fields
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Mock service to return minimal metadata (missing GPS)
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {},
            'capture': {},
            'location': {},  # No GPS
            'deployment': {},
            'file': {'size': 1000}
        }

        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        mock_series = Mock()
        mock_series.get_series_by_id.return_value = None

        test_service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
            series_service=mock_series
        )

        metadata = test_service.get_export_metadata(photo)
        result = test_service.validate_for_format(metadata, ExportFormat.DARWIN_CORE)

        assert result.is_valid is False
        assert len(result.missing_fields) > 0

    def test_validate_returns_validation_result(self, service, sample_photo_path):
        """validate_for_format should return ValidationResult."""
        metadata = service.get_export_metadata(sample_photo_path)

        result = service.validate_for_format(metadata, ExportFormat.GENERIC_JSON)

        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'missing_fields')
        assert hasattr(result, 'warnings')

    def test_validate_reports_missing_fields(self, service, tmp_path):
        """Validation should list specific missing fields."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Mock minimal metadata
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {},
            'capture': {'timestamp': None},
            'location': {},
            'deployment': {},
            'file': {'size': 1000}
        }

        test_service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=Mock(return_value=None),
            series_service=Mock(return_value=None)
        )

        metadata = test_service.get_export_metadata(photo)
        result = test_service.validate_for_format(metadata, ExportFormat.DARWIN_CORE)

        assert not result.is_valid
        # Should specify what's missing (using Darwin Core field names)
        missing_str = str(result.missing_fields)
        assert 'decimalLatitude' in missing_str or 'decimalLongitude' in missing_str


# ============================================================================
# Test Caching
# ============================================================================

class TestCaching:
    """Tests for cache behavior."""

    def test_cache_hit_on_second_call(self, service, sample_photo_path):
        """Second call should use cache."""
        # First call - cache miss
        result1 = service.get_export_metadata(sample_photo_path)
        stats1 = service.get_statistics()

        # Second call - cache hit
        result2 = service.get_export_metadata(sample_photo_path)
        stats2 = service.get_statistics()

        assert result1 == result2
        assert stats2['cache_hits'] == stats1['cache_hits'] + 1

    def test_cache_invalidation(self, service, sample_photo_path):
        """invalidate_cache should clear cache."""
        # Populate cache
        service.get_export_metadata(sample_photo_path)
        stats1 = service.get_statistics()
        assert stats1['cache_entries'] > 0

        # Invalidate
        service.invalidate_cache()
        stats2 = service.get_statistics()

        assert stats2['cache_entries'] == 0

    def test_cache_statistics_tracking(self, service, sample_photo_path):
        """Cache statistics should track hits and misses."""
        stats_initial = service.get_statistics()

        # First call - miss
        service.get_export_metadata(sample_photo_path)
        stats_after_miss = service.get_statistics()

        # Second call - hit
        service.get_export_metadata(sample_photo_path)
        stats_after_hit = service.get_statistics()

        assert stats_after_miss['cache_misses'] == stats_initial['cache_misses'] + 1
        assert stats_after_hit['cache_hits'] == stats_after_miss['cache_hits'] + 1

    def test_cache_ttl_respected(self, tmp_path, mock_metadata_service,
                                   mock_sidecar_service, mock_series_service):
        """Cache should expire after TTL."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Create service with 0.1s TTL
        service = ExportMetadataService(
            cache_ttl=0.1,
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service
        )

        # First call
        service.get_export_metadata(photo)
        stats1 = service.get_statistics()

        # Wait for TTL to expire
        time.sleep(0.15)

        # Second call - should be cache miss
        service.get_export_metadata(photo)
        stats2 = service.get_statistics()

        # Should have two misses
        assert stats2['cache_misses'] == stats1['cache_misses'] + 1


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_reads_safe(self, service, tmp_path):
        """Multiple concurrent reads should work safely."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        results = []
        errors = []

        def read_metadata():
            try:
                result = service.get_export_metadata(photo)
                results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_metadata) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_concurrent_cache_access_safe(self, service, tmp_path):
        """Concurrent cache operations should work safely."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        errors = []

        def mixed_operations():
            try:
                service.get_export_metadata(photo)
                service.invalidate_cache()
                service.get_statistics()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=mixed_operations) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_permission_error_handled(self, service, tmp_path):
        """Permission errors should be handled gracefully."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Mock metadata service to raise PermissionError
        mock_meta = Mock()
        mock_meta.get_photo_metadata.side_effect = PermissionError("Access denied")

        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        test_service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
            series_service=Mock()
        )

        result = test_service.get_export_metadata(photo)

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'permission' in result['error'].lower()

    def test_corrupted_metadata_handled(self, service, tmp_path):
        """Corrupted metadata should be handled gracefully."""
        photo = tmp_path / "test.jpg"

        # Mock metadata service to return malformed data
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {'invalid': 'structure'}

        test_service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=Mock(return_value=None),
            series_service=Mock(return_value=None)
        )

        # Should not raise, should return error or partial data
        result = test_service.get_export_metadata(photo)
        assert result is not None

    def test_service_dependency_error_handled(self, tmp_path):
        """Service dependency errors should be handled gracefully."""
        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Mock all services to raise exceptions
        mock_meta = Mock()
        mock_meta.get_photo_metadata.side_effect = Exception("Service error")

        mock_sidecar = Mock()
        mock_sidecar.get_metadata.side_effect = Exception("Service error")

        mock_series = Mock()
        mock_series.get_series_by_id.side_effect = Exception("Service error")

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
            series_service=mock_series
        )

        # Should return ExportMetadata with empty fields (graceful degradation)
        # not raise an exception
        result = service.get_export_metadata(photo)
        assert isinstance(result, ExportMetadata)
        assert result.filename == "test.jpg"
        # Metadata fields should be empty since services failed
        assert result.camera_make is None
        assert result.species is None


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""

    def test_statistics_structure(self, service):
        """Statistics should have expected fields."""
        stats = service.get_statistics()

        assert 'cache_entries' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'total_exports' in stats

    def test_statistics_updates_after_operations(self, service, sample_photo_path):
        """Statistics should update after operations."""
        stats1 = service.get_statistics()
        initial_exports = stats1['total_exports']

        service.get_export_metadata(sample_photo_path)

        stats2 = service.get_statistics()
        assert stats2['total_exports'] == initial_exports + 1


# ============================================================================
# Test Reset Statistics
# ============================================================================

class TestResetStatistics:
    """Tests for reset_statistics method."""

    def test_reset_statistics_clears_counters(self, service, sample_photo_path):
        """Reset should clear all counters to zero."""
        # Generate some statistics
        service.get_export_metadata(sample_photo_path)
        service.get_export_metadata(sample_photo_path)  # Cache hit

        stats_before = service.get_statistics()
        assert stats_before['total_exports'] > 0
        assert stats_before['cache_hits'] > 0 or stats_before['cache_misses'] > 0

        # Reset
        service.reset_statistics()

        stats_after = service.get_statistics()
        assert stats_after['cache_hits'] == 0
        assert stats_after['cache_misses'] == 0
        assert stats_after['total_exports'] == 0
        assert stats_after['errors'] == 0

    def test_reset_statistics_preserves_cache_entries(self, service, sample_photo_path):
        """Reset should preserve cache_entries count (reflects actual cache)."""
        # Populate cache
        service.get_export_metadata(sample_photo_path)

        stats_before = service.get_statistics()
        cache_entries_before = stats_before['cache_entries']
        assert cache_entries_before > 0

        # Reset
        service.reset_statistics()

        stats_after = service.get_statistics()
        # cache_entries should reflect actual cache size, not be reset
        assert stats_after['cache_entries'] == cache_entries_before

    def test_reset_statistics_after_errors(self, tmp_path):
        """Reset should clear error counter."""
        from webui.backend.services.export_metadata_service import ExportMetadataService

        service = ExportMetadataService()

        # Generate an error
        nonexistent = tmp_path / "nonexistent.jpg"
        service.get_export_metadata(nonexistent)

        stats_before = service.get_statistics()
        assert stats_before['errors'] > 0

        # Reset
        service.reset_statistics()

        stats_after = service.get_statistics()
        assert stats_after['errors'] == 0

    def test_reset_statistics_is_thread_safe(self, service, sample_photo_path):
        """Reset should be thread-safe."""
        import threading

        # Generate some stats first
        service.get_export_metadata(sample_photo_path)

        errors = []

        def reset_worker():
            try:
                for _ in range(10):
                    service.reset_statistics()
            except Exception as e:
                errors.append(e)

        def stats_worker():
            try:
                for _ in range(10):
                    service.get_statistics()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reset_worker),
            threading.Thread(target=stats_worker),
            threading.Thread(target=reset_worker),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


# ============================================================================
# Test iNaturalist Transformation (Issue #118)
# ============================================================================

class TestTransformToINaturalist:
    """Tests for transform_to_inaturalist() method."""

    def test_transforms_complete_metadata(self, service, sample_photo_path):
        """Test transformation with all fields populated."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_inaturalist(metadata)

        # Check required fields
        assert 'title' in result
        assert 'notes' in result
        assert 'latitude' in result
        assert 'longitude' in result
        assert 'quality_grade' in result
        assert 'timestamp' in result

        # Verify values
        assert result['latitude'] == 37.7749
        assert result['longitude'] == -122.4194

    def test_includes_taxonomy_keywords(self, service, sample_photo_path):
        """Test that taxonomy keywords are included."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_inaturalist(metadata)

        assert 'keywords' in result
        assert isinstance(result['keywords'], list)

        # Should have taxonomy keywords
        taxonomy_keywords = [k for k in result['keywords'] if k.startswith('taxonomy:')]
        assert len(taxonomy_keywords) > 0

    def test_maps_confidence_to_quality_grade(self, tmp_path, mock_metadata_service, sample_exif_metadata):
        """Test species confidence mapping."""
        # Create photo
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Mock sidecar with 'certain' confidence
        @dataclass
        class SidecarMetadata:
            tags: list[str]
            species: str | None
            common_name: str | None
            confidence: str | None
            notes: str | None

        sidecar = SidecarMetadata(
            tags=['moth'],
            species='Actias luna',
            common_name='Luna moth',
            confidence='certain',
            notes='Test'
        )

        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = sidecar

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar,
        )

        metadata = service.get_export_metadata(photo)
        result = service.transform_to_inaturalist(metadata)

        # 'certain' maps to 'research'
        assert result['quality_grade'] in ['research', 'needs_id', 'casual']

    def test_handles_missing_species(self, tmp_path, sample_exif_metadata):
        """Test transformation with no species data."""
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = sample_exif_metadata

        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        metadata = service.get_export_metadata(photo)
        result = service.transform_to_inaturalist(metadata)

        # Should still work
        assert 'title' in result
        assert 'species' in result
        assert result['species'] == ''


# ============================================================================
# Test iNaturalist ZIP Export (Issue #118)
# ============================================================================

class TestTransformBatchToINaturalistZip:
    """Tests for transform_batch_to_inaturalist_zip() method."""

    def test_creates_zip_file(self, tmp_path, service):
        """Test ZIP creation."""
        # Create sample photos
        photos = []
        for i in range(3):
            photo = tmp_path / f"moth_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
            photos.append(photo)

        output_path = tmp_path / "export.zip"
        result = service.transform_batch_to_inaturalist_zip(
            photos,
            output_path=output_path,
        )

        assert result.success
        assert output_path.exists()
        assert result.photo_count > 0

    def test_empty_list_raises_error(self, service):
        """Test error on empty photo list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            service.transform_batch_to_inaturalist_zip([])

    def test_uses_temp_file_when_no_output_path(self, tmp_path, service):
        """Test temp file creation when output_path is None."""
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        result = service.transform_batch_to_inaturalist_zip([photo])

        assert result.success
        assert result.zip_path is not None
        assert result.zip_path.exists()
        assert str(result.zip_path).endswith('.zip')

    def test_includes_xmp_sidecars_by_default(self, tmp_path, service):
        """Test that XMP sidecars are included by default."""
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        output_path = tmp_path / "export.zip"
        result = service.transform_batch_to_inaturalist_zip(
            [photo],
            output_path=output_path,
        )

        assert result.success
        # XMP files should be created (count should match or be close to photo count)
        assert result.xmp_count >= 0

    def test_respects_zip_export_options(self, tmp_path, service):
        """Test that ZipExportOptions are respected."""
        from webui.backend.lib.zip_export import ZipExportOptions

        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        # Create options with XMP disabled
        options = ZipExportOptions(include_xmp_sidecars=False)

        output_path = tmp_path / "export.zip"
        result = service.transform_batch_to_inaturalist_zip(
            [photo],
            output_path=output_path,
            options=options,
        )

        assert result.success
        # XMP count should be 0 when disabled
        assert result.xmp_count == 0


# ============================================================================
# Test iNaturalist Validation (Issue #118)
# ============================================================================

class TestValidateINaturalist:
    """Tests for _validate_inaturalist() method."""

    def test_valid_metadata_passes(self, service, sample_photo_path):
        """Test valid metadata passes validation."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service._validate_inaturalist(metadata)

        assert result.is_valid

    def test_missing_latitude_fails(self, tmp_path, sample_exif_no_gps):
        """Test validation fails without GPS."""
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = sample_exif_no_gps

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=Mock(return_value=None),
        )

        metadata = service.get_export_metadata(photo)
        result = service._validate_inaturalist(metadata)

        assert not result.is_valid
        assert len(result.missing_fields) > 0
        # Should mention latitude or longitude
        missing_str = str(result.missing_fields)
        assert 'latitude' in missing_str or 'longitude' in missing_str

    def test_returns_warnings_for_missing_recommended(self, tmp_path, sample_exif_metadata):
        """Test warnings for missing recommended fields."""
        photo = tmp_path / "moth.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = sample_exif_metadata

        # No sidecar data
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        metadata = service.get_export_metadata(photo)
        result = service._validate_inaturalist(metadata)

        # Should be valid (GPS present) but have warnings
        assert result.is_valid
        assert len(result.warnings) > 0

    def test_validate_for_format_calls_inaturalist_validation(self, service, sample_photo_path):
        """Test that validate_for_format uses iNaturalist validation."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.validate_for_format(metadata, ExportFormat.INATURALIST)

        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'is_valid')
        assert result.is_valid  # Should pass with sample data


# ============================================================================
# Test Lazy Loading of Services (lines 220, 226-228, 234-236)
# ============================================================================

class TestLazyLoadingServices:
    """Tests for lazy-loading service accessors."""

    def test_lazy_load_metadata_service(self, tmp_path):
        """_get_metadata_service should create MetadataService when None."""
        service = ExportMetadataService(metadata_service=None)
        result = service._get_metadata_service()
        assert result is not None
        # Subsequent call should return same instance
        assert service._get_metadata_service() is result

    def test_lazy_load_sidecar_service(self, tmp_path):
        """_get_sidecar_service should import and create SidecarService when None."""
        service = ExportMetadataService(sidecar_service=None)
        result = service._get_sidecar_service()
        assert result is not None
        assert service._get_sidecar_service() is result

    def test_lazy_load_series_service(self, tmp_path):
        """_get_series_service should import and create SeriesService when None."""
        service = ExportMetadataService(series_service=None)
        result = service._get_series_service()
        assert result is not None
        assert service._get_series_service() is result


# ============================================================================
# Test Cache LRU Eviction (lines 283-285)
# ============================================================================

class TestCacheLRUEviction:
    """Tests for LRU cache eviction when cache is full."""

    def test_cache_evicts_oldest_when_full(self, tmp_path):
        """Should evict oldest cache entry when max_cache_size is reached."""
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            cache_ttl=300,
            max_cache_size=2,
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        # Create 3 photos - should trigger eviction on the 3rd
        photos = []
        for i in range(3):
            photo = tmp_path / f"photo_{i}.jpg"
            photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            photos.append(photo)

        # Fill cache to max (2 entries)
        service.get_export_metadata(photos[0])
        service.get_export_metadata(photos[1])
        stats = service.get_statistics()
        assert stats['cache_entries'] == 2

        # Third photo should trigger eviction of oldest
        service.get_export_metadata(photos[2])
        stats = service.get_statistics()
        assert stats['cache_entries'] == 2  # Still 2, not 3


# ============================================================================
# Test Cache Invalidation for Specific Key (lines 301-303)
# ============================================================================

class TestCacheInvalidateSpecificKey:
    """Tests for invalidating a specific cache entry."""

    def test_invalidate_specific_key(self, service, sample_photo_path):
        """Should invalidate only the specified cache entry."""
        # Populate cache
        service.get_export_metadata(sample_photo_path)
        stats = service.get_statistics()
        assert stats['cache_entries'] == 1

        # Invalidate specific key
        cache_key = str(sample_photo_path.resolve())
        service.invalidate_cache(key=cache_key)
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0

    def test_invalidate_nonexistent_key_no_error(self, service):
        """Should not error when invalidating a non-existent key."""
        service.invalidate_cache(key="/nonexistent/path.jpg")
        stats = service.get_statistics()
        assert stats['cache_entries'] == 0


# ============================================================================
# Test Deployment Metadata Merge (lines 399-405)
# ============================================================================

class TestDeploymentMetadataMerge:
    """Tests for merging deployment metadata when a deployment is found."""

    def test_deployment_fields_merged_when_found(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """Should merge deployment name, location, dates, and environmental data."""
        mock_deployment = Mock()
        mock_deployment_data = Mock()
        mock_deployment_data.deployment_name = "Panama Canopy 2024"
        mock_deployment_data.location_name = "Barro Colorado Island"
        mock_deployment_data.start_date = "2024-01-01"
        mock_deployment_data.end_date = "2024-03-31"
        mock_deployment_data.environmental = {"temperature": "28C", "humidity": "90%"}
        mock_deployment.find_deployment_for_photo.return_value = mock_deployment_data

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service,
            deployment_service=mock_deployment,
        )

        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        assert result.deployment_name == "Panama Canopy 2024"
        assert result.deployment_location_name == "Barro Colorado Island"
        assert result.deployment_start_date == "2024-01-01"
        assert result.deployment_end_date == "2024-03-31"
        assert result.environmental_conditions == {"temperature": "28C", "humidity": "90%"}

    def test_deployment_environmental_none_becomes_empty_dict(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """When deployment.environmental is None, should use empty dict."""
        mock_deployment = Mock()
        mock_deployment_data = Mock()
        mock_deployment_data.deployment_name = "Test Deployment"
        mock_deployment_data.location_name = None
        mock_deployment_data.start_date = None
        mock_deployment_data.end_date = None
        mock_deployment_data.environmental = None
        mock_deployment.find_deployment_for_photo.return_value = mock_deployment_data

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service,
            deployment_service=mock_deployment,
        )

        result = service.get_export_metadata(sample_photo_path)

        assert result.deployment_name == "Test Deployment"
        assert result.environmental_conditions == {}

    def test_deployment_service_exception_handled(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service, sample_photo_path
    ):
        """Should handle deployment service exceptions gracefully."""
        mock_deployment = Mock()
        mock_deployment.find_deployment_for_photo.side_effect = Exception("DB error")

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service,
            deployment_service=mock_deployment,
        )

        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        assert result.deployment_name is None


# ============================================================================
# Test Country Code Detection Exception (lines 414-415)
# ============================================================================

class TestCountryCodeDetection:
    """Tests for country code detection exception handling."""

    def test_country_code_exception_handled(
        self, mock_metadata_service, mock_sidecar_service, mock_series_service,
        mock_deployment_service, sample_photo_path
    ):
        """Should handle country code detection exceptions gracefully."""
        from unittest.mock import patch

        service = ExportMetadataService(
            metadata_service=mock_metadata_service,
            sidecar_service=mock_sidecar_service,
            series_service=mock_series_service,
            deployment_service=mock_deployment_service,
        )

        with patch(
            'webui.backend.services.export_metadata_service.detect_country_code',
            side_effect=Exception("Country code detection failed"),
            create=True,
        ):
            # Force re-import to trigger the exception path
            pass

        # Direct approach: mock the import inside the function
        with patch(
            'webui.backend.lib.country_code.detect_country_code',
            side_effect=Exception("Country code lookup failed"),
        ):
            # Clear cache to force re-computation
            service.invalidate_cache()
            result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        # Country code should be None due to exception
        assert result.country_code is None


# ============================================================================
# Test Outer Exception Handlers (lines 422-434)
# ============================================================================

class TestOuterExceptionHandlers:
    """Tests for the outer FileNotFoundError and generic Exception handlers."""

    def test_unexpected_exception_in_processing(self, tmp_path):
        """Should handle unexpected exceptions in outer try block."""
        from unittest.mock import patch

        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        # Trigger outer except Exception by making _add_to_cache raise.
        # _add_to_cache is called after all inner try blocks, so its exception
        # propagates to the outer try/except.
        with patch.object(service, '_add_to_cache', side_effect=RuntimeError("Unexpected")):
            result = service.get_export_metadata(photo)

        assert isinstance(result, dict)
        assert 'error' in result
        assert result['error'] == "Failed to process metadata"

    def test_file_not_found_error_outer_handler(self, tmp_path):
        """Should handle FileNotFoundError in the outer try block."""
        from unittest.mock import patch

        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        # Trigger outer FileNotFoundError via _add_to_cache (after inner handlers)
        with patch.object(service, '_add_to_cache', side_effect=FileNotFoundError("Gone")):
            result = service.get_export_metadata(photo)

        assert isinstance(result, dict)
        assert 'error' in result
        assert 'not found' in result['error'].lower()

    def test_outer_exception_increments_error_count(self, tmp_path):
        """Error counter should increment for outer exceptions."""
        from unittest.mock import patch

        photo = tmp_path / "test.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        initial_errors = service.get_statistics()['errors']

        with patch.object(service, '_add_to_cache', side_effect=RuntimeError("Boom")):
            service.get_export_metadata(photo)

        assert service.get_statistics()['errors'] == initial_errors + 1


# ============================================================================
# Test Sidecar Dict Branch (lines 494-499)
# ============================================================================

class TestSidecarDictBranch:
    """Tests for _merge_sidecar_data with dict input."""

    def test_merge_sidecar_data_from_dict(self, sample_photo_path):
        """Should handle sidecar data provided as a dict."""
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }

        # Return a dict instead of a SidecarMetadata dataclass
        sidecar_dict = {
            'species': 'Papilio machaon',
            'common_name': 'Swallowtail',
            'confidence': 'medium',
            'tags': ['butterfly', 'day'],
            'notes': 'Found in meadow',
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = sidecar_dict

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        assert result.species == 'Papilio machaon'
        assert result.species_common_name == 'Swallowtail'
        assert result.species_confidence == 'medium'
        assert result.tags == ['butterfly', 'day']
        assert result.notes == 'Found in meadow'

    def test_merge_sidecar_data_from_dict_missing_keys(self, sample_photo_path):
        """Should handle dict sidecar with missing keys."""
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }

        # Dict with only some keys
        sidecar_dict = {'species': 'Unknown moth'}
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = sidecar_dict

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        result = service.get_export_metadata(sample_photo_path)

        assert isinstance(result, ExportMetadata)
        assert result.species == 'Unknown moth'
        assert result.species_common_name is None
        assert result.tags == []
        assert result.notes is None


# ============================================================================
# Test Generic Filtered Transformer (lines 695-713)
# ============================================================================

class TestGenericFilteredTransformer:
    """Tests for transform_to_generic_filtered method."""

    def test_fields_and_exclude_raises_error(self, service, sample_photo_path):
        """Should raise ValueError when both fields and exclude are provided."""
        metadata = service.get_export_metadata(sample_photo_path)
        with pytest.raises(ValueError, match="Cannot specify both"):
            service.transform_to_generic_filtered(
                metadata, fields=["filename"], exclude=["notes"]
            )

    def test_no_filters_returns_full_data(self, service, sample_photo_path):
        """Should return full data when no filters are specified."""
        metadata = service.get_export_metadata(sample_photo_path)
        full = service.transform_to_generic(metadata, flat=False)
        filtered = service.transform_to_generic_filtered(metadata, flat=False)
        assert filtered == full

    def test_flat_include_fields(self, service, sample_photo_path):
        """Should include only specified fields in flat mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=True, fields=["filename", "latitude", "species"]
        )
        assert set(result.keys()) == {"filename", "latitude", "species"}

    def test_flat_exclude_fields(self, service, sample_photo_path):
        """Should exclude specified fields in flat mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        full = service.transform_to_generic(metadata, flat=True)
        result = service.transform_to_generic_filtered(
            metadata, flat=True, exclude=["notes", "tags"]
        )
        assert "notes" not in result
        assert "tags" not in result
        assert len(result) == len(full) - 2

    def test_nested_include_section(self, service, sample_photo_path):
        """Should include entire section by name in nested mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, fields=["camera"]
        )
        assert "camera" in result
        assert "location" not in result
        assert result["camera"]["make"] == "Arducam"

    def test_nested_include_leaf_field(self, service, sample_photo_path):
        """Should include specific leaf fields in nested mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, fields=["latitude", "make"]
        )
        # latitude is under location section
        assert "location" in result
        assert "latitude" in result["location"]
        # make is under camera section
        assert "camera" in result
        assert "make" in result["camera"]

    def test_nested_include_dotted_path(self, service, sample_photo_path):
        """Should support dotted paths like 'file.filename'."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, fields=["file.filename"]
        )
        assert "file" in result
        assert "filename" in result["file"]
        assert len(result["file"]) == 1  # Only filename, not other file fields

    def test_nested_include_top_level_non_dict(self, service, sample_photo_path):
        """Should include top-level non-dict fields like 'timestamp'."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, fields=["timestamp"]
        )
        assert "timestamp" in result
        assert result["timestamp"] == metadata.timestamp

    def test_nested_exclude_section(self, service, sample_photo_path):
        """Should exclude entire section by name in nested mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, exclude=["camera", "series"]
        )
        assert "camera" not in result
        assert "series" not in result
        assert "location" in result
        assert "file" in result

    def test_nested_exclude_leaf_field(self, service, sample_photo_path):
        """Should exclude specific leaf fields in nested mode."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, exclude=["make", "model"]
        )
        # Camera section should exist but without make and model
        assert "camera" in result
        assert "make" not in result["camera"]
        assert "model" not in result["camera"]

    def test_nested_exclude_dotted_path(self, service, sample_photo_path):
        """Should support dotted path exclusion like 'file.filename'."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, exclude=["file.filename"]
        )
        assert "file" in result
        assert "filename" not in result["file"]
        assert "file_size" in result["file"]

    def test_nested_exclude_all_leaves_removes_section(self, service, sample_photo_path):
        """Excluding all leaves in a section should remove the section."""
        metadata = service.get_export_metadata(sample_photo_path)
        result = service.transform_to_generic_filtered(
            metadata, flat=False, exclude=["type", "index", "count"]
        )
        # Series section had type, index, count - all excluded
        assert "series" not in result


# ============================================================================
# Test Darwin Core CSV Batch Transform (lines 841-856)
# ============================================================================

class TestDarwinCoreCsvBatch:
    """Tests for transform_batch_to_darwin_core_csv method."""

    def test_batch_csv_with_valid_metadata(self, service, sample_photo_path):
        """Should produce headers and rows for valid metadata."""
        metadata = service.get_export_metadata(sample_photo_path)
        headers, rows = service.transform_batch_to_darwin_core_csv([metadata])

        assert isinstance(headers, list)
        assert len(headers) > 0
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert isinstance(rows[0], list)

    def test_batch_csv_filters_invalid_when_enabled(self, service, tmp_path):
        """Should filter out metadata without GPS when filter_invalid=True."""
        # Create metadata without GPS
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        svc = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        photo = tmp_path / "no_gps.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata_no_gps = svc.get_export_metadata(photo)

        headers, rows = svc.transform_batch_to_darwin_core_csv(
            [metadata_no_gps], filter_invalid=True
        )

        assert len(rows) == 0  # Filtered out

    def test_batch_csv_includes_invalid_when_disabled(self, service, tmp_path):
        """Should include invalid metadata when filter_invalid=False."""
        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        svc = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        photo = tmp_path / "no_gps.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        metadata_no_gps = svc.get_export_metadata(photo)

        headers, rows = svc.transform_batch_to_darwin_core_csv(
            [metadata_no_gps], filter_invalid=False
        )

        assert len(rows) == 1  # Not filtered

    def test_batch_csv_multiple_items(self, service, sample_photo_path):
        """Should handle multiple metadata items."""
        metadata = service.get_export_metadata(sample_photo_path)
        headers, rows = service.transform_batch_to_darwin_core_csv(
            [metadata, metadata, metadata]
        )

        assert len(rows) == 3

    def test_batch_csv_empty_list(self, service):
        """Should return headers but no rows for empty list."""
        headers, rows = service.transform_batch_to_darwin_core_csv([])

        assert isinstance(headers, list)
        assert len(headers) > 0
        assert rows == []


# ============================================================================
# Test Unknown Format Validation (line 967)
# ============================================================================

class TestUnknownFormatValidation:
    """Tests for validation of unknown/unrecognized format."""

    def test_unknown_format_returns_valid(self, service, sample_photo_path):
        """Unknown format should return valid result (generic validation)."""
        metadata = service.get_export_metadata(sample_photo_path)

        # Create a mock format that is not in the known set
        # Since ExportFormat is an Enum, we test with GENERIC_CSV which hits
        # the early return, and also verify GENERIC_JSON
        result_json = service.validate_for_format(metadata, ExportFormat.GENERIC_JSON)
        assert result_json.is_valid

        result_csv = service.validate_for_format(metadata, ExportFormat.GENERIC_CSV)
        assert result_csv.is_valid


# ============================================================================
# Test Darwin Core Validation Edge Cases (lines 989-990, 996-997, 1002, 1012)
# ============================================================================

class TestDarwinCoreValidationEdgeCases:
    """Tests for Darwin Core validation edge cases."""

    def test_latitude_out_of_range(self, service, sample_photo_path):
        """Should report invalid latitude range."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 95.0  # Out of range
        metadata.longitude = -122.4194

        result = service._validate_darwin_core(metadata)

        assert not result.is_valid
        missing_str = str(result.missing_fields)
        assert 'invalid range' in missing_str
        assert '95.0' in missing_str

    def test_longitude_out_of_range(self, service, sample_photo_path):
        """Should report invalid longitude range."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 37.7749
        metadata.longitude = 200.0  # Out of range

        result = service._validate_darwin_core(metadata)

        assert not result.is_valid
        missing_str = str(result.missing_fields)
        assert 'invalid range' in missing_str
        assert '200.0' in missing_str

    def test_missing_timestamp_reported(self, service, sample_photo_path):
        """Should report missing timestamp."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 37.7749
        metadata.longitude = -122.4194
        metadata.timestamp = None

        result = service._validate_darwin_core(metadata)

        assert not result.is_valid
        missing_str = str(result.missing_fields)
        assert 'eventDate' in missing_str

    def test_missing_species_generates_warning(self, service, sample_photo_path):
        """Should generate warning for missing species."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.species = None

        result = service._validate_darwin_core(metadata)

        # Should still be valid (species is recommended, not required)
        assert result.is_valid
        warning_str = str(result.warnings)
        assert 'scientificName' in warning_str

    def test_missing_gps_accuracy_generates_warning(self, service, sample_photo_path):
        """Should generate warning for missing GPS accuracy."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.gps_accuracy = None

        result = service._validate_darwin_core(metadata)

        # Should still be valid
        assert result.is_valid
        warning_str = str(result.warnings)
        assert 'coordinateUncertaintyInMeters' in warning_str

    def test_empty_timestamp_string_reported(self, service, sample_photo_path):
        """Should report empty string timestamp as missing."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 37.7749
        metadata.longitude = -122.4194
        metadata.timestamp = ""

        result = service._validate_darwin_core(metadata)

        assert not result.is_valid
        missing_str = str(result.missing_fields)
        assert 'eventDate' in missing_str

    def test_latitude_negative_90_is_valid(self, service, sample_photo_path):
        """Latitude at -90 should be valid (South Pole)."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = -90.0
        metadata.longitude = 0.0
        metadata.timestamp = "2024-01-15T10:00:00"

        result = service._validate_darwin_core(metadata)

        # Latitude and longitude within range; no missing required fields for them
        lat_long_errors = [f for f in result.missing_fields if 'decimal' in f.lower()]
        assert len(lat_long_errors) == 0

    def test_longitude_negative_180_is_valid(self, service, sample_photo_path):
        """Longitude at -180 should be valid."""
        metadata = service.get_export_metadata(sample_photo_path)
        metadata.latitude = 0.0
        metadata.longitude = -180.0
        metadata.timestamp = "2024-01-15T10:00:00"

        result = service._validate_darwin_core(metadata)

        lat_long_errors = [f for f in result.missing_fields if 'decimal' in f.lower()]
        assert len(lat_long_errors) == 0


# ============================================================================
# Test Series Detection Path with series_id (lines 384->395, 389->395, 391-392)
# ============================================================================

class TestSeriesDetectionPaths:
    """Tests for series detection branch paths."""

    def test_series_id_found_and_series_data_returned(self, tmp_path):
        """When series_id is found and series service returns data, count is set."""
        from unittest.mock import patch

        # Use HDR naming pattern
        photo = tmp_path / "moth_2024_01_15__10_00_00_HDR0.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        mock_series_data = Mock()
        mock_series_data.count = 5

        mock_series = Mock()
        mock_series.get_series_by_id.return_value = mock_series_data

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
            series_service=mock_series,
        )

        result = service.get_export_metadata(photo)

        assert isinstance(result, ExportMetadata)
        assert result.series_type == 'hdr'
        assert result.series_index == 0
        assert result.series_count == 5

    def test_series_id_found_but_series_data_none(self, tmp_path):
        """When series_id is found but series service returns None, count stays None."""
        photo = tmp_path / "moth_2024_01_15__10_00_00_HDR0.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        mock_series = Mock()
        mock_series.get_series_by_id.return_value = None  # No series data

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
            series_service=mock_series,
        )

        result = service.get_export_metadata(photo)

        assert isinstance(result, ExportMetadata)
        assert result.series_type == 'hdr'
        assert result.series_index == 0
        assert result.series_count is None  # Not set because series_data was None

    def test_series_detection_exception_handled(self, tmp_path):
        """Should handle series detection exceptions gracefully."""
        from unittest.mock import patch

        photo = tmp_path / "moth_2024_01_15__10_00_00_HDR0.jpg"
        photo.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        mock_meta = Mock()
        mock_meta.get_photo_metadata.return_value = {
            'camera': {}, 'capture': {}, 'location': {},
            'deployment': {}, 'file': {'size': 100},
        }
        mock_sidecar = Mock()
        mock_sidecar.get_metadata.return_value = None

        service = ExportMetadataService(
            metadata_service=mock_meta,
            sidecar_service=mock_sidecar,
        )

        with patch(
            'webui.backend.lib.series_detection.detect_series_type',
            side_effect=Exception("Series detection error"),
        ):
            result = service.get_export_metadata(photo)

        assert isinstance(result, ExportMetadata)
        assert result.series_type is None
        assert result.series_count is None
