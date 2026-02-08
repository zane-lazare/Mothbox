# GPIO Architecture Reference

Comprehensive reference for the Mothbox firmware GPIO system. Covers every pin, signal path, library, and known issue. Intended as a self-contained document for developers working on GPIO-related code.

**Last updated**: 2026-02-08
**Based on**: GPIO System Audit (branch `dev`, production Pi 5 runtime capture, hardware polarity test)

---

## 1. Canonical Pin Map

Every GPIO pin used by the Mothbox system.

### 1.1 Relay Pins (BCM Mode)

| BCM | Physical | controls.txt Key | Controls | Dir | Firmware | Used By |
|-----|----------|------------------|----------|-----|----------|---------|
| 5 | 29 | `Relay_Ch1=5` | UV / attract lights | OUT | 5.x (code default & deployed) | Attract_On/Off.py, TakePhoto.py, DebugMode.py, gpio.py |
| 6 | 31 | `Relay_Ch2=6` | Camera flash | OUT | 5.x (deployed) | Flash_On/Off.py, TakePhoto.py, gpio.py |
| 13 | 33 | `Relay_Ch3=13` | Spare relay | OUT | 5.x (deployed) | Attract_On/Off.py, TakePhoto.py, DebugMode.py |
| 19 | 35 | `Relay_Ch2=19` | Camera flash | OUT | 5.x (code default) | Flash_On/Off.py, TakePhoto.py, gpio.py |
| 9 | 21 | `Relay_Ch3=9` | 5V buck / auxiliary | OUT | 5.x (code default) | Attract_On/Off.py, TakePhoto.py, DebugMode.py |
| 26 | 37 | `Relay_Ch1` (default) | UV / attract lights | OUT | 4.x (fallback) | 4.x/Attract_On/Off.py, 4.x/TakePhoto.py |
| 20 | 38 | `Relay_Ch2` (default) | Camera flash | OUT | 4.x (fallback) | 4.x/Attract_On/Off.py, 4.x/TakePhoto.py |
| 21 | 40 | `Relay_Ch3` (default) | 5V buck converter | OUT | 4.x (fallback) | 4.x/Attract_On/Off.py, 4.x/TakePhoto.py |

`get_gpio_pins()` falls back to the 4.x defaults (26/20/21) when `controls.txt` is missing or has parse errors. A 5.x installation **must** have explicit pin values in `controls.txt` to function correctly.

### 1.2 Physical Switch Pins (BCM Mode, Hardcoded)

| BCM | Physical | Controls | Dir | Pull | Used By |
|-----|----------|----------|-----|------|---------|
| 16 | 36 | Off switch | IN | PUD_UP | Scheduler.py, TakePhoto.py, UpdateDisplay.py, CheckGPIOPin.py |
| 12 | 32 | Debug switch | IN | PUD_UP | Scheduler.py, TakePhoto.py, UpdateDisplay.py, CheckGPIOPin.py |

These pins are **not configurable** via `controls.txt`. They are hardcoded in 8 files across both firmware versions.

**Switch logic**: Internal pull-up enabled. Pin grounded (LOW) = switch activated. Both HIGH = ACTIVE mode. Pin 12 LOW = DEBUG mode. Pin 16 LOW = OFF mode (overrides DEBUG).

### 1.3 E-paper Display Pins (BCM Mode, Configurable)

| BCM | Physical | controls.txt Key | Function | Dir |
|-----|----------|------------------|----------|-----|
| 17 | 11 | `epaper_rst_pin` | RST (reset) | OUT |
| 25 | 22 | `epaper_dc_pin` | DC (data/command) | OUT |
| 8 | 24 | `epaper_cs_pin` | CS (chip select / CE0) | OUT |
| 24 | 18 | `epaper_busy_pin` | BUSY | IN |
| 18 | 12 | `epaper_pwr_pin` | PWR (power) | OUT |
| 11 | 23 | (hardware SPI) | SPI CLK | ALT |
| 10 | 19 | (hardware SPI) | SPI MOSI | ALT |

Managed by the Waveshare e-paper driver library (`epdconfig.py`), not directly by Mothbox scripts.

### 1.4 Multiplexer Pins (BOARD Mode, Configurable)

| BOARD | BCM | controls.txt Key | Function | Dir |
|-------|-----|------------------|----------|-----|
| 31 | 6 | `mux_en_a` | Enable MUX A | OUT |
| 29 | 5 | `mux_en_b` | Enable MUX B | OUT |
| 33 | 13 | `mux_s0` | Channel select bit 0 | OUT |
| 13 | 27 | `mux_s1` | Channel select bit 1 | OUT |
| 12 | 18 | `mux_s2` | Channel select bit 2 | OUT |
| 15 | 22 | `mux_s3` | Channel select bit 3 | OUT |
| 36 | 16 | `mux_sig` | Signal read | IN (PUD_UP) |

