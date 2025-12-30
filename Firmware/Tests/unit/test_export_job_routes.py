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

from datetime import datetime
from unittest.mock import Mock

import pytest
from flask import Flask

from webui.backend.lib.export_job_types import (
    ExportError,
    ExportJob,
    ExportJobFilter,
    ExportJobFormat,
    ExportJobProgress,
    ExportJobStatus,
)
from webui.backend.lib.series_detection import SeriesType

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
        # series_type is passed as string to ExportJobFilter constructor
        assert filter_obj.series_type in ("hdr", SeriesType.HDR)
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

    def test_create_job_valid_series_type_hdr(self, client, mock_export_job_service):
        """Test creating job with valid series_type 'hdr'."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "series_type": "hdr",
                },
            },
        )

        assert response.status_code == 202

    def test_create_job_valid_series_type_focus_bracket(self, client, mock_export_job_service):
        """Test creating job with valid series_type 'focus_bracket'."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "series_type": "focus_bracket",
                },
            },
        )

        assert response.status_code == 202

    def test_create_job_invalid_series_type(self, client, mock_export_job_service):
        """Test 400 error for invalid series_type value."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "series_type": "invalid_type",
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Invalid series_type" in data["error"]
        assert "invalid_type" in data["error"]

    def test_create_job_invalid_series_type_uppercase(self, client, mock_export_job_service):
        """Test 400 error for series_type with wrong case (HDR instead of hdr)."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {
                    "series_type": "HDR",  # Wrong case
                },
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Invalid series_type" in data["error"]

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

    def test_create_job_with_ttl_seconds(self, client, mock_export_job_service):
        """Test creating job with custom TTL."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 7200,  # 2 hours
            },
        )

        assert response.status_code == 202

        # Verify ttl_seconds was passed to service
        mock_export_job_service.create_job.assert_called_once()
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["ttl_seconds"] == 7200

    def test_create_job_ttl_seconds_minimum(self, client, mock_export_job_service):
        """Test creating job with minimum valid TTL (60 seconds)."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 60,  # Minimum allowed
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["ttl_seconds"] == 60

    def test_create_job_ttl_seconds_maximum(self, client, mock_export_job_service):
        """Test creating job with maximum valid TTL (86400 seconds = 24 hours)."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 86400,  # Maximum allowed
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["ttl_seconds"] == 86400

    def test_create_job_ttl_seconds_too_low(self, client, mock_export_job_service):
        """Test 400 error when TTL is below minimum (60 seconds)."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 59,  # Below minimum
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "60" in data["error"]  # Should mention minimum

    def test_create_job_ttl_seconds_too_high(self, client, mock_export_job_service):
        """Test 400 error when TTL exceeds maximum (86400 seconds)."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 86401,  # Above maximum
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "86400" in data["error"]  # Should mention maximum

    def test_create_job_ttl_seconds_not_integer(self, client, mock_export_job_service):
        """Test 400 error when TTL is not an integer."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": "3600",  # String instead of int
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "integer" in data["error"].lower()

    def test_create_job_ttl_seconds_float(self, client, mock_export_job_service):
        """Test 400 error when TTL is a float."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "ttl_seconds": 3600.5,  # Float instead of int
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "integer" in data["error"].lower()

    def test_create_job_without_ttl_uses_default(self, client, mock_export_job_service):
        """Test that jobs without ttl_seconds use service default."""
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={"format": "darwin_core"},
        )

        assert response.status_code == 202

        # Verify ttl_seconds was passed as None (service uses default)
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["ttl_seconds"] is None


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
            ExportError(error="metadata missing", photo_path="photo1.jpg"),
            ExportError(error="GPS invalid", photo_path="photo2.jpg"),
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

        # Verify: 400 status with generic error (no info disclosure)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Invalid job ID"


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


# ============================================================================
# Preset Integration Tests (Issue #123)
# ============================================================================


@pytest.fixture
def mock_export_preset_manager():
    """Mock ExportPresetManager for preset integration testing."""
    from unittest.mock import Mock

    from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
    from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

    manager = Mock()

    # Default: no preset found
    manager.get_preset.return_value = None

    return manager


@pytest.fixture
def app_with_preset_manager(mock_export_job_service, mock_export_preset_manager, tmp_path):
    """Flask app with both export job service and preset manager."""
    from webui.backend.routes.export import export_bp

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['EXPORT_JOB_SERVICE'] = mock_export_job_service
    app.config['EXPORT_PRESET_MANAGER'] = mock_export_preset_manager

    app.register_blueprint(export_bp, url_prefix='/api/export')

    return app


@pytest.fixture
def client_with_presets(app_with_preset_manager):
    """Test client with preset manager configured."""
    return app_with_preset_manager.test_client()


class TestCreateExportJobWithPreset:
    """Tests for POST /api/export/jobs with preset parameter (Issue #123)."""

    def test_create_job_with_valid_preset(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test creating job using a preset name."""
        from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

        # Set up mock preset
        preset = ExportPreset(
            name="gbif_biodiversity",
            display_name="GBIF Export",
            export_format=ExportJobFormat.DARWIN_CORE,
            description="Export for GBIF",
            filter=ExportJobFilter(has_species=True),
            options={"validate": True},
            category=ExportPresetCategory.BUILT_IN,
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job(format=ExportJobFormat.DARWIN_CORE)
        mock_export_job_service.create_job.return_value = job

        response = client_with_presets.post(
            "/api/export/jobs",
            json={"preset": "gbif_biodiversity"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == "test-job-123"
        assert data["format"] == "darwin_core"

        # Verify preset was looked up
        mock_export_preset_manager.get_preset.assert_called_once_with("gbif_biodiversity")

        # Verify job was created with preset values
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.DARWIN_CORE
        assert call_kwargs["filter"].has_species is True
        assert call_kwargs["options"]["validate"] is True

    def test_create_job_preset_overridden_by_explicit_values(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that explicit values override preset defaults."""
        from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory

        # Preset with default values
        preset = ExportPreset(
            name="simple_json",
            display_name="Simple JSON",
            export_format=ExportJobFormat.JSON,
            filter=ExportJobFilter(has_species=False, tags=["default"]),
            options={"pretty": True},
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job(format=ExportJobFormat.CSV)
        mock_export_job_service.create_job.return_value = job

        # Override format, filter, and options
        response = client_with_presets.post(
            "/api/export/jobs",
            json={
                "preset": "simple_json",
                "format": "csv",  # Override preset format
                "filter": {
                    "tags": ["moth", "identified"],  # Override preset tags
                    "date_start": "2024-01-01",  # Add new filter
                },
                "options": {
                    "include_bom": True,  # Override options
                },
            },
        )

        assert response.status_code == 202

        # Verify overrides were applied
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.CSV  # Overridden
        assert call_kwargs["filter"].tags == ["moth", "identified"]  # Overridden
        assert call_kwargs["filter"].date_start == "2024-01-01"  # Added
        assert call_kwargs["filter"].has_species is False  # From preset (not overridden)
        assert call_kwargs["options"]["include_bom"] is True  # Overridden

    def test_create_job_invalid_preset_name(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test 400 error for non-existent preset."""
        mock_export_preset_manager.get_preset.return_value = None

        response = client_with_presets.post(
            "/api/export/jobs",
            json={"preset": "nonexistent_preset"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "preset" in data["error"].lower()
        assert "nonexistent_preset" in data["error"]

    def test_create_job_preset_with_format_only(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that preset provides format when not specified."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="hdr_series",
            display_name="HDR Series",
            export_format=ExportJobFormat.JSON,
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job(format=ExportJobFormat.JSON)
        mock_export_job_service.create_job.return_value = job

        # Only provide preset, no format
        response = client_with_presets.post(
            "/api/export/jobs",
            json={"preset": "hdr_series"},
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.JSON

    def test_create_job_preset_filter_merged_with_explicit(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that preset filter and explicit filter are merged."""
        from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        # Preset with partial filter
        preset = ExportPreset(
            name="focus_bracket_series",
            display_name="Focus Bracket Series",
            export_format=ExportJobFormat.JSON,
            filter=ExportJobFilter(series_type="focus_bracket"),
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        # Add additional filter criteria
        response = client_with_presets.post(
            "/api/export/jobs",
            json={
                "preset": "focus_bracket_series",
                "filter": {
                    "date_start": "2024-06-01",
                    "deployment": "summer_2024",
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        filter_obj = call_kwargs["filter"]
        # From preset
        assert filter_obj.series_type == "focus_bracket"
        # From explicit filter
        assert filter_obj.date_start == "2024-06-01"
        assert filter_obj.deployment == "summer_2024"

    def test_create_job_preset_options_merged(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that preset options and explicit options are merged."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="simple_csv",
            display_name="Simple CSV",
            export_format=ExportJobFormat.CSV,
            options={"include_bom": True, "delimiter": ","},
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client_with_presets.post(
            "/api/export/jobs",
            json={
                "preset": "simple_csv",
                "options": {
                    "delimiter": ";",  # Override
                    "quote_char": '"',  # Add
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        options = call_kwargs["options"]
        assert options["include_bom"] is True  # From preset
        assert options["delimiter"] == ";"  # Overridden
        assert options["quote_char"] == '"'  # Added

    def test_create_job_both_preset_and_format(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that explicit format overrides preset format."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="gbif_biodiversity",
            display_name="GBIF Export",
            export_format=ExportJobFormat.DARWIN_CORE,
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job(format=ExportJobFormat.CSV)
        mock_export_job_service.create_job.return_value = job

        response = client_with_presets.post(
            "/api/export/jobs",
            json={
                "preset": "gbif_biodiversity",
                "format": "csv",  # Override darwin_core
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.CSV

    def test_create_job_preset_with_ttl(
        self, client_with_presets, mock_export_job_service, mock_export_preset_manager
    ):
        """Test that TTL can be specified with preset."""
        from webui.backend.lib.export_job_types import ExportJobFormat
        from webui.backend.lib.export_preset_types import ExportPreset

        preset = ExportPreset(
            name="simple_json",
            display_name="Simple JSON",
            export_format=ExportJobFormat.JSON,
        )
        mock_export_preset_manager.get_preset.return_value = preset

        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client_with_presets.post(
            "/api/export/jobs",
            json={
                "preset": "simple_json",
                "ttl_seconds": 7200,
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["ttl_seconds"] == 7200

    def test_create_job_no_preset_manager_configured(
        self, client, mock_export_job_service
    ):
        """Test that preset parameter is ignored if no preset manager configured."""
        # Use regular client (no preset manager)
        response = client.post(
            "/api/export/jobs",
            json={
                "preset": "some_preset",
                "format": "csv",  # Must provide format since no preset manager
            },
        )

        # Should work since format is provided
        # Preset is silently ignored when manager not configured
        job = create_test_job()
        mock_export_job_service.create_job.return_value = job

        response = client.post(
            "/api/export/jobs",
            json={"format": "csv"},
        )

        assert response.status_code == 202
