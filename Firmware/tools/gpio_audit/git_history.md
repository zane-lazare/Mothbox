# GPIO Audit - Git History Analysis

Generated: 2026-02-08

## 1. 5.x Script History

All 5.x GPIO scripts trace back to the same origin: the original `Software/` directory scripts,
split into `Firmware/4.x/` and `Firmware/5.x/` on 2025-09-20.

### Combined commit log (5.x/Attract_On.py, Attract_Off.py, Flash_On.py, Flash_Off.py, FlashOn.py, TakePhoto.py, TurnEverythingOff.py)

```
d1c3d87b 2025-02-?? fix(firmware): apply user's AfRange/AfSpeed during calibration
56783699 2025-02-?? fix(firmware): apply calibrated focus to capture path
7036cadb 2025-02-?? feat(firmware): replace PNG with TIFF for lossless capture
eaee598d            refactor(firmware): add type hints, unknown setting warnings, and schema tests
43ca3993            feat(firmware): add shared camera_settings_schema for CSV type coercion
93e5fc00            fix(firmware): coerce unknown CSV settings to numeric types for picamera2
8d32c79f            fix(firmware): handle webui colour gain and focus bracket CSV settings
31d2353d            fix(camera): add picam2.close() in TakePhoto.py cleanup
83866e84            fix(camera): remove false warnings and duplicate settings loading
7513cfca            security: improve directory permissions from 0o755 to 0o750
d7c8b5b0 2025-11-05 refactor: complete ruff linting cleanup - fix all 26 errors
a94f05ae            fix: resolve 27 backend test failures
15d56423            fix(camera): apply BGR888 format fix to all camera outputs
5ca53a03 2025-10-11 Add Web UI with GPIO controls, diagnostic endpoints, and installer improvements (#22)
71580b43            fix: address PR review feedback from Claude
a5065cd2 2025-10-08 feat: add interactive GPIO pin configuration
628a0e94            fix: address security review - correct permissions and add path validation
17a1c1c7            refactor: complete remaining hardcoded path replacements
0f660d28            feat: add central path configuration module and refactor core scripts
732e25c6 2025-09-22 updated 5 firmware                    [Andrew Quitmeyer]
6b9cb4d1 2025-09-20 made new separate firmware for v4 and v5 mothboxes   [Andrew Quitmeyer]
```

### Key milestones for 5.x GPIO:

| Date | Commit | Author | Event |
|------|--------|--------|-------|
| 2025-09-20 | `6b9cb4d1` | Andrew Quitmeyer | Split `Firmware/` into `4.x/` and `5.x/` -- files were identical copies |
| 2025-09-22 | `732e25c6` | Andrew Quitmeyer | **POLARITY REVERSAL**: Updated 5.x with new pin numbers AND flipped HIGH/LOW semantics. Also created `Flash_On.py` and `Flash_Off.py` |
| 2025-10-08 | `a5065cd2` | Zane Lazare | Replaced hardcoded pin numbers with `get_gpio_pins()` from `mothbox_paths.py` |
| 2025-10-11 | `5ca53a03` | Zane Lazare | Added Web UI with GPIO routes (used HIGH=on, LOW=off assumption) |
| 2025-11-05 | `d7c8b5b0` | Zane Lazare | Ruff linting cleanup -- reformatted code, no logic changes to GPIO |

---

## 2. 4.x Script History

The 4.x scripts retain the **original active-low polarity** from the pre-split era.

### Combined commit log

```
d1c3d87b fix(firmware): apply user's AfRange/AfSpeed during calibration
56783699 fix(firmware): apply calibrated focus to capture path
7036cadb feat(firmware): replace PNG with TIFF for lossless capture
...
d7c8b5b0 2025-11-05 refactor: complete ruff linting cleanup - fix all 26 errors
5ca53a03 2025-10-11 Add Web UI with GPIO controls
a5065cd2 2025-10-08 feat: add interactive GPIO pin configuration
d183049c 2025-10-06 feat: refactor 4.x utility scripts to use dynamic paths
0f660d28            feat: add central path configuration module and refactor core scripts
6b9cb4d1 2025-09-20 made new separate firmware for v4 and v5 mothboxes
```

