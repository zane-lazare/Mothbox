#!/bin/bash
# ==============================================================================
# GPS EXIF Tagger Service - Monitoring Test
# ==============================================================================
#
# This script monitors the GPS EXIF Tagger service and displays real-time logs.
#
# Usage: ./test_monitoring.sh
#
# Features:
# - Shows current service status
# - Displays recent logs
# - Follows logs in real-time
# - Highlights important events
#
# Press Ctrl+C to stop monitoring
#
# ==============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect service name
if systemctl list-unit-files | grep -q "gps-exif-tagger.service"; then
    SERVICE_NAME="gps-exif-tagger.service"
elif systemctl list-unit-files | grep -q "gps-exif-tagger-legacy.service"; then
    SERVICE_NAME="gps-exif-tagger-legacy.service"
else
    echo -e "${RED}Error: GPS EXIF Tagger service not installed${NC}"
    echo "Run installation test first: ./test_installation.sh"
    exit 1
fi

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}GPS EXIF Tagger Service - Monitoring${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Check if service is running
echo -e "${BLUE}Service Status:${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}  ✓ Service is running${NC}"
else
    echo -e "${YELLOW}  ⚠ Service is not running${NC}"
    echo ""
    read -p "Start the service now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start "$SERVICE_NAME"
        echo -e "${GREEN}  ✓ Service started${NC}"
        sleep 2
    else
        echo "Showing logs from last run..."
    fi
fi
echo ""

# Show service details
echo -e "${BLUE}Service Details:${NC}"
systemctl show "$SERVICE_NAME" -p MainPID --value | xargs -I {} echo "  PID: {}"
systemctl show "$SERVICE_NAME" -p MemoryCurrent --value | awk '{printf "  Memory: %.2f MB\n", $1/1024/1024}'
systemctl show "$SERVICE_NAME" -p CPUUsageNSec --value | awk '{printf "  CPU Time: %.2f seconds\n", $1/1000000000}'
echo ""

# Show recent logs (last 20 lines)
echo -e "${BLUE}Recent Logs (last 20 lines):${NC}"
echo -e "${BLUE}--------------------------------------------------------------------------------${NC}"
sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager | sed -E \
    -e "s/(GPS connection established)/$(printf "${GREEN}\1${NC}")/" \
    -e "s/(Successfully embedded GPS)/$(printf "${GREEN}\1${NC}")/" \
    -e "s/(ERROR|Error|error)/$(printf "${RED}\1${NC}")/g" \
    -e "s/(WARNING|Warning|warning)/$(printf "${YELLOW}\1${NC}")/g" \
    -e "s/(Started watching)/$(printf "${BLUE}\1${NC}")/"
echo -e "${BLUE}--------------------------------------------------------------------------------${NC}"
echo ""

# Follow logs in real-time
echo -e "${BLUE}Following logs in real-time...${NC}"
echo -e "${YELLOW}(Press Ctrl+C to stop)${NC}"
echo ""
sleep 1

# Use journalctl with color highlighting
sudo journalctl -u "$SERVICE_NAME" -f --no-pager | sed -E \
    -e "s/(GPS connection established)/$(printf "${GREEN}\1${NC}")/" \
    -e "s/(Successfully embedded GPS)/$(printf "${GREEN}\1${NC}")/" \
    -e "s/(Processing photo)/$(printf "${BLUE}\1${NC}")/" \
    -e "s/(ERROR|Error|error)/$(printf "${RED}\1${NC}")/g" \
    -e "s/(WARNING|Warning|warning)/$(printf "${YELLOW}\1${NC}")/g" \
    -e "s/(Started watching)/$(printf "${BLUE}\1${NC}")/"
