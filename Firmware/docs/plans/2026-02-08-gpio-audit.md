# GPIO System Audit — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce a complete inventory of every GPIO operation in the Mothbox codebase, trace every logic pipeline from user intent to electrical outcome, and deliver a living architecture reference plus a specification for the target GPIO model.

**Architecture:** Three-phase audit. Phase 1 builds tooling and runs local static analysis (AST + grep across 129 files). Phase 2 investigates the live Pi via SSH (pyright with real GPIO libs, runtime pin state, deployed config). Phase 3 synthesizes findings into three deliverables: raw audit, architecture reference, and target specification.

**Tech Stack:** Python `ast` module, grep/glob, pyright (remote), SSH to `mothbox-remote`, `gpioinfo`/`pinctrl` on Pi 5

---

## Phase 1: Local Static Analysis

### Task 1: Write the AST GPIO extraction script

**Files:**
- Create: `tools/gpio_audit/extract_gpio_calls.py`

**Step 1: Write the extraction script**

This script walks every `.py` file in the repo, parses it with `ast`, and extracts:
- All GPIO-related imports (RPi.GPIO, lgpio, gpiod, gpiozero, waveshare_epd)
- All `GPIO.setmode()` calls with the mode argument (BCM/BOARD)
- All `GPIO.setup()` calls with pin, direction, and pull-up/pull-down
- All `GPIO.output()` calls with pin and HIGH/LOW value
- All `GPIO.input()` calls with pin
- All `GPIO.cleanup()` calls with scope
- All `GPIO.setwarnings()` calls
- All lgpio/gpiod/gpiozero equivalents
- All pin variable assignments (e.g., `Relay_Ch1 = pins["Relay_Ch1"]`)
- The enclosing function/class for each call

Output: JSON file at `tools/gpio_audit/raw_ast_results.json`

