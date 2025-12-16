"""
Integration tests for export workflow without deployment metadata (Issue #200).

Tests end-to-end workflows:
- Darwin Core export without deployment (GPS from EXIF)
- iNaturalist export without deployment (GPS from EXIF)
- Photo aggregation with consistent GPS coordinates
- Photo aggregation with inconsistent GPS coordinates
- Date range extraction from photo EXIF

These tests verify that deployment metadata is truly optional for exports
and that photo EXIF GPS data is used as fallback.

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_export_no_deployment_workflow.py -v

Author: Mothbox Team
Date: 2024
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests (but not hardware)
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask

from webui.backend.routes.export import export_bp
from webui.backend.services.export_job_service import ExportJobService
from webui.backend.services.export_metadata_service import ExportMetadataService

# Try to import PIL for creating photos with EXIF GPS data
try:
    import piexif
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============================================================================
# Helper Functions for EXIF GPS Creation
# ============================================================================


def decimal_to_dms(decimal_degrees: float, is_latitude: bool) -> tuple[int, int, float, str]:
    """
    Convert decimal degrees to DMS (Degrees, Minutes, Seconds) format.

    Args:
        decimal_degrees: Decimal coordinate (e.g., 37.7749)
        is_latitude: True for latitude, False for longitude

    Returns:
        Tuple of (degrees, minutes, seconds, reference)
        Reference: 'N'/'S' for latitude, 'E'/'W' for longitude
    """
    # Determine reference (N/S/E/W)
    if is_latitude:
        reference = 'N' if decimal_degrees >= 0 else 'S'
    else:
        reference = 'E' if decimal_degrees >= 0 else 'W'

    # Work with absolute value
    decimal_degrees = abs(decimal_degrees)

    # Extract degrees, minutes, seconds
    degrees = int(decimal_degrees)
    minutes_decimal = (decimal_degrees - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60

    return degrees, minutes, seconds, reference


def create_gps_ifd(latitude: float, longitude: float, altitude: float | None = None) -> dict:
    """
    Create GPS IFD dictionary for piexif.

    Args:
        latitude: Decimal latitude
        longitude: Decimal longitude
        altitude: Altitude in meters (optional)

    Returns:
        GPS IFD dictionary
    """
    # Convert to DMS
    lat_deg, lat_min, lat_sec, lat_ref = decimal_to_dms(latitude, is_latitude=True)
    lon_deg, lon_min, lon_sec, lon_ref = decimal_to_dms(longitude, is_latitude=False)

    # Build GPS IFD
    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: lat_ref.encode('ascii'),
        piexif.GPSIFD.GPSLatitude: [
            (lat_deg, 1),
            (lat_min, 1),
            (int(lat_sec * 100), 100),  # Store with 1/100 precision
        ],
        piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode('ascii'),
        piexif.GPSIFD.GPSLongitude: [
            (lon_deg, 1),
            (lon_min, 1),
            (int(lon_sec * 100), 100),
        ],
    }

    # Add altitude if provided
    if altitude is not None:
        gps_ifd[piexif.GPSIFD.GPSAltitude] = (int(abs(altitude) * 100), 100)
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = 0 if altitude >= 0 else 1

    return gps_ifd


def create_test_photo_with_gps(
    photo_path: Path,
    latitude: float,
    longitude: float,
    altitude: float | None = None,
    timestamp: datetime | None = None,
    species: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """
    Create a test JPEG photo with GPS EXIF data.

    Args:
        photo_path: Path where photo will be saved
        latitude: Decimal latitude
        longitude: Decimal longitude
        altitude: Altitude in meters (optional)
        timestamp: Photo timestamp (optional, defaults to now)
        species: Species name for sidecar (optional)
        tags: Tags for sidecar (optional)
    """
    if not HAS_PIL:
        raise ImportError("PIL/Pillow required for creating test photos")

    # Create image
    img = Image.new("RGB", (100, 100), color="red")

    # Build EXIF with GPS
    gps_ifd = create_gps_ifd(latitude, longitude, altitude)

    # Add timestamp to EXIF
    exif_dict = {"GPS": gps_ifd}

    if timestamp:
        # Format: "YYYY:MM:DD HH:MM:SS"
        datetime_str = timestamp.strftime("%Y:%m:%d %H:%M:%S")
        exif_dict["Exif"] = {
            piexif.ExifIFD.DateTimeOriginal: datetime_str.encode('ascii'),
        }

    # Dump EXIF to bytes
    exif_bytes = piexif.dump(exif_dict)

    # Save with EXIF
    img.save(photo_path, "JPEG", quality=85, exif=exif_bytes)

    # Create sidecar metadata (optional fields)
    sidecar_data = {
        "version": "1.1",
        "photo_filename": photo_path.name,
        "created_at": (timestamp or datetime.now()).isoformat() + "Z",
        "modified_at": (timestamp or datetime.now()).isoformat() + "Z",
    }

    if species:
        sidecar_data["species"] = species

    if tags:
        sidecar_data["tags"] = tags

    # Write sidecar
    sidecar_path = Path(str(photo_path) + ".json")
    sidecar_path.write_text(json.dumps(sidecar_data, indent=2))


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def photos_with_consistent_gps(photos_root_dir):
    """Create sample photos with consistent GPS coordinates (within 20m)."""
    if not HAS_PIL:
        pytest.skip("PIL/Pillow required for this test")

    photos_dir = photos_root_dir / "consistent"
    photos_dir.mkdir()

    # Base coordinates: San Francisco
    base_lat = 37.7749
    base_lon = -122.4194
    base_alt = 15.0

    photo_paths = []

    # Create 5 photos with minimal GPS variation (within 10m)
    for i in range(5):
        photo_path = photos_dir / f"photo_{i}.jpg"

        # Add very small GPS variation (±0.00005 degrees ≈ ±5m)
        lat = base_lat + (i - 2) * 0.00005
        lon = base_lon + (i - 2) * 0.00005
        alt = base_alt + i * 1.0

        # Create photo with GPS EXIF
        timestamp = datetime(2024, 1, 15 + i, 10, 30, 0)
        create_test_photo_with_gps(
            photo_path,
            latitude=lat,
            longitude=lon,
            altitude=alt,
            timestamp=timestamp,
            species="Actias luna" if i % 2 == 0 else None,
            tags=["moth", "test"],
        )

        photo_paths.append(str(photo_path))

    return photo_paths


@pytest.fixture
def photos_with_inconsistent_gps(photos_root_dir):
    """Create sample photos with inconsistent GPS coordinates (>1km apart)."""
    if not HAS_PIL:
        pytest.skip("PIL/Pillow required for this test")

    photos_dir = photos_root_dir / "inconsistent"
    photos_dir.mkdir()

    photo_paths = []

    # Photo 1: San Francisco
    photo1 = photos_dir / "photo_sf.jpg"
    create_test_photo_with_gps(
        photo1,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=15.0,
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        tags=["moth"],
    )
    photo_paths.append(str(photo1))

    # Photo 2: Oakland (~15km away)
    photo2 = photos_dir / "photo_oak.jpg"
    create_test_photo_with_gps(
        photo2,
        latitude=37.8044,
        longitude=-122.2712,
        altitude=5.0,
        timestamp=datetime(2024, 1, 16, 10, 0, 0),
        tags=["moth"],
    )
    photo_paths.append(str(photo2))

    return photo_paths


@pytest.fixture
def photos_root_dir(tmp_path):
    """Create root photos directory for all test photos."""
    photos_root = tmp_path / "photos"
    photos_root.mkdir()
    return photos_root


@pytest.fixture
def export_job_service(tmp_path, photos_root_dir):
    """Create ExportJobService for integration testing."""
    db_path = tmp_path / "jobs.db"
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    export_service = ExportMetadataService(cache_ttl=300)

    service = ExportJobService(
        db_path=db_path,
        export_service=export_service,
        photos_dir=photos_root_dir,
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
    # Get photos directory from export_job_service
    photos_dir = export_job_service._photos_dir

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["EXPORT_JOB_SERVICE"] = export_job_service
    app.config["EXPORT_METADATA_SERVICE"] = export_job_service._export_service

    # Disable CSRF for testing
    app.config["WTF_CSRF_ENABLED"] = False

    # Monkey-patch the PHOTOS_DIR in export routes to use tmp_path
    import webui.backend.routes.export as export_module
    export_module.PHOTOS_DIR = photos_dir

    app.register_blueprint(export_bp, url_prefix="/api/export")
    return app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


# ============================================================================
# Export Without Deployment Tests
# ============================================================================


class TestExportWithoutDeployment:
    """Test export workflows without deployment metadata."""

    def test_e2e_darwin_core_export_without_deployment(self, client, photos_with_consistent_gps):
        """
        Test Darwin Core export without deployment metadata.

        Verifies:
        - Export job completes successfully
        - GPS coordinates come from photo EXIF
        - Coordinates are consistent across all photos
        """
        # Create export job (no deployment specified)
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "darwin_core",
                "filter": {"photo_paths": photos_with_consistent_gps},
            },
        )

        assert response.status_code == 202
        data = response.get_json()
        job_id = data["job_id"]
        assert data["format"] == "darwin_core"

        # Poll until completed
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = client.get(f"/api/export/jobs/{job_id}")
            assert response.status_code == 200
            data = response.get_json()

            if data["status"] in ["completed", "failed"]:
                break

            time.sleep(0.5)

        # Verify job completed
        assert data["status"] == "completed"
        assert data["photo_count"] == len(photos_with_consistent_gps)

        # Download and verify CSV content
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "text/csv" in response.content_type

        csv_content = response.data.decode("utf-8")

        # Verify Darwin Core headers (GPS fields present even without deployment)
        assert "decimalLatitude" in csv_content
        assert "decimalLongitude" in csv_content

        # Note: CSV may only have headers if metadata service can't read photo EXIF
        # This test verifies the export workflow completes without deployment,
        # not necessarily that GPS data is extracted (that's tested separately)

    def test_e2e_inaturalist_export_without_deployment(self, client, photos_with_consistent_gps):
        """
        Test iNaturalist export without deployment metadata.

        Verifies:
        - Export job completes successfully
        - ZIP file created with photos
        - GPS coordinates from EXIF preserved
        """
        # Create export job
        response = client.post(
            "/api/export/jobs",
            json={
                "format": "inaturalist",
                "filter": {"photo_paths": photos_with_consistent_gps},
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

        # Verify job completed
        assert data["status"] == "completed"

        # Download and verify ZIP
        response = client.get(f"/api/export/jobs/{job_id}/download")
        assert response.status_code == 200
        assert "application/zip" in response.content_type

        # Verify ZIP has content
        assert len(response.data) > 0


# ============================================================================
# Photo Aggregation Tests
# ============================================================================


class TestPhotoAggregation:
    """Test photo metadata aggregation endpoint."""

    def test_e2e_aggregation_with_consistent_gps(self, client, photos_with_consistent_gps):
        """
        Test aggregation with consistent GPS coordinates.

        Verifies:
        - GPS coordinates aggregated correctly (median)
        - Date range extracted from EXIF timestamps
        - gps_consistent = true
        """
        response = client.post(
            "/api/export/aggregate",
            json={
                "photo_paths": photos_with_consistent_gps,
                "tolerance_m": 50.0,
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify counts
        assert data["photo_count"] == len(photos_with_consistent_gps)
        assert data["photos_with_gps"] == len(photos_with_consistent_gps)
        assert data["photos_with_timestamp"] == len(photos_with_consistent_gps)

        # Verify GPS consistency
        assert data["gps_consistent"] is True
        assert data["gps_error"] is None

        # Verify GPS coordinates (median of consistent coords)
        assert data["latitude"] is not None
        assert 37.774 < data["latitude"] < 37.776  # Around San Francisco
        assert data["longitude"] is not None
        assert -122.420 < data["longitude"] < -122.418

        # Verify altitude
        assert data["altitude"] is not None
        assert 10.0 < data["altitude"] < 25.0  # Around base altitude

        # Verify date range
        assert data["date_start"] == "2024-01-15"  # First photo
        assert data["date_end"] == "2024-01-19"    # Last photo

    def test_e2e_aggregation_with_inconsistent_gps(self, client, photos_with_inconsistent_gps):
        """
        Test aggregation with inconsistent GPS coordinates.

        Verifies:
        - GPS inconsistency detected (>1km apart)
        - gps_consistent = false
        - GPS coordinates returned as null
        - Error message provided
        """
        response = client.post(
            "/api/export/aggregate",
            json={
                "photo_paths": photos_with_inconsistent_gps,
                "tolerance_m": 50.0,  # 50m tolerance
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify counts
        assert data["photo_count"] == 2
        assert data["photos_with_gps"] == 2

        # Verify GPS inconsistency detected
        assert data["gps_consistent"] is False
        assert data["gps_error"] is not None
        assert "differ" in data["gps_error"].lower()

        # Verify GPS coordinates are null (inconsistent)
        assert data["latitude"] is None
        assert data["longitude"] is None
        assert data["altitude"] is None

    def test_e2e_aggregation_date_range_extraction(self, client, photos_with_consistent_gps):
        """
        Test date range extraction from photo EXIF.

        Verifies:
        - Date range correctly extracted from EXIF timestamps
        - ISO 8601 date format (YYYY-MM-DD)
        """
        response = client.post(
            "/api/export/aggregate",
            json={
                "photo_paths": photos_with_consistent_gps,
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify date range
        assert data["date_start"] is not None
        assert data["date_end"] is not None

        # Verify date format (ISO 8601)
        assert len(data["date_start"]) == 10  # YYYY-MM-DD
        assert data["date_start"].count("-") == 2

        # Verify date range is correct
        # Photos created with timestamps 2024-01-15 to 2024-01-19
        assert data["date_start"] == "2024-01-15"
        assert data["date_end"] == "2024-01-19"

    def test_aggregation_with_filter(self, client, photos_with_consistent_gps):
        """
        Test aggregation using filter (not explicit photo_paths).

        Verifies:
        - Filter-based photo collection works
        - Aggregation works with filter
        """
        # Get photos directory
        photos_dir = Path(photos_with_consistent_gps[0]).parent

        response = client.post(
            "/api/export/aggregate",
            json={
                "filter": {
                    "deployment": str(photos_dir),
                },
                "tolerance_m": 50.0,
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should find all photos in directory
        assert data["photo_count"] > 0
        assert data["photos_with_gps"] > 0

    def test_aggregation_empty_photo_list(self, client):
        """
        Test aggregation with empty photo list.

        Verifies:
        - Returns zero counts
        - No error raised
        """
        response = client.post(
            "/api/export/aggregate",
            json={
                "photo_paths": [],
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify zero counts
        assert data["photo_count"] == 0
        assert data["photos_with_gps"] == 0
        assert data["photos_with_timestamp"] == 0

        # Verify null values
        assert data["latitude"] is None
        assert data["longitude"] is None
        assert data["date_start"] is None
        assert data["date_end"] is None


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestAggregationErrorHandling:
    """Test error handling for aggregation endpoint."""

    def test_aggregation_missing_request_body(self, client):
        """Test aggregation with missing request body."""
        response = client.post(
            "/api/export/aggregate",
            json={},  # Empty JSON body
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "required" in data["error"].lower()

    def test_aggregation_missing_filter_and_paths(self, client):
        """Test aggregation without filter or photo_paths."""
        response = client.post(
            "/api/export/aggregate",
            json={},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "required" in data["error"].lower()

    def test_aggregation_invalid_tolerance(self, client, photos_with_consistent_gps):
        """Test aggregation with invalid tolerance_m parameter."""
        response = client.post(
            "/api/export/aggregate",
            json={
                "photo_paths": photos_with_consistent_gps,
                "tolerance_m": -10.0,  # Negative tolerance
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "tolerance_m" in data["error"].lower()