Used only by `ReadMuxAMuxB.py` (standalone CLI tool, not scheduled). Note: `get_mux_pins()` returns **BOARD** pin numbers, and `ReadMuxAMuxB.py` uses `GPIO.setmode(GPIO.BOARD)`.

**Pin overlap**: Default mux SIG (BOARD 36 = BCM 16) is the same GPIO as the off switch. Safe because the mux script and switch-reading scripts never run concurrently.

### 1.5 I2C Devices (Not Direct GPIO)

| Device | Bus | Default Address | controls.txt Key | Purpose |
|--------|-----|-----------------|------------------|---------|
| INA260 | I2C-1 | 0x40 | `ina260_address` | Power monitor |
| PCA9536 | I2C-1 | 0x41 | `pca9536_address` | 4-channel GPIO expander |

Uses I2C pins GPIO 2 (SDA1) and GPIO 3 (SCL1) in alternate function mode. Not direct GPIO control.

### 1.6 Deployed vs Code Default Pin Discrepancy

The deployed production system (`/etc/mothbox/controls.txt`) uses `Relay_Ch2=6` and `Relay_Ch3=13`, while the code defaults in `mothbox_paths.py` are `Relay_Ch2=19` and `Relay_Ch3=9`. Hardware testing confirmed GPIO 6 is actively wired to the flash relay and GPIO 13 to the spare relay. The code defaults reflect a different hardware revision.

| BCM | Code Default | Deployed | Status |
|-----|-------------|----------|--------|
| 6 | -- | Relay_Ch2 (Flash) | Active, confirmed by hardware test |
| 13 | -- | Relay_Ch3 (Spare) | Active, confirmed by hardware test |
| 19 | Relay_Ch2 | -- | Not wired on deployed hardware |
| 9 | Relay_Ch3 | -- | Not wired on deployed hardware |

---

## 2. Polarity Model

### 2.1 Active-Low vs Active-High

- **Active-low**: `GPIO.LOW` (0) on the pin energizes the relay, turning the connected load ON. `GPIO.HIGH` (1) de-energizes. This is the convention used by most commodity relay modules.
- **Active-high**: `GPIO.HIGH` (1) energizes the relay. `GPIO.LOW` (0) de-energizes.

### 2.2 Hardware-Confirmed Polarity (Production Pi 5)

**The production Mothbox relay module is active-HIGH.** This was confirmed by hardware testing on 2026-02-08 using `pinctrl` to toggle each relay pin while observing the physical hardware:

| GPIO | HIGH | LOW | Load |
|------|------|-----|------|
| 5 (Ch1) | UV ON | UV OFF | Active-HIGH |
| 6 (Ch2) | Flash ON | Flash OFF | Active-HIGH |
| 13 (Ch3) | Spare ON | Spare OFF | Active-HIGH |

All three relay channels behave identically: HIGH energizes, LOW de-energizes.

**Wiring**: Loads (UV LEDs, flash LEDs) are wired to the **Normally Open (NO)** contacts. When the relay coil is de-energized, the NO contact is open (load OFF). When energized, the NO contact closes (load ON). The relay module itself has active-HIGH inputs (HIGH = coil energized), which combined with NO wiring gives: HIGH = load ON.

**Note**: The deployed pin assignments (5/6/13) differ from the code defaults in `mothbox_paths.py` (5/19/9). The production `controls.txt` at `/etc/mothbox/controls.txt` has `Relay_Ch2=6` and `Relay_Ch3=13`.

### 2.3 Firmware Conventions

**4.x firmware**: Consistently uses **active-low** polarity across all scripts. LOW = relay ON, HIGH = relay OFF. This was correct for the relay hardware used with 4.x.

**5.x firmware**: The top-level scripts (`Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`) and the web UI (`gpio.py`) were changed to **active-high** in commit `732e25c6`. HIGH = relay ON, LOW = relay OFF. **Hardware testing confirms this is correct for the production relay module.**

### 2.4 Current State: Polarity Is Inconsistent

**The 5.x polarity model is not uniformly applied.** The following files still use active-low (4.x) polarity:

