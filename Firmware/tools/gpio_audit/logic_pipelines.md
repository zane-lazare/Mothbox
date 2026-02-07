# GPIO Audit: Logic Pipelines

Every complete signal path from trigger to electrical outcome, traced from source code (Phase 1-2 data) and runtime observations.

**Conventions:**
- `HIGH=1`, `LOW=0` (confirmed from Pi 5: `RPi.GPIO.HIGH=1`, `RPi.GPIO.LOW=0`)
- "Active-low relay" means: LOW on pin → relay energised → load ON. HIGH → relay de-energised → load OFF.
- "Active-high" means the opposite: HIGH → relay energised → load ON.
- **Hardware reality is unknown** — the audit cannot determine whether the physical relay board is active-low or active-high without electrical testing. Bugs are marked based on inconsistency between versions, not hardware truth.

---

## Pipeline 1: Web UI Relay Toggle (5.x)

**Intent:** User toggles a relay on/off via the web UI.

**Trigger:** Frontend `POST /api/gpio/control` with `{"relay": "Relay_Ch1", "state": true}`

**Path:**
```
Frontend toggle → POST /api/gpio/control → gpio.py:198 control_gpio()
  → get_gpio_pins() → pins = {"Relay_Ch1": 5, "Relay_Ch2": 19, "Relay_Ch3": 9}
  → GPIO.setup(pin, GPIO.OUT)       [gpio.py:228]
  → GPIO.output(pin, GPIO.HIGH)     [gpio.py:230]  (state=True → HIGH)
  → GPIO.output(pin, GPIO.LOW)      [gpio.py:230]  (state=False → LOW)
  → _save_state() persists to gpio_state.json
```

**Pins:** Relay_Ch1=5, Relay_Ch2=19, Relay_Ch3=9 (from controls.txt)

**Logic:**
| state | GPIO.output | Electrical |
|-------|-------------|------------|
| True (on) | `GPIO.HIGH` (1) | Pin driven HIGH |
| False (off) | `GPIO.LOW` (0) | Pin driven LOW |

**Convention:** Active-high — `state=True → HIGH → ON`.

**Cleanup:** GPIO.setup() called each request. No GPIO.cleanup(). Pin state persists between requests.

**Runtime confirmation:** GPIO 5 observed as output, driving HIGH, consumer "lg" (see runtime_state.md).

---

## Pipeline 2: Web UI Flash Trigger (5.x)

**Intent:** User fires a momentary camera flash pulse from the web UI.

**Trigger:** Frontend `POST /api/gpio/flash`

**Path:**
```
Frontend flash button → POST /api/gpio/flash → gpio.py:243 trigger_flash()
  → get_gpio_pins() → flash_pin = pins["Relay_Ch2"] = 19
  → controls.get("flash_duration_ms", 100) → typically 100ms
  → GPIO.setup(flash_pin, GPIO.OUT)        [gpio.py:270]
  → GPIO.output(flash_pin, GPIO.HIGH)      [gpio.py:272]  ON
  → time.sleep(0.1)                        [gpio.py:273]  100ms pulse
  → GPIO.output(flash_pin, GPIO.LOW)       [gpio.py:275]  OFF
```

**Pin:** Relay_Ch2=19 (BCM)

**Logic:** HIGH=flash on, LOW=flash off. Active-high convention.

**Convention match:** Matches Pipeline 1 (Web UI relay toggle). Consistent.

---

## Pipeline 3: Web UI Scheduler → Cron → Attract_On.py (5.x)

**Intent:** Scheduled routine turns on attraction lights.

**Trigger:** Web UI schedule activation → cron_bridge.py → system crontab entry

