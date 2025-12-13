"""
Unit tests for ExportJobService.

Tests the export job queue management service.
Simplified version focusing on core functionality.
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from webui.backend.services.export_job_service import ExportJobService
from webui.backend.lib.export_job_types import (
    ExportJob,
    ExportJobStatus,
    ExportJobFormat,
    ExportJobFilter,
)


@pytest.fixture
def mock_export_service():
    """Mock ExportMetadataService."""
    service = Mock()
    # transform_batch_to_darwin_core_csv returns (headers, rows) tuple
    service.transform_batch_to_darwin_core_csv.return_value = (
        ['header1', 'header2'],
        [['row1val1', 'row1val2'], ['row2val1', 'row2val2']]
    )
    service.transform_batch_to_inaturalist_zip.return_value = None  # Writes to output_path directly
    service.transform_to_generic.return_value = {'key': 'value'}
    # get_export_metadata returns an object with to_dict method
    mock_metadata = Mock()
    mock_metadata.to_dict.return_value = {'filename': 'test.jpg'}
    service.get_export_metadata.return_value = mock_metadata
    return service


@pytest.fixture
def photos_dir(tmp_path):
    """Create temp photos directory."""
    photos = tmp_path / "photos"
    photos.mkdir()
    for i in range(5):
        (photos / f"photo_{i}.jpg").write_text(f"photo {i}")
    return photos


@pytest.fixture
def temp_dir(tmp_path):
    """Create temp directory for exports."""
    temp = tmp_path / "temp"
    temp.mkdir()
    return temp


@pytest.fixture
def db_path(tmp_path):
    """Database path for tests."""
    return tmp_path / "export_jobs.db"


@pytest.fixture
def service(db_path, mock_export_service, photos_dir, temp_dir):
    """Create ExportJobService instance."""
    svc = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_timeout_seconds=5,
        job_ttl_seconds=60,
        max_history=50,
    )
    yield svc
    if svc._running:
        svc.stop()


# =============================================================================
# Job Creation Tests
# =============================================================================


def test_create_job_basic(service):
    """Test creating a basic export job."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    assert job is not None
    assert job.job_id is not None
    assert len(job.job_id) == 36  # UUID4 format
    assert job.status == ExportJobStatus.PENDING
    assert job.format == ExportJobFormat.DARWIN_CORE


def test_create_job_with_filter(service):
    """Test creating job with filter options."""
    filter_obj = ExportJobFilter(
        date_start="2024-01-01",
        deployment="test_deployment",
        tags=["moth"],
    )

    job = service.create_job(
        format=ExportJobFormat.INATURALIST,
        filter=filter_obj,
    )

    assert job.filter.date_start == "2024-01-01"
    assert job.filter.deployment == "test_deployment"


# =============================================================================
# Job Retrieval Tests
# =============================================================================


def test_get_job_exists(service):
    """Test retrieving existing job."""
    created_job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    retrieved_job = service.get_job(created_job.job_id)

    assert retrieved_job is not None
    assert retrieved_job.job_id == created_job.job_id


def test_get_job_not_exists(service):
    """Test retrieving non-existent job returns None."""
    job = service.get_job("non-existent-id")
    assert job is None


def test_list_jobs_empty(service):
    """Test listing jobs when empty."""
    jobs, total = service.list_jobs()
    assert jobs == []
    assert total == 0


def test_list_jobs_all(service):
    """Test listing all jobs."""
    for i in range(3):
        service.create_job(
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
        )

    jobs, total = service.list_jobs()
    assert len(jobs) == 3
    assert total == 3


def test_list_jobs_pagination(service):
    """Test listing jobs with pagination."""
    for i in range(5):
        service.create_job(
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
        )

    jobs_page1, total = service.list_jobs(limit=2, offset=0)
    assert len(jobs_page1) == 2
    assert total == 5

    jobs_page2, total = service.list_jobs(limit=2, offset=2)
    assert len(jobs_page2) == 2


# =============================================================================
# Job Control Tests
# =============================================================================