- `5.x/TakePhoto.py` -- Ch3 (attract) uses LOW for "on" while Ch2 (flash) uses HIGH for "on" (**mixed** within a single file)
- `5.x/DebugMode.py` -- sends HIGH to "turn off", which is the 4.x convention
- `5.x/FlashOn.py` -- sends LOW for "on" (also has a BOARD/BCM mode bug)
- All files in `5.x/scripts/` -- every TakePhoto variant, Flash_On/Off, CheckFocus, PlowmanAutofocus, etc.
- `webui/backend/scripts/capture_focus_bracket.py` -- Ch3 uses LOW for "on" (matches TakePhoto.py, not Attract_On.py)

This means the attract relay (Ch3) receives contradictory signals depending on which script controls it. `Attract_On.py` sends HIGH; `TakePhoto.py` sends LOW. Both claim to turn the attract lights on. **One of them is wrong.**

### 2.4 Polarity Comparison Matrix

| Script | Ch1 ON | Ch1 OFF | Ch2 ON | Ch2 OFF | Ch3 ON | Ch3 OFF | Convention |
|--------|--------|---------|--------|---------|--------|---------|------------|
| 4.x Attract_On.py | LOW | -- | HIGH\* | -- | LOW | -- | Active-low |
| 4.x Attract_Off.py | -- | HIGH | -- | HIGH | -- | HIGH | Active-low |
| 4.x TakePhoto flashOn | -- | -- | LOW | -- | LOW | -- | Active-low |
| 4.x TakePhoto flashOff | -- | -- | -- | HIGH | LOW | -- | Active-low |
| **5.x Attract_On.py** | HIGH | -- | HIGH | -- | HIGH | -- | **Active-high** |
| **5.x Attract_Off.py** | -- | LOW | -- | LOW | -- | LOW | **Active-high** |
| **5.x TakePhoto flashOn** | -- | -- | HIGH | -- | LOW | -- | **MIXED** |
| **5.x TakePhoto flashOff** | -- | -- | -- | LOW | LOW | -- | **MIXED** |
| 5.x Flash_On.py | -- | -- | HIGH | -- | -- | -- | Active-high |
| 5.x Flash_Off.py | -- | -- | -- | LOW | -- | -- | Active-high |
| 5.x FlashOn.py | -- | -- | LOW | -- | -- | -- | Active-low\*\* |
| 5.x DebugMode AttractOff | -- | HIGH | -- | HIGH | -- | HIGH | Active-low |
| 5.x gpio.py control | HIGH | LOW | -- | -- | -- | -- | Active-high |
| 5.x gpio.py flash | -- | -- | HIGH | LOW | -- | -- | Active-high |
| 5.x scripts/ (all) | -- | -- | LOW | HIGH | LOW | HIGH | Active-low |

\*4.x Attract_On Ch2: HIGH when not in `OnlyFlash` mode (flash off during attract), LOW in `OnlyFlash` mode.
\*\*FlashOn.py also has a BOARD/BCM mode bug, so it operates the wrong physical pin entirely.

---

## 3. Signal Path Diagrams

### 3.1 Web UI Relay Toggle

```
User clicks toggle
  |
  v
Frontend: POST /api/gpio/control {"relay": "Relay_Ch1", "state": true}
  |
  v
gpio.py:control_gpio()
  |-- get_gpio_pins() -> {"Relay_Ch1": 5, ...}
  |-- GPIO.setup(5, GPIO.OUT)
  |-- GPIO.output(5, GPIO.HIGH)       # state=True -> HIGH (active-high)
  |-- _save_state() -> gpio_state.json
  |
  v
Pin 5 driven HIGH. No GPIO.cleanup(). Pin persists between requests.
```

### 3.2 Web UI Flash Trigger

```
User clicks flash button
  |
  v
Frontend: POST /api/gpio/flash
  |
  v
gpio.py:trigger_flash()
  |-- get_gpio_pins() -> flash_pin = 19 (Relay_Ch2)
  |-- controls.get("flash_duration_ms", 100) -> 100ms
  |-- GPIO.setup(19, GPIO.OUT)
  |-- GPIO.output(19, GPIO.HIGH)       # Flash ON
  |-- time.sleep(0.1)                  # 100ms pulse
  |-- GPIO.output(19, GPIO.LOW)        # Flash OFF
```

### 3.3 Web UI Scheduler to Cron to GPIO Script

