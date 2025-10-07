# Mothbox Installation Guide

This guide explains how to install and configure the Mothbox firmware with the new flexible directory structure.

## Installation Types

The Mothbox firmware now supports three installation types:

### 1. Legacy Installation (Default)
**Location:** `/home/pi/Desktop/Mothbox`

This is the traditional location for backward compatibility with existing installations.

```bash
./install_mothbox.sh --type legacy
```

### 2. Production Installation (Recommended)
**Locations:**
- Application: `/opt/mothbox`
- Configuration: `/etc/mothbox`
- Data: `/var/lib/mothbox`

This follows Linux Filesystem Hierarchy Standard (FHS) and is recommended for new deployments.

```bash
./install_mothbox.sh --type production
```

### 3. Custom Installation
**Location:** User-defined

Useful for development or special deployment scenarios.

```bash
./install_mothbox.sh --type custom --path /your/custom/path
export MOTHBOX_HOME=/your/custom/path
```

## Quick Start

### New Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/zane-lazare/Mothbox.git
   cd Mothbox/Firmware
   ```

2. **Run the installation script:**
   ```bash
   chmod +x install_mothbox.sh
   ./install_mothbox.sh --type production
   ```

3. **Configure your Mothbox:**
   Edit configuration files in `/etc/mothbox/`:
   - `controls.txt` - System control parameters
   - `camera_settings.csv` - Camera configuration
   - `schedule_settings.csv` - Scheduling configuration
   - `wordlist.csv` - Device naming wordlist

4. **Set up cron jobs:**
   ```bash
   crontab -e
   ```
   Use the examples in `crontab_examples/` as templates, updating paths as needed.

### Migrating from Legacy Installation

If you have an existing installation at `/home/pi/Desktop/Mothbox`:

1. **Backup your current installation:**
   ```bash
   sudo cp -r /home/pi/Desktop/Mothbox /home/pi/Desktop/Mothbox.backup
   ```

2. **Install to production location:**
   ```bash
   cd /home/pi/Desktop/Mothbox/Firmware
   ./install_mothbox.sh --type production
   ```

3. **Copy your existing configuration:**
   ```bash
   sudo cp /home/pi/Desktop/Mothbox/controls.txt /etc/mothbox/
   sudo cp /home/pi/Desktop/Mothbox/camera_settings.csv /etc/mothbox/
   sudo cp /home/pi/Desktop/Mothbox/schedule_settings.csv /etc/mothbox/
   ```

4. **Update your crontab:**
   ```bash
   crontab -e
   ```
   Change paths from `/home/pi/Desktop/Mothbox` to `/opt/mothbox`

5. **Test the new installation:**
   ```bash
   python3 /opt/mothbox/mothbox_paths.py
   python3 /opt/mothbox/TakePhoto.py  # Test photo capture
   ```

6. **Remove old installation** (after confirming everything works):
   ```bash
   sudo rm -rf /home/pi/Desktop/Mothbox
   ```

## Directory Structure

### Production Installation
```
/opt/mothbox/              # Application code
├── firmware/              # Firmware scripts
│   ├── 4.x/
│   ├── 5.x/
│   └── mothbox_paths.py
└── install_mothbox.sh

/etc/mothbox/              # Configuration
├── controls.txt
├── camera_settings.csv
├── schedule_settings.csv
└── wordlist.csv

/var/lib/mothbox/          # Data storage
└── photos/                # Captured photos
    └── YYYY-MM-DD/        # Date-organized
```

### Legacy Installation
```
/home/pi/Desktop/Mothbox/  # All-in-one directory
├── Firmware/
├── photos/
├── controls.txt
├── camera_settings.csv
└── ...
```

## Configuration

### Path Configuration Module

The `mothbox_paths.py` module automatically detects your installation type:

```python
from mothbox_paths import (
    MOTHBOX_HOME,      # Application directory
    CONFIG_DIR,        # Configuration directory
    DATA_DIR,          # Data storage directory
    PHOTOS_DIR,        # Photo output directory
    CONTROLS_FILE,     # controls.txt location
    CAMERA_SETTINGS_FILE,  # camera_settings.csv location
    SCHEDULE_SETTINGS_FILE, # schedule_settings.csv location
)
```

You can verify your paths:
```bash
python3 /opt/mothbox/mothbox_paths.py
```

### Environment Variables

For custom installations, set:
```bash
export MOTHBOX_HOME=/your/custom/path
```

Add this to `~/.bashrc` to make it permanent.

## Troubleshooting

### Scripts Can't Find Configuration Files

**Problem:** Scripts report missing `controls.txt` or other config files.

**Solution:**
1. Check installation type with: `python3 mothbox_paths.py`
2. Verify files exist in the correct location
3. For production: check `/etc/mothbox/`
4. For legacy: check `/home/pi/Desktop/Mothbox/`

### Permission Errors

**Problem:** Can't write to photos directory or config files.

**Solution:**
```bash
# For production installation
sudo chown -R pi:pi /etc/mothbox /var/lib/mothbox /opt/mothbox
sudo chmod -R 755 /var/lib/mothbox
```

### Cron Jobs Not Running

**Problem:** Scheduled tasks don't execute.

**Solution:**
1. Check crontab: `crontab -l`
2. Verify script paths match installation location
3. Check cron logs: `grep CRON /var/log/syslog`
4. Test scripts manually first

## Support

- **Documentation:** See main README.md
- **Issues:** https://github.com/zane-lazare/Mothbox/issues
- **Discussions:** Use GitHub Discussions for questions

## Technical Details

### Path Detection Logic

The firmware automatically detects installation type in this order:

1. **Environment Variable:** If `MOTHBOX_HOME` is set, use custom paths
2. **Production Check:** If `/opt/mothbox` exists, use FHS layout
3. **Legacy Fallback:** Otherwise use `/home/pi/Desktop/Mothbox`

### Backward Compatibility

All existing scripts continue to work without modification. The path detection is transparent to the end user.

### Upgrading

When upgrading firmware:

1. Pull latest changes
2. Re-run installation script
3. Review any new configuration options
4. Restart scheduled tasks if needed

## Best Practices

1. **Use production layout** for new installations
2. **Backup configs** before major changes
3. **Test scripts manually** before adding to cron
4. **Keep firmware updated** via git pull
5. **Document customizations** in a local README

## See Also

- Main project README
- Hardware setup guide
- Camera configuration guide
- Scheduling documentation
