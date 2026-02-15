"""Tests for GPS EXIF tagger API routes.

Tests the endpoints in webui/backend/routes/gps_exif.py:
- GET /api/gps-exif/status
- POST /api/gps-exif/tag-photo
- POST /api/gps-exif/batch-tag
- GET /api/gps-exif/config
- PUT /api/gps-exif/config
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Path setup for imports
_test_dir = Path(__file__).resolve().parent
_tests_root = _test_dir.parent
_firmware_root = _tests_root.parent
sys.path.insert(0, str(_firmware_root))
sys.path.insert(0, str(_firmware_root / "webui" / "backend"))


@pytest.fixture()
def gps_exif_app(tmp_path):
    """Create a Flask test app with gps_exif blueprint registered."""
    from flask import Flask
    from routes.gps_exif import gps_exif_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.register_blueprint(gps_exif_bp, url_prefix="/api/gps-exif")

    return app


@pytest.fixture()
def client(gps_exif_app):
    """Flask test client."""
    return gps_exif_app.test_client()


# ============================================================================
# GET /status
# ============================================================================


class TestGetStatus:
    """Tests for GET /api/gps-exif/status."""

    def test_get_status_returns_200(self, client):
        """GET /status returns 200 with expected top-level keys."""
        with patch("routes.gps_exif.PHOTOS_DIR", Path("/tmp/nonexistent_photos")):
            response = client.get("/api/gps-exif/status")

        assert response.status_code == 200
        data = response.get_json()
        assert "coordinate_sources" in data
        assert "service_running" in data
        assert "stats" in data

    def test_get_status_coordinate_sources(self, client):
        """GET /status includes known coordinate source names."""
        with patch("routes.gps_exif.PHOTOS_DIR", Path("/tmp/nonexistent_photos")):
            response = client.get("/api/gps-exif/status")

        data = response.get_json()
        sources = data["coordinate_sources"]
        assert isinstance(sources, list)
        assert "deployment" in sources
        assert "gps" in sources


# ============================================================================
# POST /tag-photo
# ============================================================================


class TestTagPhoto:
    """Tests for POST /api/gps-exif/tag-photo."""

    def test_tag_photo_rejects_missing_path(self, client):
        """POST /tag-photo with no photo_path returns 400."""
        response = client.post(
            "/api/gps-exif/tag-photo",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_tag_photo_rejects_empty_path(self, client):
        """POST /tag-photo with empty photo_path returns 400."""
        response = client.post(
            "/api/gps-exif/tag-photo",
            data=json.dumps({"photo_path": ""}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_tag_photo_rejects_path_traversal(self, client):
        """POST /tag-photo with ../etc/passwd returns 400."""
        response = client.post(
            "/api/gps-exif/tag-photo",
            data=json.dumps({"photo_path": "../etc/passwd"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        # Should mention path traversal or invalid path
        assert "path" in data["error"].lower() or "traversal" in data["error"].lower()

    def test_tag_photo_rejects_absolute_path(self, client):
        """POST /tag-photo with absolute path returns 400."""
        response = client.post(
            "/api/gps-exif/tag-photo",
            data=json.dumps({"photo_path": "/etc/passwd"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_tag_photo_returns_404_for_missing_file(self, client, tmp_path):
        """POST /tag-photo returns 404 when photo file does not exist."""
        with patch("routes.gps_exif.PHOTOS_DIR", tmp_path):
            response = client.post(
                "/api/gps-exif/tag-photo",
                data=json.dumps({"photo_path": "nonexistent.jpg"}),
                content_type="application/json",
            )
        assert response.status_code == 404

    def test_tag_photo_success(self, client, tmp_path):
        """POST /tag-photo successfully tags a photo."""
        # Create a test photo file
        photo = tmp_path / "test.jpg"
        photo.touch()

        mock_resolved = {
            "lat": 9.123,
            "lon": -83.456,
            "source": "deployment",
            "deployment_name": "test",
            "gps_data": {"has_fix": True, "latitude": 9.123, "longitude": -83.456},
        }
        mock_embed_result = {
            "success": True,
            "skipped": False,
            "error": None,
            "gps_embedded": True,
            "original_had_gps": False,
            "backup_path": None,
        }

        with (
            patch("routes.gps_exif.PHOTOS_DIR", tmp_path),
            patch("routes.gps_exif.resolve_coordinates", return_value=mock_resolved),
            patch("routes.gps_exif.embed_gps_exif", return_value=mock_embed_result),
        ):
            response = client.post(
                "/api/gps-exif/tag-photo",
                data=json.dumps({"photo_path": "test.jpg"}),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["source_used"] == "deployment"
        assert data["coordinates"]["lat"] == 9.123
        assert data["coordinates"]["lon"] == -83.456


# ============================================================================
# POST /batch-tag
# ============================================================================


class TestBatchTag:
    """Tests for POST /api/gps-exif/batch-tag."""

    def test_batch_tag_returns_stats(self, client, tmp_path):
        """POST /batch-tag returns stats dict when batch processing succeeds."""
        mock_stats = {
            "total": 10,
            "tagged": 7,
            "skipped": 2,
            "errors": 1,
            "error_list": [],
            "source_counts": {"deployment": 5, "gps": 2},
        }

        with (
            patch("routes.gps_exif.PHOTOS_DIR", tmp_path),
            patch(
                "webui.cli.gps_exif_tagger.batch_process_directory",
                return_value=mock_stats,
            ),
        ):
            response = client.post(
                "/api/gps-exif/batch-tag",
                data=json.dumps({"coordinate_sources": ["deployment", "gps"]}),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 10
        assert data["tagged"] == 7
        assert data["skipped"] == 2
        assert data["errors"] == 1
        assert data["source_counts"]["deployment"] == 5

    def test_batch_tag_rejects_path_traversal_directory(self, client, tmp_path):
        """POST /batch-tag rejects directory with path traversal."""
        with patch("routes.gps_exif.PHOTOS_DIR", tmp_path):
            response = client.post(
                "/api/gps-exif/batch-tag",
                data=json.dumps({"directory": "../../etc"}),
                content_type="application/json",
            )
        assert response.status_code == 400

    def test_batch_tag_uses_default_photos_dir(self, client, tmp_path):
        """POST /batch-tag with no directory uses PHOTOS_DIR."""
        mock_stats = {
            "total": 0,
            "tagged": 0,
            "skipped": 0,
            "errors": 0,
            "error_list": [],
            "source_counts": {},
        }

        with (
            patch("routes.gps_exif.PHOTOS_DIR", tmp_path),
            patch(
                "webui.cli.gps_exif_tagger.batch_process_directory",
                return_value=mock_stats,
            ) as mock_batch,
        ):
            response = client.post(
                "/api/gps-exif/batch-tag",
                data=json.dumps({}),
                content_type="application/json",
            )

        assert response.status_code == 200
        # Should have been called with PHOTOS_DIR (tmp_path)
        call_args = mock_batch.call_args
        assert call_args[0][0] == tmp_path


# ============================================================================
# GET /config
# ============================================================================


class TestGetConfig:
    """Tests for GET /api/gps-exif/config."""

    def test_get_config_returns_defaults(self, client, tmp_path):
        """GET /config returns default sources when no config file exists."""
        config_file = tmp_path / "gps_exif_config.json"

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.get("/api/gps-exif/config")

        assert response.status_code == 200
        data = response.get_json()
        assert "default_sources" in data
        assert "pattern" in data
        # Default sources should include deployment and gps
        assert "deployment" in data["default_sources"]
        assert "gps" in data["default_sources"]

    def test_get_config_reads_existing_file(self, client, tmp_path):
        """GET /config reads from existing config file."""
        config_file = tmp_path / "gps_exif_config.json"
        config_data = {"default_sources": ["gps"], "pattern": "*.jpeg"}
        config_file.write_text(json.dumps(config_data))

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.get("/api/gps-exif/config")

        assert response.status_code == 200
        data = response.get_json()
        assert data["default_sources"] == ["gps"]
        assert data["pattern"] == "*.jpeg"


# ============================================================================
# PUT /config
# ============================================================================


class TestUpdateConfig:
    """Tests for PUT /api/gps-exif/config."""

    def test_update_config_validates_sources(self, client, tmp_path):
        """PUT /config with invalid source returns 400."""
        config_file = tmp_path / "gps_exif_config.json"

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.put(
                "/api/gps-exif/config",
                data=json.dumps({"default_sources": ["invalid_source"]}),
                content_type="application/json",
            )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_update_config_saves_valid_sources(self, client, tmp_path):
        """PUT /config saves valid configuration."""
        config_file = tmp_path / "gps_exif_config.json"

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.put(
                "/api/gps-exif/config",
                data=json.dumps({"default_sources": ["gps"], "pattern": "*.jpeg"}),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["config"]["default_sources"] == ["gps"]
        assert data["config"]["pattern"] == "*.jpeg"

        # Verify it was persisted
        saved = json.loads(config_file.read_text())
        assert saved["default_sources"] == ["gps"]

    def test_update_config_rejects_empty_sources(self, client, tmp_path):
        """PUT /config with empty sources list returns 400."""
        config_file = tmp_path / "gps_exif_config.json"

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.put(
                "/api/gps-exif/config",
                data=json.dumps({"default_sources": []}),
                content_type="application/json",
            )

        assert response.status_code == 400

    def test_update_config_rejects_no_body(self, client, tmp_path):
        """PUT /config with no request body returns 400."""
        config_file = tmp_path / "gps_exif_config.json"

        with patch("routes.gps_exif._get_config_file", return_value=config_file):
            response = client.put(
                "/api/gps-exif/config",
                content_type="application/json",
            )

        assert response.status_code == 400
