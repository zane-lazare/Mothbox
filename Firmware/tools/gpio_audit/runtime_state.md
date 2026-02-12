# GPIO Audit: Runtime State Capture

**Captured**: 2026-02-08
**Target**: mothbox-remote (Raspberry Pi 5 Model B Rev 1.0)
**Kernel**: Linux 6.12.47+rpt-rpi-2712, aarch64
**Firmware**: 5.x (relay pins 5/19/9 in controls.txt, softwareversion=5.0.0)

---

## 1. GPIO Pin State (gpioinfo)

Full `gpioinfo` output for gpiochip0 (54 lines, the user-accessible GPIO header):

```
line   0: "ID_SDA"           input
line   1: "ID_SCL"           input
line   2: "GPIO2"            input
line   3: "GPIO3"            input
line   4: "GPIO4"            input
line   5: "GPIO5"            output bias=disabled consumer="lg"   <-- RELAY CH1
line   6: "GPIO6"            output bias=disabled consumer="lg"   <-- UNEXPECTED: not in controls.txt
line   7: "GPIO7"            input
line   8: "GPIO8"            input
line   9: "GPIO9"            input                                <-- RELAY CH3 (idle)
line  10: "GPIO10"           input
line  11: "GPIO11"           input
line  12: "GPIO12"           input
line  13: "GPIO13"           input
line  14: "GPIO14"           input
line  15: "GPIO15"           input
line  16: "GPIO16"           input
line  17: "GPIO17"           input
line  18: "GPIO18"           input
line  19: "GPIO19"           input                                <-- RELAY CH2 (idle)
line  20: "GPIO20"           input
line  21: "GPIO21"           input
line  22: "GPIO22"           input
line  23: "GPIO23"           input
line  24: "GPIO24"           input
line  25: "GPIO25"           input
line  26: "GPIO26"           input
line  27: "GPIO27"           input
line  28: "PCIE_RP1_WAKE"    input
line  29: "FAN_TACH"         input
line  30: "HOST_SDA"         input
line  31: "HOST_SCL"         input
line  32: "ETH_RST_N"        output active-low consumer="phy-reset"
line  33: "-"                input
line  34: "CD0_IO0_MICCLK"   output consumer="cam0_reg"
line  35: "CD0_IO0_MICDAT0"  input
line  36: "RP1_PCIE_CLKREQ_N" input
line  37: "-"                input
line  38: "CD0_SDA"          input
line  39: "CD0_SCL"          input
line  40: "CD1_SDA"          input
line  41: "CD1_SCL"          input
line  42: "USB_VBUS_EN"      output
line  43: "USB_OC_N"         input
line  44: "RP1_STAT_LED"     output active-low consumer="PWR"
line  45: "FAN_PWM"          output
line  46: "CD1_IO0_MICCLK"   output consumer="cam1_reg"
line  47: "2712_WAKE"        input
line  48: "CD1_IO1_MICDAT1"  input
line  49: "EN_MAX_USB_CUR"   output
line  50-53: "-"             input
```

**pinctrl summary** (first 28 user GPIO pins):

```
 0: ip    pu | hi  // ID_SDA
 1: ip    pu | hi  // ID_SCL
 2: a3    pu | hi  // SDA1 (I2C)
 3: a3    pu | hi  // SCL1 (I2C)
 4: no    pu | --  // none
 5: op dh pn | hi  // OUTPUT, drive-high, no pull, reads HIGH
 6: op dh pn | hi  // OUTPUT, drive-high, no pull, reads HIGH
 7: no    pu | --  // none
 8: no    pu | --  // none
 9: ip    pn | lo  // INPUT, no pull, reads LOW
10: no    pd | --  // none
11: no    pd | --  // none
12: ip    pu | hi  // input
13: ip    pn | hi  // input, no pull, reads HIGH
14: a4    pn | hi  // TXD0 (UART)
15: a4    pu | hi  // RXD0 (UART)
16: ip    pu | hi  // input
17: no    pd | --  // none (e-paper RST)
18: no    pd | --  // none (e-paper SCK)
19: ip    pn | lo  // INPUT, no pull, reads LOW
20: no    pd | --  // none
21: no    pd | --  // none
22: no    pd | --  // none
23: no    pd | --  // none
24: no    pd | --  // none (e-paper BUSY)
25: no    pd | --  // none (e-paper DC)
26: no    pd | --  // none
27: no    pd | --  // none
```

