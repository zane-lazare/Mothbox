# GPS EXIF Tagging - User Guide

## Overview

The GPS EXIF Tagging system automatically embeds GPS coordinates into Mothbox photos, enabling geolocation analysis and mapping of insect observations. This guide covers installation, usage, troubleshooting, and best practices.

## Features

- **Automatic Geotagging**: Embeds GPS coordinates into photo EXIF metadata
- **Dual Modes**: Batch processing or continuous watch mode
- **Metadata Preservation**: Preserves all existing camera EXIF data
- **Idempotent**: Safe to run multiple times (skips already-tagged photos)
- **High Performance**: >10 photos/second throughput
- **Systemd Integration**: Optional background service for automatic tagging
- **Verification Tools**: Inspect and validate GPS EXIF data

## Prerequisites

### Hardware Requirements
- Raspberry Pi with GPS module (any model supported by Mothbox)
- GPS module must be configured and working (see GPS setup documentation)

### Software Requirements
- Python 3.7+ with dependencies:
  - `piexif` (EXIF manipulation)
  - `Pillow` (image processing)
  - `mothbox_paths` (path resolution)

### GPS Configuration
GPS data is read from `controls.txt` with the following fields:
- `lat`: Latitude in decimal degrees
- `lon`: Longitude in decimal degrees
- `gps_fix_mode`: Fix quality (0=no fix, 2=2D, 3=3D)
- `alt`: Altitude in meters (optional, requires 3D fix)
- `gpstime`: GPS timestamp (Unix epoch)
- `gps_satellites_used`: Number of satellites
- `gps_hdop`, `gps_pdop`: Dilution of precision metrics

**Example controls.txt GPS section**:
```
lat=40.7128
lon=-74.0060
gps_fix_mode=3
alt=25.5
gpstime=1704990645
gps_satellites_used=8
gps_hdop=1.2
gps_pdop=2.1
```

## Installation

### Option 1: Via Installation Script (Recommended)
```bash
cd /path/to/Mothbox/Firmware
./install_mothbox.sh --with-gps-exif-service
```

This installs and enables the systemd service for automatic GPS tagging.

### Option 2: Manual Installation
```bash
# Install dependencies
pip3 install piexif Pillow

# Test the GPS EXIF tagger
python3 gps_exif_tagger.py --help

# Verify GPS data is available
python3 -c "from lib.gps_exif_lib import get_gps_data_from_controls; print(get_gps_data_from_controls())"
```

## Usage

### Batch Processing

Process all photos in a directory once:

```bash
# Basic usage - process default photos directory
python3 gps_exif_tagger.py

# Process specific directory
python3 gps_exif_tagger.py --directory /path/to/photos

# Dry run - see what would be processed without modifying files
python3 gps_exif_tagger.py --dry-run --verbose

# Create backups before modifying photos
python3 gps_exif_tagger.py --backup

# Force re-tag all photos (even if already tagged)
python3 gps_exif_tagger.py --force

# Process specific file pattern
python3 gps_exif_tagger.py --pattern "*.jpeg"
```

**Batch Mode Output**:
```
GPS EXIF Tagger starting...
Mode: batch
Directory: /var/lib/mothbox/photos
GPS fix available: 40.712800, -74.006000

Processing 150 photos...
[████████████████████████████████] 150/150

Summary:
  Total photos: 150
  Successfully tagged: 145
  Skipped (already tagged): 3
  Errors: 2
  Time: 12.4s
  Throughput: 12.1 photos/sec
```

### Watch Mode

Monitor directory for new photos and tag them automatically:

```bash
# Start watch mode with default settings
python3 gps_exif_tagger.py --watch

# Custom polling interval (check every 5 seconds)
python3 gps_exif_tagger.py --watch --interval 5

# Watch mode with backup creation
python3 gps_exif_tagger.py --watch --backup --interval 10

# Watch mode with verbose logging
python3 gps_exif_tagger.py --watch --verbose
```

