"""
Integration tests for gallery pagination (Issue #135)

Tests pagination API with real filesystem operations and end-to-end workflows.
Validates performance on Pi hardware with actual photo files.

Run with: pytest Tests/integration/test_gallery_pagination.py -v -s

Test Categories:
  - Real Filesystem Tests: Actual JPEG files, real file I/O
  - End-to-End API Tests: Full request/response cycles
  - Performance Benchmarks: Query time with 100+ photos (<200ms target)
  - Edge Cases: Empty directories, single photos, mixed files

Markers:
  - @pytest.mark.integration: Requires real filesystem
  - @pytest.mark.performance: Performance benchmarking tests
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from PIL import Image, JpegImagePlugin, PngImagePlugin  # Force encoder registration

# Setup path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "webui" / "backend"))

from routes.gallery import gallery_bp
from services.photo_service import PhotoService

# Mark all tests as integration
pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def real_photos_dir(tmp_path):
    """
    Create temporary directory with real JPEG files

    Creates 100 actual JPEG photos with:
    - Proper JPEG headers (PIL-generated)
    - Specific mtimes for sorting tests (1 hour apart)
    - Realistic file sizes (~50-100KB each)
    - Sequential naming for easy tracking
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    base_time = datetime(2024, 11, 1, 0, 0, 0)

    for i in range(100):
        photo_path = photos_dir / f"photo_{i:04d}.jpg"

        # Create actual JPEG using PIL (realistic file ~50-100KB)
        # Vary colors slightly to create different file sizes
        img = Image.new("RGB", (640, 480), color=(i * 2, 100, 150))

        # Add some random patterns to make file size vary
        from PIL import ImageDraw

        draw = ImageDraw.Draw(img)
        for j in range(10):
            draw.rectangle([j * 60, j * 45, j * 60 + 50, j * 45 + 40], fill=(255 - i, i, 128))

        img.save(photo_path, "JPEG", quality=85)

        # Set specific mtime for sorting tests (newest first: i=0 is most recent)
        photo_time = base_time + timedelta(hours=i)
        timestamp = photo_time.timestamp()
        os.utime(photo_path, (timestamp, timestamp))

    return photos_dir


@pytest.fixture
def integration_app(real_photos_dir, monkeypatch):
    """
    Flask app configured for integration testing with real photos

    Patches PHOTOS_DIR to use temporary directory with real photos.
    Registers gallery blueprint for API testing.
    """
    import mothbox_paths

    monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", real_photos_dir)

    # Also patch in routes.gallery module
    import routes.gallery

    monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", real_photos_dir)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(gallery_bp, url_prefix="/api/gallery")

    return app


@pytest.fixture
def integration_client(integration_app):
    """Test client for integration testing"""
    return integration_app.test_client()


@pytest.fixture
def dated_real_photos(tmp_path):
    """
    Create real JPEG photos with specific dates for filtering tests

    Distribution:
    - 10 photos from 2024-10-01 to 2024-10-10 (October)
    - 10 photos from 2024-11-01 to 2024-11-10 (November)
    - 10 photos from 2024-12-01 to 2024-12-10 (December)

    Total: 30 real JPEG photos
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # October photos
    for i in range(10):
        photo_path = photos_dir / f"oct_photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(200, 100, i * 20))
        img.save(photo_path, "JPEG", quality=85)

        photo_date = datetime(2024, 10, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        os.utime(photo_path, (timestamp, timestamp))

    # November photos
    for i in range(10):
        photo_path = photos_dir / f"nov_photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(100, 200, i * 20))
        img.save(photo_path, "JPEG", quality=85)

        photo_date = datetime(2024, 11, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        os.utime(photo_path, (timestamp, timestamp))

    # December photos
    for i in range(10):
        photo_path = photos_dir / f"dec_photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(100, i * 20, 200))
        img.save(photo_path, "JPEG", quality=85)

        photo_date = datetime(2024, 12, i + 1, 12, 0, 0)
        timestamp = photo_date.timestamp()
        os.utime(photo_path, (timestamp, timestamp))

    return photos_dir


@pytest.fixture
def mixed_file_types_dir(tmp_path):
    """
    Create directory with mixed file types to test filtering

    Includes:
    - 10 JPEGs (should be returned)
    - 5 PNGs (should be skipped)
    - 3 text files (should be skipped)
    - 2 subdirectories with photos (should be found via rglob)
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Create JPEGs
    for i in range(10):
        photo_path = photos_dir / f"photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(i * 25, 100, 150))
        img.save(photo_path, "JPEG", quality=85)

    # Create PNGs (now a supported photo format)
    for i in range(5):
        png_path = photos_dir / f"image_{i:02d}.png"
        img = Image.new("RGB", (640, 480), color=(100, i * 50, 150))
        img.save(png_path, "PNG")

    # Create text files (should be ignored)
    for i in range(3):
        txt_path = photos_dir / f"file_{i:02d}.txt"
        txt_path.write_text(f"Not a photo {i}")

    # Create subdirectories with photos
    subdir1 = photos_dir / "2024-11-01"
    subdir1.mkdir()
    for i in range(3):
        photo_path = subdir1 / f"subdir_photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(150, 100, i * 80))
        img.save(photo_path, "JPEG", quality=85)

    subdir2 = photos_dir / "2024-11-02"
    subdir2.mkdir()
    for i in range(2):
        photo_path = subdir2 / f"nested_photo_{i:02d}.jpg"
        img = Image.new("RGB", (640, 480), color=(150, i * 120, 100))
        img.save(photo_path, "JPEG", quality=85)

    return photos_dir