```python
#!/usr/bin/env python3
"""AST-based GPIO call extractor for Mothbox codebase audit."""
import ast
import json
import sys

# GPIO libraries to track
GPIO_MODULES = {
    'RPi.GPIO', 'RPi', 'GPIO', 'lgpio', 'gpiod', 'gpiozero',
    'waveshare_epd', 'epdconfig',
}

# GPIO function names to track (method names on GPIO objects)
GPIO_FUNCTIONS = {
    'setmode', 'setup', 'output', 'input', 'cleanup', 'setwarnings',
    'gpio_write', 'gpio_read', 'gpio_claim_output', 'gpio_claim_input',
    'gpio_free',  # lgpio
    'Line', 'Chip',  # gpiod
}

# Pin variable patterns
PIN_KEYWORDS = {
    'relay', 'ch1', 'ch2', 'ch3', 'pin', 'rst', 'dc', 'cs', 'busy',
    'pwr', 'sck', 'mosi', 'miso', 'gpio', 'mux', 'sig', 'en',
    's0', 's1', 's2', 's3',
}


class GPIOVisitor(ast.NodeVisitor):
    """Visits AST nodes and extracts GPIO-related operations."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.imports = []
        self.calls = []
        self.pin_assignments = []
        self.mode_sets = []
        self._current_func = None
        self._current_class = None

    def _context(self):
        """Return the enclosing function/class context."""
        parts = []
        if self._current_class:
            parts.append(self._current_class)
        if self._current_func:
            parts.append(self._current_func)
        return '.'.join(parts) if parts else '<module>'

    def _stringify_node(self, node):
        """Best-effort conversion of AST node to source string."""
        try:
            return ast.unparse(node)
        except Exception:
            return repr(node)

    def visit_Import(self, node):
        for alias in node.names:
            if any(mod in alias.name for mod in GPIO_MODULES):
                self.imports.append({
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'import',
                    'module': alias.name,
                    'alias': alias.asname,
                    'context': self._context(),
                })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ''
        if any(mod in module for mod in GPIO_MODULES):
            for alias in node.names:
                self.imports.append({
                    'file': self.filepath,
                    'line': node.lineno,
                    'type': 'from_import',
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'context': self._context(),
                })
        # Also catch: from mothbox_paths import get_gpio_pins, etc.
        if node.names:
            for alias in node.names:
                if 'gpio' in alias.name.lower() or 'pin' in alias.name.lower():
                    self.imports.append({
                        'file': self.filepath,
                        'line': node.lineno,
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'context': self._context(),
                        'note': 'pin/gpio helper import',
                    })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        old = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = old

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        old = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old

    def visit_Call(self, node):
        call_str = self._stringify_node(node.func)
        # Match GPIO.output(...), GPIO.setup(...), lgpio.gpio_write(...), etc.
        is_gpio_call = False
        if any(func in call_str for func in GPIO_FUNCTIONS):
            is_gpio_call = True
        if any(mod in call_str for mod in ('GPIO.', 'lgpio.', 'gpiod.', 'gpiozero.')):
            is_gpio_call = True
        # Catch get_gpio_pins(), get_relay_level(), etc.
        if 'gpio' in call_str.lower() or 'relay' in call_str.lower():
            is_gpio_call = True

        if is_gpio_call:
            args_str = [self._stringify_node(a) for a in node.args]
            kwargs_str = {
                kw.arg: self._stringify_node(kw.value)
                for kw in node.keywords if kw.arg
            }
            self.calls.append({
                'file': self.filepath,
                'line': node.lineno,
                'call': call_str,
                'args': args_str,
                'kwargs': kwargs_str,
                'context': self._context(),
            })
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Track pin variable assignments: Relay_Ch1 = ..., pin = ..., etc.
        for target in node.targets:
            if isinstance(target, ast.Name):
                name_lower = target.id.lower()
                if any(kw in name_lower for kw in PIN_KEYWORDS):
                    self.pin_assignments.append({
                        'file': self.filepath,
                        'line': node.lineno,
                        'name': target.id,
                        'value': self._stringify_node(node.value),
                        'context': self._context(),
                    })
        self.generic_visit(node)


def scan_file(filepath):
    """Parse a single Python file and extract GPIO operations."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {'file': filepath, 'error': f'SyntaxError: {e}'}

    visitor = GPIOVisitor(filepath)
    visitor.visit(tree)

    if not (visitor.imports or visitor.calls or visitor.pin_assignments):
        return None  # No GPIO usage in this file

    return {
        'file': filepath,
        'imports': visitor.imports,
        'calls': visitor.calls,
        'pin_assignments': visitor.pin_assignments,
    }


def scan_directory(root_dir, exclude_dirs=None):
    """Walk directory tree and scan all Python files."""
    exclude_dirs = exclude_dirs or {
        '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    }
    results = []
    errors = []

    for dirpath, _dirnames, filenames in sorted_walk(root_dir, exclude_dirs):
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            fpath = dirpath + '/' + fname
            result = scan_file(fpath)
            if result:
                if 'error' in result:
                    errors.append(result)
                else:
                    results.append(result)

    return {'files_with_gpio': results, 'parse_errors': errors}


def sorted_walk(root, exclude_dirs):
    """Walk directory tree, excluding specified directories."""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        yield dirpath, dirnames, filenames


if __name__ == '__main__':
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = scan_directory(root)

    # Summary
    print(f"Files with GPIO usage: {len(data['files_with_gpio'])}")
    print(f"Parse errors: {len(data['parse_errors'])}")
    total_imports = sum(len(f['imports']) for f in data['files_with_gpio'])
    total_calls = sum(len(f['calls']) for f in data['files_with_gpio'])
    total_pins = sum(len(f['pin_assignments']) for f in data['files_with_gpio'])
    print(f"Total GPIO imports: {total_imports}")
    print(f"Total GPIO calls: {total_calls}")
    print(f"Total pin assignments: {total_pins}")

    # Write full results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_ast_results.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nFull results written to: {output_path}")
```

**Step 2: Run the script and verify output**

Run: `python3 tools/gpio_audit/extract_gpio_calls.py .`
Expected: Summary showing file count, import count, call count, pin assignment count. JSON output at `tools/gpio_audit/raw_ast_results.json`.

**Step 3: Commit**

```bash
git add tools/gpio_audit/extract_gpio_calls.py
git commit -m "chore: add AST-based GPIO extraction script for audit"
```

---

### Task 2: Run local grep passes for cross-file relationships

These capture what AST cannot: subprocess invocations, cron expressions, config file references, and string-based script paths.

**Files:**
- Create: `tools/gpio_audit/grep_results.md`

