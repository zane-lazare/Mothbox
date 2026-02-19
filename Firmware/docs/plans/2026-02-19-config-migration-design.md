# Config File Migration System Design

**Issue**: #378 — Add config file migration system for update_mothbox.sh
**Date**: 2026-02-19

## Problem

When `update_mothbox.sh` runs, it syncs firmware but leaves `/etc/mothbox/` configs untouched. New settings added to config templates never reach existing installations, causing silent misbehavior (e.g., HDR defaulting to 3 photos instead of 1).

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Add + rename + remove keys | Covers real-world needs without full schema migration complexity |
| Definition location | Separate `config_migrations.sh` | Keeps update_mothbox.sh clean, easy to review migration diffs |
| Tracking | Idempotent re-run | No migration registry needed; each operation checks state first |
| Backups | Single rolling `.pre-migration` | Matches existing pattern from camera_settings split migration |

## Architecture

### New File: `config_migrations.sh`

Located in repo root alongside `update_mothbox.sh`. Sourced by the update script.

### Helper Functions

Three format-aware functions that handle both `key=value` (controls.txt) and `SETTING,VALUE,DETAILS` CSV formats:

#### `ensure_key file format key default [details]`
- Adds key with default value if it doesn't exist
- No-op if key already present (idempotent)
- For CSV format, `details` provides the third column

#### `rename_key file format old_key new_key`
- Renames a key in-place, preserving the user's value
- No-op if old key missing or new key already exists

#### `remove_key file format key`
- Deletes the line containing the key
- No-op if key doesn't exist

### Backup

Before any migration, each config file is copied to `<file>.pre-migration`. Single rolling backup — always reflects state before the most recent update.

### Entry Point

```bash
run_config_migrations() {
    local config_dir="$1"

    backup_config "$config_dir/controls.txt"
    backup_config "$config_dir/camera_settings.csv"
    backup_config "$config_dir/schedule_settings.csv"

    migrate_controls_txt "$config_dir/controls.txt"
    migrate_camera_settings "$config_dir/camera_settings.csv"
    migrate_schedule_settings "$config_dir/schedule_settings.csv"

    log "Config migrations complete"
}
```

### Integration Point

In `update_mothbox.sh`, after file sync but before service restarts:

```bash
source "$(dirname "$0")/config_migrations.sh"
run_config_migrations "$CONFIG_DIR"
```

## Config File Formats

### controls.txt — `key=value`
```
shutdown_enabled=False
relay_enabled=true
cache_max_size_mb=500
```

### camera_settings.csv / schedule_settings.csv — CSV
```
SETTING,VALUE,DETAILS
LensPosition,0.5,unit in diopters
HDR,1,0 is off 3 is HDR with 3 photos
```

## Per-File Migration Functions

### `migrate_controls_txt()`
Ensures newer keys exist: `cache_warm_on_startup`, `cache_warm_count`, `log_level`, `log_retention_days`, `flash_duration_ms`, etc.

### `migrate_camera_settings()`
Ensures newer keys exist: `HDR`, `HDR_width`, `AutoCalibration`, `AutoCalibrationPeriod`, `ImageFileType`, etc.

### `migrate_schedule_settings()`
Ensures any newer keys exist (currently minimal changes expected).

The exact migration list will be determined by comparing the oldest known deployed configs against current templates.

## Testing

- **Bash unit tests**: Create temp config files, run migrations, assert expected contents. Verify idempotency by running twice.
- **Python integration tests**: Invoke `config_migrations.sh` via subprocess, verify file contents programmatically.
- **Manual Pi test**: Run `update_mothbox.sh` on a device with old configs, verify new keys appear and user values are preserved.

## Acceptance Criteria

- [ ] Running `update_mothbox.sh` adds missing settings to installed configs
- [ ] Existing user-customized values are preserved
- [ ] Renamed keys preserve user values under the new name
- [ ] Removed deprecated keys are cleaned up
- [ ] Migrations are idempotent (safe to run multiple times)
- [ ] `.pre-migration` backup created before changes
- [ ] New installations still get full config files (no change to install path)
