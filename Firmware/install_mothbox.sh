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
#   ./install_mothbox.sh                          # Interactive mode (recommended)
#   ./install_mothbox.sh [--type TYPE] [--quick] [--with-webui] [--path PATH]
#
# Interactive Mode (default when no arguments):
#   - Guided menu for installation type selection
#   - Option for quick install or custom hardware configuration
#   - Option to install Web UI
#   - Best for manual installations
#
# CLI Mode (for automation):
#   --type [legacy|production|custom]   Installation type
#   --path /custom/path                 Path for custom installation
#   --quick                             Skip interactive prompts, use defaults
#   --with-webui                        Install Web UI (Node.js + Flask + React)
#   --env [development|production]      Web UI environment (default: development)
#
# Examples:
#   ./install_mothbox.sh                                # Interactive wizard
#   ./install_mothbox.sh --type production              # CLI: production install
#   ./install_mothbox.sh --type legacy --quick          # CLI: quick legacy install
#   ./install_mothbox.sh --type production --with-webui # CLI: production + webui (dev mode)
#   ./install_mothbox.sh --with-webui --env production  # CLI: webui in production mode
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

# Input validation functions
validate_gpio_pin() {
    local pin="$1"
    if ! [[ "$pin" =~ ^[0-9]+$ ]]; then
        echo "Error: GPIO pin must be numeric"
        return 1
    fi
    if [ "$pin" -lt 2 ] || [ "$pin" -gt 27 ]; then
        echo "Error: GPIO pin out of range (2-27)"
        return 1
    fi
    return 0
}

validate_i2c_address() {
    local addr="$1"
    if [[ ! "$addr" =~ ^0x[0-9a-fA-F]{2}$ ]]; then
        echo "Error: Invalid I2C address format (expected: 0xNN)"
        return 1
    fi
    local decimal=$((addr))
    if [ "$decimal" -lt 3 ] || [ "$decimal" -gt 119 ]; then
        echo "Error: I2C address out of valid range (0x03-0x77)"
        return 1
    fi
    return 0
}

validate_positive_integer() {
    local num="$1"
    local max="${2:-999999}"
    if ! [[ "$num" =~ ^[0-9]+$ ]]; then
        echo "Error: Must be a positive integer"
        return 1
    fi
    if [ "$num" -gt "$max" ]; then
        echo "Error: Value exceeds maximum ($max)"
        return 1
    fi
    return 0
}


# Default values
INSTALL_TYPE="legacy"
CUSTOM_PATH=""
QUICK_MODE="false"
INSTALL_WEBUI_FLAG="false"
MOTHBOX_ENV="development"  # Default environment for Web UI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect the user who should own Mothbox files
# If run with sudo, use SUDO_USER; otherwise use current USER; fallback to 'pi'
if [ -n "$SUDO_USER" ]; then
    MOTHBOX_USER="$SUDO_USER"
elif [ -n "$USER" ]; then
    MOTHBOX_USER="$USER"
else
    MOTHBOX_USER="pi"
fi

# Detect if running interactively (no arguments provided)
INTERACTIVE_MODE="false"
if [ $# -eq 0 ]; then
    INTERACTIVE_MODE="true"
fi

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
        --with-webui)
            INSTALL_WEBUI_FLAG="true"
            shift
            ;;
        --env)
            MOTHBOX_ENV="$2"
            if [[ ! "$MOTHBOX_ENV" =~ ^(development|production)$ ]]; then
                echo -e "${RED}Invalid environment: $MOTHBOX_ENV${NC}"
                echo "Valid options: development, production"
                exit 1
            fi
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

# Interactive menu if no arguments provided
if [ "$INTERACTIVE_MODE" = "true" ]; then
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}Mothbox Installation Wizard${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    # Installation type selection
    echo "Select installation type:"
    echo "  1) Legacy    (/home/pi/Desktop/Mothbox - all files in one location)"
    echo "  2) Production (/opt/mothbox - FHS compliant, recommended)"
    echo "  3) Custom    (specify your own path)"
    echo ""
    read -p "Choice [1-3]: " choice

    case $choice in
        1)
            INSTALL_TYPE="legacy"
            MOTHBOX_HOME="/home/pi/Desktop/Mothbox"
            CONFIG_DIR="$MOTHBOX_HOME"
            DATA_DIR="$MOTHBOX_HOME"
            ;;
        2)
            INSTALL_TYPE="production"
            MOTHBOX_HOME="/opt/mothbox"
            CONFIG_DIR="/etc/mothbox"
            DATA_DIR="/var/lib/mothbox"
            ;;
        3)
            INSTALL_TYPE="custom"
            read -p "Enter custom installation path: " CUSTOM_PATH
            # Validate custom path
            if [ -z "$CUSTOM_PATH" ]; then
                echo -e "${RED}Error: Custom path cannot be empty${NC}"
                exit 1
            fi
            # Remove trailing slashes for consistency
            CUSTOM_PATH="${CUSTOM_PATH%/}"
            # Check for dangerous characters
            # Use variable for regex to avoid bash interpreting special chars
            INVALID_PATH_CHARS='[[:space:];$`()|&<>]'
            if [[ "$CUSTOM_PATH" =~ $INVALID_PATH_CHARS ]]; then
                echo -e "${RED}Error: Custom path contains invalid characters${NC}"
                exit 1
            fi
            # Validate custom path for security
            if [[ "$CUSTOM_PATH" =~ \.\. ]] || [[ "$CUSTOM_PATH" =~ ^/(etc|usr|bin|sbin|boot|sys|proc|dev|root) ]]; then
                echo -e "${RED}Error: Custom path cannot be a system directory or contain path traversal${NC}"
                exit 1
            fi
            if [[ ! "$CUSTOM_PATH" =~ ^/ ]]; then
                echo -e "${RED}Error: Custom path must be absolute${NC}"
                exit 1
            fi
            MOTHBOX_HOME="$CUSTOM_PATH"
            CONFIG_DIR="$MOTHBOX_HOME"
            DATA_DIR="$MOTHBOX_HOME"
            ;;
        *)
            echo -e "${RED}Invalid choice. Exiting.${NC}"
            exit 1
            ;;
    esac

    # Quick mode selection
    echo ""
    read -p "Quick installation with defaults? (Y/n): " quick_choice
    if [[ ! $quick_choice =~ ^[Nn]$ ]]; then
        QUICK_MODE="true"
    fi

    echo ""
fi