**Path:**
```
Web UI → POST /api/scheduler/activate
  → scheduler_service.py:activate_schedule()
  → cron_bridge.py: generate_cron_entries()
    → For action type="gpio", name="attract_on":
      → cron_security.py: get_script_key_for_action("gpio", "attract_on") → "attract_on"
      → cron_security.py: ALLOWED_SCRIPTS["attract_on"] = "Attract_On.py"
      → get_validated_command("attract_on")
        → "systemd-cat -t mothbox /usr/bin/python3 /opt/mothbox/Attract_On.py"
  → CronTab writes entry to system crontab

[At scheduled time]:
  cron → python3 Attract_On.py
    → get_gpio_pins() → {Ch1=5, Ch2=19, Ch3=9}
    → GPIO.setmode(GPIO.BCM)
    → GPIO.setup(Ch1, OUT), GPIO.setup(Ch2, OUT), GPIO.setup(Ch3, OUT)
    → AttractOn():
      → GPIO.output(Relay_Ch3, GPIO.HIGH)   [Attract_On.py:52]
      → GPIO.output(Relay_Ch2, GPIO.HIGH)   [Attract_On.py:53]
      → GPIO.output(Relay_Ch1, GPIO.HIGH)   [Attract_On.py:54]
  → Process exits. No GPIO.cleanup(). Pins remain HIGH.
```

**Pins:** All three relays: Ch1=5, Ch2=19, Ch3=9

**Logic:** All channels → HIGH. Active-high convention.

**Convention match:** Matches Web UI (Pipeline 1). Consistent with 5.x active-high model.

**BUG vs 4.x:** 4.x Attract_On.py sends LOW to turn on. See Pipeline 9.

---

## Pipeline 4: Scheduler → Cron → Attract_Off.py (5.x)

**Intent:** Scheduled routine turns off attraction lights.

**Trigger:** Cron job runs Attract_Off.py (same cron_bridge path as Pipeline 3 but action="attract_off")

**Path:**
```
cron → python3 Attract_Off.py
  → get_gpio_pins() → {Ch1=5, Ch2=19, Ch3=9}
  → GPIO.setmode(GPIO.BCM)
  → GPIO.setup(Ch1, OUT), GPIO.setup(Ch2, OUT), GPIO.setup(Ch3, OUT)
  → AttractOff():
    → GPIO.output(Relay_Ch3, GPIO.LOW)   [Attract_Off.py:60]
    → GPIO.output(Relay_Ch2, GPIO.LOW)   [Attract_Off.py:61]
    → GPIO.output(Relay_Ch1, GPIO.LOW)   [Attract_Off.py:62]
  → Process exits. No GPIO.cleanup().
```

**NOTE:** Despite the file being named "Attract_Off.py", the print banner says `"Attract On!"` — the file was cloned from Attract_On.py. The **function called at bottom** is `AttractOff()` [line 68], which sends LOW. Functionally correct.

**Logic:** All channels → LOW. Active-high convention OFF.

**Convention match:** Consistent with Pipeline 3.

---

## Pipeline 5: Scheduler → Cron → Flash_On.py (5.x)

**Intent:** Turn on camera flash via scheduled action.

**Trigger:** Cron job runs `Flash_On.py` (action "flash_on" → cron_security maps to "Flash_On.py")

**Path:**
```
cron → python3 Flash_On.py
  → get_gpio_pins() → pins["Relay_Ch2"] = 19
  → BUT: Relay_Ch1 = pins["Relay_Ch2"]   [Flash_On.py:25] ← PIN ALIASED
  → GPIO.setmode(GPIO.BCM)
  → GPIO.setup(Relay_Ch1, GPIO.OUT)       [uses pin 19, aliased]
  → AttractOn():                          [Flash_On.py:57] ← calls the wrong-named fn
    → GPIO.output(Relay_Ch1, GPIO.HIGH)   [Flash_On.py:51]
```

**Pin:** Relay_Ch2=19 (BCM). The variable `Relay_Ch1` is misleadingly aliased to `pins["Relay_Ch2"]`.

**Logic:** Pin 19 → HIGH. Active-high convention.

