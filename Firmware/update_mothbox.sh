#!/bin/bash
# ==============================================================================
# Mothbox Update Script
# ==============================================================================
#
# This script updates Mothbox by pulling the latest changes from git and
# selectively reinstalling only the components that have changed.
#
# Usage:
#   ./update_mothbox.sh                    # Interactive update
#   ./update_mothbox.sh --yes              # Auto-confirm all prompts
#   ./update_mothbox.sh --dry-run          # Show what would be updated
#   ./update_mothbox.sh --branch <name>    # Pull from specific branch
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

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Mothbox Update${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

# Check if we're in a git repository
if ! git -C "$MOTHBOX_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo "This update script requires Mothbox to be installed from git"
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

# Check if updates are available
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse "origin/$TARGET_BRANCH")

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo -e "${GREEN}✓ Already up to date!${NC}"
    echo "No updates available"
    exit 0
fi

echo ""
echo -e "${YELLOW}Updates available!${NC}"
echo -e "${CYAN}Remote commit:${NC} $(git rev-parse --short origin/$TARGET_BRANCH)"
echo ""

# Show what will be updated
echo -e "${BLUE}Changed files:${NC}"
git --no-pager diff --name-status "$LOCAL_COMMIT..$REMOTE_COMMIT" | head -20
echo ""

TOTAL_CHANGES=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | wc -l)
if [ "$TOTAL_CHANGES" -gt 20 ]; then
    echo -e "${CYAN}... and $(($TOTAL_CHANGES - 20)) more files${NC}"
    echo ""
fi

# Categorize changes
FIRMWARE_CHANGED=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | grep -E '^Firmware/.*\.py$' | wc -l)
WEBUI_BACKEND_CHANGED=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | grep -E '^Firmware/webui/backend/' | wc -l)
WEBUI_FRONTEND_CHANGED=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | grep -E '^Firmware/webui/frontend/' | wc -l)
INSTALLER_CHANGED=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | grep -E '^Firmware/install.*\.sh$|^Firmware/installation-utils/' | wc -l)
CONFIG_CHANGED=$(git diff --name-only "$LOCAL_COMMIT..$REMOTE_COMMIT" | grep -E '\.csv$|\.txt$|\.template$' | grep -v 'webui/frontend' | wc -l)

echo -e "${CYAN}Components affected:${NC}"
[ "$FIRMWARE_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Firmware Python scripts ($FIRMWARE_CHANGED files)"
[ "$WEBUI_BACKEND_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Web UI backend ($WEBUI_BACKEND_CHANGED files)"
[ "$WEBUI_FRONTEND_CHANGED" -gt 0 ] && echo -e "  ${YELLOW}•${NC} Web UI frontend ($WEBUI_FRONTEND_CHANGED files)"
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

# Pull updates
if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}[DRY RUN] Would run: git pull origin $TARGET_BRANCH${NC}"
else
    echo -e "${BLUE}Pulling updates...${NC}"
    git pull origin "$TARGET_BRANCH"
    echo -e "${GREEN}✓ Updates pulled${NC}"
    echo ""
fi

NEW_COMMIT_SHORT=$(git rev-parse --short HEAD)

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo -e "${YELLOW}[DRY RUN] Update complete - no changes made${NC}"
    exit 0
fi

# Update components based on what changed
UPDATES_PERFORMED=0

# Update firmware Python scripts permissions
if [ "$FIRMWARE_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating firmware script permissions...${NC}"
    find "$MOTHBOX_ROOT/Firmware" -name "*.py" -exec chmod +x {} \;
    echo -e "${GREEN}✓ Firmware permissions updated${NC}"
    UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
    echo ""
fi

# Update Web UI backend
if [ "$WEBUI_BACKEND_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating Web UI backend...${NC}"

    # Check if requirements changed
    if git diff --name-only "$CURRENT_COMMIT..HEAD" | grep -q "requirements.txt\|setup.py"; then
        echo "Reinstalling Python dependencies..."
        sudo -u "$MOTHBOX_USER" pip3 install --break-system-packages -r "$MOTHBOX_ROOT/Firmware/webui/backend/requirements.txt" 2>/dev/null || true
    fi

    echo -e "${GREEN}✓ Web UI backend updated${NC}"
    UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
    echo ""
fi

# Rebuild Web UI frontend
if [ "$WEBUI_FRONTEND_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Rebuilding Web UI frontend...${NC}"
    cd "$MOTHBOX_ROOT/Firmware/webui/frontend"

    # Check if package.json changed (need to reinstall deps)
    if git diff --name-only "$CURRENT_COMMIT..HEAD" | grep -q "package.json"; then
        echo "Reinstalling npm dependencies..."
        sudo -u "$MOTHBOX_USER" npm install
    fi

    echo "Building production frontend..."
    sudo -u "$MOTHBOX_USER" npm run build
    echo -e "${GREEN}✓ Web UI frontend rebuilt${NC}"
    UPDATES_PERFORMED=$((UPDATES_PERFORMED + 1))
    echo ""
fi

# Warn about config changes
if [ "$CONFIG_CHANGED" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Configuration files changed${NC}"
    echo "The following config files were updated:"
    git diff --name-only "$CURRENT_COMMIT..HEAD" | grep -E '\.csv$|\.txt$|\.template$' | grep -v 'webui/frontend' | sed 's/^/  • /'
    echo ""
    echo -e "${YELLOW}Note: Your existing configuration has been preserved${NC}"
    echo "Review the changes and update your config if needed"
    echo ""
fi

# Restart services if Web UI was updated
if [ "$WEBUI_BACKEND_CHANGED" -gt 0 ] || [ "$WEBUI_FRONTEND_CHANGED" -gt 0 ]; then
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
    fi
fi

# Summary
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
echo -e "${CYAN}Updated from:${NC} $CURRENT_COMMIT_SHORT"
echo -e "${CYAN}Updated to:${NC}   $NEW_COMMIT_SHORT"
echo -e "${CYAN}Branch:${NC}       $TARGET_BRANCH"
echo ""

if [ "$UPDATES_PERFORMED" -gt 0 ]; then
    echo -e "${GREEN}✓ $UPDATES_PERFORMED component(s) updated${NC}"
else
    echo -e "${YELLOW}No component updates required${NC}"
fi

echo ""
echo -e "${BLUE}View changes:${NC} git log $CURRENT_COMMIT_SHORT..$NEW_COMMIT_SHORT --oneline"
echo ""
