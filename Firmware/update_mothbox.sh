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

# Ensure memory tuning is applied (for existing installations)
ensure_memory_tuning() {
    SYSCTL_FILE="/etc/sysctl.d/99-mothbox-memory.conf"

    # Only apply on Pi 5 with fake NUMA
    if grep -q "numa=fake" /proc/cmdline 2>/dev/null; then
        if [ ! -f "$SYSCTL_FILE" ]; then
            echo -e "${YELLOW}Applying memory tuning for Pi 5...${NC}"

            sudo tee "$SYSCTL_FILE" > /dev/null <<EOF
# Mothbox memory tuning for Raspberry Pi 5
# Disables watermark boost to prevent OOM during photo capture
# See: https://github.com/zane-lazare/Mothbox/issues/393

vm.watermark_boost_factor = 0
EOF

            sudo sysctl -p "$SYSCTL_FILE" > /dev/null
            echo -e "${GREEN}✓ Memory tuning configured${NC}"
        else
            echo -e "${GREEN}✓ Memory tuning already configured${NC}"
        fi
    fi
}

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
FIX_PERMISSIONS="false"
DEBUG_MODE="false"

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
        --fix-permissions)
            FIX_PERMISSIONS="true"
            shift
            ;;
        --debug)
            DEBUG_MODE="true"
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
            echo "  --fix-permissions Fix repository ownership issues before updating"
            echo "  --debug           Enable verbose diagnostic output for troubleshooting"
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

