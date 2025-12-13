"""
Unit tests for export preset management routes.

Tests all export preset endpoints with comprehensive mocking.
Focus areas: preset CRUD operations, validation, format filtering.

Test structure:
- TestListExportPresetsEndpoint: GET /api/export/presets tests
- TestGetExportPresetEndpoint: GET /api/export/presets/<name> tests
- TestCreateExportPresetEndpoint: POST /api/export/presets tests
- TestDeleteExportPresetEndpoint: DELETE /api/export/presets/<name> tests
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_export_preset_manager():
    """Create a mock ExportPresetManager for testing."""
    mock = MagicMock()

    # Default return values
    mock.list_presets.return_value = []
    mock.get_preset.return_value = None
    mock.save_preset.return_value = (True, "Saved")
    mock.delete_preset.return_value = (True, "Deleted")
    mock.get_preset_count.return_value = {"built_in": 0, "user": 0, "total": 0}

    return mock


@pytest.fixture
def app_with_export_presets(mock_export_preset_manager):
    """Create Flask app with mocked export preset manager."""
    from flask import Flask
    from webui.backend.routes.export_presets import export_presets_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
    app.config["EXPORT_PRESET_MANAGER"] = mock_export_preset_manager

    app.register_blueprint(export_presets_bp, url_prefix="/api/export/presets")

    return app


@pytest.fixture
def client(app_with_export_presets):
    """Flask test client."""
    return app_with_export_presets.test_client()


class TestListExportPresetsEndpoint:
    """Tests for GET /api/export/presets endpoint."""

    def test_list_presets_returns_all(self, client, mock_export_preset_manager):
        """GET /api/export/presets returns all presets."""
        mock_export_preset_manager.list_presets.return_value = [
            {
                "name": "gbif_biodiversity",
                "display_name": "GBIF Export",
                "export_format": "darwin_core",
                "category": "built-in",
            },
            {
                "name": "my_preset",
                "display_name": "My Preset",
                "export_format": "json",
                "category": "user",
            },
        ]
        mock_export_preset_manager.get_preset_count.return_value = {
            "built_in": 6,
            "user": 1,
            "total": 7,
        }

        response = client.get("/api/export/presets")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["presets"]) == 2
        assert data["counts"]["total"] == 7
        assert data["presets"][0]["name"] == "gbif_biodiversity"

    def test_list_presets_filter_by_format(self, client, mock_export_preset_manager):
        """GET /api/export/presets?format=darwin_core filters by format."""
        mock_export_preset_manager.list_presets.return_value = [
            {"name": "gbif", "export_format": "darwin_core"},
        ]
        mock_export_preset_manager.get_preset_count.return_value = {
            "built_in": 1,
            "user": 0,
            "total": 1,
        }

        response = client.get("/api/export/presets?format=darwin_core")

        assert response.status_code == 200
        mock_export_preset_manager.list_presets.assert_called_with(
            format_filter="darwin_core"
        )

    def test_list_presets_empty(self, client, mock_export_preset_manager):
        """GET /api/export/presets returns empty list when no presets."""
        mock_export_preset_manager.list_presets.return_value = []
        mock_export_preset_manager.get_preset_count.return_value = {
            "built_in": 0,
            "user": 0,
            "total": 0,
        }

        response = client.get("/api/export/presets")

        assert response.status_code == 200
        data = response.get_json()
        assert data["presets"] == []
        assert data["counts"]["total"] == 0

    def test_list_presets_handles_error(self, client, mock_export_preset_manager):
        """GET /api/export/presets returns 500 on error."""
        mock_export_preset_manager.list_presets.side_effect = RuntimeError("Error")

        response = client.get("/api/export/presets")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestGetExportPresetEndpoint:
    """Tests for GET /api/export/presets/<name> endpoint."""

    def test_get_preset_returns_data(self, client, mock_export_preset_manager):
        """GET /api/export/presets/<name> returns preset data."""
        from webui.backend.lib.export_preset_types import ExportPreset
        from webui.backend.lib.export_job_types import ExportJobFormat, ExportJobFilter

        mock_preset = ExportPreset(
            name="gbif_biodiversity",
            display_name="GBIF Export",
            export_format=ExportJobFormat.DARWIN_CORE,
            description="GBIF export",
            filter=ExportJobFilter(has_species=True),
        )
        mock_export_preset_manager.get_preset.return_value = mock_preset

        response = client.get("/api/export/presets/gbif_biodiversity")

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "gbif_biodiversity"
        assert data["export_format"] == "darwin_core"
        assert data["filter"]["has_species"] is True

    def test_get_preset_returns_404(self, client, mock_export_preset_manager):
        """GET /api/export/presets/<name> returns 404 when not found."""
        mock_export_preset_manager.get_preset.return_value = None

        response = client.get("/api/export/presets/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_get_preset_handles_error(self, client, mock_export_preset_manager):
        """GET /api/export/presets/<name> returns 500 on error."""
        mock_export_preset_manager.get_preset.side_effect = PermissionError("Error")

        response = client.get("/api/export/presets/test")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestCreateExportPresetEndpoint:
    """Tests for POST /api/export/presets endpoint."""

    def test_create_preset_success(self, client, mock_export_preset_manager):
        """POST /api/export/presets creates preset successfully."""
        mock_export_preset_manager.save_preset.return_value = (
            True,
            "Preset saved successfully",
        )

        response = client.post(
            "/api/export/presets",
            json={
                "name": "my_preset",
                "display_name": "My Preset",
                "export_format": "json",
                "description": "My custom preset",
                "filter": {"tags": ["moth"]},
                "options": {},
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["name"] == "my_preset"

        # Verify save_preset was called
        mock_export_preset_manager.save_preset.assert_called_once()

    def test_create_preset_missing_name(self, client, mock_export_preset_manager):
        """POST /api/export/presets returns 400 without name."""
        response = client.post(
            "/api/export/presets",
            json={
                "display_name": "My Preset",
                "export_format": "json",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "name" in data["error"].lower()

    def test_create_preset_missing_display_name(self, client, mock_export_preset_manager):
        """POST /api/export/presets returns 400 without display_name."""
        response = client.post(
            "/api/export/presets",
            json={
                "name": "my_preset",
                "export_format": "json",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "display_name" in data["error"].lower()

    def test_create_preset_missing_format(self, client, mock_export_preset_manager):
        """POST /api/export/presets returns 400 without export_format."""
        response = client.post(
            "/api/export/presets",
            json={
                "name": "my_preset",
                "display_name": "My Preset",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "format" in data["error"].lower()

    def test_create_preset_invalid_format(self, client, mock_export_preset_manager):
        """POST /api/export/presets returns 400 for invalid format."""
        response = client.post(
            "/api/export/presets",
            json={
                "name": "my_preset",
                "display_name": "My Preset",
                "export_format": "invalid_format",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "format" in data["error"].lower()

    def test_create_preset_rejects_builtin_category(self, client, mock_export_preset_manager):
        """POST /api/export/presets rejects built-in category."""
        response = client.post(
            "/api/export/presets",
            json={
                "name": "fake_builtin",
                "display_name": "Fake Built-in",
                "export_format": "json",
                "category": "built-in",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "built-in" in data["error"].lower()

    def test_create_preset_save_fails(self, client, mock_export_preset_manager):
        """POST /api/export/presets returns 400 when save fails."""
        mock_export_preset_manager.save_preset.return_value = (
            False,
            "Invalid preset name",
        )

        response = client.post(
            "/api/export/presets",
            json={
                "name": "invalid-name!",
                "display_name": "Invalid",
                "export_format": "json",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestDeleteExportPresetEndpoint:
    """Tests for DELETE /api/export/presets/<name> endpoint."""

    def test_delete_preset_success(self, client, mock_export_preset_manager):
        """DELETE /api/export/presets/<name> deletes preset successfully."""
        mock_export_preset_manager.delete_preset.return_value = (
            True,
            "Preset deleted",
        )

        response = client.delete("/api/export/presets/my_preset")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_export_preset_manager.delete_preset.assert_called_with("my_preset")

    def test_delete_preset_protects_builtin(self, client, mock_export_preset_manager):
        """DELETE /api/export/presets/<name> protects built-in presets."""
        mock_export_preset_manager.delete_preset.return_value = (
            False,
            "Cannot delete built-in presets",
        )

        response = client.delete("/api/export/presets/gbif_biodiversity")

        assert response.status_code == 400
        data = response.get_json()
        assert "built-in" in data["error"].lower()

    def test_delete_preset_not_found(self, client, mock_export_preset_manager):
        """DELETE /api/export/presets/<name> returns 404 for missing preset."""
        mock_export_preset_manager.delete_preset.return_value = (
            False,
            "Preset 'nonexistent' not found",
        )

        response = client.delete("/api/export/presets/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()

    def test_delete_preset_handles_error(self, client, mock_export_preset_manager):
        """DELETE /api/export/presets/<name> returns 500 on error."""
        mock_export_preset_manager.delete_preset.side_effect = OSError("Error")

        response = client.delete("/api/export/presets/test")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
