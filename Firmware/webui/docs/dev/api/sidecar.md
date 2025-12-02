# Sidecar Metadata API Documentation

**Last Updated**: 2025-12-01
**Version**: v5.3.0 (Issue #107)
**Base URL**: `/api/sidecar`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Single Photo Endpoints](#single-photo-endpoints)
5. [Bulk Operations](#bulk-operations)
6. [Aggregation Endpoints](#aggregation-endpoints)
7. [Pagination Contract](#pagination-contract)
8. [TypeScript Interfaces](#typescript-interfaces)

---

## Overview

The Sidecar Metadata API provides CRUD operations for managing user-editable photo metadata stored in JSON sidecar files (`.meta.json`). This is separate from EXIF metadata which is embedded in photos and read-only.

**Key Features**:
- Create, read, update, delete sidecar metadata
- Bulk tag operations with append/replace modes
- Tag and species aggregation with counts
- Pagination and sorting support
- API key authentication for programmatic access

**Implementation**: `webui/backend/routes/sidecar.py` (663 lines)

**Related**:
- Library: `webui/backend/lib/sidecar_metadata.py`
- Service: `webui/backend/services/sidecar_service.py`
- Tests: `Tests/unit/test_metadata_crud_api.py` (55 tests)

---

## Authentication

Two authentication methods are supported:

### 1. CSRF Token (Web UI)
For browser-based access, include CSRF token in state-changing requests:
```http
X-CSRFToken: <token_from_/api/csrf-token>
```

### 2. API Key (Programmatic)
For scripts and external tools, use API key header:
```http
X-API-Key: <your-api-key>
```

Configure API key in `controls.txt`:
```
api_key=your-secure-api-key-here
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (validation error, invalid JSON, invalid parameters) |
| 403 | Forbidden (path traversal attempt) |
| 404 | Not Found (photo or sidecar doesn't exist) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Single Photo Endpoints

### GET /photos/{filename}

Get sidecar metadata for a single photo.

**Parameters**:
- `filename` (path): Photo filename (e.g., `moth_2024_01_15__10_30_00.jpg`)

**Response** (200 OK):
```json
{
  "version": "1.0",
  "photo_filename": "moth_2024_01_15__10_30_00.jpg",
  "created_at": "2024-01-15T10:30:00Z",
  "modified_at": "2024-01-15T14:20:00Z",
  "tags": ["moth", "night", "luna"],
  "species": "Actias luna",
  "notes": "Beautiful luna moth specimen",
  "custom": {},
  "modified_by": null
}
```

**Response when no sidecar exists** (200 OK):
```json
{
  "version": "1.0",
  "photo_filename": "photo.jpg",
  "created_at": null,
  "modified_at": null,
  "tags": [],
  "species": null,
  "notes": null,
  "custom": {},
  "modified_by": null
}
```

**Errors**:
- `404`: Photo file not found
- `403`: Path traversal blocked

**Example**:
```bash
curl http://localhost:5000/api/sidecar/photos/moth_2024_01_15__10_30_00.jpg
```

---

### PATCH /photos/{filename}

Update sidecar metadata for a photo. Creates sidecar if it doesn't exist.

**Parameters**:
- `filename` (path): Photo filename

**Request Body**:
```json
{
  "tags": ["moth", "night"],
  "species": "Actias luna",
  "notes": "Updated notes",
  "tag_mode": "append"
}
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `tags` | string[] | List of tags (max 50 chars each) |
| `species` | string | Species identification |
| `notes` | string | Free-form notes (max 10000 chars) |
| `custom` | object | Custom key-value pairs |
| `tag_mode` | string | "append" (default) or "replace" |

**Tag Modes**:
- `append`: Merges new tags with existing tags (preserves order, removes duplicates)
- `replace`: Overwrites all existing tags with new tags

**Response** (200 OK):
```json
{
  "version": "1.0",
  "photo_filename": "moth_2024_01_15__10_30_00.jpg",
  "tags": ["moth", "night", "luna"],
  "species": "Actias luna",
  "notes": "Updated notes",
  ...
}
```

**Errors**:
- `400`: Invalid JSON or validation error
- `404`: Photo file not found
- `403`: Path traversal blocked

**Examples**:
```bash
# With CSRF token
curl -X PATCH http://localhost:5000/api/sidecar/photos/photo.jpg \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{"tags": ["moth"], "species": "Actias luna"}'

# With API key
curl -X PATCH http://localhost:5000/api/sidecar/photos/photo.jpg \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"tags": ["moth"], "tag_mode": "replace"}'
```

---

### DELETE /photos/{filename}

Delete sidecar metadata for a photo.

**Parameters**:
- `filename` (path): Photo filename

**Response** (200 OK):
```json
{
  "success": true
}
```

**Errors**:
- `404`: Sidecar not found
- `403`: Path traversal blocked

**Example**:
```bash
curl -X DELETE http://localhost:5000/api/sidecar/photos/photo.jpg \
  -H "X-API-Key: <your-api-key>"
```

---

## Bulk Operations

### POST /bulk

Update metadata for multiple photos in a single request.

**Request Body**:
```json
{
  "filenames": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
  "updates": {
    "tags": ["moth", "night"],
    "species": "Actias luna"
  },
  "mode": "append"
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filenames` | string[] | Yes | List of photo filenames (max 100) |
| `updates` | object | Yes | Metadata updates to apply |
| `mode` | string | No | "append" (default) or "replace" for tags |

**Behavior**:
- Each file is processed independently (partial success allowed)
- For `mode: "append"`: Tags are merged, other fields are replaced
- For `mode: "replace"`: All fields including tags are replaced
- Files that don't exist are reported in `failed` list

**Response** (200 OK):
```json
{
  "success": ["photo1.jpg", "photo2.jpg"],
  "failed": ["photo3.jpg"],
  "errors": {
    "photo3.jpg": "Photo not found"
  },
  "total": 3,
  "successful": 2,
  "failed_count": 1
}
```

**Errors**:
- `400`: Invalid request (empty filenames, too many files, missing updates)

**Example**:
```bash
curl -X POST http://localhost:5000/api/sidecar/bulk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "filenames": ["photo1.jpg", "photo2.jpg"],
    "updates": {"tags": ["field_trip"]},
    "mode": "append"
  }'
```

---

## Aggregation Endpoints

### GET /tags

List all unique tags across all sidecar files with usage counts.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Items per page (max 200) |
| `sort` | string | "count" | Sort by "count" or "name" |
| `order` | string | "desc" | Sort order "asc" or "desc" |

**Response** (200 OK):
```json
{
  "tags": [
    {"name": "moth", "count": 45},
    {"name": "night", "count": 32},
    {"name": "luna", "count": 12}
  ],
  "total": 89,
  "pagination": {
    "page": 1,
    "per_page": 50,
    "has_next": true,
    "has_previous": false
  }
}
```

**Example**:
```bash
# Get top 20 tags by count
curl "http://localhost:5000/api/sidecar/tags?per_page=20&sort=count&order=desc"

# Get tags sorted alphabetically
curl "http://localhost:5000/api/sidecar/tags?sort=name&order=asc"
```

---

### GET /species

List all unique species across all sidecar files with usage counts.

**Query Parameters**: Same as `/tags`

**Response** (200 OK):
```json
{
  "species": [
    {"name": "Actias luna", "count": 12},
    {"name": "Antheraea polyphemus", "count": 8},
    {"name": "Automeris io", "count": 5}
  ],
  "total": 25,
  "pagination": {
    "page": 1,
    "per_page": 50,
    "has_next": false,
    "has_previous": false
  }
}
```

**Note**: Photos with `species: null` are excluded from results.

**Example**:
```bash
curl "http://localhost:5000/api/sidecar/species?sort=name"
```

---

## Pagination Contract

All list endpoints follow this pagination contract:

### Request Parameters
- `page`: 1-indexed page number (minimum: 1)
- `per_page`: Items per page (minimum: 1, maximum: 200, default: 50)

### Response Structure
```json
{
  "items": [...],
  "total": 150,
  "pagination": {
    "page": 2,
    "per_page": 50,
    "has_next": true,
    "has_previous": true
  }
}
```

### Validation
- `page < 1`: Returns 400 Bad Request
- `per_page > 200`: Automatically capped at 200
- `page > total_pages`: Returns empty items list (not an error)

---

## TypeScript Interfaces

```typescript
// Sidecar metadata structure
interface SidecarMetadata {
  version: string;
  photo_filename: string;
  created_at: string | null;
  modified_at: string | null;
  tags: string[];
  species: string | null;
  notes: string | null;
  custom: Record<string, unknown>;
  modified_by: string | null;
}

// PATCH request body
interface UpdateMetadataRequest {
  tags?: string[];
  species?: string;
  notes?: string;
  custom?: Record<string, unknown>;
  tag_mode?: 'append' | 'replace';
}

// Bulk update request
interface BulkUpdateRequest {
  filenames: string[];
  updates: UpdateMetadataRequest;
  mode?: 'append' | 'replace';
}

// Bulk update response
interface BulkUpdateResponse {
  success: string[];
  failed: string[];
  errors: Record<string, string>;
  total: number;
  successful: number;
  failed_count: number;
}

// Tag/Species aggregation item
interface AggregationItem {
  name: string;
  count: number;
}

// Pagination info
interface Pagination {
  page: number;
  per_page: number;
  has_next: boolean;
  has_previous: boolean;
}

// Tags response
interface TagsResponse {
  tags: AggregationItem[];
  total: number;
  pagination: Pagination;
}

// Species response
interface SpeciesResponse {
  species: AggregationItem[];
  total: number;
  pagination: Pagination;
}
```

---

## Performance Characteristics

| Endpoint | Time Complexity | Typical Response Time |
|----------|-----------------|----------------------|
| GET /photos/{filename} | O(1) | <10ms |
| PATCH /photos/{filename} | O(1) | <50ms |
| DELETE /photos/{filename} | O(1) | <10ms |
| POST /bulk (100 files) | O(n) | <500ms |
| GET /tags | O(n) | <100ms for 1000 sidecars |
| GET /species | O(n) | <100ms for 1000 sidecars |

**Notes**:
- Aggregation endpoints scan all sidecar files on each request
- For large collections (>10,000 photos), consider implementing caching
- Bulk operations are rate-limited to 10 requests/minute (planned)

---

## Related Documentation

- [Sidecar Metadata Format](../../../docs/SIDECAR_METADATA.md)
- [Gallery API](./gallery.md)
- [EXIF Metadata API](./metadata.md) (read-only EXIF extraction)
