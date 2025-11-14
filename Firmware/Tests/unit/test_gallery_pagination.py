"""
Unit tests for gallery pagination (Issue #135)

Tests paginated photo listing with limit/offset query parameters.
Validates pagination metadata, sorting options, and filtering support.

Following strict TDD: These tests written BEFORE implementation.
They will fail initially - that's expected and correct.

Coverage Target: 90%+ (pagination logic is critical path)
Reference: Tests/unit/test_gallery_routes.py for patterns
"""

import json
from datetime import datetime, timedelta

import pytest
from flask import Flask

# Import the blueprint
from routes.gallery import gallery_bp

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def gallery_app(temp_photos_dir):
    """Flask app with gallery blueprint for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True

    # Register blueprint AFTER patching PHOTOS_DIR
    app.register_blueprint(gallery_bp, url_prefix='/api/gallery')
    return app


@pytest.fixture
def gallery_client(gallery_app):
    """Test client for gallery routes"""
    return gallery_app.test_client()


@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """
    Temporary PHOTOS_DIR for gallery tests

    Creates isolated photo directory and patches mothbox_paths.PHOTOS_DIR
    in all relevant modules.
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Patch PHOTOS_DIR in mothbox_paths
    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, 'PHOTOS_DIR', photos_dir)

    # Also patch in routes.gallery module (already imported)
    import routes.gallery
    monkeypatch.setattr(routes.gallery, 'PHOTOS_DIR', photos_dir)

    return photos_dir


@pytest.fixture
def large_photo_set(temp_photos_dir):
    """
    Create 150 test photos for pagination testing

    Photos created with staggered timestamps (1 minute apart)
    to ensure consistent ordering in pagination tests.
    """
    photos = []
    base_time = datetime(2024, 11, 1, 12, 0, 0)

    for i in range(150):
        photo_path = temp_photos_dir / f"photo_{i:03d}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Minimal JPEG

        # Set specific mtime for each photo (newest first: i=0 is most recent)
        photo_time = base_time - timedelta(minutes=i)
        timestamp = photo_time.timestamp()
        photo_path.touch()
        import os
        os.utime(photo_path, (timestamp, timestamp))

        photos.append(photo_path)

    return photos


@pytest.fixture
def dated_photos(temp_photos_dir):
    """
    Create 30 photos with specific dates for filtering tests

    Distribution:
    - 10 photos from 2024-10-01 to 2024-10-10 (October)
    - 10 photos from 2024-11-01 to 2024-11-10 (November)
    - 10 photos from 2024-12-01 to 2024-12-10 (December)
    """
    photos = []

    # October photos
    for i in range(10):
        photo_path = temp_photos_dir / f"oct_photo_{i:02d}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        photo_date = datetime(2024, 10, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        import os
        os.utime(photo_path, (timestamp, timestamp))
        photos.append(photo_path)

    # November photos
    for i in range(10):
        photo_path = temp_photos_dir / f"nov_photo_{i:02d}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        photo_date = datetime(2024, 11, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        import os
        os.utime(photo_path, (timestamp, timestamp))
        photos.append(photo_path)

    # December photos
    for i in range(10):
        photo_path = temp_photos_dir / f"dec_photo_{i:02d}.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        photo_date = datetime(2024, 12, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        import os
        os.utime(photo_path, (timestamp, timestamp))
        photos.append(photo_path)

    return photos


@pytest.fixture
def huge_photo_set(temp_photos_dir):
    """
    Mock 100,000 photos for performance testing without creating actual files

    Returns a mock that simulates a huge photo collection for performance tests.
    """
    # Note: This fixture will be used with mocking to avoid actually creating 100k files
    return {'count': 100000, 'dir': temp_photos_dir}


# ============================================================================
# Test Pagination Basics
# ============================================================================

