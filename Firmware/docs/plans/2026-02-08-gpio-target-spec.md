# GPIO Target Specification

**Date**: 2026-02-08
**Issue**: #399
**Status**: Target state specification (not yet implemented)
**Scope**: All GPIO relay control in the Mothbox firmware (4.x and 5.x)
**Data Sources**: `docs/gpio-architecture.md`, `tools/gpio_audit/logic_pipelines.md`, `docs/plans/2026-02-08-gpio-raw-audit.md`

---

## 1. Overview

This specification defines the target state of the Mothbox GPIO system after resolving Issue #399 and the nine bugs identified by the GPIO System Audit (2026-02-08). The root problem is that the 5.x firmware has no single source of truth for relay polarity: some scripts use active-HIGH (where `GPIO.HIGH` energizes the relay), others use active-LOW (where `GPIO.LOW` energizes the relay), and some use both within the same file. The result is that scripts contradict each other when driving the same pins for the same purpose. This specification prescribes a unified polarity model, a GPIO helper module, pin mode standardization, cleanup discipline, state synchronization, and configurable switch pins. Every section is self-contained and references the specific bugs it addresses.

---

## 2. Polarity Model

**Addresses**: BUG-1 (TakePhoto vs Attract_On Ch3 polarity contradiction), BUG-2 (DebugMode uses 4.x polarity on 5.x)

### 2.1 Configuration

A new boolean key MUST be added to `controls.txt`:

```
relay_active_low=true
```

**Semantics**:
- `relay_active_low=true` (default): Standard relay modules. `GPIO.LOW` energizes the relay (load ON). `GPIO.HIGH` de-energizes (load OFF).
- `relay_active_low=false`: Inverted relay modules. `GPIO.HIGH` energizes the relay (load ON). `GPIO.LOW` de-energizes (load OFF).

The default MUST be `true` because:
1. The 4.x firmware used active-low consistently and correctly for standard relay modules.
2. Most commodity relay boards (SRD-05VDC-SL-C, HW-307, etc.) are active-low.
3. The 5.x polarity reversal at commit `732e25c6` was incomplete and undocumented, creating the contradictions that this specification resolves.

### 2.2 Single Source of Truth

All code that drives relay pins MUST read `relay_active_low` from `controls.txt` (via the helper functions defined in Section 3) to determine the correct `GPIO.HIGH` / `GPIO.LOW` value for "on" and "off". No script SHOULD contain a hardcoded `GPIO.HIGH` or `GPIO.LOW` literal for relay operations. The mapping is:

| Intent | `relay_active_low=true` | `relay_active_low=false` |
|--------|------------------------|--------------------------|
| Relay ON (energize) | `GPIO.LOW` (0) | `GPIO.HIGH` (1) |
| Relay OFF (de-energize) | `GPIO.HIGH` (1) | `GPIO.LOW` (0) |

### 2.3 Per-Channel Polarity

This specification does NOT introduce per-channel polarity (e.g., `relay_ch1_active_low`). The audit found no evidence that different relay channels on the same board use different polarity. If a future hardware revision requires per-channel polarity, the helper module (Section 3) can be extended without changing the call sites.

---

## 3. GPIO Helper Module

**Addresses**: BUG-1, BUG-2, BUG-4 (naming confusion in Flash scripts), BUG-6 (no cleanup discipline)

### 3.1 Module Location

A new file MUST be created: `gpio_helpers.py`, placed alongside `mothbox_paths.py` at the firmware root. This module MUST import from `mothbox_paths` for pin and configuration access, and MUST import `RPi.GPIO` with the standard `GPIO_AVAILABLE` guard pattern used by `gpio.py`.

### 3.2 Functions

#### `get_relay_level(on: bool) -> int`

Returns the GPIO level (0 or 1) for the requested relay state, based on the `relay_active_low` configuration.

