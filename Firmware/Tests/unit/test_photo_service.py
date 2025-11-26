"""
Unit tests for PhotoService class (Issue #135 - Gallery API Pagination)

Tests comprehensive photo listing, pagination, sorting, and filtering.
Follows TDD methodology with strict test-first approach.

Test Coverage:
- Service initialization and configuration
- File system operations (_get_all_photos)
- Sorting (date, filename, ascending/descending)
- Date filtering (start_date, end_date, ranges)
- Validation (limit, offset, sort options)
- list_photos integration (pagination, combined operations)
- Edge cases and error handling

Coverage Target: 85%+
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))

from services.photo_service import PaginationError, PhotoService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_photos_dir(tmp_path):
    """
    Temporary photos directory for testing

    Creates isolated photo directory with temp_path for each test.
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    return photos_dir


@pytest.fixture
def photo_service(temp_photos_dir):
    """
    PhotoService instance with temporary directory

    Uses tmp_path to ensure tests don't depend on real PHOTOS_DIR.
    """
    return PhotoService(photos_dir=temp_photos_dir)


@pytest.fixture
def sample_photos(temp_photos_dir):
    """
    Create sample photos with different timestamps

    Creates 10 photos with predictable names and modification times
    for testing sorting and filtering.
    """
    photos = []
    base_time = datetime(2024, 11, 1, 12, 0, 0).timestamp()

    for i in range(10):
        photo_path = temp_photos_dir / f"photo_{i:02d}.jpg"
        photo_path.write_text(f"Photo {i}")

        # Set modification time (each photo 1 hour apart)
        mtime = base_time + (i * 3600)
        photo_path.touch()
        import os
        os.utime(photo_path, (mtime, mtime))

        photos.append(photo_path)

    return photos


@pytest.fixture
def nested_photos(temp_photos_dir):
    """
    Create photos in nested subdirectories

    Tests recursive directory traversal.
    """
    photos = []

    # Root level
    root_photo = temp_photos_dir / "root.jpg"
    root_photo.write_text("Root photo")
    photos.append(root_photo)

    # Subdirectory
    subdir = temp_photos_dir / "2024-11"
    subdir.mkdir()
    sub_photo = subdir / "photo_sub.jpg"
    sub_photo.write_text("Sub photo")
    photos.append(sub_photo)

    # Nested subdirectory
    nested = subdir / "day-01"
    nested.mkdir()
    nested_photo = nested / "photo_nested.jpg"
    nested_photo.write_text("Nested photo")
    photos.append(nested_photo)

    return photos


@pytest.fixture
def mixed_files(temp_photos_dir):
    """
    Create mix of JPG and non-image files

    Tests file type filtering.
    """
    files = {}

    # JPG files (should be included)
    files['jpg1'] = temp_photos_dir / "photo1.jpg"
    files['jpg1'].write_text("Photo 1")

    files['jpg2'] = temp_photos_dir / "photo2.jpg"
    files['jpg2'].write_text("Photo 2")

    # Non-image files (should be excluded)
    files['txt'] = temp_photos_dir / "readme.txt"
    files['txt'].write_text("Text file")

    files['png'] = temp_photos_dir / "image.png"
    files['png'].write_text("PNG file")

    files['json'] = temp_photos_dir / "metadata.json"
    files['json'].write_text("{}")

    return files


# ============================================================================
# Test Class 1: Initialization
# ============================================================================


class TestPhotoServiceInitialization:
    """Test PhotoService initialization and configuration"""

    def test_default_initialization(self):
        """Test service initializes with default PHOTOS_DIR"""
        service = PhotoService()

        assert service is not None
        assert service.photos_dir is not None
        assert hasattr(service, 'list_photos')

    def test_custom_photos_directory(self, temp_photos_dir):
        """Test service initializes with custom photos directory"""
        service = PhotoService(photos_dir=temp_photos_dir)

        assert service.photos_dir == temp_photos_dir

    def test_invalid_directory_handling(self, tmp_path):
        """Test service handles non-existent directory gracefully"""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise during initialization
        service = PhotoService(photos_dir=nonexistent)
        assert service.photos_dir == nonexistent

        # Should return empty list when listing photos
        result = service.list_photos()
        assert result['photos'] == []
        assert result['pagination']['total'] == 0


