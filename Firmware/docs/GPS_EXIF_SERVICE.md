# GPS EXIF Tagger Service Guide

This guide covers installation, configuration, and management of the GPS EXIF Tagger systemd service for Mothbox.

## Overview

The GPS EXIF Tagger Service is a background daemon that automatically embeds GPS coordinates into photos taken by Mothbox. It runs continuously, watching for new photos and adding EXIF metadata with location data from the GPS module.

### Features

- **Automatic Processing**: Watches photos directory and processes new images immediately
- **GPS Integration**: Reads real-time GPS data from gpsd service
- **EXIF Embedding**: Adds 9 GPS EXIF tags (latitude, longitude, altitude, timestamp, etc.)
- **Resource Limited**: Constrained to 256MB memory and 25% CPU usage
- **Security Hardened**: Runs with strict systemd security restrictions
- **Auto-Recovery**: Automatically restarts on failure, handles GPS signal loss

### Architecture

```
┌─────────────────┐
│   TakePhoto.py  │ Captures photo → photos/
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  GPS EXIF Tagger Service                            │
│  (gps_exif_tagger.py --watch)                       │
│                                                      │
│  1. inotify watches photos/ for IN_CLOSE_WRITE      │
│  2. Detects new .jpg file                           │
│  3. Reads GPS data from gpsd                        │
│  4. Converts to EXIF format                         │
│  5. Embeds GPS IFD into JPEG                        │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Photo with GPS │ Ready for upload/sync
│  EXIF metadata  │
└─────────────────┘
```

---

## Installation

### Automatic Installation (Recommended)

Use the install_mothbox.sh script with the `--with-gps-exif-service` flag:

```bash
# Production installation with GPS service
./install_mothbox.sh --type production --with-gps-exif-service

# Legacy installation with GPS service
./install_mothbox.sh --type legacy --with-gps-exif-service

# Interactive mode (will prompt for GPS service installation)
./install_mothbox.sh
```

The installer will:
1. Copy the appropriate service file to `/etc/systemd/system/`
2. Reload systemd daemon
3. Enable the service for boot (but not start it)
4. Display service management commands

### Manual Installation

If you need to install manually:

```bash
# 1. Determine installation type
if [ -f /opt/mothbox/mothbox_paths.py ]; then
    INSTALL_TYPE="production"
    SERVICE_FILE="gps-exif-tagger.service"
else
    INSTALL_TYPE="legacy"
    SERVICE_FILE="gps-exif-tagger-legacy.service"
fi

# 2. Copy service file
sudo cp services/$SERVICE_FILE /etc/systemd/system/

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Enable service for boot
sudo systemctl enable $SERVICE_FILE

# 5. Start service
sudo systemctl start $SERVICE_FILE
```

---

## Service Management

### Basic Commands

```bash
# Determine which service is installed
SERVICE=$(systemctl list-units --all | grep gps-exif-tagger | awk '{print $1}')

# Start service
sudo systemctl start $SERVICE

# Stop service
sudo systemctl stop $SERVICE

# Restart service
sudo systemctl restart $SERVICE

# Check status
sudo systemctl status $SERVICE

# Enable at boot
sudo systemctl enable $SERVICE

# Disable at boot
sudo systemctl disable $SERVICE
```

### Viewing Logs

```bash
# View recent logs
sudo journalctl -u $SERVICE -n 50

# Follow logs in real-time
sudo journalctl -u $SERVICE -f

# View logs since boot
sudo journalctl -u $SERVICE -b

# View logs for specific time range
sudo journalctl -u $SERVICE --since "2025-11-10 10:00" --until "2025-11-10 12:00"

# Export logs to file
sudo journalctl -u $SERVICE --since today > gps-exif-logs.txt
```

### Monitoring Resource Usage

