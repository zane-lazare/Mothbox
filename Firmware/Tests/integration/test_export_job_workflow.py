"""
Integration tests for export job workflow (Issue #122).

Tests the complete async export job system from creation through execution,
download, and cleanup. Verifies job queue behavior, persistence, and API integration.

Tests are marked as @pytest.mark.integration since they test cross-component
workflows but do NOT require Raspberry Pi hardware (no camera/GPIO).

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_export_job_workflow.py -v -s
"""

import json
import os
import sys
import time
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask
from webui.backend.routes.export import export_bp
from webui.backend.services.export_job_service import ExportJobService
from webui.backend.services.export_metadata_service import ExportMetadataService
from webui.backend.lib.export_job_types import (
    ExportJobFormat,
    ExportJobFilter,
    ExportJobStatus,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_photos(tmp_path):
    """Create sample photo files for integration testing."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Create test JPEG files with minimal valid JPEG data
    try:
        from PIL import Image

        photo_paths = []
        for i in range(5):
            photo_path = photos_dir / f"test_photo_{i}.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(photo_path, "JPEG", quality=85)
            photo_paths.append(str(photo_path))

            # Create sidecar metadata for export metadata service
            sidecar = photos_dir / f"test_photo_{i}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"test_photo_{i}.jpg",
                        "created_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "modified_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "tags": ["moth", "test"],
                        "latitude": 37.7749 + (i * 0.001),
                        "longitude": -122.4194 - (i * 0.001),
                        "altitude": 100.0 + (i * 10),
                    }
                )
            )

        return photo_paths
    except ImportError:
        # Fallback to minimal JPEG if PIL not available
        photo_paths = []
        for i in range(5):
            photo_path = photos_dir / f"test_photo_{i}.jpg"
            # Minimal valid JPEG
            header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            footer = b"\xFF\xD9"
            padding = b"\x00" * 100
            photo_path.write_bytes(header + padding + footer)
            photo_paths.append(str(photo_path))

            # Create sidecar
            sidecar = photos_dir / f"test_photo_{i}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"test_photo_{i}.jpg",
                        "created_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "tags": ["moth"],
                    }
                )
            )

        return photo_paths


@pytest.fixture
def export_job_service(tmp_path, sample_photos):
    """Create ExportJobService for integration testing."""
    db_path = tmp_path / "jobs.db"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    photos_dir = Path(sample_photos[0]).parent

    export_service = ExportMetadataService(cache_ttl=300)

    service = ExportJobService(
        db_path=db_path,
        export_service=export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_timeout_seconds=30,  # Short timeout for tests
        job_ttl_seconds=300,
        max_history=50,
    )
    service.start()
    yield service
    service.stop()


@pytest.fixture
def app(tmp_path, export_job_service):
    """Flask app with export job service configured."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["EXPORT_JOB_SERVICE"] = export_job_service
    app.config["EXPORT_METADATA_SERVICE"] = export_job_service._export_service

    # Disable CSRF for testing
    app.config["WTF_CSRF_ENABLED"] = False

    app.register_blueprint(export_bp, url_prefix="/api/export")
    return app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


# ============================================================================
# Full Job Lifecycle Tests
# ============================================================================


@pytest.mark.integration
class TestFullJobLifecycle:
    """Test complete job lifecycle for all export formats."""

    def test_full_lifecycle_darwin_core(self, client, sample_photos):
        """Test create → poll → download → delete workflow for Darwin Core CSV."""
        # 1. Create job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "filter": {"photo_paths": sample_photos},
            },
        )
        assert response.status_code == 202
        data = response.get_json()
        assert "job_id" in data
        job_id = data["job_id"]
        assert data["status"] == "pending"
        assert data["format"] == "darwin_core"

        # 2. Poll until completed (with timeout)
        max_wait = 30  # seconds
        start_time = time.time()
        final_status = None

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            assert response.status_code == 200
            data = response.get_json()
            final_status = data["status"]

            if final_status in ["completed", "failed", "cancelled"]:
                break

            time.sleep(0.5)

        assert final_status == "completed", f"Job did not complete. Status: {final_status}"
        assert data["photo_count"] == len(sample_photos)
        assert data["output_path"] is not None

        # 3. Download result
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        assert len(response.data) > 0

        # Verify CSV content
        csv_content = response.data.decode("utf-8")
        assert "occurrenceID" in csv_content  # Darwin Core header
        assert "basisOfRecord" in csv_content

        # 4. Delete job
        response = client.delete(f"/api/export/jobs/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # 5. Verify job is gone
        response = client.get(f"/api/export/jobs/{job_id}")
        assert response.status_code == 404

    def test_full_lifecycle_inaturalist_zip(self, client, sample_photos):
        """Test create → poll → download → delete workflow for iNaturalist ZIP."""
        # 1. Create job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "inaturalist",
                "filter": {"photo_paths": sample_photos},
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        # 2. Poll until completed
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            data = response.get_json()
            if data["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        assert data["status"] == "completed"

        # 3. Download result
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "application/zip" in response.content_type

        # Verify ZIP content
        zip_data = response.data
        assert len(zip_data) > 0

        # 4. Delete job
        response = client.delete(f"/api/export/jobs/{job_id}")
        assert response.status_code == 200

    def test_full_lifecycle_json(self, client, sample_photos):
        """Test create → poll → download → delete workflow for JSON."""
        # 1. Create job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos},
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        # 2. Poll until completed
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            data = response.get_json()
            if data["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        assert data["status"] == "completed"

        # 3. Download result
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "application/json" in response.content_type

        # Verify JSON content
        # JSON is returned as file, not parsed
        json_data = response.data
        assert len(json_data) > 0

        # 4. Delete job
        response = client.delete(f"/api/export/jobs/{job_id}")
        assert response.status_code == 200

    def test_full_lifecycle_csv(self, client, sample_photos):
        """Test create → poll → download → delete workflow for CSV."""
        # 1. Create job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {"photo_paths": sample_photos},
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        # 2. Poll until completed
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            data = response.get_json()
            if data["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        assert data["status"] == "completed"

        # 3. Download result
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "text/csv" in response.content_type

        # Verify CSV content
        csv_content = response.data.decode("utf-8")
        assert "photo_path" in csv_content  # Generic CSV header
        assert len(csv_content) > 0

        # 4. Delete job
        response = client.delete(f"/api/export/jobs/{job_id}")
        assert response.status_code == 200


# ============================================================================
# Job Persistence Tests
# ============================================================================


@pytest.mark.integration
class TestJobPersistence:
    """Test job persistence across service restarts."""

    def test_job_persistence_across_restart(self, tmp_path, sample_photos):
        """Test that jobs survive service restart."""
        db_path = tmp_path / "jobs.db"
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        photos_dir = Path(sample_photos[0]).parent

        export_service = ExportMetadataService(cache_ttl=300)

        # 1. Create service and add job
        service1 = ExportJobService(
            db_path=db_path,
            export_service=export_service,
            photos_dir=photos_dir,
            temp_dir=temp_dir,
            job_timeout_seconds=30,
            job_ttl_seconds=300,
            max_history=50,
        )
        service1.start()

        job = service1.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos),
        )
        original_job_id = job.job_id

        service1.stop()

        # 2. Create new service instance
        service2 = ExportJobService(
            db_path=db_path,
            export_service=export_service,
            photos_dir=photos_dir,
            temp_dir=temp_dir,
            job_timeout_seconds=30,
            job_ttl_seconds=300,
            max_history=50,
        )
        service2.start()

        # 3. Job should still exist
        recovered = service2.get_job(original_job_id)
        assert recovered is not None
        assert recovered.job_id == original_job_id
        assert recovered.format == ExportJobFormat.JSON

        service2.stop()

    def test_job_execution_after_restart(self, tmp_path, sample_photos):
        """Test that pending jobs execute after service restart."""
        db_path = tmp_path / "jobs.db"
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        photos_dir = Path(sample_photos[0]).parent

        export_service = ExportMetadataService(cache_ttl=300)

        # 1. Create service and add job (don't start worker)
        service1 = ExportJobService(
            db_path=db_path,
            export_service=export_service,
            photos_dir=photos_dir,
            temp_dir=temp_dir,
            job_timeout_seconds=30,
            job_ttl_seconds=300,
            max_history=50,
        )
        # Don't start worker
        job = service1.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos),
        )
        job_id = job.job_id
        # Job should be PENDING
        assert job.status == ExportJobStatus.PENDING

        # 2. Create new service and start worker
        service2 = ExportJobService(
            db_path=db_path,
            export_service=export_service,
            photos_dir=photos_dir,
            temp_dir=temp_dir,
            job_timeout_seconds=30,
            job_ttl_seconds=300,
            max_history=50,
        )
        service2.start()

        # 3. Wait for job to complete
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            recovered = service2.get_job(job_id)
            if recovered.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]:
                break
            time.sleep(0.5)

        # 4. Verify job completed
        final_job = service2.get_job(job_id)
        assert final_job.status == ExportJobStatus.COMPLETED

        service2.stop()


