# Darwin Core Export API

## Overview

The Mothbox Photo Gallery supports exporting photo metadata in Darwin Core (DwC) format, the biodiversity data standard maintained by TDWG (Biodiversity Information Standards). This enables researchers to share occurrence data with the Global Biodiversity Information Facility (GBIF) and other biodiversity data repositories.

**Related Issue:** [#116](https://github.com/zane-lazare/Mothbox/issues/116)

## Darwin Core Standard

Darwin Core is a standard for sharing biodiversity occurrence data. Each photo in Mothbox represents a single occurrence record - an observation of a species at a specific time and place.

**Key Resources:**
- [Darwin Core Quick Reference](https://dwc.tdwg.org/terms/)
- [GBIF Darwin Core Guide](https://ipt.gbif.org/manual/en/ipt/latest/dwca-guide)

## API Endpoints

### Single Photo Export

```http
GET /api/export/metadata/<photo_path>?format=darwin_core
```

Export a single photo's metadata in Darwin Core format.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| photo_path | path | Yes | Relative path to photo file |
| format | query | No | `json`, `csv`, or `darwin_core` (default: `json`) |

**Response (200):**
```json
{
  "occurrenceID": "mothbox:oak-ridge-2024:a1b2c3d4",
  "basisOfRecord": "MachineObservation",
  "eventDate": "2024-01-15T10:30:00",
  "decimalLatitude": 37.7749,
  "decimalLongitude": -122.4194,
  "geodeticDatum": "WGS84",
  "scientificName": "Actias luna",
  "vernacularName": "Luna Moth",
  "identificationQualifier": "",
  "coordinateUncertaintyInMeters": 2.5,
  "occurrenceStatus": "present",
  "recordedBy": "Mothbox",
  "associatedMedia": "/photos/moth_2024_01_15.jpg",
  "_warnings": ["coordinateUncertaintyInMeters not provided - GPS accuracy recommended for GBIF"]
}
```

**Error Responses:**
- `400`: Darwin Core validation failed (missing GPS coordinates or timestamp)
- `403`: Invalid path (path traversal attempt)
- `404`: Photo not found
- `500`: Internal error

### Batch Export

```http
POST /api/export/darwin-core/batch
```

Export multiple photos as Darwin Core CSV. Supports dual response format based on `Accept` header.

**Request Body:**
```json
{
  "photo_paths": ["photo1.jpg", "subdir/photo2.jpg"],
  "validate": true,
  "include_warnings": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| photo_paths | array | Yes | List of relative photo paths |
| validate | boolean | No | Skip photos without GPS (default: true) |
| include_warnings | boolean | No | Include validation warnings (default: false) |

**Response Format:**

Based on `Accept` header:

**`Accept: application/json` (default):**
```json
{
  "csv_data": "occurrenceID,basisOfRecord,...\nmothbox:...,MachineObservation,...",
  "headers": ["occurrenceID", "basisOfRecord", ...],
  "row_count": 150,
  "total_requested": 200,
  "exported": 150,
  "skipped": 50,
  "validation_errors": [
    {"photo_path": "no_gps.jpg", "error": "Darwin Core validation failed", "missing_fields": ["decimalLatitude"]}
  ]
}
```

**`Accept: text/csv`:**
```
Returns CSV file download with Content-Disposition header
```

**Rate Limit:** 5 requests per minute

### Deployment Export

```http
GET /api/export/darwin-core/deployment/<deployment_path>
```

Export all photos in a deployment directory as Darwin Core CSV.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| deployment_path | path | Yes | Relative path to deployment directory |
| validate | query | No | Skip photos without GPS (default: true) |
| include_warnings | query | No | Include validation warnings (default: false) |

**Response Format:**

Same as batch export - based on `Accept` header.

**Rate Limit:** 5 requests per minute

---

## Field Mapping Reference

### Required Fields (GBIF)

| Darwin Core Term | Mothbox Source | Description |
|-----------------|----------------|-------------|
| `occurrenceID` | *computed* | Unique ID: `mothbox:{deployment}:{hash}` |
| `basisOfRecord` | *constant* | `MachineObservation` |
| `eventDate` | `timestamp` | ISO 8601 datetime |
| `decimalLatitude` | `latitude` | GPS latitude (-90 to 90) |
| `decimalLongitude` | `longitude` | GPS longitude (-180 to 180) |
| `geodeticDatum` | *constant* | `WGS84` |

### Recommended Fields

| Darwin Core Term | Mothbox Source | Description |
|-----------------|----------------|-------------|
| `scientificName` | `species` | Scientific name |
| `vernacularName` | `species_common_name` | Common name |
| `coordinateUncertaintyInMeters` | `gps_accuracy` | GPS accuracy in meters |
| `identificationQualifier` | `species_confidence` | Confidence qualifier |
| `occurrenceStatus` | *constant* | `present` |
| `recordedBy` | *constant* | `Mothbox` |
| `associatedMedia` | `photo_path` | Photo file path |

### Collection Fields

| Darwin Core Term | Mothbox Source | Description |
|-----------------|----------------|-------------|
| `institutionCode` | *constant* | `Mothbox` |
| `collectionCode` | `deployment_name` | Deployment identifier |
| `catalogNumber` | `filename` | Photo filename |

---

## Species Confidence Mapping

The Mothbox species confidence levels map to Darwin Core identification qualifiers:

| Mothbox Confidence | Darwin Core Qualifier | Meaning |
|-------------------|----------------------|---------|
| `certain` | *(empty)* | Confident identification |
| `probable` | `cf.` | Compare with (confer) |
| `possible` | `aff.` | Affinity with (related to) |
| `unknown` | `?` | Uncertain |

---

## Occurrence ID Format

Occurrence IDs are deterministic and unique:

```
mothbox:{deployment_name}:{filename_hash}
```

**Example:** `mothbox:oak-ridge-2024:a1b2c3d4`

- `deployment_name`: Sanitized deployment name (lowercase, hyphens)
- `filename_hash`: SHA-256 hash of `{deployment}:{filename}` (first 8 characters)

The same photo always generates the same occurrence ID, enabling consistent exports and updates.

---

## GBIF Submission Guide

### Validation Requirements

Photos are validated before export. **Required for GBIF:**

1. **GPS coordinates** - `latitude` and `longitude` must be present and within valid ranges
2. **Timestamp** - `timestamp` must be present (ISO 8601 format)

Photos without GPS coordinates are **excluded** from export by default (GBIF strict mode).

### Generated CSV Format

The CSV export follows the Darwin Core Archive (DwC-A) simple CSV format:

1. UTF-8 encoding
2. Comma-separated values
3. First row contains Darwin Core term names
4. Each subsequent row represents one occurrence

### Example Workflow

```bash
# 1. Export deployment to CSV
curl -X GET \
  'http://localhost:5000/api/export/darwin-core/deployment/2024/oak-ridge?validate=true' \
  -H 'Accept: text/csv' \
  -o darwin_core_export.csv

# 2. Validate with GBIF validator (external tool)
# https://www.gbif.org/tools/data-validator

# 3. Upload to GBIF via IPT (Integrated Publishing Toolkit)
```

### Handling Photos Without GPS

If some photos lack GPS coordinates:

1. **Default behavior (validate=true):** Photos without GPS are skipped. The `validation_errors` array lists skipped photos.

2. **Include all (validate=false):** All photos are included, but records without coordinates will fail GBIF validation.

**Recommendation:** Ensure Mothbox GPS is enabled during capture for GBIF-compatible exports.

---

## Error Handling

### Validation Errors

```json
{
  "error": "Darwin Core validation failed",
  "missing_fields": [
    "decimalLatitude (GPS latitude required for GBIF)",
    "decimalLongitude (GPS longitude required for GBIF)"
  ],
  "warnings": []
}
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Darwin Core validation failed` | Missing GPS | Enable GPS on Mothbox |
| `Invalid path` | Path traversal attempt | Use relative paths only |
| `No photos found` | Empty deployment | Check deployment directory |

---

## Code Examples

### Python

```python
import requests

# Single photo
response = requests.get(
    'http://localhost:5000/api/export/metadata/moth_2024_01_15.jpg',
    params={'format': 'darwin_core'}
)
dwc_record = response.json()

# Batch export (JSON)
response = requests.post(
    'http://localhost:5000/api/export/darwin-core/batch',
    json={
        'photo_paths': ['photo1.jpg', 'photo2.jpg'],
        'validate': True
    }
)
data = response.json()
csv_data = data['csv_data']

# Batch export (CSV file)
response = requests.post(
    'http://localhost:5000/api/export/darwin-core/batch',
    json={'photo_paths': ['photo1.jpg', 'photo2.jpg']},
    headers={'Accept': 'text/csv'}
)
with open('export.csv', 'w') as f:
    f.write(response.text)
```

### JavaScript

```javascript
// Single photo
const response = await fetch(
  '/api/export/metadata/moth_2024_01_15.jpg?format=darwin_core'
);
const dwcRecord = await response.json();

// Batch export
const response = await fetch('/api/export/darwin-core/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  body: JSON.stringify({
    photo_paths: ['photo1.jpg', 'photo2.jpg'],
    validate: true
  })
});
const data = await response.json();
console.log(`Exported ${data.row_count} records`);
```

---

## Related Documentation

- [Export Metadata Service](../services/export-metadata-service.md)
- [Sidecar Metadata Schema](../schemas/sidecar-metadata.md)
- [Deployment Metadata Schema](../schemas/deployment-metadata.md)