```bash
# Check current memory and CPU usage
sudo systemctl status $SERVICE

# Show detailed resource metrics
sudo systemctl show $SERVICE -p MemoryCurrent -p CPUUsageNSec

# Monitor with top
top -p $(systemctl show $SERVICE -p MainPID --value)

# Use the automated monitoring script
cd Tests/manual/gps_exif_service
./test_resource_limits.sh 60
```

---

## Configuration

### Service File Locations

- **Production**: `/etc/systemd/system/gps-exif-tagger.service`
- **Legacy**: `/etc/systemd/system/gps-exif-tagger-legacy.service`

### Key Configuration Parameters

#### Production Service (gps-exif-tagger.service)

```ini
[Service]
Type=simple
User=pi
WorkingDirectory=/opt/mothbox

# Main command: watch mode with 10-second polling
ExecStart=/usr/bin/python3 /opt/mothbox/gps_exif_tagger.py --mode immediate --watch --interval 10 --verbose

# Resource limits
MemoryMax=256M
CPUQuota=25%

# Filesystem access
ProtectSystem=strict
ReadWritePaths=/var/lib/mothbox/photos
ReadOnlyPaths=/etc/mothbox
```

#### Legacy Service (gps-exif-tagger-legacy.service)

```ini
[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Desktop/Mothbox/Firmware

# Main command
ExecStart=/usr/bin/python3 /home/pi/Desktop/Mothbox/Firmware/gps_exif_tagger.py --mode immediate --watch --interval 10 --verbose

# Resource limits
MemoryMax=256M
CPUQuota=25%

# Filesystem access
ProtectSystem=strict
ReadWritePaths=/home/pi/Desktop/Mothbox/Firmware/photos
ReadOnlyPaths=/home/pi/Desktop/Mothbox/Firmware
```

### Adjusting Resource Limits

Edit the service file if you need to adjust limits:

```bash
# Edit service file
sudo systemctl edit --full $SERVICE

# Increase memory limit (if needed)
# Change: MemoryMax=256M
# To:     MemoryMax=512M

# Increase CPU limit (if needed)
# Change: CPUQuota=25%
# To:     CPUQuota=50%

# Reload systemd and restart
sudo systemctl daemon-reload
sudo systemctl restart $SERVICE
```

### Changing Polling Interval

The service checks for new photos every 10 seconds by default. To change:

```bash
# Edit service file
sudo systemctl edit --full $SERVICE

# Change --interval parameter
# From: --interval 10
# To:   --interval 5  (check every 5 seconds)

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart $SERVICE
```

---

## Security

The service runs with strict systemd security hardening:

### Filesystem Protection

- **ProtectSystem=strict**: Entire filesystem read-only except specified paths
- **ReadWritePaths**: Only photos directory is writable
- **ReadOnlyPaths**: Config directory accessible for reading only
- **ProtectHome=true** (production): User home directories protected

### Privilege Restrictions

- **NoNewPrivileges=yes**: Cannot gain new privileges
- **CapabilityBoundingSet=** (empty): No Linux capabilities
- **AmbientCapabilities=** (empty): No ambient capabilities

### Kernel Protection

- **ProtectKernelTunables=yes**: Cannot modify kernel parameters
- **ProtectKernelModules=yes**: Cannot load/unload kernel modules
- **ProtectControlGroups=yes**: Control groups read-only
- **RestrictRealtime=yes**: No real-time scheduling

### System Call Filtering

- **SystemCallFilter=@system-service**: Only allows system calls needed for services
- **SystemCallFilter=~@privileged @resources**: Denies privileged operations

### Verify Security Settings

```bash
# Check all security settings
sudo systemctl show $SERVICE | grep -E "Protect|NoNew|Private|Restrict|Capability|SystemCall"

# Expected output should include:
# ProtectSystem=strict
# NoNewPrivileges=yes
# ProtectHome=yes (or read-only)
# RestrictRealtime=yes
# etc.
```

---

## Troubleshooting

### Service Won't Start

**Symptoms**: Service fails to start or immediately exits

