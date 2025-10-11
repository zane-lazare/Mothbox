#!/bin/bash
# ==============================================================================
# Mothbox Update Script
# ==============================================================================
#
# This script updates Mothbox by pulling the latest changes from git and
# selectively reinstalling only the components that have changed.
#
# Features:
#   - Detects installation type (legacy, production, custom)
#   - Tracks last processed commit to avoid re-processing after manual pulls
#   - Syncs files to installation directory for production installs
#   - Selectively updates only changed components
#   - Updates systemd service files when templates change
#   - Verifies installation health (builds, dependencies, services)
#   - Rebuilds Web UI frontend when needed
#   - Restarts services automatically
#
# Usage:
#   This script MUST be run from the git repository, not the installation directory.
#   For production installs, keep the source repo and run updates from there.
#
#   cd /path/to/mothbox-repo
#   ./Firmware/update_mothbox.sh                    # Interactive update
#   ./Firmware/update_mothbox.sh --yes              # Auto-confirm all prompts
#   ./Firmware/update_mothbox.sh --dry-run          # Show what would be updated
#   ./Firmware/update_mothbox.sh --branch <name>    # Pull from specific branch
#   ./Firmware/update_mothbox.sh --force            # Reprocess current state
#   ./Firmware/update_mothbox.sh --verify           # Check installation health
#   ./Firmware/update_mothbox.sh --rebuild          # Force clean frontend rebuild
#
# ==============================================================================

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOTHBOX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect user
if [ -n "$SUDO_USER" ]; then
    MOTHBOX_USER="$SUDO_USER"
elif [ -n "$USER" ]; then
    MOTHBOX_USER="$USER"
else
    MOTHBOX_USER="pi"
fi

# Default values
DRY_RUN="false"
AUTO_YES="false"
TARGET_BRANCH=""
BACKUP_BEFORE_UPDATE="false"
FORCE_UPDATE="false"
VERIFY_ONLY="false"
SKIP_FILE_COPY="false"
FORCE_FRONTEND_REBUILD="false"

# Installation location variables (will be detected)
MOTHBOX_HOME=""
CONFIG_DIR=""
DATA_DIR=""
INSTALL_TYPE=""
FIRMWARE_VERSION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --yes|-y)
            AUTO_YES="true"
            shift
            ;;
        --branch|-b)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        --backup)
            BACKUP_BEFORE_UPDATE="true"
            shift
            ;;
        --force|-f)
            FORCE_UPDATE="true"
            shift
            ;;
        --verify)
            VERIFY_ONLY="true"
            shift
            ;;
        --skip-copy)
            SKIP_FILE_COPY="true"
            shift
            ;;
        --rebuild)
            FORCE_FRONTEND_REBUILD="true"
            shift
            ;;
        --help|-h)
            echo "Mothbox Update Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run         Show what would be updated without making changes"
            echo "  --yes, -y         Auto-confirm all prompts"
            echo "  --branch, -b NAME Pull from specific branch"
            echo "  --backup          Backup current installation before updating"
            echo "  --force, -f       Force reprocess updates even if no git changes"
            echo "  --verify          Check installation status without updating"
            echo "  --skip-copy       Skip copying files to installation (for testing)"
            echo "  --rebuild         Force clean rebuild of frontend (clears Vite cache)"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ==============================================================================
# Helper Functions
# ==============================================================================

