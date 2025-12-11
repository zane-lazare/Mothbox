"""
Export Metadata Service for Mothbox Photo Gallery (Issue #112)

Provides aggregated metadata for photo exports by combining data from:
- MetadataService: EXIF data (camera, location, capture settings)
- SidecarService: User annotations (tags, species, notes)
- SeriesService: Series detection (HDR, focus bracket)

Thread-safe with configurable TTL caching for performance.

Architecture:
- Thin wrapper over existing services (no business logic duplication)
- Generic JSON/CSV transformer implemented
- Darwin Core/iNaturalist transformers are stubs (Issues #116, #118)

Usage:
    from webui.backend.services.export_metadata_service import (
        ExportMetadataService,
        ExportFormat,
    )

    service = ExportMetadataService(cache_ttl=300)

    # Single photo
    metadata = service.get_export_metadata("/photos/moth_2024_01_15__10_00_00.jpg")

    # Batch processing
    photos = ["/photos/photo1.jpg", "/photos/photo2.jpg"]
    results = service.batch_get_export_metadata(photos)

    # Transform to format
    json_data = service.transform_to_generic(metadata, flat=False)
    csv_row = service.transform_to_generic(metadata, flat=True)

    # Validate for export format
    validation = service.validate_for_format(metadata, ExportFormat.DARWIN_CORE)
    if not validation.is_valid:
        print(f"Missing: {validation.missing_fields}")

Performance Targets:
- Single photo: <100ms
- Cache hit: <10ms
"""

import logging
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from webui.backend.services.metadata_service import MetadataService
from webui.backend.services.sidecar_service import SidecarMetadata, SidecarService

if TYPE_CHECKING:
    from webui.backend.services.series_service import SeriesService

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ExportMetadata:
    """Aggregated photo metadata for export.

    Combines:
    - EXIF from MetadataService (camera, location, capture)
    - User data from SidecarService (tags, species, notes)
    - Series info from SeriesService (HDR/FB detection)
    """
    photo_path: str
    filename: str
    timestamp: str | None = None

    # Location
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    gps_accuracy: float | None = None

    # Camera
    camera_make: str | None = None
    camera_model: str | None = None
    exposure_time: str | None = None
    iso: int | None = None
    focal_length: str | None = None

    # Identification
    species: str | None = None
    species_common_name: str | None = None
    species_confidence: str | None = None

    # User data
    tags: list[str] = field(default_factory=list)
    notes: str | None = None

    # Deployment
    mothbox_id: str | None = None
    firmware_version: str | None = None

    # Series
    series_type: str | None = None  # "hdr" or "focus_bracket" or None
    series_index: int | None = None
    series_count: int | None = None

    # File
    file_size: int = 0
    width: int | None = None
    height: int | None = None


@dataclass
class ValidationResult:
    """Result of metadata validation for export format."""
    is_valid: bool
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ExportFormat(Enum):
    """Supported export formats."""
    DARWIN_CORE = "darwin_core"
    INATURALIST = "inaturalist"
    GENERIC_JSON = "json"
    GENERIC_CSV = "csv"


# ============================================================================
# Export Metadata Service
# ============================================================================

# Required fields per format
DARWIN_CORE_REQUIRED = ['latitude', 'longitude', 'timestamp']
INATURALIST_REQUIRED = ['latitude', 'longitude', 'timestamp']
GENERIC_REQUIRED = []  # No required fields for generic


