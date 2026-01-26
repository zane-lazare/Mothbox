# Scheduler API Documentation

**Last Updated**: 2026-01-27
**Schema Version**: 3.0
**Base URL**: `/api/scheduler/ui`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Endpoint Quick Reference](#endpoint-quick-reference)
5. [Schedule Endpoints](#schedule-endpoints)
6. [Cron Endpoints](#cron-endpoints)
7. [Data Structures](#data-structures)
8. [Trigger Types](#trigger-types)
9. [Usage Examples](#usage-examples)
10. [React Hooks Reference](#react-hooks-reference)
11. [Related Documentation](#related-documentation)

---

## Overview

The Scheduler API provides a routine-based scheduling system for automated photo capture, GPIO control, and service execution on Mothbox devices.

### Key Concepts

- **Schedule**: Container for one or more routines, represents a complete automation workflow
- **Routine**: Action sequence with its own trigger configuration (e.g., "Take photo at sunset")
- **Action**: Single operation (GPIO control, camera capture, GPS sync, service call)
- **Trigger**: Timing configuration (interval, solar event, moon phase, fixed time, cron, recurring days)

### Architecture

```
Schedule (container)
├── name, description, enabled, is_active
└── routines[] (each with own trigger)
    ├── Routine 1: trigger=SolarTrigger(sunset) → actions=[attract_on]
    ├── Routine 2: trigger=IntervalTrigger(15min) → actions=[flash_on, takephoto, flash_off]
    └── Routine 3: trigger=SolarTrigger(dawn) → actions=[attract_off]
```

### Implementation Files

| File | Purpose |
|------|---------|
| `webui/backend/routes/scheduler_ui.py` | REST API endpoints |
| `webui/backend/services/scheduler_service.py` | Service layer with caching |
| `webui/backend/lib/schedule_schema.py` | Data structures (Schedule, Routine, Action) |
| `webui/backend/lib/schedule_storage.py` | JSON file persistence |
| `webui/backend/lib/cron_bridge.py` | Schedule to cron conversion |
| `webui/backend/lib/schedule_preview.py` | Preview generation |
| `webui/backend/lib/schedule_conflict.py` | Conflict detection |

---

## Authentication

**Current Status**: CSRF protection required for state-changing operations

| Requirement | Endpoints |
|-------------|-----------|
| CSRF Token | POST, PUT, DELETE operations |
| Rate Limit (30/min) | CRUD, validate, preview, clone |
| Rate Limit (10/min) | Activate, deactivate |

**Future** (Issue #19): User authentication planned

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful request |
| 201 | Created | Schedule/clone created |
| 400 | Bad Request | Validation error, invalid parameters |
| 403 | Forbidden | Cannot modify/delete built-in schedule |
| 404 | Not Found | Schedule not found |
| 409 | Conflict | Schedule activation blocked by conflicts |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

---

## Endpoint Quick Reference

**13 endpoints total**

| # | Method | Endpoint | Description | Rate Limit |
|---|--------|----------|-------------|------------|
| 1 | GET | `/schedules` | [List schedules](#1-list-schedules) | - |
| 2 | GET | `/schedules/<id>` | [Get schedule](#2-get-schedule) | - |
| 3 | GET | `/schedules/active` | [Get active schedule](#3-get-active-schedule) | - |
| 4 | GET | `/schedules/builtin` | [List built-in schedules](#4-list-built-in-schedules) | - |
| 5 | POST | `/schedules` | [Create schedule](#5-create-schedule) | 30/min |
| 6 | PUT | `/schedules/<id>` | [Update schedule](#6-update-schedule) | 30/min |
| 7 | DELETE | `/schedules/<id>` | [Delete schedule](#7-delete-schedule) | 30/min |
| 8 | POST | `/schedules/<id>/clone` | [Clone schedule](#8-clone-schedule) | 30/min |
| 9 | POST | `/schedules/<id>/activate` | [Activate schedule](#9-activate-schedule) | 10/min |
| 10 | POST | `/schedules/deactivate` | [Deactivate schedule](#10-deactivate-schedule) | 10/min |
| 11 | POST | `/schedules/<id>/validate` | [Validate schedule](#11-validate-schedule) | 30/min |
| 12 | GET | `/schedules/<id>/preview` | [Preview schedule](#12-preview-schedule) | 30/min |
| 13 | POST | `/cron/validate` | [Validate cron expression](#13-validate-cron-expression) | 30/min |

---

## Schedule Endpoints

### 1. List Schedules

List all schedules with optional filtering.

**Endpoint**: `GET /api/scheduler/ui/schedules`

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_builtin` | boolean | false | Include built-in schedules |
| `active_only` | boolean | false | Filter to active schedule only |

#### Response (200)

```json
{
  "schedules": [
    {
      "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Overnight Moth Survey",
      "description": "UV lights at dusk, photos every 15min, off at dawn",
      "enabled": true,
      "is_active": true,
      "routine_count": 3,
      "created_at": "2026-01-20T10:30:00",
      "modified_at": "2026-01-20T15:45:00"
    }
  ],
  "total": 1
}
```

#### Examples

```bash
# List user schedules
curl "http://localhost:5000/api/scheduler/ui/schedules"

# Include built-in schedules
curl "http://localhost:5000/api/scheduler/ui/schedules?include_builtin=true"

# Get only active schedule
curl "http://localhost:5000/api/scheduler/ui/schedules?active_only=true"
```

---

### 2. Get Schedule

Get full schedule details including embedded routines.

**Endpoint**: `GET /api/scheduler/ui/schedules/<schedule_id>`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `schedule_id` | string (UUID) | Schedule identifier |

#### Response (200)

```json
{
  "schema_version": "3.0",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Overnight Moth Survey",
  "description": "UV lights at dusk, photos every 15min, off at dawn",
  "routines": [
    {
      "routine_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "UV Lights On",
      "trigger": {
        "type": "solar",
        "solar_event": "dusk",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn on UV attract lights"
        }
      ],
      "pre_condition": null,
      "description": ""
    },
    {
      "routine_id": "660e8400-e29b-41d4-a716-446655440002",
      "name": "Photo Capture",
      "trigger": {
        "type": "interval",
        "interval_minutes": 15,
        "time_window": {
          "start_time": "dusk",
          "end_time": "dawn",
          "start_offset_minutes": 30,
          "end_offset_minutes": -30
        }
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "flash_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": ""
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 1,
          "parameters": {},
          "description": ""
        },
        {
          "action_type": "gpio",
          "action_name": "flash_off",
          "offset_minutes": 2,
          "parameters": {},
          "description": ""
        }
      ],
      "pre_condition": null,
      "description": ""
    },
    {
      "routine_id": "660e8400-e29b-41d4-a716-446655440003",
      "name": "UV Lights Off",
      "trigger": {
        "type": "solar",
        "solar_event": "dawn",
        "offset_minutes": 0
      },
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn off UV attract lights"
        }
      ],
      "pre_condition": null,
      "description": ""
    }
  ],
  "deployment_id": null,
  "create_deployment": false,
  "enabled": true,
  "is_active": true,
  "created_at": "2026-01-20T10:30:00",
  "modified_at": "2026-01-20T15:45:00",
  "modified_by": null
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 404 | Schedule not found |

---

### 3. Get Active Schedule

Get the currently active schedule (if any).

**Endpoint**: `GET /api/scheduler/ui/schedules/active`

#### Response (200)

```json
{
  "active": true,
  "schedule": {
    "schema_version": "3.0",
    "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Overnight Moth Survey",
    "...": "full schedule object"
  }
}
```

When no schedule is active:

```json
{
  "active": false,
  "schedule": null
}
```

---

### 4. List Built-in Schedules

List available built-in schedule templates.

**Endpoint**: `GET /api/scheduler/ui/schedules/builtin`

#### Response (200)

```json
{
  "schedules": [
    {
      "schedule_id": "builtin-overnight-moth-survey",
      "name": "Overnight Moth Survey",
      "description": "Standard overnight moth photography workflow",
      "enabled": true,
      "is_active": false,
      "routine_count": 3,
      "created_at": "2026-01-01T00:00:00",
      "modified_at": "2026-01-01T00:00:00"
    },
    {
      "schedule_id": "builtin-daytime-pollinator",
      "name": "Daytime Pollinator Survey",
      "description": "Daytime pollinator photography workflow",
      "enabled": true,
      "is_active": false,
      "routine_count": 2,
      "created_at": "2026-01-01T00:00:00",
      "modified_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 2
}
```

---

### 5. Create Schedule

Create a new schedule.

**Endpoint**: `POST /api/scheduler/ui/schedules`

**Rate Limit**: 30 requests/minute

**Requires**: CSRF token, JSON body

#### Request Body

```json
{
  "name": "My Custom Schedule",
  "description": "Optional description",
  "routines": [
    {
      "name": "Photo Every Hour",
      "trigger": {
        "type": "interval",
        "interval_minutes": 60,
        "time_window": {
          "start_time": "00:00",
          "end_time": "23:59"
        }
      },
      "actions": [
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 0
        }
      ]
    }
  ],
  "enabled": true
}
```

#### Response (201)

```json
{
  "message": "Schedule created",
  "schedule_id": "770e8400-e29b-41d4-a716-446655440000",
  "schedule": { "...": "full schedule object" }
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Missing required field, invalid format, validation failed |

---

### 6. Update Schedule

Update an existing schedule.

**Endpoint**: `PUT /api/scheduler/ui/schedules/<schedule_id>`

**Rate Limit**: 30 requests/minute

**Requires**: CSRF token, JSON body

#### Request Body

Partial or complete schedule update:

```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "enabled": false
}
```

#### Response (200)

```json
{
  "message": "Schedule updated",
  "schedule": { "...": "full updated schedule object" }
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Validation failed |
| 403 | Cannot modify built-in schedule |
| 404 | Schedule not found |

---

### 7. Delete Schedule

Delete a schedule.

**Endpoint**: `DELETE /api/scheduler/ui/schedules/<schedule_id>`

**Rate Limit**: 30 requests/minute

#### Response (200)

```json
{
  "message": "Schedule deleted",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 403 | Cannot delete built-in schedule |
| 404 | Schedule not found |

---

### 8. Clone Schedule

Create a copy of an existing schedule.

**Endpoint**: `POST /api/scheduler/ui/schedules/<schedule_id>/clone`

**Rate Limit**: 30 requests/minute

#### Request Body (Optional)

```json
{
  "name": "My Copy of Moth Survey"
}
```

If name is omitted, generates "Copy of {original_name}".

#### Response (201)

```json
{
  "message": "Schedule cloned",
  "schedule_id": "880e8400-e29b-41d4-a716-446655440000",
  "schedule": { "...": "full cloned schedule object" }
}
```

#### Clone Behavior

- New UUIDs generated for schedule and all routines
- `is_active` set to false
- `deployment_id` cleared
- Fresh timestamps

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Invalid name (too long) |
| 404 | Schedule not found |

---

### 9. Activate Schedule

Activate a schedule (generates cron jobs).

**Endpoint**: `POST /api/scheduler/ui/schedules/<schedule_id>/activate`

**Rate Limit**: 10 requests/minute

#### Request Body (Optional)

```json
{
  "check_conflicts": true,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timezone": "America/Los_Angeles"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `check_conflicts` | boolean | true | Check for time conflicts before activation |
| `latitude` | float | null | Latitude for solar calculations (-90 to 90) |
| `longitude` | float | null | Longitude for solar calculations (-180 to 180) |
| `timezone` | string | "UTC" | Timezone for schedule execution |

**Note**: Both latitude and longitude must be provided together, or neither.

#### Response (200)

```json
{
  "message": "Schedule activated",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### WebSocket Progress

Emits `schedule:activation_progress` events during activation:

```json
{
  "step": 2,
  "total_steps": 5,
  "message": "Generating cron jobs...",
  "progress": 40
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Invalid coordinates, invalid timezone, activation error |
| 404 | Schedule not found |
| 409 | Schedule has blocking conflicts |

---

### 10. Deactivate Schedule

Deactivate the currently active schedule.

**Endpoint**: `POST /api/scheduler/ui/schedules/deactivate`

**Rate Limit**: 10 requests/minute

#### Response (200)

When a schedule was active:

```json
{
  "message": "Schedule deactivated",
  "was_active": true,
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

When no schedule was active:

```json
{
  "message": "No active schedule to deactivate",
  "was_active": false,
  "schedule_id": null
}
```

---

### 11. Validate Schedule

Validate a schedule and check for conflicts.

**Endpoint**: `POST /api/scheduler/ui/schedules/<schedule_id>/validate`

**Rate Limit**: 30 requests/minute

#### Request Body (Optional)

```json
{
  "days": 7,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timezone": "America/Los_Angeles"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | integer | 7 | Number of days to check (1-90) |
| `latitude` | float | null | Latitude for solar calculations |
| `longitude` | float | null | Longitude for solar calculations |
| `timezone` | string | "UTC" | Timezone for validation |

#### Response (200)

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "valid": true,
  "has_warnings": false,
  "conflicts": [],
  "total_conflicts": 0,
  "blocking_conflicts": 0
}
```

With conflicts:

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "valid": false,
  "has_warnings": true,
  "conflicts": [
    {
      "routine_id": "660e8400-e29b-41d4-a716-446655440001",
      "severity": "warning",
      "message": "Routine executions overlap at 22:00",
      "time": "2026-01-20T22:00:00"
    }
  ],
  "total_conflicts": 1,
  "blocking_conflicts": 0
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Invalid parameters |
| 404 | Schedule not found |

---

### 12. Preview Schedule

Generate a preview of schedule executions.

**Endpoint**: `GET /api/scheduler/ui/schedules/<schedule_id>/preview`

**Rate Limit**: 30 requests/minute

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Preview days (1-90) |
| `lat` | float | null | Latitude for solar calculations |
| `lon` | float | null | Longitude for solar calculations |
| `tz` | string | "UTC" | Timezone |

#### Response (200)

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "schedule_name": "Overnight Moth Survey",
  "preview_start": "2026-01-20T00:00:00Z",
  "preview_end": "2026-01-27T00:00:00Z",
  "executions": [
    {
      "start_time": "2026-01-20T17:30:00Z",
      "end_time": "2026-01-20T17:30:00Z",
      "routine_id": "660e8400-e29b-41d4-a716-446655440001",
      "routine_name": "UV Lights On",
      "trigger_info": "At dusk",
      "actions": [
        {
          "time": "2026-01-20T17:30:00Z",
          "action_name": "attract_on",
          "action_type": "gpio",
          "offset_minutes": 0,
          "description": "Turn on UV attract lights"
        }
      ]
    },
    {
      "start_time": "2026-01-20T18:00:00Z",
      "end_time": "2026-01-20T18:02:00Z",
      "routine_id": "660e8400-e29b-41d4-a716-446655440002",
      "routine_name": "Photo Capture",
      "trigger_info": "Every 15 minutes",
      "actions": [
        {
          "time": "2026-01-20T18:00:00Z",
          "action_name": "flash_on",
          "action_type": "gpio",
          "offset_minutes": 0,
          "description": ""
        },
        {
          "time": "2026-01-20T18:01:00Z",
          "action_name": "takephoto",
          "action_type": "camera",
          "offset_minutes": 1,
          "description": ""
        },
        {
          "time": "2026-01-20T18:02:00Z",
          "action_name": "flash_off",
          "action_type": "gpio",
          "offset_minutes": 2,
          "description": ""
        }
      ]
    }
  ],
  "conflicts": [],
  "moon_phases": {
    "2026-01-20": {
      "date": "2026-01-20",
      "phase": "waxing_gibbous",
      "phase_name": "Waxing Gibbous",
      "illumination": 0.75
    }
  },
  "total_actions": 42,
  "total_executions": 14,
  "generated_at": "2026-01-20T10:30:00Z"
}
```

#### Errors

| Code | Condition |
|------|-----------|
| 400 | Invalid days, coordinates, or timezone |
| 404 | Schedule not found |

---

## Cron Endpoints

### 13. Validate Cron Expression

Validate a cron expression and preview next executions.

**Endpoint**: `POST /api/scheduler/ui/cron/validate`

**Rate Limit**: 30 requests/minute

**Requires**: CSRF token, JSON body

#### Request Body

```json
{
  "expression": "*/15 * * * *",
  "count": 5
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `expression` | string | required | Cron expression (max 100 chars) |
| `count` | integer | 5 | Number of next executions (1-20) |

#### Response (200) - Valid

```json
{
  "valid": true,
  "expression": "*/15 * * * *",
  "next_executions": [
    "2026-01-20T10:45:00Z",
    "2026-01-20T11:00:00Z",
    "2026-01-20T11:15:00Z",
    "2026-01-20T11:30:00Z",
    "2026-01-20T11:45:00Z"
  ],
  "human_readable": "Every 15 minutes"
}
```

#### Response (400) - Invalid

```json
{
  "valid": false,
  "error": "Invalid cron expression: expected 5 fields, got 4"
}
```

---

## Data Structures

### Schedule

Top-level container for routines.

```json
{
  "schema_version": "3.0",
  "schedule_id": "string (UUID)",
  "name": "string (required, max 200 chars)",
  "description": "string (max 2000 chars)",
  "routines": [Routine],
  "deployment_id": "string | null",
  "create_deployment": "boolean",
  "enabled": "boolean",
  "is_active": "boolean",
  "created_at": "ISO 8601 timestamp",
  "modified_at": "ISO 8601 timestamp",
  "modified_by": "string | null"
}
```

### Routine

Action sequence with embedded trigger.

```json
{
  "routine_id": "string (UUID)",
  "name": "string | null (auto-generated if null)",
  "trigger": "Trigger object",
  "actions": [Action],
  "pre_condition": "SensorTrigger | null",
  "description": "string (max 2000 chars)"
}
```

### Action

Single operation within a routine.

```json
{
  "action_type": "gpio | camera | gps | service",
  "action_name": "string",
  "offset_minutes": "integer (0-1440)",
  "parameters": "object",
  "description": "string"
}
```

#### Action Types and Names

| Type | Valid Names | Description |
|------|-------------|-------------|
| `gpio` | `attract_on`, `attract_off`, `flash_on`, `flash_off` | GPIO relay control |
| `camera` | `takephoto` | Trigger photo capture |
| `gps` | `sync` | Sync GPS coordinates |
| `service` | `start`, `stop`, `restart` | Systemd service control |

### TimeWindow

Time window for interval-based triggers.

```json
{
  "start_time": "HH:MM | solar_event",
  "end_time": "HH:MM | solar_event",
  "start_offset_minutes": "integer",
  "end_offset_minutes": "integer"
}
```

---

## Trigger Types

### IntervalTrigger

Execute at regular intervals within a time window.

```json
{
  "type": "interval",
  "interval_minutes": 15,
  "time_window": {
    "start_time": "sunset",
    "end_time": "sunrise",
    "start_offset_minutes": 30,
    "end_offset_minutes": -30
  }
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `interval_minutes` | integer | 1-10080 | Interval between executions |
| `time_window` | TimeWindow | required | When interval is active |

### SolarTrigger

Execute at solar events (sunrise, sunset, etc.).

```json
{
  "type": "solar",
  "solar_event": "sunset",
  "offset_minutes": 30
}
```

| Field | Type | Description |
|-------|------|-------------|
| `solar_event` | string | Solar event name (see list below) |
| `offset_minutes` | integer | Offset from event (-1440 to 1440) |

**Solar Events**: `dawn`, `sunrise`, `noon`, `sunset`, `dusk`, `civil_dawn`, `civil_dusk`, `nautical_dawn`, `nautical_dusk`, `astronomical_dawn`, `astronomical_dusk`, `golden_hour_start`, `golden_hour_end`, `blue_hour_start`, `blue_hour_end`

### MoonPhaseTrigger

Execute during specific moon phases.

```json
{
  "type": "moon_phase",
  "phases": ["new", "full"],
  "time_of_day": "22:00",
  "offset_days": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `phases` | string[] | Moon phases to trigger on |
| `time_of_day` | string | Time to execute (HH:MM) |
| `offset_days` | integer | Days before/after phase (-7 to 7) |

**Moon Phases**: `new`, `waxing_crescent`, `first_quarter`, `waxing_gibbous`, `full`, `waning_gibbous`, `last_quarter`, `waning_crescent`

### FixedTimeTrigger

Execute at specific times.

```json
{
  "type": "fixed_time",
  "times": ["06:00", "12:00", "18:00"],
  "days_of_week": [0, 1, 2, 3, 4]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `times` | string[] | Times to execute (HH:MM format) |
| `days_of_week` | integer[] | Days to execute (0=Monday, 6=Sunday) |

### RecurringDaysTrigger

Execute every N days.

```json
{
  "type": "recurring_days",
  "interval_days": 3,
  "time_of_day": "09:00",
  "start_date": "2026-01-20"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `interval_days` | integer | Days between executions (1-365) |
| `time_of_day` | string | Time to execute (HH:MM) |
| `start_date` | string | First execution date (YYYY-MM-DD) |

### CronTrigger

Execute based on cron expression (expert mode).

```json
{
  "type": "cron",
  "expression": "0 */2 * * *"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `expression` | string | Standard 5-field cron expression |

### SensorTrigger (Pre-condition Only)

Gate execution based on sensor readings.

```json
{
  "type": "sensor",
  "sensor_type": "light",
  "condition": "below",
  "threshold": 100,
  "cooldown_minutes": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sensor_type` | string | Sensor to monitor |
| `condition` | string | `above`, `below`, `equals` |
| `threshold` | number | Trigger threshold |
| `cooldown_minutes` | integer | Minimum time between triggers (0-60) |

**Note**: SensorTrigger is only valid as a `pre_condition` on a Routine, not as a primary trigger.

---

## Usage Examples

### JavaScript (fetch)

```javascript
// List schedules
const response = await fetch('/api/scheduler/ui/schedules');
const { schedules, total } = await response.json();

// Get schedule details
const schedule = await fetch(`/api/scheduler/ui/schedules/${scheduleId}`)
  .then(r => r.json());

// Create schedule
const newSchedule = await fetch('/api/scheduler/ui/schedules', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({
    name: 'My Schedule',
    routines: [{
      trigger: { type: 'interval', interval_minutes: 60, time_window: { start_time: '00:00', end_time: '23:59' } },
      actions: [{ action_type: 'camera', action_name: 'takephoto', offset_minutes: 0 }]
    }]
  })
}).then(r => r.json());

// Activate schedule with location
await fetch(`/api/scheduler/ui/schedules/${scheduleId}/activate`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({
    latitude: 37.7749,
    longitude: -122.4194,
    timezone: 'America/Los_Angeles'
  })
});

// Clone a built-in schedule
const cloned = await fetch(`/api/scheduler/ui/schedules/${builtinId}/clone`, {
  method: 'POST',
  headers: { 'X-CSRFToken': csrfToken }
}).then(r => r.json());
```

### Python (requests)

```python
import requests

BASE_URL = 'http://localhost:5000/api/scheduler/ui'

# List schedules
response = requests.get(f'{BASE_URL}/schedules')
schedules = response.json()['schedules']

# Get schedule
schedule = requests.get(f'{BASE_URL}/schedules/{schedule_id}').json()

# Create schedule
new_schedule = requests.post(
    f'{BASE_URL}/schedules',
    json={
        'name': 'My Schedule',
        'routines': [{
            'trigger': {
                'type': 'solar',
                'solar_event': 'sunset',
                'offset_minutes': 0
            },
            'actions': [{
                'action_type': 'gpio',
                'action_name': 'attract_on',
                'offset_minutes': 0
            }]
        }]
    },
    headers={'X-CSRFToken': csrf_token}
).json()

# Preview schedule
preview = requests.get(
    f'{BASE_URL}/schedules/{schedule_id}/preview',
    params={'days': 7, 'lat': 37.7749, 'lon': -122.4194, 'tz': 'America/Los_Angeles'}
).json()
```

---

## React Hooks Reference

### useSchedules

```javascript
import { useSchedules } from '@/hooks/useSchedules';

function ScheduleList() {
  const {
    schedules,
    isLoading,
    error,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    activateSchedule,
    deactivateSchedule
  } = useSchedules();

  // Create
  await createSchedule({ name: 'New Schedule', routines: [...] });

  // Activate with location
  await activateSchedule(scheduleId, {
    latitude: 37.7749,
    longitude: -122.4194,
    timezone: 'America/Los_Angeles'
  });
}
```

### useRoutines

```javascript
import { useRoutines } from '@/hooks/useRoutines';

function RoutineEditor({ scheduleId }) {
  const {
    routines,
    addRoutine,
    updateRoutine,
    removeRoutine,
    reorderRoutines
  } = useRoutines(scheduleId);
}
```

---

## Related Documentation

- **User Guide**: `webui/docs/SCHEDULER_USER_GUIDE.md`
- **Cron Bridge**: `webui/docs/dev/api/cron-bridge.md`
- **CLAUDE.md**: Visual Scheduler System section
- **Schema Source**: `webui/backend/lib/schedule_schema.py`

---

## Validation Limits

| Limit | Value |
|-------|-------|
| Max schedule name | 200 characters |
| Max description | 2000 characters |
| Max actions per routine | 20 |
| Max routines per schedule | 10 |
| Max offset minutes | 1440 (24 hours) |
| Max interval minutes | 10080 (7 days) |
| Min interval minutes | 1 |
| Max cooldown minutes | 60 |
| Max recurring days | 365 |
