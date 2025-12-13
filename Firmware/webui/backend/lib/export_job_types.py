"""
Export job type definitions for async export system.

This module defines the data structures used throughout the export job queue system:
- ExportJobStatus: Job lifecycle states
- ExportJobFormat: Supported export formats
- ExportJobFilter: Photo selection criteria
- ExportJobProgress: Progress tracking
- ExportJob: Complete job instance with metadata

All dataclasses provide to_dict()/from_dict() methods for serialization to JSON/SQLite.

Author: Mothbox Team
Date: 2024
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from webui.backend.lib.series_detection import SeriesType


class ExportJobStatus(Enum):
    """
    Export job lifecycle states.

    States:
        PENDING: Job created, waiting to start
        RUNNING: Job currently executing
        COMPLETED: Job finished successfully
        FAILED: Job encountered error and stopped
        CANCELLED: Job cancelled by user
        EXPIRED: Job output files expired and were cleaned up
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExportJobFormat(Enum):
    """
    Supported async export formats.

    Formats:
        DARWIN_CORE: Darwin Core Archive (DwC-A) for biodiversity data
        INATURALIST: iNaturalist CSV format
        JSON: Generic JSON export with photo metadata
        CSV: Generic CSV export with photo metadata
    """

    DARWIN_CORE = "darwin_core"
    INATURALIST = "inaturalist"
    JSON = "json"
    CSV = "csv"


