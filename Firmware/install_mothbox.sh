#!/bin/bash
# ==============================================================================
# Mothbox Installation/Migration Script
# ==============================================================================
#
# This script helps install or migrate Mothbox to different directory locations.
# It supports three installation types:
#
# 1. Legacy:     /home/pi/Desktop/Mothbox (default, backward compatible)
# 2. Production: /opt/mothbox (recommended for new installations)
# 3. Custom:     User-specified location via MOTHBOX_HOME environment variable
#
# Usage:
#   ./install_mothbox.sh [--type legacy|production|custom] [--path /custom/path]
#
# Examples:
#   ./install_mothbox.sh                          # Install to legacy location
#   ./install_mothbox.sh --type production        # Install to /opt/mothbox
#   ./install_mothbox.sh --type custom --path /srv/mothbox
#
# ==============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INSTALL_TYPE="legacy"
CUSTOM_PATH=""
QUICK_MODE="false"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            INSTALL_TYPE="$2"
            shift 2
            ;;
        --path)
            CUSTOM_PATH="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE="true"
            shift
            ;;
        --help|-h)
            grep -A 100 "^#" "$0" | grep -B 100 "^# =====.*=====$" | tail -n +2 | head -n -1 | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Determine target directories based on installation type
case $INSTALL_TYPE in
    legacy)
        MOTHBOX_HOME="/home/pi/Desktop/Mothbox"
        CONFIG_DIR="$MOTHBOX_HOME"
        DATA_DIR="$MOTHBOX_HOME"
        ;;
    production)
        MOTHBOX_HOME="/opt/mothbox"
        CONFIG_DIR="/etc/mothbox"
        DATA_DIR="/var/lib/mothbox"
        ;;
    custom)
        if [ -z "$CUSTOM_PATH" ]; then
            echo -e "${RED}Error: --path required for custom installation${NC}"
            exit 1
        fi
        MOTHBOX_HOME="$CUSTOM_PATH"
        CONFIG_DIR="$MOTHBOX_HOME"
        DATA_DIR="$MOTHBOX_HOME"
        ;;
    *)
        echo -e "${RED}Error: Invalid installation type: $INSTALL_TYPE${NC}"
        echo "Valid types: legacy, production, custom"
        exit 1
        ;;
esac

# Print installation plan
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Installation Script${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""
echo -e "${GREEN}Installation Type:${NC} $INSTALL_TYPE"
echo -e "${GREEN}Application Directory:${NC} $MOTHBOX_HOME"
echo -e "${GREEN}Configuration Directory:${NC} $CONFIG_DIR"
echo -e "${GREEN}Data Directory:${NC} $DATA_DIR"
echo ""

# Detect Raspberry Pi model
echo -e "${BLUE}Detecting Raspberry Pi model...${NC}"
PI_VERSION=$(python3 "$SCRIPT_DIR/installation-utils/detect_pi_model.py")
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to detect Pi model. Installation aborted.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Detected Raspberry Pi ${PI_VERSION}${NC}"
echo ""

# Interactive firmware selection
echo -e "${BLUE}Firmware Selection${NC}"
echo "Detected: Raspberry Pi ${PI_VERSION}"
echo "Recommended firmware: ${PI_VERSION}.x"
echo ""
echo "Firmware versions use different GPIO pin mappings:"
echo "  4.x firmware: Relay pins 26/20/21 (legacy)"
echo "  5.x firmware: Relay pins 5/19/9 (current hardware)"
echo ""
echo "Select firmware version:"
echo "  1) 4.x firmware"
echo "  2) 5.x firmware"
echo ""

# Determine default based on detected Pi
if [ "$PI_VERSION" = "4" ]; then
    DEFAULT_CHOICE=1
else
    DEFAULT_CHOICE=2
fi

# Read user choice with default
while true; do
    read -p "Choice [$DEFAULT_CHOICE]: " FIRMWARE_CHOICE
    FIRMWARE_CHOICE=${FIRMWARE_CHOICE:-$DEFAULT_CHOICE}

    case $FIRMWARE_CHOICE in
        1)
            FIRMWARE_VERSION="4"
            echo -e "${GREEN}✓ Selected: 4.x firmware${NC}"
            break
            ;;
        2)
            FIRMWARE_VERSION="5"
            echo -e "${GREEN}✓ Selected: 5.x firmware${NC}"
            break
            ;;
        *)
            echo -e "${RED}Invalid choice. Please enter 1 or 2.${NC}"
            ;;
    esac
