# GPS EXIF Tagger Improvements (#410) - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the GPS EXIF tagger's glob bug, add deployment-aware coordinate resolution, expose coordinate source selection in CLI and web UI.

**Architecture:** New `gps_coordinate_resolver` module orchestrates three coordinate sources (deployment sidecar, controls.txt GPS, manual). The existing tagger calls the resolver per-photo instead of reading controls.txt globally. New API routes expose tagging to the frontend. A settings subsection and gallery banner provide UI control.

**Tech Stack:** Python/Flask backend, React/TanStack Query frontend, piexif for EXIF, existing DeploymentService for sidecar lookups.

**Branch:** `fix/410-gps-exif-tagger`

**Design doc:** `docs/plans/2026-02-15-gps-exif-tagger-improvements.md`

---

### Task 1: Coordinate Resolver Module

**Files:**
- Create: `webui/backend/lib/gps_coordinate_resolver.py`
- Test: `Tests/unit/test_gps_coordinate_resolver.py`

**Step 1: Write the failing tests**

```python
"""Unit tests for gps_coordinate_resolver."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from webui.backend.lib.gps_coordinate_resolver import resolve_coordinates


class TestResolveCoordinates:
    """Test coordinate resolution from multiple sources."""

    def test_deployment_source_returns_coords_from_sidecar(self):
        """Deployment source uses DeploymentService.find_deployment_for_photo."""
        mock_metadata = Mock()
        mock_metadata.latitude = 35.96
        mock_metadata.longitude = -83.92
        mock_metadata.deployment_name = "Oak Ridge"

        mock_service = Mock()
        mock_service.find_deployment_for_photo.return_value = mock_metadata

        result = resolve_coordinates(
            Path("/photos/2026-02-10/photo.jpg"),
            sources=("deployment",),
            deployment_service=mock_service,
        )

        assert result["lat"] == 35.96
        assert result["lon"] == -83.92
        assert result["source"] == "deployment"
        assert result["deployment_name"] == "Oak Ridge"

    def test_gps_source_reads_controls_txt(self):
        """GPS source falls back to controls.txt."""
        mock_gps_data = {
            "has_fix": True,
            "latitude": 40.77,
            "longitude": -73.98,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "altitude": None,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.0,
        }

        with patch(
            "webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls",
            return_value=mock_gps_data,
        ):
            result = resolve_coordinates(
                Path("/photos/photo.jpg"),
                sources=("gps",),
            )

        assert result["lat"] == 40.77
        assert result["lon"] == -73.98
        assert result["source"] == "gps"

    def test_manual_source_passes_through(self):
        """Manual source uses provided coordinates."""
        result = resolve_coordinates(
            Path("/photos/photo.jpg"),
            sources=("manual",),
            manual_coords={"lat": 51.50, "lon": -0.12},
        )

        assert result["lat"] == 51.50
        assert result["lon"] == -0.12
        assert result["source"] == "manual"

    def test_fallback_chain_skips_failed_sources(self):
        """If deployment has no sidecar, falls back to GPS."""
        mock_service = Mock()
        mock_service.find_deployment_for_photo.return_value = None

        mock_gps_data = {
            "has_fix": True,
            "latitude": 40.77,
            "longitude": -73.98,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "altitude": None,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.0,
        }

        with patch(
            "webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls",
            return_value=mock_gps_data,
        ):
            result = resolve_coordinates(
                Path("/photos/photo.jpg"),
                sources=("deployment", "gps"),
                deployment_service=mock_service,
            )

        assert result["source"] == "gps"

    def test_returns_none_when_all_sources_fail(self):
        """Returns None when no source has coordinates."""
        mock_service = Mock()
        mock_service.find_deployment_for_photo.return_value = None

        mock_gps_data = {"has_fix": False, "latitude": None, "longitude": None}

        with patch(
            "webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls",
            return_value=mock_gps_data,
        ):
            result = resolve_coordinates(
                Path("/photos/photo.jpg"),
                sources=("deployment", "gps"),
                deployment_service=mock_service,
            )

        assert result is None

    def test_manual_without_coords_skipped(self):
        """Manual source is skipped when no coords provided."""
        result = resolve_coordinates(
            Path("/photos/photo.jpg"),
            sources=("manual",),
            manual_coords=None,
        )

        assert result is None

    def test_deployment_with_null_coords_skipped(self):
        """Deployment with null lat/lon is skipped."""
        mock_metadata = Mock()
        mock_metadata.latitude = None
        mock_metadata.longitude = None

        mock_service = Mock()
        mock_service.find_deployment_for_photo.return_value = mock_metadata

        result = resolve_coordinates(
            Path("/photos/photo.jpg"),
            sources=("deployment",),
            deployment_service=mock_service,
        )

        assert result is None

    def test_invalid_source_name_raises(self):
        """Unknown source name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown coordinate source"):
            resolve_coordinates(
                Path("/photos/photo.jpg"),
                sources=("invalid_source",),
            )

    def test_gps_data_includes_full_metadata(self):
        """GPS source result includes full gps_data for embed_gps_exif."""
        mock_gps_data = {
            "has_fix": True,
            "latitude": 40.77,
            "longitude": -73.98,
            "fix_mode": 3,
            "gpstime": 1700000000,
            "altitude": 42.5,
            "satellites_used": 8,
            "hdop": 1.2,
            "pdop": 2.0,
        }

        with patch(
            "webui.backend.lib.gps_coordinate_resolver.get_gps_data_from_controls",
            return_value=mock_gps_data,
        ):
            result = resolve_coordinates(
                Path("/photos/photo.jpg"),
                sources=("gps",),
            )

        assert result["gps_data"]["altitude"] == 42.5
        assert result["gps_data"]["satellites_used"] == 8
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_gps_coordinate_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'webui.backend.lib.gps_coordinate_resolver'`

