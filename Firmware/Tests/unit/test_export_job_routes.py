"""
Unit tests for export job API routes (Issue #122).

Tests all REST endpoints for export job management:
- POST /api/export/jobs - Create export job
- GET /api/export/jobs - List all jobs
- GET /api/export/jobs/<job_id> - Get job status
- GET /api/export/jobs/<job_id>/download - Download result
- DELETE /api/export/jobs/<job_id> - Delete job
- POST /api/export/jobs/<job_id>/cancel - Cancel job

Author: Mothbox Team
Date: 2024
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from flask import Flask
from datetime import datetime

from webui.backend.lib.export_job_types import (
    ExportJob,
    ExportJobStatus,
    ExportJobFormat,
    ExportJobFilter,
    ExportJobProgress,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_export_job_service():
    """Mock ExportJobService for route testing."""
    service = Mock()

    # Default return values
    service.create_job.return_value = None
    service.get_job.return_value = None
    service.list_jobs.return_value = ([], 0)  # Returns (jobs, total_count) tuple
    service.cancel_job.return_value = False
    service.delete_job.return_value = False
    service.get_download_path.return_value = None
    service.get_statistics.return_value = {}

    return service


@pytest.fixture
def app(mock_export_job_service, tmp_path):
    """Flask app with export routes for testing."""
    from webui.backend.routes.export import export_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
    app.config['EXPORT_JOB_SERVICE'] = mock_export_job_service
    app.register_blueprint(export_bp, url_prefix='/api/export')

    return app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


def create_test_job(
    job_id: str = "test-job-123",
    status: ExportJobStatus = ExportJobStatus.PENDING,
    format: ExportJobFormat = ExportJobFormat.DARWIN_CORE,
    photo_count: int = 0,
    output_path: str | None = None,
) -> ExportJob:
    """Helper to create test job instances."""
    return ExportJob(
        job_id=job_id,
        status=status,
        format=format,
        filter=ExportJobFilter(),
        progress=ExportJobProgress(),
        created_at=datetime.now().timestamp(),
        photo_count=photo_count,
        output_path=output_path,
    )


# ============================================================================
# POST /api/export/jobs - Create Export Job
# ============================================================================


class TestCreateExportJob:
    """Tests for POST /api/export/jobs - Create export job."""

    def test_create_job_minimal(self, client, mock_export_job_service):
        """Test creating job with only required format field."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={"format": "darwin_core"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "pending"
        assert data["format"] == "darwin_core"
        assert "status_url" in data
        assert data["message"] == "Export job created"

        # Verify service was called correctly
        mock_export_job_service.create_job.assert_called_once()
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.DARWIN_CORE
        assert isinstance(call_kwargs["filter"], ExportJobFilter)

    def test_create_job_with_filter(self, client, mock_export_job_service):
        """Test creating job with filter criteria."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "2024-01-01",
                    "date_end": "2024-12-31",
                    "deployment": "forest_2024",
                    "tags": ["moth", "identified"],
                    "series_type": "hdr",
                    "has_species": True,
                },
            },
        )

        assert response.status_code == 202

        # Verify filter was passed correctly
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert filter_obj.date_start == "2024-01-01"
        assert filter_obj.date_end == "2024-12-31"
        assert filter_obj.deployment == "forest_2024"
        assert filter_obj.tags == ["moth", "identified"]
        assert filter_obj.series_type == "hdr"
        assert filter_obj.has_species is True

    def test_create_job_with_photo_paths(self, client, mock_export_job_service):
        """Test creating job with explicit photo paths."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {
                    "photo_paths": ["photo1.jpg", "photo2.jpg"],
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert filter_obj.photo_paths == ["photo1.jpg", "photo2.jpg"]

    def test_create_job_with_options(self, client, mock_export_job_service):
        """Test creating job with format-specific options."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "options": {
                    "validate": True,
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["options"] == {"validate": True}

    def test_create_job_missing_format(self, client, mock_export_job_service):
        """Test 400 error when format is missing."""
        response = client.post(
            "/api/export/jobs",
            json={},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "format" in data["error"].lower()

    def test_create_job_invalid_format(self, client, mock_export_job_service):
        """Test 400 error for invalid format."""
        response = client.post(
            "/api/export/jobs",
            json={"format": "invalid_format"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "format" in data["error"].lower()

    def test_create_job_invalid_filter_field(self, client, mock_export_job_service):
        """Test 400 error for invalid filter field."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "invalid_field": "value",
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_job_valid_date_filter(self, client, mock_export_job_service):
        """Test creating job with valid date filter."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "2024-01-01",
                    "date_end": "2024-12-31",
                },
            },
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == job.job_id

    def test_create_job_invalid_date_format(self, client, mock_export_job_service):
        """Test 400 error for invalid date format."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "01/15/2024",  # Wrong format
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "date_start" in data["error"]
        assert "YYYY-MM-DD" in data["error"]

    def test_create_job_invalid_date_value(self, client, mock_export_job_service):
        """Test 400 error for invalid date value (Feb 30)."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "2024-02-30",  # Invalid date
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "date_start" in data["error"]

    def test_create_job_invalid_date_end(self, client, mock_export_job_service):
        """Test 400 error for invalid date_end format."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_end": "not-a-date",
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "date_end" in data["error"]

    def test_create_job_date_start_after_end(self, client, mock_export_job_service):
        """Test 400 error when date_start is after date_end."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "2024-12-31",
                    "date_end": "2024-01-01",  # Before start
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "date_start must be before" in data["error"]

    def test_create_job_date_start_only(self, client, mock_export_job_service):
        """Test creating job with only date_start."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_start": "2024-06-01",
                },
            },
        )

        assert response.status_code == 202

    def test_create_job_date_end_only(self, client, mock_export_job_service):
        """Test creating job with only date_end."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "date_end": "2024-06-30",
                },
            },
        )

        assert response.status_code == 202

    def test_create_job_service_unavailable(self, client):
        """Test 500 error when service is not available."""
        # Create app without service configured
        from webui.backend.routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Don't set EXPORT_JOB_SERVICE
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        response = client.post(
            "/api/export/jobs",
            json={"format": "csv"},
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "service" in data["error"].lower()

    def test_create_job_all_formats(self, client, mock_export_job_service):
        """Test creating jobs with all supported formats."""
        formats = ["darwin_core", "inaturalist", "json", "csv"]

        for fmt in formats:
            job = create_test_job(format=ExportJobFormat(fmt))
            mock_export_job_service.create_job.return_value = job

            response = client.post(
                "/api/export/jobs",
                json={"format": fmt},
            )

            assert response.status_code == 202
            data = response.get_json()
            assert data["format"] == fmt


# ============================================================================
# GET /api/export/jobs - List Jobs
# ============================================================================


class TestListJobs:
    """Tests for GET /api/export/jobs - List all jobs."""

    def test_list_empty_jobs(self, client, mock_export_job_service):
        """Test listing when no jobs exist."""
        mock_export_job_service.list_jobs.return_value = ([], 0)

        response = client.get("/api/export/jobs")

        assert response.status_code == 200
        data = response.get_json()
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_all_jobs(self, client, mock_export_job_service):
        """Test listing multiple jobs."""
        jobs = [
            create_test_job(job_id="job1", status=ExportJobStatus.PENDING),
            create_test_job(job_id="job2", status=ExportJobStatus.RUNNING),
            create_test_job(job_id="job3", status=ExportJobStatus.COMPLETED),
        ]
        mock_export_job_service.list_jobs.return_value = (jobs, len(jobs))

        response = client.get("/api/export/jobs")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) == 3
        assert data["total"] == 3

        # Verify jobs are serialized correctly
        job_ids = [j["job_id"] for j in data["jobs"]]
        assert "job1" in job_ids
        assert "job2" in job_ids
        assert "job3" in job_ids

    def test_list_with_pagination(self, client, mock_export_job_service):
        """Test pagination with limit and offset."""
        jobs = [create_test_job(job_id=f"job{i}") for i in range(10)]
        mock_export_job_service.list_jobs.return_value = (jobs, len(jobs))

        response = client.get("/api/export/jobs?limit=5&offset=2")

        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 5
        assert data["offset"] == 2

        # Verify service was called with pagination params
        mock_export_job_service.list_jobs.assert_called_once_with(
            status=None, limit=5, offset=2
        )

    def test_list_with_status_filter(self, client, mock_export_job_service):
        """Test filtering by status."""
        jobs = [create_test_job(status=ExportJobStatus.COMPLETED)]
        mock_export_job_service.list_jobs.return_value = (jobs, len(jobs))

        response = client.get("/api/export/jobs?status=completed")

        assert response.status_code == 200

        # Verify service was called with status filter
        mock_export_job_service.list_jobs.assert_called_once_with(
            status=ExportJobStatus.COMPLETED, limit=50, offset=0
        )

    def test_list_with_invalid_status(self, client, mock_export_job_service):
        """Test 400 error for invalid status filter."""
        response = client.get("/api/export/jobs?status=invalid")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "status" in data["error"].lower()

    def test_list_with_max_limit(self, client, mock_export_job_service):
        """Test that limit is capped at 100."""
        mock_export_job_service.list_jobs.return_value = ([], 0)

        response = client.get("/api/export/jobs?limit=200")

        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 100

        # Verify service was called with capped limit
        mock_export_job_service.list_jobs.assert_called_once_with(
            status=None, limit=100, offset=0
        )

    def test_list_timestamp_serialization(self, client, mock_export_job_service):
        """Test that timestamps are serialized as ISO 8601 strings."""
        job = create_test_job()
        job.created_at = 1701388800.0  # 2023-12-01 00:00:00 UTC
        job.started_at = 1701388801.0
        job.completed_at = 1701388900.0

        mock_export_job_service.list_jobs.return_value = ([job], 1)

        response = client.get("/api/export/jobs")

        assert response.status_code == 200
        data = response.get_json()
        job_data = data["jobs"][0]

        assert "created_at" in job_data
        assert "started_at" in job_data
        assert "completed_at" in job_data
        # Check ISO 8601 format
        assert job_data["created_at"].endswith("Z")


# ============================================================================
# GET /api/export/jobs/<job_id> - Get Job Status
# ============================================================================


class TestGetJobStatus:
    """Tests for GET /api/export/jobs/<job_id> - Get job status."""

    def test_get_existing_job(self, client, mock_export_job_service):
        """Test getting status of existing job."""
        job = create_test_job(
            job_id="job123",
            status=ExportJobStatus.RUNNING,
            photo_count=50,
        )
        job.progress = ExportJobProgress(
            current=25,
            total=50,
            percent=50,
            phase="exporting",
        )
        mock_export_job_service.get_job.return_value = job

        response = client.get("/api/export/jobs/job123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["job_id"] == "job123"
        assert data["status"] == "running"
        assert data["photo_count"] == 50
        assert data["progress"]["current"] == 25
        assert data["progress"]["total"] == 50
        assert data["progress"]["percent"] == 50
        assert data["progress"]["phase"] == "exporting"

    def test_get_nonexistent_job(self, client, mock_export_job_service):
        """Test 404 error for non-existent job."""
        mock_export_job_service.get_job.return_value = None

        response = client.get("/api/export/jobs/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_get_completed_job(self, client, mock_export_job_service):
        """Test getting completed job with all fields populated."""
        job = create_test_job(
            status=ExportJobStatus.COMPLETED,
            photo_count=100,
            output_path="/tmp/export.csv",
        )
        job.output_size_bytes = 50000
        job.started_at = datetime.now().timestamp()
        job.completed_at = datetime.now().timestamp()

        mock_export_job_service.get_job.return_value = job

        response = client.get("/api/export/jobs/test-job-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"
        assert data["photo_count"] == 100
        assert data["output_size_bytes"] == 50000
        assert data["started_at"] is not None
        assert data["completed_at"] is not None

    def test_get_failed_job(self, client, mock_export_job_service):
        """Test getting failed job with error information."""
        job = create_test_job(status=ExportJobStatus.FAILED)
        job.error_message = "Export failed: timeout"
        job.errors = [
            {"photo": "photo1.jpg", "error": "metadata missing"},
            {"photo": "photo2.jpg", "error": "GPS invalid"},
        ]

        mock_export_job_service.get_job.return_value = job

        response = client.get("/api/export/jobs/test-job-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Export failed: timeout"
        assert len(data["errors"]) == 2


# ============================================================================
# GET /api/export/jobs/<job_id>/download - Download Result
# ============================================================================


class TestDownloadJobResult:
    """Tests for GET /api/export/jobs/<job_id>/download - Download result."""

    def test_download_completed_csv(self, client, mock_export_job_service, tmp_path):
        """Test downloading completed CSV export."""
        # Create test output file
        output_file = tmp_path / "export.csv"
        output_file.write_text("header1,header2\nvalue1,value2\n")

        job = create_test_job(
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.CSV,
            output_path=str(output_file),
        )
        mock_export_job_service.get_job.return_value = job
        mock_export_job_service.get_download_path.return_value = output_file

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert b"header1,header2" in response.data
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_download_completed_json(self, client, mock_export_job_service, tmp_path):
        """Test downloading completed JSON export."""
        output_file = tmp_path / "export.json"
        output_file.write_text('{"data": []}')

        job = create_test_job(
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.JSON,
            output_path=str(output_file),
        )
        mock_export_job_service.get_job.return_value = job
        mock_export_job_service.get_download_path.return_value = output_file

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 200
        assert response.mimetype == "application/json"

    def test_download_completed_zip(self, client, mock_export_job_service, tmp_path):
        """Test downloading completed ZIP export (iNaturalist)."""
        output_file = tmp_path / "export.zip"
        output_file.write_bytes(b"PK\x03\x04")  # ZIP magic bytes

        job = create_test_job(
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.INATURALIST,
            output_path=str(output_file),
        )
        mock_export_job_service.get_job.return_value = job
        mock_export_job_service.get_download_path.return_value = output_file

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 200
        assert response.mimetype == "application/zip"

    def test_download_pending_job(self, client, mock_export_job_service):
        """Test 400 error when job is not completed."""
        job = create_test_job(status=ExportJobStatus.PENDING)
        mock_export_job_service.get_job.return_value = job

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "not completed" in data["error"].lower()

    def test_download_running_job(self, client, mock_export_job_service):
        """Test 400 error when job is still running."""
        job = create_test_job(status=ExportJobStatus.RUNNING)
        mock_export_job_service.get_job.return_value = job

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 400

    def test_download_nonexistent_job(self, client, mock_export_job_service):
        """Test 404 error for non-existent job."""
        mock_export_job_service.get_job.return_value = None

        response = client.get("/api/export/jobs/nonexistent/download")

        assert response.status_code == 404

    def test_download_missing_output_file(self, client, mock_export_job_service):
        """Test 404 error when output file doesn't exist."""
        job = create_test_job(status=ExportJobStatus.COMPLETED)
        mock_export_job_service.get_job.return_value = job
        mock_export_job_service.get_download_path.return_value = None

        response = client.get("/api/export/jobs/test-job-123/download")

        assert response.status_code == 404
        data = response.get_json()
        assert "output file" in data["error"].lower()


