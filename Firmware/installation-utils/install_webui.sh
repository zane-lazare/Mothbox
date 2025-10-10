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

# Ask for installation type
echo -e "${BLUE}Select installation type:${NC}"
echo "  1) Development (recommended for testing - enables debug mode)"
echo "  2) Production (for deployment - requires gunicorn, not yet implemented)"
echo ""
read -p "Enter choice [1-2] (default: 1): " INSTALL_TYPE
INSTALL_TYPE=${INSTALL_TYPE:-1}

if [ "$INSTALL_TYPE" = "1" ]; then
    MOTHBOX_ENV="development"
    echo -e "${GREEN}Installing in DEVELOPMENT mode${NC}"
    echo -e "${YELLOW}Note: Development mode enables debug logging and verbose error messages${NC}"
elif [ "$INSTALL_TYPE" = "2" ]; then
    MOTHBOX_ENV="production"
    echo -e "${YELLOW}WARNING: Production mode is not yet fully implemented!${NC}"
    echo -e "${YELLOW}Production mode currently uses Werkzeug development server (not recommended)${NC}"
    echo -e "${YELLOW}For production deployment, wait for gunicorn implementation (issue #19)${NC}"
    echo ""
    read -p "Continue with production mode anyway? [y/N]: " CONFIRM_PROD
    if [[ ! "$CONFIRM_PROD" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation cancelled${NC}"
        exit 1
    fi
else
    echo -e "${RED}Invalid choice. Exiting.${NC}"
    exit 1
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
if sudo -u $MOTHBOX_USER pip3 install --break-system-packages Flask==3.0.0 Flask-CORS==4.0.0 Flask-SocketIO==5.3.6 Flask-WTF==1.2.1 python-socketio==5.11.0; then
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install Python dependencies${NC}"
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

# Install systemd service
echo -e "${BLUE}Installing systemd service...${NC}"
SERVICE_TEMPLATE="$SCRIPT_DIR/mothbox-webui.service.template"

if [ ! -f "$SERVICE_TEMPLATE" ]; then
    echo -e "${YELLOW}Warning: mothbox-webui.service.template not found, skipping service installation${NC}"
else
    # Generate service file from template with actual values
    echo "Generating service file from template..."
    sudo sed -e "s|__MOTHBOX_USER__|$MOTHBOX_USER|g" \
             -e "s|__MOTHBOX_HOME__|$MOTHBOX_HOME|g" \
             -e "s|__MOTHBOX_ENV__|$MOTHBOX_ENV|g" \
             "$SERVICE_TEMPLATE" > /tmp/mothbox-webui.service

    # Install the generated service file
    sudo mv /tmp/mothbox-webui.service /etc/systemd/system/mothbox-webui.service
    sudo systemctl daemon-reload
    sudo systemctl enable mothbox-webui.service
    echo -e "${GREEN}✓ Systemd service installed and enabled${NC}"
    echo -e "${GREEN}  User: $MOTHBOX_USER${NC}"
    echo -e "${GREEN}  Path: $MOTHBOX_HOME${NC}"
    echo -e "${GREEN}  Environment: $MOTHBOX_ENV${NC}"

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