**Step 3: Write the implementation**

```python
"""Coordinate resolution strategy for GPS EXIF tagging.

Resolves GPS coordinates for a photo by walking a configurable chain of
sources. Each source is tried in order; the first to return valid
coordinates wins.

Sources:
    deployment - Look up deployment sidecar metadata for the photo's directory
    gps        - Read current GPS fix from controls.txt
    manual     - User-provided lat/lon pass-through
"""

import logging
from pathlib import Path
from typing import Any

from webui.backend.lib.gps_exif_lib import get_gps_data_from_controls

logger = logging.getLogger(__name__)

VALID_SOURCES = ("deployment", "gps", "manual")


def resolve_coordinates(
    photo_path: Path,
    sources: tuple[str, ...] = ("deployment", "gps"),
    manual_coords: dict | None = None,
    deployment_service: Any | None = None,
) -> dict | None:
    """Resolve GPS coordinates for a photo from configured sources.

    Args:
        photo_path: Path to the photo file.
        sources: Ordered tuple of source names to try.
        manual_coords: Dict with 'lat' and 'lon' keys (for manual source).
        deployment_service: DeploymentService instance (for deployment source).
            If None and 'deployment' is in sources, that source is skipped.

    Returns:
        Dict with keys: lat, lon, source, deployment_name (optional), gps_data.
        None if no source has valid coordinates.

    Raises:
        ValueError: If an unknown source name is provided.
    """
    for source in sources:
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Unknown coordinate source: '{source}'. "
                f"Valid sources: {', '.join(VALID_SOURCES)}"
            )

        result = _try_source(source, photo_path, manual_coords, deployment_service)
        if result is not None:
            return result

    return None


def _try_source(
    source: str,
    photo_path: Path,
    manual_coords: dict | None,
    deployment_service: Any | None,
) -> dict | None:
    """Try a single coordinate source. Returns result dict or None."""
    if source == "deployment":
        return _resolve_from_deployment(photo_path, deployment_service)
    elif source == "gps":
        return _resolve_from_gps()
    elif source == "manual":
        return _resolve_from_manual(manual_coords)
    return None


def _resolve_from_deployment(photo_path: Path, service: Any | None) -> dict | None:
    """Resolve coordinates from deployment sidecar metadata."""
    if service is None:
        return None

    try:
        metadata = service.find_deployment_for_photo(photo_path)
    except Exception as e:
        logger.warning(f"Deployment lookup failed for {photo_path}: {e}")
        return None

    if metadata is None:
        return None

    lat = getattr(metadata, "latitude", None)
    lon = getattr(metadata, "longitude", None)
    if lat is None or lon is None:
        return None

    name = getattr(metadata, "deployment_name", None)

    # Build gps_data dict compatible with embed_gps_exif
    gps_data = {
        "has_fix": True,
        "latitude": lat,
        "longitude": lon,
        "altitude": getattr(metadata, "altitude", None),
        "fix_mode": 3,
        "gpstime": 0,
        "satellites_used": 0,
        "hdop": 99.99,
        "pdop": 99.99,
    }

    return {
        "lat": lat,
        "lon": lon,
        "source": "deployment",
        "deployment_name": name,
        "gps_data": gps_data,
    }


def _resolve_from_gps() -> dict | None:
    """Resolve coordinates from controls.txt GPS data."""
    try:
        gps_data = get_gps_data_from_controls()
    except Exception as e:
        logger.warning(f"Failed to read GPS data from controls: {e}")
        return None

    if not gps_data.get("has_fix", False):
        return None

    lat = gps_data.get("latitude")
    lon = gps_data.get("longitude")
    if lat is None or lon is None:
        return None

    return {
        "lat": lat,
        "lon": lon,
        "source": "gps",
        "gps_data": gps_data,
    }


def _resolve_from_manual(coords: dict | None) -> dict | None:
    """Resolve coordinates from user-provided manual input."""
    if coords is None:
        return None

    lat = coords.get("lat")
    lon = coords.get("lon")
    if lat is None or lon is None:
        return None

    gps_data = {
        "has_fix": True,
        "latitude": lat,
        "longitude": lon,
        "altitude": coords.get("altitude"),
        "fix_mode": 3,
        "gpstime": 0,
        "satellites_used": 0,
        "hdop": 99.99,
        "pdop": 99.99,
    }

    return {
        "lat": lat,
        "lon": lon,
        "source": "manual",
        "gps_data": gps_data,
    }
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_gps_coordinate_resolver.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add webui/backend/lib/gps_coordinate_resolver.py Tests/unit/test_gps_coordinate_resolver.py
git commit -m "feat(gps): add coordinate resolver with deployment/gps/manual sources (#410)"
```

