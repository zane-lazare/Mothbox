"""
Unit tests for export job type definitions.

Tests data structures used in the export job queue system:
- ExportJobStatus enum
- ExportJobFormat enum
- ExportJobFilter dataclass
- ExportJobProgress dataclass
- ExportJob dataclass

Coverage target: 100%
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from webui.backend.lib.export_job_types import (
    ExportJob,
    ExportJobFilter,
    ExportJobFormat,
    ExportJobProgress,
    ExportJobStatus,
)


class TestExportJobStatusEnum:
    """Test ExportJobStatus enum."""

    def test_enum_values(self):
        """Test all enum values are accessible."""
        assert ExportJobStatus.PENDING.value == "pending"
        assert ExportJobStatus.RUNNING.value == "running"
        assert ExportJobStatus.COMPLETED.value == "completed"
        assert ExportJobStatus.FAILED.value == "failed"
        assert ExportJobStatus.CANCELLED.value == "cancelled"
        assert ExportJobStatus.EXPIRED.value == "expired"

    def test_enum_string_conversion(self):
        """Test enum to string conversion."""
        assert str(ExportJobStatus.PENDING.value) == "pending"
        assert str(ExportJobStatus.RUNNING.value) == "running"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        status1 = ExportJobStatus.PENDING
        status2 = ExportJobStatus.PENDING
        assert status1 == status2
        assert status1 != ExportJobStatus.RUNNING

    def test_enum_membership(self):
        """Test enum membership."""
        assert ExportJobStatus.PENDING in ExportJobStatus
        # Note: String value membership behavior varies by Python version
        # In 3.12+, "pending" in ExportJobStatus returns False
        # In 3.11, it raises TypeError
        # We test that enum members work correctly


class TestExportJobFormatEnum:
    """Test ExportJobFormat enum."""

    def test_enum_values(self):
        """Test all enum values are accessible."""
        assert ExportJobFormat.DARWIN_CORE.value == "darwin_core"
        assert ExportJobFormat.INATURALIST.value == "inaturalist"
        assert ExportJobFormat.JSON.value == "json"
        assert ExportJobFormat.CSV.value == "csv"

    def test_enum_string_conversion(self):
        """Test enum to string conversion."""
        assert str(ExportJobFormat.DARWIN_CORE.value) == "darwin_core"
        assert str(ExportJobFormat.JSON.value) == "json"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        fmt1 = ExportJobFormat.DARWIN_CORE
        fmt2 = ExportJobFormat.DARWIN_CORE
        assert fmt1 == fmt2
        assert fmt1 != ExportJobFormat.JSON


class TestExportJobFilter:
    """Test ExportJobFilter dataclass."""

    def test_instantiate_with_defaults(self):
        """Test creating filter with all defaults (None)."""
        filter_obj = ExportJobFilter()
        assert filter_obj.date_start is None
        assert filter_obj.date_end is None
        assert filter_obj.deployment is None
        assert filter_obj.tags is None
        assert filter_obj.series_type is None
        assert filter_obj.has_species is None
        assert filter_obj.photo_paths is None

    def test_instantiate_with_all_fields(self):
        """Test creating filter with all fields populated."""
        filter_obj = ExportJobFilter(
            date_start="2024-01-01",
            date_end="2024-12-31",
            deployment="/photos/forest_2024",
            tags=["moth", "lepidoptera"],
            series_type="hdr",
            has_species=True,
            photo_paths=["/photos/photo1.jpg", "/photos/photo2.jpg"],
        )
        assert filter_obj.date_start == "2024-01-01"
        assert filter_obj.date_end == "2024-12-31"
        assert filter_obj.deployment == "/photos/forest_2024"
        assert filter_obj.tags == ["moth", "lepidoptera"]
        assert filter_obj.series_type == "hdr"
        assert filter_obj.has_species is True
        assert filter_obj.photo_paths == ["/photos/photo1.jpg", "/photos/photo2.jpg"]

    def test_to_dict_with_defaults(self):
        """Test serialization with default values."""
        filter_obj = ExportJobFilter()
        data = filter_obj.to_dict()
        assert data == {
            "date_start": None,
            "date_end": None,
            "deployment": None,
            "tags": None,
            "series_type": None,
            "has_species": None,
            "photo_paths": None,
        }

    def test_to_dict_with_all_fields(self):
        """Test serialization with all fields populated."""
        filter_obj = ExportJobFilter(
            date_start="2024-01-01",
            date_end="2024-12-31",
            deployment="/photos/forest_2024",
            tags=["moth"],
            series_type="hdr",
            has_species=True,
            photo_paths=["/photos/photo1.jpg"],
        )
        data = filter_obj.to_dict()
        assert data["date_start"] == "2024-01-01"
        assert data["date_end"] == "2024-12-31"
        assert data["deployment"] == "/photos/forest_2024"
        assert data["tags"] == ["moth"]
        assert data["series_type"] == "hdr"
        assert data["has_species"] is True
        assert data["photo_paths"] == ["/photos/photo1.jpg"]

    def test_from_dict_with_defaults(self):
        """Test deserialization with default values."""
        data: dict[str, Any] = {
            "date_start": None,
            "date_end": None,
            "deployment": None,
            "tags": None,
            "series_type": None,
            "has_species": None,
            "photo_paths": None,
        }
        filter_obj = ExportJobFilter.from_dict(data)
        assert filter_obj.date_start is None
        assert filter_obj.date_end is None
        assert filter_obj.deployment is None
        assert filter_obj.tags is None
        assert filter_obj.series_type is None
        assert filter_obj.has_species is None
        assert filter_obj.photo_paths is None

    def test_from_dict_with_all_fields(self):
        """Test deserialization with all fields populated."""
        data = {
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "deployment": "/photos/forest_2024",
            "tags": ["moth", "butterfly"],
            "series_type": "focus_bracket",
            "has_species": False,
            "photo_paths": ["/photos/photo1.jpg", "/photos/photo2.jpg"],
        }
        filter_obj = ExportJobFilter.from_dict(data)
        assert filter_obj.date_start == "2024-01-01"
        assert filter_obj.date_end == "2024-12-31"
        assert filter_obj.deployment == "/photos/forest_2024"
        assert filter_obj.tags == ["moth", "butterfly"]
        assert filter_obj.series_type == "focus_bracket"
        assert filter_obj.has_species is False
        assert filter_obj.photo_paths == ["/photos/photo1.jpg", "/photos/photo2.jpg"]

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ExportJobFilter(
            date_start="2024-06-01",
            deployment="/photos/meadow_2024",
            tags=["moth", "nocturnal"],
            has_species=True,
        )
        data = original.to_dict()
        restored = ExportJobFilter.from_dict(data)
        assert restored.date_start == original.date_start
        assert restored.deployment == original.deployment
        assert restored.tags == original.tags
        assert restored.has_species == original.has_species

    def test_from_dict_with_empty_lists(self):
        """Test deserialization with empty lists."""
        data = {
            "tags": [],
            "photo_paths": [],
        }
        filter_obj = ExportJobFilter.from_dict(data)
        assert filter_obj.tags == []
        assert filter_obj.photo_paths == []


class TestExportJobProgress:
    """Test ExportJobProgress dataclass."""

    def test_instantiate_with_defaults(self):
        """Test creating progress with defaults."""
        progress = ExportJobProgress()
        assert progress.current == 0
        assert progress.total == 0
        assert progress.percent == 0
        assert progress.phase == "initializing"

    def test_instantiate_with_all_fields(self):
        """Test creating progress with all fields."""
        progress = ExportJobProgress(
            current=50,
            total=100,
            percent=50,
            phase="exporting",
        )
        assert progress.current == 50
        assert progress.total == 100
        assert progress.percent == 50
        assert progress.phase == "exporting"

    def test_calculate_percent_zero_total(self):
        """Test percent calculation when total is 0."""
        progress = ExportJobProgress(current=0, total=0)
        assert progress.calculate_percent() == 0

    def test_calculate_percent_zero_progress(self):
        """Test percent calculation at 0%."""
        progress = ExportJobProgress(current=0, total=100)
        assert progress.calculate_percent() == 0

    def test_calculate_percent_fifty_percent(self):
        """Test percent calculation at 50%."""
        progress = ExportJobProgress(current=50, total=100)
        assert progress.calculate_percent() == 50

    def test_calculate_percent_complete(self):
        """Test percent calculation at 100%."""
        progress = ExportJobProgress(current=100, total=100)
        assert progress.calculate_percent() == 100

    def test_calculate_percent_rounding(self):
        """Test percent calculation with rounding."""
        progress = ExportJobProgress(current=1, total=3)
        # 1/3 = 33.333... should round to 33
        assert progress.calculate_percent() == 33

    def test_calculate_percent_rounding_up(self):
        """Test percent calculation rounding up."""
        progress = ExportJobProgress(current=2, total=3)
        # 2/3 = 66.666... should round to 67
        assert progress.calculate_percent() == 67

    def test_to_dict(self):
        """Test serialization."""
        progress = ExportJobProgress(
            current=25,
            total=100,
            percent=25,
            phase="collecting",
        )
        data = progress.to_dict()
        assert data == {
            "current": 25,
            "total": 100,
            "percent": 25,
            "phase": "collecting",
        }

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "current": 75,
            "total": 100,
            "percent": 75,
            "phase": "finalizing",
        }
        progress = ExportJobProgress.from_dict(data)
        assert progress.current == 75
        assert progress.total == 100
        assert progress.percent == 75
        assert progress.phase == "finalizing"

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ExportJobProgress(current=42, total=100, percent=42, phase="exporting")
        data = original.to_dict()
        restored = ExportJobProgress.from_dict(data)
        assert restored.current == original.current
        assert restored.total == original.total
        assert restored.percent == original.percent
        assert restored.phase == original.phase


class TestExportJob:
    """Test ExportJob dataclass."""

    def test_instantiate_minimal(self):
        """Test creating job with minimal required fields."""
        now = time.time()
        job = ExportJob(
            job_id="test-job-123",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=now,
        )
        assert job.job_id == "test-job-123"
        assert job.status == ExportJobStatus.PENDING
        assert job.format == ExportJobFormat.DARWIN_CORE
        assert isinstance(job.filter, ExportJobFilter)
        assert isinstance(job.progress, ExportJobProgress)
        assert job.created_at == now
        assert job.started_at is None
        assert job.completed_at is None
        assert job.expires_at is None
        assert job.output_path is None
        assert job.output_size_bytes == 0
        assert job.photo_count == 0
        assert job.error_message is None
        assert job.errors == []
        assert job.options == {}

    def test_instantiate_with_all_fields(self):
        """Test creating job with all fields populated."""
        now = time.time()
        job = ExportJob(
            job_id="test-job-456",
            status=ExportJobStatus.COMPLETED,
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(deployment="/photos/forest_2024"),
            progress=ExportJobProgress(current=100, total=100, percent=100, phase="finalizing"),
            created_at=now,
            started_at=now + 1,
            completed_at=now + 10,
            expires_at=now + 3600,
            output_path="/tmp/exports/export-456.zip",
            output_size_bytes=1024000,
            photo_count=42,
            error_message=None,
            errors=[],
            options={"include_metadata": True},
        )
        assert job.job_id == "test-job-456"
        assert job.status == ExportJobStatus.COMPLETED
        assert job.format == ExportJobFormat.JSON
        assert job.filter.deployment == "/photos/forest_2024"
        assert job.progress.current == 100
        assert job.started_at == now + 1
        assert job.completed_at == now + 10
        assert job.expires_at == now + 3600
        assert job.output_path == "/tmp/exports/export-456.zip"
        assert job.output_size_bytes == 1024000
        assert job.photo_count == 42
        assert job.error_message is None
        assert job.errors == []
        assert job.options == {"include_metadata": True}

    def test_instantiate_failed_job(self):
        """Test creating a failed job with error details."""
        now = time.time()
        job = ExportJob(
            job_id="test-job-789",
            status=ExportJobStatus.FAILED,
            format=ExportJobFormat.CSV,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(current=25, total=100, phase="exporting"),
            created_at=now,
            started_at=now + 1,
            completed_at=now + 5,
            error_message="Failed to write CSV file",
            errors=[
                {"photo": "/photos/photo1.jpg", "error": "Permission denied"},
                {"photo": "/photos/photo2.jpg", "error": "File not found"},
            ],
        )
        assert job.status == ExportJobStatus.FAILED
        assert job.error_message == "Failed to write CSV file"
        assert len(job.errors) == 2
        assert job.errors[0]["photo"] == "/photos/photo1.jpg"

    def test_to_dict_minimal(self):
        """Test serialization with minimal fields."""
        now = time.time()
        job = ExportJob(
            job_id="test-job-123",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=now,
        )
        data = job.to_dict()
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "pending"
        assert data["format"] == "darwin_core"
        assert isinstance(data["filter"], dict)
        assert isinstance(data["progress"], dict)
        assert data["created_at"] == now
        assert data["started_at"] is None
        assert data["completed_at"] is None
        assert data["expires_at"] is None
        assert data["output_path"] is None
        assert data["output_size_bytes"] == 0
        assert data["photo_count"] == 0
        assert data["error_message"] is None
        assert data["errors"] == []
        assert data["options"] == {}

    def test_to_dict_with_all_fields(self):
        """Test serialization with all fields populated."""
        now = time.time()
        job = ExportJob(
            job_id="test-job-456",
            status=ExportJobStatus.RUNNING,
            format=ExportJobFormat.INATURALIST,
            filter=ExportJobFilter(tags=["moth"], has_species=True),
            progress=ExportJobProgress(current=50, total=100, percent=50, phase="exporting"),
            created_at=now,
            started_at=now + 1,
            expires_at=now + 7200,
            output_path="/tmp/exports/export-456.zip",
            output_size_bytes=512000,
            photo_count=25,
            options={"compression": "zip"},
        )
        data = job.to_dict()
        assert data["job_id"] == "test-job-456"
        assert data["status"] == "running"
        assert data["format"] == "inaturalist"
        assert data["filter"]["tags"] == ["moth"]
        assert data["filter"]["has_species"] is True
        assert data["progress"]["current"] == 50
        assert data["started_at"] == now + 1
        assert data["expires_at"] == now + 7200
        assert data["output_path"] == "/tmp/exports/export-456.zip"
        assert data["output_size_bytes"] == 512000
        assert data["photo_count"] == 25
        assert data["options"]["compression"] == "zip"

    def test_from_dict_minimal(self):
        """Test deserialization with minimal fields."""
        now = time.time()
        data = {
            "job_id": "test-job-123",
            "status": "pending",
            "format": "darwin_core",
            "filter": {},
            "progress": {},
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "expires_at": None,
            "output_path": None,
            "output_size_bytes": 0,
            "photo_count": 0,
            "error_message": None,
            "errors": [],
            "options": {},
        }
        job = ExportJob.from_dict(data)
        assert job.job_id == "test-job-123"
        assert job.status == ExportJobStatus.PENDING
        assert job.format == ExportJobFormat.DARWIN_CORE
        assert isinstance(job.filter, ExportJobFilter)
        assert isinstance(job.progress, ExportJobProgress)
        assert job.created_at == now
        assert job.started_at is None

    def test_from_dict_with_all_fields(self):
        """Test deserialization with all fields populated."""
        now = time.time()
        data = {
            "job_id": "test-job-789",
            "status": "completed",
            "format": "csv",
            "filter": {
                "date_start": "2024-01-01",
                "deployment": "/photos/forest_2024",
            },
            "progress": {
                "current": 100,
                "total": 100,
                "percent": 100,
                "phase": "finalizing",
            },
            "created_at": now,
            "started_at": now + 1,
            "completed_at": now + 20,
            "expires_at": now + 3600,
            "output_path": "/tmp/exports/export-789.zip",
            "output_size_bytes": 2048000,
            "photo_count": 100,
            "error_message": None,
            "errors": [],
            "options": {"format": "csv", "delimiter": ","},
        }
        job = ExportJob.from_dict(data)
        assert job.job_id == "test-job-789"
        assert job.status == ExportJobStatus.COMPLETED
        assert job.format == ExportJobFormat.CSV
        assert job.filter.date_start == "2024-01-01"
        assert job.filter.deployment == "/photos/forest_2024"
        assert job.progress.current == 100
        assert job.started_at == now + 1
        assert job.completed_at == now + 20
        assert job.expires_at == now + 3600
        assert job.output_path == "/tmp/exports/export-789.zip"
        assert job.output_size_bytes == 2048000
        assert job.photo_count == 100
        assert job.options["delimiter"] == ","

    def test_from_dict_failed_job(self):
        """Test deserialization of failed job with errors."""
        now = time.time()
        data = {
            "job_id": "test-job-fail",
            "status": "failed",
            "format": "json",
            "filter": {},
            "progress": {"current": 10, "total": 100, "percent": 10, "phase": "exporting"},
            "created_at": now,
            "started_at": now + 1,
            "completed_at": now + 5,
            "expires_at": None,
            "output_path": None,
            "output_size_bytes": 0,
            "photo_count": 0,
            "error_message": "Export process crashed",
            "errors": [
                {"photo": "/photos/photo1.jpg", "error": "Read timeout"},
            ],
            "options": {},
        }
        job = ExportJob.from_dict(data)
        assert job.status == ExportJobStatus.FAILED
        assert job.error_message == "Export process crashed"
        assert len(job.errors) == 1
        assert job.errors[0]["error"] == "Read timeout"

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves all data."""
        now = time.time()
        original = ExportJob(
            job_id="test-round-trip",
            status=ExportJobStatus.RUNNING,
            format=ExportJobFormat.DARWIN_CORE,
            filter=ExportJobFilter(
                date_start="2024-01-01",
                tags=["moth", "butterfly"],
                has_species=True,
            ),
            progress=ExportJobProgress(current=33, total=100, percent=33, phase="collecting"),
            created_at=now,
            started_at=now + 2,
            expires_at=now + 7200,
            photo_count=33,
            options={"include_deployment": True},
        )
        data = original.to_dict()
        restored = ExportJob.from_dict(data)

        assert restored.job_id == original.job_id
        assert restored.status == original.status
        assert restored.format == original.format
        assert restored.filter.date_start == original.filter.date_start
        assert restored.filter.tags == original.filter.tags
        assert restored.filter.has_species == original.filter.has_species
        assert restored.progress.current == original.progress.current
        assert restored.progress.total == original.progress.total
        assert restored.progress.percent == original.progress.percent
        assert restored.progress.phase == original.progress.phase
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.expires_at == original.expires_at
        assert restored.photo_count == original.photo_count
        assert restored.options == original.options

    def test_from_dict_with_invalid_status(self):
        """Test deserialization with invalid status value."""
        data = {
            "job_id": "test-invalid",
            "status": "invalid_status",
            "format": "json",
            "filter": {},
            "progress": {},
            "created_at": time.time(),
        }
        with pytest.raises(ValueError, match="invalid_status"):
            ExportJob.from_dict(data)

    def test_from_dict_with_invalid_format(self):
        """Test deserialization with invalid format value."""
        data = {
            "job_id": "test-invalid",
            "status": "pending",
            "format": "invalid_format",
            "filter": {},
            "progress": {},
            "created_at": time.time(),
        }
        with pytest.raises(ValueError, match="invalid_format"):
            ExportJob.from_dict(data)

    def test_nested_object_serialization(self):
        """Test that nested filter and progress objects are properly serialized."""
        now = time.time()
        job = ExportJob(
            job_id="test-nested",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(
                deployment="/photos/test",
                tags=["tag1", "tag2"],
            ),
            progress=ExportJobProgress(current=10, total=50, percent=20, phase="collecting"),
            created_at=now,
        )
        data = job.to_dict()

        # Verify filter is dict
        assert isinstance(data["filter"], dict)
        assert data["filter"]["deployment"] == "/photos/test"
        assert data["filter"]["tags"] == ["tag1", "tag2"]

        # Verify progress is dict
        assert isinstance(data["progress"], dict)
        assert data["progress"]["current"] == 10
        assert data["progress"]["total"] == 50

    def test_empty_errors_list(self):
        """Test that errors list defaults to empty list, not None."""
        job = ExportJob(
            job_id="test-errors",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )
        assert job.errors == []
        assert isinstance(job.errors, list)

    def test_empty_options_dict(self):
        """Test that options dict defaults to empty dict, not None."""
        job = ExportJob(
            job_id="test-options",
            status=ExportJobStatus.PENDING,
            format=ExportJobFormat.JSON,
            filter=ExportJobFilter(),
            progress=ExportJobProgress(),
            created_at=time.time(),
        )
        assert job.options == {}
        assert isinstance(job.options, dict)