# Determine target directories based on installation type (CLI mode only)
if [ "$INTERACTIVE_MODE" = "false" ]; then
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
            # Remove trailing slashes for consistency
            CUSTOM_PATH="${CUSTOM_PATH%/}"
            # Check for dangerous characters
            # Use variable for regex to avoid bash interpreting special chars
            INVALID_PATH_CHARS='[[:space:];$`()|&<>]'
            if [[ "$CUSTOM_PATH" =~ $INVALID_PATH_CHARS ]]; then
                echo -e "${RED}Error: Custom path contains invalid characters${NC}"
                exit 1
            fi
            # Validate custom path for security
            if [[ "$CUSTOM_PATH" =~ \.\. ]] || [[ "$CUSTOM_PATH" =~ ^/(etc|usr|bin|sbin|boot|sys|proc|dev|root) ]]; then
                echo -e "${RED}Error: Custom path cannot be a system directory or contain path traversal${NC}"
                exit 1
            fi
            if [[ ! "$CUSTOM_PATH" =~ ^/ ]]; then
                echo -e "${RED}Error: Custom path must be absolute${NC}"
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
fi

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

# Set firmware-specific defaults for relay GPIO pins
if [ "$FIRMWARE_VERSION" = "4" ]; then
    DEFAULT_CH1=26
    DEFAULT_CH2=20
    DEFAULT_CH3=21
else
    DEFAULT_CH1=5
    DEFAULT_CH2=19
    DEFAULT_CH3=9
fi

if [ "$QUICK_MODE" = "true" ]; then
    # Quick mode - use all defaults
    RELAY_ENABLED="true"
    RELAY_CH1=$DEFAULT_CH1
    RELAY_CH2=$DEFAULT_CH2
    RELAY_CH3=$DEFAULT_CH3
    INA260_ENABLED="true"
    INA260_ADDRESS="0x40"
    EPAPER_ENABLED="true"
    EPAPER_RST=17
    EPAPER_DC=25
    EPAPER_CS=8
    EPAPER_BUSY=24
    EPAPER_PWR=18
    GPS_ENABLED="true"
    GPS_DEVICE="/dev/ttyAMA0"
    GPS_BAUDRATE=9600
    GPS_TIMEOUT=10
    LIGHT_SENSOR_ENABLED="false"
    LIGHT_SENSOR_TYPE="LTR303"
    LIGHT_SENSOR_ADDRESS="0x29"
    PCA9536_ENABLED="false"
    PCA9536_ADDRESS="0x21"
    MUX_ENABLED="false"
    MUX_TYPE="i2c"
    MUX_ADDRESS="0x20"
    echo -e "${GREEN}Using default hardware configuration (quick mode)${NC}"
    echo "  Relay module:      enabled"
    echo "    Ch1 (main):      GPIO $RELAY_CH1"
    echo "    Ch2 (flash):     GPIO $RELAY_CH2"
    echo "    Ch3 (UV):        GPIO $RELAY_CH3"
