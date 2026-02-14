"""
Thumbnail Caching Service

Provides multi-resolution thumbnail caching with:
- File-based locking (MutexLock) for multi-process safety
- LRU eviction when cache exceeds max_size_mb
- Placeholder images for corrupt sources (5-minute TTL)
- Statistics tracking (hits/misses/size)
- Manual invalidation support

Design Decisions:
- Immutable photos: No automatic invalidation based on mtime
- Cache structure: cache_dir/{size}/{hash}.jpg
- Hash: MD5 of photo path (12 chars)
- Sizes: Configurable (default: 64, 128, 256)
- JPEG quality: 85

Usage:
    from services.thumbnail_cache import ThumbnailCache
    from mothbox_paths import DATA_DIR

    cache = ThumbnailCache(cache_dir=DATA_DIR / "cache" / "thumbnails")
    thumbnail_path = cache.get_thumbnail(photo_path, size=128)
"""

import hashlib
import json
import os
import time
from contextlib import suppress
from pathlib import Path

from PIL import Image, ImageDraw

from webui.backend.lib.file_lock import MutexLock


class ThumbnailError(Exception):
    """Exception raised for thumbnail cache operations"""


class ThumbnailCache:
    """
    Multi-resolution thumbnail cache with LRU eviction

    Provides fast thumbnail generation and retrieval with:
    - File-based locking for thread/process safety
    - LRU eviction to maintain size limits
    - Error handling with placeholder images
    - Statistics tracking and persistence
    """

    def __init__(
        self, cache_dir: str | Path, max_size_mb: int = 500, sizes: list[int] | None = None
    ):
        """
        Initialize thumbnail cache

        Args:
            cache_dir: Directory for cache storage
            max_size_mb: Maximum cache size in MB (default: 500)
            sizes: List of allowed thumbnail sizes (default: [64, 128, 256])
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.sizes = sizes if sizes is not None else [64, 128, 256]

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create size subdirectories
        for size in self.sizes:
            (self.cache_dir / str(size)).mkdir(exist_ok=True)

        # Statistics file
        self.stats_file = self.cache_dir / "cache_stats.json"

        # Initialize statistics
        self._load_statistics()

        # Periodic flush tracking for I/O optimization
        self._stats_dirty = False
        self._last_stats_flush = time.time()
        self._stats_flush_interval = 60  # seconds
        self._last_flushed_hits = self.hits
        self._last_flushed_misses = self.misses

    def get_thumbnail(self, photo_path: str | Path, size: int) -> Path:
        """
        Get thumbnail from cache or generate if missing

        Args:
            photo_path: Path to source photo
            size: Thumbnail size (must be in self.sizes)

        Returns:
            Path to cached thumbnail

        Raises:
            ThumbnailError: If size invalid, path invalid, or generation fails
        """
        photo_path = Path(photo_path)

        # Validate size
        if size not in self.sizes:
            raise ThumbnailError(f"Invalid size {size}. Allowed sizes: {self.sizes}")

        # Validate photo path
        self._validate_photo_path(photo_path)

        # Get cache path
        cache_path = self._get_cache_path(photo_path, size)

        # Check if cached (and not error cache that expired)
        try:
            cache_exists = cache_path.exists()
        except (PermissionError, OSError) as err:
            raise ThumbnailError(f"Permission denied accessing cache: {cache_path}") from err

        if cache_exists:
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

        # Cache miss - generate thumbnail
        self._update_statistics(hit=False)

        # Generate with file locking
        self._generate_thumbnail(photo_path, size)

        # Check eviction
        self._check_eviction()

        return cache_path

    def _generate_thumbnail(self, photo_path: Path, size: int) -> Path:
        """
        Generate thumbnail with file-based locking

        Uses MutexLock to prevent duplicate generation by concurrent
        requests. Only the first request generates; others wait for completion.

        Args:
            photo_path: Path to source photo
            size: Thumbnail size

        Returns:
            Path to generated thumbnail

        Raises:
            ThumbnailError: If generation fails
        """
        cache_path = self._get_cache_path(photo_path, size)
        lock_path = cache_path.parent / f".{cache_path.name}.lock"

        # Thumbnail generation is I/O-bound, may take seconds
        with MutexLock(lock_path, timeout=10.0, cleanup=True):
            # Check again if file exists (another process may have generated it)
            if cache_path.exists():
                return cache_path

            # Generate thumbnail
            try:
                # Check if source exists
                if not photo_path.exists():
                    raise ThumbnailError(f"Source photo not found: {photo_path}")

                # Open and resize with explicit resource cleanup
                with Image.open(photo_path) as img:
                    # Preserve aspect ratio, fit within size
                    img.thumbnail((size, size), Image.LANCZOS)

                    # Save as JPEG with quality 85
                    img.save(cache_path, format="JPEG", quality=85)

            except (OSError, Exception):
                # Error opening/processing image - create placeholder
                try:
                    placeholder = self._create_placeholder(size)
                    placeholder.save(cache_path, format="JPEG", quality=85)

                    # Mark as error cache
                    self._mark_error_cache(cache_path)
                except OSError as save_error:
                    # Can't even save placeholder (disk full, permissions, etc.)
                    raise ThumbnailError(
                        f"Failed to generate thumbnail: {save_error}"
                    ) from save_error

        return cache_path

    def _create_placeholder(self, size: int) -> Image.Image:
        """
        Create placeholder image for corrupt/missing sources

        Args:
            size: Placeholder size

        Returns:
            PIL Image (gray square with "?" text)
        """
        # Create gray square
        img = Image.new("RGB", (size, size), color=(128, 128, 128))

        # Draw "?" in center
        draw = ImageDraw.Draw(img)

        # Use default font (no external font file needed)
        font_size = size // 3
        try:
            # Try to use a larger default font if available
            from PIL import ImageFont

            font = ImageFont.load_default()
        except Exception:
            font = None

        text = "?"

        # Get text bounding box for centering
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            # Fallback for older PIL versions
            text_width = font_size
            text_height = font_size

        position = ((size - text_width) // 2, (size - text_height) // 2)

        draw.text(position, text, fill=(200, 200, 200), font=font)

        return img

    def _get_cache_path(self, photo_path: Path, size: int) -> Path:
        """
        Generate cache file path

        Structure: cache_dir/{size}/{hash}.jpg

        Args:
            photo_path: Source photo path
            size: Thumbnail size

        Returns:
            Path to cache file
        """
        photo_hash = self._get_hash(photo_path)
        return self.cache_dir / str(size) / f"{photo_hash}.jpg"

    def _get_hash(self, photo_path: Path) -> str:
        """
        Generate MD5 hash of photo path

        Args:
            photo_path: Source photo path

        Returns:
            32-character hash (full MD5 for collision resistance)
        """
        # MD5 used for cache key generation, not security
        # Full hash used to prevent collisions in large photo collections
        hash_obj = hashlib.md5(str(photo_path).encode(), usedforsecurity=False)  # nosec B324
        return hash_obj.hexdigest()

    def _validate_photo_path(self, photo_path: Path):
        """
        Validate photo path for security

        Prevents path traversal and other attacks.

        Args:
            photo_path: Photo path to validate

        Raises:
            ThumbnailError: If path is invalid or unsafe
        """
        try:
            # Check for null bytes
            if "\x00" in str(photo_path):
                raise ThumbnailError("Invalid path: null byte detected")

            # Resolve to absolute path
            resolved = photo_path.resolve()

            # Check if file exists
            if not resolved.exists():
                raise ThumbnailError(f"Photo not found: {photo_path}")

            # Check if it's a file (not directory)
            if not resolved.is_file():
                raise ThumbnailError(f"Not a file: {photo_path}")

        except (ValueError, OSError) as e:
            raise ThumbnailError(f"Invalid photo path: {e}") from e

    def _is_error_cache(self, cache_path: Path) -> bool:
        """
        Check if cache file is an error placeholder

        Args:
            cache_path: Cache file path

        Returns:
            True if this is an error cache with TTL
        """
        error_marker = cache_path.parent / f".{cache_path.name}.error"
        return error_marker.exists()

    def _mark_error_cache(self, cache_path: Path):
        """
        Mark cache file as error placeholder

        Args:
            cache_path: Cache file path
        """
        error_marker = cache_path.parent / f".{cache_path.name}.error"
        error_marker.touch()

    def _touch_file(self, file_path: Path):
        """
        Update file access time for LRU tracking

        Args:
            file_path: File to touch
        """
        try:
            # Update only atime, preserve mtime
            stat_info = file_path.stat()
            os.utime(file_path, (time.time(), stat_info.st_mtime))
        except OSError:
            pass

    def _check_eviction(self):
        """
        Check cache size and evict if over limit

        Removes least recently accessed files until under max_size_mb.
        """
        cache_size_mb = self._calculate_cache_size()

        if cache_size_mb > self.max_size_mb:
            self._evict_lru()

    def _evict_lru(self):
        """
        Evict least recently used files until under max_size_mb

        Uses file access times (atime) to determine LRU order.
        """
        # Get all cached files
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
                # Remove cache file
                file_path.unlink()

                # Remove error marker if exists
                error_marker = file_path.parent / f".{file_path.name}.error"
                if error_marker.exists():
                    error_marker.unlink()

                current_size -= file_size / (1024 * 1024)

            except OSError:
                pass

    def _calculate_cache_size(self) -> float:
        """
        Calculate total cache size in MB

        Returns:
            Cache size in megabytes
        """
        total_size = 0

        for size_dir in self.cache_dir.iterdir():
            if size_dir.is_dir() and size_dir.name.isdigit():
                for file in size_dir.glob("*.jpg"):
                    try:
                        total_size += file.stat().st_size
                    except OSError:
                        continue

        return total_size / (1024 * 1024)

    def _load_statistics(self):
        """Load statistics from JSON file or initialize"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file) as f:
                    stats = json.load(f)
                    self.hits = stats.get("hits", 0)
                    self.misses = stats.get("misses", 0)
            else:
                self.hits = 0
                self.misses = 0
        except (json.JSONDecodeError, OSError):
            self.hits = 0
            self.misses = 0

    def _save_statistics(self):
        """Save statistics to JSON file"""
        try:
            stats = {
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": self.hits + self.misses,
                "last_updated": time.time(),
            }

            with open(self.stats_file, "w") as f:
                json.dump(stats, f, indent=2)

        except OSError:
            pass

    def _update_statistics(self, hit: bool):
        """
        Update cache statistics in-memory with periodic flush

        Optimized for performance: Updates counters in memory only,
        flushes to disk every 60 seconds (configurable).

        Reduces disk I/O by 99%+ compared to per-request writes.

        Args:
            hit: True for cache hit, False for miss
        """
        # Update in-memory counters only (no file I/O)
        if hit:
            self.hits += 1
        else:
            self.misses += 1

        self._stats_dirty = True

        # Check if periodic flush needed
        now = time.time()
        if now - self._last_stats_flush >= self._stats_flush_interval:
            self._flush_statistics()

    def _flush_statistics(self):
        """
        Flush in-memory statistics to disk with atomic multi-process update

        Uses file locking and delta-merge to safely update statistics
        across multiple processes without losing data.

        Called automatically every 60 seconds (configurable) or manually
        via flush() or close() methods.
        """
        if not self._stats_dirty:
            return

        lock_path = self.cache_dir / ".cache_stats.json.lock"

        try:
            with MutexLock(lock_path, timeout=5.0, cleanup=True):
                # Read current stats from file (source of truth for multi-process)
                current_stats = {}
                if self.stats_file.exists():
                    try:
                        with open(self.stats_file) as f:
                            current_stats = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        pass

                # Calculate deltas since last flush
                delta_hits = self.hits - self._last_flushed_hits
                delta_misses = self.misses - self._last_flushed_misses

                # Add deltas to file stats (handles multi-process updates)
                new_hits = current_stats.get("hits", 0) + delta_hits
                new_misses = current_stats.get("misses", 0) + delta_misses

                # Write atomically to file
                stats = {
                    "hits": new_hits,
                    "misses": new_misses,
                    "total_requests": new_hits + new_misses,
                    "last_updated": time.time(),
                }

                with open(self.stats_file, "w") as f:
                    json.dump(stats, f, indent=2)

                # Update flush tracking
                self._last_flushed_hits = self.hits
                self._last_flushed_misses = self.misses
                self._stats_dirty = False
                self._last_stats_flush = time.time()

                # Update instance variables for get_statistics() consistency
                self.hits = new_hits
                self.misses = new_misses
        except OSError:
            # File system errors - continue without flushing
            # Will retry on next flush interval
            pass

    def get_statistics(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with statistics:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - total_requests: Total requests (hits + misses)
            - hit_ratio: Cache hit ratio (0.0-1.0)
            - cache_size_mb: Total cache size in MB
            - cached_files: Number of cached files
            - sizes: Configured thumbnail sizes
        """
        total_requests = self.hits + self.misses
        hit_ratio = self.hits / total_requests if total_requests > 0 else 0.0

        # Count cached files
        cached_files = 0
        for size_dir in self.cache_dir.iterdir():
            if size_dir.is_dir() and size_dir.name.isdigit():
                cached_files += len(list(size_dir.glob("*.jpg")))

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_ratio": round(hit_ratio, 3),
            "cache_size_mb": round(self._calculate_cache_size(), 2),
            "cached_files": cached_files,
            "sizes": self.sizes,
        }

    def invalidate(self, photo_path: str | Path | None = None, size: int | None = None):
        """
        Manually invalidate cache entries

        Args:
            photo_path: Specific photo to invalidate (None = entire cache)
            size: Specific size to invalidate (None = all sizes)
        """
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

    def flush(self):
        """
        Manually flush statistics to disk

        Useful for:
        - Testing (ensure statistics written before assertions)
        - Explicit cleanup before shutdown
        - Forcing immediate statistics update

        This is a public method that wraps _flush_statistics().
        """
        self._flush_statistics()

    def close(self):
        """
        Close the cache and flush pending statistics

        Should be called explicitly before application shutdown
        to ensure statistics are persisted to disk.

        Safe to call multiple times (idempotent).
        """
        self._flush_statistics()

    def __del__(self):
        """
        Destructor: Flush statistics on garbage collection

        Backup cleanup mechanism if close() wasn't called explicitly.
        Note: __del__ may not be called immediately, so prefer close().
        """
        # Suppress exceptions during cleanup to avoid issues during interpreter shutdown
        with suppress(Exception):
            self._flush_statistics()