```
User activates schedule in web UI
  |
  v
POST /api/scheduler/activate
  |
  v
scheduler_service.activate_schedule()
  |
  v
cron_bridge.py: generate_cron_entries()
  |-- For action type="gpio", name="attract_on":
  |   cron_security.py: ALLOWED_SCRIPTS["attract_on"] = "Attract_On.py"
  |   -> "systemd-cat -t mothbox /usr/bin/python3 /opt/mothbox/Attract_On.py"
  |
  v
CronTab writes entry to system crontab
  |
  v
[At scheduled time]
cron -> python3 Attract_On.py
  |-- get_gpio_pins() -> {Ch1=5, Ch2=19, Ch3=9}
  |-- GPIO.setmode(GPIO.BCM)
  |-- GPIO.output(Relay_Ch3, GPIO.HIGH)   # All channels HIGH (active-high)
  |-- GPIO.output(Relay_Ch2, GPIO.HIGH)
  |-- GPIO.output(Relay_Ch1, GPIO.HIGH)
  |
  v
Process exits. No GPIO.cleanup(). Pins remain HIGH.
```

### 3.4 Boot Sequence: Scheduler.py Switch Detection

```
System boot -> systemd/cron starts Scheduler.py
  |
  v
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.IN)   # off_pin
GPIO.setup(12, GPIO.IN)   # debug_pin
  |
  v
Read physical switch positions:
  off_pin=16:   PUD_UP, read value. LOW=grounded=OFF mode.
  debug_pin=12: PUD_UP, read value. LOW=grounded=DEBUG mode.
  |
  +-- OFF (pin 16 grounded): -> shutdown sequence
  |     |-- GPIO.cleanup()
  |     |-- subprocess: UpdateDisplay.py
  |     |-- sudo shutdown -h now
  |
  +-- DEBUG (pin 12 grounded): -> DebugMode.py
  |     |-- Stop cron
  |     |-- GPIO.output(all channels, HIGH)  # BUG: active-low "off"
  |     |-- Write shutdown_enabled=False
  |
  +-- ACTIVE (neither grounded): -> normal operation
        |-- Start cron jobs
        |-- Run scheduled TakePhoto.py cycles
        |-- Timer -> shutdown -> GPIO.cleanup() -> UpdateDisplay.py -> poweroff
```

### 3.5 TakePhoto.py Flash Cycle (5.x)

```
python3 TakePhoto.py
  |
  v
[Startup, line 752]
  GPIO.output(Relay_Ch2, HIGH)    # Flash ON
  GPIO.output(Relay_Ch3, LOW)     # "Ensure attract is on" (active-low for Ch3)
  |
  v
[Calibration, if enabled]
  flashOn():
    GPIO.output(Relay_Ch2, HIGH)  # Flash ON
    GPIO.output(Relay_Ch3, LOW)   # Attract "on" (active-low)
  [autofocus cycle]
  flashOff():
    GPIO.output(Relay_Ch3, LOW)   # Attract stays "on"
    GPIO.output(Relay_Ch2, LOW)   # Flash OFF
  |
  v
[Photo capture loop, line 564]
  flashOn()                       # Flash ON
  picam2.capture_request()        # Take photo
  if not onlyflash: flashOff()    # Flash OFF (unless always-on mode)
  |
  v
[End of script, line 910]
  GPIO.output(Relay_Ch3, LOW)     # Attract stays "on"
  # No GPIO.cleanup() -- comment: "it will kill the relay"
  GPIO.cleanup(Relay_Ch2)         # Clean up flash pin only (line 925)
```

---

## 4. Library Usage

### 4.1 Library Stack

All Mothbox GPIO code imports `RPi.GPIO`. On Raspberry Pi 5, this resolves to a compatibility shim:

```
Mothbox code
  -> import RPi.GPIO as GPIO
    -> rpi-lgpio v0.6 (compatibility shim by Dave Jones)
      -> lgpio v0.2.2.0 (C library)
        -> Linux kernel GPIO character device (/dev/gpiochip*)
```

### 4.2 Constant Values (Confirmed on Pi 5)

| Constant | Value | Type |
|----------|-------|------|
| `GPIO.HIGH` | 1 | int |
| `GPIO.LOW` | 0 | int |
| `GPIO.BCM` | 11 | int |
| `GPIO.BOARD` | 10 | int |
| `GPIO.OUT` | 0 | int |
| `GPIO.IN` | 1 | int |
| `GPIO.PUD_UP` | 22 | int |
| `GPIO.PUD_DOWN` | 21 | int |

### 4.3 Installed Packages

| Package | Version | Role in Mothbox |
|---------|---------|-----------------|
| rpi-lgpio | 0.6 | RPi.GPIO compatibility shim (**active**, used by all GPIO code) |
| lgpio | 0.2.2.0 | Low-level GPIO C library (used indirectly by shim) |
| gpiod | 2.2.0 | Character-device GPIO (**not used**, system dependency) |
| gpiozero | 2.0.1 | High-level GPIO (**not used**, only in waveshare driver fallback) |
| types-RPi.GPIO | 0.7 | Type stubs for static analysis |

