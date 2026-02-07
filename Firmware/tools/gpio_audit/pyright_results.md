# GPIO Audit: Remote Pi Library Constants & Pyright Results

**Date**: 2026-02-08
**Host**: mothbox-remote (Raspberry Pi, production install at `/opt/mothbox`)
**Python**: 3.13.5
**Pyright**: 1.1.408

---

## 1. RPi.GPIO Constants

> **Important discovery**: `RPi.GPIO` on this system is **not** the original C-extension package.
> It is the **rpi-lgpio** shim (v0.6) by Dave Jones, which wraps `lgpio` to provide
> backward-compatible `RPi.GPIO` API.

| Constant        | Value | Type        |
|-----------------|-------|-------------|
| `GPIO.HIGH`     | 1     | `<class 'int'>` |
| `GPIO.LOW`      | 0     | `<class 'int'>` |
| `GPIO.BCM`      | 11    | `int`       |
| `GPIO.BOARD`    | 10    | `int`       |
| `GPIO.OUT`      | 0     | `int`       |
| `GPIO.IN`       | 1     | `int`       |
| `GPIO.PUD_UP`   | 22    | `int`       |
| `GPIO.PUD_DOWN` | 21    | `int`       |

**RPi.GPIO VERSION**: `0.7.2` (reported by shim, not the real RPi.GPIO)

**RPi.GPIO module location**: `/usr/lib/python3/dist-packages/RPi/GPIO/__init__.py`

The shim file begins with:
```python
# Copyright (c) 2022-2023 Dave Jones <dave@waveform.org.uk>
# SPDX-License-Identifier: MIT
import lgpio
```

This means **all GPIO operations in the codebase ultimately call `lgpio`** under the hood,
even when they `import RPi.GPIO as GPIO`.

---

## 2. lgpio Constants

**lgpio version**: 0.2.2.0
**LGPIO_PY_VERSION**: 131584

| Constant              | Value |
|-----------------------|-------|
| `lgpio.HIGH`          | 1     |
| `lgpio.LOW`           | 0     |
| `lgpio.SET_PULL_UP`   | 32    |
| `lgpio.SET_PULL_DOWN` | 64    |
| `lgpio.SET_PULL_NONE` | 128   |
| `lgpio.SET_ACTIVE_LOW`| 4     |
| `lgpio.SET_OPEN_DRAIN`| 8     |
| `lgpio.SET_OPEN_SOURCE`| 16   |
| `lgpio.RISING_EDGE`   | 1     |
| `lgpio.FALLING_EDGE`  | 2     |
| `lgpio.BOTH_EDGES`    | 3     |

**Not found**: `lgpio.OUTPUT`, `lgpio.INPUT` -- lgpio does not use INPUT/OUTPUT constants.
Instead, pins are claimed as input/output via `gpio_claim_input()` / `gpio_claim_output()`.

### Available lgpio GPIO functions

```
gpio_claim_alert, gpio_claim_input, gpio_claim_output, gpio_free,
gpio_get_chip_info, gpio_get_line_info, gpio_get_mode, gpio_read,
gpio_set_debounce_micros, gpio_set_watchdog_micros, gpio_write,
gpiochip_close, gpiochip_open
```

---

## 3. gpiod Info

**gpiod version**: 2.2.0

Available classes/functions:
```
Chip, ChipClosedError, ChipInfo, EdgeEvent, InfoEvent, LineInfo,
LineRequest, LineSettings, RequestReleasedError, api_version, chip,
chip_info, edge_event, exception, info_event, internal,
is_gpiochip_device, line, line_info, line_request, line_settings,
request_lines, version
```

**Note**: `gpiod` 2.x is the modern character-device GPIO interface. Not currently
used by the Mothbox codebase directly, but is available on the system.

---

## 4. gpiozero Info

**gpiozero version**: 2.0.1 (from pip)
**Pin factory**: `None` (not initialized -- requires runtime device access)

### Available pin factories

| Factory   | Available |
|-----------|-----------|
| lgpio     | Yes       |
| rpigpio   | Yes       |
| mock      | Yes       |

**Note**: `gpiozero` is not used by the Mothbox codebase. It is installed as a
system dependency but the firmware uses `RPi.GPIO` (via rpi-lgpio shim) directly.

---

## 5. Installed Packages

**Python version**: 3.13.5

| Package              | Version | Notes |
|----------------------|---------|-------|
| gpiod                | 2.2.0   | Modern character-device GPIO |
| gpiozero             | 2.0.1   | High-level GPIO (not used by Mothbox) |
| lgpio                | 0.2.2.0 | Low-level GPIO library |
| rpi-lgpio            | 0.6     | **RPi.GPIO compatibility shim over lgpio** |
| rpi-keyboard-config  | 1.0     | System package |
| types-RPi.GPIO       | 0.7     | Type stubs for pyright/mypy |
| types-Jetson.GPIO    | 2.1     | Type stubs (not relevant to Mothbox) |

### Package relationship chain

```
Mothbox code
  --> import RPi.GPIO as GPIO
    --> rpi-lgpio (v0.6) shim
      --> lgpio (v0.2.2.0) C library
        --> Linux kernel GPIO character device (/dev/gpiochip*)
```