else
    # Relay Module Configuration (Core Hardware)
    echo -e "${YELLOW}Relay Module (3-channel for attract lights/flash/UV)${NC}"
    read -p "Enable relay module? (Y/n): " CONFIGURE_RELAY
    CONFIGURE_RELAY=${CONFIGURE_RELAY:-Y}

    if [[ "$CONFIGURE_RELAY" =~ ^[Yy]$ ]]; then
        RELAY_ENABLED="true"
        echo "  Configure relay module GPIO pins:"
        echo "  Default for ${FIRMWARE_VERSION}.x: Ch1=${DEFAULT_CH1}, Ch2=${DEFAULT_CH2}, Ch3=${DEFAULT_CH3}"
        echo ""

        read -p "  Relay Ch1 (main) GPIO pin [$DEFAULT_CH1]: " RELAY_CH1
        RELAY_CH1=${RELAY_CH1:-$DEFAULT_CH1}

        read -p "  Relay Ch2 (flash) GPIO pin [$DEFAULT_CH2]: " RELAY_CH2
        RELAY_CH2=${RELAY_CH2:-$DEFAULT_CH2}

        read -p "  Relay Ch3 (UV) GPIO pin [$DEFAULT_CH3]: " RELAY_CH3
        RELAY_CH3=${RELAY_CH3:-$DEFAULT_CH3}

        # Validate GPIO pins (BCM mode: 2-27)
        for pin in $RELAY_CH1 $RELAY_CH2 $RELAY_CH3; do
            if [ $pin -lt 2 ] || [ $pin -gt 27 ]; then
                echo -e "${RED}  Error: GPIO pin $pin out of range (2-27)${NC}"
                exit 1
            fi
        done

        # Check for conflicts
        if [ "$RELAY_CH1" = "$RELAY_CH2" ] || [ "$RELAY_CH1" = "$RELAY_CH3" ] || [ "$RELAY_CH2" = "$RELAY_CH3" ]; then
            echo -e "${RED}  Error: GPIO pins must be unique${NC}"
            exit 1
        fi

        echo -e "${GREEN}  ✓ Relay module enabled${NC}"
    else
        RELAY_ENABLED="false"
        RELAY_CH1=$DEFAULT_CH1
        RELAY_CH2=$DEFAULT_CH2
        RELAY_CH3=$DEFAULT_CH3
        echo -e "${YELLOW}  ⊗ Relay module disabled${NC}"
    fi
    echo ""

    # Additional Hardware Modules
    echo -e "${BLUE}Additional Hardware Modules${NC}"
    echo ""

    # Power Sensor Configuration
    echo -e "${YELLOW}Power Sensor (INA260/INA219)${NC}"
    read -p "Configure INA260 power sensor? (Y/n): " CONFIGURE_INA260
    CONFIGURE_INA260=${CONFIGURE_INA260:-Y}

    if [[ "$CONFIGURE_INA260" =~ ^[Yy]$ ]]; then
        INA260_ENABLED="true"
        while true; do
            read -p "  INA260 I2C address [0x40]: " INA260_ADDRESS
            INA260_ADDRESS=${INA260_ADDRESS:-0x40}
            if validate_i2c_address "$INA260_ADDRESS"; then
                break
            fi
            echo -e "${RED}    Invalid input. Please try again.${NC}"
        done
        echo -e "${GREEN}  ✓ INA260 enabled at address $INA260_ADDRESS${NC}"
    else
        INA260_ENABLED="false"
        INA260_ADDRESS="0x40"
        echo -e "${YELLOW}  ⊗ INA260 disabled${NC}"
    fi
    echo ""

    # E-Paper Display Configuration
    echo -e "${YELLOW}E-Paper Display (Waveshare 2.13\")${NC}"
    read -p "Configure e-paper display? (Y/n): " CONFIGURE_EPAPER
    CONFIGURE_EPAPER=${CONFIGURE_EPAPER:-Y}

    if [[ "$CONFIGURE_EPAPER" =~ ^[Yy]$ ]]; then
        EPAPER_ENABLED="true"
        echo "  E-paper GPIO pins [RST=17, DC=25, CS=8, BUSY=24, PWR=18]"
        echo "  Press Enter to use defaults, or configure custom pins:"

        # RST pin with validation
        while true; do
            read -p "    RST pin [17]: " EPAPER_RST
            EPAPER_RST=${EPAPER_RST:-17}
            if validate_gpio_pin "$EPAPER_RST"; then
                break
            fi
            echo -e "${RED}      Invalid input. Please try again.${NC}"
        done

        # DC pin with validation
        while true; do
            read -p "    DC pin [25]: " EPAPER_DC
            EPAPER_DC=${EPAPER_DC:-25}
            if validate_gpio_pin "$EPAPER_DC"; then
                break
            fi
            echo -e "${RED}      Invalid input. Please try again.${NC}"
        done

        # CS pin with validation
        while true; do
            read -p "    CS pin [8]: " EPAPER_CS
            EPAPER_CS=${EPAPER_CS:-8}
            if validate_gpio_pin "$EPAPER_CS"; then
                break
            fi
            echo -e "${RED}      Invalid input. Please try again.${NC}"
        done

        # BUSY pin with validation
        while true; do
            read -p "    BUSY pin [24]: " EPAPER_BUSY
            EPAPER_BUSY=${EPAPER_BUSY:-24}
            if validate_gpio_pin "$EPAPER_BUSY"; then
                break
            fi
            echo -e "${RED}      Invalid input. Please try again.${NC}"
        done

        # PWR pin with validation
        while true; do
            read -p "    PWR pin [18]: " EPAPER_PWR
            EPAPER_PWR=${EPAPER_PWR:-18}
            if validate_gpio_pin "$EPAPER_PWR"; then
                break
            fi
            echo -e "${RED}      Invalid input. Please try again.${NC}"
        done

        echo -e "${GREEN}  ✓ E-paper display enabled${NC}"
    else
        EPAPER_ENABLED="false"
        EPAPER_RST=17
        EPAPER_DC=25
        EPAPER_CS=8
        EPAPER_BUSY=24
        EPAPER_PWR=18
        echo -e "${YELLOW}  ⊗ E-paper display disabled${NC}"
    fi
    echo ""

    # GPS Module Configuration
    echo -e "${YELLOW}GPS Module (NEO-M8N or compatible)${NC}"
    echo "  Hardware connection:"
    echo "    - GPIO 14 (TX) → GPS RX"
    echo "    - GPIO 15 (RX) → GPS TX"
    echo "    - 3.3V → GPS VCC"
    echo "    - GND → GPS GND"
    echo ""
    echo -e "${YELLOW}  ⚠ Note: UART mode disables Bluetooth on Pi 3/4/5${NC}"
    echo "  (Bluetooth conflicts with UART0 on these models)"
    echo ""
    read -p "Configure GPS module? (Y/n): " CONFIGURE_GPS
    CONFIGURE_GPS=${CONFIGURE_GPS:-Y}

    if [[ "$CONFIGURE_GPS" =~ ^[Yy]$ ]]; then
        GPS_ENABLED="true"
        echo "  GPS device options:"
        echo "    1) /dev/ttyAMA0 (UART - GPIO pins 14/15, disables Bluetooth)"
        echo "    2) /dev/ttyUSB0 (USB GPS module, Bluetooth unaffected)"
        echo "    3) Custom device path"
        read -p "  Select GPS device [1]: " GPS_DEVICE_CHOICE
        GPS_DEVICE_CHOICE=${GPS_DEVICE_CHOICE:-1}

        case $GPS_DEVICE_CHOICE in
            1) GPS_DEVICE="/dev/ttyAMA0" ;;
            2) GPS_DEVICE="/dev/ttyUSB0" ;;
            3)
                read -p "  Enter custom GPS device path: " GPS_DEVICE
                GPS_DEVICE=${GPS_DEVICE:-/dev/ttyAMA0}
                ;;
            *) GPS_DEVICE="/dev/ttyAMA0" ;;
        esac

        # GPS baud rate with validation
        while true; do
            read -p "  GPS baud rate [9600]: " GPS_BAUDRATE
            GPS_BAUDRATE=${GPS_BAUDRATE:-9600}
            if validate_positive_integer "$GPS_BAUDRATE" 115200; then
                break
            fi
            echo -e "${RED}    Invalid input. Please try again.${NC}"
        done

        # GPS timeout with validation
        while true; do
            read -p "  GPS timeout (seconds) [10]: " GPS_TIMEOUT
            GPS_TIMEOUT=${GPS_TIMEOUT:-10}
            if validate_positive_integer "$GPS_TIMEOUT" 300; then
                break
            fi
            echo -e "${RED}    Invalid input. Please try again.${NC}"
        done

        echo -e "${GREEN}  ✓ GPS enabled: $GPS_DEVICE @ $GPS_BAUDRATE baud${NC}"
    else
        GPS_ENABLED="false"
        GPS_DEVICE="/dev/ttyAMA0"
        GPS_BAUDRATE=9600
        GPS_TIMEOUT=10
        echo -e "${YELLOW}  ⊗ GPS disabled${NC}"
    fi
    echo ""

    # Optional Modules
    echo -e "${YELLOW}Optional Modules${NC}"
    echo ""

    # Light Sensor
    echo -e "${YELLOW}Light Sensor (BH1750/LTR-303)${NC}"
    read -p "Enable light sensor? (y/N): " CONFIGURE_LIGHT_SENSOR
    CONFIGURE_LIGHT_SENSOR=${CONFIGURE_LIGHT_SENSOR:-N}

    if [[ "$CONFIGURE_LIGHT_SENSOR" =~ ^[Yy]$ ]]; then
        LIGHT_SENSOR_ENABLED="true"
        echo "  Sensor type:"
        echo "    1) LTR-303 (I2C 0x29) - Current hardware"
        echo "    2) BH1750 (I2C 0x23) - Legacy hardware"
        read -p "  Select sensor type [1]: " LIGHT_SENSOR_CHOICE
        LIGHT_SENSOR_CHOICE=${LIGHT_SENSOR_CHOICE:-1}

        case $LIGHT_SENSOR_CHOICE in
            1)
                LIGHT_SENSOR_TYPE="LTR303"
                LIGHT_SENSOR_ADDRESS="0x29"
                ;;
            2)
                LIGHT_SENSOR_TYPE="BH1750"
                LIGHT_SENSOR_ADDRESS="0x23"
                ;;
            *)
                LIGHT_SENSOR_TYPE="LTR303"
                LIGHT_SENSOR_ADDRESS="0x29"
                ;;
        esac

        echo -e "${GREEN}  ✓ Light sensor enabled: $LIGHT_SENSOR_TYPE at $LIGHT_SENSOR_ADDRESS${NC}"
    else
        LIGHT_SENSOR_ENABLED="false"
        LIGHT_SENSOR_TYPE="LTR303"
        LIGHT_SENSOR_ADDRESS="0x29"
        echo -e "${YELLOW}  ⊗ Light sensor disabled${NC}"
    fi
    echo ""

    # PCA9536 GPIO Expander
    echo -e "${YELLOW}PCA9536 GPIO Expander${NC}"
    read -p "Enable PCA9536? (y/N): " CONFIGURE_PCA9536
    CONFIGURE_PCA9536=${CONFIGURE_PCA9536:-N}

    if [[ "$CONFIGURE_PCA9536" =~ ^[Yy]$ ]]; then
        PCA9536_ENABLED="true"
        while true; do
            read -p "  I2C address [0x21]: " PCA9536_ADDRESS
            PCA9536_ADDRESS=${PCA9536_ADDRESS:-0x21}
            if validate_i2c_address "$PCA9536_ADDRESS"; then
                break
            fi
            echo -e "${RED}    Invalid input. Please try again.${NC}"
        done
        echo -e "${GREEN}  ✓ PCA9536 enabled at $PCA9536_ADDRESS${NC}"
    else
        PCA9536_ENABLED="false"
        PCA9536_ADDRESS="0x21"
        echo -e "${YELLOW}  ⊗ PCA9536 disabled${NC}"
    fi
    echo ""

    # Multiplexer
    echo -e "${YELLOW}Multiplexer (CD74HC4067/PCA9535)${NC}"
    read -p "Enable multiplexer? (y/N): " CONFIGURE_MUX
    CONFIGURE_MUX=${CONFIGURE_MUX:-N}

    if [[ "$CONFIGURE_MUX" =~ ^[Yy]$ ]]; then
        MUX_ENABLED="true"
        echo "  Multiplexer type:"
        echo "    1) I2C-based (PCA9535 at 0x20) - Current hardware"
        echo "    2) GPIO-based (CD74HC4067) - Legacy hardware"
        read -p "  Select type [1]: " MUX_TYPE_CHOICE
        MUX_TYPE_CHOICE=${MUX_TYPE_CHOICE:-1}

        case $MUX_TYPE_CHOICE in
            1)
                MUX_TYPE="i2c"
                while true; do
                    read -p "  I2C address [0x20]: " MUX_ADDRESS
                    MUX_ADDRESS=${MUX_ADDRESS:-0x20}
                    if validate_i2c_address "$MUX_ADDRESS"; then
                        break
                    fi
                    echo -e "${RED}    Invalid input. Please try again.${NC}"
                done
                echo -e "${GREEN}  ✓ Multiplexer enabled: I2C at $MUX_ADDRESS${NC}"
                ;;
            2)
                MUX_TYPE="gpio"
                MUX_ADDRESS="0x20"
                echo "  Using default GPIO pins (EN_A=31, EN_B=29, S0-S3=33/13/12/15, SIG=36)"
                echo -e "${GREEN}  ✓ Multiplexer enabled: GPIO mode${NC}"
                ;;
            *)
                MUX_TYPE="i2c"
                MUX_ADDRESS="0x20"
                echo -e "${GREEN}  ✓ Multiplexer enabled: I2C at $MUX_ADDRESS${NC}"
                ;;
        esac
    else
        MUX_ENABLED="false"
        MUX_TYPE="i2c"
        MUX_ADDRESS="0x20"
        echo -e "${YELLOW}  ⊗ Multiplexer disabled${NC}"
    fi
    echo ""