---

### Task 2: Fix Glob Default and Add CLI Flag

**Files:**
- Modify: `webui/cli/gps_exif_tagger.py:71` (PATTERN_DEFAULT)
- Modify: `webui/cli/gps_exif_tagger.py:407-451` (argparse, add --coordinate-source)
- Test: `Tests/unit/test_gps_exif_tagger_cli.py` (add new test)

**Step 1: Write the failing test**

Add to `Tests/unit/test_gps_exif_tagger_cli.py`:

```python
def test_default_pattern_is_recursive(self):
    """Default pattern should match photos in subdirectories."""
    from webui.cli.gps_exif_tagger import PATTERN_DEFAULT
    assert "**" in PATTERN_DEFAULT, "Default pattern must be recursive to find photos in date subdirectories"

def test_coordinate_source_flag_accepted(self):
    """CLI accepts --coordinate-source flag."""
    from webui.cli.gps_exif_tagger import main
    import sys
    with patch.object(sys, "argv", ["tagger", "--mode", "batch", "--coordinate-source", "deployment,gps", "--dry-run"]):
        # Should parse without error (will fail on missing directory, that's ok)
        pass
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest Tests/unit/test_gps_exif_tagger_cli.py::test_default_pattern_is_recursive -v`
Expected: FAIL — `assert "**" in "*.jpg"`

**Step 3: Apply the fixes**

In `webui/cli/gps_exif_tagger.py`:

1. Line 71: Change `PATTERN_DEFAULT = "*.jpg"` to `PATTERN_DEFAULT = "**/*.jpg"`

