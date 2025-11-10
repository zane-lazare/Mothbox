# Gallery API Documentation

**Last Updated**: 2025-11-10
**Version**: Phase 1 (v5.1.0)
**Base URL**: `/api/gallery`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Photo Endpoints](#photo-endpoints)
5. [Cache Management Endpoints](#cache-management-endpoints)
6. [Pagination Contract](#pagination-contract)
7. [Performance Characteristics](#performance-characteristics)

---

## Overview

The Gallery API provides endpoints for browsing, serving, and managing photo collections captured by the Mothbox system. All endpoints follow RESTful conventions and return JSON responses unless serving binary image data.

**Key Features**:
- Paginated photo listing with filtering and sorting
- Multi-resolution thumbnail serving with on-demand generation
- Full-size photo serving with path traversal protection
- Cache statistics and management
- Background cache warming with progress tracking

**Implementation**: `webui/backend/routes/gallery.py` (346 lines)

---

## Authentication

**Current Status**: No authentication required (Phase 1)

**Security Measures**:
- CSRF tokens required for state-changing operations (POST/PUT/DELETE)
- Path traversal protection on all file-serving endpoints
- Rate limiting on hardware-intensive operations

**Future** (Phase 4): User authentication system planned (see Issue #19)

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
| 400 | Bad Request | Invalid parameters, path traversal attempt |
| 404 | Not Found | Photo does not exist |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Cache/warmer service not initialized |

---

## Photo Endpoints

### 1. List Photos with Pagination

Retrieve a paginated list of photos with optional filtering and sorting.

**Endpoint**: `GET /api/gallery/photos/paginated`

**Implementation**: `webui/backend/routes/gallery.py:246-346`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `limit` | integer | No | 50 | 1-500 | Maximum photos per page |
| `offset` | integer | No | 0 | ≥0 | Number of photos to skip |
| `sort` | string | No | `date_desc` | See below | Sort order |
| `start_date` | string | No | None | ISO 8601 | Filter photos on/after this date |
| `end_date` | string | No | None | ISO 8601 | Filter photos on/before this date |

**Sort Options**:
- `date_desc`: Newest photos first (default)
- `date_asc`: Oldest photos first
- `filename_asc`: Alphabetical by filename (A-Z)
- `filename_desc`: Reverse alphabetical (Z-A)

**Date Format**: ISO 8601 date or datetime strings (e.g., `2024-11-01` or `2024-11-01T12:00:00`)

#### Response

**Success (200)**:

```json
{
  "photos": [
    {
      "path": "2024-11-10/photo_001.jpg",
      "filename": "photo_001.jpg",
      "size": 5242880,
      "timestamp": 1699632000.0,
      "date": "2024-11-10T12:00:00"
    },
    {
      "path": "2024-11-10/photo_002.jpg",
      "filename": "photo_002.jpg",
      "size": 5123456,
      "timestamp": 1699631940.0,
      "date": "2024-11-10T11:59:00"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_next": true,
    "has_previous": false
  }
}
```

**Error Responses**:

```json
// 400 - Invalid limit
{
  "error": "Limit must be an integer, got 'abc'"
}

// 400 - Limit out of range
{
  "error": "Limit cannot exceed 500, got 1000"
}

// 400 - Invalid offset
{
  "error": "Offset must be non-negative, got -5"
}

// 400 - Invalid sort option
{
  "error": "Invalid sort option 'popularity'. Valid options: date_desc, date_asc, filename_asc, filename_desc"
}

// 400 - Invalid date format
{
  "error": "Invalid start_date format: '2024-13-45'. Use ISO format (YYYY-MM-DD)"
}

// 500 - Internal error
{
  "error": "Permission denied accessing photos directory"
}
```

#### Examples

**Basic pagination**:
```bash
curl "http://localhost:5000/api/gallery/photos/paginated?limit=20&offset=0"
```

**Date range filtering**:
```bash
curl "http://localhost:5000/api/gallery/photos/paginated?start_date=2024-11-01&end_date=2024-11-10"
```

**Sorting by filename**:
```bash
curl "http://localhost:5000/api/gallery/photos/paginated?sort=filename_asc&limit=100"
```

**Large offset (infinite scroll)**:
```bash
curl "http://localhost:5000/api/gallery/photos/paginated?limit=50&offset=200"
```

#### Performance

- **Typical response time**: 50-200ms
- **Cold cache (first load)**: 200-500ms
- **Large offsets**: No degradation (in-memory sorting)
- **Complexity**: O(n log n) where n = total photos (sorting overhead)

#### Security

- **Path traversal**: Protected via `Path.resolve()` and `relative_to()`
- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (cached responses)

---

### 2. Serve Full Photo

Retrieve a full-resolution photo file.

**Endpoint**: `GET /api/gallery/photo/<path:photo_path>`

**Implementation**: `webui/backend/routes/gallery.py:43-63`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `photo_path` | string | Yes | Relative path from PHOTOS_DIR (e.g., `2024-11-10/photo_001.jpg`) |

**Headers**: None required

#### Response

**Success (200)**:
- **Content-Type**: `image/jpeg`
- **Body**: Binary JPEG image data
- **Size**: Original photo size (typically 3-10MB for 64MP images)

**Error Responses**:

```json
// 400 - Path traversal attempt
{
  "error": "Invalid path"
}

// 404 - Photo not found
{
  "error": "Photo not found"
}

// 500 - Permission error
{
  "error": "Permission denied accessing photo"
}
```

#### Examples

**Direct URL access**:
```bash
curl "http://localhost:5000/api/gallery/photo/2024-11-10/photo_001.jpg" --output photo.jpg
```

**HTML img tag**:
```html
<img src="/api/gallery/photo/2024-11-10/photo_001.jpg" alt="Photo">
```

**React component**:
```jsx
<img
  src={`/api/gallery/photo/${photo.path}`}
  alt={photo.filename}
  loading="lazy"
/>
```

#### Performance

- **Typical response time**: 50-200ms (depends on file size and network)
- **Complexity**: O(1) - direct file serving via Flask `send_file()`
- **Caching**: Browser-side caching recommended (add Cache-Control headers)

#### Security

- **Path traversal**: Uses `resolve()` + `relative_to()` validation
- **Null bytes**: Rejected by Flask/Werkzeug
- **Symlinks**: Followed and validated against PHOTOS_DIR boundary
- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (read-only operation)

---

### 3. Serve Thumbnail

Retrieve a thumbnail for a photo with on-demand generation and caching.

**Endpoint**: `GET /api/gallery/thumbnail/<path:photo_path>`

**Implementation**: `webui/backend/routes/gallery.py:66-116`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `photo_path` | string | Yes | Relative path from PHOTOS_DIR |

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `size` | integer | No | 256 | Must be in configured sizes | Thumbnail dimension (square) |

**Default Sizes**: `[64, 128, 256]` (configurable in `app.py:109`)

#### Response

**Success (200)**:
- **Content-Type**: `image/jpeg`
- **Body**: Binary JPEG thumbnail data
- **Size**: 5-30KB depending on size parameter
- **Quality**: JPEG quality=85 (fixed)

**Cache Behavior**:
- **Cache hit**: Served from disk cache (<10ms)
- **Cache miss**: Generated on-demand, saved to cache (~200ms first time)

**Error Responses**:

```json
// 400 - Invalid size
{
  "error": "Invalid size 512. Allowed sizes: [64, 128, 256]"
}

// 400 - Path traversal
{
  "error": "Invalid path: null byte detected"
}

// 404 - Photo not found
{
  "error": "Photo not found: /path/to/photo.jpg"
}

// 400 - Thumbnail generation failed
{
  "error": "Failed to generate thumbnail: disk full"
}
```

**Placeholder Thumbnails**:
- If source photo is corrupt/unreadable, a gray placeholder with "?" is returned
- Placeholder cached for 5 minutes (TTL)
- Allows automatic recovery if photo is fixed

#### Examples

**Default size (256px)**:
```bash
curl "http://localhost:5000/api/gallery/thumbnail/2024-11-10/photo_001.jpg"
```

**Small thumbnail (64px)**:
```bash
curl "http://localhost:5000/api/gallery/thumbnail/2024-11-10/photo_001.jpg?size=64"
```

**Grid view (React)**:
```jsx
<img
  src={`/api/gallery/thumbnail/${photo.path}?size=256`}
  alt={photo.filename}
  className="w-full h-full object-cover"
  loading="lazy"
/>
```

**Lightbox preview (larger thumbnail)**:
```jsx
<img
  src={`/api/gallery/thumbnail/${photo.path}?size=128`}
  alt={photo.filename}
  loading="eager"
/>
```

#### Performance

- **Cache hit**: <10ms
- **Cache miss**: <200ms (thumbnail generation)
- **Concurrent requests**: File locking prevents duplicate generation
- **Throughput**: ~5 thumbnails/second (generation limited by CPU)

#### Security

- **Path validation**: Same as `/photo/:path` endpoint
- **Size validation**: Only allowed sizes accepted (prevents resource exhaustion)
- **Error placeholders**: Prevent repeated processing of corrupt files
- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (cached after first access)

---

### 4. List Photos (Legacy)

Legacy endpoint for listing all photos without pagination.

**Endpoint**: `GET /api/gallery/photos`

**Implementation**: `webui/backend/routes/gallery.py:16-40`

**Status**: Deprecated in favor of `/photos/paginated`

#### Request

No parameters.

#### Response

**Success (200)**:

```json
{
  "photos": [
    {
      "path": "2024-11-10/photo_001.jpg",
      "filename": "photo_001.jpg",
      "size": 5242880,
      "timestamp": 1699632000.0,
      "date": "2024-11-10T12:00:00"
    }
  ]
}
```

**Note**: Returns ALL photos (no pagination). Not recommended for collections >100 photos.

#### Performance

- **50 photos**: <100ms
- **500 photos**: <500ms
- **5000 photos**: ~5s (not recommended)

#### Migration

**Replace**:
```javascript
fetch('/api/gallery/photos')
```

**With**:
```javascript
fetch('/api/gallery/photos/paginated?limit=50&offset=0')
```

---

## Cache Management Endpoints

### 5. Get Cache Statistics

Retrieve thumbnail cache statistics and health metrics.

**Endpoint**: `GET /api/gallery/cache/stats`

**Implementation**: `webui/backend/routes/gallery.py:119-128`

#### Request

No parameters.

#### Response

**Success (200)**:

```json
{
  "hits": 1234,
  "misses": 56,
  "total_requests": 1290,
  "hit_ratio": 0.956,
  "cache_size_mb": 123.45,
  "cached_files": 456,
  "sizes": [64, 128, 256]
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `hits` | integer | Number of cache hits (served from disk) |
| `misses` | integer | Number of cache misses (generated on-demand) |
| `total_requests` | integer | Total thumbnail requests (hits + misses) |
| `hit_ratio` | float | Cache effectiveness (0.0-1.0, higher is better) |
| `cache_size_mb` | float | Current cache size in megabytes |
| `cached_files` | integer | Number of thumbnails in cache |
| `sizes` | array | Configured thumbnail sizes |

**Error Responses**:

```json
// 503 - Cache not initialized
{
  "error": "Cache not available"
}
```

#### Examples

**Check cache health**:
```bash
curl "http://localhost:5000/api/gallery/cache/stats"
```

**React monitoring component**:
```jsx
const { data } = useQuery({
  queryKey: ['cache-stats'],
  queryFn: () => fetch('/api/gallery/cache/stats').then(r => r.json()),
  refetchInterval: 30000  // Update every 30s
});

return (
  <div>
    <p>Hit Rate: {(data.hit_ratio * 100).toFixed(1)}%</p>
    <p>Cache Size: {data.cache_size_mb.toFixed(2)} MB</p>
    <p>Cached Thumbnails: {data.cached_files}</p>
  </div>
);
```

#### Performance

- **Response time**: <5ms (in-memory statistics)
- **No I/O**: Statistics flushed to disk periodically (not on read)

#### Interpreting Statistics

**Healthy Cache** (after warmup):
- Hit ratio: >80% (target: >95%)
- Cache size: <500MB (default limit)
- Misses increasing slowly (only for new photos)

**Unhealthy Cache**:
- Hit ratio: <50% (possible cache eviction issues)
- Cache size: 0MB (cache initialization failed)
- Misses increasing rapidly (cache not persisting)

#### Security

- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (no resource cost)

---

### 6. Invalidate Cache

Manually invalidate cached thumbnails for a specific photo or entire cache.

**Endpoint**: `POST /api/gallery/cache/invalidate`

**Implementation**: `webui/backend/routes/gallery.py:131-156`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "photo_path": "2024-11-10/photo_001.jpg",  // Optional: specific photo
  "size": 256                                 // Optional: specific size
}
```

**Parameter Combinations**:

| `photo_path` | `size` | Effect |
|--------------|--------|--------|
| None | None | Invalidate entire cache (all photos, all sizes) |
| Provided | None | Invalidate all sizes for specific photo |
| Provided | Provided | Invalidate specific size for specific photo |
| None | Provided | Invalid (size requires photo_path) |

#### Response

**Success (200)**:

```json
// Entire cache invalidated
{
  "success": true,
  "message": "Invalidated entire cache"
}

// Specific photo invalidated
{
  "success": true,
  "message": "Invalidated cache for 2024-11-10/photo_001.jpg"
}
```

**Error Responses**:

```json
// 503 - Cache not available
{
  "error": "Cache not available"
}

// 400 - Invalid parameters
{
  "error": "Photo not found: 2024-11-10/invalid.jpg"
}

// 400 - CSRF token missing/invalid
{
  "error": "CSRF validation failed",
  "message": "The CSRF token is missing."
}
```

#### Examples

**Invalidate entire cache**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{}'
```

**Invalidate specific photo**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"photo_path": "2024-11-10/photo_001.jpg"}'
```

**Invalidate specific size**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"photo_path": "2024-11-10/photo_001.jpg", "size": 256}'
```

**React component**:
```jsx
const invalidateCache = async (photoPath = null) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  await fetch('/api/gallery/cache/invalidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({ photo_path: photoPath })
  });
};
```

#### Use Cases

1. **Photo re-processed**: User adjusts camera settings and re-captures photo
2. **Photo replaced**: Photo file manually replaced via SSH/SFTP
3. **Cache corruption**: Thumbnails appear corrupted/incorrect
4. **Testing**: Clear cache to test cold-cache performance
5. **Disk space recovery**: Free up cache space before large operations

#### Performance

- **Response time**: 5-50ms depending on cache size
- **I/O cost**: Deletes cache files (synchronous)
- **Regeneration**: Thumbnails regenerated on next request

#### Security

- **CSRF**: Required (state-changing operation)
- **Authorization**: Single-user system (no per-user checks)
- **Rate limiting**: None (CSRF protection sufficient)

---

### 7. Start Cache Warming

Trigger background cache warming for recent or all photos.

**Endpoint**: `POST /api/gallery/cache/warm`

**Implementation**: `webui/backend/routes/gallery.py:158-200`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "count": 100,              // Optional: number of recent photos (default: 100)
  "sizes": [64, 128, 256],   // Optional: sizes to warm (default: all configured)
  "background": true         // Optional: run in background (default: true)
}
```

**Parameter Details**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `count` | integer | 100 | Number of recent photos to warm |
| `sizes` | array | All sizes | Which thumbnail sizes to generate |
| `background` | boolean | true | Run in background thread (recommended) |

#### Response

**Success (200)**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "Warming 100 photos in background"
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | UUID for tracking task progress |
| `status` | string | Always "started" for background tasks |
| `message` | string | Human-readable description |

**Error Responses**:

```json
// 503 - Warmer not available
{
  "error": "Cache warmer not available"
}

// 400 - Invalid parameters
{
  "error": "Count must be positive integer"
}

// 400 - CSRF token missing
{
  "error": "CSRF validation failed"
}
```

#### Examples

**Warm recent 50 photos**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/warm" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"count": 50}'
```

**Warm specific sizes**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/warm" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"count": 100, "sizes": [256]}'
```

**Foreground warming (blocking)**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/warm" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"count": 20, "background": false}'
```

**React component**:
```jsx
const warmCache = async () => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  const response = await fetch('/api/gallery/cache/warm', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({ count: 100 })
  });

  const { task_id } = await response.json();

  // Poll for status updates
  const pollStatus = setInterval(async () => {
    const status = await fetch(`/api/gallery/cache/warm/status/${task_id}`)
      .then(r => r.json());

    console.log(`Progress: ${status.progress.percent}%`);

    if (status.status === 'completed') {
      clearInterval(pollStatus);
    }
  }, 2000);
};
```

#### Performance

- **Startup time**: <10ms (spawns background thread)
- **Warmup time**: ~60s for 100 photos × 3 sizes (300 thumbnails)
- **Throughput**: ~5 thumbnails/second
- **CPU usage**: 20-40% on single core (PIL processing)

#### Use Cases

1. **Startup warmup**: Warm recent photos on application start
2. **After batch capture**: Warm newly captured photos after night session
3. **User-triggered**: "Prepare gallery" button before showing guests
4. **Scheduled maintenance**: Cron job to warm cache during idle hours

#### Security

- **CSRF**: Required (state-changing operation)
- **Rate limiting**: None (background execution limits impact)
- **Concurrency**: Only one warming task runs at a time per warmer instance

---

### 8. Get Warming Status

Check progress of a cache warming task.

**Endpoint**: `GET /api/gallery/cache/warm/status[/:task_id]`

**Implementation**: `webui/backend/routes/gallery.py:202-228`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (UUID) | No | Task ID from `/cache/warm` response |

**Behavior**:
- With `task_id`: Return specific task status
- Without `task_id`: Return summary of all tasks

#### Response

**Success (200) - Specific Task**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": {
    "current": 45,
    "total": 100,
    "percent": 45
  },
  "started_at": 1699632000.0,
  "completed_at": null,
  "photos_warmed": 45,
  "errors": []
}
```