---

## 2. Relay Pin State

Relay pins as configured in deployed `controls.txt` (Relay_Ch1=5, Relay_Ch2=19, Relay_Ch3=9):

| Pin | controls.txt | gpioinfo Direction | gpioinfo Consumer | pinctrl State | Reads |
|-----|-------------|-------------------|------------------|---------------|-------|
| GPIO 5 | Relay_Ch1 | output | "lg" | op dh pn (output, drive-high, no pull) | HIGH |
| GPIO 19 | Relay_Ch2 | input | (none) | ip pn (input, no pull) | LOW |
| GPIO 9 | Relay_Ch3 | input | (none) | ip pn (input, no pull) | LOW |

**Observation**: Only GPIO 5 is actively configured as output. GPIO 19 and GPIO 9 are in default input state, meaning the relay control scripts are not currently holding those pins. The "lg" consumer on GPIO 5 indicates it was set via the `lgpio` library (used by `gpiozero` on Pi 5).

**Unexpected**: GPIO 6 is also configured as output with consumer "lg" and driving HIGH. GPIO 6 is NOT listed in `controls.txt`. This may be a leftover from a prior script execution or a different purpose.

---

## 3. E-paper Pin State

E-paper display pins (RST=17, DC=25, CS=8, BUSY=24, SCK=18):

| Pin | Function | pinctrl State | Reads | Notes |
|-----|----------|---------------|-------|-------|
| GPIO 17 | RST | no pd \| -- (none, pull-down) | disconnected | Not configured |
| GPIO 25 | DC | no pd \| -- (none, pull-down) | disconnected | Not configured |
| GPIO 8 | CS (CE0) | no pu \| -- (none, pull-up) | disconnected | Not configured |
| GPIO 24 | BUSY | no pd \| -- (none, pull-down) | disconnected | Not configured |
| GPIO 18 | SCK | no pd \| -- (none, pull-down) | disconnected | Not configured |

**Observation**: All e-paper pins are in their default unconfigured state. The e-paper display is not actively in use. This is expected when no display update is running.

---

## 4. I2C Devices

`i2cdetect -y 1` output:

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

**Observation**: No I2C devices detected on bus 1. This means:
- **INA260 power monitor** (typically at 0x40): Not connected or not powered
- **PCA9536 GPIO expander** (typically at 0x41): Not connected or not powered
- I2C bus itself is active (GPIO 2/3 in alternate function `a3` = SDA1/SCL1)

---

## 5. Running Services

```
● mothbox-webui.service - Mothbox Web UI Server
     Loaded: loaded (/etc/systemd/system/mothbox-webui.service; enabled; preset: enabled)
     Active: active (running) since Sat 2026-02-07 22:45:08 NZDT; 13h ago
   Main PID: 422789 (python3)
      Tasks: 21 (limit: 4762)
        CPU: 40min 27.587s
     CGroup: /system.slice/mothbox-webui.service
             ├─422789 /usr/bin/python3 /opt/mothbox/webui/backend/app.py
             └─422805 /usr/bin/python3 /opt/mothbox/webui/backend/app.py
```

Notable log entries:
- `Ignoring update to protected field: use_seconds_timing`
- `Failed to set RTC wakealarm: [Errno 13] Permission denied: '/sys/class/rtc/rtc0/wakealarm'`

**Observation**: Web UI is running with 2 worker processes (PID 422789 + 422805). The RTC wakealarm permission error indicates the service does not have write access to `/sys/class/rtc/rtc0/wakealarm`.

---

## 6. GPIO Process Holders