# ============================================================================
# Test Class 2: File System Operations - _get_all_photos
# ============================================================================


class TestGetAllPhotos:
    """Test _get_all_photos file system operations"""

    def test_empty_directory(self, photo_service):
        """Test _get_all_photos returns empty list for empty directory"""
        photos = photo_service._get_all_photos()

        assert photos == []

    def test_directory_with_photos(self, photo_service, temp_photos_dir):
        """Test _get_all_photos finds photos in directory"""
        # Create some photos
        photo1 = temp_photos_dir / "photo1.jpg"
        photo1.write_text("Photo 1")
        photo2 = temp_photos_dir / "photo2.jpg"
        photo2.write_text("Photo 2")

        photos = photo_service._get_all_photos()

        assert len(photos) == 2
        # Each photo is a tuple: (path, mtime, size)
        assert all(isinstance(p, tuple) for p in photos)
        assert all(len(p) == 3 for p in photos)

    def test_mixed_file_types(self, photo_service, mixed_files):
        """Test _get_all_photos only returns .jpg files"""
        photos = photo_service._get_all_photos()

        # Should only find 2 JPG files
        assert len(photos) == 2

        # Verify all returned files have .jpg extension
        for photo_path, _mtime, _size in photos:
            assert photo_path.suffix.lower() == '.jpg'

    def test_nested_subdirectories(self, photo_service, nested_photos):
        """Test _get_all_photos recursively finds photos in subdirectories"""
        photos = photo_service._get_all_photos()

        # Should find all 3 photos (root, subdir, nested)
        assert len(photos) == 3

        # Verify paths
        photo_names = {p[0].name for p in photos}
        assert 'root.jpg' in photo_names
        assert 'photo_sub.jpg' in photo_names
        assert 'photo_nested.jpg' in photo_names

    def test_permission_errors_skipped(self, photo_service, temp_photos_dir):
        """Test _get_all_photos skips photos with permission errors"""
        import os
        import stat

        # Create accessible photo
        accessible = temp_photos_dir / "accessible.jpg"
        accessible.write_text("Accessible")

        # Create photo and remove read permissions
        restricted = temp_photos_dir / "restricted.jpg"
        restricted.write_text("Restricted")
        os.chmod(restricted, 0o000)

        try:
            photos = photo_service._get_all_photos()

            # Should find at least the accessible photo
            # Restricted photo may or may not appear depending on permissions
            assert len(photos) >= 1

            # Accessible photo should be present
            photo_names = {p[0].name for p in photos}
            assert 'accessible.jpg' in photo_names

        finally:
            # Restore permissions for cleanup
            os.chmod(restricted, stat.S_IRUSR | stat.S_IWUSR)

    def test_glob_pattern_matching(self, photo_service, temp_photos_dir):
        """Test _get_all_photos uses correct glob pattern (*.jpg)"""
        # Create files with various extensions
        temp_photos_dir.joinpath("photo.jpg").write_text("JPG")
        temp_photos_dir.joinpath("photo.JPG").write_text("JPG uppercase")
        temp_photos_dir.joinpath("photo.jpeg").write_text("JPEG")
        temp_photos_dir.joinpath("photo.png").write_text("PNG")

        photos = photo_service._get_all_photos()

        # Should only match .jpg files (case-insensitive on most systems)
        # Note: rglob("*.jpg") is case-insensitive on some systems
        assert len(photos) >= 1  # At least "photo.jpg"

        # All returned files should have .jpg extension
        for photo_path, _mtime, _size in photos:
            assert photo_path.suffix.lower() in ['.jpg', '.jpeg']

    def test_large_directory_handling(self, photo_service, temp_photos_dir):
        """Test _get_all_photos handles large directories efficiently"""
        # Create 100 photos
        for i in range(100):
            photo = temp_photos_dir / f"photo_{i:03d}.jpg"
            photo.write_text(f"Photo {i}")

        start = time.time()
        photos = photo_service._get_all_photos()
        elapsed = time.time() - start

        assert len(photos) == 100
        # Should complete reasonably quickly (< 2 seconds)
        assert elapsed < 2.0


