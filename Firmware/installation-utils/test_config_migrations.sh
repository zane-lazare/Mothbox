#!/bin/bash
# ==============================================================================
# Mothbox Config Migration Test Suite
# ==============================================================================
#
# Tests the config migration helper functions in config_migrations.sh:
#   ensure_key, rename_key, remove_key, backup_config
#
# Covers key=value (controls.txt) and CSV (camera_settings.csv) formats,
# plus edge cases like spaces in values, comment preservation, empty files.
#
# Usage:
#   ./test_config_migrations.sh
#
# ==============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_SCRIPT="$SCRIPT_DIR/../config_migrations.sh"

if [ ! -f "$MIGRATIONS_SCRIPT" ]; then
    echo -e "${RED}Error: config_migrations.sh not found at $MIGRATIONS_SCRIPT${NC}"
    exit 1
fi

# Source the migration functions
source "$MIGRATIONS_SCRIPT"

# Create temp directory with cleanup trap
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Config Migration Test Suite${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ==============================================================================
# Test Helpers
# ==============================================================================

assert_equals() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}PASS${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        echo "       expected: '$expected'"
        echo "       actual:   '$actual'"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_contains() {
    local test_name="$1"
    local file="$2"
    local pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if grep -qF "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        echo "       pattern not found: '$pattern'"
        echo "       file contents:"
        sed 's/^/         /' "$file" 2>/dev/null || echo "         (file missing)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_not_contains() {
    local test_name="$1"
    local file="$2"
    local pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if ! grep -qF "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        echo "       pattern should NOT be present: '$pattern'"
        echo "       file contents:"
        sed 's/^/         /' "$file"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_exists() {
    local test_name="$1"
    local file="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ -f "$file" ]; then
        echo -e "${GREEN}PASS${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        echo "       file does not exist: '$file'"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

assert_file_not_exists() {
    local test_name="$1"
    local file="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ ! -f "$file" ]; then
        echo -e "${GREEN}PASS${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        echo "       file should not exist: '$file'"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# ==============================================================================
# ensure_key — key=value format
# ==============================================================================
echo -e "${BLUE}Testing ensure_key (key=value format)${NC}"
echo ""

# Adds missing key
KV_FILE="$TEST_DIR/ensure_kv_add.txt"
printf 'name=mothbox\nversion=5.0\n' > "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "relay_enabled" "true"
assert_file_contains "ensure_key kv: adds missing key" "$KV_FILE" "relay_enabled=true"
assert_file_contains "ensure_key kv: preserves existing content" "$KV_FILE" "name=mothbox"

# Preserves existing key (does NOT overwrite)
KV_FILE="$TEST_DIR/ensure_kv_preserve.txt"
printf 'relay_enabled=false\n' > "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "relay_enabled" "true"
assert_file_contains "ensure_key kv: preserves existing value" "$KV_FILE" "relay_enabled=false"
assert_file_not_contains "ensure_key kv: does not add duplicate" "$KV_FILE" "relay_enabled=true"

# Idempotent — calling twice doesn't add duplicate
KV_FILE="$TEST_DIR/ensure_kv_idempotent.txt"
printf '' > "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "debug_pin" "12"
ensure_key "$KV_FILE" keyvalue "debug_pin" "12"
count=$(grep -c "^debug_pin=" "$KV_FILE")
assert_equals "ensure_key kv: idempotent (no duplicate)" "1" "$count"

echo ""

# ==============================================================================
# ensure_key — CSV format
# ==============================================================================
echo -e "${BLUE}Testing ensure_key (CSV format)${NC}"
echo ""

# Adds missing key
CSV_FILE="$TEST_DIR/ensure_csv_add.csv"
printf 'SETTING,VALUE,DETAILS\nHDR,1,0 is off\n' > "$CSV_FILE"
ensure_key "$CSV_FILE" csv "AfMode" "0" "manual focus"
assert_file_contains "ensure_key csv: adds missing key" "$CSV_FILE" "AfMode,0,manual focus"
assert_file_contains "ensure_key csv: preserves header" "$CSV_FILE" "SETTING,VALUE,DETAILS"
assert_file_contains "ensure_key csv: preserves existing rows" "$CSV_FILE" "HDR,1,0 is off"

# Preserves existing key
CSV_FILE="$TEST_DIR/ensure_csv_preserve.csv"
printf 'SETTING,VALUE,DETAILS\nAfMode,2,continuous\n' > "$CSV_FILE"
ensure_key "$CSV_FILE" csv "AfMode" "0" "manual focus"
assert_file_contains "ensure_key csv: preserves existing CSV value" "$CSV_FILE" "AfMode,2,continuous"
assert_file_not_contains "ensure_key csv: does not add duplicate CSV" "$CSV_FILE" "AfMode,0,manual focus"

# Idempotent
CSV_FILE="$TEST_DIR/ensure_csv_idempotent.csv"
printf 'SETTING,VALUE,DETAILS\n' > "$CSV_FILE"
ensure_key "$CSV_FILE" csv "AwbEnable" "0" ""
ensure_key "$CSV_FILE" csv "AwbEnable" "0" ""
count=$(grep -c "^AwbEnable," "$CSV_FILE")
assert_equals "ensure_key csv: idempotent (no duplicate)" "1" "$count"

echo ""

# ==============================================================================
# rename_key — key=value format
# ==============================================================================
echo -e "${BLUE}Testing rename_key (key=value format)${NC}"
echo ""

# Renames key, preserving value
KV_FILE="$TEST_DIR/rename_kv_basic.txt"
printf 'old_key=myvalue\nother=keep\n' > "$KV_FILE"
rename_key "$KV_FILE" keyvalue "old_key" "new_key"
assert_file_contains "rename_key kv: new key present with value" "$KV_FILE" "new_key=myvalue"
assert_file_not_contains "rename_key kv: old key removed" "$KV_FILE" "old_key="
assert_file_contains "rename_key kv: other keys preserved" "$KV_FILE" "other=keep"

# No-op if old key missing
KV_FILE="$TEST_DIR/rename_kv_missing.txt"
printf 'something=1\n' > "$KV_FILE"
rename_key "$KV_FILE" keyvalue "nonexistent" "new_key"
assert_file_not_contains "rename_key kv: no-op if old key missing" "$KV_FILE" "new_key="
assert_file_contains "rename_key kv: existing content unchanged" "$KV_FILE" "something=1"

# No-op if new key already exists
KV_FILE="$TEST_DIR/rename_kv_exists.txt"
printf 'old_key=oldval\nnew_key=newval\n' > "$KV_FILE"
rename_key "$KV_FILE" keyvalue "old_key" "new_key"
assert_file_contains "rename_key kv: keeps existing new key" "$KV_FILE" "new_key=newval"
assert_file_contains "rename_key kv: old key still there (no-op)" "$KV_FILE" "old_key=oldval"

echo ""

# ==============================================================================
# rename_key — CSV format
# ==============================================================================
echo -e "${BLUE}Testing rename_key (CSV format)${NC}"
echo ""

# Renames key, preserving value and details
CSV_FILE="$TEST_DIR/rename_csv_basic.csv"
printf 'SETTING,VALUE,DETAILS\nOldSetting,42,some details\nKeep,1,keep me\n' > "$CSV_FILE"
rename_key "$CSV_FILE" csv "OldSetting" "NewSetting"
assert_file_contains "rename_key csv: new key present" "$CSV_FILE" "NewSetting,42,some details"
assert_file_not_contains "rename_key csv: old key removed" "$CSV_FILE" "OldSetting,"
assert_file_contains "rename_key csv: other rows preserved" "$CSV_FILE" "Keep,1,keep me"

# No-op if old key missing
CSV_FILE="$TEST_DIR/rename_csv_missing.csv"
printf 'SETTING,VALUE,DETAILS\nHDR,1,desc\n' > "$CSV_FILE"
rename_key "$CSV_FILE" csv "Missing" "NewName"
assert_file_not_contains "rename_key csv: no-op if old key missing" "$CSV_FILE" "NewName,"
assert_file_contains "rename_key csv: existing rows unchanged" "$CSV_FILE" "HDR,1,desc"

# No-op if new key already exists
CSV_FILE="$TEST_DIR/rename_csv_exists.csv"
printf 'SETTING,VALUE,DETAILS\nOldKey,1,old\nNewKey,2,new\n' > "$CSV_FILE"
rename_key "$CSV_FILE" csv "OldKey" "NewKey"
assert_file_contains "rename_key csv: keeps existing new key" "$CSV_FILE" "NewKey,2,new"
assert_file_contains "rename_key csv: old key still there (no-op)" "$CSV_FILE" "OldKey,1,old"

echo ""

# ==============================================================================
# remove_key — key=value format
# ==============================================================================
echo -e "${BLUE}Testing remove_key (key=value format)${NC}"
echo ""

# Removes key
KV_FILE="$TEST_DIR/remove_kv_basic.txt"
printf 'keep=yes\nremove_me=gone\nother=also_keep\n' > "$KV_FILE"
remove_key "$KV_FILE" keyvalue "remove_me"
assert_file_not_contains "remove_key kv: key removed" "$KV_FILE" "remove_me="
assert_file_contains "remove_key kv: first key preserved" "$KV_FILE" "keep=yes"
assert_file_contains "remove_key kv: last key preserved" "$KV_FILE" "other=also_keep"

# No-op if key missing
KV_FILE="$TEST_DIR/remove_kv_missing.txt"
printf 'keep=yes\n' > "$KV_FILE"
remove_key "$KV_FILE" keyvalue "nonexistent"
assert_file_contains "remove_key kv: no-op if missing" "$KV_FILE" "keep=yes"

echo ""

# ==============================================================================
# remove_key — CSV format
# ==============================================================================
echo -e "${BLUE}Testing remove_key (CSV format)${NC}"
echo ""

# Removes row
CSV_FILE="$TEST_DIR/remove_csv_basic.csv"
printf 'SETTING,VALUE,DETAILS\nKeep,1,stay\nRemoveMe,99,bye\nAlsoKeep,2,stay too\n' > "$CSV_FILE"
remove_key "$CSV_FILE" csv "RemoveMe"
assert_file_not_contains "remove_key csv: row removed" "$CSV_FILE" "RemoveMe,"
assert_file_contains "remove_key csv: header preserved" "$CSV_FILE" "SETTING,VALUE,DETAILS"
assert_file_contains "remove_key csv: first row preserved" "$CSV_FILE" "Keep,1,stay"
assert_file_contains "remove_key csv: last row preserved" "$CSV_FILE" "AlsoKeep,2,stay too"

# No-op if key missing
CSV_FILE="$TEST_DIR/remove_csv_missing.csv"
printf 'SETTING,VALUE,DETAILS\nHDR,1,desc\n' > "$CSV_FILE"
remove_key "$CSV_FILE" csv "Missing"
assert_file_contains "remove_key csv: no-op if missing" "$CSV_FILE" "HDR,1,desc"

echo ""

# ==============================================================================
# backup_config
# ==============================================================================
echo -e "${BLUE}Testing backup_config${NC}"
echo ""

# Creates .pre-migration file
BACKUP_FILE="$TEST_DIR/backup_test.txt"
printf 'original=content\n' > "$BACKUP_FILE"
backup_config "$BACKUP_FILE"
assert_file_exists "backup_config: creates .pre-migration file" "$BACKUP_FILE.pre-migration"
assert_file_contains "backup_config: backup has original content" "$BACKUP_FILE.pre-migration" "original=content"

# Overwrites previous backup
printf 'updated=content\n' > "$BACKUP_FILE"
backup_config "$BACKUP_FILE"
assert_file_contains "backup_config: overwrites previous backup" "$BACKUP_FILE.pre-migration" "updated=content"
assert_file_not_contains "backup_config: old content gone from backup" "$BACKUP_FILE.pre-migration" "original=content"

# Skips nonexistent file
backup_config "$TEST_DIR/does_not_exist.txt"
assert_file_not_exists "backup_config: skips nonexistent file" "$TEST_DIR/does_not_exist.txt.pre-migration"

echo ""

# ==============================================================================
# Edge Cases
# ==============================================================================
echo -e "${BLUE}Testing Edge Cases${NC}"
echo ""

# Values with spaces (key=value)
KV_FILE="$TEST_DIR/edge_spaces_kv.txt"
printf '' > "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "name" "my mothbox device"
assert_file_contains "edge: kv value with spaces" "$KV_FILE" "name=my mothbox device"

# Values with spaces (CSV)
CSV_FILE="$TEST_DIR/edge_spaces_csv.csv"
printf 'SETTING,VALUE,DETAILS\n' > "$CSV_FILE"
ensure_key "$CSV_FILE" csv "Name" "mb01" "NOTE=we actually just use serial number"
assert_file_contains "edge: csv details with spaces" "$CSV_FILE" "Name,mb01,NOTE=we actually just use serial number"

# Comment lines preserved in key=value files
KV_FILE="$TEST_DIR/edge_comments.txt"
printf '# This is a comment\nkey1=val1\n# Another comment\nkey2=val2\n' > "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "key3" "val3"
assert_file_contains "edge: comment line preserved (first)" "$KV_FILE" "# This is a comment"
assert_file_contains "edge: comment line preserved (second)" "$KV_FILE" "# Another comment"
assert_file_contains "edge: new key added after comments" "$KV_FILE" "key3=val3"

# Remove key preserves comments
remove_key "$KV_FILE" keyvalue "key1"
assert_file_contains "edge: remove preserves comments" "$KV_FILE" "# This is a comment"
assert_file_not_contains "edge: remove actually removed key" "$KV_FILE" "key1=val1"

# Empty file — ensure_key should still work
KV_FILE="$TEST_DIR/edge_empty.txt"
touch "$KV_FILE"
ensure_key "$KV_FILE" keyvalue "new_key" "new_val"
assert_file_contains "edge: ensure_key works on empty file" "$KV_FILE" "new_key=new_val"

# Rename key with value containing spaces
KV_FILE="$TEST_DIR/edge_rename_spaces.txt"
printf 'old_name=hello world foo\n' > "$KV_FILE"
rename_key "$KV_FILE" keyvalue "old_name" "new_name"
assert_file_contains "edge: rename preserves value with spaces" "$KV_FILE" "new_name=hello world foo"

echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

echo "Total tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"

if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
    echo ""
    echo -e "${RED}Some tests failed! Please review the migration functions.${NC}"
    exit 1
else
    echo -e "${GREEN}Failed:       $FAILED_TESTS${NC}"
    echo ""
    echo -e "${GREEN}================================================================================${NC}"
    echo -e "${GREEN}All config migration tests passed!${NC}"
    echo -e "${GREEN}================================================================================${NC}"
    echo ""
fi
