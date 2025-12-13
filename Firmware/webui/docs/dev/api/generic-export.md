# Generic Export API

Generic JSON and CSV export endpoints for photo metadata. These endpoints provide flexible, human-readable export formats with field customization support.

## Overview

The generic export endpoints provide two output formats:

| Format | Description | Use Case |
|--------|-------------|----------|
| **JSON** | Nested structure preserving metadata hierarchy | Programmatic access, data interchange |
| **CSV** | Flat structure with one row per photo | Spreadsheets, simple data analysis |

Both formats support:
- Single photo, batch, and deployment-level exports
- Field filtering (include or exclude specific fields)
- Content negotiation via `Accept` header
- File download responses

## JSON Endpoints

### GET /api/export/json/{photo_path}

Export metadata for a single photo as JSON.

**Parameters:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| `photo_path` | string | path | Relative path to photo from photos directory |
| `fields` | string | query | Comma-separated list of fields to include |
| `exclude` | string | query | Comma-separated list of fields to exclude |

**Headers:**

| Header | Value | Effect |
|--------|-------|--------|
| `Accept: application/json` | Default | Returns JSON response body |
| `Accept: application/octet-stream` | File download | Returns `.json` file attachment |

**Example Request:**

```bash
# Get JSON response
curl -X GET "http://localhost:5000/api/export/json/2024/photo001.jpg" \
  -H "Accept: application/json"

# Get file download
curl -X GET "http://localhost:5000/api/export/json/2024/photo001.jpg" \
  -H "Accept: application/octet-stream" \
  -o photo001_metadata.json

# With field filtering
curl -X GET "http://localhost:5000/api/export/json/2024/photo001.jpg?fields=filename,location,species"
```

**Response (200 OK):**

```json
{
  "filename": "photo001.jpg",
  "photo_path": "2024/photo001.jpg",
  "capture": {
    "timestamp": "2024-06-15T14:30:00",
    "camera": {
      "make": "Arducam",
      "model": "OwlSight 64MP"
    },
    "settings": {
      "iso": 400,
      "aperture": 2.8,
      "shutter_speed": "1/250"
    }
  },
  "location": {
    "latitude": 35.9606,
    "longitude": -83.9207,
    "altitude": 350.5,
    "gps_accuracy": 2.5
  },
  "identification": {
    "species": "Actias luna",
    "common_name": "Luna Moth",
    "tags": ["moth", "saturniidae", "green"]
  },
  "notes": "Specimen in good condition",
  "deployment": {
    "name": "Oak Ridge Survey 2024",
    "mothbox_id": "mothbox-001"
  },
  "series": {
    "type": "hdr",
    "index": 0,
    "total": 3
  }
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Both `fields` and `exclude` specified |
| 403 | Path traversal attempt detected |
| 404 | Photo not found |

---

### POST /api/export/json/batch

Export metadata for multiple photos as a JSON array.

**Rate Limit:** 10 requests per minute

**Request Body:**

```json
{
  "photo_paths": ["2024/photo001.jpg", "2024/photo002.jpg"],
  "fields": ["filename", "location", "species"],
  "exclude": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `photo_paths` | array | Yes | List of photo paths to export |
| `fields` | array | No | Fields to include (mutually exclusive with `exclude`) |
| `exclude` | array | No | Fields to exclude (mutually exclusive with `fields`) |

**Headers:**

| Header | Value | Effect |
|--------|-------|--------|
| `Accept: application/json` | Default | Returns JSON response body |
| `Accept: application/octet-stream` | File download | Returns `.json` file attachment |

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/export/json/batch" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{
    "photo_paths": ["2024/photo001.jpg", "2024/photo002.jpg"],
    "fields": ["filename", "location", "species"]
  }'
