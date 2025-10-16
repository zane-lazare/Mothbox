#!/bin/bash
# ==============================================================================
# Mothbox Web UI Installation Script
# ==============================================================================
#
# This script installs the Mothbox Web UI components:
# - Node.js (if not present)
# - Flask and web UI Python dependencies
# - Builds the React frontend
# - Configures GPIO permissions
# - Sets up systemd service for auto-start
#
# Usage:
#   ./install_webui.sh
#
# ==============================================================================

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect user
if [ -n "$SUDO_USER" ]; then
    MOTHBOX_USER="$SUDO_USER"
elif [ -n "$USER" ]; then
    MOTHBOX_USER="$USER"
else
    MOTHBOX_USER="pi"
fi

# Detect MOTHBOX_HOME from parent directory if not already set
if [ -z "$MOTHBOX_HOME" ]; then
    # Script is in Firmware/installation-utils, so parent of parent is MOTHBOX_HOME
    MOTHBOX_HOME="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Web UI Installation${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Use MOTHBOX_ENV from parent installer, or default to development for standalone runs
if [ -z "$MOTHBOX_ENV" ]; then
    MOTHBOX_ENV="development"
    echo -e "${YELLOW}Note: MOTHBOX_ENV not set, defaulting to development mode${NC}"
    echo -e "${YELLOW}Tip: Set MOTHBOX_ENV via main installer (install_mothbox.sh) for production${NC}"
fi

echo -e "${GREEN}Installing Web UI in ${MOTHBOX_ENV^^} mode${NC}"
if [ "$MOTHBOX_ENV" = "development" ]; then
    echo -e "${YELLOW}Note: Development mode enables debug logging and verbose error messages${NC}"
fi
echo ""

# Configure CORS for WebSocket/API access
echo -e "${BLUE}Configuring network access (CORS)...${NC}"
echo ""

# Auto-configure based on environment mode
if [ "$MOTHBOX_ENV" = "development" ]; then
    # Development: Allow all origins for local testing and development flexibility
    ALLOWED_ORIGINS="*"
    echo -e "${YELLOW}✓ Development mode: Allowing all origins for local testing${NC}"
    echo -e "${YELLOW}  WebSocket/API connections allowed from any origin${NC}"
    echo -e "${YELLOW}  Note: This is convenient but less secure. Use production mode for deployment.${NC}"
else
    # Production: Prompt user for security choice
    echo "The Web UI needs to know which origins can connect to its WebSocket/API."
    echo ""
    echo "Choose access mode:"
    echo "  ${GREEN}1) Same-origin only${NC} (RECOMMENDED for production)"
    echo "     - Most secure: only allows connections from the Mothbox itself"
    echo "     - Use when accessing Web UI at http://mothbox.local:5000 or http://<ip>:5000"
    echo ""
    echo "  ${YELLOW}2) Allow all origins${NC} (for testing/development)"
    echo "     - Allows connections from any device/origin"
    echo "     - Use when developing frontend separately or testing from other devices"
    echo "     - Less secure: any device can connect"
    echo ""
    read -p "Enter choice (1 or 2) [1]: " CORS_CHOICE
    CORS_CHOICE=${CORS_CHOICE:-1}

    if [ "$CORS_CHOICE" = "2" ]; then
        ALLOWED_ORIGINS="*"
        echo -e "${YELLOW}✓ Configured to allow all origins${NC}"
        echo -e "${YELLOW}  WebSocket/API connections allowed from any origin${NC}"
    else
        ALLOWED_ORIGINS=""
        echo -e "${GREEN}✓ Configured for same-origin only (most secure)${NC}"
        echo -e "${GREEN}  WebSocket/API connections only from the Mothbox itself${NC}"
    fi
fi
echo ""

# Check if Node.js is installed
echo -e "${BLUE}Checking Node.js installation...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js is already installed: $NODE_VERSION${NC}"
else
    echo -e "${YELLOW}Node.js not found. Installing Node.js 20.x...${NC}"

    # Install Node.js from NodeSource
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs

    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ Node.js installed successfully: $NODE_VERSION${NC}"
    else
        echo -e "${RED}✗ Failed to install Node.js${NC}"
        exit 1
    fi
fi
echo ""

