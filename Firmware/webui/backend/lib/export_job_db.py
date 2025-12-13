"""
SQLite persistence layer for export job system.

This module provides a thread-safe database interface for storing and
querying export jobs. Uses SQLite with JSON serialization for complex
data types.

Thread Safety:
    Uses a new connection per operation for simplicity and safety.
    SQLite handles concurrent reads/writes with file locking.

Example:
    >>> db = ExportJobDB("/var/lib/mothbox/export_jobs.db")
    >>> job = ExportJob(job_id="job-1", ...)
    >>> db.create_job(job)
    >>> retrieved = db.get_job("job-1")
    >>> db.close()
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from webui.backend.lib.export_job_types import (
    ExportError,
    ExportJob,
    ExportJobFilter,
    ExportJobFormat,
    ExportJobProgress,
    ExportJobStatus,
)


class ExportJobDB:
    """
    SQLite persistence layer for export jobs.

    Provides CRUD operations and queries for export jobs with
    thread-safe SQLite access.

    Attributes:
        db_path: Path to SQLite database file.
    """

    def __init__(self, db_path: Path | str):
        """
        Initialize database connection and create schema.

        Args:
            db_path: Path to SQLite database file. Parent directory
                will be created if it doesn't exist.
        """
        self.db_path = Path(db_path)

        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create schema
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection.

        Returns:
            New SQLite connection with row factory enabled.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _create_schema(self) -> None:
        """Create database tables and indexes if they don't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create export_jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS export_jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    format TEXT NOT NULL,
                    filter_json TEXT NOT NULL,
                    progress_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    expires_at REAL,
                    output_path TEXT,
                    output_size_bytes INTEGER DEFAULT 0,
                    photo_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    errors_json TEXT,
                    options_json TEXT
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON export_jobs(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at
                ON export_jobs(created_at)
            """)

            conn.commit()
        finally:
            conn.close()

    def _serialize_job(self, job: ExportJob) -> dict[str, Any]:
        """
        Serialize ExportJob to database row format.

        Args:
            job: Job to serialize.

        Returns:
            Dictionary with database column names and values.
        """
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "format": job.format.value,
            "filter_json": json.dumps(job.filter.to_dict()),
            "progress_json": json.dumps(job.progress.to_dict()),
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "expires_at": job.expires_at,
            "output_path": job.output_path,
            "output_size_bytes": job.output_size_bytes,
            "photo_count": job.photo_count,
            "error_message": job.error_message,
            "errors_json": json.dumps([e.to_dict() for e in job.errors]) if job.errors else None,
            "options_json": json.dumps(job.options) if job.options else None,
        }

    def _deserialize_job(self, row: sqlite3.Row) -> ExportJob:
        """
        Deserialize database row to ExportJob.

        Args:
            row: Database row from sqlite3.

        Returns:
            Deserialized ExportJob instance.
        """
        return ExportJob(
            job_id=row["job_id"],
            status=ExportJobStatus(row["status"]),
            format=ExportJobFormat(row["format"]),
            filter=ExportJobFilter.from_dict(json.loads(row["filter_json"])),
            progress=ExportJobProgress.from_dict(json.loads(row["progress_json"])),
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"],
            output_path=row["output_path"],
            output_size_bytes=row["output_size_bytes"] or 0,
            photo_count=row["photo_count"] or 0,
            error_message=row["error_message"],
            errors=[ExportError.from_dict(e) for e in json.loads(row["errors_json"])] if row["errors_json"] else [],
            options=json.loads(row["options_json"]) if row["options_json"] else {},
        )

    def create_job(self, job: ExportJob) -> None:
        """
        Insert a new job into the database.

        Args:
            job: Job to create.

        Raises:
            sqlite3.IntegrityError: If job_id already exists.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            row = self._serialize_job(job)

            cursor.execute(
                """
                INSERT INTO export_jobs (
                    job_id, status, format, filter_json, progress_json,
                    created_at, started_at, completed_at, expires_at,
                    output_path, output_size_bytes, photo_count,
                    error_message, errors_json, options_json
                ) VALUES (
                    :job_id, :status, :format, :filter_json, :progress_json,
                    :created_at, :started_at, :completed_at, :expires_at,
                    :output_path, :output_size_bytes, :photo_count,
                    :error_message, :errors_json, :options_json
                )
                """,
                row,
            )

            conn.commit()
        finally:
            conn.close()

    def get_job(self, job_id: str) -> ExportJob | None:
        """
        Retrieve a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            ExportJob if found, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM export_jobs WHERE job_id = ?",
                (job_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._deserialize_job(row)
        finally:
            conn.close()

    def update_job(self, job: ExportJob) -> bool:
        """
        Update an existing job.

        Args:
            job: Job with updated fields.

        Returns:
            True if job existed and was updated, False otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            row = self._serialize_job(job)

            cursor.execute(
                """
                UPDATE export_jobs SET
                    status = :status,
                    format = :format,
                    filter_json = :filter_json,
                    progress_json = :progress_json,
                    created_at = :created_at,
                    started_at = :started_at,
                    completed_at = :completed_at,
                    expires_at = :expires_at,
                    output_path = :output_path,
                    output_size_bytes = :output_size_bytes,
                    photo_count = :photo_count,
                    error_message = :error_message,
                    errors_json = :errors_json,
                    options_json = :options_json
                WHERE job_id = :job_id
                """,
                row,
            )

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            True if job existed and was deleted, False otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM export_jobs WHERE job_id = ?",
                (job_id,),
            )

            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_jobs(
        self,
        status: ExportJobStatus | None = None,
        limit: int | None = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[ExportJob]:
        """
        List jobs with optional filtering and pagination.

        Args:
            status: Filter by job status (None = all statuses).
            limit: Maximum number of jobs to return (None = no limit).
            offset: Number of jobs to skip.
            order_by: Column to order by (default: created_at).
            order_desc: If True, order descending (newest first).

        Returns:
            List of ExportJob instances.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Build query
            query = "SELECT * FROM export_jobs"
            params: list = []

            if status is not None:
                query += " WHERE status = ?"
                params.append(status.value)

            # Add ordering (validate column to prevent SQL injection)
            allowed_order_columns = {'created_at', 'started_at', 'completed_at', 'job_id'}
            if order_by not in allowed_order_columns:
                raise ValueError(f"Invalid order_by column: {order_by}")
            order_direction = "DESC" if order_desc else "ASC"
            query += f" ORDER BY {order_by} {order_direction}"

            # Add pagination (only if limit specified)
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            elif offset > 0:
                # SQLite requires LIMIT with OFFSET, use -1 for unlimited
                query += " LIMIT -1 OFFSET ?"
                params.append(offset)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._deserialize_job(row) for row in rows]
        finally:
            conn.close()

    def count_jobs(self, status: ExportJobStatus | None = None) -> int:
        """
        Count jobs with optional status filter.

        Args:
            status: Filter by job status (None = all statuses).

        Returns:
            Number of jobs matching criteria.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if status is not None:
                cursor.execute(
                    "SELECT COUNT(*) FROM export_jobs WHERE status = ?",
                    (status.value,),
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM export_jobs")

            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()

    def count_jobs_by_status(self) -> dict[str, int]:
        """
        Get job counts for all statuses in a single query.

        More efficient than multiple count_jobs() calls since it uses a single
        SQL query with GROUP BY rather than N+1 queries.

        Returns:
            Dict with 'total' and counts for each status (pending, running,
            completed, failed, cancelled, expired).
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Single query with GROUP BY - uses idx_jobs_status index
            cursor.execute(
                "SELECT status, COUNT(*) FROM export_jobs GROUP BY status"
            )
            rows = cursor.fetchall()

            # Initialize with zeros for all statuses
            counts: dict[str, int] = {
                'total': 0,
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
                'expired': 0,
            }

            for row in rows:
                status_value = row[0]
                count = row[1]
                counts['total'] += count
                counts[status_value] = count

            return counts
        finally:
            conn.close()

    def get_pending_jobs(self) -> list[ExportJob]:
        """
        Get all pending jobs ordered by creation time.

        Returns:
            List of pending jobs, oldest first.
        """
        return self.list_jobs(
            status=ExportJobStatus.PENDING,
            limit=None,  # No limit - get all pending
            offset=0,
            order_by="created_at",
            order_desc=False,  # Oldest first
        )

    def get_running_jobs(self) -> list[ExportJob]:
        """
        Get all currently running jobs.

        Returns:
            List of running jobs.
        """
        return self.list_jobs(
            status=ExportJobStatus.RUNNING,
            limit=None,  # No limit - get all running
            offset=0,
        )

    def cleanup_expired_jobs(self) -> int:
        """
        Delete expired jobs.

        Jobs are considered expired if expires_at is not NULL
        and is less than the current time.

        Returns:
            Number of jobs deleted.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = time.time()

            cursor.execute(
                """
                DELETE FROM export_jobs
                WHERE expires_at IS NOT NULL AND expires_at < ?
                """,
                (now,),
            )

            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def close(self) -> None:
        """
        Close the database connection.

        Note: Since we create a new connection per operation,
        this method is primarily for API compatibility and future use.
        """
        # Nothing to close since we use per-operation connections
