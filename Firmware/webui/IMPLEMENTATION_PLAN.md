# Web UI Installer Integration - Implementation Plan

## Overview
Integrate the web UI into the main Mothbox installation system with proper path handling, permissions, and systemd service management.

## Tasks

### 1. Verify Path Handling in Backend
- [ ] Audit all backend routes to ensure they use `mothbox_paths.py`
- [ ] Check PHOTOS_DIR, CONFIG_DIR, CAMERA_SETTINGS_FILE references
- [ ] Ensure routes work with all installation types (legacy, production, custom)
- [ ] Test that backend respects MOTHBOX_HOME environment variable

### 2. Fix WebSocket Connection Issues
- [ ] Update Flask-SocketIO CORS configuration for network access
- [ ] Ensure frontend WebSocket URL uses Pi's IP address (not localhost)
- [ ] Add WebSocket connection debugging/logging
- [ ] Test camera streaming on actual Pi hardware with picamera2
- [ ] Handle cases where camera is not available gracefully

### 3. Create Web UI Installation Script
Create `Firmware/installation-utils/install_webui.sh`:
- [ ] Check for and install Node.js if not present (NodeSource repo)
- [ ] Install Flask and webui-specific Python dependencies system-wide with --break-system-packages
- [ ] Navigate to frontend directory and run npm install
- [ ] Build React frontend with npm run build
- [ ] Add pi user to gpio group for GPIO access without sudo
- [ ] Provide feedback on installation progress
- [ ] Handle errors gracefully

### 4. Integrate into Main Installer
Update `Firmware/install_mothbox.sh`:
- [ ] Add interactive prompt in installation wizard: "Install Web UI? (y/n)"
- [ ] Add CLI flag: `--with-webui` for automated installations
- [ ] Call `install_webui.sh` if webui installation is selected
- [ ] Display webui access URL and instructions at end of installation
- [ ] Add webui dependencies to requirements check

### 5. Create Systemd Service
Create `Firmware/installation-utils/mothbox-webui.service`:
- [ ] Service runs as pi user (with gpio group permissions)
- [ ] Set proper WorkingDirectory to backend folder
- [ ] Use correct Python path and app.py location
- [ ] Configure auto-restart on failure
- [ ] Start after network is available
- [ ] Enable on boot by default
- [ ] Add service installation to install_webui.sh
- [ ] Test service start/stop/restart

### 6. Update Uninstaller
Update `Firmware/uninstall_mothbox.sh`:
- [ ] Stop and disable mothbox-webui.service
- [ ] Remove systemd service file
- [ ] Remove webui-specific Python packages (Flask, Flask-SocketIO, etc.)
- [ ] Optionally remove Node.js (prompt user since it may be used elsewhere)
- [ ] Remove built frontend files
- [ ] Remove pi user from gpio group (if added by installer)
- [ ] Clean up any webui-specific logs or temp files
- [ ] Provide confirmation of what was removed

### 7. Update Documentation
- [ ] Add webui installation section to main Mothbox README
- [ ] Document network access (how to find Pi IP address)
- [ ] Add troubleshooting section:
  - WebSocket connection failures
  - GPIO permission errors
  - Port 5000 conflicts
  - Camera access issues
- [ ] Document systemd service management commands
- [ ] Add screenshots/examples of the web UI
- [ ] Update Firmware/webui/README.md with installer instructions

### 8. Add Web UI Dependencies to Main Requirements
Update `Firmware/installation-utils/requirements.txt`:
- [ ] Add Flask==3.0.0
- [ ] Add Flask-CORS==4.0.0
- [ ] Add Flask-SocketIO==5.3.6
- [ ] Add python-socketio==5.11.0
- [ ] Note: RPi.GPIO, picamera2, Pillow, python-crontab already present

### 9. Testing Checklist
- [ ] Test installation on fresh Pi (legacy mode)
- [ ] Test installation on fresh Pi (production mode)
- [ ] Test webui access from local network
- [ ] Test all webui features (Dashboard, Gallery, Camera, GPIO, Scheduler, Settings)
- [ ] Test WebSocket camera preview with actual picamera2
- [ ] Test GPIO controls with real hardware
- [ ] Test systemd service (start, stop, restart, enable, disable)
- [ ] Test uninstaller removes all webui components
- [ ] Verify paths work correctly in all installation modes

### 10. Security Considerations
- [ ] Consider adding authentication (future enhancement)
- [ ] Document that webui should only be accessible on trusted networks
- [ ] Add note about changing default port if needed
- [ ] Consider HTTPS support (future enhancement)

## Implementation Order
1. Fix path handling and WebSocket issues (immediate)
2. Update requirements.txt (immediate)
3. Create install_webui.sh script
4. Update main installer
5. Create systemd service
6. Update uninstaller
7. Update documentation
8. Testing on actual hardware

## Notes
- Installation should be optional to keep Mothbox lean for users who don't need the web UI
- All webui components should be cleanly removable
- Should work with all three installation types (legacy, production, custom)
- GPIO access should not require sudo when properly configured
