# Scheduler UI API

Complete REST API for the visual scheduler UI (Issue #218).

## Overview

The Scheduler UI API provides endpoints for:
- **Schedule CRUD**: Create, read, update, delete schedules
- **Activation**: Activate/deactivate schedules for execution
- **Preview**: Generate execution timelines for calendar display
- **Validation**: Check for conflicts before activation
- **Event Patterns**: Manage reusable action sequences

All schedules use the **two-tier architecture**:
1. **Event Patterns**: Reusable action sequences with relative timing
2. **Schedules**: Define WHEN event patterns execute (embedded patterns for portability)

## Authentication

All state-changing endpoints (POST, PUT, DELETE) require CSRF tokens:
- Get token: `GET /api/csrf-token`
- Include in header: `X-CSRFToken: <token>`

## Rate Limiting

| Endpoint Type | Limit |
|--------------|-------|
| CRUD operations (POST/PUT/DELETE) | 30/min |
| Activation/deactivation | 10/min |
| Preview generation | 30/min |
| Validation | 30/min |
| Read operations (GET) | No limit |

## Endpoints

### Generate Schedule Preview

```
GET /api/scheduler/ui/schedules/{id}/preview
```

Generate an execution preview for a schedule over a specified period.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| days | integer | No | 7 | Number of days to preview (1-90) |
| lat | float | No | GPS from controls.txt | Override latitude (-90 to 90) |
| lon | float | No | GPS from controls.txt | Override longitude (-180 to 180) |
| tz | string | No | UTC | IANA timezone name (e.g., "America/New_York") |

**Example Request:**
```bash
curl "http://localhost:5000/api/scheduler/ui/schedules/nightly-survey/preview?days=7"
```

**Example Response:**
```json
{
  "schedule_id": "nightly-survey",
  "schedule_name": "Nightly Moth Survey",
  "preview_start": "2025-06-15T00:00:00+00:00",
  "preview_end": "2025-06-21T23:59:59.999999+00:00",
  "executions": [
    {
      "start_time": "2025-06-15T21:00:00+00:00",
      "end_time": "2025-06-15T21:15:00+00:00",
      "pattern_id": "uv-capture-cycle",
      "pattern_name": "UV Capture Cycle",
      "trigger_info": "interval:60m (21:00-05:00)",
      "actions": [
        {
          "time": "2025-06-15T21:00:00+00:00",
          "action_name": "attract_on",
          "action_type": "gpio",
          "offset_minutes": 0,
          "description": "Turn on UV attract lights"
        },
        {
          "time": "2025-06-15T21:05:00+00:00",
          "action_name": "takephoto",
          "action_type": "camera",
          "offset_minutes": 5,
          "description": "Capture photo"
        },
        {
          "time": "2025-06-15T21:15:00+00:00",
          "action_name": "attract_off",
          "action_type": "gpio",
          "offset_minutes": 15,
          "description": "Turn off UV lights"
        }
      ]
    }
  ],
  "conflicts": [],
  "moon_phases": {
    "2025-06-15": {
      "date": "2025-06-15",
      "phase": "waning_gibbous",
      "phase_name": "Waning Gibbous",
      "illumination": 0.72,
      "age_days": 18.5
    },
    "2025-06-16": {
      "date": "2025-06-16",
      "phase": "waning_gibbous",
      "phase_name": "Waning Gibbous",
      "illumination": 0.63,
      "age_days": 19.5
    }
  },
  "total_actions": 24,
  "total_executions": 8,
  "generated_at": "2025-06-15T12:00:00+00:00"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid parameters (days out of range, invalid coordinates, invalid timezone) |
| 404 | Schedule not found |
| 429 | Rate limit exceeded (30/min) |
| 500 | Internal server error |

**Error Response Examples:**

*400 Bad Request - Invalid Days:*
```json
{
  "error": "Invalid days parameter",
  "message": "Preview days must be at least 1, got 0"
}
```

*400 Bad Request - Invalid Coordinates:*
```json
{
  "error": "Invalid lat parameter",
  "message": "Expected number for lat, got 'abc'"
}
```

*400 Bad Request - Invalid Timezone:*
```json
{
  "error": "Invalid timezone",
  "message": "Invalid timezone 'NotATimezone'. Use IANA timezone names (e.g., 'America/New_York', 'Europe/London', 'UTC')"
}
```

*404 Not Found:*
```json
{
  "error": "Schedule not found",
  "message": "No schedule with ID 'nonexistent-schedule'"
}
```

*429 Rate Limited:*
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again later."
}
```

---

### List Schedules

```
GET /api/scheduler/ui/schedules
```

List all schedules with summary information.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| include_builtin | boolean | No | false | Include built-in schedules |
| active_only | boolean | No | false | Filter to active schedule only |

**Example Response:**
```json
{
  "schedules": [
    {
      "schedule_id": "nightly-survey",
      "name": "Nightly Moth Survey",
      "description": "Hourly captures from 9 PM to 5 AM",
      "trigger_type": "interval",
      "enabled": true,
      "is_active": true,
      "created_at": "2025-06-01T00:00:00Z",
      "modified_at": "2025-06-10T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

### Get Schedule Details

```
GET /api/scheduler/ui/schedules/{id}
```

Get full schedule details including event patterns.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Example Response:**
```json
{
  "schedule_id": "nightly-survey",
  "name": "Nightly Moth Survey",
  "description": "Hourly captures from 9 PM to 5 AM",
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "21:00",
      "end_time": "05:00"
    }
  },
  "event_patterns": [
    {
      "pattern_id": "uv-capture-cycle",
      "name": "UV Capture Cycle",
      "actions": [...]
    }
  ],
  "enabled": true,
  "is_active": true
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Schedule not found |

