"""
Integration tests for export preset workflow (Issue #123).

Tests end-to-end workflows:
- Preset creation, listing, and deletion
- Using presets with export job creation
- Preset filter and options merging
- Built-in preset loading

Run with: MOTHBOX_ENV=test pytest Tests/integration/test_export_preset_workflow.py -v

These tests are marked as @pytest.mark.integration but NOT @pytest.mark.hardware
since they test multi-layer integration without requiring Pi hardware.

Author: Mothbox Team
Date: 2024
"""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Mark all tests in this module as integration tests (but not hardware)
pytestmark = pytest.mark.integration

# Setup path
FIRMWARE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(FIRMWARE_DIR))
sys.path.insert(0, str(FIRMWARE_DIR / "webui" / "backend"))
os.environ.setdefault("MOTHBOX_ENV", "test")

from flask import Flask

from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat
from webui.backend.lib.export_preset_types import ExportPreset, ExportPresetCategory
from webui.backend.export_preset_manager import ExportPresetManager
from webui.backend.routes.export_presets import export_presets_bp
from webui.backend.routes.export import export_bp


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def preset_dirs(tmp_path):
    """Create temporary directories for presets."""
    builtin_dir = tmp_path / "built-in" / "export"
    user_dir = tmp_path / "user" / "export"
    builtin_dir.mkdir(parents=True)
    user_dir.mkdir(parents=True)

    # Create a built-in preset
    builtin_preset = {
        "name": "test_builtin",
        "display_name": "Test Built-in Preset",
        "export_format": "darwin_core",
        "description": "A test built-in preset",
        "version": "1.0",
        "author": "system",
        "category": "built-in",
        "filter": {"has_species": True},
        "options": {"validate": True},
    }
    (builtin_dir / "test_builtin.json").write_text(json.dumps(builtin_preset))

    return builtin_dir, user_dir


@pytest.fixture
def preset_manager(preset_dirs):
    """Create ExportPresetManager with temp directories."""
    builtin_dir, user_dir = preset_dirs
    return ExportPresetManager(builtin_dir=builtin_dir, user_dir=user_dir)


@pytest.fixture
def mock_export_job_service():
    """Mock ExportJobService."""
    from webui.backend.lib.export_job_types import (
        ExportJob,
        ExportJobProgress,
        ExportJobStatus,
    )
    from datetime import datetime

    service = MagicMock()

    # Default: create job returns a pending job
    def create_job(**kwargs):
        return ExportJob(
            job_id="test-job-123",
            status=ExportJobStatus.PENDING,
            format=kwargs.get("format", ExportJobFormat.DARWIN_CORE),
            filter=kwargs.get("filter", ExportJobFilter()),
            progress=ExportJobProgress(),
            created_at=datetime.now().timestamp(),
        )

    service.create_job.side_effect = create_job
    service.list_jobs.return_value = ([], 0)
    service.get_job.return_value = None

    return service