```python
def get_relay_level(on: bool) -> int:
    """Return GPIO level for the requested relay state.

    Args:
        on: True to energize the relay (load ON), False to de-energize (load OFF).

    Returns:
        GPIO.LOW or GPIO.HIGH based on relay_active_low config.
    """
    controls = get_control_values()
    active_low = controls.get("relay_active_low", "true").lower() in ("true", "1", "yes")

    if active_low:
        return GPIO.LOW if on else GPIO.HIGH
    else:
        return GPIO.HIGH if on else GPIO.LOW
```

#### `setup_relay(pin: int) -> None`

Configures a relay pin as output with a safe initial state (relay OFF).

```python
def setup_relay(pin: int) -> None:
    """Configure a relay pin as output in the OFF (de-energized) state.

    Args:
        pin: BCM pin number.
    """
    off_level = get_relay_level(on=False)
    GPIO.setup(pin, GPIO.OUT, initial=off_level)
```

#### `relay_on(pin: int) -> None`

Energizes a relay.

```python
def relay_on(pin: int) -> None:
    """Energize a relay (turn load ON).

    Args:
        pin: BCM pin number. Must have been configured with setup_relay() first.
    """
    GPIO.output(pin, get_relay_level(on=True))
```

#### `relay_off(pin: int) -> None`

De-energizes a relay.

```python
def relay_off(pin: int) -> None:
    """De-energize a relay (turn load OFF).

    Args:
        pin: BCM pin number. Must have been configured with setup_relay() first.
    """
    GPIO.output(pin, get_relay_level(on=False))
```

#### `write_gpio_state(pin_states: dict) -> None`

Persists the current relay state to `gpio_state.json` in `DATA_DIR`. This function is called internally by `relay_on()` and `relay_off()` to keep the Web UI state file synchronized. See Section 8.

```python
def write_gpio_state(pin_states: dict) -> None:
    """Write relay state to gpio_state.json for Web UI synchronization.

    Args:
        pin_states: Dict mapping relay names to boolean on/off state.
                    Example: {"Relay_Ch1": True, "Relay_Ch2": False}
    """
    state_file = DATA_DIR / "gpio_state.json"
    # Read existing state, merge, write atomically
    ...
```

### 3.3 Usage Contract

- All relay scripts MUST import from `gpio_helpers` instead of calling `GPIO.output()` directly for relay pins.
- The `gpio_helpers` module MUST call `GPIO.setmode(GPIO.BCM)` internally if not already set.
- The `gpio_helpers` module MUST call `GPIO.setwarnings(False)` to suppress duplicate setup warnings.
- Non-relay GPIO operations (switch reading, e-paper, multiplexer) are NOT managed by this module and continue to use `RPi.GPIO` directly.

---

## 4. Pin Mode Standardization

**Addresses**: BUG-3 (FlashOn.py BOARD/BCM mode mismatch)

### 4.1 Rule

All scripts MUST use `GPIO.setmode(GPIO.BCM)` unless they exclusively operate multiplexer pins obtained from `get_mux_pins()`.

### 4.2 FlashOn.py Fix

`5.x/FlashOn.py` and `4.x/FlashOn.py` currently use `GPIO.setmode(GPIO.BOARD)` but receive BCM pin numbers from `get_gpio_pins()`. This causes BCM pin 19 to be interpreted as physical pin 19, which is GPIO10 (SPI MOSI) -- the wrong pin entirely.

The fix: `FlashOn.py` MUST be changed to `GPIO.setmode(GPIO.BCM)`, or preferably deprecated in favor of `Flash_On.py` (see Section 6.6).

### 4.3 ReadMuxAMuxB.py Exception

`ReadMuxAMuxB.py` is the sole legitimate user of `GPIO.BOARD` mode. `get_mux_pins()` returns physical (BOARD) pin numbers because the CD74HC4067 multiplexer documentation and PCB silkscreen reference physical pin positions. Changing `get_mux_pins()` to return BCM numbers would create a mismatch with hardware documentation and offer no practical benefit.