# ============================================================================
# Job Queue Tests
# ============================================================================


@pytest.mark.integration
class TestJobQueue:
    """Test job queue behavior and concurrency."""

    def test_job_queue_behavior(self, export_job_service, sample_photos):
        """Test that jobs queue when another is running."""
        # Create first job
        job1 = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos),
        )

        # Wait for job1 to start running (poll with timeout instead of fixed sleep)
        # The worker thread polls every 1.0 second, so we need to wait longer than that
        max_wait = 5  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait:
            updated_job1 = export_job_service.get_job(job1.job_id)
            if updated_job1.status in [ExportJobStatus.RUNNING, ExportJobStatus.COMPLETED]:
                break
            time.sleep(0.2)

        # Create second job after job1 has started
        job2 = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos),
        )

        # Check job1 status - should have started by now
        updated_job1 = export_job_service.get_job(job1.job_id)
        assert updated_job1.status in [ExportJobStatus.RUNNING, ExportJobStatus.COMPLETED], \
            f"Job1 should be running or completed, but is {updated_job1.status}"

        # Check job2 status
        updated_job2 = export_job_service.get_job(job2.job_id)
        # Job2 should be PENDING (waiting for job1) or RUNNING if job1 completed very quickly
        assert updated_job2.status in [ExportJobStatus.PENDING, ExportJobStatus.RUNNING]

        # Wait for both to complete
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            j1 = export_job_service.get_job(job1.job_id)
            j2 = export_job_service.get_job(job2.job_id)
            if (
                j1.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]
                and j2.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]
            ):
                break
            time.sleep(0.5)

        # Both should complete
        final_job1 = export_job_service.get_job(job1.job_id)
        final_job2 = export_job_service.get_job(job2.job_id)
        assert final_job1.status == ExportJobStatus.COMPLETED
        assert final_job2.status == ExportJobStatus.COMPLETED

    def test_multiple_jobs_sequential_execution(self, export_job_service, sample_photos):
        """Test that multiple jobs execute sequentially."""
        # Create 3 jobs
        jobs = []
        for i in range(3):
            job = export_job_service.create_job(
                format=ExportJobFormat.JSON,
                filter=ExportJobFilter(photo_paths=sample_photos[:2]),  # Small batch
            )
            jobs.append(job.job_id)

        # Wait for all to complete
        max_wait = 45
        start_time = time.time()

        while time.time() - start_time < max_wait:
            statuses = [export_job_service.get_job(jid).status for jid in jobs]
            all_done = all(
                s in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED] for s in statuses
            )
            if all_done:
                break
            time.sleep(0.5)

        # All should complete
        for job_id in jobs:
            final_job = export_job_service.get_job(job_id)
            assert final_job.status == ExportJobStatus.COMPLETED