# ============================================================================
# Test Class 3: Sorting
# ============================================================================


class TestPhotoSorting:
    """Test photo sorting functionality"""

    def test_sort_by_date_descending(self, photo_service, sample_photos):
        """Test sorting photos by date (newest first)"""
        photos = photo_service._get_all_photos()
        sorted_photos = photo_service._sort_photos(photos, 'date_desc')

        # Verify sorted in descending order (newest first)
        for i in range(len(sorted_photos) - 1):
            assert sorted_photos[i][1] >= sorted_photos[i + 1][1]

    def test_sort_by_date_ascending(self, photo_service, sample_photos):
        """Test sorting photos by date (oldest first)"""
        photos = photo_service._get_all_photos()
        sorted_photos = photo_service._sort_photos(photos, 'date_asc')

        # Verify sorted in ascending order (oldest first)
        for i in range(len(sorted_photos) - 1):
            assert sorted_photos[i][1] <= sorted_photos[i + 1][1]

    def test_sort_by_filename_ascending(self, photo_service, sample_photos):
        """Test sorting photos by filename (A-Z)"""
        photos = photo_service._get_all_photos()
        sorted_photos = photo_service._sort_photos(photos, 'filename_asc')

        # Verify sorted alphabetically
        for i in range(len(sorted_photos) - 1):
            name1 = sorted_photos[i][0].name.lower()
            name2 = sorted_photos[i + 1][0].name.lower()
            assert name1 <= name2

    def test_sort_by_filename_descending(self, photo_service, sample_photos):
        """Test sorting photos by filename (Z-A)"""
        photos = photo_service._get_all_photos()
        sorted_photos = photo_service._sort_photos(photos, 'filename_desc')

        # Verify sorted reverse alphabetically
        for i in range(len(sorted_photos) - 1):
            name1 = sorted_photos[i][0].name.lower()
            name2 = sorted_photos[i + 1][0].name.lower()
            assert name1 >= name2

    def test_invalid_sort_option_defaults_to_date_desc(self, photo_service, sample_photos):
        """Test invalid sort option falls back to date_desc"""
        photos = photo_service._get_all_photos()

        # Pass invalid sort option (should default to date_desc)
        sorted_photos = photo_service._sort_photos(photos, 'invalid_option')

        # Should be sorted by date descending
        for i in range(len(sorted_photos) - 1):
            assert sorted_photos[i][1] >= sorted_photos[i + 1][1]


# ============================================================================
# Test Class 4: Date Filtering
# ============================================================================