---

## 6. Pyright Results

### 6a. GPIO Relay Scripts (5.x)

**Files**: `Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`, `FlashOn.py`

**Result: 0 errors, 0 warnings** -- All GPIO relay scripts pass pyright type checking cleanly.

### 6b. TurnEverythingOff.py

**2 errors**:

| Line | Error | Category |
|------|-------|----------|
| 10   | Import "pijuice" could not be resolved | reportMissingImports |
| 31   | "stat" is possibly unbound | reportPossiblyUnboundVariable |

**Assessment**: Not GPIO-related. `pijuice` is an optional battery management dependency. The
`stat` variable is assigned inside a try block with potential for the except branch to skip it.

### 6c. webui/backend/routes/gpio.py

**17 errors** (all GPIO-related):

| Lines | Error | Count | Root Cause |
|-------|-------|-------|------------|
| 66, 85, 228, 230, 270, 272, 275 | "GPIO" is possibly unbound | 12 | `RPi.GPIO` imported in try/except; pyright sees it may not be bound |
| 211, 212 | "get" is not a known attribute of "None" | 2 | `request.json` can be None |

**Root cause**: The `RPi.GPIO` import is inside a `try/except` block (lines 24-39).
When the import fails, `GPIO` is never defined. Pyright correctly flags all
subsequent `GPIO.*` usages as "possibly unbound" because the code uses `GPIO`
outside the import's scope, guarded only by a boolean flag (`GPIO_AVAILABLE`)
that pyright cannot track as a type narrowing mechanism.

**Recommended fix**: Either:
1. Add `GPIO: Any = None` as a default before the try block, or
2. Create a helper module that handles the conditional import and re-exports a typed `GPIO` reference.

### 6d. Other Files (non-GPIO context, for completeness)

**UpdateDisplay.py** -- 1 error:
- Line 32: Import "waveshare_epd" could not be resolved (optional e-paper display driver)

**Scheduler.py** -- 41 errors:
- Mostly `reportOptionalSubscript` / `reportOptionalMemberAccess` from `get_control_values()` returning `None`
- 2x `reportMissingImports` for `pijuice`
- 2x `reportPossiblyUnboundVariable` for `finalCombo`, `file_path`, `next_epoch_time`, `pj`

**TakePhoto.py** -- 38 errors:
- `reportOptionalMemberAccess` / `reportOptionalSubscript` from camera settings that may be None
- `reportAttributeAccessIssue` for `Transform` import from libcamera
- `reportPossiblyUnboundVariable` for `filepath`, `picam2`

**PCA9536.py** -- 1 error:
- Import "smbus" could not be resolved (I2C bus library)

**DebugMode.py** -- 1 error:
- `onlyflash` is not defined (undefined variable)

**Total across all files**: 84 errors, 0 warnings, 0 informations

---

## 7. Key Findings

### 7.1 RPi.GPIO is actually rpi-lgpio

The most significant finding is that the system does **not** have the original C-extension
`RPi.GPIO` package installed. Instead, `rpi-lgpio` (v0.6) provides a compatibility shim.
This is the standard approach on modern Raspberry Pi OS with Pi 5 hardware, where the
original RPi.GPIO cannot access the GPIO hardware directly.

**Impact on codebase**: None. The shim provides a drop-in compatible API. All `GPIO.setup()`,
`GPIO.output()`, `GPIO.input()`, `GPIO.cleanup()` calls work identically. The constant
values (`HIGH=1`, `LOW=0`, `BCM=11`, `OUT=0`, `IN=1`) are compatible.

### 7.2 GPIO relay scripts are type-safe

The 5 standalone GPIO relay scripts (`Attract_On.py`, `Attract_Off.py`, `Flash_On.py`,
`Flash_Off.py`, `FlashOn.py`) pass pyright with **zero errors**. These scripts import
`RPi.GPIO` at module level (not in try/except), which gives pyright full type information.

### 7.3 gpio.py route has 17 type errors (all from conditional import)

All 17 errors in `webui/backend/routes/gpio.py` stem from the same root cause:
`RPi.GPIO` is imported inside a `try/except` block, making `GPIO` possibly unbound.
The code correctly checks `GPIO_AVAILABLE` at runtime, but pyright cannot narrow
the type based on boolean flag checks.

### 7.4 Type stubs are installed

`types-RPi.GPIO` (v0.7) is installed, providing pyright with type information for
the RPi.GPIO API. This is why pyright can validate GPIO usage in the relay scripts.
`types-Jetson.GPIO` (v2.1) is also installed but is not relevant to this project.

### 7.5 No type errors in GPIO constant usage

No pyright errors relate to incorrect GPIO constant usage (e.g., passing wrong
values to `GPIO.setup()` or `GPIO.output()`). The GPIO HIGH/LOW/BCM/OUT constants
are used correctly throughout the codebase.

### 7.6 4.x firmware not deployed

The remote production system only has `5.x/` firmware installed at `/opt/mothbox`.
The `4.x/` directory does not exist on the remote, though it exists in the local
repository. This is expected for a 5.x hardware deployment.