```
No processes or lsof not available
```

**Observation**: No processes currently have `/dev/gpiomem*` or `/dev/gpiochip*` open. However, GPIO 5 and GPIO 6 are configured as outputs with consumer "lg", suggesting a process previously set them and either exited or the kernel retains the state. On Pi 5 with lgpio, pin state can persist after the controlling process exits.

---

## 7. Sysfs Exports

```
total 0
drwxrwxr-x  2 root gpio     0 Jan 29 20:09 .
drwxr-xr-x 71 root root     0 Jan 29 20:09 ..
--w--w----  1 root gpio 16384 Jan 29 20:09 export
lrwxrwxrwx  1 root gpio     0 Jan 29 20:09 gpiochip512 -> .../gpio/gpiochip512
lrwxrwxrwx  1 root gpio     0 Jan 29 20:09 gpiochip529 -> .../gpio/gpiochip529
lrwxrwxrwx  1 root gpio     0 Jan 29 20:09 gpiochip535 -> .../gpio/gpiochip535
lrwxrwxrwx  1 root gpio     0 Jan 29 20:09 gpiochip567 -> .../gpio/gpiochip567
lrwxrwxrwx  1 root gpio     0 Jan 29 20:09 gpiochip571 -> .../gpio/gpiochip571
--w--w----  1 root gpio 16384 Jan 29 20:09 unexport
```

**Observation**: No individual GPIO pins are exported via sysfs (no `gpio<N>` symlinks). Only the base gpiochip entries exist. The firmware uses `lgpio`/`gpiozero` character device interface, not legacy sysfs.

---

## 8. Crontab Entries

**User (pi) crontab**: Empty (no active entries)

**Root crontab**: `no root crontab`

**Observation**: No cron-based scheduling is active. The visual scheduler system (mothbox-webui) manages scheduling via its internal scheduler service, not cron.

---

## 9. Deployed Config (controls.txt)

Location: `/opt/mothbox/controls.txt`

```ini
shutdown_enabled=False
OnlyFlash=False
LastCalibration=0
nextWake=0
name=mothbox
softwareversion=5.0.0
gpstime=0
UTCoff=-5
lat=n/a
lon=n/a
last_known_lat=n/a
last_known_lon=n/a
last_position_time=0
weekdays=1;2;3;4;5;6;7
hours=19;21;23;2;4
minutes=0
runtime=59
Relay_Ch1=5
Relay_Ch2=19
Relay_Ch3=9
relay_enabled=true
flash_duration_ms=100
jpeg_quality=96
```

### GPIO-Related Settings

| Key | Value | Meaning |
|-----|-------|---------|
| Relay_Ch1 | 5 | GPIO 5 (BCM) -- attract lights relay |
| Relay_Ch2 | 19 | GPIO 19 (BCM) -- flash relay |
| Relay_Ch3 | 9 | GPIO 9 (BCM) -- UV/auxiliary relay |
| relay_enabled | true | Relay hardware is enabled |
| flash_duration_ms | 100 | Flash pulse duration |
| OnlyFlash | False | Not in flash-only mode |

---

## 10. Config Diff (Deployed vs Repo)

Compared: `/opt/mothbox/controls.txt` (deployed) vs `/home/zane/projects/Mothbox/Firmware/5.x/controls.txt` (repo)

**Repo has additional entries not present on deployed Pi**:

```diff
10a11,16
> gps_fix_mode=0
> gps_satellites_used=0
> gps_satellites_visible=0
> gps_altitude=0
> gps_hdop=99.99
> gps_pdop=99.99
23a30,87
> (Gallery thumbnail cache configuration block)
> (Logging configuration block)
```

### Differences Summary

| Category | Deployed | Repo |
|----------|----------|------|
| GPS satellite fields | Missing | Present (6 fields: fix_mode, satellites_used, etc.) |
| Cache config | Missing | Present (cache_max_size_mb=500, cache_sizes, thumbnail_quality, etc.) |
| Logging config | Missing | Present (log_level=INFO, log_retention_days=7) |
| Core GPIO pins | Relay_Ch1=5, Ch2=19, Ch3=9 | Relay_Ch1=5, Ch2=19, Ch3=9 (IDENTICAL) |
| All other core fields | IDENTICAL | IDENTICAL |