fi

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
# Use constraints file to prevent installation of conflicting packages
pip3 install --break-system-packages \
    -c "$SCRIPT_DIR/installation-utils/pip-constraints.txt" \
    -r "$SCRIPT_DIR/installation-utils/requirements.txt"
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Fix GPIO compatibility on Pi 5 (Adafruit libraries override python3-rpi-lgpio)
echo -e "${BLUE}Ensuring GPIO compatibility...${NC}"
# Remove incompatible pip-installed RPi.GPIO (conflicts with python3-rpi-lgpio)
pip3 uninstall -y --break-system-packages RPi.GPIO 2>/dev/null || true
# Remove Adafruit's RPi.GPIO override files
sudo rm -rf /usr/local/lib/python3.*/dist-packages/RPi/ 2>/dev/null || true
echo -e "${GREEN}✓ GPIO compatibility ensured${NC}"

echo ""

# Configure camera
"$SCRIPT_DIR/installation-utils/configure_camera.sh"
echo ""

# Configure GPS hardware (if enabled)
if [ "$GPS_ENABLED" = "true" ]; then
    export GPS_DEVICE
    export GPS_BAUDRATE
    "$SCRIPT_DIR/installation-utils/configure_gps.sh"
fi

echo -e "${BLUE}Creating directories...${NC}"

# Create directories
sudo mkdir -p "$MOTHBOX_HOME"
sudo mkdir -p "$CONFIG_DIR"
sudo mkdir -p "$CONFIG_DIR/isp_tuning"
sudo mkdir -p "$DATA_DIR/photos"

# Set ownership to Mothbox user
if [ "$INSTALL_TYPE" = "production" ]; then
    sudo chown -R $MOTHBOX_USER:$MOTHBOX_USER "$MOTHBOX_HOME" "$CONFIG_DIR" "$DATA_DIR"
fi

# Set permissions with proper granularity
# Directories: 755 (rwxr-xr-x)
# Regular files: 644 (rw-r--r--)
# Scripts (.py, .sh): 755 (rwxr-xr-x)
echo "Setting file permissions..."
find "$MOTHBOX_HOME" -type d -exec sudo chmod 755 {} +
find "$MOTHBOX_HOME" -type f -exec sudo chmod 644 {} +
find "$MOTHBOX_HOME" -type f \( -name "*.py" -o -name "*.sh" \) -exec sudo chmod 755 {} +