`ReadMuxAMuxB.py` MUST remain in BOARD mode. This is safe because:
1. It runs as a standalone CLI tool, never concurrently with the Flask process.
2. It is not in `cron_security.py`'s `ALLOWED_SCRIPTS`.
3. It properly calls `GPIO.cleanup()` in a `finally` block.

---

## 5. Script Cleanup Contract

**Addresses**: BUG-6 (no GPIO.cleanup in relay scripts), BUG-7 (orphaned GPIO 6)

### 5.1 Relay Scripts: No Cleanup

Relay control scripts (`Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`, `TakePhoto.py`) SHOULD NOT call `GPIO.cleanup()`. The lack of cleanup is intentional: relay state MUST persist after the script exits so that lights remain on or off as commanded. On Pi 5 with the `rpi-lgpio` shim, pin state persists after process exit -- this is the desired behavior for relay control.

This MUST be documented with a comment at the end of each relay script:

```python
# GPIO.cleanup() intentionally omitted.
# Relay pins must persist in their current state after this script exits.
# Cleanup is performed only by Scheduler.py before system shutdown.
```

### 5.2 Scheduler.py: Cleanup Before Shutdown

`Scheduler.py` MUST call `GPIO.cleanup()` before system shutdown (as it already does at lines 500, 578, and 935). This is the single point where all relay pins are returned to input state.

### 5.3 Diagnostic Tools: Cleanup Required

`ReadMuxAMuxB.py`, `Relay_Module.py`, and `CheckGPIOPin.py` MUST call `GPIO.cleanup()` in a `finally` block, as they are diagnostic tools that should leave the system in a clean state.

### 5.4 Orphaned GPIO 6 Cleanup

**Addresses**: BUG-7

GPIO 6 is currently configured as output driving HIGH on the production Pi. It was the original 5.x Relay_Ch2 pin (commit `732e25c6`) before the hardware revision changed Ch2 to pin 19. No current code references pin 6.

The fix: `Scheduler.py` MUST reset GPIO 6 to input state during its startup sequence. This is a one-time cleanup that runs on every boot:

```python
# Clean up orphaned GPIO 6 (was Relay_Ch2 in early 5.x hardware revision).
# Safe to remove this block after all deployed units have rebooted at least once.
try:
    GPIO.setup(6, GPIO.IN)
    GPIO.cleanup(6)
except Exception:
    pass  # Pin may not be accessible; ignore
```

This cleanup SHOULD be placed in the `Scheduler.py` initialization, before the physical switch check.

---

## 6. Script Responsibilities

Each script MUST control only the pins it needs. The following defines the target responsibility for each script.

### 6.1 Attract_On.py / Attract_Off.py

**Pins**: Relay_Ch1, Relay_Ch2, Relay_Ch3 (all three relay channels)
**Purpose**: Turn all attraction hardware on or off
**Implementation**: MUST use `relay_on()` / `relay_off()` from `gpio_helpers`

```python
from gpio_helpers import setup_relay, relay_on, relay_off
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
for channel in ("Relay_Ch1", "Relay_Ch2", "Relay_Ch3"):
    setup_relay(pins[channel])

# Attract_On.py calls:
relay_on(pins["Relay_Ch1"])
relay_on(pins["Relay_Ch2"])
relay_on(pins["Relay_Ch3"])

# Attract_Off.py calls:
relay_off(pins["Relay_Ch1"])
relay_off(pins["Relay_Ch2"])
relay_off(pins["Relay_Ch3"])
```

### 6.2 Flash_On.py / Flash_Off.py

**Pin**: Relay_Ch2 only (flash relay)
**Purpose**: Turn the camera flash on or off
**Implementation**: MUST use `relay_on()` / `relay_off()` from `gpio_helpers`

```python
from gpio_helpers import setup_relay, relay_on, relay_off
from mothbox_paths import get_gpio_pins

pins = get_gpio_pins()
flash_pin = pins["Relay_Ch2"]
setup_relay(flash_pin)

# Flash_On.py calls:
relay_on(flash_pin)

# Flash_Off.py calls:
relay_off(flash_pin)
```