# Detect installation location by checking for .installation_type marker
detect_installation() {
    # Check production install
    if [ -f "/opt/mothbox/.installation_type" ]; then
        MOTHBOX_HOME="/opt/mothbox"
        INSTALL_TYPE=$(cat /opt/mothbox/.installation_type)
        CONFIG_DIR="/etc/mothbox"
        DATA_DIR="/var/lib/mothbox"
        return 0
    fi

    # Check legacy install
    if [ -f "/home/pi/Desktop/Mothbox/.installation_type" ]; then
        MOTHBOX_HOME="/home/pi/Desktop/Mothbox"
        INSTALL_TYPE=$(cat /home/pi/Desktop/Mothbox/.installation_type)
        CONFIG_DIR="$MOTHBOX_HOME"
        DATA_DIR="$MOTHBOX_HOME"
        return 0
    fi

    # Check custom install via MOTHBOX_HOME env var
    if [ -n "$MOTHBOX_HOME" ] && [ -f "$MOTHBOX_HOME/.installation_type" ]; then
        INSTALL_TYPE=$(cat "$MOTHBOX_HOME/.installation_type")
        CONFIG_DIR="$MOTHBOX_HOME"
        DATA_DIR="$MOTHBOX_HOME"
        return 0
    fi

    # No installation found
    return 1
}

# Detect firmware version from controls.txt
detect_firmware_version() {
    # Try production path first, fallback to legacy firmware-version-specific path
    local controls_file
    if [ -f "$CONFIG_DIR/controls.txt" ]; then
        controls_file="$CONFIG_DIR/controls.txt"
    elif [ -f "$MOTHBOX_HOME/4.x/controls.txt" ]; then
        controls_file="$MOTHBOX_HOME/4.x/controls.txt"
    elif [ -f "$MOTHBOX_HOME/5.x/controls.txt" ]; then
        controls_file="$MOTHBOX_HOME/5.x/controls.txt"
    else
        controls_file="$CONFIG_DIR/controls.txt"  # fallback
    fi

    if [ -f "$controls_file" ]; then
        # Extract version from softwareversion=X.Y.Z
        local version=$(grep "^softwareversion=" "$controls_file" 2>/dev/null | cut -d= -f2 | cut -d. -f1)
        if [ -n "$version" ]; then
            FIRMWARE_VERSION="$version"
            return 0
        fi
    fi

    # Fallback: check which firmware directory exists in installation
    if [ -d "$MOTHBOX_HOME/5.x" ]; then
        FIRMWARE_VERSION="5"
        return 0
    elif [ -d "$MOTHBOX_HOME/4.x" ]; then
        FIRMWARE_VERSION="4"
        return 0
    fi

    # Last resort: detect from git repo
    if [ -d "$MOTHBOX_ROOT/Firmware/5.x" ]; then
        FIRMWARE_VERSION="5"
    else
        FIRMWARE_VERSION="4"
    fi

    echo -e "${YELLOW}Warning: Could not detect firmware version from config, assuming ${FIRMWARE_VERSION}.x${NC}" >&2
    return 1
}

# Read last processed commit from tracker file
get_last_update_commit() {
    local tracker_file="$CONFIG_DIR/.last_update_commit"
    if [ -f "$tracker_file" ]; then
        cat "$tracker_file"
    else
        echo ""
    fi
}

# Write current commit to tracker file
set_last_update_commit() {
    local commit="$1"
    local tracker_file="$CONFIG_DIR/.last_update_commit"
    echo "$commit" | sudo tee "$tracker_file" > /dev/null
    sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$tracker_file"
}

