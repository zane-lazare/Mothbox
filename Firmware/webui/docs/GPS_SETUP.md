# GPS Module Setup Guide - Mothbox WebUI

## Overview

This guide covers the complete setup and configuration of GPS modules (NEO-M8N, NEO-6M, etc.) for the Mothbox system. The GPS integration provides:

- **Automatic time synchronization** - Sets system time from GPS satellites
- **Location tracking** - Records GPS coordinates for each deployment
- **Timezone detection** - Automatically configures timezone based on GPS location
- **WebUI control** - Configure and monitor GPS through the web interface

## Supported Hardware

### NEO-M8N-0-10 GPS Module (Recommended)
- **Interface:** UART (serial via GPIO) or USB
- **Protocol:** NMEA 0183 / UBX binary
- **Default Baudrate:** 9600 bps (configurable: 4800-115200)
- **Power:** 3.3V or 5V
- **Update Rate:** Up to 10Hz
- **Supported Systems:** GPS, GLONASS, BeiDou, Galileo
- **Time To First Fix (TTFF):**
  - Hot start (< 4 hours): ~1 second
  - Warm start (4h - 6 days): ~26 seconds
  - Cold start (6-28 days): 26-57 seconds
  - Almanac expired (> 28 days): 12-20 minutes

### Other Compatible GPS Modules
- NEO-6M (GPS only, older generation)
- Any NMEA 0183 compatible GPS module with UART or USB interface

---

## Hardware Installation

### 1. GPIO Wiring (Recommended for Raspberry Pi)

**NEO-M8N to Raspberry Pi GPIO Connection:**

```
NEO-M8N Pin    →    Raspberry Pi GPIO Pin
───────────────────────────────────────────
VCC (3.3V-5V)  →    Pin 1 (3.3V) or Pin 2 (5V)
GND            →    Pin 6 (GND) or any ground pin
TX (Transmit)  →    Pin 10 (GPIO 15 / RX)
RX (Receive)   →    Pin 8  (GPIO 14 / TX)
```

**Visual Diagram:**
```
   Raspberry Pi GPIO Header (Top View)
   ====================================

   3.3V  [1] [2]  5V      ← Connect VCC here (3.3V recommended)
        [3] [4]  5V
        [5] [6]  GND     ← Connect GND here
   TX  [7] [8]  GPIO14   ← Connect GPS RX here
        [9] [10] GPIO15   ← Connect GPS TX here
```

**Important Notes:**
- **GPIO14 (Pin 8)** = Raspberry Pi TX → GPS RX
- **GPIO15 (Pin 10)** = Raspberry Pi RX → GPS TX
- Use **3.3V power** if your GPS module supports it (safer for Pi GPIO)
- If using **5V power**, ensure your GPS module has level shifting for TX/RX pins

### 2. USB Connection (Alternative)

If using a USB GPS module:
1. Plug GPS module into USB port
2. Device will appear as `/dev/ttyUSB0` or `/dev/ttyACM0`
3. No GPIO configuration needed
4. Skip UART configuration steps below

### 3. Antenna Installation

**Critical for GPS functionality:**
- **Outdoor placement** - GPS requires line-of-sight to satellites
- **Clear sky view** - Avoid placing near buildings, trees, or metal objects
- **Horizontal mounting** - Keep antenna parallel to ground for best reception
- **Weather protection** - Use weatherproof enclosure for outdoor installations

**Indoor testing:** GPS will work indoors near windows, but expect:
- Longer acquisition times (5-20 minutes for first fix)
- Reduced accuracy
- Intermittent signal loss

---

## Software Configuration

### Step 1: Install Required Packages

```bash
sudo apt update
sudo apt install -y gpsd gpsd-clients python3-gps
```

**Package descriptions:**
- `gpsd` - GPS daemon that interfaces with GPS hardware
- `gpsd-clients` - Testing utilities (`cgps`, `gpsmon`, `gpspipe`)
- `python3-gps` - Python GPS library (used by GPS.py script)

### Step 2: Install Python Dependencies

```bash
pip3 install timezonefinder
```

