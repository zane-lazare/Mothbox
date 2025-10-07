#!/bin/bash
# ==============================================================================
# Mothbox System Packages Installation
# ==============================================================================
#
# Installs required system packages via apt for Mothbox operation.
# This script should be run as part of the main installation process.
#
# ==============================================================================

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing system packages...${NC}"

# Update package lists
echo -e "${BLUE}Updating package lists...${NC}"
sudo apt-get update

# Install required packages
echo -e "${BLUE}Installing required packages...${NC}"
sudo apt-get install -y \
    python3-pip \
    python3-picamera2 \
    python3-rpi-lgpio \
    python3-pil \
    git \
    i2c-tools

echo -e "${GREEN}✓ System packages installed successfully${NC}"