# Verify build and dependency status
verify_installation() {
    local issues=0

    echo -e "${BLUE}Verifying installation...${NC}"
    echo ""

    # Check if Web UI frontend is built
    if [ -d "$MOTHBOX_HOME/webui/frontend" ]; then
        if [ ! -d "$MOTHBOX_HOME/webui/frontend/dist" ] || [ ! -f "$MOTHBOX_HOME/webui/frontend/dist/index.html" ]; then
            echo -e "  ${YELLOW}⚠${NC} Web UI frontend not built (missing dist/)"
            issues=$((issues + 1))
        else
            echo -e "  ${GREEN}✓${NC} Web UI frontend built"
        fi

        # Check if node_modules exists (only critical for development)
        if [ ! -d "$MOTHBOX_HOME/webui/frontend/node_modules" ]; then
            if [ "$INSTALL_TYPE" = "production" ]; then
                # Production: node_modules optional, only needed for rebuilding
                echo -e "  ${CYAN}ℹ${NC} npm dependencies not installed (only needed for rebuilding frontend)"
            else
                # Legacy/development: node_modules should exist
                echo -e "  ${YELLOW}⚠${NC} npm dependencies not installed (missing node_modules/)"
                issues=$((issues + 1))
            fi
        else
            echo -e "  ${GREEN}✓${NC} npm dependencies installed"
        fi
    fi

    # Check if Python dependencies are installed (basic check)
    if ! python3 -c "import picamera2" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Python dependency 'picamera2' not found"
        issues=$((issues + 1))
    else
        echo -e "  ${GREEN}✓${NC} Core Python dependencies present"
    fi

    # Check systemd service status
    if [ -f "/etc/systemd/system/mothbox-webui.service" ]; then
        if systemctl is-enabled --quiet mothbox-webui.service 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Web UI service installed and enabled"

            if systemctl is-active --quiet mothbox-webui.service 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Web UI service running"
            else
                echo -e "  ${YELLOW}⚠${NC} Web UI service not running"
                issues=$((issues + 1))
            fi
        else
            echo -e "  ${YELLOW}⚠${NC} Web UI service installed but not enabled"
            issues=$((issues + 1))
        fi
    else
        echo -e "  ${CYAN}ℹ${NC} Web UI service not installed (optional)"
    fi

    echo ""

    if [ $issues -gt 0 ]; then
        echo -e "${YELLOW}Found $issues issue(s) that may need attention${NC}"
        return 1
    else
        echo -e "${GREEN}Installation verified successfully${NC}"
        return 0
    fi
}

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Update${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Detect installation location
echo -e "${BLUE}Detecting installation...${NC}"
if ! detect_installation; then
    echo -e "${RED}Error: No Mothbox installation found${NC}"
    echo ""
    echo "Checked locations:"
    echo "  • /opt/mothbox/.installation_type (production)"
    echo "  • /home/pi/Desktop/Mothbox/.installation_type (legacy)"
    echo "  • \$MOTHBOX_HOME/.installation_type (custom)"
    echo ""
    echo "Please install Mothbox first using install_mothbox.sh"
    exit 1
fi

echo -e "${GREEN}✓ Found $INSTALL_TYPE installation${NC}"
echo -e "${CYAN}Location:${NC} $MOTHBOX_HOME"

# Detect firmware version
detect_firmware_version
echo -e "${CYAN}Firmware version:${NC} ${FIRMWARE_VERSION}.x"
echo -e "${CYAN}Config directory:${NC} $CONFIG_DIR"
echo ""

# Handle --verify mode
if [ "$VERIFY_ONLY" = "true" ]; then
    verify_installation
    exit $?
fi

# Check if we're in a git repository
if ! git -C "$MOTHBOX_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: This script must be run from the Mothbox git repository${NC}"
    echo ""
    echo "Current location: $MOTHBOX_ROOT"
    echo ""
    echo "This script requires the Mothbox source repository to function properly."
    echo "If you have a production install, you need to:"
    echo "  1. Keep the git repository where you cloned it"
    echo "  2. Run this script from that repository location"
    echo ""
    echo "Example:"
    echo "  cd /path/to/mothbox-repo"
    echo "  ./Firmware/update_mothbox.sh"
    exit 1
fi

cd "$MOTHBOX_ROOT"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}Warning: You have uncommitted changes in your working directory${NC}"
    if [ "$AUTO_YES" = "false" ] && [ "$DRY_RUN" = "false" ]; then
        read -p "Continue anyway? These changes may be lost. [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Update cancelled${NC}"
            exit 1
        fi
    fi
fi

# Get current branch and commit
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse HEAD)
CURRENT_COMMIT_SHORT=$(git rev-parse --short HEAD)

echo -e "${CYAN}Current branch:${NC} $CURRENT_BRANCH"
echo -e "${CYAN}Current commit:${NC} $CURRENT_COMMIT_SHORT"
echo ""