**BUG (naming):** Variable `Relay_Ch1` holds pin from `Relay_Ch2`. Functions named `AttractOn`/`AttractOff` but this is a flash script. Copy-paste artifact.

**BUG (banner):** Print says `"attract off!"` but turns flash on.

**Functional result:** Despite naming bugs, pin 19 goes HIGH. Electrically matches Web UI flash (Pipeline 2 ON direction). **Functionally correct.**

---

## Pipeline 6: Scheduler → Cron → Flash_Off.py (5.x)

**Intent:** Turn off camera flash via scheduled action.

**Trigger:** Cron job runs `Flash_Off.py`

**Path:**
```
cron → python3 Flash_Off.py
  → get_gpio_pins() → pins["Relay_Ch2"] = 19
  → Relay_Ch1 = pins["Relay_Ch2"]   [Flash_Off.py:25] ← same alias
  → GPIO.setmode(GPIO.BCM)
  → GPIO.setup(Relay_Ch1, GPIO.OUT)
  → AttractOff():                    [Flash_Off.py:58] ← calls fn at bottom
    → GPIO.output(Relay_Ch1, GPIO.LOW)   [Flash_Off.py:46]
```

**Pin:** 19 (BCM, aliased).

**Logic:** Pin 19 → LOW. Active-high convention OFF.

**Same naming bugs as Pipeline 5.** Functionally correct — pin goes LOW to turn off flash.

---

## Pipeline 7: FlashOn.py (5.x) — BOARD/BCM Bug

**Intent:** Standalone flash-on script.

**Trigger:** Direct CLI invocation: `python3 5.x/FlashOn.py`

**Path:**
```
python3 FlashOn.py
  → get_gpio_pins() → pins["Relay_Ch2"] = 19 (BCM value)
  → GPIO.setmode(GPIO.BOARD)           [FlashOn.py:32] ← BOARD MODE!
  → GPIO.setup(Relay_Ch2, GPIO.OUT)    [pin 19 in BOARD mode = physical pin 19]
  → FlashOn():
    → GPIO.output(Relay_Ch2, GPIO.LOW)  [FlashOn.py:53]
  → Process exits
```

**BUG (critical):** `GPIO.setmode(GPIO.BOARD)` but receives BCM pin 19 from `get_gpio_pins()`.
- In BCM mode, pin 19 = GPIO19 (physical pin 35).
- In BOARD mode, pin 19 = physical pin 19 = GPIO10.
- **The wrong physical pin is operated.** This script operates GPIO10 instead of GPIO19.

**BUG (polarity):** Sends LOW to turn flash ON. This is active-low (4.x convention), opposite from all other 5.x scripts. FlashOn.py was never updated for the 5.x polarity change.

**NOTE:** This script is NOT in cron_security.py's ALLOWED_SCRIPTS. Only reachable via direct CLI invocation. Low risk in production, but reveals copy-paste history.

---

## Pipeline 8: TakePhoto.py Flash Control (5.x)

**Intent:** Flash on during photo capture, off immediately after.

**Trigger:** Cron or web UI triggers `python3 TakePhoto.py`

**Path:**
```
cron → python3 TakePhoto.py
  → get_gpio_pins() → {Ch1=5, Ch2=19, Ch3=9}
  → GPIO.setmode(GPIO.BCM)

  [Startup, line 752]:
  → GPIO.output(Relay_Ch2, GPIO.HIGH)   ← Flash starts ON
  → GPIO.output(Relay_Ch3, GPIO.LOW)    ← Ensure "attract is on" per comment

  [Calibration, if enabled]:
  → flashOn():  [line 181]
    → GPIO.output(Relay_Ch2, GPIO.HIGH)   ← Flash ON
    → GPIO.output(Relay_Ch3, GPIO.LOW)    ← Attract "on"
  → [autofocus cycle]
  → flashOff():  [line 173]
    → GPIO.output(Relay_Ch3, GPIO.LOW)    ← Attract stays "on"
    → GPIO.output(Relay_Ch2, GPIO.LOW)    ← Flash OFF

  [Photo capture loop, line 564]:
  → flashOn()                             ← Flash ON
  → picam2.capture_request()              ← Take photo
  → if not onlyflash: flashOff()          ← Flash OFF (unless always-on mode)

  [End of script, line 910]:
  → GPIO.output(Relay_Ch3, GPIO.LOW)      ← Ensure attract stays "on"
  → No GPIO.cleanup() — comment explains why: "it will kill the relay"
```