# Install Flask and webui Python dependencies
echo -e "${BLUE}Installing Python dependencies for Web UI...${NC}"
# Use sudo -u to install as the correct user, not root
REQUIREMENTS_FILE="$SCRIPT_DIR/../webui/backend/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    if sudo -u $MOTHBOX_USER pip3 install --break-system-packages -r "$REQUIREMENTS_FILE"; then
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
    else
        echo -e "${RED}✗ Failed to install Python dependencies${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Requirements file not found: $REQUIREMENTS_FILE${NC}"
    exit 1
fi
echo ""

# Build React frontend
echo -e "${BLUE}Building React frontend...${NC}"
WEBUI_FRONTEND_DIR="$SCRIPT_DIR/../webui/frontend"

if [ ! -d "$WEBUI_FRONTEND_DIR" ]; then
    echo -e "${RED}✗ Web UI frontend directory not found: $WEBUI_FRONTEND_DIR${NC}"
    exit 1
fi

cd "$WEBUI_FRONTEND_DIR"

echo "Installing npm dependencies..."
# Run as the correct user, not root
if sudo -u $MOTHBOX_USER npm install; then
    echo -e "${GREEN}✓ npm dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install npm dependencies${NC}"
    exit 1
fi

# Verify node_modules was created
if [ ! -d "$WEBUI_FRONTEND_DIR/node_modules" ]; then
    echo -e "${RED}✗ node_modules directory not created${NC}"
    exit 1
fi

echo "Building production frontend..."
if sudo -u $MOTHBOX_USER npm run build; then
    echo -e "${GREEN}✓ Frontend built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build frontend${NC}"
    exit 1
fi
echo ""

# Configure GPIO permissions
echo -e "${BLUE}Configuring GPIO permissions...${NC}"
if groups $MOTHBOX_USER | grep -q '\bgpio\b'; then
    echo -e "${GREEN}✓ User $MOTHBOX_USER is already in gpio group${NC}"
else
    echo "Adding $MOTHBOX_USER to gpio group..."
    sudo usermod -a -G gpio $MOTHBOX_USER
    echo -e "${GREEN}✓ Added $MOTHBOX_USER to gpio group${NC}"
    echo -e "${YELLOW}Note: You may need to log out and log back in for group changes to take effect${NC}"
fi
echo ""

# Create webui_settings.txt if it doesn't exist and set proper permissions
echo -e "${BLUE}Setting up WebUI configuration files...${NC}"
# Detect installation type to find config directory
if [ -f "/opt/mothbox/.installation_type" ]; then
    CONFIG_DIR="/etc/mothbox"
elif [ -d "$MOTHBOX_HOME" ]; then
    CONFIG_DIR="$MOTHBOX_HOME"
else
    CONFIG_DIR="/etc/mothbox"
fi

WEBUI_SETTINGS_FILE="$CONFIG_DIR/webui_settings.txt"
if [ ! -f "$WEBUI_SETTINGS_FILE" ]; then
    echo "Creating webui_settings.txt with default values..."
    sudo tee "$WEBUI_SETTINGS_FILE" > /dev/null <<EOF
# Mothbox WebUI Settings
# Live preview stream settings (Task 5: Real-time control sliders)
sharpness=1.0
brightness=0.0
contrast=1.0
saturation=1.0
af_mode=2
af_speed=0
af_range=0
awb_enable=true
awb_mode=0
EOF
    echo -e "${GREEN}✓ Created webui_settings.txt with defaults${NC}"
fi

# Set ownership and permissions for WebUI to write to config files
# Use mode 664 (rw-rw-r--) so both user and group can write
echo "Setting config file permissions..."
sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$WEBUI_SETTINGS_FILE"
sudo chmod 664 "$WEBUI_SETTINGS_FILE"

# Also fix permissions on other config files that WebUI needs to modify
for config_file in "$CONFIG_DIR/controls.txt" "$CONFIG_DIR/camera_settings.csv" "$CONFIG_DIR/schedule_settings.csv"; do
    if [ -f "$config_file" ]; then
        sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$config_file"
        sudo chmod 664 "$config_file"
    fi
done

echo -e "${GREEN}✓ Config file permissions set (owner: $MOTHBOX_USER, mode: 664)${NC}"
echo ""

# Install systemd service
echo -e "${BLUE}Installing systemd service...${NC}"
SERVICE_TEMPLATE="$SCRIPT_DIR/mothbox-webui.service.template"