**Step 1: Run grep for subprocess calls that invoke GPIO scripts**

Search for any subprocess call that references a GPIO-related script name (Attract_On, Flash_On, TurnEverythingOff, etc.):

```bash
# Subprocess invocations of GPIO scripts
rg -n "subprocess\.(run|call|Popen|check_call|check_output).*(?:Attract|Flash|Relay|TurnEverything|GPIO)" --glob "*.py" .

# String references to GPIO script filenames
rg -n "(Attract_On|Attract_Off|Flash_On|Flash_Off|FlashOn|TurnEverythingOff)\.py" --glob "*.py" .
```

**Step 2: Run grep for cron bridge / scheduler references to GPIO actions**

```bash
# Cron bridge action types that map to GPIO
rg -n "(attract_on|attract_off|flash_on|flash_off|gpio)" --glob "*.py" webui/backend/lib/cron_bridge.py webui/backend/lib/schedule_schema.py

# Scheduler subprocess dispatching
rg -n "(get_script_path|get_takephoto_script)" --glob "*.py" .
```

**Step 3: Run grep for controls.txt pin configuration parsing**

```bash
# Where controls.txt relay/pin config is read
rg -n "(Relay_Ch|relay_|gpio_pin|epaper_.*_pin|mux_|pca9536)" --glob "*.py" .

# Where get_gpio_pins / get_hardware_config is called
rg -n "(get_gpio_pins|get_hardware_config|get_epaper_pins|get_mux_pins)" --glob "*.py" .
```

**Step 4: Run grep for HIGH/LOW logic and polarity patterns**

```bash
# Every GPIO.HIGH / GPIO.LOW usage with surrounding context
rg -n -C2 "GPIO\.(HIGH|LOW)" --glob "*.py" .

# Every lgpio write value
rg -n -C2 "gpio_write" --glob "*.py" .
```

**Step 5: Compile results into `tools/gpio_audit/grep_results.md`**

Organize grep output into sections: subprocess calls, scheduler actions, config parsing, HIGH/LOW usage. Include file:line for every match.

**Step 6: Commit**

```bash
git add tools/gpio_audit/grep_results.md
git commit -m "chore: add grep results for GPIO cross-file analysis"
```

---

### Task 3: Run git history analysis on GPIO files

Understand how GPIO code evolved over time — who changed what, when, and why.

**Files:**
- Create: `tools/gpio_audit/git_history.md`

**Step 1: Get commit history for all GPIO-related files**

```bash
# History of the core GPIO scripts
git log --oneline --follow -- 5.x/Attract_On.py 5.x/Attract_Off.py 5.x/Flash_On.py 5.x/Flash_Off.py 5.x/FlashOn.py 5.x/TakePhoto.py 5.x/TurnEverythingOff.py

# History of the web UI GPIO route
git log --oneline --follow -- webui/backend/routes/gpio.py

# History of mothbox_paths GPIO functions
git log --oneline -S "get_gpio_pins" -- mothbox_paths.py

# History of 4.x counterparts
git log --oneline --follow -- 4.x/Attract_On.py 4.x/Attract_Off.py 4.x/FlashOn.py 4.x/TakePhoto.py

# When were 5.x scripts created vs copied from 4.x?
git log --diff-filter=A --oneline -- 5.x/Attract_On.py 5.x/Flash_On.py 5.x/Flash_Off.py
```

**Step 2: Blame key lines in GPIO scripts**

```bash
# Who wrote the HIGH/LOW logic in each file?
git blame 5.x/Attract_On.py
git blame 5.x/Attract_Off.py
git blame webui/backend/routes/gpio.py
```

**Step 3: Compile into `tools/gpio_audit/git_history.md`**

Document: when each file was created, key commits that changed GPIO logic, whether 5.x was copy-pasted from 4.x, and any commits that mention polarity/relay/active-low.

**Step 4: Commit**

```bash
git add tools/gpio_audit/git_history.md
git commit -m "chore: add git history analysis for GPIO audit"
```

---

## Phase 2: Remote Investigation (mothbox-remote)

### Task 4: Run pyright on the Pi with real GPIO library resolution

**Files:**
- Create: `tools/gpio_audit/pyright_results.md`

