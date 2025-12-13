"""
Unit tests for export job database persistence layer.

Tests cover CRUD operations, queries, thread safety, and edge cases.
"""

import sqlite3
import time
from pathlib import Path
from threading import Thread

import pytest

from webui.backend.lib.export_job_db import ExportJobDB
from webui.backend.lib.export_job_types import (
    ExportJob,
    ExportJobFilter,
    ExportJobFormat,
    ExportJobProgress,
    ExportJobStatus,
)


class TestDatabaseSchemaCreation:
    """Test database schema initialization."""

    def test_create_database_creates_table(self, tmp_path):
        """Test that initializing DB creates export_jobs table."""
        db_path = tmp_path / "test.db"
        db = ExportJobDB(db_path)

        # Verify table exists by querying sqlite_master
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='export_jobs'"
        )
        result = cursor.fetchone()
        conn.close()
        db.close()

        assert result is not None
        assert result[0] == "export_jobs"

    def test_create_database_creates_indexes(self, tmp_path):
        """Test that initializing DB creates required indexes."""
        db_path = tmp_path / "test.db"
        db = ExportJobDB(db_path)

        # Verify indexes exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        db.close()

        assert "idx_jobs_status" in indexes
        assert "idx_jobs_created_at" in indexes

    def test_database_schema_has_all_columns(self, tmp_path):
        """Test that export_jobs table has all required columns."""
        db_path = tmp_path / "test.db"
        db = ExportJobDB(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(export_jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        db.close()

        expected_columns = {
            "job_id",
            "status",
            "format",
            "filter_json",
            "progress_json",
            "created_at",
            "started_at",
            "completed_at",
            "expires_at",
            "output_path",
            "output_size_bytes",
            "photo_count",
            "error_message",
            "errors_json",
            "options_json",
        }
        assert columns == expected_columns

    def test_can_initialize_with_string_path(self, tmp_path):
        """Test that DB can be initialized with string path."""
        db_path = str(tmp_path / "test.db")
        db = ExportJobDB(db_path)
        db.close()
        assert Path(db_path).exists()


class TestCreateJob:
    """Test job creation."""

    def test_create_job_inserts_into_database(self, tmp_path):
        """Test that create_job inserts a new job."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="test-job-1",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)
        retrieved = db.get_job("test-job-1")
        db.close()

        assert retrieved is not None
        assert retrieved.job_id == "test-job-1"
        assert retrieved.status == ExportJobStatus.PENDING
        assert retrieved.format == ExportJobFormat.DARWIN_CORE

    def test_create_job_preserves_all_fields(self, tmp_path):
        """Test that all job fields are persisted correctly."""
        db = ExportJobDB(tmp_path / "test.db")
        now = time.time()
        job = ExportJob(
            job_id="test-job-2",
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(date_start="2024-01-01", date_end="2024-12-31"),
            progress=ExportJobProgress(total=100, current=100, phase="completed"),
            created_at=now,
            started_at=now + 1,
            completed_at=now + 10,
            expires_at=now + 3600,
            output_path="/tmp/export.zip",
            output_size_bytes=1024000,
            photo_count=100,
            error_message=None,
            errors=[],
            options={"compression": "zip"},
        )

        db.create_job(job)
        retrieved = db.get_job("test-job-2")
        db.close()

        assert retrieved is not None
        assert retrieved.job_id == "test-job-2"
        assert retrieved.status == ExportJobStatus.COMPLETED
        assert retrieved.format == ExportJobFormat.JSON
        assert retrieved.filter.date_start == "2024-01-01"
        assert retrieved.filter.date_end == "2024-12-31"
        assert retrieved.progress.total == 100
        assert retrieved.progress.current == 100
        assert retrieved.progress.phase == "completed"
        assert abs(retrieved.created_at - now) < 0.001
        assert abs(retrieved.started_at - (now + 1)) < 0.001
        assert abs(retrieved.completed_at - (now + 10)) < 0.001
        assert abs(retrieved.expires_at - (now + 3600)) < 0.001
        assert retrieved.output_path == "/tmp/export.zip"
        assert retrieved.output_size_bytes == 1024000
        assert retrieved.photo_count == 100
        assert retrieved.error_message is None
        assert retrieved.errors == []
        assert retrieved.options == {"compression": "zip"}

    def test_create_job_with_errors(self, tmp_path):
        """Test that job errors are persisted correctly."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="test-job-3",
            status=ExportJobStatus.FAILED,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
            error_message="Export failed",
            errors=[
                {"photo": "photo1.jpg", "error": "File not found"},
                {"photo": "photo2.jpg", "error": "Corrupt EXIF"},
            ],
        )

        db.create_job(job)
        retrieved = db.get_job("test-job-3")
        db.close()

        assert retrieved is not None
        assert retrieved.error_message == "Export failed"
        assert len(retrieved.errors) == 2
        assert retrieved.errors[0]["photo"] == "photo1.jpg"
        assert retrieved.errors[1]["error"] == "Corrupt EXIF"

    def test_create_duplicate_job_raises_error(self, tmp_path):
        """Test that creating a duplicate job_id raises an error."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="duplicate-job",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)

        # Attempt to create duplicate should raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            db.create_job(job)

        db.close()


class TestGetJob:
    """Test job retrieval."""

    def test_get_job_returns_existing_job(self, tmp_path):
        """Test that get_job retrieves an existing job."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="get-test-1",
            status=ExportJobStatus.RUNNING,
            format=ExportJobFormat.CSV,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)
        retrieved = db.get_job("get-test-1")
        db.close()

        assert retrieved is not None
        assert retrieved.job_id == "get-test-1"
        assert retrieved.status == ExportJobStatus.RUNNING

    def test_get_job_returns_none_for_nonexistent(self, tmp_path):
        """Test that get_job returns None for non-existent job."""
        db = ExportJobDB(tmp_path / "test.db")
        retrieved = db.get_job("nonexistent-job")
        db.close()

        assert retrieved is None

    def test_get_job_from_empty_database(self, tmp_path):
        """Test that get_job works on empty database."""
        db = ExportJobDB(tmp_path / "test.db")
        retrieved = db.get_job("any-job")
        db.close()

        assert retrieved is None


