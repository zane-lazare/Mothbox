# Config File Migration System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an idempotent config migration system to `update_mothbox.sh` that adds missing keys, renames keys, and removes deprecated keys — preserving user values.

**Architecture:** A single `config_migrations.sh` script in the repo root with format-aware helper functions (`ensure_key`, `rename_key`, `remove_key`) and per-config-file migration functions. Sourced by `update_mothbox.sh` after file sync, before service restarts.

**Tech Stack:** Bash (matching existing scripts), Python pytest for integration tests

---

### Task 1: Create `config_migrations.sh` skeleton with helper functions

**Files:**
- Create: `config_migrations.sh`
- Test: `installation-utils/test_config_migrations.sh`

**Step 1: Write the test script skeleton**

Create `installation-utils/test_config_migrations.sh`:

```bash
#!/bin/bash
# ==============================================================================
# Mothbox Config Migration Test Suite
# ==============================================================================
#
# Tests the config migration helper functions to ensure they correctly
# add, rename, and remove keys in both key=value and CSV config formats.
#
# Usage:
#   ./test_config_migrations.sh
#
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config_migrations.sh"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Temp dir for test config files
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

assert_equals() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_contains() {
    local test_name="$1"
    local file="$2"
    local pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        echo "  Pattern not found: $pattern"
        echo "  File contents:"
        cat "$file" | sed 's/^/    /'
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_not_contains() {
    local test_name="$1"
    local file="$2"
    local pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        echo "  Pattern should NOT be present: $pattern"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Config Migration Test Suite${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# ============================================================================
# ensure_key tests (key=value format)
# ============================================================================
echo -e "${BLUE}--- ensure_key: key=value format ---${NC}"

# Test: adds missing key
cat > "$TEST_DIR/kv1.txt" <<'EOF'
existing_key=existing_value
EOF
ensure_key "$TEST_DIR/kv1.txt" "keyvalue" "new_key" "default_val"
assert_file_contains "ensure_key adds missing key" "$TEST_DIR/kv1.txt" "^new_key=default_val$"
assert_file_contains "ensure_key preserves existing key" "$TEST_DIR/kv1.txt" "^existing_key=existing_value$"

# Test: does NOT overwrite existing key
cat > "$TEST_DIR/kv2.txt" <<'EOF'
my_key=user_value
EOF
ensure_key "$TEST_DIR/kv2.txt" "keyvalue" "my_key" "default_val"
assert_file_contains "ensure_key preserves user value" "$TEST_DIR/kv2.txt" "^my_key=user_value$"
assert_file_not_contains "ensure_key does not add duplicate" "$TEST_DIR/kv2.txt" "^my_key=default_val$"

# Test: idempotent — running twice produces same result
ensure_key "$TEST_DIR/kv1.txt" "keyvalue" "new_key" "default_val"
count=$(grep -c "^new_key=" "$TEST_DIR/kv1.txt")
assert_equals "ensure_key is idempotent" "1" "$count"

# ============================================================================
# ensure_key tests (CSV format)
# ============================================================================
echo ""
echo -e "${BLUE}--- ensure_key: CSV format ---${NC}"

cat > "$TEST_DIR/csv1.csv" <<'EOF'
SETTING,VALUE,DETAILS
ExistingSetting,42,some details
EOF
ensure_key "$TEST_DIR/csv1.csv" "csv" "NewSetting" "10" "new setting details"
assert_file_contains "ensure_key csv adds missing key" "$TEST_DIR/csv1.csv" "^NewSetting,10,new setting details$"
assert_file_contains "ensure_key csv preserves existing" "$TEST_DIR/csv1.csv" "^ExistingSetting,42,some details$"

# Test: does NOT overwrite existing CSV key
ensure_key "$TEST_DIR/csv1.csv" "csv" "ExistingSetting" "99" "overwrite attempt"
assert_file_contains "ensure_key csv preserves user value" "$TEST_DIR/csv1.csv" "^ExistingSetting,42,some details$"

# ============================================================================
# rename_key tests (key=value format)
# ============================================================================
echo ""
echo -e "${BLUE}--- rename_key: key=value format ---${NC}"

cat > "$TEST_DIR/kv3.txt" <<'EOF'
old_name=my_value
other_key=other_value
EOF
rename_key "$TEST_DIR/kv3.txt" "keyvalue" "old_name" "new_name"
assert_file_contains "rename_key renames key" "$TEST_DIR/kv3.txt" "^new_name=my_value$"
assert_file_not_contains "rename_key removes old key" "$TEST_DIR/kv3.txt" "^old_name="

# Test: no-op if old key doesn't exist
cat > "$TEST_DIR/kv4.txt" <<'EOF'
some_key=value
EOF
rename_key "$TEST_DIR/kv4.txt" "keyvalue" "nonexistent" "new_name"
assert_file_not_contains "rename_key no-op if old key missing" "$TEST_DIR/kv4.txt" "^new_name="

# Test: no-op if new key already exists
cat > "$TEST_DIR/kv5.txt" <<'EOF'
old_name=old_value
new_name=already_here
EOF
rename_key "$TEST_DIR/kv5.txt" "keyvalue" "old_name" "new_name"
assert_file_contains "rename_key no-op if new key exists" "$TEST_DIR/kv5.txt" "^new_name=already_here$"
assert_file_contains "rename_key keeps old key when new exists" "$TEST_DIR/kv5.txt" "^old_name=old_value$"

# ============================================================================
# rename_key tests (CSV format)
# ============================================================================
echo ""
echo -e "${BLUE}--- rename_key: CSV format ---${NC}"

cat > "$TEST_DIR/csv2.csv" <<'EOF'
SETTING,VALUE,DETAILS
OldSetting,42,some details
OtherSetting,10,other
EOF
rename_key "$TEST_DIR/csv2.csv" "csv" "OldSetting" "NewSetting"
assert_file_contains "rename_key csv renames" "$TEST_DIR/csv2.csv" "^NewSetting,42,some details$"
assert_file_not_contains "rename_key csv removes old" "$TEST_DIR/csv2.csv" "^OldSetting,"

# ============================================================================
# remove_key tests (key=value format)
# ============================================================================
echo ""
echo -e "${BLUE}--- remove_key: key=value format ---${NC}"

cat > "$TEST_DIR/kv6.txt" <<'EOF'
keep_this=yes
remove_this=bye
also_keep=yes
EOF
remove_key "$TEST_DIR/kv6.txt" "keyvalue" "remove_this"
assert_file_not_contains "remove_key removes key" "$TEST_DIR/kv6.txt" "^remove_this="
assert_file_contains "remove_key preserves other keys" "$TEST_DIR/kv6.txt" "^keep_this=yes$"
assert_file_contains "remove_key preserves other keys 2" "$TEST_DIR/kv6.txt" "^also_keep=yes$"

# Test: no-op if key doesn't exist
remove_key "$TEST_DIR/kv6.txt" "keyvalue" "nonexistent"
assert_file_contains "remove_key no-op if missing" "$TEST_DIR/kv6.txt" "^keep_this=yes$"

# ============================================================================
# remove_key tests (CSV format)
# ============================================================================
echo ""
echo -e "${BLUE}--- remove_key: CSV format ---${NC}"

cat > "$TEST_DIR/csv3.csv" <<'EOF'
SETTING,VALUE,DETAILS
KeepMe,1,keep
RemoveMe,2,remove
AlsoKeep,3,keep
EOF
remove_key "$TEST_DIR/csv3.csv" "csv" "RemoveMe"
assert_file_not_contains "remove_key csv removes" "$TEST_DIR/csv3.csv" "^RemoveMe,"
assert_file_contains "remove_key csv preserves header" "$TEST_DIR/csv3.csv" "^SETTING,VALUE,DETAILS$"
assert_file_contains "remove_key csv preserves other" "$TEST_DIR/csv3.csv" "^KeepMe,1,keep$"

# ============================================================================
# backup_config tests
# ============================================================================
echo ""
echo -e "${BLUE}--- backup_config ---${NC}"

echo "original content" > "$TEST_DIR/backup_test.txt"
backup_config "$TEST_DIR/backup_test.txt"
assert_file_contains "backup creates .pre-migration" "$TEST_DIR/backup_test.txt.pre-migration" "^original content$"

# Modify original and backup again — should overwrite
echo "modified content" > "$TEST_DIR/backup_test.txt"
backup_config "$TEST_DIR/backup_test.txt"
assert_file_contains "backup overwrites previous" "$TEST_DIR/backup_test.txt.pre-migration" "^modified content$"

# backup_config on nonexistent file — should not create backup
backup_config "$TEST_DIR/nonexistent.txt"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ ! -f "$TEST_DIR/nonexistent.txt.pre-migration" ]; then
    echo -e "${GREEN}✓${NC} backup_config skips nonexistent file"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} backup_config should skip nonexistent file"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# ============================================================================
# Edge cases
# ============================================================================
echo ""
echo -e "${BLUE}--- Edge cases ---${NC}"

# Key with spaces in value (key=value)
cat > "$TEST_DIR/kv_space.txt" <<'EOF'
name=my mothbox
EOF
ensure_key "$TEST_DIR/kv_space.txt" "keyvalue" "name" "default"
assert_file_contains "preserves value with spaces" "$TEST_DIR/kv_space.txt" "^name=my mothbox$"

# CSV with spaces in value
cat > "$TEST_DIR/csv_space.csv" <<'EOF'
SETTING,VALUE,DETAILS
AfMode, 0, manual mode
EOF
ensure_key "$TEST_DIR/csv_space.csv" "csv" "AfMode" "1" "auto"
assert_file_contains "preserves csv value with spaces" "$TEST_DIR/csv_space.csv" "^AfMode, 0, manual mode$"

# Key with comment line above (key=value)
cat > "$TEST_DIR/kv_comment.txt" <<'EOF'
# This is a comment
real_key=value
EOF
ensure_key "$TEST_DIR/kv_comment.txt" "keyvalue" "real_key" "default"
assert_file_contains "handles comment lines" "$TEST_DIR/kv_comment.txt" "^real_key=value$"
assert_file_contains "preserves comments" "$TEST_DIR/kv_comment.txt" "^# This is a comment$"

# Empty file
touch "$TEST_DIR/empty.txt"
ensure_key "$TEST_DIR/empty.txt" "keyvalue" "first_key" "first_val"
assert_file_contains "adds key to empty file" "$TEST_DIR/empty.txt" "^first_key=first_val$"

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${BLUE}================================================================================${NC}"
echo -e "Total: $TOTAL_TESTS  Passed: ${GREEN}$PASSED_TESTS${NC}  Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "${BLUE}================================================================================${NC}"

if [ "$FAILED_TESTS" -gt 0 ]; then
    exit 1
fi
```

