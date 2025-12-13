"""
Unit tests for ExportJobService.

Tests the export job queue management service.
Simplified version focusing on core functionality.
"""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from webui.backend.lib.export_job_types import (
    ExportJobFilter,
    ExportJobFormat,
    ExportJobStatus,
)
from webui.backend.services.export_job_service import ExportJobService


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
    # get_export_metadata returns an object with to_dict method and required attributes
    mock_metadata = Mock()
    mock_metadata.to_dict.return_value = {'filename': 'test.jpg'}
    # Required attributes for is_valid_for_export() and transform_to_csv_row()
    mock_metadata.latitude = 35.9606
    mock_metadata.longitude = -83.9207
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


def test_get_download_path_completed_job(service, temp_dir):
    """Test getting download path for completed job."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Complete the job with path in allowed temp_dir
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    output_file = temp_dir / "export.csv"
    output_file.write_text("test")  # Create the file
    job.output_path = str(output_file)
    service._db.update_job(job)

    download_path = service.get_download_path(job.job_id)
    assert download_path == output_file.resolve()


def test_get_download_path_blocks_path_traversal(service):
    """Test that path traversal attempts are blocked."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Complete the job with path outside temp_dir (simulating DB manipulation)
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    job.output_path = "/etc/passwd"  # Attempted path traversal
    service._db.update_job(job)

    # Should return None due to path validation
    download_path = service.get_download_path(job.job_id)
    assert download_path is None


def test_get_download_path_blocks_relative_traversal(service, temp_dir):
    """Test that relative path traversal is blocked."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Complete the job with path using ../ to escape temp_dir
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    job.output_path = str(temp_dir / ".." / ".." / "etc" / "passwd")
    service._db.update_job(job)

    # Should return None due to path validation
    download_path = service.get_download_path(job.job_id)
    assert download_path is None


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
    # Patch Darwin Core functions to bypass real transformation logic
    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', return_value=['val1', 'val2']):
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
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Patch Darwin Core functions - make transform_to_csv_row raise an error
    with patch.object(service, '_collect_photos', return_value=[Path("/tmp/photo.jpg")]), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', side_effect=Exception("Export failed")):
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


# =============================================================================
# Date Filtering Tests
# =============================================================================


def test_date_filter_matches_in_range(service, photos_dir):
    """Photo date matches filter range."""
    # Create photo with known date in filename
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
        date_end="2024-06-30",
    )

    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_before_start(service, photos_dir):
    """Photo date before start date."""
    photo = photos_dir / "moth_2024_05_15__10_00_00.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
    )

    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_after_end(service, photos_dir):
    """Photo date after end date."""
    photo = photos_dir / "moth_2024_07_15__10_00_00.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(
        date_end="2024-06-30",
    )

    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_start_only(service, photos_dir):
    """Filter with only date_start."""
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    # Photo after start date
    filter_obj = ExportJobFilter(date_start="2024-06-01")
    assert service._matches_filter(photo, filter_obj) is True

    # Photo before start date
    filter_obj = ExportJobFilter(date_start="2024-07-01")
    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_end_only(service, photos_dir):
    """Filter with only date_end."""
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    # Photo before end date
    filter_obj = ExportJobFilter(date_end="2024-06-30")
    assert service._matches_filter(photo, filter_obj) is True

    # Photo after end date
    filter_obj = ExportJobFilter(date_end="2024-05-31")
    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_inclusive_start(service, photos_dir):
    """Filter is inclusive on start date."""
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    # Start date == photo date
    filter_obj = ExportJobFilter(date_start="2024-06-15")
    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_inclusive_end(service, photos_dir):
    """Filter is inclusive on end date."""
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    # End date == photo date
    filter_obj = ExportJobFilter(date_end="2024-06-15")
    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_hdr_filename(service, photos_dir):
    """HDR filename pattern works."""
    photo = photos_dir / "moth_2024_06_15__10_00_00_HDR0.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
        date_end="2024-06-30",
    )

    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_focus_bracket_filename(service, photos_dir):
    """Focus bracket filename pattern works."""
    photo = photos_dir / "ManFocus_moth_2024_06_15__10_00_00_FB0.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
        date_end="2024-06-30",
    )

    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_no_timestamp_mtime_fallback(service, photos_dir):
    """Photo without timestamp in filename uses mtime fallback."""
    from datetime import date

    photo = photos_dir / "unknown_photo.jpg"
    photo.write_text("test")

    # File was just created, so mtime should be today
    today = date.today()

    filter_obj = ExportJobFilter(
        date_start=today.isoformat(),
        date_end=today.isoformat(),
    )

    assert service._matches_filter(photo, filter_obj) is True


def test_date_filter_nonexistent_file(service, photos_dir):
    """Nonexistent file returns False (can't determine date)."""
    photo = photos_dir / "nonexistent.jpg"

    filter_obj = ExportJobFilter(date_start="2024-06-01")

    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_combined_with_deployment(service, photos_dir):
    """Date filter combines with deployment filter."""
    subdir = photos_dir / "deployment_2024"
    subdir.mkdir()
    photo = subdir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    # Both filters pass
    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
        deployment="deployment_2024",
    )
    assert service._matches_filter(photo, filter_obj) is True

    # Date passes, deployment fails
    filter_obj = ExportJobFilter(
        date_start="2024-06-01",
        deployment="other_deployment",
    )
    assert service._matches_filter(photo, filter_obj) is False

    # Date fails, deployment passes
    filter_obj = ExportJobFilter(
        date_start="2024-07-01",
        deployment="deployment_2024",
    )
    assert service._matches_filter(photo, filter_obj) is False