Variable names MUST match the actual channel: `flash_pin = pins["Relay_Ch2"]`, not `Relay_Ch1 = pins["Relay_Ch2"]`.

### 6.3 TakePhoto.py

**Pins**: Relay_Ch2 (flash), Relay_Ch3 (attract UV)
**Purpose**: Flash control during photo capture; maintain attract state
**Implementation**: MUST use `relay_on()` / `relay_off()` from `gpio_helpers`

The `flashOn()` and `flashOff()` functions MUST be updated:

```python
def flashOn():
    relay_on(flash_pin)       # Flash ON
    relay_on(attract_pin)     # Ensure attract stays on

def flashOff():
    relay_off(flash_pin)      # Flash OFF
    relay_on(attract_pin)     # Ensure attract stays on
```

### 6.4 DebugMode.py

**Pins**: Relay_Ch1, Relay_Ch2, Relay_Ch3 (all three -- turning OFF)
**Purpose**: Turn off all relays for safe debugging
**Implementation**: MUST use `relay_off()` from `gpio_helpers`

```python
def AttractOff():
    relay_off(pins["Relay_Ch1"])
    relay_off(pins["Relay_Ch2"])
    relay_off(pins["Relay_Ch3"])
```

### 6.5 gpio.py (Web UI)

**Pins**: Any relay pin (via API), Relay_Ch2 (flash trigger)
**Purpose**: REST API for relay control and flash
**Implementation**: MUST use `gpio_helpers` functions instead of raw `GPIO.output()` calls

The `control_gpio()` handler MUST call:
```python
if state:
    relay_on(pin)
else:
    relay_off(pin)
```

The `trigger_flash()` handler MUST call:
```python
relay_on(flash_pin)
time.sleep(duration_sec)
relay_off(flash_pin)
```

### 6.6 FlashOn.py: Deprecation

`FlashOn.py` (both 4.x and 5.x) SHOULD be deprecated. It has two bugs (BUG-3: BOARD mode, and active-low polarity on 5.x) and duplicates the functionality of `Flash_On.py`. The file SHOULD be:
1. Renamed to `FlashOn.py.deprecated` or removed entirely.
2. Removed from any documentation or script lists.
3. It is already absent from `cron_security.py`'s `ALLOWED_SCRIPTS`, so no scheduler change is needed.

If removal is not feasible, at minimum it MUST be fixed to use `GPIO.BCM` mode and `gpio_helpers`.

### 6.7 capture_focus_bracket.py

**Pins**: Relay_Ch1, Relay_Ch2, Relay_Ch3 (via GPIOHandler class)
**Purpose**: Focus bracket capture with flash control
**Implementation**: The `GPIOHandler` class MUST be updated to use `gpio_helpers` internally. Its `flash_on()` and `flash_off()` methods MUST call `relay_on()` / `relay_off()` instead of raw `GPIO.output()`.

### 6.8 5.x/scripts/ Subdirectory

All TakePhoto variants and Flash scripts in `5.x/scripts/` currently use 4.x active-low polarity. After the `gpio_helpers` module is available, these scripts SHOULD be migrated to use `relay_on()` / `relay_off()`. This eliminates the polarity discrepancy with the top-level 5.x scripts.

Scripts that are rarely used MAY be left unchanged with a deprecation notice, provided they are not invoked by the scheduler or web UI.

---

## 7. Naming Cleanup

**Addresses**: BUG-4 (Flash_On.py / Flash_Off.py naming confusion)

### 7.1 Variable Names

All relay scripts MUST use variable names that match the actual relay channel:

| Variable | Value | Used In |
|----------|-------|---------|
| `attract_pin` | `pins["Relay_Ch1"]` | Attract scripts, DebugMode, TakePhoto |
| `flash_pin` | `pins["Relay_Ch2"]` | Flash scripts, TakePhoto |
| `buck_pin` or `aux_pin` | `pins["Relay_Ch3"]` | Attract scripts, TakePhoto |