class TestUpdateJob:
    """Test job updates."""

    def test_update_job_modifies_existing_job(self, tmp_path):
        """Test that update_job modifies an existing job."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="update-test-1",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)

        # Update job status
        job.status = ExportJobStatus.RUNNING
        job.started_at = time.time()
        result = db.update_job(job)

        retrieved = db.get_job("update-test-1")
        db.close()

        assert result is True
        assert retrieved is not None
        assert retrieved.status == ExportJobStatus.RUNNING
        assert retrieved.started_at is not None

    def test_update_job_updates_progress(self, tmp_path):
        """Test that update_job persists progress changes."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="update-test-2",
            status=ExportJobStatus.RUNNING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(total=100, current=0),
            created_at=time.time(),
        )

        db.create_job(job)

        # Update progress
        job.progress.current = 50
        job.progress.phase = "exporting"
        db.update_job(job)

        retrieved = db.get_job("update-test-2")
        db.close()

        assert retrieved is not None
        assert retrieved.progress.current == 50
        assert retrieved.progress.phase == "exporting"

    def test_update_job_returns_false_for_nonexistent(self, tmp_path):
        """Test that update_job returns False for non-existent job."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="nonexistent",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        result = db.update_job(job)
        db.close()

        assert result is False

    def test_update_job_can_set_nullable_fields(self, tmp_path):
        """Test that update_job can set nullable fields to None."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="update-test-3",
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
            output_path="/tmp/export.zip",
            error_message="Some error",
        )

        db.create_job(job)

        # Clear nullable fields
        job.output_path = None
        job.error_message = None
        db.update_job(job)

        retrieved = db.get_job("update-test-3")
        db.close()

        assert retrieved is not None
        assert retrieved.output_path is None
        assert retrieved.error_message is None