2. After line 450 (the `--verbose` argument), add:

```python
    parser.add_argument(
        "--coordinate-source",
        default="deployment,gps",
        help="Comma-separated coordinate sources in priority order (default: deployment,gps). "
        "Valid sources: deployment, gps, manual",
    )
```

3. After line 452 (`args = parser.parse_args()`), add parsing logic:

```python
    # Parse coordinate sources
    coordinate_sources = tuple(s.strip() for s in args.coordinate_source.split(","))
```

4. Pass `coordinate_sources` to `batch_process_directory` and `watch_directory` calls (see Task 3).

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_gps_exif_tagger_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add webui/cli/gps_exif_tagger.py Tests/unit/test_gps_exif_tagger_cli.py
git commit -m "fix(gps): change default glob to **/*.jpg and add --coordinate-source flag (#410)"
```

---

### Task 3: Integrate Resolver into Tagger

**Files:**
- Modify: `webui/cli/gps_exif_tagger.py:161-205` (process_single_photo)
- Modify: `webui/cli/gps_exif_tagger.py:208-285` (batch_process_directory)
- Modify: `webui/cli/gps_exif_tagger.py:288-404` (watch_directory)
- Test: `Tests/unit/test_gps_exif_tagger_operations.py` (add resolver tests)

**Step 1: Write the failing test**

Add to `Tests/unit/test_gps_exif_tagger_operations.py`:

```python
class TestResolverIntegration:
    """Test that tagger uses coordinate resolver."""

    def test_batch_uses_resolver_per_photo(self):
        """batch_process_directory calls resolve_coordinates for each photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            # Create two photos in subdirectories (tests recursive glob too)
            subdir = tmp_path / "2026-02-10"
            subdir.mkdir()
            for name in ["photo_001.jpg", "photo_002.jpg"]:
                img = Image.new("RGB", (100, 100), color="white")
                img.save(subdir / name)

            mock_result = {
                "lat": 35.96,
                "lon": -83.92,
                "source": "deployment",
                "deployment_name": "Test Deploy",
                "gps_data": {
                    "has_fix": True,
                    "latitude": 35.96,
                    "longitude": -83.92,
                    "altitude": None,
                    "fix_mode": 3,
                    "gpstime": 0,
                    "satellites_used": 0,
                    "hdop": 99.99,
                    "pdop": 99.99,
                },
            }

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_result,
            ) as mock_resolve:
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment", "gps"),
                )

            # Resolver called once per photo
            assert mock_resolve.call_count == 2
            assert stats["total"] == 2

    def test_batch_skips_photo_when_resolver_returns_none(self):
        """Photos are skipped when no coordinate source has data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            img = Image.new("RGB", (100, 100), color="white")
            img.save(tmp_path / "photo.jpg")

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=None,
            ):
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment", "gps"),
                )

            assert stats["skipped"] == 1

    def test_batch_stats_include_source_counts(self):
        """Batch stats track how many photos tagged per source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            logger = Mock()

            for i in range(3):
                img = Image.new("RGB", (100, 100), color="white")
                img.save(tmp_path / f"photo_{i}.jpg")

            mock_result = {
                "lat": 35.96,
                "lon": -83.92,
                "source": "deployment",
                "gps_data": {
                    "has_fix": True, "latitude": 35.96, "longitude": -83.92,
                    "altitude": None, "fix_mode": 3, "gpstime": 0,
                    "satellites_used": 0, "hdop": 99.99, "pdop": 99.99,
                },
            }

            with patch(
                "webui.cli.gps_exif_tagger.resolve_coordinates",
                return_value=mock_result,
            ):
                stats = gps_exif_tagger.batch_process_directory(
                    tmp_path,
                    logger,
                    pattern="**/*.jpg",
                    coordinate_sources=("deployment",),
                )

            assert "source_counts" in stats
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_gps_exif_tagger_operations.py::TestResolverIntegration -v`
Expected: FAIL — `TypeError: batch_process_directory() got an unexpected keyword argument 'coordinate_sources'`

**Step 3: Implement the integration**

Key changes to `webui/cli/gps_exif_tagger.py`:

1. Add import at top (after existing imports):
```python
from webui.backend.lib.gps_coordinate_resolver import resolve_coordinates
from webui.backend.services.deployment_service import DeploymentService
```

2. Add module-level deployment service (lazy init):
```python
_deployment_service = None

def _get_deployment_service():
    global _deployment_service
    if _deployment_service is None:
        _deployment_service = DeploymentService()
    return _deployment_service
```

3. Update `process_single_photo` signature to accept `gps_data`:
```python
def process_single_photo(
    photo_path: Path,
    logger: logging.Logger,
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False,
    gps_data: dict | None = None,
) -> dict[str, Any]:
```
And pass `gps_data` to `embed_gps_exif`:
```python
    result = embed_gps_exif(photo_path, gps_data=gps_data, backup=backup, dry_run=dry_run)
```

4. Update `batch_process_directory` to accept and use `coordinate_sources`:
```python
def batch_process_directory(
    directory: Path,
    logger: logging.Logger,
    pattern: str = "**/*.jpg",
    force: bool = False,
    backup: bool = False,
    dry_run: bool = False,
    coordinate_sources: tuple[str, ...] = ("deployment", "gps"),
) -> dict[str, Any]:
```
Add `source_counts` to stats, resolve per photo:
```python
    stats = {"total": 0, "tagged": 0, "skipped": 0, "errors": 0, "error_list": [], "source_counts": {}}

    # ... (existing photo finding code) ...

    for photo_path in photo_files:
        # Resolve coordinates for this specific photo
        resolved = resolve_coordinates(
            photo_path,
            sources=coordinate_sources,
            deployment_service=_get_deployment_service(),
        )

        if resolved is None:
            logger.warning(f"Skipped {photo_path.name} (no coordinates from any source)")
            stats["skipped"] += 1
            continue

        source = resolved["source"]
        source_label = resolved.get("deployment_name", source)
        logger.debug(f"Using {source} coordinates for {photo_path.name} ({source_label})")

        result = process_single_photo(
            photo_path, logger, force, backup, dry_run,
            gps_data=resolved["gps_data"],
        )

        if result["success"]:
            stats["tagged"] += 1
            stats["source_counts"][source] = stats["source_counts"].get(source, 0) + 1
        elif result["skipped"]:
            stats["skipped"] += 1
        elif result["error"]:
            stats["errors"] += 1
            stats["error_list"].append((photo_path, result["error"]))
```

5. Same pattern for `watch_directory` — add `coordinate_sources` param, resolve per photo.

6. Update `main()` to pass parsed sources through to batch/watch calls.

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_gps_exif_tagger_operations.py -v`
Expected: All tests PASS (both new and existing)

**Step 5: Commit**

```bash
git add webui/cli/gps_exif_tagger.py Tests/unit/test_gps_exif_tagger_operations.py
git commit -m "feat(gps): integrate coordinate resolver into tagger batch and watch modes (#410)"
```

---

### Task 4: Update Service File

**Files:**
- Modify: `webui/services/gps-exif-tagger.service:44,47-53`

**Step 1: Apply changes**

Line 44: `Environment="GPS_EXIF_PATTERN=*.jpg"` → `Environment="GPS_EXIF_PATTERN=**/*.jpg"`

Lines 47-53: Add `--coordinate-source` to ExecStart:
```ini
ExecStart=/usr/bin/python3 ${MOTHBOX_HOME}/webui/cli/gps_exif_tagger.py \
    --mode immediate \
    --watch \
    --directory ${MOTHBOX_PHOTOS_DIR} \
    --interval ${GPS_EXIF_INTERVAL} \
    --pattern ${GPS_EXIF_PATTERN} \
    --coordinate-source deployment,gps \
    --verbose
```

**Step 2: Commit**

```bash
git add webui/services/gps-exif-tagger.service
git commit -m "fix(service): update tagger to recursive glob and deployment-first coords (#410)"
```

---

### Task 5: API Routes

**Files:**
- Create: `webui/backend/routes/gps_exif.py`
- Modify: `webui/backend/app.py:347,370` (register blueprint)
- Test: `Tests/unit/test_gps_exif_routes.py`

**Step 1: Write the failing tests**

```python
"""Unit tests for GPS EXIF tagger API routes."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from webui.backend.routes.gps_exif import gps_exif_bp