**Pins:** Ch2=19 (flash), Ch3=9 (attract/UV)

**Logic:**
| Action | Ch2 (flash) | Ch3 (attract) |
|--------|-------------|---------------|
| flashOn | HIGH | LOW |
| flashOff | LOW | LOW |
| Script end | (unchanged) | LOW |

**Convention:** Ch2 (flash): HIGH=on, LOW=off (active-high). Ch3 (attract): **LOW=on** per comment "ensure attract is on because new wiring dictates that".

**BUG (polarity inconsistency):** TakePhoto.py treats Ch3 as active-LOW ("LOW means attract on"), but Attract_On.py sends HIGH to Ch3 to turn it on. **These contradict each other.** Either:
1. TakePhoto.py is wrong about Ch3 polarity, or
2. Attract_On.py is wrong about Ch3 polarity.

This is the core polarity bug from Issue #399.

---

## Pipeline 9: Attract_On.py (4.x) — Reference Implementation

**Intent:** Turn on attraction lights (4.x hardware).

**Trigger:** Cron or CLI

**Path:**
```
python3 4.x/Attract_On.py
  → get_gpio_pins() → {Ch1=26, Ch2=20, Ch3=21} (4.x defaults)
  → GPIO.setmode(GPIO.BCM)
  → AttractOn():
    → GPIO.output(Relay_Ch3, GPIO.LOW)    [line 52]
    → if onlyflash: GPIO.output(Relay_Ch2, GPIO.LOW)
    → else: GPIO.output(Relay_Ch2, GPIO.HIGH)  [line 57]
    → GPIO.output(Relay_Ch1, GPIO.LOW)    [line 59]
```

**Logic:** LOW=on for Ch1 and Ch3. Ch2 conditional: LOW if onlyflash, HIGH otherwise.

**Convention:** **Active-low.** LOW turns relays ON. This matches standard relay module behaviour (most relay boards are active-low).

---

## Pipeline 10: Attract_Off.py (4.x) — Reference Implementation

**Intent:** Turn off attraction lights (4.x hardware).

**Trigger:** Cron or CLI

**Path:**
```
python3 4.x/Attract_Off.py
  → AttractOff():
    → GPIO.output(Relay_Ch1, GPIO.HIGH)   [line 64]
    → GPIO.output(Relay_Ch2, GPIO.HIGH)   [line 69]
    → GPIO.output(Relay_Ch3, GPIO.HIGH)   [line 70]
```

**Logic:** HIGH=off for all channels. Active-low convention confirmed.

---

## Pipeline 11: TakePhoto.py Flash Control (4.x) — Reference

**Intent:** Flash on/off during photo capture (4.x hardware).

**Path:**
```
python3 4.x/TakePhoto.py
  → flashOn():  [line 177]
    → GPIO.output(Relay_Ch3, GPIO.LOW)    ← attract "on" (active-low)
    → GPIO.output(Relay_Ch2, GPIO.LOW)    ← flash on (active-low)
  → flashOff():  [line 185]
    → GPIO.output(Relay_Ch2, GPIO.HIGH)   ← flash off (active-low)
    → GPIO.output(Relay_Ch3, GPIO.LOW)    ← attract stays "on" (active-low)
```

**Logic:** All active-low. LOW=on, HIGH=off. Consistent with 4.x Attract scripts.