**Step 2: Create `config_migrations.sh` with helper functions**

Create `config_migrations.sh` in the repo root:

```bash
#!/bin/bash
# ==============================================================================
# Mothbox Config Migration System
# ==============================================================================
#
# Sourced by update_mothbox.sh to migrate config files during updates.
# Adds missing keys, renames keys, and removes deprecated keys while
# preserving user-customized values.
#
# All operations are idempotent — safe to run multiple times.
#
# Usage (from update_mothbox.sh):
#   source "$(dirname "$0")/config_migrations.sh"
#   run_config_migrations "$CONFIG_DIR"
#
# ==============================================================================

# Use color codes from parent script if available, otherwise define them
: "${RED:=\033[0;31m}"
: "${GREEN:=\033[0;32m}"
: "${YELLOW:=\033[1;33m}"
: "${BLUE:=\033[0;34m}"
: "${CYAN:=\033[0;36m}"
: "${NC:=\033[0m}"

# --------------------------------------------------------------------------
# backup_config FILE
# Creates a .pre-migration backup of the file (rolling — overwrites previous)
# --------------------------------------------------------------------------
backup_config() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "$file.pre-migration"
    fi
}

# --------------------------------------------------------------------------
# ensure_key FILE FORMAT KEY DEFAULT [DETAILS]
#
# Adds a key with a default value if it doesn't already exist.
# FORMAT: "keyvalue" for key=value files, "csv" for SETTING,VALUE,DETAILS files.
# No-op if the key already exists (preserves user value).
# --------------------------------------------------------------------------
ensure_key() {
    local file="$1"
    local format="$2"
    local key="$3"
    local default="$4"
    local details="${5:-}"

    if [ ! -f "$file" ]; then
        return
    fi

    case "$format" in
        keyvalue)
            # Check if key exists (ignoring comments and whitespace)
            if grep -q "^${key}=" "$file"; then
                return
            fi
            echo "${key}=${default}" >> "$file"
            ;;
        csv)
            # Check if setting exists in first column
            if grep -q "^${key}," "$file"; then
                return
            fi
            # Also check with leading space (some CSV values have spaces)
            if grep -q "^${key} ," "$file"; then
                return
            fi
            echo "${key},${default},${details}" >> "$file"
            ;;
    esac
}

# --------------------------------------------------------------------------
# rename_key FILE FORMAT OLD_KEY NEW_KEY
#
# Renames a key in-place, preserving the user's value.
# No-op if old key doesn't exist or new key already exists.
# --------------------------------------------------------------------------
rename_key() {
    local file="$1"
    local format="$2"
    local old_key="$3"
    local new_key="$4"

    if [ ! -f "$file" ]; then
        return
    fi

    case "$format" in
        keyvalue)
            # Skip if old key doesn't exist
            if ! grep -q "^${old_key}=" "$file"; then
                return
            fi
            # Skip if new key already exists
            if grep -q "^${new_key}=" "$file"; then
                return
            fi
            # Replace key name, keep value
            sed -i "s/^${old_key}=/${new_key}=/" "$file"
            ;;
        csv)
            # Skip if old key doesn't exist
            if ! grep -q "^${old_key}," "$file"; then
                return
            fi
            # Skip if new key already exists
            if grep -q "^${new_key}," "$file"; then
                return
            fi
            # Replace setting name, keep value and details
            sed -i "s/^${old_key},/${new_key},/" "$file"
            ;;
    esac
}

# --------------------------------------------------------------------------
# remove_key FILE FORMAT KEY
#
# Removes a key and its line from the file.
# No-op if key doesn't exist.
# --------------------------------------------------------------------------
remove_key() {
    local file="$1"
    local format="$2"
    local key="$3"

    if [ ! -f "$file" ]; then
        return
    fi

    case "$format" in
        keyvalue)
            sed -i "/^${key}=/d" "$file"
            ;;
        csv)
            sed -i "/^${key},/d" "$file"
            ;;
    esac
}

# --------------------------------------------------------------------------
# Per-file migration functions
# --------------------------------------------------------------------------

migrate_controls_txt() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return
    fi

    # --- Add missing keys (with defaults matching current templates) ---
    ensure_key "$file" "keyvalue" "relay_enabled" "true"
    ensure_key "$file" "keyvalue" "relay_active_low" "true"
    ensure_key "$file" "keyvalue" "flash_duration_ms" "100"
    ensure_key "$file" "keyvalue" "off_pin" "16"
    ensure_key "$file" "keyvalue" "debug_pin" "12"
    ensure_key "$file" "keyvalue" "jpeg_quality" "96"
    ensure_key "$file" "keyvalue" "cache_max_size_mb" "500"
    ensure_key "$file" "keyvalue" "cache_sizes" "64,128,256"
    ensure_key "$file" "keyvalue" "thumbnail_quality" "85"
    ensure_key "$file" "keyvalue" "cache_warm_on_startup" "false"
    ensure_key "$file" "keyvalue" "cache_warm_count" "100"
    ensure_key "$file" "keyvalue" "log_level" "INFO"
    ensure_key "$file" "keyvalue" "log_retention_days" "7"
    ensure_key "$file" "keyvalue" "gps_fix_mode" "0"
    ensure_key "$file" "keyvalue" "gps_satellites_used" "0"
    ensure_key "$file" "keyvalue" "gps_satellites_visible" "0"
    ensure_key "$file" "keyvalue" "gps_altitude" "0"
    ensure_key "$file" "keyvalue" "gps_hdop" "99.99"
    ensure_key "$file" "keyvalue" "gps_pdop" "99.99"
    ensure_key "$file" "keyvalue" "last_known_lat" "n/a"
    ensure_key "$file" "keyvalue" "last_known_lon" "n/a"
    ensure_key "$file" "keyvalue" "last_position_time" "0"

    # --- Rename keys (none currently, placeholder for future) ---
    # rename_key "$file" "keyvalue" "old_name" "new_name"

    # --- Remove deprecated keys (none currently, placeholder for future) ---
    # remove_key "$file" "keyvalue" "deprecated_key"
}

migrate_camera_settings() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return
    fi

    # --- Add missing keys ---
    ensure_key "$file" "csv" "HDR" "1" "0 is off 3 is HDR with 3 photos - 1-2 is also off 3 and up is that many photos to take"
    ensure_key "$file" "csv" "HDR_width" "7000" "duration of exposure to shift on both sides"
    ensure_key "$file" "csv" "AutoCalibration" "1" "0 is off 1 enables autocalibration"
    ensure_key "$file" "csv" "AutoCalibrationPeriod" "600" "Seconds since last autocalibration"
    ensure_key "$file" "csv" "ImageFileType" "0" "0 is jpeg 1 is png 2 is BMP"
    ensure_key "$file" "csv" "VerticalFlip" "1" "0 is no flip 1 is flip vertically"
    ensure_key "$file" "csv" "AfMode" "0" "AfModeManual=0 AfModeAuto=1 AfModeContinuous=2"
    ensure_key "$file" "csv" "AfSpeed" "1" "AfSpeedNormal=0 AfSpeedFast=1"
    ensure_key "$file" "csv" "AfRange" "1" "AfRangeNormal=0 AfRangeMacro=1 AfRangeFull=2"
    ensure_key "$file" "csv" "AwbEnable" "0" ""
}

migrate_schedule_settings() {
    local file="$1"
    if [ ! -f "$file" ]; then
        return
    fi

    # --- Add missing keys ---
    ensure_key "$file" "csv" "onlyflash" "0" "switch to using only the flash by setting to 1"
}

# --------------------------------------------------------------------------
# run_config_migrations CONFIG_DIR
#
# Main entry point. Backs up configs, then runs all per-file migrations.
# Called from update_mothbox.sh after file sync, before service restarts.
# --------------------------------------------------------------------------
run_config_migrations() {
    local config_dir="$1"

    if [ -z "$config_dir" ] || [ ! -d "$config_dir" ]; then
        echo -e "${YELLOW}⚠ Config directory not found, skipping migrations${NC}"
        return
    fi

    local migrated=0

    # Back up configs before any changes
    for config_file in "controls.txt" "camera_settings.csv" "schedule_settings.csv"; do
        if [ -f "$config_dir/$config_file" ]; then
            backup_config "$config_dir/$config_file"
        fi
    done

    # Run per-file migrations
    if [ -f "$config_dir/controls.txt" ]; then
        local before=$(md5sum "$config_dir/controls.txt" | cut -d' ' -f1)
        migrate_controls_txt "$config_dir/controls.txt"
        local after=$(md5sum "$config_dir/controls.txt" | cut -d' ' -f1)
        if [ "$before" != "$after" ]; then
            migrated=$((migrated + 1))
            echo -e "${CYAN}  Updated: controls.txt${NC}"
        fi
    fi

    if [ -f "$config_dir/camera_settings.csv" ]; then
        local before=$(md5sum "$config_dir/camera_settings.csv" | cut -d' ' -f1)
        migrate_camera_settings "$config_dir/camera_settings.csv"
        local after=$(md5sum "$config_dir/camera_settings.csv" | cut -d' ' -f1)
        if [ "$before" != "$after" ]; then
            migrated=$((migrated + 1))
            echo -e "${CYAN}  Updated: camera_settings.csv${NC}"
        fi
    fi

    if [ -f "$config_dir/schedule_settings.csv" ]; then
        local before=$(md5sum "$config_dir/schedule_settings.csv" | cut -d' ' -f1)
        migrate_schedule_settings "$config_dir/schedule_settings.csv"
        local after=$(md5sum "$config_dir/schedule_settings.csv" | cut -d' ' -f1)
        if [ "$before" != "$after" ]; then
            migrated=$((migrated + 1))
            echo -e "${CYAN}  Updated: schedule_settings.csv${NC}"
        fi
    fi

    if [ "$migrated" -gt 0 ]; then
        echo -e "${GREEN}✓ Config migration complete ($migrated file(s) updated)${NC}"
    else
        echo -e "${GREEN}✓ Config files up to date${NC}"
    fi
}
```