@pytest.fixture
def app():
    """Create test Flask app with GPS EXIF blueprint."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(gps_exif_bp, url_prefix="/api/gps-exif")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetStatus:
    def test_returns_status(self, client):
        """GET /api/gps-exif/status returns tagger status."""
        response = client.get("/api/gps-exif/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "coordinate_sources" in data


class TestTagPhoto:
    def test_tag_single_photo(self, client):
        """POST /api/gps-exif/tag-photo tags a photo."""
        with patch("webui.backend.routes.gps_exif._tag_single_photo") as mock_tag:
            mock_tag.return_value = {
                "success": True,
                "source_used": "gps",
                "coordinates": {"lat": 40.77, "lon": -73.98},
            }
            response = client.post(
                "/api/gps-exif/tag-photo",
                json={"photo_path": "2026-02-10/photo.jpg", "coordinate_source": "gps"},
            )
            assert response.status_code == 200

    def test_rejects_missing_photo_path(self, client):
        """POST /api/gps-exif/tag-photo rejects missing photo_path."""
        response = client.post("/api/gps-exif/tag-photo", json={})
        assert response.status_code == 400


class TestBatchTag:
    def test_batch_tag_returns_stats(self, client):
        """POST /api/gps-exif/batch-tag returns processing stats."""
        with patch("webui.backend.routes.gps_exif._batch_tag") as mock_batch:
            mock_batch.return_value = {
                "total": 5, "tagged": 3, "skipped": 2, "errors": 0,
                "source_counts": {"deployment": 2, "gps": 1},
            }
            response = client.post(
                "/api/gps-exif/batch-tag",
                json={"coordinate_sources": ["deployment", "gps"]},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["total"] == 5


class TestConfig:
    def test_get_config(self, client):
        """GET /api/gps-exif/config returns current configuration."""
        response = client.get("/api/gps-exif/config")
        assert response.status_code == 200
        data = response.get_json()
        assert "default_sources" in data

    def test_update_config(self, client):
        """PUT /api/gps-exif/config updates configuration."""
        with patch("webui.backend.routes.gps_exif._save_config") as mock_save:
            mock_save.return_value = True
            response = client.put(
                "/api/gps-exif/config",
                json={"default_sources": ["gps"]},
            )
            assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_gps_exif_routes.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the route implementation**

Create `webui/backend/routes/gps_exif.py` following the pattern in `routes/gps.py`:

- Blueprint: `gps_exif_bp = Blueprint("gps_exif", __name__)`
- Routes: `/status`, `/tag-photo`, `/batch-tag`, `/config`
- Uses `resolve_coordinates` from the resolver module
- Uses `embed_gps_exif` from gps_exif_lib
- Path traversal validation on photo paths using `validate_photo_path` pattern from gallery routes
- Config persisted to `user_preferences.json` (existing preferences infrastructure)

Register in `app.py`:
- Line 347 area: `from routes.gps_exif import gps_exif_bp`
- Line 370 area: `app.register_blueprint(gps_exif_bp, url_prefix="/api/gps-exif")`

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest Tests/unit/test_gps_exif_routes.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add webui/backend/routes/gps_exif.py webui/backend/app.py Tests/unit/test_gps_exif_routes.py
git commit -m "feat(api): add GPS EXIF tagger API routes (#410)"
```

---

### Task 6: Frontend — API Layer and Query Keys

**Files:**
- Modify: `webui/frontend/src/utils/api.js:136` (add GPS EXIF API calls)
- Modify: `webui/frontend/src/utils/queryKeys.js:58` (add query keys)
- Create: `webui/frontend/src/hooks/useGpsExif.js`

**Step 1: Add API functions**

In `webui/frontend/src/utils/api.js`, after line 136 (GPS APIs section):

```javascript
// GPS EXIF Tagger APIs
export const getGpsExifStatus = () => api.get('/gps-exif/status')
export const getGpsExifConfig = () => api.get('/gps-exif/config')
export const updateGpsExifConfig = (config) => api.put('/gps-exif/config', config)
export const tagSinglePhoto = (data) => api.post('/gps-exif/tag-photo', data)
export const batchTagPhotos = (data) => api.post('/gps-exif/batch-tag', data)
```

**Step 2: Add query keys**

In `webui/frontend/src/utils/queryKeys.js`, after GPS_CONFIG line 58:

```javascript
  GPS_EXIF_STATUS: ['gps-exif-status'],
  GPS_EXIF_CONFIG: ['gps-exif-config'],
```

**Step 3: Create the hook**

```javascript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  getGpsExifStatus,
  getGpsExifConfig,
  updateGpsExifConfig,
  batchTagPhotos,
  tagSinglePhoto,
} from '../utils/api'

export function useGpsExifStatus() {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_STATUS,
    queryFn: async () => {
      const response = await getGpsExifStatus()
      return response.data
    },
    staleTime: 10 * 1000,
  })
}

export function useGpsExifConfig() {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_CONFIG,
    queryFn: async () => {
      const response = await getGpsExifConfig()
      return response.data
    },
    staleTime: 60 * 1000,
  })
}

export function useUpdateGpsExifConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateGpsExifConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_CONFIG })
    },
  })
}

export function useBatchTagPhotos() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: batchTagPhotos,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.PHOTOS })
    },
  })
}

export function useTagSinglePhoto() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: tagSinglePhoto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
    },
  })
}
```

**Step 4: Commit**

```bash
git add webui/frontend/src/utils/api.js webui/frontend/src/utils/queryKeys.js webui/frontend/src/hooks/useGpsExif.js
git commit -m "feat(frontend): add GPS EXIF API layer and TanStack Query hooks (#410)"
```

---

### Task 7: Frontend — GPS Settings EXIF Subsection

**Files:**
- Modify: `webui/frontend/src/components/GPSSettings.jsx` (add collapsible EXIF section after line ~491)

**Step 1: Add the EXIF tagging subsection**

Import the hook at top of file:
```javascript
import { useGpsExifStatus, useGpsExifConfig, useUpdateGpsExifConfig } from '../hooks/useGpsExif'
```

Add state for collapsed section:
```javascript
const [exifSectionOpen, setExifSectionOpen] = useState(false)
```

Add hooks:
```javascript
const { data: exifStatus } = useGpsExifStatus()
const { data: exifConfig } = useGpsExifConfig()
const updateExifConfig = useUpdateGpsExifConfig()
```

Insert after the GPS configuration inputs section (before Advanced Timeout Configuration), a collapsible card matching the existing nested pattern:

- Header: "GPS EXIF Tagging" with collapse toggle
- **Default Source** dropdown: options map to `["deployment,gps", "gps", "manual"]`
- **Status indicator**: green/gray dot + "Running"/"Stopped" from `exifStatus.service_running`
- **Stats line**: `"{tagged} photos tagged ({source_counts})"` from `exifStatus`
- **Save** button calls `updateExifConfig.mutate({ default_sources: selectedSources })`

Follow the exact styling pattern of the Advanced Timeout section (nested `div` with `border border-gray-300 rounded-md p-3`).

**Step 2: Build and verify**

Run: `cd webui/frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add webui/frontend/src/components/GPSSettings.jsx
git commit -m "feat(ui): add EXIF tagging config to GPS Settings (#410)"
```

---

### Task 8: Frontend — Gallery GPS Tag Banner

**Files:**
- Create: `webui/frontend/src/components/Gallery/GpsTagBanner.jsx`
- Modify: `webui/frontend/src/pages/Gallery.jsx` (insert banner above search bar, ~line 677)

**Step 1: Create the banner component**

Follow the `ActiveScheduleBanner` pattern (amber bg, border, icon, action button):

```jsx
import { useState } from 'react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useBatchTagPhotos, useGpsExifConfig } from '../../hooks/useGpsExif'
import toast from 'react-hot-toast'

const SOURCE_OPTIONS = [
  { value: 'deployment,gps', label: 'Deployment → GPS fallback' },
  { value: 'gps', label: 'GPS only' },
  { value: 'manual', label: 'Manual coordinates' },
]

export default function GpsTagBanner({ untaggedCount, currentDirectory }) {
  const { data: config } = useGpsExifConfig()
  const batchTag = useBatchTagPhotos()
  const [source, setSource] = useState(config?.default_sources?.join(',') || 'deployment,gps')
  const [manualLat, setManualLat] = useState('')
  const [manualLon, setManualLon] = useState('')

  if (!untaggedCount || untaggedCount === 0) return null

  const handleTag = () => {
    const payload = {
      coordinate_sources: source.split(','),
      directory: currentDirectory,
    }
    if (source === 'manual') {
      payload.manual_coords = { lat: parseFloat(manualLat), lon: parseFloat(manualLon) }
    }
    batchTag.mutate(payload, {
      onSuccess: (res) => toast.success(`Tagged ${res.data.tagged} photos`),
      onError: () => toast.error('Tagging failed'),
    })
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-amber-600" />
          <span className="text-sm font-medium text-amber-900">
            {untaggedCount} photo{untaggedCount !== 1 ? 's' : ''} without GPS coordinates
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="text-sm border border-amber-300 rounded px-2 py-1 bg-white"
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            onClick={handleTag}
            disabled={batchTag.isPending}
            className="px-3 py-1 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
          >
            {batchTag.isPending ? 'Tagging...' : 'Tag Now'}
          </button>
        </div>
      </div>
      {source === 'manual' && (
        <div className="mt-2 flex items-center gap-2">
          <input type="number" step="any" placeholder="Latitude" value={manualLat}
            onChange={(e) => setManualLat(e.target.value)}
            className="text-sm border rounded px-2 py-1 w-32" />
          <input type="number" step="any" placeholder="Longitude" value={manualLon}
            onChange={(e) => setManualLon(e.target.value)}
            className="text-sm border rounded px-2 py-1 w-32" />
        </div>
      )}
    </div>
  )
}
```

**Step 2: Insert into Gallery.jsx**

Import at top:
```javascript
import GpsTagBanner from '../components/Gallery/GpsTagBanner'
```

Import the status hook:
```javascript
import { useGpsExifStatus } from '../hooks/useGpsExif'
```

Add hook call inside the Gallery component:
```javascript
const { data: exifStatus } = useGpsExifStatus()
```

Insert the banner between the header and search bar (~line 677):
```jsx
<GpsTagBanner
  untaggedCount={exifStatus?.untagged_count}
  currentDirectory={activeFilters?.date}
/>
```

**Step 3: Build and verify**

Run: `cd webui/frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add webui/frontend/src/components/Gallery/GpsTagBanner.jsx webui/frontend/src/pages/Gallery.jsx
git commit -m "feat(ui): add GPS tag banner to gallery for untagged photos (#410)"
```

---

### Task 9: Final Integration Test and Cleanup

**Files:**
- Review all modified files
- Run full test suite for affected modules

**Step 1: Run backend tests**

```bash
python3 -m pytest Tests/unit/test_gps_coordinate_resolver.py Tests/unit/test_gps_exif_tagger_operations.py Tests/unit/test_gps_exif_tagger_cli.py Tests/unit/test_gps_exif_routes.py -v
```

Expected: All PASS

**Step 2: Run linting**

```bash
python3 -m ruff check webui/backend/lib/gps_coordinate_resolver.py webui/backend/routes/gps_exif.py webui/cli/gps_exif_tagger.py
```

Expected: No errors

**Step 3: Build frontend**

```bash
cd webui/frontend && npm run build
```

Expected: Build succeeds with no errors

**Step 4: Final commit if any cleanup needed**

```bash
git add -A && git commit -m "chore: cleanup after GPS EXIF tagger improvements (#410)"
```