### 4.4 Pin State Persistence (Pi 5 Behavior)

On Pi 5 with the lgpio backend, **GPIO pin state persists after the controlling process exits**. This is confirmed by runtime observation: GPIO 5 remains configured as output driving HIGH with consumer "lg" even though no process holds an open file descriptor on `/dev/gpiochip*`.

This differs from the original RPi.GPIO on Pi 4 where pins returned to input state when the process exited. On Pi 5, the only way to reset pin state is an explicit `GPIO.cleanup()` call or a system reboot.

---

## 5. Resource Management

### 5.1 No Locking Between Concurrent Scripts

There is no file lock, semaphore, or other concurrency mechanism preventing multiple scripts from driving the same GPIO pin simultaneously. Possible conflict scenarios:

- Web UI toggles a relay while a cron-triggered `Attract_On.py` runs
- `TakePhoto.py` flash cycle runs while the web UI flash button is pressed
- Two cron jobs fire at the same time (e.g., `Attract_On.py` and `TakePhoto.py`)

In practice, the RPi.GPIO library allows multiple calls to `GPIO.setup()` and `GPIO.output()` on the same pin from different processes. The last write wins.

### 5.2 Web UI State Tracking

The web UI tracks relay state in `gpio_state.json` (located in `DATA_DIR`). This file is written by `gpio.py:_save_state()` after every relay toggle.

**This is not live pin state.** The file records what the web UI *thinks* the pins are set to. If an external script (cron job, Scheduler.py, TakePhoto.py) changes a pin, `gpio_state.json` is not updated and the web UI shows stale data.

### 5.3 GPIO Cleanup Inventory

| Script | Has GPIO.cleanup()? | Scope | Notes |
|--------|---------------------|-------|-------|
| `Scheduler.py` | Yes (x3) | All pins | Lines 500, 578, 935 -- only on shutdown path |
| `ReadMuxAMuxB.py` | Yes | All pins | In `finally` block |
| `Relay_Module.py` | Yes | All pins | After interactive test |
| `CheckGPIOPin.py` | Yes | All pins | After diagnostic |
| `UpdateDisplay.py` | Yes | All pins | At script end |
| `TakePhoto.py` (5.x) | Partial | Relay_Ch2 only | Line 925 -- cleans flash pin, intentionally leaves Ch3 |
| `gpio.py` (web UI) | Partial | Single test pin | During startup validation only |
| `Attract_On.py` | **No** | -- | Pins persist as output at last value |
| `Attract_Off.py` | **No** | -- | Pins persist as output at last value |
| `Flash_On.py` | **No** | -- | Pin persists as output |
| `Flash_Off.py` | **No** | -- | Pin persists as output |
| `FlashOn.py` | **No** | -- | Pin persists (wrong pin due to BOARD bug) |
| `DebugMode.py` | **No** | -- | Pins persist as output |
| All `scripts/TakePhoto*.py` | **No** | -- | Relay pins persist |

### 5.4 GPIO Mode Enforcement

RPi.GPIO enforces a single mode (`BCM` or `BOARD`) per process. Calling `GPIO.setmode()` with a different value after it has been set raises a `ValueError`.

- The Flask web UI process sets `GPIO.BCM` at module load. All web UI operations use BCM.
- Standalone scripts (cron, CLI) run as separate processes and set their own mode.
- `ReadMuxAMuxB.py` is the only script that uses `GPIO.BOARD`. It runs standalone and cannot conflict with BCM-mode scripts in the same process.

---

## 6. 4.x vs 5.x Differences

### 6.1 Key Differences

| Aspect | 4.x | 5.x |
|--------|-----|-----|
| **Relay pins (default)** | 26 / 20 / 21 | 5 / 19 / 9 (via controls.txt) |
| **Polarity convention** | Active-low (LOW=ON) | Active-high (HIGH=ON) in top-level scripts; mixed in TakePhoto.py and scripts/ |
| **`OnlyFlash` handling** | Full conditional logic in Attract_On.py (Ch2 behavior changes) | Removed from top-level scripts; Ch2 unconditionally follows same pattern as Ch1/Ch3 |
| **Flash scripts** | `FlashOn.py` only (BOARD mode, active-low) | `Flash_On.py` + `Flash_Off.py` (BCM, active-high) and legacy `FlashOn.py` (BOARD, active-low) |
| **`get_gpio_pins()` source** | Always returns defaults (26/20/21) | Returns controls.txt values (5/19/9) or defaults |
| **scripts/ subdirectory** | Active-low throughout | Active-low throughout (**not updated for 5.x**) |
| **DebugMode.py** | Active-low (correct) | Active-low (**not updated**, contradicts 5.x convention) |