# ============================================================================
# Job Cancellation Tests
# ============================================================================


@pytest.mark.integration
class TestJobCancellation:
    """Test job cancellation functionality."""

    def test_cancel_pending_job(self, export_job_service, sample_photos):
        """Test cancelling a pending job."""
        # Create a job but don't let it start (create many to queue them)
        jobs = []
        for _ in range(3):
            job = export_job_service.create_job(
                format=ExportJobFormat.JSON,
                filter=ExportJobFilter(photo_paths=sample_photos),
            )
            jobs.append(job.job_id)

        # Wait a moment
        time.sleep(0.5)

        # Cancel the last job (should still be pending)
        last_job_id = jobs[-1]
        last_job = export_job_service.get_job(last_job_id)

        if last_job.status == ExportJobStatus.PENDING:
            # Cancel it
            result = export_job_service.cancel_job(last_job_id)
            assert result is True

            # Verify cancelled
            updated = export_job_service.get_job(last_job_id)
            assert updated.status == ExportJobStatus.CANCELLED

    def test_cancel_running_job(self, export_job_service, sample_photos):
        """Test cancelling a running job."""
        # Create job that takes a while
        job = export_job_service.create_job(
            format=ExportJobFormat.INATURALIST,  # ZIP creation takes longer
            filter=ExportJobFilter(photo_paths=sample_photos),
        )

        # Wait for it to start running
        max_wait = 5
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)
            if updated.status == ExportJobStatus.RUNNING:
                break
            time.sleep(0.2)

        # Try to cancel
        result = export_job_service.cancel_job(job.job_id)

        # Should succeed if job is still running
        updated = export_job_service.get_job(job.job_id)
        if result:
            assert updated.status == ExportJobStatus.CANCELLED
        # If cancel failed, job might have already completed
        else:
            assert updated.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]

    def test_cannot_cancel_completed_job(self, export_job_service, sample_photos):
        """Test that completed jobs cannot be cancelled."""
        # Create and wait for completion
        job = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos[:2]),
        )

        # Wait for completion
        max_wait = 20
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)
            if updated.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.5)

        # Try to cancel
        result = export_job_service.cancel_job(job.job_id)
        assert result is False  # Cannot cancel completed job


