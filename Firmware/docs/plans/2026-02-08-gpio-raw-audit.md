# GPIO System Raw Audit

**Date**: 2026-02-08
**Scope**: All GPIO usage in the Mothbox Firmware repository
**Branch**: `dev`
**Data Sources**:
- `tools/gpio_audit/raw_ast_results.json` -- AST extraction (528 files, 342 imports, 1262 calls, 2474 pin assignments)
- `tools/gpio_audit/grep_results.md` -- Cross-file grep analysis
- `tools/gpio_audit/git_history.md` -- Git history timeline
- `tools/gpio_audit/pyright_results.md` -- Pyright type checking + library constant values
- `tools/gpio_audit/runtime_state.md` -- Live GPIO state from Pi 5 production unit
- `tools/gpio_audit/logic_pipelines.md` -- 18 signal paths with 9 confirmed bugs

---

## 1. File Inventory

All files that interact with GPIO hardware, categorized by function.

### 1.1 Relay Control Scripts (Primary)

Top-level scripts invoked by cron, scheduler, or CLI to control relays.

| File | Version | Function | Pin Source | Polarity |
|------|---------|----------|------------|----------|
| `5.x/Attract_On.py` | 5.x | Turn attract lights on | `get_gpio_pins()` | Active-HIGH |
| `5.x/Attract_Off.py` | 5.x | Turn attract lights off | `get_gpio_pins()` | Active-HIGH |
| `5.x/Flash_On.py` | 5.x | Turn flash on | `get_gpio_pins()` | Active-HIGH |
| `5.x/Flash_Off.py` | 5.x | Turn flash off | `get_gpio_pins()` | Active-HIGH |
| `5.x/FlashOn.py` | 5.x | Legacy flash on (BOARD bug) | `get_gpio_pins()` | Active-LOW |
| `5.x/TakePhoto.py` | 5.x | Photo capture with flash control | `get_gpio_pins()` | MIXED |
| `5.x/DebugMode.py` | 5.x | Debug mode (turn off relays) | `get_gpio_pins()` | Active-LOW |
| `5.x/TurnEverythingOff.py` | 5.x | Shutdown all hardware | `get_gpio_pins()` | N/A (uses PiJuice) |
| `4.x/Attract_On.py` | 4.x | Turn attract lights on | `get_gpio_pins()` | Active-LOW |
| `4.x/Attract_Off.py` | 4.x | Turn attract lights off | `get_gpio_pins()` | Active-LOW |
| `4.x/FlashOn.py` | 4.x | Flash on (BOARD mode bug) | `get_gpio_pins()` | Active-LOW |
| `4.x/TakePhoto.py` | 4.x | Photo capture with flash control | `get_gpio_pins()` | Active-LOW |
| `4.x/DebugMode.py` | 4.x | Debug mode (turn off relays) | `get_gpio_pins()` | Active-LOW |

### 1.2 Web UI GPIO Routes

| File | Function | Pin Source | Polarity |
|------|----------|------------|----------|
| `webui/backend/routes/gpio.py` | REST API for relay control, flash, status | `get_gpio_pins()` | Active-HIGH |

### 1.3 Scheduler / Switch Reading

| File | Version | Function | GPIO Usage |
|------|---------|----------|------------|
| `5.x/Scheduler.py` | 5.x | Boot scheduler, switch reading, cleanup | Input (pins 16/12), `GPIO.cleanup()` |
| `4.x/Scheduler.py` | 4.x | Boot scheduler, switch reading, cleanup | Input (pins 16/12), `GPIO.cleanup()` |

### 1.4 Display and Sensor Scripts

| File | Version | Function | GPIO Usage |
|------|---------|----------|------------|
| `5.x/UpdateDisplay.py` | 5.x | E-paper display update | Switch input (16/12), e-paper pins via waveshare lib |
| `4.x/UpdateDisplay.py` | 4.x | E-paper display update | Switch input (16/12), e-paper pins via waveshare lib |
| `5.x/scripts/CheckGPIOPin.py` | 5.x | Diagnostic: check switch positions | Input (pins 16/12) |
| `4.x/scripts/CheckGPIOPin.py` | 4.x | Diagnostic: check switch positions | Input (pins 16/12) |

### 1.5 E-paper Driver (Vendor Library)

