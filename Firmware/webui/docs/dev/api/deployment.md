# Deployment Metadata API Documentation

**Last Updated**: 2025-12-12
**Version**: Issue #114 Implementation
**Base URL**: `/api/deployment`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Deployment Metadata Endpoints](#deployment-metadata-endpoints)
5. [Discovery Endpoints](#discovery-endpoints)
6. [Batch Operations](#batch-operations)
7. [Cache Management](#cache-management)
8. [Schema Reference](#schema-reference)
9. [Performance Characteristics](#performance-characteristics)

---

## Overview

The Deployment Metadata API provides endpoints for managing deployment-level metadata files that describe entire photo collections. Deployment metadata includes location, time period, environmental conditions, and custom fields at the directory level.

**Key Features**:
- Hierarchical discovery (walk up directory tree to find nearest deployment metadata)
- Atomic read-modify-write operations with file locking
- JSON and YAML format support
- Thread-safe LRU cache with configurable TTL
- Batch operations for multiple deployments
- Path traversal protection

**Implementation**: `webui/backend/routes/deployment.py` (1153 lines)

---

## Authentication

**Current Status**: CSRF protection required for state-changing operations

**Security Measures**:
- CSRF tokens required for POST/PUT/PATCH/DELETE endpoints
- Path traversal protection on all file operations
- Input validation for coordinates, dates, and custom fields
- Sanitized error messages (no stack trace exposure)
- Rate limiting on batch operations (10/minute)

**Future** (Issue #175): API key authentication planned

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
| 400 | Bad Request | Invalid parameters, validation error |
| 403 | Forbidden | Invalid path, CSRF validation failed |
| 404 | Not Found | Deployment or directory not found |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Deployment service not initialized |

---

## Deployment Metadata Endpoints

### 1. Get Deployment Metadata

Retrieve deployment metadata for a directory.

**Endpoint**: `GET /api/deployment/metadata/<path:directory>`

**Implementation**: `webui/backend/routes/deployment.py:206-277`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `directory` | string | Yes | Directory path relative to PHOTOS_DIR |

#### Response

**Success (200)**:

```json
{
  "deployment": {
    "version": "1.0",
    "deployment_name": "Oak Ridge Forest Survey 2024",
    "created_at": "2024-06-01T12:00:00Z",
    "modified_at": "2024-08-31T15:30:00Z",
    "latitude": 35.9606,
    "longitude": -83.9207,
    "altitude": 350.5,
    "location_name": "Oak Ridge, TN, USA",
    "start_date": "2024-06-01",
    "end_date": "2024-08-31",
    "environmental": {
      "habitat": "deciduous forest",
      "temperature_range": "18-28°C"
    },
    "mothbox_id": "mothbox-001",
    "firmware_version": "5.2.1",
    "custom": {
      "project_code": "ORNL-2024-001",
      "permit_number": "NPS-2024-SCI-1234"
    },
    "modified_by": "user123"
  },
  "source_path": "/var/lib/mothbox/photos/forest_2024/deployment.json"
}
```

**Error Responses**:

```json
// 400 - Path traversal attempt
{
  "error": "Invalid path: Access denied"
}

// 404 - Directory not found
{
  "error": "Directory not found"
}

// 404 - Deployment not found
{
  "error": "Deployment not found"
}

// 503 - Service unavailable
{
  "error": "Service unavailable"
}
```

#### Examples

```bash
# Get deployment metadata
curl "http://localhost:5000/api/deployment/metadata/forest_2024"

# React component
const { data } = useQuery({
  queryKey: ['deployment', directory],
  queryFn: () =>
    fetch(`/api/deployment/metadata/${directory}`).then(r => r.json())
});
```

---

### 2. Create/Replace Deployment Metadata

Create or completely replace deployment metadata for a directory.

**Endpoint**: `PUT /api/deployment/metadata/<path:directory>`

**Implementation**: `webui/backend/routes/deployment.py:284-412`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `directory` | string | Yes | Directory path relative to PHOTOS_DIR |

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | No | `json` | File format (`json` or `yaml`) |

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "deployment_name": "Forest Survey 2024",  // required
  "latitude": 35.9606,                       // optional
  "longitude": -83.9207,                     // optional
  "altitude": 350.5,                         // optional
  "location_name": "Oak Ridge, TN, USA",     // optional
  "start_date": "2024-06-01",                // optional (ISO 8601: YYYY-MM-DD)
  "end_date": "2024-08-31",                  // optional (ISO 8601: YYYY-MM-DD)
  "environmental": {                         // optional
    "habitat": "deciduous forest",
    "temperature_range": "18-28°C"
  },
  "mothbox_id": "mothbox-001",               // optional
  "firmware_version": "5.2.1",               // optional
  "custom": {                                // optional
    "project_code": "ORNL-2024-001"
  },
  "modified_by": "user123"                   // optional
}
```

#### Response

**Success (200)**:

```json
{
  "version": "1.0",
  "deployment_name": "Forest Survey 2024",
  "created_at": "2024-06-01T12:00:00Z",
  "modified_at": "2024-06-01T12:00:00Z",
  "latitude": 35.9606,
  "longitude": -83.9207,
  "altitude": 350.5,
  "location_name": "Oak Ridge, TN, USA",
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "environmental": {
    "habitat": "deciduous forest",
    "temperature_range": "18-28°C"
  },
  "mothbox_id": "mothbox-001",
  "firmware_version": "5.2.1",
  "custom": {
    "project_code": "ORNL-2024-001"
  },
  "modified_by": "user123"
}
```

**Error Responses**:

```json
// 400 - Missing required field
{
  "error": "Field 'deployment_name' is required"
}

// 400 - Invalid coordinates
{
  "error": "latitude must be between -90.0 and 90.0"
}

// 400 - Invalid date format
{
  "error": "start_date must be in ISO 8601 format (YYYY-MM-DD)"
}

// 400 - Invalid custom fields
{
  "error": "Too many custom fields (max 100)"
}
```

#### Examples

```bash
# Create deployment metadata
curl -X PUT "http://localhost:5000/api/deployment/metadata/forest_2024?format=json" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "deployment_name": "Forest Survey 2024",
    "latitude": 35.9606,
    "longitude": -83.9207,
    "location_name": "Oak Ridge, TN, USA"
  }'

# Create YAML format
curl -X PUT "http://localhost:5000/api/deployment/metadata/forest_2024?format=yaml" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"deployment_name": "Forest Survey 2024"}'
```

---

### 3. Partial Update Deployment Metadata

Update specific fields in existing deployment metadata.

**Endpoint**: `PATCH /api/deployment/metadata/<path:directory>`

**Implementation**: `webui/backend/routes/deployment.py:418-515`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `directory` | string | Yes | Directory path relative to PHOTOS_DIR |

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "end_date": "2024-09-15",
  "location_name": "Updated Location",
  "environmental": {
    "habitat": "mixed forest"
  }
}
```

**Note**: Only provided fields are updated. Other fields remain unchanged.

#### Response

**Success (200)**:

```json
{
  "version": "1.0",
  "deployment_name": "Forest Survey 2024",
  "created_at": "2024-06-01T12:00:00Z",
  "modified_at": "2024-09-15T10:30:00Z",
  "end_date": "2024-09-15",
  "location_name": "Updated Location",
  ...
}
```

**Error Responses**:

```json
// 404 - Deployment not found
{
  "error": "Deployment not found"
}

// 400 - Validation error
{
  "error": "latitude must be between -90.0 and 90.0"
}
```

#### Examples

```bash
# Update end date
curl -X PATCH "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"end_date": "2024-09-15"}'

# Update custom fields
curl -X PATCH "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "custom": {
      "project_code": "ORNL-2024-002",
      "notes": "Extended survey period"
    }
  }'
```

---

### 4. Delete Deployment Metadata

Delete deployment metadata for a directory.

**Endpoint**: `DELETE /api/deployment/metadata/<path:directory>`

**Implementation**: `webui/backend/routes/deployment.py:521-576`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `directory` | string | Yes | Directory path relative to PHOTOS_DIR |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "success": true
}
```

**Error Responses**:

```json
// 404 - Deployment not found
{
  "error": "Deployment not found"
}

// 500 - Delete failed
{
  "error": "Failed to delete deployment metadata"
}
```

**Note**: Backup files (`.bak`) are created automatically before deletion.

#### Examples

```bash
# Delete deployment metadata
curl -X DELETE "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

## Discovery Endpoints

### 5. List All Deployments

List all deployments under a root directory.

**Endpoint**: `GET /api/deployment/list`

**Implementation**: `webui/backend/routes/deployment.py:582-653`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `root_dir` | string | No | PHOTOS_DIR | Root directory to search (relative to PHOTOS_DIR) |

#### Response

**Success (200)**:

```json
{
  "deployments": [
    {
      "version": "1.0",
      "deployment_name": "Forest Survey 2024",
      "latitude": 35.9606,
      "longitude": -83.9207,
      ...
    },
    {
      "version": "1.0",
      "deployment_name": "Meadow Survey 2024",
      "latitude": 36.0000,
      "longitude": -84.0000,
      ...
    }
  ],
  "total": 2
}
```

#### Examples

```bash
# List all deployments
curl "http://localhost:5000/api/deployment/list"

# List deployments under specific directory
curl "http://localhost:5000/api/deployment/list?root_dir=2024"
```

---

### 6. Discover Deployment for Photo

Find nearest deployment metadata by walking up directory tree.

**Endpoint**: `GET /api/deployment/discover/<path:photo_path>`

**Implementation**: `webui/backend/routes/deployment.py:658-725`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `photo_path` | string | Yes | Photo file path (relative to PHOTOS_DIR) |

#### Response

**Success (200)**:

```json
{
  "deployment": {
    "version": "1.0",
    "deployment_name": "Forest Survey 2024",
    ...
  },
  "source_path": "/var/lib/mothbox/photos/forest_2024/deployment.json"
}
```

**Error Responses**:

```json
// 404 - Photo not found
{
  "error": "Photo not found"
}

// 404 - Deployment not found
{
  "error": "Deployment not found"
}
```

**Note**: Searches current directory and all parent directories up to PHOTOS_DIR root.

#### Examples

```bash
# Discover deployment for photo
curl "http://localhost:5000/api/deployment/discover/forest_2024/subfolder/photo.jpg"

# React component
const { data } = useQuery({
  queryKey: ['deployment-for-photo', photoPath],
  queryFn: () =>
    fetch(`/api/deployment/discover/${photoPath}`).then(r => r.json())
});
```

---

## Batch Operations

### 7. Batch Update Deployments

Update multiple deployments in a single request.

**Endpoint**: `POST /api/deployment/batch`

**Implementation**: `webui/backend/routes/deployment.py:731-901`

**Rate Limiting**: 10 requests per minute

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "updates": [
    {
      "directory": "forest_2024",
      "data": {
        "end_date": "2024-09-15"
      }
    },
    {
      "directory": "meadow_2024",
      "data": {
        "end_date": "2024-09-20",
        "modified_by": "user456"
      }
    }
  ]
}
```

**Constraints**:
- Maximum 100 updates per request
- Each update is processed independently (partial success allowed)

#### Response

**Success (200)**:

```json
{
  "success": ["forest_2024"],
  "failed": ["meadow_2024"],
  "errors": {
    "meadow_2024": "Deployment not found"
  },
  "total": 2,
  "successful": 1,
  "failed_count": 1
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | array | List of successfully updated directory paths |
| `failed` | array | List of failed directory paths |
| `errors` | object | Map of failed paths to error messages |
| `total` | integer | Total number of updates attempted |
| `successful` | integer | Number of successful updates |
| `failed_count` | integer | Number of failed updates |

#### Examples

```bash
# Batch update
curl -X POST "http://localhost:5000/api/deployment/batch" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "updates": [
      {"directory": "forest_2024", "data": {"end_date": "2024-09-15"}},
      {"directory": "meadow_2024", "data": {"end_date": "2024-09-20"}}
    ]
  }'
```

---

### 8. Generate Deployment Sidecars

Generate deployment sidecars for subdirectories using a template.

**Endpoint**: `POST /api/deployment/generate`

**Implementation**: `webui/backend/routes/deployment.py:907-1021`

**Rate Limiting**: 10 requests per minute

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "directory": "surveys_2024",
  "template": {
    "deployment_name": "Auto-generated",
    "location_name": "Oak Ridge",
    "latitude": 35.9606,
    "longitude": -83.9207
  }
}
```

**Behavior**:
- Creates deployment metadata for each subdirectory that doesn't already have one
- Uses template as base values
- Subdirectory name becomes `deployment_name` if not in template

#### Response

**Success (200)**:

```json
{
  "generated_count": 5
}
```

#### Examples

```bash
# Generate sidecars
curl -X POST "http://localhost:5000/api/deployment/generate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "directory": "surveys_2024",
    "template": {
      "deployment_name": "Auto-generated",
      "location_name": "Oak Ridge"
    }
  }'
```

---

## Cache Management

### 9. Get Cache Statistics

Retrieve deployment service cache statistics.

**Endpoint**: `GET /api/deployment/stats`

**Implementation**: `webui/backend/routes/deployment.py:1027-1080`

#### Response

**Success (200)**:

```json
{
  "cache_hits": 450,
  "cache_misses": 50,
  "cache_evictions": 10,
  "cache_size": 75,
  "max_cache_size": 100,
  "cache_ttl": 300,
  "hit_ratio": 0.90,
  "total_reads": 500,
  "total_writes": 25,
  "total_deletes": 5
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `cache_hits` | integer | Number of cache hits |
| `cache_misses` | integer | Number of cache misses |
| `cache_evictions` | integer | Number of LRU evictions |
| `cache_size` | integer | Current cache entries |
| `max_cache_size` | integer | Maximum cache entries |
| `cache_ttl` | integer | Cache TTL in seconds |
| `hit_ratio` | float | Cache hit ratio (0.0 to 1.0) |
| `total_reads` | integer | Total read operations |
| `total_writes` | integer | Total write operations |
| `total_deletes` | integer | Total delete operations |

---

### 10. Invalidate Cache

Invalidate deployment service cache.

**Endpoint**: `POST /api/deployment/cache/invalidate`

**Implementation**: `webui/backend/routes/deployment.py:1086-1146`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | No | None | Directory to invalidate (if not provided, invalidates entire cache) |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "success": true
}
```

#### Examples

```bash
# Invalidate entire cache
curl -X POST "http://localhost:5000/api/deployment/cache/invalidate" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"

# Invalidate specific directory
curl -X POST "http://localhost:5000/api/deployment/cache/invalidate?directory=forest_2024" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

## Schema Reference

### Deployment Metadata Schema (v1.0)

**Required Fields**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `version` | string | Schema version | Always "1.0" |
| `deployment_name` | string | Deployment name/description | Max 200 characters, non-empty |
| `created_at` | string | Creation timestamp | ISO 8601 with 'Z' suffix |
| `modified_at` | string | Last modification timestamp | ISO 8601 with 'Z' suffix |

**Optional Fields**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `latitude` | float | GPS latitude | -90.0 to 90.0 |
| `longitude` | float | GPS longitude | -180.0 to 180.0 |
| `altitude` | float | Altitude in meters | Any numeric value |
| `location_name` | string | Human-readable location | Max 500 characters |
| `start_date` | string | Deployment start date | ISO 8601 date (YYYY-MM-DD) |
| `end_date` | string | Deployment end date | ISO 8601 date (YYYY-MM-DD) |
| `environmental` | object | Environmental conditions | Arbitrary JSON object |
| `mothbox_id` | string | Unique Mothbox identifier | No length limit |
| `firmware_version` | string | Firmware version | No length limit |
| `custom` | object | Custom metadata | Max 100 keys, max depth 5 |
| `modified_by` | string | User identifier | No length limit |

**Example Schema**:

```json
{
  "version": "1.0",
  "deployment_name": "Oak Ridge Forest Survey 2024",
  "created_at": "2024-06-01T12:00:00Z",
  "modified_at": "2024-08-31T15:30:00Z",
  "latitude": 35.9606,
  "longitude": -83.9207,
  "altitude": 350.5,
  "location_name": "Oak Ridge, TN, USA",
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "environmental": {
    "habitat": "deciduous forest",
    "temperature_range": "18-28°C",
    "elevation_range": "300-400m"
  },
  "mothbox_id": "mothbox-001",
  "firmware_version": "5.2.1",
  "custom": {
    "project_code": "ORNL-2024-001",
    "permit_number": "NPS-2024-SCI-1234",
    "principal_investigator": "Dr. Jane Smith"
  },
  "modified_by": "user123"
}
```

---

## Performance Characteristics

### Response Times

| Endpoint | Cold Cache | Warm Cache | Notes |
|----------|-----------|------------|-------|
| `GET /metadata/:dir` | <50ms | <10ms | Disk read vs cache hit |
| `PUT /metadata/:dir` | <100ms | <100ms | Includes file write |
| `PATCH /metadata/:dir` | <100ms | <100ms | Atomic read-modify-write |
| `DELETE /metadata/:dir` | <50ms | <50ms | Includes backup creation |
| `GET /list` | 100-500ms | 100-500ms | Depends on directory depth |
| `GET /discover/:photo` | <50ms | <10ms | Hierarchical search |
| `POST /batch` | Variable | Variable | Depends on number of updates |
| `POST /generate` | Variable | Variable | Depends on number of subdirectories |
| `GET /stats` | <5ms | <5ms | In-memory statistics |
| `POST /cache/invalidate` | <5ms | <5ms | Cache flag reset |

### Performance Targets

- **Cache hit**: <10ms
- **Disk read**: <50ms
- **Batch processing**: 100 directories < 1 second
- **Cache hit rate**: >80%

### Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| Get metadata | O(1) | O(1) |
| Update metadata | O(1) | O(1) |
| List deployments | O(n) | O(n) |
| Discover for photo | O(d) | O(1) |
| Batch update | O(m) | O(m) |

Where:
- n = number of deployments
- d = directory tree depth
- m = number of batch updates

---

## Related Documentation

- **Library**: `webui/backend/lib/deployment_sidecar.py` - Core CRUD operations
- **Schema**: `webui/backend/lib/deployment_schema.py` - Schema definition and validation
- **Service**: `webui/backend/services/deployment_service.py` - Cached service layer
- **User Guide**: `webui/docs/DEPLOYMENT_SIDECAR.md` - End-user documentation
- **Testing**: `Tests/unit/test_deployment_*.py` - Unit tests

---

**Document Version**: 1.0.0
**Last Validated**: 2025-12-12
**Issue**: #114 - Deployment Metadata Sidecar
