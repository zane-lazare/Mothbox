"""
Cache Warmer Service (Issue #134 - Phase 3)

Background cache warming service with smart triggers:
- Manual warming via API
- Automatic warming on startup
- Smart warming based on usage patterns
- Progress tracking
- Resource-aware execution

Design Approach: Combination (Manual + Smart Auto-Warming)

Manual Triggering:
- API endpoint for on-demand warming
- Parameters: priority (newest/all), sizes (which sizes to warm)
- Background task execution (non-blocking)
- Progress tracking and status reporting

Smart Auto-Warming Triggers:
- On app startup (warm most recent photos)
- When new photos detected (warm new additions)
- When cache hit ratio drops below threshold
- Only when server is not busy (respect system resources)

Usage:
    from services.cache_warmer import CacheWarmer
    from services.thumbnail_cache import ThumbnailCache

    thumbnail_cache = ThumbnailCache(cache_dir=CACHE_DIR)
    cache_warmer = CacheWarmer(
        thumbnail_cache=thumbnail_cache,
        photos_dir=PHOTOS_DIR
    )

    # Manual warming
    result = cache_warmer.warm_recent(count=100)

    # Background monitoring
    cache_warmer.start_background_warming()
"""

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from services.thumbnail_cache import ThumbnailCache, ThumbnailError