# Verify file sync status between repo and installation
verify_file_sync() {
    # Use rsync dry-run with checksums to detect file drift
    # Returns 0 if sync needed, 1 if already in sync

    local files_differ=false
    local sync_check_file="/tmp/mothbox_sync_check_$$"
    local debug_file="/tmp/mothbox_sync_debug_$$"

    # Debug: Show sync configuration
    if [ "$DEBUG_MODE" = "true" ]; then
        echo -e "${CYAN}[DEBUG] File sync check: ${FIRMWARE_VERSION}.x (excluding ${exclude_firmware:-none})${NC}" >&2
    fi

    # Determine which firmware version to exclude
    local exclude_firmware
    if [ "$FIRMWARE_VERSION" = "4" ]; then
        exclude_firmware="5.x"
    else
        exclude_firmware="4.x"
    fi

    # Check the entire Firmware directory (matching rsync copy behavior)
    local source="$MOTHBOX_ROOT/Firmware/"
    local dest="$MOTHBOX_HOME/"

    if [ ! -e "$source" ]; then
        [ "$DEBUG_MODE" = "true" ] && echo -e "${RED}[DEBUG] Source directory not found: $source${NC}" >&2
        return 1
    fi

    # Debug mode shows detailed rsync output below

    # Run rsync dry-run with checksums to detect differences
    # Use same exclusions as actual sync operation
    local rsync_output_file="/tmp/mothbox_rsync_output_$$"
    local rsync_err_file="/tmp/mothbox_rsync_err_$$"

    if [ "$INSTALL_TYPE" = "production" ]; then
        if [ "$DEBUG_MODE" = "true" ]; then
            # Debug mode: capture full output including errors
            sudo rsync --dry-run --checksum --itemize-changes --archive \
                  --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
                  --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
                  --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
                  --exclude='installation-utils' --exclude='migrate_*.py' \
                  --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
                  --exclude='*.md' \
                  --exclude='Tests' \
                  --exclude="$exclude_firmware" \
                  "$source" "$dest" > "$rsync_output_file" 2> "$rsync_err_file"
            local rsync_exit=$?

            # Filter and save differences
            grep -E '^[^.]' "$rsync_output_file" >> "$sync_check_file"
            local diff_count=$(grep -E '^[^.]' "$rsync_output_file" | wc -l)

            echo -e "${CYAN}[DEBUG] Rsync check complete: $diff_count file(s) differ${NC}" >&2
            if [ "$diff_count" -gt 0 ] && [ "$diff_count" -le 10 ]; then
                echo -e "${CYAN}[DEBUG] Changed files:${NC}" >&2
                grep -E '^[^.]' "$rsync_output_file" | sed 's/^/  /' >&2
            elif [ "$diff_count" -gt 10 ]; then
                echo -e "${CYAN}[DEBUG] First 10 changed files:${NC}" >&2
                grep -E '^[^.]' "$rsync_output_file" | head -10 | sed 's/^/  /' >&2
                echo "  ... and $(($diff_count - 10)) more" >&2
            fi

            if [ -s "$rsync_err_file" ]; then
                echo -e "${RED}[DEBUG] Rsync errors:${NC}" >&2
                cat "$rsync_err_file" | sed 's/^/  /' >&2
            fi
            echo "" >&2
        else
            # Normal mode: suppress errors
            sudo rsync --dry-run --checksum --itemize-changes --archive \
                  --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
                  --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
                  --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
                  --exclude='installation-utils' --exclude='migrate_*.py' \
                  --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
                  --exclude='*.md' \
                  --exclude='Tests' \
                  --exclude="$exclude_firmware" \
                  "$source" "$dest" 2>/dev/null | grep -E '^[^.]' >> "$sync_check_file"
        fi
    else
        if [ "$DEBUG_MODE" = "true" ]; then
            rsync --dry-run --checksum --itemize-changes --archive \
                  --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
                  --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
                  --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
                  --exclude='installation-utils' --exclude='migrate_*.py' \
                  --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
                  --exclude='*.md' \
                  --exclude='Tests' \
                  --exclude="$exclude_firmware" \
                  "$source" "$dest" > "$rsync_output_file" 2> "$rsync_err_file"
            local rsync_exit=$?

            # Filter and save differences
            grep -E '^[^.]' "$rsync_output_file" >> "$sync_check_file"
            local diff_count=$(grep -E '^[^.]' "$rsync_output_file" | wc -l)

            echo -e "${CYAN}[DEBUG] Rsync check complete: $diff_count file(s) differ${NC}" >&2
            if [ "$diff_count" -gt 0 ] && [ "$diff_count" -le 10 ]; then
                echo -e "${CYAN}[DEBUG] Changed files:${NC}" >&2
                grep -E '^[^.]' "$rsync_output_file" | sed 's/^/  /' >&2
            elif [ "$diff_count" -gt 10 ]; then
                echo -e "${CYAN}[DEBUG] First 10 changed files:${NC}" >&2
                grep -E '^[^.]' "$rsync_output_file" | head -10 | sed 's/^/  /' >&2
                echo "  ... and $(($diff_count - 10)) more" >&2
            fi

            if [ -s "$rsync_err_file" ]; then
                echo -e "${RED}[DEBUG] Rsync errors:${NC}" >&2
                cat "$rsync_err_file" | sed 's/^/  /' >&2
            fi
            echo "" >&2
        else
            rsync --dry-run --checksum --itemize-changes --archive \
                  --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
                  --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
                  --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
                  --exclude='installation-utils' --exclude='migrate_*.py' \
                  --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
                  --exclude='*.md' \
                  --exclude='Tests' \
                  --exclude="$exclude_firmware" \
                  "$source" "$dest" 2>/dev/null | grep -E '^[^.]' >> "$sync_check_file"
        fi
    fi

    rm -f "$rsync_output_file" "$rsync_err_file"

    # Check if any files differ
    if [ -s "$sync_check_file" ]; then
        files_differ=true
        echo -e "${YELLOW}Files out of sync detected:${NC}" >&2
        head -20 "$sync_check_file" | sed 's/^/  /' >&2
        local total=$(wc -l < "$sync_check_file")
        [ "$total" -gt 20 ] && echo "  ... and $(($total - 20)) more files" >&2
    fi

    # Clean up temp files (kept in debug mode for inspection)
    if [ "$DEBUG_MODE" != "true" ]; then
        rm -f "$sync_check_file"
    fi

    # Return 0 if sync needed, 1 if in sync
    [ "$files_differ" = true ] && return 0 || return 1
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

# Check if git repository has permission issues
check_repo_permissions() {
    local repo_path="$1"
    local current_user="${2:-$USER}"

    # Check if repo has files owned by other users (especially root)
    if [ -d "$repo_path/.git" ]; then
        local root_owned=$(find "$repo_path" -user root 2>/dev/null | wc -l)
        local write_test_dir="$repo_path/.git"

        # Try to create a test file to verify write permissions
        if ! touch "$write_test_dir/.permission_test" 2>/dev/null; then
            echo -e "${RED}Error: Cannot write to git repository${NC}"
            echo -e "${YELLOW}Repository path: $repo_path${NC}"
            echo ""
            echo "This usually happens when the repository has files owned by root"
            echo "from previous sudo operations."
            echo ""
            echo "To fix, run:"
            echo -e "${CYAN}  sudo chown -R $current_user:$current_user $(realpath $repo_path)${NC}"
            echo ""
            return 1
        else
            rm -f "$write_test_dir/.permission_test" 2>/dev/null
        fi

        if [ "$root_owned" -gt 0 ]; then
            echo -e "${YELLOW}Warning: Found $root_owned files owned by root in repository${NC}"
            echo "This may cause issues with git operations"
            echo ""
            echo "To fix ownership, run:"
            echo -e "${CYAN}  sudo chown -R $current_user:$current_user $(realpath $repo_path)${NC}"
            echo ""

            if [ "$AUTO_YES" = "false" ]; then
                read -p "Continue anyway? [y/N] " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    return 1
                fi
            fi
        fi
    fi

    return 0
}

# Fix repository permissions
fix_repo_permissions() {
    local repo_path="$1"
    local target_user="${2:-$USER}"

    echo -e "${BLUE}Fixing repository permissions...${NC}"
    echo -e "${CYAN}Repository:${NC} $repo_path"
    echo -e "${CYAN}Target owner:${NC} $target_user"
    echo ""

    sudo chown -R "$target_user:$target_user" "$repo_path"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Repository permissions fixed${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to fix permissions${NC}"
        return 1
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

# Handle --fix-permissions mode
if [ "$FIX_PERMISSIONS" = "true" ]; then
    fix_repo_permissions "$MOTHBOX_ROOT" "$MOTHBOX_USER"
    exit $?
fi

# Check repository permissions before git operations
echo -e "${BLUE}Checking repository permissions...${NC}"
if ! check_repo_permissions "$MOTHBOX_ROOT" "$MOTHBOX_USER"; then
    echo -e "${RED}Repository permission check failed${NC}"
    echo ""
    echo "You can fix this by running:"
    echo -e "${CYAN}  $0 --fix-permissions${NC}"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ Repository permissions OK${NC}"
echo ""

# Check for uncommitted changes and untracked files
HAS_UNCOMMITTED=false
HAS_UNTRACKED=false
STASH_NEEDED=false

if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    HAS_UNCOMMITTED=true
fi

# Check for untracked files (excluding common directories)
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    HAS_UNTRACKED=true
fi

if [ "$HAS_UNCOMMITTED" = "true" ] || [ "$HAS_UNTRACKED" = "true" ]; then
    echo -e "${YELLOW}Warning: You have local changes in your working directory${NC}"

    if [ "$HAS_UNCOMMITTED" = "true" ]; then
        echo -e "${YELLOW}  • Modified files that haven't been committed${NC}"
    fi
    if [ "$HAS_UNTRACKED" = "true" ]; then
        echo -e "${YELLOW}  • Untracked files${NC}"
    fi

    echo ""
    echo "To update successfully, we need to temporarily save your changes."
    echo "Your changes will be stashed and can be restored later if needed."
    echo ""

    if [ "$AUTO_YES" = "false" ] && [ "$DRY_RUN" = "false" ]; then
        read -p "Stash local changes and continue with update? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Update cancelled${NC}"
            echo ""
            echo "To update manually:"
            echo "  1. Commit your changes: git add . && git commit -m 'local changes'"
            echo "  2. Or stash them: git stash --include-untracked"
            echo "  3. Then run: $0"
            exit 1
        fi
        STASH_NEEDED=true
    elif [ "$AUTO_YES" = "true" ]; then
        STASH_NEEDED=true
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
        # Stash local changes if needed
        if [ "$STASH_NEEDED" = "true" ]; then
            echo -e "${BLUE}Stashing local changes...${NC}"
            STASH_NAME="mothbox-update-$(date +%Y%m%d-%H%M%S)"

            # Stash both tracked and untracked files
            if git stash push --include-untracked -m "$STASH_NAME" 2>&1; then
                echo -e "${GREEN}✓ Local changes stashed as '$STASH_NAME'${NC}"
                echo ""
                echo "To restore your changes later, run:"
                echo -e "${CYAN}  git stash list${NC}  (to see stashed changes)"
                echo -e "${CYAN}  git stash pop${NC}   (to restore the most recent stash)"
                echo ""
            else
                echo -e "${YELLOW}Warning: Failed to stash some changes${NC}"
                echo "Attempting to continue with update..."
                echo ""
            fi
        fi

        echo -e "${BLUE}Pulling updates from git...${NC}"

        # Try git pull with error handling
        if ! git pull origin "$TARGET_BRANCH" 2>&1 | tee /tmp/mothbox_git_pull.log; then
            # Git pull failed - check if it's a permission issue
            if grep -q "Permission denied" /tmp/mothbox_git_pull.log || grep -q "unable to create file" /tmp/mothbox_git_pull.log; then
                echo -e "${RED}✗ Git pull failed due to permission issues${NC}"
                echo ""
                echo "This usually happens when files in the repository are owned by root"
                echo "or another user, preventing git from creating/updating files."
                echo ""
                echo "To fix this, run:"
                echo -e "${CYAN}  $0 --fix-permissions${NC}"
                echo ""
                echo "Or manually:"
                echo -e "${CYAN}  sudo chown -R $MOTHBOX_USER:$MOTHBOX_USER $(realpath $MOTHBOX_ROOT)${NC}"
                echo -e "${CYAN}  $0${NC}"
                echo ""
                rm -f /tmp/mothbox_git_pull.log
                exit 1
            else
                # Other git error
                echo -e "${RED}✗ Git pull failed${NC}"
                echo "Check the error message above for details"
                rm -f /tmp/mothbox_git_pull.log
                exit 1
            fi
        fi

        rm -f /tmp/mothbox_git_pull.log
        echo -e "${GREEN}✓ Git updates pulled${NC}"

        # Update COMPARE_COMMIT to new HEAD after pull
        COMPARE_COMMIT=$(git rev-parse HEAD)
        echo ""
    fi
fi

# For production installs, always check file sync status
FILES_NEED_SYNC=false
if [ "$INSTALL_TYPE" = "production" ]; then
    echo -e "${BLUE}Checking file sync status...${NC}"
    if verify_file_sync; then
        FILES_NEED_SYNC=true
        echo -e "${YELLOW}⚠ Files need synchronization${NC}"
    else
        echo -e "${GREEN}✓ Files in sync${NC}"
    fi
    echo ""
fi

# Check if processing is needed (now comparing against pulled code)
GIT_HAS_CHANGES=false
if [ "$BASE_COMMIT" != "$COMPARE_COMMIT" ]; then
    GIT_HAS_CHANGES=true
fi

# Early exit if nothing to do
if [ "$GIT_HAS_CHANGES" = "false" ] && [ "$FILES_NEED_SYNC" = "false" ] && \
   [ "$FORCE_UPDATE" = "false" ] && [ "$FORCE_FRONTEND_REBUILD" = "false" ]; then
    echo -e "${GREEN}✓ No updates to process!${NC}"
    echo ""

    # Still verify installation health
    verify_installation

    exit 0
fi

# If production and files need sync but no git changes, do sync-only
if [ "$INSTALL_TYPE" = "production" ] && [ "$FILES_NEED_SYNC" = "true" ] && [ "$GIT_HAS_CHANGES" = "false" ]; then
    echo -e "${BLUE}Syncing files (no git changes, but files out of sync)...${NC}"
    echo ""
    # Will proceed to file sync section below, then exit early
fi

# If only rebuild requested (no git changes), skip to rebuild section
if [ "$GIT_HAS_CHANGES" = "false" ] && [ "$FORCE_FRONTEND_REBUILD" = "true" ]; then
    echo -e "${YELLOW}No git changes, but --rebuild requested${NC}"
    echo ""
fi

# Show what will be updated (changes between base and current)
if [ "$GIT_HAS_CHANGES" = "true" ]; then
    echo ""
    echo -e "${BLUE}Changes to process:${NC}"
    git --no-pager diff --name-status "$BASE_COMMIT..$COMPARE_COMMIT" | head -20
    echo ""
fi

# Categorize changes (only if git has changes)
FIRMWARE_CHANGED=0
WEBUI_BACKEND_CHANGED=0
WEBUI_FRONTEND_CHANGED=0
BACKEND_CONFIG_CHANGED=0
INSTALLER_CHANGED=0
SERVICE_CHANGED=0
CONFIG_CHANGED=0

if [ "$GIT_HAS_CHANGES" = "true" ]; then
    TOTAL_CHANGES=$(git diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" | wc -l)
    if [ "$TOTAL_CHANGES" -gt 20 ]; then
        echo -e "${CYAN}... and $(($TOTAL_CHANGES - 20)) more files${NC}"
        echo ""
    fi

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
fi

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

    # Determine which firmware version to exclude (sync only installed version)
    if [ "$FIRMWARE_VERSION" = "4" ]; then
        EXCLUDE_FIRMWARE="5.x"
    else
        EXCLUDE_FIRMWARE="4.x"
    fi

    # Copy entire Firmware directory structure (matching installer behavior)
    # This preserves the X.x subdirectory structure that mothbox_paths.py expects
    echo "Syncing firmware files (${FIRMWARE_VERSION}.x)..."
    sudo rsync -av --checksum \
        --exclude='.git' --exclude='__pycache__' --exclude='node_modules' \
        --exclude='*.pyc' --exclude='.DS_Store' --exclude='.gitignore' --exclude='.github' \
        --exclude='install_mothbox.sh' --exclude='uninstall_mothbox.sh' \
        --exclude='installation-utils' --exclude='migrate_*.py' \
        --exclude='INSTALLATION.md' --exclude='HARDWARE_CONFIG_REMAINING.md' \
        --exclude='*.md' \
        --exclude='Tests' \
        --exclude="$EXCLUDE_FIRMWARE" \
        "$MOTHBOX_ROOT/Firmware/" "$MOTHBOX_HOME/"

    # Note: We do NOT copy update_mothbox.sh to installation directory
    # The update script must always be run from the source git repository

    # Preserve critical files (don't delete during sync)
    # Create .installation_type if it doesn't exist
    if [ ! -f "$MOTHBOX_HOME/.installation_type" ]; then
        echo "$INSTALL_TYPE" | sudo tee "$MOTHBOX_HOME/.installation_type" > /dev/null
    fi

    # Set proper ownership
    sudo chown -R $MOTHBOX_USER:$MOTHBOX_USER "$MOTHBOX_HOME"

    # Also fix config directory ownership for production installs
    # Config files must be writable by webui service (runs as pi:gpio)
    if [ "$INSTALL_TYPE" = "production" ]; then
        echo "Setting config directory permissions..."
        sudo chown -R $MOTHBOX_USER:gpio "$CONFIG_DIR"
    fi

    echo -e "${GREEN}✓ Files synced to $MOTHBOX_HOME${NC}"
    echo ""

    # Sync built-in presets to config directory
    echo "Syncing built-in presets..."
    BUILTIN_PRESET_SOURCE="$MOTHBOX_ROOT/Firmware/webui/backend/presets_builtin"
    PRESET_DIR="$CONFIG_DIR/presets"

    if [ -d "$BUILTIN_PRESET_SOURCE" ]; then
        sudo mkdir -p "$PRESET_DIR/built-in"
        sudo cp -f "$BUILTIN_PRESET_SOURCE"/*.json "$PRESET_DIR/built-in/"
        sudo chown -R "$MOTHBOX_USER:gpio" "$PRESET_DIR"
        sudo chmod -R 644 "$PRESET_DIR/built-in"/*.json
        echo -e "${GREEN}✓ Built-in presets synced${NC}"
    else
        echo -e "${YELLOW}⚠ Built-in preset source not found: $BUILTIN_PRESET_SOURCE${NC}"
    fi
    echo ""
elif [ "$INSTALL_TYPE" = "legacy" ]; then
    # For legacy installs, git repo IS the installation - no copying needed
    echo -e "${CYAN}Legacy install detected - files already in place${NC}"
    echo ""
fi

# If we only needed file sync (no git changes) and no rebuild requested, exit here
if [ "$GIT_HAS_CHANGES" = "false" ] && [ "$FILES_NEED_SYNC" = "true" ] && [ "$FORCE_FRONTEND_REBUILD" = "false" ]; then
    echo -e "${GREEN}✓ File sync complete, no other updates needed${NC}"
    echo ""
    verify_installation
    set_last_update_commit "$COMPARE_COMMIT"
    exit 0
fi

# Update components based on what changed
UPDATES_PERFORMED=0

# Update firmware Python scripts permissions
if [ "$FIRMWARE_CHANGED" -gt 0 ]; then
    echo -e "${BLUE}Updating firmware script permissions...${NC}"
    find "$MOTHBOX_HOME" -name "*.py" -exec chmod +x {} +
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
        NPM_INSTALLED=false
        if [ ! -d "node_modules" ]; then
            echo "Installing npm dependencies (node_modules not found)..."
            sudo -u "$MOTHBOX_USER" npm install
            NPM_INSTALLED=true
        elif git -C "$MOTHBOX_ROOT" diff --name-only "$BASE_COMMIT..$COMPARE_COMMIT" 2>/dev/null | grep -q "webui/frontend/package"; then
            echo "Reinstalling npm dependencies (package files changed)..."
            sudo -u "$MOTHBOX_USER" npm install
            NPM_INSTALLED=true
        fi

        # Fix execute permissions on npm binaries after install
        if [ "$NPM_INSTALLED" = true ]; then
            echo "Setting execute permissions on npm binaries..."
            find node_modules/.bin -type l 2>/dev/null | while read -r link; do
                target=$(readlink -f "$link")
                if [ -f "$target" ]; then
                    chmod +x "$target" 2>/dev/null || true
                fi
            done
        fi

        # Clean build to avoid Vite caching issues with incremental builds
        echo "Cleaning previous build artifacts and Vite cache..."
        rm -rf dist
        rm -rf node_modules/.vite

        # Always ensure npm binaries are executable before build (in case permissions were lost)
        if [ -d "node_modules/.bin" ]; then
            find node_modules/.bin -type l 2>/dev/null | while read -r link; do
                target=$(readlink -f "$link")
                if [ -f "$target" ] && [ ! -x "$target" ]; then
                    chmod +x "$target" 2>/dev/null || true
                fi
            done
        fi

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

        # Fix execute permissions on npm binaries
        echo "Setting execute permissions on npm binaries..."
        find node_modules/.bin -type l 2>/dev/null | while read -r link; do
            target=$(readlink -f "$link")
            if [ -f "$target" ]; then
                chmod +x "$target" 2>/dev/null || true
            fi
        done

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

# Migration: Split camera_settings.csv into firmware vs webui settings
# (Added for commit 3a3e6953 - refactor: Split camera settings)
if [ ! -f "$CONFIG_DIR/webui_settings.csv" ] && [ -f "$CONFIG_DIR/camera_settings.csv" ]; then
    echo -e "${BLUE}Migrating camera settings to new format...${NC}"
    echo "Creating webui_settings.csv for webui-specific workflow settings"

    # Define settings TakePhoto.py actually uses (keep only these in camera_settings.csv)
    # TakePhoto.py only uses: ExposureValue, LensPosition, ExposureTime, AnalogueGain
    FIRMWARE_SETTINGS=(
        "ExposureValue"
        "LensPosition"
        "ExposureTime"
        "AnalogueGain"
        "LastCalibration"
    )

    # All other settings are webui-only and should be moved
    WEBUI_SETTINGS=(
        "HDR"
        "HDR_width"
        "FocusBracket"
        "FocusBracket_Start"
        "FocusBracket_End"
        "FlashDelay_BeforeCapture"
        "FlashDelay_AfterCapture"
        "FocusBracket_SettleDelay"
        "FocusBracket_LockColorGains"
        "FocusBracket_ColorGainRed"
        "FocusBracket_ColorGainBlue"
        "AutoCalibration"
        "AutoCalibrationPeriod"
        "ImageFileType"
        "VerticalFlip"
        "Name"
        "Sharpness"
        "Brightness"
        "Contrast"
        "Saturation"
        "NoiseReductionMode"
        "ColourGainRed"
        "ColourGainBlue"
        "AeEnable"
        "AwbEnable"
        "AfMode"
        "AfSpeed"
        "AfRange"
        "AwbMode"
        "AeMeteringMode"
        "AfMetering"
    )

    # Create backup of original camera_settings.csv
    sudo cp "$CONFIG_DIR/camera_settings.csv" "$CONFIG_DIR/camera_settings.csv.pre-split-backup"
    echo "  Created backup: camera_settings.csv.pre-split-backup"

    # Create webui_settings.csv with header
    echo "SETTING,VALUE,DETAILS" | sudo tee "$CONFIG_DIR/webui_settings.csv" > /dev/null

    # Move all non-firmware settings to webui_settings.csv
    while IFS= read -r line; do
        # Skip header and empty lines
        if [[ "$line" =~ ^SETTING, ]] || [ -z "$line" ]; then
            continue
        fi

        # Extract setting name (first column)
        setting=$(echo "$line" | cut -d',' -f1)

        # Check if this is a firmware setting
        is_firmware=false
        for fw_setting in "${FIRMWARE_SETTINGS[@]}"; do
            if [ "$setting" = "$fw_setting" ]; then
                is_firmware=true
                break
            fi
        done

        # If not a firmware setting, move to webui_settings.csv
        if [ "$is_firmware" = false ]; then
            echo "$line" | sudo tee -a "$CONFIG_DIR/webui_settings.csv" > /dev/null
            echo "  Moved to webui: $setting"
        fi
    done < "$CONFIG_DIR/camera_settings.csv"

    # Create new camera_settings.csv with only firmware settings
    TEMP_FILE=$(mktemp)
    echo "SETTING,VALUE,DETAILS" > "$TEMP_FILE"

    # Keep only firmware settings in camera_settings.csv
    while IFS= read -r line; do
        # Skip header
        if [[ "$line" =~ ^SETTING, ]]; then
            continue
        fi

        setting=$(echo "$line" | cut -d',' -f1)

        # Check if this is a firmware setting
        for fw_setting in "${FIRMWARE_SETTINGS[@]}"; do
            if [ "$setting" = "$fw_setting" ]; then
                echo "$line" >> "$TEMP_FILE"
                echo "  Kept in camera_settings: $setting"
                break
            fi
        done
    done < "$CONFIG_DIR/camera_settings.csv"

    sudo mv "$TEMP_FILE" "$CONFIG_DIR/camera_settings.csv"

    # Set proper ownership
    sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$CONFIG_DIR/webui_settings.csv"
    sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$CONFIG_DIR/camera_settings.csv"
    sudo chown $MOTHBOX_USER:$MOTHBOX_USER "$CONFIG_DIR/camera_settings.csv.pre-split-backup"

    echo -e "${GREEN}✓ Settings migration complete${NC}"
    echo "  camera_settings.csv now contains only firmware camera controls"
    echo "  webui_settings.csv contains webui workflow settings (HDR, FocusBracket, etc.)"
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

# Ensure memory tuning for Pi 5
ensure_memory_tuning

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