def test_date_filter_no_filter_passes(service, photos_dir):
    """No date filter passes all photos."""
    photo = photos_dir / "moth_2024_06_15__10_00_00.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter()
    assert service._matches_filter(photo, filter_obj) is True


# =============================================================================
# Deployment Filtering Tests
# =============================================================================


def test_deployment_filter_exact_match(service, photos_dir):
    """Deployment filter matches exact directory name."""
    subdir = photos_dir / "forest_2024"
    subdir.mkdir()
    photo = subdir / "photo.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(deployment="forest_2024")
    assert service._matches_filter(photo, filter_obj) is True


def test_deployment_filter_no_partial_match(service, photos_dir):
    """Deployment filter does NOT match partial directory names."""
    # This tests the bug fix: forest_2024_backup should NOT match forest_2024
    subdir = photos_dir / "forest_2024_backup"
    subdir.mkdir()
    photo = subdir / "photo.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(deployment="forest_2024")
    assert service._matches_filter(photo, filter_obj) is False


def test_deployment_filter_no_prefix_match(service, photos_dir):
    """Deployment filter does NOT match prefix of directory name."""
    # old_forest_2024 should NOT match forest_2024
    subdir = photos_dir / "old_forest_2024"
    subdir.mkdir()
    photo = subdir / "photo.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(deployment="forest_2024")
    assert service._matches_filter(photo, filter_obj) is False


def test_deployment_filter_nested_photo(service, photos_dir):
    """Photo in nested subdirectory of deployment still matches."""
    deployment = photos_dir / "forest_2024"
    nested = deployment / "site_A" / "batch_1"
    nested.mkdir(parents=True)
    photo = nested / "photo.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(deployment="forest_2024")
    assert service._matches_filter(photo, filter_obj) is True


def test_deployment_filter_full_path(service, photos_dir):
    """Deployment filter with absolute path works."""
    subdir = photos_dir / "forest_2024"
    subdir.mkdir()
    photo = subdir / "photo.jpg"
    photo.write_text("test")

    filter_obj = ExportJobFilter(deployment=str(subdir))
    assert service._matches_filter(photo, filter_obj) is True


def test_deployment_filter_full_path_no_match(service, photos_dir):
    """Deployment filter with wrong absolute path fails."""
    subdir = photos_dir / "forest_2024"
    subdir.mkdir()
    photo = subdir / "photo.jpg"
    photo.write_text("test")

    wrong_path = photos_dir / "other_deployment"
    filter_obj = ExportJobFilter(deployment=str(wrong_path))
    assert service._matches_filter(photo, filter_obj) is False


def test_deployment_filter_similar_names(service, photos_dir):
    """Deployment filter distinguishes between similar directory names."""
    # Create directories with similar names
    dir1 = photos_dir / "survey"
    dir2 = photos_dir / "survey_v2"
    dir3 = photos_dir / "pre_survey"
    for d in [dir1, dir2, dir3]:
        d.mkdir()
        (d / "photo.jpg").write_text("test")

    # Only exact match should work
    filter_obj = ExportJobFilter(deployment="survey")

    assert service._matches_filter(dir1 / "photo.jpg", filter_obj) is True
    assert service._matches_filter(dir2 / "photo.jpg", filter_obj) is False
    assert service._matches_filter(dir3 / "photo.jpg", filter_obj) is False
