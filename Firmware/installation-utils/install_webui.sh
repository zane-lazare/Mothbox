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

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Web UI Installation${NC}"
echo -e "${BLUE}================================================================================${NC}"
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
if pip3 install --break-system-packages Flask==3.0.0 Flask-CORS==4.0.0 Flask-SocketIO==5.3.6 python-socketio==5.11.0; then
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
if npm install; then
    echo -e "${GREEN}✓ npm dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install npm dependencies${NC}"
    exit 1
fi

echo "Building production frontend..."
if npm run build; then
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
SERVICE_FILE="$SCRIPT_DIR/mothbox-webui.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}Warning: mothbox-webui.service not found, skipping service installation${NC}"
else
    sudo cp "$SERVICE_FILE" /etc/systemd/system/
    sudo systemctl daemon-reload

    # Enable but don't start yet (user can start manually)
    sudo systemctl enable mothbox-webui.service
    echo -e "${GREEN}✓ Systemd service installed and enabled${NC}"
    echo -e "${YELLOW}To start the service: sudo systemctl start mothbox-webui${NC}"
fi
echo ""

echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Web UI Installation Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
echo -e "${BLUE}To start the Web UI manually:${NC}"
echo "  cd $SCRIPT_DIR/../webui/backend"
echo "  python3 app.py"
echo ""
echo -e "${BLUE}To start the Web UI service:${NC}"
echo "  sudo systemctl start mothbox-webui"
echo ""
echo -e "${BLUE}To access the Web UI:${NC}"
echo "  Local: http://localhost:5000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo -e "${YELLOW}Note: If you added $MOTHBOX_USER to the gpio group for the first time,${NC}"
echo -e "${YELLOW}you'll need to log out and log back in for the changes to take effect.${NC}"
echo ""