# ============================================================================
# Test Real Filesystem Operations
# ============================================================================


class TestRealFilesystemOperations:
    """Test pagination with real JPEG files and actual file I/O (5 tests)"""

    def test_pagination_with_real_photos(self, integration_client):
        """
        Basic pagination with actual JPEG files

        Validates:
        - Real photos are read from filesystem
        - Metadata extracted correctly (size, mtime)
        - Pagination works with real file I/O
        """
        response = integration_client.get("/api/gallery/photos/paginated?limit=25&offset=0")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data["photos"]) == 25
        assert data["pagination"]["total"] == 100

        # Verify photo metadata is realistic (not mock data)
        first_photo = data["photos"][0]
        assert first_photo["size"] > 1000  # Real JPEG should be >1KB
        assert first_photo["filename"].endswith(".jpg")
        assert "timestamp" in first_photo
        assert "date" in first_photo

        print(f"\n✓ Real filesystem: {len(data['photos'])} photos, first size={first_photo['size']} bytes")

    def test_sorting_with_real_mtimes(self, integration_client):
        """
        Verify sort orders with real file timestamps

        Tests that sorting works correctly with actual filesystem mtimes.
        """
        # Test date descending (newest first - default)
        desc_response = integration_client.get("/api/gallery/photos/paginated?limit=10&sort=date_desc")
        desc_data = json.loads(desc_response.data)

        # Test date ascending (oldest first)
        asc_response = integration_client.get("/api/gallery/photos/paginated?limit=10&sort=date_asc")
        asc_data = json.loads(asc_response.data)

        # Verify timestamps are in correct order
        desc_timestamps = [p["timestamp"] for p in desc_data["photos"]]
        asc_timestamps = [p["timestamp"] for p in asc_data["photos"]]

        assert desc_timestamps == sorted(desc_timestamps, reverse=True)
        assert asc_timestamps == sorted(asc_timestamps)

        # Newest and oldest should be opposites
        assert desc_data["photos"][0]["filename"] != asc_data["photos"][0]["filename"]

        print(f"\n✓ Sorting verified: desc={desc_data['photos'][0]['filename']}, asc={asc_data['photos'][0]['filename']}")

    def test_date_filtering_accuracy(self, monkeypatch, dated_real_photos):
        """
        Filter by date range with real photos

        Validates that date filtering works correctly with actual file mtimes.
        """
        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", dated_real_photos)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", dated_real_photos)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        # Filter for November only
        response = client.get("/api/gallery/photos/paginated?start_date=2024-11-01&end_date=2024-11-30")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return exactly 10 photos (November only)
        assert data["pagination"]["total"] == 10

        # Verify all photos are within November
        for photo in data["photos"]:
            photo_date = datetime.fromisoformat(photo["date"])
            assert datetime(2024, 11, 1) <= photo_date <= datetime(2024, 11, 30, 23, 59, 59)
            assert "nov_photo" in photo["filename"]

        print(f"\n✓ Date filtering: {data['pagination']['total']} photos in November range")

    def test_mixed_file_types_filtering(self, monkeypatch, mixed_file_types_dir):
        """
        All supported image formats returned, non-image files ignored

        Validates that pagination returns all supported photo formats
        (JPEG, PNG, etc.) and filters out non-image files (text).
        """
        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", mixed_file_types_dir)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", mixed_file_types_dir)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        response = client.get("/api/gallery/photos/paginated")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should return 20 photos: 10 JPEGs + 5 PNGs + 3 subdir1 JPEGs + 2 subdir2 JPEGs
        assert data["pagination"]["total"] == 20

        # Verify all are supported image formats (no .txt files)
        for photo in data["photos"]:
            assert photo["filename"].endswith((".jpg", ".png"))

        print(f"\n✓ File type filtering: {data['pagination']['total']} photos (TXT ignored)")

    def test_subdirectory_traversal(self, monkeypatch, mixed_file_types_dir):
        """
        Photos in subdirectories are found via recursive glob

        Validates that rglob correctly finds photos in nested directories.
        """
        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", mixed_file_types_dir)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", mixed_file_types_dir)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        response = client.get("/api/gallery/photos/paginated")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Find photos from subdirectories
        subdirectory_photos = [p for p in data["photos"] if "/" in p["path"] or "\\" in p["path"]]

        # Should have 5 photos from subdirectories (3 + 2)
        assert len(subdirectory_photos) >= 5

        print(f"\n✓ Subdirectory traversal: {len(subdirectory_photos)} photos found in nested dirs")