# ============================================================================
# DELETE /api/export/jobs/<job_id> - Delete Job
# ============================================================================


class TestDeleteJob:
    """Tests for DELETE /api/export/jobs/<job_id> - Delete job."""

    def test_delete_completed_job(self, client, mock_export_job_service):
        """Test deleting a completed job."""
        mock_export_job_service.delete_job.return_value = True

        response = client.delete("/api/export/jobs/test-job-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

        mock_export_job_service.delete_job.assert_called_once_with("test-job-123")

    def test_delete_nonexistent_job(self, client, mock_export_job_service):
        """Test 404 error when deleting non-existent job."""
        mock_export_job_service.delete_job.return_value = False

        response = client.delete("/api/export/jobs/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_delete_running_job_error(self, client, mock_export_job_service):
        """Test that delete_job handles running job rejection."""
        # Service should raise ValueError for running job
        mock_export_job_service.delete_job.side_effect = ValueError("Cannot delete running job")

        response = client.delete("/api/export/jobs/running-job")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "running" in data["error"].lower()


# ============================================================================
# POST /api/export/jobs/<job_id>/cancel - Cancel Job
# ============================================================================


class TestCancelJob:
    """Tests for POST /api/export/jobs/<job_id>/cancel - Cancel job."""

    def test_cancel_pending_job(self, client, mock_export_job_service):
        """Test cancelling a pending job."""
        mock_export_job_service.cancel_job.return_value = True

        response = client.post("/api/export/jobs/test-job-123/cancel")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "cancelled" in data["message"].lower()

        mock_export_job_service.cancel_job.assert_called_once_with("test-job-123")

    def test_cancel_running_job(self, client, mock_export_job_service):
        """Test cancelling a running job."""
        mock_export_job_service.cancel_job.return_value = True

        response = client.post("/api/export/jobs/running-job/cancel")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_cancel_completed_job(self, client, mock_export_job_service):
        """Test 400 error when cancelling completed job."""
        mock_export_job_service.cancel_job.side_effect = ValueError("Cannot cancel completed job")

        response = client.post("/api/export/jobs/completed-job/cancel")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_cancel_nonexistent_job(self, client, mock_export_job_service):
        """Test 404 error when cancelling non-existent job."""
        mock_export_job_service.cancel_job.return_value = False

        response = client.post("/api/export/jobs/nonexistent/cancel")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()


# ============================================================================
# Service Unavailable Tests
# ============================================================================


class TestServiceUnavailable:
    """Tests for service unavailable scenarios."""

    def test_all_endpoints_require_service(self):
        """Test that all endpoints return 500 when service is unavailable."""
        from webui.backend.routes.export import export_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Don't set EXPORT_JOB_SERVICE
        app.register_blueprint(export_bp, url_prefix='/api/export')

        client = app.test_client()

        # POST /jobs
        response = client.post("/api/export/jobs", json={"format": "csv"})
        assert response.status_code == 500

        # GET /jobs
        response = client.get("/api/export/jobs")
        assert response.status_code == 500

        # GET /jobs/<id>
        response = client.get("/api/export/jobs/test-job")
        assert response.status_code == 500

        # GET /jobs/<id>/download
        response = client.get("/api/export/jobs/test-job/download")
        assert response.status_code == 500

        # DELETE /jobs/<id>
        response = client.delete("/api/export/jobs/test-job")
        assert response.status_code == 500

        # POST /jobs/<id>/cancel
        response = client.post("/api/export/jobs/test-job/cancel")
        assert response.status_code == 500
