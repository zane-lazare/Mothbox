#!/bin/bash
# ==============================================================================
# Mothbox Config Migration Helpers
# ==============================================================================
#
# Provides idempotent functions for migrating config files during updates:
#   backup_config  — create a .pre-migration backup
#   ensure_key     — add a key if missing (preserves existing values)
#   rename_key     — rename a key (preserves value)
#   remove_key     — remove a key
#
# Supports two formats:
#   keyvalue — key=value lines (controls.txt)
#   csv      — SETTING,VALUE,DETAILS rows (camera_settings.csv, schedule_settings.csv)
#
# Usage:
#   source config_migrations.sh
#   run_config_migrations /etc/mothbox
#
# ==============================================================================

# Color code fallbacks (use parent's if already set)
: "${RED:=\033[0;31m}"
: "${GREEN:=\033[0;32m}"
: "${YELLOW:=\033[1;33m}"
: "${BLUE:=\033[0;34m}"
: "${NC:=\033[0m}"

# ==============================================================================
# Core Helper Functions
# ==============================================================================
# NOTE: Key names are used directly in grep/sed regex patterns.
# They must be plain identifiers: [a-zA-Z_][a-zA-Z0-9_]*
# Regex metacharacters (. * [ etc.) in key names are NOT escaped.

# backup_config FILE
#   Create a .pre-migration backup of FILE. Skips if FILE does not exist.
backup_config() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "$file.pre-migration"
    fi
}

# ensure_key FILE FORMAT KEY DEFAULT [DETAILS]
#   Add KEY with DEFAULT value if it does not already exist in FILE.
#   FORMAT: "keyvalue" for key=value, "csv" for SETTING,VALUE,DETAILS
#   No-op if key already present (preserves user's value).
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
            if ! grep -q "^${key}=" "$file" 2>/dev/null; then
                echo "${key}=${default}" >> "$file"
            fi
            ;;
        csv)
            if ! grep -q "^${key}," "$file" 2>/dev/null; then
                echo "${key},${default},${details}" >> "$file"
            fi
            ;;
    esac
}

# rename_key FILE FORMAT OLD_KEY NEW_KEY
#   Rename OLD_KEY to NEW_KEY, preserving the value.
#   No-op if OLD_KEY is missing or NEW_KEY already exists.
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
            # Only rename if old exists AND new does not
            if grep -q "^${old_key}=" "$file" 2>/dev/null && \
               ! grep -q "^${new_key}=" "$file" 2>/dev/null; then
                sed -i "s/^${old_key}=/${new_key}=/" "$file"
            fi
            ;;
        csv)
            if grep -q "^${old_key}," "$file" 2>/dev/null && \
               ! grep -q "^${new_key}," "$file" 2>/dev/null; then
                sed -i "s/^${old_key},/${new_key},/" "$file"
            fi
            ;;
    esac
}

# remove_key FILE FORMAT KEY
#   Remove all lines starting with KEY= (keyvalue) or KEY, (csv).
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

# ==============================================================================
# Per-File Migration Functions
# ==============================================================================

# migrate_controls_txt FILE
#   Ensure all expected keys exist in controls.txt (key=value format).
migrate_controls_txt() {
    local file="$1"

    # Relay configuration
    ensure_key "$file" keyvalue "relay_enabled" "true"
    ensure_key "$file" keyvalue "relay_active_low" "true"
    ensure_key "$file" keyvalue "flash_duration_ms" "100"
    ensure_key "$file" keyvalue "off_pin" "16"
    ensure_key "$file" keyvalue "debug_pin" "12"

    # Image quality
    ensure_key "$file" keyvalue "jpeg_quality" "96"

    # Gallery thumbnail cache
    ensure_key "$file" keyvalue "cache_max_size_mb" "500"
    ensure_key "$file" keyvalue "cache_sizes" "64,128,256"
    ensure_key "$file" keyvalue "thumbnail_quality" "85"
    ensure_key "$file" keyvalue "cache_warm_on_startup" "false"
    ensure_key "$file" keyvalue "cache_warm_count" "100"

    # Logging
    ensure_key "$file" keyvalue "log_level" "INFO"
    ensure_key "$file" keyvalue "log_retention_days" "7"

    # GPS
    ensure_key "$file" keyvalue "gps_fix_mode" "0"
    ensure_key "$file" keyvalue "gps_satellites_used" "0"
    ensure_key "$file" keyvalue "gps_satellites_visible" "0"
    ensure_key "$file" keyvalue "gps_altitude" "0"
    ensure_key "$file" keyvalue "gps_hdop" "99.99"
    ensure_key "$file" keyvalue "gps_pdop" "99.99"
    ensure_key "$file" keyvalue "last_known_lat" "n/a"
    ensure_key "$file" keyvalue "last_known_lon" "n/a"
    ensure_key "$file" keyvalue "last_position_time" "0"
}

