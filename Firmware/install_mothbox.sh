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

# Additional Hardware Module Configuration
echo -e "${BLUE}Additional Hardware Modules${NC}"
echo ""

if [ "$QUICK_MODE" = "true" ]; then
    # Quick mode - use all defaults
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
else
    # Power Sensor Configuration
    echo -e "${YELLOW}Power Sensor (INA260/INA219)${NC}"
    read -p "Configure INA260 power sensor? (Y/n): " CONFIGURE_INA260
    CONFIGURE_INA260=${CONFIGURE_INA260:-Y}

    if [[ "$CONFIGURE_INA260" =~ ^[Yy]$ ]]; then
        INA260_ENABLED="true"
        read -p "  INA260 I2C address [0x40]: " INA260_ADDRESS
        INA260_ADDRESS=${INA260_ADDRESS:-0x40}
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

        read -p "    RST pin [17]: " EPAPER_RST
        EPAPER_RST=${EPAPER_RST:-17}

        read -p "    DC pin [25]: " EPAPER_DC
        EPAPER_DC=${EPAPER_DC:-25}

        read -p "    CS pin [8]: " EPAPER_CS
        EPAPER_CS=${EPAPER_CS:-8}

        read -p "    BUSY pin [24]: " EPAPER_BUSY
        EPAPER_BUSY=${EPAPER_BUSY:-24}

        read -p "    PWR pin [18]: " EPAPER_PWR
        EPAPER_PWR=${EPAPER_PWR:-18}

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
    echo -e "${YELLOW}GPS Module${NC}"
    read -p "Configure GPS module? (Y/n): " CONFIGURE_GPS
    CONFIGURE_GPS=${CONFIGURE_GPS:-Y}

    if [[ "$CONFIGURE_GPS" =~ ^[Yy]$ ]]; then
        GPS_ENABLED="true"
        echo "  GPS device options:"
        echo "    1) /dev/ttyAMA0 (UART - GPIO pins 14/15)"
        echo "    2) /dev/ttyUSB0 (USB GPS module)"
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

        read -p "  GPS baud rate [9600]: " GPS_BAUDRATE
        GPS_BAUDRATE=${GPS_BAUDRATE:-9600}

        read -p "  GPS timeout (seconds) [10]: " GPS_TIMEOUT
        GPS_TIMEOUT=${GPS_TIMEOUT:-10}

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
        read -p "  I2C address [0x21]: " PCA9536_ADDRESS
        PCA9536_ADDRESS=${PCA9536_ADDRESS:-0x21}
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
                read -p "  I2C address [0x20]: " MUX_ADDRESS
                MUX_ADDRESS=${MUX_ADDRESS:-0x20}
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

# Write hardware module configuration
echo -e "${BLUE}Configuring hardware modules...${NC}"
if ! grep -q "^ina260_enabled=" "$CONTROLS_FILE" 2>/dev/null; then
    echo "ina260_enabled=$INA260_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "ina260_address=$INA260_ADDRESS" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_enabled=$EPAPER_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_rst_pin=$EPAPER_RST" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_dc_pin=$EPAPER_DC" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_cs_pin=$EPAPER_CS" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_busy_pin=$EPAPER_BUSY" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "epaper_pwr_pin=$EPAPER_PWR" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "gps_enabled=$GPS_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "gps_device=$GPS_DEVICE" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "gps_baudrate=$GPS_BAUDRATE" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "gps_timeout=$GPS_TIMEOUT" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "light_sensor_enabled=$LIGHT_SENSOR_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "light_sensor_type=$LIGHT_SENSOR_TYPE" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "light_sensor_address=$LIGHT_SENSOR_ADDRESS" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "pca9536_enabled=$PCA9536_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "pca9536_address=$PCA9536_ADDRESS" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "mux_enabled=$MUX_ENABLED" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "mux_type=$MUX_TYPE" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo "mux_address=$MUX_ADDRESS" | sudo tee -a "$CONTROLS_FILE" > /dev/null
    echo -e "${GREEN}✓ Hardware module configuration written to controls.txt${NC}"
else
    # Update existing hardware configuration
    sudo sed -i "s/^ina260_enabled=.*/ina260_enabled=$INA260_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s/^ina260_address=.*/ina260_address=$INA260_ADDRESS/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_enabled=.*/epaper_enabled=$EPAPER_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_rst_pin=.*/epaper_rst_pin=$EPAPER_RST/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_dc_pin=.*/epaper_dc_pin=$EPAPER_DC/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_cs_pin=.*/epaper_cs_pin=$EPAPER_CS/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_busy_pin=.*/epaper_busy_pin=$EPAPER_BUSY/" "$CONTROLS_FILE"
    sudo sed -i "s/^epaper_pwr_pin=.*/epaper_pwr_pin=$EPAPER_PWR/" "$CONTROLS_FILE"
    sudo sed -i "s/^gps_enabled=.*/gps_enabled=$GPS_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s|^gps_device=.*|gps_device=$GPS_DEVICE|" "$CONTROLS_FILE"
    sudo sed -i "s/^gps_baudrate=.*/gps_baudrate=$GPS_BAUDRATE/" "$CONTROLS_FILE"
    sudo sed -i "s/^gps_timeout=.*/gps_timeout=$GPS_TIMEOUT/" "$CONTROLS_FILE"
    sudo sed -i "s/^light_sensor_enabled=.*/light_sensor_enabled=$LIGHT_SENSOR_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s/^light_sensor_type=.*/light_sensor_type=$LIGHT_SENSOR_TYPE/" "$CONTROLS_FILE"
    sudo sed -i "s/^light_sensor_address=.*/light_sensor_address=$LIGHT_SENSOR_ADDRESS/" "$CONTROLS_FILE"
    sudo sed -i "s/^pca9536_enabled=.*/pca9536_enabled=$PCA9536_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s/^pca9536_address=.*/pca9536_address=$PCA9536_ADDRESS/" "$CONTROLS_FILE"
    sudo sed -i "s/^mux_enabled=.*/mux_enabled=$MUX_ENABLED/" "$CONTROLS_FILE"
    sudo sed -i "s/^mux_type=.*/mux_type=$MUX_TYPE/" "$CONTROLS_FILE"
    sudo sed -i "s/^mux_address=.*/mux_address=$MUX_ADDRESS/" "$CONTROLS_FILE"
    echo -e "${GREEN}✓ Hardware module configuration updated in controls.txt${NC}"
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
echo -e "${BLUE}Hardware Modules:${NC}"
echo "  INA260 Power Sensor:  $INA260_ENABLED (address: $INA260_ADDRESS)"
echo "  E-Paper Display:      $EPAPER_ENABLED"
echo "  GPS Module:           $GPS_ENABLED (device: $GPS_DEVICE)"
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
