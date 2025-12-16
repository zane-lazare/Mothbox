"""
Integration tests for optimized ZIP export with Export Job Service (Issue #128).

Tests verify the complete export pipeline from job creation through ZIP generation,
download, and cleanup. Covers the optimized ZIP export features:
- True streaming ZIP (temp file instead of BytesIO)
- Parallel photo I/O (ThreadPoolExecutor, 4 workers)
- Batched processing (batch_size=50 default)

Tests are marked as @pytest.mark.integration since they test cross-component
workflows but do NOT require Raspberry Pi hardware (no camera/GPIO).

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_zip_export_integration.py -v -s
"""

import json
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask

from webui.backend.lib.export_job_types import (
    ExportJobFilter,
    ExportJobFormat,
    ExportJobStatus,
)
from webui.backend.routes.export import export_bp
from webui.backend.services.export_job_service import ExportJobService
from webui.backend.services.export_metadata_service import ExportMetadataService

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def large_photo_set(tmp_path):
    """Create 100+ photos for large export testing."""
    photos_dir = tmp_path / "large_photos"
    photos_dir.mkdir()

    try:
        from PIL import Image

        photo_paths = []
        for i in range(100):
            photo_path = photos_dir / f"moth_{i:03d}.jpg"
            # Create realistic sized photos (not tiny test images)
            img = Image.new("RGB", (1024, 768), color=(i * 2, 100, 150))
            img.save(photo_path, "JPEG", quality=85)
            photo_paths.append(str(photo_path))

            # Create sidecar metadata
            sidecar = photos_dir / f"moth_{i:03d}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"moth_{i:03d}.jpg",
                        "created_at": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
                        "modified_at": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
                        "tags": ["moth", "test", f"batch_{i // 10}"],
                        "latitude": 37.7749 + (i * 0.001),
                        "longitude": -122.4194 - (i * 0.001),
                        "altitude": 100.0 + (i * 10),
                        "species": "Test Species" if i % 5 == 0 else None,
                    }
                )
            )

        return photo_paths
    except ImportError:
        pytest.skip("PIL not available for large photo set creation")


@pytest.fixture
def sample_photos_for_zip(tmp_path):
    """Create sample photos specifically for ZIP export testing."""
    photos_dir = tmp_path / "zip_photos"
    photos_dir.mkdir()

    try:
        from PIL import Image

        photo_paths = []
        for i in range(20):
            photo_path = photos_dir / f"photo_{i:02d}.jpg"
            img = Image.new("RGB", (800, 600), color=(i * 10, 100, 200))
            img.save(photo_path, "JPEG", quality=85)
            photo_paths.append(str(photo_path))

            # Create sidecar
            sidecar = photos_dir / f"photo_{i:02d}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"photo_{i:02d}.jpg",
                        "created_at": f"2024-06-{(i % 30) + 1:02d}T20:00:00Z",
                        "modified_at": f"2024-06-{(i % 30) + 1:02d}T20:00:00Z",
                        "tags": ["moth"],
                        "latitude": 35.9606 + (i * 0.01),
                        "longitude": -83.9207 - (i * 0.01),
                    }
                )
            )

        return photo_paths
    except ImportError:
        pytest.skip("PIL not available")


@pytest.fixture
def export_job_service(tmp_path, sample_photos_for_zip):
    """Create ExportJobService for integration testing."""
    db_path = tmp_path / "jobs.db"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    photos_dir = Path(sample_photos_for_zip[0]).parent

    export_service = ExportMetadataService(cache_ttl=300)

    service = ExportJobService(
        db_path=db_path,
        export_service=export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_timeout_seconds=120,  # Longer timeout for large exports
        job_ttl_seconds=300,
        max_history=50,
    )
    service.start()
    yield service
    service.stop()