The `timezonefinder` library enables automatic timezone detection based on GPS coordinates.

### Step 3: Configure UART (GPIO Connection Only)

**For Raspberry Pi 3/4:**

Edit `/boot/config.txt` (or `/boot/firmware/config.txt` on newer Pi OS):

```bash
sudo nano /boot/config.txt
```

Add these lines:

```
# Enable UART for GPS
enable_uart=1

# Disable Bluetooth to free up UART0 for GPS
dtoverlay=disable-bt
```

**For Raspberry Pi 5:**

```
# Enable UART for GPS
enable_uart=1

# Raspberry Pi 5 specific overlays
dtoverlay=disable-bt-pi5
dtoverlay=uart0-pi5
```

**Remove Serial Console (if present):**

Edit `/boot/cmdline.txt`:

```bash
sudo nano /boot/cmdline.txt
```

Remove any `console=serial0,115200` or `console=ttyAMA0,115200` entries.

**Save and reboot:**

```bash
sudo reboot
```

### Step 4: Configure gpsd

The GPS WebUI automatically configures gpsd when you change device or baudrate settings. For manual configuration:

Create/edit `/etc/default/gpsd`:

```bash
sudo nano /etc/default/gpsd
```

**For GPIO/UART GPS (default):**

```bash
# Start gpsd automatically
START_DAEMON="true"

# GPS device path
DEVICES="/dev/ttyAMA0"

# gpsd options
# -n: Don't wait for client to connect
# -s: Set GPS speed/baudrate (configures the GPS module)
GPSD_OPTIONS="-n -s 9600"

# Listen socket
GPSD_SOCKET="/var/run/gpsd.sock"
```

**For USB GPS:**

```bash
DEVICES="/dev/ttyUSB0"
GPSD_OPTIONS="-n -s 9600"
```

**Restart gpsd service:**

```bash
sudo systemctl stop gpsd.socket
sudo systemctl stop gpsd
sudo systemctl enable gpsd
sudo systemctl start gpsd
```

### Step 5: Configure Mothbox GPS Settings

Edit `controls.txt` to enable GPS:

```bash
nano ~/Mothbox/5.x/controls.txt
```

Update these values:

```
gps_enabled=true
gps_device=/dev/ttyAMA0
gps_baudrate=9600

# Adaptive timeout settings (in seconds)
gps_timeout_hot=15        # Hot start (< 4 hours since last sync)
gps_timeout_warm=60       # Warm start (4h - 6 days)
gps_timeout_cold=90       # Cold start (6-28 days)
gps_timeout_almanac=1200  # Almanac expired (> 28 days) - 20 minutes
```

**Timeout Recommendations:**
- **Hot start (15s):** GPS has recent data, very fast acquisition
- **Warm start (60s):** GPS needs fresh ephemeris data
- **Cold start (90s):** GPS must download ephemeris from satellites
- **Almanac expired (1200s / 20 min):** First sync after long power-off

---

## Testing and Verification

### 1. Test Raw GPS Data

Verify GPS is receiving data:

```bash
cat /dev/ttyAMA0
```