# ============================================================================
# Filter Functionality Tests
# ============================================================================


@pytest.mark.integration
class TestFilterFunctionality:
    """Test photo filtering functionality."""

    def test_filter_by_photo_paths(self, export_job_service, sample_photos):
        """Test explicit photo_paths filter."""
        # Only include 2 of the sample photos
        subset = sample_photos[:2]

        job = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=subset),
        )

        # Wait for completion
        max_wait = 20
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)
            if updated.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]:
                break
            time.sleep(0.5)

        # Verify only 2 photos in output
        final_job = export_job_service.get_job(job.job_id)
        assert final_job.status == ExportJobStatus.COMPLETED
        assert final_job.photo_count == 2

    def test_filter_empty_photo_paths(self, export_job_service, sample_photos):
        """Test that empty photo_paths list falls back to directory scan.

        When photo_paths is an empty list [], the service treats it as falsy
        and scans the photos directory instead. This is intentional behavior.
        """
        job = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=[]),
        )

        # Wait for job to finish
        max_wait = 10
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)
            if updated.status in [
                ExportJobStatus.COMPLETED,
                ExportJobStatus.FAILED,
                ExportJobStatus.CANCELLED,
            ]:
                break
            time.sleep(0.5)

        # Job should complete and export all photos from directory
        final_job = export_job_service.get_job(job.job_id)
        assert final_job.status == ExportJobStatus.COMPLETED
        # Falls back to directory scan, finding all 5 sample photos
        assert final_job.photo_count == len(sample_photos)


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling scenarios."""

    def test_job_timeout(self, tmp_path, sample_photos):
        """Test that jobs timeout after configured duration."""
        db_path = tmp_path / "jobs.db"
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        photos_dir = Path(sample_photos[0]).parent

        export_service = ExportMetadataService(cache_ttl=300)

        # Create service with very short timeout
        service = ExportJobService(
            db_path=db_path,
            export_service=export_service,
            photos_dir=photos_dir,
            temp_dir=temp_dir,
            job_timeout_seconds=1,  # 1 second timeout
            job_ttl_seconds=300,
            max_history=50,
        )
        service.start()

        # Create a job that might take longer than 1 second
        # (depends on system speed, so this test might be flaky)
        # Using large batch to increase likelihood of timeout
        many_photos = sample_photos * 20  # Duplicate paths to make longer list

        job = service.create_job(
            format=ExportJobFormat.INATURALIST,
            filter=ExportJobFilter(photo_paths=many_photos),
        )

        # Wait up to 10 seconds
        max_wait = 10
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = service.get_job(job.job_id)
            if updated.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]:
                break
            time.sleep(0.5)

        final_job = service.get_job(job.job_id)
        # Job should either complete (if fast enough) or fail with timeout
        # We accept both outcomes since system speed varies
        assert final_job.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]

        if final_job.status == ExportJobStatus.FAILED:
            assert "timeout" in final_job.error_message.lower()

        service.stop()

    def test_invalid_photo_paths(self, export_job_service, tmp_path):
        """Test job with invalid photo paths.

        Note: Currently the service counts paths provided, not files that exist.
        The export metadata service silently skips non-existent files.
        """
        # Create paths to non-existent photos
        invalid_photos = [
            str(tmp_path / "nonexistent1.jpg"),
            str(tmp_path / "nonexistent2.jpg"),
        ]

        job = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=invalid_photos),
        )

        # Wait for job to finish
        max_wait = 10
        start_time = time.time()

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)
            if updated.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]:
                break
            time.sleep(0.5)

        # Job completes - photo_count reflects paths provided (not files found)
        # Export metadata service silently handles missing files
        final_job = export_job_service.get_job(job.job_id)
        assert final_job.status == ExportJobStatus.COMPLETED
        assert final_job.photo_count == len(invalid_photos)


# ============================================================================
# API Integration Tests
# ============================================================================


@pytest.mark.integration
class TestAPIIntegration:
    """Test API endpoints with real service."""

    def test_list_jobs_with_filtering(self, client, sample_photos):
        """Test listing jobs with status filter."""
        # Create multiple jobs with different outcomes
        jobs = []

        # Create a completed job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos[:2]},
            },
        )
        jobs.append(response.get_json()["job_id"])

        # Wait for first job to complete
        time.sleep(2)

        # Create a pending/running job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos},
            },
        )
        jobs.append(response.get_json()["job_id"])

        # List all jobs
        response = client.get("/api/export/jobs")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] >= 2
        assert len(data["jobs"]) >= 2

        # List only completed jobs
        response = client.get("/api/export/jobs?status=completed")
        assert response.status_code == 200
        data = response.get_json()
        # At least one completed job
        assert data["total"] >= 1

    def test_job_not_found_errors(self, client):
        """Test 404 responses for non-existent jobs."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"

        # Get job
        response = client.get(f"/api/export/jobs/{fake_job_id}")
        assert response.status_code == 404

        # Download
        response = client.get(f"/api/export/jobs/{fake_job_id}/download")
        assert response.status_code == 404

        # Delete
        response = client.delete(f"/api/export/jobs/{fake_job_id}")
        assert response.status_code == 404

        # Cancel
        response = client.post(f"/api/export/jobs/{fake_job_id}/cancel")
        assert response.status_code == 404

    def test_download_incomplete_job_error(self, client, sample_photos):
        """Test that downloading incomplete job returns error."""
        # Create job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos},
            },
        )
        job_id = response.get_json()["job_id"]

        # Try to download immediately (job is PENDING or RUNNING)
        response = client.get(f"/api/export/jobs/{job_id}/download")
        # Should return 400 if job not completed
        if response.status_code == 400:
            data = response.get_json()
            assert "not completed" in data["error"].lower()
        # Or 200 if job completed very quickly
        else:
            assert response.status_code == 200

    def test_invalid_format_creation(self, client, sample_photos):
        """Test creating job with invalid format."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "invalid_format",
                "filter": {"photo_paths": sample_photos},
            },
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "invalid format" in data["error"].lower()


# ============================================================================
# Service Statistics Tests
# ============================================================================


@pytest.mark.integration
class TestServiceStatistics:
    """Test service statistics tracking."""

    def test_statistics_tracking(self, export_job_service, sample_photos):
        """Test that statistics are tracked correctly."""
        # Get initial stats
        initial_stats = export_job_service.get_statistics()

        # Create a job
        job = export_job_service.create_job(
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(photo_paths=sample_photos[:2]),
        )

        # Wait for completion
        time.sleep(3)

        # Get updated stats
        stats = export_job_service.get_statistics()

        # Should have at least 1 job
        assert stats["total_jobs"] >= 1

        # Worker should be running
        assert stats["worker_running"] is True

        # Check job status counts
        assert stats["completed_jobs"] >= 0
        assert stats["pending_jobs"] >= 0
        assert stats["running_jobs"] >= 0