| File | Notes |
|------|-------|
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/lib/waveshare_epd/epdconfig.py` | BCM mode, manages RST/DC/CS/BUSY/PWR pins |
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/python/lib/waveshare_epd/epdconfig.py` | Duplicate of above |
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/lib/waveshare_epd/epd2in13d.py` | E-paper display model driver |
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/lib/waveshare_epd/epd2in9d.py` | E-paper display model driver |
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/lib/waveshare_epd/epd4in2.py` | E-paper display model driver |
| `{4,5}.x/scripts/RaspberryPi_JetsonNano_Epaper/lib/waveshare_epd/epd4in2_V2.py` | E-paper display model driver |

### 1.6 I2C / Multiplexer Scripts

| File | Version | Function | GPIO Mode |
|------|---------|----------|-----------|
| `{4,5}.x/scripts/ReadMuxAMuxB.py` | Both | Read CD74HC4067 multiplexer switches | BOARD mode |
| `5.x/PCA9536.py` | 5.x | I2C GPIO expander control | I2C (smbus), not RPi.GPIO |
| `5.x/testPCA.py` | 5.x | PCA9536 test | I2C |
| `5.x/testmuxi2c.py` | 5.x | I2C multiplexer test | I2C |

### 1.7 Utility / Test Scripts (scripts/ subdirectories)

| File | Version | Function |
|------|---------|----------|
| `{4,5}.x/scripts/Relay_Module.py` | Both | Interactive relay test (cycles all channels) |
| `{4,5}.x/scripts/Flash_On.py` | Both | Standalone flash on (uses `onlyflash` conditional) |
| `{4,5}.x/scripts/Flash_Off.py` | Both | Standalone flash off |
| `{4,5}.x/scripts/FlashOn_ManPhoto_FlashOff.py` | Both | Flash-on, take photo, flash-off cycle |
| `{4,5}.x/scripts/Full_Test_Relay_Photo_Logging_Shutdown.py` | Both | Full hardware test cycle |
| `{4,5}.x/scripts/CheckFocus.py` | Both | Focus check with flash |
| `{4,5}.x/scripts/PlowmanAutofocus.py` | Both | Autofocus with flash control |
| `{4,5}.x/scripts/TakePhoto16mp.py` | Both | 16MP capture variant |
| `{4,5}.x/scripts/TakePhotoHDR_Fast_WithEXIF.py` | Both | HDR capture variant |
| `{4,5}.x/scripts/TakePhoto_AutoExposure.py` | Both | Auto-exposure variant |
| `{4,5}.x/scripts/TakePhoto_HDR.py` | Both | HDR capture variant |
| `{4,5}.x/scripts/TakePhoto_Stereo_HDR.py` | Both | Stereo HDR variant |
| `{4,5}.x/scripts/TakePhoto_noAuto.py` | Both | Manual capture variant |
| `{4,5}.x/scripts/TakePhoto_uniqueAutoID.py` | Both | Unique ID capture variant |
| `{4,5}.x/scripts/TakeSinglePhoto with flash.py` | Both | Single photo with flash |
| `webui/backend/scripts/capture_focus_bracket.py` | N/A | Focus bracket capture (GPIOHandler class) |

### 1.8 Deprecated / OldScripts

| File | Notes |
|------|-------|
| `{4,5}.x/scripts/OldScripts/flashOn.py` | Hardcoded pins 26/20/21, BCM mode |
| `{4,5}.x/scripts/OldScripts/flashOff.py` | Hardcoded pins 26/20/21, BCM mode |
| `{4,5}.x/scripts/OldScripts/buckOn.py` | Hardcoded pins, BCM mode |
| `{4,5}.x/scripts/OldScripts/allRelaysOff_waveshare.py` | Hardcoded pins, BCM mode |
| `{4,5}.x/scripts/OldScripts/relay_hard_turnoff.py` | Hardcoded pins, BCM mode |
| `{4,5}.x/scripts/OldScripts/cam_relay_hard_turnoff.py` | Hardcoded pins, BCM mode |
| `{4,5}.x/scripts/OldScripts/FlashOn_ManPhoto_FlashOff_Speed.py` | Hardcoded pins, BCM mode |
| `{4,5}.x/scripts/OldScripts/RingLight_Autofocus_TakePhoto.py` | BOARD mode |
| `{4,5}.x/scripts/OldScripts/RingLight_Autofocus_TakePhoto_SavetoUSB_Date_Manyphotos.py` | Hardcoded pins |
| `{4,5}.x/scripts/OldScripts/TurnOffBlackLights.py` | BOARD mode |
| `{4,5}.x/scripts/OldScripts/TurnOnBlackLights.py` | BOARD mode |
| `{4,5}.x/scripts/OldScripts/onepicture_GPIO.py` | BOARD mode |

All OldScripts hardcode pin values (26/20/21) and do not use `get_gpio_pins()`.

### 1.9 Test Files

| File | Purpose |
|------|---------|
| `Tests/conftest.py` | MockGPIO class, `gpio_bp` import |
| `Tests/unit/test_capture_focus_bracket_unit.py` | GPIOHandler unit tests |
| `Tests/unit/test_gpio_routes.py` | gpio.py route tests (implied by conftest) |
| `Tests/unit/test_mothbox_paths_hardware.py` | Pin configuration tests |

### 1.10 Configuration Layer

| File | Function |
|------|----------|
| `mothbox_paths.py` | `get_gpio_pins()`, `get_epaper_pins()`, `get_mux_pins()`, `get_hardware_config()` |
| `webui/backend/routes/config.py` | Relay_Ch1/Ch2/Ch3 validation (BCM pin range check) |
| `webui/backend/lib/cron_security.py` | Maps action names to GPIO script filenames |
| `webui/backend/lib/schedule_schema.py` | Defines `gpio` action type with `attract_on/off`, `flash_on/off` |
| `webui/backend/lib/cron_bridge.py` | Converts schedule actions to cron commands invoking GPIO scripts |

**Total unique files with GPIO imports (RPi.GPIO)**: 93 (from AST extraction)

---

## 2. Library Inventory

### 2.1 RPi.GPIO (via rpi-lgpio shim)

**Usage**: All relay control scripts, all TakePhoto variants, Scheduler, UpdateDisplay, gpio.py route, e-paper driver.
**93 files** import `RPi.GPIO as GPIO`.

**Runtime reality**: The installed `RPi.GPIO` package is **not** the original C-extension. It is the `rpi-lgpio` compatibility shim (v0.6) by Dave Jones.

```
Mothbox code
  --> import RPi.GPIO as GPIO
    --> rpi-lgpio (v0.6) shim
      --> lgpio (v0.2.2.0) C library
        --> Linux kernel GPIO character device (/dev/gpiochip*)