**Watch Mode Output**:
```
GPS EXIF Tagger starting...
Mode: immediate
Starting watch mode on /var/lib/mothbox/photos
Polling interval: 10s
Pattern: *.jpg
GPS fix available: 40.712800, -74.006000

[2024-01-15 20:30:15] Detected new photo: 20240115_203015.jpg
[2024-01-15 20:30:15] ✓ Tagged 20240115_203015.jpg
[2024-01-15 20:32:18] Detected new photo: 20240115_203218.jpg
[2024-01-15 20:32:18] ✓ Tagged 20240115_203218.jpg
^C
Watch mode stopped by user
```

### Systemd Service (Background Operation)

#### Enable and Start Service
```bash
# Enable service to start on boot
sudo systemctl enable gps-exif-tagger.service

# Start service immediately
sudo systemctl start gps-exif-tagger.service

# Verify service is running
sudo systemctl status gps-exif-tagger.service
```

#### Monitor Service
```bash
# View live logs (Ctrl+C to exit)
sudo journalctl -u gps-exif-tagger.service -f

# View last 50 log lines
sudo journalctl -u gps-exif-tagger.service -n 50

# View logs for specific time period
sudo journalctl -u gps-exif-tagger.service --since "1 hour ago"
```

#### Stop/Restart Service
```bash
# Stop service
sudo systemctl stop gps-exif-tagger.service

# Restart service (after configuration changes)
sudo systemctl restart gps-exif-tagger.service

# Disable service (prevent auto-start on boot)
sudo systemctl disable gps-exif-tagger.service
```

### Verification Tools

Check if photos have GPS EXIF data:

```bash
# Verify single photo
python3 scripts/verify_gps_exif.py /path/to/photo.jpg

# Verify all photos in directory
python3 scripts/verify_gps_exif.py --directory /var/lib/mothbox/photos

# Generate CSV report
python3 scripts/verify_gps_exif.py --directory /var/lib/mothbox/photos --csv gps_report.csv
```

**Verification Output**:
```
Photo: /var/lib/mothbox/photos/20240115_203015.jpg
Filename timestamp: 2024-01-15 20:30:15

GPS EXIF Data:
  Has GPS: Yes
  Latitude: 40.712800°N
  Longitude: 74.006000°W
  Altitude: 25.5m
  Timestamp: 2024-01-15 20:30:10 UTC
  Satellites: 8
```

## Troubleshooting

### No GPS Fix

**Symptom**: Photos are not being tagged, logs show "No GPS fix available"

**Diagnosis**:
```bash
# Check GPS status
python3 -c "from lib.gps_exif_lib import get_gps_data_from_controls; import pprint; pprint.pprint(get_gps_data_from_controls())"
```

**Solutions**:
1. Wait for GPS to acquire fix (can take 2-30 minutes after power-on)
2. Ensure GPS antenna has clear view of sky
3. Check GPS module is enabled in `controls.txt`: `gps_enabled=true`
4. Verify GPS service is running: `sudo systemctl status GPS.service`
5. Check GPS logs: `sudo journalctl -u GPS.service -n 100`

### Photos Already Tagged

**Symptom**: Batch processing skips all photos, logs show "Already has GPS EXIF"

**Diagnosis**:
```bash
# Verify photo has GPS data
python3 scripts/verify_gps_exif.py /path/to/photo.jpg
```

**Solutions**:
- This is normal behavior (idempotent operation)
- To re-tag anyway, use `--force` flag
- To update GPS coordinates, use `--force` with current GPS data

### Permission Errors

**Symptom**: "Permission denied" errors when modifying photos

**Solutions**:
1. Check file permissions:
   ```bash
   ls -la /var/lib/mothbox/photos/
   ```
2. Ensure tagger has write access to photos directory
3. For systemd service, verify user has permissions:
   ```bash
   # Check service user
   sudo systemctl show gps-exif-tagger.service | grep User

   # Fix permissions (if needed)
   sudo chown -R pi:pi /var/lib/mothbox/photos
   sudo chmod -R u+w /var/lib/mothbox/photos
   ```

### Service Not Starting

**Symptom**: Systemd service fails to start