**KEY DIFFERENCE from 5.x TakePhoto:** 4.x flashOn sends Ch2 LOW. 5.x flashOn sends Ch2 HIGH. The polarity was **intentionally reversed** in commit `732e25c6` by Andrew Quitmeyer.

---

## Pipeline 12: DebugMode.py (5.x)

**Intent:** Stop cron, turn off attract lights, keep Pi running for debugging.

**Trigger:** Physical debug switch detected at boot → Scheduler.py invokes DebugMode.py. Or direct CLI.

**Path:**
```
python3 DebugMode.py
  → stop_cron() via subprocess
  → get_gpio_pins() → {Ch1=5, Ch2=19, Ch3=9}
  → GPIO.setmode(GPIO.BCM)
  → GPIO.setup(Ch1, OUT), GPIO.setup(Ch2, OUT), GPIO.setup(Ch3, OUT)
  → AttractOff():
    → GPIO.output(Relay_Ch1, GPIO.HIGH)   [line 77]
    → GPIO.output(Relay_Ch2, GPIO.HIGH)   [line 79]
    → GPIO.output(Relay_Ch3, GPIO.HIGH)   [line 80]
  → Writes shutdown_enabled=False to controls.txt
```

**Logic:** All channels → HIGH. **This is active-low "OFF" convention** (same as 4.x Attract_Off).

**BUG (polarity mismatch with 5.x):** DebugMode.py sends HIGH to mean "off". But 5.x Attract_On.py sends HIGH to mean "on". If the 5.x hardware is truly active-high, DebugMode.py turns everything ON instead of OFF. If 4.x active-low is correct, DebugMode.py is correct but Attract_On.py (5.x) is broken.

**Evidence:** DebugMode.py has the same AttractOff() code as 4.x/Attract_Off.py — it was not updated for the 5.x polarity change. The `onlyflash` check was also preserved from 4.x.

---

## Pipeline 13: Scheduler.py Physical Switch Check

**Intent:** Read physical switch position to determine operating mode (ACTIVE/DEBUG/OFF).

**Trigger:** Boot → Scheduler.py runs at startup

**Path:**
```
Scheduler.py [line 773]:
  → GPIO.setmode(GPIO.BCM)
  → off_pin = 16 (BCM, hardcoded)
  → debug_pin = 12 (BCM, hardcoded)
  → GPIO.setup(off_pin, GPIO.IN)
  → GPIO.setup(debug_pin, GPIO.IN)

  → debug_connected_to_ground():
    → GPIO.setup(debug_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    → pin_value = GPIO.input(debug_pin)
    → return pin_value == 0   (LOW = connected to ground = switch ON)

  → off_connected_to_ground():
    → GPIO.setup(off_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    → pin_value = GPIO.input(off_pin)
    → return pin_value == 0

  Mode resolution:
    DEBUG if debug_pin grounded
    OFF if off_pin grounded (overrides DEBUG)
    ACTIVE otherwise
```

**Pins:** GPIO 16 (off switch), GPIO 12 (debug switch). BCM mode. Hardcoded — NOT configurable via controls.txt.

**Also used in:** TakePhoto.py (both 4.x and 5.x), UpdateDisplay.py — same logic, same hardcoded pins.

**Concern:** 8 files hardcode these pins. If hardware changes, all must be updated manually.

---

## Pipeline 14: Scheduler.py → Shutdown → GPIO.cleanup()

**Intent:** Clean up GPIO before shutdown.

**Trigger:** Scheduler.py shutdown timer fires → run_shutdown_pi5() or run_shutdown_pi5_FAST()

**Path:**
```
Scheduler.py:run_shutdown_pi5() [line 500]:
  → GPIO.cleanup()          ← The ONLY cleanup in the entire codebase (besides ReadMuxAMuxB.py)
  → subprocess.Popen(["python", "UpdateDisplay.py"])
  → sudo shutdown -h now
```