**Expected output (NMEA sentences):**
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPGSA,A,3,04,05,,09,12,,,24,,,,,2.5,1.3,2.1*39
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```

If you see garbage or nothing:
- Check wiring (TX/RX may be swapped)
- Verify baudrate matches GPS module (try 4800 or 9600)
- Ensure GPS has antenna connected and clear sky view

### 2. Test gpsd

**Check gpsd status:**

```bash
sudo systemctl status gpsd
```

Should show `active (running)`.

**Interactive GPS monitor:**

```bash
cgps
```

**Expected output:**
```
┌───────────────────────────────────────────┐
│Time:       2025-10-26T14:30:45.000Z      │
│Latitude:    42.3601 N                     │
│Longitude:   71.0589 W                     │
│Altitude:    10.5 m                        │
│Speed:       0.0 km/h                      │
│Satellites:  8 used / 12 visible           │
└───────────────────────────────────────────┘
```

**Raw GPS data via gpsd:**

```bash
gpspipe -r
```

**GPS monitor with satellite details:**

```bash
gpsmon
```

### 3. Test GPS.py Script

Run the Mothbox GPS script manually:

```bash
cd ~/Mothbox/5.x
python3 GPS.py
```

**Expected output:**
```
startingGPS
TPV: 42.3601  -71.0589  2025-10-26T14:30:45.000Z  alt=10.5  mode=3  epv=5.0  ept=0.005
SKY: nSat=12, uSat=8, HDOP=1.20, PDOP=2.10
Finished Looking for GPS. GPS device found = True
Epoch time: 1729954245
System UTC time set.
Setting system timezone to: America/New_York
UTC Offset (hours): -4
Updated lat=42.3601
Updated lon=-71.0589
Updated gpstime=1729954245
Updated UTCoff=-4
```

Check GPS values in controls.txt:

```bash
grep -E "^(lat|lon|gpstime|UTCoff)=" ~/Mothbox/5.x/controls.txt
```

### 4. Test WebUI Integration

1. Open Mothbox WebUI in browser: `http://mothbox.local`
2. Navigate to **Settings** page
3. Scroll to **GPS Module Configuration** section
4. Verify GPS is enabled and configured correctly
5. Click **Sync GPS Now** button
6. Check **Dashboard** for GPS status

---

## WebUI Configuration

### GPS Settings Panel

**Location:** Settings → GPS Module Configuration

**Configuration Options:**

1. **Enable GPS Module** - Toggle GPS functionality on/off

2. **GPS Device Path**
   - Default: `/dev/ttyAMA0` (GPIO UART)
   - USB GPS: `/dev/ttyUSB0` or `/dev/ttyACM0`
   - Click **Save Configuration** after changing

3. **Baud Rate**
   - Default: 9600 (NEO-M8N default)
   - Options: 4800, 9600, 19200, 38400, 57600, 115200
   - Must match GPS module configuration

4. **Advanced Timeout Configuration** (Collapsible)
   - **Hot Start (< 4 hours):** 5-60 seconds (default: 15s)
   - **Warm Start (4h-6d):** 30-180 seconds (default: 60s)
   - **Cold Start (6-28d):** 60-300 seconds (default: 90s)
   - **Almanac Expired (> 28d):** 5-30 minutes (default: 20 min)

**Adaptive Timeout System:**

The WebUI automatically selects the appropriate timeout based on how long since the last GPS sync:

- **Recent sync (< 4 hours ago):** Uses hot start timeout (~15s)
- **Moderate gap (4h - 6 days):** Uses warm start timeout (~60s)
- **Long gap (6-28 days):** Uses cold start timeout (~90s)
- **Very long gap (> 28 days):** Uses almanac timeout (~20 min)

This ensures quick GPS acquisition when satellites are readily available, while allowing enough time for initial sync after long power-off periods.

### Dashboard GPS Widget

**Location:** Dashboard → GPS Status Card

**Displayed Information:**
- GPS fix status (green = fix acquired, red = no fix)
- Latitude and longitude coordinates
- UTC offset (timezone offset from UTC)
- Last sync timestamp
- **Sync Now** button for manual GPS sync

### Current GPS Status (Settings Page)

Shows real-time GPS quality metrics:
- **Fix Type:** 2D or 3D fix
- **Satellites:** Used / Visible count (e.g., "8/12 satellites")
- **HDOP:** Horizontal Dilution of Precision (accuracy indicator)
  - < 2: Excellent
  - 2-5: Good
  - 5-10: Fair
  - > 10: Poor
- **PDOP:** Position Dilution of Precision
- **Last Known Position:** Preserved coordinates when GPS loses fix

---

## Understanding GPS Behavior

### Time To First Fix (TTFF)

GPS acquisition time depends on how long since last sync:

| GPS State | Time Since Last Sync | Expected TTFF | Why It Takes This Long |
|-----------|---------------------|---------------|------------------------|
| **Hot Start** | < 4 hours | ~1 second | GPS has valid ephemeris, almanac, and recent position |
| **Warm Start** | 4 hours - 6 days | ~26 seconds | GPS has almanac but needs fresh ephemeris data |
| **Cold Start** | 6 - 28 days | 26-57 seconds | GPS must download ephemeris from satellites |
| **Almanac Expired** | > 28 days | 12-20 minutes | GPS must download full almanac (broadcast every 12.5 min) |

