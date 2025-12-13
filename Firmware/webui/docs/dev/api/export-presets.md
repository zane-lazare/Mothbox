# Export Presets API Documentation

**Last Updated**: 2025-12-14
**Version**: Issue #123 Implementation
**Base URL**: `/api/export/presets`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Preset Schema](#preset-schema)
5. [Built-in Presets](#built-in-presets)
6. [Export Preset Endpoints](#export-preset-endpoints)
7. [Usage with Export Jobs](#usage-with-export-jobs)
8. [Usage Examples](#usage-examples)

---

## Overview

The Export Presets API provides management of reusable export configurations. Presets store export format, filter criteria, and format-specific options that can be applied when creating export jobs.

**Key Features**:
- Built-in presets for common export scenarios (GBIF, iNaturalist, JSON, CSV)
- User-defined presets stored in filesystem
- Preset application during job creation with override support
- Protected built-in presets (read-only)
- Unified preset namespace (`CONFIG_DIR/presets/{built-in,user}/export/`)

**Implementation**:
- `webui/backend/routes/export_presets.py` - REST API endpoints
- `webui/backend/export_preset_manager.py` - Preset management service
- `webui/backend/lib/export_preset_types.py` - Type definitions
- `webui/backend/presets_builtin/export/` - Built-in preset JSON files

---

## Authentication

**Current Status**: CSRF protection required for state-changing operations

**Security Measures**:
- CSRF tokens required for POST/DELETE endpoints
- Input validation for all parameters
- Protected built-in presets (cannot be modified or deleted)

---

## Error Responses

### Standard Error Format

All error responses follow this JSON structure:

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 201 | Created | Preset created successfully |
| 400 | Bad Request | Invalid parameters, validation error |
| 403 | Forbidden | CSRF validation failed |
| 404 | Not Found | Preset not found |
| 500 | Internal Server Error | Unexpected server error |

---

## Preset Schema

### ExportPreset Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier (alphanumeric + underscore, max 50 chars) |
| `display_name` | string | Yes | Human-readable name (max 100 chars) |
| `export_format` | string | Yes | Export format: `darwin_core`, `inaturalist`, `json`, `csv` |
| `description` | string | No | Description of the preset |
| `version` | string | No | Preset version (default: "1.0") |
| `created_at` | string | No | ISO 8601 timestamp |
| `author` | string | No | Author identifier (default: "user") |
| `category` | string | Auto | Preset category: `built-in` or `user` |
| `filter` | object | No | ExportJobFilter criteria |
| `options` | object | No | Format-specific options |

### ExportJobFilter Fields

| Field | Type | Description |
|-------|------|-------------|
| `date_start` | string | Start date (YYYY-MM-DD) |
| `date_end` | string | End date (YYYY-MM-DD) |
| `deployment` | string | Deployment directory path |
| `tags` | array | List of tags to match |
| `series_type` | string | `hdr` or `focus_bracket` |
| `has_species` | boolean | Only photos with species ID |
| `photo_paths` | array | Explicit photo paths |

### Example Preset JSON

```json
{
  "name": "gbif_biodiversity",
  "display_name": "GBIF Biodiversity Export",
  "export_format": "darwin_core",
  "description": "Darwin Core export for GBIF submission. Requires species identification.",
  "version": "1.0",
  "category": "built-in",
  "filter": {
    "has_species": true
  },
  "options": {
    "validate": true
  }
}
```

---

## Built-in Presets

The system includes 6 built-in presets located in `webui/backend/presets_builtin/export/`:

| Name | Format | Description | Filter |
|------|--------|-------------|--------|
| `gbif_biodiversity` | darwin_core | Export for GBIF/iDigBio submission | `has_species: true` |
| `inaturalist_upload` | inaturalist | iNaturalist-compatible export with XMP sidecars | `has_species: true`, `include_xmp: true` |
| `simple_json` | json | Generic JSON metadata export | None |
| `simple_csv` | csv | Excel-compatible CSV with UTF-8 BOM | `include_bom: true` |
| `hdr_series` | json | HDR photo series export | `series_type: hdr` |
| `focus_bracket_series` | json | Focus bracket series export | `series_type: focus_bracket` |

Built-in presets are **read-only** and cannot be modified or deleted.

---

## Export Preset Endpoints

### 1. List Export Presets

List all available export presets (built-in + user).

**Endpoint**: `GET /api/export/presets`

**Implementation**: `webui/backend/routes/export_presets.py`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | string | No | Filter by export format |

#### Response

**Success (200)**:

```json
{
  "presets": [
    {
      "name": "gbif_biodiversity",
      "display_name": "GBIF Biodiversity Export",
      "export_format": "darwin_core",
      "category": "built-in",
      "description": "Export for GBIF/iDigBio submission"
    },
    {
      "name": "my_custom_preset",
      "display_name": "My Custom Preset",
      "export_format": "json",
      "category": "user",
      "description": "Custom preset for my workflow"
    }
  ],
  "counts": {
    "built_in": 6,
    "user": 1,
    "total": 7
  }
}
```

#### Examples

```bash
# List all presets
curl "http://localhost:5000/api/export/presets"

# List only Darwin Core presets
curl "http://localhost:5000/api/export/presets?format=darwin_core"

# List only JSON presets
curl "http://localhost:5000/api/export/presets?format=json"
```

---

### 2. Get Export Preset

Get detailed configuration for a specific preset.

**Endpoint**: `GET /api/export/presets/<name>`

**Implementation**: `webui/backend/routes/export_presets.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Preset name |

#### Response

**Success (200)**:

```json
{
  "name": "gbif_biodiversity",
  "display_name": "GBIF Biodiversity Export",
  "export_format": "darwin_core",
  "description": "Darwin Core export for GBIF submission. Requires species identification.",
  "version": "1.0",
  "created_at": "",
  "author": "system",
  "category": "built-in",
  "filter": {
    "date_start": null,
    "date_end": null,
    "deployment": null,
    "tags": null,
    "series_type": null,
    "has_species": true,
    "photo_paths": null
  },
  "options": {
    "validate": true
  }
}
```

**Error (404)**:

```json
{
  "error": "Preset 'nonexistent' not found"
}
```

#### Examples

```bash
# Get specific preset
curl "http://localhost:5000/api/export/presets/gbif_biodiversity"

# Get user preset
curl "http://localhost:5000/api/export/presets/my_custom_preset"
```

---

### 3. Create Export Preset

Create a new user export preset.

**Endpoint**: `POST /api/export/presets`

**Implementation**: `webui/backend/routes/export_presets.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "name": "my_moth_export",
  "display_name": "My Moth Export",
  "export_format": "json",
  "description": "Custom export for moth photos",
  "filter": {
    "tags": ["moth"],
    "has_species": true
  },
  "options": {
    "pretty_print": true
  }
}
```

**Required Fields**:
- `name`: Unique identifier (alphanumeric + underscore)
- `display_name`: Human-readable name
- `export_format`: Export format

#### Response

**Success (201)**:

```json
{
  "success": true,
  "message": "Preset saved successfully",
  "name": "my_moth_export"
}
```

**Error (400)**:

```json
{
  "error": "Preset name is required"
}
```

```json
{
  "error": "Invalid export_format. Must be one of: ['darwin_core', 'inaturalist', 'json', 'csv']"
}
```

```json
{
  "error": "Cannot create preset with built-in category"
}
```

#### Examples

```bash
# Create user preset
curl -X POST "http://localhost:5000/api/export/presets" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "name": "summer_moths",
    "display_name": "Summer Moth Export",
    "export_format": "darwin_core",
    "description": "Export moths captured during summer months",
    "filter": {
      "tags": ["moth", "nocturnal"],
      "has_species": true
    }
  }'
```

---

### 4. Delete Export Preset

Delete a user export preset.

**Endpoint**: `DELETE /api/export/presets/<name>`

**Implementation**: `webui/backend/routes/export_presets.py`

**Note**: Built-in presets cannot be deleted.

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Preset name to delete |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "success": true,
  "message": "Preset 'my_custom_preset' deleted successfully"
}
```

**Error (400 - Built-in preset)**:

```json
{
  "error": "Cannot delete built-in presets"
}
```

**Error (404 - Not found)**:

```json
{
  "error": "Preset 'nonexistent' not found"
}
```

#### Examples

```bash
# Delete user preset
curl -X DELETE "http://localhost:5000/api/export/presets/my_custom_preset" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

## Usage with Export Jobs

Presets can be applied when creating export jobs via the `preset` parameter.

### Basic Usage

```bash
# Create job using preset
curl -X POST "http://localhost:5000/api/export/jobs" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "preset": "gbif_biodiversity"
  }'
```

### Override Preset Values

Explicit values override preset defaults:

```bash
# Use preset but override format
curl -X POST "http://localhost:5000/api/export/jobs" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "preset": "simple_json",
    "format": "csv",
    "filter": {
      "date_start": "2024-01-01"
    }
  }'
```

### Merge Behavior

When using a preset with explicit values:

1. **Format**: Explicit format overrides preset format
2. **Filter**: Explicit filter fields are merged with preset filter (explicit wins for same field)
3. **Options**: Explicit options are merged with preset options (explicit wins for same key)

**Example**:

Preset `simple_csv` has:
- `filter.has_species: false`
- `options.include_bom: true`

Request:
```json
{
  "preset": "simple_csv",
  "filter": {
    "date_start": "2024-01-01"
  },
  "options": {
    "delimiter": ";"
  }
}
```

Resulting job:
- `filter.has_species: false` (from preset)
- `filter.date_start: "2024-01-01"` (from request)
- `options.include_bom: true` (from preset)
- `options.delimiter: ";"` (from request)

---

## Usage Examples

### JavaScript/React

```javascript
// List all presets
const listPresets = async () => {
  const response = await fetch('/api/export/presets');
  const data = await response.json();
  return data.presets;
};

// Create preset
const createPreset = async (preset) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  const response = await fetch('/api/export/presets', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify(preset)
  });

  return response.json();
};