**Also at line 578:** run_shutdown_pi5_FAST() calls GPIO.cleanup() before UpdateDisplay.py.

**And at line 935:** Main flow calls GPIO.cleanup() before UpdateDisplay.py subprocess.

**NOTE:** GPIO.cleanup() resets ALL pins to input mode. This is called before spawning UpdateDisplay.py which itself uses GPIO. The cleanup is correct timing (free pins for next user).

---

## Pipeline 15: ReadMuxAMuxB.py — Multiplexer

**Intent:** Read 32 switch positions via two 16-channel multiplexers.

**Trigger:** Direct CLI invocation only (not scheduled, not in cron_security whitelist).

**Path:**
```
python3 ReadMuxAMuxB.py
  → GPIO.setmode(GPIO.BOARD)           ← BOARD MODE
  → get_mux_pins() → {EN_A, EN_B, S0-S3, SIG} (all physical pin numbers)
  → GPIO.setup(EN_A, OUT), ..., GPIO.setup(SIG, IN, PUD_UP)
  → read_switches():
    → Enable MUX A: GPIO.output(EN_A, GPIO.LOW), GPIO.output(EN_B, GPIO.HIGH)
    → For channel 0-15: select_channel(ch), GPIO.input(SIG)
    → Enable MUX B: GPIO.output(EN_A, GPIO.HIGH), GPIO.output(EN_B, GPIO.LOW)
    → For channel 0-15: select_channel(ch), GPIO.input(SIG)
  → GPIO.cleanup()                     ← Properly cleans up
```

**Pins:** Physical BOARD pins from get_mux_pins(). NOT BCM.

**BUG (mode conflict):** Uses GPIO.BOARD while all other scripts use GPIO.BCM. get_mux_pins() returns physical pin numbers, so BOARD mode is correct for this script. But if any other script is using BCM mode concurrently, setmode() will fail.

**Cleanup:** Proper GPIO.cleanup() in finally block. Only GPIO script (besides Scheduler.py) that cleans up.

---

## Pipeline 16: UpdateDisplay.py — E-paper Display

**Intent:** Render system info on Waveshare 2.13" e-paper display.

**Trigger:** Scheduler.py at shutdown (via subprocess), or direct CLI.

**Path:**
```
python3 UpdateDisplay.py
  → import RPi.GPIO as GPIO             ← Uses RPi.GPIO (not gpiozero as initially expected)
  → GPIO pins managed by waveshare_epd library internally (via epd2in13_V4)
  → Also reads switch pins 16/12 (BCM, hardcoded) for mode detection
  → epdconfig.py manages: RST, DC, CS, BUSY pins via RPi.GPIO or spidev
```

**Pins:** E-paper pins from get_epaper_pins(): RST=17, DC=25, CS=8, BUSY=24, plus SPI CLK=11, MOSI=10.

**Switch pins:** GPIO 16 (off), GPIO 12 (debug) — hardcoded, same as Pipeline 13.

**Cleanup:** The waveshare library calls epd.sleep() which puts display in low-power mode but does NOT call GPIO.cleanup().

---

## Pipeline 17: Web UI GPIO Status

**Intent:** Frontend polls relay state for toggle switch UI.

**Trigger:** Frontend `GET /api/gpio/status`

**Path:**
```
GET /api/gpio/status → gpio.py:170 get_gpio_status()
  → _get_state() → reads gpio_state.json from DATA_DIR
  → Returns saved state (not live pin state)
```

**NOTE:** Does NOT read actual GPIO pin state. Relies on gpio_state.json written by Pipeline 1. If an external script (Attract_On.py, TakePhoto.py) changes pin state, the web UI will show stale data. The comment in code explains: "Reading OUTPUT pins can be unreliable and may reset their state."

**BUG (stale state):** Web UI will show incorrect state after any cron-triggered GPIO script runs. No mechanism to sync external GPIO changes back to gpio_state.json.