**Ephemeris Data:** Precise satellite orbit information, valid for ~4 hours, broadcast every 30 seconds

**Almanac Data:** Coarse satellite orbit information, valid for ~180 days, broadcast every 12.5 minutes

### GPS Quality Metrics

**Fix Mode:**
- **0:** No fix - GPS has no position lock
- **2:** 2D fix - Latitude/longitude only (< 4 satellites)
- **3:** 3D fix - Latitude/longitude/altitude (4+ satellites)

**HDOP (Horizontal Dilution of Precision):**
- Measures horizontal position accuracy
- Lower is better (1.0 = ideal, > 20 = poor)
- Affected by satellite geometry (spacing in sky)

**PDOP (Position Dilution of Precision):**
- Measures overall 3D position accuracy
- Combines horizontal and vertical accuracy
- Good satellite coverage results in lower PDOP

**Satellite Count:**
- **Used:** Satellites actively contributing to position fix
- **Visible:** Total satellites GPS can detect above horizon
- Need minimum 4 satellites for 3D fix
- More satellites = better accuracy and faster acquisition

### Last Known Position Tracking

The GPS system preserves the last valid position even when GPS signal is lost:

**Behavior:**
- When GPS acquires a fix → Updates current position AND saves to "last known position"
- When GPS loses fix → Current position shows "n/a", but last known position is preserved
- When GPS regains fix → Updates both current and last known position

**Use Cases:**
- Continuous position tracking even with intermittent GPS signal
- Fallback location data when GPS is temporarily unavailable
- Historical position reference

---

## Troubleshooting

### GPS Won't Acquire Fix

**Symptoms:** GPS sync times out, no coordinates displayed

**Solutions:**

1. **Verify Antenna Placement**
   - Move to outdoor location with clear sky view
   - Avoid indoors, near buildings, or under tree cover
   - Ensure antenna is horizontal and not obstructed

2. **Check Hardware Connections**
   ```bash
   # Verify GPS device exists
   ls -l /dev/ttyAMA0

   # Test raw GPS data
   cat /dev/ttyAMA0
   ```
   Should show NMEA sentences. If not, check wiring.

3. **Verify gpsd is Running**
   ```bash
   sudo systemctl status gpsd
   ```
   Should show "active (running)". If not:
   ```bash
   sudo systemctl restart gpsd
   ```

4. **Check Satellite Visibility**
   ```bash
   cgps
   ```
   Look for "Satellites: X used / Y visible"
   - If visible = 0: Antenna problem or no clear sky view
   - If visible > 0 but used = 0: Wait longer (cold start can take 5-20 min)

5. **Increase Timeout**
   - First sync after long power-off can take 12-20 minutes
   - In WebUI Settings → GPS → Advanced Timeout Configuration
   - Set "Almanac Expired" timeout to 1800s (30 minutes)

6. **Be Patient on Cold Start**
   - After 28+ days powered off, GPS needs to download full almanac
   - This broadcasts every 12.5 minutes from satellites
   - Expected wait: 12-20 minutes for first fix
   - Subsequent fixes will be much faster (< 1 minute)

### GPS Shows Old/Incorrect Coordinates

**Symptoms:** Dashboard shows coordinates from previous location

**Explanation:** This is the "Last Known Position" feature - working as designed

**To Get Current Position:**
1. Click **Sync Now** button
2. Wait for GPS to acquire fix (15s - 20 min depending on GPS state)
3. New coordinates will update once fix is acquired

**Note:** If GPS cannot get a fix (indoors, no antenna), last known position will persist

### Wrong Baud Rate

**Symptoms:** `cat /dev/ttyAMA0` shows garbage characters

**Solution:**
Most GPS modules default to 9600 baud. Try:
```bash
# Test different baud rates
stty -F /dev/ttyAMA0 4800 && cat /dev/ttyAMA0
stty -F /dev/ttyAMA0 9600 && cat /dev/ttyAMA0
```