@pytest.fixture
def app(preset_manager, mock_export_job_service):
    """Create Flask app with preset manager and export service."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["EXPORT_PRESET_MANAGER"] = preset_manager
    app.config["EXPORT_JOB_SERVICE"] = mock_export_job_service

    app.register_blueprint(export_presets_bp, url_prefix="/api/export/presets")
    app.register_blueprint(export_bp, url_prefix="/api/export")

    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ============================================================================
# Preset CRUD Workflow Tests
# ============================================================================


class TestPresetCRUDWorkflow:
    """Test complete preset CRUD workflow."""

    def test_list_builtin_presets(self, client):
        """List presets includes built-in presets."""
        response = client.get("/api/export/presets")

        assert response.status_code == 200
        data = response.get_json()
        assert "presets" in data
        assert "counts" in data

        # Should have at least the test_builtin preset
        names = [p["name"] for p in data["presets"]]
        assert "test_builtin" in names

    def test_create_and_list_user_preset(self, client):
        """Create user preset and verify it appears in list."""
        # Create preset
        create_response = client.post(
            "/api/export/presets",
            json={
                "name": "my_preset",
                "display_name": "My Custom Preset",
                "export_format": "json",
                "description": "A custom preset",
                "filter": {"tags": ["moth"]},
            },
        )

        assert create_response.status_code == 201
        create_data = create_response.get_json()
        assert create_data["success"] is True
        assert create_data["name"] == "my_preset"

        # List presets
        list_response = client.get("/api/export/presets")
        assert list_response.status_code == 200
        list_data = list_response.get_json()

        # Should have both built-in and user preset
        names = [p["name"] for p in list_data["presets"]]
        assert "test_builtin" in names
        assert "my_preset" in names

        # Check counts
        assert list_data["counts"]["user"] >= 1

    def test_get_preset_details(self, client):
        """Get preset returns full details."""
        response = client.get("/api/export/presets/test_builtin")

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "test_builtin"
        assert data["export_format"] == "darwin_core"
        assert data["filter"]["has_species"] is True
        assert data["options"]["validate"] is True
        assert data["category"] == "built-in"

    def test_create_and_delete_user_preset(self, client):
        """Create and delete user preset."""
        # Create
        client.post(
            "/api/export/presets",
            json={
                "name": "temp_preset",
                "display_name": "Temporary Preset",
                "export_format": "csv",
            },
        )

        # Verify it exists
        get_response = client.get("/api/export/presets/temp_preset")
        assert get_response.status_code == 200

        # Delete
        delete_response = client.delete("/api/export/presets/temp_preset")
        assert delete_response.status_code == 200
        assert delete_response.get_json()["success"] is True

        # Verify it's gone
        get_response = client.get("/api/export/presets/temp_preset")
        assert get_response.status_code == 404

    def test_cannot_delete_builtin_preset(self, client):
        """Built-in presets are protected from deletion."""
        response = client.delete("/api/export/presets/test_builtin")

        assert response.status_code == 400
        data = response.get_json()
        assert "built-in" in data["error"].lower()

    def test_filter_presets_by_format(self, client):
        """Filter presets by export format."""
        # Create presets with different formats
        client.post(
            "/api/export/presets",
            json={
                "name": "json_preset",
                "display_name": "JSON Preset",
                "export_format": "json",
            },
        )
        client.post(
            "/api/export/presets",
            json={
                "name": "csv_preset",
                "display_name": "CSV Preset",
                "export_format": "csv",
            },
        )

        # Filter by JSON
        response = client.get("/api/export/presets?format=json")
        assert response.status_code == 200
        data = response.get_json()

        formats = [p["export_format"] for p in data["presets"]]
        assert all(f == "json" for f in formats)


# ============================================================================
# Preset Integration with Export Jobs
# ============================================================================


class TestPresetJobIntegration:
    """Test preset integration with export job creation."""

    def test_create_job_with_preset(self, client, mock_export_job_service):
        """Create export job using preset."""
        response = client.post(
            "/api/export/jobs",
            json={"preset": "test_builtin"},
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == "test-job-123"
        assert data["format"] == "darwin_core"

        # Verify service was called with preset values
        mock_export_job_service.create_job.assert_called_once()
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.DARWIN_CORE
        assert call_kwargs["filter"].has_species is True
        assert call_kwargs["options"]["validate"] is True

    def test_create_job_preset_with_filter_merge(self, client, mock_export_job_service):
        """Preset filter merged with explicit filter."""
        response = client.post(
            "/api/export/jobs",
            json={
                "preset": "test_builtin",
                "filter": {
                    "date_start": "2024-01-01",
                    "tags": ["moth"],
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        filter_obj = call_kwargs["filter"]
        # From preset
        assert filter_obj.has_species is True
        # From explicit
        assert filter_obj.date_start == "2024-01-01"
        assert filter_obj.tags == ["moth"]

    def test_create_job_preset_with_format_override(
        self, client, mock_export_job_service
    ):
        """Explicit format overrides preset format."""
        response = client.post(
            "/api/export/jobs",
            json={
                "preset": "test_builtin",  # darwin_core
                "format": "csv",  # Override
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.CSV

    def test_create_job_preset_with_options_merge(
        self, client, mock_export_job_service
    ):
        """Preset options merged with explicit options."""
        response = client.post(
            "/api/export/jobs",
            json={
                "preset": "test_builtin",
                "options": {
                    "include_header": True,  # Add new option
                },
            },
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        options = call_kwargs["options"]
        # From preset
        assert options["validate"] is True
        # From explicit
        assert options["include_header"] is True

    def test_create_job_invalid_preset_returns_400(
        self, client, mock_export_job_service
    ):
        """Invalid preset name returns 400."""
        response = client.post(
            "/api/export/jobs",
            json={"preset": "nonexistent_preset"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "preset" in data["error"].lower()
        assert "nonexistent_preset" in data["error"]

    def test_create_job_user_preset(self, client, mock_export_job_service):
        """Create job using user-defined preset."""
        # First create user preset
        client.post(
            "/api/export/presets",
            json={
                "name": "my_export",
                "display_name": "My Export",
                "export_format": "json",
                "filter": {"series_type": "hdr"},
                "options": {"pretty_print": True},
            },
        )

        # Create job with user preset
        response = client.post(
            "/api/export/jobs",
            json={"preset": "my_export"},
        )

        assert response.status_code == 202

        call_kwargs = mock_export_job_service.create_job.call_args[1]
        assert call_kwargs["format"] == ExportJobFormat.JSON
        assert call_kwargs["filter"].series_type == "hdr"
        assert call_kwargs["options"]["pretty_print"] is True


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_workflow_create_preset_and_use_in_job(
        self, client, mock_export_job_service
    ):
        """Complete workflow: create preset, use in job, delete preset."""
        # 1. Create custom preset
        create_response = client.post(
            "/api/export/presets",
            json={
                "name": "summer_moths",
                "display_name": "Summer Moth Export",
                "export_format": "darwin_core",
                "description": "Export moths from summer 2024",
                "filter": {
                    "tags": ["moth", "nocturnal"],
                    "has_species": True,
                },
                "options": {
                    "validate": True,
                },
            },
        )
        assert create_response.status_code == 201

        # 2. Verify preset in list
        list_response = client.get("/api/export/presets")
        names = [p["name"] for p in list_response.get_json()["presets"]]
        assert "summer_moths" in names

        # 3. Create job using preset with additional filter
        job_response = client.post(
            "/api/export/jobs",
            json={
                "preset": "summer_moths",
                "filter": {
                    "date_start": "2024-06-01",
                    "date_end": "2024-08-31",
                },
            },
        )
        assert job_response.status_code == 202

        # Verify merged filter
        call_kwargs = mock_export_job_service.create_job.call_args[1]
        filter_obj = call_kwargs["filter"]
        assert filter_obj.tags == ["moth", "nocturnal"]
        assert filter_obj.has_species is True
        assert filter_obj.date_start == "2024-06-01"
        assert filter_obj.date_end == "2024-08-31"

        # 4. Delete preset
        delete_response = client.delete("/api/export/presets/summer_moths")
        assert delete_response.status_code == 200

        # 5. Verify preset is gone
        get_response = client.get("/api/export/presets/summer_moths")
        assert get_response.status_code == 404

    def test_workflow_multiple_presets_same_format(
        self, client, mock_export_job_service
    ):
        """Create multiple presets for same format with different filters."""
        # Create HDR series preset
        client.post(
            "/api/export/presets",
            json={
                "name": "hdr_only",
                "display_name": "HDR Series Only",
                "export_format": "json",
                "filter": {"series_type": "hdr"},
            },
        )

        # Create focus bracket preset
        client.post(
            "/api/export/presets",
            json={
                "name": "focus_only",
                "display_name": "Focus Bracket Only",
                "export_format": "json",
                "filter": {"series_type": "focus_bracket"},
            },
        )

        # Use HDR preset
        hdr_response = client.post(
            "/api/export/jobs",
            json={"preset": "hdr_only"},
        )
        assert hdr_response.status_code == 202
        hdr_filter = mock_export_job_service.create_job.call_args[1]["filter"]
        assert hdr_filter.series_type == "hdr"

        # Use focus bracket preset
        fb_response = client.post(
            "/api/export/jobs",
            json={"preset": "focus_only"},
        )
        assert fb_response.status_code == 202
        fb_filter = mock_export_job_service.create_job.call_args[1]["filter"]
        assert fb_filter.series_type == "focus_bracket"