---

## Pipeline 18: GPIO Permission Validation (Startup)

**Intent:** Verify GPIO access when web UI starts.

**Trigger:** Web UI Flask app imports gpio.py module

**Path:**
```
gpio.py module load:
  → GPIO.setmode(GPIO.BCM)              [line 27]
  → GPIO.setwarnings(False)             [line 28]
  → _validate_gpio_permissions():
    → test_pin = get_gpio_pins()["Relay_Ch1"] or 26
    → GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)  [line 66]
    → GPIO.cleanup(test_pin)            [line 85]
```

**Side effect:** On startup, briefly sets Relay_Ch1 to OUTPUT/LOW, then cleans up. If the relay is active-low, this could cause a brief relay activation pulse at startup.

---

## Polarity Comparison Matrix

| Script | Ch1 ON | Ch1 OFF | Ch2 ON | Ch2 OFF | Ch3 ON | Ch3 OFF | Convention |
|--------|--------|---------|--------|---------|--------|---------|------------|
| **4.x Attract_On.py** | LOW | — | HIGH* | — | LOW | — | Active-low |
| **4.x Attract_Off.py** | — | HIGH | — | HIGH | — | HIGH | Active-low |
| **4.x TakePhoto flashOn** | — | — | LOW | — | LOW | — | Active-low |
| **4.x TakePhoto flashOff** | — | — | — | HIGH | LOW(stay) | — | Active-low |
| **5.x Attract_On.py** | HIGH | — | HIGH | — | HIGH | — | Active-HIGH |
| **5.x Attract_Off.py** | — | LOW | — | LOW | — | LOW | Active-HIGH |
| **5.x TakePhoto flashOn** | — | — | HIGH | — | LOW | — | **MIXED** |
| **5.x TakePhoto flashOff** | — | — | — | LOW | LOW(stay) | — | **MIXED** |
| **5.x Flash_On.py** | — | — | HIGH | — | — | — | Active-HIGH |
| **5.x Flash_Off.py** | — | — | — | LOW | — | — | Active-HIGH |
| **5.x FlashOn.py** | — | — | LOW | — | — | — | Active-low† |
| **5.x DebugMode AttractOff** | — | HIGH | — | HIGH | — | HIGH | Active-low |
| **5.x gpio.py control** | HIGH | LOW | — | — | — | — | Active-HIGH |
| **5.x gpio.py flash** | — | — | HIGH | LOW | — | — | Active-HIGH |

*4.x Attract_On Ch2: HIGH when not in onlyflash mode (flash off during attract), LOW in onlyflash mode.
†FlashOn.py also has BOARD/BCM mode bug — wrong physical pin entirely.

---

## Confirmed Bugs

### BUG-1: 5.x TakePhoto.py Ch3 polarity contradicts 5.x Attract_On.py

**Files:** `5.x/TakePhoto.py:184` vs `5.x/Attract_On.py:52`

TakePhoto.py comment says "ensure attract is on" while sending Ch3 LOW. Attract_On.py sends Ch3 HIGH to turn attract on. One of them has the wrong polarity for Ch3.

If active-high is correct (5.x convention): TakePhoto.py is wrong.
If active-low is correct: Attract_On.py is wrong.

### BUG-2: 5.x DebugMode.py uses 4.x polarity

**File:** `5.x/DebugMode.py:64-83`

AttractOff() sends HIGH to all channels — 4.x convention. If 5.x hardware is active-high, this turns everything ON instead of OFF.

### BUG-3: FlashOn.py BOARD/BCM mode mismatch

**File:** `5.x/FlashOn.py:32`

Uses `GPIO.BOARD` but pin from `get_gpio_pins()` is BCM value 19. Physical pin 19 = GPIO10, not GPIO19. Operates wrong hardware pin.

### BUG-4: Flash_On.py / Flash_Off.py naming confusion