class TestDateFiltering:
    """Test date range filtering functionality"""

    def test_filter_by_start_date_only(self, photo_service, sample_photos):
        """Test filtering photos on or after start date"""
        all_photos = photo_service._get_all_photos()

        # Filter to photos from Nov 1, 2024 15:00 onwards (after photo 3)
        start_date = datetime(2024, 11, 1, 15, 0, 0)

        filtered = photo_service._filter_by_date(all_photos, start_date, None)

        # Should include photos 4-9 (6 photos)
        assert len(filtered) >= 6

        # All photos should be on or after start_date
        for _photo_path, mtime, _size in filtered:
            photo_datetime = datetime.fromtimestamp(mtime)
            assert photo_datetime >= start_date

    def test_filter_by_end_date_only(self, photo_service, sample_photos):
        """Test filtering photos on or before end date"""
        all_photos = photo_service._get_all_photos()

        # Filter to photos before Nov 1, 2024 15:00 (through photo 2)
        end_date = datetime(2024, 11, 1, 14, 0, 0)

        filtered = photo_service._filter_by_date(all_photos, None, end_date)

        # Should include photos 0-2 (3 photos)
        assert len(filtered) >= 3

        # All photos should be on or before end_date (inclusive of day)
        end_of_day = datetime(
            end_date.year, end_date.month, end_date.day,
            23, 59, 59, 999999
        )
        for _photo_path, mtime, _size in filtered:
            photo_datetime = datetime.fromtimestamp(mtime)
            assert photo_datetime <= end_of_day

    def test_filter_by_date_range(self, photo_service, sample_photos):
        """Test filtering photos within date range"""
        all_photos = photo_service._get_all_photos()

        # Filter to photos between 13:00 and 16:00 on Nov 1, 2024
        start_date = datetime(2024, 11, 1, 13, 0, 0)
        end_date = datetime(2024, 11, 1, 16, 0, 0)

        filtered = photo_service._filter_by_date(all_photos, start_date, end_date)

        # Should include photos in range
        assert len(filtered) >= 3

        # All photos should be within range
        end_of_day = datetime(
            end_date.year, end_date.month, end_date.day,
            23, 59, 59, 999999
        )
        for _photo_path, mtime, _size in filtered:
            photo_datetime = datetime.fromtimestamp(mtime)
            assert photo_datetime >= start_date
            assert photo_datetime <= end_of_day

    def test_boundary_conditions_exact_match(self, photo_service, temp_photos_dir):
        """Test date filtering with exact timestamp match"""
        import os

        # Create photo with exact timestamp
        exact_time = datetime(2024, 11, 15, 12, 0, 0)
        photo = temp_photos_dir / "exact.jpg"
        photo.write_text("Exact time photo")

        # Set exact modification time
        exact_timestamp = exact_time.timestamp()
        os.utime(photo, (exact_timestamp, exact_timestamp))

        all_photos = photo_service._get_all_photos()

        # Filter with exact same datetime
        filtered = photo_service._filter_by_date(all_photos, exact_time, exact_time)

        # Should include the photo (start_date is inclusive)
        assert len(filtered) == 1

    def test_empty_result_when_no_matches(self, photo_service, sample_photos):
        """Test filtering returns empty list when no photos match"""
        all_photos = photo_service._get_all_photos()

        # Filter to future date range (no photos should match)
        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 12, 31, 23, 59, 59)

        filtered = photo_service._filter_by_date(all_photos, start_date, end_date)

        assert filtered == []

    def test_invalid_date_format_handling(self, photo_service):
        """Test handling of invalid date objects"""
        all_photos = []

        # Should not raise exception with None dates
        filtered = photo_service._filter_by_date(all_photos, None, None)
        assert filtered == []

    def test_timezone_handling(self, photo_service, temp_photos_dir):
        """Test date filtering with timezone-naive datetimes"""
        import os

        # Create photo
        photo = temp_photos_dir / "tz_photo.jpg"
        photo.write_text("TZ photo")

        # Set modification time
        photo_time = datetime(2024, 11, 1, 12, 0, 0)
        photo_timestamp = photo_time.timestamp()
        os.utime(photo, (photo_timestamp, photo_timestamp))

        all_photos = photo_service._get_all_photos()

        # Filter with timezone-naive datetime (same as photo)
        start_date = datetime(2024, 11, 1, 11, 0, 0)
        end_date = datetime(2024, 11, 1, 13, 0, 0)

        filtered = photo_service._filter_by_date(all_photos, start_date, end_date)

        # Should find the photo
        assert len(filtered) == 1

    def test_filename_date_parsing(self, photo_service, temp_photos_dir):
        """Test filtering works with modification time (not filename)"""
        import os

        # Create photo with filename date that doesn't match mtime
        photo = temp_photos_dir / "mothbox_2023_01_01__00_00_00.jpg"
        photo.write_text("Photo")

        # Set mtime to 2024 (different from filename)
        mtime = datetime(2024, 11, 1, 12, 0, 0).timestamp()
        os.utime(photo, (mtime, mtime))

        all_photos = photo_service._get_all_photos()

        # Filter by 2024 date (should match mtime, not filename)
        start_date = datetime(2024, 10, 1, 0, 0, 0)
        end_date = datetime(2024, 12, 31, 23, 59, 59)

        filtered = photo_service._filter_by_date(all_photos, start_date, end_date)

        # Should find photo based on mtime, not filename
        assert len(filtered) == 1