done
echo ""

# Hardware Configuration
echo -e "${BLUE}Hardware Configuration${NC}"
echo ""

# Set firmware-specific defaults
if [ "$FIRMWARE_VERSION" = "4" ]; then
    DEFAULT_CH1=26
    DEFAULT_CH2=20
    DEFAULT_CH3=21
else
    DEFAULT_CH1=5
    DEFAULT_CH2=19
    DEFAULT_CH3=9
fi

# Check for --quick flag to skip prompts
if [ "$QUICK_MODE" = "true" ]; then
    RELAY_CH1=$DEFAULT_CH1
    RELAY_CH2=$DEFAULT_CH2
    RELAY_CH3=$DEFAULT_CH3
    echo -e "${GREEN}Using default GPIO pins (quick mode)${NC}"
    echo "  Relay Ch1 (main):  GPIO $RELAY_CH1"
    echo "  Relay Ch2 (flash): GPIO $RELAY_CH2"
    echo "  Relay Ch3 (UV):    GPIO $RELAY_CH3"
else
    echo "Configure relay module GPIO pins:"
    echo "  Default for ${FIRMWARE_VERSION}.x: Ch1=${DEFAULT_CH1}, Ch2=${DEFAULT_CH2}, Ch3=${DEFAULT_CH3}"
    echo ""

    read -p "Relay Ch1 (main) GPIO pin [$DEFAULT_CH1]: " RELAY_CH1
    RELAY_CH1=${RELAY_CH1:-$DEFAULT_CH1}

    read -p "Relay Ch2 (flash) GPIO pin [$DEFAULT_CH2]: " RELAY_CH2
    RELAY_CH2=${RELAY_CH2:-$DEFAULT_CH2}

    read -p "Relay Ch3 (UV) GPIO pin [$DEFAULT_CH3]: " RELAY_CH3
    RELAY_CH3=${RELAY_CH3:-$DEFAULT_CH3}

    # Validate GPIO pins (BCM mode: 2-27)
    for pin in $RELAY_CH1 $RELAY_CH2 $RELAY_CH3; do
        if [ $pin -lt 2 ] || [ $pin -gt 27 ]; then
            echo -e "${RED}Error: GPIO pin $pin out of range (2-27)${NC}"
            exit 1
        fi
    done

    # Check for conflicts
    if [ "$RELAY_CH1" = "$RELAY_CH2" ] || [ "$RELAY_CH1" = "$RELAY_CH3" ] || [ "$RELAY_CH2" = "$RELAY_CH3" ]; then
        echo -e "${RED}Error: GPIO pins must be unique${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ GPIO configuration validated${NC}"
fi
echo ""

# Ask for confirmation
read -p "Proceed with installation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installation cancelled.${NC}"
    exit 0
fi

echo ""

# Install system packages
"$SCRIPT_DIR/installation-utils/install_system_packages.sh"
echo ""

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install --break-system-packages -r "$SCRIPT_DIR/installation-utils/requirements.txt"
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Configure camera
"$SCRIPT_DIR/installation-utils/configure_camera.sh"
echo ""

echo -e "${BLUE}Creating directories...${NC}"

# Create directories
sudo mkdir -p "$MOTHBOX_HOME"
sudo mkdir -p "$CONFIG_DIR"
sudo mkdir -p "$DATA_DIR/photos"

# Set ownership to pi user (adjust if needed)
if [ "$INSTALL_TYPE" = "production" ]; then
    sudo chown -R pi:pi "$MOTHBOX_HOME" "$CONFIG_DIR" "$DATA_DIR"
fi

# Set permissions
sudo chmod -R 755 "$MOTHBOX_HOME"
sudo chmod -R 755 "$CONFIG_DIR"
sudo chmod -R 755 "$DATA_DIR"  # Owner rwx, group rx, others rx

echo -e "${GREEN}✓ Directories created${NC}"

