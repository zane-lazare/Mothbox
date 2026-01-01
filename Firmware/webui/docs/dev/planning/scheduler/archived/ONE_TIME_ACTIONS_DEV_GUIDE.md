# One-Time Actions for Scheduler Developer Guide

**Last Updated**: 2025-12-31
**Version**: 1.0
**Issue**: [#295](https://github.com/zane-lazare/Mothbox/issues/295)
**Audience**: Developers implementing this feature

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Integration Points](#integration-points)
4. [Implementation Guide](#implementation-guide)
5. [API Specification](#api-specification)
6. [Data Structures](#data-structures)
7. [Frontend Components](#frontend-components)
8. [Testing Strategy](#testing-strategy)
9. [Common Patterns Reference](#common-patterns-reference)
10. [Implementation Phases](#implementation-phases)

---

## Overview

### Purpose

This feature adds **one-time actions** to the Mothbox scheduler, enabling setup/teardown workflows that run once at absolute times rather than repeating at every interval. This solves a critical MVP gap where users cannot configure schedules like:

- UV lights ON at dusk (once)
- Photos every 15 minutes (repeating)
- UV lights OFF at dawn (once)

### Scope

**Included:**
- New `one_time`, `fixed_time`, `solar_event` fields on `PatternAction`
- Cron generation for one-time actions (separate from interval cron entries)
- Frontend UI for adding/editing one-time actions
- Conflict detection for one-time actions
- Timeline preview showing one-time actions

**Excluded:**
- Conditional one-time actions (sensor-triggered)
- Moon phase triggers for one-time actions (future enhancement)
- Duration-based one-time actions (use scripts instead)

### User Stories

- As a researcher, I want to turn UV lights on once at dusk so that I don't cycle them every interval
- As a field operator, I want GPS sync before my session starts so that timestamps are accurate
- As a researcher, I want a backup service to run once after my session ends so that photos are safely stored

### Related Documentation

- **CLAUDE.md**: Visual Scheduler System section (Issues #208-233)
- **Feature Planning**: `webui/docs/dev/planning/ONE_TIME_ACTIONS_FEATURE.md`
- **Scheduler API**: `webui/docs/dev/api/scheduler.md`

---

## Architecture

### System Context

```
┌──────────────────────────────────────────────────────────────────┐
│                     Mothbox Scheduler System                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐  │
│  │   Frontend  │───▶│   Flask API  │───▶│  scheduler_service  │  │
│  │ (React UI)  │    │  (routes/)   │    │                     │  │
│  └─────────────┘    └──────────────┘    └──────────┬──────────┘  │
│                                                     │             │
│                                          ┌──────────▼──────────┐  │
│                                          │   schedule_schema   │  │
│                                          │   (PatternAction)   │  │
│                                          └──────────┬──────────┘  │
│                                                     │             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────▼──────────┐  │
│  │ System Cron │◀───│  cron_bridge │◀───│ schedule_conflict   │  │
│  └─────────────┘    └──────────────┘    └─────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
PatternAction (MODIFIED)
├── action_type: str
├── action_name: str
├── offset_minutes: int        # Repeating: offset from pattern start
├── parameters: dict
├── description: str
├── one_time: bool = False     # NEW: If true, runs once per trigger cycle
├── fixed_time: str | None     # NEW: "HH:MM" absolute time
└── solar_event: str | None    # NEW: "dusk", "dawn", etc.

EventPattern
├── pattern_id: str
├── name: str
├── actions: list[PatternAction]  # Contains BOTH one-time and repeating
└── ...

Schedule
├── event_patterns: list[EventPattern]
├── trigger_type: str           # "interval", "solar", etc.
└── interval_trigger: IntervalTrigger  # Governs REPEATING actions only
```

### Data Flow

```
1. User creates schedule with mixed actions (one-time + repeating)
   ↓
2. Frontend sends schedule to POST /api/scheduler/schedules
   ↓
3. scheduler_service validates via schedule_schema.validate_schedule()
   ↓
4. On activation, schedule_to_cron() processes schedule:
   ├── One-time actions → Fixed cron entries at absolute times
   └── Repeating actions → Interval cron entries (existing logic)
   ↓
5. Cron entries written to system crontab
   ↓
6. Actions execute at scheduled times
```

---

## Integration Points

### Backend: schedule_schema.py

**File**: `webui/backend/lib/schedule_schema.py`

**Current PatternAction** (lines 170-222):
```python
@dataclass
class PatternAction:
    """
    A single action within an event pattern.

    Actions use relative offsets from pattern start (t=0), enabling
    coordinated multi-action sequences.
    """
    action_type: str
    action_name: str
    offset_minutes: int = 0
    parameters: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "offset_minutes": self.offset_minutes,
            "parameters": self.parameters,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternAction":
        """Create from dictionary."""
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
        )
```

**Extension required**: Add 3 new optional fields with backwards-compatible defaults.

### Backend: cron_bridge.py

**File**: `webui/backend/lib/cron_bridge.py`

**Existing pattern_to_cron_entries** (lines 827-888):
```python
def pattern_to_cron_entries(
    pattern: EventPattern,
    base_time: str,  # "HH:MM" format
    days_of_week: list[int] | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert EventPattern actions to cron entries.

    Each action in the pattern becomes a separate cron entry with:
    - Execution time = base_time + action.offset_minutes
    - Command from cron_security.get_validated_command()
    """
    # ... existing implementation for repeating actions
```

**Extension required**: Filter one-time actions BEFORE calling this function. Process them separately with absolute time logic.

### Backend: schedule_conflict.py

**File**: `webui/backend/lib/schedule_conflict.py`

**Current conflict detection** (lines 54-97):
```python
@dataclass
class ResourceUsage:
    """Describes resource usage by a single action."""
    resource_type: str
    resource_name: str
    start_time: datetime
    end_time: datetime
    pattern_id: str
    action_index: int
```

**Extension required**: Include one-time actions when building `PatternExecution` instances for conflict analysis.

### Frontend: ActionForm.jsx

**File**: `webui/frontend/src/components/scheduler/PatternEditor/ActionForm.jsx`

**Current form state** (lines 10-16):
```javascript
const [formData, setFormData] = useState({
  action_type: '',
  action_name: '',
  offset_minutes: '',
  description: '',
  parameters: [],
});
```

**Extension required**: Add `one_time`, `fixed_time`, `solar_event` fields with conditional rendering.

### Frontend: constants.js

**File**: `webui/frontend/src/components/scheduler/PatternEditor/constants.js`

**Current constants**:
```javascript
export const ACTION_LIMITS = {
  DESCRIPTION_MAX_LENGTH: 500,
  MIN_OFFSET_MINUTES: 0,
  MAX_OFFSET_MINUTES: 1440, // 24 hours
}

export const ACTION_NAMES = {
  gpio: ['attract_on', 'attract_off', 'flash_on', 'flash_off'],
  camera: ['takephoto'],
  gps_sync: ['sync'],
  service: ['backup', 'update_display'],
}
```

**Extension required**: Add `SOLAR_EVENTS` constant for dropdown options.

---

## Implementation Guide

### Step 1: Extend PatternAction Schema

**File**: `webui/backend/lib/schedule_schema.py`

**Location**: After line 201, extend `PatternAction` dataclass

```python
@dataclass
class PatternAction:
    """
    A single action within an event pattern.

    Regular actions: Use offset_minutes (relative to pattern start)
    One-time actions: Use fixed_time or solar_event (absolute timing)

    Attributes:
        action_type: Category ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action (e.g., "attract_on", "takephoto")
        offset_minutes: Minutes from pattern start (t=0). Default 0, max 1440.
            For one-time actions with solar_event, this is offset from solar event.
        parameters: Action-specific configuration dict
        description: Human-readable description (max 500 chars)
        one_time: If True, runs once per trigger cycle instead of every interval
        fixed_time: Absolute clock time ("HH:MM") for one-time actions
        solar_event: Solar event name for one-time actions ("dusk", "dawn", etc.)
    """

    action_type: str
    action_name: str
    offset_minutes: int = 0
    parameters: dict = field(default_factory=dict)
    description: str = ""
    # One-time action fields
    one_time: bool = False
    fixed_time: str | None = None
    solar_event: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "action_type": self.action_type,
            "action_name": self.action_name,
            "offset_minutes": self.offset_minutes,
            "parameters": self.parameters,
            "description": self.description,
        }
        # Only include one-time fields when relevant (backwards compatibility)
        if self.one_time:
            result["one_time"] = self.one_time
        if self.fixed_time is not None:
            result["fixed_time"] = self.fixed_time
        if self.solar_event is not None:
            result["solar_event"] = self.solar_event
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "PatternAction":
        """Create from dictionary."""
        return cls(
            action_type=data["action_type"],
            action_name=data["action_name"],
            offset_minutes=data.get("offset_minutes", 0),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
            one_time=data.get("one_time", False),
            fixed_time=data.get("fixed_time"),
            solar_event=data.get("solar_event"),
        )
```

**Key implementation notes**:
- Defaults ensure backwards compatibility (existing schedules work unchanged)
- `to_dict()` only includes new fields when non-default (cleaner JSON output)
- `offset_minutes` is reused for solar event offsets in one-time actions

### Step 2: Add Validation for One-Time Actions

**File**: `webui/backend/lib/schedule_schema.py`

**Location**: Extend `validate_pattern_action()` function (around line 1025)

```python
def validate_pattern_action(action: PatternAction) -> tuple[bool, str | None]:
    """
    Validate a single pattern action.

    Args:
        action: PatternAction to validate

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Existing validation for action_type
    if action.action_type not in ACTION_TYPES:
        return (
            False,
            f"Invalid action type: '{action.action_type}'. "
            f"Must be one of: {', '.join(ACTION_TYPES)}",
        )

    # One-time action validation
    if action.one_time:
        # One-time actions need absolute timing
        if not action.fixed_time and not action.solar_event:
            return False, "One-time action requires fixed_time or solar_event"

        # Cannot have both fixed_time and solar_event
        if action.fixed_time and action.solar_event:
            return False, "One-time action cannot have both fixed_time and solar_event"

        # Validate fixed_time format
        if action.fixed_time:
            if not _is_valid_time_format(action.fixed_time):
                return (
                    False,
                    f"Invalid fixed_time format: '{action.fixed_time}'. Must be HH:MM (24-hour)",
                )

        # Validate solar_event
        if action.solar_event:
            if action.solar_event not in SOLAR_EVENTS:
                return (
                    False,
                    f"Invalid solar_event: '{action.solar_event}'. "
                    f"Must be one of: {', '.join(SOLAR_EVENTS[:5])}...",
                )
            # For solar one-time actions, offset_minutes means offset from solar event
            # Allow +/- 120 minutes (same as SolarTrigger)
            if abs(action.offset_minutes) > 120:
                return (
                    False,
                    f"Solar event offset {action.offset_minutes} exceeds +/- 120 minutes",
                )
    else:
        # Repeating actions should not use fixed_time/solar_event
        if action.fixed_time or action.solar_event:
            return (
                False,
                "Repeating actions should not use fixed_time or solar_event. "
                "Set one_time=true to use absolute timing.",
            )

        # Existing offset validation for repeating actions
        if action.offset_minutes < 0:
            return False, "Action offset cannot be negative"

        if action.offset_minutes > MAX_OFFSET_MINUTES:
            return (
                False,
                f"Action offset {action.offset_minutes} exceeds maximum "
                f"of {MAX_OFFSET_MINUTES} minutes (24 hours)",
            )

    return True, None
```

### Step 3: Extend Cron Bridge for One-Time Actions

**File**: `webui/backend/lib/cron_bridge.py`

**Add new function** after `pattern_to_cron_entries()`:

```python
def one_time_action_to_cron(
    action: PatternAction,
    pattern_name: str,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
    from_date: date | None = None,
    comment_prefix: str = CRON_COMMENT_PREFIX,
) -> list[CronEntry]:
    """Convert a one-time PatternAction to cron entries.

    One-time actions use absolute timing (fixed_time or solar_event)
    instead of relative offsets from pattern start.

    Args:
        action: PatternAction with one_time=True
        pattern_name: Name of parent pattern for comments
        latitude: Observer latitude (required for solar events)
        longitude: Observer longitude (required for solar events)
        timezone_name: Timezone for calculations
        days_ahead: Number of days to pre-calculate (for solar events)
        from_date: Start date (defaults to today)
        comment_prefix: Prefix for cron comments

    Returns:
        List of CronEntry objects for this action
    """
    if not action.one_time:
        raise ValueError("Action must have one_time=True")

    # Get validated command
    script_key = get_script_key_for_action(action.action_type, action.action_name)
    if script_key:
        command = get_validated_command(script_key)
    else:
        logger.warning(
            f"Unknown action type '{action.action_type}/{action.action_name}' - skipping"
        )
        return []

    entries = []

    if action.fixed_time:
        # Fixed time: single cron entry at absolute time, runs daily
        hour, minute = map(int, action.fixed_time.split(":"))
        expression = f"{minute} {hour} * * *"
        comment = (
            f"{comment_prefix} {pattern_name}: {action.action_name} "
            f"(one-time at {action.fixed_time})"
        )
        entries.append(CronEntry(expression=expression, command=command, comment=comment))

    elif action.solar_event:
        # Solar event: pre-calculate for upcoming days
        if latitude is None or longitude is None:
            logger.warning("Solar one-time action requires latitude/longitude")
            return []

        if from_date is None:
            from_date = date.today()

        # Create a SolarTrigger to reuse existing calculation logic
        solar_trigger = SolarTrigger(
            solar_event=action.solar_event,
            offset_minutes=action.offset_minutes,  # Reused for solar offset
            days_of_week=None,  # One-time runs on all days
        )

        # Generate entries for each day
        for day_offset in range(days_ahead):
            target_date = from_date + timedelta(days=day_offset)

            exec_time = get_solar_execution_time(
                solar_trigger, target_date, latitude, longitude, timezone_name
            )

            if exec_time is None:
                continue  # Solar event doesn't occur (polar regions)

            # Build cron expression with specific day and month
            expression = (
                f"{exec_time.minute} {exec_time.hour} "
                f"{target_date.day} {target_date.month} *"
            )

            offset_str = f"+{action.offset_minutes}" if action.offset_minutes >= 0 else str(action.offset_minutes)
            comment = (
                f"{comment_prefix} {pattern_name}: {action.action_name} "
                f"(one-time at {action.solar_event}{offset_str}min on {target_date.isoformat()})"
            )

            entries.append(CronEntry(expression=expression, command=command, comment=comment))

    return entries
```

**Modify schedule_to_cron()** to separate one-time actions:

```python
def schedule_to_cron(
    schedule: Schedule,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone_name: str = "UTC",
    days_ahead: int = 7,
) -> CronBridgeResult:
    """Convert Schedule to cron entries.

    Handles both repeating and one-time actions:
    - One-time actions: Generate absolute-time cron entries
    - Repeating actions: Use existing interval logic
    """
    result = CronBridgeResult(
        entries=[],
        rtc_waketime=None,
        schedule_id=schedule.schedule_id,
        errors=[],
    )

    if not schedule.enabled or not schedule.event_patterns:
        return result

    all_entries = []

    for pattern in schedule.event_patterns:
        # Separate one-time and repeating actions
        one_time_actions = [a for a in pattern.actions if a.one_time]
        repeating_actions = [a for a in pattern.actions if not a.one_time]

        # Process one-time actions (absolute timing)
        for action in one_time_actions:
            entries = one_time_action_to_cron(
                action=action,
                pattern_name=pattern.name,
                latitude=latitude,
                longitude=longitude,
                timezone_name=timezone_name,
                days_ahead=days_ahead,
            )
            all_entries.extend(entries)

        # Process repeating actions (existing logic)
        # ... (existing trigger-specific processing)

    # Merge one-time entries with repeating entries
    result.entries = all_entries

    # ... rest of existing implementation
```

### Step 4: Update Frontend Constants

**File**: `webui/frontend/src/components/scheduler/PatternEditor/constants.js`

```javascript
/**
 * Constants for PatternEditor components
 */

export const PATTERN_LIMITS = {
  NAME_MAX_LENGTH: 200,
  DESCRIPTION_MAX_LENGTH: 2000,
}

export const ACTION_LIMITS = {
  DESCRIPTION_MAX_LENGTH: 500,
  MIN_OFFSET_MINUTES: 0,
  MAX_OFFSET_MINUTES: 1440, // 24 hours
  MAX_SOLAR_OFFSET_MINUTES: 120, // +/- 2 hours for solar events
}

/**
 * Available action types and their corresponding action names.
 */
export const ACTION_NAMES = {
  gpio: ['attract_on', 'attract_off', 'flash_on', 'flash_off'],
  camera: ['takephoto'],
  gps_sync: ['sync'],
  service: ['backup', 'update_display'],
}

/**
 * Solar events for one-time action timing.
 * Matches SOLAR_EVENTS in schedule_schema.py
 */
export const SOLAR_EVENTS = [
  { value: 'dawn', label: 'Dawn' },
  { value: 'sunrise', label: 'Sunrise' },
  { value: 'noon', label: 'Solar Noon' },
  { value: 'sunset', label: 'Sunset' },
  { value: 'dusk', label: 'Dusk' },
  { value: 'civil_dawn', label: 'Civil Dawn' },
  { value: 'civil_dusk', label: 'Civil Dusk' },
  { value: 'nautical_dawn', label: 'Nautical Dawn' },
  { value: 'nautical_dusk', label: 'Nautical Dusk' },
  { value: 'astronomical_dawn', label: 'Astronomical Dawn' },
  { value: 'astronomical_dusk', label: 'Astronomical Dusk' },
  { value: 'golden_hour_start', label: 'Golden Hour Start' },
  { value: 'golden_hour_end', label: 'Golden Hour End' },
  { value: 'blue_hour_start', label: 'Blue Hour Start' },
  { value: 'blue_hour_end', label: 'Blue Hour End' },
]
```

### Step 5: Update ActionForm Component

**File**: `webui/frontend/src/components/scheduler/PatternEditor/ActionForm.jsx`

Add one-time action fields to the form:

```jsx
// Add to formData state (line 10-16)
const [formData, setFormData] = useState({
  action_type: '',
  action_name: '',
  offset_minutes: '',
  description: '',
  parameters: [],
  // New one-time fields
  one_time: false,
  fixed_time: '',
  solar_event: '',
  solar_offset_minutes: 0,
});

// Add to useEffect for initialization (line 24-53)
useEffect(() => {
  if (isOpen) {
    if (action) {
      setFormData({
        action_type: action.action_type || '',
        action_name: action.action_name || '',
        offset_minutes: action.one_time ? '' : (action.offset_minutes ?? ''),
        description: action.description || '',
        parameters: action.parameters
          ? Object.entries(action.parameters).map(([key, value]) => ({
              id: generateUUID(),
              key,
              value
            }))
          : [],
        // One-time fields
        one_time: action.one_time || false,
        fixed_time: action.fixed_time || '',
        solar_event: action.solar_event || '',
        solar_offset_minutes: action.one_time && action.solar_event
          ? (action.offset_minutes || 0)
          : 0,
      });
    } else {
      // Reset for new action
      setFormData({
        action_type: '',
        action_name: '',
        offset_minutes: '',
        description: '',
        parameters: [],
        one_time: false,
        fixed_time: '',
        solar_event: '',
        solar_offset_minutes: 0,
      });
    }
    setErrors({});
  }
}, [action, isOpen]);

// Update validate() function to handle one-time actions
const validate = () => {
  const newErrors = {};

  if (!formData.action_type) {
    newErrors.action_type = 'Action type is required';
  }

  if (!formData.action_name) {
    newErrors.action_name = 'Action name is required';
  }

  if (formData.one_time) {
    // One-time validation
    if (!formData.fixed_time && !formData.solar_event) {
      newErrors.timing = 'One-time action requires fixed time or solar event';
    }
    if (formData.fixed_time && formData.solar_event) {
      newErrors.timing = 'Choose either fixed time or solar event, not both';
    }
    // Validate solar offset
    if (formData.solar_event) {
      const offset = Number(formData.solar_offset_minutes);
      if (Math.abs(offset) > ACTION_LIMITS.MAX_SOLAR_OFFSET_MINUTES) {
        newErrors.solar_offset_minutes = `Offset must be between -${ACTION_LIMITS.MAX_SOLAR_OFFSET_MINUTES} and +${ACTION_LIMITS.MAX_SOLAR_OFFSET_MINUTES} minutes`;
      }
    }
  } else {
    // Repeating action validation (existing)
    if (formData.offset_minutes === '' || formData.offset_minutes === null) {
      newErrors.offset_minutes = 'Offset is required';
    } else {
      const offset = Number(formData.offset_minutes);
      if (offset < ACTION_LIMITS.MIN_OFFSET_MINUTES || offset > ACTION_LIMITS.MAX_OFFSET_MINUTES) {
        newErrors.offset_minutes = `Offset must be between ${ACTION_LIMITS.MIN_OFFSET_MINUTES} and ${ACTION_LIMITS.MAX_OFFSET_MINUTES} minutes`;
      }
    }
  }

  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};

// Update handleSave() to build correct action data
const handleSave = () => {
  if (!validate()) {
    return;
  }

  const parametersObj = formData.parameters.reduce((acc, param) => {
    if (param.key && param.value) {
      acc[param.key] = param.value;
    }
    return acc;
  }, {});

  const actionData = {
    action_type: formData.action_type,
    action_name: formData.action_name,
    description: formData.description || undefined,
    parameters: parametersObj,
  };

  if (formData.one_time) {
    actionData.one_time = true;
    if (formData.fixed_time) {
      actionData.fixed_time = formData.fixed_time;
      actionData.offset_minutes = 0;  // Not used for fixed time
    } else if (formData.solar_event) {
      actionData.solar_event = formData.solar_event;
      actionData.offset_minutes = Number(formData.solar_offset_minutes);
    }
  } else {
    actionData.one_time = false;
    actionData.offset_minutes = Number(formData.offset_minutes);
  }

  onSave(actionData);
};
```

Add the UI elements in the render:

```jsx
{/* One-Time Toggle (after Action Name) */}
<div className="flex items-center gap-2 mt-4">
  <input
    type="checkbox"
    id="one_time"
    checked={formData.one_time}
    onChange={(e) => handleInputChange('one_time', e.target.checked)}
    className="rounded border-gray-300 dark:border-gray-600
               text-blue-600 focus:ring-blue-500"
  />
  <label
    htmlFor="one_time"
    className="text-sm font-medium text-gray-700 dark:text-gray-300"
  >
    One-time action (runs once, not every interval)
  </label>
</div>

{/* Timing Section - Conditional based on one_time */}
{formData.one_time ? (
  <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mt-4">
    <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
      When to run
    </h3>

    {/* Radio: Fixed Time vs Solar Event */}
    <div className="flex gap-4 mb-4">
      <label className="flex items-center gap-2">
        <input
          type="radio"
          name="timing_type"
          checked={!formData.solar_event}
          onChange={() => {
            setFormData(prev => ({ ...prev, solar_event: '', fixed_time: prev.fixed_time || '' }));
          }}
          className="text-blue-600 focus:ring-blue-500"
        />
        <span className="text-sm text-gray-700 dark:text-gray-300">Fixed Time</span>
      </label>
      <label className="flex items-center gap-2">
        <input
          type="radio"
          name="timing_type"
          checked={!!formData.solar_event}
          onChange={() => {
            setFormData(prev => ({ ...prev, fixed_time: '', solar_event: prev.solar_event || 'dusk' }));
          }}
          className="text-blue-600 focus:ring-blue-500"
        />
        <span className="text-sm text-gray-700 dark:text-gray-300">Solar Event</span>
      </label>
    </div>

    {/* Fixed Time Input */}
    {!formData.solar_event && (
      <div>
        <label htmlFor="fixed_time" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Time (24-hour)
        </label>
        <input
          type="time"
          id="fixed_time"
          value={formData.fixed_time}
          onChange={(e) => handleInputChange('fixed_time', e.target.value)}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 px-3 py-2"
        />
      </div>
    )}

    {/* Solar Event Select */}
    {formData.solar_event && (
      <>
        <div className="mb-3">
          <label htmlFor="solar_event" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Solar Event
          </label>
          <select
            id="solar_event"
            value={formData.solar_event}
            onChange={(e) => handleInputChange('solar_event', e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2"
          >
            {SOLAR_EVENTS.map(event => (
              <option key={event.value} value={event.value}>
                {event.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="solar_offset" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Offset (minutes)
          </label>
          <input
            type="number"
            id="solar_offset"
            value={formData.solar_offset_minutes}
            onChange={(e) => handleInputChange('solar_offset_minutes', e.target.value)}
            min={-ACTION_LIMITS.MAX_SOLAR_OFFSET_MINUTES}
            max={ACTION_LIMITS.MAX_SOLAR_OFFSET_MINUTES}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-3 py-2"
            placeholder="e.g., 30 for 30 min after"
          />
          <p className="mt-1 text-xs text-gray-500">
            Positive = after event, negative = before event
          </p>
        </div>
      </>
    )}

    {errors.timing && (
      <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.timing}</p>
    )}
  </div>
) : (
  /* Existing offset_minutes field for repeating actions */
  <div className="mt-4">
    <label htmlFor="offset_minutes" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      Offset (minutes from pattern start)
    </label>
    <input
      type="number"
      id="offset_minutes"
      value={formData.offset_minutes}
      onChange={(e) => handleInputChange('offset_minutes', e.target.value)}
      min={ACTION_LIMITS.MIN_OFFSET_MINUTES}
      max={ACTION_LIMITS.MAX_OFFSET_MINUTES}
      className="w-full rounded-md border border-gray-300 dark:border-gray-600
                 bg-white dark:bg-gray-800 px-3 py-2"
    />
    {errors.offset_minutes && (
      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.offset_minutes}</p>
    )}
  </div>
)}
```

---

## API Specification

The existing scheduler API endpoints remain unchanged. The `PatternAction` schema is extended with optional fields:

### PatternAction Schema (Extended)

**Request/Response format**:
```json
{
  "action_type": "gpio",
  "action_name": "attract_on",
  "offset_minutes": 0,
  "parameters": {},
  "description": "UV lights on at dusk",
  "one_time": true,
  "solar_event": "dusk"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| action_type | string | Yes | "gpio", "camera", "gps_sync", "service" |
| action_name | string | Yes | Specific action name |
| offset_minutes | int | No | Repeating: offset from pattern start. Solar one-time: offset from solar event. Default: 0 |
| parameters | object | No | Action-specific configuration |
| description | string | No | Human-readable description |
| one_time | bool | No | If true, runs once instead of every interval. Default: false |
| fixed_time | string | No | "HH:MM" for fixed-time one-time actions |
| solar_event | string | No | Solar event name for solar one-time actions |

### Validation Rules

1. **Repeating actions** (`one_time: false` or omitted):
   - `offset_minutes` required, 0-1440
   - `fixed_time` and `solar_event` must NOT be set

2. **Fixed-time one-time actions** (`one_time: true`, `fixed_time` set):
   - `fixed_time` must be valid "HH:MM" format
   - `solar_event` must NOT be set

3. **Solar one-time actions** (`one_time: true`, `solar_event` set):
   - `solar_event` must be valid solar event name
   - `offset_minutes` means offset from solar event (-120 to +120)
   - `fixed_time` must NOT be set

---

## Data Structures

### PatternAction (Extended)

**Location**: `webui/backend/lib/schedule_schema.py`

```python
@dataclass
class PatternAction:
    """
    A single action within an event pattern.

    Attributes:
        action_type: Category ("gpio", "camera", "gps_sync", "service")
        action_name: Specific action (e.g., "attract_on", "takephoto")
        offset_minutes: For repeating: offset from pattern start.
                        For solar one-time: offset from solar event.
        parameters: Action-specific configuration dict
        description: Human-readable description
        one_time: If True, runs once per trigger cycle
        fixed_time: "HH:MM" absolute time (one-time only)
        solar_event: Solar event name (one-time only)
    """
    action_type: str
    action_name: str
    offset_minutes: int = 0
    parameters: dict = field(default_factory=dict)
    description: str = ""
    one_time: bool = False
    fixed_time: str | None = None
    solar_event: str | None = None
```

### Validation constants

Add to `webui/backend/lib/schedule_schema.py`:

```python
# Max offset for solar one-time actions (same as SolarTrigger)
MAX_SOLAR_OFFSET_MINUTES: Final[int] = 120
```

---

## Frontend Components

### ActionForm.jsx (Modified)

**File**: `webui/frontend/src/components/scheduler/PatternEditor/ActionForm.jsx`

**State changes**:
- Add `one_time`, `fixed_time`, `solar_event`, `solar_offset_minutes` to form state

**Validation changes**:
- Conditional validation based on `one_time` flag
- Solar offset range validation (+/- 120 minutes)

**UI changes**:
- One-time checkbox toggle
- Conditional timing section (fixed time vs solar event)
- Solar event dropdown with offset input

### ActionList.jsx (Modified)

**File**: `webui/frontend/src/components/scheduler/PatternEditor/ActionList.jsx`

**Display changes**: Show different badge for one-time vs repeating actions

```jsx
{/* In SortableAction component */}
<div className="flex-shrink-0">
  {action.one_time ? (
    <span className="px-2 py-1 text-xs font-medium bg-amber-100 dark:bg-amber-900
                     text-amber-800 dark:text-amber-200 rounded">
      {action.fixed_time || action.solar_event}
    </span>
  ) : (
    <span className="px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900
                     text-blue-800 dark:text-blue-200 rounded">
      +{action.offset_minutes}min
    </span>
  )}
</div>
```

---

## Testing Strategy

### Unit Tests

**File**: `Tests/unit/test_schedule_schema.py`

#### Test Cases for PatternAction

| Test | Description |
|------|-------------|
| `test_pattern_action_one_time_fixed` | PatternAction with one_time=True and fixed_time validates |
| `test_pattern_action_one_time_solar` | PatternAction with one_time=True and solar_event validates |
| `test_pattern_action_one_time_no_timing` | One-time without fixed_time/solar_event fails validation |
| `test_pattern_action_one_time_both_timing` | One-time with both fixed_time AND solar_event fails |
| `test_pattern_action_repeating_with_timing` | Repeating action with fixed_time fails validation |
| `test_pattern_action_solar_offset_range` | Solar offset beyond +/-120 fails validation |
| `test_pattern_action_to_dict_one_time` | to_dict() includes one_time fields only when set |
| `test_pattern_action_from_dict_backwards_compat` | from_dict() works without new fields (backwards compat) |

**Sample test**:
```python
class TestPatternActionOneTime:
    """Test one-time action validation."""

    def test_one_time_fixed_time_valid(self):
        """One-time action with fixed_time validates."""
        action = PatternAction(
            action_type="gpio",
            action_name="attract_on",
            one_time=True,
            fixed_time="21:00",
        )
        valid, error = validate_pattern_action(action)
        assert valid is True
        assert error is None

    def test_one_time_solar_event_valid(self):
        """One-time action with solar_event validates."""
        action = PatternAction(
            action_type="gpio",
            action_name="attract_off",
            one_time=True,
            solar_event="dawn",
            offset_minutes=30,  # 30 min after dawn
        )
        valid, error = validate_pattern_action(action)
        assert valid is True
        assert error is None

    def test_one_time_requires_timing(self):
        """One-time action without fixed_time or solar_event fails."""
        action = PatternAction(
            action_type="gpio",
            action_name="attract_on",
            one_time=True,
        )
        valid, error = validate_pattern_action(action)
        assert valid is False
        assert "requires fixed_time or solar_event" in error

    def test_repeating_with_fixed_time_fails(self):
        """Repeating action with fixed_time fails validation."""
        action = PatternAction(
            action_type="gpio",
            action_name="attract_on",
            one_time=False,
            fixed_time="21:00",
            offset_minutes=0,
        )
        valid, error = validate_pattern_action(action)
        assert valid is False
        assert "should not use fixed_time" in error
```

**File**: `Tests/unit/test_cron_bridge.py`

#### Test Cases for Cron Generation

| Test | Description |
|------|-------------|
| `test_one_time_fixed_to_cron` | Fixed-time one-time action generates daily cron entry |
| `test_one_time_solar_to_cron` | Solar one-time action generates date-specific entries |
| `test_one_time_solar_with_offset` | Solar offset correctly applied to execution time |
| `test_schedule_mixed_actions` | Schedule with both one-time and repeating actions |
| `test_one_time_requires_coordinates` | Solar one-time without lat/lon returns empty list |

### Integration Tests

**File**: `Tests/integration/test_scheduler_one_time_workflow.py`

```python
class TestOneTimeActionWorkflow:
    """Integration tests for one-time action workflows."""

    def test_create_schedule_with_one_time_actions(self, client, app):
        """Create schedule with mixed one-time and repeating actions."""
        schedule_data = {
            "name": "Overnight Survey",
            "trigger": {
                "trigger_type": "interval",
                "interval_minutes": 15,
                "time_window_start": "22:00",
                "time_window_end": "06:00",
            },
            "event_patterns": [{
                "name": "Survey Pattern",
                "actions": [
                    {
                        "action_type": "gpio",
                        "action_name": "attract_on",
                        "one_time": True,
                        "solar_event": "dusk",
                    },
                    {
                        "action_type": "camera",
                        "action_name": "takephoto",
                        "offset_minutes": 0,
                    },
                    {
                        "action_type": "gpio",
                        "action_name": "attract_off",
                        "one_time": True,
                        "solar_event": "dawn",
                    },
                ],
            }],
        }

        response = client.post("/api/scheduler/schedules", json=schedule_data)
        assert response.status_code == 201

        # Verify actions are saved correctly
        schedule_id = response.json["schedule_id"]
        get_response = client.get(f"/api/scheduler/schedules/{schedule_id}")
        pattern = get_response.json["event_patterns"][0]

        assert pattern["actions"][0]["one_time"] is True
        assert pattern["actions"][0]["solar_event"] == "dusk"
        assert pattern["actions"][1]["one_time"] is False
        assert pattern["actions"][2]["one_time"] is True
        assert pattern["actions"][2]["solar_event"] == "dawn"
```

### Frontend Tests

**File**: `webui/frontend/src/components/scheduler/PatternEditor/__tests__/ActionForm.test.jsx`

```javascript
describe('ActionForm one-time actions', () => {
  it('shows timing options when one_time is checked', async () => {
    render(<ActionForm isOpen={true} onSave={jest.fn()} onCancel={jest.fn()} />);

    const oneTimeCheckbox = screen.getByLabelText(/one-time action/i);
    await userEvent.click(oneTimeCheckbox);

    expect(screen.getByText(/fixed time/i)).toBeInTheDocument();
    expect(screen.getByText(/solar event/i)).toBeInTheDocument();
  });

  it('validates one-time action requires timing', async () => {
    const onSave = jest.fn();
    render(<ActionForm isOpen={true} onSave={onSave} onCancel={jest.fn()} />);

    // Fill required fields
    await userEvent.selectOptions(screen.getByLabelText(/action type/i), 'gpio');
    await userEvent.selectOptions(screen.getByLabelText(/action name/i), 'attract_on');

    // Check one-time but don't set timing
    await userEvent.click(screen.getByLabelText(/one-time action/i));

    // Try to save
    await userEvent.click(screen.getByText(/save/i));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/requires fixed time or solar event/i)).toBeInTheDocument();
  });

  it('saves one-time action with solar event', async () => {
    const onSave = jest.fn();
    render(<ActionForm isOpen={true} onSave={onSave} onCancel={jest.fn()} />);

    await userEvent.selectOptions(screen.getByLabelText(/action type/i), 'gpio');
    await userEvent.selectOptions(screen.getByLabelText(/action name/i), 'attract_on');
    await userEvent.click(screen.getByLabelText(/one-time action/i));
    await userEvent.click(screen.getByLabelText(/solar event/i));
    await userEvent.selectOptions(screen.getByLabelText(/solar event/i), 'dusk');

    await userEvent.click(screen.getByText(/save/i));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      one_time: true,
      solar_event: 'dusk',
    }));
  });
});
```

---

## Common Patterns Reference

### Pattern 1: Dataclass Extension with Backwards Compatibility

**Used in**: `webui/backend/lib/schedule_schema.py` (PatternAction)

```python
@dataclass
class PatternAction:
    # Existing fields with defaults
    action_type: str
    action_name: str
    offset_minutes: int = 0

    # New optional fields with backwards-compatible defaults
    one_time: bool = False
    fixed_time: str | None = None

    def to_dict(self) -> dict:
        result = {...existing fields...}
        # Only include new fields when non-default
        if self.one_time:
            result["one_time"] = self.one_time
        if self.fixed_time is not None:
            result["fixed_time"] = self.fixed_time
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "PatternAction":
        return cls(
            ...existing fields...,
            # New fields with .get() for backwards compat
            one_time=data.get("one_time", False),
            fixed_time=data.get("fixed_time"),
        )
```

**When to use**: Adding optional fields to existing dataclasses without breaking existing data.

### Pattern 2: Conditional Validation

**Used in**: `webui/backend/lib/schedule_schema.py` (validate_pattern_action)

```python
def validate_pattern_action(action: PatternAction) -> tuple[bool, str | None]:
    if action.one_time:
        # One-time specific validation
        if not action.fixed_time and not action.solar_event:
            return False, "One-time action requires timing"
    else:
        # Repeating action validation
        if action.fixed_time or action.solar_event:
            return False, "Repeating actions shouldn't use absolute timing"
    return True, None
```

**When to use**: Validation rules that depend on a mode flag.

### Pattern 3: Frontend Conditional Rendering

**Used in**: `webui/frontend/src/components/scheduler/PatternEditor/ActionForm.jsx`

```jsx
{formData.one_time ? (
  <div className="timing-section">
    {/* One-time timing UI */}
  </div>
) : (
  <div className="offset-section">
    {/* Repeating offset UI */}
  </div>
)}
```

**When to use**: UI that shows different inputs based on a mode toggle.

---

## Implementation Phases

### Phase 1: Backend Schema and Validation

**Goal**: Extend PatternAction with one-time fields and validation

**Issues**:
1. **Extend PatternAction dataclass** (S)
   - Labels: `backend`, `scheduler`
   - Add `one_time`, `fixed_time`, `solar_event` fields
   - Update `to_dict()` and `from_dict()` methods
   - Acceptance criteria:
     - [ ] New fields have backwards-compatible defaults
     - [ ] Existing schedules serialize/deserialize unchanged
     - [ ] Unit tests pass

2. **Add one-time action validation** (S)
   - Labels: `backend`, `scheduler`
   - Update `validate_pattern_action()` function
   - Acceptance criteria:
     - [ ] One-time requires fixed_time OR solar_event
     - [ ] Cannot have both fixed_time AND solar_event
     - [ ] Repeating cannot use fixed_time/solar_event
     - [ ] Solar offset validated (-120 to +120)

**Success criteria**:
- [ ] All existing unit tests pass
- [ ] New validation tests pass
- [ ] Backwards compatibility verified

### Phase 2: Cron Bridge Extension

**Goal**: Generate cron entries for one-time actions

**Issues**:
1. **Add one_time_action_to_cron function** (M)
   - Labels: `backend`, `scheduler`, `cron`
   - Handle fixed_time one-time actions
   - Handle solar_event one-time actions with offset
   - Acceptance criteria:
     - [ ] Fixed time generates daily cron entry
     - [ ] Solar generates date-specific entries
     - [ ] Solar offset correctly applied

2. **Update schedule_to_cron for mixed actions** (M)
   - Labels: `backend`, `scheduler`, `cron`
   - Separate one-time from repeating actions
   - Merge entries from both types
   - Acceptance criteria:
     - [ ] Schedule with both action types generates correct cron
     - [ ] One-time entries have correct absolute times
     - [ ] Repeating entries unchanged from current behavior

**Success criteria**:
- [ ] Cron generation tests pass
- [ ] Integration test with mixed actions passes

### Phase 3: Conflict Detection

**Goal**: Include one-time actions in conflict analysis

**Issues**:
1. **Update conflict detection for one-time actions** (S)
   - Labels: `backend`, `scheduler`
   - Include one-time actions when building PatternExecution
   - Detect conflicts between one-time and repeating actions
   - Acceptance criteria:
     - [ ] One-time actions appear in conflict preview
     - [ ] One-time vs repeating conflicts detected
     - [ ] One-time vs one-time conflicts detected

**Success criteria**:
- [ ] Conflict detection tests include one-time scenarios

### Phase 4: Frontend Implementation

**Goal**: UI for creating/editing one-time actions

**Issues**:
1. **Add SOLAR_EVENTS constant** (XS)
   - Labels: `frontend`, `scheduler`
   - Add to constants.js
   - Acceptance criteria:
     - [ ] All 15 solar events available

2. **Update ActionForm for one-time actions** (L)
   - Labels: `frontend`, `scheduler`
   - Add one_time checkbox
   - Add conditional timing section
   - Update validation
   - Acceptance criteria:
     - [ ] One-time toggle shows timing options
     - [ ] Fixed time and solar event mutually exclusive
     - [ ] Form validates one-time requirements
     - [ ] Saves correct action data structure

3. **Update ActionList display** (S)
   - Labels: `frontend`, `scheduler`
   - Different badge for one-time vs repeating
   - Show timing info for one-time actions
   - Acceptance criteria:
     - [ ] Visual distinction between action types
     - [ ] One-time shows time/event, repeating shows offset

**Success criteria**:
- [ ] Frontend tests pass
- [ ] E2E test creates schedule with one-time actions

### Phase 5: Timeline Preview

**Goal**: Show one-time actions in schedule preview

**Issues**:
1. **Update preview to show one-time actions** (M)
   - Labels: `frontend`, `backend`, `scheduler`
   - Include one-time actions in `get_next_events()`
   - Frontend displays one-time events distinctly
   - Acceptance criteria:
     - [ ] One-time actions appear in preview timeline
     - [ ] Visual distinction from repeating events
     - [ ] Solar times calculated correctly for preview

**Success criteria**:
- [ ] Preview shows complete schedule with mixed actions

---

## Appendix

### File Checklist

**Modified files**:
- [ ] `webui/backend/lib/schedule_schema.py` - Add one-time fields to PatternAction
- [ ] `webui/backend/lib/cron_bridge.py` - Add one_time_action_to_cron, update schedule_to_cron
- [ ] `webui/backend/lib/schedule_conflict.py` - Include one-time in conflict detection
- [ ] `webui/frontend/src/components/scheduler/PatternEditor/constants.js` - Add SOLAR_EVENTS
- [ ] `webui/frontend/src/components/scheduler/PatternEditor/ActionForm.jsx` - Add one-time UI
- [ ] `webui/frontend/src/components/scheduler/PatternEditor/ActionList.jsx` - Update display

**New test files**:
- [ ] `Tests/unit/test_schedule_schema.py` - Add one-time action tests (extend existing)
- [ ] `Tests/unit/test_cron_bridge.py` - Add one-time cron tests (extend existing)
- [ ] `Tests/integration/test_scheduler_one_time_workflow.py` - New integration tests
- [ ] `webui/frontend/src/components/scheduler/PatternEditor/__tests__/ActionForm.test.jsx` - Add one-time tests

### Configuration Checklist

- [ ] No new configuration files needed
- [ ] No new environment variables
- [ ] Update `CLAUDE.md` scheduler section to mention one-time actions

### Documentation Checklist

- [ ] Update `webui/docs/dev/api/scheduler.md` with new PatternAction fields
- [ ] Update `webui/docs/SCHEDULER_USER_GUIDE.md` with one-time action usage
- [ ] Archive planning doc after implementation complete