**Diagnosis**:
```bash
# Check detailed status
sudo systemctl status $SERVICE

# View recent logs
sudo journalctl -u $SERVICE -n 50

# Check for Python errors
sudo journalctl -u $SERVICE | grep -i error
```

**Common Causes**:
1. **Missing gps_exif_tagger.py**
   - Verify file exists: `ls /opt/mothbox/gps_exif_tagger.py`
   - Reinstall if missing

2. **Wrong WorkingDirectory**
   - Check service file: `sudo systemctl cat $SERVICE`
   - Ensure WorkingDirectory matches installation type

3. **Permission errors**
   - Check photos directory: `ls -la /var/lib/mothbox/photos`
   - Should be owned by `pi:pi`

4. **Missing dependencies**
   - Verify Pillow: `python3 -c "from PIL import Image"`
   - Verify gpsd: `python3 -c "import gps"`

### GPS Connection Fails

**Symptoms**: Logs show "GPS unavailable" or "Waiting for GPS fix"

**Diagnosis**:
```bash
# Test gpsd directly
gpspipe -r | head -n 10

# Check GPS fix status
cgps

# Verify gpsd service
sudo systemctl status gpsd
```

**Solutions**:
1. **No GPS hardware detected**
   - Check wiring: TX↔RX, 3.3V, GND
   - Verify UART enabled: `grep enable_uart /boot/firmware/config.txt`

2. **No GPS fix**
   - Move to location with clear sky view
   - Wait 30-60 seconds for cold start
   - Check antenna connection

3. **gpsd not running**
   ```bash
   sudo systemctl start gpsd
   sudo systemctl enable gpsd
   ```

### Photos Not Being Processed

**Symptoms**: New photos don't get GPS EXIF data

**Diagnosis**:
```bash
# Check if service is running
sudo systemctl status $SERVICE

# Watch logs while taking photo
sudo journalctl -u $SERVICE -f &
python3 5.x/TakePhoto.py

# Check if inotify is working
ls -la /proc/$(systemctl show $SERVICE -p MainPID --value)/fd/ | grep inotify
```

**Solutions**:
1. **Service not watching correct directory**
   - Verify in logs: Should show "Started watching: [photos_dir]"
   - Check WorkingDirectory in service file

2. **Inotify limit reached**
   ```bash
   # Check current limit
   cat /proc/sys/fs/inotify/max_user_watches

   # Increase if needed
   echo 'fs.inotify.max_user_watches=524288' | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

3. **Photos created too quickly**
   - Service polls every 10 seconds
   - May miss photos created before service started
   - Solution: Restart service or process manually

### Memory Limit Exceeded

**Symptoms**: Service stops, OOM (Out of Memory) in logs

**Diagnosis**:
```bash
# Check if OOM killed the service
sudo journalctl -u $SERVICE | grep -i "oom\|killed"

# Monitor memory usage
./Tests/manual/gps_exif_service/test_resource_limits.sh 60
```

**Solutions**:
1. **Increase memory limit**
   ```bash
   sudo systemctl edit --full $SERVICE
   # Change MemoryMax=256M to MemoryMax=512M
   sudo systemctl daemon-reload
   sudo systemctl restart $SERVICE
   ```

2. **Investigate memory leak**
   - Check logs for patterns
   - Report issue with logs and memory profile

### High CPU Usage

**Symptoms**: CPU consistently above 25%

**Diagnosis**:
```bash
# Monitor CPU usage
top -p $(systemctl show $SERVICE -p MainPID --value)

# Run resource test
./Tests/manual/gps_exif_service/test_resource_limits.sh 120
```

**Solutions**:
1. **Increase polling interval** (reduce frequency)
   ```bash
   sudo systemctl edit --full $SERVICE
   # Change --interval 10 to --interval 30
   sudo systemctl daemon-reload
   sudo systemctl restart $SERVICE
   ```

2. **Increase CPU quota** (allow more CPU)
   ```bash
   sudo systemctl edit --full $SERVICE
   # Change CPUQuota=25% to CPUQuota=50%
   sudo systemctl daemon-reload
   sudo systemctl restart $SERVICE
   ```

---

## Manual Testing

Comprehensive manual test procedures are available:

```bash
cd /home/zane/projects/Mothbox/Firmware/Tests/manual/gps_exif_service

