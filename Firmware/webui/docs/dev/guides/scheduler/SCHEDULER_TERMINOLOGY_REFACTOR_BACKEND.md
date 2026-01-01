# Scheduler Terminology Refactor - Backend Implementation

**Purpose**: Step-by-step guide for implementing backend schema and service changes.

**Prerequisites**: Read [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) first for architecture context.

**Next Steps**: [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md) or [Testing](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)

> **TDD Workflow**: Before implementing each step below, follow the TDD protocol in
> [Testing Strategy → TDD Approach](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#tdd-approach-with-e2e-phases).
> Write tests first, run them (expect failure), implement the change, run tests again (expect pass).

---

## Table of Contents

1. [Integration Points](#integration-points)
2. [Implementation Steps](#implementation-steps)
   - [Step 1: Rename Action Class](#step-1-rename-action-class)
   - [Step 2: Create Trigger Union Type](#step-2-create-trigger-union-type)
   - [Step 3: Create Routine Class](#step-3-create-routine-class)
   - [Step 4: Update Schedule Class](#step-4-update-schedule-class)
   - [Step 5: Update Validation Functions](#step-5-update-validation-functions)
   - [Step 6: Update Cron Bridge](#step-6-update-cron-bridge)
   - [Step 7: Update Conflict Detection](#step-7-update-conflict-detection)
   - [Step 8: Create Built-in Schedules](#step-8-create-built-in-schedules)
3. [API Updates](#api-updates)

---

## Integration Points

### schedule_schema.py

**File**: `webui/backend/lib/schedule_schema.py`

#### Current PatternAction (lines 170-222)

```python
@dataclass
class PatternAction:
    """A single action within an event pattern."""
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
```

**Rename to**: `Action` (same structure, just rename class)

#### Current EventPattern (lines 230-307)

```python
@dataclass
class EventPattern:
    """A reusable event pattern with actions."""
    pattern_id: str
    name: str
    description: str = ""
    actions: list[PatternAction] = field(default_factory=list)
    category: str = "user"
    tags: list[str] = field(default_factory=list)
```

**Transform to**: `Routine` with embedded trigger (see Step 3)

#### Current Schedule (lines 587-950)

Key fields to REMOVE from Schedule:
- `trigger_type`
- `interval_trigger`, `solar_trigger`, `moon_phase_trigger`, `fixed_time_trigger`, `sensor_trigger`, `cron_trigger`
- `start_date`, `end_date`, `days_of_week`

Key fields to ADD/CHANGE:
- `event_patterns` → `routines: list[Routine]`

#### Trigger Classes (lines 371-578)

Keep all 6 existing trigger types and add RecurringDaysTrigger:
- `IntervalTrigger` (lines 372-403)
- `SolarTrigger` (lines 407-438)
- `MoonPhaseTrigger` (lines 442-475)
- `FixedTimeTrigger` (lines 479-506)
- `SensorTrigger` (lines 510-554) - Implemented as pre-conditions
- `CronTrigger` (lines 558-578)
- `RecurringDaysTrigger` (NEW) - For "every N days" patterns

### cron_bridge.py

**File**: `webui/backend/lib/cron_bridge.py`

#### Current schedule_to_cron() (lines 1047-1141)

Currently routes by `schedule.trigger_type` to helper functions.

**New approach**: Iterate `schedule.routines`, each routine has its own trigger.

#### Current get_next_events() (lines 1149-1204)

**Rename to**: `preview_schedule()`

### schedule_conflict.py

**File**: `webui/backend/lib/schedule_conflict.py`

#### PatternExecution (lines 100-137)

Rename field: `pattern_id` → `routine_id`, `pattern_name` → `routine_name`

#### generate_pattern_executions() (lines 618-715)

Rename to `generate_routine_executions()`. Update to iterate `schedule.routines`.

### schedule_storage.py

**File**: `webui/backend/lib/schedule_storage.py`

Minimal changes - storage is JSON-agnostic. Just update any references to `event_patterns` field name.

### scheduler_service.py

**File**: `webui/backend/services/scheduler_service.py`

Add one-active-schedule enforcement functions (see Step 4).

### routes/scheduler_ui.py

**File**: `webui/backend/routes/scheduler_ui.py`

**Endpoints to REMOVE**:
- `GET /patterns/builtin` - Pattern library replaced by built-in schedules
- `POST /patterns/validate` - Validation happens through schedule endpoints

**Endpoints to ADD**:
- `GET /schedules/builtin` - Load built-in schedule templates
- `POST /schedules/{id}/activate` - Activate a schedule (deactivating others)
- `POST /schedules/{id}/deactivate` - Deactivate a schedule

---

## Implementation Steps

> **TDD Protocol**: Each step below follows the TDD workflow. For complete test fixtures,
> class rename mappings, and pytest commands, see:
> **[Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)**
>
> Key sections:
> - [Unit Tests to Update](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#unit-tests-to-update) - Test class renames
> - [Complete Test Fixtures](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#complete-test-fixtures) - All 7 trigger fixtures
> - [New Tests to Add](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#new-tests-to-add) - Auto-name, validation tests

### Step 1: Rename Action Class

**File**: `webui/backend/lib/schedule_schema.py`

```python
# OLD
@dataclass
class PatternAction:
    """A single action within an event pattern."""
    ...

# NEW
@dataclass
class Action:
    """A single action within a routine."""
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
    def from_dict(cls, data: dict) -> "Action":
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
        )
```

#### TDD Reference
See [Testing → Unit Tests to Update → test_schedule_schema.py](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#unit-tests-to-update) for `TestPatternAction` → `TestAction` rename.

### Step 2: Create Trigger Union Type

**File**: `webui/backend/lib/schedule_schema.py`

**Location**: After CronTrigger class, add RecurringDaysTrigger and union type:

```python
@dataclass
class RecurringDaysTrigger:
    """Trigger that fires every N days at a specific time."""
    trigger_type: str = "recurring_days"
    every_n_days: int = 1          # e.g., 3 for every 3 days
    time: str = "00:00"            # "HH:MM" format
    start_date: str | None = None  # When to start counting (optional)

    def to_dict(self) -> dict:
        return {
            "trigger_type": self.trigger_type,
            "every_n_days": self.every_n_days,
            "time": self.time,
            "start_date": self.start_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecurringDaysTrigger":
        return cls(
            every_n_days=data.get("every_n_days", 1),
            time=data.get("time", "00:00"),
            start_date=data.get("start_date"),
        )


from typing import Union

# Trigger union type for Routine
Trigger = Union[
    IntervalTrigger,
    SolarTrigger,
    MoonPhaseTrigger,
    FixedTimeTrigger,
    SensorTrigger,
    CronTrigger,
    RecurringDaysTrigger,
]

def trigger_from_dict(data: dict) -> Trigger:
    """Create appropriate trigger from dictionary."""
    trigger_type = data.get("trigger_type")

    if trigger_type == "interval":
        return IntervalTrigger.from_dict(data)
    elif trigger_type == "solar":
        return SolarTrigger.from_dict(data)
    elif trigger_type == "moon_phase":
        return MoonPhaseTrigger.from_dict(data)
    elif trigger_type == "fixed_time":
        return FixedTimeTrigger.from_dict(data)
    elif trigger_type == "sensor":
        return SensorTrigger.from_dict(data)
    elif trigger_type == "cron":
        return CronTrigger.from_dict(data)
    elif trigger_type == "recurring_days":
        return RecurringDaysTrigger.from_dict(data)
    else:
        raise ValueError(f"Unknown trigger_type: {trigger_type}")
```

#### TDD Reference
See [Testing → Complete Test Fixtures](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#complete-test-fixtures) for `RecurringDaysTrigger` and trigger union fixtures.

### Step 3: Create Routine Class

**File**: `webui/backend/lib/schedule_schema.py`

**Location**: Replace EventPattern class

```python
# Action display name mapping
ACTION_DISPLAY_NAMES = {
    "attract_on": "Attract On",
    "attract_off": "Attract Off",
    "flash_on": "Flash On",
    "flash_off": "Flash Off",
    "takephoto": "Photo",
    "gps_sync": "GPS Sync",
    "backup": "Backup",
    "update_display": "Update Display",
}


@dataclass
class Routine:
    """
    A routine with its own trigger and actions.

    Each routine runs independently based on its trigger configuration.

    Attributes:
        routine_id: Unique identifier (auto-generated if empty)
        name: Display name (auto-generated from trigger+actions if None)
        trigger: When this routine runs
        actions: What happens when routine triggers
        pre_condition: Optional sensor check before execution
        description: Optional description
    """
    routine_id: str
    name: str | None
    trigger: Trigger
    actions: list[Action] = field(default_factory=list)
    pre_condition: SensorTrigger | None = None
    description: str = ""

    def __post_init__(self):
        if not self.routine_id:
            self.routine_id = str(uuid.uuid4())
        # Normalize empty string name to None for auto-generation
        if self.name == "":
            self.name = None

    @property
    def duration_minutes(self) -> int:
        """Calculate routine duration from max action offset."""
        if not self.actions:
            return 0
        return max(action.offset_minutes for action in self.actions)

    def get_display_name(self) -> str:
        """Get display name, auto-generating if not set."""
        if self.name:
            return self.name
        return self._generate_name()

    def _generate_name(self) -> str:
        """Generate name from trigger and actions."""
        action_summary = self._summarize_actions()
        trigger_desc = self._describe_trigger()
        return f"{action_summary} {trigger_desc}"

    def _summarize_actions(self) -> str:
        """Summarize actions for display name.

        Edge case handling:
        - Empty actions: Returns "Empty"
        - Single action: Returns display name (e.g., "Attract On")
        - Duplicate actions: Counts and formats (e.g., "3x Photo")
        - Common patterns: Flash+Photo, etc.
        - Fallback: "{N} Actions" or "Routine {id[:8]}" if all else fails
        """
        if not self.actions:
            return "Empty"

        action_names = [a.action_name for a in self.actions]

        # Handle duplicates: count identical action names
        from collections import Counter
        counts = Counter(action_names)

        # If all actions are the same, use count format
        if len(counts) == 1:
            name, count = list(counts.items())[0]
            display = ACTION_DISPLAY_NAMES.get(name, name.replace("_", " ").title())
            if count > 1:
                return f"{count}x {display}"
            return display

        # Common patterns
        if action_names == ["attract_on"]:
            return "Attract On"
        if action_names == ["attract_off"]:
            return "Attract Off"
        if "takephoto" in action_names and "flash_on" in action_names:
            return "Flash + Photo"
        if action_names == ["takephoto"]:
            return "Photo"
        if action_names == ["backup"]:
            return "Backup"
        if action_names == ["gps_sync"]:
            return "GPS Sync"

        # Generic fallback
        if len(action_names) > 0:
            return f"{len(action_names)} Actions"

        # Ultimate fallback using routine ID
        return f"Routine {self.routine_id[:8]}"

    def _describe_trigger(self) -> str:
        """Describe trigger for display name."""
        trigger = self.trigger
        trigger_type = getattr(trigger, "trigger_type", None)

        if trigger_type == "solar":
            event = getattr(trigger, "solar_event", "solar")
            return f"at {event.replace('_', ' ').title()}"
        elif trigger_type == "interval":
            minutes = getattr(trigger, "interval_minutes", 0)
            return f"every {minutes}min"
        elif trigger_type == "fixed_time":
            time = getattr(trigger, "time", "00:00")
            return f"at {time}"
        elif trigger_type == "moon_phase":
            phases = getattr(trigger, "phases", [])
            return f"on {', '.join(phases)}"
        elif trigger_type == "cron":
            return "(cron)"
        elif trigger_type == "recurring_days":
            days = getattr(trigger, "every_n_days", 1)
            time = getattr(trigger, "time", "00:00")
            return f"every {days} days at {time}"
        elif trigger_type == "sensor":
            # Used for pre_condition descriptions (not primary triggers)
            sensor = getattr(trigger, "sensor_type", "sensor")
            condition = getattr(trigger, "condition", "triggers")
            threshold = getattr(trigger, "threshold", "")
            # Format: "when light below 100" or "when temperature above 25"
            return f"when {sensor} {condition} {threshold}"
        else:
            return ""

    def to_dict(self) -> dict:
        result = {
            "routine_id": self.routine_id,
            "name": self.name,
            "trigger": self.trigger.to_dict(),
            "actions": [a.to_dict() for a in self.actions],
            "description": self.description,
        }
        if self.pre_condition:
            result["pre_condition"] = self.pre_condition.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Routine":
        pre_condition = None
        if "pre_condition" in data and data["pre_condition"]:
            pre_condition = SensorTrigger.from_dict(data["pre_condition"])

        return cls(
            routine_id=data.get("routine_id", ""),
            name=data.get("name"),
            trigger=trigger_from_dict(data["trigger"]),
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            pre_condition=pre_condition,
            description=data.get("description", ""),
        )
```

#### TDD Reference
See [Testing → New Tests to Add → Auto-Generated Name Tests](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#auto-generated-name-tests) for `TestRoutine` patterns.

### Step 4: Update Schedule Class

**File**: `webui/backend/lib/schedule_schema.py`

Remove trigger fields, update to use routines:

```python
@dataclass
class Schedule:
    """
    A complete schedule containing routines.

    Only one schedule can be active at a time. Each routine within
    the schedule has its own trigger configuration.
    """
    schedule_id: str
    name: str
    description: str = ""
    routines: list[Routine] = field(default_factory=list)
    enabled: bool = True
    is_active: bool = False
    created_at: str = ""
    modified_at: str = ""
    modified_by: str = ""

    # Deployment integration (optional)
    deployment_id: str | None = None
    create_deployment: bool = False

    def __post_init__(self):
        if not self.schedule_id:
            self.schedule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.modified_at:
            self.modified_at = now

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "routines": [r.to_dict() for r in self.routines],
            "enabled": self.enabled,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "modified_by": self.modified_by,
            "deployment_id": self.deployment_id,
            "create_deployment": self.create_deployment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            schedule_id=data.get("schedule_id", ""),
            name=data["name"],
            description=data.get("description", ""),
            routines=[Routine.from_dict(r) for r in data.get("routines", [])],
            enabled=data.get("enabled", True),
            is_active=data.get("is_active", False),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            modified_by=data.get("modified_by", ""),
            deployment_id=data.get("deployment_id"),
            create_deployment=data.get("create_deployment", False),
        )
```

**Add to scheduler_service.py** - One-active-schedule enforcement:

```python
def activate_schedule(schedule_id: str) -> Schedule:
    """Activate a schedule, deactivating any currently active schedule."""
    # Deactivate current active schedule (if any)
    current = get_active_schedule()
    if current and current.schedule_id != schedule_id:
        current.is_active = False
        save_schedule(current)
        logger.info(f"Deactivated schedule: {current.name}")

    # Activate requested schedule
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise ScheduleNotFoundError(f"Schedule not found: {schedule_id}")

    schedule.is_active = True
    save_schedule(schedule)
    logger.info(f"Activated schedule: {schedule.name}")

    # Generate and apply cron entries (5-year pre-computation)
    result = schedule_to_cron(schedule, latitude, longitude)
    apply_to_system(result.entries, schedule.schedule_id)

    return schedule


def deactivate_schedule(schedule_id: str) -> Schedule:
    """Deactivate a schedule."""
    schedule = get_schedule(schedule_id)
    if schedule is None:
        raise ScheduleNotFoundError(f"Schedule not found: {schedule_id}")

    schedule.is_active = False
    save_schedule(schedule)
    logger.info(f"Deactivated schedule: {schedule.name}")

    # Clear cron entries if this was the active schedule
    clear_schedule_cron_entries()

    return schedule


def get_active_schedule() -> Schedule | None:
    """Get the currently active schedule, if any."""
    all_schedules = list_schedules()
    for schedule in all_schedules:
        if schedule.is_active:
            return schedule
    return None
```

#### TDD Reference
See [Testing → Unit Tests to Update](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#unit-tests-to-update) for `TestSchedule` and service layer updates.

### Step 5: Update Validation Functions

**File**: `webui/backend/lib/schedule_schema.py`

```python
# Validation constants
MAX_SCHEDULE_NAME_LENGTH = 100
MAX_ROUTINES_PER_SCHEDULE = 50
MAX_ACTIONS_PER_ROUTINE = 20
MAX_ROUTINE_NAME_LENGTH = 100
MAX_ACTION_DESCRIPTION_LENGTH = 500


def validate_action(action: Action) -> tuple[bool, str | None]:
    """Validate a single action."""
    if action.action_type not in ACTION_TYPES:
        return False, f"Invalid action type: '{action.action_type}'"
    # Existing validation logic...
    return True, None


def validate_routine(routine: Routine) -> tuple[bool, str | None]:
    """Validate a routine with its trigger and actions."""
    # Validate routine_id
    if not routine.routine_id:
        return False, "Routine must have a routine_id"

    # Validate trigger exists
    if not routine.trigger:
        return False, "Routine must have a trigger"

    # Sensor triggers are pre-conditions only, not primary triggers
    if getattr(routine.trigger, "trigger_type", None) == "sensor":
        return False, "Sensor triggers can only be used as pre_condition, not as primary trigger"

    # Validate trigger
    trigger_valid, trigger_error = _validate_trigger(routine.trigger)
    if not trigger_valid:
        return False, f"Invalid trigger: {trigger_error}"

    # Validate pre_condition (optional)
    if routine.pre_condition:
        pre_valid, pre_error = validate_sensor_trigger(routine.pre_condition)
        if not pre_valid:
            return False, f"Invalid pre_condition: {pre_error}"

    # Validate actions
    if not routine.actions:
        return False, "Routine must have at least one action"

    if len(routine.actions) > MAX_ACTIONS_PER_ROUTINE:
        return False, f"Routine exceeds maximum of {MAX_ACTIONS_PER_ROUTINE} actions"

    for i, action in enumerate(routine.actions):
        valid, error = validate_action(action)
        if not valid:
            return False, f"Action {i}: {error}"

    return True, None


def _validate_trigger(trigger: Trigger) -> tuple[bool, str | None]:
    """Validate any trigger type."""
    trigger_type = getattr(trigger, "trigger_type", None)

    if trigger_type == "interval":
        return validate_interval_trigger(trigger)
    elif trigger_type == "solar":
        return validate_solar_trigger(trigger)
    elif trigger_type == "moon_phase":
        return validate_moon_phase_trigger(trigger)
    elif trigger_type == "fixed_time":
        return validate_fixed_time_trigger(trigger)
    elif trigger_type == "sensor":
        return validate_sensor_trigger(trigger)
    elif trigger_type == "cron":
        return validate_cron_trigger(trigger)
    elif trigger_type == "recurring_days":
        return validate_recurring_days_trigger(trigger)
    else:
        return False, f"Unknown trigger type: {trigger_type}"


def validate_recurring_days_trigger(trigger: RecurringDaysTrigger) -> tuple[bool, str | None]:
    """Validate a recurring days trigger."""
    import re

    # Validate every_n_days range
    if trigger.every_n_days < 1 or trigger.every_n_days > 365:
        return False, "every_n_days must be between 1 and 365"

    # Validate time format (HH:MM)
    if not re.match(r"^\d{2}:\d{2}$", trigger.time):
        return False, "time must be in HH:MM format"

    # Validate time values
    hours, minutes = map(int, trigger.time.split(":"))
    if hours < 0 or hours > 23:
        return False, "hours must be between 00 and 23"
    if minutes < 0 or minutes > 59:
        return False, "minutes must be between 00 and 59"

    # Validate start_date if provided (ISO format)
    if trigger.start_date:
        try:
            datetime.fromisoformat(trigger.start_date.replace("Z", "+00:00"))
        except ValueError:
            return False, "start_date must be in ISO 8601 format"

    return True, None


def validate_time_window(window: TimeWindow) -> tuple[bool, str | None]:
    """Validate a time window."""
    if not window:
        return True, None  # Optional field

    # Reject ambiguous same start/end time
    if window.start_time == window.end_time:
        return False, "start_time and end_time cannot be identical (ambiguous: zero-length or 24-hour?)"

    # Validate format: either HH:MM or solar event name
    import re
    valid_solar_events = {
        "sunrise", "sunset", "dawn", "dusk",
        "nautical_dawn", "nautical_dusk",
        "astronomical_dawn", "astronomical_dusk",
        "noon", "midnight"
    }
    time_pattern = re.compile(r"^\d{2}:\d{2}$")

    for field_name, value in [("start_time", window.start_time), ("end_time", window.end_time)]:
        if value not in valid_solar_events and not time_pattern.match(value):
            return False, f"{field_name} must be HH:MM format or a solar event name"

    return True, None


def validate_routine_ids_unique(schedule: Schedule) -> tuple[bool, str | None]:
    """Ensure all routine IDs within a schedule are unique."""
    if not schedule.routines:
        return True, None

    routine_ids = [r.routine_id for r in schedule.routines]

    if len(routine_ids) != len(set(routine_ids)):
        seen = set()
        duplicates = set()
        for rid in routine_ids:
            if rid in seen:
                duplicates.add(rid)
            seen.add(rid)
        return False, f"Duplicate routine IDs: {sorted(duplicates)}"

    return True, None


def validate_schedule(schedule: Schedule) -> tuple[bool, str | None]:
    """Validate a complete schedule."""
    # Validate name
    if not schedule.name or not schedule.name.strip():
        return False, "Schedule name is required"

    if len(schedule.name) > MAX_SCHEDULE_NAME_LENGTH:
        return False, f"Schedule name exceeds {MAX_SCHEDULE_NAME_LENGTH} characters"

    # Validate routines
    if not schedule.routines:
        return False, "Schedule must have at least one routine"

    if len(schedule.routines) > MAX_ROUTINES_PER_SCHEDULE:
        return False, f"Schedule exceeds maximum of {MAX_ROUTINES_PER_SCHEDULE} routines"

    # Validate routine ID uniqueness
    unique_valid, unique_error = validate_routine_ids_unique(schedule)
    if not unique_valid:
        return False, unique_error

    for i, routine in enumerate(schedule.routines):
        valid, error = validate_routine(routine)
        if not valid:
            return False, f"Routine {i}: {error}"

    return True, None
```

#### TDD Reference
See [Testing → New Tests to Add → Validation Tests](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#validation-tests) for routine ID uniqueness tests.

### Step 6: Update Cron Bridge

**File**: `webui/backend/lib/cron_bridge.py`

#### Unified Date-Specific Cron Generation

All trigger types are converted to **date-specific cron entries** at activation time, pre-computed for 5 years ahead. This unified approach:

1. Handles solar/moon events that vary daily
2. Supports RecurringDaysTrigger ("every N days") which standard cron cannot express
3. Enables offline operation - no GPS/internet needed at execution time
4. Simplifies code with a uniform approach for all triggers

#### Execution Time Calculator Cross-References

The `calculate_execution_times()` function dispatches to trigger-specific calculators. These implementations follow existing patterns in `cron_bridge.py`:

| Trigger Type | Calculator Function | Reference Implementation |
|--------------|---------------------|--------------------------|
| `interval` | `_calculate_interval_times()` | `cron_bridge.py::interval_trigger_to_cron()`, `_get_events_interval()` |
| `fixed_time` | `_calculate_fixed_time_times()` | `cron_bridge.py::fixed_time_trigger_to_cron()`, `_get_events_fixed_time()` |
| `solar` | `_calculate_solar_times()` | `cron_bridge.py::solar_trigger_to_cron()`, `_get_events_solar()`, `get_solar_execution_time()` |
| `moon_phase` | `_calculate_moon_phase_times()` | `cron_bridge.py::moon_phase_trigger_to_cron()`, `_get_events_moon_phase()` |
| `recurring_days` | `_calculate_recurring_days_times()` | New - similar to `fixed_time` but with day counting from `start_date` |
| `cron` | `_calculate_cron_times()` | `cron_bridge.py::cron_trigger_to_cron()` - parse with `croniter` library |

Each calculator returns a `list[datetime]` of execution times for the specified period.

#### TimeWindow Algorithm Summary

**TimeWindow Solar Resolution:**
- Solar event strings (`"sunrise"`, `"sunset"`, `"civil_dawn"`, `"dusk"`, etc.) are resolved to actual times using the device's configured latitude/longitude
- Resolution happens at cron generation time, not runtime
- See `cron_bridge.py::get_solar_execution_time()` for implementation

**Overnight Windows:**
- When `end_time < start_time` (e.g., `"22:00"` to `"06:00"`), the window is automatically treated as overnight
- The codebase detects this in `_generate_execution_times()` (lines 253-255) and `schedule_conflict.py` (lines 497-499)
- No explicit `is_overnight` flag needed

**Polar Edge Cases:**
- When a solar event doesn't occur (polar day/night), that day is skipped with a warning log
- See `get_solar_execution_time()` - returns `None` when solar event is unavailable
- The `_calculate_solar_times()` function catches this and logs: `"Solar event '{event}' not available on {date} at lat {latitude}"`

**Same-Time Validation:**
- `start_time == end_time` is rejected as invalid (ambiguous: zero-length or 24-hour?)
- If a user wants "all day", they should omit the time window entirely

#### Update schedule_to_cron()

```python
def schedule_to_cron(
    schedule: Schedule,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
    years_ahead: int = 5,
) -> CronBridgeResult:
    """Convert Schedule to date-specific cron entries.

    Pre-computes all execution times for the next N years.
    Each entry targets a specific date/time rather than a repeating pattern.
    """
    result = CronBridgeResult(
        entries=[],
        schedule_id=schedule.schedule_id,
        errors=[],
    )

    if not schedule.enabled or not schedule.routines:
        return result

    all_entries = []

    for routine in schedule.routines:
        try:
            entries = routine_to_dated_cron(
                routine=routine,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                years_ahead=years_ahead,
            )
            all_entries.extend(entries)
        except Exception as e:
            result.errors.append(f"Routine '{routine.get_display_name()}': {str(e)}")

    result.entries = all_entries
    return result


def routine_to_dated_cron(
    routine: Routine,
    latitude: float,
    longitude: float,
    timezone_name: str = "UTC",
    years_ahead: int = 5,
) -> list[CronEntry]:
    """Convert a single Routine to date-specific cron entries.

    All trigger types use the same output format: specific dates.
    """
    # Calculate all execution times for this routine's trigger
    execution_times = calculate_execution_times(
        trigger=routine.trigger,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
        years_ahead=years_ahead,
    )

    entries = []
    for exec_time in execution_times:
        for action in routine.actions:
            action_time = exec_time + timedelta(minutes=action.offset_minutes)
            entries.append(CronEntry(
                expression=datetime_to_cron(action_time),
                command=build_action_command(action),
                comment=f"Routine: {routine.routine_id} ({action_time.date().isoformat()})",
                routine_id=routine.routine_id,
                execution_time=action_time,
            ))

    return entries


def datetime_to_cron(dt: datetime) -> str:
    """Convert datetime to date-specific cron expression."""
    return f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"


def calculate_execution_times(
    trigger: Trigger,
    latitude: float,
    longitude: float,
    timezone_name: str,
    years_ahead: int,
) -> list[datetime]:
    """Calculate all execution times for a trigger over the given period.

    Dispatches to trigger-specific calculators but all return
    a flat list of datetime objects.
    """
    trigger_type = getattr(trigger, "trigger_type", None)

    if trigger_type == "interval":
        return _calculate_interval_times(trigger, years_ahead)
    elif trigger_type == "fixed_time":
        return _calculate_fixed_time_times(trigger, years_ahead)
    elif trigger_type == "solar":
        return _calculate_solar_times(trigger, latitude, longitude, timezone_name, years_ahead)
    elif trigger_type == "moon_phase":
        return _calculate_moon_phase_times(trigger, years_ahead)
    elif trigger_type == "recurring_days":
        return _calculate_recurring_days_times(trigger, years_ahead)
    elif trigger_type == "cron":
        return _calculate_cron_times(trigger, years_ahead)
    elif trigger_type == "sensor":
        logger.warning("Sensor triggers are pre-conditions only, not schedulable")
        return []
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")
```

**Size considerations:**
- Typical overnight survey: ~60,000 entries over 5 years
- Crontab size: ~6MB (acceptable for Pi storage)
- Re-activation required after 5 years or on location change

#### RecurringDaysTrigger Algorithm

The `RecurringDaysTrigger` handles "every N days" patterns which cannot be expressed in standard cron syntax. The algorithm calculates specific dates from a start date:

```python
def _calculate_recurring_days_times(
    trigger: RecurringDaysTrigger,
    years_ahead: int,
    from_date: date | None = None,
) -> list[datetime]:
    """Calculate execution times for a recurring days trigger.

    Algorithm:
    1. Determine start date (trigger.start_date or today)
    2. Parse execution time from trigger.time (HH:MM)
    3. Calculate all dates from start through end of period
    4. Filter to only dates where (current - start) % every_n_days == 0

    Args:
        trigger: RecurringDaysTrigger with every_n_days, time, start_date
        years_ahead: How many years to pre-compute
        from_date: Override start date (for testing)

    Returns:
        List of datetime objects for each execution

    Example:
        trigger = RecurringDaysTrigger(every_n_days=3, time="21:00", start_date="2025-01-01")
        # Returns: 2025-01-01 21:00, 2025-01-04 21:00, 2025-01-07 21:00, ...
    """
    from datetime import date, datetime, timedelta
    from zoneinfo import ZoneInfo

    times = []

    # Parse start date
    if trigger.start_date:
        start = date.fromisoformat(trigger.start_date)
    elif from_date:
        start = from_date
    else:
        start = date.today()

    # Parse execution time
    hours, minutes = map(int, trigger.time.split(":"))

    # Calculate end date (N years from start)
    end = start + timedelta(days=365 * years_ahead)

    # Generate all execution dates
    current = start
    while current <= end:
        # Check if this date matches the N-day pattern
        days_since_start = (current - start).days
        if days_since_start % trigger.every_n_days == 0:
            exec_time = datetime(
                current.year, current.month, current.day,
                hours, minutes, 0
            )
            times.append(exec_time)
        current += timedelta(days=1)

    return times
```

**Edge cases handled:**
- `start_date` not provided: uses today's date
- `every_n_days=1`: equivalent to daily (every day matches)
- `every_n_days=365`: annual (approximately yearly)
- Leap years: algorithm uses actual day counts, handles Feb 29 correctly

**Cron output format:**
Since standard cron cannot express "every N days", each execution becomes a date-specific entry:
```
# Routine: gps-sync-3day (2025-01-01)
0 21 1 1 * /opt/mothbox/bin/gps_sync.py
# Routine: gps-sync-3day (2025-01-04)
0 21 4 1 * /opt/mothbox/bin/gps_sync.py
# Routine: gps-sync-3day (2025-01-07)
0 21 7 1 * /opt/mothbox/bin/gps_sync.py
```

#### Progress Feedback (Required)

Schedule activation (5-year pre-computation) can take several seconds. Implement progress feedback via WebSocket:

```python
# In scheduler_service.py
def activate_schedule_with_progress(schedule_id: str, socketio) -> Schedule:
    """Activate schedule with progress events."""
    schedule = get_schedule(schedule_id)

    # Phase 1: Calculate execution times (longest phase)
    phases = ["calculating_solar", "calculating_moon", "calculating_intervals", "writing_crontab"]

    for i, phase in enumerate(phases):
        progress = int((i / len(phases)) * 100)
        socketio.emit("schedule:activation_progress", {
            "schedule_id": schedule_id,
            "phase": phase,
            "progress": progress,
        })
        # ... do phase work ...

    socketio.emit("schedule:activation_progress", {
        "schedule_id": schedule_id,
        "phase": "complete",
        "progress": 100,
    })

    return schedule
```

Frontend should display a progress bar during activation. See [Frontend → Progress UI Component](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md#activation-progress-ui).

#### Polar Latitude Edge Case

When calculating solar times at extreme latitudes (>66°), some events may not occur (polar day/night):

```python
def _calculate_solar_times(trigger, latitude, longitude, timezone_name, years_ahead):
    times = []
    for date in date_range:
        try:
            solar_time = get_solar_event(trigger.solar_event, date, latitude, longitude)
            times.append(solar_time)
        except ValueError as e:
            # Solar event doesn't occur on this date (polar day/night)
            logger.warning(
                f"Solar event '{trigger.solar_event}' not available on "
                f"{date.isoformat()} at lat {latitude}: {e}"
            )
            # Skip this day, don't fail the entire activation
            continue
    return times
```

#### Pre-Condition Wrapper Script

When a routine has a `pre_condition`, cron entries must check the sensor before executing:

```python
def build_action_command(action: Action, pre_condition: SensorTrigger | None = None) -> str:
    """Build command string for cron entry."""
    base_command = _get_action_script(action)  # e.g., "python3 TakePhoto.py"

    if pre_condition:
        # Wrap with pre-condition checker
        return (
            f"python3 /opt/mothbox/check_and_run.py "
            f"--sensor {pre_condition.sensor_type} "
            f"--op {pre_condition.condition} "
            f"--threshold {pre_condition.threshold} "
            f"-- {base_command}"
        )

    return base_command
```

The `check_and_run.py` script:
1. Reads sensor value using existing `sensor_reader.py`
2. Evaluates condition (above/below/equals threshold)
3. If met: executes the wrapped command
4. If not met: logs `WARNING: Pre-condition not met (light=250 >= 100), skipping: python3 TakePhoto.py`

**CronEntry structure (updated):**

```python
@dataclass
class CronEntry:
    expression: str          # e.g., "0 21 15 1 *" (date-specific)
    command: str             # Full command to execute
    comment: str = ""        # Routine name and date for debugging
    enabled: bool = True
    routine_id: str = ""     # Links back to source routine
    execution_time: datetime | None = None  # Exact execution time
```

#### Rename get_next_events() → preview_schedule()

```python
def preview_schedule(
    schedule: Schedule,
    count: int = 10,
    from_time: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
) -> list[dict]:
    """Preview upcoming schedule executions.

    Returns list of dicts with:
    - datetime: When action runs
    - action_type, action_name: What runs
    - routine_name, routine_id: Which routine
    """
    if from_time is None:
        from_time = datetime.now(timezone.utc)

    events = []

    for routine in schedule.routines:
        routine_events = _get_routine_events(
            routine=routine,
            count=count,
            from_time=from_time,
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
        )
        events.extend(routine_events)

    # Sort by datetime, take top N
    events.sort(key=lambda e: e["datetime"])
    return events[:count]
```

#### TDD Reference
See [Testing → Unit Tests to Update → test_cron_bridge.py](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#unit-tests-to-update) for `preview_schedule()` rename.

### Step 7: Update Conflict Detection

**File**: `webui/backend/lib/schedule_conflict.py`

#### Time Collision Detection (Blocking)

```python
@dataclass
class TimeCollision:
    """Represents two routines executing at the same time."""
    time: datetime
    routine_ids: list[str]
    message: str

    def to_dict(self) -> dict:
        return {
            "type": "time_collision",
            "time": self.time.isoformat(),
            "routine_ids": self.routine_ids,
            "message": self.message,
        }


def detect_time_collisions(
    schedule: Schedule,
    preview_days: int = 7,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[TimeCollision]:
    """
    Detect when two routines execute at exactly the same time.

    Returns list of collisions. These are BLOCKING ERRORS that prevent save.
    Only exact matches are flagged (no tolerance window).
    """
    # Generate execution times for all routines
    executions = []
    for routine in schedule.routines:
        routine_times = get_routine_execution_times(
            routine, preview_days, latitude, longitude
        )
        for exec_time in routine_times:
            executions.append((exec_time, routine.routine_id, routine.get_display_name()))

    # Sort by time and find exact matches
    executions.sort(key=lambda x: x[0])
    collisions = []

    for i in range(len(executions) - 1):
        if executions[i][0] == executions[i + 1][0]:
            collisions.append(TimeCollision(
                time=executions[i][0],
                routine_ids=[executions[i][1], executions[i + 1][1]],
                message=f"'{executions[i][2]}' and '{executions[i + 1][2]}' execute at identical time"
            ))

    return collisions
```

#### GPIO State Conflict Detection (Warning)

```python
@dataclass
class GpioConflict:
    """Represents a potential GPIO state issue."""
    routine_id: str
    action: str
    message: str

    def to_dict(self) -> dict:
        return {
            "type": "gpio_conflict",
            "routine_id": self.routine_id,
            "action": self.action,
            "message": self.message,
        }


def detect_gpio_state_conflicts(schedule: Schedule) -> list[GpioConflict]:
    """
    Analyze schedule for GPIO state conflicts (warnings only).

    Returns list of potential issues like:
    - Unbalanced on/off pairs
    - State left on at end of schedule window
    """
    gpio_pairs = {
        "attract_on": "attract_off",
        "flash_on": "flash_off",
        "uv_on": "uv_off",
    }

    conflicts = []

    for routine in schedule.routines:
        # Track GPIO actions within routine
        gpio_states = {}
        for action in routine.actions:
            if action.action_name in gpio_pairs:
                gpio_states[action.action_name] = action.offset_minutes
            elif action.action_name in gpio_pairs.values():
                # Check if corresponding "on" exists
                on_action = next(
                    (k for k, v in gpio_pairs.items() if v == action.action_name),
                    None
                )
                if on_action and on_action not in gpio_states:
                    conflicts.append(GpioConflict(
                        routine_id=routine.routine_id,
                        action=action.action_name,
                        message=f"'{action.action_name}' without prior '{on_action}'"
                    ))

        # Check for unclosed "on" states
        for on_action, off_action in gpio_pairs.items():
            if on_action in gpio_states:
                has_off = any(
                    a.action_name == off_action
                    for a in routine.actions
                    if a.offset_minutes > gpio_states[on_action]
                )
                if not has_off:
                    conflicts.append(GpioConflict(
                        routine_id=routine.routine_id,
                        action=on_action,
                        message=f"'{on_action}' without corresponding '{off_action}'"
                    ))

    return conflicts
```

#### Integration in Routes

```python
# In routes/scheduler_ui.py

@dataclass
class ValidationResult:
    time_collisions: list[TimeCollision]
    gpio_warnings: list[GpioConflict]


def detect_schedule_conflicts(schedule: Schedule) -> ValidationResult:
    """Run all conflict detection checks."""
    time_collisions = detect_time_collisions(schedule)
    gpio_warnings = detect_gpio_state_conflicts(schedule)

    return ValidationResult(
        time_collisions=time_collisions,
        gpio_warnings=gpio_warnings,
    )


@bp.route("/schedules", methods=["POST"])
def create_schedule():
    """Create a new schedule."""
    data = request.get_json()
    schedule = Schedule.from_dict(data)

    # Validate schema
    valid, error = validate_schedule(schedule)
    if not valid:
        return jsonify({"error": error}), 400

    # Detect conflicts BEFORE saving
    validation_result = detect_schedule_conflicts(schedule)

    # Time collisions are blocking errors
    if validation_result.time_collisions:
        return jsonify({
            "error": "Schedule has time collisions",
            "errors": [c.to_dict() for c in validation_result.time_collisions],
            "warnings": [w.to_dict() for w in validation_result.gpio_warnings],
        }), 400

    # GPIO conflicts are warnings (allow save)
    save_schedule(schedule)

    return jsonify({
        "schedule": schedule.to_dict(),
        "warnings": [w.to_dict() for w in validation_result.gpio_warnings],
    }), 201
```

#### TDD Reference
See [Testing → Unit Tests to Update → test_schedule_conflict_lib.py](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#unit-tests-to-update) for conflict detection tests.

### Step 8: Update Built-in Schedules to Schema 3.0

#### Current State

Built-in schedules exist in `webui/backend/presets_builtin/schedules/` but are in **schema 2.0 format**. These must be converted to 3.0 format as part of this refactor.

**Files to convert:**
- `nightly_moth_survey.json` → Primary example (overnight UV + photos)
- `dawn_dusk_survey.json` → Multi-routine example (solar triggers)
- `continuous_monitoring.json` → Simple interval example
- Other files as needed

**Conversion steps for each file:**
1. Change `schema_version` from `"2.0"` to `"3.0"`
2. Rename `event_patterns` → `routines`
3. Rename `pattern_id` → `routine_id` in each routine
4. Move trigger from schedule level into each routine (duplicating if multiple routines share same trigger)
5. Remove schedule-level trigger fields (`trigger_type`, `interval_trigger`, `solar_trigger`, etc.)
6. Remove `start_date`, `end_date`, `days_of_week` from schedule level
7. Add `is_builtin: true` flag

#### Built-in Schedule Loading Mechanism

Built-in schedules are loaded by `scheduler_service.py` from `presets_builtin/schedules/`. The service reads JSON files and returns them via `GET /schedules/builtin`. No separate preset manager is needed - direct file loading with LRU caching.

**Implementation in `scheduler_service.py`:**

```python
from functools import lru_cache
from pathlib import Path

BUILTIN_SCHEDULES_DIR = Path(__file__).parent.parent / "presets_builtin" / "schedules"


@lru_cache(maxsize=1)
def get_builtin_schedules() -> list[Schedule]:
    """Load all built-in schedule templates.

    Returns cached list of Schedule objects from JSON files.
    Files are read once and cached until service restart.
    """
    schedules = []

    if not BUILTIN_SCHEDULES_DIR.exists():
        logger.warning(f"Built-in schedules directory not found: {BUILTIN_SCHEDULES_DIR}")
        return schedules

    for json_file in BUILTIN_SCHEDULES_DIR.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
            schedule = Schedule.from_dict(data)
            schedules.append(schedule)
            logger.debug(f"Loaded built-in schedule: {schedule.name}")
        except Exception as e:
            logger.error(f"Failed to load built-in schedule {json_file}: {e}")

    return schedules


def is_builtin_schedule(schedule_id: str) -> bool:
    """Check if a schedule ID is a built-in schedule."""
    return any(s.schedule_id == schedule_id for s in get_builtin_schedules())
```

**Route implementation:**

```python
@bp.route("/schedules/builtin", methods=["GET"])
def list_builtin_schedules():
    """Get all built-in schedule templates."""
    schedules = get_builtin_schedules()
    return jsonify({
        "schedules": [s.to_dict() for s in schedules]
    })
```

**Immutability enforcement:**
- `PUT /schedules/{id}` returns 403 Forbidden for built-in schedules
- `DELETE /schedules/{id}` returns 403 Forbidden for built-in schedules
- Users must clone to customize (see Frontend doc for clone workflow)

#### Built-in Schedule JSON Files

**File**: `webui/backend/presets_builtin/schedules/overnight-moth-survey.json`

```json
{
  "schema_version": "3.0",
  "schedule_id": "overnight-moth-survey",
  "name": "Overnight Moth Survey",
  "description": "UV-attracted moth photography session from dusk to dawn",
  "enabled": true,
  "is_builtin": true,
  "created_at": "2025-01-01T00:00:00Z",
  "routines": [
    {
      "routine_id": "attract-on-dusk",
      "name": null,
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "dusk",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn on UV lights"
        }
      ]
    },
    {
      "routine_id": "photo-cycle",
      "name": null,
      "trigger": {
        "trigger_type": "interval",
        "interval_minutes": 15,
        "time_window": {
          "start_time": "22:00",
          "end_time": "06:00"
        }
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "flash_on",
          "offset_minutes": 0,
          "parameters": {}
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 1,
          "parameters": {}
        },
        {
          "action_type": "gpio",
          "action_name": "flash_off",
          "offset_minutes": 2,
          "parameters": {}
        }
      ]
    },
    {
      "routine_id": "attract-off-dawn",
      "name": null,
      "trigger": {
        "trigger_type": "solar",
        "solar_event": "dawn",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn off UV lights"
        }
      ]
    }
  ]
}
```

**File**: `webui/backend/presets_builtin/schedules/daytime-pollinator.json`

```json
{
  "schema_version": "3.0",
  "schedule_id": "daytime-pollinator",
  "name": "Daytime Pollinator",
  "description": "Daylight pollinator monitoring with photos every 30 minutes",
  "enabled": true,
  "is_builtin": true,
  "created_at": "2025-01-01T00:00:00Z",
  "routines": [
    {
      "routine_id": "daytime-photos",
      "name": null,
      "trigger": {
        "trigger_type": "interval",
        "interval_minutes": 30,
        "time_window": {
          "start_time": "sunrise",
          "end_time": "sunset"
        }
      },
      "actions": [
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 0,
          "parameters": {}
        }
      ]
    }
  ]
}
```

#### TDD Reference
See [Testing → Mixed Trigger Schedule Tests](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md#mixed-trigger-schedule-tests) for built-in schedule tests.

---

## API Updates

### Schedule Object (New Format)

```json
{
  "schedule_id": "string",
  "name": "string",
  "description": "string",
  "enabled": true,
  "is_active": false,
  "routines": [
    {
      "routine_id": "string",
      "name": "string | null",
      "display_name": "string",
      "trigger": {
        "trigger_type": "interval | solar | fixed_time | moon_phase | cron | recurring_days",
        "...trigger-specific fields..."
      },
      "actions": [
        {
          "action_type": "gpio | camera | gps_sync | service",
          "action_name": "string",
          "offset_minutes": 0,
          "parameters": {},
          "description": "string"
        }
      ],
      "pre_condition": {
        "trigger_type": "sensor",
        "sensor_type": "string",
        "sensor_id": "string",
        "condition": "above | below | equals | between",
        "threshold": 0
      },
      "description": "string"
    }
  ],
  "created_at": "ISO8601",
  "modified_at": "ISO8601"
}
```

**Notes on `display_name`:**
- Always computed server-side via `routine.get_display_name()`
- Returns explicit `name` if set, otherwise auto-generates from trigger + actions
- Frontend should use this value for display after saving (not compute locally)
- Read-only field - not accepted in POST/PUT requests

### Trigger Type JSON Examples

**IntervalTrigger**:
```json
{
  "trigger_type": "interval",
  "interval_minutes": 15,
  "time_window": { "start_time": "22:00", "end_time": "06:00" },
  "days_of_week": [0, 1, 2, 3, 4, 5, 6]
}
```

**SolarTrigger**:
```json
{
  "trigger_type": "solar",
  "solar_event": "dusk",
  "offset_minutes": 0,
  "days_of_week": null
}
```

**FixedTimeTrigger**:
```json
{
  "trigger_type": "fixed_time",
  "time": "09:00",
  "days_of_week": [0, 1, 2, 3, 4]
}
```

**MoonPhaseTrigger**:
```json
{
  "trigger_type": "moon_phase",
  "phases": ["full", "new"],
  "time_window": null,
  "offset_days": 0
}
```

**CronTrigger**:
```json
{
  "trigger_type": "cron",
  "cron_expression": "0 */2 * * *"
}
```

**RecurringDaysTrigger** (NEW):
```json
{
  "trigger_type": "recurring_days",
  "every_n_days": 3,
  "time": "21:00",
  "start_date": "2025-01-01"
}
```

### Endpoints

**Unchanged**:
- `GET /scheduler/ui/schedules` - List schedules
- `GET /scheduler/ui/schedules/{id}` - Get schedule
- `POST /scheduler/ui/schedules` - Create schedule
- `PUT /scheduler/ui/schedules/{id}` - Update schedule
- `DELETE /scheduler/ui/schedules/{id}` - Delete schedule
- `POST /scheduler/ui/schedules/{id}/activate` - Activate
- `POST /scheduler/ui/schedules/deactivate` - Deactivate

**Updated**:
- `GET /scheduler/ui/schedules/{id}/preview` - Now uses `preview_schedule()`

**Removed**:
- `GET /scheduler/ui/patterns/builtin` - Replaced by built-in schedules

**New**:
- `GET /scheduler/ui/schedules/builtin` - List built-in schedule templates

### Error Response Contracts

All API endpoints return consistent error responses with the following structure:

#### Validation Errors (400 Bad Request)

```json
{
  "error": "Validation failed",
  "details": "Schedule name is required",
  "field": "name"
}
```

#### Conflict Errors (400 Bad Request)

Returned when schedule has blocking conflicts (time collisions):

```json
{
  "error": "Schedule has time collisions",
  "errors": [
    {
      "type": "time_collision",
      "time": "2025-01-15T19:00:00",
      "routine_ids": ["routine-1", "routine-2"],
      "message": "'Take Photo every 15 min' and 'HDR Bracket' execute at identical time"
    }
  ],
  "warnings": [
    {
      "type": "gpio_conflict",
      "routine_id": "routine-3",
      "action": "attract_off",
      "message": "'attract_off' without prior 'attract_on'"
    }
  ]
}
```

**Note**: Warnings (GPIO state conflicts) are included but do NOT block save. Only `errors` block save.

#### Not Found Errors (404)

```json
{
  "error": "Schedule not found",
  "schedule_id": "non-existent-id"
}
```

#### Forbidden Errors (403)

Returned when trying to modify or delete built-in schedules:

```json
{
  "error": "Cannot modify built-in schedule",
  "schedule_id": "overnight-moth-survey",
  "hint": "Clone the schedule to customize it"
}
```

#### Activation Errors (409 Conflict)

Returned when activation fails due to another schedule being active:

```json
{
  "error": "Another schedule is already active",
  "active_schedule_id": "daytime-pollinator",
  "active_schedule_name": "Daytime Pollinator Survey",
  "hint": "Deactivate the current schedule first or use force=true"
}
```

**Note**: With `force=true` query parameter, the API will deactivate the current schedule and activate the new one without returning this error.

#### Pre-Condition Failures (at runtime)

When a routine has a pre-condition that is not met at execution time, no API error is returned. Instead, the action is skipped and logged:

```
WARNING: Pre-condition not met for routine 'daylight-photo' (light=50 < 500 required). Skipping actions.
```

This is logged to the system log, not returned via API.

### Success Response Contracts

#### Create/Update Schedule (201/200)

```json
{
  "schedule": {
    "schedule_id": "abc-123",
    "name": "My Schedule",
    "routines": [...],
    ...
  },
  "warnings": [
    {
      "type": "gpio_conflict",
      "routine_id": "routine-3",
      "action": "attract_off",
      "message": "'attract_off' without prior 'attract_on'"
    }
  ]
}
```

**Note**: Even on success, `warnings` may be present. Frontend should display these to the user.

#### Activate Schedule (200)

```json
{
  "schedule": {...},
  "activation": {
    "entries_created": 18250,
    "earliest_execution": "2025-01-15T17:23:00",
    "latest_execution": "2030-01-14T06:32:00"
  }
}
```

#### Preview Schedule (200)

```json
{
  "events": [
    {
      "datetime": "2025-01-15T17:23:00",
      "action_type": "gpio",
      "action_name": "attract_on",
      "routine_id": "routine-1",
      "routine_name": "Attract On at Dusk"
    },
    ...
  ],
  "total_count": 52
}
```

---

## Success Criteria

- [ ] All `PatternAction` references renamed to `Action`
- [ ] All `EventPattern` references renamed to `Routine`
- [ ] `Routine` class has embedded `trigger` field
- [ ] `Schedule` class has `routines` list (not `event_patterns`)
- [ ] `RecurringDaysTrigger` implemented with validation
- [ ] `schedule_to_cron()` iterates routines with per-routine triggers
- [ ] `preview_schedule()` replaces `get_next_events()`
- [ ] Conflict detection uses `routine_id`/`routine_name`
- [ ] Built-in schedules created in schema v3.0 format
- [ ] All backend tests pass

---

## Related Documentation

- [Index](./SCHEDULER_TERMINOLOGY_REFACTOR_INDEX.md) - Navigation hub
- [Overview](./SCHEDULER_TERMINOLOGY_REFACTOR_OVERVIEW.md) - Architecture context
- [Frontend Implementation](./SCHEDULER_TERMINOLOGY_REFACTOR_FRONTEND.md)
- [Testing Strategy](./SCHEDULER_TERMINOLOGY_REFACTOR_TESTING.md)
- [Reference](./SCHEDULER_TERMINOLOGY_REFACTOR_REFERENCE.md) - Patterns, API spec