**Diagnosis**:
```bash
# Check service status
sudo systemctl status gps-exif-tagger.service

# View detailed logs
sudo journalctl -u gps-exif-tagger.service -n 50 --no-pager
```

**Common Causes**:
1. **Missing dependencies**: Install with `pip3 install piexif Pillow`
2. **Wrong path**: Service file references incorrect installation path
3. **Permissions**: Service user lacks access to photos directory
4. **Configuration error**: Invalid parameters in service file

**Solutions**:
1. Verify installation:
   ```bash
   which python3
   python3 -c "import piexif; print('piexif OK')"
   python3 gps_exif_tagger.py --help
   ```
2. Check service file paths:
   ```bash
   sudo cat /etc/systemd/system/gps-exif-tagger.service
   ```
3. Reload systemd and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart gps-exif-tagger.service
   ```

### High CPU/Memory Usage

**Symptom**: Service consuming excessive resources

**Diagnosis**:
```bash
# Check resource usage
systemctl status gps-exif-tagger.service

# Monitor in real-time
top -p $(pgrep -f gps_exif_tagger)
```

**Solutions**:
1. Increase polling interval (reduce CPU usage):
   ```bash
   # Edit service file
   sudo systemctl edit gps-exif-tagger.service

   # Change --interval value (e.g., 30 seconds instead of 10)
   ExecStart=/usr/bin/python3 .../gps_exif_tagger.py --watch --interval 30

   # Reload and restart
   sudo systemctl daemon-reload
   sudo systemctl restart gps-exif-tagger.service
   ```
2. Verify resource limits are in place:
   ```bash
   systemctl show gps-exif-tagger.service | grep -E "(Memory|CPU)"
   ```

### Corrupted EXIF Data

**Symptom**: Photos have broken/unreadable EXIF data after tagging

**Diagnosis**:
```bash
# Check EXIF data
exiftool photo.jpg

# Or use verification tool
python3 scripts/verify_gps_exif.py photo.jpg
```

**Prevention**:
- Always test with `--dry-run` first
- Use `--backup` flag to create safety copies
- Verify GPS data is valid before tagging

**Recovery**:
1. If backups exist (`.bak` files):
   ```bash
   mv photo.jpg.bak photo.jpg
   ```
2. If no backups, photo may need re-processing from RAW (if available)

## Best Practices

### For Batch Processing
1. **Test first**: Use `--dry-run --verbose` to preview operations
2. **Create backups**: Use `--backup` for first-time processing
3. **Verify results**: Spot-check photos with verification tool
4. **Monitor logs**: Watch for errors during processing

### For Systemd Service
1. **Monitor initially**: Watch logs for first few days to ensure stable operation
2. **Set appropriate interval**: Balance between responsiveness and resource usage
   - Fast interval (5-10s): Immediate tagging, higher CPU usage
   - Slow interval (30-60s): Lower CPU usage, delayed tagging
3. **Enable on tested system**: Only enable service after verifying GPS works
4. **Regular verification**: Periodically check that photos are being tagged

### For GPS Accuracy
1. **Wait for good fix**: Ensure `gps_fix_mode=3` (3D fix) for best accuracy
2. **Monitor satellite count**: More satellites (`gps_satellites_used`) = better accuracy
3. **Check HDOP/PDOP**: Lower values indicate better precision
   - HDOP < 2.0: Excellent
   - HDOP 2-5: Good
   - HDOP > 5: Poor
4. **Antenna placement**: Keep GPS antenna with clear view of sky

### For Data Integrity
1. **Preserve camera EXIF**: GPS tagging preserves camera metadata
2. **Idempotent operations**: Safe to re-run (skips already-tagged photos)
3. **Force with caution**: Use `--force` only when intentionally re-tagging
4. **Backup important photos**: Use `--backup` or separate backups

## Performance Optimization

### Batch Processing Performance
- **Expected throughput**: 10-15 photos/second
- **Factors affecting speed**:
  - Photo size (larger files take longer)
  - Disk I/O speed (SSD faster than SD card)
  - Existing EXIF complexity (more metadata = slower)
  - Backup creation (doubles write time)

### Watch Mode Performance
- **Polling overhead**: Each poll scans directory
- **Optimization tips**:
  - Use longer intervals if tagging delay is acceptable
  - Process photos in batches overnight instead of watch mode
  - Monitor CPU usage and adjust interval accordingly

### Service Resource Limits
The systemd service has built-in limits:
- **Memory**: 256MB maximum
- **CPU**: 25% quota (1 core = 100%)
- **Restart policy**: Automatic restart on failure

## Advanced Usage

### Custom GPS Data Source
By default, GPS data is read from `controls.txt`. To use a custom source:

```python
from lib.gps_exif_lib import embed_gps_exif
from pathlib import Path

