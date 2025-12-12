"""
Unit tests for Export Metadata Service (Issue #112 - Subtask 1)

Tests ExportMetadataService aggregation layer with caching and thread-safety.
TDD approach: tests written first, then implementation.

Coverage Target: 90%+
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, asdict
from enum import Enum


# Import will fail until implementation exists - that's expected in TDD
try:
    from webui.backend.services.export_metadata_service import (
        ExportMetadataService,
        ExportMetadata,
        ValidationResult,
        ExportFormat,
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
def service(mock_metadata_service, mock_sidecar_service, mock_series_service):
    """Create ExportMetadataService with mocked dependencies."""
    return ExportMetadataService(
        cache_ttl=1,  # 1 second TTL for fast testing
        metadata_service=mock_metadata_service,
        sidecar_service=mock_sidecar_service,
        series_service=mock_series_service
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

    def test_get_metadata_performance_under_100ms(
        self, service, sample_photo_path
    ):
        """get_export_metadata should complete in <100ms."""
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


# ============================================================================
# Test Format Stubs
# ============================================================================

class TestFormatStubs:
    """Tests for format transformer stubs."""

    def test_darwin_core_stub_raises_not_implemented(self, service, sample_photo_path):
        """transform_to_darwin_core should raise NotImplementedError."""
        metadata = service.get_export_metadata(sample_photo_path)

        with pytest.raises(NotImplementedError, match="Darwin Core"):
            service.transform_to_darwin_core(metadata)

    def test_inaturalist_stub_raises_not_implemented(self, service, sample_photo_path):
        """transform_to_inaturalist should raise NotImplementedError."""
        metadata = service.get_export_metadata(sample_photo_path)

        with pytest.raises(NotImplementedError, match="iNaturalist"):
            service.transform_to_inaturalist(metadata)


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
        # Should specify what's missing
        assert 'latitude' in result.missing_fields or 'longitude' in result.missing_fields


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