```

Source: `pyright_results.md`, Section 1.

**Constant values** (confirmed on Pi 5):

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

Source: `pyright_results.md`, Section 1.

### 2.2 lgpio

**Version**: 0.2.2.0
**Usage**: Not called directly by any Mothbox code. Used indirectly via the rpi-lgpio shim. The `gpio_write`, `gpio_read`, `gpio_claim_output`, `gpio_claim_input` functions exist in the library but are never invoked directly.

Source: `grep_results.md`, Section 8.

### 2.3 gpiod

**Version**: 2.2.0
**Usage**: Not used by the Mothbox codebase. Installed on the system as a system dependency. Provides the modern character-device GPIO interface.

Source: `pyright_results.md`, Section 3.

### 2.4 gpiozero

**Version**: 2.0.1
**Usage**: Not used by the Mothbox codebase directly. Installed as a system dependency. Available pin factories: lgpio, rpigpio, mock.

**AST data**: 4 files import `gpiozero` -- all in the waveshare e-paper driver as a fallback import, not the Mothbox firmware itself.

Source: `pyright_results.md`, Section 4.

### 2.5 Installed Package Summary

| Package | Version | Role |
|---------|---------|------|
| rpi-lgpio | 0.6 | RPi.GPIO compatibility shim (active) |
| lgpio | 0.2.2.0 | Low-level GPIO (used by shim) |
| gpiod | 2.2.0 | Character-device GPIO (unused) |
| gpiozero | 2.0.1 | High-level GPIO (unused) |
| types-RPi.GPIO | 0.7 | Type stubs for pyright |

Source: `pyright_results.md`, Section 5.

---

## 3. Pin Map

Every GPIO pin referenced in code or configuration.

### 3.1 Relay Pins (BCM Mode)

| BCM Pin | Physical Pin | Channel | Function | 4.x Default | 5.x Production | Source |
|---------|-------------|---------|----------|-------------|----------------|--------|
| 26 | 37 | Relay_Ch1 | UV/attract lights | Yes (default) | No | `mothbox_paths.py:355` |
| 20 | 38 | Relay_Ch2 | Flash lights | Yes (default) | No | `mothbox_paths.py:356` |
| 21 | 40 | Relay_Ch3 | 5V buck converter | Yes (default) | No | `mothbox_paths.py:357` |
| 5 | 29 | Relay_Ch1 | UV/attract lights | No | Yes | `controls.txt:Relay_Ch1=5` |
| 19 | 35 | Relay_Ch2 | Flash lights | No | Yes | `controls.txt:Relay_Ch2=19` |
| 9 | 21 | Relay_Ch3 | 5V buck converter / auxiliary | No | Yes | `controls.txt:Relay_Ch3=9` |
| 6 | 31 | (none) | Orphaned on Pi (original 5.x Ch2) | No | Orphaned | `runtime_state.md` |

`get_gpio_pins()` defaults to 4.x pins (26/20/21) when `controls.txt` does not specify values. See `mothbox_paths.py:364`.

Source: `mothbox_paths.py:355-364`, `grep_results.md` Section 5, `runtime_state.md` Section 2.

### 3.2 Physical Switch Pins (BCM Mode, Hardcoded)

| BCM Pin | Physical Pin | Function | Direction | Files |
|---------|-------------|----------|-----------|-------|
| 16 | 36 | Off switch | Input (PUD_UP) | 8 files (see Section 8) |
| 12 | 32 | Debug switch | Input (PUD_UP) | 8 files (see Section 8) |

These pins are NOT configurable via `controls.txt` or `get_gpio_pins()`.

Source: `grep_results.md` Section 10.

### 3.3 E-paper Display Pins (BCM Mode, Configurable)

| BCM Pin | Physical Pin | Function | Direction | Source |
|---------|-------------|----------|-----------|--------|
| 17 | 11 | RST (reset) | Output | `mothbox_paths.py:385` |
| 25 | 22 | DC (data/command) | Output | `mothbox_paths.py:388` |
| 8 | 24 | CS (chip select / CE0) | Output | `mothbox_paths.py:391` |
| 24 | 18 | BUSY | Input | `mothbox_paths.py:394` |
| 18 | 12 | PWR (power) | Output | `mothbox_paths.py:397` |
| 11 | 23 | SPI CLK | Alt function (SPI) | Hardware SPI |
| 10 | 19 | SPI MOSI | Alt function (SPI) | Hardware SPI |

Configurable via `controls.txt` keys: `epaper_rst_pin`, `epaper_dc_pin`, `epaper_cs_pin`, `epaper_busy_pin`, `epaper_pwr_pin`.

Source: `mothbox_paths.py:384-397`, `grep_results.md` Section 6.

### 3.4 Multiplexer Pins (BOARD Mode, Configurable)

| BOARD Pin | BCM Pin | Function | Direction | Source |
|-----------|---------|----------|-----------|--------|
| 31 | 6 | EN_A (enable mux A) | Output | `mothbox_paths.py:433` |
| 29 | 5 | EN_B (enable mux B) | Output | `mothbox_paths.py:434` |
| 33 | 13 | S0 (channel select) | Output | `mothbox_paths.py:435` |
| 13 | 27 | S1 (channel select) | Output | `mothbox_paths.py:436` |
| 12 | 18 | S2 (channel select) | Output | `mothbox_paths.py:437` |
| 15 | 22 | S3 (channel select) | Output | `mothbox_paths.py:438` |
| 36 | 16 | SIG (signal read) | Input (PUD_UP) | `mothbox_paths.py:439` |

Configurable via `controls.txt` keys: `mux_en_a`, `mux_en_b`, `mux_s0`-`mux_s3`, `mux_sig`.

**Note**: Multiplexer pin overlap with switch pin: mux SIG default is BOARD 36 = BCM 16, which is the same as the `off_pin` switch. This overlap is acceptable only because `ReadMuxAMuxB.py` runs BOARD mode and the switch-reading scripts run BCM mode at different times.

Source: `mothbox_paths.py:433-439`.

### 3.5 I2C Devices (Not GPIO Pins, but GPIO-Adjacent)

| Device | Bus | Address | Config Key | Purpose |
|--------|-----|---------|------------|---------|
| INA260 | I2C-1 | 0x40 (default) | `ina260_address` | Power monitor |
| PCA9536 | I2C-1 | 0x41 (default) | `pca9536_address` | 4-channel GPIO expander |

**Runtime**: No I2C devices detected on the production Pi (`i2cdetect -y 1` returned empty).

Source: `mothbox_paths.py:517-518`, `runtime_state.md` Section 4.

### 3.6 Historical Pin Numbers

Pin assignments have changed over the project lifetime:

| Source | Ch1 | Ch2 | Ch3 | Date |
|--------|-----|-----|-----|------|
| Original (pre-split) | 26 | 20 | 21 | 2024-03-11 |
| 5.x at `732e25c6` | 5 | 6 | 9 | 2025-09-22 |
| `mothbox_paths.py` defaults | 26 | 20 | 21 | 2025-10-08 |
| 5.x `Flash_On.py` at `732e25c6` | -- | 19 | -- | 2025-09-22 |
| Production `controls.txt` | 5 | 19 | 9 | Current |

The change of Ch2 from 6 to 19 between `732e25c6` and the current `controls.txt` indicates a hardware revision. GPIO 6 remains orphaned as output on the production Pi.

Source: `git_history.md` Section 7, `runtime_state.md` Section 2.

---

## 4. Operation Inventory

Every `GPIO.setup()`, `GPIO.output()`, `GPIO.input()`, `GPIO.cleanup()`, and `GPIO.setmode()` call from AST extraction, summarized per production file. OldScripts and test files excluded for brevity.

### 4.1 Relay Control Scripts -- 5.x

**`5.x/Attract_On.py`**:

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 30 | `GPIO.setwarnings` | `False` | module |
| 31 | `GPIO.setmode` | `GPIO.BCM` | module |
| 33 | `GPIO.setup` | `Relay_Ch1, GPIO.OUT` | module |
| 34 | `GPIO.setup` | `Relay_Ch2, GPIO.OUT` | module |
| 36 | `GPIO.setup` | `Relay_Ch3, GPIO.OUT` | module |
| 52 | `GPIO.output` | `Relay_Ch3, GPIO.HIGH` | AttractOn |
| 53 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | AttractOn |
| 54 | `GPIO.output` | `Relay_Ch1, GPIO.HIGH` | AttractOn |
| 60 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | AttractOff |
| 61 | `GPIO.output` | `Relay_Ch2, GPIO.LOW` | AttractOff |
| 62 | `GPIO.output` | `Relay_Ch1, GPIO.LOW` | AttractOff |

**`5.x/Attract_Off.py`**: Identical structure to `Attract_On.py` (same operations, same lines). The file calls `AttractOff()` at bottom.

**`5.x/Flash_On.py`**:

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 27 | `GPIO.setwarnings` | `False` | module |
| 28 | `GPIO.setmode` | `GPIO.BCM` | module |
| 30 | `GPIO.setup` | `Relay_Ch1, GPIO.OUT` | module |
| 46 | `GPIO.output` | `Relay_Ch1, GPIO.LOW` | AttractOff |
| 51 | `GPIO.output` | `Relay_Ch1, GPIO.HIGH` | AttractOn |

Note: `Relay_Ch1` variable is aliased to `pins["Relay_Ch2"]` at line 25.

**`5.x/Flash_Off.py`**: Same structure as `Flash_On.py`. Calls `AttractOff()` at bottom (pin LOW).

**`5.x/FlashOn.py`**:

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 31 | `GPIO.setwarnings` | `False` | module |
| 32 | `GPIO.setmode` | `GPIO.BOARD` | module |
| 35 | `GPIO.setup` | `Relay_Ch2, GPIO.OUT` | module |
| 53 | `GPIO.output` | `Relay_Ch2, GPIO.LOW` | FlashOn |
| 58 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | FlashOff |

### 4.2 TakePhoto.py -- 5.x

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 66 | `GPIO.setmode` | `GPIO.BCM` | module |
| 72 | `GPIO.setup` | `off_pin, GPIO.IN` | off_connected_to_ground |
| 75 | `GPIO.input` | `off_pin` | off_connected_to_ground |
| 83 | `GPIO.setup` | `debug_pin, GPIO.IN` | debug_connected_to_ground |
| 86 | `GPIO.input` | `debug_pin` | debug_connected_to_ground |
| 97 | `GPIO.setup` | `off_pin, GPIO.IN` | module |
| 98 | `GPIO.setup` | `debug_pin, GPIO.IN` | module |
| 174 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | flashOff |
| 177 | `GPIO.output` | `Relay_Ch2, GPIO.LOW` | flashOff |
| 182 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | flashOn |
| 183 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | flashOn |
| 741 | `GPIO.setwarnings` | `False` | module |
| 742 | `GPIO.setmode` | `GPIO.BCM` | module |
| 745 | `GPIO.setup` | `Relay_Ch2, GPIO.OUT` | module |
| 746 | `GPIO.setup` | `Relay_Ch3, GPIO.OUT` | module |
| 752 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | module (flash on at start) |
| 753 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | module (attract "on") |
| 910 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | module (ensure attract stays on) |
| 925 | `GPIO.cleanup` | `Relay_Ch2` | module (cleanup flash pin only) |

### 4.3 DebugMode.py -- 5.x

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 53 | `GPIO.setwarnings` | `False` | module |
| 54 | `GPIO.setmode` | `GPIO.BCM` | module |
| 56 | `GPIO.setup` | `Relay_Ch1, GPIO.OUT` | module |
| 57 | `GPIO.setup` | `Relay_Ch2, GPIO.OUT` | module |
| 59 | `GPIO.setup` | `Relay_Ch3, GPIO.OUT` | module |
| 65 | `GPIO.output` | `Relay_Ch3, GPIO.LOW` | AttractOn |
| 67 | `GPIO.output` | `Relay_Ch2, GPIO.LOW` | AttractOn |
| 70 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | AttractOn |
| 72 | `GPIO.output` | `Relay_Ch1, GPIO.LOW` | AttractOn |
| 77 | `GPIO.output` | `Relay_Ch1, GPIO.HIGH` | AttractOff |
| 79 | `GPIO.output` | `Relay_Ch2, GPIO.HIGH` | AttractOff |
| 80 | `GPIO.output` | `Relay_Ch3, GPIO.HIGH` | AttractOff |

### 4.4 Scheduler.py -- 5.x

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 106 | `GPIO.setup` | `off_pin, GPIO.IN` | off_connected_to_ground |
| 109 | `GPIO.input` | `off_pin` | off_connected_to_ground |
| 117 | `GPIO.setup` | `debug_pin, GPIO.IN` | debug_connected_to_ground |
| 120 | `GPIO.input` | `debug_pin` | debug_connected_to_ground |
| 500 | `GPIO.cleanup` | (all) | run_shutdown_pi5 |
| 578 | `GPIO.cleanup` | (all) | run_shutdown_pi5_FAST |
| 773 | `GPIO.setmode` | `GPIO.BCM` | module |
| 780 | `GPIO.setup` | `off_pin, GPIO.IN` | module |
| 781 | `GPIO.setup` | `debug_pin, GPIO.IN` | module |
| 935 | `GPIO.cleanup` | (all) | module (before shutdown) |

### 4.5 Web UI gpio.py

| Line | Operation | Arguments | Context |
|------|-----------|-----------|---------|
| 27 | `GPIO.setmode` | `GPIO.BCM` | module load |
| 28 | `GPIO.setwarnings` | `False` | module load |
| 66 | `GPIO.setup` | `test_pin, GPIO.OUT, initial=GPIO.LOW` | _validate_gpio_permissions |
| 85 | `GPIO.cleanup` | `test_pin` | _validate_gpio_permissions |
| 228 | `GPIO.setup` | `pin, GPIO.OUT` | control_gpio |
| 230 | `GPIO.output` | `pin, GPIO.HIGH if state else GPIO.LOW` | control_gpio |
| 270 | `GPIO.setup` | `flash_pin, GPIO.OUT` | trigger_flash |
| 272 | `GPIO.output` | `flash_pin, GPIO.HIGH` | trigger_flash (on) |
| 275 | `GPIO.output` | `flash_pin, GPIO.LOW` | trigger_flash (off) |

### 4.6 scripts/ Subdirectory (5.x) -- Summary

All scripts in `5.x/scripts/` (excluding OldScripts and e-paper) follow the same pattern: BCM mode, setup all 3 channels as OUT, active-LOW polarity for flash on/off (matching 4.x convention, NOT updated for 5.x).

| Script | Channels Used | Polarity | Cleanup |
|--------|--------------|----------|---------|
| `CheckFocus.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `FlashOn_ManPhoto_FlashOff.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `Flash_On.py` (scripts/) | Ch1-3 setup, all channels output | Active-LOW | No |
| `Flash_Off.py` (scripts/) | Ch1-3 setup, all channels output | Active-LOW | No |
| `Full_Test_Relay_Photo_Logging_Shutdown.py` | Ch1-3 setup, Ch1+Ch3 output | Active-LOW | No |
| `PlowmanAutofocus.py` | Ch1-3 setup, Ch2 output | Active-LOW | No |
| `Relay_Module.py` | Ch1-3 setup, all channels output | Active-LOW | Yes |
| `ReadMuxAMuxB.py` | Mux pins (BOARD mode) | N/A | Yes |
| `CheckGPIOPin.py` | Switch pins 16/12 (input) | N/A | Yes |
| `TakePhoto16mp.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakePhotoHDR_Fast_WithEXIF.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakePhoto_AutoExposure.py` | Ch1-3 setup, Ch2 output | Active-LOW | No |
| `TakePhoto_HDR.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakePhoto_Stereo_HDR.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakePhoto_noAuto.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakePhoto_uniqueAutoID.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |
| `TakeSinglePhoto with flash.py` | Ch1-3 setup, Ch2+Ch3 output | Active-LOW | No |