find "$CONFIG_DIR" -type d -exec sudo chmod 755 {} +
find "$CONFIG_DIR" -type f -exec sudo chmod 644 {} +

find "$DATA_DIR" -type d -exec sudo chmod 755 {} +
find "$DATA_DIR" -type f -exec sudo chmod 644 {} +

echo -e "${GREEN}✓ Directories created and permissions set${NC}"

# Copy firmware files (exclude development artifacts)
echo -e "${BLUE}Copying firmware files...${NC}"

# Determine which firmware version to exclude (copy only selected version)
if [ "$FIRMWARE_VERSION" = "4" ]; then
    EXCLUDE_FIRMWARE="5.x"
else
    EXCLUDE_FIRMWARE="4.x"
fi

# Validate selected firmware version exists
SELECTED_FIRMWARE="${FIRMWARE_VERSION}.x"
if [ ! -d "$SCRIPT_DIR/$SELECTED_FIRMWARE" ]; then
    echo -e "${RED}✗ Error: Firmware version $SELECTED_FIRMWARE not found in $SCRIPT_DIR${NC}"
    echo -e "${RED}   Available firmware versions:${NC}"

    # Show available firmware versions with completeness status
    found_any=false
    for fw_dir in "$SCRIPT_DIR"/*.x; do
        if [ -d "$fw_dir" ]; then
            found_any=true
            fw_name=$(basename "$fw_dir")

            # Check if all critical files are present
            has_all_files=true
            for file in TakePhoto.py controls.txt Scheduler.py; do
                if [ ! -f "$fw_dir/$file" ]; then
                    has_all_files=false
                    break
                fi
            done

            # Display with status indicator
            if [ "$has_all_files" = true ]; then
                echo -e "  ${GREEN}✓${NC} $fw_name (complete)"
            else
                echo -e "  ${YELLOW}⚠${NC} $fw_name (incomplete)"
            fi
        fi
    done

    if [ "$found_any" = false ]; then
        echo "  None found"
    fi

    exit 1
fi
echo -e "${GREEN}✓ Firmware version $SELECTED_FIRMWARE validated${NC}"

# Verify critical firmware files exist
CRITICAL_FILES=("TakePhoto.py" "controls.txt" "Scheduler.py")
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$SELECTED_FIRMWARE/$file" ]; then
        echo -e "${RED}✗ Error: Critical file missing: $SCRIPT_DIR/$SELECTED_FIRMWARE/$file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ All critical firmware files present${NC}"

# Use rsync if available for better control, fallback to cp
if command -v rsync &> /dev/null; then
    sudo rsync -av \
        --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
        --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
        --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
        --exclude='installation-utils' --exclude='migrate_*.py' \
        --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
        --exclude='*.md' \
        --exclude='Tests' \
        --exclude="$EXCLUDE_FIRMWARE" \
        "$SCRIPT_DIR/" "$MOTHBOX_HOME/"
    echo -e "${GREEN}✓ Firmware files copied (${FIRMWARE_VERSION}.x only, excluding dev artifacts)${NC}"
else
    sudo cp -r "$SCRIPT_DIR"/* "$MOTHBOX_HOME/"
    echo -e "${YELLOW}⚠ rsync not available, copied all files including dev artifacts${NC}"
fi

# Copy configuration files (ALL installation types need these)
echo -e "${BLUE}Setting up configuration files...${NC}"

# Config files are in the firmware-version-specific directory
CONFIG_SOURCE="$SCRIPT_DIR/${FIRMWARE_VERSION}.x"

# Copy config files from source with atomic permission setting
# Use 'install' command to set ownership and permissions atomically
# This prevents race conditions where files briefly have wrong permissions
CONFIG_FILES=("controls.txt" "camera_settings.csv" "schedule_settings.csv" "wordlist.csv")
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$CONFIG_SOURCE/$file" ]; then
        # install command atomically copies and sets permissions
        # -o: owner, -g: group, -m: mode (664 = rw-rw-r--)
        sudo install -o $MOTHBOX_USER -g $MOTHBOX_USER -m 664 \
            "$CONFIG_SOURCE/$file" "$CONFIG_DIR/$file"
        echo -e "${GREEN}  ✓ Copied $file${NC}"
    else
        echo -e "${YELLOW}  ⚠ Warning: $file not found in $CONFIG_SOURCE${NC}"
    fi
done

# Update softwareversion in controls.txt to match user's firmware selection
if [ -f "$CONFIG_DIR/controls.txt" ]; then
    echo -e "${BLUE}Updating firmware version in config...${NC}"
    sudo sed -i "s/^softwareversion=.*/softwareversion=${FIRMWARE_VERSION}.0.0/" "$CONFIG_DIR/controls.txt"
    echo -e "${GREEN}✓ Firmware version set to ${FIRMWARE_VERSION}.0.0${NC}"
fi

# Copy ISP tuning file (camera ISP configuration for Picamera2)
echo -e "${BLUE}Setting up ISP tuning configuration...${NC}"
ISP_SOURCE="$SCRIPT_DIR/isp_tuning/camera_isp_tuning.json"
if [ -f "$ISP_SOURCE" ]; then
    sudo install -o $MOTHBOX_USER -g $MOTHBOX_USER -m 644 \
        "$ISP_SOURCE" "$CONFIG_DIR/isp_tuning/camera_isp_tuning.json"
    echo -e "${GREEN}  ✓ Copied camera_isp_tuning.json${NC}"
else
    echo -e "${YELLOW}  ⚠ Warning: ISP tuning file not found at $ISP_SOURCE${NC}"
fi

# Copy libcamera tuning file (autofocus retrigger configuration for OV64A40)
echo -e "${BLUE}Setting up libcamera tuning configuration...${NC}"
LIBCAMERA_TUNING_SOURCE="$SCRIPT_DIR/webui/libcamera_tuning/ov64a40_mothbox.json"
LIBCAMERA_TUNING_DEST="/usr/share/libcamera/ipa/rpi/pisp/ov64a40.json"
if [ -f "$LIBCAMERA_TUNING_SOURCE" ]; then
    # Backup original if it exists and backup doesn't already exist
    if [ -f "$LIBCAMERA_TUNING_DEST" ] && [ ! -f "${LIBCAMERA_TUNING_DEST}.orig" ]; then
        sudo cp "$LIBCAMERA_TUNING_DEST" "${LIBCAMERA_TUNING_DEST}.orig"
        echo -e "${GREEN}  ✓ Backed up original ov64a40.json${NC}"
    fi

    # Install custom tuning file
    sudo install -o root -g root -m 644 \
        "$LIBCAMERA_TUNING_SOURCE" "$LIBCAMERA_TUNING_DEST"
    echo -e "${GREEN}  ✓ Installed custom OV64A40 tuning file (AF retrigger enabled)${NC}"
