"""
Export Metadata Service for Mothbox Photo Gallery (Issue #112)

Provides aggregated metadata for photo exports by combining data from:
- MetadataService: EXIF data (camera, location, capture settings)
- SidecarService: User annotations (tags, species, notes)
- SeriesService: Series detection (HDR, focus bracket)
- DeploymentService: Deployment context (location, time period, environmental conditions)

Thread-safe with configurable TTL caching for performance.

Architecture:
- Thin wrapper over existing services (no business logic duplication)
- Generic JSON/CSV transformer implemented
- Darwin Core transformer implemented (Issue #116)
- iNaturalist transformer implemented (Issue #118)

Usage:
    from webui.backend.services.export_metadata_service import (
        ExportMetadataService,
        ExportFormat,
    )

    service = ExportMetadataService(cache_ttl=300)

    # Single photo
    metadata = service.get_export_metadata("/photos/moth_2024_01_15__10_00_00.jpg")
    # metadata includes: EXIF, sidecar, series, and deployment context

    # Access deployment context
    print(f"Deployment: {metadata.deployment_name}")
    print(f"Location: {metadata.deployment_location_name}")
    print(f"Period: {metadata.deployment_start_date} to {metadata.deployment_end_date}")
    print(f"Environment: {metadata.environmental_conditions}")

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
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from webui.backend.services.metadata_service import MetadataService
from webui.backend.services.sidecar_service import SidecarMetadata, SidecarService

if TYPE_CHECKING:
    from webui.backend.lib.zip_export import ZipExportOptions, ZipExportResult
    from webui.backend.services.deployment_service import DeploymentService
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
    - Deployment context from DeploymentService (location, time period, environment)
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

    # Deployment (EXIF-level)
    mothbox_id: str | None = None
    firmware_version: str | None = None

    # Deployment (Context-level from DeploymentService)
    deployment_name: str | None = None
    deployment_location_name: str | None = None
    deployment_start_date: str | None = None
    deployment_end_date: str | None = None
    environmental_conditions: dict = field(default_factory=dict)

    # Series
    series_type: str | None = None  # "hdr" or "focus_bracket" or None
    series_index: int | None = None
    series_count: int | None = None

    # File
    file_size: int = 0
    width: int | None = None
    height: int | None = None

    # Country (for Darwin Core export)
    country_code: str | None = None  # ISO 3166-1 alpha-2


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
DARWIN_CORE_REQUIRED = ["latitude", "longitude", "timestamp"]
INATURALIST_REQUIRED = ["latitude", "longitude", "timestamp"]
GENERIC_REQUIRED = []  # No required fields for generic


class ExportMetadataService:
    """
    Service for aggregating photo metadata for export operations.

    Thread-safe with configurable TTL caching.
    """

    def __init__(
        self,
        cache_ttl: int = 300,
        max_cache_size: int = 500,
        metadata_service: MetadataService | None = None,
        sidecar_service: SidecarService | None = None,
        series_service: "SeriesService | None" = None,
        deployment_service: "DeploymentService | None" = None,
    ):
        """Initialize with optional dependency injection for testing.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
            max_cache_size: Maximum cache entries before LRU eviction (default 500)
            metadata_service: MetadataService instance (or None for lazy load)
            sidecar_service: SidecarService instance (or None for lazy load)
            series_service: SeriesService instance (or None for lazy load)
            deployment_service: DeploymentService instance (or None for lazy load)
        """
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size
        self._cache: dict[str, tuple[ExportMetadata, float]] = {}
        self._lock = threading.RLock()
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_entries": 0,
            "total_exports": 0,
            "errors": 0,
        }

        # Lazy-loaded services
        self._metadata_service = metadata_service
        self._sidecar_service = sidecar_service
        self._series_service = series_service
        self._deployment_service = deployment_service

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

    def _get_deployment_service(self) -> "DeploymentService":
        """Get DeploymentService instance (lazy load if needed)."""
        if self._deployment_service is None:
            from webui.backend.services.deployment_service import DeploymentService

            self._deployment_service = DeploymentService(cache_ttl=300)
        return self._deployment_service

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
                    self._stats["cache_hits"] += 1
                    return metadata
                # Expired - remove
                del self._cache[key]
                self._stats["cache_entries"] = len(self._cache)
            self._stats["cache_misses"] += 1
            return None

    def _add_to_cache(self, key: str, metadata: ExportMetadata) -> None:
        """Add metadata to cache with LRU eviction.

        Args:
            key: Cache key (photo path)
            metadata: ExportMetadata to cache
        """
        with self._lock:
            # Evict oldest entry if at capacity (LRU eviction)
            if len(self._cache) >= self._max_cache_size and key not in self._cache:
                # Materialize items to avoid race condition during iteration
                items = list(self._cache.items())
                oldest_key = min(items, key=lambda item: item[1][1])[0]
                del self._cache[oldest_key]

            self._cache[key] = (metadata, time.time())
            self._stats["cache_entries"] = len(self._cache)

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
            self._stats["cache_entries"] = len(self._cache)

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
            self._stats["total_exports"] += 1

        # Fail fast: Check if file exists before processing
        if not photo_path.exists():
            error_result = {"error": "Photo not found", "photo_path": str(photo_path)}
            with self._lock:
                self._stats["errors"] += 1
            return error_result

        try:
            # Initialize result with required fields
            export_metadata = ExportMetadata(
                photo_path=str(photo_path),
                filename=photo_path.name,
            )

            # Get EXIF metadata
            try:
                exif_data = self._get_metadata_service().get_photo_metadata(photo_path)
                if exif_data and "error" not in exif_data:
                    self._merge_exif_data(export_metadata, exif_data)
            except PermissionError as e:
                logger.warning("Failed to get EXIF metadata for %s: %s", photo_path.name, e)
                with self._lock:
                    self._stats["errors"] += 1
                return {"error": "Permission denied", "photo_path": str(photo_path)}
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
                            series_id, directory=photo_path.parent
                        )
                        if series_data:
                            export_metadata.series_count = series_data.count
            except Exception as e:
                logger.warning("Failed to get series info for %s: %s", photo_path.name, e)

            # Get deployment metadata
            try:
                deployment_service = self._get_deployment_service()
                deployment = deployment_service.find_deployment_for_photo(photo_path)
                if deployment:
                    export_metadata.deployment_name = deployment.deployment_name
                    export_metadata.deployment_location_name = deployment.location_name
                    export_metadata.deployment_start_date = deployment.start_date
                    export_metadata.deployment_end_date = deployment.end_date
                    export_metadata.environmental_conditions = deployment.environmental or {}
            except Exception as e:
                logger.warning("Failed to get deployment metadata for %s: %s", photo_path.name, e)

            # Detect country code from GPS coordinates
            try:
                from webui.backend.lib.country_code import detect_country_code

                export_metadata.country_code = detect_country_code(
                    export_metadata.latitude, export_metadata.longitude
                )
            except Exception as e:
                logger.warning("Failed to detect country code for %s: %s", photo_path.name, e)

            # Cache the result
            self._add_to_cache(cache_key, export_metadata)

            return export_metadata

        except FileNotFoundError:
            logger.error("Photo not found: %s", photo_path, exc_info=True)
            error_result = {"error": "Photo not found", "photo_path": str(photo_path)}
            with self._lock:
                self._stats["errors"] += 1
            return error_result

        except Exception as e:
            logger.error("Unexpected error processing %s: %s", photo_path, e, exc_info=True)
            error_result = {"error": "Failed to process metadata", "photo_path": str(photo_path)}
            with self._lock:
                self._stats["errors"] += 1
            return error_result

    def _merge_exif_data(self, export_metadata: ExportMetadata, exif_data: dict) -> None:
        """Merge EXIF data into ExportMetadata.

        Args:
            export_metadata: ExportMetadata to update
            exif_data: EXIF data from MetadataService
        """
        # Camera info
        camera = exif_data.get("camera", {})
        export_metadata.camera_make = camera.get("make")
        export_metadata.camera_model = camera.get("model")

        # Capture info (includes dimensions)
        capture = exif_data.get("capture", {})
        export_metadata.timestamp = capture.get("timestamp")
        export_metadata.exposure_time = capture.get("exposure_time")
        export_metadata.iso = capture.get("iso")
        export_metadata.focal_length = capture.get("focal_length")
        export_metadata.width = capture.get("width")
        export_metadata.height = capture.get("height")

        # Location info
        location = exif_data.get("location", {})
        export_metadata.latitude = location.get("latitude")
        export_metadata.longitude = location.get("longitude")
        export_metadata.altitude = location.get("altitude")
        # Try both 'gps_accuracy' and 'hdop' (different services use different keys)
        # Use explicit None check to handle gps_accuracy=0 (valid value) correctly
        gps_accuracy = location.get("gps_accuracy")
        export_metadata.gps_accuracy = (
            gps_accuracy if gps_accuracy is not None else location.get("hdop")
        )

        # Deployment info
        deployment = exif_data.get("deployment", {})
        export_metadata.mothbox_id = deployment.get("mothbox_id")
        export_metadata.firmware_version = deployment.get("firmware_version")

        # File info
        file_info = exif_data.get("file", {})
        export_metadata.file_size = file_info.get("size", 0)

    def _merge_sidecar_data(
        self, export_metadata: ExportMetadata, sidecar_data: SidecarMetadata
    ) -> None:
        """Merge sidecar data into ExportMetadata.

        Args:
            export_metadata: ExportMetadata to update
            sidecar_data: SidecarMetadata from SidecarService
        """
        # Handle both dataclass and dict-like objects
        if hasattr(sidecar_data, "species"):
            export_metadata.species = sidecar_data.species
            export_metadata.species_common_name = sidecar_data.common_name
            export_metadata.species_confidence = sidecar_data.confidence
            export_metadata.tags = sidecar_data.tags if sidecar_data.tags else []
            export_metadata.notes = sidecar_data.notes
        elif isinstance(sidecar_data, dict):
            export_metadata.species = sidecar_data.get("species")
            export_metadata.species_common_name = sidecar_data.get("common_name")
            export_metadata.species_confidence = sidecar_data.get("confidence")
            export_metadata.tags = sidecar_data.get("tags", [])
            export_metadata.notes = sidecar_data.get("notes")

    # ========================================================================
    # Batch Processing
    # ========================================================================

    def batch_get_export_metadata(
        self,
        photo_paths: list[Path | str],
        stream: bool = False,
    ) -> list[ExportMetadata | dict] | Generator[ExportMetadata | dict]:
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

    def _batch_generator(self, photo_paths: list[Path | str]) -> Generator[ExportMetadata | dict]:
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

    def _apply_gps_precision(self, value: float | None, precision: int | None) -> float | None:
        """Apply GPS precision rounding to a coordinate value.

        Args:
            value: Coordinate value (latitude or longitude)
            precision: Number of decimal places (0-6), None for no rounding.
                      The UI enforces 0-6 range. Values outside this range
                      are technically valid (uses Python's round()) but
                      0=111km, 6=0.11m covers practical use cases.

        Returns:
            Rounded coordinate or original if precision is None
        """
        if value is None or precision is None:
            return value
        return round(value, precision)

    def transform_to_generic(
        self,
        metadata: ExportMetadata,
        flat: bool = False,
        gps_precision: int | None = None,
    ) -> dict:
        """Transform to generic JSON/CSV format.

        Args:
            metadata: ExportMetadata to transform
            flat: If True, flatten for CSV (no nested dicts)
            gps_precision: GPS coordinate precision (0-6 decimals), None for full precision

        Returns:
            Dictionary with nested (JSON) or flat (CSV) structure
        """
        # Apply GPS precision if specified
        latitude = self._apply_gps_precision(metadata.latitude, gps_precision)
        longitude = self._apply_gps_precision(metadata.longitude, gps_precision)

        if flat:
            # Flatten for CSV - prefix nested fields
            return {
                "photo_path": metadata.photo_path,
                "filename": metadata.filename,
                "timestamp": metadata.timestamp,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": metadata.altitude,
                "gps_accuracy": metadata.gps_accuracy,
                "camera_make": metadata.camera_make,
                "camera_model": metadata.camera_model,
                "exposure_time": metadata.exposure_time,
                "iso": metadata.iso,
                "focal_length": metadata.focal_length,
                "species": metadata.species,
                "species_common_name": metadata.species_common_name,
                "species_confidence": metadata.species_confidence,
                "tags": ",".join(metadata.tags) if metadata.tags else "",
                "notes": metadata.notes,
                "mothbox_id": metadata.mothbox_id,
                "firmware_version": metadata.firmware_version,
                "deployment_name": metadata.deployment_name,
                "deployment_location_name": metadata.deployment_location_name,
                "deployment_start_date": metadata.deployment_start_date,
                "deployment_end_date": metadata.deployment_end_date,
                "environmental_conditions": str(metadata.environmental_conditions)
                if metadata.environmental_conditions
                else "",
                "series_type": metadata.series_type,
                "series_index": metadata.series_index,
                "series_count": metadata.series_count,
                "file_size": metadata.file_size,
                "width": metadata.width,
                "height": metadata.height,
            }
        else:
            # Nested structure for JSON
            return {
                "file": {
                    "path": metadata.photo_path,
                    "filename": metadata.filename,
                    "file_size": metadata.file_size,
                    "width": metadata.width,
                    "height": metadata.height,
                },
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "altitude": metadata.altitude,
                    "accuracy": metadata.gps_accuracy,
                },
                "camera": {
                    "make": metadata.camera_make,
                    "model": metadata.camera_model,
                    "exposure": metadata.exposure_time,
                    "iso": metadata.iso,
                    "focal_length": metadata.focal_length,
                },
                "species": {
                    "scientific_name": metadata.species,
                    "common_name": metadata.species_common_name,
                    "confidence": metadata.species_confidence,
                },
                "user_data": {
                    "tags": metadata.tags,
                    "notes": metadata.notes,
                },
                "deployment": {
                    "mothbox_id": metadata.mothbox_id,
                    "firmware_version": metadata.firmware_version,
                    "name": metadata.deployment_name,
                    "location_name": metadata.deployment_location_name,
                    "start_date": metadata.deployment_start_date,
                    "end_date": metadata.deployment_end_date,
                    "environmental": metadata.environmental_conditions,
                },
                "series": {
                    "type": metadata.series_type,
                    "index": metadata.series_index,
                    "count": metadata.series_count,
                },
                "timestamp": metadata.timestamp,
            }

    def transform_to_generic_filtered(
        self,
        metadata: ExportMetadata,
        flat: bool = False,
        fields: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> dict:
        """Transform to generic format with optional field filtering.

        Args:
            metadata: ExportMetadata to transform
            flat: If True, flatten for CSV (no nested dicts)
            fields: If provided, only include these fields (for nested: top-level
                    sections like 'file', 'location', or leaf fields like 'filename')
            exclude: If provided, exclude these fields

        Returns:
            Filtered dictionary

        Raises:
            ValueError: If both fields and exclude are provided

        Example:
            >>> # Include only specific fields
            >>> data = service.transform_to_generic_filtered(
            ...     metadata, flat=False, fields=["filename", "latitude", "longitude"]
            ... )

            >>> # Exclude specific fields
            >>> data = service.transform_to_generic_filtered(
            ...     metadata, flat=True, exclude=["notes", "tags"]
            ... )
        """
        if fields is not None and exclude is not None:
            raise ValueError("Cannot specify both 'fields' and 'exclude' parameters")

        # Get full transform first
        full_data = self.transform_to_generic(metadata, flat=flat)

        # No filtering requested
        if fields is None and exclude is None:
            return full_data

        if flat:
            # For flat structure, filter directly by field names
            if fields is not None:
                return {k: v for k, v in full_data.items() if k in fields}
            else:  # exclude is not None
                return {k: v for k, v in full_data.items() if k not in exclude}
        else:
            # For nested structure, need to handle section and leaf field filtering
            return self._filter_nested_dict(full_data, fields, exclude)

    def _filter_nested_dict(
        self,
        data: dict,
        fields: list[str] | None,
        exclude: list[str] | None,
    ) -> dict:
        """Filter a nested dictionary based on field names.

        Supports:
        - Top-level section names (e.g., 'file', 'location', 'camera')
        - Leaf field names (e.g., 'filename', 'latitude')
        - Dotted paths (e.g., 'file.filename', 'location.latitude')

        Args:
            data: Nested dictionary to filter
            fields: Fields to include (None means include all)
            exclude: Fields to exclude (None means exclude none)

        Returns:
            Filtered dictionary
        """
        if fields is not None:
            return self._include_fields(data, fields)
        else:  # exclude is not None
            return self._exclude_fields(data, exclude)

    def _include_fields(self, data: dict, fields: list[str]) -> dict:
        """Include only specified fields in nested dictionary."""
        result = {}

        # Build a set of section names and leaf names for quick lookup
        field_set = set(fields)

        for key, value in data.items():
            if key in field_set:
                # Include entire section
                result[key] = value
            elif isinstance(value, dict):
                # Check if any leaf fields in this section are requested
                section_result = {}
                for leaf_key, leaf_value in value.items():
                    if leaf_key in field_set:
                        section_result[leaf_key] = leaf_value
                    # Check dotted path (e.g., 'file.filename')
                    dotted = f"{key}.{leaf_key}"
                    if dotted in field_set:
                        section_result[leaf_key] = leaf_value
                if section_result:
                    result[key] = section_result
            else:
                # Top-level non-dict field (like timestamp)
                if key in field_set:
                    result[key] = value

        return result

    def _exclude_fields(self, data: dict, exclude: list[str]) -> dict:
        """Exclude specified fields from nested dictionary."""
        result = {}
        exclude_set = set(exclude)

        for key, value in data.items():
            if key in exclude_set:
                # Skip entire section
                continue
            elif isinstance(value, dict):
                # Filter fields within section
                section_result = {}
                for leaf_key, leaf_value in value.items():
                    if leaf_key not in exclude_set:
                        dotted = f"{key}.{leaf_key}"
                        if dotted not in exclude_set:
                            section_result[leaf_key] = leaf_value
                if section_result:
                    result[key] = section_result
            else:
                # Top-level non-dict field
                result[key] = value

        return result

    def transform_to_darwin_core(self, metadata: ExportMetadata) -> dict:
        """Transform to Darwin Core format for GBIF-compatible export.

        Maps Mothbox metadata fields to Darwin Core standard terms.
        See https://dwc.tdwg.org/terms/ for Darwin Core term definitions.

        Args:
            metadata: ExportMetadata to transform

        Returns:
            Dictionary with Darwin Core term names as keys

        Example:
            >>> dwc = service.transform_to_darwin_core(metadata)
            >>> dwc["basisOfRecord"]
            'MachineObservation'
        """
        from webui.backend.lib.darwin_core_mapping import transform_metadata_to_darwin_core

        return transform_metadata_to_darwin_core(metadata)

    def transform_batch_to_darwin_core_csv(
        self,
        metadata_list: list[ExportMetadata],
        filter_invalid: bool = True,
    ) -> tuple[list[str], list[list[str]]]:
        """Transform multiple ExportMetadata to Darwin Core CSV format.

        Returns headers and rows ready for CSV generation. Optionally filters
        out photos without valid GPS coordinates (GBIF strict mode).

        Args:
            metadata_list: List of ExportMetadata instances to transform
            filter_invalid: If True, exclude photos without GPS coordinates

        Returns:
            Tuple of (headers, rows) where:
            - headers: List of Darwin Core term names for CSV header
            - rows: List of lists containing string values for each row

        Example:
            >>> headers, rows = service.transform_batch_to_darwin_core_csv(metadata_list)
            >>> len(rows) <= len(metadata_list)
            True
        """
        from webui.backend.lib.darwin_core_mapping import (
            get_csv_headers,
            is_valid_for_export,
            transform_to_csv_row,
        )

        headers = get_csv_headers()
        rows = []

        for metadata in metadata_list:
            # Skip invalid photos if filtering is enabled
            if filter_invalid and not is_valid_for_export(metadata):
                continue
            rows.append(transform_to_csv_row(metadata))

        return headers, rows

    def transform_batch_to_inaturalist_zip(
        self,
        photo_paths: list[Path],
        output_path: Path | None = None,
        options: "ZipExportOptions | None" = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> "ZipExportResult":
        """Export multiple photos as iNaturalist ZIP with XMP sidecars.

        Creates a ZIP archive containing:
        - Original photos (uncompressed)
        - XMP sidecar files with iNaturalist-compatible metadata
        - manifest.json with collection metadata
        - summary.csv with tabular data

        Args:
            photo_paths: List of paths to photos to export
            output_path: Path for output ZIP file. If None, uses temp file.
            options: ZipExportOptions for customization
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            ZipExportResult with success status and statistics

        Raises:
            ValueError: If photo_paths is empty
        """
        from webui.backend.lib.zip_export import (
            ZipExportOptions,
            create_zip_export,
        )

        if not photo_paths:
            raise ValueError("photo_paths cannot be empty")

        # Get metadata for all photos
        metadata_list = self.batch_get_export_metadata(photo_paths)

        # Use temp file if output_path not provided
        if output_path is None:
            import tempfile

            # Create temp file securely, then use its path for ZIP creation
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_fd:
                output_path = Path(temp_fd.name)

        # Create ZIP with default options if not provided
        if options is None:
            options = ZipExportOptions()

        return create_zip_export(
            photo_paths, metadata_list, output_path, options, progress_callback
        )

    def transform_to_inaturalist(self, metadata: ExportMetadata) -> dict:
        """Transform to iNaturalist format.

        Maps Mothbox metadata fields to iNaturalist-compatible structure
        for XMP sidecar generation and observation data.

        Args:
            metadata: ExportMetadata to transform

        Returns:
            dict with iNaturalist-compatible fields including:
            - title: "Common Name (Scientific Name)"
            - notes: Combined notes and tags
            - latitude, longitude: GPS coordinates
            - timestamp: ISO 8601 datetime
            - quality_grade: Mapped from species_confidence
            - taxonomy_keywords: Hierarchical taxonomy for dc:subject
            - license: Default CC BY-NC 4.0
            - creator: Default "Mothbox"
        """
        from webui.backend.lib.inaturalist_mapping import transform_metadata_to_inaturalist

        return transform_metadata_to_inaturalist(metadata)

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

        # Darwin Core has comprehensive validation
        if format == ExportFormat.DARWIN_CORE:
            return self._validate_darwin_core(metadata)

        # iNaturalist has comprehensive validation
        if format == ExportFormat.INATURALIST:
            return self._validate_inaturalist(metadata)

        # Unknown format - return generic validation
        return ValidationResult(is_valid=True)

    def _validate_darwin_core(self, metadata: ExportMetadata) -> ValidationResult:
        """Comprehensive validation for Darwin Core export.

        Validates:
        - Required fields presence (GPS coordinates required - GBIF strict mode)
        - Coordinate ranges (lat: -90 to 90, lon: -180 to 180)
        - ISO 8601 date format

        Args:
            metadata: ExportMetadata to validate

        Returns:
            ValidationResult with validation status, missing fields, and warnings
        """
        missing_fields = []
        warnings = []

        # Required: GPS coordinates (GBIF strict mode)
        if metadata.latitude is None:
            missing_fields.append("decimalLatitude (GPS latitude required for GBIF)")
        elif not (-90 <= metadata.latitude <= 90):
            missing_fields.append(
                f"decimalLatitude (invalid range: {metadata.latitude}, must be -90 to 90)"
            )

        if metadata.longitude is None:
            missing_fields.append("decimalLongitude (GPS longitude required for GBIF)")
        elif not (-180 <= metadata.longitude <= 180):
            missing_fields.append(
                f"decimalLongitude (invalid range: {metadata.longitude}, must be -180 to 180)"
            )

        # Required: Event date/time
        if not metadata.timestamp:
            missing_fields.append("eventDate (timestamp required for GBIF)")

        # Recommended: Scientific name
        if not metadata.species:
            warnings.append(
                "scientificName not provided - record may have limited value for biodiversity research"
            )

        # Recommended: GPS accuracy
        if metadata.gps_accuracy is None:
            warnings.append(
                "coordinateUncertaintyInMeters not provided - GPS accuracy recommended for GBIF"
            )

        return ValidationResult(
            is_valid=len(missing_fields) == 0,
            missing_fields=missing_fields,
            warnings=warnings,
        )

    def _validate_inaturalist(self, metadata: ExportMetadata) -> ValidationResult:
        """Validate metadata for iNaturalist export.

        Checks:
        - Required fields: latitude, longitude, timestamp
        - Valid coordinate ranges (-90 to 90 for lat, -180 to 180 for lon)
        - Warns for missing species/common_name

        Args:
            metadata: ExportMetadata to validate

        Returns:
            ValidationResult with validation status and details
        """
        from webui.backend.lib.inaturalist_mapping import validate_for_inaturalist

        # Use the library's validation function
        lib_result = validate_for_inaturalist(metadata)

        # Convert library's ValidationResult to service's ValidationResult
        # Note: Both have the same structure, but different imports
        return ValidationResult(
            is_valid=lib_result.is_valid,
            missing_fields=lib_result.missing_required,
            warnings=lib_result.warnings
            + [f"Missing recommended: {', '.join(lib_result.missing_recommended)}"]
            if lib_result.missing_recommended
            else lib_result.warnings,
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
                "cache_entries": self._stats["cache_entries"],
                "cache_hits": self._stats["cache_hits"],
                "cache_misses": self._stats["cache_misses"],
                "total_exports": self._stats["total_exports"],
                "errors": self._stats["errors"],
            }

    def reset_statistics(self) -> None:
        """Reset all statistics counters to zero.

        Useful for long-running services to prevent unbounded counter growth.
        Cache entries count is preserved as it reflects actual cache state.
        """
        with self._lock:
            self._stats["cache_hits"] = 0
            self._stats["cache_misses"] = 0
            self._stats["total_exports"] = 0
            self._stats["errors"] = 0
            # Note: cache_entries is not reset - it reflects actual cache size
            logger.debug("Reset export metadata service statistics")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ExportMetadataService",
    "ExportMetadata",
    "ValidationResult",
    "ExportFormat",
]
