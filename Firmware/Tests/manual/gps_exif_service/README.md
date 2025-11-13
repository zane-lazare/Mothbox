# GPS EXIF Tagger Service - Manual Testing Guide

This directory contains manual test procedures and helper scripts for the GPS EXIF Tagger systemd service.

## Prerequisites

- Raspberry Pi with Mothbox installed (production or legacy)
- GPS hardware connected and configured
- gpsd service running
- GPS has valid fix (can acquire satellite signals)

## Test Files

- `test_installation.sh` - Validates service installation
- `test_monitoring.sh` - Monitors service operation and logs
- `test_resource_limits.sh` - Verifies resource constraints
- `MANUAL_TEST_PROCEDURES.md` - Detailed manual test procedures

## Quick Test Sequence

1. **Installation Test** (5 minutes)
   ```bash
   ./test_installation.sh
   ```
   Verifies service file exists, is enabled, and configuration is correct.

2. **Functional Test** (10 minutes)
   ```bash
   # Start the service
   sudo systemctl start gps-exif-tagger.service

   # Monitor logs
   ./test_monitoring.sh

   # Take a test photo
   cd /opt/mothbox  # or /home/pi/Desktop/Mothbox/Firmware
   python3 5.x/TakePhoto.py  # or 4.x/TakePhoto.py

   # Verify GPS EXIF was embedded (check logs for "Successfully embedded GPS")
   ```

3. **Resource Limits Test** (5 minutes)
   ```bash
   ./test_resource_limits.sh
   ```
   Verifies service stays within 256MB memory and 25% CPU limits.

4. **Security Test** (5 minutes)
   ```bash
   # Check security restrictions
   sudo systemctl show gps-exif-tagger.service | grep -E "Protect|NoNew|Private|Restrict"
   ```
   Verifies security hardening is active.

## Expected Results

### Installation Test
- ✓ Service file exists in /etc/systemd/system/
- ✓ Service is enabled for boot
- ✓ WorkingDirectory matches installation type
- ✓ ReadWritePaths and ReadOnlyPaths are correct

### Functional Test
- ✓ Service starts without errors
- ✓ Logs show GPS connection established
- ✓ New photos trigger processing
- ✓ GPS EXIF metadata embedded successfully
- ✓ exiftool shows GPSLatitude, GPSLongitude, GPSAltitude

### Resource Limits Test
- ✓ Memory usage stays below 256MB
- ✓ CPU usage stays below 25%
- ✓ No OOM (Out of Memory) kills

### Security Test
- ✓ ProtectSystem=strict
- ✓ NoNewPrivileges=yes
- ✓ PrivateTmp=yes
- ✓ ProtectKernelTunables=yes
- ✓ RestrictRealtime=yes

## Troubleshooting

### Service Won't Start
```bash
# Check detailed status
sudo systemctl status gps-exif-tagger.service

# View full logs
sudo journalctl -u gps-exif-tagger.service -n 100 --no-pager

# Check file permissions
ls -la /var/lib/mothbox/photos  # or /home/pi/Desktop/Mothbox/Firmware/photos
```

### No GPS Data
```bash
# Test GPS hardware
gpspipe -r | head -n 10

# Check gpsd service
sudo systemctl status gpsd.service

# Run GPS.py manually
cd /opt/mothbox
python3 5.x/GPS.py
```

### EXIF Not Embedded
```bash
# Check if service is watching correct directory
sudo systemctl show gps-exif-tagger.service | grep WorkingDirectory

# Verify gps_exif_tagger.py exists
ls -la /opt/mothbox/gps_exif_tagger.py

# Test tagger manually
python3 /opt/mothbox/gps_exif_tagger.py --mode immediate --verbose
```

## See Also

- `/home/zane/projects/Mothbox/Firmware/docs/GPS_EXIF_SERVICE.md` - Service setup guide
- `MANUAL_TEST_PROCEDURES.md` - Detailed test procedures
- `/home/zane/projects/Mothbox/Firmware/TESTING_PROCEDURE.md` - General testing guide
