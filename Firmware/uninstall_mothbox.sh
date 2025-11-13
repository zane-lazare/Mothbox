#!/bin/bash
# ==============================================================================
# Mothbox Uninstallation Script
# ==============================================================================
#
# Safely removes Mothbox installation with options to preserve data and configs.
#
# Usage:
#   ./uninstall_mothbox.sh
#
# Features:
#   - Auto-detects installation type (legacy/production/custom)
#   - Option to backup configuration files before removal
#   - Option to preserve photos directory
#   - Option to remove crontab entries
#   - Requires explicit confirmation before deletion
#
# What is NOT removed:
#   - System packages (python3, git, etc.) - may be used by other software
#   - Python packages - may be used by other projects
#
# ==============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}================================================================================${NC}"
echo -e "${RED}Mothbox Uninstallation Script${NC}"
echo -e "${RED}================================================================================${NC}"
echo ""

# Detect installation using same logic as installer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try to detect installation type
# Priority: marker file > /opt/mothbox exists > env var > legacy path
INSTALLATION_MARKER="/opt/mothbox/.installation_type"

if [ -f "$INSTALLATION_MARKER" ]; then
    # Read installation type from marker file (most reliable)
    INSTALL_TYPE=$(cat "$INSTALLATION_MARKER" 2>/dev/null || echo "production")
    MOTHBOX_HOME="/opt/mothbox"

    # Set paths based on detected type
    if [ "$INSTALL_TYPE" = "production" ]; then
        CONFIG_DIR="/etc/mothbox"
        DATA_DIR="/var/lib/mothbox"
    else
        CONFIG_DIR="$MOTHBOX_HOME"
        DATA_DIR="$MOTHBOX_HOME"
    fi
elif [ -d "/opt/mothbox" ] && [ -z "$MOTHBOX_HOME" ]; then
    # Production installation (no env var override)
    INSTALL_TYPE="production"
    MOTHBOX_HOME="/opt/mothbox"
    CONFIG_DIR="/etc/mothbox"
    DATA_DIR="/var/lib/mothbox"
elif [ -n "$MOTHBOX_HOME" ] && [ -d "$MOTHBOX_HOME" ]; then
    # Custom location via environment variable
    INSTALL_TYPE="custom"
    CONFIG_DIR="$MOTHBOX_HOME"
    DATA_DIR="$MOTHBOX_HOME"
elif [ -d "/home/pi/Desktop/Mothbox" ]; then
    # Legacy Desktop installation
    INSTALL_TYPE="legacy"
    MOTHBOX_HOME="/home/pi/Desktop/Mothbox"
    CONFIG_DIR="$MOTHBOX_HOME"
    DATA_DIR="$MOTHBOX_HOME"
else
    echo -e "${YELLOW}No Mothbox installation detected.${NC}"
    echo ""
    echo "Checked locations:"
    echo "  - /opt/mothbox/.installation_type (marker file)"
    echo "  - /opt/mothbox (production)"
    echo "  - /home/pi/Desktop/Mothbox (legacy)"
    echo "  - \$MOTHBOX_HOME environment variable (custom)"
    echo ""
    exit 0
fi

echo -e "${BLUE}Detected Installation:${NC}"
echo -e "  Type: $INSTALL_TYPE"
echo -e "  Location: $MOTHBOX_HOME"
echo -e "  Configuration: $CONFIG_DIR"
echo -e "  Data: $DATA_DIR"
echo ""

# Backup configuration files
echo -e "${YELLOW}Do you want to backup configuration files before uninstalling?${NC}"
read -p "(y/N) " -n 1 -r
echo
BACKUP_CONFIGS=$REPLY

if [[ $BACKUP_CONFIGS =~ ^[Yy]$ ]]; then
    BACKUP_DIR="$HOME/mothbox_backup_$(date +%Y%m%d_%H%M%S)"
    echo -e "${BLUE}Creating backup in: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"

    if [ -f "$CONFIG_DIR/controls.txt" ]; then
        cp "$CONFIG_DIR/controls.txt" "$BACKUP_DIR/"
    fi
    if [ -f "$CONFIG_DIR/camera_settings.csv" ]; then
        cp "$CONFIG_DIR/camera_settings.csv" "$BACKUP_DIR/"
    fi
    if [ -f "$CONFIG_DIR/schedule_settings.csv" ]; then
        cp "$CONFIG_DIR/schedule_settings.csv" "$BACKUP_DIR/"
    fi
    if [ -f "$CONFIG_DIR/wordlist.csv" ]; then
        cp "$CONFIG_DIR/wordlist.csv" "$BACKUP_DIR/"
    fi

    echo -e "${GREEN}✓ Configuration backed up to: $BACKUP_DIR${NC}"
    echo ""
