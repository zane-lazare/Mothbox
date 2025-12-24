# Visual Scheduler UI - Developer Guide

**Last Updated**: 2025-12-18
**Version**: 2.0
**Audience**: Developers implementing the Mothbox visual scheduler system

---

## Table of Contents

1. [Overview](#overview)
2. [Executive Summary](#executive-summary)
3. [Architecture](#architecture)
4. [Integration Points](#integration-points)
5. [Implementation Guide](#implementation-guide)
6. [API Specification](#api-specification)
7. [Data Structures](#data-structures)
8. [Frontend Components](#frontend-components)
9. [Testing Strategy](#testing-strategy)
10. [Common Patterns Reference](#common-patterns-reference)
11. [Implementation Phases](#implementation-phases)

---

## Overview

### Purpose

The Visual Scheduler UI wraps the existing cron-based `Scheduler.py` infrastructure with a user-friendly calendar interface. The system uses a **two-tier architecture** to separate **what happens** (Event Patterns) from **when it happens** (Schedule Patterns), enabling reusable action sequences and flexible scheduling triggers.

### Scope

**Included:**
- **Two-tier scheduling**: Event Patterns (reusable action sequences) + Schedule Patterns (timing triggers)
- **Sub-hour GPIO control**: Support patterns like "UV on for 15min, photo at +5min, UV off at +15min"
- **Interval scheduling**: Repeat event patterns every N minutes within time windows
- **Solar/lunar triggers**: sunset+30, astronomical_dusk, full moon ±2 days
- **Sensor triggers**: Motion, light level, and temperature-based scheduling
- Calendar-based schedule creation and management
- Multiple named schedules (one active at a time)
- Expert mode for raw cron expression editing
- Conflict detection with user-driven resolution
- Deployment integration (create/link on activation)
- Schedule import/export/backup

**Excluded:**
- Modifying the core `Scheduler.py` cron/RTC infrastructure (we wrap it)
- Power management scheduling (future phase)
- E-paper update scheduling (future phase)

### User Stories

- As a **field researcher**, I want to create a "Summer Moth Survey" schedule that runs from sunset+30min to 6am daily from June-August, so that I can deploy the Mothbox and let it run autonomously.
- As a **researcher**, I want to schedule captures only around the full moon (+/- 2 days), so that I can study lunar effects on moth behavior.
- As a **technician**, I want to save my schedule as a preset, so that I can apply it to multiple Mothbox units quickly.
- As an **advanced user**, I want to edit the raw cron expression, so that I can create complex scheduling patterns.
- As a **researcher**, I want to run UV light for 15 minutes every hour from 1am-6am with a photo at the 5-minute mark, so I can study attraction patterns without constant monitoring.

---

## Executive Summary

### Two-Tier Conceptual Model

The scheduler uses a **two-tier conceptual model** to enable flexible scheduling:

1. **Event Patterns**: Reusable action sequences with relative timing
   - Actions use relative offsets from pattern start (e.g., "UV on at t=0, photo at t+5min, UV off at t+15min")
   - Multiple patterns can be combined in a single schedule

2. **Schedules**: Define WHEN event patterns execute
   - Embed event patterns directly (single-file storage for portability)
   - Support multiple trigger types: interval, solar, moon phase, sensor
   - Include time windows, date constraints, and deployment linkage

**Storage**: Each schedule is a **single self-contained JSON file** with patterns embedded inline, making schedules portable and easy to export/import between Mothbox units.

### Example Use Case

> "Starting at 1am turn UV on for 15mins every hour until 6am, run takephoto.py at 01:05am"

**Event Pattern**: "UV Capture Cycle"
```
- UV_ON at offset +0 minutes
- TakePhoto at offset +5 minutes
- UV_OFF at offset +15 minutes
- Total duration: 15 minutes
```

**Schedule**: "Nightly Hourly Survey"
```
- Contains: "UV Capture Cycle" pattern (embedded)
- Trigger: interval_minutes=60
- Time window: 01:00 to 06:00
- Date range: June-August 2024
```

**Result**: UV on at 1:00, photo at 1:05, UV off at 1:15, repeat at 2:00, 3:00... until 6:00

### Trigger Types

| Trigger | Description | Example |
|---------|-------------|---------|
| **Interval** | Every N minutes within time window | Every 60 min from 21:00-05:00 |
| **Solar** | Relative to sun position | sunset+30, astronomical_dusk |
| **Moon Phase** | On specific lunar phases | Full moon ±2 days |
| **Fixed Time** | Specific clock time | Every day at 21:00 |

### Pre-conditions (Optional)

Any trigger type can have optional sensor pre-conditions. Pre-conditions are checked at capture time and skip the capture if not met:

| Sensor | Description | Example |
|--------|-------------|---------|
| **Light** | BH1750/LTR303 I2C lux sensor | Only capture if light < 100 lux |
| **Temperature** | TMP102/MCP9808 I2C temp sensor | Skip if temperature < 5°C |

### Related Documentation

- **CLAUDE.md**: Project architecture, GPS EXIF system, Export system
- **5.x/Scheduler.py**: Existing cron/RTC scheduling infrastructure
- **webui/docs/dev/api/deployment.md**: Deployment metadata system
- **webui/docs/dev/api/export-presets.md**: Preset management patterns

### Dependencies

#### New External Libraries

| Library | Version | Purpose | Size | Install |
|---------|---------|---------|------|---------|
| `astral` | ≥3.2 | Sun/moon calculations | ~50KB | `pip install astral` |

**Why `astral`?**
- Pure Python (no C compilation on Raspberry Pi)
- Accurate sun times (±1 minute)
- Moon phases, moonrise/moonset
- Twilight types (civil, nautical, astronomical)
- Blue hour and golden hour for photography
- Lightweight (~50KB vs 3MB for ephem)

#### Already Available (in requirements.txt)

| Library | Purpose |
|---------|---------|
| `Flask` | API routes |
| `Flask-Limiter` | Rate limiting |
| `python-crontab` | Cron job manipulation |

#### Standard Library (No Install)

| Module | Purpose |
|--------|---------|
| `dataclasses` | Schema definitions |
| `datetime`, `timedelta` | Time handling |
| `json` | File storage |
| `threading` (RLock) | Thread safety |
| `collections` (OrderedDict) | LRU cache |
| `uuid` | Schedule/event IDs |
| `re` | Time spec parsing |
| `math` | Illumination calculations |

---

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Interface                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    React Frontend                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │  Calendar  │  │  Pattern   │  │  Conflict  │  │   Expert   │ │   │
│  │  │    View    │  │  Builder   │  │  Resolver  │  │    Mode    │ │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │   │
│  │               │              │              │              │       │   │
│  │               └──────────────┴──────────────┴──────────────┘      │   │
│  │                              │                                      │   │
│  │                      SchedulerContext + Hooks                       │   │
│  └──────────────────────────────┬─────────────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ REST API
┌─────────────────────────────────┼───────────────────────────────────────┐
│                           Flask Backend                                   │
│  ┌──────────────────────────────┴─────────────────────────────────────┐ │
│  │                    scheduler_ui.py Routes                            │ │
│  │  GET/POST/PUT/DELETE /schedules, /activate, /preview, /moon         │ │
│  └───────────────────────────────┬────────────────────────────────────┘ │
│                                  │                                       │
│  ┌───────────────────────────────┴────────────────────────────────────┐ │
│  │                     SchedulerService                                 │ │
│  │  - LRU Cache (300s TTL)                                             │ │
│  │  - CRUD Operations                                                   │ │
│  │  - Activation Management                                             │ │
│  │  - Conflict Detection                                                │ │
│  └───────────────┬──────────────────────────────────┬─────────────────┘ │
│                  │                                  │                    │
│  ┌───────────────┴─────────────┐  ┌────────────────┴──────────────────┐│
│  │        CronBridge           │  │      Supporting Libraries          ││
│  │  - Pattern → Cron           │  │  - moon_phase.py (local calc)      ││
│  │  - Apply to System          │  │  - solar_time.py (sunset/sunrise)  ││
│  │  - Preview Events           │  │  - schedule_conflict.py            ││
│  └───────────────┬─────────────┘  └──────────────────────────────────┘ │
│                  │                                                       │
│  ┌───────────────┴─────────────────────────────────────────────────────┐│
│  │                      File Storage                                     ││
│  │               CONFIG_DIR/schedules/*.json                             ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Subprocess / File Write
┌─────────────────────────────────┴───────────────────────────────────────┐
│                     Existing Scheduler Infrastructure                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   Scheduler.py   │  │ schedule_settings│  │  /sys/class/rtc/     │  │
│  │  (Cron + RTC)    │  │      .csv        │  │   rtc0/wakealarm     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      GPIO Control Scripts                          │   │
│  │  Attract_On.py, Attract_Off.py, Flash_On.py, FlashOn.py           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
webui/backend/
├── lib/
│   ├── cron_security.py           # [NEW] Shared whitelist & validation (refactored)
│   ├── schedule_schema.py         # Data classes, validation
│   ├── schedule_storage.py        # JSON file I/O with locking
│   ├── cron_bridge.py             # Pattern → cron translation (uses cron_security)
│   ├── moon_phase.py              # Local moon phase calculation
│   ├── solar_time.py              # Sunrise/sunset calculation
│   ├── schedule_conflict.py       # Conflict detection
│   └── schedule_preset_types.py   # Preset data classes
│
├── services/
│   └── scheduler_service.py       # Main service with LRU cache
│
├── routes/
│   ├── scheduler.py               # [EXISTING] Low-level cron API (uses cron_security)
│   ├── scheduler_ui.py            # [NEW] High-level schedule UI API
│   └── schedule_presets.py        # [NEW] Preset API endpoints
│
├── schedule_preset_manager.py     # Preset file management
│
└── presets_builtin/schedules/     # Built-in preset JSON files

webui/frontend/src/
├── contexts/
│   └── SchedulerContext.jsx       # Schedule state management
│
├── hooks/
│   ├── useSchedules.js            # TanStack Query hooks
│   └── useMoonPhases.js           # Moon phase data hook
│
├── pages/
│   └── SchedulerUI.jsx            # Main scheduler page
│
└── components/scheduler/
    ├── CalendarView/              # Calendar display components
    ├── ScheduleList/              # Schedule list components
    ├── EventEditor/               # Event editing drawer
    ├── PatternBuilder/            # Time pattern forms
    ├── ConflictResolver/          # Conflict UI components
    ├── ExpertMode/                # Raw cron editing
    └── Preview/                   # Schedule preview components
```

### Data Flow

```
User creates schedule via CalendarView
    ↓
SchedulerContext.dispatch(ADD_EVENT)
    ↓
User clicks "Save Schedule"
    ↓
useCreateSchedule.mutate(scheduleData)
    ↓
POST /api/scheduler/ui/schedules
    ↓
SchedulerService.create_schedule()
    ↓
schedule_storage.write_schedule() → CONFIG_DIR/schedules/{id}.json
    ↓
Response: 201 Created + schedule object

User clicks "Activate"
    ↓
useActivateSchedule.mutate(scheduleId)
    ↓
POST /api/scheduler/ui/schedules/{id}/activate
    ↓
SchedulerService.activate_schedule()
    ├── Deactivate any currently active schedule
    ├── Validate schedule (conflict check)
    ├── CronBridge.apply_to_system()
    │   ├── Write to schedule_settings.csv
    │   ├── Set RTC wakealarm (Pi 5) or PiJuice alarm (Pi 4)
    │   └── Optionally create deployment metadata
    └── Mark schedule as active

System wakes at scheduled time
    ↓
Scheduler.py runs on boot
    ↓
GPIO scripts execute (Attract_On.py, etc.)
    ↓
TakePhoto.py captures images
    ↓
System shuts down, RTC alarm set for next wakeup
```

---

## Integration Points

### Backend Services

#### DeploymentService (for deployment linkage)

**File**: `webui/backend/services/deployment_service.py`
**Integration**: When activating a schedule with `create_deployment: true`, create deployment metadata.

**Relevant code** (lines 250-280):
```python
def create_deployment_metadata(
    self,
    directory: str,
    metadata: DeploymentMetadata
) -> DeploymentMetadata:
    """Create new deployment metadata for a directory."""
    normalized = self._normalize_path(directory)

    # Validate and write
    with self._cache_lock:
        write_deployment_metadata(normalized, metadata)
        self._cache[normalized] = (metadata, time.time())
        self._total_writes += 1

    return metadata
```

**Extension pattern** for scheduler:
```python
# In scheduler_service.py
def activate_schedule(self, schedule_id: str) -> tuple[bool, str]:
    schedule = self.get_schedule(schedule_id)

    if schedule.create_deployment:
        deployment_service = get_deployment_service()
        deployment = DeploymentMetadata(
            deployment_name=schedule.name,
            created_at=datetime.now().isoformat(),
            # ... populate from schedule
        )
        deployment_service.create_deployment_metadata(
            PHOTOS_DIR,
            deployment
        )
```

#### Existing Scheduler.py (cron/RTC integration)

**File**: `5.x/Scheduler.py`
**Integration**: CronBridge uses same cron expression format and RTC interface.

**Cron expression building** (lines 894-909):
```python
# Loop through each key-value pair in the dictionary
for key, value in settings.items():
    # Check if the value is a string and contains semicolons
    if isinstance(value, str) and ";" in value:
        # Replace semicolons with commas
        settings[key] = value.replace(";", ",")
cron_expression = (
    str(settings["minute"])
    + " "
    + str(settings["hour"])
    + " "
    + "*"
    + " "
    + "*"
    + " "
    + str(settings["weekday"])
)
```

**RTC alarm setting** (lines 702-716):
```python
def set_wakeup_alarm(epoch_time):
    """
    Sets the wakeup alarm for the Raspberry Pi using /sys/class/rtc/rtc0/wakealarm.
    """
    # Open the wakealarm file for writing
    with open("/sys/class/rtc/rtc0/wakealarm", "w") as f:
        # Write the epoch time in seconds
        f.write(str(epoch_time))
    logging.info("Set the Wakeup Alarm" + str(epoch_time))
    # Write to controls here!
    set_nextWakeinControls(str(CONTROLS_FILE), epoch_time)
```

**Extension pattern** for CronBridge:
```python
# In cron_bridge.py
class CronBridge:
    def apply_to_system(self, schedule: Schedule) -> bool:
        """Write schedule to system (cron + RTC)."""
        # Build schedule_settings.csv content
        csv_data = self._schedule_to_csv(schedule)

        # Write CSV
        with open(SCHEDULE_SETTINGS_FILE, 'w') as f:
            f.write(csv_data)

        # Calculate next wakeup and set RTC
        cron_expr = self._get_next_cron_expression(schedule)
        next_epoch = calculate_next_event(cron_expr)

        # Clear and set alarm (reuse Scheduler.py patterns)
        clear_wakeup_alarm()
        set_wakeup_alarm(next_epoch)

        return True
```

### API Routes

#### Deployment Routes Blueprint

**File**: `webui/backend/routes/deployment.py`
**Pattern to follow** (lines 50-90):

```python
deployment_bp = Blueprint("deployment", __name__)

@deployment_bp.route("/metadata/<path:directory>", methods=["GET"])
def get_deployment_metadata(directory: str):
    """Get deployment metadata for a directory."""
    try:
        # Path validation
        validate_photo_path(directory)

        # Service call
        service = get_deployment_service()
        metadata = service.get_deployment_metadata(directory)

        if metadata is None:
            return jsonify({"error": "Not found"}), 404

        return jsonify(metadata.to_dict()), 200

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": "Internal error"}), 500

@deployment_bp.route("/metadata/<path:directory>", methods=["PUT"])
def create_deployment_metadata(directory: str):
    """Create or replace deployment metadata."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate input
        valid, error = _validate_deployment_input(data)
        if not valid:
            return jsonify({"error": error}), 400

        # Create metadata
        service = get_deployment_service()
        metadata = service.set_deployment_metadata(directory, data)

        return jsonify(metadata.to_dict()), 201

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": "Internal error"}), 500
```

### Frontend Hooks

#### useExportJobs (polling pattern)

**File**: `webui/frontend/src/hooks/useExportJobs.js`
**Pattern** (lines 30-60):

```javascript
export function useExportJob(jobId) {
  return useQuery({
    queryKey: QUERY_KEYS.EXPORT_JOB(jobId),
    queryFn: async () => {
      const response = await getExportJob(jobId)
      return response.data
    },
    enabled: !!jobId,
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Poll while active
      if (status === 'pending' || status === 'running') return 5000
      return false
    },
    refetchIntervalInBackground: false,
  })
}
```

**Apply to scheduler** for preview polling:
```javascript
// In useSchedules.js
export function useSchedulePreview(scheduleId, days = 7) {
  return useQuery({
    queryKey: QUERY_KEYS.SCHEDULE_PREVIEW(scheduleId, days),
    queryFn: async () => {
      const response = await api.get(
        `/scheduler/v2/schedules/${scheduleId}/preview`,
        { params: { days } }
      )
      return response.data
    },
    enabled: !!scheduleId,
    staleTime: 60000, // 1 minute (preview doesn't change often)
  })
}
```

### Configuration

**Files to modify**:
- `mothbox_paths.py`: Add `SCHEDULES_DIR = CONFIG_DIR / "schedules"`
- `webui/backend/constants.py`: Add scheduler constants

```python
# In mothbox_paths.py
SCHEDULES_DIR = CONFIG_DIR / "schedules"

# In constants.py
SCHEDULE_CACHE_TTL_SECONDS: Final[int] = 300
SCHEDULE_MAX_EVENTS: Final[int] = 100
SCHEDULE_MAX_ACTIONS_PER_EVENT: Final[int] = 10
SCHEDULE_PREVIEW_MAX_DAYS: Final[int] = 90
```

---

## Implementation Guide

### Step 0: Refactor - Extract Cron Security Library

**Before building new features**, extract reusable code from existing `scheduler.py` into a shared library. This enables both the existing low-level cron API and the new high-level scheduler to share security code.

**Existing code** (`webui/backend/routes/scheduler.py`, lines 14-21):
```python
# Currently embedded in routes file - needs extraction
ALLOWED_SCRIPTS = {
    "takephoto": "TakePhoto.py",
    "scheduler": "Scheduler.py",
    "backup": "Backup_Files.py",
    "attract_on": "Attract_On.py",
    "attract_off": "Attract_Off.py",
    "flash_on": "FlashOn.py",
}
```

**Create file**: `webui/backend/lib/cron_security.py`

```python
"""
Cron job security utilities.

Provides whitelist-based validation for schedulable scripts,
preventing command injection attacks. Used by both:
- routes/scheduler.py (low-level cron API)
- routes/scheduler_ui.py (high-level schedule API)
"""

from typing import Final
from mothbox_paths import get_script_path

# Whitelist of allowed Mothbox scripts
# Maps friendly keys to script filenames
ALLOWED_SCRIPTS: Final[dict[str, str]] = {
    # Photo capture
    "takephoto": "TakePhoto.py",

    # Scheduling
    "scheduler": "Scheduler.py",

    # Data management
    "backup": "Backup_Files.py",

    # GPIO control - Attraction lights
    "attract_on": "Attract_On.py",
    "attract_off": "Attract_Off.py",

    # GPIO control - Flash
    "flash_on": "FlashOn.py",
    "flash_off": "Flash_Off.py",

    # GPS
    "gps_sync": "GPS.py",

    # Display
    "update_display": "UpdateDisplay.py",

    # Debug/maintenance
    "debug_mode": "DebugMode.py",
    "stop_cron": "StopCron.py",
    "start_cron": "StartCron.py",
}

# Action type to script key mapping (for schedule actions)
ACTION_TYPE_SCRIPTS: Final[dict[str, dict[str, str]]] = {
    "gpio": {
        "attract_on": "attract_on",
        "attract_off": "attract_off",
        "flash_on": "flash_on",
        "flash_off": "flash_off",
    },
    "camera": {
        "takephoto": "takephoto",
    },
    "gps_sync": {
        "sync": "gps_sync",
    },
    "service": {
        "backup": "backup",
        "update_display": "update_display",
    },
}


def get_allowed_script_keys() -> list[str]:
    """Get list of all allowed script keys."""
    return list(ALLOWED_SCRIPTS.keys())


def validate_script_key(script_key: str) -> tuple[bool, str | None]:
    """
    Validate script key against whitelist.

    Args:
        script_key: The script key to validate

    Returns:
        (True, None) if valid
        (False, error_message) if invalid
    """
    if script_key not in ALLOWED_SCRIPTS:
        allowed = ", ".join(ALLOWED_SCRIPTS.keys())
        return False, f"Invalid script_key '{script_key}'. Allowed: {allowed}"
    return True, None


def get_script_filename(script_key: str) -> str | None:
    """Get the filename for a script key."""
    return ALLOWED_SCRIPTS.get(script_key)


def get_validated_script_path(script_key: str) -> str:
    """
    Get validated full path for a script key.

    Raises:
        ValueError: If script_key is not in whitelist
    """
    valid, error = validate_script_key(script_key)
    if not valid:
        raise ValueError(error)

    script_name = ALLOWED_SCRIPTS[script_key]
    return str(get_script_path(script_name))


def get_validated_command(script_key: str) -> str:
    """
    Get validated command string for a script key.

    Returns:
        Full command string (e.g., "/usr/bin/python3 /path/to/script.py")

    Raises:
        ValueError: If script_key is not in whitelist
    """
    script_path = get_validated_script_path(script_key)
    return f"/usr/bin/python3 {script_path}"


def get_script_key_for_action(action_type: str, action_name: str) -> str | None:
    """
    Get the script key for a schedule action.

    Args:
        action_type: Action type ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action name ("attract_on", "takephoto", etc.)

    Returns:
        Script key if found, None otherwise
    """
    type_scripts = ACTION_TYPE_SCRIPTS.get(action_type, {})
    return type_scripts.get(action_name)


def is_mothbox_command(command: str) -> bool:
    """
    Check if a command string appears to be a Mothbox job.
    Used for safe deletion of cron jobs.
    """
    from mothbox_paths import MOTHBOX_HOME

    indicators = [
        "mothbox" in command.lower(),
        "TakePhoto" in command,
        str(MOTHBOX_HOME) in command,
    ]
    return any(indicators)
```

**Then update existing `scheduler.py`** to import from shared library:

```python
# webui/backend/routes/scheduler.py - Updated imports
from webui.backend.lib.cron_security import (
    ALLOWED_SCRIPTS,
    validate_script_key,
    get_validated_command,
    is_mothbox_command,
)

# Remove the local ALLOWED_SCRIPTS dict and use imported version
# Update add_cron_job() to use validate_script_key() and get_validated_command()
# Update delete_cron_job() to use is_mothbox_command()
```

**Benefits of this refactoring:**
- Security code shared between both APIs
- Expanded whitelist with additional scripts (GPS, display, etc.)
- `ACTION_TYPE_SCRIPTS` mapping for schedule action → script translation
- Backward compatible (existing `/api/scheduler/*` routes keep working)
- Foundation for `cron_bridge.py` to build upon

---

### Step 1: Schedule Schema

**Create file**: `webui/backend/lib/schedule_schema.py`

**Follow pattern from**: `webui/backend/lib/deployment_schema.py`

The schema uses a **two-tier conceptual model** with **single-file storage**:
- **Event Patterns**: Reusable action sequences with relative timing (embedded in schedule)
- **Schedule**: Contains patterns + trigger configuration + date constraints

```python
"""
Schedule data structures and validation.

This module defines the schema for Mothbox schedules:
- EventPattern: Reusable action sequences with relative timing
- Schedule: Complete schedule with embedded patterns (single-file storage)

Schema version 2.0 introduces single-file storage for portability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Final
import uuid

# Schema version
SCHEDULE_SCHEMA_VERSION: Final[str] = "2.0"
SUPPORTED_VERSIONS: Final[list[str]] = ["2.0"]

# Validation limits
MAX_PATTERN_NAME_LENGTH: Final[int] = 200
MAX_DESCRIPTION_LENGTH: Final[int] = 2000
MAX_ACTIONS_PER_PATTERN: Final[int] = 20
MAX_PATTERNS_PER_SCHEDULE: Final[int] = 10
MAX_OFFSET_MINUTES: Final[int] = 1440  # 24 hours

# Action types
class ActionType(str, Enum):
    GPIO = "gpio"
    CAMERA = "camera"
    GPS_SYNC = "gps_sync"
    SERVICE = "service"

ACTION_TYPES: Final[list[str]] = [e.value for e in ActionType]

# GPIO action names
GPIO_ACTIONS: Final[list[str]] = [
    "attract_on", "attract_off",
    "flash_on", "flash_off",
    "uv_on", "uv_off"
]

# Trigger types (note: "sensor" removed - sensors are now pre-conditions, not triggers)
TRIGGER_TYPES: Final[list[str]] = [
    "interval", "solar", "moon_phase", "fixed_time"
]

# Moon phases
MOON_PHASES: Final[list[str]] = [
    "new", "waxing_crescent", "first_quarter", "waxing_gibbous",
    "full", "waning_gibbous", "last_quarter", "waning_crescent"
]

# Twilight types (from astral library)
TWILIGHT_TYPES: Final[list[str]] = ["civil", "nautical", "astronomical"]

# Solar events supported in time_spec (via astral)
SOLAR_EVENTS: Final[list[str]] = [
    "dawn", "sunrise", "noon", "sunset", "dusk",
    "civil_dawn", "civil_dusk",
    "nautical_dawn", "nautical_dusk",
    "astronomical_dawn", "astronomical_dusk",
    "golden_hour_start", "golden_hour_end",
    "blue_hour_start", "blue_hour_end",
]

# Sensor types for sensor pre-conditions (I2C sensors only, no GPIO)
SENSOR_TYPES: Final[list[str]] = ["light", "temperature"]
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]


class ScheduleValidationError(Exception):
    """Raised when schedule validation fails."""
    pass


# =============================================================================
# TIER 1: EVENT PATTERNS (Reusable Action Sequences)
# =============================================================================

@dataclass
class PatternAction:
    """
    A single action within an event pattern.

    Actions use relative offsets from pattern start (t=0), enabling
    coordinated multi-action sequences like:
    - UV_ON at t+0
    - TakePhoto at t+5
    - UV_OFF at t+15

    Attributes:
        action_type: Category ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action ("uv_on", "takephoto", etc.)
        offset_minutes: Minutes from pattern start (t=0). Default 0.
        parameters: Action-specific configuration
        description: Human-readable description
    """
    action_type: str
    action_name: str
    offset_minutes: int = 0
    parameters: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "offset_minutes": self.offset_minutes,
            "parameters": self.parameters,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternAction":
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
        )


@dataclass
class EventPattern:
    """
    Reusable template defining a sequence of timed actions.

    Event patterns are library items that can be reused across multiple
    schedules. Actions use relative offsets from pattern start (t=0).

    Example: "UV Capture Cycle"
    - UV_ON at offset +0 minutes
    - TakePhoto at offset +5 minutes
    - UV_OFF at offset +15 minutes
    - duration_minutes = 15 (computed from max offset)

    Attributes:
        pattern_id: Unique identifier (UUID)
        name: Human-readable name
        description: Detailed description
        actions: Ordered list of actions with offsets
        category: "built-in" or "user"
        tags: Tags for filtering/search
    """
    pattern_id: str
    name: str
    description: str
    actions: list[PatternAction]
    category: str = "user"  # "built-in" or "user"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.pattern_id:
            self.pattern_id = str(uuid.uuid4())

    @property
    def duration_minutes(self) -> int:
        """Total duration = max action offset."""
        return max(a.offset_minutes for a in self.actions) if self.actions else 0

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "category": self.category,
            "tags": self.tags,
            "duration_minutes": self.duration_minutes,  # Computed, read-only
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventPattern":
        return cls(
            pattern_id=data.get("pattern_id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            actions=[PatternAction.from_dict(a) for a in data.get("actions", [])],
            category=data.get("category", "user"),
            tags=data.get("tags", []),
        )


# =============================================================================
# TIER 2: SCHEDULE PATTERNS (When Event Patterns Run)
# =============================================================================

@dataclass
class TimeWindow:
    """
    Daily time window for pattern execution.

    Supports both fixed times ("HH:MM") and solar events ("sunset").

    Attributes:
        start_time: Window start ("HH:MM" or solar event)
        end_time: Window end ("HH:MM" or solar event)
        start_offset_minutes: Offset if start_time is solar
        end_offset_minutes: Offset if end_time is solar
    """
    start_time: str  # "HH:MM" or solar event
    end_time: str    # "HH:MM" or solar event
    start_offset_minutes: int = 0
    end_offset_minutes: int = 0

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_offset_minutes": self.start_offset_minutes,
            "end_offset_minutes": self.end_offset_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeWindow":
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            start_offset_minutes=data.get("start_offset_minutes", 0),
            end_offset_minutes=data.get("end_offset_minutes", 0),
        )


@dataclass
class IntervalTrigger:
    """
    Execute pattern every N minutes within time window.

    Example: Every 60 minutes from 01:00 to 06:00

    Attributes:
        interval_minutes: Interval in minutes (e.g., 60 = hourly)
        time_window: When executions can occur
        days_of_week: 0=Mon..6=Sun, None=every day
    """
    interval_minutes: int
    time_window: TimeWindow
    days_of_week: list[int] | None = None

    def to_dict(self) -> dict:
        return {
            "interval_minutes": self.interval_minutes,
            "time_window": self.time_window.to_dict(),
            "days_of_week": self.days_of_week,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntervalTrigger":
        return cls(
            interval_minutes=data["interval_minutes"],
            time_window=TimeWindow.from_dict(data["time_window"]),
            days_of_week=data.get("days_of_week"),
        )


@dataclass
class SolarTrigger:
    """
    Execute pattern relative to solar event.

    Example: At sunset+30 every day

    Attributes:
        solar_event: Event name ("sunset", "astronomical_dusk", etc.)
        offset_minutes: +/- minutes from event
        days_of_week: 0=Mon..6=Sun, None=every day
    """
    solar_event: str
    offset_minutes: int = 0
    days_of_week: list[int] | None = None

    def to_dict(self) -> dict:
        return {
            "solar_event": self.solar_event,
            "offset_minutes": self.offset_minutes,
            "days_of_week": self.days_of_week,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SolarTrigger":
        return cls(
            solar_event=data["solar_event"],
            offset_minutes=data.get("offset_minutes", 0),
            days_of_week=data.get("days_of_week"),
        )


@dataclass
class MoonPhaseTrigger:
    """
    Execute pattern on moon phases.

    Example: On full moon ±2 days, from dusk to dawn

    Attributes:
        phases: List of phases to match (["full", "new"])
        offset_days: +/- days from exact phase
        time_window: Optional execution window on phase days
    """
    phases: list[str]
    offset_days: int = 0
    time_window: TimeWindow | None = None

    def to_dict(self) -> dict:
        return {
            "phases": self.phases,
            "offset_days": self.offset_days,
            "time_window": self.time_window.to_dict() if self.time_window else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoonPhaseTrigger":
        return cls(
            phases=data["phases"],
            offset_days=data.get("offset_days", 0),
            time_window=TimeWindow.from_dict(data["time_window"]) if data.get("time_window") else None,
        )


@dataclass
class SensorPrecondition:
    """
    Pre-condition check based on sensor readings.

    Evaluated at scheduled capture time - NOT real-time triggers.
    If pre-condition fails, capture is skipped (with logging).

    Supported sensors (I2C only):
    - "light": BH1750/LTR303 lux sensor, check ambient light
    - "temperature": TMP102/MCP9808 temp sensor, check ambient temperature

    Example use case:
    "Capture every hour, but only if light < 100 lux"

    Attributes:
        sensor_type: Sensor type ("light", "temperature")
        threshold: Value to compare against
        comparison: Comparison operator ("gt", "lt", "eq", "gte", "lte")
    """
    sensor_type: str
    threshold: float = 0.0
    comparison: str = "lt"  # Default "less than" for light threshold

    def to_dict(self) -> dict:
        return {
            "sensor_type": self.sensor_type,
            "threshold": self.threshold,
            "comparison": self.comparison,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SensorPrecondition":
        return cls(
            sensor_type=data["sensor_type"],
            threshold=data.get("threshold", 0.0),
            comparison=data.get("comparison", "lt"),
        )


@dataclass
class Schedule:
    """
    Complete schedule with embedded event patterns (single-file storage).

    Each schedule is fully self-contained with event patterns embedded inline,
    making it portable and easy to export/import between Mothbox units.

    Attributes:
        schedule_id: Unique identifier (UUID)
        name: Human-readable name
        description: Detailed description
        event_patterns: Embedded EventPattern objects (not references)
        trigger_type: Type of trigger ("interval", "solar", "moon_phase", "fixed_time")
        interval_trigger: Config for interval triggers
        solar_trigger: Config for solar triggers
        moon_phase_trigger: Config for moon phase triggers
        fixed_time_trigger: Config for fixed time triggers
        preconditions: Optional sensor pre-conditions (checked at capture time)
        start_date: Start of schedule validity (ISO 8601)
        end_date: End of schedule validity (ISO 8601)
        deployment_id: Linked deployment
        create_deployment: Create deployment on activation
        enabled: Whether schedule is enabled
        is_active: Whether schedule is currently active
    """
    schedule_id: str
    name: str
    description: str
    event_patterns: list[EventPattern]  # Embedded patterns, not references
    trigger_type: str  # "interval", "solar", "moon_phase", "fixed_time"

    # Trigger configs (one active based on trigger_type)
    interval_trigger: IntervalTrigger | None = None
    solar_trigger: SolarTrigger | None = None
    moon_phase_trigger: MoonPhaseTrigger | None = None
    fixed_time_trigger: FixedTimeTrigger | None = None

    # Sensor pre-conditions (optional, checked at capture time)
    preconditions: list[SensorPrecondition] | None = None

    # Date constraints
    start_date: str | None = None
    end_date: str | None = None

    # Deployment linkage
    deployment_id: str | None = None
    create_deployment: bool = False

    # State
    enabled: bool = True
    is_active: bool = False

    # Metadata
    created_at: str = ""
    modified_at: str = ""
    modified_by: str | None = None

    def __post_init__(self):
        if not self.schedule_id:
            self.schedule_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at

    @property
    def total_duration_minutes(self) -> int:
        """Total duration of all event patterns combined."""
        return sum(p.duration_minutes for p in self.event_patterns)

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "event_patterns": [p.to_dict() for p in self.event_patterns],
            "trigger_type": self.trigger_type,
            "interval_trigger": self.interval_trigger.to_dict() if self.interval_trigger else None,
            "solar_trigger": self.solar_trigger.to_dict() if self.solar_trigger else None,
            "moon_phase_trigger": self.moon_phase_trigger.to_dict() if self.moon_phase_trigger else None,
            "fixed_time_trigger": self.fixed_time_trigger.to_dict() if self.fixed_time_trigger else None,
            "preconditions": [p.to_dict() for p in self.preconditions] if self.preconditions else None,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "deployment_id": self.deployment_id,
            "create_deployment": self.create_deployment,
            "enabled": self.enabled,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "modified_by": self.modified_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            schedule_id=data.get("schedule_id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            event_patterns=[EventPattern.from_dict(p) for p in data.get("event_patterns", [])],
            trigger_type=data["trigger_type"],
            interval_trigger=IntervalTrigger.from_dict(data["interval_trigger"]) if data.get("interval_trigger") else None,
            solar_trigger=SolarTrigger.from_dict(data["solar_trigger"]) if data.get("solar_trigger") else None,
            moon_phase_trigger=MoonPhaseTrigger.from_dict(data["moon_phase_trigger"]) if data.get("moon_phase_trigger") else None,
            fixed_time_trigger=FixedTimeTrigger.from_dict(data["fixed_time_trigger"]) if data.get("fixed_time_trigger") else None,
            preconditions=[SensorPrecondition.from_dict(p) for p in data["preconditions"]] if data.get("preconditions") else None,
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            deployment_id=data.get("deployment_id"),
            create_deployment=data.get("create_deployment", False),
            enabled=data.get("enabled", True),
            is_active=data.get("is_active", False),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            modified_by=data.get("modified_by"),
        )


# =============================================================================
# VALIDATION
# =============================================================================

def validate_event_pattern(pattern: EventPattern) -> tuple[bool, str | None]:
    """Validate an event pattern."""
    if not pattern.name:
        return False, "Pattern name is required"
    if len(pattern.name) > MAX_PATTERN_NAME_LENGTH:
        return False, f"Pattern name exceeds {MAX_PATTERN_NAME_LENGTH} characters"

    if len(pattern.actions) == 0:
        return False, "Pattern must have at least one action"
    if len(pattern.actions) > MAX_ACTIONS_PER_PATTERN:
        return False, f"Pattern exceeds {MAX_ACTIONS_PER_PATTERN} actions"

    for action in pattern.actions:
        valid, error = _validate_action(action)
        if not valid:
            return False, error

    return True, None


def validate_schedule(schedule: Schedule) -> tuple[bool, str | None]:
    """Validate a complete schedule with embedded patterns."""
    if not schedule.name:
        return False, "Schedule name is required"
    if len(schedule.name) > MAX_PATTERN_NAME_LENGTH:
        return False, f"Schedule name exceeds {MAX_PATTERN_NAME_LENGTH} characters"

    if not schedule.event_patterns:
        return False, "Schedule must have at least one event pattern"
    if len(schedule.event_patterns) > MAX_PATTERNS_PER_SCHEDULE:
        return False, f"Schedule exceeds {MAX_PATTERNS_PER_SCHEDULE} event patterns"

    # Validate each embedded pattern
    for pattern in schedule.event_patterns:
        valid, error = validate_event_pattern(pattern)
        if not valid:
            return False, f"Invalid pattern '{pattern.name}': {error}"

    if schedule.trigger_type not in TRIGGER_TYPES:
        return False, f"Invalid trigger type: {schedule.trigger_type}"

    # Validate trigger-specific config
    if schedule.trigger_type == "interval" and not schedule.interval_trigger:
        return False, "Interval trigger requires interval_trigger config"
    if schedule.trigger_type == "solar" and not schedule.solar_trigger:
        return False, "Solar trigger requires solar_trigger config"
    if schedule.trigger_type == "moon_phase" and not schedule.moon_phase_trigger:
        return False, "Moon phase trigger requires moon_phase_trigger config"
    if schedule.trigger_type == "fixed_time" and not schedule.fixed_time_trigger:
        return False, "Fixed time trigger requires fixed_time_trigger config"

    # Validate pre-conditions if present (optional for any trigger type)
    if schedule.preconditions:
        for precondition in schedule.preconditions:
            if precondition.sensor_type not in SENSOR_TYPES:
                return False, f"Invalid sensor type: {precondition.sensor_type}"
            if precondition.comparison not in SENSOR_COMPARISONS:
                return False, f"Invalid comparison: {precondition.comparison}"

    return True, None


def _validate_action(action: PatternAction) -> tuple[bool, str | None]:
    """Validate a single action."""
    if action.action_type not in ACTION_TYPES:
        return False, f"Invalid action type: {action.action_type}"

    if action.offset_minutes < 0:
        return False, "Action offset cannot be negative"
    if action.offset_minutes > MAX_OFFSET_MINUTES:
        return False, f"Action offset exceeds {MAX_OFFSET_MINUTES} minutes"

    return True, None
```

**Key implementation notes**:
- Use dataclasses for clean serialization
- Include `to_dict()` and `from_dict()` for JSON conversion
- Validation returns (bool, error_message) tuple pattern
- Constants at module level for easy configuration

### Step 2: Astronomical Calculations (using `astral`)

**External dependency**: `astral>=3.2` (add to `requirements.txt`)

The `astral` library provides accurate sun/moon calculations with ±1 minute precision for solar times.

#### Moon Phase Calculator

**Create file**: `webui/backend/lib/moon_phase.py`

```python
"""
Moon phase calculations using the astral library.

Provides moon phase detection, moonrise/moonset times, and phase searching
for scheduling triggers based on lunar conditions.

External dependency: astral>=3.2
"""

from datetime import date, datetime, timedelta
from typing import Final

from astral import moon
from astral import LocationInfo
from astral.moon import moonrise, moonset

# Phase value ranges (astral returns 0-27.99)
# 0 = new moon, 7 = first quarter, 14 = full moon, 21 = last quarter
PHASE_RANGES: Final[list[tuple[str, float, float]]] = [
    ("new", 0, 1.85),
    ("waxing_crescent", 1.85, 7.38),
    ("first_quarter", 7.38, 11.07),
    ("waxing_gibbous", 11.07, 14.77),
    ("full", 14.77, 18.46),
    ("waning_gibbous", 18.46, 22.15),
    ("last_quarter", 22.15, 25.84),
    ("waning_crescent", 25.84, 27.99),
]

# Human-readable phase names
PHASE_NAMES: Final[dict[str, str]] = {
    "new": "New Moon",
    "waxing_crescent": "Waxing Crescent",
    "first_quarter": "First Quarter",
    "waxing_gibbous": "Waxing Gibbous",
    "full": "Full Moon",
    "waning_gibbous": "Waning Gibbous",
    "last_quarter": "Last Quarter",
    "waning_crescent": "Waning Crescent",
}


def get_moon_phase(target_date: date) -> dict:
    """
    Get moon phase information for a specific date.

    Args:
        target_date: The date to get moon phase for

    Returns:
        Dict with:
        - date: ISO 8601 date string
        - phase: str (e.g., "full", "new", "first_quarter")
        - phase_name: Human-readable name
        - phase_value: float (0-27.99, astral raw value)
        - illumination: float (0.0 to 1.0, approximate)
    """
    # Get astral phase value (0-27.99)
    phase_value = moon.phase(target_date)

    # Determine phase name from ranges
    phase = "new"  # default
    for phase_name, start, end in PHASE_RANGES:
        if start <= phase_value < end:
            phase = phase_name
            break
    # Handle wrap-around for values very close to 28
    if phase_value >= 27.99:
        phase = "new"

    # Approximate illumination from phase value
    # 0 and 28 = new (0%), 14 = full (100%)
    import math
    illumination = (1 - math.cos(math.pi * phase_value / 14)) / 2

    return {
        "date": target_date.isoformat(),
        "phase": phase,
        "phase_name": PHASE_NAMES[phase],
        "phase_value": round(phase_value, 2),
        "illumination": round(illumination, 3),
    }


def get_moon_times(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> dict:
    """
    Get moonrise and moonset times for a location.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name (e.g., "America/New_York")

    Returns:
        Dict with moonrise and moonset times (or None if moon doesn't rise/set)
    """
    location = LocationInfo(
        name="Observer",
        region="",
        timezone=timezone_name,
        latitude=latitude,
        longitude=longitude,
    )

    rise_time = None
    set_time = None

    try:
        rise_time = moonrise(location.observer, target_date)
    except ValueError:
        pass  # Moon doesn't rise on this date at this location

    try:
        set_time = moonset(location.observer, target_date)
    except ValueError:
        pass  # Moon doesn't set on this date at this location

    return {
        "date": target_date.isoformat(),
        "moonrise": rise_time.isoformat() if rise_time else None,
        "moonset": set_time.isoformat() if set_time else None,
    }


def get_moon_phases_for_range(start_date: date, end_date: date) -> list[dict]:
    """
    Get moon phases for a date range.

    Args:
        start_date: Start of range
        end_date: End of range

    Returns:
        List of moon phase dicts for each day
    """
    phases = []
    current = start_date
    while current <= end_date:
        phases.append(get_moon_phase(current))
        current += timedelta(days=1)
    return phases


def get_significant_phases_for_range(start_date: date, end_date: date) -> list[dict]:
    """
    Get only significant moon phases (new, first quarter, full, last quarter).

    Args:
        start_date: Start of range
        end_date: End of range

    Returns:
        List of significant phase events (phase transitions only)
    """
    significant = ["new", "first_quarter", "full", "last_quarter"]
    all_phases = get_moon_phases_for_range(start_date, end_date)

    result = []
    prev_phase = None

    for phase_info in all_phases:
        phase = phase_info["phase"]
        if phase in significant and phase != prev_phase:
            result.append(phase_info)
        prev_phase = phase

    return result


def next_moon_phase(target_phase: str, from_date: date) -> date:
    """
    Find the next occurrence of a specific moon phase.

    Args:
        target_phase: The phase to find ("full", "new", etc.)
        from_date: Start searching from this date

    Returns:
        Date of next occurrence of the target phase
    """
    current = from_date
    max_days = 60  # Safety limit (2 lunar cycles)

    for _ in range(max_days):
        phase_info = get_moon_phase(current)
        if phase_info["phase"] == target_phase:
            return current
        current += timedelta(days=1)

    # Fallback (should never reach here)
    return from_date + timedelta(days=30)


def is_within_moon_phase(
    target_date: date,
    target_phase: str,
    offset_days: int = 0
) -> bool:
    """
    Check if a date is within range of a moon phase.

    Args:
        target_date: Date to check
        target_phase: Phase to match ("full", "new", etc.)
        offset_days: +/- days from exact phase (default 0)

    Returns:
        True if date matches criteria
    """
    if offset_days == 0:
        return get_moon_phase(target_date)["phase"] == target_phase

    # Check range around target date
    for delta in range(-offset_days, offset_days + 1):
        check_date = target_date + timedelta(days=delta)
        if get_moon_phase(check_date)["phase"] == target_phase:
            return True

    return False
```

#### Solar Time Calculator

**Create file**: `webui/backend/lib/solar_time.py`

```python
"""
Solar time calculations using the astral library.

Provides sunrise, sunset, twilight times, and solar position calculations
for scheduling events relative to sun position.

External dependency: astral>=3.2
"""

from datetime import date, datetime, timedelta, time
from typing import Final
import re

from astral import LocationInfo
from astral.sun import sun, golden_hour, blue_hour, twilight, elevation, azimuth

# Twilight types supported
TWILIGHT_TYPES: Final[list[str]] = ["civil", "nautical", "astronomical"]

# Solar event types
SOLAR_EVENTS: Final[list[str]] = [
    "dawn",
    "sunrise",
    "noon",
    "sunset",
    "dusk",
]

# Time spec pattern: "sunset", "sunset+30", "sunrise-15", "civil_dawn", etc.
TIME_SPEC_PATTERN = re.compile(
    r"^(dawn|sunrise|noon|sunset|dusk|civil_dawn|civil_dusk|"
    r"nautical_dawn|nautical_dusk|astronomical_dawn|astronomical_dusk|"
    r"golden_hour_start|golden_hour_end|blue_hour_start|blue_hour_end)"
    r"([+-]\d+)?$"
)


def get_observer(
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
    elevation_m: float = 0
) -> LocationInfo:
    """
    Create an astral LocationInfo observer.

    Args:
        latitude: Observer latitude (-90 to 90)
        longitude: Observer longitude (-180 to 180)
        timezone_name: Timezone name (e.g., "America/New_York")
        elevation_m: Elevation in meters (affects sunrise/sunset by ~1 min per 1.5km)

    Returns:
        LocationInfo object for calculations
    """
    return LocationInfo(
        name="Observer",
        region="",
        timezone=timezone_name,
        latitude=latitude,
        longitude=longitude,
    )


def get_sun_times(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> dict:
    """
    Get all sun times for a date and location.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Dict with dawn, sunrise, noon, sunset, dusk times
    """
    location = get_observer(latitude, longitude, timezone_name)
    s = sun(location.observer, date=target_date, tzinfo=location.timezone)

    return {
        "date": target_date.isoformat(),
        "dawn": s["dawn"].isoformat(),
        "sunrise": s["sunrise"].isoformat(),
        "noon": s["noon"].isoformat(),
        "sunset": s["sunset"].isoformat(),
        "dusk": s["dusk"].isoformat(),
    }


def get_twilight_times(
    target_date: date,
    latitude: float,
    longitude: float,
    twilight_type: str = "civil",
    timezone_name: str = "UTC"
) -> dict:
    """
    Get twilight times for a specific twilight type.

    Twilight types:
    - civil: Sun 0° to -6° (reading outdoors possible)
    - nautical: Sun -6° to -12° (horizon visible at sea)
    - astronomical: Sun -12° to -18° (sky fully dark)

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        twilight_type: "civil", "nautical", or "astronomical"
        timezone_name: Timezone name

    Returns:
        Dict with morning and evening twilight start/end times
    """
    if twilight_type not in TWILIGHT_TYPES:
        raise ValueError(f"Invalid twilight type: {twilight_type}. Must be one of {TWILIGHT_TYPES}")

    location = get_observer(latitude, longitude, timezone_name)

    # Map twilight type to sun depression angle
    depression = {"civil": 6, "nautical": 12, "astronomical": 18}[twilight_type]

    # Morning twilight (dawn direction)
    try:
        morning_start, morning_end = twilight(
            location.observer, target_date, direction=1, tzinfo=location.timezone
        )
    except ValueError:
        morning_start = morning_end = None

    # Evening twilight (dusk direction)
    try:
        evening_start, evening_end = twilight(
            location.observer, target_date, direction=-1, tzinfo=location.timezone
        )
    except ValueError:
        evening_start = evening_end = None

    return {
        "date": target_date.isoformat(),
        "twilight_type": twilight_type,
        "morning_start": morning_start.isoformat() if morning_start else None,
        "morning_end": morning_end.isoformat() if morning_end else None,
        "evening_start": evening_start.isoformat() if evening_start else None,
        "evening_end": evening_end.isoformat() if evening_end else None,
    }


def get_golden_hour(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> dict:
    """
    Get golden hour times (sun -4° to +6°).

    Golden hour provides warm, diffused light ideal for photography.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Dict with morning and evening golden hour start/end times
    """
    location = get_observer(latitude, longitude, timezone_name)

    try:
        morning_start, morning_end = golden_hour(
            location.observer, target_date, direction=1, tzinfo=location.timezone
        )
    except ValueError:
        morning_start = morning_end = None

    try:
        evening_start, evening_end = golden_hour(
            location.observer, target_date, direction=-1, tzinfo=location.timezone
        )
    except ValueError:
        evening_start = evening_end = None

    return {
        "date": target_date.isoformat(),
        "morning_start": morning_start.isoformat() if morning_start else None,
        "morning_end": morning_end.isoformat() if morning_end else None,
        "evening_start": evening_start.isoformat() if evening_start else None,
        "evening_end": evening_end.isoformat() if evening_end else None,
    }


def get_blue_hour(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> dict:
    """
    Get blue hour times (sun -6° to -4°).

    Blue hour occurs just before sunrise and just after sunset,
    when the sky has a deep blue color.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Dict with morning and evening blue hour start/end times
    """
    location = get_observer(latitude, longitude, timezone_name)

    try:
        morning_start, morning_end = blue_hour(
            location.observer, target_date, direction=1, tzinfo=location.timezone
        )
    except ValueError:
        morning_start = morning_end = None

    try:
        evening_start, evening_end = blue_hour(
            location.observer, target_date, direction=-1, tzinfo=location.timezone
        )
    except ValueError:
        evening_start = evening_end = None

    return {
        "date": target_date.isoformat(),
        "morning_start": morning_start.isoformat() if morning_start else None,
        "morning_end": morning_end.isoformat() if morning_end else None,
        "evening_start": evening_start.isoformat() if evening_start else None,
        "evening_end": evening_end.isoformat() if evening_end else None,
    }


def parse_time_spec(
    time_spec: str,
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> datetime:
    """
    Parse a time specification string into an actual datetime.

    Supported formats:
    - "HH:MM" - Absolute time (e.g., "19:30")
    - "sunset" - Exact sunset time
    - "sunset+30" - 30 minutes after sunset
    - "sunrise-15" - 15 minutes before sunrise
    - "civil_dusk" - Civil twilight end
    - "nautical_dawn" - Nautical twilight start
    - "astronomical_dusk" - Astronomical twilight end
    - "golden_hour_start" - Start of evening golden hour
    - "blue_hour_end" - End of evening blue hour

    Args:
        time_spec: Time specification string
        target_date: The date for calculation
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Calculated datetime

    Raises:
        ValueError: If time_spec format is invalid
    """
    # Check for absolute time format (HH:MM)
    if re.match(r"^\d{1,2}:\d{2}$", time_spec):
        hours, minutes = map(int, time_spec.split(":"))
        return datetime.combine(target_date, time(hours, minutes))

    # Check for solar event format
    match = TIME_SPEC_PATTERN.match(time_spec.lower())
    if not match:
        raise ValueError(f"Invalid time_spec format: {time_spec}")

    event_name = match.group(1)
    offset_str = match.group(2)
    offset_minutes = int(offset_str) if offset_str else 0

    location = get_observer(latitude, longitude, timezone_name)
    s = sun(location.observer, date=target_date, tzinfo=location.timezone)

    # Map event names to calculated times
    event_times = {
        "dawn": s["dawn"],
        "sunrise": s["sunrise"],
        "noon": s["noon"],
        "sunset": s["sunset"],
        "dusk": s["dusk"],
    }

    # Handle twilight variants
    if "civil" in event_name or "nautical" in event_name or "astronomical" in event_name:
        twilight_type = event_name.split("_")[0]
        direction = 1 if "dawn" in event_name else -1
        try:
            start, end = twilight(
                location.observer, target_date, direction=direction, tzinfo=location.timezone
            )
            event_times[event_name] = start if "dawn" in event_name else end
        except ValueError:
            raise ValueError(f"Cannot calculate {event_name} for this date/location")

    # Handle golden/blue hour
    if "golden_hour" in event_name:
        try:
            start, end = golden_hour(
                location.observer, target_date, direction=-1, tzinfo=location.timezone
            )
            event_times["golden_hour_start"] = start
            event_times["golden_hour_end"] = end
        except ValueError:
            raise ValueError(f"Cannot calculate golden hour for this date/location")

    if "blue_hour" in event_name:
        try:
            start, end = blue_hour(
                location.observer, target_date, direction=-1, tzinfo=location.timezone
            )
            event_times["blue_hour_start"] = start
            event_times["blue_hour_end"] = end
        except ValueError:
            raise ValueError(f"Cannot calculate blue hour for this date/location")

    if event_name not in event_times:
        raise ValueError(f"Unknown solar event: {event_name}")

    base_time = event_times[event_name]
    return base_time + timedelta(minutes=offset_minutes)


def get_daylight_hours(
    target_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC"
) -> float:
    """
    Get the number of daylight hours for a date and location.

    Args:
        target_date: The date to calculate for
        latitude: Observer latitude
        longitude: Observer longitude
        timezone_name: Timezone name

    Returns:
        Daylight hours as a float (e.g., 14.5)
    """
    location = get_observer(latitude, longitude, timezone_name)
    s = sun(location.observer, date=target_date, tzinfo=location.timezone)

    daylight = s["sunset"] - s["sunrise"]
    return daylight.total_seconds() / 3600
```

### Step 2.3: Sensor Reading Library (for Pre-conditions)

**Create file**: `webui/backend/lib/sensor_reader.py`

Provides one-shot I2C sensor reading for pre-condition checks and environmental logging.

```python
"""
Sensor reading library for I2C-based environmental sensors.

Simple one-shot read functions for light and temperature sensors.
Used for:
1. Pre-condition checks at scheduled capture time
2. Environmental logging (recording ambient conditions with photos)

Supported sensors (I2C only):
- light: BH1750 or LTR303 ambient light sensor
- temperature: TMP102 or MCP9808 temperature sensor

NOTE: This is NOT a real-time monitoring daemon. Sensors are read
on-demand at capture time, making it compatible with cron-based
scheduling and power-saving modes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

logger = logging.getLogger(__name__)

# Supported sensor types
SENSOR_TYPES: Final[list[str]] = ["light", "temperature"]

# Comparison operators for pre-conditions
SENSOR_COMPARISONS: Final[list[str]] = ["gt", "lt", "eq", "gte", "lte"]


@dataclass
class SensorReading:
    """A single sensor reading."""
    sensor_type: str
    value: float
    timestamp: datetime
    unit: str  # "lux" or "celsius"


def read_light_sensor() -> float | None:
    """
    Read current lux value from light sensor (BH1750 or LTR303).

    Returns:
        Lux value, or None if sensor unavailable/disabled
    """
    try:
        from mothbox_paths import get_hardware_config

        hw_config = get_hardware_config()

        if not hw_config.get("light_sensor_enabled", False):
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("light_sensor_type", "BH1750")
        address = hw_config.get("light_sensor_address", 0x23)

        with SMBus(1) as bus:
            if sensor_type == "BH1750":
                # BH1750 one-time high resolution mode
                bus.write_byte(address, 0x20)
                import time
                time.sleep(0.2)
                data = bus.read_i2c_block_data(address, 0x00, 2)
                raw_val = (data[0] << 8) | data[1]
                return raw_val / 1.2

            elif sensor_type == "LTR303":
                # LTR303 ambient light sensor
                bus.write_byte_data(address, 0x80, 0x01)
                import time
                time.sleep(0.1)
                ch1_low = bus.read_byte_data(address, 0x88)
                ch1_high = bus.read_byte_data(address, 0x89)
                ch1 = (ch1_high << 8) | ch1_low
                return ch1 * 0.5

            else:
                logger.warning(f"Unknown light sensor type: {sensor_type}")
                return None

    except ImportError:
        logger.debug("smbus2 not available")
        return None
    except Exception as e:
        logger.debug(f"Light sensor read error: {e}")
        return None


def read_temperature_sensor() -> float | None:
    """
    Read current temperature from sensor (TMP102 or MCP9808).

    Returns:
        Temperature in Celsius, or None if sensor unavailable/disabled
    """
    try:
        from mothbox_paths import get_hardware_config

        hw_config = get_hardware_config()

        if not hw_config.get("temperature_sensor_enabled", False):
            return None

        from smbus2 import SMBus

        sensor_type = hw_config.get("temperature_sensor_type", "TMP102")
        address = hw_config.get("temperature_sensor_address", 0x48)

        with SMBus(1) as bus:
            if sensor_type == "TMP102":
                # TMP102 temperature register
                data = bus.read_i2c_block_data(address, 0x00, 2)
                raw = (data[0] << 4) | (data[1] >> 4)
                if raw > 2047:  # Negative temperature
                    raw -= 4096
                return raw * 0.0625

            elif sensor_type == "MCP9808":
                # MCP9808 ambient temperature register
                data = bus.read_i2c_block_data(address, 0x05, 2)
                raw = (data[0] << 8) | data[1]
                raw &= 0x1FFF
                if raw > 4095:  # Negative temperature
                    raw -= 8192
                return raw / 16.0

            else:
                logger.warning(f"Unknown temperature sensor type: {sensor_type}")
                return None

    except ImportError:
        logger.debug("smbus2 not available")
        return None
    except Exception as e:
        logger.debug(f"Temperature sensor read error: {e}")
        return None


def check_precondition(sensor_type: str, threshold: float, comparison: str) -> bool:
    """
    Check if sensor reading meets threshold condition.

    Args:
        sensor_type: "light" or "temperature"
        threshold: Value to compare against
        comparison: "gt", "lt", "eq", "gte", "lte"

    Returns:
        True if condition met, False otherwise (including if sensor unavailable)
    """
    if sensor_type == "light":
        value = read_light_sensor()
    elif sensor_type == "temperature":
        value = read_temperature_sensor()
    else:
        logger.warning(f"Unknown sensor type: {sensor_type}")
        return False

    if value is None:
        logger.debug(f"Sensor {sensor_type} unavailable, precondition fails")
        return False

    comparisons = {
        "gt": value > threshold,
        "lt": value < threshold,
        "eq": abs(value - threshold) < 0.01,
        "gte": value >= threshold,
        "lte": value <= threshold,
    }

    result = comparisons.get(comparison, False)
    logger.debug(f"Precondition check: {sensor_type} {value} {comparison} {threshold} = {result}")
    return result


def get_environmental_readings() -> dict:
    """
    Get current environmental sensor readings for logging.

    Returns dict suitable for embedding in photo metadata.
    """
    return {
        "ambient_light_lux": read_light_sensor(),
        "ambient_temperature_celsius": read_temperature_sensor(),
        "sensor_reading_timestamp": datetime.now().isoformat(),
    }
```

**Sensor Pre-condition Service** (`webui/backend/services/sensor_service.py`):

```python
"""
Sensor service for pre-condition evaluation.

Evaluates sensor thresholds at scheduled capture time.
NOT a real-time monitoring daemon - reads sensors on-demand.
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock

from webui.backend.lib.sensor_reader import (
    read_light_sensor,
    read_temperature_sensor,
    check_precondition,
    SensorReading,
)
from webui.backend.lib.schedule_schema import SensorPrecondition

logger = logging.getLogger(__name__)


@dataclass
class PreconditionResult:
    """Result of evaluating a pre-condition."""
    precondition: SensorPrecondition
    reading_value: float | None
    passed: bool
    timestamp: datetime
    reason: str  # "passed", "failed", "sensor_unavailable"


class SensorService:
    """
    Service for evaluating sensor pre-conditions.

    Called at scheduled capture time to check if conditions are met.
    """

    def __init__(self):
        self._evaluation_history: deque[PreconditionResult] = deque(maxlen=100)
        self._lock = RLock()

    def evaluate_preconditions(self, preconditions: list[SensorPrecondition]) -> bool:
        """
        Evaluate all pre-conditions.

        Args:
            preconditions: List of sensor pre-conditions to check

        Returns:
            True if ALL conditions pass, False if any fail
        """
        if not preconditions:
            return True

        for precondition in preconditions:
            result = self._evaluate_single(precondition)
            with self._lock:
                self._evaluation_history.append(result)

            if not result.passed:
                logger.info(
                    f"Pre-condition failed: {precondition.sensor_type} "
                    f"{precondition.comparison} {precondition.threshold} "
                    f"(actual: {result.reading_value}, reason: {result.reason})"
                )
                return False

        return True

    def _evaluate_single(self, precondition: SensorPrecondition) -> PreconditionResult:
        """Evaluate a single pre-condition."""
        # Read current sensor value
        if precondition.sensor_type == "light":
            value = read_light_sensor()
        elif precondition.sensor_type == "temperature":
            value = read_temperature_sensor()
        else:
            return PreconditionResult(
                precondition=precondition,
                reading_value=None,
                passed=False,
                timestamp=datetime.now(),
                reason="unknown_sensor_type",
            )

        if value is None:
            return PreconditionResult(
                precondition=precondition,
                reading_value=None,
                passed=False,
                timestamp=datetime.now(),
                reason="sensor_unavailable",
            )

        # Check threshold
        passed = check_precondition(
            precondition.sensor_type,
            precondition.threshold,
            precondition.comparison,
        )

        return PreconditionResult(
            precondition=precondition,
            reading_value=value,
            passed=passed,
            timestamp=datetime.now(),
            reason="passed" if passed else "failed",
        )

    def get_current_readings(self) -> dict[str, SensorReading | None]:
        """Get current readings from all sensors (for diagnostics/UI)."""
        now = datetime.now()
        return {
            "light": SensorReading("light", val, now, "lux") if (val := read_light_sensor()) else None,
            "temperature": SensorReading("temperature", val, now, "celsius") if (val := read_temperature_sensor()) else None,
        }

    def get_evaluation_history(self, limit: int = 10) -> list[PreconditionResult]:
        """Get recent pre-condition evaluation results."""
        with self._lock:
            return list(self._evaluation_history)[-limit:]


# Singleton
_sensor_service: SensorService | None = None


def get_sensor_service() -> SensorService:
    """Get singleton SensorService instance."""
    global _sensor_service
    if _sensor_service is None:
        _sensor_service = SensorService()
    return _sensor_service
```

### Step 3: Scheduler Service

**Create file**: `webui/backend/services/scheduler_service.py`

**Follow pattern from**: `webui/backend/services/deployment_service.py` (lines 77-587)

```python
"""
Scheduler service with LRU caching.

Provides CRUD operations for schedules, activation management,
and conflict detection with thread-safe caching.
"""

import logging
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Final

from webui.backend.lib.schedule_schema import (
    Schedule,
    validate_schedule,
    ScheduleValidationError,
)
from webui.backend.lib.schedule_storage import (
    read_schedule,
    write_schedule,
    delete_schedule_file,
    list_schedule_files,
)
from webui.backend.lib.schedule_conflict import detect_conflicts, Conflict
from webui.backend.lib.cron_bridge import CronBridge

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CACHE_TTL: Final[int] = 300  # 5 minutes
DEFAULT_MAX_CACHE_SIZE: Final[int] = 50


class SchedulerService:
    """
    Service layer for schedule management.

    Features:
    - LRU cache with TTL expiration
    - Thread-safe operations via RLock
    - Only one schedule active at a time
    - Automatic conflict detection
    - Statistics tracking

    Thread Safety:
    - _cache_lock: Protects in-memory cache
    - _stats_lock: Protects statistics counters
    - Always acquire locks in order: _cache_lock -> _stats_lock
    """

    def __init__(
        self,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    ):
        """
        Initialize the scheduler service.

        Args:
            cache_ttl: Cache entry TTL in seconds
            max_cache_size: Maximum cache entries
        """
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size

        # LRU cache: schedule_id -> (Schedule, timestamp)
        self._cache: OrderedDict[str, tuple[Schedule, float]] = OrderedDict()
        self._cache_lock = RLock()

        # Statistics
        self._stats_lock = RLock()
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_reads = 0
        self._total_writes = 0

        # Cron bridge for system integration
        self._cron_bridge = CronBridge()

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def get_schedule(self, schedule_id: str) -> Schedule | None:
        """
        Get a schedule by ID.

        Args:
            schedule_id: The schedule identifier

        Returns:
            Schedule if found, None otherwise
        """
        with self._stats_lock:
            self._total_reads += 1

        # Check cache first
        with self._cache_lock:
            if schedule_id in self._cache:
                schedule, timestamp = self._cache[schedule_id]
                if time.time() - timestamp < self._cache_ttl:
                    # Cache hit - move to end (LRU)
                    self._cache.move_to_end(schedule_id)
                    with self._stats_lock:
                        self._cache_hits += 1
                    return schedule
                else:
                    # Expired - remove
                    del self._cache[schedule_id]

        # Cache miss - read from disk
        with self._stats_lock:
            self._cache_misses += 1

        schedule = read_schedule(schedule_id)

        if schedule:
            self._add_to_cache(schedule_id, schedule)

        return schedule

    def list_schedules(self) -> list[Schedule]:
        """
        List all schedules.

        Returns:
            List of all Schedule objects
        """
        schedule_ids = list_schedule_files()
        schedules = []

        for schedule_id in schedule_ids:
            schedule = self.get_schedule(schedule_id)
            if schedule:
                schedules.append(schedule)

        return schedules

    def create_schedule(self, schedule: Schedule) -> Schedule:
        """
        Create a new schedule.

        Args:
            schedule: Schedule to create

        Returns:
            Created schedule with assigned ID

        Raises:
            ScheduleValidationError: If validation fails
        """
        # Validate
        valid, error = validate_schedule(schedule)
        if not valid:
            raise ScheduleValidationError(error)

        # Set timestamps
        now = datetime.now().isoformat()
        schedule.created_at = now
        schedule.modified_at = now

        # Write to disk
        write_schedule(schedule)

        # Update cache
        self._add_to_cache(schedule.schedule_id, schedule)

        with self._stats_lock:
            self._total_writes += 1

        logger.info(f"Created schedule: {schedule.schedule_id}")
        return schedule

    def update_schedule(
        self,
        schedule_id: str,
        updates: dict
    ) -> Schedule | None:
        """
        Update an existing schedule.

        Args:
            schedule_id: ID of schedule to update
            updates: Dictionary of field updates

        Returns:
            Updated schedule, or None if not found
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(schedule, key) and key not in ('schedule_id', 'version'):
                setattr(schedule, key, value)

        # Update timestamp
        schedule.modified_at = datetime.now().isoformat()

        # Validate
        valid, error = validate_schedule(schedule)
        if not valid:
            raise ScheduleValidationError(error)

        # Write to disk
        write_schedule(schedule)

        # Update cache
        self._add_to_cache(schedule_id, schedule)

        with self._stats_lock:
            self._total_writes += 1

        logger.info(f"Updated schedule: {schedule_id}")
        return schedule

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: ID of schedule to delete

        Returns:
            True if deleted, False if not found
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False

        # Cannot delete active schedule
        if schedule.is_active:
            raise ScheduleValidationError(
                "Cannot delete active schedule. Deactivate first."
            )

        # Delete from disk
        delete_schedule_file(schedule_id)

        # Remove from cache
        with self._cache_lock:
            if schedule_id in self._cache:
                del self._cache[schedule_id]

        logger.info(f"Deleted schedule: {schedule_id}")
        return True

    # -------------------------------------------------------------------------
    # Activation Management
    # -------------------------------------------------------------------------

    def get_active_schedule(self) -> Schedule | None:
        """
        Get the currently active schedule.

        Returns:
            Active schedule, or None if none active
        """
        for schedule in self.list_schedules():
            if schedule.is_active:
                return schedule
        return None

    def activate_schedule(self, schedule_id: str) -> tuple[bool, str]:
        """
        Activate a schedule.

        Only one schedule can be active at a time. Activating a schedule:
        1. Deactivates any currently active schedule
        2. Validates the schedule (conflict check)
        3. Applies to system (cron + RTC)
        4. Optionally creates deployment metadata

        Args:
            schedule_id: ID of schedule to activate

        Returns:
            (success: bool, message: str)
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False, "Schedule not found"

        # Validate
        valid, error = validate_schedule(schedule)
        if not valid:
            return False, f"Validation failed: {error}"

        # Check for conflicts
        conflicts = detect_conflicts(schedule)
        unresolved = [c for c in conflicts if not c.resolved]
        if unresolved:
            return False, f"Unresolved conflicts: {len(unresolved)}"

        # Deactivate current active schedule
        current_active = self.get_active_schedule()
        if current_active:
            self.deactivate_schedule()

        # Apply to system
        success = self._cron_bridge.apply_to_system(schedule)
        if not success:
            return False, "Failed to apply schedule to system"

        # Update schedule state
        now = datetime.now().isoformat()
        schedule.is_active = True
        schedule.last_activated_at = now
        schedule.modified_at = now
        write_schedule(schedule)
        self._add_to_cache(schedule_id, schedule)

        # Create deployment if requested
        if schedule.create_deployment:
            self._create_deployment_for_schedule(schedule)

        logger.info(f"Activated schedule: {schedule_id}")
        return True, "Schedule activated successfully"

    def deactivate_schedule(self) -> bool:
        """
        Deactivate the current active schedule.

        Returns:
            True if deactivated, False if none active
        """
        active = self.get_active_schedule()
        if not active:
            return False

        # Remove from system
        self._cron_bridge.remove_from_system()

        # Update schedule state
        now = datetime.now().isoformat()
        active.is_active = False
        active.last_deactivated_at = now
        active.modified_at = now
        write_schedule(active)
        self._add_to_cache(active.schedule_id, active)

        logger.info(f"Deactivated schedule: {active.schedule_id}")
        return True

    # -------------------------------------------------------------------------
    # Validation and Preview
    # -------------------------------------------------------------------------

    def validate_schedule(self, schedule: Schedule) -> list[Conflict]:
        """
        Validate a schedule and return any conflicts.

        Args:
            schedule: Schedule to validate

        Returns:
            List of Conflict objects (empty if no conflicts)
        """
        return detect_conflicts(schedule)

    def preview_events(
        self,
        schedule: Schedule,
        days: int = 7
    ) -> list[dict]:
        """
        Preview scheduled events for the next N days.

        Args:
            schedule: Schedule to preview
            days: Number of days to preview

        Returns:
            List of event dicts with datetime and action info
        """
        return self._cron_bridge.get_next_events(schedule, days=days)

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def invalidate_cache(self, schedule_id: str | None = None):
        """
        Invalidate cache entries.

        Args:
            schedule_id: Specific schedule to invalidate, or None for all
        """
        with self._cache_lock:
            if schedule_id:
                if schedule_id in self._cache:
                    del self._cache[schedule_id]
                    logger.debug(f"Invalidated cache for: {schedule_id}")
            else:
                self._cache.clear()
                logger.debug("Invalidated all cache entries")

    def get_statistics(self) -> dict:
        """
        Get service statistics.

        Returns:
            Dict with cache and operation statistics
        """
        with self._cache_lock:
            cache_size = len(self._cache)

        with self._stats_lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

            return {
                "cache_size": cache_size,
                "cache_max_size": self._max_cache_size,
                "cache_ttl_seconds": self._cache_ttl,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate_percent": round(hit_rate, 2),
                "total_reads": self._total_reads,
                "total_writes": self._total_writes,
            }

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _add_to_cache(self, schedule_id: str, schedule: Schedule):
        """Add schedule to cache with LRU eviction."""
        with self._cache_lock:
            # Evict if at capacity
            while len(self._cache) >= self._max_cache_size:
                self._cache.popitem(last=False)

            self._cache[schedule_id] = (schedule, time.time())
            self._cache.move_to_end(schedule_id)

    def _create_deployment_for_schedule(self, schedule: Schedule):
        """Create deployment metadata when schedule is activated."""
        try:
            from webui.backend.services import get_deployment_service
            from webui.backend.lib.deployment_schema import DeploymentMetadata
            from mothbox_paths import PHOTOS_DIR

            service = get_deployment_service()

            # Build metadata from schedule
            now = datetime.now().isoformat()
            metadata = DeploymentMetadata(
                version="1.0",
                deployment_name=schedule.name,
                created_at=now,
                modified_at=now,
            )

            service.set_deployment_metadata(str(PHOTOS_DIR), metadata)
            logger.info(f"Created deployment for schedule: {schedule.schedule_id}")

        except Exception as e:
            logger.error(f"Failed to create deployment: {e}")


# Singleton instance
_scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Get the singleton SchedulerService instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
```

---

## API Specification

The API manages **self-contained schedules** with embedded event patterns (single-file storage).

### Schedule Endpoints

| Method | Path | Description | Rate Limit |
|--------|------|-------------|------------|
| GET | /api/scheduler/ui/schedules | List all schedules | - |
| GET | /api/scheduler/ui/schedules/{id} | Get single schedule (full details) | - |
| POST | /api/scheduler/ui/schedules | Create schedule | 30/min |
| PUT | /api/scheduler/ui/schedules/{id} | Replace schedule | 30/min |
| DELETE | /api/scheduler/ui/schedules/{id} | Delete schedule | 30/min |
| POST | /api/scheduler/ui/schedules/{id}/activate | Activate schedule | 10/min |
| POST | /api/scheduler/ui/schedules/deactivate | Deactivate current | 10/min |
| GET | /api/scheduler/ui/schedules/active | Get active schedule | - |
| POST | /api/scheduler/ui/schedules/{id}/validate | Check conflicts | - |
| GET | /api/scheduler/ui/schedules/{id}/preview | Preview executions | - |
| GET | /api/scheduler/ui/schedules/builtin | List built-in schedules | - |

#### List Schedules

**Endpoint**: `GET /api/scheduler/ui/schedules`

**Response** (200 OK):
```json
{
  "schedules": [
    {
      "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Nightly Hourly UV Survey",
      "description": "UV capture every hour from 1am-6am",
      "trigger_type": "interval",
      "is_active": true,
      "event_pattern_count": 1,
      "total_duration_minutes": 15,
      "created_at": "2025-06-01T12:00:00Z",
      "modified_at": "2025-06-15T08:30:00Z"
    }
  ],
  "total": 1
}
```

#### Create Schedule

**Endpoint**: `POST /api/scheduler/ui/schedules`

Each schedule is self-contained with event patterns embedded inline.

**Request** (Interval Trigger):
```json
{
  "name": "Nightly Hourly UV Survey",
  "description": "UV capture cycle every hour from 1am-6am",
  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "actions": [
        {"action_type": "gpio", "action_name": "uv_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
        {"action_type": "gpio", "action_name": "uv_off", "offset_minutes": 15}
      ],
      "duration_minutes": 15
    }
  ],
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "01:00",
      "end_time": "06:00"
    }
  },
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "create_deployment": true
}
```

**Request** (Solar Trigger):
```json
{
  "name": "Dusk Survey",
  "description": "Capture at sunset+30 every day",
  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "actions": [
        {"action_type": "gpio", "action_name": "uv_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
        {"action_type": "gpio", "action_name": "uv_off", "offset_minutes": 15}
      ],
      "duration_minutes": 15
    }
  ],
  "trigger_type": "solar",
  "solar_trigger": {
    "solar_event": "sunset",
    "offset_minutes": 30
  },
  "start_date": "2024-06-01"
}
```

**Request** (Moon Phase Trigger):
```json
{
  "name": "Full Moon Study",
  "description": "Capture during full moon period",
  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "actions": [
        {"action_type": "gpio", "action_name": "uv_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
        {"action_type": "gpio", "action_name": "uv_off", "offset_minutes": 15}
      ],
      "duration_minutes": 15
    }
  ],
  "trigger_type": "moon_phase",
  "moon_phase_trigger": {
    "phases": ["full"],
    "offset_days": 2,
    "time_window": {
      "start_time": "dusk",
      "end_time": "dawn"
    }
  }
}
```

**Request** (Sensor Trigger):
```json
{
  "name": "Nightly Capture with Light Check",
  "description": "Capture hourly between sunset and sunrise, only if ambient light < 100 lux",
  "event_patterns": [
    {
      "pattern_id": "flash-capture",
      "name": "Flash Capture",
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0, "parameters": {"delay_ms": 100}},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 1}
      ],
      "duration_minutes": 1
    }
  ],
  "trigger_type": "solar",
  "solar_trigger": {
    "event_type": "sunset",
    "offset_minutes": 30,
    "time_window": {
      "start_time": "sunset",
      "end_time": "sunrise"
    }
  },
  "preconditions": [
    {
      "sensor_type": "light",
      "threshold": 100.0,
      "comparison": "lt"
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Nightly Hourly UV Survey",
  "trigger_type": "interval",
  "created_at": "2025-06-01T12:00:00Z",
  "is_active": false
}
```

#### Activate Schedule

**Endpoint**: `POST /api/scheduler/ui/schedules/{id}/activate`

**Request** (optional):
```json
{
  "deployment_options": {
    "create_deployment": true,
    "deployment_name": "Summer Survey 2025",
    "location_from_gps": true
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Schedule activated successfully",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "next_event": {
    "datetime": "2025-06-01T17:45:00Z",
    "event_name": "Turn on attract lights"
  }
}
```

**Error Responses**:
- 400: Unresolved conflicts
- 404: Schedule not found
- 409: Another schedule already active (if force not specified)

#### Preview Events

**Endpoint**: `GET /api/scheduler/ui/schedules/{id}/preview`

**Query Parameters**:
- `days`: Number of days to preview (default: 7, max: 90)

**Response** (200 OK):
```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "preview_start": "2025-06-15T00:00:00Z",
  "preview_end": "2025-06-16T00:00:00Z",
  "executions": [
    {
      "start_time": "2025-06-15T01:00:00Z",
      "pattern_name": "UV Capture Cycle",
      "pattern_id": "uv-capture-cycle",
      "actions": [
        {"time": "2025-06-15T01:00:00Z", "action": "uv_on"},
        {"time": "2025-06-15T01:05:00Z", "action": "takephoto"},
        {"time": "2025-06-15T01:15:00Z", "action": "uv_off"}
      ]
    },
    {
      "start_time": "2025-06-15T02:00:00Z",
      "pattern_name": "UV Capture Cycle",
      "pattern_id": "uv-capture-cycle",
      "actions": [
        {"time": "2025-06-15T02:00:00Z", "action": "uv_on"},
        {"time": "2025-06-15T02:05:00Z", "action": "takephoto"},
        {"time": "2025-06-15T02:15:00Z", "action": "uv_off"}
      ]
    }
  ],
  "conflicts": [],
  "moon_phase": {
    "phase": "waxing_gibbous",
    "illumination": 0.72
  }
}
```

### Moon Phase API

#### Get Moon Phases

**Endpoint**: `GET /api/scheduler/ui/moon/phases`

**Query Parameters**:
- `start_date`: ISO 8601 date (required)
- `end_date`: ISO 8601 date (required)
- `significant_only`: Boolean, return only major phases (default: false)

**Response** (200 OK):
```json
{
  "start_date": "2025-06-01",
  "end_date": "2025-06-30",
  "phases": [
    {
      "date": "2025-06-03",
      "phase": "full",
      "illumination": 1.0,
      "age_days": 14.77
    },
    {
      "date": "2025-06-11",
      "phase": "last_quarter",
      "illumination": 0.5,
      "age_days": 22.15
    }
  ]
}
```

---

## Data Structures

The scheduler uses **single-file storage** where each schedule is fully self-contained with event patterns embedded inline. This simplifies export/import and makes schedules portable between Mothbox units.

### Schedule JSON File Format

**Location**: `CONFIG_DIR/schedules/{schedule_id}.json`

Each schedule file contains both the scheduling configuration (when to run) and the event patterns (what to run) in a single portable file.

```json
{
  "schema_version": "2.0",
  "schedule_id": "nightly-hourly-survey",
  "name": "Nightly Hourly UV Survey",
  "description": "Run UV capture cycle every hour from 1am-6am during summer",

  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "description": "15-minute UV session with photo capture at 5-minute mark",
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "uv_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn on UV attract lights"
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 5,
          "parameters": {
            "hdr_enabled": true,
            "preset": "night_photography"
          },
          "description": "Capture photo"
        },
        {
          "action_type": "gpio",
          "action_name": "uv_off",
          "offset_minutes": 15,
          "parameters": {},
          "description": "Turn off UV attract lights"
        }
      ],
      "tags": ["uv", "capture", "15min"],
      "duration_minutes": 15
    }
  ],

  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "01:00",
      "end_time": "06:00",
      "start_offset_minutes": 0,
      "end_offset_minutes": 0
    },
    "days_of_week": null
  },
  "solar_trigger": null,
  "moon_phase_trigger": null,
  "fixed_time_trigger": null,
  "preconditions": null,

  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "deployment_id": null,
  "create_deployment": true,
  "enabled": true,
  "is_active": true,

  "created_at": "2024-06-01T12:00:00Z",
  "modified_at": "2024-06-01T12:00:00Z",
  "modified_by": null
}
```

### Example: Full Moon Study Schedule

```json
{
  "schema_version": "2.0",
  "schedule_id": "full-moon-study",
  "name": "Full Moon Moth Study",
  "description": "Intensive capture during full moon ±2 days",

  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "actions": [
        {"action_type": "gpio", "action_name": "uv_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
        {"action_type": "gpio", "action_name": "uv_off", "offset_minutes": 15}
      ],
      "duration_minutes": 15
    },
    {
      "pattern_id": "attract-session",
      "name": "Attract Session",
      "actions": [
        {"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 10},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 20},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 30},
        {"action_type": "gpio", "action_name": "attract_off", "offset_minutes": 60}
      ],
      "duration_minutes": 60
    }
  ],

  "trigger_type": "moon_phase",
  "moon_phase_trigger": {
    "phases": ["full"],
    "offset_days": 2,
    "time_window": {
      "start_time": "dusk",
      "end_time": "dawn"
    }
  },

  "start_date": "2024-06-01",
  "end_date": "2024-12-31",
  "create_deployment": true,
  "enabled": true,
  "is_active": false
}
```

### Example: Pre-condition Guarded Capture

```json
{
  "schema_version": "2.0",
  "schedule_id": "precondition-capture",
  "name": "Dark-Only Night Capture",
  "description": "Capture every 30 minutes during nighttime, but only if ambient light is below 50 lux",

  "event_patterns": [
    {
      "pattern_id": "flash-capture",
      "name": "Flash Capture",
      "actions": [
        {"action_type": "gpio", "action_name": "flash_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 0, "parameters": {"delay_ms": 100}},
        {"action_type": "gpio", "action_name": "flash_off", "offset_minutes": 1}
      ],
      "duration_minutes": 1
    }
  ],

  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 30,
    "time_window": {
      "start_time": "sunset",
      "end_time": "sunrise"
    }
  },
  "preconditions": [
    {
      "sensor_type": "light",
      "threshold": 50.0,
      "comparison": "lt"
    },
    {
      "sensor_type": "temperature",
      "threshold": 5.0,
      "comparison": "gt"
    }
  ],
  "enabled": true,
  "is_active": false
}
```

> **Note**: Pre-conditions are optional and checked at capture time. If any pre-condition
> fails, the capture is skipped (with logging). This example requires light < 50 lux AND
> temperature > 5°C for capture to proceed.

### Conflict Detection

```python
@dataclass
class Conflict:
    """Represents a scheduling conflict."""
    conflict_id: str
    event1_id: str
    event2_id: str
    conflict_type: str  # "time_overlap", "resource_contention"
    message: str
    suggested_resolution: str
    resolved: bool = False
    resolution_method: str | None = None  # "priority", "skip", "queue"
```

---

## Frontend Components

### SchedulerContext State

```javascript
const initialState = {
  // Data
  schedules: [],
  activeSchedule: null,
  editingSchedule: null,
  editingEvent: null,
  previewEvents: [],
  conflicts: [],
  moonPhases: {},

  // UI State
  viewMode: 'calendar',      // 'calendar' | 'list' | 'timeline'
  calendarView: 'week',      // 'day' | 'week' | 'month'
  selectedDate: new Date(),
  isExpertMode: false,
  isDrawerOpen: false,

  // Loading states
  isLoading: false,
  isSaving: false,
  error: null,
}
```

### Component Props

#### CalendarView

**File**: `webui/frontend/src/components/scheduler/CalendarView/CalendarView.jsx`

**Props**:
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| events | array | Yes | List of scheduled events to display |
| moonPhases | object | No | Moon phase data by date |
| selectedDate | Date | Yes | Currently selected/focused date |
| onDateSelect | function | Yes | Called when user selects a date |
| onEventClick | function | Yes | Called when user clicks an event |
| viewMode | string | Yes | 'day' \| 'week' \| 'month' |

#### TimePatternBuilder

**File**: `webui/frontend/src/components/scheduler/PatternBuilder/TimePatternBuilder.jsx`

**Props**:
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| value | TimePattern | Yes | Current pattern configuration |
| onChange | function | Yes | Called with updated pattern |
| location | object | No | {lat, lon} for solar calculations |
| isExpertMode | boolean | No | Show raw cron input |
| errors | object | No | Validation errors by field |

---

## Testing Strategy

### Unit Tests

**File**: `Tests/unit/test_schedule_schema.py`

**Test Cases**:
| Test | Description | Pattern Reference |
|------|-------------|-------------------|
| test_schedule_creation | Create valid schedule | deployment_schema tests |
| test_schedule_validation_name | Name length limits | |
| test_schedule_validation_events | Event count limits | |
| test_action_type_validation | Valid action types | |
| test_time_pattern_recurring | Recurring pattern validation | |
| test_time_pattern_calendar | Calendar pattern validation | |
| test_moon_phase_validation | Valid moon phases | |
| test_to_dict_from_dict | Serialization round-trip | |

**Fixture pattern** (from `conftest.py`):
```python
@pytest.fixture
def sample_schedule():
    """Create a valid sample schedule for testing."""
    return Schedule(
        version="1.0",
        schedule_id="test-schedule-001",
        name="Test Schedule",
        description="A test schedule",
        created_at=datetime.now().isoformat(),
        modified_at=datetime.now().isoformat(),
        events=[
            ScheduleEvent(
                event_id="event-001",
                name="Test Event",
                time_pattern=TimePattern(
                    pattern_type="recurring",
                    days_of_week=[0, 1, 2, 3, 4],
                    time_spec="19:00",
                ),
                actions=[
                    ScheduleAction(
                        action_type="gpio",
                        action_name="attract_on",
                        priority=5,
                    )
                ],
            )
        ],
    )
```

### Integration Tests

**File**: `Tests/integration/test_scheduler_workflow.py`

```python
def test_schedule_activation_workflow(client, sample_schedule):
    """Test complete schedule creation and activation."""
    # Create schedule
    response = client.post(
        '/api/scheduler/ui/schedules',
        json=sample_schedule.to_dict()
    )
    assert response.status_code == 201
    schedule_id = response.json['schedule_id']

    # Verify created
    response = client.get(f'/api/scheduler/ui/schedules/{schedule_id}')
    assert response.status_code == 200

    # Activate
    response = client.post(f'/api/scheduler/ui/schedules/{schedule_id}/activate')
    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify active
    response = client.get('/api/scheduler/ui/schedules/active')
    assert response.status_code == 200
    assert response.json['schedule_id'] == schedule_id
```

### Performance Tests

**File**: `Tests/performance/test_scheduler_performance.py`

**Benchmarks**:
| Operation | Target | Measurement Method |
|-----------|--------|-------------------|
| Schedule CRUD | <100ms | pytest-benchmark |
| Validation (50 events) | <200ms | time.perf_counter |
| Preview (30 days) | <500ms | time.perf_counter |
| Moon phase range | <50ms | time.perf_counter |

---

## Common Patterns Reference

### Pattern 1: LRU Cache with TTL

**Used in**: `services/deployment_service.py`, `services/scheduler_service.py`

```python
def _add_to_cache(self, key: str, value: Any):
    """Add item to cache with LRU eviction."""
    with self._cache_lock:
        # Evict oldest if at capacity
        while len(self._cache) >= self._max_cache_size:
            self._cache.popitem(last=False)

        # Add with timestamp
        self._cache[key] = (value, time.time())
        self._cache.move_to_end(key)

def _get_from_cache(self, key: str) -> Any | None:
    """Get item from cache if not expired."""
    with self._cache_lock:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                self._cache.move_to_end(key)  # LRU touch
                return value
            else:
                del self._cache[key]  # Expired
    return None
```

### Pattern 2: File Locking for Atomic Operations

**Used in**: `lib/deployment_sidecar.py`, `lib/sidecar_metadata.py`

```python
from filelock import FileLock, Timeout

def write_schedule(schedule: Schedule) -> bool:
    """Atomic write with file locking."""
    file_path = SCHEDULES_DIR / f"{schedule.schedule_id}.json"
    lock_path = file_path.with_suffix('.lock')

    lock = FileLock(lock_path, timeout=10)
    try:
        with lock:
            # Create backup
            if file_path.exists():
                backup_path = file_path.with_suffix('.bak')
                shutil.copy2(file_path, backup_path)

            # Write new content
            with open(file_path, 'w') as f:
                json.dump(schedule.to_dict(), f, indent=2)

            return True
    except Timeout:
        logger.error(f"Lock timeout for {file_path}")
        return False
```

### Pattern 3: React Query Mutation with Cache Invalidation

**Used in**: `hooks/useExportJobs.js`, `hooks/useBulkOperations.js`

```javascript
export function useCreateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (scheduleData) => {
      const response = await api.post('/scheduler/v2/schedules', scheduleData)
      return response.data
    },
    onSuccess: () => {
      // Invalidate list to refetch
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.SCHEDULES
      })
    },
    onError: (error) => {
      toast.error(formatErrorMessage(error))
    },
  })
}
```

---

## Implementation Phases

### Phase 0: Refactoring (Prerequisite)

**Goal**: Extract shared security code from existing `scheduler.py` to enable code reuse

**Issues**:
0. **Extract Cron Security Library** (1 story point)
   - Labels: `backend`, `refactor`, `security`
   - Extract `ALLOWED_SCRIPTS` and validation logic from `routes/scheduler.py`
   - Create `lib/cron_security.py` with shared code
   - Update `routes/scheduler.py` to import from new library
   - Acceptance criteria:
     - [ ] `lib/cron_security.py` created with all functions
     - [ ] `ALLOWED_SCRIPTS` expanded with GPS, display, debug scripts
     - [ ] `ACTION_TYPE_SCRIPTS` mapping added for schedule actions
     - [ ] Existing `routes/scheduler.py` updated to use imports
     - [ ] All existing scheduler API tests still pass
     - [ ] 15+ unit tests for new cron_security module

**Dependencies**: None (this is the first issue to complete)

---

### Phase 1: Backend Schema & Storage

**Goal**: Single-file schedule storage with embedded event patterns

**Issues**:
1. **Schedule Schema** (3 story points)
   - Labels: `backend`, `foundation`
   - Create `schedule_schema.py` with dataclasses
   - Acceptance criteria:
     - [ ] PatternAction, EventPattern dataclasses defined
     - [ ] TimeWindow, trigger dataclasses defined
     - [ ] Schedule dataclass with embedded event_patterns list
     - [ ] Validation functions for all types
     - [ ] 40+ unit tests passing

2. **Schedule Storage** (2 story points)
   - Labels: `backend`, `storage`
   - Create `schedule_storage.py` with single-file storage
   - Acceptance criteria:
     - [ ] Schedule CRUD (CONFIG_DIR/schedules/)
     - [ ] Each schedule is self-contained with embedded patterns
     - [ ] File locking and backup
     - [ ] Built-in schedules directory support
     - [ ] 25+ unit tests passing

### Phase 2: Astronomical Calculations

**Goal**: Sun/moon calculations using astral

**Issues**:
3. **Moon Phase Calculator** (1 story point)
   - Labels: `backend`, `utility`
   - Create `moon_phase.py` using astral
   - Acceptance criteria:
     - [ ] All 8 phases detected
     - [ ] Moonrise/moonset times
     - [ ] Phase searching
     - [ ] 20+ unit tests passing

4. **Solar Time Calculator** (1 story point)
   - Labels: `backend`, `utility`
   - Create `solar_time.py` using astral
   - Acceptance criteria:
     - [ ] Sunrise/sunset calculation
     - [ ] All twilight types (civil, nautical, astronomical)
     - [ ] Golden/blue hour
     - [ ] Time spec parsing ("sunset+30")
     - [ ] 20+ unit tests passing

### Phase 3: Service Layer

**Goal**: Core service with caching and conflict detection

**Issues**:
5. **Scheduler Service** (3 story points)
   - Labels: `backend`, `service`
   - Create `scheduler_service.py`
   - Acceptance criteria:
     - [ ] LRU cache with TTL for both tiers
     - [ ] Thread-safe operations
     - [ ] Event pattern + schedule pattern CRUD
     - [ ] 50+ unit tests passing

6. **Conflict Detection** (2 story points)
   - Labels: `backend`, `validation`
   - Create `schedule_conflict.py`
   - Acceptance criteria:
     - [ ] Time overlap detection for pattern executions
     - [ ] Resource contention detection
     - [ ] 25+ unit tests passing

7. **Schedule Preview** (2 story points)
   - Labels: `backend`, `utility`
   - Create `schedule_preview.py`
   - Acceptance criteria:
     - [ ] Generate execution timeline
     - [ ] Resolve pattern references
     - [ ] Include moon phases
     - [ ] 20+ unit tests passing

### Phase 4: Cron Integration

**Goal**: System integration with cron and RTC

**Issues**:
8. **Cron Bridge** (3 story points)
   - Labels: `backend`, `integration`
   - Create `cron_bridge.py`
   - Acceptance criteria:
     - [ ] Schedule pattern → cron expression
     - [ ] Event pattern action sequencing
     - [ ] RTC alarm integration
     - [ ] 40+ unit tests passing

9. **Integration Tests** (2 story points)
   - Labels: `backend`, `testing`
   - Create integration tests
   - Acceptance criteria:
     - [ ] RTC wakealarm tests
     - [ ] Cron job creation tests
     - [ ] 15+ integration tests passing

### Phase 5: REST API

**Goal**: Two-tier API endpoints

**Issues**:
10. **Event Pattern API** (2 story points)
    - Labels: `backend`, `api`
    - Create pattern endpoints in `routes/scheduler_ui.py`
    - Acceptance criteria:
      - [ ] CRUD for event patterns
      - [ ] Built-in pattern listing
      - [ ] 25+ API tests passing

11. **Schedule Pattern API** (3 story points)
    - Labels: `backend`, `api`
    - Create schedule endpoints in `routes/scheduler_ui.py`
    - Acceptance criteria:
      - [ ] CRUD for schedule patterns
      - [ ] Activation/deactivation
      - [ ] Preview endpoint
      - [ ] 35+ API tests passing

### Phase 6: Built-in Patterns

**Goal**: Built-in event and schedule patterns

**Issues**:
12. **Built-in Event Patterns** (1 story point)
    - Labels: `backend`, `content`
    - Create event pattern JSON files
    - Acceptance criteria:
      - [ ] uv_capture_cycle.json (15 min UV + photo)
      - [ ] attract_session.json (60 min attract lights)
      - [ ] flash_capture.json (instant flash + photo)
      - [ ] dawn_transect.json
      - [ ] dusk_transect.json

13. **Built-in Schedule Patterns** (1 story point)
    - Labels: `backend`, `content`
    - Create schedule pattern JSON files
    - Acceptance criteria:
      - [ ] nightly_hourly.json (interval trigger)
      - [ ] full_moon_survey.json (moon phase trigger)
      - [ ] twilight_transect.json (solar trigger)
      - [ ] continuous_monitoring.json

### Phase 7: Frontend Core

**Goal**: State management and hooks for schedules

**Issues**:
14. **Scheduler Context** (2 story points)
    - Labels: `frontend`, `state`
    - Create `contexts/SchedulerContext.jsx`
    - Acceptance criteria:
      - [ ] Event patterns state
      - [ ] Schedule patterns state
      - [ ] Active schedule tracking
      - [ ] 20+ unit tests passing

15. **Event Pattern Hooks** (2 story points)
    - Labels: `frontend`, `hooks`
    - Create `hooks/useEventPatterns.js`
    - Acceptance criteria:
      - [ ] CRUD mutations
      - [ ] Pattern library queries
      - [ ] 15+ unit tests passing

16. **Schedule Pattern Hooks** (2 story points)
    - Labels: `frontend`, `hooks`
    - Create `hooks/useSchedulePatterns.js`
    - Acceptance criteria:
      - [ ] CRUD mutations
      - [ ] Activation mutations
      - [ ] Preview queries
      - [ ] 15+ unit tests passing

### Phase 8: Frontend Scheduling

**Goal**: Pattern editor and schedule builder UI

**Issues**:
17. **Main Page** (2 story points)
    - Labels: `frontend`, `page`
    - Create `pages/SchedulerUI.jsx`
    - Acceptance criteria:
      - [ ] Tabs: Patterns | Schedules | Calendar
      - [ ] Responsive layout
      - [ ] Active schedule indicator

18. **Pattern Library** (3 story points)
    - Labels: `frontend`, `component`
    - Create `PatternLibrary/` components
    - Acceptance criteria:
      - [ ] Browse event patterns
      - [ ] Filter by category/tags
      - [ ] Pattern details drawer

19. **Pattern Editor** (3 story points)
    - Labels: `frontend`, `form`
    - Create `PatternEditor/` components
    - Acceptance criteria:
      - [ ] Action list with offset timeline
      - [ ] Action parameter forms
      - [ ] Duration preview

20. **Schedule Editor** (4 story points)
    - Labels: `frontend`, `form`
    - Create `ScheduleEditor/` components
    - Acceptance criteria:
      - [ ] Pattern reference selector
      - [ ] Trigger type forms (interval, solar, moon, sensor)
      - [ ] Date range picker
      - [ ] Preview timeline

21. **Calendar View** (4 story points)
    - Labels: `frontend`, `calendar`
    - Create `CalendarView/` components
    - Acceptance criteria:
      - [ ] Execution timeline view
      - [ ] Pattern color coding
      - [ ] Moon phase overlay

22. **Conflict Resolver** (2 story points)
    - Labels: `frontend`, `validation`
    - Create `ConflictResolver/` components
    - Acceptance criteria:
      - [ ] Overlap detection display
      - [ ] Resolution suggestions

### Phase 9: Sensor Pre-conditions

**Goal**: Sensor reading and pre-condition evaluation

**Issues**:
23. **Sensor Reader Library** (#230, 2 story points)
    - Labels: `backend`, `hardware`
    - Create `lib/sensor_reader.py`
    - Acceptance criteria:
      - [ ] Light sensor (BH1750/LTR303 I2C) support
      - [ ] Temperature sensor (TMP102/MCP9808 I2C) support
      - [ ] Pre-condition check function
      - [ ] Environmental reading helper
      - [ ] 20+ unit tests passing

24. **Sensor Pre-condition Service** (#231, 2 story points)
    - Labels: `backend`, `service`
    - Create `services/sensor_service.py`
    - Acceptance criteria:
      - [ ] Pre-condition evaluation at capture time
      - [ ] Evaluation history tracking
      - [ ] 15+ unit tests passing

25. **Sensor Integration Tests** (#232, 2 story points)
    - Labels: `backend`, `testing`
    - Create sensor integration tests
    - Acceptance criteria:
      - [ ] Mock I2C sensor tests
      - [ ] Pre-condition evaluation tests
      - [ ] Environmental logging tests

### Phase 10: Polish

**Goal**: Expert mode and E2E testing

**Issues**:
26. **Expert Mode** (2 story points)
    - Labels: `frontend`, `advanced`
    - Create `ExpertMode/` components
    - Acceptance criteria:
      - [ ] Raw cron input
      - [ ] Cron preview

27. **E2E Tests** (2 story points)
    - Labels: `testing`, `e2e`
    - Create Playwright tests
    - Acceptance criteria:
      - [ ] Pattern CRUD workflow
      - [ ] Schedule activation workflow
      - [ ] Calendar navigation

28. **Documentation** (1 story point)
    - Labels: `docs`
    - Update documentation
    - Acceptance criteria:
      - [ ] CLAUDE.md Scheduler section
      - [ ] API documentation
      - [ ] User guide

---

## Appendix

### File Checklist

**Backend - Libraries (10 files)**:
- [ ] `webui/backend/lib/cron_security.py` *(Phase 0 - refactored from scheduler.py)*
- [ ] `webui/backend/lib/schedule_schema.py` - Dataclasses (EventPattern, Schedule with embedded patterns)
- [ ] `webui/backend/lib/schedule_storage.py` - Single-file storage (CONFIG_DIR/schedules/)
- [ ] `webui/backend/lib/cron_bridge.py` - Schedule → cron + RTC
- [ ] `webui/backend/lib/moon_phase.py` - Moon calculations (astral)
- [ ] `webui/backend/lib/solar_time.py` - Solar calculations (astral)
- [ ] `webui/backend/lib/schedule_conflict.py` - Overlap detection
- [ ] `webui/backend/lib/schedule_preview.py` - Execution preview generation
- [ ] `webui/backend/lib/sensor_reader.py` - I2C sensor reading for pre-conditions

**Backend - Services (2 files)**:
- [ ] `webui/backend/services/scheduler_service.py` - CRUD + activation + preview
- [ ] `webui/backend/services/sensor_service.py` - Pre-condition evaluation

**Backend - Routes (1 file)**:
- [ ] `webui/backend/routes/scheduler_ui.py` - All scheduler endpoints

**Backend - Built-in Schedules (4 files)**:
- [ ] `webui/backend/presets_builtin/schedules/nightly_hourly.json` - UV capture every hour 1am-6am
- [ ] `webui/backend/presets_builtin/schedules/full_moon_survey.json` - Full moon ±2 days
- [ ] `webui/backend/presets_builtin/schedules/twilight_transect.json` - Dawn/dusk transects
- [ ] `webui/backend/presets_builtin/schedules/continuous_monitoring.json` - 30-min intervals sunset-sunrise

**Frontend - Context & Hooks (3 files)**:
- [ ] `webui/frontend/src/contexts/SchedulerContext.jsx`
- [ ] `webui/frontend/src/hooks/useSchedules.js` - Schedule CRUD
- [ ] `webui/frontend/src/hooks/useMoonPhases.js`

**Frontend - Pages (1 file)**:
- [ ] `webui/frontend/src/pages/SchedulerUI.jsx`

**Frontend - Components (~20 files)**:
- [ ] `webui/frontend/src/components/scheduler/SchedulerHeader.jsx`
- [ ] `webui/frontend/src/components/scheduler/SchedulerToolbar.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleList/ScheduleList.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleList/ScheduleCard.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleList/ActiveScheduleBadge.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/ScheduleEditor.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/EventPatternEditor.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/ActionList.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/ActionForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/OffsetTimeline.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/TriggerForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/IntervalTriggerForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/SolarTriggerForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/MoonPhaseTriggerForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/ScheduleEditor/SensorTriggerForm.jsx`
- [ ] `webui/frontend/src/components/scheduler/CalendarView/CalendarView.jsx`
- [ ] `webui/frontend/src/components/scheduler/CalendarView/ExecutionTimeline.jsx`
- [ ] `webui/frontend/src/components/scheduler/CalendarView/MoonPhaseOverlay.jsx`
- [ ] `webui/frontend/src/components/scheduler/ConflictResolver/ConflictWarningBanner.jsx`
- [ ] `webui/frontend/src/components/scheduler/ExpertMode/CronExpressionInput.jsx`

**Tests (~18 files)**:
- [ ] `Tests/unit/test_cron_security.py` *(Phase 0)*
- [ ] `Tests/unit/test_schedule_schema.py`
- [ ] `Tests/unit/test_schedule_storage.py`
- [ ] `Tests/unit/test_moon_phase.py`
- [ ] `Tests/unit/test_solar_time.py`
- [ ] `Tests/unit/test_scheduler_service.py`
- [ ] `Tests/unit/test_schedule_conflict.py`
- [ ] `Tests/unit/test_schedule_preview.py`
- [ ] `Tests/unit/test_cron_bridge.py`
- [ ] `Tests/unit/test_sensor_reader.py`
- [ ] `Tests/unit/test_sensor_service.py`
- [ ] `Tests/unit/test_scheduler_ui_api.py`
- [ ] `Tests/integration/test_scheduler_workflow.py`
- [ ] `Tests/integration/test_scheduler_activation.py`
- [ ] `Tests/integration/test_sensor_workflow.py`
- [ ] `Tests/performance/test_scheduler_performance.py`
- [ ] `webui/frontend/e2e/tests/scheduler-schedules.spec.js`
- [ ] `webui/frontend/e2e/tests/scheduler-calendar.spec.js`

**Total: ~45 new files**

**Existing files to modify (7 files)**:
- [ ] `webui/backend/requirements.txt` - Add `astral>=3.2`
- [ ] `webui/backend/routes/scheduler.py` - *(Phase 0)* Import from `lib/cron_security.py`
- [ ] `webui/backend/app.py` - Register scheduler_ui blueprint
- [ ] `webui/frontend/src/App.jsx` - Add /scheduler route
- [ ] `webui/frontend/src/utils/queryKeys.js` - Add SCHEDULE_* keys
- [ ] `webui/frontend/src/utils/api.js` - Add schedule API functions
- [ ] `mothbox_paths.py` - Add SCHEDULES_DIR
- [ ] `CLAUDE.md` - Add Scheduler system documentation

### Configuration Checklist

- [ ] Add to `webui/backend/requirements.txt`: `astral>=3.2`
- [ ] Add to `mothbox_paths.py`: `SCHEDULES_DIR = CONFIG_DIR / "schedules"`
- [ ] Add to `constants.py`: Scheduler constants
- [ ] Create directory: `CONFIG_DIR/schedules/`

### Documentation Checklist

- [ ] `webui/docs/dev/api/scheduler.md` - API documentation
- [ ] `webui/docs/SCHEDULER_USER_GUIDE.md` - User guide
- [ ] Update `CLAUDE.md` - Add Scheduler system section