All 5.x/scripts/ files retain the 4.x active-low polarity. They were never updated for the 5.x polarity change.

### 4.7 capture_focus_bracket.py (Web UI Backend)

Uses a `GPIOHandler` class that wraps `RPi.GPIO`:

| Line | Operation | Context |
|------|-----------|---------|
| 371 | `gpio.setwarnings(False)` | GPIOHandler.setup |
| 372 | `gpio.setmode(gpio.BCM)` | GPIOHandler.setup |
| 373-375 | `gpio.setup(relay_chN, gpio.OUT)` | GPIOHandler.setup |
| (flash_on) | `gpio.output(relay_ch2, gpio.HIGH)` | GPIOHandler.flash_on |
| (flash_on) | `gpio.output(relay_ch3, gpio.LOW)` | GPIOHandler.flash_on |
| (flash_off) | `gpio.output(relay_ch2, gpio.LOW)` | GPIOHandler.flash_off |

**Polarity**: Ch2=HIGH for on (active-high), Ch3=LOW for on (MIXED, matching TakePhoto.py).

---

## 5. Logic Pipelines

Full signal path analysis is documented in `tools/gpio_audit/logic_pipelines.md`. 18 pipelines were traced covering all trigger-to-outcome paths.

### 5.1 Polarity Comparison Matrix