@dataclass
class ExportJobFilter:
    """
    Filter criteria for selecting photos to export.

    Filters can be combined (AND logic). If photo_paths is provided,
    it takes precedence over other filters.

    Attributes:
        date_start: Start date (ISO 8601 format: YYYY-MM-DD)
        date_end: End date (ISO 8601 format: YYYY-MM-DD)
        deployment: Deployment directory path
        tags: List of tags to match (any tag matches)
        series_type: Series type filter ("hdr" or "focus_bracket")
        has_species: Only include photos with species identification
        photo_paths: Explicit list of photo paths (overrides other filters)
    """

    date_start: str | None = None
    date_end: str | None = None
    deployment: str | None = None
    tags: list[str] | None = None
    series_type: SeriesType | str | None = None
    has_species: bool | None = None
    photo_paths: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize filter to dictionary.

        Returns:
            Dictionary with all filter fields
        """
        return {
            "date_start": self.date_start,
            "date_end": self.date_end,
            "deployment": self.deployment,
            "tags": self.tags,
            "series_type": self.series_type.value if isinstance(self.series_type, SeriesType) else self.series_type,
            "has_species": self.has_species,
            "photo_paths": self.photo_paths,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportJobFilter:
        """
        Deserialize filter from dictionary.

        Args:
            data: Dictionary with filter fields

        Returns:
            ExportJobFilter instance
        """
        # Parse series_type to enum if valid
        series_type_val = data.get("series_type")
        if series_type_val is not None:
            with contextlib.suppress(ValueError):
                series_type_val = SeriesType(series_type_val)

        return cls(
            date_start=data.get("date_start"),
            date_end=data.get("date_end"),
            deployment=data.get("deployment"),
            tags=data.get("tags"),
            series_type=series_type_val,
            has_species=data.get("has_species"),
            photo_paths=data.get("photo_paths"),
        )


@dataclass
class ExportJobProgress:
    """
    Progress tracking for export jobs.

    Attributes:
        current: Number of items processed so far
        total: Total number of items to process
        percent: Completion percentage (0-100)
        phase: Current processing phase (initializing, collecting, exporting, finalizing)
    """

    current: int = 0
    total: int = 0
    percent: int = 0
    phase: str = "initializing"

    def calculate_percent(self) -> int:
        """
        Calculate completion percentage from current/total.

        Returns:
            Percentage as integer (0-100), or 0 if total is 0
        """
        if self.total == 0:
            return 0
        return round((self.current / self.total) * 100)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize progress to dictionary.

        Returns:
            Dictionary with all progress fields
        """
        return {
            "current": self.current,
            "total": self.total,
            "percent": self.percent,
            "phase": self.phase,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportJobProgress:
        """
        Deserialize progress from dictionary.

        Args:
            data: Dictionary with progress fields

        Returns:
            ExportJobProgress instance
        """
        return cls(
            current=data.get("current", 0),
            total=data.get("total", 0),
            percent=data.get("percent", 0),
            phase=data.get("phase", "initializing"),
        )


@dataclass
class ExportError:
    """
    Individual error during export operation.

    Attributes:
        error: Human-readable error message
        photo_path: Path to photo that caused error (if applicable)
        error_type: Error category ("permission", "io", "unknown")
        timestamp: Unix timestamp when error occurred
    """

    error: str
    photo_path: str | None = None
    error_type: str | None = None
    timestamp: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize error to dictionary.

        Returns:
            Dictionary with all error fields
        """
        return {
            "error": self.error,
            "photo_path": self.photo_path,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportError:
        """
        Deserialize error from dictionary.

        Handles legacy keys for backward compatibility:
        - "photo" -> photo_path
        - "filename" -> photo_path

        Args:
            data: Dictionary with error fields

        Returns:
            ExportError instance
        """
        # Handle legacy "photo" and "filename" keys
        photo_path = data.get("photo_path") or data.get("photo") or data.get("filename")
        return cls(
            error=data.get("error", "Unknown error"),
            photo_path=photo_path,
            error_type=data.get("error_type"),
            timestamp=data.get("timestamp"),
        )


@dataclass
class ExportJob:
    """
    Export job instance with complete metadata.

    Represents a single export job through its entire lifecycle from creation
    to completion or failure. Includes filter criteria, progress tracking,
    timestamps, and results.

    Attributes:
        job_id: Unique job identifier
        status: Current job status
        format: Export format
        filter: Photo selection criteria
        progress: Progress tracking information

        created_at: Job creation timestamp (Unix timestamp)
        started_at: Job start timestamp (Unix timestamp)
        completed_at: Job completion timestamp (Unix timestamp)
        expires_at: Expiration timestamp for output file (Unix timestamp)

        output_path: Path to output file (once generated)
        output_size_bytes: Size of output file in bytes
        photo_count: Number of photos included in export
        error_message: High-level error message if job failed
        errors: List of per-photo errors with details

        options: Format-specific export options (dict)
    """

    job_id: str
    status: ExportJobStatus
    format: ExportJobFormat
    filter: ExportJobFilter
    progress: ExportJobProgress

    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    expires_at: float | None = None

    output_path: str | None = None
    output_size_bytes: int = 0
    photo_count: int = 0
    error_message: str | None = None
    errors: list[ExportError] = field(default_factory=list)

    options: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize job to dictionary.

        Converts enums to string values and nested objects to dicts.
        Suitable for JSON serialization or SQLite storage.

        Returns:
            Dictionary with all job fields
        """
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "format": self.format.value,
            "filter": self.filter.to_dict(),
            "progress": self.progress.to_dict(),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "expires_at": self.expires_at,
            "output_path": self.output_path,
            "output_size_bytes": self.output_size_bytes,
            "photo_count": self.photo_count,
            "error_message": self.error_message,
            "errors": [e.to_dict() for e in self.errors],
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportJob:
        """
        Deserialize job from dictionary.

        Converts string values back to enums and nested dicts to objects.

        Args:
            data: Dictionary with job fields

        Returns:
            ExportJob instance

        Raises:
            ValueError: If status or format strings are invalid
        """
        # Convert string status to enum
        try:
            status = ExportJobStatus(data["status"])
        except ValueError as e:
            raise ValueError(f"Invalid status value: {data['status']}") from e

        # Convert string format to enum
        try:
            fmt = ExportJobFormat(data["format"])
        except ValueError as e:
            raise ValueError(f"Invalid format value: {data['format']}") from e

        # Deserialize nested objects
        filter_data = data.get("filter", {})
        filter_obj = ExportJobFilter.from_dict(filter_data)

        progress_data = data.get("progress", {})
        progress_obj = ExportJobProgress.from_dict(progress_data)

        return cls(
            job_id=data["job_id"],
            status=status,
            format=fmt,
            filter=filter_obj,
            progress=progress_obj,
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            expires_at=data.get("expires_at"),
            output_path=data.get("output_path"),
            output_size_bytes=data.get("output_size_bytes", 0),
            photo_count=data.get("photo_count", 0),
            error_message=data.get("error_message"),
            errors=[ExportError.from_dict(e) for e in data.get("errors", [])],
            options=data.get("options", {}),
        )