### 4.x Polarity (ORIGINAL, from pre-split `Software/` directory)

From `4.x/Attract_On.py` at commit `6b9cb4d1` (initial split, verbatim copy from `Firmware/Attract_On.py`):

```python
def AttractOn():
    GPIO.output(Relay_Ch3, GPIO.LOW)      # LOW = relay ON (active-low)
    if onlyflash:
        GPIO.output(Relay_Ch2, GPIO.LOW)  # LOW = relay ON (active-low)
    else:
        GPIO.output(Relay_Ch2, GPIO.HIGH) # HIGH = relay OFF (flash stays off)
    GPIO.output(Relay_Ch1, GPIO.LOW)      # LOW = relay ON (active-low)

def AttractOff():
    GPIO.output(Relay_Ch1, GPIO.HIGH)     # HIGH = relay OFF (active-low)
    if onlyflash:
        GPIO.output(Relay_Ch2, GPIO.HIGH)
    else:
        GPIO.output(Relay_Ch2, GPIO.HIGH)
    GPIO.output(Relay_Ch3, GPIO.HIGH)     # HIGH = relay OFF (active-low)
```

This is **active-low** relay logic: LOW turns relays ON, HIGH turns relays OFF.

---

## 3. Web UI GPIO Route History

```
97e252ef 2025-12-30 feat(logging): Migrate from print() to Python logging module
6974156f 2025-11-09 feat(gallery): add grid/list view toggle with backend persistence
1d8906d1            fix(webui): use mothbox_import for consistent path resolution
d7c8b5b0 2025-11-05 refactor: complete ruff linting cleanup - fix all 26 errors
ce3fd3f2 2025-10-31 test: add comprehensive unit tests for GPIO and config routes
7ca5fa26            refactor: simplify logging and fix updater frontend rebuild logic
bad52402            debug: add verbose CSRF and GPIO request logging
5ca53a03 2025-10-11 Add Web UI with GPIO controls, diagnostic endpoints, and installer improvements (#22)
```

### GPIO polarity in `webui/backend/routes/gpio.py` (unchanged since creation)

The Web UI has used **active-high** logic since its creation at `5ca53a03`:

```python
# Line 229-230 (control_gpio function) - ORIGINAL AND CURRENT
# Set state (HIGH=1/True, LOW=0/False)
GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

# Line 64 (validation) - ORIGINAL AND CURRENT
GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)

# Lines 272-275 (flash trigger) - ORIGINAL AND CURRENT
GPIO.output(flash_pin, GPIO.HIGH)   # Turn on
time.sleep(flash_duration_sec)
GPIO.output(flash_pin, GPIO.LOW)    # Turn off
```

**Author**: Zane Lazare (all GPIO route code written 2025-10-11)

The Web UI GPIO route has NEVER been modified to match the 4.x active-low convention. It assumes HIGH=on throughout.

---

## 4. mothbox_paths GPIO Function History

```
80b7bc1a feat: add comprehensive hardware module configuration (WIP)
a5065cd2 2025-10-08 feat: add interactive GPIO pin configuration   [Zane Lazare]
```

### `get_gpio_pins()` pin defaults

At creation (2025-10-08) and currently:
```python
'Relay_Ch1': int(pins.get('Relay_Ch1', 26)),  # Default: 4.x pin
'Relay_Ch2': int(pins.get('Relay_Ch2', 20)),  # Default: 4.x pin
'Relay_Ch3': int(pins.get('Relay_Ch3', 21))   # Default: 4.x pin
```

The defaults map to **4.x pins (26/20/21)**. For 5.x hardware, users must set `Relay_Ch1=5`, `Relay_Ch2=19`, `Relay_Ch3=9` in `controls.txt`.

