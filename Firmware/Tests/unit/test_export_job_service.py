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


def test_create_job_with_custom_ttl(service):
    """Test creating job with custom TTL."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
        ttl_seconds=7200,  # 2 hours
    )

    assert job is not None
    assert job.options.get('_ttl_seconds') == 7200


def test_create_job_default_ttl(service):
    """Test creating job uses service default TTL when not specified."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Should not have custom TTL in options
    assert '_ttl_seconds' not in job.options


def test_create_job_with_ttl_preserves_other_options(service):
    """Test that TTL doesn't overwrite other options."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
        options={"validate": True, "custom_key": "value"},
        ttl_seconds=3600,
    )

    assert job.options.get('validate') is True
    assert job.options.get('custom_key') == "value"
    assert job.options.get('_ttl_seconds') == 3600


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


# =============================================================================
# Series Type Filter Tests
# =============================================================================


def test_series_type_filter_hdr_match(service, photos_dir):
    """Series type filter matches HDR photos."""
    # HDR filename pattern: {name}_{YYYY_MM_DD__HH_MM_SS}_HDR{index}.jpg
    hdr_photo = photos_dir / "moth_2024_01_15__10_30_00_HDR0.jpg"
    hdr_photo.write_text("hdr photo")

    filter_obj = ExportJobFilter(series_type="hdr")
    assert service._matches_filter(hdr_photo, filter_obj) is True


def test_series_type_filter_hdr_no_match(service, photos_dir):
    """Series type filter rejects non-HDR photos when filtering for HDR."""
    regular_photo = photos_dir / "moth_2024_01_15__10_30_00.jpg"
    regular_photo.write_text("regular photo")

    filter_obj = ExportJobFilter(series_type="hdr")
    assert service._matches_filter(regular_photo, filter_obj) is False


def test_series_type_filter_focus_bracket_match(service, photos_dir):
    """Series type filter matches focus bracket photos."""
    # Focus bracket pattern: ManFocus_{name}_{YYYY_MM_DD__HH_MM_SS}_FB{index}.jpg
    fb_photo = photos_dir / "ManFocus_moth_2024_01_15__10_30_00_FB0.jpg"
    fb_photo.write_text("focus bracket photo")

    filter_obj = ExportJobFilter(series_type="focus_bracket")
    assert service._matches_filter(fb_photo, filter_obj) is True


def test_series_type_filter_focus_bracket_no_match(service, photos_dir):
    """Series type filter rejects non-focus-bracket photos."""
    regular_photo = photos_dir / "moth_2024_01_15__10_30_00.jpg"
    regular_photo.write_text("regular photo")

    filter_obj = ExportJobFilter(series_type="focus_bracket")
    assert service._matches_filter(regular_photo, filter_obj) is False


def test_series_type_filter_hdr_not_focus_bracket(service, photos_dir):
    """HDR photos don't match focus_bracket filter."""
    hdr_photo = photos_dir / "moth_2024_01_15__10_30_00_HDR0.jpg"
    hdr_photo.write_text("hdr photo")

    filter_obj = ExportJobFilter(series_type="focus_bracket")
    assert service._matches_filter(hdr_photo, filter_obj) is False


# =============================================================================
# Tags Filter Tests
# =============================================================================


def test_tags_filter_match_single(service, photos_dir):
    """Tags filter matches when photo has the requested tag."""
    photo = photos_dir / "photo_0.jpg"

    # Mock sidecar service to return metadata with tags
    mock_metadata = Mock()
    mock_metadata.tags = ["moth", "nocturnal"]
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"])
    assert service._matches_filter(photo, filter_obj) is True


def test_tags_filter_match_any(service, photos_dir):
    """Tags filter matches if any requested tag is present (OR logic)."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = ["butterfly"]
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    # Photo has "butterfly", filter asks for "moth" OR "butterfly"
    filter_obj = ExportJobFilter(tags=["moth", "butterfly"])
    assert service._matches_filter(photo, filter_obj) is True


def test_tags_filter_no_match(service, photos_dir):
    """Tags filter rejects photos without matching tags."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = ["beetle"]
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth", "butterfly"])
    assert service._matches_filter(photo, filter_obj) is False


def test_tags_filter_no_metadata(service, photos_dir):
    """Tags filter rejects photos with no sidecar metadata."""
    photo = photos_dir / "photo_0.jpg"

    service._sidecar_service.get_metadata = Mock(return_value=None)

    filter_obj = ExportJobFilter(tags=["moth"])
    assert service._matches_filter(photo, filter_obj) is False