The pattern `Relay_Ch1 = pins["Relay_Ch2"]` (current Flash_On.py) MUST NOT appear in any script.

### 7.2 Function Names

Functions MUST describe their actual purpose:
- Flash scripts: `flash_on()` / `flash_off()`, not `AttractOn()` / `AttractOff()`
- Attract scripts: `attract_on()` / `attract_off()`
- DebugMode: `all_relays_off()`

### 7.3 Print Banners

Print statements and log messages MUST match the script's actual function:
- `Flash_On.py` MUST print a message about flash, not "attract off!"
- `Attract_Off.py` MUST NOT print "Attract On!" (currently has this from copy-paste)

### 7.4 Dead Code Removal

The following dead code SHOULD be removed:
- Unused `get_control_values()` duplicates in scripts that already import from `mothbox_paths`
- Commented-out function bodies
- `onlyflash` conditional logic in `5.x/DebugMode.py` (this setting is not used by 5.x top-level scripts)

---

## 8. State Synchronization

**Addresses**: BUG-5 (Web UI state desynchronization)

### 8.1 Problem

The Web UI tracks relay state in `gpio_state.json`. This file is only written by `gpio.py:_save_state()`. When cron-triggered scripts (`Attract_On.py`, `TakePhoto.py`, etc.) change relay state, `gpio_state.json` is not updated and the Web UI shows stale toggle positions.

### 8.2 Solution: Automatic State Persistence via `gpio_helpers`

**Recommended**: Option A -- the `gpio_helpers` module automatically writes to `gpio_state.json` after every `relay_on()` / `relay_off()` call.

The `relay_on()` and `relay_off()` functions MUST:
1. Drive the GPIO pin to the correct level.
2. Update the in-memory state.
3. Write the updated state to `gpio_state.json` atomically (write to temp file, then rename).

This means every script that uses `gpio_helpers` -- whether invoked by cron, CLI, or the Web UI -- automatically keeps the state file current.

### 8.3 State File Format

The `gpio_state.json` format MUST remain compatible with the existing Web UI:

```json
{
  "Relay_Ch1": true,
  "Relay_Ch2": false,
  "Relay_Ch3": true
}
```

Where `true` means relay is energized (load ON) and `false` means de-energized (load OFF).

### 8.4 gpio.py Integration

The `gpio.py:_save_state()` function SHOULD be replaced by a call to `gpio_helpers.write_gpio_state()` to avoid duplicate state-writing logic.

The `gpio.py:_get_state()` function MAY remain unchanged -- it reads `gpio_state.json` as before, but now that file is also updated by external scripts.

### 8.5 Alternatives Considered

**Option B** (read live pin state via `GPIO.input()`): Rejected. The existing code comment explains that reading OUTPUT pins can be unreliable and may reset their state under `rpi-lgpio`. This option would also require GPIO access from the Flask process, which conflicts with pins being configured as output by other processes.

**Option C** ("Refresh from hardware" button): Rejected as a standalone solution. It provides a poor user experience by requiring manual action. However, it MAY be added as a supplementary feature alongside Option A.

---

## 9. Configurable Switch Pins

**Addresses**: BUG-8 (hardcoded switch pins in 8 files)

### 9.1 Configuration

Two new keys MUST be added to `controls.txt`:

```
off_pin=16
debug_pin=12
```

These default to the current hardcoded values (BCM 16 and BCM 12).

### 9.2 mothbox_paths.py Function

A new function MUST be added to `mothbox_paths.py`:

```python
def get_switch_pins() -> dict:
    """Return physical switch pin assignments.

    Returns:
        dict with keys 'off_pin' and 'debug_pin', values are BCM pin numbers.
    """
    controls = get_control_values()
    off_pin = int(controls.get("off_pin", "16"))
    debug_pin = int(controls.get("debug_pin", "12"))

    # Validate BCM range
    for name, pin in [("off_pin", off_pin), ("debug_pin", debug_pin)]:
        if not 0 <= pin <= 27:
            raise ValueError(f"{name}={pin} is outside BCM range 0-27")

    return {"off_pin": off_pin, "debug_pin": debug_pin}
```

On any exception, the function MUST return the defaults `{"off_pin": 16, "debug_pin": 12}`, consistent with the error-handling pattern in `get_gpio_pins()`.

### 9.3 Migration

All 8 files that hardcode `off_pin=16` and `debug_pin=12` MUST be updated to call `get_switch_pins()`:

| File | Current Code | Target Code |
|------|-------------|-------------|
| `5.x/Scheduler.py` | `off_pin = 16` | `switch_pins = get_switch_pins(); off_pin = switch_pins["off_pin"]` |
| `5.x/TakePhoto.py` | `off_pin = 16` | Same pattern |
| `5.x/UpdateDisplay.py` | `off_pin = 16` | Same pattern |
| `5.x/scripts/CheckGPIOPin.py` | `off_pin = 16` | Same pattern |
| `4.x/Scheduler.py` | `off_pin = 16` | Same pattern |
| `4.x/TakePhoto.py` | `off_pin = 16` | Same pattern |
| `4.x/UpdateDisplay.py` | `off_pin = 16` | Same pattern |
| `4.x/scripts/CheckGPIOPin.py` | `off_pin = 16` | Same pattern |

---

## 10. Startup Safety

**Addresses**: BUG-9 (startup permission check side effect)

### 10.1 Problem

At module load, `gpio.py:_validate_gpio_permissions()` calls `GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)` on Relay_Ch1. This briefly drives the pin LOW. On active-low hardware, this momentarily energizes the relay.

### 10.2 Solution: Input Mode Permission Test

The permission check MUST use `GPIO.IN` (input) mode instead of `GPIO.OUT` (output). Reading a pin verifies GPIO access permissions without driving any electrical signal:

```python
def _validate_gpio_permissions():
    """Verify GPIO access without driving any relay pin."""
    try:
        test_pin = get_gpio_pins().get("Relay_Ch1", 26)
        GPIO.setup(test_pin, GPIO.IN)
        GPIO.input(test_pin)  # Read to verify access
        GPIO.cleanup(test_pin)
        return True
    except Exception as e:
        logger.error("GPIO permission check failed: %s", e)
        return False
```

This approach:
- Verifies that the process can access `/dev/gpiochip*` (the actual permission being tested).
- Does not configure any pin as output.
- Does not drive any voltage level.
- Cleans up the input configuration immediately.

---

## 11. Test Strategy

### 11.1 Unit Tests (Mock Hardware)

Unit tests MUST mock `RPi.GPIO` and verify that the `gpio_helpers` module translates polarity correctly.

**`get_relay_level()` tests**:

```python
def test_relay_level_active_low_on():
    """relay_active_low=true: ON should return GPIO.LOW."""
    with patch_controls({"relay_active_low": "true"}):
        assert get_relay_level(on=True) == GPIO.LOW

def test_relay_level_active_low_off():
    """relay_active_low=true: OFF should return GPIO.HIGH."""
    with patch_controls({"relay_active_low": "true"}):
        assert get_relay_level(on=False) == GPIO.HIGH

def test_relay_level_active_high_on():
    """relay_active_low=false: ON should return GPIO.HIGH."""
    with patch_controls({"relay_active_low": "false"}):
        assert get_relay_level(on=True) == GPIO.HIGH

def test_relay_level_active_high_off():
    """relay_active_low=false: OFF should return GPIO.LOW."""
    with patch_controls({"relay_active_low": "false"}):
        assert get_relay_level(on=False) == GPIO.LOW
```

**Default behavior test**:

```python
def test_relay_level_missing_config_defaults_to_active_low():
    """Missing relay_active_low should default to true (active-low)."""
    with patch_controls({}):
        assert get_relay_level(on=True) == GPIO.LOW
```