else
    echo -e "${YELLOW}  ⚠ Warning: Custom libcamera tuning file not found at $LIBCAMERA_TUNING_SOURCE${NC}"
fi

echo -e "${GREEN}✓ Configuration files set up at $CONFIG_DIR${NC}"

# Create installation type marker file for reliable detection
echo -e "${BLUE}Creating installation marker...${NC}"
echo "$INSTALL_TYPE" | sudo tee "$MOTHBOX_HOME/.installation_type" > /dev/null
sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$MOTHBOX_HOME/.installation_type"
echo -e "${GREEN}✓ Installation type marked as '$INSTALL_TYPE'${NC}"

# Helper function to atomically update controls.txt with file locking
# Prevents race conditions when WebUI or firmware scripts access the file
update_controls_atomic() {
    local lockfile="${CONTROLS_FILE}.lock"

    # Acquire exclusive lock (wait up to 10 seconds)
    (
        flock -x -w 10 200 || {
            echo -e "${RED}✗ Failed to acquire lock on controls.txt${NC}"
            return 1
        }

        # All updates happen atomically inside the lock
        "$@"

    ) 200>"$lockfile"
}

# Helper function to update or add a config line in controls.txt
# Usage: update_or_add_config "key" "value" "$CONTROLS_FILE"
update_or_add_config() {
    local key="$1"
    local value="$2"
    local file="$3"

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # Update existing line
        sudo sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        # Add new line
        echo "${key}=${value}" | sudo tee -a "$file" > /dev/null
    fi
}

# Export function so it's available in subshells (needed for update_controls_atomic)
export -f update_or_add_config

# Write GPIO configuration to controls.txt
echo -e "${BLUE}Configuring GPIO pins...${NC}"

# Determine the controls.txt path based on installation type
if [ "$INSTALL_TYPE" = "production" ]; then
    CONTROLS_FILE="$CONFIG_DIR/controls.txt"
else
    CONTROLS_FILE="$MOTHBOX_HOME/${FIRMWARE_VERSION}.x/controls.txt"
fi

# Validate GPIO pin numbers before writing to prevent command injection
# Valid BCM GPIO pins are 2-27 (same validation as WebUI)
echo -e "${BLUE}Validating GPIO configuration...${NC}"
for pin_name in "RELAY_CH1" "RELAY_CH2" "RELAY_CH3"; do
    pin_value="${!pin_name}"
    if ! [[ "$pin_value" =~ ^[0-9]+$ ]] || [ "$pin_value" -lt 2 ] || [ "$pin_value" -gt 27 ]; then
        echo -e "${RED}✗ Error: Invalid GPIO pin for $pin_name: $pin_value${NC}"
        echo -e "${RED}  Valid BCM GPIO pins are 2-27${NC}"
        exit 1
    fi
done