class TestDeleteJob:
    """Test job deletion."""

    def test_delete_job_removes_job(self, tmp_path):
        """Test that delete_job removes a job."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="delete-test-1",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)
        result = db.delete_job("delete-test-1")
        retrieved = db.get_job("delete-test-1")
        db.close()

        assert result is True
        assert retrieved is None

    def test_delete_job_returns_false_for_nonexistent(self, tmp_path):
        """Test that delete_job returns False for non-existent job."""
        db = ExportJobDB(tmp_path / "test.db")
        result = db.delete_job("nonexistent")
        db.close()

        assert result is False


class TestListJobs:
    """Test job listing with pagination and filtering."""

    def test_list_jobs_returns_all_jobs(self, tmp_path):
        """Test that list_jobs returns all jobs by default."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create multiple jobs
        for i in range(5):
            job = ExportJob(
                job_id=f"list-test-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)  # Small delay to ensure different timestamps

        jobs = db.list_jobs()
        db.close()

        assert len(jobs) == 5

    def test_list_jobs_respects_limit(self, tmp_path):
        """Test that list_jobs respects limit parameter."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(10):
            job = ExportJob(
                job_id=f"list-limit-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        jobs = db.list_jobs(limit=5)
        db.close()

        assert len(jobs) == 5

    def test_list_jobs_respects_offset(self, tmp_path):
        """Test that list_jobs respects offset parameter."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(10):
            job = ExportJob(
                job_id=f"list-offset-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        jobs = db.list_jobs(limit=5, offset=5)
        db.close()

        assert len(jobs) == 5
        # Should get the older jobs (lower created_at)
        assert all("list-offset-" in job.job_id for job in jobs)

    def test_list_jobs_filters_by_status(self, tmp_path):
        """Test that list_jobs filters by status."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create jobs with different statuses
        statuses = [
            ExportJobStatus.PENDING,
            ExportJobStatus.RUNNING,
            ExportJobStatus.COMPLETED,
            ExportJobStatus.FAILED,
        ]
        for i, status in enumerate(statuses * 2):  # 8 jobs total
            job = ExportJob(
                job_id=f"status-filter-{i}",
                status=status,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        pending_jobs = db.list_jobs(status=ExportJobStatus.PENDING)
        running_jobs = db.list_jobs(status=ExportJobStatus.RUNNING)
        db.close()

        assert len(pending_jobs) == 2
        assert all(job.status == ExportJobStatus.PENDING for job in pending_jobs)
        assert len(running_jobs) == 2
        assert all(job.status == ExportJobStatus.RUNNING for job in running_jobs)

    def test_list_jobs_orders_by_created_at_desc(self, tmp_path):
        """Test that list_jobs orders by created_at descending by default."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create jobs with different timestamps
        for i in range(5):
            job = ExportJob(
                job_id=f"order-test-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        jobs = db.list_jobs()
        db.close()

        # Should be ordered newest first
        for i in range(len(jobs) - 1):
            assert jobs[i].created_at >= jobs[i + 1].created_at

    def test_list_jobs_can_order_ascending(self, tmp_path):
        """Test that list_jobs can order ascending."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(5):
            job = ExportJob(
                job_id=f"order-asc-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        jobs = db.list_jobs(order_desc=False)
        db.close()

        # Should be ordered oldest first
        for i in range(len(jobs) - 1):
            assert jobs[i].created_at <= jobs[i + 1].created_at

    def test_list_jobs_empty_database(self, tmp_path):
        """Test that list_jobs returns empty list for empty database."""
        db = ExportJobDB(tmp_path / "test.db")
        jobs = db.list_jobs()
        db.close()

        assert jobs == []


class TestCountJobs:
    """Test job counting."""

    def test_count_jobs_returns_total(self, tmp_path):
        """Test that count_jobs returns total job count."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(10):
            job = ExportJob(
                job_id=f"count-test-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        count = db.count_jobs()
        db.close()

        assert count == 10

    def test_count_jobs_filters_by_status(self, tmp_path):
        """Test that count_jobs filters by status."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create 3 pending, 2 running
        for i in range(3):
            job = ExportJob(
                job_id=f"count-pending-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        for i in range(2):
            job = ExportJob(
                job_id=f"count-running-{i}",
                status=ExportJobStatus.RUNNING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        pending_count = db.count_jobs(status=ExportJobStatus.PENDING)
        running_count = db.count_jobs(status=ExportJobStatus.RUNNING)
        total_count = db.count_jobs()
        db.close()

        assert pending_count == 3
        assert running_count == 2
        assert total_count == 5

    def test_count_jobs_empty_database(self, tmp_path):
        """Test that count_jobs returns 0 for empty database."""
        db = ExportJobDB(tmp_path / "test.db")
        count = db.count_jobs()
        db.close()

        assert count == 0


class TestCountJobsByStatus:
    """Test count_jobs_by_status aggregate query."""

    def test_count_jobs_by_status_empty_database(self, tmp_path):
        """Test that count_jobs_by_status returns zeros for empty database."""
        db = ExportJobDB(tmp_path / "test.db")
        counts = db.count_jobs_by_status()
        db.close()

        assert counts['total'] == 0
        assert counts['pending'] == 0
        assert counts['running'] == 0
        assert counts['completed'] == 0
        assert counts['failed'] == 0
        assert counts['cancelled'] == 0
        assert counts['expired'] == 0

    def test_count_jobs_by_status_with_multiple_statuses(self, tmp_path):
        """Test counting jobs with various statuses."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create jobs with different statuses
        test_cases = [
            (ExportJobStatus.PENDING, 3),
            (ExportJobStatus.RUNNING, 1),
            (ExportJobStatus.COMPLETED, 4),
            (ExportJobStatus.FAILED, 2),
            (ExportJobStatus.CANCELLED, 1),
        ]

        job_counter = 0
        for status, count in test_cases:
            for _ in range(count):
                job = ExportJob(
                    job_id=f"count-by-status-{job_counter}",
                    status=status,
                    format=ExportJobFormat.DARWIN_CORE,
                    filter=ExportJobFilter(),
                    progress=ExportJobProgress(),
                    created_at=time.time(),
                )
                db.create_job(job)
                job_counter += 1

        counts = db.count_jobs_by_status()
        db.close()

        assert counts['total'] == 11
        assert counts['pending'] == 3
        assert counts['running'] == 1
        assert counts['completed'] == 4
        assert counts['failed'] == 2
        assert counts['cancelled'] == 1
        assert counts['expired'] == 0

    def test_count_jobs_by_status_single_status(self, tmp_path):
        """Test counting when all jobs have the same status."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(5):
            job = ExportJob(
                job_id=f"single-status-{i}",
                status=ExportJobStatus.COMPLETED,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        counts = db.count_jobs_by_status()
        db.close()

        assert counts['total'] == 5
        assert counts['completed'] == 5
        assert counts['pending'] == 0
        assert counts['running'] == 0


class TestGetPendingJobs:
    """Test getting pending jobs."""

    def test_get_pending_jobs_returns_only_pending(self, tmp_path):
        """Test that get_pending_jobs returns only PENDING jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create jobs with different statuses
        statuses = [
            ExportJobStatus.PENDING,
            ExportJobStatus.RUNNING,
            ExportJobStatus.PENDING,
            ExportJobStatus.COMPLETED,
            ExportJobStatus.PENDING,
        ]
        for i, status in enumerate(statuses):
            job = ExportJob(
                job_id=f"pending-test-{i}",
                status=status,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        pending_jobs = db.get_pending_jobs()
        db.close()

        assert len(pending_jobs) == 3
        assert all(job.status == ExportJobStatus.PENDING for job in pending_jobs)

    def test_get_pending_jobs_ordered_by_created_at(self, tmp_path):
        """Test that get_pending_jobs is ordered by creation time."""
        db = ExportJobDB(tmp_path / "test.db")

        for i in range(5):
            job = ExportJob(
                job_id=f"pending-order-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time() + i,
            )
            db.create_job(job)
            time.sleep(0.001)

        pending_jobs = db.get_pending_jobs()
        db.close()

        # Should be ordered oldest first (ascending)
        for i in range(len(pending_jobs) - 1):
            assert pending_jobs[i].created_at <= pending_jobs[i + 1].created_at

    def test_get_pending_jobs_empty_result(self, tmp_path):
        """Test that get_pending_jobs returns empty list when no pending jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create only completed jobs
        for i in range(3):
            job = ExportJob(
                job_id=f"completed-{i}",
                status=ExportJobStatus.COMPLETED,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        pending_jobs = db.get_pending_jobs()
        db.close()

        assert pending_jobs == []


class TestGetRunningJobs:
    """Test getting running jobs."""

    def test_get_running_jobs_returns_only_running(self, tmp_path):
        """Test that get_running_jobs returns only RUNNING jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create jobs with different statuses
        statuses = [
            ExportJobStatus.RUNNING,
            ExportJobStatus.PENDING,
            ExportJobStatus.RUNNING,
            ExportJobStatus.COMPLETED,
            ExportJobStatus.RUNNING,
        ]
        for i, status in enumerate(statuses):
            job = ExportJob(
                job_id=f"running-test-{i}",
                status=status,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        running_jobs = db.get_running_jobs()
        db.close()

        assert len(running_jobs) == 3
        assert all(job.status == ExportJobStatus.RUNNING for job in running_jobs)

    def test_get_running_jobs_empty_result(self, tmp_path):
        """Test that get_running_jobs returns empty list when no running jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create only pending jobs
        for i in range(3):
            job = ExportJob(
                job_id=f"pending-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        running_jobs = db.get_running_jobs()
        db.close()

        assert running_jobs == []


class TestCleanupExpiredJobs:
    """Test expired job cleanup."""

    def test_cleanup_expired_jobs_deletes_expired(self, tmp_path):
        """Test that cleanup_expired_jobs deletes expired jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        now = time.time()
        # Create expired job
        expired_job = ExportJob(
            job_id="expired-1",
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=now - 7200,
            expires_at=now - 3600,  # Expired 1 hour ago
        )
        db.create_job(expired_job)

        deleted_count = db.cleanup_expired_jobs()
        retrieved = db.get_job("expired-1")
        db.close()

        assert deleted_count == 1
        assert retrieved is None

    def test_cleanup_expired_jobs_keeps_valid(self, tmp_path):
        """Test that cleanup_expired_jobs keeps non-expired jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        now = time.time()
        # Create non-expired job
        valid_job = ExportJob(
            job_id="valid-1",
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=now,
            expires_at=now + 3600,  # Expires in 1 hour
        )
        db.create_job(valid_job)

        deleted_count = db.cleanup_expired_jobs()
        retrieved = db.get_job("valid-1")
        db.close()

        assert deleted_count == 0
        assert retrieved is not None

    def test_cleanup_expired_jobs_keeps_jobs_without_expiry(self, tmp_path):
        """Test that cleanup_expired_jobs keeps jobs without expires_at."""
        db = ExportJobDB(tmp_path / "test.db")

        job = ExportJob(
            job_id="no-expiry",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
            expires_at=None,
        )
        db.create_job(job)

        deleted_count = db.cleanup_expired_jobs()
        retrieved = db.get_job("no-expiry")
        db.close()

        assert deleted_count == 0
        assert retrieved is not None

    def test_cleanup_expired_jobs_deletes_multiple(self, tmp_path):
        """Test that cleanup_expired_jobs deletes multiple expired jobs."""
        db = ExportJobDB(tmp_path / "test.db")

        now = time.time()
        for i in range(5):
            job = ExportJob(
                job_id=f"expired-{i}",
                status=ExportJobStatus.COMPLETED,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=now - 7200,
                expires_at=now - 1,  # All expired
            )
            db.create_job(job)

        deleted_count = db.cleanup_expired_jobs()
        db.close()

        assert deleted_count == 5

    def test_cleanup_expired_jobs_returns_zero_for_empty_db(self, tmp_path):
        """Test that cleanup_expired_jobs returns 0 for empty database."""
        db = ExportJobDB(tmp_path / "test.db")
        deleted_count = db.cleanup_expired_jobs()
        db.close()

        assert deleted_count == 0


class TestThreadSafety:
    """Test thread safety of database operations."""

    def test_concurrent_create_operations(self, tmp_path):
        """Test that concurrent create operations are safe."""
        db = ExportJobDB(tmp_path / "test.db")

        def create_jobs(thread_id, count):
            for i in range(count):
                job = ExportJob(
                    job_id=f"thread-{thread_id}-job-{i}",
                    status=ExportJobStatus.PENDING,
                    format=ExportJobFormat.DARWIN_CORE,
                    filter=ExportJobFilter(),
                    progress=ExportJobProgress(),
                    created_at=time.time(),
                )
                db.create_job(job)

        threads = [Thread(target=create_jobs, args=(i, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_count = db.count_jobs()
        db.close()

        assert total_count == 50  # 5 threads * 10 jobs each

    def test_concurrent_read_write_operations(self, tmp_path):
        """Test that concurrent read/write operations don't corrupt data."""
        db = ExportJobDB(tmp_path / "test.db")

        # Create initial jobs
        for i in range(10):
            job = ExportJob(
                job_id=f"concurrent-{i}",
                status=ExportJobStatus.PENDING,
                format=ExportJobFormat.DARWIN_CORE,
                filter=ExportJobFilter(),
                progress=ExportJobProgress(),
                created_at=time.time(),
            )
            db.create_job(job)

        def update_jobs():
            for i in range(10):
                job = db.get_job(f"concurrent-{i}")
                if job:
                    job.status = ExportJobStatus.RUNNING
                    db.update_job(job)

        def read_jobs():
            for _ in range(20):
                db.list_jobs()
                time.sleep(0.001)

        threads = [
            Thread(target=update_jobs),
            Thread(target=read_jobs),
            Thread(target=read_jobs),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        db.close()
        # If we get here without errors, thread safety is working


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_job_with_empty_filter(self, tmp_path):
        """Test job with empty filter."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="empty-filter",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),  # All fields None
            progress=ExportJobProgress(),
            created_at=time.time(),
        )

        db.create_job(job)
        retrieved = db.get_job("empty-filter")
        db.close()

        assert retrieved is not None
        assert retrieved.filter.date_start is None
        assert retrieved.filter.date_end is None

    def test_job_with_large_errors_list(self, tmp_path):
        """Test job with large errors list."""
        db = ExportJobDB(tmp_path / "test.db")
        errors = [{"photo": f"photo{i}.jpg", "error": "Error"} for i in range(1000)]
        job = ExportJob(
            job_id="large-errors",
            status=ExportJobStatus.FAILED,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
            errors=errors,
        )

        db.create_job(job)
        retrieved = db.get_job("large-errors")
        db.close()

        assert retrieved is not None
        assert len(retrieved.errors) == 1000

    def test_job_with_unicode_in_fields(self, tmp_path):
        """Test job with unicode characters."""
        db = ExportJobDB(tmp_path / "test.db")
        job = ExportJob(
            job_id="unicode-test",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
            error_message="Error: 日本語 中文 العربية",
        )

        db.create_job(job)
        retrieved = db.get_job("unicode-test")
        db.close()

        assert retrieved is not None
        assert retrieved.error_message == "Error: 日本語 中文 العربية"

    def test_database_path_creation(self, tmp_path):
        """Test that database parent directory is created if needed."""
        nested_path = tmp_path / "nested" / "path" / "test.db"
        db = ExportJobDB(nested_path)
        db.close()

        assert nested_path.exists()

    def test_close_can_be_called_multiple_times(self, tmp_path):
        """Test that close() can be called multiple times safely."""
        db = ExportJobDB(tmp_path / "test.db")
        db.close()
        db.close()  # Should not raise error
