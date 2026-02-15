"""
Unit tests for sidecar route list_all_metadata() filter parameters.

Tests the GET /api/sidecar/photos endpoint's filter parameters:
- date_start, date_end: Date range filtering
- tags: Comma-separated tag filtering
- series_type: HDR or focus_bracket filtering
- has_species: Boolean species presence filtering
- has_sidecar: Boolean sidecar presence filtering

Also tests pagination edge cases, combined filters, and error handling.

These tests verify that query parameters are correctly parsed and passed
to the service layer (service.list_metadata_for_directory).

Endpoint: routes/sidecar.py lines 612-741
"""

import json
from unittest.mock import Mock

import pytest
from flask import Flask

from webui.backend.routes.sidecar import sidecar_bp
from webui.backend.services.sidecar_service import SidecarService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_sidecar_service():
    """Mock SidecarService with a default empty list response."""
    mock_service = Mock(spec=SidecarService)
    mock_service.list_metadata_for_directory.return_value = {
        "items": [],
        "total": 0,
        "limit": 50,
        "offset": 0,
        "has_next": False,
    }
    return mock_service


@pytest.fixture
def temp_photos_dir(tmp_path, monkeypatch):
    """Temporary PHOTOS_DIR patched into mothbox_paths and routes.sidecar."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    import mothbox_paths
    monkeypatch.setattr(mothbox_paths, "PHOTOS_DIR", photos_dir)

    import routes.sidecar
    monkeypatch.setattr(routes.sidecar, "PHOTOS_DIR", photos_dir)

    return photos_dir


@pytest.fixture
def client(temp_photos_dir, mock_sidecar_service):
    """Flask test client with sidecar blueprint and mock service."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SIDECAR_SERVICE"] = mock_sidecar_service
    app.register_blueprint(sidecar_bp, url_prefix="/api/sidecar")
    return app.test_client()


# ============================================================================
# Helper
# ============================================================================


def get_service_kwargs(mock_sidecar_service):
    """Extract keyword arguments from the last list_metadata_for_directory call."""
    return mock_sidecar_service.list_metadata_for_directory.call_args[1]


# ============================================================================
# TestListMetadataDateFiltering
# ============================================================================


class TestListMetadataDateFiltering:
    """Tests for date_start and date_end filter parameters."""

    def test_date_start_passed_to_service(self, client, mock_sidecar_service):
        """date_start query param is passed through to the service."""
        response = client.get("/api/sidecar/photos?date_start=2024-06-01")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_start"] == "2024-06-01"

    def test_date_end_passed_to_service(self, client, mock_sidecar_service):
        """date_end query param is passed through to the service."""
        response = client.get("/api/sidecar/photos?date_end=2024-12-31")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_end"] == "2024-12-31"

    def test_date_range_both_passed(self, client, mock_sidecar_service):
        """Both date_start and date_end are passed when provided together."""
        response = client.get(
            "/api/sidecar/photos?date_start=2024-01-01&date_end=2024-06-30"
        )

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_start"] == "2024-01-01"
        assert kwargs["date_end"] == "2024-06-30"

    def test_no_dates_passes_none(self, client, mock_sidecar_service):
        """Omitting date params passes None to the service."""
        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_start"] is None
        assert kwargs["date_end"] is None


# ============================================================================
# TestListMetadataTagFiltering
# ============================================================================