# 1. Run installation verification
./test_installation.sh

# 2. Monitor service operation
./test_monitoring.sh

# 3. Test resource limits
./test_resource_limits.sh 60

# 4. Follow detailed manual procedures
# See MANUAL_TEST_PROCEDURES.md for step-by-step tests
```

---

## Integration with Mothbox

### Photo Capture Workflow

1. **TakePhoto.py** captures photo → saves to `photos/` directory
2. **inotify** (via gps_exif_tagger.py) detects new file (`IN_CLOSE_WRITE` event)
3. **GPS EXIF Tagger** reads GPS data from gpsd
4. **EXIF Embedding** adds GPS metadata to photo
5. **Photo ready** for upload/sync with location data

### Verification After Photo Capture

```bash
# Take a photo
python3 5.x/TakePhoto.py

# Wait 10 seconds for processing

# Check latest photo
LATEST=$(ls -t /var/lib/mothbox/photos/*.jpg | head -n 1)
exiftool "$LATEST" | grep GPS

# Expected output:
# GPS Latitude                    : 40 deg 44' 54.24" N
# GPS Longitude                   : 73 deg 59' 8.28" W
# GPS Altitude                    : 10 m Above Sea Level
# GPS Date/Time                   : 2025:11:11 14:30:45Z
# ...
```

### Coordinate Conversion

The service handles coordinate conversion automatically:

- **Input from GPS**: Decimal degrees (e.g., 40.748400)
- **Output in EXIF**: Degrees/minutes/seconds (e.g., 40° 44' 54.24" N)
- **Reference**: N/S for latitude, E/W for longitude
- **Datum**: Always WGS-84

---

## Performance

### Resource Usage (Typical)

- **Memory**: 20-50 MB (peak: ~80 MB during EXIF processing)
- **CPU**: 0-5% average (peaks to 15-20% during photo processing)
- **Disk I/O**: Minimal (only during photo processing)

### Processing Time

- **GPS data read**: < 100ms
- **EXIF embedding**: 200-500ms (depends on photo size)
- **Total overhead**: < 1 second per photo

### Scaling Considerations

- **Max photos/minute**: ~60 (1 per second sustained)
- **Concurrent photos**: Processes sequentially, no parallel processing
- **Large photos**: 64MP images take ~500ms to process

---

## Uninstallation

To remove the GPS EXIF Tagger Service:

```bash
# 1. Stop service
sudo systemctl stop $SERVICE

# 2. Disable service
sudo systemctl disable $SERVICE

# 3. Remove service file
sudo rm /etc/systemd/system/gps-exif-tagger*.service

# 4. Reload systemd
sudo systemctl daemon-reload

# 5. Reset failed state (if any)
sudo systemctl reset-failed
```

Note: This does not remove gps_exif_tagger.py or affect existing photos.

---

## Related Documentation

- **Installation**: `/home/zane/projects/Mothbox/Firmware/install_mothbox.sh --help`
- **Manual Testing**: `/home/zane/projects/Mothbox/Firmware/Tests/manual/gps_exif_service/`
- **EXIF Library**: `/home/zane/projects/Mothbox/Firmware/gps_exif/`
- **GPS Setup**: `/home/zane/projects/Mothbox/Firmware/README.md` (GPS section)
- **Service Files**: `/home/zane/projects/Mothbox/Firmware/services/`

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review service logs: `sudo journalctl -u $SERVICE -n 100`
3. Run diagnostic tests: `./test_installation.sh`, `./test_monitoring.sh`
4. Report issues with:
   - Service status output
   - Recent logs (last 100 lines)
   - Installation type (production/legacy)
   - GPS hardware model