# migrate_camera_settings FILE
#   Ensure all expected keys exist in camera_settings.csv (CSV format).
migrate_camera_settings() {
    local file="$1"

    ensure_key "$file" csv "HDR" "1" "0 is off 3 is HDR with 3 photos"
    ensure_key "$file" csv "HDR_width" "7000" "duration of exposure to shift"
    ensure_key "$file" csv "AutoCalibration" "1" "0 is off 1 enables autocalibration"
    ensure_key "$file" csv "AutoCalibrationPeriod" "600" "Seconds since last autocalibration"
    ensure_key "$file" csv "ImageFileType" "0" "0 is jpeg 1 is png 2 is BMP"
    ensure_key "$file" csv "VerticalFlip" "1" "0 is no flip 1 is flip"
    ensure_key "$file" csv "AfMode" "0" "AfModeManual=0 AfModeAuto=1 AfModeContinuous=2"
    ensure_key "$file" csv "AfSpeed" "1" "AfSpeedNormal=0 AfSpeedFast=1"
    ensure_key "$file" csv "AfRange" "1" "AfRangeNormal=0 AfRangeMacro=1 AfRangeFull=2"
    ensure_key "$file" csv "AwbEnable" "0" ""
}

# migrate_schedule_settings FILE
#   Ensure all expected keys exist in schedule_settings.csv (CSV format).
migrate_schedule_settings() {
    local file="$1"

    ensure_key "$file" csv "onlyflash" "0" "switch to using only the flash for attraction by setting to 1"
}

# ==============================================================================
# Main Entry Point
# ==============================================================================

# run_config_migrations CONFIG_DIR
#   Backup all config files, run per-file migrations, report changes.
run_config_migrations() {
    local config_dir="$1"

    if [ -z "$config_dir" ] || [ ! -d "$config_dir" ]; then
        echo -e "${YELLOW}⚠ Config directory not found, skipping migrations${NC}"
        return
    fi

    local controls="$config_dir/controls.txt"
    local camera="$config_dir/camera_settings.csv"
    local schedule="$config_dir/schedule_settings.csv"

    echo -e "${BLUE}Running config migrations...${NC}"

    # Compute checksums before migration (empty string if file missing)
    local md5_controls="" md5_camera="" md5_schedule=""
    [ -f "$controls" ] && md5_controls=$(md5sum "$controls" | cut -d' ' -f1)
    [ -f "$camera" ] && md5_camera=$(md5sum "$camera" | cut -d' ' -f1)
    [ -f "$schedule" ] && md5_schedule=$(md5sum "$schedule" | cut -d' ' -f1)

    # Backup all config files
    backup_config "$controls"
    backup_config "$camera"
    backup_config "$schedule"

    # Run per-file migrations
    [ -f "$controls" ] && migrate_controls_txt "$controls"
    [ -f "$camera" ] && migrate_camera_settings "$camera"
    [ -f "$schedule" ] && migrate_schedule_settings "$schedule"

    # Detect and report changes
    local changed=0

    if [ -f "$controls" ]; then
        local new_md5=$(md5sum "$controls" | cut -d' ' -f1)
        if [ "$md5_controls" != "$new_md5" ]; then
            echo -e "  ${GREEN}Updated${NC} controls.txt (added missing keys)"
            changed=1
        else
            echo -e "  ${YELLOW}No changes${NC} controls.txt (already up to date)"
        fi
    else
        echo -e "  ${YELLOW}Skipped${NC} controls.txt (not found)"
    fi

    if [ -f "$camera" ]; then
        local new_md5=$(md5sum "$camera" | cut -d' ' -f1)
        if [ "$md5_camera" != "$new_md5" ]; then
            echo -e "  ${GREEN}Updated${NC} camera_settings.csv (added missing keys)"
            changed=1
        else
            echo -e "  ${YELLOW}No changes${NC} camera_settings.csv (already up to date)"
        fi
    else
        echo -e "  ${YELLOW}Skipped${NC} camera_settings.csv (not found)"
    fi

    if [ -f "$schedule" ]; then
        local new_md5=$(md5sum "$schedule" | cut -d' ' -f1)
        if [ "$md5_schedule" != "$new_md5" ]; then
            echo -e "  ${GREEN}Updated${NC} schedule_settings.csv (added missing keys)"
            changed=1
        else
            echo -e "  ${YELLOW}No changes${NC} schedule_settings.csv (already up to date)"
        fi
    else
        echo -e "  ${YELLOW}Skipped${NC} schedule_settings.csv (not found)"
    fi

    if [ "$changed" -eq 1 ]; then
        echo -e "${GREEN}Config migrations complete. Backups saved as *.pre-migration${NC}"
    else
        echo -e "${GREEN}Config migrations complete. All files already up to date.${NC}"
    fi
}