**Step 3: Run the tests**

Run: `bash installation-utils/test_config_migrations.sh`
Expected: All tests PASS (30+ tests)

**Step 4: Make test script executable and commit**

```bash
chmod +x config_migrations.sh installation-utils/test_config_migrations.sh
git add config_migrations.sh installation-utils/test_config_migrations.sh
git commit -m "feat: add config migration helpers with test suite (#378)

Adds ensure_key, rename_key, remove_key functions that handle both
key=value and CSV config formats. All operations are idempotent."
```

---

### Task 2: Integrate into `update_mothbox.sh`

**Files:**
- Modify: `update_mothbox.sh:991-1001` (insert migration call after file sync)
- Modify: `update_mothbox.sh:993-999` (add migration to early-exit path too)

**Step 1: Write integration test**

Create `Tests/unit/test_config_migration_integration.py`:

```python
"""Tests for config_migrations.sh integration with update workflow.

Verifies that:
- ensure_key adds missing keys without overwriting existing values
- rename_key preserves user values under new names
- remove_key cleans up deprecated keys
- Migrations are idempotent
- Backup files are created
"""

import os
import subprocess
import tempfile
import textwrap

import pytest


@pytest.fixture
def migration_script():
    """Path to config_migrations.sh."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(repo_root, "config_migrations.sh")
    assert os.path.exists(script), f"config_migrations.sh not found at {script}"
    return script


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory with old-style config files."""
    return tmp_path


def run_migration(migration_script, config_dir):
    """Source config_migrations.sh and call run_config_migrations."""
    cmd = f'source "{migration_script}" && run_config_migrations "{config_dir}"'
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )
    return result


class TestEnsureKeyIntegration:
    """Test that missing keys are added to real config files."""

    def test_adds_missing_keys_to_controls(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\nsoftwareversion=5.0.0\n")

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0

        content = controls.read_text()
        assert "cache_max_size_mb=500" in content
        assert "log_level=INFO" in content
        assert "name=mothbox" in content  # preserved

    def test_preserves_user_customized_values(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("log_level=DEBUG\ncache_max_size_mb=1000\n")

        run_migration(migration_script, config_dir)

        content = controls.read_text()
        assert "log_level=DEBUG" in content  # not overwritten
        assert "cache_max_size_mb=1000" in content  # not overwritten

    def test_adds_missing_csv_keys(self, migration_script, config_dir):
        camera = config_dir / "camera_settings.csv"
        camera.write_text("SETTING,VALUE,DETAILS\nLensPosition,0.5,lens\n")

        run_migration(migration_script, config_dir)

        content = camera.read_text()
        assert "HDR," in content
        assert "LensPosition,0.5,lens" in content  # preserved

    def test_idempotent(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)
        content_first = controls.read_text()

        run_migration(migration_script, config_dir)
        content_second = controls.read_text()

        assert content_first == content_second


class TestBackupIntegration:
    """Test that backup files are created correctly."""

    def test_creates_pre_migration_backup(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)

        backup = config_dir / "controls.txt.pre-migration"
        assert backup.exists()
        assert backup.read_text() == "name=mothbox\n"

    def test_backup_reflects_pre_migration_state(self, migration_script, config_dir):
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        run_migration(migration_script, config_dir)

        # Backup should have original content (no new keys)
        backup = config_dir / "controls.txt.pre-migration"
        assert "cache_max_size_mb" not in backup.read_text()

        # Original should have new keys
        assert "cache_max_size_mb=500" in controls.read_text()


class TestMissingFiles:
    """Test graceful handling of missing config files."""

    def test_handles_missing_config_dir(self, migration_script, tmp_path):
        nonexistent = tmp_path / "nonexistent"
        result = run_migration(migration_script, nonexistent)
        assert result.returncode == 0

    def test_handles_missing_individual_files(self, migration_script, config_dir):
        # Only create controls.txt, not camera_settings.csv
        controls = config_dir / "controls.txt"
        controls.write_text("name=mothbox\n")

        result = run_migration(migration_script, config_dir)
        assert result.returncode == 0
        assert "cache_max_size_mb=500" in controls.read_text()
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest Tests/unit/test_config_migration_integration.py -v`
Expected: Tests should PASS (config_migrations.sh already exists from Task 1)