# Copy firmware files
echo -e "${BLUE}Copying firmware files...${NC}"
sudo cp -r "$SCRIPT_DIR"/* "$MOTHBOX_HOME/"

# For production installation, copy config files to /etc/mothbox
if [ "$INSTALL_TYPE" = "production" ]; then
    echo -e "${BLUE}Setting up production configuration...${NC}"

    # Config files are in the firmware-version-specific directory
    CONFIG_SOURCE="$SCRIPT_DIR/${FIRMWARE_VERSION}.x"

    # Copy config files from source
    if [ -f "$CONFIG_SOURCE/controls.txt" ]; then
        sudo cp "$CONFIG_SOURCE/controls.txt" "$CONFIG_DIR/"
    fi
    if [ -f "$CONFIG_SOURCE/camera_settings.csv" ]; then
        sudo cp "$CONFIG_SOURCE/camera_settings.csv" "$CONFIG_DIR/"
    fi
    if [ -f "$CONFIG_SOURCE/schedule_settings.csv" ]; then
        sudo cp "$CONFIG_SOURCE/schedule_settings.csv" "$CONFIG_DIR/"
    fi
    if [ -f "$CONFIG_SOURCE/wordlist.csv" ]; then
        sudo cp "$CONFIG_SOURCE/wordlist.csv" "$CONFIG_DIR/"
    fi

    echo -e "${GREEN}✓ Configuration files copied to $CONFIG_DIR${NC}"
fi

echo -e "${GREEN}✓ Firmware files copied${NC}"

# Write GPIO configuration to controls.txt
echo -e "${BLUE}Configuring GPIO pins...${NC}"

# Determine the controls.txt path based on installation type
if [ "$INSTALL_TYPE" = "production" ]; then
    CONTROLS_FILE="$CONFIG_DIR/controls.txt"
else
    CONTROLS_FILE="$MOTHBOX_HOME/${FIRMWARE_VERSION}.x/controls.txt"
fi

# Append GPIO configuration if not already present
if ! grep -q "^Relay_Ch1=" "$CONTROLS_FILE" 2>/dev/null; then
    echo "" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "# GPIO Pin Configuration" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "Relay_Ch1=$RELAY_CH1" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "Relay_Ch2=$RELAY_CH2" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "Relay_Ch3=$RELAY_CH3" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo -e "${GREEN}✓ GPIO configuration written to controls.txt${NC}"
else
    # Update existing GPIO configuration
    sudo sed -i "s/^Relay_Ch1=.*/Relay_Ch1=$RELAY_CH1/" "$CONTROLS_FILE"
    sudo sed -i "s/^Relay_Ch2=.*/Relay_Ch2=$RELAY_CH2/" "$CONTROLS_FILE"
    sudo sed -i "s/^Relay_Ch3=.*/Relay_Ch3=$RELAY_CH3/" "$CONTROLS_FILE"
    echo -e "${GREEN}✓ GPIO configuration updated in controls.txt${NC}"
fi
echo ""

# Set execute permissions on Python scripts
echo -e "${BLUE}Setting script permissions...${NC}"
find "$MOTHBOX_HOME" -name "*.py" -exec sudo chmod +x {} \;
echo -e "${GREEN}✓ Script permissions set${NC}"

# Print success message and next steps
echo ""
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
echo -e "${BLUE}Raspberry Pi Model:${NC} Pi ${PI_VERSION}"
echo -e "${BLUE}Firmware Version:${NC} ${FIRMWARE_VERSION}.x"
echo -e "${BLUE}Mothbox Location:${NC} $MOTHBOX_HOME"
echo -e "${BLUE}Configuration:${NC} $CONFIG_DIR"
echo -e "${BLUE}Data Directory:${NC} $DATA_DIR"
echo ""
echo -e "${BLUE}Hardware Configuration:${NC}"
echo "  Relay Ch1 (main):  GPIO $RELAY_CH1"
echo "  Relay Ch2 (flash): GPIO $RELAY_CH2"
echo "  Relay Ch3 (UV):    GPIO $RELAY_CH3"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review and edit configuration files in: $CONFIG_DIR"
echo "2. Update your crontab to point to: $MOTHBOX_HOME"
echo "3. Test the installation by running: python3 $MOTHBOX_HOME/mothbox_paths.py"
echo "4. Test photo capture: python3 $MOTHBOX_HOME/${FIRMWARE_VERSION}.x/TakePhoto.py"
echo ""

if [ "$INSTALL_TYPE" = "custom" ]; then
    echo -e "${YELLOW}Custom Installation Note:${NC}"
    echo "Set the MOTHBOX_HOME environment variable in your .bashrc:"
    echo "  export MOTHBOX_HOME=$MOTHBOX_HOME"
    echo ""
fi

echo -e "${BLUE}Documentation:${NC} See README for full setup instructions"
echo ""