---

## Trigger Info Formats

The `trigger_info` field in preview executions describes how the pattern was triggered:

| Trigger Type | Format | Example |
|--------------|--------|---------|
| Interval | `interval:{minutes}m ({start}-{end})` | `interval:60m (21:00-05:00)` |
| Solar | `{event}` or `{event}+{offset}` | `sunset+30`, `sunrise-15` |
| Moon Phase | `moon:{phases}` or `moon:{phases}+{offset}d` | `moon:full`, `moon:full,new+2d` |
| Fixed Time | `daily:{time}` | `daily:21:00` |
| Sensor | `sensor:{type}` | `sensor:motion` |

---

## Location Fallback

When latitude/longitude are not provided:
1. Tries to read from GPS data in `controls.txt`
2. Falls back to (0, 0) with a warning logged

Solar-based triggers (sunset, sunrise) require valid coordinates for accurate times.

---

### Get Active Schedule

```
GET /api/scheduler/ui/schedules/active
```

Get the currently active schedule.

**Example Response (Active):**
```json
{
  "active": true,
  "schedule": {
    "schedule_id": "nightly-survey",
    "name": "Nightly Moth Survey",
    "trigger_type": "interval",
    "enabled": true,
    "is_active": true,
    ...
  }
}
```

**Example Response (None Active):**
```json
{
  "active": false,
  "schedule": null
}
```

---

### List Built-in Schedules

```
GET /api/scheduler/ui/schedules/builtin
```

List all built-in (read-only) schedules.

**Example Response:**
```json
{
  "schedules": [
    {
      "schedule_id": "nightly_moth_survey",
      "name": "Nightly Moth Survey",
      "description": "Standard moth survey from dusk to dawn",
      "trigger_type": "solar",
      "enabled": true,
      "is_active": false,
      "created_at": "2025-01-01T00:00:00Z",
      "modified_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3
}
```

**Note:** Built-in schedules cannot be modified or deleted.

---

## Schedule CRUD Operations

### Create Schedule

```
POST /api/scheduler/ui/schedules
```

Create a new schedule with embedded event patterns.

**Rate Limit:** 30/min

**Request Body:**
```json
{
  "name": "My Custom Survey",
  "description": "Description of the survey",
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "21:00",
      "end_time": "05:00"
    },
    "days_of_week": null
  },
  "event_patterns": [
    {
      "name": "UV Capture Cycle",
      "description": "Turn on UV, capture photo, turn off",
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "description": "Turn on UV lights"
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 5,
          "description": "Capture photo"
        },
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 15,
          "description": "Turn off UV lights"
        }
      ]
    }
  ],
  "start_date": "2025-06-01",
  "end_date": "2025-08-31",
  "enabled": true
}
```

**Trigger Types:**

| Type | Required Config | Description |
|------|-----------------|-------------|
| `interval` | `interval_trigger` | Every N minutes within time window |
| `solar` | `solar_trigger` | Relative to sun position (sunset, sunrise) |
| `moon_phase` | `moon_phase_trigger` | On specific lunar phases |
| `fixed_time` | `fixed_time_trigger` | Specific clock time daily |
| `sensor` | `sensor_trigger` | Based on sensor readings |