Once you find the correct baud rate, update in WebUI Settings → GPS Configuration.

### TX/RX Wires Swapped

**Symptoms:** No data from GPS, or partial/corrupted data

**Solution:**
- GPS **TX** must connect to Pi **RX** (GPIO 15, Pin 10)
- GPS **RX** must connect to Pi **TX** (GPIO 14, Pin 8)
- Swap the wires if connected incorrectly

### gpsd Not Seeing GPS Device

**Symptoms:** `cgps` shows "No GPS data available"

**Check gpsd configuration:**
```bash
cat /etc/default/gpsd
```

Verify `DEVICES="/dev/ttyAMA0"` points to correct device.

**Restart gpsd:**
```bash
sudo systemctl stop gpsd.socket
sudo systemctl stop gpsd
sudo systemctl start gpsd
```

**Check for device conflicts:**
```bash
sudo lsof /dev/ttyAMA0
```
If other processes are using the device, stop them.

### Bluetooth Conflict (Pi 3/4/5)

**Symptoms:** GPS not working after enabling UART

**Solution:**
Bluetooth uses the same UART as GPS by default. Disable Bluetooth:

Edit `/boot/config.txt`:
```bash
# Raspberry Pi 3/4
dtoverlay=disable-bt

# Raspberry Pi 5
dtoverlay=disable-bt-pi5
```

Reboot after changes.

### Serial Console Conflict

**Symptoms:** GPS data mixed with boot messages

**Solution:**
Remove serial console from boot command line.

Edit `/boot/cmdline.txt` and remove:
```
console=serial0,115200 console=ttyAMA0,115200
```

Reboot after changes.

### GPS Works in cgps but Not in WebUI

**Symptoms:** `cgps` shows GPS data, but WebUI sync fails

**Check GPS.py script:**
```bash
cd ~/Mothbox/5.x
python3 GPS.py
```

Look for Python errors or timeout messages.

**Verify controls.txt permissions:**
```bash
ls -l ~/Mothbox/5.x/controls.txt
```
Should be writable by the user running GPS.py.

**Check WebUI logs:**
```bash
# If running as systemd service
sudo journalctl -u mothbox-webui -f
```

### Slow GPS Acquisition

**Symptoms:** GPS sync takes 5-20 minutes every time

**Causes:**
- Almanac expired (> 28 days since last sync)
- Poor satellite visibility
- Obstructed antenna

**Solutions:**
1. **Run GPS Sync Regularly**
   - Schedule daily GPS sync to maintain "hot start" state
   - Hot start takes ~15 seconds vs. 12-20 minutes for almanac download

2. **Improve Antenna Placement**
   - Move antenna to location with better sky view
   - Avoid metal structures, buildings, trees

3. **Wait for Almanac Download**
   - First sync after long power-off requires full almanac
   - Be patient - this is normal GPS behavior
   - Subsequent syncs will be much faster

---

## Advanced Topics

### Multiple GPS Devices

To use multiple GPS modules (e.g., backup GPS):

Edit `/etc/default/gpsd`:
```bash
DEVICES="/dev/ttyAMA0 /dev/ttyUSB0"
```

gpsd will use the first device with valid data.

### Custom GPS Module Configuration

Some GPS modules can be configured via UBX binary protocol:

**Change GPS Update Rate:**
```bash
# Requires ubxtool from gpsd-clients
ubxtool -P 27.15 -s 38400  # Set update rate to 10Hz
```

**Change Baud Rate Permanently:**
Most GPS modules default to 9600 baud. To change permanently, consult your GPS module's documentation for UBX configuration commands.

### GPS Data Logging

To log raw NMEA data for debugging:

```bash
gpspipe -r > gps_log.nmea
```

Stop with Ctrl+C. Analyze with:
```bash
less gps_log.nmea
```

### Precision Time Sync

GPS provides extremely accurate time (within 100 nanoseconds of UTC):