**Step 1: Run pyright on all GPIO scripts via SSH**

```bash
# Run pyright on the core GPIO files on the Pi
ssh mothbox-remote "cd /opt/mothbox && npx pyright --outputjson \
    5.x/Attract_On.py 5.x/Attract_Off.py 5.x/Flash_On.py 5.x/Flash_Off.py \
    5.x/FlashOn.py 5.x/TakePhoto.py 5.x/TurnEverythingOff.py \
    webui/backend/routes/gpio.py" > /tmp/pyright_gpio.json

# Run on e-paper, PCA9536, multiplexer files
ssh mothbox-remote "cd /opt/mothbox && npx pyright --outputjson \
    5.x/UpdateDisplay.py 5.x/PCA9536.py 5.x/testmuxi2c.py" > /tmp/pyright_peripheral.json
```

Expected: JSON output with resolved types. GPIO.HIGH/GPIO.LOW should resolve to `int`. Any type errors flagged.

**Step 2: Check what GPIO.HIGH and GPIO.LOW actually resolve to at runtime**

```bash
ssh mothbox-remote "python3 -c \"
import RPi.GPIO as GPIO
print('GPIO.HIGH =', GPIO.HIGH, type(GPIO.HIGH))
print('GPIO.LOW =', GPIO.LOW, type(GPIO.LOW))
print('GPIO.BCM =', GPIO.BCM)
print('GPIO.BOARD =', GPIO.BOARD)
print('GPIO.OUT =', GPIO.OUT)
print('GPIO.IN =', GPIO.IN)
print('GPIO.PUD_UP =', GPIO.PUD_UP)
print('GPIO.PUD_DOWN =', GPIO.PUD_DOWN)
\""
```

**Step 3: Check lgpio constants and available functions**

```bash
ssh mothbox-remote "python3 -c \"
import lgpio
print('Available functions:', [x for x in dir(lgpio) if 'gpio' in x.lower()])
\""
```

**Step 4: Compile findings into `tools/gpio_audit/pyright_results.md`**

Document: type errors, unresolved imports, constant values, library version differences.

**Step 5: Commit**

```bash
git add tools/gpio_audit/pyright_results.md
git commit -m "chore: add pyright remote analysis results for GPIO audit"
```

---

### Task 5: Capture runtime GPIO state on the Pi

**Files:**
- Create: `tools/gpio_audit/runtime_state.md`

**Step 1: Capture current GPIO pin state**

```bash
# gpioinfo shows all GPIO lines, their direction, and active state
ssh mothbox-remote "gpioinfo 2>/dev/null || echo 'gpioinfo not available'"

# pinctrl on Pi 5 shows pin function assignments
ssh mothbox-remote "pinctrl 2>/dev/null | head -60 || echo 'pinctrl not available'"

# Check specific relay pins (5, 6, 13)
ssh mothbox-remote "pinctrl get 5; pinctrl get 6; pinctrl get 13" 2>/dev/null

# /sys/class/gpio exported pins
ssh mothbox-remote "for pin in 5 6 13; do echo \"GPIO \$pin:\"; cat /sys/class/gpio/gpio\$pin/direction 2>/dev/null; cat /sys/class/gpio/gpio\$pin/value 2>/dev/null; done"
```

**Step 2: Check e-paper, mux, PCA9536 pin state**

```bash
# E-paper pins from controls.txt: RST=17, DC=25, CS=8, BUSY=24, PWR=18
ssh mothbox-remote "for pin in 17 25 8 24 18; do echo \"GPIO \$pin (epaper):\"; pinctrl get \$pin 2>/dev/null; done"

# I2C devices (PCA9536, INA260, mux)
ssh mothbox-remote "i2cdetect -y 1 2>/dev/null || echo 'i2cdetect not available'"
```

**Step 3: Check what processes/services interact with GPIO**

```bash
# Mothbox service status
ssh mothbox-remote "systemctl status mothbox-webui.service 2>/dev/null | head -15"

# Any process holding gpiomem/gpiochip
ssh mothbox-remote "sudo lsof /dev/gpiomem* /dev/gpiochip* 2>/dev/null"

# Check if any GPIO pins are exported by sysfs
ssh mothbox-remote "ls /sys/class/gpio/ 2>/dev/null"
```