**`setup_relay()` tests**:

```python
def test_setup_relay_initializes_to_off():
    """setup_relay() should configure pin as OUTPUT with OFF level."""
    with patch_controls({"relay_active_low": "true"}):
        setup_relay(5)
        GPIO.setup.assert_called_with(5, GPIO.OUT, initial=GPIO.HIGH)
```

**`relay_on()` / `relay_off()` tests**:

```python
def test_relay_on_drives_correct_level():
    """relay_on() should call GPIO.output with the ON level."""
    with patch_controls({"relay_active_low": "true"}):
        relay_on(5)
        GPIO.output.assert_called_with(5, GPIO.LOW)

def test_relay_off_drives_correct_level():
    """relay_off() should call GPIO.output with the OFF level."""
    with patch_controls({"relay_active_low": "true"}):
        relay_off(5)
        GPIO.output.assert_called_with(5, GPIO.HIGH)
```

### 11.2 State Synchronization Tests

```python
def test_relay_on_writes_state_file(tmp_path):
    """relay_on() should update gpio_state.json."""
    with patch("gpio_helpers.DATA_DIR", tmp_path):
        relay_on(pins["Relay_Ch1"])
        state = json.loads((tmp_path / "gpio_state.json").read_text())
        assert state["Relay_Ch1"] is True

def test_relay_off_writes_state_file(tmp_path):
    """relay_off() should update gpio_state.json."""
    with patch("gpio_helpers.DATA_DIR", tmp_path):
        relay_off(pins["Relay_Ch1"])
        state = json.loads((tmp_path / "gpio_state.json").read_text())
        assert state["Relay_Ch1"] is False
```

### 11.3 Pipeline Tests

Each signal path from `tools/gpio_audit/logic_pipelines.md` SHOULD have a corresponding unit test that verifies the end-to-end flow. Key pipelines to test:

| Pipeline | Test Description |
|----------|-----------------|
| 1 (Web UI relay toggle) | `POST /api/gpio/control` with `state=True` calls `relay_on()` |
| 3 (Attract_On via cron) | `Attract_On.py` calls `relay_on()` on all three channels |
| 8 (TakePhoto flash) | `flashOn()` calls `relay_on(flash_pin)` and `relay_on(attract_pin)` |
| 12 (DebugMode) | `AttractOff()` calls `relay_off()` on all three channels |

### 11.4 Integration Tests (On Pi Hardware)

Integration tests MUST verify actual pin state after script execution, using `GPIO.input()` or `pinctrl get` to read pin values. These tests MUST be marked with `@pytest.mark.hardware`.

```python
@pytest.mark.hardware
def test_attract_on_drives_pins():
    """Attract_On.py should energize all relay pins."""
    subprocess.run(["python3", "5.x/Attract_On.py"], check=True)
    for pin in (5, 19, 9):
        GPIO.setup(pin, GPIO.IN)
        expected = GPIO.LOW if active_low else GPIO.HIGH
        assert GPIO.input(pin) == expected
```

### 11.5 Switch Pin Tests

```python
def test_get_switch_pins_defaults():
    """get_switch_pins() should return 16/12 when not configured."""
    pins = get_switch_pins()
    assert pins == {"off_pin": 16, "debug_pin": 12}

def test_get_switch_pins_custom():
    """get_switch_pins() should read from controls.txt."""
    with patch_controls({"off_pin": "20", "debug_pin": "21"}):
        pins = get_switch_pins()
        assert pins == {"off_pin": 20, "debug_pin": 21}

def test_get_switch_pins_invalid_falls_back():
    """get_switch_pins() should return defaults on invalid values."""
    with patch_controls({"off_pin": "99"}):
        pins = get_switch_pins()
        assert pins == {"off_pin": 16, "debug_pin": 12}
```

---

## 12. Migration Plan

### 12.1 Configuration

