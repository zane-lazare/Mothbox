"""
Photo service for gallery pagination and filtering

Provides efficient photo listing with pagination, sorting, and filtering support.
"""

from datetime import datetime
from pathlib import Path

from webui.backend.constants import PHOTO_PATTERNS

from mothbox_paths import PHOTOS_DIR


class PaginationError(Exception):
    """Raised when pagination parameters are invalid"""



class PhotoService:
    """
    Service for managing photo listing and pagination

    Handles:
    - Efficient photo listing from PHOTOS_DIR
    - Pagination (limit/offset)
    - Sorting (date_desc, date_asc, filename_asc, filename_desc)
    - Date range filtering (start_date, end_date)
    """

    # Valid sort options
    VALID_SORT_OPTIONS = ['date_desc', 'date_asc', 'filename_asc', 'filename_desc']

    # Pagination limits
    MIN_LIMIT = 1
    MAX_LIMIT = 500
    DEFAULT_LIMIT = 50
    DEFAULT_OFFSET = 0

    def __init__(self, photos_dir: Path | None = None):
        """
        Initialize photo service

        Args:
            photos_dir: Directory containing photos (defaults to PHOTOS_DIR)
        """
        self.photos_dir = photos_dir or PHOTOS_DIR

    def list_photos(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = DEFAULT_OFFSET,
        sort: str = 'date_desc',
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """
        List photos with pagination, sorting, and filtering

        Args:
            limit: Maximum number of photos to return (1-500)
            offset: Number of photos to skip (>=0)
            sort: Sort order (date_desc, date_asc, filename_asc, filename_desc)
            start_date: Filter photos on or after this date
            end_date: Filter photos on or before this date

        Returns:
            Dictionary with 'photos' list and 'pagination' metadata:
            {
                "photos": [
                    {
                        "path": "relative/path.jpg",
                        "filename": "photo.jpg",
                        "size": 12345,
                        "timestamp": 1234567890.0,
                        "date": "2024-11-01T12:00:00"
                    },
                    ...
                ],
                "pagination": {
                    "total": 150,
                    "limit": 50,
                    "offset": 0,
                    "has_next": True,
                    "has_previous": False
                }
            }

        Raises:
            PaginationError: If parameters are invalid
        """
        # Validate parameters
        self._validate_limit(limit)
        self._validate_offset(offset)
        self._validate_sort(sort)

        # Get all photos with metadata
        all_photos = self._get_all_photos()

        # Apply date filtering
        if start_date or end_date:
            all_photos = self._filter_by_date(all_photos, start_date, end_date)

        # Sort photos
        sorted_photos = self._sort_photos(all_photos, sort)

        # Apply pagination
        total = len(sorted_photos)
        page_photos = sorted_photos[offset : offset + limit]

        # Calculate pagination metadata
        has_next = (offset + limit) < total
        has_previous = offset > 0

        # Convert to response format
        photos_list = [self._photo_to_dict(photo) for photo in page_photos]

        return {
            "photos": photos_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_next": has_next,
                "has_previous": has_previous,
            },
        }

    def _get_all_photos(self) -> list:
        """
        Get all photos from photos directory

        Returns:
            List of tuples: (path, mtime, size)
        """
        if not self.photos_dir.exists():
            return []

        photos = []
        for pattern in PHOTO_PATTERNS:
            for photo_path in self.photos_dir.rglob(pattern):
                try:
                    stat = photo_path.stat()
                    photos.append((photo_path, stat.st_mtime, stat.st_size))
                except OSError:
                    # Skip photos that can't be accessed
                    continue

        return photos

    def _filter_by_date(
        self, photos: list, start_date: datetime | None, end_date: datetime | None
    ) -> list:
        """
        Filter photos by date range

        Args:
            photos: List of (path, mtime, size) tuples
            start_date: Include photos on or after this date
            end_date: Include photos on or before this date

        Returns:
            Filtered list of photos
        """
        filtered = []

        for photo_path, mtime, size in photos:
            photo_datetime = datetime.fromtimestamp(mtime)

            # Check start_date
            if start_date and photo_datetime < start_date:
                continue

            # Check end_date (inclusive - allow any time on that day)
            if end_date:
                # Create end of day datetime for comparison
                end_of_day = datetime(
                    end_date.year,
                    end_date.month,
                    end_date.day,
                    23,
                    59,
                    59,
                    999999,
                )
                if photo_datetime > end_of_day:
                    continue

            filtered.append((photo_path, mtime, size))

        return filtered

    def _sort_photos(self, photos: list, sort: str) -> list:
        """
        Sort photos by specified order

        Args:
            photos: List of (path, mtime, size) tuples
            sort: Sort order (date_desc, date_asc, filename_asc, filename_desc)

        Returns:
            Sorted list of photos
        """
        if sort == 'date_desc':
            return sorted(photos, key=lambda x: x[1], reverse=True)
        elif sort == 'date_asc':
            return sorted(photos, key=lambda x: x[1])
        elif sort == 'filename_asc':
            return sorted(photos, key=lambda x: x[0].name.lower())
        elif sort == 'filename_desc':
            return sorted(photos, key=lambda x: x[0].name.lower(), reverse=True)
        else:
            # Should never reach here due to validation, but default to date_desc
            return sorted(photos, key=lambda x: x[1], reverse=True)

    def _photo_to_dict(self, photo_tuple: tuple) -> dict:
        """
        Convert photo tuple to dictionary format

        Args:
            photo_tuple: (path, mtime, size) tuple

        Returns:
            Dictionary with photo metadata
        """
        photo_path, mtime, size = photo_tuple

        return {
            "path": str(photo_path.relative_to(self.photos_dir)),
            "filename": photo_path.name,
            "size": size,
            "timestamp": mtime,
            "date": datetime.fromtimestamp(mtime).isoformat(),
        }

    def _validate_limit(self, limit: int) -> None:
        """
        Validate limit parameter

        Args:
            limit: Requested page size

        Raises:
            PaginationError: If limit is invalid
        """
        if not isinstance(limit, int):
            raise PaginationError(f"Limit must be an integer, got {type(limit).__name__}")

        if limit < self.MIN_LIMIT:
            raise PaginationError(
                f"Limit must be at least {self.MIN_LIMIT}, got {limit}"
            )

        if limit > self.MAX_LIMIT:
            raise PaginationError(
                f"Limit cannot exceed {self.MAX_LIMIT}, got {limit}"
            )

    def _validate_offset(self, offset: int) -> None:
        """
        Validate offset parameter

        Args:
            offset: Number of photos to skip

        Raises:
            PaginationError: If offset is invalid
        """
        if not isinstance(offset, int):
            raise PaginationError(f"Offset must be an integer, got {type(offset).__name__}")

        if offset < 0:
            raise PaginationError(f"Offset must be non-negative, got {offset}")

    def _validate_sort(self, sort: str) -> None:
        """
        Validate sort parameter

        Args:
            sort: Sort order

        Raises:
            PaginationError: If sort is invalid
        """
        if sort not in self.VALID_SORT_OPTIONS:
            raise PaginationError(
                f"Invalid sort option '{sort}'. "
                f"Valid options: {', '.join(self.VALID_SORT_OPTIONS)}"
            )