| Script | Ch1 ON | Ch1 OFF | Ch2 ON | Ch2 OFF | Ch3 ON | Ch3 OFF | Convention |
|--------|--------|---------|--------|---------|--------|---------|------------|
| **4.x Attract_On.py** | LOW | -- | HIGH* | -- | LOW | -- | Active-LOW |
| **4.x Attract_Off.py** | -- | HIGH | -- | HIGH | -- | HIGH | Active-LOW |
| **4.x TakePhoto flashOn** | -- | -- | LOW | -- | LOW | -- | Active-LOW |
| **4.x TakePhoto flashOff** | -- | -- | -- | HIGH | LOW(stay) | -- | Active-LOW |
| **5.x Attract_On.py** | HIGH | -- | HIGH | -- | HIGH | -- | Active-HIGH |
| **5.x Attract_Off.py** | -- | LOW | -- | LOW | -- | LOW | Active-HIGH |
| **5.x TakePhoto flashOn** | -- | -- | HIGH | -- | LOW | -- | **MIXED** |
| **5.x TakePhoto flashOff** | -- | -- | -- | LOW | LOW(stay) | -- | **MIXED** |
| **5.x Flash_On.py** | -- | -- | HIGH | -- | -- | -- | Active-HIGH |
| **5.x Flash_Off.py** | -- | -- | -- | LOW | -- | -- | Active-HIGH |
| **5.x FlashOn.py** | -- | -- | LOW | -- | -- | -- | Active-LOW** |
| **5.x DebugMode AttractOff** | -- | HIGH | -- | HIGH | -- | HIGH | Active-LOW |
| **5.x gpio.py control** | HIGH | LOW | -- | -- | -- | -- | Active-HIGH |
| **5.x gpio.py flash** | -- | -- | HIGH | LOW | -- | -- | Active-HIGH |

*4.x Attract_On Ch2: HIGH when not in `onlyflash` mode (flash off during attract), LOW in `onlyflash` mode.
**FlashOn.py also has BOARD/BCM mode bug so it operates the wrong physical pin entirely.

Source: `logic_pipelines.md`, Polarity Comparison Matrix.

### 5.2 Key Contradictions

1. **5.x TakePhoto.py Ch3 vs 5.x Attract_On.py Ch3**: TakePhoto sends LOW for "attract on"; Attract_On sends HIGH for "attract on". These cannot both be correct for the same relay.

2. **5.x DebugMode.py vs 5.x Attract_On.py**: DebugMode sends HIGH to "turn off"; Attract_On sends HIGH to "turn on". These are opposite interpretations of the same signal level on the same pins.

3. **5.x FlashOn.py vs 5.x Flash_On.py**: FlashOn sends LOW for "on" (active-low); Flash_On sends HIGH for "on" (active-high). FlashOn also uses wrong pin mode (BOARD).

4. **5.x scripts/ subdirectory**: All TakePhoto variants, Flash_On/Off, CheckFocus, etc. in `scripts/` use active-LOW (4.x convention), contradicting the top-level 5.x active-HIGH scripts.

---

## 6. Entry Points

Every mechanism that can trigger GPIO operations.

| Entry Point | Mechanism | Scripts/Code Invoked | GPIO Pins Affected |
|-------------|-----------|---------------------|-------------------|
| Web UI relay toggle | `POST /api/gpio/control` | `gpio.py:control_gpio()` | Any relay pin (Ch1/Ch2/Ch3) |
| Web UI flash button | `POST /api/gpio/flash` | `gpio.py:trigger_flash()` | Relay_Ch2 |
| Web UI capture photo | `POST /api/camera/capture` | `camera.py` -> subprocess `TakePhoto.py` | Ch2, Ch3, switch pins 16/12 |
| Web UI focus bracket | `POST /api/camera/focus-bracket` | `capture_focus_bracket.py` GPIOHandler | Ch1, Ch2, Ch3 |
| Scheduler (cron) attract on | Crontab entry via `cron_bridge.py` | `Attract_On.py` | Ch1, Ch2, Ch3 |
| Scheduler (cron) attract off | Crontab entry via `cron_bridge.py` | `Attract_Off.py` | Ch1, Ch2, Ch3 |
| Scheduler (cron) flash on | Crontab entry via `cron_bridge.py` | `Flash_On.py` | Ch2 (aliased from Relay_Ch2) |
| Scheduler (cron) flash off | Crontab entry via `cron_bridge.py` | `Flash_Off.py` | Ch2 (aliased from Relay_Ch2) |
| Scheduler (cron) takephoto | Crontab entry via `cron_bridge.py` | `TakePhoto.py` | Ch2, Ch3, switch pins 16/12 |
| Boot-time Scheduler.py | systemd/cron starts `Scheduler.py` | `Scheduler.py` -> physical switch check -> branch to mode | Switch pins 16/12 |
| Boot -> DEBUG mode | `Scheduler.py` detects debug switch | `DebugMode.py` | Ch1, Ch2, Ch3 |
| Shutdown timer | `Scheduler.py` timer fires | `GPIO.cleanup()`, `UpdateDisplay.py` | All pins reset, then e-paper pins |
| CLI direct invocation | `python3 <script>` | Any relay script | Depends on script |
| Web UI startup | Flask module import | `gpio.py:_validate_gpio_permissions()` | Relay_Ch1 (brief LOW pulse) |

Source: `grep_results.md` Sections 1-4, `logic_pipelines.md` Pipeline 1-18.

---

## 7. Cleanup Patterns

### 7.1 Scripts With GPIO.cleanup()

| Script | Location | Scope | Notes |
|--------|----------|-------|-------|
| `{4,5}.x/Scheduler.py` | Lines 500, 578, 935 | All pins | Only on shutdown path |
| `{4,5}.x/scripts/ReadMuxAMuxB.py` | Line 113 | All pins | In finally block |
| `{4,5}.x/scripts/Relay_Module.py` | Line 67 | All pins | After interactive test |
| `{4,5}.x/scripts/CheckGPIOPin.py` | Line 58 | All pins | After diagnostic |
| `{4,5}.x/UpdateDisplay.py` | Line 293/316 | All pins | At script end |
| `webui/backend/routes/gpio.py` | Line 85 | Single pin (test_pin) | During startup validation only |
| `5.x/TakePhoto.py` | Line 925 | Single pin (Relay_Ch2) | Flash pin only; Ch3 intentionally left |
| E-paper driver (epdconfig.py) | Line 250 | E-paper pins | In module_exit (JetsonNano/SunriseX3 paths) |

