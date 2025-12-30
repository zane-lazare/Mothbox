"""
Export Job Service - Job queue management for async exports.

Manages export job lifecycle:
- Job creation and queuing
- Background worker thread execution
- Job state transitions (PENDING → RUNNING → COMPLETED/FAILED)
- Single job concurrency (queue-based processing)
- SQLite persistence (jobs survive server restarts)
- Timeout handling (default 10 minutes)
- Automatic cleanup of expired jobs

Usage:
    from webui.backend.services.export_job_service import ExportJobService
    from webui.backend.services.export_metadata_service import ExportMetadataService

    export_svc = ExportMetadataService(...)
    job_svc = ExportJobService(
        db_path="/var/lib/mothbox/export_jobs.db",
        export_service=export_svc,
        photos_dir="/var/lib/mothbox/photos",
    )

    # Start worker
    job_svc.start()

    # Create job
    job = job_svc.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(date_start="2024-01-01"),
    )

    # Monitor progress
    while True:
        job = job_svc.get_job(job.id)
        if job.status in (ExportJobStatus.COMPLETED, ExportJobStatus.FAILED):
            break
        time.sleep(1)

    # Download result
    if job.status == ExportJobStatus.COMPLETED:
        download_path = job_svc.get_download_path(job.id)
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path

from webui.backend.lib.export_job_db import ExportJobDB
from webui.backend.lib.export_job_types import (
    ExportJob,
    ExportJobFilter,
    ExportJobFormat,
    ExportJobStatus,
)
from webui.backend.lib.series_detection import SeriesType, detect_series_type
from webui.backend.services.export_metadata_service import ExportMetadataService
from webui.backend.services.sidecar_service import SidecarService

logger = logging.getLogger(__name__)


class ExportJobService:
    """
    Export job queue management service.

    Manages async export jobs with:
    - Single job concurrency (queue-based)
    - 10-minute default timeout
    - SQLite persistence
    - Background worker thread
    - Progress tracking
    """

    def __init__(
        self,
        db_path: Path | str,
        export_service: ExportMetadataService,
        photos_dir: Path | str,
        temp_dir: Path | str | None = None,
        job_timeout_seconds: int = 600,  # 10 minutes
        job_ttl_seconds: int = 3600,  # 1 hour
        max_history: int = 50,
        sidecar_service: SidecarService | None = None,
    ):
        """
        Initialize export job service.

        Args:
            db_path: Path to SQLite database
            export_service: ExportMetadataService instance for executing exports
            photos_dir: Directory containing photos
            temp_dir: Directory for temporary export files (default: system temp)
            job_timeout_seconds: Max execution time per job (default: 600 = 10 min)
            job_ttl_seconds: Time to keep completed jobs before cleanup (default: 3600 = 1 hour)
            max_history: Max number of completed jobs to keep (default: 50)
            sidecar_service: SidecarService instance for metadata filtering (default: create new)
        """
        self._db_path = Path(db_path)
        self._export_service = export_service
        self._photos_dir = Path(photos_dir)
        self._temp_dir = Path(temp_dir) if temp_dir else None
        self._job_timeout_seconds = job_timeout_seconds
        self._job_ttl_seconds = job_ttl_seconds
        self._max_history = max_history
        self._sidecar_service = sidecar_service or SidecarService(photos_dir)

        # Initialize database
        self._db = ExportJobDB(self._db_path)

        # Worker thread state
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._worker_lock = threading.Lock()

        # Cancellation tracking
        self._cancelled_jobs: set[str] = set()
        self._cancel_lock = threading.Lock()

        logger.info(
            "ExportJobService initialized: db=%s, timeout=%ds, ttl=%ds, max_history=%d",
            self._db_path,
            self._job_timeout_seconds,
            self._job_ttl_seconds,
            self._max_history,
        )

    # =========================================================================
    # Job Creation
    # =========================================================================

    def create_job(
        self,
        format: ExportJobFormat,
        filter: ExportJobFilter,
        options: dict | None = None,
        ttl_seconds: int | None = None,
    ) -> ExportJob:
        """
        Create and queue a new export job.

        Args:
            format: Export format (DARWIN_CORE, INATURALIST, JSON, CSV)
            filter: Filter criteria for photo selection
            options: Format-specific options
            ttl_seconds: Custom TTL in seconds (uses service default if None)

        Returns:
            Created ExportJob with PENDING status
        """
        from webui.backend.lib.export_job_types import ExportJobProgress

        # Merge user options with internal TTL setting
        job_options = dict(options) if options else {}
        if ttl_seconds is not None:
            job_options["_ttl_seconds"] = ttl_seconds

        job = ExportJob(
            job_id=str(uuid.uuid4()),
            status=ExportJobStatus.PENDING,
            format=format,
            filter=filter,
            progress=ExportJobProgress(),
            options=job_options,
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            output_path=None,
            photo_count=0,
            error_message=None,
        )

        self._db.create_job(job)

        logger.info("Created export job: id=%s, format=%s", job.job_id, job.format.value)

        return job

    # =========================================================================
    # Job Retrieval
    # =========================================================================

    def get_job(self, job_id: str) -> ExportJob | None:
        """
        Get job by ID.

        Args:
            job_id: Job UUID

        Returns:
            ExportJob or None if not found
        """
        return self._db.get_job(job_id)

    def list_jobs(
        self,
        status: ExportJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ExportJob], int]:
        """
        List jobs with optional status filter.

        Args:
            status: Filter by status (default: all statuses)
            limit: Max jobs to return (default: 50)
            offset: Offset for pagination (default: 0)

        Returns:
            Tuple of (jobs, total_count)
        """
        jobs = self._db.list_jobs(status=status, limit=limit, offset=offset)
        total = self._db.count_jobs(status=status)
        return (jobs, total)

    # =========================================================================
    # Job Control
    # =========================================================================

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running or pending job.

        Args:
            job_id: Job UUID

        Returns:
            True if cancelled, False if job doesn't exist or can't be cancelled
        """
        job = self.get_job(job_id)
        if not job:
            logger.warning("Cannot cancel job - not found: id=%s", job_id)
            return False

        # Can only cancel PENDING or RUNNING jobs
        if job.status not in (ExportJobStatus.PENDING, ExportJobStatus.RUNNING):
            logger.warning(
                "Cannot cancel job - wrong status: id=%s, status=%s",
                job_id,
                job.status.value,
            )
            return False

        # Mark for cancellation
        with self._cancel_lock:
            self._cancelled_jobs.add(job_id)

        # Update job status
        job.status = ExportJobStatus.CANCELLED
        job.completed_at = time.time()
        # Cancelled jobs also expire (for cleanup)
        job_ttl = job.options.get("_ttl_seconds", self._job_ttl_seconds)
        job.expires_at = job.completed_at + job_ttl
        self._db.update_job(job)

        logger.info("Cancelled job: id=%s", job_id)

        return True

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a completed/failed/cancelled job.

        Cannot delete PENDING or RUNNING jobs (must cancel first).

        Args:
            job_id: Job UUID

        Returns:
            True if deleted, False if job doesn't exist or can't be deleted
        """
        job = self.get_job(job_id)
        if not job:
            logger.warning("Cannot delete job - not found: id=%s", job_id)
            return False

        # Can only delete finished jobs
        if job.status in (ExportJobStatus.PENDING, ExportJobStatus.RUNNING):
            logger.warning(
                "Cannot delete job - still active: id=%s, status=%s",
                job_id,
                job.status.value,
            )
            return False

        # Delete from database
        self._db.delete_job(job_id)

        # Clean up output file if exists
        if job.output_path:
            try:
                output_path = Path(job.output_path)
                if output_path.exists():
                    output_path.unlink()
                    logger.debug("Deleted output file: %s", output_path)
            except Exception as e:
                logger.warning("Failed to delete output file: %s - %s", job.output_path, e)

        logger.info("Deleted job: id=%s", job_id)

        return True

    # =========================================================================
    # Download
    # =========================================================================

    def get_download_path(self, job_id: str) -> Path | None:
        """
        Get output file path for completed job.

        Args:
            job_id: Job UUID

        Returns:
            Path to output file, or None if job not completed, not found,
            or path fails security validation.
        """
        job = self.get_job(job_id)
        if not job:
            return None

        if job.status != ExportJobStatus.COMPLETED:
            return None

        if not job.output_path:
            return None

        output_path = Path(job.output_path).resolve()

        # Security: Validate path is within allowed temp directory
        # Prevents path traversal if database is compromised
        import tempfile

        allowed_dir = (self._temp_dir or Path(tempfile.gettempdir())).resolve()
        try:
            output_path.relative_to(allowed_dir)
        except ValueError:
            # Path is outside allowed directory - security violation
            logger.warning("Path traversal attempt blocked: %s not in %s", output_path, allowed_dir)
            return None

        return output_path

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def start(self) -> None:
        """
        Start the worker thread and resume pending jobs.

        Idempotent - safe to call multiple times.
        """
        with self._worker_lock:
            if self._running:
                logger.debug("Worker already running")
                return

            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_thread_main,
                daemon=True,
                name="export-job-worker",
            )
            self._worker_thread.start()

            logger.info("Export job worker started")

    def stop(self) -> None:
        """
        Stop the worker thread gracefully.

        Waits for current job to finish or timeout.
        """
        with self._worker_lock:
            if not self._running:
                logger.debug("Worker not running")
                return

            self._running = False

        # Wait for worker thread to stop
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not stop cleanly")
            else:
                logger.info("Export job worker stopped")

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict:
        """
        Get service statistics.

        Returns:
            Dictionary with statistics:
            - total_jobs: Total number of jobs
            - pending_jobs: Jobs waiting to run
            - running_jobs: Jobs currently executing
            - completed_jobs: Successfully completed jobs
            - failed_jobs: Failed jobs
            - cancelled_jobs: Cancelled jobs
            - worker_running: Whether worker thread is active
        """
        # Get counts by status
        stats = {
            "total_jobs": 0,
            "pending_jobs": 0,
            "running_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "worker_running": self._running,
        }

        # Query database for counts using efficient aggregate query
        counts = self._db.count_jobs_by_status()
        stats["total_jobs"] = counts["total"]
        stats["pending_jobs"] = counts["pending"]
        stats["running_jobs"] = counts["running"]
        stats["completed_jobs"] = counts["completed"]
        stats["failed_jobs"] = counts["failed"]
        stats["cancelled_jobs"] = counts["cancelled"]

        return stats

    # =========================================================================
    # Worker Thread
    # =========================================================================

    def _worker_thread_main(self) -> None:
        """Background worker that processes queued jobs."""
        logger.info("Worker thread started")

        while self._running:
            # Get next pending job
            job = self._get_next_pending_job()

            if job:
                # Execute job
                self._execute_job(job)
            else:
                # No jobs - sleep and check again
                time.sleep(1.0)

            # Periodic cleanup
            self._cleanup_expired_jobs()
            self._cleanup_old_jobs()

        logger.info("Worker thread stopped")

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def _update_progress(
        self,
        job: ExportJob,
        phase: str | None = None,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        """
        Update job progress and persist to database.

        Args:
            job: Job to update
            phase: New phase name (e.g., "collecting", "exporting", "finalizing")
            current: Number of items processed
            total: Total items to process
        """
        if phase is not None:
            job.progress.phase = phase
        if current is not None:
            job.progress.current = current
        if total is not None:
            job.progress.total = total
        job.progress.percent = job.progress.calculate_percent()
        self._db.update_job(job)

    def _make_progress_callback(self, job: ExportJob) -> Callable[[int, int], None]:
        """
        Create a progress callback for batch operations.

        Args:
            job: Job to update progress for

        Returns:
            Callable that accepts (current, total) and updates job progress
        """

        def callback(current: int, total: int) -> None:
            self._update_progress(job, current=current, total=total)

        return callback

    def _get_next_pending_job(self) -> ExportJob | None:
        """Get next pending job from queue."""
        jobs = self._db.list_jobs(status=ExportJobStatus.PENDING, limit=1, offset=0)

        if not jobs:
            return None

        return jobs[0]

    def _execute_job(self, job: ExportJob) -> None:
        """
        Execute a single export job with timeout handling.

        Args:
            job: Job to execute
        """
        logger.info("Executing job: id=%s, format=%s", job.job_id, job.format.value)

        # Check if cancelled before starting and update status atomically
        with self._cancel_lock:
            if job.job_id in self._cancelled_jobs:
                logger.info("Job cancelled before execution: id=%s", job.job_id)
                return

            # Update status to RUNNING while holding lock to prevent race
            job.status = ExportJobStatus.RUNNING
            job.started_at = time.time()
            job.progress.phase = "collecting"
            self._db.update_job(job)

        # Execute with timeout using ThreadPoolExecutor
        try:
            # Collect photos first (usually fast)
            photo_paths = self._collect_photos(job.filter)

            # Check for cancellation after photo collection
            with self._cancel_lock:
                if job.job_id in self._cancelled_jobs:
                    logger.info("Job cancelled during execution: id=%s", job.job_id)
                    return

            logger.info("Collected %d photos for export: id=%s", len(photo_paths), job.job_id)

            # Update progress: collection complete, starting export
            self._update_progress(job, phase="exporting", total=len(photo_paths), current=0)

            # Execute export with proper timeout enforcement
            output_path = None
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_export, job, photo_paths)
                try:
                    output_path = future.result(timeout=self._job_timeout_seconds)
                except FuturesTimeoutError:
                    future.cancel()
                    raise TimeoutError(
                        f"Job execution timeout after {self._job_timeout_seconds}s"
                    ) from None

            # Check for cancellation after execution
            with self._cancel_lock:
                if job.job_id in self._cancelled_jobs:
                    logger.info("Job cancelled after execution: id=%s", job.job_id)
                    # Clean up output file
                    try:
                        if output_path and output_path.exists():
                            output_path.unlink()
                    except OSError as e:
                        logger.warning(
                            "Failed to delete output file for cancelled job %s: %s", job.job_id, e
                        )
                    return

            # Update progress: export complete, finalizing
            self._update_progress(job, phase="finalizing", current=len(photo_paths))

            # Update job with success
            job.output_path = str(output_path)
            job.output_size_bytes = output_path.stat().st_size if output_path.exists() else 0
            job.photo_count = len(photo_paths)
            job.status = ExportJobStatus.COMPLETED
            job.completed_at = time.time()
            # Set expiration based on per-job TTL or service default
            job_ttl = job.options.get("_ttl_seconds", self._job_ttl_seconds)
            job.expires_at = job.completed_at + job_ttl
            # Final progress update: completed
            job.progress.phase = "completed"
            job.progress.current = len(photo_paths)
            job.progress.percent = 100
            self._db.update_job(job)

            logger.info(
                "Job completed: id=%s, photos=%d, output=%s, expires_at=%s",
                job.job_id,
                len(photo_paths),
                output_path,
                job.expires_at,
            )

        except TimeoutError as e:
            logger.error("Job timeout: id=%s - %s", job.job_id, e)
            job.status = ExportJobStatus.FAILED
            job.completed_at = time.time()
            # Failed jobs also expire (for cleanup)
            job_ttl = job.options.get("_ttl_seconds", self._job_ttl_seconds)
            job.expires_at = job.completed_at + job_ttl
            job.error_message = str(e)
            self._db.update_job(job)

        except Exception as e:
            logger.error("Job failed: id=%s - %s", job.job_id, e, exc_info=True)
            job.status = ExportJobStatus.FAILED
            job.completed_at = time.time()
            # Failed jobs also expire (for cleanup)
            job_ttl = job.options.get("_ttl_seconds", self._job_ttl_seconds)
            job.expires_at = job.completed_at + job_ttl
            job.error_message = str(e)
            self._db.update_job(job)

        finally:
            # Remove from cancelled set
            with self._cancel_lock:
                self._cancelled_jobs.discard(job.job_id)

    # =========================================================================
    # Photo Collection
    # =========================================================================

    def _collect_photos(self, filter: ExportJobFilter) -> list[Path]:
        """
        Collect photos matching filter criteria.

        Args:
            filter: Filter criteria

        Returns:
            List of photo paths
        """
        # If explicit photo paths provided, use those
        if filter.photo_paths:
            return [Path(p) for p in filter.photo_paths]

        # Otherwise, scan photos directory with single traversal
        photos = []

        for photo_path in self._photos_dir.rglob("*"):
            # Skip non-JPEG files
            if photo_path.suffix.lower() not in (".jpg", ".jpeg"):
                continue
            # Apply filters
            if not self._matches_filter(photo_path, filter):
                continue
            photos.append(photo_path)

        # Sort by name for consistent ordering
        photos.sort()

        return photos

    def _matches_filter(self, photo_path: Path, filter: ExportJobFilter) -> bool:
        """
        Check if photo matches filter criteria.

        Args:
            photo_path: Path to photo
            filter: Filter criteria

        Returns:
            True if photo matches filter
        """
        # Date filtering (filename timestamp with mtime fallback)
        if filter.date_start or filter.date_end:
            from webui.backend.lib.date_utils import get_photo_date, parse_date_filter

            photo_date = get_photo_date(photo_path)

            # If we can't determine date and filter requires it, exclude photo
            if photo_date is None:
                return False

            # Check date_start (inclusive)
            if filter.date_start:
                start_date = parse_date_filter(filter.date_start)
                if start_date and photo_date < start_date:
                    return False

            # Check date_end (inclusive)
            if filter.date_end:
                end_date = parse_date_filter(filter.date_end)
                if end_date and photo_date > end_date:
                    return False

        # Deployment filtering (check if photo is in deployment directory)
        if filter.deployment:
            deployment_path = Path(filter.deployment)
            photo_parents = photo_path.parents

            # Check if deployment is a full path or just a directory name
            if deployment_path.is_absolute():
                # Full path: photo must be inside deployment directory
                if not any(parent == deployment_path for parent in photo_parents):
                    return False
            else:
                # Directory name: check if any parent has this exact name
                deployment_name = deployment_path.name or str(deployment_path)
                if not any(parent.name == deployment_name for parent in photo_parents):
                    return False

        # Series type filtering (uses filename pattern detection)
        if filter.series_type:
            series_info = detect_series_type(photo_path.name)
            # Handle both SeriesType enum and string for backward compat
            filter_value = (
                filter.series_type.value
                if isinstance(filter.series_type, SeriesType)
                else filter.series_type
            )
            if not series_info or series_info.series_type != filter_value:
                return False

        # Get sidecar metadata once if needed for tags or species filtering
        metadata = None
        if filter.tags or filter.has_species:
            metadata = self._sidecar_service.get_metadata(str(photo_path))

        # Tags filtering (any tag matches)
        if filter.tags:
            if not metadata or not metadata.tags:
                return False
            if not any(tag in metadata.tags for tag in filter.tags):
                return False

        # Species filtering (has_species = True means only include photos with species)
        if filter.has_species and (not metadata or not metadata.species):  # noqa: SIM103
            return False

        return True

    # =========================================================================
    # Export Execution
    # =========================================================================

    def _execute_export(self, job: ExportJob, photo_paths: list[Path]) -> Path:
        """
        Execute export and return output path.

        Args:
            job: Job to execute
            photo_paths: Photos to export

        Returns:
            Path to output file
        """
        # Determine output filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        job_id_short = job.job_id[:8]

        # Extract GPS precision from job options (used by all formats)
        gps_precision = job.options.get("gps_precision") if job.options else None

        if job.format == ExportJobFormat.DARWIN_CORE:
            filename = f"mothbox_darwin_core_{timestamp}_{job_id_short}.csv"
            output_path = self._get_output_path(filename)

            # Stream Darwin Core CSV row-by-row to minimize memory usage
            import csv

            from webui.backend.lib.darwin_core_mapping import (
                get_csv_headers,
                is_valid_for_export,
                transform_to_csv_row,
            )

            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(get_csv_headers())

                total = len(photo_paths)
                for idx, photo_path in enumerate(photo_paths):
                    metadata = self._export_service.get_export_metadata(photo_path)
                    if not hasattr(metadata, "to_dict"):
                        continue
                    # Filter invalid (no GPS) for GBIF compliance
                    if not is_valid_for_export(metadata):
                        continue
                    writer.writerow(transform_to_csv_row(metadata, gps_precision=gps_precision))
                    # Update progress every 10 photos or at the end
                    if (idx + 1) % 10 == 0 or idx == total - 1:
                        self._update_progress(job, current=idx + 1)

        elif job.format == ExportJobFormat.INATURALIST:
            filename = f"mothbox_inaturalist_{timestamp}_{job_id_short}.zip"
            output_path = self._get_output_path(filename)

            # Create ZipExportOptions with GPS precision if specified
            from webui.backend.lib.zip_export import ZipExportOptions

            zip_options = ZipExportOptions(gps_precision=gps_precision)

            self._export_service.transform_batch_to_inaturalist_zip(
                photo_paths=photo_paths,
                output_path=output_path,
                options=zip_options,
                progress_callback=self._make_progress_callback(job),
            )

        elif job.format == ExportJobFormat.JSON:
            filename = f"mothbox_export_{timestamp}_{job_id_short}.json"
            output_path = self._get_output_path(filename)

            # Build JSON export by collecting metadata for each photo
            import json

            results = []
            total = len(photo_paths)
            for idx, photo_path in enumerate(photo_paths):
                metadata = self._export_service.get_export_metadata(photo_path)
                if hasattr(metadata, "to_dict"):
                    # ExportMetadata object
                    transformed = self._export_service.transform_to_generic(
                        metadata, flat=False, gps_precision=gps_precision
                    )
                    results.append(transformed)
                # Update progress every 10 photos or at the end
                if (idx + 1) % 10 == 0 or idx == total - 1:
                    self._update_progress(job, current=idx + 1)

            # Write JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "results": results,
                        "total": len(results),
                        "exported_at": timestamp,
                    },
                    f,
                    indent=2,
                    default=str,
                )

        elif job.format == ExportJobFormat.CSV:
            filename = f"mothbox_export_{timestamp}_{job_id_short}.csv"
            output_path = self._get_output_path(filename)

            # Stream generic CSV row-by-row to minimize memory usage
            import csv

            headers = [
                "photo_path",
                "filename",
                "timestamp",
                "latitude",
                "longitude",
                "altitude",
                "gps_accuracy",
                "camera_make",
                "camera_model",
                "exposure_time",
                "iso",
                "focal_length",
                "species",
                "species_common_name",
                "species_confidence",
                "tags",
                "notes",
                "mothbox_id",
                "firmware_version",
                "deployment_name",
                "deployment_location_name",
                "deployment_start_date",
                "deployment_end_date",
                "environmental_conditions",
                "series_type",
                "series_index",
                "series_count",
                "file_size",
                "width",
                "height",
            ]

            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)

                total = len(photo_paths)
                for idx, photo_path in enumerate(photo_paths):
                    metadata = self._export_service.get_export_metadata(photo_path)
                    if not hasattr(metadata, "to_dict"):
                        continue
                    flat_data = self._export_service.transform_to_generic(
                        metadata, flat=True, gps_precision=gps_precision
                    )
                    row = [str(flat_data.get(h, "")) for h in headers]
                    writer.writerow(row)
                    # Update progress every 10 photos or at the end
                    if (idx + 1) % 10 == 0 or idx == total - 1:
                        self._update_progress(job, current=idx + 1)

        else:
            raise ValueError(f"Unsupported export format: {job.format}")

        return output_path

    def _get_output_path(self, filename: str) -> Path:
        """Get output file path (in temp_dir or system temp)."""
        if self._temp_dir:
            return self._temp_dir / filename
        else:
            import tempfile

            return Path(tempfile.gettempdir()) / filename

    # =========================================================================
    # Cleanup
    # =========================================================================

    def _cleanup_expired_jobs(self) -> None:
        """Clean up jobs that have expired based on expires_at."""
        now = time.time()

        # Get all completed/failed/cancelled jobs
        for status in (
            ExportJobStatus.COMPLETED,
            ExportJobStatus.FAILED,
            ExportJobStatus.CANCELLED,
        ):
            jobs = self._db.list_jobs(status=status, limit=1000, offset=0)

            for job in jobs:
                # Use expires_at if set, fall back to created_at + TTL for legacy jobs
                if job.expires_at is not None:
                    if job.expires_at < now:
                        logger.debug(
                            "Cleaning up expired job: id=%s, expired_at=%s",
                            job.job_id,
                            job.expires_at,
                        )
                        self.delete_job(job.job_id)
                else:
                    # Fallback for jobs created before this fix
                    cutoff_time = now - self._job_ttl_seconds
                    if job.created_at < cutoff_time:
                        logger.debug(
                            "Cleaning up expired job (legacy): id=%s, age=%ds",
                            job.job_id,
                            now - job.created_at,
                        )
                        self.delete_job(job.job_id)

    def _cleanup_old_jobs(self) -> None:
        """Enforce max_history limit."""
        # Get all completed jobs
        all_jobs = self._db.list_jobs(limit=100000, offset=0)

        # Filter to finished jobs
        finished_jobs = [
            j
            for j in all_jobs
            if j.status
            in (ExportJobStatus.COMPLETED, ExportJobStatus.FAILED, ExportJobStatus.CANCELLED)
        ]

        # Sort by created_at (oldest first)
        finished_jobs.sort(key=lambda j: j.created_at)

        # Delete oldest jobs if over limit
        if len(finished_jobs) > self._max_history:
            jobs_to_delete = finished_jobs[: len(finished_jobs) - self._max_history]

            for job in jobs_to_delete:
                logger.debug("Cleaning up old job (max_history): id=%s", job.job_id)
                self.delete_job(job.job_id)