Note: The docstring comment says `Relay_Ch2=19` for 5.x, but the original 5.x scripts (at `732e25c6`) used `Relay_Ch2=6`. The pin 19 value appears to be a later correction or different hardware revision.

---

## 5. 5.x Creation Timeline

### Files first appearing in 5.x directory

| File | Commit | Date | Method |
|------|--------|------|--------|
| `5.x/Attract_On.py` | `6b9cb4d1` | 2025-09-20 | Copied from `Firmware/Attract_On.py` (identical to 4.x) |
| `5.x/Attract_Off.py` | `6b9cb4d1` | 2025-09-20 | Copied from `Firmware/Attract_Off.py` (identical to 4.x) |
| `5.x/Flash_On.py` | `732e25c6` | 2025-09-22 | **NEW FILE** created by Andrew Quitmeyer |
| `5.x/Flash_Off.py` | `732e25c6` | 2025-09-22 | **NEW FILE** created by Andrew Quitmeyer |
| `5.x/FlashOn.py` | `6b9cb4d1` | 2025-09-20 | Copied from `Firmware/FlashOn.py` |

### Fork from 4.x

At `6b9cb4d1`, the 5.x directory was a **verbatim copy** of 4.x (just `mv Firmware/* Firmware/4.x/` and copy to `5.x/`). They had identical GPIO polarity (active-low).

Two days later, at `732e25c6`, Andrew Quitmeyer:
1. Changed 5.x pin numbers from `26/20/21` to `5/6/9`
2. **Reversed the polarity**: Changed `AttractOn()` from LOW to HIGH, and `AttractOff()` from HIGH to LOW
3. Removed the `onlyflash` conditional logic from `Attract_On.py` and `Attract_Off.py`
4. Created new `Flash_On.py` and `Flash_Off.py` files with pin 19 (using GPIO.HIGH=on, GPIO.LOW=off)

---

## 6. Blame Analysis

### 5.x/Attract_On.py - GPIO polarity lines

| Line | Commit | Author | Date | Code |
|------|--------|--------|------|------|
| 52 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch3, GPIO.HIGH)` |
| 53 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch2, GPIO.HIGH)` |
| 54 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch1, GPIO.HIGH)` |
| 60 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch3, GPIO.LOW)` |
| 61 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch2, GPIO.LOW)` |
| 62 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch1, GPIO.LOW)` |

Note: `d7c8b5b0` was a **ruff linting cleanup** that only reformatted whitespace/quotes. The actual HIGH/LOW logic was introduced by Andrew Quitmeyer at `732e25c6` (2025-09-22). Git blame attributes reformatted lines to the reformatter.

### 5.x/Attract_Off.py - GPIO polarity lines

Same pattern -- blame shows `d7c8b5b0` (Zane Lazare ruff cleanup), but the logic was set at `732e25c6` (Andrew Quitmeyer).

### 5.x/Flash_On.py - GPIO polarity lines

| Line | Commit | Author | Date | Code |
|------|--------|--------|------|------|
| 46 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch1, GPIO.LOW)` (AttractOff) |
| 51 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch1, GPIO.HIGH)` (AttractOn) |

Uses HIGH=on for single-pin flash control. Logic from `732e25c6`.

### 5.x/Flash_Off.py - GPIO polarity lines

Same structure as Flash_On.py but calls `AttractOff()` at bottom.

### 5.x/FlashOn.py - GPIO polarity lines