**Step 3: Add source + call to `update_mothbox.sh`**

Insert after line 991 in `update_mothbox.sh` (after the `fi` closing the file sync block):

```bash
# Run config migrations (add missing keys, rename, remove deprecated)
MIGRATIONS_SCRIPT="$(cd "$(dirname "$0")" && pwd)/config_migrations.sh"
if [ -f "$MIGRATIONS_SCRIPT" ]; then
    source "$MIGRATIONS_SCRIPT"
    echo -e "${BLUE}Running config migrations...${NC}"
    run_config_migrations "$CONFIG_DIR"
    echo ""
fi
```

Also add the same migration call inside the early-exit block (line 994-999) so that file-sync-only updates also get migrations. Insert before the `verify_installation` call:

```bash
if [ "$GIT_HAS_CHANGES" = "false" ] && [ "$FILES_NEED_SYNC" = "true" ] && [ "$FORCE_FRONTEND_REBUILD" = "false" ]; then
    # Run config migrations even on sync-only updates
    MIGRATIONS_SCRIPT="$(cd "$(dirname "$0")" && pwd)/config_migrations.sh"
    if [ -f "$MIGRATIONS_SCRIPT" ]; then
        source "$MIGRATIONS_SCRIPT"
        echo -e "${BLUE}Running config migrations...${NC}"
        run_config_migrations "$CONFIG_DIR"
        echo ""
    fi
    echo -e "${GREEN}✓ File sync complete, no other updates needed${NC}"
    echo ""
    verify_installation
    set_last_update_commit "$COMPARE_COMMIT"
    exit 0
fi
```