def test_cancel_pending_job(service):
    """Test cancelling a pending job."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    result = service.cancel_job(job.job_id)
    assert result is True

    updated_job = service.get_job(job.job_id)
    assert updated_job.status == ExportJobStatus.CANCELLED


def test_cancel_nonexistent_job(service):
    """Test cancelling non-existent job returns False."""
    result = service.cancel_job("non-existent-id")
    assert result is False


def test_delete_completed_job(service):
    """Test deleting a completed job."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Manually complete the job
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    service._db.update_job(job)

    result = service.delete_job(job.job_id)
    assert result is True

    deleted_job = service.get_job(job.job_id)
    assert deleted_job is None


def test_delete_pending_job_fails(service):
    """Test deleting a pending job fails."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    result = service.delete_job(job.job_id)
    assert result is False


# =============================================================================
# Download Path Tests
# =============================================================================


def test_get_download_path_completed_job(service):
    """Test getting download path for completed job."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Complete the job
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    job.output_path = "/tmp/export.csv"
    service._db.update_job(job)

    download_path = service.get_download_path(job.job_id)
    assert download_path == Path("/tmp/export.csv")


def test_get_download_path_pending_job(service):
    """Test getting download path for pending job returns None."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    download_path = service.get_download_path(job.job_id)
    assert download_path is None


# =============================================================================
# Worker Thread Tests
# =============================================================================


def test_start_service(service):
    """Test starting the service."""
    assert service._running is False
    service.start()
    assert service._running is True
    assert service._worker_thread is not None


def test_stop_service(service):
    """Test stopping the service."""
    service.start()
    service.stop()
    assert service._running is False


# =============================================================================
# Job Execution Tests
# =============================================================================


def test_job_execution_success(service, mock_export_service, photos_dir):
    """Test successful job execution."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    photo_paths = list(photos_dir.glob("*.jpg"))
    with patch.object(service, '_collect_photos', return_value=photo_paths):
        service.start()

        # Wait for job to complete
        for _ in range(30):  # 3 seconds max
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.COMPLETED
    assert final_job.output_path is not None
    assert final_job.photo_count == len(photo_paths)


def test_job_execution_failure(service, mock_export_service):
    """Test job execution with error."""
    mock_export_service.transform_batch_to_darwin_core_csv.side_effect = Exception("Export failed")

    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    with patch.object(service, '_collect_photos', return_value=[Path("/tmp/photo.jpg")]):
        service.start()

        # Wait for job to fail
        for _ in range(30):
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.FAILED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.FAILED
    assert "Export failed" in final_job.error_message


# =============================================================================
# Statistics Tests
# =============================================================================


def test_get_statistics_empty(service):
    """Test statistics when no jobs exist."""
    stats = service.get_statistics()
    assert stats['total_jobs'] == 0
    assert stats['pending_jobs'] == 0
    assert stats['worker_running'] is False


def test_get_statistics_with_jobs(service):
    """Test statistics with jobs."""
    service.create_job(format=ExportJobFormat.DARWIN_CORE, filter=ExportJobFilter())
    service.create_job(format=ExportJobFormat.JSON, filter=ExportJobFilter())

    stats = service.get_statistics()
    assert stats['total_jobs'] == 2
    assert stats['pending_jobs'] == 2


# =============================================================================
# Photo Collection Tests
# =============================================================================


def test_collect_photos_explicit_paths(service):
    """Test collecting photos with explicit paths."""
    photo_paths = ["/photos/photo1.jpg", "/photos/photo2.jpg"]
    filter_obj = ExportJobFilter(photo_paths=photo_paths)

    collected = service._collect_photos(filter_obj)
    assert len(collected) == 2
    assert all(isinstance(p, Path) for p in collected)


def test_collect_photos_all_in_directory(service, photos_dir):
    """Test collecting all photos in directory."""
    filter_obj = ExportJobFilter()
    collected = service._collect_photos(filter_obj)
    assert len(collected) == 5


# =============================================================================
# Persistence Tests
# =============================================================================


def test_job_persistence_across_restart(db_path, mock_export_service, photos_dir, temp_dir):
    """Test that jobs persist across service restarts."""
    service1 = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
    )

    job = service1.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )
    job_id = job.job_id
    service1.stop()

    # Create new service with same database
    service2 = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
    )

    recovered_job = service2.get_job(job_id)
    assert recovered_job is not None
    assert recovered_job.job_id == job_id
    assert recovered_job.status == ExportJobStatus.PENDING
    service2.stop()