**Step 4: Compare deployed controls.txt with repo**

```bash
# Deployed config
ssh mothbox-remote "cat /opt/mothbox/controls.txt"

# Diff against repo
ssh mothbox-remote "cat /opt/mothbox/controls.txt" > /tmp/deployed_controls.txt
diff /tmp/deployed_controls.txt controls.txt
```

**Step 5: Compare deployed GPIO scripts with repo versions**

```bash
for script in Attract_On.py Attract_Off.py Flash_On.py Flash_Off.py FlashOn.py TakePhoto.py TurnEverythingOff.py; do
    echo "=== $script ==="
    ssh mothbox-remote "cat /opt/mothbox/5.x/$script 2>/dev/null" | diff - "5.x/$script" || echo "DIFFERS"
done
```

**Step 6: Compile into `tools/gpio_audit/runtime_state.md`**

Document: actual pin levels, exported pins, I2C devices detected, service state, deployed vs repo differences.

**Step 7: Commit**

```bash
git add tools/gpio_audit/runtime_state.md
git commit -m "chore: add runtime GPIO state from mothbox-remote"
```

---

## Phase 3: Synthesis

### Task 6: Trace all logic pipelines

Using the raw data from Phases 1-2, manually trace every complete signal path from trigger to electrical outcome.

**Files:**
- Create: `tools/gpio_audit/logic_pipelines.md`

**Step 1: Read every GPIO-using file identified by the AST scan**

Read each file in full. For every `GPIO.output()` call, trace backwards:
- What function is it in?
- What calls that function?
- What triggers that caller? (API route? Subprocess from scheduler? Cron? CLI?)
- What is the user's **intent** at the start of the chain?
- What is the **electrical outcome** at the end?

**Step 2: Document each pipeline**

For each distinct signal path, document:

```
Pipeline: [Human-readable name]
Intent: [What the user/system wants to happen]
Trigger: [Entry point — UI button, cron job, script invocation, etc.]
Path: [trigger] → [handler] → [function] → [GPIO call]
Pin: [GPIO number and what it's connected to]
Logic: [HIGH/LOW and what that means electrically]
Outcome: [What actually happens on the hardware]
Bug: [If intent ≠ outcome, describe the mismatch]
```