class TestPaginationBasic:
    """Basic pagination functionality tests (6 tests)"""

    def test_default_parameters_no_query_params(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated returns first page with default limit (50) when no params provided

        Expected behavior:
        - Returns 50 photos (default limit)
        - Offset is 0 (default)
        - Photos sorted by date descending (newest first)
        """
        response = gallery_client.get('/api/gallery/photos/paginated')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert 'photos' in data
        assert 'pagination' in data

        # Check photo count matches default limit
        assert len(data['photos']) == 50

        # Verify photos are sorted newest first
        timestamps = [photo['timestamp'] for photo in data['photos']]
        assert timestamps == sorted(timestamps, reverse=True), "Photos should be newest first"

    def test_custom_limit(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated?limit=25 returns specified number of photos

        Tests that limit parameter correctly controls page size.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=25')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['photos']) == 25
        assert data['pagination']['limit'] == 25

    def test_custom_offset(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated?offset=50 skips first 50 photos

        Tests that offset parameter correctly skips photos.
        """
        # Get first page to compare
        first_page = gallery_client.get('/api/gallery/photos/paginated?limit=10')
        first_data = json.loads(first_page.data)

        # Get page starting at offset 50
        response = gallery_client.get('/api/gallery/photos/paginated?offset=50&limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['photos']) == 10
        assert data['pagination']['offset'] == 50

        # Verify photos are different from first page
        first_filenames = [p['filename'] for p in first_data['photos']]
        offset_filenames = [p['filename'] for p in data['photos']]
        assert first_filenames != offset_filenames, "Offset should return different photos"

    def test_combined_limit_and_offset(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated?limit=20&offset=30 combines both parameters correctly

        Tests pagination with both limit and offset parameters.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=20&offset=30')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['photos']) == 20
        assert data['pagination']['limit'] == 20
        assert data['pagination']['offset'] == 30

    def test_offset_exceeds_total(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated?offset=200 returns empty list when offset exceeds total photos

        Expected behavior:
        - Returns 200 OK (not an error)
        - Photos array is empty
        - Pagination metadata shows offset beyond total
        """
        response = gallery_client.get('/api/gallery/photos/paginated?offset=200')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['photos'] == []
        assert data['pagination']['offset'] == 200
        assert data['pagination']['total'] == 150  # Total photos in large_photo_set

    def test_limit_exceeds_remaining(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated?offset=140&limit=50 returns only remaining photos

        When limit exceeds remaining photos, return only what's available.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?offset=140&limit=50')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return only 10 photos (150 total - 140 offset = 10 remaining)
        assert len(data['photos']) == 10
        assert data['pagination']['limit'] == 50
        assert data['pagination']['offset'] == 140


# ============================================================================
# Test Pagination Metadata
# ============================================================================

class TestPaginationMetadata:
    """Pagination metadata structure tests (6 tests)"""

    def test_metadata_structure_validation(self, gallery_client, large_photo_set):
        """
        Pagination metadata includes all required fields

        Required fields:
        - total: total number of photos
        - limit: requested page size
        - offset: starting position
        - has_next: boolean indicating more pages
        - has_previous: boolean indicating previous pages
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=25&offset=25')

        assert response.status_code == 200
        data = json.loads(response.data)

        pagination = data['pagination']

        # Verify all required fields present
        assert 'total' in pagination
        assert 'limit' in pagination
        assert 'offset' in pagination
        assert 'has_next' in pagination
        assert 'has_previous' in pagination

        # Verify data types
        assert isinstance(pagination['total'], int)
        assert isinstance(pagination['limit'], int)
        assert isinstance(pagination['offset'], int)
        assert isinstance(pagination['has_next'], bool)
        assert isinstance(pagination['has_previous'], bool)

    def test_has_next_true_when_more_pages(self, gallery_client, large_photo_set):
        """
        has_next is True when there are more photos after current page

        With 150 total photos, offset=0 limit=50 should have has_next=True
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=50&offset=0')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['has_next'] is True
        assert data['pagination']['total'] == 150
        # offset + limit < total, so more pages exist

    def test_has_next_false_on_last_page(self, gallery_client, large_photo_set):
        """
        has_next is False when on the last page

        With 150 total photos, offset=100 limit=50 should have has_next=False
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=50&offset=100')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['has_next'] is False
        # offset + limit >= total, so this is the last page

    def test_has_previous_true_when_offset_greater_than_zero(self, gallery_client, large_photo_set):
        """
        has_previous is True when offset > 0

        Tests that has_previous correctly indicates previous pages exist.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=50&offset=50')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['has_previous'] is True
        assert data['pagination']['offset'] == 50

    def test_has_previous_false_on_first_page(self, gallery_client, large_photo_set):
        """
        has_previous is False when offset is 0 (first page)

        Tests that has_previous correctly indicates no previous pages.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=50&offset=0')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['pagination']['has_previous'] is False
        assert data['pagination']['offset'] == 0

    def test_total_count_accuracy(self, gallery_client, large_photo_set):
        """
        total field accurately reflects total number of photos

        Tests that total count is consistent across different pages.
        """
        # Request multiple pages and verify total is consistent
        pages = [
            '/api/gallery/photos/paginated?limit=50&offset=0',
            '/api/gallery/photos/paginated?limit=50&offset=50',
            '/api/gallery/photos/paginated?limit=50&offset=100',
        ]

        totals = []
        for page_url in pages:
            response = gallery_client.get(page_url)
            data = json.loads(response.data)
            totals.append(data['pagination']['total'])

        # All pages should report same total
        assert len(set(totals)) == 1, "Total count should be consistent across pages"
        assert totals[0] == 150  # large_photo_set has 150 photos


# ============================================================================
# Test Pagination Sorting
# ============================================================================

class TestPaginationSorting:
    """Sorting options for paginated results (5 tests)"""

    def test_default_sort_date_desc(self, gallery_client, large_photo_set):
        """
        Default sort order is date_desc (newest first)

        When no sort parameter provided, photos sorted by timestamp descending.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify descending timestamp order
        timestamps = [photo['timestamp'] for photo in data['photos']]
        assert timestamps == sorted(timestamps, reverse=True), "Default should be newest first"

    def test_sort_date_asc(self, gallery_client, large_photo_set):
        """
        sort=date_asc returns oldest photos first

        Tests ascending date sort order.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=10&sort=date_asc')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify ascending timestamp order
        timestamps = [photo['timestamp'] for photo in data['photos']]
        assert timestamps == sorted(timestamps), "date_asc should be oldest first"

    def test_sort_filename_asc(self, gallery_client, large_photo_set):
        """
        sort=filename_asc returns photos sorted alphabetically by filename

        Tests alphabetical ascending sort.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=10&sort=filename_asc')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify alphabetical order
        filenames = [photo['filename'] for photo in data['photos']]
        assert filenames == sorted(filenames), "filename_asc should be alphabetical"

    def test_sort_filename_desc(self, gallery_client, large_photo_set):
        """
        sort=filename_desc returns photos sorted reverse alphabetically

        Tests alphabetical descending sort.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=10&sort=filename_desc')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify reverse alphabetical order
        filenames = [photo['filename'] for photo in data['photos']]
        assert filenames == sorted(filenames, reverse=True), "filename_desc should be reverse alphabetical"

    def test_invalid_sort_option_returns_400(self, gallery_client, large_photo_set):
        """
        sort=invalid returns 400 error with helpful message

        Tests validation of sort parameter.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?sort=invalid_sort')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'


# ============================================================================
# Test Pagination Filtering
# ============================================================================

class TestPaginationFiltering:
    """Date range filtering for paginated results (5 tests)"""

    def test_filter_by_start_date(self, gallery_client, dated_photos):
        """
        start_date filters photos to only those on or after specified date

        Tests that start_date parameter correctly filters photos.
        """
        # Filter for November onwards (should exclude October photos)
        response = gallery_client.get('/api/gallery/photos/paginated?start_date=2024-11-01')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return 20 photos (10 November + 10 December)
        assert len(data['photos']) <= data['pagination']['total']
        assert data['pagination']['total'] == 20

        # Verify all photos are from November or later
        for photo in data['photos']:
            photo_date = datetime.fromisoformat(photo['date'])
            assert photo_date >= datetime(2024, 11, 1)

    def test_filter_by_end_date(self, gallery_client, dated_photos):
        """
        end_date filters photos to only those on or before specified date

        Tests that end_date parameter correctly filters photos.
        """
        # Filter for October only (should exclude November and December)
        response = gallery_client.get('/api/gallery/photos/paginated?end_date=2024-10-31')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return 10 photos (October only)
        assert data['pagination']['total'] == 10

        # Verify all photos are from October or earlier
        for photo in data['photos']:
            photo_date = datetime.fromisoformat(photo['date'])
            assert photo_date <= datetime(2024, 10, 31, 23, 59, 59)

    def test_filter_by_date_range(self, gallery_client, dated_photos):
        """
        start_date and end_date together filter to specific date range

        Tests that both date parameters work together correctly.
        """
        # Filter for November only (start and end date both specified)
        response = gallery_client.get(
            '/api/gallery/photos/paginated?start_date=2024-11-01&end_date=2024-11-30'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return 10 photos (November only)
        assert data['pagination']['total'] == 10

        # Verify all photos are within November
        for photo in data['photos']:
            photo_date = datetime.fromisoformat(photo['date'])
            assert datetime(2024, 11, 1) <= photo_date <= datetime(2024, 11, 30, 23, 59, 59)

    def test_filter_combined_with_pagination(self, gallery_client, dated_photos):
        """
        Date filters work correctly with limit and offset

        Tests that filtering and pagination parameters work together.
        """
        # Filter for all photos, but paginate with limit=5
        response = gallery_client.get('/api/gallery/photos/paginated?start_date=2024-10-01&limit=5')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['photos']) == 5  # Respects limit
        assert data['pagination']['total'] == 30  # Total filtered photos
        assert data['pagination']['has_next'] is True  # More pages available

    def test_empty_filter_results(self, gallery_client, dated_photos):
        """
        Date filter with no matching photos returns empty list

        Tests handling of filter with no results.
        """
        # Filter for future date (no photos should match)
        response = gallery_client.get('/api/gallery/photos/paginated?start_date=2025-01-01')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['photos'] == []
        assert data['pagination']['total'] == 0
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_previous'] is False


# ============================================================================
# Test Pagination Validation
# ============================================================================

class TestPaginationValidation:
    """Input validation for pagination parameters (6 tests)"""

    def test_negative_limit_returns_400(self, gallery_client, large_photo_set):
        """
        limit=-10 returns 400 error

        Tests that negative limit values are rejected.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=-10')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'

    def test_zero_limit_returns_400(self, gallery_client, large_photo_set):
        """
        limit=0 returns 400 error

        Tests that zero limit is rejected (must be positive).
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=0')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'

    def test_limit_exceeds_max_returns_400(self, gallery_client, large_photo_set):
        """
        limit=1000 returns 400 error when max limit is 500

        Tests that excessively large limit values are rejected.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=1000')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'

    def test_negative_offset_returns_400(self, gallery_client, large_photo_set):
        """
        offset=-5 returns 400 error

        Tests that negative offset values are rejected.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?offset=-5')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'

    def test_invalid_date_format_returns_400(self, gallery_client, dated_photos):
        """
        start_date=invalid-date returns 400 error

        Tests that malformed date strings are rejected.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?start_date=not-a-date')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data
        assert 'date' in data['error'].lower()

    def test_non_integer_limit_returns_400(self, gallery_client, large_photo_set):
        """
        limit=abc returns 400 error

        Tests that non-numeric limit values are rejected.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=abc')

        assert response.status_code == 400
        data = json.loads(response.data)

        assert 'error' in data


# ============================================================================
# Test Pagination Performance
# ============================================================================

class TestPaginationPerformance:
    """Performance characteristics of pagination (4 tests)"""

    def test_large_collection_query_time(self, gallery_client, large_photo_set):
        """
        Pagination on large collection (150 photos) completes quickly

        Tests that pagination query time is acceptable even with many photos.
        Target: < 500ms for 150 photos
        """
        import time

        start_time = time.time()
        response = gallery_client.get('/api/gallery/photos/paginated?limit=50')
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # Performance target: should complete within 500ms
        assert elapsed_time < 0.5, f"Query took {elapsed_time:.3f}s, expected < 0.5s"

    def test_repeated_pagination_consistency(self, gallery_client, large_photo_set):
        """
        Repeated pagination requests return consistent results

        Tests that pagination results are stable across multiple requests.
        """
        # Request same page twice
        response1 = gallery_client.get('/api/gallery/photos/paginated?limit=25&offset=25')
        response2 = gallery_client.get('/api/gallery/photos/paginated?limit=25&offset=25')

        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)

        # Results should be identical
        assert data1['photos'] == data2['photos']
        assert data1['pagination'] == data2['pagination']

    def test_empty_directory_handling(self, gallery_client, temp_photos_dir):
        """
        Pagination on empty directory returns gracefully

        Tests that pagination handles empty photo directory without errors.
        """
        response = gallery_client.get('/api/gallery/photos/paginated')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['photos'] == []
        assert data['pagination']['total'] == 0
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_previous'] is False

    def test_single_photo_handling(self, gallery_client, temp_photos_dir):
        """
        Pagination with single photo returns correctly

        Tests edge case of single photo in directory.
        """
        # Create single photo
        photo_path = temp_photos_dir / "single.jpg"
        photo_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)

        response = gallery_client.get('/api/gallery/photos/paginated')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data['photos']) == 1
        assert data['pagination']['total'] == 1
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_previous'] is False


# ============================================================================
# Test Backward Compatibility
# ============================================================================

class TestBackwardCompatibility:
    """Ensure new pagination endpoint maintains compatibility (3 tests)"""

    def test_no_params_returns_paginated_results(self, gallery_client, large_photo_set):
        """
        GET /photos/paginated with no params returns valid paginated response

        Tests that endpoint works without any query parameters (backward compatible).
        """
        response = gallery_client.get('/api/gallery/photos/paginated')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have both photos and pagination keys
        assert 'photos' in data
        assert 'pagination' in data

        # Should return default page size
        assert len(data['photos']) <= 50  # Default limit

    def test_response_includes_photos_key(self, gallery_client, large_photo_set):
        """
        Response includes 'photos' key for consistency with existing /photos endpoint

        Tests that response format is compatible with existing code expecting 'photos' array.
        """
        response = gallery_client.get('/api/gallery/photos/paginated?limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'photos' in data
        assert isinstance(data['photos'], list)

    def test_photo_metadata_format_unchanged(self, gallery_client, large_photo_set):
        """
        Photo metadata format matches existing /photos endpoint

        Tests that individual photo objects have same structure as non-paginated endpoint.
        """
        # Get photo from paginated endpoint
        paginated_response = gallery_client.get('/api/gallery/photos/paginated?limit=1')
        paginated_data = json.loads(paginated_response.data)
        paginated_photo = paginated_data['photos'][0]

        # Get photo from non-paginated endpoint for comparison
        all_response = gallery_client.get('/api/gallery/photos')
        all_data = json.loads(all_response.data)
        all_photo = all_data['photos'][0]

        # Both should have same keys
        assert set(paginated_photo.keys()) == set(all_photo.keys())

        # Verify expected keys present
        required_keys = {'path', 'filename', 'size', 'timestamp', 'date'}
        assert required_keys.issubset(set(paginated_photo.keys()))