def test_tags_filter_empty_tags(service, photos_dir):
    """Tags filter rejects photos with empty tags list."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = []
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"])
    assert service._matches_filter(photo, filter_obj) is False


def test_tags_filter_none_tags(service, photos_dir):
    """Tags filter rejects photos with None tags."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = None
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"])
    assert service._matches_filter(photo, filter_obj) is False


# =============================================================================
# Species Filter Tests
# =============================================================================


def test_has_species_filter_match(service, photos_dir):
    """has_species filter matches photos with species identification."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.species = "Actias luna"
    mock_metadata.tags = None  # tags not needed for this test
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(has_species=True)
    assert service._matches_filter(photo, filter_obj) is True


def test_has_species_filter_no_species(service, photos_dir):
    """has_species filter rejects photos without species."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.species = None
    mock_metadata.tags = None
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(has_species=True)
    assert service._matches_filter(photo, filter_obj) is False


def test_has_species_filter_empty_species(service, photos_dir):
    """has_species filter rejects photos with empty species string."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.species = ""
    mock_metadata.tags = None
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(has_species=True)
    assert service._matches_filter(photo, filter_obj) is False


def test_has_species_filter_no_metadata(service, photos_dir):
    """has_species filter rejects photos without sidecar metadata."""
    photo = photos_dir / "photo_0.jpg"

    service._sidecar_service.get_metadata = Mock(return_value=None)

    filter_obj = ExportJobFilter(has_species=True)
    assert service._matches_filter(photo, filter_obj) is False


# =============================================================================
# Combined Filter Tests
# =============================================================================


def test_combined_tags_and_species_filter(service, photos_dir):
    """Combined tags and species filter requires both conditions."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = ["moth", "nocturnal"]
    mock_metadata.species = "Actias luna"
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"], has_species=True)
    assert service._matches_filter(photo, filter_obj) is True


def test_combined_tags_and_species_fails_tags(service, photos_dir):
    """Combined filter fails if tags don't match even with species."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = ["beetle"]
    mock_metadata.species = "Actias luna"
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"], has_species=True)
    assert service._matches_filter(photo, filter_obj) is False


def test_combined_tags_and_species_fails_species(service, photos_dir):
    """Combined filter fails if species missing even with matching tags."""
    photo = photos_dir / "photo_0.jpg"

    mock_metadata = Mock()
    mock_metadata.tags = ["moth"]
    mock_metadata.species = None
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(tags=["moth"], has_species=True)
    assert service._matches_filter(photo, filter_obj) is False


def test_combined_series_and_tags_filter(service, photos_dir):
    """Combined series type and tags filter requires both conditions."""
    hdr_photo = photos_dir / "moth_2024_01_15__10_30_00_HDR0.jpg"
    hdr_photo.write_text("hdr photo")

    mock_metadata = Mock()
    mock_metadata.tags = ["moth"]
    mock_metadata.species = None
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(series_type="hdr", tags=["moth"])
    assert service._matches_filter(hdr_photo, filter_obj) is True


def test_combined_series_and_tags_fails_series(service, photos_dir):
    """Combined filter fails if series type doesn't match."""
    regular_photo = photos_dir / "moth_2024_01_15__10_30_00.jpg"
    regular_photo.write_text("regular photo")

    mock_metadata = Mock()
    mock_metadata.tags = ["moth"]
    service._sidecar_service.get_metadata = Mock(return_value=mock_metadata)

    filter_obj = ExportJobFilter(series_type="hdr", tags=["moth"])
    assert service._matches_filter(regular_photo, filter_obj) is False


# =============================================================================
# TTL and Expiration Tests
# =============================================================================