### 7.2 Scripts Without GPIO.cleanup()

| Script | Consequence |
|--------|-------------|
| `5.x/Attract_On.py` | All 3 relay pins persist as output at their last value (HIGH) |
| `5.x/Attract_Off.py` | All 3 relay pins persist as output at their last value (LOW) |
| `5.x/Flash_On.py` | Pin 19 persists as output HIGH |
| `5.x/Flash_Off.py` | Pin 19 persists as output LOW |
| `5.x/FlashOn.py` | Pin persists as output (wrong pin due to BOARD bug) |
| `5.x/DebugMode.py` | All 3 relay pins persist as output HIGH |
| All `scripts/TakePhoto*.py` variants | Relay pins persist |
| `scripts/Flash_On.py`, `scripts/Flash_Off.py` | All 3 relay pins persist |
| `scripts/CheckFocus.py` | Relay pins persist |
| `scripts/PlowmanAutofocus.py` | Relay pins persist |
| `scripts/FlashOn_ManPhoto_FlashOff.py` | Relay pins persist |
| `scripts/Full_Test_Relay_Photo_Logging_Shutdown.py` | Relay pins persist |
| `webui/backend/routes/gpio.py` (runtime) | Pins persist between HTTP requests (by design) |

### 7.3 Behavior on Pi 5

On Pi 5 with the lgpio backend, GPIO pin state persists after the controlling process exits. This is confirmed by runtime observation: GPIO 5 and GPIO 6 are configured as outputs with no process holding them open (`lsof` returned empty).

This means the lack of `GPIO.cleanup()` has a tangible effect: relays remain energized (or de-energized) indefinitely after script exit, with no controlling process to manage their state.

Source: `runtime_state.md` Section 6, `logic_pipelines.md` BUG-6.

---

## 8. Mode Conflicts

### 8.1 BCM Mode (Standard)

Every modern relay/sensor script uses `GPIO.setmode(GPIO.BCM)`. Files confirmed BCM:

- All `{4,5}.x/Attract_On.py`, `Attract_Off.py`, `TakePhoto.py`, `DebugMode.py`
- `{4,5}.x/Scheduler.py`, `UpdateDisplay.py`
- All `{4,5}.x/scripts/` (except ReadMuxAMuxB.py and OldScripts)
- `5.x/Flash_On.py`, `Flash_Off.py`
- `webui/backend/routes/gpio.py`
- E-paper driver (`epdconfig.py`)

Source: `grep_results.md` Section 9.

### 8.2 BOARD Mode

| File | Intentional? | Risk |
|------|-------------|------|
| `{4,5}.x/FlashOn.py:32` | **No** (bug) | BCM pin from `get_gpio_pins()` interpreted as BOARD number. Wrong physical pin operated. |
| `{4,5}.x/scripts/ReadMuxAMuxB.py:19` | **Yes** | `get_mux_pins()` returns BOARD numbers. Correct usage. |
| `{4,5}.x/scripts/OldScripts/RingLight_Autofocus_TakePhoto.py:20` | Legacy | BOARD mode with hardcoded pins. Not in active use. |
| `{4,5}.x/scripts/OldScripts/TurnOffBlackLights.py:9` | Legacy | BOARD mode with hardcoded pins. Not in active use. |
| `{4,5}.x/scripts/OldScripts/TurnOnBlackLights.py:9` | Legacy | BOARD mode with hardcoded pins. Not in active use. |
| `{4,5}.x/scripts/OldScripts/onepicture_GPIO.py:19` | Legacy | BOARD mode with hardcoded pins. Not in active use. |

### 8.3 Mode Conflict Scenarios

The RPi.GPIO library enforces a single mode per process. `GPIO.setmode()` cannot be called with a different mode after it has been set. This means:

1. If `gpio.py` (BCM mode, Flask process) is running, any attempt to use BOARD mode from the same process would fail.
2. Separate scripts run as subprocesses (cron, Scheduler.py) have their own GPIO mode context.
3. `FlashOn.py` sets BOARD mode but receives BCM pin numbers -- this is a bug, not a conflict.
4. `ReadMuxAMuxB.py` uses BOARD mode intentionally and runs as a standalone script, so no conflict with BCM scripts.

Source: `grep_results.md` Section 9.

---

## 9. Runtime State

Captured from production Raspberry Pi 5 on 2026-02-08. Full details in `tools/gpio_audit/runtime_state.md`.

### 9.1 Relay Pin State at Capture Time

| GPIO | Config Role | Direction | pinctrl | Reads | Consumer |
|------|------------|-----------|---------|-------|----------|
| 5 | Relay_Ch1 | output | op dh pn | HIGH | "lg" |
| 19 | Relay_Ch2 | input | ip pn | LOW | (none) |
| 9 | Relay_Ch3 | input | ip pn | LOW | (none) |
| 6 | (none -- orphaned) | output | op dh pn | HIGH | "lg" |

Source: `runtime_state.md` Sections 1-2.

### 9.2 Switch Pin State

| GPIO | Role | Direction | pinctrl | Reads |
|------|------|-----------|---------|-------|
| 16 | off_pin | input | ip pu | HIGH |
| 12 | debug_pin | input | ip pu | HIGH |

Both switch pins read HIGH (not grounded), indicating ACTIVE mode (not OFF, not DEBUG).

### 9.3 E-paper Pin State

All e-paper pins (17, 25, 8, 24, 18) are in default unconfigured state (`no pd` or `no pu`). No active display update was running at capture time.

### 9.4 I2C Bus

No I2C devices detected at any address (0x00-0x77). INA260 and PCA9536 either not connected or not powered.

### 9.5 Services

- `mothbox-webui.service`: Active, running for 13+ hours, 2 workers (PID 422789, 422805)
- No processes holding GPIO file descriptors (yet GPIO 5 and 6 remain as outputs)
- No crontab entries for any user
- RTC wakealarm write fails with permission denied

### 9.6 GPIO 6 Orphan Analysis

GPIO 6 is configured as output, driving HIGH, with "lg" consumer, but is not referenced anywhere in the current configuration (`controls.txt` maps Ch1=5, Ch2=19, Ch3=9). GPIO 6 was the original 5.x Relay_Ch2 pin assigned in commit `732e25c6` before it was changed to pin 19. The pin state persists from a previous script execution and was never cleaned up.

Source: `runtime_state.md` Section 12, `git_history.md` Section 7.

---

## 10. Deployed vs Repo Diff

Comparison performed on the production Pi at `/opt/mothbox` against the local repository.

### 10.1 Script Parity