**Success (200) - Completed Task**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": {
    "current": 100,
    "total": 100,
    "percent": 100
  },
  "started_at": 1699632000.0,
  "completed_at": 1699632060.0,
  "photos_warmed": 98,
  "errors": [
    {
      "photo": "/path/to/corrupt.jpg",
      "size": 256,
      "error": "Cannot identify image file"
    }
  ]
}
```

**Success (200) - All Tasks Summary**:

```json
{
  "active_tasks": 1,
  "total_tasks": 5,
  "task_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Error Responses**:

```json
// 200 - Task not found (not an error status)
{
  "error": "Task not found",
  "task_id": "invalid-uuid"
}

// 503 - Warmer not available
{
  "error": "Cache warmer not available"
}
```

#### Examples

**Check specific task**:
```bash
curl "http://localhost:5000/api/gallery/cache/warm/status/550e8400-e29b-41d4-a716-446655440000"
```

**Check all tasks**:
```bash
curl "http://localhost:5000/api/gallery/cache/warm/status"
```

**React progress bar**:
```jsx
const { data } = useQuery({
  queryKey: ['warming-status', taskId],
  queryFn: () =>
    fetch(`/api/gallery/cache/warm/status/${taskId}`).then(r => r.json()),
  refetchInterval: (data) =>
    data?.status === 'running' ? 2000 : false  // Poll while running
});

return (
  <div>
    <ProgressBar value={data.progress.percent} />
    <p>{data.photos_warmed} / {data.progress.total} photos</p>
    {data.errors.length > 0 && (
      <p className="text-red-500">{data.errors.length} errors</p>
    )}
  </div>
);
```

#### Performance

- **Response time**: <5ms (in-memory task tracking)
- **Polling recommendation**: 2-5 second intervals
- **Task history**: Last 10 tasks kept in memory

#### Security

- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: None (lightweight operation)

---

### 9. Cancel Warming Task

Cancel a running cache warming task.

**Endpoint**: `POST /api/gallery/cache/warm/cancel/:task_id`

**Implementation**: `webui/backend/routes/gallery.py:230-243`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (UUID) | Yes | Task ID to cancel |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

**Body**: None

#### Response

**Success (200)**:

```json
{
  "success": true,
  "message": "Task 550e8400-e29b-41d4-a716-446655440000 cancelled"
}
```

**Error Responses**:

```json
// 200 - Task not found (returns success: false)
{
  "success": false,
  "error": "Task not found"
}

// 200 - Task already completed
{
  "success": false,
  "error": "Task is completed, cannot cancel"
}

// 503 - Warmer not available
{
  "error": "Cache warmer not available"
}

// 400 - CSRF token missing
{
  "error": "CSRF validation failed"
}
```

#### Examples

**Cancel running task**:
```bash
curl -X POST "http://localhost:5000/api/gallery/cache/warm/cancel/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

**React cancel button**:
```jsx
const cancelWarmup = async (taskId) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  const response = await fetch(`/api/gallery/cache/warm/cancel/${taskId}`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken.csrf_token
    }
  });

  const result = await response.json();

  if (result.success) {
    console.log('Warming cancelled');
  } else {
    console.error('Failed to cancel:', result.error);
  }
};
```

#### Performance

- **Response time**: <5ms (sets cancellation flag)
- **Task cleanup**: Background thread exits on next iteration (~1-2 seconds)

#### Behavior

- Task status changes to "cancelled" immediately
- Background thread checks status before processing each photo
- Partial progress saved (photos already warmed remain cached)
- Task remains in history (for debugging)

#### Security

- **CSRF**: Required (state-changing operation)
- **Rate limiting**: None (lightweight operation)

---

## Pagination Contract

### Response Structure

All paginated endpoints return this structure:

```json
{
  "photos": [...],
  "pagination": {
    "total": <integer>,
    "limit": <integer>,
    "offset": <integer>,
    "has_next": <boolean>,
    "has_previous": <boolean>
  }
}
```

### Pagination Metadata Fields

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `total` | integer | Total photos matching filter | Count after filtering |
| `limit` | integer | Maximum photos in this response | From request parameter |
| `offset` | integer | Number of photos skipped | From request parameter |
| `has_next` | boolean | More photos available after this page | `(offset + limit) < total` |
| `has_previous` | boolean | Previous page exists | `offset > 0` |

### Infinite Scroll Implementation

**Frontend Pattern** (React):

```jsx
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: ['photos'],
  queryFn: ({ pageParam = 0 }) =>
    fetch(`/api/gallery/photos/paginated?limit=50&offset=${pageParam}`)
      .then(r => r.json()),
  getNextPageParam: (lastPage, pages) => {
    if (lastPage.pagination.has_next) {
      return lastPage.pagination.offset + lastPage.pagination.limit;
    }
    return undefined;
  }
});

