# Event Patterns API

Event pattern management API for the visual scheduler UI.

## Overview

The Event Patterns API provides access to built-in event patterns and validation for user-defined patterns. Event patterns are reusable templates defining sequences of timed actions (e.g., "UV Capture Cycle" with UV lights on, photo capture, UV lights off).

Patterns are used within schedules to define what actions should happen when a trigger fires.

## Performance

- **Built-in patterns**: Cached on first request (requires server restart to refresh)
- **Validation**: Rate limited to 30 requests per minute

## Endpoints

### List Built-in Patterns

```
GET /api/scheduler/ui/patterns/builtin
```

List all built-in event patterns extracted from built-in schedule files.

**Query Parameters:** None

**Example Request:**
```bash
curl "http://localhost:5000/api/scheduler/ui/patterns/builtin"
```

**Example Response:**
```json
[
  {
    "pattern_id": "uv-capture-cycle",
    "name": "UV Capture Cycle",
    "description": "Turn on UV lights, capture photo, turn off lights",
    "actions": [
      {
        "action_type": "gpio",
        "action_name": "attract_on",
        "offset_minutes": 0,
        "parameters": {},
        "description": "Turn on UV attract lights"
      },
      {
        "action_type": "camera",
        "action_name": "takephoto",
        "offset_minutes": 5,
        "parameters": {},
        "description": "Capture photo"
      },
      {
        "action_type": "gpio",
        "action_name": "attract_off",
        "offset_minutes": 15,
        "parameters": {},
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| pattern_id | string | Unique pattern identifier |
| name | string | Pattern name (max 200 chars) |
| description | string | Pattern description (max 2000 chars) |
| actions | array | List of PatternAction objects (1-20 actions) |
| category | string | Always "built-in" for this endpoint |
| tags | array | Pattern tags for categorization |
| source_schedule | string | Name of schedule containing this pattern |
| duration_minutes | number | Computed from max action offset |

**PatternAction Schema:**

| Field | Type | Description |
|-------|------|-------------|
| action_type | string | Action category: "gpio", "camera", "gps_sync", "service" |
| action_name | string | Specific action: "attract_on", "takephoto", etc. |
| offset_minutes | number | Time offset from pattern start (0-1440 minutes) |
| parameters | object | Action-specific parameters |
| description | string | Human-readable action description |

**Error Responses:**

| Status | Description |
|--------|-------------|
| 500 | Internal server error |

---

### Validate Event Pattern

```
POST /api/scheduler/ui/patterns/validate
```

Validate an event pattern structure against the schema.

**Rate Limit:** 30 requests per minute

**Request Body:**
```json
{
  "name": "My Custom Pattern",
  "description": "A custom pattern for testing",
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "offset_minutes": 0,
      "parameters": {},
      "description": "Turn on lights"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 5,
      "parameters": {},
      "description": "Take a photo"
    }
  ],
  "category": "user",
  "tags": ["custom", "test"]
}
```

**Request Schema:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Max 200 characters |
| description | string | No | Max 2000 characters |
| actions | array | Yes | 1-20 PatternAction objects |
| category | string | No | "user" or "built-in" (default: "user") |
| tags | array | No | List of strings |

**Success Response (200 OK):**
```json
{
  "valid": true,
  "pattern": {
    "pattern_id": "",
    "name": "My Custom Pattern",
    "description": "A custom pattern for testing",
    "actions": [
      {
        "action_type": "gpio",
        "action_name": "attract_on",
        "offset_minutes": 0,
        "parameters": {},
        "description": "Turn on lights"
      },
      {
        "action_type": "camera",
        "action_name": "takephoto",
        "offset_minutes": 5,
        "parameters": {},
        "description": "Take a photo"
      }
    ],
    "category": "user",
    "tags": ["custom", "test"]
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "valid": false,
  "error": "Pattern name cannot be empty"
}
```

**Error Responses:**

| Status | Description | Example Error Messages |
|--------|-------------|------------------------|
| 400 | Invalid pattern structure | "Missing required field: name" |
| 400 | Missing required fields | "Missing required field: actions" |
| 400 | Invalid field values | "Pattern name cannot be empty" |
| 400 | Invalid JSON | "Request body must be valid JSON" |
| 400 | Not a JSON object | "Request body must be a JSON object" |
| 429 | Rate limit exceeded | "Rate limit exceeded. Try again later." |
| 500 | Internal server error | "Internal server error during validation" |

**Validation Rules:**

- **name**: Required, non-empty, max 200 characters
- **description**: Optional, max 2000 characters
- **actions**: Required, must contain 1-20 actions
- **action.offset_minutes**: Must be 0-1440 (24 hours)
- **action.action_type**: Must be valid type ("gpio", "camera", "gps_sync", "service")
- **action.action_name**: Must be non-empty
- **category**: Optional, defaults to "user"
- **tags**: Optional, list of strings

---

## Error Response Format

All error responses follow this structure:

```json
{
  "valid": false,
  "error": "Descriptive error message"
}
```

Or for non-validation endpoints:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

---

## Pattern Categories

| Category | Description | Source |
|----------|-------------|--------|
| built-in | Official patterns from built-in schedules | Extracted from `presets_builtin/schedules/*.json` |
| user | User-defined patterns | Created by users via UI or API |

---

## Caching Behavior

Built-in patterns are cached on first request for performance:

1. **First request**: Reads all schedule files from `presets_builtin/schedules/`
2. **Subsequent requests**: Returns cached patterns (no disk I/O)
3. **Cache refresh**: Requires server restart if built-in files are modified

This caching strategy ensures fast response times while built-in patterns remain static during runtime.

---

## Pattern Deduplication

When listing built-in patterns:
- Patterns with `pattern_id` are deduplicated (only first occurrence kept)
- Patterns without `pattern_id` are always included (cannot deduplicate)
- Deduplication is based on `pattern_id` across all built-in schedule files

---

## Action Types

| Type | Description | Example Actions |
|------|-------------|-----------------|
| gpio | GPIO relay control | attract_on, attract_off, flash_on, flash_off, uv_on, uv_off |
| camera | Camera operations | takephoto, start_stream, stop_stream |
| gps_sync | GPS synchronization | sync_time, get_coordinates |
| service | System services | start_service, stop_service, restart_service |

---

## Related Documentation

- [Scheduler Dev Guide](../guides/SCHEDULER_DEV_GUIDE.md) - Complete scheduler architecture
- [Schedule Schema](../guides/SCHEDULER_DEV_GUIDE.md#data-structures) - JSON file format
- [Schedule Preview API](scheduler-preview.md) - Preview generation for schedules