fi

# Preserve photos
PRESERVE_PHOTOS="n"
if [ -d "$DATA_DIR/photos" ]; then
    echo -e "${YELLOW}Do you want to preserve the photos directory?${NC}"
    echo -e "Location: $DATA_DIR/photos"
    read -p "(Y/n) " -n 1 -r
    echo
    PRESERVE_PHOTOS=$REPLY
fi

# Remove crontab entries
echo -e "${YELLOW}Do you want to remove Mothbox crontab entries?${NC}"
echo -e "(This will show you the crontab for manual editing)"
read -p "(y/N) " -n 1 -r
echo
REMOVE_CRON=$REPLY

# Ask about Node.js removal
REMOVE_NODEJS="n"
if command -v node &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Node.js is installed on this system.${NC}"
    echo -e "Do you want to remove Node.js and npm?"
    echo -e "${YELLOW}Warning: This may affect other applications that use Node.js${NC}"
    read -p "(y/N) " -n 1 -r
    echo
    REMOVE_NODEJS=$REPLY
fi

echo ""
echo -e "${RED}================================================================================${NC}"
echo -e "${RED}WARNING: The following will be PERMANENTLY DELETED:${NC}"
echo -e "${RED}================================================================================${NC}"
echo ""

if [ "$INSTALL_TYPE" = "production" ]; then
    echo -e "  ${RED}✗${NC} $MOTHBOX_HOME (application files)"
    echo -e "  ${RED}✗${NC} $CONFIG_DIR (configuration)"
    if [[ $PRESERVE_PHOTOS =~ ^[Nn]$ ]] || [ -z "$PRESERVE_PHOTOS" ]; then
        echo -e "  ${RED}✗${NC} $DATA_DIR (all data including photos)"
    else
        echo -e "  ${RED}✗${NC} $DATA_DIR (data directory structure, photos preserved)"
    fi
else
    if [[ $PRESERVE_PHOTOS =~ ^[Nn]$ ]] || [ -z "$PRESERVE_PHOTOS" ]; then
        echo -e "  ${RED}✗${NC} $MOTHBOX_HOME (all files including photos)"
    else
        echo -e "  ${RED}✗${NC} $MOTHBOX_HOME (all files except photos)"
    fi
fi

if [[ $REMOVE_CRON =~ ^[Yy]$ ]]; then
    echo -e "  ${RED}✗${NC} Mothbox crontab entries (you will edit manually)"
fi

if [[ $REMOVE_NODEJS =~ ^[Yy]$ ]]; then
    echo -e "  ${RED}✗${NC} Node.js and npm"
fi

echo ""

if [[ $PRESERVE_PHOTOS =~ ^[Yy]$ ]] || ([ -z "$PRESERVE_PHOTOS" ] && [ "$PRESERVE_PHOTOS" != "n" ]); then
    echo -e "${GREEN}The following will be PRESERVED:${NC}"
    echo -e "  ${GREEN}✓${NC} $DATA_DIR/photos"
    echo ""
fi