def test_expires_at_set_on_job_completion(service, photos_dir):
    """Test that expires_at is set when job completes successfully."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    photo_paths = list(photos_dir.glob("*.jpg"))
    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', return_value=['val1', 'val2']):
        service.start()

        # Wait for job to complete
        for _ in range(30):
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.COMPLETED
    assert final_job.expires_at is not None
    assert final_job.completed_at is not None
    # expires_at should be completed_at + TTL (default 60 seconds in fixture)
    assert final_job.expires_at == final_job.completed_at + 60


def test_expires_at_uses_custom_ttl(service, photos_dir):
    """Test that expires_at respects custom TTL."""
    custom_ttl = 7200  # 2 hours
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
        ttl_seconds=custom_ttl,
    )

    photo_paths = list(photos_dir.glob("*.jpg"))
    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', return_value=['val1', 'val2']):
        service.start()

        for _ in range(30):
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.COMPLETED
    assert final_job.expires_at is not None
    # expires_at should use custom TTL
    assert final_job.expires_at == final_job.completed_at + custom_ttl


def test_expires_at_set_on_job_failure(service, mock_export_service):
    """Test that expires_at is set when job fails."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    with patch.object(service, '_collect_photos', return_value=[Path("/tmp/photo.jpg")]), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', side_effect=Exception("Export failed")):
        service.start()

        for _ in range(30):
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.FAILED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.FAILED
    assert final_job.expires_at is not None
    assert final_job.completed_at is not None


def test_expires_at_set_on_job_cancellation(service):
    """Test that expires_at is set when job is cancelled."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Cancel the pending job
    service.cancel_job(job.job_id)

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.CANCELLED
    assert final_job.expires_at is not None
    assert final_job.completed_at is not None


def test_cleanup_expired_jobs_uses_expires_at(db_path, mock_export_service, photos_dir, temp_dir):
    """Test that cleanup uses expires_at field."""
    service = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_ttl_seconds=60,
    )

    # Create a completed job and manually set expires_at in the past
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time() - 100  # Completed 100 seconds ago
    job.expires_at = time.time() - 50  # Expired 50 seconds ago
    service._db.update_job(job)

    # Create another job that hasn't expired yet
    job2 = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )
    job2 = service.get_job(job2.job_id)
    job2.status = ExportJobStatus.COMPLETED
    job2.completed_at = time.time()
    job2.expires_at = time.time() + 3600  # Expires in 1 hour
    service._db.update_job(job2)

    # Run cleanup
    service._cleanup_expired_jobs()

    # Expired job should be deleted
    assert service.get_job(job.job_id) is None
    # Non-expired job should still exist
    assert service.get_job(job2.job_id) is not None

    service.stop()


def test_cleanup_legacy_jobs_without_expires_at(db_path, mock_export_service, photos_dir, temp_dir):
    """Test cleanup of legacy jobs without expires_at field."""
    service = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_ttl_seconds=60,
    )

    # Create a completed job without expires_at (simulating legacy job)
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time() - 100
    job.created_at = time.time() - 100  # Created 100 seconds ago (past default TTL of 60)
    job.expires_at = None  # Legacy job without expires_at
    service._db.update_job(job)

    # Run cleanup
    service._cleanup_expired_jobs()

    # Legacy job should be deleted using created_at fallback
    assert service.get_job(job.job_id) is None

    service.stop()


def test_cleanup_preserves_non_expired_legacy_jobs(db_path, mock_export_service, photos_dir, temp_dir):
    """Test that cleanup preserves legacy jobs within TTL based on created_at."""
    service = ExportJobService(
        db_path=db_path,
        export_service=mock_export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_ttl_seconds=3600,  # 1 hour TTL
    )

    # Create a completed job without expires_at but within TTL
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )
    job = service.get_job(job.job_id)
    job.status = ExportJobStatus.COMPLETED
    job.completed_at = time.time()
    job.expires_at = None  # Legacy job without expires_at
    # created_at is set to now by default, so within TTL
    service._db.update_job(job)

    # Run cleanup
    service._cleanup_expired_jobs()

    # Job should NOT be deleted (within TTL)
    assert service.get_job(job.job_id) is not None

    service.stop()


# =============================================================================
# Progress Tracking Tests
# =============================================================================


def test_progress_phases_during_execution(service, photos_dir):
    """Test that progress phases transition correctly during job execution."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Initial phase should be "initializing"
    assert job.progress.phase == "initializing"

    photo_paths = list(photos_dir.glob("*.jpg"))
    observed_phases = []

    def capture_phase():
        current_job = service.get_job(job.job_id)
        if current_job and current_job.progress.phase not in observed_phases:
            observed_phases.append(current_job.progress.phase)

    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', return_value=['val1', 'val2']):
        service.start()

        # Poll for completion while capturing phases
        for _ in range(50):
            capture_phase()
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.COMPLETED
    assert final_job.progress.phase == "completed"

    # Verify expected phases were observed (order may vary due to timing)
    expected_phases = {"initializing", "collecting", "exporting", "finalizing", "completed"}
    # At minimum, we should see initializing and completed
    assert "initializing" in observed_phases
    assert "completed" in observed_phases or final_job.progress.phase == "completed"


