# GPS EXIF Tagger Service - Manual Test Procedures

This document provides detailed step-by-step procedures for manually testing the GPS EXIF Tagger systemd service on Raspberry Pi hardware.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test 1: Installation Verification](#test-1-installation-verification)
3. [Test 2: Service Startup and Basic Operation](#test-2-service-startup-and-basic-operation)
4. [Test 3: GPS Data Acquisition](#test-3-gps-data-acquisition)
5. [Test 4: Photo Processing](#test-4-photo-processing)
6. [Test 5: Resource Limits](#test-5-resource-limits)
7. [Test 6: Security Hardening](#test-6-security-hardening)
8. [Test 7: Error Recovery](#test-7-error-recovery)
9. [Test 8: Service Lifecycle](#test-8-service-lifecycle)
10. [Cleanup](#cleanup)

---

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4 or 5
- GPS module connected and powered
- GPS antenna with clear sky view
- Arducam OwlSight camera

### Software Requirements
- Mothbox firmware installed (production or legacy)
- gpsd service running
- exiftool installed: `sudo apt-get install exiftool`

### Pre-Test Setup
```bash
# 1. Verify GPS hardware
gpspipe -r | head -n 5
# Should show NMEA sentences like $GPGGA, $GPRMC

# 2. Verify GPS has fix
cgps
# Wait until you see valid latitude/longitude

# 3. Check installation type
python3 -c "from mothbox_paths import MOTHBOX_HOME; print(MOTHBOX_HOME)"
```

---

## Test 1: Installation Verification

**Objective:** Verify service is correctly installed and configured.

**Duration:** 5 minutes

**Procedure:**

1. Run installation test script:
   ```bash
   cd /home/zane/projects/Mothbox/Firmware/Tests/manual/gps_exif_service
   chmod +x test_installation.sh
   ./test_installation.sh
   ```

2. **Expected Results:**
   - All 7 tests pass
   - Service file exists
   - Service is enabled
   - Working directory matches installation type
   - Security settings are active

3. **Manual Verification:**
   ```bash
   # Check service file content
   cat /etc/systemd/system/gps-exif-tagger*.service

   # Verify security settings
   sudo systemctl show gps-exif-tagger*.service | grep -E "Protect|NoNew"
   ```

4. **Pass Criteria:**
   - ✓ All automated tests pass
   - ✓ Service file contains ProtectSystem=strict
   - ✓ ReadWritePaths includes photos directory

---

## Test 2: Service Startup and Basic Operation

**Objective:** Verify service starts cleanly and initializes correctly.

**Duration:** 10 minutes

**Procedure:**

1. Start the service:
   ```bash
   # Determine which service is installed
   if [ -f /etc/systemd/system/gps-exif-tagger.service ]; then
       SERVICE="gps-exif-tagger.service"
   else
       SERVICE="gps-exif-tagger-legacy.service"
   fi

   sudo systemctl start $SERVICE
   ```

2. Check immediate status:
   ```bash
   sudo systemctl status $SERVICE
   ```

3. Monitor startup logs:
   ```bash
   sudo journalctl -u $SERVICE -n 50 --no-pager
   ```

4. **Expected Results:**
   - Service status shows "active (running)"
   - Logs show: "Starting GPS EXIF Tagger..."
   - Logs show: "GPS connection established" (within 30 seconds)
   - Logs show: "Started watching for photos..."
   - No error messages

5. **Pass Criteria:**
   - ✓ Service reaches "active" state
   - ✓ GPS connection established within 30s
   - ✓ No errors in logs
   - ✓ Process is running (check PID in systemctl status)

---

## Test 3: GPS Data Acquisition

**Objective:** Verify service can read GPS data from gpsd.

**Duration:** 5 minutes

**Procedure:**

1. Monitor service logs in real-time:
   ```bash
   sudo journalctl -u $SERVICE -f
   ```

2. In another terminal, verify GPS data:
   ```bash
   # Check gpsd is providing data
   gpspipe -w | head -n 10

   # Check GPS fix status
   cgps
   ```

3. **Expected Results:**
   - Service logs show GPS coordinates in verbose mode
   - gpsd shows MODE=3 (3D fix)
   - cgps shows valid latitude/longitude

4. **Pass Criteria:**
   - ✓ Service shows GPS coordinates in logs
   - ✓ Coordinates match cgps output
   - ✓ No "GPS unavailable" errors

---

## Test 4: Photo Processing

**Objective:** Verify service detects new photos and embeds GPS EXIF data.

**Duration:** 15 minutes

**Procedure:**

1. Clear any existing test photos (optional):
   ```bash
   # Be careful with this command!
   # For production: ls /var/lib/mothbox/photos/
   # For legacy: ls /home/pi/Desktop/Mothbox/Firmware/photos/
   ```

2. Start monitoring service logs:
   ```bash
   sudo journalctl -u $SERVICE -f
   ```

3. In another terminal, take a test photo:
   ```bash
   # For production (5.x firmware):
   cd /opt/mothbox
   python3 5.x/TakePhoto.py

   # For legacy (5.x firmware):
   cd /home/pi/Desktop/Mothbox/Firmware
   python3 5.x/TakePhoto.py
   ```

4. Watch service logs for processing:
   - Should see: "New photo detected: [filename]"
   - Should see: "Processing photo: [filename]"
   - Should see: "Successfully embedded GPS EXIF data"

5. Verify EXIF data was embedded:
   ```bash
   # For production:
   LATEST_PHOTO=$(ls -t /var/lib/mothbox/photos/*.jpg | head -n 1)

   # For legacy:
   LATEST_PHOTO=$(ls -t /home/pi/Desktop/Mothbox/Firmware/photos/*.jpg | head -n 1)

   # Check EXIF data
   exiftool "$LATEST_PHOTO" | grep GPS
   ```

6. **Expected EXIF Tags:**
   ```
   GPS Latitude                    : [value] N (or S)
   GPS Longitude                   : [value] E (or W)
   GPS Altitude                    : [value] m Above Sea Level
   GPS Altitude Ref                : Above Sea Level
   GPS Latitude Ref                : N (or S)
   GPS Longitude Ref               : E (or W)
   GPS Map Datum                   : WGS-84
   GPS Date/Time                   : [UTC timestamp]
   GPS Processing Method           : GPSD
   ```

7. **Pass Criteria:**
   - ✓ Service detects new photo within 10 seconds
   - ✓ Processing completes without errors
   - ✓ All 9 GPS EXIF tags are present
   - ✓ Coordinates match current location
   - ✓ GPSMapDatum is "WGS-84"

---

## Test 5: Resource Limits

**Objective:** Verify service stays within memory and CPU limits.

**Duration:** 5-10 minutes

**Procedure:**

1. Run resource monitoring script:
   ```bash
   chmod +x test_resource_limits.sh
   ./test_resource_limits.sh 60
   ```

2. While monitoring runs, trigger photo processing:
   ```bash
   # Take multiple photos to stress test
   for i in {1..5}; do
       python3 5.x/TakePhoto.py
       sleep 5
   done
   ```

3. **Expected Results:**
   - Peak memory < 256MB
   - CPU usage averages < 25% (brief bursts OK)
   - No OOM (Out of Memory) kills
   - Process remains stable

4. **Pass Criteria:**
   - ✓ Memory never exceeds 256MB
   - ✓ Average CPU < 25%
   - ✓ Service remains running
   - ✓ All photos processed successfully

---

## Test 6: Security Hardening

**Objective:** Verify systemd security restrictions are enforced.

**Duration:** 5 minutes

**Procedure:**

1. Check filesystem protection:
   ```bash
   sudo systemctl show $SERVICE | grep ProtectSystem
   # Expected: ProtectSystem=strict

   sudo systemctl show $SERVICE | grep ReadWritePaths
   # Expected: Should include photos directory

   sudo systemctl show $SERVICE | grep ReadOnlyPaths
   # Expected: Should include config directory
   ```

2. Check capability restrictions:
   ```bash
   sudo systemctl show $SERVICE | grep CapabilityBoundingSet
   # Expected: Empty (no special capabilities)

   sudo systemctl show $SERVICE | grep NoNewPrivileges
   # Expected: yes
   ```

3. Check kernel protection:
   ```bash
   sudo systemctl show $SERVICE | grep ProtectKernel
   # Expected: ProtectKernelTunables=yes, ProtectKernelModules=yes
   ```

4. Check system call filtering:
   ```bash
   sudo systemctl show $SERVICE | grep SystemCallFilter
   # Expected: SystemCallFilter with @system-service
   ```

5. **Pass Criteria:**
   - ✓ ProtectSystem=strict
   - ✓ CapabilityBoundingSet is empty
   - ✓ NoNewPrivileges=yes
   - ✓ ProtectKernelTunables=yes
   - ✓ SystemCallFilter is active

---

## Test 7: Error Recovery

**Objective:** Verify service handles errors gracefully and recovers.

**Duration:** 10 minutes

**Test 7a: GPS Signal Loss**

1. While service is running, temporarily block GPS signal:
   - Cover GPS antenna with metal object
   - Or disconnect GPS module

2. Monitor logs:
   ```bash
   sudo journalctl -u $SERVICE -f
   ```

3. **Expected Behavior:**
   - Service continues running
   - Logs show "GPS unavailable" or "Waiting for GPS fix"
   - Photos taken during outage remain unprocessed or get skipped

4. Restore GPS signal and verify recovery:
   - Remove obstruction
   - Wait for GPS fix
   - Take new photo
   - Verify GPS EXIF is embedded

**Test 7b: Service Crash Recovery**

1. Kill service process:
   ```bash
   PID=$(systemctl show $SERVICE -p MainPID --value)
   sudo kill -9 $PID
   ```

2. Check service restarts automatically:
   ```bash
   sleep 35  # Wait for RestartSec=30s + margin
   sudo systemctl status $SERVICE
   ```

3. **Expected Behavior:**
   - Service automatically restarts (Restart=on-failure)
   - New PID assigned
   - Service returns to "active" state
   - GPS reconnects

4. **Pass Criteria:**
   - ✓ Service survives GPS signal loss
   - ✓ Service auto-restarts after crash
   - ✓ No data corruption

---

## Test 8: Service Lifecycle

**Objective:** Verify service management commands work correctly.

**Duration:** 5 minutes

**Procedure:**

1. Stop service:
   ```bash
   sudo systemctl stop $SERVICE
   sudo systemctl status $SERVICE
   ```
   - Expected: "inactive (dead)"

2. Start service:
   ```bash
   sudo systemctl start $SERVICE
   sleep 5
   sudo systemctl status $SERVICE
   ```
   - Expected: "active (running)"

3. Restart service:
   ```bash
   sudo systemctl restart $SERVICE
   sleep 5
   sudo systemctl status $SERVICE
   ```
   - Expected: New PID, "active (running)"

4. Check boot persistence:
   ```bash
   sudo systemctl is-enabled $SERVICE
   ```
   - Expected: "enabled"

5. Disable and re-enable:
   ```bash
   sudo systemctl disable $SERVICE
   sudo systemctl is-enabled $SERVICE  # Should show "disabled"

   sudo systemctl enable $SERVICE
   sudo systemctl is-enabled $SERVICE  # Should show "enabled"
   ```

6. **Pass Criteria:**
   - ✓ All systemctl commands execute without errors
   - ✓ Service responds correctly to start/stop/restart
   - ✓ Service is enabled for boot

---

## Cleanup

After completing all tests:

1. Leave service in desired state:
   ```bash
   # Option A: Leave running
   sudo systemctl start $SERVICE

   # Option B: Stop for now
   sudo systemctl stop $SERVICE
   ```

2. Review test results:
   - Document any failures
   - Note performance metrics
   - Save logs if needed:
     ```bash
     sudo journalctl -u $SERVICE --since today > gps-exif-test-logs.txt
     ```

3. Clean up test photos (optional):
   ```bash
   # Be careful! This deletes photos
   # Only run if test photos are not needed
   # rm /var/lib/mothbox/photos/test_*.jpg
   ```

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| 1. Installation Verification | ☐ Pass ☐ Fail | |
| 2. Service Startup | ☐ Pass ☐ Fail | |
| 3. GPS Data Acquisition | ☐ Pass ☐ Fail | |
| 4. Photo Processing | ☐ Pass ☐ Fail | |
| 5. Resource Limits | ☐ Pass ☐ Fail | |
| 6. Security Hardening | ☐ Pass ☐ Fail | |
| 7. Error Recovery | ☐ Pass ☐ Fail | |
| 8. Service Lifecycle | ☐ Pass ☐ Fail | |

---

## Troubleshooting

### Service Won't Start
- Check logs: `sudo journalctl -u $SERVICE -n 100`
- Verify Python script exists and has correct permissions
- Check WorkingDirectory matches installation

### GPS Connection Fails
- Test gpsd: `cgps`, `gpspipe -r`
- Verify GPS hardware: Check wiring, antenna position
- Check gpsd service: `sudo systemctl status gpsd`

### Photos Not Processed
- Verify photos directory is writable: `ls -la /var/lib/mothbox/photos`
- Check service is watching correct directory
- Verify inotify limits: `cat /proc/sys/fs/inotify/max_user_watches`

### EXIF Data Missing
- Test gps_exif_tagger.py manually:
  ```bash
  python3 /opt/mothbox/gps_exif_tagger.py --mode immediate --verbose
  ```
- Check if exiftool is installed: `which exiftool`
- Verify GPS data is valid (not null/empty)