**Use GPS as NTP time source:**
1. Install gpsd-ntp package
2. Configure chronyd or ntpd to use gpsd SOCK clock
3. System time will sync to GPS time automatically

---

## File Locations Reference

| File/Directory | Purpose |
|----------------|---------|
| `/dev/ttyAMA0` | GPIO UART device (Pi GPIO pins 8/10) |
| `/dev/ttyUSB0` | USB GPS device (may be ttyACM0) |
| `/boot/config.txt` | Pi hardware configuration (UART, Bluetooth) |
| `/boot/cmdline.txt` | Pi boot command line (serial console) |
| `/etc/default/gpsd` | gpsd daemon configuration |
| `~/Mothbox/5.x/GPS.py` | Mothbox GPS sync script |
| `~/Mothbox/5.x/controls.txt` | Mothbox GPS configuration and data storage |
| `/var/run/gpsd.sock` | gpsd socket for client connections |

---

## Additional Resources

**Official Documentation:**
- gpsd: https://gpsd.gitlab.io/gpsd/
- NEO-M8N Datasheet: https://www.u-blox.com/en/product/neo-m8-series

**Useful Commands:**
```bash
# GPS status
cgps                    # Interactive GPS monitor
gpsmon                  # Detailed satellite view
gpspipe -r              # Raw NMEA data
gpspipe -w              # JSON GPS data

# System status
systemctl status gpsd   # gpsd service status
dmesg | grep tty        # Check UART devices
ls -l /dev/tty*         # List serial devices

# Testing
cat /dev/ttyAMA0        # Raw GPS serial data
gpsd -D 5 -N -n /dev/ttyAMA0  # Run gpsd in foreground with debug
```

**Getting Help:**
- Check WebUI Settings → GPS Configuration for inline help
- Review gpsd logs: `journalctl -u gpsd`
- Test with `cgps` to isolate hardware vs. software issues
- Verify antenna has clear sky view (most common issue)

---

## FAQ

**Q: Why does GPS take 20 minutes on first sync?**

A: After 28+ days powered off, the GPS almanac expires. GPS must download a new almanac from satellites, which broadcasts every 12.5 minutes. This is normal GPS behavior. Subsequent syncs will be much faster (15-60 seconds).

**Q: Can I use GPS indoors?**

A: Limited. GPS works best outdoors with clear sky view. Indoors near windows may work but expect:
- Longer acquisition times (5-20 minutes)
- Lower accuracy
- Intermittent signal loss

**Q: Do I need an active (powered) GPS antenna?**

A: No, passive antennas work fine for most applications. Active antennas (with built-in amplifier) are useful for:
- Very long antenna cables (> 5 meters)
- Indoor installations with poor signal
- Metal enclosures that block GPS signals

**Q: Why does the Dashboard show old coordinates?**

A: The "Last Known Position" feature preserves the last valid GPS fix. Click "Sync Now" to get current coordinates. If indoors or without antenna, GPS cannot acquire a new fix, so last known position is displayed.

**Q: How accurate is GPS?**

A: Consumer GPS modules like NEO-M8N provide:
- Horizontal accuracy: 2.5 meters (typical)
- Time accuracy: 100 nanoseconds to UTC
- Altitude accuracy: 5 meters (typical)

Accuracy depends on satellite geometry, signal quality, and environmental factors.

**Q: Can I change the GPS update rate?**

A: Yes, but it doesn't affect time sync (which happens once per manual/scheduled sync). To change update rate for real-time tracking applications, use ubxtool or GPS manufacturer's configuration software.

**Q: What's the difference between /dev/ttyAMA0 and /dev/serial0?**

A: `/dev/serial0` is a symlink that points to the primary UART:
- Pi 3/4: Points to `/dev/ttyS0` (mini-UART) or `/dev/ttyAMA0` (full UART)
- Pi 5: Points to `/dev/ttyAMA0`

For GPS, use `/dev/ttyAMA0` directly to avoid confusion.

**Q: Does GPS work without internet?**

A: Yes! GPS is completely independent of internet connectivity. It receives signals directly from satellites. Internet is only used by the WebUI for remote access.