# Try to import psutil for CPU monitoring
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Background cache warming service with smart triggers

    Provides:
    - Manual warming via API
    - Automatic warming on startup
    - Smart warming based on usage patterns
    - Progress tracking
    - Resource-aware execution
    """

    def __init__(
        self,
        thumbnail_cache: ThumbnailCache,
        photos_dir: str | Path,
        hit_ratio_threshold: float = 0.80,
        cpu_threshold: float = 0.70,
        check_interval_minutes: int = 5,
    ):
        """
        Initialize cache warmer

        Args:
            thumbnail_cache: ThumbnailCache instance
            photos_dir: Directory containing photos to warm
            hit_ratio_threshold: Trigger warming if hit ratio below this (default: 0.80)
            cpu_threshold: Don't warm if CPU usage above this (default: 0.70)
            check_interval_minutes: Background check interval (default: 5)
        """
        self.thumbnail_cache = thumbnail_cache
        self.photos_dir = Path(photos_dir)
        self.hit_ratio_threshold = hit_ratio_threshold
        self.cpu_threshold = cpu_threshold
        self.check_interval_minutes = check_interval_minutes

        # Task tracking
        self._tasks: dict[str, dict[str, Any]] = {}
        self._task_lock = threading.Lock()
        self._active_task_id: str | None = None

        # Background monitoring
        self._running = False
        self._monitoring_thread: threading.Thread | None = None
        self._monitoring_interval = check_interval_minutes * 60  # Convert to seconds
        self._last_warming_time: float | None = None

        # Maximum task history to keep
        self._max_task_history = 10

        logger.info(
            f"CacheWarmer initialized: photos_dir={photos_dir}, "
            f"hit_ratio_threshold={hit_ratio_threshold}, "
            f"cpu_threshold={cpu_threshold}"
        )

    def warm_photos(
        self,
        photo_paths: list[Path],
        sizes: list[int] | None = None,
        priority: str = "newest",
        background: bool = True,
    ) -> dict[str, Any]:
        """
        Warm cache for specified photos

        Args:
            photo_paths: List of photo paths to warm
            sizes: Sizes to generate (None = all configured)
            priority: "newest" (recent first) or "all" (chronological)
            background: Run in background thread

        Returns:
            Status dict with task_id, progress info
        """
        task_id = str(uuid.uuid4())

        # Use all configured sizes if not specified
        if sizes is None:
            sizes = self.thumbnail_cache.sizes

        # Sort photos by priority
        if priority == "newest":
            # Sort by mtime, newest first
            sorted_photos = sorted(
                photo_paths, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True
            )
        else:
            # Chronological order (oldest first)
            sorted_photos = sorted(
                photo_paths, key=lambda p: p.stat().st_mtime if p.exists() else 0
            )

        # Initialize task tracking
        with self._task_lock:
            self._tasks[task_id] = {
                'task_id': task_id,
                'status': 'running',
                'progress': {'current': 0, 'total': len(sorted_photos), 'percent': 0},
                'started_at': time.time(),
                'completed_at': None,
                'photos_warmed': 0,
                'errors': [],
            }

        if background:
            # Run in background thread
            thread = threading.Thread(
                target=self._warm_photos_worker,
                args=(task_id, sorted_photos, sizes),
                daemon=True,
            )
            thread.start()

            return {
                'task_id': task_id,
                'status': 'started',
                'message': f'Warming {len(sorted_photos)} photos in background',
            }
        else:
            # Run in foreground
            self._warm_photos_worker(task_id, sorted_photos, sizes)

            with self._task_lock:
                task = self._tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': task['status'],
                    'photos_warmed': task['photos_warmed'],
                    'errors': task['errors'],
                }

    def _warm_photos_worker(
        self, task_id: str, photo_paths: list[Path], sizes: list[int]
    ):
        """
        Worker function to warm photos (runs in thread if background=True)

        Args:
            task_id: Task ID for tracking
            photo_paths: Photos to warm
            sizes: Sizes to generate
        """
        photos_warmed = 0
        errors = []

        for idx, photo_path in enumerate(photo_paths):
            # Check if task was cancelled
            with self._task_lock:
                task = self._tasks.get(task_id)
                if task and task['status'] == 'cancelled':
                    logger.info(f"Task {task_id} cancelled")
                    return

            photo_had_error = False

            try:
                # Generate thumbnails for all sizes
                for size in sizes:
                    try:
                        self.thumbnail_cache.get_thumbnail(photo_path, size)
                    except ThumbnailError as e:
                        errors.append({'photo': str(photo_path), 'size': size, 'error': str(e)})
                        photo_had_error = True

                # Only count as warmed if no errors occurred
                if not photo_had_error:
                    photos_warmed += 1

            except Exception as e:
                errors.append({'photo': str(photo_path), 'error': str(e)})
                logger.warning(f"Error warming {photo_path}: {e}")
                photo_had_error = True

            # Update progress
            with self._task_lock:
                task = self._tasks.get(task_id)
                if task:
                    task['progress']['current'] = idx + 1
                    task['progress']['percent'] = int(
                        (idx + 1) / len(photo_paths) * 100
                    )
                    task['photos_warmed'] = photos_warmed
                    task['errors'] = errors

        # Mark as completed
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task['status'] = 'completed'
                task['completed_at'] = time.time()
                task['progress']['percent'] = 100
                task['photos_warmed'] = photos_warmed

        # Update last warming time
        self._last_warming_time = time.time()

        # Cleanup old tasks
        self._cleanup_old_tasks()

        logger.info(
            f"Task {task_id} completed: {photos_warmed} photos warmed, {len(errors)} errors"
        )

    def warm_recent(
        self, count: int = 100, sizes: list[int] | None = None, background: bool = True
    ) -> dict[str, Any]:
        """
        Warm cache for N most recent photos

        Args:
            count: Number of recent photos to warm
            sizes: Sizes to generate (None = all configured)
            background: Run in background thread

        Returns:
            Status dict with task_id, progress info
        """
        # Get recent photos
        recent_photos = self._get_recent_photos(count)

        return self.warm_photos(
            photo_paths=recent_photos,
            sizes=sizes,
            priority="newest",
            background=background,
        )

    def warm_all(
        self, sizes: list[int] | None = None, background: bool = True
    ) -> dict[str, Any]:
        """
        Warm entire cache (all photos in PHOTOS_DIR)

        Args:
            sizes: Sizes to generate (None = all configured)
            background: Run in background thread

        Returns:
            Status dict with task_id, progress info
        """
        # Get all photos
        all_photos = self._get_all_photos()

        return self.warm_photos(
            photo_paths=all_photos, sizes=sizes, priority="all", background=background
        )

    def get_warming_status(self, task_id: str | None = None) -> dict[str, Any]:
        """
        Get warming task status

        Args:
            task_id: Task ID to query (None = return info about all tasks)

        Returns:
            Task status dict or summary of all tasks
        """
        with self._task_lock:
            if task_id is not None:
                # Return specific task
                task = self._tasks.get(task_id)
                if task:
                    return dict(task)  # Return copy
                else:
                    return {
                        'error': 'Task not found',
                        'task_id': task_id,
                    }
            else:
                # Return summary of all tasks
                active_tasks = [
                    tid for tid, task in self._tasks.items() if task['status'] == 'running'
                ]

                return {
                    'active_tasks': len(active_tasks),
                    'total_tasks': len(self._tasks),
                    'task_ids': list(self._tasks.keys()),
                }

    def cancel_warming(self, task_id: str) -> dict[str, Any]:
        """
        Cancel a running warming task

        Args:
            task_id: Task ID to cancel

        Returns:
            Status dict
        """
        with self._task_lock:
            task = self._tasks.get(task_id)
            if not task:
                return {'success': False, 'error': 'Task not found'}

            if task['status'] != 'running':
                return {
                    'success': False,
                    'error': f"Task is {task['status']}, cannot cancel",
                }

            # Mark as cancelled
            task['status'] = 'cancelled'
            task['completed_at'] = time.time()

            return {'success': True, 'message': f'Task {task_id} cancelled'}

    def should_trigger_warming(self) -> bool:
        """
        Determine if auto-warming should trigger

        Checks:
        - Cache hit ratio below threshold (e.g., <80%)
        - System CPU usage acceptable (e.g., <70%)
        - Not currently warming
        - Sufficient time since last warming (5+ minutes)

        Returns:
            True if warming recommended
        """
        # Check if already warming
        with self._task_lock:
            active_tasks = [
                task for task in self._tasks.values() if task['status'] == 'running'
            ]
            if active_tasks:
                return False

        # Check if enough time has passed since last warming
        if self._last_warming_time is not None:
            time_since_last_warming = time.time() - self._last_warming_time
            if time_since_last_warming < self._monitoring_interval:
                return False

        # Check cache statistics
        stats = self.thumbnail_cache.get_statistics()

        # Need minimum requests before evaluating hit ratio
        if stats['total_requests'] < 100:
            return False

        # Check hit ratio
        if stats['hit_ratio'] >= self.hit_ratio_threshold:
            return False

        # Check CPU usage (if psutil available)
        if HAS_PSUTIL:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > (self.cpu_threshold * 100):
                    logger.debug(
                        f"CPU usage too high ({cpu_percent}%), skipping warming"
                    )
                    return False
            except Exception as e:
                logger.warning(f"Error checking CPU usage: {e}")
                # Assume CPU is OK if we can't check

        return True

    def detect_new_photos(self, since: float | None = None) -> list[Path]:
        """
        Detect new photos added since timestamp

        Args:
            since: Unix timestamp (None = last warming time)

        Returns:
            List of new photo paths
        """
        if since is None:
            since = self._last_warming_time if self._last_warming_time else 0

        new_photos = []

        if not self.photos_dir.exists():
            return new_photos

        # Find photos modified after timestamp
        for photo_path in self.photos_dir.rglob("*.jpg"):
            try:
                if photo_path.is_file() and photo_path.stat().st_mtime > since:
                    new_photos.append(photo_path)
            except (OSError, PermissionError):
                continue

        return new_photos

    def start_background_warming(self):
        """Start background monitoring thread for auto-warming"""
        if self._running:
            logger.warning("Background warming already running")
            return

        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()

        logger.info("Background cache warming monitoring started")

    def stop_background_warming(self):
        """Stop background monitoring thread"""
        if not self._running:
            return

        self._running = False

        # Wait for thread to terminate (with timeout)
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)

        logger.info("Background cache warming monitoring stopped")

    def _monitoring_loop(self):
        """Background monitoring thread for smart auto-warming"""
        logger.info("Cache warming monitoring loop started")

        while self._running:
            try:
                # Sleep first (check interval)
                sleep_time = self._monitoring_interval
                # Break sleep into smaller chunks to allow quick shutdown
                while sleep_time > 0 and self._running:
                    time.sleep(min(sleep_time, 10))
                    sleep_time -= 10

                if not self._running:
                    break

                # Check if warming should trigger
                if self.should_trigger_warming():
                    logger.info("Auto-warming triggered by smart detection")

                    # Check for new photos
                    new_photos = self.detect_new_photos()
                    if new_photos:
                        logger.info(f"Detected {len(new_photos)} new photos")
                        self.warm_photos(new_photos, background=True)
                    else:
                        # No new photos, warm recent photos
                        stats = self.thumbnail_cache.get_statistics()
                        if stats['hit_ratio'] < self.hit_ratio_threshold:
                            logger.info(
                                f"Low hit ratio ({stats['hit_ratio']:.2%}), "
                                "warming recent photos"
                            )
                            self.warm_recent(count=100, background=True)

            except Exception as e:
                logger.error(f"Error in cache warming monitoring: {e}", exc_info=True)

        logger.info("Cache warming monitoring loop stopped")

    def _get_recent_photos(self, count: int) -> list[Path]:
        """
        Get N most recent photos from photos_dir

        Args:
            count: Number of recent photos to return

        Returns:
            List of photo paths, sorted by mtime (newest first)
        """
        if not self.photos_dir.exists():
            return []

        photos = []
        for photo_path in self.photos_dir.rglob("*.jpg"):
            if photo_path.is_file():
                try:
                    photos.append((photo_path, photo_path.stat().st_mtime))
                except (OSError, PermissionError):
                    continue

        # Sort by mtime, newest first
        photos.sort(key=lambda x: x[1], reverse=True)

        return [p[0] for p in photos[:count]]

    def _get_all_photos(self) -> list[Path]:
        """
        Get all photos from photos_dir

        Returns:
            List of all photo paths
        """
        if not self.photos_dir.exists():
            return []

        photos = []
        for photo_path in self.photos_dir.rglob("*.jpg"):
            if photo_path.is_file():
                photos.append(photo_path)

        return photos

    def _cleanup_old_tasks(self):
        """Remove old completed/cancelled tasks to prevent memory growth"""
        with self._task_lock:
            if len(self._tasks) <= self._max_task_history:
                return

            # Keep only most recent tasks
            sorted_tasks = sorted(
                self._tasks.items(), key=lambda x: x[1]['started_at'], reverse=True
            )

            # Keep max_task_history most recent
            tasks_to_keep = dict(sorted_tasks[: self._max_task_history])

            self._tasks = tasks_to_keep

            logger.debug(f"Cleaned up old tasks, kept {len(self._tasks)}")