# Determine target branch
if [ -z "$TARGET_BRANCH" ]; then
    TARGET_BRANCH="$CURRENT_BRANCH"
fi

echo -e "${BLUE}Fetching updates from origin/$TARGET_BRANCH...${NC}"

if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}[DRY RUN] Would fetch from origin${NC}"
    git fetch origin "$TARGET_BRANCH" --dry-run
else
    git fetch origin "$TARGET_BRANCH"
fi

# Get last processed commit from installation
LAST_PROCESSED_COMMIT=$(get_last_update_commit)

# Check if updates are available
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse "origin/$TARGET_BRANCH")

# Determine the base commit for comparison
if [ "$FORCE_UPDATE" = "true" ]; then
    # Force mode: compare against remote (will show all differences)
    BASE_COMMIT="$REMOTE_COMMIT"
    COMPARE_COMMIT="$LOCAL_COMMIT"
    echo -e "${YELLOW}Force mode: Reprocessing current state${NC}"
    echo ""
elif [ -n "$LAST_PROCESSED_COMMIT" ]; then
    # Normal mode with tracker: compare against last processed commit
    BASE_COMMIT="$LAST_PROCESSED_COMMIT"
    COMPARE_COMMIT="$LOCAL_COMMIT"
    echo -e "${CYAN}Last processed commit:${NC} $(git rev-parse --short "$LAST_PROCESSED_COMMIT" 2>/dev/null || echo "invalid")"

    # Check if last processed commit is valid
    if ! git rev-parse "$LAST_PROCESSED_COMMIT" >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Stored commit no longer exists in git history${NC}"
        echo -e "${YELLOW}Comparing against remote instead${NC}"
        BASE_COMMIT="$REMOTE_COMMIT"
    fi
else
    # First run: compare against initial commit to process all current files
    BASE_COMMIT=$(git rev-list --max-parents=0 HEAD)
    COMPARE_COMMIT="$LOCAL_COMMIT"
    echo -e "${CYAN}First update run (no tracker file found)${NC}"
    echo -e "${CYAN}Will process all current files to set up installation${NC}"
fi

# Check if git pull is needed
if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo -e "${YELLOW}Git updates available!${NC}"
    echo -e "${CYAN}Remote commit:${NC} $(git rev-parse --short origin/$TARGET_BRANCH)"
    NEED_GIT_PULL="true"
else
    echo -e "${GREEN}Git repository up to date${NC}"
    NEED_GIT_PULL="false"
fi

# Pull updates from git BEFORE checking if processing is needed
# This ensures we compare against the latest code
if [ "$NEED_GIT_PULL" = "true" ]; then
    if [ "$DRY_RUN" = "true" ]; then
        echo -e "${YELLOW}[DRY RUN] Would run: git pull origin $TARGET_BRANCH${NC}"
    else
        echo -e "${BLUE}Pulling updates from git...${NC}"
        git pull origin "$TARGET_BRANCH"
        echo -e "${GREEN}✓ Git updates pulled${NC}"

        # Update COMPARE_COMMIT to new HEAD after pull
        COMPARE_COMMIT=$(git rev-parse HEAD)
        echo ""
    fi
fi

# Check if processing is needed (now comparing against pulled code)
if [ "$BASE_COMMIT" = "$COMPARE_COMMIT" ] && [ "$FORCE_UPDATE" = "false" ]; then
    echo -e "${GREEN}✓ No updates to process!${NC}"
    echo ""

    # Still verify installation health
    verify_installation

    exit 0
fi

echo ""

# Show what will be updated (changes between base and current)
echo -e "${BLUE}Changes to process:${NC}"
git --no-pager diff --name-status "$BASE_COMMIT..$COMPARE_COMMIT" | head -20
echo ""