### 6.2 Files That Differ Between 4.x and 5.x

| File | Difference |
|------|-----------|
| `Attract_On.py` | 5.x: HIGH=on, no OnlyFlash logic. 4.x: LOW=on, OnlyFlash conditional. |
| `Attract_Off.py` | 5.x: LOW=off. 4.x: HIGH=off. |
| `Flash_On.py` / `Flash_Off.py` | Exist only in 5.x (created at `732e25c6`). |
| `TakePhoto.py` | 5.x: Ch2 (flash) uses HIGH=on. Ch3 (attract) still uses LOW=on. 4.x: both active-low. |
| `DebugMode.py` | Functionally identical (both use active-low). 5.x copy was never updated. |
| `FlashOn.py` | Functionally identical (both use BOARD mode + active-low). Both have the BOARD/BCM bug. |
| All `scripts/` files | Functionally identical (active-low). 5.x copies were never updated. |

---

## 7. Configuration

### 7.1 controls.txt Keys

All GPIO-related keys in `controls.txt`:

| Key | Type | Default | Used By |
|-----|------|---------|---------|
| `Relay_Ch1` | int (BCM 0-27) | 26 | `get_gpio_pins()` |
| `Relay_Ch2` | int (BCM 0-27) | 20 | `get_gpio_pins()` |
| `Relay_Ch3` | int (BCM 0-27) | 21 | `get_gpio_pins()` |
| `relay_enabled` | bool | true | `gpio.py` route guard |
| `flash_duration_ms` | int | 100 | `gpio.py:trigger_flash()` |
| `OnlyFlash` | bool | False | 4.x scripts only (ignored by 5.x top-level) |
| `epaper_rst_pin` | int (BCM) | 17 | `get_epaper_pins()` |
| `epaper_dc_pin` | int (BCM) | 25 | `get_epaper_pins()` |
| `epaper_cs_pin` | int (BCM) | 8 | `get_epaper_pins()` |
| `epaper_busy_pin` | int (BCM) | 24 | `get_epaper_pins()` |
| `epaper_pwr_pin` | int (BCM) | 18 | `get_epaper_pins()` |
| `mux_en_a` | int (BOARD 1-40) | 31 | `get_mux_pins()` |
| `mux_en_b` | int (BOARD 1-40) | 29 | `get_mux_pins()` |
| `mux_s0` | int (BOARD 1-40) | 33 | `get_mux_pins()` |
| `mux_s1` | int (BOARD 1-40) | 13 | `get_mux_pins()` |
| `mux_s2` | int (BOARD 1-40) | 12 | `get_mux_pins()` |
| `mux_s3` | int (BOARD 1-40) | 15 | `get_mux_pins()` |
| `mux_sig` | int (BOARD 1-40) | 36 | `get_mux_pins()` |

### 7.2 Configuration Functions

All in `mothbox_paths.py`:

| Function | Returns | Pin Mode | Fallback |
|----------|---------|----------|----------|
| `get_gpio_pins()` | `{Relay_Ch1, Relay_Ch2, Relay_Ch3}` | BCM | 26/20/21 (4.x defaults) |
| `get_epaper_pins()` | `{RST_PIN, DC_PIN, CS_PIN, BUSY_PIN, PWR_PIN}` | BCM | 17/25/8/24/18 |
| `get_mux_pins()` | `{EN_A, EN_B, S0-S3, SIG}` | BOARD | 31/29/33/13/12/15/36 |
| `get_hardware_config()` | Full hardware config dict (32+ keys) | Mixed | Per-key defaults |

Pin validation: BCM pins must be 0-27. BOARD pins must be 1-40. Invalid values raise `ValueError`. On any exception, the functions return hardcoded defaults.

### 7.3 Non-Configurable Pins

| Pin | BCM | Purpose | Where Hardcoded |
|-----|-----|---------|-----------------|
| Off switch | 16 | Physical power-off switch | 8 files (Scheduler.py, TakePhoto.py, UpdateDisplay.py, CheckGPIOPin.py -- both 4.x and 5.x) |
| Debug switch | 12 | Physical debug mode switch | Same 8 files |

These should be migrated to `controls.txt` / `get_gpio_pins()` to avoid manual multi-file edits on hardware changes.

---

## 8. Known Issues

Nine confirmed bugs from the GPIO audit, ordered by severity.

### BUG-1: TakePhoto.py Ch3 Polarity Contradicts Attract_On.py (5.x)

**Files**: `5.x/TakePhoto.py:183` vs `5.x/Attract_On.py:52`