1. Add `relay_active_low=true` to the default `controls.txt` template.
2. Add `off_pin=16` and `debug_pin=12` to the default `controls.txt` template.
3. Deployed systems that already have a `controls.txt` without these keys will use the hardcoded defaults in the helper functions. No manual configuration edit is required.

### 12.2 New Code

1. Create `gpio_helpers.py` with the functions specified in Section 3.
2. Add `get_switch_pins()` to `mothbox_paths.py` as specified in Section 9.

### 12.3 Script Updates

Each relay script MUST be updated to import and use `gpio_helpers`. The migration can proceed one script at a time. Recommended order (highest impact first):

1. `5.x/TakePhoto.py` -- fixes BUG-1 (the core Issue #399 polarity contradiction)
2. `5.x/DebugMode.py` -- fixes BUG-2 (turns everything ON instead of OFF)
3. `5.x/Attract_On.py` / `5.x/Attract_Off.py` -- establishes consistent pattern
4. `5.x/Flash_On.py` / `5.x/Flash_Off.py` -- fixes BUG-4 (naming)
5. `webui/backend/routes/gpio.py` -- fixes BUG-5 (state sync via helpers) and BUG-9 (startup side effect)
6. `5.x/Scheduler.py` -- adds GPIO 6 cleanup (BUG-7) and switch pin migration (BUG-8)
7. `5.x/FlashOn.py` -- deprecate or fix BUG-3 (BOARD mode)
8. `webui/backend/scripts/capture_focus_bracket.py` -- align GPIOHandler with helpers
9. Switch pin migration across all 8 files (BUG-8)
10. `5.x/scripts/` subdirectory (lower priority, utility scripts)

### 12.4 4.x Firmware

The 4.x firmware SHOULD receive the same `gpio_helpers` migration for consistency, but at lower priority. 4.x polarity is already consistent (all active-low), so the bugs are less severe. The 4.x migration:
- Gains configurable switch pins (BUG-8)
- Gains state synchronization (BUG-5)
- Does NOT need polarity fixes (4.x is already uniform)

### 12.5 Deployment

1. Run `update_mothbox.sh` on deployed systems. The update script copies new code and preserves existing `controls.txt`.
2. The new `relay_active_low` default (`true`) applies automatically when the key is absent from `controls.txt`.
3. No data migration is needed. Only code and configuration defaults change.
4. Backward compatible: existing `controls.txt` files without the new keys use the correct defaults.

### 12.6 Rollback

If a deployed system experiences issues:
1. The `relay_active_low` key can be toggled in `controls.txt` to switch polarity without a code change.
2. Individual scripts can be reverted to their pre-migration versions by restoring from git.
3. No database or data file changes need to be rolled back.

---

## Summary: Bug Resolution Map

| Bug | Description | Resolved By |
|-----|-------------|-------------|
| BUG-1 | TakePhoto Ch3 polarity contradicts Attract_On | Section 2 (polarity model), Section 3 (helpers), Section 6.3 (TakePhoto responsibilities) |
| BUG-2 | DebugMode uses 4.x polarity on 5.x | Section 2 (polarity model), Section 3 (helpers), Section 6.4 (DebugMode responsibilities) |
| BUG-3 | FlashOn.py BOARD/BCM mode mismatch | Section 4.2 (pin mode fix), Section 6.6 (deprecation) |
| BUG-4 | Flash_On/Off naming confusion | Section 7 (naming cleanup) |
| BUG-5 | Web UI state desynchronization | Section 8 (state synchronization via helpers) |
| BUG-6 | No GPIO.cleanup in relay scripts | Section 5 (cleanup contract -- intentional non-cleanup documented) |
| BUG-7 | GPIO 6 orphaned output | Section 5.4 (Scheduler.py startup cleanup) |
| BUG-8 | Hardcoded switch pins in 8 files | Section 9 (configurable switch pins) |
| BUG-9 | Startup permission check side effect | Section 10 (input mode permission test) |