# Custom controls file
custom_controls = Path('/custom/path/gps_data.txt')
result = embed_gps_exif(
    photo_path,
    controls_file=custom_controls,
    backup=True
)
```

### Programmatic Usage
```python
from lib.gps_exif_lib import get_gps_data_from_controls, embed_gps_exif, verify_gps_exif
from pathlib import Path

# Check GPS status
gps_data = get_gps_data_from_controls()
if gps_data['has_fix']:
    print(f"GPS: {gps_data['latitude']}, {gps_data['longitude']}")

# Tag a photo
photo = Path('/path/to/photo.jpg')
result = embed_gps_exif(photo, backup=True)
if result['success']:
    print(f"Tagged: {photo.name}")

# Verify GPS EXIF
verification = verify_gps_exif(photo)
if verification['has_gps']:
    print(f"Coordinates: {verification['latitude']}, {verification['longitude']}")
```

### Batch Processing with Progress
```python
import gps_exif_tagger
from pathlib import Path
from unittest.mock import Mock

# Setup logging
logger = gps_exif_tagger.setup_logging(verbose=True)

# Process directory
stats = gps_exif_tagger.batch_process_directory(
    Path('/var/lib/mothbox/photos'),
    logger,
    pattern='*.jpg',
    force=False,
    backup=True,
    dry_run=False
)

print(f"Processed {stats['total']} photos")
print(f"Tagged: {stats['tagged']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")
```

## Frequently Asked Questions

**Q: Will GPS tagging slow down photo capture?**
A: No. When using the systemd service or manual batch processing, GPS tagging happens after photo capture is complete. Photos are captured first, then tagged later.

**Q: What happens if GPS loses fix during operation?**
A: Photos captured without GPS fix are skipped. When GPS regains fix, new photos will be tagged. Existing untagged photos can be processed later with `--force` once GPS is available.

**Q: Can I tag old photos retroactively?**
A: Yes. Run batch processing on any directory. The GPS coordinates from the current `controls.txt` will be embedded. For historical accuracy, you'd need GPS data from when each photo was taken.

**Q: Does GPS tagging modify the photo image data?**
A: No. Only EXIF metadata is modified. The actual image pixels are unchanged. File size may increase slightly due to GPS EXIF data (~500 bytes).

**Q: What photo formats are supported?**
A: JPEG files (.jpg, .jpeg, case-insensitive). RAW formats are not supported.

**Q: Can I view GPS coordinates on my computer?**
A: Yes. Most photo viewers (Windows Photos, macOS Photos, GIMP, ExifTool) can read GPS EXIF. Photos will appear on maps in applications like Google Photos, Lightroom, etc.

**Q: Is GPS EXIF compatible with photo stacking/HDR?**
A: Yes. GPS EXIF is preserved through most photo processing workflows. Test your specific workflow to confirm.

## Support and Documentation

- **Main documentation**: See `CLAUDE.md` for developer details
- **Service setup**: See `docs/GPS_EXIF_SERVICE.md`
- **Testing procedures**: See `TESTING_PROCEDURE.md`
- **Issue tracker**: Report bugs on GitHub issue tracker
- **GPS setup**: See main Mothbox documentation for GPS module configuration

## Version History

- **v1.0** (January 2025): Initial release
  - Core GPS EXIF embedding functionality
  - Batch and watch modes
  - Systemd service integration
  - Verification tools
  - Comprehensive test suite (90%+ coverage)