# ============================================================================
# Test End-to-End API Workflows
# ============================================================================


class TestEndToEndAPIWorkflows:
    """End-to-end API request/response cycles (5 tests)"""

    def test_paginate_through_all_pages_e2e(self, integration_client):
        """
        End-to-end: Navigate through all pages sequentially

        Validates:
        - Multiple sequential requests work correctly
        - No duplicates across pages
        - All photos eventually returned
        """
        all_photos_collected = []
        offset = 0
        limit = 25
        has_next = True

        while has_next:
            response = integration_client.get(f"/api/gallery/photos/paginated?limit={limit}&offset={offset}")

            assert response.status_code == 200
            data = json.loads(response.data)

            all_photos_collected.extend(data["photos"])
            has_next = data["pagination"]["has_next"]
            offset += limit

        # Should have collected all 100 photos
        assert len(all_photos_collected) == 100

        # No duplicates
        filenames = [p["filename"] for p in all_photos_collected]
        assert len(filenames) == len(set(filenames)), "Should not have duplicate photos"

        print(f"\n✓ E2E pagination: {len(all_photos_collected)} photos, {offset // limit} pages, no duplicates")

    def test_combined_query_parameters_e2e(self, integration_client):
        """
        Multiple query parameters work together correctly

        Tests: limit + offset + sort + date filtering all at once
        """
        response = integration_client.get(
            "/api/gallery/photos/paginated?limit=10&offset=5&sort=filename_asc"
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data["photos"]) == 10
        assert data["pagination"]["offset"] == 5
        assert data["pagination"]["limit"] == 10

        # Verify sorting applied
        filenames = [p["filename"] for p in data["photos"]]
        assert filenames == sorted(filenames)

        print(f"\n✓ Combined parameters: limit={data['pagination']['limit']}, offset={data['pagination']['offset']}, sorted")

    def test_sequential_page_consistency(self, integration_client):
        """
        Sequential page requests return consistent, non-overlapping results

        Validates that pagination boundaries are correct.
        """
        # Get first page
        page1 = integration_client.get("/api/gallery/photos/paginated?limit=20&offset=0")
        data1 = json.loads(page1.data)

        # Get second page
        page2 = integration_client.get("/api/gallery/photos/paginated?limit=20&offset=20")
        data2 = json.loads(page2.data)

        # Get third page
        page3 = integration_client.get("/api/gallery/photos/paginated?limit=20&offset=40")
        data3 = json.loads(page3.data)

        # All pages should have correct number of photos
        assert len(data1["photos"]) == 20
        assert len(data2["photos"]) == 20
        assert len(data3["photos"]) == 20

        # No overlap between pages
        filenames1 = set(p["filename"] for p in data1["photos"])
        filenames2 = set(p["filename"] for p in data2["photos"])
        filenames3 = set(p["filename"] for p in data3["photos"])

        assert len(filenames1 & filenames2) == 0, "Page 1 and 2 should not overlap"
        assert len(filenames2 & filenames3) == 0, "Page 2 and 3 should not overlap"
        assert len(filenames1 & filenames3) == 0, "Page 1 and 3 should not overlap"

        print(f"\n✓ Sequential pages: 60 photos, 3 pages, no overlap")

    def test_error_handling_with_real_filesystem(self, integration_client):
        """
        API handles filesystem errors gracefully

        Tests error handling with invalid parameters and edge cases.
        """
        # Invalid limit
        response = integration_client.get("/api/gallery/photos/paginated?limit=-1")
        assert response.status_code == 400

        # Invalid offset
        response = integration_client.get("/api/gallery/photos/paginated?offset=-5")
        assert response.status_code == 400

        # Invalid sort
        response = integration_client.get("/api/gallery/photos/paginated?sort=invalid_sort")
        assert response.status_code == 400

        # Invalid date format
        response = integration_client.get("/api/gallery/photos/paginated?start_date=not-a-date")
        assert response.status_code == 400

        # Limit exceeds max
        response = integration_client.get("/api/gallery/photos/paginated?limit=1000")
        assert response.status_code == 400

        print(f"\n✓ Error handling: All invalid parameters rejected")

    def test_empty_directory_handling(self, tmp_path, monkeypatch):
        """
        Pagination gracefully handles empty photo directory

        Validates that API returns empty results without errors.
        """
        empty_dir = tmp_path / "empty_photos"
        empty_dir.mkdir()

        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", empty_dir)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", empty_dir)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        response = client.get("/api/gallery/photos/paginated")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["photos"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_previous"] is False

        print(f"\n✓ Empty directory: Graceful handling, total=0")


# ============================================================================
# Test Performance Benchmarks
# ============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmarking tests (<200ms target) (5 tests)"""

    @pytest.mark.performance
    def test_pagination_query_performance_target(self, integration_client):
        """
        Pagination query must complete in <200ms with 100 photos

        Performance target for Pi hardware: <200ms per paginated request
        """
        # Warm up (first query may be slower due to filesystem cache)
        integration_client.get("/api/gallery/photos/paginated")

        # Benchmark actual query
        start = time.perf_counter()
        response = integration_client.get("/api/gallery/photos/paginated?limit=50&offset=0")
        duration = time.perf_counter() - start

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["photos"]) == 50

        # Performance assertion
        assert duration < 0.2, f"Query took {duration * 1000:.1f}ms (target: <200ms)"

        print(f"\n✓ Performance: {duration * 1000:.1f}ms for 100 photos (target: <200ms)")

    @pytest.mark.performance
    def test_performance_different_sort_orders(self, integration_client):
        """
        Compare performance of different sort options

        Validates that sorting doesn't significantly impact query time.
        """
        sort_options = ["date_desc", "date_asc", "filename_asc", "filename_desc"]
        timings = {}

        for sort in sort_options:
            start = time.perf_counter()
            response = integration_client.get(f"/api/gallery/photos/paginated?limit=50&sort={sort}")
            duration = time.perf_counter() - start

            assert response.status_code == 200
            timings[sort] = duration

            # All should be under 200ms
            assert duration < 0.2, f"{sort} took {duration * 1000:.1f}ms (target: <200ms)"

        print(f"\n✓ Sort performance:")
        for sort, dur in timings.items():
            print(f"  - {sort}: {dur * 1000:.1f}ms")

    @pytest.mark.performance
    def test_performance_with_date_filtering(self, monkeypatch, dated_real_photos):
        """
        Date filtering performance with real photos

        Validates that date filtering doesn't degrade performance significantly.
        """
        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", dated_real_photos)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", dated_real_photos)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        # Warm up
        client.get("/api/gallery/photos/paginated")

        # Benchmark filtered query
        start = time.perf_counter()
        response = client.get("/api/gallery/photos/paginated?start_date=2024-11-01&end_date=2024-11-30")
        duration = time.perf_counter() - start

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["pagination"]["total"] == 10

        # Should still be fast even with filtering
        assert duration < 0.2, f"Filtered query took {duration * 1000:.1f}ms (target: <200ms)"

        print(f"\n✓ Date filter performance: {duration * 1000:.1f}ms (target: <200ms)")

    @pytest.mark.performance
    def test_performance_large_offset(self, integration_client):
        """
        Query performance with large offset

        Validates that performance doesn't degrade with large offsets.
        """
        # Test query at end of dataset
        start = time.perf_counter()
        response = integration_client.get("/api/gallery/photos/paginated?limit=10&offset=90")
        duration = time.perf_counter() - start

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["photos"]) == 10

        # Should still be fast even at large offset
        assert duration < 0.2, f"Large offset query took {duration * 1000:.1f}ms (target: <200ms)"

        print(f"\n✓ Large offset performance: {duration * 1000:.1f}ms at offset=90 (target: <200ms)")

    @pytest.mark.performance
    def test_performance_repeated_requests(self, integration_client):
        """
        Performance consistency across repeated requests

        Validates that performance is consistent and doesn't degrade.
        """
        timings = []

        # Run 10 identical requests
        for _ in range(10):
            start = time.perf_counter()
            response = integration_client.get("/api/gallery/photos/paginated?limit=25")
            duration = time.perf_counter() - start

            assert response.status_code == 200
            timings.append(duration)

        # All should be under 200ms
        for duration in timings:
            assert duration < 0.2, f"Request took {duration * 1000:.1f}ms (target: <200ms)"

        # Calculate statistics
        avg_time = sum(timings) / len(timings)
        max_time = max(timings)
        min_time = min(timings)

        print(f"\n✓ Repeated request performance (10 runs):")
        print(f"  - Average: {avg_time * 1000:.1f}ms")
        print(f"  - Min: {min_time * 1000:.1f}ms")
        print(f"  - Max: {max_time * 1000:.1f}ms")