**Files:** `5.x/Flash_On.py:25`, `5.x/Flash_Off.py:25`

`Relay_Ch1 = pins["Relay_Ch2"]` — misleading variable alias. Functions named `AttractOn`/`AttractOff` for a flash script. Print banner says "attract off!" in a flash-on script.

### BUG-5: Web UI state desynchronisation

**File:** `webui/backend/routes/gpio.py:184`

`/api/gpio/status` reads from gpio_state.json, not live pins. After any cron script changes GPIO state, web UI shows stale data. No sync mechanism.

### BUG-6: No GPIO.cleanup() in relay scripts

**Files:** All of `5.x/Attract_On.py`, `Attract_Off.py`, `Flash_On.py`, `Flash_Off.py`, `FlashOn.py`

None call GPIO.cleanup(). On Pi 5 with rpi-lgpio, pin state persists after process exit. Runtime observation confirms: GPIO 5 remains output/HIGH long after the script that set it has exited.

### BUG-7: GPIO 6 orphaned output

**Source:** Runtime observation (runtime_state.md)

GPIO 6 is output, driving HIGH, consumer "lg" — but GPIO 6 is not referenced in controls.txt or any current script. Likely set by a previous version that used pin 6 for Relay_Ch2 (commit 732e25c6 originally used pins 5/6/9 before changing Ch2 to 19).

### BUG-8: Hardcoded switch pins

**Files:** 8 files hardcode `off_pin=16`, `debug_pin=12`

Not configurable via controls.txt. If hardware changes, all 8 files must be manually updated.

### BUG-9: Startup permission check side effect

**File:** `webui/backend/routes/gpio.py:66`

`GPIO.setup(test_pin, GPIO.OUT, initial=GPIO.LOW)` briefly drives Relay_Ch1 LOW at web UI startup. On active-low hardware, this would momentarily activate the relay.

---

## Entry Point Summary

| Entry Point | Scripts Invoked | GPIO Pins Affected |
|-------------|----------------|-------------------|
| Web UI relay toggle | gpio.py (in-process) | Any relay pin |
| Web UI flash button | gpio.py (in-process) | Relay_Ch2 |
| Web UI scheduler activate | cron_bridge → crontab → Attract_On/Off, Flash_On/Off | Ch1, Ch2, Ch3 |
| Boot-time Scheduler.py | Physical switch check, DebugMode.py, TakePhoto.py, UpdateDisplay.py | 16, 12, Ch1-3 |
| Cron: TakePhoto.py | TakePhoto.py (in-process GPIO) | Ch2, Ch3, 16, 12 |
| CLI: FlashOn.py | FlashOn.py | Ch2 (wrong pin due to BOARD bug) |
| CLI: ReadMuxAMuxB.py | ReadMuxAMuxB.py | Mux pins (BOARD mode) |
| Scheduler shutdown | GPIO.cleanup(), UpdateDisplay.py | All, then e-paper pins |

---

## Cleanup Inventory

| Script | Has GPIO.cleanup()? | Notes |
|--------|---------------------|-------|
| Attract_On.py (5.x) | No | Pins persist as output |
| Attract_Off.py (5.x) | No | Pins persist as output |
| Flash_On.py (5.x) | No | Pin persists as output |
| Flash_Off.py (5.x) | No | Pin persists as output |
| FlashOn.py (5.x) | No | Pin persists (wrong pin) |
| TakePhoto.py (5.x) | No | Intentional: "it will kill the relay" |
| DebugMode.py (5.x) | No | Pins persist |
| Scheduler.py (5.x) | Yes (x3) | Before UpdateDisplay subprocess + shutdown |
| ReadMuxAMuxB.py | Yes | In finally block |
| gpio.py (web UI) | Partial | cleanup(test_pin) on startup validation only |
| UpdateDisplay.py | No | waveshare lib calls epd.sleep() |