class TestListMetadataTagFiltering:
    """Tests for the tags filter parameter (comma-separated)."""

    def test_single_tag_parsed(self, client, mock_sidecar_service):
        """A single tag is parsed into a one-element list."""
        response = client.get("/api/sidecar/photos?tags=moth")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["tags"] == ["moth"]

    def test_multiple_tags_parsed(self, client, mock_sidecar_service):
        """Comma-separated tags are parsed into a list."""
        response = client.get("/api/sidecar/photos?tags=moth,luna,night")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["tags"] == ["moth", "luna", "night"]

    def test_whitespace_stripped_from_tags(self, client, mock_sidecar_service):
        """Whitespace around tags is stripped."""
        response = client.get("/api/sidecar/photos?tags=%20moth%20,%20luna%20")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["tags"] == ["moth", "luna"]

    def test_empty_tags_ignored(self, client, mock_sidecar_service):
        """Empty segments from trailing/leading commas are ignored."""
        response = client.get("/api/sidecar/photos?tags=moth,,luna,")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["tags"] == ["moth", "luna"]

    def test_no_tags_passes_none(self, client, mock_sidecar_service):
        """Omitting the tags param passes None to the service."""
        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["tags"] is None


# ============================================================================
# TestListMetadataSeriesTypeFiltering
# ============================================================================


class TestListMetadataSeriesTypeFiltering:
    """Tests for the series_type filter parameter."""

    def test_hdr_series_type(self, client, mock_sidecar_service):
        """series_type=hdr is passed to the service."""
        response = client.get("/api/sidecar/photos?series_type=hdr")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["series_type"] == "hdr"

    def test_focus_bracket_series_type(self, client, mock_sidecar_service):
        """series_type=focus_bracket is passed to the service."""
        response = client.get("/api/sidecar/photos?series_type=focus_bracket")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["series_type"] == "focus_bracket"

    def test_invalid_series_type_returns_400(self, client, mock_sidecar_service):
        """Invalid series_type values return 400."""
        response = client.get("/api/sidecar/photos?series_type=invalid")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "series_type" in data["error"]

        # Service should NOT have been called
        mock_sidecar_service.list_metadata_for_directory.assert_not_called()

    def test_no_series_type_passes_none(self, client, mock_sidecar_service):
        """Omitting series_type passes None to the service."""
        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["series_type"] is None


# ============================================================================
# TestListMetadataBooleanFilters
# ============================================================================


class TestListMetadataBooleanFilters:
    """Tests for has_species and has_sidecar boolean filter parameters."""

    # --- has_species ---

    def test_has_species_true(self, client, mock_sidecar_service):
        """has_species=true is parsed as True."""
        response = client.get("/api/sidecar/photos?has_species=true")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_species"] is True

    def test_has_species_false(self, client, mock_sidecar_service):
        """has_species=false is parsed as False."""
        response = client.get("/api/sidecar/photos?has_species=false")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_species"] is False

    def test_has_species_case_insensitive(self, client, mock_sidecar_service):
        """has_species comparison is case-insensitive (True, TRUE, etc.)."""
        response = client.get("/api/sidecar/photos?has_species=True")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_species"] is True

    def test_has_species_absent_passes_none(self, client, mock_sidecar_service):
        """Omitting has_species passes None to the service."""
        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_species"] is None

    # --- has_sidecar ---

    def test_has_sidecar_true(self, client, mock_sidecar_service):
        """has_sidecar=true is parsed as True."""
        response = client.get("/api/sidecar/photos?has_sidecar=true")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_sidecar"] is True

    def test_has_sidecar_false(self, client, mock_sidecar_service):
        """has_sidecar=false is parsed as False."""
        response = client.get("/api/sidecar/photos?has_sidecar=false")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_sidecar"] is False

    def test_has_sidecar_absent_passes_none(self, client, mock_sidecar_service):
        """Omitting has_sidecar passes None to the service."""
        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["has_sidecar"] is None


# ============================================================================
# TestListMetadataCombinedFilters
# ============================================================================