// Intersection observer to trigger loading
useEffect(() => {
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  });

  observer.observe(sentinelRef.current);
  return () => observer.disconnect();
}, [hasNextPage, isFetchingNextPage]);
```

### Page Navigation Pattern

**Calculate page numbers**:

```javascript
const currentPage = Math.floor(offset / limit) + 1;
const totalPages = Math.ceil(total / limit);

// Next page
const nextOffset = has_next ? offset + limit : offset;

// Previous page
const prevOffset = has_previous ? Math.max(0, offset - limit) : 0;

// Jump to page N
const jumpToPage = (pageNum) => {
  const newOffset = (pageNum - 1) * limit;
  return Math.min(newOffset, Math.max(0, total - limit));
};
```

---

## Performance Characteristics

### Response Times (Raspberry Pi 4)

| Endpoint | Cold Cache | Warm Cache | Notes |
|----------|-----------|------------|-------|
| `/photos/paginated` (50 photos) | 200-500ms | 50-200ms | Filesystem cache warmup |
| `/photos/paginated` (offset=450) | 200-500ms | 50-200ms | No degradation at large offsets |
| `/photo/:path` | 50-200ms | 50-200ms | Depends on file size |
| `/thumbnail/:path` (hit) | <10ms | <10ms | Direct file serving |
| `/thumbnail/:path` (miss) | <200ms | <200ms | Includes generation time |
| `/cache/stats` | <5ms | <5ms | In-memory read |
| `/cache/invalidate` | 5-50ms | 5-50ms | Depends on cache size |
| `/cache/warm` (startup) | <10ms | <10ms | Background thread spawn |
| `/cache/warm/status` | <5ms | <5ms | In-memory read |

### Complexity Analysis

| Operation | Time Complexity | Space Complexity | Notes |
|-----------|----------------|------------------|-------|
| List photos | O(n log n) | O(n) | n = total photos (sorting) |
| Pagination slice | O(1) | O(1) | Python list slicing |
| Date filtering | O(n) | O(n) | Linear scan through photos |
| Cache lookup | O(1) | O(1) | Direct file path calculation |
| Cache eviction | O(m log m) | O(m) | m = cached files (LRU sort) |
| Thumbnail generation | O(p) | O(p) | p = source photo pixels |

### Throughput Benchmarks

**Thumbnail Generation**:
- Sequential: ~5 thumbnails/second
- Concurrent (5 threads): ~4-5 thumbnails/second (I/O bound)

**Cache Warming**:
- 100 photos × 3 sizes: 60 seconds
- 500 photos × 3 sizes: ~5 minutes

**API Requests** (cached):
- Pagination endpoint: >100 requests/second
- Thumbnail serving: >50 requests/second

---

## Related Documentation

- **Architecture**: [`docs/gallery-architecture.md`](../gallery-architecture.md) - System design and data flows
- **Cache Guide**: [`docs/thumbnail-cache.md`](../thumbnail-cache.md) - Cache operations and tuning
- **Performance Results**: [`Tests/performance/GALLERY_PERFORMANCE_RESULTS.md`](../../Tests/performance/GALLERY_PERFORMANCE_RESULTS.md) - Benchmark data
- **Testing Guide**: [`TESTING_PROCEDURE.md`](../../TESTING_PROCEDURE.md) - Manual testing procedures

---

**Document Version**: 1.0.0
**Last Validated**: 2025-11-10
**Next Review**: Phase 2 deployment (Week 6)