// Create job using preset
const createJobWithPreset = async (presetName, additionalFilters) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  const response = await fetch('/api/export/jobs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({
      preset: presetName,
      filter: additionalFilters
    })
  });

  return response.json();
};

// Usage
await createPreset({
  name: 'my_preset',
  display_name: 'My Preset',
  export_format: 'json',
  filter: { tags: ['moth'] }
});

await createJobWithPreset('my_preset', { date_start: '2024-01-01' });
```

### Python

```python
import requests

class ExportPresetClient:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()

        # Get CSRF token
        response = self.session.get(f"{base_url}/api/csrf-token")
        self.csrf_token = response.json()['csrf_token']

    def list_presets(self, format_filter: str | None = None) -> list:
        """List all presets."""
        url = f"{self.base_url}/api/export/presets"
        if format_filter:
            url += f"?format={format_filter}"

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()['presets']

    def get_preset(self, name: str) -> dict:
        """Get preset by name."""
        response = self.session.get(
            f"{self.base_url}/api/export/presets/{name}"
        )
        response.raise_for_status()
        return response.json()

    def create_preset(self, preset: dict) -> dict:
        """Create new user preset."""
        response = self.session.post(
            f"{self.base_url}/api/export/presets",
            json=preset,
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()

    def delete_preset(self, name: str) -> dict:
        """Delete user preset."""
        response = self.session.delete(
            f"{self.base_url}/api/export/presets/{name}",
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()

    def create_job_with_preset(
        self,
        preset_name: str,
        additional_filter: dict | None = None
    ) -> dict:
        """Create export job using preset."""
        payload = {"preset": preset_name}
        if additional_filter:
            payload["filter"] = additional_filter

        response = self.session.post(
            f"{self.base_url}/api/export/jobs",
            json=payload,
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()


# Usage
client = ExportPresetClient()

# List built-in presets
presets = client.list_presets()
for p in presets:
    print(f"{p['name']}: {p['display_name']} ({p['category']})")

# Create custom preset
client.create_preset({
    "name": "my_moths",
    "display_name": "My Moth Export",
    "export_format": "json",
    "filter": {"tags": ["moth"], "has_species": True}
})

# Create job using preset
job = client.create_job_with_preset(
    "my_moths",
    {"date_start": "2024-06-01", "date_end": "2024-08-31"}
)
print(f"Created job: {job['job_id']}")
```

---

## Related Documentation

- **Export Jobs API**: `webui/docs/dev/api/export-jobs.md` - Job creation and management
- **Preset Types**: `webui/backend/lib/export_preset_types.py` - Type definitions
- **Preset Manager**: `webui/backend/export_preset_manager.py` - Preset CRUD operations
- **Job Types**: `webui/backend/lib/export_job_types.py` - ExportJobFilter schema
- **Testing**: `Tests/unit/test_export_preset_*.py` - Unit tests

---

**Document Version**: 1.0.0
**Last Validated**: 2025-12-14
**Issue**: #123 - Export Preset Save/Load System