**Response (201 Created):**
```json
{
  "message": "Schedule created",
  "schedule_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schedule": { ... }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Missing required field, invalid format, or validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

### Update Schedule

```
PUT /api/scheduler/ui/schedules/{id}
```

Update an existing schedule. Supports partial updates.

**Rate Limit:** 30/min

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Request Body (Partial Update):**
```json
{
  "name": "Updated Survey Name",
  "description": "Updated description",
  "enabled": false
}
```

**Response (200 OK):**
```json
{
  "message": "Schedule updated",
  "schedule": { ... }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Validation error |
| 403 | Cannot modify built-in schedule |
| 404 | Schedule not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

### Delete Schedule

```
DELETE /api/scheduler/ui/schedules/{id}
```

Delete a schedule.

**Rate Limit:** 30/min

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Response (200 OK):**
```json
{
  "message": "Schedule deleted",
  "schedule_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 403 | Cannot delete built-in schedule |
| 404 | Schedule not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Schedule Activation

### Activate Schedule

```
POST /api/scheduler/ui/schedules/{id}/activate
```

Activate a schedule for execution. Deactivates any currently active schedule first.

**Rate Limit:** 10/min

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Request Body (Optional):**
```json
{
  "check_conflicts": true,
  "latitude": 35.6762,
  "longitude": 139.6503,
  "timezone": "Asia/Tokyo"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| check_conflicts | boolean | true | Check for conflicts before activation |
| latitude | float | 0.0 | Latitude for solar calculations (-90 to 90) |
| longitude | float | 0.0 | Longitude for solar calculations (-180 to 180) |
| timezone | string | "UTC" | IANA timezone name |

**Response (200 OK):**
```json
{
  "message": "Schedule activated",
  "schedule_id": "nightly-survey"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Schedule is disabled, invalid coordinates, or activation failed |
| 404 | Schedule not found |
| 409 | Schedule has blocking conflicts |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

**409 Conflict Response:**
```json
{
  "error": "Schedule conflict detected",
  "conflict": true
}
```

---

### Deactivate Schedule

```
POST /api/scheduler/ui/schedules/deactivate
```

Deactivate the currently active schedule. Idempotent - returns success even if no schedule is active.

**Rate Limit:** 10/min

**Response (200 OK - Was Active):**
```json
{
  "message": "Schedule deactivated",
  "was_active": true,
  "schedule_id": "nightly-survey"
}
```

**Response (200 OK - None Active):**
```json
{
  "message": "No active schedule to deactivate",
  "was_active": false,
  "schedule_id": null
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Schedule Validation

### Validate Schedule

```
POST /api/scheduler/ui/schedules/{id}/validate
```

Validate a schedule for conflicts without activating it.

**Rate Limit:** 30/min

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Schedule ID |

**Request Body (Optional):**
```json
{
  "days": 14,
  "latitude": 35.6762,
  "longitude": 139.6503,
  "timezone": "Asia/Tokyo"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| days | integer | 7 | Preview period for conflict detection (1-90) |
| latitude | float | 0.0 | Latitude for solar calculations |
| longitude | float | 0.0 | Longitude for solar calculations |
| timezone | string | "UTC" | IANA timezone name |

**Response (200 OK):**
```json
{
  "schedule_id": "nightly-survey",
  "valid": true,
  "has_warnings": false,
  "conflicts": [],
  "total_conflicts": 0,
  "blocking_conflicts": 0
}
```

**Response with Conflicts:**
```json
{
  "schedule_id": "nightly-survey",
  "valid": false,
  "has_warnings": true,
  "conflicts": [
    {
      "type": "overlap",
      "severity": "error",
      "time_start": "2025-06-15T21:00:00Z",
      "time_end": "2025-06-15T21:30:00Z",
      "description": "Pattern execution overlaps with existing scheduled event"
    }
  ],
  "total_conflicts": 1,
  "blocking_conflicts": 1
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid coordinates |
| 404 | Schedule not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Event Pattern Endpoints

### List Built-in Patterns

```
GET /api/scheduler/ui/patterns/builtin
```

List all built-in event patterns extracted from built-in schedules.

**Example Response:**
```json
[
  {
    "pattern_id": "uv-capture-cycle",
    "name": "UV Capture Cycle",
    "description": "Standard UV light capture sequence",
    "actions": [
      {
        "action_type": "gpio",
        "action_name": "attract_on",
        "offset_minutes": 0,
        "description": "Turn on UV lights"
      },
      {
        "action_type": "camera",
        "action_name": "takephoto",
        "offset_minutes": 5,
        "description": "Capture photo"
      },
      {
        "action_type": "gpio",
        "action_name": "attract_off",
        "offset_minutes": 15,
        "description": "Turn off UV lights"
      }
    ],
    "category": "built-in",
    "tags": ["uv", "capture", "standard"],
    "source_schedule": "Nightly Moth Survey",
    "duration_minutes": 15
  }
]
```

---

### Validate Event Pattern

```
POST /api/scheduler/ui/patterns/validate
```

Validate an event pattern structure.

**Rate Limit:** 30/min

**Request Body:**
```json
{
  "name": "My Custom Pattern",
  "description": "Description of the pattern",
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "offset_minutes": 0,
      "description": "Turn on lights"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 5,
      "description": "Capture photo"
    }
  ],
  "category": "user",
  "tags": ["custom"]
}
```

**Validation Rules:**

| Field | Constraint |
|-------|------------|
| name | Required, max 200 characters |
| description | Optional, max 2000 characters |
| actions | Required, 1-20 actions |
| action_type | One of: `gpio`, `camera`, `gps_sync`, `service` |
| action_name | Depends on action_type (e.g., `attract_on`, `takephoto`) |
| offset_minutes | 0-1440 (max 24 hours) |
| category | `user` or `built-in` |

**Response (200 OK - Valid):**
```json
{
  "valid": true,
  "pattern": { ... }
}
```

**Response (400 Bad Request - Invalid):**
```json
{
  "valid": false,
  "error": "Action offset exceeds 1440 minutes (24 hours)"
}
```

---

## Trigger Info Formats

The `trigger_info` field in preview executions describes how the pattern was triggered:

| Trigger Type | Format | Example |
|--------------|--------|---------|
| Interval | `interval:{minutes}m ({start}-{end})` | `interval:60m (21:00-05:00)` |
| Solar | `{event}` or `{event}+{offset}` | `sunset+30`, `sunrise-15` |
| Moon Phase | `moon:{phases}` or `moon:{phases}+{offset}d` | `moon:full`, `moon:full,new+2d` |
| Fixed Time | `daily:{time}` | `daily:21:00` |
| Sensor | `sensor:{type}` | `sensor:motion` |

---

## Location Fallback

When latitude/longitude are not provided:
1. Tries to read from GPS data in `controls.txt`
2. Falls back to (0, 0) with a warning logged

Solar-based triggers (sunset, sunrise) require valid coordinates for accurate times.

---

## Schedule Schema Reference

### Action Types

| Type | Actions | Description |
|------|---------|-------------|
| `gpio` | `attract_on`, `attract_off`, `flash_on`, `flash_off` | GPIO relay control |
| `camera` | `takephoto` | Camera capture |
| `gps_sync` | `sync` | GPS time synchronization |
| `service` | `backup`, `update_display` | System services |

### Trigger Configurations

**Interval Trigger:**
```json
{
  "interval_minutes": 60,
  "time_window": {
    "start_time": "21:00",
    "end_time": "05:00"
  },
  "days_of_week": [0, 1, 2, 3, 4]
}
```

**Solar Trigger:**
```json
{
  "solar_event": "sunset",
  "offset_minutes": 30,
  "days_of_week": null
}
```

**Moon Phase Trigger:**
```json
{
  "phases": ["full", "new"],
  "offset_days": 2,
  "time_window": {
    "start_time": "dusk",
    "end_time": "dawn"
  }
}
```

**Fixed Time Trigger:**
```json
{
  "time": "21:00",
  "days_of_week": [0, 1, 2, 3, 4, 5, 6]
}
```

**Sensor Trigger:**
```json
{
  "sensor_type": "motion",
  "threshold": 0,
  "comparison": "gt",
  "cooldown_minutes": 5,
  "time_window": {
    "start_time": "21:00",
    "end_time": "05:00"
  }
}
```

---

## Related Documentation

- [Scheduler Dev Guide](../guides/SCHEDULER_DEV_GUIDE.md) - Complete scheduler architecture
- [Schedule Schema](../guides/SCHEDULER_DEV_GUIDE.md#data-structures) - JSON file format
- [Conflict Detection](../guides/SCHEDULER_DEV_GUIDE.md#conflict-detection) - How conflicts are detected
- [Cron Bridge](./cron-bridge.md) - Schedule to cron conversion