TOTAL_CHANGES=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | wc -l)
if [ "$TOTAL_CHANGES" -gt 20 ]; then
    echo -e "${CYAN}... and $(($TOTAL_CHANGES - 20)) more files${NC}"
    echo ""
fi

# Categorize changes
FIRMWARE_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '^Firmware/.*\.py$' | wc -l)
WEBUI_BACKEND_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '^Firmware/webui/backend/' | wc -l)
WEBUI_FRONTEND_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '^Firmware/webui/frontend/' | wc -l)
# Also rebuild frontend if backend config or dependencies changed (may affect CSRF, CORS, API behavior)
BACKEND_CONFIG_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '^Firmware/webui/backend/(config\.py|requirements\.txt)$' | wc -l)
INSTALLER_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '^Firmware/install.*\.sh$|^Firmware/installation-utils/' | wc -l)
SERVICE_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '\.service\.template$' | wc -l)
CONFIG_CHANGED=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E 'controls\.txt$|camera_settings\.csv$|schedule_settings\.csv$|wordlist\.csv$' | wc -l)

echo -e "${CYAN}Components affected:${NC}"
[ "$FIRMWARE_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Firmware Python scripts ($FIRMWARE_CHANGED files)"
[ "$WEBUI_BACKEND_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Web UI backend ($WEBUI_BACKEND_CHANGED files)"
[ "$WEBUI_FRONTEND_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Web UI frontend ($WEBUI_FRONTEND_CHANGED files)"
[ "$BACKEND_CONFIG_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Backend config/dependencies ($BACKEND_CONFIG_CHANGED files) - requires frontend rebuild"
[ "$SERVICE_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Systemd service files ($SERVICE_CHANGED files)"
[ "$INSTALLER_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Installer scripts ($INSTALLER_CHANGED files)"
[ "$CONFIG_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Configuration files ($CONFIG_CHANGED files)"
echo ""

# Confirm update
if [ "$AUTO_YES" = "false" ] && [ "$DRY_RUN" = "false" ]; then
    read -p "Proceed with update? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Update cancelled${NC}"
        exit 1
    fi
    echo ""
fi

# Backup if requested
if [ "$BACKUP_BEFORE_UPDATE" = "true" ] && [ "$DRY_RUN" = "false" ]; then
    BACKUP_DIR="/tmp/mothbox-backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${BLUE}Creating backup at $BACKUP_DIR...${NC}"
    mkdir -p "$BACKUP_DIR"
    cp -r "$MOTHBOX_ROOT" "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup created${NC}"
    echo ""
fi

# Git pull already happened earlier (before processing check)
NEW_COMMIT_SHORT=$(git rev-parse --short HEAD)

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo -e "${YELLOW}[DRY RUN] Update complete - no changes made${NC}"
    exit 0
fi

# Copy files to installation location (for production installs)
if [ "$INSTALL_TYPE" = "production" ] && [ "$SKIP_FILE_COPY" = "false" ]; then
    echo -e "${BLUE}Syncing files to installation directory...${NC}"

    # Copy firmware-version-specific files to root of installation
    echo "Copying ${FIRMWARE_VERSION}.x firmware files..."
    sudo rsync -av \
        --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='node_modules' --exclude='.DS_Store' \
        "$MOTHBOX_ROOT/Firmware/${FIRMWARE_VERSION}.x/" "$MOTHBOX_HOME/"

    # Copy common files (mothbox_paths.py, etc.)
    echo "Copying common files..."
    sudo rsync -av \
        --exclude='__pycache__' --exclude='*.pyc' \
        "$MOTHBOX_ROOT/Firmware/mothbox_paths.py" "$MOTHBOX_HOME/"

    # Copy Web UI (if it exists)
    if [ -d "$MOTHBOX_ROOT/Firmware/webui" ]; then
        echo "Copying Web UI..."
        sudo rsync -av \
            --exclude='__pycache__' --exclude='*.pyc' \
            --exclude='node_modules' --exclude='.DS_Store' \
            "$MOTHBOX_ROOT/Firmware/webui/" "$MOTHBOX_HOME/webui/"
    fi

    # Note: We do NOT copy update_mothbox.sh to installation directory
    # The update script must always be run from the source git repository

    # Preserve critical files (don't delete during sync)
    # Create .installation_type if it doesn't exist
    if [ ! -f "$MOTHBOX_HOME/.installation_type" ]; then
        echo "$INSTALL_TYPE" | sudo tee "$MOTHBOX_HOME/.installation_type" > /dev/null
    fi

    # Set proper ownership
    sudo chown -R $MOTHBOX_USER:$MOTHBOX_USER "$MOTHBOX_HOME"

    echo -e "${GREEN}✓ Files synced to $MOTHBOX_HOME${NC}"
    echo ""
elif [ "$INSTALL_TYPE" = "legacy" ]; then
    # For legacy installs, git repo IS the installation - no copying needed
    echo -e "${CYAN}Legacy install detected - files already in place${NC}"
    echo ""
fi

# Update components based on what changed
UPDATES_PERFORMED=0

# Update firmware Python scripts permissions
if [ "$FIRMWARE_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating firmware script permissions...${NC}"
    find "$MOTHBOX_HOME" -name "*.py" -exec chmod +x {} \;
    echo -e "${GREEN}✓ Firmware permissions updated${NC}"
    UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
    echo ""
fi

# Update Web UI backend
if [ "$WEBUI_BACKEND_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating Web UI backend...${NC}"

    # Check if requirements changed
    if git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -q "webui/backend/requirements.txt"; then
        echo "Reinstalling Python dependencies..."
        if [ -f "$MOTHBOX_ROOT/Firmware/webui/backend/requirements.txt" ]; then
            # Use constraints file to prevent installation of conflicting packages
            sudo -u "$MOTHBOX_USER" pip3 install --break-system-packages \
                -c "$MOTHBOX_ROOT/Firmware/installation-utils/pip-constraints.txt" \
                -r "$MOTHBOX_ROOT/Firmware/webui/backend/requirements.txt"
        fi
    fi

    # Ensure GPIO compatibility after backend updates
    echo "Ensuring GPIO compatibility..."
    pip3 uninstall -y --break-system-packages RPi.GPIO 2>/dev/null || true
    sudo rm -rf /usr/local/lib/python3.*/dist-packages/RPi/ 2>/dev/null || true

    echo -e "${GREEN}✓ Web UI backend updated${NC}"
    UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
    echo ""
fi

# Rebuild Web UI frontend if frontend files OR critical backend config changed OR --rebuild flag
if [ "$WEBUI_FRONTEND_CHANGED" -gt 0 ] || [ "$BACKEND_CONFIG_CHANGED" -gt 0 ] || [ "$FORCE_FRONTEND_REBUILD" = "true" ]; then
    echo -e "${BLUE}Rebuilding Web UI frontend...${NC}"

    # Explain why we're rebuilding
    if [ "$FORCE_FRONTEND_REBUILD" = "true" ]; then
        echo "Force rebuild requested - performing clean build"
    elif [ "$BACKEND_CONFIG_CHANGED" -gt 0 ] && [ "$WEBUI_FRONTEND_CHANGED" -eq 0 ]; then
        echo "Backend configuration changed - rebuilding frontend to ensure compatibility"
    fi

    if [ -d "$MOTHBOX_HOME/webui/frontend" ]; then
        cd "$MOTHBOX_HOME/webui/frontend"

        # Check if we need to install/reinstall npm dependencies
        # Install if: node_modules missing OR package.json/package-lock.json changed
        if [ ! -d "node_modules" ]; then
            echo "Installing npm dependencies (node_modules not found)..."
            sudo -u "$MOTHBOX_USER" npm install
        elif git -C "$MOTHBOX_ROOT" diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" 2>/dev/null | grep -q "webui/frontend/package"; then
            echo "Reinstalling npm dependencies (package files changed)..."
            sudo -u "$MOTHBOX_USER" npm install
        fi

        # Clean build to avoid Vite caching issues with incremental builds
        echo "Cleaning previous build artifacts and Vite cache..."
        rm -rf dist
        rm -rf node_modules/.vite

        echo "Building production frontend..."
        sudo -u "$MOTHBOX_USER" npm run build
        echo -e "${GREEN}✓ Web UI frontend rebuilt${NC}"
        UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))

        # Return to original directory
        cd "$MOTHBOX_ROOT"
    else
        echo -e "${YELLOW}⚠ Web UI frontend directory not found, skipping${NC}"
    fi
    echo ""
fi

# Ensure node_modules exists in production installs for development/testing
# This allows frontend rebuilds without having to maintain source directory
if [ "$INSTALL_TYPE" = "production" ] && [ -d "$MOTHBOX_HOME/webui/frontend" ]; then
    if [ ! -d "$MOTHBOX_HOME/webui/frontend/node_modules" ]; then
        echo -e "${BLUE}Installing npm dependencies in production location...${NC}"
        echo "This enables frontend rebuilds for development/testing"
        cd "$MOTHBOX_HOME/webui/frontend"
        sudo -u "$MOTHBOX_USER" npm install
        echo -e "${GREEN}✓ npm dependencies installed${NC}"
        cd "$MOTHBOX_ROOT"
        echo ""
    fi
fi

# Update systemd service files if changed
if [ "$SERVICE_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating systemd service files...${NC}"

    # Update Web UI service if template changed
    if git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -q "mothbox-webui.service.template"; then
        SERVICE_TEMPLATE="$MOTHBOX_ROOT/Firmware/installation-utils/mothbox-webui.service.template"

        if [ -f "$SERVICE_TEMPLATE" ]; then
            echo "Regenerating mothbox-webui.service..."

            # Detect MOTHBOX_ENV from existing service or default to development
            MOTHBOX_ENV="development"
            if [ -f "/etc/systemd/system/mothbox-webui.service" ]; then
                MOTHBOX_ENV=$(grep "^Environment=\"MOTHBOX_ENV=" /etc/systemd/system/mothbox-webui.service | cut -d= -f3 | tr -d '"' || echo "development")
            fi

            # Detect ALLOWED_ORIGINS from existing service or default to empty (same-origin only)
            ALLOWED_ORIGINS=""
            if [ -f "/etc/systemd/system/mothbox-webui.service" ]; then
                # Extract ALLOWED_ORIGINS value, handling the format: Environment="ALLOWED_ORIGINS=value"
                ALLOWED_ORIGINS=$(grep "^Environment=\"ALLOWED_ORIGINS=" /etc/systemd/system/mothbox-webui.service | sed 's/^Environment="ALLOWED_ORIGINS=//' | sed 's/"$//' || echo "")
            fi

            # Fix old wildcard patterns that don't work with Flask-SocketIO
            # Flask-SocketIO only supports '*' (all origins) or specific origin lists
            # Patterns like http://192.168.*.*:* or http://localhost:* don't work
            if [[ "$ALLOWED_ORIGINS" == *"*.*"* ]] || [[ "$ALLOWED_ORIGINS" == *":*"* ]]; then
                echo "  Detected invalid wildcard patterns in ALLOWED_ORIGINS"
                echo "  Flask-SocketIO doesn't support shell-style wildcards"
                echo "  Converting to '*' (allow all origins)"
                ALLOWED_ORIGINS="*"
            fi

            echo "Preserving configuration:"
            echo "  Environment: $MOTHBOX_ENV"
            echo "  CORS Origins: ${ALLOWED_ORIGINS:-same-origin only}"

            # Generate service file with substitutions
            # Use mktemp for secure temporary file creation (prevents TOCTOU race conditions)
            TEMP_SERVICE=$(mktemp)
            sed -e "s|__MOTHBOX_USER__|$MOTHBOX_USER|g" \
                -e "s|__MOTHBOX_HOME__|$MOTHBOX_HOME|g" \
                -e "s|__MOTHBOX_ENV__|$MOTHBOX_ENV|g" \
                -e "s|__ALLOWED_ORIGINS__|$ALLOWED_ORIGINS|g" \
                "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"

            # Install service file
            sudo mv "$TEMP_SERVICE" /etc/systemd/system/mothbox-webui.service
            sudo systemctl daemon-reload

            echo -e "${GREEN}✓ Service file updated and daemon reloaded${NC}"
            UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
        else
            echo -e "${YELLOW}⚠ Service template not found, skipping${NC}"
        fi
    fi
    echo ""
fi

# Warn about config changes
if [ "$CONFIG_CHANGED" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Configuration files changed${NC}"
    echo "The following config files were updated:"
    git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | grep -E '\.csv$|\.txt$' | grep -v 'webui/frontend' | grep -v '.template$' | sed 's/^/  • /'
    echo ""
    echo -e "${YELLOW}Note: Your existing configuration has been preserved${NC}"
    echo "Review the changes and update your config if needed"
    echo ""
fi

# Restart services if Web UI was updated or service file changed
if [ "$WEBUI_BACKEND_CHANGED" -gt 0 ] || [ "$WEBUI_FRONTEND_CHANGED" -gt 0 ] || [ "$SERVICE_CHANGED" -gt 0 ]; then
    if systemctl is-active --quiet mothbox-webui.service 2>/dev/null; then
        echo -e "${BLUE}Restarting Web UI service...${NC}"
        sudo systemctl restart mothbox-webui.service

        sleep 2
        if systemctl is-active --quiet mothbox-webui.service; then
            echo -e "${GREEN}✓ Service restarted successfully${NC}"
        else
            echo -e "${RED}✗ Service failed to restart${NC}"
            echo "Check logs: sudo journalctl -u mothbox-webui.service -n 50"
        fi
        echo ""
    elif [ "$SERVICE_CHANGED" -gt 0 ]; then
        echo -e "${YELLOW}Service file updated but service not running${NC}"
        echo "Start it with: sudo systemctl start mothbox-webui.service"
        echo ""
    fi
fi

# Update tracker file with current commit
FINAL_COMMIT=$(git rev-parse HEAD)
set_last_update_commit "$FINAL_COMMIT"
echo -e "${BLUE}Updated tracker file${NC}"
echo -e "${CYAN}Last processed commit set to:${NC} $(git rev-parse --short HEAD)"
echo ""

# Summary
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""

if [ -n "$LAST_PROCESSED_COMMIT" ] && [ "$LAST_PROCESSED_COMMIT" != "$FINAL_COMMIT" ]; then
    echo -e "${CYAN}Processed commits:${NC} $(git rev-parse --short "$LAST_PROCESSED_COMMIT" 2>/dev/null || echo "none")..$(git rev-parse --short HEAD)"
else
    echo -e "${CYAN}Current commit:${NC} $(git rev-parse --short HEAD)"
fi
echo -e "${CYAN}Branch:${NC} $TARGET_BRANCH"
echo -e "${CYAN}Installation:${NC} $INSTALL_TYPE ($MOTHBOX_HOME)"
echo ""

if [ "$UPDATES_PERFORMED" -gt 0 ]; then
    echo -e "${GREEN}✓ $UPDATES_PERFORMED component(s) updated${NC}"
else
    echo -e "${YELLOW}No component updates required${NC}"
fi

echo ""
if [ -n "$LAST_PROCESSED_COMMIT" ]; then
    echo -e "${BLUE}View changes:${NC} git log $(git rev-parse --short "$LAST_PROCESSED_COMMIT" 2>/dev/null || echo "$CURRENT_COMMIT_SHORT")..$(git rev-parse --short HEAD) --oneline"
fi
echo ""
