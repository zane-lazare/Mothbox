# Scheduler Preview API

Schedule preview generation API for the visual scheduler UI.

## Overview

The Scheduler Preview API generates execution timelines for schedules, showing:
- Pattern executions with absolute action times
- Moon phase information for calendar display
- Conflicts detected over the preview period

This API is designed to support the visual scheduler UI calendar view.

## Performance

- **Preview generation**: Scales with `days` parameter
- **Rate limit**: 30 requests per minute

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

## Related Documentation

- [Scheduler Dev Guide](../guides/SCHEDULER_DEV_GUIDE.md) - Complete scheduler architecture
- [Schedule Schema](../guides/SCHEDULER_DEV_GUIDE.md#data-structures) - JSON file format
- [Conflict Detection](../guides/SCHEDULER_DEV_GUIDE.md#conflict-detection) - How conflicts are detected
