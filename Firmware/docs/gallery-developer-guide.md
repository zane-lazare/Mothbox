# Gallery Developer Guide

**Last Updated**: 2025-01-10
**Version**: 1.0 (Phase 1)
**Audience**: Developers extending or maintaining the Mothbox gallery system

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Architecture Quick Reference](#architecture-quick-reference)
4. [Adding New Gallery Features](#adding-new-gallery-features)
5. [Common Development Patterns](#common-development-patterns)
6. [Code Organization](#code-organization)
7. [Testing Strategy](#testing-strategy)
8. [Performance Considerations](#performance-considerations)
9. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
10. [Debugging Gallery Issues](#debugging-gallery-issues)
11. [Extending Gallery for Phase 2+](#extending-gallery-for-phase-2)
12. [Code Quality Standards](#code-quality-standards)

---

## Introduction

This guide provides practical patterns and workflows for developers working on the Mothbox gallery system. It documents real implementation patterns from Phase 1 (performance foundation) and provides guidance for extending the system through future phases.

### Purpose

- Accelerate feature development by providing proven patterns
- Prevent common mistakes through documented pitfalls
- Ensure consistent code quality across the codebase
- Support TDD workflow with concrete examples

### Related Documentation

- **CLAUDE.md**: Project architecture and installation types
- **TDD_WORKFLOW.md**: Testing patterns and pytest workflows
- **GALLERY_ROADMAP.md**: Feature roadmap and phase planning
- **webui/README.md**: API documentation and deployment guide

---

## Prerequisites

### Required Knowledge

- **Python**: 3.9+ with type hints
- **Flask**: Blueprints, test client, CSRF protection
- **React**: Hooks, custom hooks, component patterns
- **pytest**: Fixtures, monkeypatching, parametrization
- **TanStack Query**: useQuery, useInfiniteQuery patterns

### Development Environment

```bash
# Backend setup
pip install -r requirements.txt

# Frontend setup
cd webui/frontend
npm install

# Run tests to verify setup
pytest Tests/unit/ -v
```

---

## Architecture Quick Reference

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Gallery    │  │   Infinite   │  │  Progressive │  │
│  │     Page     │  │    Scroll    │  │    Image     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│           │                  │                │           │
│           └──────────────────┴────────────────┘          │
│                          │                                │
│                   TanStack Query                          │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP/REST API
┌───────────────────────────┴─────────────────────────────┐
│                    Flask Backend                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Gallery    │  │   Photo      │  │  Thumbnail   │  │
│  │   Routes     │──│   Service    │──│    Cache     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                            │                │             │
│                            │                │             │
│                    ┌───────┴────────┬───────┘            │
│                    │                │                     │
│              ┌─────▼─────┐    ┌────▼────┐               │
│              │  PHOTOS_  │    │  Cache  │               │
│              │    DIR    │    │   Dir   │               │
│              └───────────┘    └─────────┘               │
└─────────────────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Service Layer Pattern**: Business logic in services (no Flask dependencies)
   - `services/photo_service.py`: Photo listing, pagination, filtering
   - `services/thumbnail_cache.py`: Multi-resolution caching with LRU
   - `services/cache_warmer.py`: Background cache warming

2. **Flask Blueprint Pattern**: API routes in blueprints
   - `routes/gallery.py`: Gallery endpoints organized by feature

3. **React Query Pattern**: Data fetching with caching
   - `useInfiniteQuery`: Infinite scroll pagination
   - `useQuery`: View mode persistence

### Data Flow

```
User scrolls → IntersectionObserver triggers → useInfiniteQuery.fetchNextPage()
    ↓
API: GET /api/gallery/photos/paginated?limit=50&offset=50
    ↓
gallery_bp.list_photos_paginated() → PhotoService.list_photos()
    ↓
Return: {"photos": [...], "pagination": {...}}
    ↓
React Query caches pages → Progressive images load thumbnails
```

---

## Adding New Gallery Features

### Step-by-Step Workflow

#### 1. Identify the Feature Layer

**Questions to ask:**
- Is this business logic? → **Service Layer** (`services/`)
- Is this an API endpoint? → **Route Layer** (`routes/`)
- Is this UI/UX? → **Frontend Layer** (`webui/frontend/src/`)

**Example: Adding photo sorting**
- Service: Extend `PhotoService._sort_photos()` with new sort option
- Route: Add validation for new sort parameter
- Frontend: Add UI control in Gallery page

#### 2. Follow TDD Workflow

Reference: `docs/TDD_WORKFLOW.md`

```bash
# Step 1: Create test file FIRST
touch Tests/unit/test_new_feature.py

# Step 2: Write failing test (see patterns below)
# Step 3: Run test (should fail)
pytest Tests/unit/test_new_feature.py -v

# Step 4: Implement minimal code to pass
# Step 5: Run test (should pass)
# Step 6: Refactor with confidence
# Step 7: Check coverage (>85%)
pytest Tests/unit/test_new_feature.py --cov=webui/backend/services --cov-report=term
```

#### 3. Service Layer: Extending PhotoService

**When to extend:**
- Photo listing logic (new filters, sort options)
- Pagination modifications
- Data transformation

**Pattern:**
```python
# webui/backend/services/photo_service.py (lines 48-126)

class PhotoService:
    """Service for managing photo listing and pagination"""

    def list_photos(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = DEFAULT_OFFSET,
        sort: str = 'date_desc',
        # Add new parameters here
        filter_type: str | None = None,  # Example extension
    ) -> dict:
        """List photos with pagination, sorting, and filtering"""

        # 1. Validate parameters
        self._validate_limit(limit)
        self._validate_offset(offset)
        self._validate_sort(sort)

        # 2. Get all photos with metadata
        all_photos = self._get_all_photos()

        # 3. Apply filters (add new filter logic here)
        if filter_type:
            all_photos = self._filter_by_type(all_photos, filter_type)

        # 4. Sort and paginate (existing logic)
        sorted_photos = self._sort_photos(all_photos, sort)
        total = len(sorted_photos)
        page_photos = sorted_photos[offset : offset + limit]

        # 5. Return standardized response
        return {
            "photos": [self._photo_to_dict(p) for p in page_photos],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total,
                "has_previous": offset > 0,
            },
        }
```

**Test pattern** (from `Tests/unit/test_gallery_pagination.py`):
```python
def test_new_filter_type(gallery_client, sample_photos):
    """New filter parameter correctly filters photos"""
    response = gallery_client.get('/api/gallery/photos/paginated?filter_type=hdr')

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify all photos match filter
    for photo in data['photos']:
        assert 'HDR' in photo['filename']  # Or check metadata
```

#### 4. Service Layer: Extending ThumbnailCache

**When to extend:**
- New thumbnail sizes
- Cache eviction strategy changes
- Statistics tracking enhancements

**Pattern** (from `webui/backend/services/thumbnail_cache.py`, lines 90-150):
```python
def get_thumbnail(self, photo_path: str | Path, size: int) -> Path:
    """Get thumbnail from cache or generate if missing"""
    photo_path = Path(photo_path)

    # 1. Validate inputs
    if size not in self.sizes:
        raise ThumbnailError(f"Invalid size {size}. Allowed sizes: {self.sizes}")
    self._validate_photo_path(photo_path)

    # 2. Check cache
    cache_path = self._get_cache_path(photo_path, size)
    if cache_path.exists():
        if not self._is_error_cache(cache_path):
            self._update_statistics(hit=True)
            self._touch_file(cache_path)  # Update LRU
            return cache_path

    # 3. Cache miss - generate
    self._update_statistics(hit=False)
    self._generate_thumbnail(photo_path, size)
    self._check_eviction()  # Maintain size limits

    return cache_path
```

**Key implementation details:**
- **File locking**: Uses `fcntl.flock()` for multi-process safety (lines 173-214)
- **Error handling**: Generates placeholder images for corrupt sources (lines 197-208)
- **Statistics**: Periodic flush optimization (60s interval) to reduce I/O (lines 461-485)

#### 5. API Layer: Adding Endpoints

**Pattern** (from `webui/backend/routes/gallery.py`):
```python
from flask import Blueprint, jsonify, request
from services.photo_service import PhotoService, PaginationError

gallery_bp = Blueprint("gallery", __name__)

@gallery_bp.route("/photos/paginated", methods=["GET"])
def list_photos_paginated():
    """
    List photos with pagination, sorting, and filtering support

    Query Parameters:
        limit (int): Maximum photos per page (1-500, default: 50)
        offset (int): Number of photos to skip (>=0, default: 0)
        sort (str): Sort order - date_desc, date_asc, filename_asc, filename_desc

    Returns:
        JSON response with photos array and pagination metadata

    Error Responses:
        400: Invalid parameters
        500: Internal server error
    """
    try:
        # Extract and validate parameters
        limit_str = request.args.get('limit')
        offset_str = request.args.get('offset')

        # Parse integers with explicit error handling
        if limit_str is not None:
            try:
                limit = int(limit_str)
            except ValueError:
                return jsonify({"error": f"Limit must be an integer"}), 400
        else:
            limit = 50  # Default

        # Call service layer
        photo_service = PhotoService(PHOTOS_DIR)
        result = photo_service.list_photos(limit=limit, offset=offset)

        return jsonify(result)

    except PaginationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**IMPORTANT: CSRF Protection**

All POST/PUT/DELETE/PATCH endpoints require CSRF tokens (from `webui/backend/app.py`, lines 31-32):

```python
# Routes automatically protected by Flask-WTF
@gallery_bp.route("/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """Manually invalidate cache entries (requires CSRF token)"""
    # CSRF validation happens automatically
    # No @csrf.exempt needed for state-changing operations
```

Frontend CSRF token handling:
```javascript
// Fetch token once per session
const response = await fetch('/api/csrf-token');
const { csrf_token } = await response.json();

// Include in requests
await fetch('/api/gallery/cache/invalidate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
  },
  body: JSON.stringify({})
});
```

#### 6. Frontend Layer: Component Patterns

**Pattern: Infinite Scroll** (referenced from Phase 1 implementation):

```jsx
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';

function Gallery() {
  // TanStack Query for data fetching with pagination
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['photos', { sort, filter }],
    queryFn: ({ pageParam = 0 }) => fetchPhotos({
      limit: 50,
      offset: pageParam
    }),
    getNextPageParam: (lastPage) => {
      // Calculate next offset from pagination metadata
      const { pagination } = lastPage;
      return pagination.has_next
        ? pagination.offset + pagination.limit
        : undefined;
    },
  });

  // Custom hook for scroll detection
  const { sentinelRef } = useInfiniteScroll({
    enabled: hasNextPage && !isFetchingNextPage,
    onIntersect: fetchNextPage,
  });

  // Flatten all pages into single array
  const photos = data?.pages.flatMap(page => page.photos) ?? [];

  return (
    <div className="grid grid-cols-4 gap-4">
      {photos.map(photo => (
        <PhotoGridItem key={photo.path} photo={photo} />
      ))}
      {/* Sentinel element for IntersectionObserver */}
      <div ref={sentinelRef} className="h-20" />
      {isFetchingNextPage && <LoadingSpinner />}
    </div>
  );
}
```

**Pattern: Progressive Image Loading**:

```jsx
function ProgressiveImage({ src, thumbnailSrc, alt }) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);

  return (
    <div className="relative">
      {/* Low-res thumbnail loads first */}
      <img
        src={thumbnailSrc}
        alt={alt}
        className={`blur-sm transition-opacity ${
          thumbnailLoaded && !isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
        onLoad={() => setThumbnailLoaded(true)}
      />

      {/* High-res image loads in background */}
      <img
        src={src}
        alt={alt}
        className={`absolute inset-0 transition-opacity ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
        onLoad={() => setIsLoaded(true)}
      />
    </div>
  );
}
```

#### 7. Integration Testing

After implementing across layers, write integration test (from `Tests/unit/test_gallery_routes.py` pattern):

```python
def test_complete_gallery_workflow(gallery_client, sample_photos):
    """End-to-end test of new feature across all layers"""
    # 1. Test API endpoint
    response = gallery_client.get('/api/gallery/photos/paginated?filter_type=hdr&limit=10')
    assert response.status_code == 200

    data = json.loads(response.data)

    # 2. Verify service layer behavior
    assert len(data['photos']) <= 10
    assert data['pagination']['total'] >= 0

    # 3. Verify data transformation
    for photo in data['photos']:
        assert 'path' in photo
        assert 'filename' in photo
        assert 'HDR' in photo['filename']  # Filter worked
```

---

## Common Development Patterns

### Backend Patterns

#### Pattern 1: PhotoService Usage

**Use case**: List photos with pagination

```python
from services.photo_service import PhotoService
from mothbox_paths import PHOTOS_DIR

# Initialize service
photo_service = PhotoService(PHOTOS_DIR)

# Basic pagination
result = photo_service.list_photos(limit=50, offset=0)
# Returns: {"photos": [...], "pagination": {...}}

# With sorting
result = photo_service.list_photos(
    limit=25,
    offset=0,
    sort='filename_asc'  # Options: date_desc, date_asc, filename_asc, filename_desc
)

# With date filtering
from datetime import datetime
result = photo_service.list_photos(
    limit=100,
    offset=0,
    start_date=datetime(2024, 11, 1),
    end_date=datetime(2024, 11, 30)
)
```

**Validation** (from `services/photo_service.py`, lines 234-287):
- `limit`: 1-500 (raises `PaginationError` if invalid)
- `offset`: >=0 (raises `PaginationError` if negative)
- `sort`: Must be in `VALID_SORT_OPTIONS` list

#### Pattern 2: ThumbnailCache Usage

**Use case**: Generate and cache thumbnails

```python
from services.thumbnail_cache import ThumbnailCache
from mothbox_paths import DATA_DIR

# Initialize cache (from app.py, lines 106-111)
cache = ThumbnailCache(
    cache_dir=DATA_DIR / "cache" / "thumbnails",
    max_size_mb=500,
    sizes=[64, 128, 256]
)

# Get thumbnail (generates if missing)
photo_path = PHOTOS_DIR / "2024/11/photo.jpg"
thumbnail_path = cache.get_thumbnail(photo_path, size=128)
# Returns: Path to cached thumbnail

# Check cache statistics
stats = cache.get_statistics()
# Returns: {
#   'hits': int,
#   'misses': int,
#   'total_requests': int,
#   'hit_ratio': float,  # 0.0-1.0
#   'cache_size_mb': float,
#   'cached_files': int,
#   'sizes': [64, 128, 256]
# }

# Manual cache invalidation
cache.invalidate(photo_path)  # Invalidate specific photo
cache.invalidate()  # Invalidate entire cache

# Flush statistics to disk (normally automatic every 60s)
cache.flush()
```

**Error handling** (from `services/thumbnail_cache.py`):
```python
from services.thumbnail_cache import ThumbnailError

try:
    thumbnail_path = cache.get_thumbnail(photo_path, size=999)
except ThumbnailError as e:
    # Handle invalid size, missing photo, or generation failure
    print(f"Thumbnail error: {e}")
```

#### Pattern 3: Flask Route with CSRF

**Use case**: POST endpoint with validation

```python
from flask import Blueprint, request, jsonify
from flask_wtf.csrf import csrf_exempt  # Only if needed

gallery_bp = Blueprint("gallery", __name__)

# CSRF automatically enforced (no decorator needed)
@gallery_bp.route("/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """Manually invalidate cache entries"""
    # Get cache instance from app config
    cache = current_app.config.get('THUMBNAIL_CACHE')

    if not cache:
        return jsonify({"error": "Cache not available"}), 503

    # Parse JSON body
    data = request.get_json() or {}
    photo_path = data.get('photo_path')
    size = data.get('size')

    try:
        if photo_path:
            cache.invalidate(PHOTOS_DIR / photo_path, size=size)
            return jsonify({"success": True, "message": f"Invalidated {photo_path}"})
        else:
            cache.invalidate()
            return jsonify({"success": True, "message": "Invalidated entire cache"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

**Test pattern** (from `Tests/unit/test_gallery_routes.py`, lines 588-612):
```python
def test_cache_invalidate(gallery_app):
    """POST /cache/invalidate without CSRF in testing mode"""
    mock_cache = MagicMock()
    gallery_app.config['THUMBNAIL_CACHE'] = mock_cache

    with gallery_app.test_client() as client:
        response = client.post(
            '/api/gallery/cache/invalidate',
            data=json.dumps({'photo_path': '2024/photo.jpg'}),
            content_type='application/json'
        )

        assert response.status_code == 200
        mock_cache.invalidate.assert_called_once()
```

#### Pattern 4: Path Resolution

**CRITICAL**: Never hardcode paths

```python
# CORRECT: Use mothbox_paths module
from mothbox_paths import PHOTOS_DIR, CONFIG_DIR, DATA_DIR

camera_settings = CONFIG_DIR / "camera_settings.csv"
photos = list(PHOTOS_DIR.glob("*.jpg"))
cache_dir = DATA_DIR / "cache" / "thumbnails"

# WRONG: Hardcoded paths break across installation types
camera_settings = "/opt/mothbox/camera_settings.csv"  # DON'T DO THIS
photos_dir = "/home/pi/Desktop/Mothbox/photos"  # DON'T DO THIS
```

**Installation types** (from `mothbox_paths.py`, lines 51-100):
- **Test**: Repository root when `MOTHBOX_ENV=test` or pytest detected
- **Production**: `/opt/mothbox` with FHS layout
- **Legacy**: `/home/pi/Desktop/Mothbox` (backward compat)
- **Custom**: `MOTHBOX_HOME` environment variable

#### Pattern 5: Error Handling in Routes

**Use case**: Graceful error handling with appropriate status codes

```python
from services.photo_service import PaginationError

@gallery_bp.route("/photos/paginated", methods=["GET"])
def list_photos_paginated():
    try:
        # Parameter parsing with validation
        limit_str = request.args.get('limit')
        if limit_str is not None:
            try:
                limit = int(limit_str)
            except ValueError:
                return jsonify({"error": "Limit must be an integer"}), 400
        else:
            limit = 50

        # Service call
        result = photo_service.list_photos(limit=limit, offset=offset)
        return jsonify(result)

    except PaginationError as e:
        # Known validation error
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Unexpected error
        current_app.logger.error(f"Pagination error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
```

### Frontend Patterns

#### Pattern 1: TanStack Query with Infinite Scroll

**Use case**: Paginated photo loading

```javascript
import { useInfiniteQuery } from '@tanstack/react-query';

function usePhotos({ sort = 'date_desc', filters = {} }) {
  return useInfiniteQuery({
    queryKey: ['photos', sort, filters],
    queryFn: async ({ pageParam = 0 }) => {
      const params = new URLSearchParams({
        limit: '50',
        offset: pageParam.toString(),
        sort,
        ...filters,
      });

      const response = await fetch(`/api/gallery/photos/paginated?${params}`);
      if (!response.ok) throw new Error('Failed to fetch photos');

      return response.json();
    },
    getNextPageParam: (lastPage) => {
      const { pagination } = lastPage;
      return pagination.has_next
        ? pagination.offset + pagination.limit
        : undefined;
    },
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 10 * 60 * 1000,  // 10 minutes
  });
}

// Usage in component
function Gallery() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = usePhotos({
    sort: 'date_desc'
  });

  const photos = data?.pages.flatMap(page => page.photos) ?? [];

  return (
    <div>
      {photos.map(photo => <PhotoCard key={photo.path} photo={photo} />)}
      {hasNextPage && (
        <button onClick={() => fetchNextPage()}>Load More</button>
      )}
    </div>
  );
}
```

#### Pattern 2: Custom Hook for IntersectionObserver

**Use case**: Trigger loading on scroll

```javascript
import { useEffect, useRef } from 'react';

function useInfiniteScroll({ enabled, onIntersect, rootMargin = '100px' }) {
  const sentinelRef = useRef(null);

  useEffect(() => {
    if (!enabled || !sentinelRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          onIntersect();
        }
      },
      { rootMargin }
    );

    observer.observe(sentinelRef.current);

    return () => observer.disconnect();
  }, [enabled, onIntersect, rootMargin]);

  return { sentinelRef };
}

// Usage
function Gallery() {
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = usePhotos();

  const { sentinelRef } = useInfiniteScroll({
    enabled: hasNextPage && !isFetchingNextPage,
    onIntersect: fetchNextPage,
  });

  return (
    <div>
      {/* Photos grid */}
      <div ref={sentinelRef} className="h-20" />
    </div>
  );
}
```

#### Pattern 3: Progressive Image Loading

**Use case**: Blur-up technique for better perceived performance

```javascript
import { useState } from 'react';

function ProgressiveImage({ photo, size = 256 }) {
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);
  const [fullLoaded, setFullLoaded] = useState(false);

  const thumbnailUrl = `/api/gallery/thumbnail/${photo.path}?size=${size}`;
  const fullUrl = `/api/gallery/photo/${photo.path}`;

  return (
    <div className="relative overflow-hidden">
      {/* Thumbnail (blurred) */}
      <img
        src={thumbnailUrl}
        alt={photo.filename}
        className={`
          w-full h-full object-cover transition-all duration-300
          ${thumbnailLoaded && !fullLoaded ? 'blur-sm scale-110' : 'opacity-0'}
        `}
        onLoad={() => setThumbnailLoaded(true)}
      />

      {/* Full image */}
      <img
        src={fullUrl}
        alt={photo.filename}
        className={`
          absolute inset-0 w-full h-full object-cover
          transition-opacity duration-300
          ${fullLoaded ? 'opacity-100' : 'opacity-0'}
        `}
        onLoad={() => setFullLoaded(true)}
      />
    </div>
  );
}
```

#### Pattern 4: Optimistic Updates for View Mode

**Use case**: Instant UI feedback for preference changes

```javascript
import { useMutation, useQueryClient } from '@tanstack/react-query';

function useViewMode() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (viewMode) => {
      const response = await fetch('/api/preferences/view-mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ view_mode: viewMode }),
      });

      if (!response.ok) throw new Error('Failed to update view mode');
      return response.json();
    },
    // Optimistic update (immediate UI feedback)
    onMutate: async (newViewMode) => {
      await queryClient.cancelQueries({ queryKey: ['viewMode'] });

      const previousViewMode = queryClient.getQueryData(['viewMode']);
      queryClient.setQueryData(['viewMode'], newViewMode);

      return { previousViewMode };
    },
    // Rollback on error
    onError: (err, newViewMode, context) => {
      queryClient.setQueryData(['viewMode'], context.previousViewMode);
    },
    // Refetch after success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['viewMode'] });
    },
  });

  return mutation;
}
```

---

## Code Organization

### Backend Structure

```
webui/backend/
├── services/                    # Business logic (no Flask dependencies)
│   ├── photo_service.py         # Photo listing, pagination, filtering
│   ├── thumbnail_cache.py       # Multi-resolution caching with LRU
│   └── cache_warmer.py          # Background cache warming
│
├── routes/                      # Flask blueprints (API layer)
│   ├── gallery.py               # Gallery endpoints
│   ├── camera.py                # Camera control endpoints
│   ├── gpio.py                  # GPIO control endpoints
│   └── system.py                # System status endpoints
│
├── app.py                       # Application initialization
├── config.py                    # Configuration classes
└── requirements.txt             # Python dependencies
```

### Frontend Structure

```
webui/frontend/src/
├── pages/                       # Route components
│   ├── Gallery.jsx              # Main gallery page
│   ├── Camera.jsx               # Camera control page
│   └── Dashboard.jsx            # System dashboard
│
├── components/                  # Reusable UI components
│   ├── PhotoGridItem.jsx        # Individual photo in grid
│   ├── ProgressiveImage.jsx     # Progressive image loading
│   ├── LoadingSpinner.jsx       # Loading indicators
│   └── EmptyState.jsx           # Empty state messages
│
├── hooks/                       # Custom React hooks
│   ├── useInfiniteScroll.js     # Infinite scroll implementation
│   ├── useViewMode.js           # View mode persistence
│   └── usePhotos.js             # Photo fetching with TanStack Query
│
├── utils/                       # Utility functions
│   ├── api.js                   # API client
│   └── formatters.js            # Data formatting
│
└── App.jsx                      # Root component with routing
```

### Separation of Concerns

#### Service Layer (Pure Python)

**Responsibilities:**
- Business logic implementation
- Data transformation
- Validation and error handling
- **No Flask dependencies** (can be tested without Flask)

**Example**: `PhotoService` (245 lines)
- Pagination logic
- Sorting algorithms
- Date filtering
- Path-to-dict conversion

**When to add code here:**
- Photo listing algorithms
- Metadata parsing
- Data aggregation
- Business rule validation

#### Route Layer (Flask Blueprints)

**Responsibilities:**
- HTTP request/response handling
- Parameter parsing and validation
- Service orchestration
- Error response formatting
- CSRF protection

**Example**: `gallery_bp` in `routes/gallery.py` (345 lines)
- Query parameter extraction
- Service method calls
- JSON response construction
- HTTP status code selection

**When to add code here:**
- New API endpoints
- Request validation
- Response formatting
- Authentication/authorization (future)

#### Frontend Layer (React Components)

**Responsibilities:**
- UI rendering
- User interaction handling
- State management
- API integration via TanStack Query

**Example**: Gallery page components
- Grid vs list view rendering
- Infinite scroll coordination
- Loading states and empty states
- Progressive image loading

**When to add code here:**
- New UI features
- User interaction logic
- Client-side state management
- Responsive design

---

## Testing Strategy

### Overview

All code follows strict TDD with 85%+ coverage requirement. Tests are organized by speed and dependencies.

### Test Organization

```
Tests/
├── unit/                        # Fast, isolated tests
│   ├── test_thumbnail_cache.py  # Service logic (1209 lines, comprehensive)
│   ├── test_gallery_routes.py   # API endpoints (988 lines)
│   ├── test_gallery_pagination.py  # Pagination logic (809 lines)
│   └── test_photo_service.py    # Photo service (if exists)
│
├── integration/                 # Multi-component tests
│   └── (Future: cross-service integration tests)
│
└── performance/                 # Benchmark tests
    └── test_gallery_performance.py  # Phase 1 validation (733 lines)
```

### Unit Testing Services

**Pattern**: Mock filesystem and dependencies

```python
import pytest
from services.thumbnail_cache import ThumbnailCache
from pathlib import Path

@pytest.fixture
def cache_dir(tmp_path):
    """Temporary cache directory"""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache

@pytest.fixture
def sample_photo(tmp_path):
    """Create test photo"""
    from PIL import Image
    photo = tmp_path / "test.jpg"
    Image.new('RGB', (800, 600), color='red').save(photo)
    return photo

def test_cache_miss_generates_thumbnail(cache_dir, sample_photo):
    """First request should generate thumbnail"""
    cache = ThumbnailCache(cache_dir=cache_dir, sizes=[64, 128, 256])

    # Cache should be empty initially
    assert not list(cache_dir.glob("**/*.jpg"))

    # Request thumbnail (cache miss)
    thumbnail = cache.get_thumbnail(sample_photo, size=128)

    # Verify generation
    assert thumbnail.exists()
    assert thumbnail.parent.name == "128"

    # Verify statistics
    stats = cache.get_statistics()
    assert stats['misses'] == 1
    assert stats['hits'] == 0
```

**Reference**: `Tests/unit/test_thumbnail_cache.py` has 1209 lines covering:
- Cache initialization (5 tests)
- Hit/miss scenarios (7 tests)
- Multi-resolution generation (7 tests)
- File-based locking (5 tests)
- LRU eviction (7 tests)
- Error handling (8 tests)
- Statistics tracking (7 tests)
- Security (4 tests)

### Testing Flask Routes

**Pattern**: Flask test client with fixtures

```python
import pytest
import json
from flask import Flask
from routes.gallery import gallery_bp

@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app

@pytest.fixture
def gallery_client(gallery_app):
    """Test client"""
    return gallery_app.test_client()

def test_list_photos_paginated(gallery_client, sample_photos):
    """GET /photos/paginated returns paginated results"""
    response = gallery_client.get('/api/gallery/photos/paginated?limit=10&offset=0')

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify response structure
    assert 'photos' in data
    assert 'pagination' in data
    assert len(data['photos']) <= 10
    assert data['pagination']['limit'] == 10
    assert data['pagination']['offset'] == 0
```

**CSRF Testing** (from `Tests/unit/test_gallery_routes.py`, lines 667-690):
```python
def test_cache_invalidate_requires_csrf_token(gallery_app):
    """POST /cache/invalidate requires CSRF token"""
    mock_cache = MagicMock()
    gallery_app.config['THUMBNAIL_CACHE'] = mock_cache

    with gallery_app.test_client() as client:
        # In TESTING mode, CSRF may be disabled
        # But endpoint should exist and handle request
        response = client.post(
            '/api/gallery/cache/invalidate',
            data=json.dumps({}),
            content_type='application/json'
        )

        # Should work in test mode (200) or require CSRF (400)
        assert response.status_code in [200, 400]
```

### Testing Frontend Components

**Pattern**: React Testing Library with MSW

```javascript
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import Gallery from '../pages/Gallery';

// Mock API server
const server = setupServer(
  rest.get('/api/gallery/photos/paginated', (req, res, ctx) => {
    const offset = parseInt(req.url.searchParams.get('offset') || '0');

    return res(ctx.json({
      photos: Array.from({ length: 50 }, (_, i) => ({
        path: `photo_${offset + i}.jpg`,
        filename: `photo_${offset + i}.jpg`,
        size: 100000,
        timestamp: Date.now(),
        date: new Date().toISOString(),
      })),
      pagination: {
        total: 500,
        limit: 50,
        offset: offset,
        has_next: offset + 50 < 500,
        has_previous: offset > 0,
      },
    }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('gallery loads initial photos', async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  render(
    <QueryClientProvider client={queryClient}>
      <Gallery />
    </QueryClientProvider>
  );

  // Wait for photos to load
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(50);
  });
});
```

### Performance Testing

**Pattern**: Benchmark critical paths (from `Tests/performance/test_gallery_performance.py`):

```python
import pytest
import time

@pytest.mark.performance
def test_initial_load_50_photos(performance_client):
    """Gallery initial load (50 photos) completes in <500ms"""
    # Warmup
    performance_client.get("/api/gallery/photos/paginated")

    # Measure
    start = time.perf_counter()
    response = performance_client.get("/api/gallery/photos/paginated?limit=50")
    duration = time.perf_counter() - start

    assert response.status_code == 200
    assert duration < 0.5, f"Load took {duration * 1000:.1f}ms (target: <500ms)"
```

**Performance targets** (from `Tests/performance/test_gallery_performance.py`, lines 22-27):
- Initial load (50 photos): <500ms
- Pagination (next page): <200ms
- Cache warmup (50 photos): <60s
- Cache hit ratio (after warmup): >95%
- Concurrent requests (5 clients): <300ms avg
- Large dataset (500 photos): <1000ms initial load

### Running Tests

```bash
# Unit tests only (fast, no hardware required)
pytest Tests/unit/ -v

# Specific test file
pytest Tests/unit/test_thumbnail_cache.py -v

# Specific test class
pytest Tests/unit/test_thumbnail_cache.py::TestCacheHitMissScenarios -v

# With coverage
pytest Tests/unit/ --cov=webui/backend/services --cov-report=html
open htmlcov/index.html

# Performance tests (requires real photos)
pytest Tests/performance/ -v -s

# Check coverage threshold (85% minimum)
coverage report --fail-under=85
```

---

## Performance Considerations

### Cache-First Strategy

**Implementation**: `services/thumbnail_cache.py`

The gallery uses a multi-resolution thumbnail cache to minimize regeneration:

1. **Cache lookup** (lines 119-139): Check if thumbnail exists
2. **Hit**: Touch file for LRU tracking, update statistics, return path
3. **Miss**: Generate thumbnail with file locking, check eviction, return path

**Key optimizations**:
- **Periodic statistics flush** (lines 461-485): Write to disk every 60s instead of per-request (99%+ I/O reduction)
- **File-based locking** (lines 173-214): Prevent duplicate generation in concurrent requests
- **LRU eviction** (lines 370-409): Maintain cache size limit automatically
- **Error cache with TTL** (lines 125-135): Cache placeholder images for 5 minutes to avoid repeated generation attempts

### Pagination to Limit Data Transfer

**Implementation**: `services/photo_service.py`

Photos are paginated server-side to reduce:
- Network transfer size
- Client memory usage
- Initial render time

**Configuration** (lines 33-37):
```python
MIN_LIMIT = 1
MAX_LIMIT = 500
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0
```

**Pagination logic** (lines 107-126):
```python
# Apply pagination AFTER filtering and sorting
total = len(sorted_photos)
page_photos = sorted_photos[offset : offset + limit]

# Calculate metadata
has_next = (offset + limit) < total
has_previous = offset > 0

return {
    "photos": [self._photo_to_dict(p) for p in page_photos],
    "pagination": {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": has_next,
        "has_previous": has_previous,
    },
}
```

### Progressive Image Loading

**Implementation**: Frontend `ProgressiveImage` component

Uses "blur-up" technique for perceived performance:

1. **Low-res thumbnail loads first** (size=64 or 128)
2. **Blurred and scaled to fill space** (CSS: `blur-sm scale-110`)
3. **High-res image loads in background**
4. **Fade transition when high-res ready**

**Benefits**:
- Instant visual feedback (thumbnail < 10KB)
- Perceived load time reduced
- Bandwidth saved for users who scroll past

### Infinite Scroll with Intersection Observer

**Implementation**: Custom `useInfiniteScroll` hook

```javascript
const observer = new IntersectionObserver(
  (entries) => {
    const [entry] = entries;
    if (entry.isIntersecting) {
      onIntersect();  // Trigger fetchNextPage
    }
  },
  { rootMargin: '100px' }  // Start loading 100px before visible
);
```

**Benefits**:
- No scroll event listeners (better performance)
- Automatic cleanup on unmount
- Configurable preload distance

### Query Deduplication with TanStack Query

**Implementation**: React Query configuration

```javascript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,    // 5 minutes
      cacheTime: 10 * 60 * 1000,   // 10 minutes
      refetchOnWindowFocus: false,  // Don't refetch on tab focus
    },
  },
});
```

**Benefits**:
- Multiple components can share same query
- Automatic background refetching
- Optimistic updates support

### When to Use Cache Warming

**Implementation**: `services/cache_warmer.py`

Cache warming is triggered:

1. **On app startup** (`app.py`, lines 134-137):
   ```python
   cache_warmer.warm_recent(count=50, background=True)
   cache_warmer.start_background_warming()
   ```

2. **Manually via API** (`routes/gallery.py`, lines 158-200):
   ```python
   POST /api/gallery/cache/warm
   {
     "count": 100,
     "sizes": [64, 128, 256],
     "background": true
   }
   ```

3. **Smart auto-warming** (`services/cache_warmer.py`, lines 370-421):
   - When hit ratio drops below 80%
   - When CPU usage is below 70%
   - No active warming task
   - 5+ minutes since last warming

**Use cases**:
- Pre-warm cache after capturing many photos
- Scheduled warming during low-activity periods
- User-initiated optimization

---

## Common Pitfalls and Solutions

### Pitfall 1: Path Traversal Vulnerabilities

**Problem**: User-provided paths can escape `PHOTOS_DIR`

**Example** (WRONG):
```python
# DON'T DO THIS - vulnerable to path traversal
photo_path = PHOTOS_DIR / request.args.get('path')
return send_file(photo_path)
```

**Solution** (from `routes/gallery.py`, lines 47-52):
```python
# Use resolve() and relative_to() for robust protection
full_path = (PHOTOS_DIR / photo_path).resolve()
photos_dir_resolved = PHOTOS_DIR.resolve()

# Ensure path is within PHOTOS_DIR (raises ValueError if not)
full_path.relative_to(photos_dir_resolved)
```

**Test pattern** (from `Tests/unit/test_gallery_routes.py`, lines 215-231):
```python
def test_get_photo_path_traversal_blocked(gallery_client):
    """GET /photo/<path> blocks path traversal attempts"""
    traversal_attempts = [
        '../../../etc/passwd',
        '../../secrets.txt',
        '../.ssh/id_rsa',
    ]

    for malicious_path in traversal_attempts:
        response = gallery_client.get(f'/api/gallery/photo/{malicious_path}')
        assert response.status_code in [400, 404]
```

### Pitfall 2: Cache Invalidation

**Problem**: Cached thumbnails become stale when source photo changes

**Current design** (from `services/thumbnail_cache.py`, lines 11-12):
- **Immutable photos**: No automatic invalidation based on mtime
- Photos are assumed to never change after creation

**When to invalidate**:
1. **Manual deletion**: Photo removed from filesystem
2. **Manual edit**: Photo modified externally (rare)
3. **Testing**: Clear cache between test runs

**Solutions**:
```python
# Option 1: Invalidate specific photo
cache.invalidate(photo_path=PHOTOS_DIR / "2024/photo.jpg")

# Option 2: Invalidate entire cache
cache.invalidate()

# Option 3: Invalidate specific size only
cache.invalidate(photo_path=PHOTOS_DIR / "2024/photo.jpg", size=128)
```

**API endpoint** (`routes/gallery.py`, lines 131-155):
```python
POST /api/gallery/cache/invalidate
{
  "photo_path": "2024/11/photo.jpg",  # Optional
  "size": 128  # Optional
}
```

### Pitfall 3: Camera Resource Contention

**Problem**: Picamera2 can only run one instance at a time

**Conflict scenarios**:
1. Photo capture subprocess blocks live streaming
2. Live streaming blocks manual capture
3. Two capture attempts overlap

**Solution** (from `CLAUDE.md`, Camera State Management section):

```python
# CORRECT: Sequential operations
def capture_workflow():
    # Stop streaming if active
    if camera_streamer.is_streaming():
        camera_streamer.stop()
        time.sleep(1.0)  # Allow hardware reset

    # Capture photo (subprocess)
    result = subprocess.run([sys.executable, str(takephoto_script)], ...)

    # Resume streaming if needed
    if should_stream:
        time.sleep(1.0)  # Allow camera release
        camera_streamer.start()
```

**Test isolation** (from `Tests/conftest.py` pattern):
```python
@pytest.fixture
def camera_streamer_func():
    """Function-scoped camera streamer with cleanup"""
    streamer = LiveViewStreamer(socketio)
    try:
        yield streamer
    finally:
        streamer.cleanup()
        time.sleep(1.0)  # Hardware reset delay
```

### Pitfall 4: React State Updates

**Problem**: Unnecessary re-renders or stale closures

**Example** (WRONG):
```javascript
function Gallery() {
  const [photos, setPhotos] = useState([]);

  // DON'T DO THIS - causes infinite loop
  useEffect(() => {
    fetchPhotos().then(setPhotos);
  }, [photos]);  // Dependency on state that changes in effect

  return <div>{photos.map(...)}</div>;
}
```

**Solution**: Use TanStack Query
```javascript
function Gallery() {
  // Query automatically manages state and prevents redundant fetches
  const { data, isLoading } = useQuery({
    queryKey: ['photos'],
    queryFn: fetchPhotos,
    staleTime: 5 * 60 * 1000,  // 5 minutes
  });

  if (isLoading) return <Loading />;

  return <div>{data.photos.map(...)}</div>;
}
```

### Pitfall 5: Test Isolation

**Problem**: Tests pollute each other's state (cache, filesystem)

**Example** (WRONG):
```python
# Shared fixture without cleanup
@pytest.fixture(scope="module")
def thumbnail_cache():
    return ThumbnailCache(cache_dir="/tmp/cache")
    # Cache persists across all tests in module!
```

**Solution** (from `Tests/unit/test_thumbnail_cache.py`, lines 37-52):
```python
@pytest.fixture
def temp_cache_dir(tmp_path, monkeypatch):
    """Isolated cache directory per test"""
    cache_dir = tmp_path / "cache" / "thumbnails"
    cache_dir.mkdir(parents=True)

    # Patch globally
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'THUMBNAIL_CACHE_DIR', cache_dir)

    return cache_dir

@pytest.fixture
def thumbnail_cache(temp_cache_dir):
    """Fresh cache instance per test"""
    return ThumbnailCache(
        cache_dir=temp_cache_dir,
        max_size_mb=10,
        sizes=[64, 128, 256]
    )
```

### Pitfall 6: CSRF Token Handling

**Problem**: Frontend POST requests fail with 400 CSRF validation error

**Solution**:

Backend (from `app.py`, lines 202-207):
```python
@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """Return CSRF token for the session"""
    from flask_wtf.csrf import generate_csrf
    return jsonify({"csrf_token": generate_csrf()})
```

Frontend:
```javascript
// Fetch token once on app load
useEffect(() => {
  fetch('/api/csrf-token')
    .then(res => res.json())
    .then(data => setCSRFToken(data.csrf_token));
}, []);

// Include in all POST/PUT/DELETE requests
const handleInvalidate = async () => {
  await fetch('/api/gallery/cache/invalidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify({}),
  });
};
```

**Testing** (from `Tests/unit/test_gallery_routes.py`, lines 667-690):
```python
def test_requires_csrf_token(gallery_app):
    """Endpoint requires CSRF in production"""
    # In test mode, CSRF may be disabled
    # But code should support it
    with gallery_app.test_client() as client:
        response = client.post('/api/gallery/cache/invalidate', ...)
        assert response.status_code in [200, 400]  # Both acceptable in test
```

---

## Debugging Gallery Issues

### Backend Debugging

#### 1. Flask Debug Mode

```bash
export MOTHBOX_ENV=development
python webui/backend/app.py
```

**Features**:
- Detailed error pages with stack traces
- Automatic reloading on code changes
- Interactive debugger in browser

#### 2. Logging Patterns

```python
import logging
from flask import current_app

# In route handler
current_app.logger.info(f"Photo request: {photo_path}")
current_app.logger.error(f"Thumbnail error: {e}", exc_info=True)

# In service
logger = logging.getLogger(__name__)
logger.debug(f"Cache hit for {photo_path}")
logger.warning(f"Cache size exceeded: {cache_size_mb}MB")
```

**View logs**:
```bash
# Systemd service
sudo journalctl -u mothbox-webui -f

# Development server
# Logs appear in terminal
```

#### 3. Cache Statistics Debugging

```bash
# Get cache statistics
curl http://localhost:5000/api/gallery/cache/stats

# Response:
{
  "hits": 42,
  "misses": 8,
  "total_requests": 50,
  "hit_ratio": 0.84,
  "cache_size_mb": 15.5,
  "cached_files": 123,
  "sizes": [64, 128, 256]
}
```

**Diagnose issues**:
- **Low hit ratio (<50%)**: Cache too small or eviction too aggressive
- **High cache size**: Increase `max_size_mb` or clear old photos
- **Zero hits**: Cache warming not running or paths incorrect

#### 4. Path Resolution Debugging

```bash
# Check path detection
python3 mothbox_paths.py

# Output:
# MOTHBOX_HOME: /opt/mothbox
# PHOTOS_DIR: /var/lib/mothbox/photos
# CONFIG_DIR: /etc/mothbox
# DATA_DIR: /var/lib/mothbox
```

### Frontend Debugging

#### 1. React DevTools

Install React DevTools browser extension:
- Inspect component tree
- View component props and state
- Track re-renders

**Usage**:
1. Open DevTools → React tab
2. Select Gallery component
3. View `useInfiniteQuery` state
4. Check `pages` array for loaded data

#### 2. TanStack Query DevTools

Add to development build:
```javascript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        {/* App components */}
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

**Features**:
- View all active queries
- Inspect query cache
- Force refetch or invalidate
- Track query lifecycle

#### 3. Network Tab Debugging

**Check API calls**:
1. Open DevTools → Network tab
2. Filter: XHR/Fetch
3. Look for `/api/gallery/photos/paginated` requests

**Common issues**:
- **400 Bad Request**: Check query parameters
- **403 Forbidden**: CSRF token missing
- **500 Internal Server Error**: Check backend logs
- **Slow responses**: Check performance with 500+ photos

#### 4. Console Errors

**Common errors**:

```javascript
// Error: CSRF validation failed
// Solution: Fetch and include CSRF token

// Error: Cannot read property 'map' of undefined
// Solution: Add loading state check
if (!data?.pages) return <Loading />;

// Error: Maximum update depth exceeded
// Solution: Remove dependency that causes infinite loop
useEffect(() => {
  // ...
}, [stableValue]);  // Not [changingValue]
```

### Performance Debugging

#### 1. Backend Performance

```bash
# Run performance test suite
pytest Tests/performance/test_gallery_performance.py -v -s

# Check specific benchmark
pytest Tests/performance/test_gallery_performance.py::TestGalleryLoadPerformance::test_initial_load_50_photos -v -s
```

**Metrics** (from `Tests/performance/test_gallery_performance.py`, lines 186-210):
```python
start = time.perf_counter()
response = performance_client.get("/api/gallery/photos/paginated?limit=50")
duration = time.perf_counter() - start

assert duration < 0.5, f"Load took {duration * 1000:.1f}ms (target: <500ms)"
```

#### 2. Frontend Performance

**React Profiler**:
1. Open DevTools → React tab → Profiler
2. Click "Record"
3. Perform action (scroll, toggle view)
4. Click "Stop"
5. Analyze commit timings

**Look for**:
- Components rendering multiple times
- Expensive operations (>16ms = dropped frame)
- Unnecessary re-renders

#### 3. Cache Performance

```bash
# Check cache hit ratio over time
watch -n 5 'curl -s http://localhost:5000/api/gallery/cache/stats | jq ".hit_ratio"'

# Monitor cache size growth
watch -n 10 'curl -s http://localhost:5000/api/gallery/cache/stats | jq ".cache_size_mb"'
```

### Common Error Messages

#### "Cache not available" (503)

**Cause**: `THUMBNAIL_CACHE` not initialized in app config

**Solution**:
```python
# Check app.py initialization (lines 106-120)
thumbnail_cache = ThumbnailCache(...)
app.config['THUMBNAIL_CACHE'] = thumbnail_cache
```

#### "Invalid size 999. Allowed sizes: [64, 128, 256]" (400)

**Cause**: Requested thumbnail size not in configured sizes

**Solution**:
```python
# Use valid size
cache.get_thumbnail(photo_path, size=128)  # ✓ Valid

# Or configure additional sizes
cache = ThumbnailCache(cache_dir=..., sizes=[64, 128, 256, 512])
```

#### "Photo not found" (404)

**Cause**: Photo path doesn't exist in PHOTOS_DIR

**Solution**:
```python
# Verify photo exists
from mothbox_paths import PHOTOS_DIR
photo_path = PHOTOS_DIR / "2024/11/photo.jpg"
assert photo_path.exists(), f"Photo not found: {photo_path}"
```

#### "Limit must be at least 1, got 0" (400)

**Cause**: Invalid pagination parameter

**Solution**:
```python
# Use valid limits
result = photo_service.list_photos(limit=50)   # ✓ Valid (1-500)
result = photo_service.list_photos(limit=0)    # ✗ Invalid
result = photo_service.list_photos(limit=1000) # ✗ Invalid (exceeds max)
```

---

## Extending Gallery for Phase 2+

### Integration Points for Future Phases

#### Phase 2: Photo Viewer & Metadata

**Metadata API preparation** (routes structure):
```python
# webui/backend/routes/metadata.py (future)
metadata_bp = Blueprint("metadata", __name__)

@metadata_bp.route("/photo/<path:photo_path>/metadata", methods=["GET"])
def get_photo_metadata(photo_path):
    """Get EXIF and GPS metadata for photo"""
    # Parse EXIF tags
    # Extract GPS coordinates
    # Return structured metadata
    pass
```

**Service layer extension**:
```python
# webui/backend/services/metadata_service.py (future)
class MetadataService:
    """Service for photo metadata extraction and parsing"""

    def get_exif_data(self, photo_path: Path) -> dict:
        """Extract EXIF tags from photo"""
        pass

    def get_gps_coordinates(self, photo_path: Path) -> tuple[float, float] | None:
        """Extract GPS coordinates if available"""
        pass
```

**Frontend integration**:
```javascript
// Extend PhotoGridItem to show metadata icon
function PhotoGridItem({ photo }) {
  const { data: metadata } = useQuery({
    queryKey: ['metadata', photo.path],
    queryFn: () => fetchMetadata(photo.path),
    enabled: false,  // Lazy load on demand
  });

  return (
    <div>
      <img src={photo.thumbnail} />
      {metadata?.gps && <GPSIcon />}
    </div>
  );
}
```

#### Phase 3: Series Grouping

**Series detection service** (future):
```python
# webui/backend/services/series_detector.py
class SeriesDetector:
    """Detect HDR and focus bracket series"""

    def detect_series(self, photos: list[Path]) -> list[dict]:
        """
        Group photos into series based on timestamps and filenames

        Returns:
            List of series with metadata:
            [
                {
                    "type": "hdr",  # or "focus_bracket"
                    "photos": [Path, Path, ...],
                    "count": 5,
                    "timestamp": float,
                },
                ...
            ]
        """
        pass
```

**API endpoint**:
```python
@gallery_bp.route("/series", methods=["GET"])
def list_series():
    """List photo series (HDR, focus brackets)"""
    detector = SeriesDetector()
    series = detector.detect_series(PHOTOS_DIR)
    return jsonify({"series": series})
```

#### Phase 4: Tagging System

**Sidecar metadata preparation**:
```python
# webui/backend/services/metadata_store.py (future)
class MetadataStore:
    """Manage .meta.json sidecar files"""

    def save_metadata(self, photo_path: Path, metadata: dict) -> None:
        """Save metadata to .meta.json sidecar file"""
        meta_path = photo_path.with_suffix('.meta.json')

        # Use file locking for concurrent writes
        with open(meta_path, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            current = json.load(f) if meta_path.exists() else {}
            current.update(metadata)
            f.seek(0)
            json.dump(current, f, indent=2)
            f.truncate()
```

**Tag structure**:
```json
{
  "tags": ["moth", "nocturnal", "large"],
  "species": "Actias luna",
  "notes": "Green luna moth, excellent condition",
  "location": "Field station #3",
  "weather": "clear",
  "temperature_c": 18.5,
  "custom_fields": {}
}
```

#### Phase 5: Export System

**Export service structure**:
```python
# webui/backend/services/export_service.py (future)
class ExportService:
    """Handle photo exports in various formats"""

    def export_darwin_core(
        self,
        photos: list[Path],
        metadata: dict
    ) -> Path:
        """Export photos with Darwin Core CSV"""
        pass

    def export_inaturalist(
        self,
        photos: list[Path],
        metadata: dict
    ) -> Path:
        """Export photos with iNaturalist metadata"""
        pass
```

### Maintaining Backward Compatibility

#### API Versioning Strategy

**Current approach**: No versioning (breaking changes rare)

**Future approach** (if needed):
```python
# Version 1 (current)
@gallery_bp.route("/photos/paginated", methods=["GET"])
def list_photos_paginated():
    # Current implementation
    pass

# Version 2 (future breaking changes)
@gallery_bp.route("/v2/photos/paginated", methods=["GET"])
def list_photos_paginated_v2():
    # New implementation with breaking changes
    pass
```

#### Database/Storage Migration

**Current state**: Filesystem-only (no database)

**Future state**: SQLite for metadata search

**Migration pattern**:
```python
# scripts/migrate_to_metadata_db.py (future)
def migrate_metadata():
    """Migrate existing .meta.json files to SQLite database"""
    db = MetadataDatabase(DATA_DIR / "metadata.db")

    for meta_file in PHOTOS_DIR.rglob("*.meta.json"):
        photo_path = meta_file.with_suffix('.jpg')
        with open(meta_file) as f:
            metadata = json.load(f)

        db.insert_metadata(photo_path, metadata)

    print(f"Migrated {db.count()} photos")
```

#### Configuration Versioning

**Pattern**: Add new fields, keep defaults for old fields

```python
# controls.txt
# New in Phase 2:
metadata_cache_enabled=True  # Default: True for backward compat

# New in Phase 4:
tagging_enabled=True  # Default: True
autocomplete_min_chars=2  # Default: 2
```

---

## Code Quality Standards

### Linting Configuration

**Ruff** (configured in `pyproject.toml`):

```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

**Key rules**:
- Line length: 100 characters (not 79, more readable for modern screens)
- Import sorting: Automatic with `isort` profile
- Type hints: Encouraged but not enforced
- Docstrings: Required for public functions

### Test Coverage Requirements

**Configuration** (from `pyproject.toml`):
```toml
[tool.coverage.run]
branch = true
source = ["webui/backend", "mothbox_paths"]

[tool.coverage.report]
fail_under = 85
```

**Check coverage**:
```bash
pytest Tests/ --cov=webui/backend --cov=mothbox_paths --cov-report=html
coverage report --fail-under=85
```

**Coverage guidelines**:
- **Overall**: ≥85% (enforced in CI)
- **Critical paths**: ≥95% (export, GPS, caching)
- **UI components**: ≥75% (focus on logic, not styling)

**Exclude from coverage** (from `pyproject.toml`):
```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### Security Scanning

**Bandit** (configured in `pyproject.toml`):

```bash
# Security scan (MEDIUM+ severity enforced)
bandit -c pyproject.toml -r . --severity-level medium

# Generate report
bandit -c pyproject.toml -r . --format json --output bandit-report.json
```

**Common false positives** (from `CLAUDE.md`):
```python
# B603/B607: subprocess usage (required for GPIO/camera control)
result = subprocess.run([...])  # nosec B603 - Required for camera control

# B103: File permissions 0o755 (standard for photo directories)
os.chmod(photo_dir, 0o755)  # nosec B103 - Standard photo dir permissions

# B104: Bind to 0.0.0.0 (local network device with CSRF/CORS protection)
socketio.run(app, host='0.0.0.0', ...)  # nosec B104 - Local network only
```

### Documentation Requirements

**Docstring format**:
```python
def list_photos(
    self,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    sort: str = 'date_desc',
) -> dict:
    """
    List photos with pagination, sorting, and filtering

    Args:
        limit: Maximum number of photos to return (1-500)
        offset: Number of photos to skip (>=0)
        sort: Sort order (date_desc, date_asc, filename_asc, filename_desc)

    Returns:
        Dictionary with 'photos' list and 'pagination' metadata:
        {
            "photos": [...],
            "pagination": {
                "total": int,
                "limit": int,
                "offset": int,
                "has_next": bool,
                "has_previous": bool
            }
        }

    Raises:
        PaginationError: If parameters are invalid
    """
```

**Required documentation**:
- Public functions: Full docstring with Args/Returns/Raises
- Complex algorithms: Inline comments explaining logic
- API endpoints: OpenAPI-style comments
- Configuration: Comments in controls.txt explaining each setting

### Type Hints

**Use modern Python 3.9+ syntax**:
```python
from pathlib import Path

# Union types (Python 3.10+)
def get_thumbnail(self, photo_path: str | Path, size: int) -> Path:
    pass

# Optional types
def filter_by_date(
    self,
    photos: list,
    start_date: datetime | None,
    end_date: datetime | None
) -> list:
    pass

# Generic types
from typing import Any

def get_statistics(self) -> dict[str, Any]:
    pass
```

---

**Last Updated**: 2025-01-10
**Version**: 1.0
**For**: Mothbox Gallery Phase 1 (Performance Foundation)

**Next Steps**: Implement Phase 2 features following patterns in this guide. Update this document with new patterns as they emerge.