# ============================================================================
# Test Class 5: Validation Methods
# ============================================================================


class TestValidationMethods:
    """Test parameter validation methods"""

    def test_validate_limit_valid_values(self, photo_service):
        """Test _validate_limit accepts valid limit values"""
        # Should not raise exception
        photo_service._validate_limit(1)
        photo_service._validate_limit(50)
        photo_service._validate_limit(500)

    def test_validate_limit_below_minimum(self, photo_service):
        """Test _validate_limit rejects limit below minimum"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_limit(0)

        assert "must be at least" in str(exc_info.value).lower()

    def test_validate_limit_above_maximum(self, photo_service):
        """Test _validate_limit rejects limit above maximum"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_limit(501)

        assert "cannot exceed" in str(exc_info.value).lower()

    def test_validate_limit_non_integer(self, photo_service):
        """Test _validate_limit rejects non-integer types"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_limit("50")

        assert "must be an integer" in str(exc_info.value).lower()

    def test_validate_offset_valid_values(self, photo_service):
        """Test _validate_offset accepts valid offset values"""
        # Should not raise exception
        photo_service._validate_offset(0)
        photo_service._validate_offset(100)
        photo_service._validate_offset(1000)

    def test_validate_offset_negative(self, photo_service):
        """Test _validate_offset rejects negative offset"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_offset(-1)

        assert "must be non-negative" in str(exc_info.value).lower()

    def test_validate_offset_non_integer(self, photo_service):
        """Test _validate_offset rejects non-integer types"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_offset(10.5)

        assert "must be an integer" in str(exc_info.value).lower()

    def test_validate_sort_valid_options(self, photo_service):
        """Test _validate_sort accepts all valid sort options"""
        # Should not raise exception
        for sort_option in PhotoService.VALID_SORT_OPTIONS:
            photo_service._validate_sort(sort_option)

    def test_validate_sort_invalid_option(self, photo_service):
        """Test _validate_sort rejects invalid sort option"""
        with pytest.raises(PaginationError) as exc_info:
            photo_service._validate_sort('invalid_sort')

        assert "invalid sort option" in str(exc_info.value).lower()
        assert "valid options" in str(exc_info.value).lower()


# ============================================================================
# Test Class 6: list_photos() Integration
# ============================================================================


class TestListPhotosIntegration:
    """Test list_photos end-to-end integration"""

    def test_basic_listing(self, photo_service, sample_photos):
        """Test basic photo listing returns correct structure"""
        result = photo_service.list_photos()

        assert 'photos' in result
        assert 'pagination' in result

        # Check pagination metadata
        assert result['pagination']['total'] == 10
        assert result['pagination']['limit'] == 50  # Default
        assert result['pagination']['offset'] == 0   # Default
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_previous'] is False

        # Check photos list
        assert len(result['photos']) == 10

    def test_pagination_offset(self, photo_service, sample_photos):
        """Test pagination with offset parameter"""
        result = photo_service.list_photos(limit=5, offset=3)

        assert len(result['photos']) == 5
        assert result['pagination']['offset'] == 3
        assert result['pagination']['total'] == 10
        assert result['pagination']['has_previous'] is True
        assert result['pagination']['has_next'] is True

    def test_pagination_limit(self, photo_service, sample_photos):
        """Test pagination with limit parameter"""
        result = photo_service.list_photos(limit=3, offset=0)

        assert len(result['photos']) == 3
        assert result['pagination']['limit'] == 3
        assert result['pagination']['has_next'] is True
        assert result['pagination']['has_previous'] is False

    def test_combined_sorting_and_filtering(self, photo_service, sample_photos):
        """Test combined date filtering and sorting"""
        # Filter to middle photos and sort by filename
        start_date = datetime(2024, 11, 1, 14, 0, 0)
        end_date = datetime(2024, 11, 1, 18, 0, 0)

        result = photo_service.list_photos(
            sort='filename_asc',
            start_date=start_date,
            end_date=end_date
        )

        # Should have filtered subset
        assert result['pagination']['total'] > 0
        assert result['pagination']['total'] < 10

        # Verify sorted alphabetically
        filenames = [p['filename'] for p in result['photos']]
        assert filenames == sorted(filenames)

    def test_return_format_validation(self, photo_service, sample_photos):
        """Test returned photo objects have correct format"""
        result = photo_service.list_photos(limit=1)

        photo = result['photos'][0]

        # Check all required fields
        assert 'path' in photo
        assert 'filename' in photo
        assert 'size' in photo
        assert 'timestamp' in photo
        assert 'date' in photo

        # Verify field types
        assert isinstance(photo['path'], str)
        assert isinstance(photo['filename'], str)
        assert isinstance(photo['size'], int)
        assert isinstance(photo['timestamp'], float)
        assert isinstance(photo['date'], str)

        # Verify date is ISO format
        datetime.fromisoformat(photo['date'])  # Should not raise

    def test_total_count_accuracy(self, photo_service, sample_photos):
        """Test pagination total count is accurate"""
        # Test with different limits
        result1 = photo_service.list_photos(limit=3)
        result2 = photo_service.list_photos(limit=100)

        # Total should be same regardless of limit
        assert result1['pagination']['total'] == 10
        assert result2['pagination']['total'] == 10

        # But returned photo count should differ
        assert len(result1['photos']) == 3
        assert len(result2['photos']) == 10

    def test_edge_case_empty_directory(self, photo_service):
        """Test list_photos with empty directory"""
        result = photo_service.list_photos()

        assert result['photos'] == []
        assert result['pagination']['total'] == 0
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_previous'] is False

    def test_edge_case_single_photo(self, photo_service, temp_photos_dir):
        """Test list_photos with single photo"""
        photo = temp_photos_dir / "single.jpg"
        photo.write_text("Single photo")

        result = photo_service.list_photos()

        assert len(result['photos']) == 1
        assert result['pagination']['total'] == 1
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_previous'] is False

    def test_performance_with_large_result_sets(self, photo_service, temp_photos_dir):
        """Test list_photos performance with many photos"""
        # Create 200 photos
        for i in range(200):
            photo = temp_photos_dir / f"photo_{i:03d}.jpg"
            photo.write_text(f"Photo {i}")

        start = time.time()
        result = photo_service.list_photos(limit=50, offset=0)
        elapsed = time.time() - start

        assert len(result['photos']) == 50
        assert result['pagination']['total'] == 200

        # Should complete quickly (< 1 second)
        assert elapsed < 1.0

    def test_pagination_has_next_calculation(self, photo_service, sample_photos):
        """Test has_next pagination flag is calculated correctly"""
        # First page - should have next
        result1 = photo_service.list_photos(limit=5, offset=0)
        assert result1['pagination']['has_next'] is True

        # Last page - should not have next
        result2 = photo_service.list_photos(limit=5, offset=5)
        assert result2['pagination']['has_next'] is False

        # Beyond last page - should not have next
        result3 = photo_service.list_photos(limit=5, offset=10)
        assert result3['pagination']['has_next'] is False

    def test_pagination_has_previous_calculation(self, photo_service, sample_photos):
        """Test has_previous pagination flag is calculated correctly"""
        # First page - should not have previous
        result1 = photo_service.list_photos(limit=5, offset=0)
        assert result1['pagination']['has_previous'] is False

        # Second page - should have previous
        result2 = photo_service.list_photos(limit=5, offset=5)
        assert result2['pagination']['has_previous'] is True

        # Middle page - should have previous
        result3 = photo_service.list_photos(limit=3, offset=3)
        assert result3['pagination']['has_previous'] is True

    def test_validation_integration_invalid_limit(self, photo_service):
        """Test list_photos raises PaginationError for invalid limit"""
        with pytest.raises(PaginationError):
            photo_service.list_photos(limit=0)

        with pytest.raises(PaginationError):
            photo_service.list_photos(limit=1000)

    def test_validation_integration_invalid_offset(self, photo_service):
        """Test list_photos raises PaginationError for invalid offset"""
        with pytest.raises(PaginationError):
            photo_service.list_photos(offset=-5)

    def test_validation_integration_invalid_sort(self, photo_service):
        """Test list_photos raises PaginationError for invalid sort"""
        with pytest.raises(PaginationError):
            photo_service.list_photos(sort='invalid')


# ============================================================================
# Test Class 7: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling"""

    def test_photo_to_dict_conversion(self, photo_service, temp_photos_dir):
        """Test _photo_to_dict converts photo tuple correctly"""
        photo = temp_photos_dir / "test.jpg"
        photo.write_text("Test photo content")

        # Get stat info
        stat = photo.stat()
        photo_tuple = (photo, stat.st_mtime, stat.st_size)

        # Convert to dict
        result = photo_service._photo_to_dict(photo_tuple)

        # Verify structure
        assert result['filename'] == 'test.jpg'
        assert result['size'] == stat.st_size
        assert result['timestamp'] == stat.st_mtime
        assert isinstance(result['date'], str)
        assert result['path'] == 'test.jpg'  # Relative to photos_dir

    def test_photo_to_dict_nested_path(self, photo_service, temp_photos_dir):
        """Test _photo_to_dict handles nested paths correctly"""
        subdir = temp_photos_dir / "2024" / "november"
        subdir.mkdir(parents=True)

        photo = subdir / "nested.jpg"
        photo.write_text("Nested photo")

        stat = photo.stat()
        photo_tuple = (photo, stat.st_mtime, stat.st_size)

        result = photo_service._photo_to_dict(photo_tuple)

        # Path should be relative to photos_dir
        assert result['path'] == '2024/november/nested.jpg'
        assert result['filename'] == 'nested.jpg'

    def test_constant_values(self):
        """Test PhotoService class constants are defined correctly"""
        assert PhotoService.MIN_LIMIT == 1
        assert PhotoService.MAX_LIMIT == 500
        assert PhotoService.DEFAULT_LIMIT == 50
        assert PhotoService.DEFAULT_OFFSET == 0

        assert 'date_desc' in PhotoService.VALID_SORT_OPTIONS
        assert 'date_asc' in PhotoService.VALID_SORT_OPTIONS
        assert 'filename_asc' in PhotoService.VALID_SORT_OPTIONS
        assert 'filename_desc' in PhotoService.VALID_SORT_OPTIONS
        assert len(PhotoService.VALID_SORT_OPTIONS) == 4

    def test_empty_photos_list_operations(self, photo_service):
        """Test operations on empty photos list don't raise errors"""
        empty_photos = []

        # Sorting empty list
        sorted_photos = photo_service._sort_photos(empty_photos, 'date_desc')
        assert sorted_photos == []

        # Filtering empty list
        filtered = photo_service._filter_by_date(
            empty_photos,
            datetime.now(),
            datetime.now()
        )
        assert filtered == []

    def test_offset_beyond_total(self, photo_service, sample_photos):
        """Test list_photos with offset beyond total photos"""
        result = photo_service.list_photos(limit=10, offset=100)

        # Should return empty list
        assert result['photos'] == []
        assert result['pagination']['total'] == 10
        assert result['pagination']['offset'] == 100
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_previous'] is True

    def test_exact_page_boundary(self, photo_service, sample_photos):
        """Test pagination exactly at page boundary"""
        # Request exactly the last photo
        result = photo_service.list_photos(limit=1, offset=9)

        assert len(result['photos']) == 1
        assert result['pagination']['has_next'] is False
        assert result['pagination']['has_previous'] is True

    def test_case_insensitive_filename_sorting(self, photo_service, temp_photos_dir):
        """Test filename sorting is case-insensitive"""
        # Create photos with mixed case names
        temp_photos_dir.joinpath("ALPHA.jpg").write_text("A")
        temp_photos_dir.joinpath("beta.jpg").write_text("B")
        temp_photos_dir.joinpath("Charlie.jpg").write_text("C")

        result = photo_service.list_photos(sort='filename_asc')

        filenames = [p['filename'] for p in result['photos']]
        # Should be sorted case-insensitively
        assert filenames[0] == 'ALPHA.jpg'
        assert filenames[1] == 'beta.jpg'
        assert filenames[2] == 'Charlie.jpg'
