# GPS EXIF Tagger Improvements (#410)

## Summary

Fix the GPS EXIF tagger service's glob bug, add deployment-aware coordinate
resolution for batch correctness, expose coordinate source selection in the
CLI and web UI, and update the service configuration.

## Problem

1. **Glob bug**: Default pattern `*.jpg` misses photos in date subdirectories
   (`photos/YYYY-MM-DD/*.jpg`).
2. **Batch correctness**: Batch mode applies the device's *current* GPS to all
   photos regardless of capture date/location. Incorrect when the device has
   moved between deployments.
3. **No UI control**: Users cannot choose which coordinate source to use for
   tagging (deployment metadata vs live GPS vs manual entry).

## Design

### 1. Coordinate Resolution Strategy

New module: `webui/backend/lib/gps_coordinate_resolver.py`

```python
def resolve_coordinates(
    photo_path: Path,
    sources: tuple[str, ...] = ('deployment', 'gps'),
    manual_coords: dict | None = None,
) -> dict | None:
    """Resolve GPS coordinates for a photo from configured sources.

    Returns:
        {lat, lon, source: 'deployment'|'gps'|'manual', deployment_name?: str}
        or None if no source has valid coordinates.
    """
```

Resolution sources (walked in order, first valid result wins):

| Source | Implementation |
|--------|---------------|
| `deployment` | `DeploymentService.find_deployment_for_photo()` - walks directory tree, LRU cached |
| `gps` | `get_gps_data_from_controls()` - reads controls.txt |
| `manual` | Pass-through of user-provided lat/lon |

### 2. Tagger Fixes

- Change `PATTERN_DEFAULT` from `"*.jpg"` to `"**/*.jpg"` in
  `webui/cli/gps_exif_tagger.py`.
- Modify `batch_process_directory()` and `watch_directory()` to call
  `resolve_coordinates()` per photo instead of reading controls.txt once.
- Pass resolved `gps_data` dict into `embed_gps_exif()` via its existing
  parameter (no signature change needed).
- Add `--coordinate-source` CLI flag (default: `deployment,gps`).
- Log which source was used per photo; batch summary reports counts per source.

### 3. API Endpoints

New route file: `webui/backend/routes/gps_exif.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/gps-exif/status` | Service status, tagging stats, per-source breakdown |
| `POST` | `/api/gps-exif/tag-photo` | Tag single photo with specified coordinate source |
| `POST` | `/api/gps-exif/batch-tag` | Batch tag with source config and optional date range |
| `GET` | `/api/gps-exif/config` | Current tagger config (default source chain, pattern) |
| `PUT` | `/api/gps-exif/config` | Update tagger config (persisted) |

Security: CSRF on POST/PUT, path traversal validation, rate limiting on batch
(10/min).

### 4. Frontend: GPS Settings Integration

Add an "EXIF Tagging" subsection to the existing `GPSSettings` collapsible card:

- **Default Coordinate Source** dropdown: `Deployment -> GPS fallback` | `GPS only` | `Manual`
- **Service status** indicator with last-tagged timestamp
- **Stats row**: tagged count with per-source breakdown
- Persisted via `PUT /api/gps-exif/config`

### 5. Frontend: Gallery Banner

Contextual banner at top of Gallery when untagged photos exist in current view.
Follows `ActiveScheduleBanner` pattern.

| State | Color | Content |
|-------|-------|---------|
| Untagged photos exist | Amber | Count + "Tag Now" button + source dropdown |
| Tagging in progress | Blue | Progress indicator + cancel |
| All tagged | Hidden | Banner disappears |

Source dropdown defaults to Settings config. "Manual" expands inline lat/lon
input. "Tag Now" calls `POST /api/gps-exif/batch-tag` scoped to current view.

### 6. Service Configuration

Update existing `webui/services/gps-exif-tagger.service`:

- Change `GPS_EXIF_PATTERN=*.jpg` to `GPS_EXIF_PATTERN=**/*.jpg`
- Add `--coordinate-source deployment,gps` to `ExecStart`

Install/update scripts already handle this service file — no script changes
needed.

## Files Modified

| File | Change |
|------|--------|
| `webui/backend/lib/gps_coordinate_resolver.py` | **New** - coordinate resolution strategy |
| `webui/cli/gps_exif_tagger.py` | Fix glob default, add `--coordinate-source`, use resolver |
| `webui/backend/lib/gps_exif_lib.py` | No changes (existing `gps_data` param sufficient) |
| `webui/backend/routes/gps_exif.py` | **New** - API endpoints |
| `webui/frontend/src/components/GPSSettings.jsx` | Add EXIF Tagging subsection |
| `webui/frontend/src/components/Gallery/GpsTagBanner.jsx` | **New** - gallery banner |
| `webui/frontend/src/hooks/useGpsExifStatus.js` | **New** - TanStack Query hook |
| `webui/services/gps-exif-tagger.service` | Update pattern + coordinate source |

## Dependencies

- Existing: `DeploymentService`, `gps_exif_lib`, `deployment_sidecar`
- No new packages required

## Out of Scope

- #409 (GPS lock contention metrics) - separate concern
- #382 (scheduler coordinate refresh) - separate subsystem
- #272 (sensor metadata) - different domain
- #150 full scope (dashboard panel, batch modal) - this covers a minimal UI only
