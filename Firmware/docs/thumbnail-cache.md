# Thumbnail Cache Guide

**Last Updated**: 2025-11-10
**Version**: Phase 1 (v5.1.0)
**Implementation**: `webui/backend/services/thumbnail_cache.py` (669 lines)

---

## Table of Contents

1. [Overview](#overview)
2. [Cache Architecture](#cache-architecture)
3. [Cache Operations](#cache-operations)
4. [Configuration Options](#configuration-options)
5. [Cache Warming](#cache-warming)
6. [Monitoring and Statistics](#monitoring-and-statistics)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)

---

## Overview

The Mothbox thumbnail cache provides high-performance multi-resolution thumbnail generation and caching with LRU eviction, file-based locking for multi-process safety, and persistent statistics tracking.

### Purpose

**Primary Goals**:
1. **Performance**: Sub-second gallery loads for collections of 500+ photos
2. **Resource Efficiency**: Limit disk usage via configurable size cap
3. **Reliability**: Multi-process safe, graceful error handling
4. **Transparency**: Detailed statistics for monitoring cache effectiveness

**Design Philosophy**:
- **Immutable photos**: Photos never change after capture (no mtime-based invalidation)
- **Aggressive caching**: Once generated, thumbnails persist until evicted
- **Smart eviction**: LRU algorithm keeps frequently accessed thumbnails
- **Error tolerance**: Corrupt photos generate placeholder thumbnails with TTL

### Key Features

- **Multi-resolution support**: Configurable sizes (default: 64px, 128px, 256px)
- **File-based locking**: `fcntl.flock()` prevents duplicate generation
- **LRU eviction**: Automatic cleanup when cache exceeds size limit
- **Persistent statistics**: Track hit rate, cache size, and usage patterns
- **Error placeholders**: Gray "?" thumbnails for corrupt/missing photos (5-minute TTL)
- **Background warming**: Pre-generate thumbnails for recent photos

---

## Cache Architecture

### Directory Structure

The cache uses a hierarchical directory layout organized by thumbnail size:

```
CACHE_DIR/thumbnails/
├── 64/
│   ├── a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4.jpg
│   ├── b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4.jpg
│   ├── .a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4.jpg.lock  # Temporary lock file
│   └── .b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4.jpg.error # Error marker
├── 128/
│   ├── a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4.jpg
│   └── ...
├── 256/
│   ├── a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4.jpg
│   └── ...
├── cache_stats.json
└── .cache_stats.json.lock  # Statistics lock file
```

**Default Location**:
- **Production**: `/var/lib/mothbox/cache/thumbnails/`
- **Legacy**: `/home/pi/Desktop/Mothbox/cache/thumbnails/`
- **Test**: `{repo_root}/cache/thumbnails/`

See `mothbox_paths.py:119-120` for path resolution logic.

### Hash Algorithm

**Implementation** (`services/thumbnail_cache.py:276-289`):

```python
def _get_hash(self, photo_path: Path) -> str:
    """Generate MD5 hash of photo path"""
    # MD5 used for cache key generation, not security
    # Full hash used to prevent collisions in large photo collections
    hash_obj = hashlib.md5(str(photo_path).encode(), usedforsecurity=False)  # nosec B324
    return hash_obj.hexdigest()  # Returns 32-character hash
```

**Key Properties**:
- **Input**: Full absolute path to source photo (e.g., `/var/lib/mothbox/photos/2024-11-10/photo_001.jpg`)
- **Output**: 32-character hexadecimal string (e.g., `a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4`)
- **Algorithm**: MD5 (not for security, just fast hashing)
- **Collision resistance**: 2^128 possible hashes (virtually no collisions)
- **Consistency**: Same photo path always produces same hash

**Why MD5 of path, not content?**:
1. **Performance**: No need to read photo file for hash calculation
2. **Consistency**: Hash doesn't change when photo is regenerated
3. **Simplicity**: Path-based lookups are faster than content-based

**Cache Path Construction** (`services/thumbnail_cache.py:260-274`):

```python
def _get_cache_path(self, photo_path: Path, size: int) -> Path:
    """Generate cache file path"""
    photo_hash = self._get_hash(photo_path)
    return self.cache_dir / str(size) / f"{photo_hash}.jpg"

# Example:
# photo_path: /var/lib/mothbox/photos/2024-11-10/photo_001.jpg
# size: 256
# Result: /var/lib/mothbox/cache/thumbnails/256/a3b5c8d9e1f2a4b6c7d8e9f0a1b2c3d4.jpg
```

### File Format

**Thumbnail Specifications**:
- **Format**: JPEG
- **Quality**: 85 (fixed, optimal size/quality tradeoff)
- **Dimensions**: Square thumbnails (width = height = size)
- **Aspect ratio**: Preserved via `thumbnail()` method (fits within square)
- **Resampling**: LANCZOS (high quality, preserves scientific detail)
- **File size**: ~5-10KB (64px), ~10-20KB (128px), ~20-40KB (256px)

**JPEG Quality Tradeoff** (quality=85):
- **Rationale**: Balances visual quality with file size
- **Testing**: Visually lossless for insect photography at thumbnail scale
- **Performance**: ~5-10ms faster encoding than quality=95
- **Disk usage**: ~30% smaller than quality=95

### Supported Resolutions

**Default Sizes** (`services/thumbnail_cache.py:68`):
```python
self.sizes = sizes if sizes is not None else [64, 128, 256]
```

**Size Guidelines**:

| Size | Use Case | Typical File Size | UI Context |
|------|----------|-------------------|------------|
| 64px | Grid thumbnails (small screens) | 5-10KB | Mobile gallery grid |
| 128px | Grid thumbnails (desktop) | 10-20KB | Desktop gallery grid |
| 256px | Lightbox previews | 20-40KB | Photo viewer preview |
| 512px+ | High-res previews (future) | 60-100KB | Full-screen lightbox |

**Configurable Sizes**:
```python
# In app.py initialization
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    sizes=[64, 128, 256, 512]  # Custom sizes
)
```

**Validation** (`services/thumbnail_cache.py:107-110`):
```python
if size not in self.sizes:
    raise ThumbnailError(
        f"Invalid size {size}. Allowed sizes: {self.sizes}"
    )
```

---

## Cache Operations

### Cache Hit Flow

**Implementation** (`services/thumbnail_cache.py:124-139`):

```python
if cache_path.exists():
    if self._is_error_cache(cache_path):
        # Check TTL (5 minutes)
        if time.time() - cache_path.stat().st_mtime < 300:
            # Still valid error cache
            self._update_statistics(hit=True)
            self._touch_file(cache_path)  # Update access time
            return cache_path
        else:
            # Expired error cache, regenerate
            cache_path.unlink()
    else:
        # Normal cache hit
        self._update_statistics(hit=True)
        self._touch_file(cache_path)  # Update access time for LRU
        return cache_path
```

**Sequence**:
1. **Path calculation**: Hash photo path → construct cache path
2. **Existence check**: Check if `cache_dir/{size}/{hash}.jpg` exists
3. **Error cache check**: Check for `.{hash}.jpg.error` marker
4. **TTL validation**: Verify error cache hasn't expired (5 minutes)
5. **atime update**: Touch file to mark as recently accessed (LRU tracking)
6. **Statistics update**: Increment hit counter (in-memory)
7. **Return**: Send cached thumbnail to client

**Performance**: <10ms (one file existence check + one stat() call)

### Cache Miss Flow

**Implementation** (`services/thumbnail_cache.py:142-150`):

```python
# Cache miss - generate thumbnail
self._update_statistics(hit=False)

# Generate with file locking
self._generate_thumbnail(photo_path, size)

# Check eviction
self._check_eviction()

return cache_path
```

**Generation with Locking** (`services/thumbnail_cache.py:152-215`):

```python
def _generate_thumbnail(self, photo_path: Path, size: int) -> Path:
    """Generate thumbnail with file-based locking"""
    cache_path = self._get_cache_path(photo_path, size)
    lock_path = cache_path.parent / f".{cache_path.name}.lock"

    # Acquire lock (open in append mode to create atomically)
    with open(lock_path, 'a') as lock_file:
        try:
            # Exclusive lock (blocks until available)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            # Double-check existence (another process may have generated it)
            if cache_path.exists():
                return cache_path

            # Generate thumbnail
            try:
                img = Image.open(photo_path)
                img.thumbnail((size, size), Image.LANCZOS)
                img.save(cache_path, format='JPEG', quality=85)
            except (OSError, Exception):
                # Error: create placeholder
                placeholder = self._create_placeholder(size)
                placeholder.save(cache_path, format='JPEG', quality=85)
                self._mark_error_cache(cache_path)

        finally:
            # Release lock and clean up
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_path.unlink(missing_ok=True)

    return cache_path
```

**Sequence**:
1. **Miss counter**: Increment miss counter (in-memory)
2. **Lock acquisition**: Create lock file, acquire exclusive lock (blocks concurrent requests)
3. **Double-check**: Verify cache still missing (race condition handling)
4. **Image loading**: Open source photo with PIL
5. **Thumbnail resize**: `thumbnail()` method (preserves aspect ratio)
6. **Save to disk**: Write JPEG with quality=85
7. **Error handling**: Generate placeholder if source is corrupt
8. **Lock release**: Release lock, delete lock file
9. **Eviction check**: Check if cache size exceeds limit
10. **LRU eviction**: Remove oldest files if needed
11. **Return**: Send generated thumbnail to client

**Performance**: <200ms (includes I/O, PIL processing, and disk write)

**Concurrency Handling**:
- **First request**: Acquires lock, generates thumbnail
- **Concurrent requests**: Block on lock, reuse generated thumbnail
- **No duplicate work**: Only first request does generation

### Cache Invalidation

**Manual Invalidation** (`services/thumbnail_cache.py:586-633`):

```python
def invalidate(
    self,
    photo_path: str | Path | None = None,
    size: int | None = None
):
    """Manually invalidate cache entries"""
    if photo_path is None:
        # Invalidate entire cache
        for size_dir in self.cache_dir.iterdir():
            if size_dir.is_dir() and size_dir.name.isdigit():
                for file in size_dir.glob("*.jpg"):
                    try:
                        file.unlink()
                        # Remove error marker
                        error_marker = file.parent / f".{file.name}.error"
                        if error_marker.exists():
                            error_marker.unlink()
                    except OSError:
                        pass
    else:
        # Invalidate specific photo
        photo_path = Path(photo_path)
        photo_hash = self._get_hash(photo_path)

        # Invalidate specific size or all sizes
        sizes_to_invalidate = [size] if size is not None else self.sizes

        for sz in sizes_to_invalidate:
            cache_file = self.cache_dir / str(sz) / f"{photo_hash}.jpg"
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    # Remove error marker
                    error_marker = cache_file.parent / f".{cache_file.name}.error"
                    if error_marker.exists():
                        error_marker.unlink()
                except OSError:
                    pass
```

**Use Cases**:
1. **Photo replaced**: User re-captures photo with different settings
2. **Cache corruption**: Thumbnail appears incorrect/corrupted
3. **Testing**: Clear cache to measure cold-cache performance
4. **Disk space**: Free up cache before large operations

**API Usage**:
```python
# Invalidate entire cache
thumbnail_cache.invalidate()

# Invalidate specific photo (all sizes)
thumbnail_cache.invalidate(photo_path="2024-11-10/photo_001.jpg")

# Invalidate specific size
thumbnail_cache.invalidate(photo_path="2024-11-10/photo_001.jpg", size=256)
```

**HTTP API**:
```bash
# Via REST endpoint
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_TOKEN" \
  -d '{"photo_path": "2024-11-10/photo_001.jpg"}'
```

### LRU Eviction

**Trigger** (`services/thumbnail_cache.py:359-368`):

```python
def _check_eviction(self):
    """Check cache size and evict if over limit"""
    cache_size_mb = self._calculate_cache_size()

    if cache_size_mb > self.max_size_mb:
        self._evict_lru()
```

**Eviction Algorithm** (`services/thumbnail_cache.py:370-409`):

```python
def _evict_lru(self):
    """Evict least recently used files until under max_size_mb"""
    # Get all cached files with atime
    cached_files = []
    for size_dir in self.cache_dir.iterdir():
        if size_dir.is_dir() and size_dir.name.isdigit():
            for file in size_dir.glob("*.jpg"):
                try:
                    stat = file.stat()
                    cached_files.append((file, stat.st_atime, stat.st_size))
                except OSError:
                    pass

    # Sort by access time (oldest first)
    cached_files.sort(key=lambda x: x[1])

    # Remove files until under limit
    current_size = sum(f[2] for f in cached_files) / (1024 * 1024)

    for file_path, _atime, file_size in cached_files:
        if current_size <= self.max_size_mb:
            break

        try:
            file_path.unlink()
            # Remove error marker if exists
            error_marker = file_path.parent / f".{file_path.name}.error"
            if error_marker.exists():
                error_marker.unlink()
            current_size -= file_size / (1024 * 1024)
        except OSError:
            pass
```

**Process**:
1. **Scan**: Iterate all cached files across all size directories
2. **Collect metadata**: Get (path, atime, size) for each file
3. **Sort**: Order by atime (least recently accessed first)
4. **Calculate size**: Sum total cache size in MB
5. **Delete**: Remove oldest files until under `max_size_mb` limit
6. **Cleanup**: Remove associated error markers

**Access Time Tracking** (`services/thumbnail_cache.py:345-357`):

```python
def _touch_file(self, file_path: Path):
    """Update file access time for LRU tracking"""
    try:
        # Update only atime, preserve mtime
        stat_info = file_path.stat()
        os.utime(file_path, (time.time(), stat_info.st_mtime))
    except OSError:
        pass
```

**When atime is updated**:
- Every cache hit (every time thumbnail is served)
- After thumbnail generation (marks as recently used)

**Eviction Frequency**:
- Checked after every thumbnail generation (cache miss)
- Not checked on cache hits (performance optimization)

**Trade-offs**:
- **Pros**: Keeps frequently accessed thumbnails, automatic cleanup
- **Cons**: Recent photos may be evicted if limit is too low

---

## Configuration Options

### Current Configuration (Phase 1)

**Hardcoded in app.py** (`webui/backend/app.py:104-109`):

```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=500,
    sizes=[64, 128, 256]
)
```

### Planned Configuration (Phase 2+)

**In controls.txt** (future implementation):

```ini
# Thumbnail Cache Settings
cache_max_size_mb=500           # Maximum cache size in MB
cache_sizes=64,128,256          # Comma-separated thumbnail sizes
cache_warmup_on_startup=true    # Warm cache on app start
cache_warmup_count=50           # Number of recent photos to warm
cache_stats_flush_interval=60   # Statistics flush interval (seconds)
```

### Configuration Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `cache_dir` | Path | `DATA_DIR/cache/thumbnails` | Any valid path | Cache root directory |
| `max_size_mb` | integer | 500 | 10-10000 | Maximum cache size in MB |
| `sizes` | list[int] | [64, 128, 256] | 32-2048 | Thumbnail dimensions (square) |

**Constructor Signature** (`services/thumbnail_cache.py:52-68`):

```python
def __init__(
    self,
    cache_dir: str | Path,
    max_size_mb: int = 500,
    sizes: list[int] | None = None
):
```

### Default Values and Rationale

**`max_size_mb=500`**:
- **Justification**: 500MB can store ~8000-10000 thumbnails at 256px
- **Typical usage**: 500 photos × 3 sizes = 1500 thumbnails ≈ 30-60MB
- **Overhead**: Leaves room for 3000+ photos before eviction
- **SD card friendly**: Modest size for embedded systems

**`sizes=[64, 128, 256]`**:
- **64px**: Mobile grid view (space-efficient)
- **128px**: Desktop grid view (optimal for typical screens)
- **256px**: Lightbox preview, larger thumbnails
- **Omitted 512px+**: Phase 1 doesn't need high-res previews

**Storage Requirements**:

| Photos | Sizes | Total Thumbnails | Approx. Disk Usage |
|--------|-------|------------------|--------------------|
| 100 | 3 | 300 | 6-12 MB |
| 500 | 3 | 1500 | 30-60 MB |
| 1000 | 3 | 3000 | 60-120 MB |
| 5000 | 3 | 15000 | 300-600 MB |

### Tuning for Different Deployments

**Small Deployments** (50-200 photos):
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=100,      # Smaller limit
    sizes=[128, 256]      # Skip 64px (not needed)
)
```

**Large Deployments** (1000+ photos):
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=1000,     # Larger limit
    sizes=[64, 128, 256, 512]  # Add high-res
)
```

**Research Deployments** (high-quality previews):
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=2000,
    sizes=[128, 256, 512, 1024]  # High-res thumbnails
)
```

**SD Card Deployments** (limited storage):
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=100,      # Aggressive limit
    sizes=[128]           # Single size only
)
```

---

## Cache Warming

### Overview

Cache warming pre-generates thumbnails in the background to improve perceived performance. Users experience fast gallery loads because thumbnails are ready before they're requested.

**Implementation**: `webui/backend/services/cache_warmer.py` (577 lines)

### Manual Warming

**API Usage** (`services/cache_warmer.py:266-288`):

```python
# Warm recent 100 photos
result = cache_warmer.warm_recent(count=100, background=True)
# Returns: {'task_id': 'uuid', 'status': 'started', 'message': '...'}

# Warm specific photos
photos = [Path('/path/photo1.jpg'), Path('/path/photo2.jpg')]
result = cache_warmer.warm_photos(
    photo_paths=photos,
    sizes=[256],           # Optional: specific sizes
    priority="newest",     # Or "all" (chronological)
    background=True
)

# Warm entire collection
result = cache_warmer.warm_all(background=True)
```

**HTTP API**:

```bash
# Warm recent 100 photos
curl -X POST "http://localhost:5000/api/gallery/cache/warm" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_TOKEN" \
  -d '{"count": 100}'

# Check progress
curl "http://localhost:5000/api/gallery/cache/warm/status/{task_id}"

# Cancel warming
curl -X POST "http://localhost:5000/api/gallery/cache/warm/cancel/{task_id}" \
  -H "X-CSRFToken: YOUR_TOKEN"
```

### Automatic Warming Triggers

**On Application Startup** (`webui/backend/app.py:134`):

```python
# Warm recent photos on startup (non-blocking)
cache_warmer.warm_recent(count=50, background=True)
```

**Smart Auto-Warming** (`services/cache_warmer.py:370-421`):

Background monitoring thread checks these conditions:

```python
def should_trigger_warming(self) -> bool:
    """Determine if auto-warming should trigger"""
    # 1. Not already warming
    if active_tasks:
        return False

    # 2. Sufficient time since last warming (5+ minutes)
    if time.time() - self._last_warming_time < self._monitoring_interval:
        return False

    # 3. Sufficient requests to evaluate hit ratio (100+ requests)
    if stats['total_requests'] < 100:
        return False

    # 4. Hit ratio below threshold (<80%)
    if stats['hit_ratio'] >= self.hit_ratio_threshold:
        return False

    # 5. CPU usage acceptable (<70%)
    if HAS_PSUTIL:
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > (self.cpu_threshold * 100):
            return False

    return True
```

**Trigger Scenarios**:
1. **Low hit rate**: Hit ratio drops below 80% after 100+ requests
2. **New photos**: Detect new photos via mtime (future enhancement)
3. **System idle**: CPU usage below 70% (optional, requires psutil)

**Configuration** (`services/cache_warmer.py:74-96`):

```python
cache_warmer = CacheWarmer(
    thumbnail_cache=thumbnail_cache,
    photos_dir=PHOTOS_DIR,
    hit_ratio_threshold=0.80,      # Trigger if <80%
    cpu_threshold=0.70,             # Only if CPU <70%
    check_interval_minutes=5        # Check every 5 minutes
)
```

### Progress Tracking

**Task Status Structure** (`services/cache_warmer.py:156-165`):

```python
{
    'task_id': 'uuid-string',
    'status': 'running',  # or 'completed', 'cancelled'
    'progress': {
        'current': 45,
        'total': 100,
        'percent': 45
    },
    'started_at': 1699632000.0,
    'completed_at': None,  # Set when finished
    'photos_warmed': 45,
    'errors': []  # List of error dicts
}
```

**React Progress Bar Example**:

```jsx
const WarmingProgress = ({ taskId }) => {
  const { data } = useQuery({
    queryKey: ['warming-status', taskId],
    queryFn: () =>
      fetch(`/api/gallery/cache/warm/status/${taskId}`).then(r => r.json()),
    refetchInterval: (data) =>
      data?.status === 'running' ? 2000 : false
  });

  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <h3>Warming Cache</h3>
      <ProgressBar value={data.progress.percent} max={100} />
      <p>{data.photos_warmed} / {data.progress.total} photos</p>
      {data.status === 'completed' && (
        <p className="text-green-600">✓ Complete</p>
      )}
      {data.errors.length > 0 && (
        <p className="text-red-600">{data.errors.length} errors</p>
      )}
    </div>
  );
};
```

### Cancellation

**Implementation** (`services/cache_warmer.py:343-368`):

```python
def cancel_warming(self, task_id: str) -> dict[str, Any]:
    """Cancel a running warming task"""
    with self._task_lock:
        task = self._tasks.get(task_id)
        if not task:
            return {'success': False, 'error': 'Task not found'}

        if task['status'] != 'running':
            return {
                'success': False,
                'error': f"Task is {task['status']}, cannot cancel"
            }

        # Mark as cancelled
        task['status'] = 'cancelled'
        task['completed_at'] = time.time()

        return {'success': True, 'message': f'Task {task_id} cancelled'}
```

**Background Thread** (`services/cache_warmer.py:194-215`):

```python
# Check cancellation before each photo
with self._task_lock:
    task = self._tasks.get(task_id)
    if task and task['status'] == 'cancelled':
        logger.info(f"Task {task_id} cancelled")
        return  # Exit worker thread
```

**Behavior**:
- Cancellation is cooperative (thread checks status periodically)
- Partial progress is preserved (already warmed thumbnails remain)
- Thread exits within 1-2 seconds (after current photo completes)

### Performance Characteristics

**Throughput**:
- **Sequential**: ~5 thumbnails/second (CPU-bound)
- **100 photos × 3 sizes**: ~60 seconds
- **500 photos × 3 sizes**: ~5 minutes

**Resource Usage**:
- **CPU**: 20-40% on single core (PIL processing)
- **Memory**: ~50MB peak per thumbnail generation
- **Disk I/O**: Sequential writes (~1-2 MB/s)

**Optimization**:
- Warming runs in background thread (non-blocking)
- Only warms photos not already cached
- Skips corrupt photos (creates placeholder)

---

## Monitoring and Statistics

### Statistics Endpoint

**API**: `GET /api/gallery/cache/stats`

**Response** (`services/thumbnail_cache.py:553-584`):

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

### Key Metrics

**Hit Ratio** (`hit_ratio`):
- **Formula**: `hits / (hits + misses)`
- **Range**: 0.0 to 1.0 (higher is better)
- **Target**: >0.80 (80%)
- **Achieved**: >0.95 (95%) in testing after warmup

**Interpretation**:
- **>95%**: Excellent (most requests served from cache)
- **80-95%**: Good (acceptable performance)
- **50-80%**: Fair (consider warming or increasing cache size)
- **<50%**: Poor (cache ineffective, investigate eviction or configuration)

**Cache Size** (`cache_size_mb`):
- **Current usage** in megabytes
- **Compare to `max_size_mb`** to check headroom
- **Monitor growth** over time

**Cached Files** (`cached_files`):
- **Total thumbnails** across all sizes
- **Rough estimate**: `cached_files / len(sizes)` = unique photos cached
- **Example**: 1500 cached_files / 3 sizes = ~500 photos

### Persistent Statistics

**Storage** (`services/thumbnail_cache.py:78`):

```json
// cache_stats.json
{
  "hits": 1234,
  "misses": 56,
  "total_requests": 1290,
  "last_updated": 1699632000.0
}
```

**Update Strategy** (`services/thumbnail_cache.py:461-484`):

```python
# In-memory counters (updated on every request)
self.hits += 1

# Periodic flush (every 60 seconds)
if time.time() - self._last_stats_flush >= self._stats_flush_interval:
    self._flush_statistics()
```

**Benefits**:
- **Performance**: 99%+ reduction in disk writes
- **Durability**: Statistics survive restarts
- **Multi-process safe**: File locking prevents corruption

**Manual Flush**:

```python
# Force immediate flush (e.g., before shutdown)
thumbnail_cache.flush()
```

### Health Monitoring

**Dashboard Example** (React):

```jsx
const CacheHealth = () => {
  const { data } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: () =>
      fetch('/api/gallery/cache/stats').then(r => r.json()),
    refetchInterval: 30000  // Update every 30s
  });

  if (!data) return <Spinner />;

  const hitRatePercent = (data.hit_ratio * 100).toFixed(1);
  const cacheUsagePercent = (data.cache_size_mb / 500 * 100).toFixed(1);

  return (
    <div className="grid grid-cols-2 gap-4">
      <Card>
        <h3>Cache Hit Rate</h3>
        <p className={data.hit_ratio > 0.8 ? 'text-green-600' : 'text-red-600'}>
          {hitRatePercent}%
        </p>
        <ProgressBar value={data.hit_ratio * 100} />
      </Card>

      <Card>
        <h3>Cache Usage</h3>
        <p>{data.cache_size_mb.toFixed(2)} MB / 500 MB</p>
        <ProgressBar value={cacheUsagePercent} />
      </Card>

      <Card>
        <h3>Cached Thumbnails</h3>
        <p>{data.cached_files} files</p>
      </Card>

      <Card>
        <h3>Total Requests</h3>
        <p>{data.total_requests.toLocaleString()}</p>
        <p className="text-sm text-gray-500">
          {data.hits} hits / {data.misses} misses
        </p>
      </Card>
    </div>
  );
};
```

---

## Troubleshooting

### Common Issues

#### 1. Low Hit Rate (<50%)

**Symptoms**:
- Gallery feels slow despite cache being enabled
- `/cache/stats` shows hit_ratio < 0.50
- Many cache misses

**Possible Causes**:
1. **Cache too small**: Eviction happening too frequently
2. **No warmup**: Cache empty on first access
3. **LRU thrashing**: Working set larger than cache size

**Solutions**:

```python
# Increase cache size
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=1000  # Double the limit
)

# Trigger manual warmup
curl -X POST "http://localhost:5000/api/gallery/cache/warm" \
  -H "X-CSRFToken: TOKEN" \
  -d '{"count": 200}'

# Check cache size usage
curl "http://localhost:5000/api/gallery/cache/stats"
# If cache_size_mb ≈ max_size_mb, eviction is happening
```

#### 2. Slow Thumbnail Generation (>500ms)

**Symptoms**:
- First load of each photo takes >500ms
- `/thumbnail/:path` endpoint slow on cache miss

**Possible Causes**:
1. **Large source photos**: 64MP images take longer to process
2. **Slow disk**: SD card read/write performance
3. **CPU bottleneck**: ARM CPU limited (no GPU acceleration)

**Solutions**:

```python
# Use smaller thumbnail sizes
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    sizes=[64, 128]  # Omit 256px for speed
)

# Upgrade storage (SD card → SSD)
# Edit /etc/fstab to mount cache on SSD

# Warm cache proactively (avoid on-demand generation)
cache_warmer.warm_recent(count=200, background=True)
```

#### 3. Disk Space Exhausted

**Symptoms**:
- Thumbnail generation fails with "disk full" error
- Cache size not respecting `max_size_mb` limit
- System logs show ENOSPC errors

**Possible Causes**:
1. **Other applications**: Photos directory or logs filling disk
2. **LRU not running**: Eviction disabled or misconfigured
3. **Incorrect size calculation**: Bug in `_calculate_cache_size()`

**Solutions**:

```bash
# Check disk usage
df -h /var/lib/mothbox

# Check cache size
du -sh /var/lib/mothbox/cache/thumbnails

# Manual cleanup (entire cache)
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "X-CSRFToken: TOKEN" \
  -d '{}'

# Reduce cache limit
# Edit webui/backend/app.py:
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=100  # Smaller limit
)
```

#### 4. Cache Corruption

**Symptoms**:
- Thumbnails show wrong photos
- Gray placeholder thumbnails persist
- Hash collisions suspected

**Possible Causes**:
1. **Filesystem corruption**: SD card wear, power loss
2. **Concurrent writes**: File locking failed (rare)
3. **Bug in hash function**: (extremely unlikely with MD5)

**Solutions**:

```bash
# Invalidate entire cache (regenerate all)
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "X-CSRFToken: TOKEN" \
  -d '{}'

# Check filesystem integrity
sudo fsck /dev/mmcblk0p1

# Verify photo files
cd /var/lib/mothbox/photos
find . -name "*.jpg" -exec jpeginfo -c {} \;
```

#### 5. Error Placeholders Won't Regenerate

**Symptoms**:
- Corrupt photo shows "?" placeholder indefinitely
- Fixed photo still shows placeholder
- Error marker file persists

**Possible Causes**:
1. **TTL not expired**: 5-minute TTL still active
2. **Error marker not deleted**: Manual cleanup needed

**Solutions**:

```bash
# Wait 5 minutes, then reload (TTL expires)
# Or manually invalidate:
curl -X POST "http://localhost:5000/api/gallery/cache/invalidate" \
  -H "X-CSRFToken: TOKEN" \
  -d '{"photo_path": "2024-11-10/corrupt.jpg"}'

# Or delete error markers manually:
cd /var/lib/mothbox/cache/thumbnails
find . -name ".*.error" -delete
```

### Debugging Commands

**Check cache directory structure**:
```bash
tree -L 3 /var/lib/mothbox/cache/thumbnails
```

**Count cached files per size**:
```bash
for size in 64 128 256; do
  echo "$size: $(ls /var/lib/mothbox/cache/thumbnails/$size/*.jpg 2>/dev/null | wc -l)"
done
```

**Find largest cached files**:
```bash
find /var/lib/mothbox/cache/thumbnails -name "*.jpg" -exec ls -lh {} \; | sort -k5 -hr | head -20
```

**Check for orphaned lock files**:
```bash
find /var/lib/mothbox/cache/thumbnails -name ".*.lock"
# Should be empty (locks cleaned up automatically)
```

**Verify MD5 hashing**:
```python
from pathlib import Path
from services.thumbnail_cache import ThumbnailCache

cache = ThumbnailCache(Path("/var/lib/mothbox/cache/thumbnails"))
photo_path = Path("/var/lib/mothbox/photos/2024-11-10/photo_001.jpg")

# Should return consistent hash
hash1 = cache._get_hash(photo_path)
hash2 = cache._get_hash(photo_path)
print(f"Hash: {hash1}")
print(f"Match: {hash1 == hash2}")  # Should be True
```

### Log Analysis

**Enable debug logging** (future enhancement):

```python
# In app.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs show:
# - Cache hits/misses
# - Eviction events
# - Lock acquisition/release
# - Error placeholder creation
```

**Current logging** (`services/cache_warmer.py:112-116`):

```python
logger.info(
    f"CacheWarmer initialized: photos_dir={photos_dir}, "
    f"hit_ratio_threshold={hit_ratio_threshold}, "
    f"cpu_threshold={cpu_threshold}"
)
```

---

## Performance Tuning

### Optimal Cache Sizes for Different Use Cases

#### Casual Photographer (50-200 photos)

**Configuration**:
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=100,
    sizes=[128, 256]
)
```

**Rationale**:
- Small collection fits entirely in cache
- 128px sufficient for most screens
- 256px for lightbox previews
- Skip 64px (not needed for small collections)

**Expected Performance**:
- Hit rate: >99% after initial load
- Disk usage: ~10-20 MB
- Gallery load: <200ms

#### Active Researcher (500-1000 photos)

**Configuration**:
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=500,
    sizes=[64, 128, 256]
)
```

**Rationale**:
- Default configuration optimal for this range
- 64px for mobile grid view
- 128px for desktop grid
- 256px for previews

**Expected Performance**:
- Hit rate: >95% after warmup
- Disk usage: ~60-120 MB
- Gallery load: <500ms

#### Large-Scale Deployment (1000-5000 photos)

**Configuration**:
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=1000,
    sizes=[64, 128, 256, 512]
)
```

**Rationale**:
- Larger cache to accommodate more photos
- Add 512px for high-quality lightbox
- Warmup critical (can't cache entire collection)

**Expected Performance**:
- Hit rate: 80-90% (LRU eviction active)
- Disk usage: ~300-600 MB
- Gallery load: <1000ms

**Optimization Strategy**:
- Warm recent 500 photos on startup
- Schedule warmup during idle hours
- Monitor hit rate, adjust `max_size_mb` if low

#### Research Archive (5000+ photos)

**Configuration**:
```python
thumbnail_cache = ThumbnailCache(
    cache_dir=THUMBNAIL_CACHE_DIR,
    max_size_mb=2000,
    sizes=[128, 256, 512]
)
```

**Rationale**:
- Prioritize quality over cache coverage
- Assume users focus on recent photos
- High-res thumbnails for scientific analysis

**Expected Performance**:
- Hit rate: 70-80% (aggressive LRU)
- Disk usage: ~1.5-2 GB
- Gallery load: <2000ms (first load)

**Optimization Strategy**:
- Consider database for metadata (Phase 3+)
- Implement date-based directory indexing
- Warm most recent 1000 photos only

### Trade-offs: Quality vs. Speed vs. Disk Space

**JPEG Quality Settings** (currently fixed at 85):

| Quality | File Size (256px) | Generation Time | Visual Quality |
|---------|-------------------|-----------------|----------------|
| 70 | 15-25 KB | ~150ms | Noticeable artifacts |
| 85 | 20-40 KB | ~200ms | Visually lossless |
| 95 | 50-80 KB | ~250ms | Excellent |
| 100 | 100-150 KB | ~300ms | Perfect (overkill) |

**Recommendation**: Keep quality=85 (sweet spot)

**Thumbnail Size Trade-offs**:

| Size | Use Case | File Size | Generation Time | Bandwidth |
|------|----------|-----------|-----------------|-----------|
| 64px | Mobile grid | 5-10 KB | ~100ms | Low |
| 128px | Desktop grid | 10-20 KB | ~150ms | Medium |
| 256px | Previews | 20-40 KB | ~200ms | Medium |
| 512px | Lightbox | 60-100 KB | ~400ms | High |
| 1024px | Full-screen | 200-400 KB | ~800ms | Very high |

**Raspberry Pi-Specific Recommendations**:

1. **SD Card**:
   - Limit cache to 500MB max (SD card wear)
   - Prefer smaller sizes (64, 128, 256)
   - Avoid frequent eviction (minimize writes)

2. **SSD**:
   - Increase cache to 1000-2000MB
   - Add larger sizes (512, 1024)
   - More aggressive warmup

3. **CPU Constraints**:
   - Avoid generating >512px thumbnails (slow on ARM)
   - Batch warmup during idle hours
   - Prioritize recent photos

4. **Network (LAN)**:
   - Bandwidth not a bottleneck (<1 Gbps sufficient)
   - Serve compressed JPEGs directly (no streaming needed)

---

## Related Documentation

- **Architecture**: [`docs/gallery-architecture.md`](./gallery-architecture.md) - System design and data flows
- **API Reference**: [`docs/api/gallery.md`](./api/gallery.md) - Complete endpoint documentation
- **Performance Results**: [`Tests/performance/GALLERY_PERFORMANCE_RESULTS.md`](../Tests/performance/GALLERY_PERFORMANCE_RESULTS.md) - Benchmark data
- **Testing Guide**: [`TESTING_PROCEDURE.md`](../TESTING_PROCEDURE.md) - Manual testing procedures

---

**Document Version**: 1.0.0
**Last Validated**: 2025-11-10
**Next Review**: Phase 2 deployment (Week 6)