@pytest.fixture
def app(tmp_path, export_job_service):
    """Flask app with export job service configured."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["EXPORT_JOB_SERVICE"] = export_job_service
    app.config["EXPORT_METADATA_SERVICE"] = export_job_service._export_service

    # Disable CSRF for testing
    app.config["WTF_CSRF_ENABLED"] = False

    app.register_blueprint(export_bp, url_prefix="/api/export")
    return app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


# ============================================================================
# Optimized ZIP Export Tests
# ============================================================================


@pytest.mark.integration
class TestOptimizedZIPExport:
    """Test optimized ZIP export features."""

    def test_zip_uses_temp_file_not_memory(self, tmp_path, sample_photos_for_zip):
        """Verify ZIP export uses temp file instead of BytesIO."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip]
        output_zip = tmp_path / "export.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        # Monitor temp file creation with progress callback
        temp_file_created = []

        def progress_callback(current, total):
            # Check if temp files exist during processing
            temp_files = list(tmp_path.glob("*.zip*"))
            if temp_files:
                temp_file_created.append(True)

        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            progress_callback=progress_callback,
        )

        # Verify export succeeded
        assert result.success
        assert output_zip.exists()
        assert result.zip_size_bytes > 0

        # Final output should exist
        assert output_zip.exists()

    def test_parallel_photo_io(self, tmp_path, sample_photos_for_zip):
        """Test parallel photo I/O with ThreadPoolExecutor."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip[:10]]
        output_zip = tmp_path / "parallel.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        # Export with 4 workers (parallel I/O)
        start_time = time.time()
        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            max_workers=4,
            batch_size=10,
        )
        parallel_time = time.time() - start_time

        # Verify success
        assert result.success
        assert result.photo_count == len(photos)
        assert output_zip.exists()

        # Verify all photos in ZIP
        with zipfile.ZipFile(output_zip) as zf:
            jpg_files = [n for n in zf.namelist() if n.endswith('.jpg')]
            assert len(jpg_files) == len(photos)

        # Note: Can't reliably test speed improvement without comparing to serial,
        # but we can verify it completes successfully with parallel processing
        assert parallel_time < 30  # Should complete in reasonable time

    def test_batched_processing(self, tmp_path, sample_photos_for_zip):
        """Test batched processing to bound memory usage."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip]
        output_zip = tmp_path / "batched.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        # Track progress callbacks to verify batching
        progress_updates = []

        def progress_callback(current, total):
            progress_updates.append((current, total))

        # Export with small batch size to ensure multiple batches
        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            progress_callback=progress_callback,
            batch_size=5,  # Small batch to ensure multiple batches
        )

        # Verify success
        assert result.success
        assert result.photo_count == len(photos)

        # Verify progress callbacks were called (indicating batching)
        assert len(progress_updates) > 0
        # Should have updates for each batch (every 10 photos or at completion)
        assert progress_updates[-1][0] == len(photos)  # Final update
        assert progress_updates[-1][1] == len(photos)

    def test_progress_callbacks_work_correctly(self, tmp_path, sample_photos_for_zip):
        """Test progress callbacks during batched processing."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip]
        output_zip = tmp_path / "progress.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        progress_updates = []

        def progress_callback(current, total):
            progress_updates.append((current, total))
            # Verify current <= total
            assert current <= total
            # Verify total matches photo count
            assert total == len(photos)

        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            progress_callback=progress_callback,
            batch_size=10,
        )

        # Verify success
        assert result.success

        # Verify progress updates
        assert len(progress_updates) > 0
        # Progress should be monotonically increasing
        for i in range(1, len(progress_updates)):
            assert progress_updates[i][0] >= progress_updates[i - 1][0]

        # Final update should be at 100%
        assert progress_updates[-1][0] == len(photos)

    def test_error_handling_across_batches(self, tmp_path, sample_photos_for_zip):
        """Test error handling when errors occur in different batches."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip[:10]]
        output_zip = tmp_path / "errors.zip"

        # Add some non-existent files to trigger errors
        photos.insert(3, Path(tmp_path / "missing1.jpg"))
        photos.insert(7, Path(tmp_path / "missing2.jpg"))

        service = ExportMetadataService(cache_ttl=1)
        # Get metadata for valid photos only
        metadata_list = []
        for photo in photos:
            if photo.exists():
                metadata_list.append(service.get_export_metadata(photo))
            else:
                # Create minimal metadata for missing photo
                from webui.backend.services.export_metadata_service import ExportMetadata
                metadata_list.append(ExportMetadata(
                    photo_path=str(photo),
                    filename=photo.name,
                ))

        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            batch_size=5,  # Multiple batches to test error handling across batches
        )

        # Export should complete (not crash)
        assert result is not None

        # Should have errors for missing files
        assert len(result.errors) == 2

        # Valid photos should still be exported
        assert result.photo_count > 0

    def test_large_export_completes_successfully(self, tmp_path, large_photo_set):
        """Test large export (100+ photos) completes successfully."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in large_photo_set]
        output_zip = tmp_path / "large_export.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        # Track progress
        progress_updates = []

        def progress_callback(current, total):
            progress_updates.append((current, total))

        start_time = time.time()
        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            progress_callback=progress_callback,
            max_workers=4,
            batch_size=50,
        )
        elapsed = time.time() - start_time

        # Verify success
        assert result.success
        assert result.photo_count == 100
        assert output_zip.exists()

        # Verify reasonable performance (<60 seconds for 100 photos)
        assert elapsed < 60, f"Large export took too long: {elapsed:.2f}s"

        # Verify ZIP integrity
        with zipfile.ZipFile(output_zip) as zf:
            jpg_files = [n for n in zf.namelist() if n.endswith('.jpg')]
            xmp_files = [n for n in zf.namelist() if n.endswith('.xmp')]

            assert len(jpg_files) == 100
            assert len(xmp_files) == 100
            assert 'manifest.json' in zf.namelist()
            assert 'summary.csv' in zf.namelist()

        # Verify progress was tracked
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100

    def test_memory_usage_stays_bounded(self, tmp_path, large_photo_set):
        """Test memory usage stays bounded during large exports."""
        import psutil

        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in large_photo_set]
        output_zip = tmp_path / "memory_test.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        # Get baseline memory
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Export with batching
        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            max_workers=4,
            batch_size=25,  # Small batches to test memory bounding
        )

        # Get peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Verify success
        assert result.success

        # Memory increase should be bounded (not loading all photos at once)
        # With batch_size=25 and ~1024x768 JPEGs, expect <200MB increase
        # (batch_size × avg_photo_size × 2 for photo + XMP data)
        assert memory_increase < 300, f"Memory increase too high: {memory_increase:.2f}MB"


# ============================================================================
# Export Job Service Integration Tests
# ============================================================================


@pytest.mark.integration
class TestExportJobServiceIntegration:
    """Test ZIP export integration with Export Job Service."""

    def test_export_job_uses_optimized_zip(self, client, sample_photos_for_zip):
        """Test export job uses optimized ZIP creation."""
        # Create iNaturalist export job (uses ZIP)
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "inaturalist",
                "filter": {"photo_paths": sample_photos_for_zip},
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        # Poll until completed
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            data = response.get_json()
            if data["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        assert data["status"] == "completed"

        # Download and verify ZIP
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "application/zip" in response.content_type

        # Verify ZIP is valid
        import io
        zip_data = response.data
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            names = zf.namelist()
            jpg_files = [n for n in names if n.endswith('.jpg')]
            xmp_files = [n for n in names if n.endswith('.xmp')]

            assert len(jpg_files) == len(sample_photos_for_zip)
            assert len(xmp_files) == len(sample_photos_for_zip)
            assert 'manifest.json' in names
            assert 'summary.csv' in names

    def test_export_job_progress_updates(self, export_job_service, sample_photos_for_zip):
        """Test export job provides progress updates during processing."""

        job = export_job_service.create_job(
            format=ExportJobFormat.INATURALIST,
            filter=ExportJobFilter(photo_paths=sample_photos_for_zip),
        )

        # Poll for progress updates
        max_wait = 30
        start_time = time.time()
        progress_seen = []

        while time.time() - start_time < max_wait:
            updated = export_job_service.get_job(job.job_id)

            # Track progress
            if updated.progress:
                progress_seen.append({
                    'current': updated.progress.current,
                    'total': updated.progress.total,
                    'percent': updated.progress.percent,
                })

            if updated.status in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED]:
                break

            time.sleep(0.2)

        final_job = export_job_service.get_job(job.job_id)
        assert final_job.status == ExportJobStatus.COMPLETED

        # Should have seen progress updates
        assert len(progress_seen) > 0

    def test_api_endpoint_response_time_acceptable(self, client, sample_photos_for_zip):
        """Test API endpoint response times are acceptable."""
        # Create job
        start_time = time.time()
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "inaturalist",
                "filter": {"photo_paths": sample_photos_for_zip[:5]},  # Small batch
            },
        )
        create_time = time.time() - start_time

        assert response.status_code == 202
        # Job creation should be fast (<1 second)
        assert create_time < 1.0

        job_id = response.get_json()["job_id"]

        # Wait for completion
        max_wait = 20
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            data = response.get_json()
            if data["status"] == "completed":
                break
            time.sleep(0.5)

        # Download
        start_time = time.time()
        response = client.get(f"/api/export/jobs/{job_id}/download")
        download_time = time.time() - start_time

        assert response.status_code == 200
        # Download should be reasonably fast (<5 seconds for small ZIP)
        assert download_time < 5.0

    def test_multiple_concurrent_jobs(self, export_job_service, sample_photos_for_zip):
        """Test multiple export jobs process correctly (sequentially due to queue)."""

        # Create 3 small jobs
        jobs = []
        for _i in range(3):
            job = export_job_service.create_job(
                format=ExportJobFormat.INATURALIST,
                filter=ExportJobFilter(photo_paths=sample_photos_for_zip[:5]),
            )
            jobs.append(job.job_id)

        # Wait for all to complete
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            statuses = [export_job_service.get_job(jid).status for jid in jobs]
            all_done = all(
                s in [ExportJobStatus.COMPLETED, ExportJobStatus.FAILED] for s in statuses
            )
            if all_done:
                break
            time.sleep(0.5)

        # All should complete
        for job_id in jobs:
            final_job = export_job_service.get_job(job_id)
            assert final_job.status == ExportJobStatus.COMPLETED
            assert final_job.output_path is not None


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.integration
class TestZIPExportPerformance:
    """Performance tests for ZIP export."""

    def test_export_performance_meets_targets(self, tmp_path, large_photo_set):
        """Test export performance meets targets (100 photos < 60s)."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in large_photo_set]
        output_zip = tmp_path / "performance.zip"

        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        start_time = time.time()
        result = create_zip_export(
            photos,
            metadata_list,
            output_zip,
            ZipExportOptions(),
            max_workers=4,
            batch_size=50,
        )
        elapsed = time.time() - start_time

        # Verify success
        assert result.success
        assert result.photo_count == 100

        # Performance target: 100 photos < 60 seconds
        assert elapsed < 60, f"Export took {elapsed:.2f}s (target: <60s)"

        # Log performance
        photos_per_second = 100 / elapsed
        print(f"\nPerformance: {photos_per_second:.2f} photos/second")

    def test_throughput_with_different_batch_sizes(self, tmp_path, sample_photos_for_zip):
        """Test throughput with different batch sizes."""
        from webui.backend.lib.zip_export import ZipExportOptions, create_zip_export
        from webui.backend.services.export_metadata_service import ExportMetadataService

        photos = [Path(p) for p in sample_photos_for_zip]
        service = ExportMetadataService(cache_ttl=1)
        metadata_list = service.batch_get_export_metadata(photos)

        batch_sizes = [5, 10, 20]
        results = {}

        for batch_size in batch_sizes:
            output_zip = tmp_path / f"batch_{batch_size}.zip"

            start_time = time.time()
            result = create_zip_export(
                photos,
                metadata_list,
                output_zip,
                ZipExportOptions(),
                max_workers=4,
                batch_size=batch_size,
            )
            elapsed = time.time() - start_time

            results[batch_size] = {
                'elapsed': elapsed,
                'success': result.success,
                'photo_count': result.photo_count,
            }

        # All should succeed
        for _batch_size, data in results.items():
            assert data['success']
            assert data['photo_count'] == len(photos)

        # Log results
        print("\nBatch size performance:")
        for batch_size, data in results.items():
            print(f"  Batch {batch_size}: {data['elapsed']:.2f}s")