class TestListMetadataCombinedFilters:
    """Tests for combining multiple filter parameters together."""

    def test_all_filters_combined(self, client, mock_sidecar_service):
        """All six filter params are correctly forwarded when used together."""
        response = client.get(
            "/api/sidecar/photos"
            "?date_start=2024-01-01"
            "&date_end=2024-12-31"
            "&tags=moth,luna"
            "&series_type=hdr"
            "&has_species=true"
            "&has_sidecar=true"
        )

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_start"] == "2024-01-01"
        assert kwargs["date_end"] == "2024-12-31"
        assert kwargs["tags"] == ["moth", "luna"]
        assert kwargs["series_type"] == "hdr"
        assert kwargs["has_species"] is True
        assert kwargs["has_sidecar"] is True

    def test_tags_with_date_range(self, client, mock_sidecar_service):
        """Tags and date range filters work together."""
        response = client.get(
            "/api/sidecar/photos"
            "?date_start=2024-03-01"
            "&date_end=2024-09-30"
            "&tags=night,trap"
        )

        assert response.status_code == 200
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["date_start"] == "2024-03-01"
        assert kwargs["date_end"] == "2024-09-30"
        assert kwargs["tags"] == ["night", "trap"]
        # Unset filters remain None
        assert kwargs["series_type"] is None
        assert kwargs["has_species"] is None
        assert kwargs["has_sidecar"] is None


# ============================================================================
# TestListMetadataResponseFormat
# ============================================================================


class TestListMetadataResponseFormat:
    """Tests for response structure, pagination metadata, and error responses."""

    def test_pagination_metadata_in_response(self, client, mock_sidecar_service):
        """Response includes correct pagination metadata structure."""
        mock_sidecar_service.list_metadata_for_directory.return_value = {
            "items": [{"photo_filename": "a.jpg"}],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "has_next": False,
        }

        response = client.get("/api/sidecar/photos")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "items" in data
        assert "total" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 50
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_previous"] is False
        assert data["total"] == 1

    def test_page_2_has_previous(self, client, mock_sidecar_service):
        """Page 2 sets has_previous to True."""
        mock_sidecar_service.list_metadata_for_directory.return_value = {
            "items": [],
            "total": 100,
            "limit": 50,
            "offset": 50,
            "has_next": False,
        }

        response = client.get("/api/sidecar/photos?page=2")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["pagination"]["has_previous"] is True
        assert data["pagination"]["page"] == 2

    def test_service_exception_returns_500(self, client, mock_sidecar_service):
        """Service exceptions produce a 500 with a sanitized error message."""
        mock_sidecar_service.list_metadata_for_directory.side_effect = RuntimeError(
            "database locked"
        )

        response = client.get("/api/sidecar/photos")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        # Internal details should be sanitized
        assert "database locked" not in data["error"]

    def test_no_service_returns_503(self, client):
        """Missing SIDECAR_SERVICE returns 503."""
        # Create a fresh app without the service
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        # Explicitly no SIDECAR_SERVICE
        app.register_blueprint(sidecar_bp, url_prefix="/api/sidecar")
        no_service_client = app.test_client()

        response = no_service_client.get("/api/sidecar/photos")

        assert response.status_code == 503
        data = json.loads(response.data)
        assert "error" in data


# ============================================================================
# TestListMetadataPaginationEdgeCases
# ============================================================================


class TestListMetadataPaginationEdgeCases:
    """Tests for pagination boundary conditions and invalid values."""

    def test_page_zero_returns_400(self, client):
        """page=0 is invalid (1-indexed) and returns 400."""
        response = client.get("/api/sidecar/photos?page=0")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_negative_page_returns_400(self, client):
        """Negative page numbers return 400."""
        response = client.get("/api/sidecar/photos?page=-5")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_per_page_zero_returns_400(self, client):
        """per_page=0 is invalid and returns 400."""
        response = client.get("/api/sidecar/photos?per_page=0")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_per_page_exceeds_max_is_capped(self, client, mock_sidecar_service):
        """per_page above MAX_PAGINATION_LIMIT (200) is silently capped."""
        response = client.get("/api/sidecar/photos?per_page=500")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["pagination"]["per_page"] <= 200

        # Verify the service was called with the capped limit
        kwargs = get_service_kwargs(mock_sidecar_service)
        assert kwargs["limit"] <= 200