if [ ! -f "$SERVICE_TEMPLATE" ]; then
    echo -e "${YELLOW}Warning: mothbox-webui.service.template not found, skipping service installation${NC}"
else
    # Validate systemd template variables to prevent injection
    if [[ "$MOTHBOX_HOME" =~ [;$\`\(\)\|&<>\n] ]]; then
        echo -e "${RED}Error: MOTHBOX_HOME contains invalid characters${NC}"
        exit 1
    fi
    if [[ "$MOTHBOX_USER" =~ [;$\`\(\)\|&<>\n] ]]; then
        echo -e "${RED}Error: MOTHBOX_USER contains invalid characters${NC}"
        exit 1
    fi

    # Generate service file from template with actual values
    echo "Generating service file from template..."
    # Use mktemp for secure temporary file creation (prevents TOCTOU race conditions)
    TEMP_SERVICE=$(mktemp)
    sudo sed -e "s|__MOTHBOX_USER__|$MOTHBOX_USER|g" \
             -e "s|__MOTHBOX_HOME__|$MOTHBOX_HOME|g" \
             -e "s|__MOTHBOX_ENV__|$MOTHBOX_ENV|g" \
             -e "s|__ALLOWED_ORIGINS__|$ALLOWED_ORIGINS|g" \
             "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"

    # Install the generated service file
    sudo mv "$TEMP_SERVICE" /etc/systemd/system/mothbox-webui.service
    sudo systemctl daemon-reload
    sudo systemctl enable mothbox-webui.service
    echo -e "${GREEN}✓ Systemd service installed and enabled${NC}"
    echo -e "${GREEN}  User: $MOTHBOX_USER${NC}"
    echo -e "${GREEN}  Path: $MOTHBOX_HOME${NC}"
    echo -e "${GREEN}  Environment: $MOTHBOX_ENV${NC}"
    echo -e "${GREEN}  CORS Origins: ${ALLOWED_ORIGINS:-same-origin only}${NC}"

    # Start the service
    echo -e "${BLUE}Starting Web UI service...${NC}"
    if sudo systemctl start mothbox-webui.service; then
        echo -e "${GREEN}✓ Service started${NC}"

        # Wait a moment for service to initialize
        sleep 2

        # Verify service is running
        if systemctl is-active --quiet mothbox-webui.service; then
            echo -e "${GREEN}✓ Service is running${NC}"
        else
            echo -e "${RED}✗ Service started but is not active${NC}"
            echo -e "${YELLOW}Checking service status...${NC}"
            sudo systemctl status mothbox-webui.service --no-pager
        fi
    else
        echo -e "${RED}✗ Failed to start service${NC}"
        echo -e "${YELLOW}Checking service status...${NC}"
        sudo systemctl status mothbox-webui.service --no-pager
    fi
fi
echo ""

echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Web UI Installation Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""

# Show service status
if systemctl is-active --quiet mothbox-webui.service; then
    echo -e "${GREEN}✓ Web UI service is running${NC}"
    echo ""
    echo -e "${BLUE}Access the Web UI at:${NC}"
    echo "  Local:   http://localhost:5000"
    echo "  Network: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo -e "${BLUE}Service management:${NC}"
    echo "  Check status: sudo systemctl status mothbox-webui"
    echo "  Stop service: sudo systemctl stop mothbox-webui"
    echo "  Restart:      sudo systemctl restart mothbox-webui"
    echo "  View logs:    sudo journalctl -u mothbox-webui -f"
else
    echo -e "${YELLOW}Service is not running (see errors above)${NC}"
    echo ""
    echo -e "${BLUE}To start manually:${NC}"
    echo "  cd $SCRIPT_DIR/../webui/backend"
    echo "  python3 app.py"
    echo ""
    echo -e "${BLUE}Service commands:${NC}"
    echo "  sudo systemctl start mothbox-webui"
    echo "  sudo systemctl status mothbox-webui"
fi

echo ""
if ! groups $MOTHBOX_USER | grep -q '\bgpio\b'; then
    echo -e "${YELLOW}Note: $MOTHBOX_USER was added to the gpio group.${NC}"
    echo -e "${YELLOW}You'll need to log out and log back in for GPIO access to work.${NC}"
    echo ""
fi