| Script | Deployed vs Repo |
|--------|-----------------|
| `5.x/Attract_On.py` | **IDENTICAL** |
| `5.x/Attract_Off.py` | **IDENTICAL** |
| `5.x/Flash_On.py` | **IDENTICAL** |
| `5.x/Flash_Off.py` | **IDENTICAL** |
| `5.x/FlashOn.py` | **IDENTICAL** |
| `5.x/TakePhoto.py` | **IDENTICAL** |
| `5.x/TurnEverythingOff.py` | **IDENTICAL** |

All deployed GPIO scripts match the repository exactly. No code drift.

Source: `runtime_state.md` Section 11.

### 10.2 Configuration Parity

| Category | Deployed | Repo |
|----------|----------|------|
| Relay pins (Ch1/Ch2/Ch3) | 5/19/9 | 5/19/9 | **IDENTICAL** |
| relay_enabled | true | true | **IDENTICAL** |
| flash_duration_ms | 100 | 100 | **IDENTICAL** |
| OnlyFlash | False | False | **IDENTICAL** |
| softwareversion | 5.0.0 | 5.0.0 | **IDENTICAL** |

**Differences** (non-GPIO): Deployed Pi is missing 6 GPS fields (`gps_fix_mode`, `gps_satellites_used`, etc.), gallery cache config, and logging config that exist in the repo `controls.txt`. These are unrelated to GPIO operation.

Source: `runtime_state.md` Section 10.

### 10.3 Deployment Status

