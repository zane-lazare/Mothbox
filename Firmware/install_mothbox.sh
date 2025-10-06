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

# Ask for confirmation
read -p "Proceed with installation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installation cancelled.${NC}"
    exit 0
fi

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
sudo chmod -R 777 "$DATA_DIR"  # Photos directory needs write access

echo -e "${GREEN}✓ Directories created${NC}"

# Copy firmware files
echo -e "${BLUE}Copying firmware files...${NC}"
sudo cp -r "$SCRIPT_DIR"/* "$MOTHBOX_HOME/"

# For production installation, copy config files to /etc/mothbox
if [ "$INSTALL_TYPE" = "production" ]; then
    echo -e "${BLUE}Setting up production configuration...${NC}"

    # Copy config files
    if [ -f "$MOTHBOX_HOME/controls.txt" ]; then
        sudo cp "$MOTHBOX_HOME/controls.txt" "$CONFIG_DIR/"
    fi
    if [ -f "$MOTHBOX_HOME/camera_settings.csv" ]; then
        sudo cp "$MOTHBOX_HOME/camera_settings.csv" "$CONFIG_DIR/"
    fi
    if [ -f "$MOTHBOX_HOME/schedule_settings.csv" ]; then
        sudo cp "$MOTHBOX_HOME/schedule_settings.csv" "$CONFIG_DIR/"
    fi
    if [ -f "$MOTHBOX_HOME/wordlist.csv" ]; then
        sudo cp "$MOTHBOX_HOME/wordlist.csv" "$CONFIG_DIR/"
    fi

    echo -e "${GREEN}✓ Configuration files copied to $CONFIG_DIR${NC}"
fi

echo -e "${GREEN}✓ Firmware files copied${NC}"

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
echo -e "${BLUE}Mothbox Location:${NC} $MOTHBOX_HOME"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review and edit configuration files in: $CONFIG_DIR"
echo "2. Update your crontab to point to: $MOTHBOX_HOME"
echo "3. Test the installation by running: python3 $MOTHBOX_HOME/mothbox_paths.py"
echo ""

if [ "$INSTALL_TYPE" = "custom" ]; then
    echo -e "${YELLOW}Custom Installation Note:${NC}"
    echo "Set the MOTHBOX_HOME environment variable in your .bashrc:"
    echo "  export MOTHBOX_HOME=$MOTHBOX_HOME"
    echo ""
fi

echo -e "${BLUE}Documentation:${NC} See README for full setup instructions"
echo ""