# Validate numeric values for hardware config
if ! [[ "$GPS_BAUDRATE" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}✗ Error: GPS_BAUDRATE must be numeric: $GPS_BAUDRATE${NC}"
    exit 1
fi
if ! [[ "$GPS_TIMEOUT" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}✗ Error: GPS_TIMEOUT must be numeric: $GPS_TIMEOUT${NC}"
    exit 1
fi

# Validate I2C addresses (hex format 0xXX)
for addr_name in "INA260_ADDRESS" "LIGHT_SENSOR_ADDRESS" "PCA9536_ADDRESS" "MUX_ADDRESS"; do
    addr_value="${!addr_name}"
    if ! [[ "$addr_value" =~ ^0x[0-9A-Fa-f]{2}$ ]]; then
        echo -e "${RED}✗ Error: Invalid I2C address for $addr_name: $addr_value${NC}"
        echo -e "${RED}  Must be in format 0xXX (e.g., 0x40)${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Configuration values validated${NC}"

# Append GPIO configuration if not already present
if ! grep -q "^Relay_Ch1=" "$CONTROLS_FILE" 2>/dev/null; then
    update_controls_atomic bash -c "
        echo 'Relay_Ch1=$RELAY_CH1' | sudo tee -a '$CONTROLS_FILE' > /dev/null
        echo 'Relay_Ch2=$RELAY_CH2' | sudo tee -a '$CONTROLS_FILE' > /dev/null
        echo 'Relay_Ch3=$RELAY_CH3' | sudo tee -a '$CONTROLS_FILE' > /dev/null
    "
    echo -e "${GREEN}✓ GPIO configuration written to controls.txt${NC}"
else
    # Update existing GPIO configuration with file locking
    update_controls_atomic bash -c "
        sudo sed -i 's/^Relay_Ch1=.*/Relay_Ch1=$RELAY_CH1/' '$CONTROLS_FILE'
        sudo sed -i 's/^Relay_Ch2=.*/Relay_Ch2=$RELAY_CH2/' '$CONTROLS_FILE'
        sudo sed -i 's/^Relay_Ch3=.*/Relay_Ch3=$RELAY_CH3/' '$CONTROLS_FILE'
    "
    echo -e "${GREEN}✓ GPIO configuration updated in controls.txt${NC}"
fi

# Write hardware module configuration
echo -e "${BLUE}Configuring hardware modules...${NC}"

# Use update_or_add_config to handle both new installations and updates
# This ensures GPS config is added even to existing installations
update_controls_atomic bash -c "
    update_or_add_config 'relay_enabled' '$RELAY_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'ina260_enabled' '$INA260_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'ina260_address' '$INA260_ADDRESS' '$CONTROLS_FILE'
    update_or_add_config 'epaper_enabled' '$EPAPER_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'epaper_rst_pin' '$EPAPER_RST' '$CONTROLS_FILE'
    update_or_add_config 'epaper_dc_pin' '$EPAPER_DC' '$CONTROLS_FILE'
    update_or_add_config 'epaper_cs_pin' '$EPAPER_CS' '$CONTROLS_FILE'
    update_or_add_config 'epaper_busy_pin' '$EPAPER_BUSY' '$CONTROLS_FILE'
    update_or_add_config 'epaper_pwr_pin' '$EPAPER_PWR' '$CONTROLS_FILE'
    update_or_add_config 'gps_enabled' '$GPS_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'gps_device' '$GPS_DEVICE' '$CONTROLS_FILE'
    update_or_add_config 'gps_baudrate' '$GPS_BAUDRATE' '$CONTROLS_FILE'
    update_or_add_config 'gps_timeout' '$GPS_TIMEOUT' '$CONTROLS_FILE'
    update_or_add_config 'light_sensor_enabled' '$LIGHT_SENSOR_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'light_sensor_type' '$LIGHT_SENSOR_TYPE' '$CONTROLS_FILE'
    update_or_add_config 'light_sensor_address' '$LIGHT_SENSOR_ADDRESS' '$CONTROLS_FILE'
    update_or_add_config 'pca9536_enabled' '$PCA9536_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'pca9536_address' '$PCA9536_ADDRESS' '$CONTROLS_FILE'
    update_or_add_config 'mux_enabled' '$MUX_ENABLED' '$CONTROLS_FILE'
    update_or_add_config 'mux_type' '$MUX_TYPE' '$CONTROLS_FILE'
    update_or_add_config 'mux_address' '$MUX_ADDRESS' '$CONTROLS_FILE'
"

echo -e "${GREEN}✓ Hardware module configuration written/updated in controls.txt${NC}"
echo ""

# Set execute permissions on Python scripts
echo -e "${BLUE}Setting script permissions...${NC}"
find "$MOTHBOX_HOME" -name "*.py" -exec sudo chmod +x {} +
echo -e "${GREEN}✓ Script permissions set${NC}"

# Optional: Install Web UI
if [ "$INSTALL_WEBUI_FLAG" = "true" ] || [ "$INTERACTIVE_MODE" = "true" ]; then
    echo ""
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}Web UI Installation (Optional)${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo ""

    # Only prompt in interactive mode or if flag not set
    INSTALL_WEBUI="n"
    if [ "$INSTALL_WEBUI_FLAG" = "true" ]; then
        INSTALL_WEBUI="y"
    elif [ "$INTERACTIVE_MODE" = "true" ]; then
        echo -e "The Mothbox Web UI provides a browser-based interface for:"
        echo "  - Real-time system monitoring (CPU, disk, photos)"
        echo "  - Photo gallery with thumbnails"
        echo "  - Live camera preview"
        echo "  - GPIO controls (lights, flash)"
        echo "  - Scheduler management"
        echo "  - Settings configuration"
        echo ""
        echo -e "${YELLOW}Do you want to install the Web UI?${NC}"
        echo "(This will install Node.js, Flask, and build the frontend)"
        read -p "(y/N) " -n 1 -r
        echo
        INSTALL_WEBUI=$REPLY
    fi

    if [[ $INSTALL_WEBUI =~ ^[Yy]$ ]]; then
        echo ""

        # Ask for environment mode only in interactive mode (not if --env was specified)
        if [ "$INTERACTIVE_MODE" = "true" ]; then
            echo -e "${BLUE}Select Web UI environment:${NC}"
            echo "  1) Development (recommended for testing - enables debug mode)"
            echo "  2) Production (for deployment - requires gunicorn, not yet implemented)"
            echo ""
            read -p "Enter choice [1-2] (default: 1): " -r
            echo
            ENV_CHOICE=$REPLY
            ENV_CHOICE=${ENV_CHOICE:-1}

            if [ "$ENV_CHOICE" = "2" ]; then
                MOTHBOX_ENV="production"
                echo -e "${YELLOW}WARNING: Production mode is not yet fully implemented!${NC}"
                echo -e "${YELLOW}Production mode currently uses Werkzeug development server (not recommended)${NC}"
                echo -e "${YELLOW}For production deployment, wait for gunicorn implementation (issue #19)${NC}"
                echo ""
                read -p "Continue with production mode anyway? [y/N]: " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "${YELLOW}Reverting to development mode${NC}"
                    MOTHBOX_ENV="development"
                fi
            fi
        fi

        echo ""
        echo -e "${BLUE}Installing Web UI in ${MOTHBOX_ENV} mode...${NC}"
        # Export variables so install_webui.sh can use them for service file generation
        export MOTHBOX_HOME
        export MOTHBOX_ENV
        "$SCRIPT_DIR/installation-utils/install_webui.sh"
    fi
fi

# Post-install validation
echo ""
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Validating Installation...${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

VALIDATION_ERRORS=0

# Check required config files exist
echo -e "${BLUE}Checking configuration files...${NC}"
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$CONFIG_DIR/$file" ]; then
        echo -e "${GREEN}  ✓ $file exists${NC}"
    else
        echo -e "${RED}  ✗ $file missing!${NC}"
        VALIDATION_ERRORS=$((VALIDATION_ERRORS+1))
    fi
done

# Check Python can import mothbox_paths
echo -e "${BLUE}Checking Python imports...${NC}"
if python3 -c "import sys; sys.path.insert(0, '$MOTHBOX_HOME'); from mothbox_paths import get_gpio_pins; print('✓ Python imports OK')" 2>/dev/null; then
    echo -e "${GREEN}  ✓ mothbox_paths module loads correctly${NC}"
else
    echo -e "${RED}  ✗ Failed to import mothbox_paths!${NC}"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS+1))
fi

# Check GPIO pins are configured
echo -e "${BLUE}Checking GPIO configuration...${NC}"
if grep -q "^Relay_Ch1=" "$CONFIG_DIR/controls.txt" 2>/dev/null; then
    echo -e "${GREEN}  ✓ GPIO pins configured in controls.txt${NC}"
else
    echo -e "${YELLOW}  ⚠ GPIO pins not found in controls.txt (will use defaults)${NC}"
fi

# Check firmware version was updated
echo -e "${BLUE}Checking firmware version...${NC}"
if grep -q "^softwareversion=${FIRMWARE_VERSION}\." "$CONFIG_DIR/controls.txt" 2>/dev/null; then
    echo -e "${GREEN}  ✓ Firmware version correctly set to ${FIRMWARE_VERSION}.x${NC}"
else
    echo -e "${YELLOW}  ⚠ Firmware version may not match installation${NC}"
fi

# Check GPS configuration (if enabled)
if [ "$GPS_ENABLED" = "true" ]; then
    echo -e "${BLUE}Checking GPS configuration...${NC}"

    # Check gpsd is installed
    if command -v gpsd &> /dev/null; then
        echo -e "${GREEN}  ✓ gpsd installed${NC}"
    else
        echo -e "${RED}  ✗ gpsd not installed!${NC}"
        VALIDATION_ERRORS=$((VALIDATION_ERRORS+1))
    fi

    # Check UART is enabled (for /dev/ttyAMA0)
    if [ "$GPS_DEVICE" = "/dev/ttyAMA0" ] || [ "$GPS_DEVICE" = "/dev/serial0" ]; then
        if grep -q "^enable_uart=1" /boot/firmware/config.txt 2>/dev/null || \
           grep -q "^enable_uart=1" /boot/config.txt 2>/dev/null; then
            echo -e "${GREEN}  ✓ UART enabled in boot config${NC}"
        else
            echo -e "${YELLOW}  ⚠ UART not enabled in boot config${NC}"
        fi

        # Check Bluetooth is disabled
        if grep -q "^dtoverlay=disable-bt" /boot/firmware/config.txt 2>/dev/null || \
           grep -q "^dtoverlay=disable-bt" /boot/config.txt 2>/dev/null; then
            echo -e "${GREEN}  ✓ Bluetooth disabled (UART freed)${NC}"
        else
            echo -e "${YELLOW}  ⚠ Bluetooth not disabled${NC}"
        fi
    fi

    # Check GPS device exists (may not exist until reboot)
    if [ -e "$GPS_DEVICE" ]; then
        echo -e "${GREEN}  ✓ GPS device $GPS_DEVICE exists${NC}"
    else
        echo -e "${YELLOW}  ⚠ GPS device $GPS_DEVICE not found (reboot required if using UART)${NC}"
    fi

    # Check gpsd configuration
    if [ -f "/etc/default/gpsd" ] && grep -q "DEVICES=\"$GPS_DEVICE\"" /etc/default/gpsd; then
        echo -e "${GREEN}  ✓ gpsd configured for $GPS_DEVICE${NC}"
    else
        echo -e "${YELLOW}  ⚠ gpsd configuration may be incomplete${NC}"
    fi
fi

echo ""
if [ $VALIDATION_ERRORS -gt 0 ]; then
    echo -e "${RED}Installation completed with $VALIDATION_ERRORS validation errors!${NC}"
    echo -e "${YELLOW}Please check the errors above before running Mothbox.${NC}"
    echo ""
fi

# Print success message and next steps
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
echo -e "${BLUE}Hardware Modules:${NC}"
echo "  INA260 Power Sensor:  $INA260_ENABLED (address: $INA260_ADDRESS)"
echo "  E-Paper Display:      $EPAPER_ENABLED"
if [ "$GPS_ENABLED" = "true" ]; then
    echo "  GPS Module:           $GPS_ENABLED (device: $GPS_DEVICE @ ${GPS_BAUDRATE} baud)"
    if [ "$GPS_DEVICE" = "/dev/ttyAMA0" ] || [ "$GPS_DEVICE" = "/dev/serial0" ]; then
        echo "                        GPIO 14 (TX), GPIO 15 (RX)"
        echo "                        Bluetooth disabled (UART conflict)"
    fi
else
    echo "  GPS Module:           $GPS_ENABLED"
fi
if [ "$LIGHT_SENSOR_ENABLED" = "true" ]; then
    echo "  Light Sensor:         $LIGHT_SENSOR_ENABLED ($LIGHT_SENSOR_TYPE at $LIGHT_SENSOR_ADDRESS)"
fi
if [ "$PCA9536_ENABLED" = "true" ]; then
    echo "  PCA9536 Expander:     $PCA9536_ENABLED (address: $PCA9536_ADDRESS)"
fi
if [ "$MUX_ENABLED" = "true" ]; then
    echo "  Multiplexer:          $MUX_ENABLED ($MUX_TYPE mode)"
fi
echo ""

# GPS-specific next steps (if enabled and using UART)
if [ "$GPS_ENABLED" = "true" ]; then
    if [ "$GPS_DEVICE" = "/dev/ttyAMA0" ] || [ "$GPS_DEVICE" = "/dev/serial0" ]; then
        echo -e "${YELLOW}⚠ GPS UART Configuration Applied - REBOOT REQUIRED${NC}"
        echo ""
        echo -e "${BLUE}After reboot, test GPS hardware:${NC}"
        echo "  1. cat $GPS_DEVICE                  # Should show NMEA sentences"
        echo "  2. gpspipe -r                        # Shows raw GPS data via gpsd"
        echo "  3. cgps                              # Interactive GPS status viewer"
        echo "  4. python3 $MOTHBOX_HOME/${FIRMWARE_VERSION}.x/GPS.py  # Run GPS sync script"
        echo "  5. View GPS status in Web UI:       http://<pi-ip>:5000/settings"
        echo ""
        echo -e "${BLUE}GPS Troubleshooting:${NC}"
        echo "  • No NMEA data: Check wiring (TX↔RX, 3.3V, GND)"
        echo "  • No fix: Move to location with clear sky view (outdoor)"
        echo "  • Cold start: First fix may take 30-60 seconds"
        echo ""
    fi
fi

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review and edit configuration files in: $CONFIG_DIR"
if [ "$GPS_ENABLED" = "true" ] && [[ "$GPS_DEVICE" =~ ^/dev/ttyAMA0|/dev/serial0$ ]]; then
    echo "2. REBOOT to apply UART configuration: sudo reboot"
    echo "3. Update your crontab to point to: $MOTHBOX_HOME"
    echo "4. Test the installation by running: python3 $MOTHBOX_HOME/mothbox_paths.py"
    echo "5. Test photo capture: python3 $MOTHBOX_HOME/${FIRMWARE_VERSION}.x/TakePhoto.py"
else
    echo "2. Update your crontab to point to: $MOTHBOX_HOME"
    echo "3. Test the installation by running: python3 $MOTHBOX_HOME/mothbox_paths.py"
    echo "4. Test photo capture: python3 $MOTHBOX_HOME/${FIRMWARE_VERSION}.x/TakePhoto.py"
fi
echo ""

if [ "$INSTALL_TYPE" = "custom" ]; then
    echo -e "${YELLOW}Custom Installation Note:${NC}"
    echo "Set the MOTHBOX_HOME environment variable in your .bashrc:"
    echo "  export MOTHBOX_HOME=$MOTHBOX_HOME"
    echo ""
fi

echo -e "${BLUE}Documentation:${NC} See README for full setup instructions"
echo ""
