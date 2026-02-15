"""Tests for GPS coordinate resolver module.

The coordinate resolver walks a configurable chain of sources
(deployment, gps, manual) and returns the first valid GPS coordinates.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from webui.backend.lib.gps_coordinate_resolver import resolve_coordinates


class TestDeploymentSource:
    """Tests for the deployment sidecar source."""

    def test_deployment_source_returns_coords_from_sidecar(self):
        """Deployment source reads lat/lon from DeploymentService sidecar metadata."""
        deployment_service = Mock()
        metadata = Mock()
        metadata.latitude = 35.9606
        metadata.longitude = -83.9207
        metadata.altitude = 350.0
        metadata.deployment_name = "Forest Survey 2024"
        deployment_service.find_deployment_for_photo.return_value = metadata

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("deployment",),
            deployment_service=deployment_service,
        )

        assert result is not None
        assert result["source"] == "deployment"
        assert result["lat"] == 35.9606
        assert result["lon"] == -83.9207
        assert result["deployment_name"] == "Forest Survey 2024"
        deployment_service.find_deployment_for_photo.assert_called_once_with(
            Path("/photos/test.jpg")
        )

    def test_deployment_with_null_coords_skipped(self):
        """Deployment metadata with lat=None is treated as no valid coords."""
        deployment_service = Mock()
        metadata = Mock()
        metadata.latitude = None
        metadata.longitude = -83.9207
        metadata.deployment_name = "Incomplete Deployment"
        deployment_service.find_deployment_for_photo.return_value = metadata

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("deployment",),
            deployment_service=deployment_service,
        )

        assert result is None


class TestGpsSource:
    """Tests for the GPS controls.txt source."""

    @patch("webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls")
    def test_gps_source_reads_controls_txt(self, mock_get_gps):
        """GPS source calls get_gps_data_from_controls and extracts coordinates."""
        mock_get_gps.return_value = {
            "has_fix": True,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.0,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.1,
        }

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("gps",),
        )

        assert result is not None
        assert result["source"] == "gps"
        assert result["lat"] == 37.7749
        assert result["lon"] == -122.4194
        mock_get_gps.assert_called_once()

    @patch("webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls")
    def test_gps_data_includes_full_metadata(self, mock_get_gps):
        """GPS source result includes the full gps_data dict for embed_gps_exif."""
        gps_data = {
            "has_fix": True,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.0,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.1,
        }
        mock_get_gps.return_value = gps_data

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("gps",),
        )

        assert result is not None
        assert result["gps_data"]["has_fix"] is True
        assert result["gps_data"]["latitude"] == 37.7749
        assert result["gps_data"]["longitude"] == -122.4194
        assert result["gps_data"]["altitude"] == 10.0
        assert result["gps_data"]["fix_mode"] == 3
        assert result["gps_data"]["gpstime"] == 1700000000
        assert result["gps_data"]["satellites_used"] == 8
        assert result["gps_data"]["hdop"] == 1.2
        assert result["gps_data"]["pdop"] == 2.1


class TestManualSource:
    """Tests for the manual coordinate pass-through source."""

    def test_manual_source_passes_through(self):
        """Manual source uses provided manual_coords dict."""
        manual = {"lat": 51.5074, "lon": -0.1278}

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("manual",),
            manual_coords=manual,
        )

        assert result is not None
        assert result["source"] == "manual"
        assert result["lat"] == 51.5074
        assert result["lon"] == -0.1278

    def test_manual_without_coords_skipped(self):
        """Manual source with manual_coords=None is skipped."""
        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("manual",),
            manual_coords=None,
        )

        assert result is None


class TestFallbackChain:
    """Tests for the source fallback chain logic."""

    @patch("webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls")
    def test_fallback_chain_skips_failed_sources(self, mock_get_gps):
        """When deployment returns None, resolver falls back to GPS source."""
        deployment_service = Mock()
        deployment_service.find_deployment_for_photo.return_value = None

        mock_get_gps.return_value = {
            "has_fix": True,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.0,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.1,
        }

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("deployment", "gps"),
            deployment_service=deployment_service,
        )

        assert result is not None
        assert result["source"] == "gps"

    @patch("webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls")
    def test_returns_none_when_all_sources_fail(self, mock_get_gps):
        """Returns None when all sources in the chain fail."""
        deployment_service = Mock()
        deployment_service.find_deployment_for_photo.return_value = None

        mock_get_gps.return_value = {
            "has_fix": False,
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "fix_mode": 0,
            "gpstime": 0,
            "satellites_used": 0,
            "hdop": 99.99,
            "pdop": 99.99,
        }

        result = resolve_coordinates(
            photo_path=Path("/photos/test.jpg"),
            sources=("deployment", "gps"),
            deployment_service=deployment_service,
        )

        assert result is None


class TestValidation:
    """Tests for input validation."""

    def test_invalid_source_name_raises(self):
        """Unknown source name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown source"):
            resolve_coordinates(
                photo_path=Path("/photos/test.jpg"),
                sources=("deployment", "weather_station"),
            )