TakePhoto.py sends `GPIO.LOW` to Ch3 with comment "ensure attract is on". Attract_On.py sends `GPIO.HIGH` to Ch3 to turn attract on. These are opposite signals for the same intent on the same pin. One is wrong.

### BUG-2: DebugMode.py Uses 4.x Polarity (5.x)

**File**: `5.x/DebugMode.py:77-80`

Sends HIGH to all channels to "turn off". In active-high (5.x), HIGH means ON. DebugMode.py turns everything on instead of off on 5.x hardware.

### BUG-3: FlashOn.py BOARD/BCM Mode Mismatch

**File**: `5.x/FlashOn.py:32` (also `4.x/FlashOn.py:30`)

Uses `GPIO.setmode(GPIO.BOARD)` but receives a BCM pin number from `get_gpio_pins()`. BCM pin 19 interpreted as BOARD pin 19 = physical pin 19 = GPIO10. Operates the SPI MOSI pin instead of the flash relay. Not in `cron_security.py` allowed scripts, so CLI-only risk.

### BUG-4: Flash_On.py / Flash_Off.py Naming Confusion

**Files**: `5.x/Flash_On.py:25`, `5.x/Flash_Off.py:25`

Variable `Relay_Ch1` is aliased to `pins["Relay_Ch2"]`. Functions named `AttractOn`/`AttractOff` for a flash script. Print banner says "attract off!" in a flash-on script. Functionally correct but misleading.

### BUG-5: Web UI State Desynchronization

**File**: `webui/backend/routes/gpio.py:184`

`GET /api/gpio/status` reads from `gpio_state.json`, not live pins. After any cron-triggered script changes GPIO state, the web UI shows stale toggle positions. No sync mechanism exists.

### BUG-6: No GPIO.cleanup() in Relay Scripts

**Files**: All of `5.x/Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`, `FlashOn.py`, `DebugMode.py`

On Pi 5 with rpi-lgpio, pin state persists after process exit. Relays remain in their last commanded state indefinitely. No safety mechanism to return pins to input state after a script crash.

### ~~BUG-7: GPIO 6 Orphaned Output~~ (RESOLVED)

**Source**: Runtime observation on production Pi

GPIO 6 was initially flagged as orphaned because the code default for Relay_Ch2 is pin 19. However, the deployed `controls.txt` at `/etc/mothbox/controls.txt` has `Relay_Ch2=6`, and **hardware testing confirmed GPIO 6 is actively wired to the flash relay**. GPIO 6 is not orphaned — the code defaults simply reflect a different hardware revision than what is deployed. The deployed config correctly overrides the defaults.

### BUG-8: Hardcoded Switch Pins in 8 Files

**Files**: `{4,5}.x/Scheduler.py`, `TakePhoto.py`, `UpdateDisplay.py`, `scripts/CheckGPIOPin.py`

`off_pin=16` and `debug_pin=12` are hardcoded in 8 files. Not configurable via `controls.txt` or any `mothbox_paths.py` function.

### BUG-9: Startup Permission Check Side Effect

**File**: `webui/backend/routes/gpio.py:66`

At module load, `_validate_gpio_permissions()` drives Relay_Ch1 LOW briefly (`GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)`). On the production active-HIGH hardware, this momentarily de-energizes the relay (safe direction). On active-LOW hardware, it would momentarily energize the relay. Cleanup follows immediately. Still a design issue — the permission check should use input mode to avoid driving pins at all.

### Additional Findings (Not Bugs)

- **5.x scripts/ subdirectory**: All TakePhoto variants, Flash, CheckFocus, etc. use active-low (4.x polarity). Never updated for 5.x.
- **`OnlyFlash` silently ignored on 5.x**: The setting exists in `controls.txt` but 5.x top-level scripts unconditionally drive all channels.
- **Module-level pin loading in gpio.py**: `get_gpio_pins()` is called at import time (line 15) and again inside each route handler. The module-level value becomes stale if `controls.txt` is modified at runtime.

---

## 9. Troubleshooting Commands

Commands for diagnosing GPIO issues on a live Raspberry Pi.

### Pin State Inspection

```bash
# Show all GPIO line directions and consumers (gpiochip0 = user GPIO)
gpioinfo gpiochip0

# Show specific pin state (direction, pull, drive, read value)
pinctrl get 5          # Check Relay_Ch1
pinctrl get 19         # Check Relay_Ch2
pinctrl get 9          # Check Relay_Ch3
pinctrl get 16         # Check off switch
pinctrl get 12         # Check debug switch

# Show all pin states at once
pinctrl get
```

### Process Inspection