if [[ $BACKUP_CONFIGS =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Configuration backup saved to:${NC}"
    echo -e "  ${GREEN}✓${NC} $BACKUP_DIR"
    echo ""
fi

echo -e "${YELLOW}This action cannot be undone!${NC}"
echo -e "${YELLOW}Type 'yes' to confirm uninstallation:${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${GREEN}Uninstallation cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Uninstalling Mothbox...${NC}"

# Stop and remove web UI systemd service if it exists
if systemctl is-active --quiet mothbox-webui.service 2>/dev/null; then
    echo -e "${BLUE}Stopping mothbox-webui service...${NC}"
    sudo systemctl stop mothbox-webui.service
    echo -e "${GREEN}✓ Service stopped${NC}"
fi

if systemctl is-enabled --quiet mothbox-webui.service 2>/dev/null; then
    echo -e "${BLUE}Disabling mothbox-webui service...${NC}"
    sudo systemctl disable mothbox-webui.service
    echo -e "${GREEN}✓ Service disabled${NC}"
fi

if [ -f "/etc/systemd/system/mothbox-webui.service" ]; then
    echo -e "${BLUE}Removing systemd service file...${NC}"
    sudo rm /etc/systemd/system/mothbox-webui.service
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ Service file removed${NC}"
fi

# Stop and remove GPS EXIF Tagger systemd service if it exists
for SERVICE_FILE in gps-exif-tagger.service gps-exif-tagger-legacy.service; do
    if systemctl is-active --quiet "$SERVICE_FILE" 2>/dev/null; then
        echo -e "${BLUE}Stopping $SERVICE_FILE...${NC}"
        sudo systemctl stop "$SERVICE_FILE"
        echo -e "${GREEN}✓ Service stopped${NC}"
    fi

    if systemctl is-enabled --quiet "$SERVICE_FILE" 2>/dev/null; then
        echo -e "${BLUE}Disabling $SERVICE_FILE...${NC}"
        sudo systemctl disable "$SERVICE_FILE"
        echo -e "${GREEN}✓ Service disabled${NC}"
    fi

    if [ -f "/etc/systemd/system/$SERVICE_FILE" ]; then
        echo -e "${BLUE}Removing systemd service file: $SERVICE_FILE${NC}"
        sudo rm "/etc/systemd/system/$SERVICE_FILE"
        echo -e "${GREEN}✓ Service file removed${NC}"
    fi

    # Remove custom path override drop-in if it exists
    if [ -d "/etc/systemd/system/${SERVICE_FILE}.d" ]; then
        echo -e "${BLUE}Removing systemd drop-in overrides: ${SERVICE_FILE}.d/${NC}"
        sudo rm -rf "/etc/systemd/system/${SERVICE_FILE}.d"
        echo -e "${GREEN}✓ Drop-in overrides removed${NC}"
    fi
done

# Reload systemd after removing GPS EXIF services
if systemctl list-unit-files | grep -q "gps-exif-tagger"; then
    sudo systemctl daemon-reload
fi

# Preserve photos if requested
PHOTOS_BACKUP=""
if [[ $PRESERVE_PHOTOS =~ ^[Yy]$ ]] || ([ -z "$PRESERVE_PHOTOS" ] && [ "$PRESERVE_PHOTOS" != "n" ]); then
    if [ -d "$DATA_DIR/photos" ]; then
        PHOTOS_BACKUP="/tmp/mothbox_photos_$(date +%Y%m%d_%H%M%S)"
        echo -e "${BLUE}Temporarily moving photos to: $PHOTOS_BACKUP${NC}"
        sudo mv "$DATA_DIR/photos" "$PHOTOS_BACKUP"
    fi
fi

# Remove directories based on installation type
if [ "$INSTALL_TYPE" = "production" ]; then
    # Production: separate directories for code, config, and data
    if [ -d "$MOTHBOX_HOME" ]; then
        sudo rm -rf "$MOTHBOX_HOME"
        echo -e "${GREEN}✓ Removed $MOTHBOX_HOME${NC}"
    fi
    if [ -d "$CONFIG_DIR" ] && [ "$CONFIG_DIR" != "$MOTHBOX_HOME" ]; then
        sudo rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓ Removed $CONFIG_DIR${NC}"
    fi
    if [ -d "$DATA_DIR" ] && [ "$DATA_DIR" != "$MOTHBOX_HOME" ]; then
        sudo rm -rf "$DATA_DIR"
        echo -e "${GREEN}✓ Removed $DATA_DIR${NC}"
    fi
else
    # Legacy or custom: everything in one directory
    if [ -d "$MOTHBOX_HOME" ]; then
        sudo rm -rf "$MOTHBOX_HOME"
        echo -e "${GREEN}✓ Removed $MOTHBOX_HOME${NC}"
    fi
fi

# Remove installation marker file if it exists (created by new installer)
if [ -f "$INSTALLATION_MARKER" ]; then
    sudo rm -f "$INSTALLATION_MARKER"
    echo -e "${GREEN}✓ Removed installation marker${NC}"
fi

# Clean up temporary files created by Mothbox
echo -e "${BLUE}Cleaning up temporary files...${NC}"
CLEANED_FILES=0

# Remove GPIO state file (legacy /tmp location for backward compatibility)
# Note: Current GPIO state is stored in DATA_DIR/gpio_state.json
#       and is already removed during DATA_DIR cleanup (see lines 248-250 above)
if [ -f "/tmp/mothbox_gpio_state.json" ]; then
    sudo rm -f "/tmp/mothbox_gpio_state.json"
    echo -e "${GREEN}✓ Removed /tmp/mothbox_gpio_state.json${NC}"
    CLEANED_FILES=$((CLEANED_FILES + 1))
fi

# Remove EEPROM config file (created by Scheduler)
if [ -f "/tmp/eeprom_config.txt" ]; then
    sudo rm -f "/tmp/eeprom_config.txt"
    echo -e "${GREEN}✓ Removed /tmp/eeprom_config.txt${NC}"
    CLEANED_FILES=$((CLEANED_FILES + 1))
fi

# Remove any leftover service template file
if [ -f "/tmp/mothbox-webui.service" ]; then
    sudo rm -f "/tmp/mothbox-webui.service"
    echo -e "${GREEN}✓ Removed /tmp/mothbox-webui.service${NC}"
    CLEANED_FILES=$((CLEANED_FILES + 1))
fi

if [ $CLEANED_FILES -eq 0 ]; then
    echo -e "${YELLOW}  No temporary files found${NC}"
fi

# Restore photos if preserved
if [ -n "$PHOTOS_BACKUP" ] && [ -d "$PHOTOS_BACKUP" ]; then
    PHOTOS_DEST="$HOME/mothbox_photos"
    sudo mv "$PHOTOS_BACKUP" "$PHOTOS_DEST"
    sudo chown -R $USER:$USER "$PHOTOS_DEST"
    echo -e "${GREEN}✓ Photos preserved in: $PHOTOS_DEST${NC}"
fi

# Handle crontab
if [[ $REMOVE_CRON =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Opening crontab for editing...${NC}"
    echo -e "${YELLOW}Remove any lines that reference Mothbox, then save and exit.${NC}"
    echo ""
    read -p "Press Enter to continue..."
    crontab -e
fi

# Remove Node.js if requested
if [[ $REMOVE_NODEJS =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Removing Node.js and npm...${NC}"
    sudo apt-get remove -y nodejs npm
    sudo apt-get autoremove -y
    echo -e "${GREEN}✓ Node.js and npm removed${NC}"
fi

# Remove Python packages
REMOVE_PYTHON_PACKAGES="n"
echo ""
echo -e "${YELLOW}Python packages installed by Mothbox are still present.${NC}"
echo -e "Do you want to remove them?"
echo -e "${YELLOW}Warning: This may affect other applications that use these packages${NC}"
read -p "(y/N) " -n 1 -r
echo
REMOVE_PYTHON_PACKAGES=$REPLY

if [[ $REMOVE_PYTHON_PACKAGES =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Removing Python packages...${NC}"
    pip3 uninstall -y --break-system-packages \
        picamera2 opencv-python Pillow piexif \
        smbus2 adafruit-circuitpython-ina260 \
        psutil numpy python-crontab schedule \
        Flask Flask-CORS Flask-SocketIO python-socketio 2>/dev/null || true
    echo -e "${GREEN}✓ Python packages removed${NC}"
fi

echo ""
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Uninstallation Complete${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""

if [[ $BACKUP_CONFIGS =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Configuration backup:${NC} $BACKUP_DIR"
fi

if [ -n "$PHOTOS_BACKUP" ]; then
    echo -e "${GREEN}Photos location:${NC} $PHOTOS_DEST"
fi

echo ""
echo -e "${BLUE}What was NOT removed:${NC}"
echo "  - System packages (python3, git, i2c-tools, etc.)"
if [[ ! $REMOVE_PYTHON_PACKAGES =~ ^[Yy]$ ]]; then
    echo "  - Python packages (picamera2, opencv-python, Flask, etc.)"
fi
if [[ ! $REMOVE_NODEJS =~ ^[Yy]$ ]]; then
    echo "  - Node.js and npm (declined removal)"
fi
echo ""