Expected pipelines to trace (discover the actual list, don't assume this is complete):
- Web UI "Attract On" button → gpio route → GPIO.output
- Web UI "Attract Off" button → gpio route → GPIO.output
- Web UI "Flash trigger" → gpio route → GPIO.output
- Web UI relay toggle → gpio route → GPIO.output
- Scheduler routine → subprocess Attract_On.py → GPIO.output
- Scheduler routine → subprocess Attract_Off.py → GPIO.output
- Scheduler routine → subprocess Flash_On.py → GPIO.output
- Scheduler routine → subprocess Flash_Off.py → GPIO.output
- TakePhoto.py flash management → GPIO.output
- TakePhoto.py attract management → GPIO.output
- TurnEverythingOff.py → GPIO.output for all pins
- UpdateDisplay.py → e-paper pin operations
- PCA9536.py → I2C GPIO expander operations
- Multiplexer scripts → mux pin operations
- 4.x equivalents of all the above

**Step 3: Identify all mismatches between intent and outcome**

For each pipeline where the electrical outcome doesn't match the stated intent, document the root cause (polarity inversion, wrong pin, no-op on unconnected pin, etc.)

**Step 4: Commit**

```bash
git add tools/gpio_audit/logic_pipelines.md
git commit -m "chore: add GPIO logic pipeline trace"
```

---

### Task 7: Write the raw audit document

Consolidate all Phase 1-2 findings into a single diagnostic document.

**Files:**
- Create: `docs/plans/2026-02-08-gpio-raw-audit.md`

**Step 1: Compile the raw audit**

Sections:
1. **File inventory** — every file with GPIO usage, categorized (relay scripts, web UI, e-paper, I2C, mux, tests, old/deprecated)
2. **Library inventory** — which GPIO libraries are used where, version info, compatibility notes
3. **Pin map** — every GPIO pin referenced in code + config, what it controls, how it's obtained (hardcoded vs config)
4. **Operation inventory** — every GPIO.setup/output/input/cleanup call with file:line, arguments, and enclosing context
5. **Logic pipelines** — from Task 6
6. **Entry points** — every mechanism that can trigger GPIO operations (discovered, not assumed)
7. **Cleanup patterns** — how each file handles GPIO resource release
8. **Mode conflicts** — BCM vs BOARD usage across files
9. **Runtime state** — from Task 5
10. **Deployed vs repo diff** — from Task 5
11. **Git evolution** — from Task 3
12. **Known bugs** — every mismatch between intent and outcome

**Step 2: Commit**

```bash
git add docs/plans/2026-02-08-gpio-raw-audit.md
git commit -m "docs: add raw GPIO system audit"
```

---

### Task 8: Write the architecture reference

Distill the raw audit into a clean, permanent reference document.

**Files:**
- Create: `docs/gpio-architecture.md`

**Step 1: Write the architecture reference**

This is the **living document** that stays in the repo. Sections:

1. **GPIO overview** — what GPIO does in Mothbox, which subsystems use it
2. **Pin map** — canonical table of every pin, its function, connected hardware, and configuration source
3. **Library usage** — which GPIO library is used for what, and why
4. **Polarity model** — how active-high vs active-low works, the configuration mechanism
5. **Signal paths** — clean diagrams (text-based) of each logic pipeline from trigger to pin
6. **Resource management** — cleanup contract, contention avoidance, mode setting rules
7. **Configuration** — how pins are configured via `controls.txt` and `mothbox_paths.py`
8. **4.x vs 5.x differences** — pin mapping differences, any logic differences
9. **Testing** — how to test GPIO code without hardware, mock patterns
10. **Troubleshooting** — common issues, diagnostic commands

**Step 2: Commit**

```bash
git add docs/gpio-architecture.md
git commit -m "docs: add GPIO architecture reference"
```

---

### Task 9: Write the target specification

Define what the GPIO system **should** look like after the refactor.

**Files:**
- Create: `docs/plans/2026-02-08-gpio-target-spec.md`

**Step 1: Write the specification**

Based on the bugs and antipatterns discovered in the audit, define:

1. **Centralized polarity model** — `relay_active_low` config option, `get_relay_level(on=True)` helper in `mothbox_paths.py`
2. **Single source of truth for pins** — all pins come from `get_gpio_pins()` / `get_hardware_config()`, zero hardcoded pin numbers
3. **GPIO abstraction layer** — whether to standardize on one library or provide a thin wrapper
4. **Cleanup contract** — every GPIO user must follow defined setup/cleanup pattern
5. **Mode standardization** — one GPIO mode (BCM or BOARD) across the entire codebase
6. **Script responsibilities** — each script controls only its designated pins, not all three relays
7. **Web UI alignment** — gpio.py route uses the same polarity model as scripts
8. **TakePhoto.py corrections** — correct pin for attract, proper cleanup
9. **Error handling** — GPIO contention prevention, graceful degradation
10. **Test strategy** — how to verify polarity logic in unit tests without hardware
11. **Migration plan** — how to get from current state to target state without breaking deployed systems

**Step 2: Commit**

```bash
git add docs/plans/2026-02-08-gpio-target-spec.md
git commit -m "docs: add GPIO target specification"
```

---

## Execution Notes

**Parallelism opportunities:**
- Tasks 1-3 (local analysis) can run in parallel — they're independent
- Task 4 and Task 5 (remote investigation) can run in parallel with each other
- Tasks 4-5 can run in parallel with Tasks 1-3
- Tasks 6-9 are sequential — each depends on the previous

**Key risks:**
- AST script may miss GPIO usage via dynamic dispatch or exec/eval (grep catches these)
- Pyright on the Pi may struggle with the project structure (no pyrightconfig.json)
- Deployed code on Pi may differ from repo significantly if updates haven't been pushed
- Some GPIO files may have syntax errors preventing AST parsing (script reports these)

**Scope boundaries:**
- OldScripts/ files are IN scope (they reveal historical patterns and may still be invoked)
- Test files are IN scope (they reveal assumptions about GPIO behavior)
- Vendor e-paper library code is IN scope (it's a GPIO consumer)
- Frontend code is OUT of scope (no GPIO usage, only API calls)
- Node modules, .git, __pycache__ are OUT of scope