**Step 4: Run all tests**

Run: `python3 -m pytest Tests/unit/test_config_migration_integration.py -v`
Expected: All PASS

Run: `bash installation-utils/test_config_migrations.sh`
Expected: All PASS

**Step 5: Commit**

```bash
git add update_mothbox.sh Tests/unit/test_config_migration_integration.py
git commit -m "feat: integrate config migration into update workflow (#378)

Sources config_migrations.sh after file sync and runs migrations
on both normal updates and sync-only updates. Creates .pre-migration
backup before any changes."
```

---

### Task 3: Add migration tests for real-world scenarios

**Files:**
- Modify: `Tests/unit/test_config_migration_integration.py`

**Step 1: Write scenario tests**

Add to `Tests/unit/test_config_migration_integration.py`:

```python
class TestRealWorldScenarios:
    """Test scenarios based on actual deployment issues."""

    def test_old_install_missing_hdr(self, migration_script, config_dir):
        """Issue #378: Old installs missing HDR setting default to wrong value."""
        camera = config_dir / "camera_settings.csv"
        # Simulate old camera_settings.csv without HDR
        camera.write_text(textwrap.dedent("""\
            SETTING,VALUE,DETAILS
            LensPosition,0.5,lens position
            ExposureValue,0.6,exposure
            ExposureTime,499,microseconds
            AnalogueGain,8.0,gain
        """))

        run_migration(migration_script, config_dir)

        content = camera.read_text()
        # HDR should be added with default=1 (off), not 3
        assert "HDR,1," in content

    def test_old_install_missing_cache_settings(self, migration_script, config_dir):
        """Old installs before gallery cache feature."""
        controls = config_dir / "controls.txt"
        controls.write_text(textwrap.dedent("""\
            shutdown_enabled=False
            name=mothbox
            softwareversion=5.0.0
            Relay_Ch1=5
            Relay_Ch2=19
            Relay_Ch3=9
        """))

        run_migration(migration_script, config_dir)

        content = controls.read_text()
        assert "cache_max_size_mb=500" in content
        assert "cache_sizes=64,128,256" in content
        assert "thumbnail_quality=85" in content
        # User values preserved
        assert "Relay_Ch1=5" in content
        assert "name=mothbox" in content

    def test_full_current_config_unchanged(self, migration_script, config_dir):
        """Running migration on a fully up-to-date config changes nothing."""
        controls = config_dir / "controls.txt"
        # Write complete current controls.txt
        controls.write_text(textwrap.dedent("""\
            shutdown_enabled=False
            OnlyFlash=False
            LastCalibration=0
            nextWake=0
            name=mothbox
            softwareversion=5.0.0
            gpstime=0
            UTCoff=-5
            lat=n/a
            lon=n/a
            gps_fix_mode=0
            gps_satellites_used=0
            gps_satellites_visible=0
            gps_altitude=0
            gps_hdop=99.99
            gps_pdop=99.99
            last_known_lat=n/a
            last_known_lon=n/a
            last_position_time=0
            weekdays=1;2;3;4;5;6;7
            hours=19;21;23;2;4
            minutes=0
            runtime=59
            Relay_Ch1=5
            Relay_Ch2=19
            Relay_Ch3=9
            relay_enabled=true
            relay_active_low=true
            flash_duration_ms=100
            off_pin=16
            debug_pin=12
            jpeg_quality=96
            cache_max_size_mb=500
            cache_sizes=64,128,256
            thumbnail_quality=85
            cache_warm_on_startup=false
            cache_warm_count=100
            log_level=INFO
            log_retention_days=7
        """))

        content_before = controls.read_text()
        run_migration(migration_script, config_dir)
        content_after = controls.read_text()

        assert content_before == content_after
```

