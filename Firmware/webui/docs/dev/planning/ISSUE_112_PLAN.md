# Implementation Plan: Issue #112 - Export Metadata Service

**Issue**: [#112 - Create export metadata service for EXIF/GPS extraction](https://github.com/zane-lazare/Mothbox/issues/112)
**Phase**: 5 (Export System)
**Estimated Effort**: 2 days
**Dependencies**: Foundation for #114, #116, #118, #120

---

## Executive Summary

The Export Metadata Service aggregates photo metadata from multiple sources (MetadataService, SidecarService, SeriesService) into a unified, export-ready format. It serves as the foundation for Phase 5 Export System, enabling downstream exporters (Darwin Core, iNaturalist, JSON/CSV) to work with normalized, validated data.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Export Metadata Service                    │
│  (webui/backend/services/export_metadata_service.py)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ MetadataService │  │ SidecarService  │  │SeriesService ││
│  │ (EXIF data)     │  │ (User data)     │  │(HDR/FB info) ││
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘│
│           │                    │                   │        │
│           └────────────────────┴───────────────────┘        │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │ Aggregator  │                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│           ┌───────────────┼───────────────┐                 │
│           │               │               │                 │
│     ┌─────▼─────┐  ┌──────▼──────┐ ┌─────▼──────┐          │
│     │Darwin Core│  │ iNaturalist │ │Generic JSON│          │
│     │Transformer│  │ Transformer │ │Transformer │          │
│     └───────────┘  └─────────────┘ └────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Subtask 1: Create Test File with Core Test Cases (TDD Red Phase)

**File**: `Tests/unit/test_export_metadata_service.py`

### Test Classes to Implement:

| Test Class | Purpose | Test Count |
|------------|---------|------------|
| `TestExportMetadataDataClass` | Data class structure validation | 3 |
| `TestExportMetadataServiceInit` | Service initialization | 3 |
| `TestGetExportMetadata` | Single photo extraction | 8 |
| `TestBatchGetExportMetadata` | Batch processing | 5 |
| `TestDarwinCoreTransformer` | Darwin Core format | 5 |
| `TestINaturalistTransformer` | iNaturalist format | 4 |
| `TestGenericTransformer` | JSON/CSV format | 3 |
| `TestValidation` | Metadata validation | 4 |
| `TestCaching` | Cache behavior | 4 |
| `TestThreadSafety` | Concurrent access | 2 |
| `TestErrorHandling` | Error scenarios | 3 |

### Required Fixtures:
- `temp_photos_dir` - Temporary directory with sample photos
- `mock_metadata_service` - Mocked MetadataService
- `mock_sidecar_service` - Mocked SidecarService
- `mock_series_service` - Mocked SeriesService
- `service` - ExportMetadataService with mocked dependencies
- `sample_exif_metadata` - Representative EXIF data
- `sample_sidecar_metadata` - Representative sidecar data

---

## Subtask 2: Create Export Metadata Service Core

**File**: `webui/backend/services/export_metadata_service.py`

### Data Classes:

```python
@dataclass
class ExportMetadata:
    """Aggregated photo metadata for export."""
    photo_path: str
    filename: str
    timestamp: str | None

    # Location
    latitude: float | None
    longitude: float | None
    altitude: float | None
    gps_accuracy: float | None

    # Camera
    camera_make: str | None
    camera_model: str | None
    exposure_time: str | None
    iso: int | None
    focal_length: str | None

    # Identification
    species: str | None
    species_common_name: str | None
    species_confidence: str | None

    # User data
    tags: list[str]
    notes: str | None

    # Deployment
    mothbox_id: str | None
    firmware_version: str | None

    # Series
    series_type: str | None
    series_index: int | None
    series_count: int | None

    # File
    file_size: int
    width: int | None
    height: int | None

@dataclass
class ValidationResult:
    """Result of metadata validation."""
    is_valid: bool
    missing_fields: list[str]
    warnings: list[str]

class ExportFormat(Enum):
    """Supported export formats."""
    DARWIN_CORE = "darwin_core"
    INATURALIST = "inaturalist"
    GENERIC_JSON = "json"
    GENERIC_CSV = "csv"
```

### Service Class:

```python
class ExportMetadataService:
    def __init__(
        self,
        cache_ttl: int = 300,
        metadata_service: MetadataService | None = None,
        sidecar_service: SidecarService | None = None,
        series_service: SeriesService | None = None,
    ): ...

    def get_export_metadata(self, photo_path: Path | str) -> ExportMetadata | dict: ...
    def batch_get_export_metadata(self, photo_paths: list, stream: bool = False) -> list | Generator: ...
    def transform_to_darwin_core(self, metadata: ExportMetadata) -> dict: ...
    def transform_to_inaturalist(self, metadata: ExportMetadata) -> dict: ...
    def transform_to_generic(self, metadata: ExportMetadata, flat: bool = False) -> dict: ...
    def validate_for_format(self, metadata: ExportMetadata, format: ExportFormat) -> ValidationResult: ...
    def invalidate_cache(self, key: str | None = None) -> None: ...
    def get_statistics(self) -> dict: ...
```

---

## Subtask 3: Implement Metadata Aggregation

### Core Methods:

| Method | Purpose | Performance Target |
|--------|---------|-------------------|
| `get_export_metadata()` | Single photo extraction | <100ms |
| `batch_get_export_metadata()` | Batch processing | >10 photos/sec |
| `_aggregate_metadata()` | Combine sources | <50ms |
| `_get_exif_metadata()` | Get EXIF via MetadataService | <30ms |
| `_get_sidecar_metadata()` | Get user data via SidecarService | <10ms |
| `_get_series_info()` | Get series via SeriesService | <10ms |

### Source Integration:
1. **MetadataService** → camera, location, capture, deployment, file
2. **SidecarService** → tags, species, notes, custom fields
3. **SeriesService** → series_type, series_index, series_count

---

## Subtask 4: Implement Export Format Transformers

### Darwin Core Mapping:

| Darwin Core Field | Source | Required |
|-------------------|--------|----------|
| `occurrenceID` | Generated from mothbox_id + filename | Yes |
| `eventDate` | timestamp | Yes |
| `decimalLatitude` | latitude | Yes |
| `decimalLongitude` | longitude | Yes |
| `geodeticDatum` | "WGS84" (constant) | Yes |
| `basisOfRecord` | "MachineObservation" (constant) | Yes |
| `scientificName` | species | No |
| `vernacularName` | species_common_name | No |
| `coordinateUncertaintyInMeters` | Calculated from gps_accuracy | No |

### iNaturalist Mapping:

| iNaturalist Field | Source | Required |
|-------------------|--------|----------|
| `observed_on` | timestamp (date only) | Yes |
| `latitude` | latitude | Yes |
| `longitude` | longitude | Yes |
| `species_guess` | species_common_name or species | No |
| `description` | notes | No |
| `tag_list` | tags (comma-separated) | No |

### Generic JSON/CSV:
- All fields included
- Optional flattening for CSV compatibility

---

## Subtask 5: Create API Routes

**File**: `webui/backend/routes/export.py`

### Endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/export/metadata/<path>` | GET | Single photo metadata |
| `/api/export/metadata/batch` | POST | Batch metadata (rate limited) |
| `/api/export/formats` | GET | List supported formats |
| `/api/export/transform` | POST | Transform to format |
| `/api/export/validate` | POST | Validate for format |
| `/api/export/stats` | GET | Service statistics |

### Registration in app.py:
```python
from routes.export import export_bp
app.register_blueprint(export_bp, url_prefix="/api/export")
app.config['EXPORT_METADATA_SERVICE'] = ExportMetadataService()
```

---

## Subtask 6: Integration Tests & Validation

**Files**:
- `Tests/integration/test_export_metadata_workflow.py`
- `Tests/performance/test_export_metadata_performance.py`

### Integration Tests:
- Complete metadata extraction workflow
- Darwin Core export end-to-end
- iNaturalist export end-to-end
- Batch export of 100+ photos
- Series metadata inclusion
- API endpoint integration

### Performance Tests:
- Single photo <100ms
- Batch >10 photos/sec
- Cache hit <10ms
- Transform <1ms
- Memory <50MB for 100 photos

### Coverage Verification:
```bash
pytest Tests/unit/test_export_metadata_service.py -v \
  --cov=webui/backend/services/export_metadata_service \
  --cov-report=term-missing
coverage report --fail-under=85
```

---

## Execution Order

```
1. Subtask 1: Create tests (TDD red phase)
   └── Tests fail because no implementation

2. Subtask 2: Create service skeleton
   └── Data classes and method stubs

3. Subtask 3: Implement aggregation
   └── Core tests start passing

4. Subtask 4: Implement transformers
   └── Format tests start passing

5. Subtask 5: Create API routes
   └── Integration with Flask app

6. Subtask 6: Integration tests
   └── Verify 85%+ coverage
```

---

## Success Criteria

- [ ] Service handles all Mothbox photo formats (.jpg, .jpeg)
- [ ] GPS data properly formatted and validated
- [ ] Metadata extraction <100ms per photo
- [ ] Unit test coverage ≥85%
- [ ] Darwin Core output validates against GBIF schema
- [ ] iNaturalist output includes required observation fields
- [ ] Batch processing supports 100+ photos
- [ ] Thread-safe with caching

---

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `Tests/unit/test_export_metadata_service.py` | Create | Unit tests |
| `webui/backend/services/export_metadata_service.py` | Create | Core service |
| `webui/backend/routes/export.py` | Create | API routes |
| `webui/backend/app.py` | Modify | Register blueprint |
| `Tests/integration/test_export_metadata_workflow.py` | Create | Integration tests |
| `Tests/performance/test_export_metadata_performance.py` | Create | Performance tests |

---

**Plan Created**: 2025-12-11
**Status**: Ready for implementation