class ExportMetadataService:
    """
    Service for aggregating photo metadata for export operations.

    Thread-safe with configurable TTL caching.
    """

    def __init__(
        self,
        cache_ttl: int = 300,
        metadata_service: MetadataService | None = None,
        sidecar_service: SidecarService | None = None,
        series_service: "SeriesService | None" = None,
    ):
        """Initialize with optional dependency injection for testing.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
            metadata_service: MetadataService instance (or None for lazy load)
            sidecar_service: SidecarService instance (or None for lazy load)
            series_service: SeriesService instance (or None for lazy load)
        """
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[ExportMetadata, float]] = {}
        self._lock = threading.RLock()
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_entries': 0,
            'total_exports': 0,
            'errors': 0,
        }

        # Lazy-loaded services
        self._metadata_service = metadata_service
        self._sidecar_service = sidecar_service
        self._series_service = series_service

    # ========================================================================
    # Service Accessors (Lazy Loading)
    # ========================================================================

    def _get_metadata_service(self) -> MetadataService:
        """Get MetadataService instance (lazy load if needed)."""
        if self._metadata_service is None:
            self._metadata_service = MetadataService()
        return self._metadata_service

    def _get_sidecar_service(self) -> SidecarService:
        """Get SidecarService instance (lazy load if needed)."""
        if self._sidecar_service is None:
            from webui.backend.services import get_sidecar_service
            self._sidecar_service = get_sidecar_service()
        return self._sidecar_service

    def _get_series_service(self) -> "SeriesService":
        """Get SeriesService instance (lazy load if needed)."""
        if self._series_service is None:
            from webui.backend.services import get_series_service
            self._series_service = get_series_service()
        return self._series_service

    # ========================================================================
    # Cache Management
    # ========================================================================

    def _get_from_cache(self, key: str) -> ExportMetadata | None:
        """Get metadata from cache if valid.

        Args:
            key: Cache key (photo path)

        Returns:
            ExportMetadata if cached and not expired, None otherwise
        """
        with self._lock:
            if key in self._cache:
                metadata, timestamp = self._cache[key]
                if time.time() - timestamp < self._cache_ttl:
                    self._stats['cache_hits'] += 1
                    return metadata
                # Expired - remove
                del self._cache[key]
                self._stats['cache_entries'] = len(self._cache)
            self._stats['cache_misses'] += 1
            return None

    def _add_to_cache(self, key: str, metadata: ExportMetadata) -> None:
        """Add metadata to cache.

        Args:
            key: Cache key (photo path)
            metadata: ExportMetadata to cache
        """
        with self._lock:
            self._cache[key] = (metadata, time.time())
            self._stats['cache_entries'] = len(self._cache)

    def invalidate_cache(self, key: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            key: If provided, invalidate specific entry. If None, clear all.
        """
        with self._lock:
            if key is None:
                self._cache.clear()
                logger.debug("Invalidated entire export metadata cache")
            else:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug("Invalidated cache for %s", key)
            self._stats['cache_entries'] = len(self._cache)

    # ========================================================================
    # Metadata Aggregation
    # ========================================================================

    def get_export_metadata(self, photo_path: Path | str) -> ExportMetadata | dict:
        """Get aggregated metadata for a single photo.

        Combines data from MetadataService, SidecarService, and SeriesService.
        Results are cached for performance.

        Args:
            photo_path: Path to photo file (Path or string)

        Returns:
            ExportMetadata on success, dict with 'error' key on failure.

        Performance target: <100ms per photo.
        """
        # Normalize path
        photo_path = Path(photo_path) if isinstance(photo_path, str) else photo_path
        cache_key = str(photo_path.resolve())

        # Check cache first
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Track export attempt
        with self._lock:
            self._stats['total_exports'] += 1

        # Fail fast: Check if file exists before processing
        if not photo_path.exists():
            error_result = {
                'error': 'Photo not found',
                'photo_path': str(photo_path)
            }
            with self._lock:
                self._stats['errors'] += 1
            return error_result

        # Track if we encounter specific errors
        permission_error_occurred = False

        try:
            # Initialize result with required fields
            export_metadata = ExportMetadata(
                photo_path=str(photo_path),
                filename=photo_path.name,
            )

            # Get EXIF metadata
            try:
                exif_data = self._get_metadata_service().get_photo_metadata(photo_path)
                if exif_data and 'error' not in exif_data:
                    self._merge_exif_data(export_metadata, exif_data)
            except PermissionError as e:
                logger.warning("Failed to get EXIF metadata for %s: %s", photo_path.name, e)
                permission_error_occurred = True
            except Exception as e:
                logger.warning("Failed to get EXIF metadata for %s: %s", photo_path.name, e)

            # Get sidecar metadata
            try:
                sidecar_service = self._get_sidecar_service()
                sidecar_data = sidecar_service.get_metadata(str(photo_path))
                if sidecar_data:
                    self._merge_sidecar_data(export_metadata, sidecar_data)
            except Exception as e:
                logger.warning("Failed to get sidecar metadata for %s: %s", photo_path.name, e)

            # Get series information
            try:
                from webui.backend.lib.series_detection import detect_series_type, get_series_id

                series_info = detect_series_type(photo_path)
                if series_info:
                    export_metadata.series_type = series_info.series_type
                    export_metadata.series_index = series_info.index

                    # Get series count from SeriesService
                    series_id = get_series_id(photo_path)
                    if series_id:
                        series_service = self._get_series_service()
                        series_data = series_service.get_series_by_id(
                            series_id,
                            directory=photo_path.parent
                        )
                        if series_data:
                            export_metadata.series_count = series_data.count
            except Exception as e:
                logger.warning("Failed to get series info for %s: %s", photo_path.name, e)

            # Handle case where permission error occurred during metadata extraction
            if permission_error_occurred:
                error_result = {
                    'error': 'Permission denied',
                    'photo_path': str(photo_path)
                }
                with self._lock:
                    self._stats['errors'] += 1
                return error_result

            # Cache the result
            self._add_to_cache(cache_key, export_metadata)

            return export_metadata

        except PermissionError:
            logger.error("Permission denied accessing %s", photo_path, exc_info=True)
            error_result = {
                'error': 'Permission denied',
                'photo_path': str(photo_path)
            }
            with self._lock:
                self._stats['errors'] += 1
            return error_result

        except FileNotFoundError:
            logger.error("Photo not found: %s", photo_path, exc_info=True)
            error_result = {
                'error': 'Photo not found',
                'photo_path': str(photo_path)
            }
            with self._lock:
                self._stats['errors'] += 1
            return error_result

        except Exception as e:
            logger.error("Unexpected error processing %s: %s", photo_path, e, exc_info=True)
            error_result = {
                'error': 'Failed to process metadata',
                'photo_path': str(photo_path)
            }
            with self._lock:
                self._stats['errors'] += 1
            return error_result

    def _merge_exif_data(self, export_metadata: ExportMetadata, exif_data: dict) -> None:
        """Merge EXIF data into ExportMetadata.

        Args:
            export_metadata: ExportMetadata to update
            exif_data: EXIF data from MetadataService
        """
        # Camera info
        camera = exif_data.get('camera', {})
        export_metadata.camera_make = camera.get('make')
        export_metadata.camera_model = camera.get('model')

        # Capture info
        capture = exif_data.get('capture', {})
        export_metadata.timestamp = capture.get('timestamp')
        export_metadata.exposure_time = capture.get('exposure_time')
        export_metadata.iso = capture.get('iso')
        export_metadata.focal_length = capture.get('focal_length')

        # Location info
        location = exif_data.get('location', {})
        export_metadata.latitude = location.get('latitude')
        export_metadata.longitude = location.get('longitude')
        export_metadata.altitude = location.get('altitude')
        # Try both 'gps_accuracy' and 'hdop' (different services use different keys)
        export_metadata.gps_accuracy = location.get('gps_accuracy') or location.get('hdop')

        # Deployment info
        deployment = exif_data.get('deployment', {})
        export_metadata.mothbox_id = deployment.get('mothbox_id')
        export_metadata.firmware_version = deployment.get('firmware_version')

        # File info
        file_info = exif_data.get('file', {})
        export_metadata.file_size = file_info.get('size', 0)
        export_metadata.width = file_info.get('width')
        export_metadata.height = file_info.get('height')

    def _merge_sidecar_data(
        self,
        export_metadata: ExportMetadata,
        sidecar_data: SidecarMetadata
    ) -> None:
        """Merge sidecar data into ExportMetadata.

        Args:
            export_metadata: ExportMetadata to update
            sidecar_data: SidecarMetadata from SidecarService
        """
        # Handle both dataclass and dict-like objects
        if hasattr(sidecar_data, 'species'):
            export_metadata.species = sidecar_data.species
            export_metadata.species_common_name = sidecar_data.common_name
            export_metadata.species_confidence = sidecar_data.confidence
            export_metadata.tags = sidecar_data.tags if sidecar_data.tags else []
            export_metadata.notes = sidecar_data.notes
        elif isinstance(sidecar_data, dict):
            export_metadata.species = sidecar_data.get('species')
            export_metadata.species_common_name = sidecar_data.get('common_name')
            export_metadata.species_confidence = sidecar_data.get('confidence')
            export_metadata.tags = sidecar_data.get('tags', [])
            export_metadata.notes = sidecar_data.get('notes')

    # ========================================================================
    # Batch Processing
    # ========================================================================

    def batch_get_export_metadata(
        self,
        photo_paths: list[Path | str],
        stream: bool = False,
    ) -> list[ExportMetadata | dict] | Generator:
        """Get metadata for multiple photos.

        Args:
            photo_paths: List of photo paths
            stream: If True, yields results as generator

        Returns:
            List or generator of ExportMetadata/error dicts.
        """
        if stream:
            return self._batch_generator(photo_paths)
        else:
            return list(self._batch_generator(photo_paths))

    def _batch_generator(
        self,
        photo_paths: list[Path | str]
    ) -> Generator[ExportMetadata | dict]:
        """Generator for batch processing.

        Args:
            photo_paths: List of photo paths

        Yields:
            ExportMetadata or error dict for each photo
        """
        for photo_path in photo_paths:
            yield self.get_export_metadata(photo_path)

    # ========================================================================
    # Format Transformers
    # ========================================================================

    def transform_to_generic(
        self,
        metadata: ExportMetadata,
        flat: bool = False,
    ) -> dict:
        """Transform to generic JSON/CSV format.

        Args:
            metadata: ExportMetadata to transform
            flat: If True, flatten for CSV (no nested dicts)

        Returns:
            Dictionary with nested (JSON) or flat (CSV) structure
        """
        if flat:
            # Flatten for CSV - prefix nested fields
            return {
                'photo_path': metadata.photo_path,
                'filename': metadata.filename,
                'timestamp': metadata.timestamp,
                'latitude': metadata.latitude,
                'longitude': metadata.longitude,
                'altitude': metadata.altitude,
                'gps_accuracy': metadata.gps_accuracy,
                'camera_make': metadata.camera_make,
                'camera_model': metadata.camera_model,
                'exposure_time': metadata.exposure_time,
                'iso': metadata.iso,
                'focal_length': metadata.focal_length,
                'species': metadata.species,
                'species_common_name': metadata.species_common_name,
                'species_confidence': metadata.species_confidence,
                'tags': ','.join(metadata.tags) if metadata.tags else '',
                'notes': metadata.notes,
                'mothbox_id': metadata.mothbox_id,
                'firmware_version': metadata.firmware_version,
                'series_type': metadata.series_type,
                'series_index': metadata.series_index,
                'series_count': metadata.series_count,
                'file_size': metadata.file_size,
                'width': metadata.width,
                'height': metadata.height,
            }
        else:
            # Nested structure for JSON
            return {
                'file': {
                    'path': metadata.photo_path,
                    'filename': metadata.filename,
                    'file_size': metadata.file_size,
                    'width': metadata.width,
                    'height': metadata.height,
                },
                'location': {
                    'latitude': metadata.latitude,
                    'longitude': metadata.longitude,
                    'altitude': metadata.altitude,
                    'accuracy': metadata.gps_accuracy,
                },
                'camera': {
                    'make': metadata.camera_make,
                    'model': metadata.camera_model,
                    'exposure': metadata.exposure_time,
                    'iso': metadata.iso,
                    'focal_length': metadata.focal_length,
                },
                'species': {
                    'scientific_name': metadata.species,
                    'common_name': metadata.species_common_name,
                    'confidence': metadata.species_confidence,
                },
                'user_data': {
                    'tags': metadata.tags,
                    'notes': metadata.notes,
                },
                'deployment': {
                    'mothbox_id': metadata.mothbox_id,
                    'firmware_version': metadata.firmware_version,
                },
                'series': {
                    'type': metadata.series_type,
                    'index': metadata.series_index,
                    'count': metadata.series_count,
                },
                'timestamp': metadata.timestamp,
            }

    def transform_to_darwin_core(self, metadata: ExportMetadata) -> dict:
        """Transform to Darwin Core format.

        STUB: Raises NotImplementedError - full implementation in Issue #116.

        Args:
            metadata: ExportMetadata to transform

        Raises:
            NotImplementedError: Darwin Core transformer not yet implemented
        """
        raise NotImplementedError(
            "Darwin Core transformation will be implemented in Issue #116"
        )

    def transform_to_inaturalist(self, metadata: ExportMetadata) -> dict:
        """Transform to iNaturalist format.

        STUB: Raises NotImplementedError - full implementation in Issue #118.

        Args:
            metadata: ExportMetadata to transform

        Raises:
            NotImplementedError: iNaturalist transformer not yet implemented
        """
        raise NotImplementedError(
            "iNaturalist transformation will be implemented in Issue #118"
        )

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_for_format(
        self,
        metadata: ExportMetadata,
        format: ExportFormat,
    ) -> ValidationResult:
        """Validate metadata completeness for export format.

        Args:
            metadata: ExportMetadata to validate
            format: Target export format

        Returns:
            ValidationResult with validation status and missing fields
        """
        # Generic formats have no required fields
        if format in (ExportFormat.GENERIC_JSON, ExportFormat.GENERIC_CSV):
            return ValidationResult(is_valid=True)

        # Get required fields for format
        required = {
            ExportFormat.DARWIN_CORE: DARWIN_CORE_REQUIRED,
            ExportFormat.INATURALIST: INATURALIST_REQUIRED,
        }.get(format, [])

        # Check for missing fields
        missing = []
        for field_name in required:
            value = getattr(metadata, field_name, None)
            if value is None:
                missing.append(field_name)

        return ValidationResult(
            is_valid=len(missing) == 0,
            missing_fields=missing,
            warnings=[]
        )

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_statistics(self) -> dict:
        """Get service statistics.

        Returns:
            Dictionary with cache metrics and operation counts
        """
        with self._lock:
            return {
                'cache_entries': self._stats['cache_entries'],
                'cache_hits': self._stats['cache_hits'],
                'cache_misses': self._stats['cache_misses'],
                'total_exports': self._stats['total_exports'],
                'errors': self._stats['errors'],
            }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'ExportMetadataService',
    'ExportMetadata',
    'ValidationResult',
    'ExportFormat',
]