**Step 2: Run tests**

Run: `python3 -m pytest Tests/unit/test_config_migration_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add Tests/unit/test_config_migration_integration.py
git commit -m "test: add real-world scenario tests for config migration (#378)"
```

---

### Task 4: Update issue #378 warning message

**Files:**
- Modify: `update_mothbox.sh:1223-1231`

The existing "config changed" warning (lines 1223-1231) says "Your existing configuration has been preserved" and tells users to manually review. Now that migrations handle this automatically, update the message.

**Step 1: Update the warning message**

Replace lines 1223-1231 in `update_mothbox.sh`:

```bash
# Inform about config changes (migrations handle adding new keys automatically)
if [ "$CONFIG_CHANGED" -gt 0 ]; then
    echo -e "${CYAN}Configuration files updated in this release:${NC}"
    git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '\.csv$|\.txt$' | grep -v 'webui/frontend' | grep -v '.template$' | sed 's/^/  • /'
    echo ""
    echo -e "${GREEN}✓ New settings were automatically added with safe defaults${NC}"
    echo "Your existing customized values have been preserved."
    echo ""
fi
```

**Step 2: Commit**

```bash
git add update_mothbox.sh
git commit -m "fix: update config change message to reflect automatic migration (#378)"
```

---

### Task 5: Final verification and cleanup

**Step 1: Run full test suite**

```bash
bash installation-utils/test_config_migrations.sh
python3 -m pytest Tests/unit/test_config_migration_integration.py -v
```

Expected: All PASS

**Step 2: Run linter**

```bash
ruff check config_migrations.sh 2>/dev/null || true  # bash file, ruff won't check it
ruff check Tests/unit/test_config_migration_integration.py
```

**Step 3: Run security scan on test file**

```bash
bandit -c pyproject.toml Tests/unit/test_config_migration_integration.py
```

**Step 4: Verify shellcheck (if available)**

```bash
shellcheck config_migrations.sh 2>/dev/null || echo "shellcheck not installed, skip"
shellcheck installation-utils/test_config_migrations.sh 2>/dev/null || echo "shellcheck not installed, skip"
```

**Step 5: Verify the complete acceptance criteria from issue #378**

- [ ] `update_mothbox.sh` runs migrations after file sync
- [ ] Missing settings are added with defaults
- [ ] Existing user values are preserved
- [ ] Migrations are idempotent (run twice, same result)
- [ ] `.pre-migration` backup created
- [ ] New installations unaffected (install_mothbox.sh unchanged)
