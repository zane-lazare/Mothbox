#!/bin/bash
# ==============================================================================
# Mothbox Camera Configuration Script
# ==============================================================================
#
# Configures camera support for Mothbox, including:
# - Enabling I2C interface (required for camera communication)
# - Adding appropriate device tree overlay for camera model
#
# Currently configured for: Arducam OwlSight 64MP (OV64A40 sensor)
#
# ==============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Configuring camera...${NC}"

# Enable I2C interface (required for camera communication)
echo -e "${BLUE}Enabling I2C interface...${NC}"
sudo raspi-config nonint do_i2c 0
echo -e "${GREEN}✓ I2C interface enabled${NC}"

# Configuration file location
CONFIG_FILE="/boot/firmware/config.txt"

# Check if camera overlay already exists
if grep -q "^dtoverlay=ov64a40" "$CONFIG_FILE" 2>/dev/null; then
    echo -e "${YELLOW}Camera overlay already configured${NC}"
    exit 0
fi

# Add camera overlay for Arducam OwlSight 64MP
echo -e "${BLUE}Adding camera overlay to config.txt...${NC}"

# Add configuration to the [all] section
# First, check if [all] section exists
if grep -q "^\[all\]" "$CONFIG_FILE"; then
    # [all] section exists, add after it
    sudo sed -i '/^\[all\]/a dtoverlay=ov64a40,cam1' "$CONFIG_FILE"
else
    # No [all] section, add it at the end
    echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "[all]" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "dtoverlay=ov64a40,cam1" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi

echo -e "${GREEN}✓ Camera overlay configured for Arducam OwlSight 64MP (OV64A40)${NC}"
echo -e "${BLUE}Note: Using CAM1 port (closer to USB-C power port)${NC}"
echo ""
echo -e "${YELLOW}A reboot will be required for camera changes to take effect.${NC}"