```

**Response (200 OK):**

```json
{
  "results": [
    {
      "filename": "photo001.jpg",
      "location": { "latitude": 35.9606, "longitude": -83.9207 },
      "species": "Actias luna"
    },
    {
      "filename": "photo002.jpg",
      "location": { "latitude": 35.9610, "longitude": -83.9210 },
      "species": "Automeris io"
    }
  ],
  "total": 2,
  "successful": 2,
  "failed": 0,
  "errors": []
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Missing `photo_paths`, empty array, both `fields` and `exclude` specified, or batch size exceeded |
| 403 | Path traversal attempt in any photo path |

---

### GET /api/export/json/deployment/{deployment_path}

Export metadata for all photos in a deployment directory.

**Rate Limit:** 5 requests per minute

**Parameters:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| `deployment_path` | string | path | Relative path to deployment directory |
| `fields` | string | query | Comma-separated list of fields to include |
| `exclude` | string | query | Comma-separated list of fields to exclude |

**Headers:**

| Header | Value | Effect |
|--------|-------|--------|
| `Accept: application/json` | Default | Returns JSON response body |
| `Accept: application/octet-stream` | File download | Returns `.json` file attachment |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/export/json/deployment/forest_survey_2024" \
  -H "Accept: application/octet-stream" \
  -o forest_survey_metadata.json
```

**Response (200 OK):**

Same structure as batch export response.

---

## CSV Endpoints

### POST /api/export/csv/batch

Export metadata for multiple photos as CSV.

**Rate Limit:** 10 requests per minute

**Request Body:**

```json
{
  "photo_paths": ["2024/photo001.jpg", "2024/photo002.jpg"],
  "fields": ["filename", "latitude", "longitude", "species"],
  "exclude": null,
  "include_bom": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `photo_paths` | array | Yes | List of photo paths to export |
| `fields` | array | No | Fields to include |
| `exclude` | array | No | Fields to exclude |
| `include_bom` | boolean | No | Include UTF-8 BOM for Excel compatibility (default: false) |

**Headers:**

| Header | Value | Effect |
|--------|-------|--------|
| `Accept: application/json` | Returns JSON with embedded CSV | `{"csv_data": "..."}` |
| `Accept: text/csv` | File download | Returns `.csv` file attachment |

**Example Request:**

```bash
# Get CSV file download
curl -X POST "http://localhost:5000/api/export/csv/batch" \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -H "X-CSRFToken: <token>" \
  -d '{
    "photo_paths": ["2024/photo001.jpg", "2024/photo002.jpg"],
    "include_bom": true
  }' \
  -o photos.csv

# Get CSV as JSON response
curl -X POST "http://localhost:5000/api/export/csv/batch" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{"photo_paths": ["2024/photo001.jpg"]}'
```

**Response (Accept: text/csv):**

```csv
filename,photo_path,timestamp,latitude,longitude,altitude,gps_accuracy,species,common_name,tags,notes,deployment_name,mothbox_id,series_type,series_index
photo001.jpg,2024/photo001.jpg,2024-06-15T14:30:00,35.9606,-83.9207,350.5,2.5,Actias luna,Luna Moth,"moth,saturniidae,green",Good specimen,Oak Ridge Survey,mothbox-001,hdr,0
photo002.jpg,2024/photo002.jpg,2024-06-15T14:31:00,35.9610,-83.9210,352.0,2.3,Automeris io,Io Moth,"moth,saturniidae,yellow",,Oak Ridge Survey,mothbox-001,,
```

**Response (Accept: application/json):**

```json
{
  "csv_data": "filename,photo_path,...\nphoto001.jpg,...",
  "total": 2,
  "successful": 2,
  "failed": 0
}
```

---

### GET /api/export/csv/deployment/{deployment_path}

Export metadata for all photos in a deployment directory as CSV.

**Rate Limit:** 5 requests per minute

**Parameters:**

| Name | Type | Location | Description |
|------|------|----------|-------------|
| `deployment_path` | string | path | Relative path to deployment directory |
| `fields` | string | query | Comma-separated list of fields to include |
| `exclude` | string | query | Comma-separated list of fields to exclude |
| `include_bom` | boolean | query | Include UTF-8 BOM (default: false) |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/export/csv/deployment/forest_2024?include_bom=true" \
  -H "Accept: text/csv" \
  -o forest_2024.csv
```

---

## Field Reference

The following fields are available for filtering. Use these names with `fields` or `exclude` parameters.

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Photo filename |
| `photo_path` | string | Relative path from photos directory |
| `timestamp` | string | Capture timestamp (ISO 8601) |

### Location Fields

| Field | Type | Description |
|-------|------|-------------|
| `latitude` | number | GPS latitude (decimal degrees) |
| `longitude` | number | GPS longitude (decimal degrees) |
| `altitude` | number | GPS altitude (meters) |
| `gps_accuracy` | number | GPS horizontal accuracy (HDOP) |

### Camera Fields

| Field | Type | Description |
|-------|------|-------------|
| `camera_make` | string | Camera manufacturer |
| `camera_model` | string | Camera model |
| `iso` | integer | ISO sensitivity |
| `aperture` | number | Aperture (f-number) |
| `shutter_speed` | string | Shutter speed |
| `focal_length` | number | Focal length (mm) |

### Identification Fields

| Field | Type | Description |
|-------|------|-------------|
| `species` | string | Scientific species name |
| `common_name` | string | Common species name |
| `tags` | array/string | Photo tags (array in JSON, comma-separated in CSV) |
| `notes` | string | User notes |

### Deployment Fields

| Field | Type | Description |
|-------|------|-------------|
| `deployment_name` | string | Deployment name |
| `mothbox_id` | string | Mothbox device ID |
| `firmware_version` | string | Firmware version |

### Series Fields

| Field | Type | Description |
|-------|------|-------------|
| `series_type` | string | Series type (hdr, focus_bracket, or null) |
| `series_index` | integer | Index within series |
| `series_total` | integer | Total photos in series |

---

## Field Filtering

### Include Mode

Only export specified fields:

```bash
# Query parameter (single photo, deployment)
?fields=filename,latitude,longitude,species

# Request body (batch)
{"photo_paths": [...], "fields": ["filename", "latitude", "longitude", "species"]}
```

### Exclude Mode

Export all fields except specified:

```bash
# Query parameter
?exclude=notes,tags,camera_make,camera_model

# Request body
{"photo_paths": [...], "exclude": ["notes", "tags"]}
```

### Rules

1. Cannot use both `fields` and `exclude` together (returns 400 error)
2. Unknown field names are silently ignored
3. For nested JSON: filtering applies to all levels
4. For flat CSV: filtering applies to column headers

---

## Response Formats

### JSON Response Structure

When `Accept: application/json` is specified:

**Single Photo:**
```json
{
  "filename": "...",
  "capture": { ... },
  "location": { ... },
  "identification": { ... },
  ...
}
```

**Batch/Deployment:**
```json
{
  "results": [ ... ],
  "total": 10,
  "successful": 9,
  "failed": 1,
  "errors": [
    {"photo_path": "missing.jpg", "error": "Photo not found"}
  ]
}
```

### File Download

When `Accept: application/octet-stream` (JSON) or `Accept: text/csv` (CSV):

- `Content-Type`: `application/json` or `text/csv; charset=utf-8`
- `Content-Disposition`: `attachment; filename="<name>_<timestamp>.<ext>"`

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error message describing the problem"
}
```

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Invalid request (missing fields, validation error) |
| 403 | Path traversal attempt or access denied |
| 404 | Photo or deployment not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Partial Failures

Batch operations continue processing even if some photos fail. Failed photos are reported in the `errors` array:

```json
{
  "results": [ ... ],
  "total": 10,
  "successful": 8,
  "failed": 2,
  "errors": [
    {"photo_path": "missing1.jpg", "error": "Photo not found"},
    {"photo_path": "bad/path", "error": "Invalid path"}
  ]
}
```

---

## Code Examples

### Python

```python
import requests

BASE_URL = "http://localhost:5000/api/export"

# Get CSRF token first
session = requests.Session()
csrf_resp = session.get(f"{BASE_URL.replace('/api/export', '/api/csrf-token')}")
csrf_token = csrf_resp.json()["csrf_token"]

# Single photo JSON export
response = requests.get(
    f"{BASE_URL}/json/2024/photo001.jpg",
    params={"fields": "filename,species,latitude,longitude"}
)
metadata = response.json()
print(f"Species: {metadata.get('species')}")

# Batch JSON export
response = session.post(
    f"{BASE_URL}/json/batch",
    headers={"X-CSRFToken": csrf_token},
    json={
        "photo_paths": ["2024/photo001.jpg", "2024/photo002.jpg"],
        "exclude": ["notes", "tags"]
    }
)
result = response.json()
print(f"Exported {result['successful']} of {result['total']} photos")

# Deployment CSV download
response = requests.get(
    f"{BASE_URL}/csv/deployment/forest_2024",
    headers={"Accept": "text/csv"},
    params={"include_bom": "true"}
)
with open("forest_2024.csv", "wb") as f:
    f.write(response.content)
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:5000/api/export';

// Get CSRF token
async function getCsrfToken() {
  const resp = await fetch('/api/csrf-token');
  const data = await resp.json();
  return data.csrf_token;
}

// Single photo JSON export
async function exportSinglePhoto(photoPath, fields = null) {
  const params = new URLSearchParams();
  if (fields) params.set('fields', fields.join(','));

  const response = await fetch(
    `${BASE_URL}/json/${photoPath}?${params}`,
    { credentials: 'include' }
  );
  return response.json();
}

// Batch JSON export
async function exportBatchJson(photoPaths, options = {}) {
  const csrfToken = await getCsrfToken();

  const response = await fetch(`${BASE_URL}/json/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify({
      photo_paths: photoPaths,
      fields: options.fields,
      exclude: options.exclude
    })
  });

  return response.json();
}

// Deployment CSV download
async function downloadDeploymentCsv(deploymentPath) {
  const response = await fetch(
    `${BASE_URL}/csv/deployment/${deploymentPath}?include_bom=true`,
    {
      headers: { 'Accept': 'text/csv' },
      credentials: 'include'
    }
  );

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `${deploymentPath.replace('/', '_')}.csv`;
  a.click();

  URL.revokeObjectURL(url);
}

// Usage
const metadata = await exportSinglePhoto('2024/photo001.jpg', ['filename', 'species']);
console.log(metadata);

const batch = await exportBatchJson(
  ['2024/photo001.jpg', '2024/photo002.jpg'],
  { exclude: ['notes'] }
);
console.log(`Exported ${batch.successful} photos`);
```

---

## Related Documentation

- [Darwin Core Export API](./export.md#darwin-core-endpoints) - GBIF-compatible export format
- [iNaturalist Export API](./export.md#inaturalist-endpoints) - iNaturalist-compatible ZIP export
- [Deployment Metadata API](./deployment.md) - Deployment-level metadata management
- [Gallery API](./gallery.md) - Photo listing and series detection
