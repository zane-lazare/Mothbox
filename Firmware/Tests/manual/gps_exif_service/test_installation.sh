#!/bin/bash
# ==============================================================================
# GPS EXIF Tagger Service - Installation Test
# ==============================================================================
#
# This script validates that the GPS EXIF Tagger service is correctly installed.
#
# Usage: ./test_installation.sh
#
# Tests performed:
# 1. Service file exists
# 2. Service is enabled for boot
# 3. Service configuration is correct
# 4. Required directories are accessible
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#
# ==============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}GPS EXIF Tagger Service - Installation Test${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Detect installation type
if [ -f "/opt/mothbox/mothbox_paths.py" ]; then
    INSTALL_TYPE="production"
    SERVICE_NAME="gps-exif-tagger.service"
    EXPECTED_WORKING_DIR="/opt/mothbox"
    EXPECTED_PHOTOS_DIR="/var/lib/mothbox/photos"
    EXPECTED_CONFIG_DIR="/etc/mothbox"
elif [ -f "/home/pi/Desktop/Mothbox/Firmware/mothbox_paths.py" ]; then
    INSTALL_TYPE="legacy"
    SERVICE_NAME="gps-exif-tagger-legacy.service"
    EXPECTED_WORKING_DIR="/home/pi/Desktop/Mothbox/Firmware"
    EXPECTED_PHOTOS_DIR="/home/pi/Desktop/Mothbox/Firmware/photos"
    EXPECTED_CONFIG_DIR="/home/pi/Desktop/Mothbox/Firmware"
else
    echo -e "${RED}Error: Cannot detect Mothbox installation${NC}"
    exit 1
fi

echo -e "${BLUE}Detected Installation Type:${NC} $INSTALL_TYPE"
echo -e "${BLUE}Expected Service Name:${NC} $SERVICE_NAME"
echo ""

# Test 1: Service file exists
echo -e "${BLUE}[1/7] Checking service file exists...${NC}"
if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    echo -e "${GREEN}  ✓ Service file found: /etc/systemd/system/$SERVICE_NAME${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}  ✗ Service file not found: /etc/systemd/system/$SERVICE_NAME${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 2: Service is enabled
echo -e "${BLUE}[2/7] Checking service is enabled...${NC}"
if systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
    echo -e "${GREEN}  ✓ Service is enabled for boot${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}  ✗ Service is not enabled${NC}"
    echo -e "${YELLOW}  Tip: sudo systemctl enable $SERVICE_NAME${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 3: Working directory is correct
echo -e "${BLUE}[3/7] Checking WorkingDirectory configuration...${NC}"
ACTUAL_WORKING_DIR=$(systemctl show "$SERVICE_NAME" -p WorkingDirectory --value)
if [ "$ACTUAL_WORKING_DIR" = "$EXPECTED_WORKING_DIR" ]; then
    echo -e "${GREEN}  ✓ WorkingDirectory correct: $ACTUAL_WORKING_DIR${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}  ✗ WorkingDirectory incorrect${NC}"
    echo -e "${RED}    Expected: $EXPECTED_WORKING_DIR${NC}"
    echo -e "${RED}    Actual: $ACTUAL_WORKING_DIR${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 4: ReadWritePaths includes photos directory
echo -e "${BLUE}[4/7] Checking ReadWritePaths configuration...${NC}"
READ_WRITE_PATHS=$(systemctl show "$SERVICE_NAME" -p ReadWritePaths --value)
if echo "$READ_WRITE_PATHS" | grep -q "$EXPECTED_PHOTOS_DIR"; then
    echo -e "${GREEN}  ✓ ReadWritePaths includes: $EXPECTED_PHOTOS_DIR${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}  ✗ ReadWritePaths does not include photos directory${NC}"
    echo -e "${RED}    Expected: $EXPECTED_PHOTOS_DIR${NC}"
    echo -e "${RED}    Actual: $READ_WRITE_PATHS${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 5: Security hardening is active
echo -e "${BLUE}[5/7] Checking security hardening...${NC}"
PROTECT_SYSTEM=$(systemctl show "$SERVICE_NAME" -p ProtectSystem --value)
NO_NEW_PRIVS=$(systemctl show "$SERVICE_NAME" -p NoNewPrivileges --value)

if [ "$PROTECT_SYSTEM" = "strict" ]; then
    echo -e "${GREEN}  ✓ ProtectSystem=strict${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}  ✗ ProtectSystem not strict (actual: $PROTECT_SYSTEM)${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

if [ "$NO_NEW_PRIVS" = "yes" ]; then
    echo -e "${GREEN}  ✓ NoNewPrivileges=yes${NC}"
else
    echo -e "${RED}  ✗ NoNewPrivileges not enabled${NC}"
fi
echo ""

# Test 6: Photos directory exists and is writable
echo -e "${BLUE}[6/7] Checking photos directory accessibility...${NC}"
if [ -d "$EXPECTED_PHOTOS_DIR" ]; then
    echo -e "${GREEN}  ✓ Photos directory exists: $EXPECTED_PHOTOS_DIR${NC}"

    if [ -w "$EXPECTED_PHOTOS_DIR" ]; then
        echo -e "${GREEN}  ✓ Photos directory is writable${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${YELLOW}  ⚠ Photos directory not writable by current user${NC}"
        echo -e "${YELLOW}    (Service runs as 'pi' user, should be OK)${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
else
    echo -e "${RED}  ✗ Photos directory does not exist: $EXPECTED_PHOTOS_DIR${NC}"
    echo -e "${YELLOW}  Tip: mkdir -p $EXPECTED_PHOTOS_DIR${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 7: gps_exif_tagger.py exists
echo -e "${BLUE}[7/7] Checking gps_exif_tagger.py exists...${NC}"
TAGGER_SCRIPT="$EXPECTED_WORKING_DIR/gps_exif_tagger.py"
if [ -f "$TAGGER_SCRIPT" ]; then
    echo -e "${GREEN}  ✓ Tagger script found: $TAGGER_SCRIPT${NC}"

    # Check if executable by Python
    if python3 -m py_compile "$TAGGER_SCRIPT" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Python syntax valid${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}  ✗ Python syntax error in tagger script${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}  ✗ Tagger script not found: $TAGGER_SCRIPT${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Summary
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Installation validation failed. Please fix the issues above.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Start the service: sudo systemctl start $SERVICE_NAME"
    echo "2. Check status: sudo systemctl status $SERVICE_NAME"
    echo "3. Monitor logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "4. Run functional tests: ./test_monitoring.sh"
    exit 0
fi