- Only `5.x/` firmware is deployed. `4.x/` directory does not exist on the production Pi.
- No crontab entries active (scheduling is via the web UI's internal scheduler).
- Web UI service is the sole active GPIO consumer.

---

## 11. Git Evolution

Key timeline of GPIO-relevant changes in the repository.

| Date | Commit | Author | Event |
|------|--------|--------|-------|
| 2024-03-11 | `f4c230f2` | Andrew Quitmeyer | Original GPIO scripts created. Active-LOW polarity. Hardcoded pins 26/20/21. |
| 2024-03-14 | `c08a6d5d` | Andrew Quitmeyer | Added `OnlyFlash` mode, `control_values` reader. |
| 2025-06-17 | `7ef88c18` | Andrew Quitmeyer | Added `FlashOn.py` with GPIO.BOARD mode (pre-split). Active-LOW. |
| 2025-09-20 | `6b9cb4d1` | Andrew Quitmeyer | Split `Firmware/` into `4.x/` and `5.x/`. Files are identical verbatim copies. |
| 2025-09-22 | `732e25c6` | Andrew Quitmeyer | **5.x polarity reversal**: Changed to active-HIGH, new pins (5/6/9). Created `Flash_On.py`/`Flash_Off.py` (pin 19, active-HIGH). Removed `onlyflash` conditional from 5.x top-level scripts. `DebugMode.py`, `FlashOn.py`, and all `scripts/` subdirectory files were NOT updated. |
| 2025-10-06 | `d183049c` | Zane Lazare | Refactored 4.x utility scripts to use dynamic paths. |
| 2025-10-08 | `a5065cd2` | Zane Lazare | Added `get_gpio_pins()` to `mothbox_paths.py`. Replaced hardcoded pins in 4.x and 5.x scripts. Default pins set to 4.x values (26/20/21). |
| 2025-10-11 | `5ca53a03` | Zane Lazare | Created Web UI with `gpio.py` routes. Active-HIGH assumption throughout (matches 5.x top-level scripts but not 4.x). |
| 2025-10-31 | `ce3fd3f2` | Zane Lazare | Added unit tests for GPIO and config routes. |
| 2025-11-05 | `d7c8b5b0` | Zane Lazare | Ruff linting cleanup. Reformatted all files (cosmetic only, no logic changes). Git blame now attributes GPIO polarity lines to this commit. |
| 2025-12-30 | `97e252ef` | Zane Lazare | Migrated `gpio.py` `print()` to logging module. |

### 11.1 Key Observations from History

1. **The polarity reversal at `732e25c6` was intentional** but incomplete. Andrew Quitmeyer updated `Attract_On.py`, `Attract_Off.py`, and created new `Flash_On.py`/`Flash_Off.py` with active-HIGH logic. He did NOT update `DebugMode.py`, `FlashOn.py`, `TakePhoto.py` (Ch3 specifically), or any files in the `scripts/` subdirectory.

2. **No commit message or documentation explains the polarity change**. The commit message is simply "updated 5 firmware". There is no record anywhere stating "4.x uses active-low, 5.x uses active-high" or why.

3. **`get_gpio_pins()` was designed with 4.x defaults**. When Zane Lazare created the configuration system at `a5065cd2`, the fallback defaults were set to 4.x pin numbers (26/20/21). For 5.x hardware to work, `controls.txt` must explicitly set `Relay_Ch1=5`, `Relay_Ch2=19`, `Relay_Ch3=9`.

4. **Relay_Ch2 pin changed from 6 to 19** between the initial 5.x commit (`732e25c6`, pin 6) and the current production config (pin 19). This is likely a hardware revision. GPIO 6 remains orphaned on the production Pi.

5. **`OnlyFlash` conditional was silently removed from 5.x**. The 4.x scripts have complex conditional logic for `OnlyFlash` mode. The 5.x rewrite at `732e25c6` removed this logic entirely. The `OnlyFlash` config key still exists in `controls.txt` but is silently ignored by 5.x top-level scripts.

Source: `git_history.md` Sections 1-8.

---

## 12. Known Bugs

Every confirmed intent-vs-outcome mismatch in the GPIO system. Numbered for tracking.

### BUG-1: 5.x TakePhoto.py Ch3 Contradicts 5.x Attract_On.py

**Files**: `5.x/TakePhoto.py:183` vs `5.x/Attract_On.py:52`

**Details**: TakePhoto.py's `flashOn()` function sends `GPIO.output(Relay_Ch3, GPIO.LOW)` with the comment "ensure attract is on because new wiring dictates that". Attract_On.py sends `GPIO.output(Relay_Ch3, GPIO.HIGH)` to turn attract on. These are opposite polarities for the same pin with the same stated intent.

**Impact**: If Attract_On.py is correct (active-HIGH), then TakePhoto.py turns off the attract relay every time it fires the flash. If TakePhoto.py is correct (active-LOW for Ch3), then Attract_On.py turns off the attract relay when it intends to turn it on.

**Root cause**: This is the core Issue #399 bug. The 5.x polarity reversal at `732e25c6` updated `Attract_On.py` but did not fully update `TakePhoto.py` Ch3 logic.

Source: `logic_pipelines.md` BUG-1.

### BUG-2: 5.x DebugMode.py Uses 4.x Polarity

**File**: `5.x/DebugMode.py:77-80`

**Details**: `AttractOff()` sends HIGH to all channels. In 4.x (active-LOW), HIGH means OFF. In 5.x (active-HIGH), HIGH means ON. DebugMode.py's purpose is to turn everything off, but on 5.x hardware it turns everything on.

**Evidence**: The `AttractOn()` and `AttractOff()` functions in DebugMode.py have the `onlyflash` conditional logic that was removed from the 5.x top-level scripts -- confirming this code was never updated for 5.x.

Source: `logic_pipelines.md` BUG-2.

### BUG-3: FlashOn.py BOARD/BCM Mode Mismatch

**File**: `5.x/FlashOn.py:32` (also `4.x/FlashOn.py:30`)

**Details**: Uses `GPIO.setmode(GPIO.BOARD)` but receives BCM pin number from `get_gpio_pins()`. With BCM pin 19 interpreted as BOARD pin 19 = physical pin 19 = GPIO10 (not GPIO19/physical pin 35). The wrong physical pin is operated.

**Impact**: On 5.x hardware, `FlashOn.py` drives GPIO10 instead of GPIO19. GPIO10 is the SPI MOSI pin, not a relay.

**Mitigation**: `FlashOn.py` is NOT in `cron_security.py`'s `ALLOWED_SCRIPTS`. It can only be run via direct CLI invocation, not via the scheduler.

Source: `logic_pipelines.md` BUG-3, `grep_results.md` Section 9.

### BUG-4: Flash_On.py / Flash_Off.py Naming Confusion

**Files**: `5.x/Flash_On.py:25`, `5.x/Flash_Off.py:25`

**Details**: Three separate naming bugs:
1. `Relay_Ch1 = pins["Relay_Ch2"]` -- local variable `Relay_Ch1` holds the pin for relay channel 2.
2. Functions are named `AttractOn()` / `AttractOff()` but the script controls flash.
3. Print banner says `"attract off!"` inside what is functionally a flash-on script.

**Impact**: Functionally correct (pin 19 goes HIGH/LOW as intended), but the code is misleading for maintenance.

Source: `logic_pipelines.md` BUG-4.

### BUG-5: Web UI State Desynchronization

**File**: `webui/backend/routes/gpio.py:184`

**Details**: `GET /api/gpio/status` reads from `gpio_state.json`, not live pin state. After any cron-triggered script (`Attract_On.py`, `TakePhoto.py`, etc.) changes GPIO state, the web UI shows stale toggle positions.

**Root cause**: The code comment at `gpio.py` explains: "Reading OUTPUT pins can be unreliable and may reset their state." No mechanism exists to synchronize external GPIO changes back to `gpio_state.json`.

**Impact**: User sees incorrect relay state in the web UI after scheduled actions run.

Source: `logic_pipelines.md` BUG-5.

### BUG-6: No GPIO.cleanup() in Relay Scripts

**Files**: `5.x/Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`, `FlashOn.py`, `DebugMode.py`

**Details**: None of the standalone relay scripts call `GPIO.cleanup()`. On Pi 5 with `rpi-lgpio`, pin configuration persists after the process exits.

**Runtime confirmation**: GPIO 5 is observed as output/HIGH with consumer "lg" and no process holding GPIO file descriptors. The pin was set by a previous script execution and remains driven indefinitely.

**Impact**: Relays remain in their last commanded state after script exit. This is arguably correct behavior for Attract_On (lights should stay on) but means there is no safety mechanism to return pins to input state after a script crash.

Source: `logic_pipelines.md` BUG-6, `runtime_state.md` Section 6.

### BUG-7: GPIO 6 Orphaned Output

**Source**: `runtime_state.md` Section 1

**Details**: GPIO 6 is configured as output, driving HIGH, with consumer "lg", but is not referenced in the current `controls.txt` (which maps Ch2 to pin 19). GPIO 6 was the original 5.x Relay_Ch2 pin in commit `732e25c6` before it was changed to 19.

**Impact**: Unknown device on GPIO 6 may be receiving power. If nothing is connected to GPIO 6, no immediate harm. If GPIO 6 is connected to hardware (e.g., an old relay wiring), it could be unintentionally powered.

Source: `runtime_state.md` Section 12, `git_history.md` Section 7.

### BUG-8: Hardcoded Switch Pins in 8 Files

**Files** (all hardcode `off_pin=16`, `debug_pin=12`):

| File | Lines |
|------|-------|
| `5.x/Scheduler.py` | 776-777 |
| `5.x/TakePhoto.py` | 93-94 |
| `5.x/UpdateDisplay.py` | 77-78 |
| `5.x/scripts/CheckGPIOPin.py` | 9-10 |
| `4.x/Scheduler.py` | 776-777 |
| `4.x/TakePhoto.py` | 97-98 |
| `4.x/UpdateDisplay.py` | 79-80 |
| `4.x/scripts/CheckGPIOPin.py` | 9-10 |

**Details**: These pins are not configurable via `controls.txt` or any function in `mothbox_paths.py`. If the PCB design changes the switch wiring, all 8 files must be manually edited.

Source: `grep_results.md` Section 10.

### BUG-9: Startup Permission Check Side Effect

**File**: `webui/backend/routes/gpio.py:66`

**Details**: At module load, `_validate_gpio_permissions()` calls `GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)` where `test_pin` is `Relay_Ch1` (GPIO 5 on 5.x). This briefly drives the pin LOW.

**Impact**: On active-LOW hardware (4.x), this causes a momentary relay activation at web UI startup. On active-HIGH hardware (5.x), this is a no-op (LOW = off). However, since `get_gpio_pins()` defaults to 4.x pin numbers (26), a misconfigured system could briefly activate the wrong pin at startup.

Source: `logic_pipelines.md` BUG-9.

### Additional Findings (Not Bugs, But Notable)

**`get_gpio_pins()` defaults to 4.x pins**: The fallback at `mothbox_paths.py:364` returns `{Relay_Ch1: 26, Relay_Ch2: 20, Relay_Ch3: 21}`. A 5.x installation that is missing `controls.txt` or has parse errors would silently use 4.x pin numbers, operating the wrong physical pins on 5.x hardware.

**`OnlyFlash` silently ignored on 5.x**: The `OnlyFlash` setting in `controls.txt` affects behavior in 4.x scripts (conditional Ch2 logic in `Attract_On.py`), but 5.x top-level scripts (`Attract_On.py`, `Attract_Off.py`) unconditionally drive all channels, ignoring the setting.

**`5.x/scripts/` subdirectory retains 4.x polarity**: Every TakePhoto variant and Flash_On/Flash_Off script in `5.x/scripts/` uses active-LOW polarity (LOW=on). These were copied from 4.x and never updated.

**Module-level pin loading in gpio.py**: `webui/backend/routes/gpio.py:15` calls `get_gpio_pins()` at import time, then calls it again inside each route handler. The module-level call is stale if `controls.txt` is modified at runtime.

**Pyright reports 17 errors in gpio.py**: All from the conditional `RPi.GPIO` import inside a `try/except` block. The `GPIO` variable is "possibly unbound" from pyright's perspective, though it is guarded by a runtime `GPIO_AVAILABLE` flag.

Source: `pyright_results.md` Section 6c.

---

*End of GPIO Raw Audit. This document is a factual reference for diagnostic purposes. Remediation recommendations belong in the target specification (Task 9).*