| Line | Commit | Author | Date | Code |
|------|--------|--------|------|------|
| 32 | `7ef88c18` | Andrew Quitmeyer | 2025-06-17 | `GPIO.setmode(GPIO.BOARD)` **BUG: uses BOARD mode!** |
| 53 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch2, GPIO.LOW)` (FlashOn) |
| 58 | `d7c8b5b0` | Zane Lazare | 2025-11-05 | `GPIO.output(Relay_Ch2, GPIO.HIGH)` (FlashOff) |

FlashOn.py has **reversed polarity** from Flash_On.py: LOW=on vs HIGH=on. Also uses BOARD mode instead of BCM mode.

### webui/backend/routes/gpio.py - GPIO polarity lines

| Line | Commit | Author | Date | Code |
|------|--------|--------|------|------|
| 66 | `5ca53a03` | Zane Lazare | 2025-10-11 | `GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)` |
| 230 | `5ca53a03` | Zane Lazare | 2025-10-11 | `GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)` |
| 272 | `5ca53a03` | Zane Lazare | 2025-10-11 | `GPIO.output(flash_pin, GPIO.HIGH)` (flash on) |
| 275 | `5ca53a03` | Zane Lazare | 2025-10-11 | `GPIO.output(flash_pin, GPIO.LOW)` (flash off) |

All written at the initial Web UI creation. Never changed.

---

## 7. Polarity Change Commits

### Commits that introduced/changed `GPIO.HIGH` in 5.x and gpio.py

```
5ca53a03 Add Web UI with GPIO controls, diagnostic endpoints, and installer improvements (#22)
732e25c6 updated 5 firmware
6b9cb4d1 made new separate firmware for v4 and v5 mothboxes
```

### Commits that introduced/changed `GPIO.LOW` in 5.x and gpio.py

```
5ca53a03 Add Web UI with GPIO controls, diagnostic endpoints, and installer improvements (#22)
732e25c6 updated 5 firmware
6b9cb4d1 made new separate firmware for v4 and v5 mothboxes
```

### Commits mentioning polarity/relay/active-low/GPIO in commit messages

```
31d2353d fix(camera): add picam2.close() in TakePhoto.py cleanup
bcdbe033 feat(scheduler): add action staggering to prevent GPIO race conditions
d1ec4a5c refactor(sensor): Replace sensor_monitor with sensor_reader library
ce3fd3f2 test: add comprehensive unit tests for GPIO and config routes
d7c8b5b0 refactor: complete ruff linting cleanup - fix all 26 errors
d1cb8259 feat: add Phase 2 coverage tests - error handling & edge cases
541761b8 feat: add comprehensive focus bracket testing and refactor for DI
37f65393 test: add comprehensive mothbox_paths.py tests (Phases 1-3)
8a3c8a7b test: Phase 2A & 2B - comprehensive backend route test coverage improvements
```

No commit message ever mentions "polarity", "active-low", or "active-high". The polarity change was a silent decision.

---

## 8. Key Findings

### Finding 1: The polarity reversal was intentional by Andrew Quitmeyer

At commit `732e25c6` (2025-09-22), Andrew Quitmeyer deliberately changed the 5.x GPIO polarity
from active-low (matching 4.x) to active-high. This was part of "updated 5 firmware" and likely
reflects a **different relay module** on the 5.x hardware that uses active-high triggering.

**Before (at `6b9cb4d1`, identical to 4.x)**:
- `AttractOn()` = `GPIO.LOW` (active-low relay)
- `AttractOff()` = `GPIO.HIGH`

**After (at `732e25c6`, 5.x only)**:
- `AttractOn()` = `GPIO.HIGH` (active-high relay)
- `AttractOff()` = `GPIO.LOW`

### Finding 2: The Web UI matches 5.x (active-high) but not 4.x (active-low)

The Web UI (`gpio.py`) was written by Zane Lazare on 2025-10-11 with active-high logic (`HIGH=on, LOW=off`). This matches the 5.x convention but is **incompatible** with 4.x hardware that uses active-low relays.

Since the Web UI uses `get_gpio_pins()` which defaults to 4.x pin numbers (26/20/21), a 4.x user would get **inverted relay behavior** from the Web UI.

### Finding 3: The 5.x `FlashOn.py` has multiple issues

1. Uses `GPIO.BOARD` mode (physical pin numbers) while all other scripts use `GPIO.BCM`
2. Uses `GPIO.LOW` for "on" (FlashOn function), which is the **opposite** of `Flash_On.py` (uses `GPIO.HIGH` for on)
3. These are two separate files (`FlashOn.py` from pre-split era, `Flash_On.py` created in the 5.x update)

### Finding 4: `Flash_On.py` and `Flash_Off.py` use different pins than `FlashOn.py`

- `Flash_On.py` / `Flash_Off.py`: Uses pin 19 via `Relay_Ch1 = pins["Relay_Ch2"]` (confusing variable naming)
- `FlashOn.py`: Uses pin from `Relay_Ch2` (loaded via `get_gpio_pins()`)
- These may control different hardware or be redundant/conflicting

### Finding 5: The `onlyflash` conditional logic was stripped in 5.x

The 4.x scripts have complex conditional logic for `onlyflash` mode where certain relays
behave differently. The 5.x rewrite at `732e25c6` removed all this conditional logic and
simplified to unconditional HIGH/LOW on all three relays. This means the `OnlyFlash` config
setting in `controls.txt` is **silently ignored** by 5.x scripts.

### Finding 6: No documentation of the polarity convention

There is no commit message, code comment, or documentation that explicitly states:
- "4.x hardware uses active-low relays"
- "5.x hardware uses active-high relays"
- Why the polarity was changed

This undocumented difference is the root cause of the inconsistencies across the codebase.

### Finding 7: Pin number discrepancies

| Source | Relay_Ch1 | Relay_Ch2 | Relay_Ch3 |
|--------|-----------|-----------|-----------|
| 4.x hardcoded (original) | 26 | 20 | 21 |
| 5.x at `732e25c6` (hardcoded) | 5 | 6 | 9 |
| `mothbox_paths.py` defaults | 26 | 20 | 21 (4.x) |
| `mothbox_paths.py` docs suggest | 5 | 19 | 9 |
| `Flash_On.py` at `732e25c6` | 19 (hardcoded) | -- | -- |
| CLAUDE.md states 5.x pins | 5 | 19 | 9 |

The 5.x Relay_Ch2 changed from **6** (at `732e25c6`) to **19** (in `mothbox_paths.py` docs and `Flash_On.py`). This pin number discrepancy may indicate a hardware revision between the initial 5.x code and the final production hardware.

---

## Timeline Summary

```
2024-03-11  f4c230f2  [Andrew Quitmeyer]  Original GPIO scripts (active-low, pins 26/20/21)
2024-03-14  c08a6d5d  [Andrew Quitmeyer]  Added OnlyFlash mode, control_values reader
2025-06-17  7ef88c18  [Andrew Quitmeyer]  Added FlashOn.py (BOARD mode, active-low)
2025-09-20  6b9cb4d1  [Andrew Quitmeyer]  Split into 4.x/ and 5.x/ (identical copies)
2025-09-22  732e25c6  [Andrew Quitmeyer]  >>> POLARITY REVERSAL in 5.x <<<
                                           Changed to active-high, new pins (5/6/9)
                                           Created Flash_On.py/Flash_Off.py (pin 19, active-high)
                                           Removed OnlyFlash conditional logic from 5.x
2025-10-06  d183049c  [Zane Lazare]       Refactored 4.x to use dynamic paths
2025-10-08  a5065cd2  [Zane Lazare]       Added get_gpio_pins() to mothbox_paths.py
                                           Replaced hardcoded pins in 4.x and 5.x scripts
2025-10-11  5ca53a03  [Zane Lazare]       Created Web UI gpio.py (active-high assumption)
2025-11-05  d7c8b5b0  [Zane Lazare]       Ruff linting cleanup (cosmetic only, no logic changes)
2025-12-30  97e252ef  [Zane Lazare]       Migrated gpio.py print() to logging module
```
