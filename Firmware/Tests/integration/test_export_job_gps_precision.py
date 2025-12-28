"""
Integration tests for GPS precision in export jobs (Issue #288).

Tests the complete GPS precision flow from job creation with gps_precision option
through to verifying rounded coordinates in output files.

Tests are marked as @pytest.mark.integration since they test cross-component
workflows but do NOT require Raspberry Pi hardware (no camera/GPIO).

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_export_job_gps_precision.py -v -s
"""

import csv
import json
import os
import sys
import time
from io import StringIO
from pathlib import Path

import pytest

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask

from webui.backend.routes.export import export_bp
from webui.backend.services.export_job_service import ExportJobService
from webui.backend.services.export_metadata_service import ExportMetadataService

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_photos_with_precise_gps(tmp_path):
    """Create sample photo files with high-precision GPS coordinates."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # High-precision coordinates for testing
    test_lat = 37.774900123456
    test_lon = -122.419400123456

    try:
        from PIL import Image

        photo_paths = []
        for i in range(3):
            photo_path = photos_dir / f"test_photo_{i}.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(photo_path, "JPEG", quality=85)
            photo_paths.append(str(photo_path))

            # Create sidecar metadata with high-precision GPS
            sidecar = photos_dir / f"test_photo_{i}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"test_photo_{i}.jpg",
                        "created_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "modified_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "tags": ["moth", "test"],
                        "latitude": test_lat + (i * 0.000001),  # Very small offset
                        "longitude": test_lon - (i * 0.000001),
                        "altitude": 100.0,
                        "species": "Actias luna",
                    }
                )
            )

        return photo_paths
    except ImportError:
        # Fallback to minimal JPEG if PIL not available
        photo_paths = []
        for i in range(3):
            photo_path = photos_dir / f"test_photo_{i}.jpg"
            # Minimal valid JPEG
            header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            footer = b"\xFF\xD9"
            padding = b"\x00" * 100
            photo_path.write_bytes(header + padding + footer)
            photo_paths.append(str(photo_path))

            # Create sidecar
            sidecar = photos_dir / f"test_photo_{i}.jpg.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "version": "1.1",
                        "photo_filename": f"test_photo_{i}.jpg",
                        "created_at": f"2024-01-{15+i:02d}T10:00:00Z",
                        "latitude": test_lat + (i * 0.000001),
                        "longitude": test_lon - (i * 0.000001),
                        "altitude": 100.0,
                        "tags": ["moth"],
                        "species": "Actias luna",
                    }
                )
            )

        return photo_paths


@pytest.fixture
def export_job_service(tmp_path, sample_photos_with_precise_gps):
    """Create ExportJobService for integration testing."""
    db_path = tmp_path / "jobs.db"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    photos_dir = Path(sample_photos_with_precise_gps[0]).parent

    export_service = ExportMetadataService(cache_ttl=300)

    service = ExportJobService(
        db_path=db_path,
        export_service=export_service,
        photos_dir=photos_dir,
        temp_dir=temp_dir,
        job_timeout_seconds=30,
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


def wait_for_job_completion(client, job_id, max_wait=30):
    """Wait for job to complete and return final status data."""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = client.get(f"/api/export/jobs/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        status = data["status"]

        if status in ["completed", "failed", "cancelled"]:
            return data

        time.sleep(0.5)

    raise TimeoutError(f"Job {job_id} did not complete within {max_wait} seconds")


# ============================================================================
# GPS Precision Integration Tests
# ============================================================================


@pytest.mark.integration
class TestGpsPrecisionInExportJobs:
    """Test GPS precision option works end-to-end through export job queue."""

    def test_darwin_core_with_gps_precision(self, client, sample_photos_with_precise_gps):
        """Darwin Core CSV export applies GPS precision from job options."""
        # Create job with gps_precision option
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "filter": {"photo_paths": sample_photos_with_precise_gps},
                "options": {"gps_precision": 2},  # 2 decimal places
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        # Wait for completion
        data = wait_for_job_completion(client, job_id)
        assert data["status"] == "completed"

        # Download and verify CSV content
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200

        # Parse CSV
        csv_content = response.data.decode("utf-8")
        reader = csv.DictReader(StringIO(csv_content))
        rows = list(reader)

        # Verify coordinates are rounded to 2 decimal places
        for row in rows:
            lat = float(row["decimalLatitude"])
            lon = float(row["decimalLongitude"])

            # Should be 37.77 (rounded from 37.774900...)
            assert lat == pytest.approx(37.77, abs=0.01)
            # Should be -122.42 (rounded from -122.419400...)
            assert lon == pytest.approx(-122.42, abs=0.01)

    def test_json_export_with_gps_precision(self, client, sample_photos_with_precise_gps):
        """JSON export applies GPS precision from job options."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos_with_precise_gps},
                "options": {"gps_precision": 3},  # 3 decimal places
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        data = wait_for_job_completion(client, job_id)
        assert data["status"] == "completed"

        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200

        json_data = json.loads(response.data.decode("utf-8"))
        results = json_data["results"]

        for result in results:
            lat = result["location"]["latitude"]
            lon = result["location"]["longitude"]

            # Should be 37.775 (rounded from 37.774900...)
            assert lat == pytest.approx(37.775, abs=0.001)
            # Should be -122.419 (rounded from -122.419400...)
            assert lon == pytest.approx(-122.419, abs=0.001)

    def test_csv_export_with_gps_precision(self, client, sample_photos_with_precise_gps):
        """Generic CSV export applies GPS precision from job options."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "csv",
                "filter": {"photo_paths": sample_photos_with_precise_gps},
                "options": {"gps_precision": 1},  # 1 decimal place
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        data = wait_for_job_completion(client, job_id)
        assert data["status"] == "completed"

        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200

        csv_content = response.data.decode("utf-8")
        reader = csv.DictReader(StringIO(csv_content))
        rows = list(reader)

        for row in rows:
            lat = float(row["latitude"])
            lon = float(row["longitude"])

            # Should be 37.8 (rounded from 37.774900...)
            assert lat == pytest.approx(37.8, abs=0.1)
            # Should be -122.4 (rounded from -122.419400...)
            assert lon == pytest.approx(-122.4, abs=0.1)

    def test_gps_precision_zero(self, client, sample_photos_with_precise_gps):
        """GPS precision 0 rounds to whole numbers."""
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "json",
                "filter": {"photo_paths": sample_photos_with_precise_gps},
                "options": {"gps_precision": 0},
            },
        )
        assert response.status_code == 202
        job_id = response.get_json()["job_id"]

        data = wait_for_job_completion(client, job_id)
        assert data["status"] == "completed"

        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200

        json_data = json.loads(response.data.decode("utf-8"))
        results = json_data["results"]

        for result in results:
            lat = result["location"]["latitude"]
            lon = result["location"]["longitude"]

            # Should be whole numbers
            assert lat == 38.0  # round(37.77..., 0) = 38.0
            assert lon == -122.0