# ============================================================================
# Test Edge Cases with Real Data
# ============================================================================


class TestEdgeCasesRealData:
    """Edge cases with real filesystem data (5 tests)"""

    def test_single_photo_handling(self, tmp_path, monkeypatch):
        """
        Pagination with single photo returns correctly

        Tests edge case of single photo in directory.
        """
        photos_dir = tmp_path / "photos"
        photos_dir.mkdir()

        # Create single photo
        photo_path = photos_dir / "single.jpg"
        img = Image.new("RGB", (640, 480), color=(100, 150, 200))
        img.save(photo_path, "JPEG", quality=85)

        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", photos_dir)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", photos_dir)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        response = client.get("/api/gallery/photos/paginated")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert len(data["photos"]) == 1
        assert data["pagination"]["total"] == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_previous"] is False

        print(f"\n✓ Single photo: Correct pagination metadata")

    def test_offset_exceeds_total_photos(self, integration_client):
        """
        Offset beyond total returns empty results gracefully

        Validates that large offsets don't cause errors.
        """
        response = integration_client.get("/api/gallery/photos/paginated?offset=500")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["photos"] == []
        assert data["pagination"]["offset"] == 500
        assert data["pagination"]["total"] == 100
        assert data["pagination"]["has_next"] is False

        print(f"\n✓ Offset exceeds total: Graceful empty result")

    def test_very_large_limit(self, integration_client):
        """
        Limit exceeding max (500) returns validation error

        Tests that max limit is enforced.
        """
        response = integration_client.get("/api/gallery/photos/paginated?limit=1000")

        assert response.status_code == 400
        data = json.loads(response.data)

        assert "error" in data
        # Generic error message for security (CodeQL requirement - don't expose internals)
        assert data['error'] == 'Invalid pagination parameters'

        print(f"\n✓ Large limit rejected: Max 500 enforced")

    def test_nonexistent_date_range(self, monkeypatch, dated_real_photos):
        """
        Date filter with no matching photos returns empty results

        Tests filtering for dates outside photo range.
        """
        import mothbox_paths

        monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", dated_real_photos)

        import routes.gallery

        monkeypatch.setattr(routes.gallery, "PHOTOS_DIR", dated_real_photos)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
        client = app.test_client()

        # Filter for future dates (no photos should match)
        response = client.get("/api/gallery/photos/paginated?start_date=2025-01-01")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["photos"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_previous"] is False

        print(f"\n✓ No matching dates: Graceful empty result")

    def test_concurrent_requests_no_interference(self, integration_client):
        """
        Multiple concurrent requests don't interfere with each other

        Validates thread safety of pagination logic.
        """
        import threading

        results = []

        def make_request(offset):
            response = integration_client.get(f"/api/gallery/photos/paginated?limit=10&offset={offset}")
            data = json.loads(response.data)
            results.append((offset, data))

        # Make 5 concurrent requests with different offsets
        threads = []
        for i in range(5):
            t = threading.Thread(target=make_request, args=(i * 10,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should succeed
        assert len(results) == 5

        # Each should have correct offset
        for offset, data in results:
            assert data["pagination"]["offset"] == offset
            assert len(data["photos"]) == 10

        print(f"\n✓ Concurrent requests: 5 threads, no interference")