```bash
# Find processes using GPIO character devices
lsof /dev/gpiomem* /dev/gpiochip*

# Check which services are running
systemctl status mothbox-webui.service

# Check for running GPIO scripts
ps aux | grep -E "(Attract|Flash|TakePhoto|Scheduler|DebugMode)"
```

### I2C Bus Scan

```bash
# Scan I2C bus 1 for connected devices (INA260 at 0x40, PCA9536 at 0x41)
i2cdetect -y 1
```

### GPIO Access Test

```bash
# Test basic GPIO access from Python
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(5, GPIO.OUT)
print('GPIO 5 setup OK')
GPIO.cleanup(5)
print('GPIO 5 cleanup OK')
"
```

### Crontab Inspection

```bash
# Check user crontab (pi user)
crontab -l

# Check root crontab
sudo crontab -l

# Check system cron directories
ls -la /etc/cron.d/
```

### Configuration Verification

```bash
# Show current GPIO pin configuration from controls.txt
python3 -c "
from mothbox_paths import get_gpio_pins, get_epaper_pins, get_mux_pins
print('Relay pins:', get_gpio_pins())
print('E-paper pins:', get_epaper_pins())
print('Mux pins:', get_mux_pins())
"

# Show full hardware config
python3 -c "
from mothbox_paths import get_hardware_config
import json
print(json.dumps(get_hardware_config(), indent=2, default=str))
"
```

### Reset Orphaned Pins

```bash
# Force a specific pin back to input state
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.IN)   # Reset orphaned GPIO 6
GPIO.cleanup(6)
print('GPIO 6 reset to input')
"
```

---

## Appendix: File Inventory

Every file that imports `RPi.GPIO` or interacts with GPIO hardware, grouped by role.

### Relay Control (Production)

| File | Version | Polarity | Cleanup |
|------|---------|----------|---------|
| `5.x/Attract_On.py` | 5.x | Active-high | No |
| `5.x/Attract_Off.py` | 5.x | Active-high | No |
| `5.x/Flash_On.py` | 5.x | Active-high | No |
| `5.x/Flash_Off.py` | 5.x | Active-high | No |
| `5.x/FlashOn.py` | 5.x | Active-low (bug) | No |
| `5.x/TakePhoto.py` | 5.x | Mixed | Partial (Ch2 only) |
| `5.x/DebugMode.py` | 5.x | Active-low (bug) | No |
| `webui/backend/routes/gpio.py` | Web UI | Active-high | Partial (startup test only) |
| `webui/backend/scripts/capture_focus_bracket.py` | Web UI | Mixed | -- |

### Scheduler / Switch Reading

| File | Version | GPIO Usage |
|------|---------|------------|
| `5.x/Scheduler.py` | 5.x | Input (pins 16/12), `GPIO.cleanup()` on shutdown |
| `5.x/UpdateDisplay.py` | 5.x | Input (pins 16/12), e-paper via waveshare lib |

### Utility Scripts (5.x/scripts/)

All use active-low polarity (4.x convention, never updated for 5.x).

| File | Channels | Cleanup |
|------|----------|---------|
| `CheckFocus.py` | Ch2+Ch3 | No |
| `FlashOn_ManPhoto_FlashOff.py` | Ch2+Ch3 | No |
| `Flash_On.py` (scripts/) | All | No |
| `Flash_Off.py` (scripts/) | All | No |
| `Full_Test_Relay_Photo_Logging_Shutdown.py` | Ch1+Ch3 | No |
| `PlowmanAutofocus.py` | Ch2 | No |
| `Relay_Module.py` | All | Yes |
| `ReadMuxAMuxB.py` | Mux (BOARD) | Yes |
| `CheckGPIOPin.py` | Switch (input) | Yes |
| `TakePhoto16mp.py` | Ch2+Ch3 | No |
| `TakePhotoHDR_Fast_WithEXIF.py` | Ch2+Ch3 | No |
| `TakePhoto_AutoExposure.py` | Ch2 | No |
| `TakePhoto_HDR.py` | Ch2+Ch3 | No |
| `TakePhoto_Stereo_HDR.py` | Ch2+Ch3 | No |
| `TakePhoto_noAuto.py` | Ch2+Ch3 | No |
| `TakePhoto_uniqueAutoID.py` | Ch2+Ch3 | No |
| `TakeSinglePhoto with flash.py` | Ch2+Ch3 | No |

### 4.x (Legacy)

Same file structure as 5.x with consistent active-low polarity throughout.

### OldScripts (Deprecated)

All hardcode pin values (26/20/21) and do not use `get_gpio_pins()`. Not in active use.
