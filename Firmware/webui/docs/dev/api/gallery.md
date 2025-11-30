# Gallery API Documentation

**Last Updated**: 2025-11-29
**Version**: Phase 3 (v5.2.0)
**Base URL**: `/api/gallery`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Photo Endpoints](#photo-endpoints)
5. [Series Endpoints](#series-endpoints) *(NEW - Issue #110)*
6. [Photo Locations Endpoint](#photo-locations-endpoint) *(NEW - Issue #113)*
7. [Clustering Endpoints](#clustering-endpoints) *(NEW - Issue #115)*
8. [Map View](#map-view) *(NEW - Issue #113)*
9. [Cache Management Endpoints](#cache-management-endpoints)
10. [Pagination Contract](#pagination-contract)
11. [Performance Characteristics](#performance-characteristics)

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

## Series Endpoints

Photo series (HDR and Focus Bracket) are automatically detected based on TakePhoto.py naming patterns.

**Naming Patterns**:
- **HDR**: `{name}_{YYYY_MM_DD__HH_MM_SS}_HDR{index}.jpg` (e.g., `moth_2024_01_15__10_30_00_HDR0.jpg`)
- **Focus Bracket**: `ManFocus_{name}_{YYYY_MM_DD__HH_MM_SS}_FB{index}.jpg` (e.g., `ManFocus_moth_2024_01_15__10_30_00_FB0.jpg`)

**Implementation**: `webui/backend/services/series_service.py`, `webui/backend/lib/series_detection.py`

---

### 10. List Series

Retrieve all photo series in the photos directory.

**Endpoint**: `GET /api/gallery/series`

**Implementation**: `webui/backend/routes/gallery.py`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `page` | integer | No | 1 | ≥1 | Page number |
| `per_page` | integer | No | 50 | 1-200 | Items per page |
| `type` | string | No | None | `hdr`, `focus_bracket` | Filter by series type |

#### Response

**Success (200)**:

```json
{
  "series": [
    {
      "series_id": "hdr_moth_2024_01_15__10_00_00",
      "series_type": "hdr",
      "base_name": "moth_2024_01_15__10_00_00",
      "count": 3,
      "cover_photo": "moth_2024_01_15__10_00_00_HDR0.jpg",
      "photos": [
        "moth_2024_01_15__10_00_00_HDR0.jpg",
        "moth_2024_01_15__10_00_00_HDR1.jpg",
        "moth_2024_01_15__10_00_00_HDR2.jpg"
      ]
    },
    {
      "series_id": "focus_bracket_ManFocus_moth_2024_01_15__11_00_00",
      "series_type": "focus_bracket",
      "base_name": "ManFocus_moth_2024_01_15__11_00_00",
      "count": 5,
      "cover_photo": "ManFocus_moth_2024_01_15__11_00_00_FB0.jpg",
      "photos": [
        "ManFocus_moth_2024_01_15__11_00_00_FB0.jpg",
        "ManFocus_moth_2024_01_15__11_00_00_FB1.jpg",
        "ManFocus_moth_2024_01_15__11_00_00_FB2.jpg",
        "ManFocus_moth_2024_01_15__11_00_00_FB3.jpg",
        "ManFocus_moth_2024_01_15__11_00_00_FB4.jpg"
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 2,
    "has_next": false
  }
}
```

**Error Responses**:

```json
// 400 - Invalid page number
{
  "error": "Invalid page: -1. Page must be >= 1"
}

// 400 - Invalid type filter
{
  "error": "Invalid type: 'invalid'. Valid types: hdr, focus_bracket"
}

// 503 - Service unavailable
{
  "error": "Series service unavailable"
}

// 500 - Internal error
{
  "error": "Internal server error"
}
```

#### Examples

**List all series**:
```bash
curl "http://localhost:5000/api/gallery/series"
```

**Filter by type**:
```bash
curl "http://localhost:5000/api/gallery/series?type=hdr"
```

**Paginate results**:
```bash
curl "http://localhost:5000/api/gallery/series?page=2&per_page=20"
```

#### Performance

- **Cold cache**: 100-500ms (directory scan)
- **Warm cache**: <10ms (in-memory lookup)
- **1000 photos**: <100ms grouping time

---

### 11. Get Series Details

Retrieve details for a specific photo series by ID.

**Endpoint**: `GET /api/gallery/series/<series_id>`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `series_id` | string | Yes | Series identifier (e.g., `hdr_moth_2024_01_15__10_00_00`) |

#### Response

**Success (200)**:

```json
{
  "series_id": "hdr_moth_2024_01_15__10_00_00",
  "series_type": "hdr",
  "base_name": "moth_2024_01_15__10_00_00",
  "count": 3,
  "cover_photo": "moth_2024_01_15__10_00_00_HDR0.jpg",
  "photos": [
    "moth_2024_01_15__10_00_00_HDR0.jpg",
    "moth_2024_01_15__10_00_00_HDR1.jpg",
    "moth_2024_01_15__10_00_00_HDR2.jpg"
  ]
}
```

**Error Responses**:

```json
// 404 - Series not found
{
  "error": "Series not found: hdr_invalid_id"
}

// 503 - Service unavailable
{
  "error": "Series service unavailable"
}
```

#### Examples

**Get specific series**:
```bash
curl "http://localhost:5000/api/gallery/series/hdr_moth_2024_01_15__10_00_00"
```

**React component**:
```jsx
const { data: series } = useQuery({
  queryKey: ['series', seriesId],
  queryFn: () =>
    fetch(`/api/gallery/series/${seriesId}`).then(r => r.json())
});

return (
  <div>
    <h2>{series.series_type.toUpperCase()} Series ({series.count} photos)</h2>
    <div className="grid grid-cols-3">
      {series.photos.map(photo => (
        <img
          key={photo}
          src={`/api/gallery/thumbnail/${photo}?size=256`}
          alt={photo}
        />
      ))}
    </div>
  </div>
);
```

---

### 12. Get Series Statistics

Retrieve cache statistics for the series service.

**Endpoint**: `GET /api/gallery/series/stats`

#### Response

**Success (200)**:

```json
{
  "cache_entries": 5,
  "cache_hits": 42,
  "cache_misses": 8,
  "total_series": 10,
  "series_by_type": {
    "hdr": 6,
    "focus_bracket": 4
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `cache_entries` | integer | Number of cached directory scans |
| `cache_hits` | integer | Total cache hit count |
| `cache_misses` | integer | Total cache miss count |
| `total_series` | integer | Total series across all cached directories |
| `series_by_type` | object | Count of series by type |

#### Examples

**Get statistics**:
```bash
curl "http://localhost:5000/api/gallery/series/stats"
```

---

### 13. Invalidate Series Cache

Manually invalidate the series detection cache.

**Endpoint**: `POST /api/gallery/series/cache/invalidate`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "directory": "/var/lib/mothbox/photos"  // Optional: specific directory
}
```

- If `directory` is not provided, the entire cache is invalidated.

#### Response

**Success (200)**:

```json
{
  "success": true
}
```

**Error Responses**:

```json
// 503 - Service unavailable
{
  "error": "Series service unavailable"
}
```

#### Examples

**Invalidate entire cache**:
```bash
curl -X POST "http://localhost:5000/api/gallery/series/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{}'
```

---

## Photo Locations Endpoint

Retrieves GPS coordinates for photos to display on the map view. Only returns photos that have GPS EXIF data embedded (via the GPS EXIF tagging system).

**Implementation**: `webui/backend/routes/gallery.py`

---

### 14. Get Photo Locations

Retrieve photos with GPS coordinates for map display.

**Endpoint**: `GET /api/gallery/locations`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `limit` | integer | No | 1000 | 1-10000 | Maximum photos to return |

#### Response

**Success (200)**:

```json
{
  "locations": [
    {
      "photo_path": "2024-11-10/photo_001.jpg",
      "filename": "photo_001.jpg",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timestamp": "2024-11-10T10:30:00",
      "thumbnail_url": "/api/gallery/thumbnail/2024-11-10/photo_001.jpg"
    },
    {
      "photo_path": "2024-11-10/photo_002.jpg",
      "filename": "photo_002.jpg",
      "latitude": 37.7750,
      "longitude": -122.4195,
      "timestamp": "2024-11-10T11:00:00",
      "thumbnail_url": "/api/gallery/thumbnail/2024-11-10/photo_002.jpg"
    }
  ],
  "total_with_gps": 150,
  "total_without_gps": 50
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `locations` | array | List of photos with GPS data |
| `locations[].photo_path` | string | Relative path from PHOTOS_DIR |
| `locations[].filename` | string | Photo filename |
| `locations[].latitude` | float | Latitude in decimal degrees (-90 to 90) |
| `locations[].longitude` | float | Longitude in decimal degrees (-180 to 180) |
| `locations[].timestamp` | string | ISO 8601 timestamp from filename |
| `locations[].thumbnail_url` | string | Thumbnail endpoint URL |
| `total_with_gps` | integer | Total photos with GPS data |
| `total_without_gps` | integer | Total photos without GPS data |

**Error Responses**:

```json
// 400 - Invalid limit
{
  "error": "Limit must be between 1 and 10000"
}

// 500 - Internal error
{
  "error": "Failed to retrieve photo locations"
}
```

#### Examples

**Default limit (1000 photos)**:
```bash
curl "http://localhost:5000/api/gallery/locations"
```

**Custom limit**:
```bash
curl "http://localhost:5000/api/gallery/locations?limit=100"
```

**React component**:
```jsx
const { data } = useQuery({
  queryKey: ['photo-locations'],
  queryFn: () =>
    fetch('/api/gallery/locations?limit=500').then(r => r.json())
});

return (
  <MapContainer center={[37.7749, -122.4194]} zoom={13}>
    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {data?.locations.map(location => (
      <Marker
        key={location.photo_path}
        position={[location.latitude, location.longitude]}
      >
        <Popup>
          <img src={location.thumbnail_url} alt={location.filename} />
          <p>{location.timestamp}</p>
        </Popup>
      </Marker>
    ))}
  </MapContainer>
);
```

#### Performance

- **Typical response time**: 50-200ms for 1000 photos
- **GPS EXIF extraction**: Cached after first read via Pillow EXIF parsing
- **Large limits**: May increase response time (10000 photos: ~500ms)
- **Complexity**: O(n) where n = number of photos scanned

#### GPS Data Source

Photos must have GPS EXIF data embedded via one of these methods:
1. **Automatic tagging**: GPS EXIF service (systemd service)
2. **Manual tagging**: `gps_exif_tagger.py` CLI tool
3. **Camera direct**: Some cameras embed GPS EXIF natively

See [`GPS_EXIF_SERVICE.md`](../../GPS_EXIF_SERVICE.md) for GPS tagging setup.

#### Security

- **Path traversal**: Protected via path validation
- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (read-only operation)

---

## Clustering Endpoints

Photo location clustering groups nearby photos using the Haversine distance algorithm for improved map visualization.

**Implementation**: `webui/backend/services/clustering_service.py`, `webui/backend/lib/geo_clustering.py`, `webui/backend/lib/haversine.py`

---

### 15. Get Clustered Locations

Get photo locations clustered by geographic proximity using Haversine distance.

**Endpoint**: `GET /api/gallery/locations/clustered`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `radius` | integer | No | 100 | >0 | Clustering radius in meters |
| `min_size` | integer | No | 2 | ≥1 | Minimum photos per cluster |
| `enabled` | boolean | No | true | true/false | Enable/disable clustering |

#### Response

**Success (200)**:

```json
{
  "clusters": [
    {
      "cluster_id": "cluster_37.7749N_122.4194W_5",
      "center": {
        "lat": 37.7749,
        "lon": -122.4194
      },
      "count": 5,
      "photos": [
        {
          "path": "2024-01-15/photo1.jpg",
          "lat": 37.7749,
          "lon": -122.4194,
          "timestamp": "2024-01-15T10:00:00"
        },
        {
          "path": "2024-01-15/photo2.jpg",
          "lat": 37.7750,
          "lon": -122.4195,
          "timestamp": "2024-01-15T10:05:00"
        }
      ],
      "date_range": {
        "earliest": "2024-01-15T10:00:00",
        "latest": "2024-01-15T14:30:00"
      },
      "radius_m": 45.2
    }
  ],
  "unclustered": [
    {
      "path": "2024-01-15/photo3.jpg",
      "lat": 38.0000,
      "lon": -122.5000,
      "timestamp": "2024-01-15T12:00:00"
    }
  ],
  "metadata": {
    "total_photos": 150,
    "total_clusters": 12,
    "clustering_enabled": true,
    "radius_m": 100,
    "min_cluster_size": 2,
    "processing_time_ms": 45.2,
    "partial_result": false,
    "warning": null
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `clusters` | array | List of photo clusters |
| `clusters[].cluster_id` | string | Unique cluster identifier |
| `clusters[].center` | object | Geographic centroid of cluster |
| `clusters[].count` | integer | Number of photos in cluster |
| `clusters[].photos` | array | Photos in cluster with coordinates |
| `clusters[].date_range` | object | Earliest and latest photo timestamps |
| `clusters[].radius_m` | float | Actual cluster radius in meters |
| `unclustered` | array | Photos not meeting min_size threshold |
| `metadata.total_photos` | integer | Total photos processed |
| `metadata.total_clusters` | integer | Number of clusters formed |
| `metadata.clustering_enabled` | boolean | Whether clustering was applied |
| `metadata.radius_m` | integer | Requested clustering radius |
| `metadata.min_cluster_size` | integer | Minimum photos per cluster |
| `metadata.processing_time_ms` | float | Time to compute clusters |
| `metadata.partial_result` | boolean | True if timeout occurred |
| `metadata.warning` | string | Warning message if applicable |

**Error Responses**:

```json
// 400 - Invalid radius (negative or zero)
{
  "error": "Radius must be positive, got -100"
}

// 400 - Invalid min_size
{
  "error": "min_size must be at least 1, got 0"
}

// 400 - Invalid enabled parameter
{
  "error": "enabled must be true or false, got 'invalid'"
}

// 503 - Clustering service unavailable
{
  "error": "Clustering service not available"
}

// 500 - Internal server error
{
  "error": "Failed to cluster locations"
}
```

#### Examples

**Default parameters (100m radius, 2 photos minimum)**:
```bash
curl "http://localhost:5000/api/gallery/locations/clustered"
```

**Larger clustering radius (500m)**:
```bash
curl "http://localhost:5000/api/gallery/locations/clustered?radius=500"
```

**Single photo clusters allowed**:
```bash
curl "http://localhost:5000/api/gallery/locations/clustered?min_size=1"
```

**Disable clustering (return all photos unclustered)**:
```bash
curl "http://localhost:5000/api/gallery/locations/clustered?enabled=false"
```

**React component**:
```jsx
const { data } = useQuery({
  queryKey: ['clustered-locations', radius, minSize],
  queryFn: () =>
    fetch(`/api/gallery/locations/clustered?radius=${radius}&min_size=${minSize}`)
      .then(r => r.json())
});

// Render clusters on map
{data?.clusters.map(cluster => (
  <ClusterMarker
    key={cluster.cluster_id}
    position={[cluster.center.lat, cluster.center.lon]}
    count={cluster.count}
    photos={cluster.photos}
  />
))}

// Render unclustered photos
{data?.unclustered.map(photo => (
  <Marker
    key={photo.path}
    position={[photo.lat, photo.lon]}
  />
))}
```

#### Performance

- **Typical response time**: 50-100ms for 1000 photos
- **Haversine calculation**: <1ms per distance calculation
- **1000 photos**: <100ms clustering time
- **10000 photos**: <500ms clustering time
- **Cache hit**: <10ms (cached results)
- **Complexity**: O(n²) worst case, O(n) average with grid optimization

#### Algorithm Details

**Clustering Method**: Grid-based geographic clustering
- **Step 1**: Divide locations into grid cells based on radius
- **Step 2**: Only compare photos in same/adjacent grid cells
- **Step 3**: Group photos within radius using Haversine distance
- **Step 4**: Calculate geographic centroid for each cluster

**Haversine Distance**: Great-circle distance calculation
- Accounts for Earth's curvature
- Accurate for distances 1m - 10000km
- Formula: `a = sin²(Δφ/2) + cos(φ1)⋅cos(φ2)⋅sin²(Δλ/2)`
- Distance: `d = 2R⋅atan2(√a, √(1−a))` where R = Earth radius (6371 km)

**Geographic Centroid**: Average of all coordinates in cluster
- Simple arithmetic mean of latitudes and longitudes
- Suitable for small geographic areas (< 100km)
- More sophisticated methods available for global-scale clustering

#### Security

- **Path traversal**: Not applicable (no file access)
- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (cached after first request)
- **DOS protection**: Grid optimization prevents O(n²) worst case

---

### 16. Get Clustering Statistics

Retrieve cache statistics for the clustering service.

**Endpoint**: `GET /api/gallery/locations/clustered/stats`

#### Response

**Success (200)**:

```json
{
  "cache_hits": 45,
  "cache_misses": 12,
  "cache_entries": 3,
  "total_clustering_time_ms": 567.8
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `cache_hits` | integer | Number of cache hits |
| `cache_misses` | integer | Number of cache misses |
| `cache_entries` | integer | Number of cached results |
| `total_clustering_time_ms` | float | Total time spent clustering |

**Error Responses**:

```json
// 503 - Service unavailable
{
  "error": "Clustering service not available"
}
```

#### Examples

**Get statistics**:
```bash
curl "http://localhost:5000/api/gallery/locations/clustered/stats"
```

**React monitoring component**:
```jsx
const { data } = useQuery({
  queryKey: ['clustering-stats'],
  queryFn: () =>
    fetch('/api/gallery/locations/clustered/stats').then(r => r.json()),
  refetchInterval: 30000  // Update every 30s
});

return (
  <div>
    <p>Cache Hit Rate: {(data.cache_hits / (data.cache_hits + data.cache_misses) * 100).toFixed(1)}%</p>
    <p>Cached Results: {data.cache_entries}</p>
    <p>Total Processing Time: {data.total_clustering_time_ms.toFixed(1)}ms</p>
  </div>
);
```

#### Performance

- **Response time**: <5ms (in-memory statistics)

#### Security

- **CSRF**: Not required (read-only GET endpoint)
- **Rate limiting**: Exempt (lightweight operation)

---

### 17. Invalidate Clustering Cache

Manually invalidate the clustering cache to force re-computation.

**Endpoint**: `POST /api/gallery/locations/clustered/cache/invalidate`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON, optional):

```json
{
  "directory": "/var/lib/mothbox/photos/2024-01-15"
}
```

- If `directory` is not provided, the entire cache is invalidated.

#### Response

**Success (200)**:

```json
{
  "success": true,
  "message": "Invalidated clustering cache for /var/lib/mothbox/photos/2024-01-15"
}
```

**Error Responses**:

```json
// 503 - Service unavailable
{
  "error": "Clustering service not available"
}

// 400 - CSRF token missing
{
  "error": "CSRF validation failed"
}
```

#### Examples

**Invalidate entire cache**:
```bash
curl -X POST "http://localhost:5000/api/gallery/locations/clustered/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{}'
```

**Invalidate specific directory**:
```bash
curl -X POST "http://localhost:5000/api/gallery/locations/clustered/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"directory": "/var/lib/mothbox/photos/2024-01-15"}'
```

**React component**:
```jsx
const invalidateCache = async (directory = null) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  await fetch('/api/gallery/locations/clustered/cache/invalidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({ directory })
  });
};
```

#### Use Cases

1. **New photos added**: Invalidate cache after batch photo import
2. **GPS data updated**: Re-tag photos with new GPS coordinates
3. **Testing**: Clear cache to test clustering algorithms
4. **Parameter tuning**: Force re-clustering with new parameters

#### Performance

- **Response time**: <5ms (cache flag reset)
- **Next clustering request**: Full computation required (no cache hit)

#### Security

- **CSRF**: Required (state-changing operation)
- **Rate limiting**: None (CSRF protection sufficient)

---

## Map View

The Gallery provides a map view for visualizing photo locations on an interactive map powered by Leaflet.

### Overview

**Features**:
- Interactive map with OpenStreetMap tiles
- Marker clustering for dense photo locations
- Popup previews with thumbnail and timestamp
- Click to open full photo in lightbox
- Responsive design (mobile and desktop)

**Access Points**:
1. **Gallery tab**: Map tab in main gallery view (`/gallery?tab=map`)
2. **Dedicated page**: Full-screen map at `/gallery/map`

**Implementation**:
- **Frontend**: `webui/frontend/src/components/Gallery/MapView.tsx`
- **Map component**: `webui/frontend/src/components/Gallery/Map/PhotoMap.tsx`
- **Marker component**: `webui/frontend/src/components/Gallery/Map/PhotoMarker.tsx`
- **Hook**: `webui/frontend/src/hooks/usePhotoLocations.ts`
- **Backend API**: `GET /api/gallery/locations`

### Configuration

Map behavior is configured in `webui/frontend/src/components/Gallery/Map/config.ts`:

```typescript
export const MAP_CONFIG = {
  // Default map center (San Francisco)
  defaultCenter: { lat: 37.7749, lng: -122.4194 },

  // Default zoom level (1-18, higher = more zoomed in)
  defaultZoom: 13,

  // Maximum photos to load
  maxPhotos: 1000,

  // Marker clustering options
  clustering: {
    enabled: true,
    maxClusterRadius: 50,  // pixels
    showCoverageOnHover: false
  },

  // Thumbnail size for popups
  thumbnailSize: 256,

  // Map tile provider
  tileLayer: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }
};
```

### Marker Clustering

**Behavior**:
- Photos at similar locations are grouped into numbered clusters
- Clusters expand when clicked or zoomed in
- Individual markers appear at higher zoom levels
- Cluster radius configurable via `MAP_CONFIG.clustering.maxClusterRadius`

**Example**:
- 50 photos within 50px radius → Single cluster with "50" badge
- Zoom in → Splits into smaller clusters
- Max zoom → Individual markers for each photo

### User Interactions

**Marker Click**:
1. Opens popup with thumbnail preview
2. Shows photo timestamp
3. "View Full Photo" button opens lightbox

**Cluster Click**:
1. Zooms into cluster bounds
2. Expands into smaller clusters or individual markers

**Map Navigation**:
- **Pan**: Click and drag
- **Zoom**: Mouse wheel, zoom controls, or pinch gesture (mobile)
- **Reset**: "Fit All Photos" button to reset bounds

### Responsive Design

**Desktop** (≥768px):
- Full-width map
- Large thumbnails (256px)
- Sidebar with photo count

**Mobile** (<768px):
- Full-screen map
- Smaller thumbnails (128px)
- Bottom sheet with photo count

### Performance Considerations

**Initial Load**:
- Fetches up to `MAP_CONFIG.maxPhotos` locations
- Rendering 1000 markers: <2 seconds on modern devices
- Clustering reduces DOM nodes significantly

**Optimization Tips**:
1. **Reduce limit**: Lower `maxPhotos` for faster initial load
2. **Adjust clustering**: Increase `maxClusterRadius` for fewer clusters
3. **Lazy loading**: Consider pagination for >5000 photos

**Memory Usage**:
- 1000 markers: ~20-30MB browser memory
- 5000 markers: ~100-150MB browser memory

### GPS Coverage Indicator

The map view displays GPS coverage statistics:

```jsx
<div className="map-stats">
  <p>Photos with GPS: {data.total_with_gps}</p>
  <p>Photos without GPS: {data.total_without_gps}</p>
  <p>Coverage: {(data.total_with_gps / (data.total_with_gps + data.total_without_gps) * 100).toFixed(1)}%</p>
</div>
```

**Low Coverage Indicators**:
- If <10% photos have GPS: Warning banner
- If 0 photos have GPS: "No GPS data available" message with setup link

### Troubleshooting

**No markers appear**:
1. Check GPS EXIF service is running: `sudo systemctl status gps-exif-tagger`
2. Verify GPS fix in controls.txt: `grep "gps_fix_mode" /etc/mothbox/controls.txt`
3. Manually tag photos: `python3 webui/cli/gps_exif_tagger.py --directory /var/lib/mothbox/photos`

**Markers in wrong location**:
1. Verify GPS coordinates in controls.txt are valid
2. Check timezone settings (may affect timestamp display)
3. Re-tag photos with `--force` flag: `python3 webui/cli/gps_exif_tagger.py --force`

**Map loads slowly**:
1. Reduce `MAP_CONFIG.maxPhotos` to 500 or less
2. Enable clustering: `MAP_CONFIG.clustering.enabled = true`
3. Increase cluster radius: `MAP_CONFIG.clustering.maxClusterRadius = 80`

### Related Documentation

- **GPS EXIF Service**: [`GPS_EXIF_SERVICE.md`](../../GPS_EXIF_SERVICE.md) - Setup and configuration
- **GPS Utilities**: [`GPS_COORDINATE_UTILITIES.md`](../../GPS_COORDINATE_UTILITIES.md) - Coordinate conversion
- **API Endpoint**: `GET /api/gallery/locations` (documented above)

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

- **Architecture**: [`architecture/gallery-architecture.md`](../architecture/gallery-architecture.md) - System design and data flows
- **Cache Guide**: [`architecture/thumbnail-cache.md`](../architecture/thumbnail-cache.md) - Cache operations and tuning
- **Performance Results**: [`Tests/performance/GALLERY_PERFORMANCE_RESULTS.md`](../../Tests/performance/GALLERY_PERFORMANCE_RESULTS.md) - Benchmark data
- **Testing Guide**: [`TESTING_PROCEDURE.md`](../../TESTING_PROCEDURE.md) - Manual testing procedures

---

**Document Version**: 1.0.0
**Last Validated**: 2025-11-10
**Next Review**: Phase 2 deployment (Week 6)