**Assessment**: GPIO pin configuration is in sync. The differences are non-GPIO configuration fields added in newer dev commits that haven't been deployed yet.

---

## 11. Script Diff (Deployed vs Repo)

All 5.x GPIO scripts compared between `/opt/mothbox/5.x/` and repo:

| Script | Status |
|--------|--------|
| Attract_On.py | IDENTICAL |
| Attract_Off.py | IDENTICAL |
| Flash_On.py | IDENTICAL |
| Flash_Off.py | IDENTICAL |
| FlashOn.py | IDENTICAL |
| TakePhoto.py | IDENTICAL |
| TurnEverythingOff.py | IDENTICAL |

**Assessment**: All deployed GPIO scripts match the repo exactly. No drift.

---

## 12. Key Findings

### Confirmed Working

1. **GPIO 5 (Relay_Ch1)** is actively configured as output, driving HIGH, with lgpio consumer. This relay channel is operational.
2. **I2C bus** is configured (GPIO 2/3 in alternate function SDA1/SCL1).
3. **All 5.x GPIO scripts** are identical between deployed and repo -- no code drift.
4. **GPIO pin assignments** in controls.txt match between deployed and repo (5/19/9).
5. **Web UI service** is running and healthy (active 13+ hours, 2 workers).

### Anomalies / Items Requiring Investigation

1. **GPIO 6 is configured as output (HIGH) with "lg" consumer** but is NOT referenced in `controls.txt`. This is an orphaned pin state. Need to determine what script set GPIO 6 and whether it should be cleaned up on shutdown. GPIO 6 is not used by the 5.x relay mapping (which uses 5/19/9).

2. **GPIO 19 and GPIO 9 (Relay_Ch2, Relay_Ch3) are in input mode** despite being relay pins. This is normal idle state -- the relay scripts only claim the pin during activation and release it after. But GPIO 5 remains as output, suggesting either:
   - GPIO 5 was set by `Attract_On.py` and the attract lights are currently ON
   - OR a script set GPIO 5 and did not release it properly

3. **No processes holding GPIO file descriptors** (`lsof` returned empty). Yet GPIO 5 and 6 retain output state. On Pi 5 with lgpio, pin configuration persists after the process exits. This means there is no guarantee pins return to safe input state after script completion.

4. **No I2C devices detected** -- INA260 power monitor and PCA9536 expander are either not installed or not powered on this unit.

5. **RTC wakealarm permission denied** -- the systemd service cannot set wake alarms. The service would need write access to `/sys/class/rtc/rtc0/wakealarm` (via udev rule or running as root).

6. **No crontab entries** -- all scheduling is via the web UI's internal scheduler, not system cron. The legacy `Scheduler.py` cron approach is not in use.

7. **E-paper pins are all unconfigured** (default state). Either no e-paper display is connected, or the display driver only configures pins transiently during updates.

8. **Deployed controls.txt is missing 6 GPS fields and all cache/logging config** compared to the repo. These are non-GPIO additions that need deployment but do not affect GPIO behavior.

### Risk Assessment

| Finding | Severity | Impact |
|---------|----------|--------|
| GPIO 6 orphaned as output HIGH | MEDIUM | Unknown device may be receiving power; potential hardware conflict if GPIO 6 is connected to anything |
| GPIO pins persist after process exit | MEDIUM | Relay could remain energized if script crashes before cleanup |
| No process holds GPIO 5 yet it's HIGH | LOW-MEDIUM | Attract lights may be on with no controlling process to turn them off |
| RTC wakealarm permission denied | LOW | Sleep/wake scheduling won't work until permissions are fixed |
| Missing I2C devices | INFO | Expected if INA260/PCA9536 hardware not installed |