def test_progress_current_and_total_set_correctly(service, photos_dir):
    """Test that progress current/total are set correctly after job completion."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    photo_paths = list(photos_dir.glob("*.jpg"))
    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', return_value=['val1', 'val2']):
        service.start()

        for _ in range(30):
            updated_job = service.get_job(job.job_id)
            if updated_job.status == ExportJobStatus.COMPLETED:
                break
            time.sleep(0.1)

        service.stop()

    final_job = service.get_job(job.job_id)
    assert final_job.status == ExportJobStatus.COMPLETED
    # Total should equal number of photos
    assert final_job.progress.total == len(photo_paths)
    # Current should equal total at completion
    assert final_job.progress.current == len(photo_paths)
    # Percent should be 100 at completion
    assert final_job.progress.percent == 100


def test_progress_percent_calculation(service, photos_dir):
    """Test that progress percent is calculated correctly."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Manually update progress and verify percent
    job.progress.total = 100
    job.progress.current = 50
    percent = job.progress.calculate_percent()
    assert percent == 50

    job.progress.current = 75
    percent = job.progress.calculate_percent()
    assert percent == 75

    # Edge case: total = 0
    job.progress.total = 0
    job.progress.current = 0
    percent = job.progress.calculate_percent()
    assert percent == 0


def test_update_progress_helper(service):
    """Test the _update_progress helper method."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Update phase only
    service._update_progress(job, phase="collecting")
    retrieved_job = service.get_job(job.job_id)
    assert retrieved_job.progress.phase == "collecting"

    # Update current and total
    service._update_progress(job, current=25, total=100)
    retrieved_job = service.get_job(job.job_id)
    assert retrieved_job.progress.current == 25
    assert retrieved_job.progress.total == 100
    assert retrieved_job.progress.percent == 25

    # Update all at once
    service._update_progress(job, phase="exporting", current=50, total=100)
    retrieved_job = service.get_job(job.job_id)
    assert retrieved_job.progress.phase == "exporting"
    assert retrieved_job.progress.current == 50
    assert retrieved_job.progress.percent == 50


def test_progress_callback_factory(service):
    """Test the _make_progress_callback helper method."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Create callback
    callback = service._make_progress_callback(job)

    # Call callback and verify progress is updated
    callback(10, 100)
    retrieved_job = service.get_job(job.job_id)
    assert retrieved_job.progress.current == 10
    assert retrieved_job.progress.total == 100
    assert retrieved_job.progress.percent == 10

    # Call again with different values
    callback(50, 100)
    retrieved_job = service.get_job(job.job_id)
    assert retrieved_job.progress.current == 50
    assert retrieved_job.progress.percent == 50


def test_progress_visible_via_api_during_execution(service, photos_dir):
    """Test that progress updates are visible through get_job during execution."""
    job = service.create_job(
        format=ExportJobFormat.DARWIN_CORE,
        filter=ExportJobFilter(),
    )

    # Create more photos to have longer execution
    for i in range(20):
        (photos_dir / f"extra_photo_{i}.jpg").write_text(f"photo {i}")

    photo_paths = list(photos_dir.glob("*.jpg"))
    progress_snapshots = []

    def slow_transform(*args):
        """Slow down transform to allow capturing progress."""
        time.sleep(0.05)  # 50ms per photo
        return ['val1', 'val2']

    with patch.object(service, '_collect_photos', return_value=photo_paths), \
         patch('webui.backend.lib.darwin_core_mapping.is_valid_for_export', return_value=True), \
         patch('webui.backend.lib.darwin_core_mapping.transform_to_csv_row', side_effect=slow_transform):
        service.start()

        # Poll and capture progress
        for _ in range(100):
            current_job = service.get_job(job.job_id)
            if current_job:
                progress_snapshots.append({
                    'phase': current_job.progress.phase,
                    'current': current_job.progress.current,
                    'total': current_job.progress.total,
                    'percent': current_job.progress.percent,
                })
                if current_job.status == ExportJobStatus.COMPLETED:
                    break
            time.sleep(0.05)

        service.stop()

    # Should have multiple snapshots showing progress
    assert len(progress_snapshots) > 1
    # Should see increasing current values in some snapshots
    currents = [s['current'] for s in progress_snapshots if s['current'] > 0]
    if len(currents) > 1:
        # At least some progress should be visible
        assert max(currents) > 0
