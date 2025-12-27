# Scheduler API Documentation

**Last Updated**: 2025-12-27
**Version**: Issues #208-233 Implementation
**Base URLs**:
- Visual Scheduler UI: `/api/scheduler/ui`
- Legacy Cron: `/api/scheduler`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Visual Scheduler UI Endpoints](#visual-scheduler-ui-endpoints)
5. [Legacy Cron Endpoints](#legacy-cron-endpoints)
6. [Data Structures](#data-structures)
7. [Usage Examples](#usage-examples)
8. [React Hooks Reference](#react-hooks-reference)
9. [Performance Characteristics](#performance-characteristics)
10. [Related Documentation](#related-documentation)

---

## Overview

The Scheduler API provides two systems for managing automated photography schedules:

**Visual Scheduler UI** (Issues #208-233): Modern visual scheduler with event patterns, multiple trigger types, and schedule preview.

**Legacy Cron** (Backward compatibility): Direct cron job management for advanced users.

**Key Features**:
- Event patterns with timed action sequences
- Multiple trigger types (interval, solar, moon phase, fixed time, sensor, cron)
- Schedule preview with conflict detection
- Built-in schedule templates
- Single active schedule enforcement
- Schedule validation before activation
- Deployment integration

**Implementation**:
- `webui/backend/routes/scheduler_ui.py` - Visual scheduler endpoints
- `webui/backend/routes/scheduler.py` - Legacy cron endpoints
- `webui/backend/services/scheduler_service.py` - Service layer
- `webui/backend/lib/schedule_schema.py` - Data structures and validation
- `webui/backend/lib/cron_bridge.py` - Schedule to cron conversion

---

## Authentication

**Current Status**: CSRF protection required for state-changing operations

**Security Measures**:
- CSRF tokens required for POST/PUT/DELETE endpoints
- Rate limiting on schedule CRUD (30 requests/minute)
- Rate limiting on activation (10 requests/minute)
- Input validation for all parameters
- Built-in schedule protection (cannot modify/delete)

**Future** (Issue #19): User authentication planned

---

## Error Responses

### Standard Error Format

All error responses follow this JSON structure:

```json
{
  "error": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful request |
| 201 | Created | Schedule created successfully |
| 400 | Bad Request | Invalid parameters, validation error |
| 403 | Forbidden | CSRF validation failed, cannot modify built-in |
| 404 | Not Found | Schedule not found |
| 409 | Conflict | Schedule activation blocked by conflicts |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

---

## Visual Scheduler UI Endpoints

### 1. List Schedules

List all schedules with optional filtering.

**Endpoint**: `GET /api/scheduler/ui/schedules`

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_builtin` | boolean | No | false | Include built-in schedules |
| `active_only` | boolean | No | false | Filter to active schedule only |

#### Response

**Success (200)**:

```json
{
  "schedules": [
    {
      "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Nightly Moth Survey",
      "description": "Automated moth photography from sunset to sunrise",
      "trigger_type": "interval",
      "enabled": true,
      "is_active": true,
      "created_at": "2025-12-20T10:30:00",
      "modified_at": "2025-12-20T15:45:00"
    }
  ],
  "total": 1
}
```

#### Examples

```bash
# List all user schedules
curl "http://localhost:5000/api/scheduler/ui/schedules"

# Include built-in schedules
curl "http://localhost:5000/api/scheduler/ui/schedules?include_builtin=true"

# Get only active schedule
curl "http://localhost:5000/api/scheduler/ui/schedules?active_only=true"
```

---

### 2. Get Schedule

Get full schedule details including embedded event patterns.

**Endpoint**: `GET /api/scheduler/ui/schedules/<schedule_id>`

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

#### Response

**Success (200)**:

```json
{
  "schema_version": "2.0",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Nightly Moth Survey",
  "description": "Automated moth photography from sunset to sunrise",
  "event_patterns": [
    {
      "pattern_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "UV Capture Cycle",
      "description": "Turn on UV lights, take photo, turn off lights",
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
      "category": "user",
      "tags": ["moth", "uv"],
      "duration_minutes": 15
    }
  ],
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "sunset",
      "end_time": "sunrise",
      "start_offset_minutes": 30,
      "end_offset_minutes": -30
    },
    "days_of_week": null
  },
  "solar_trigger": null,
  "moon_phase_trigger": null,
  "fixed_time_trigger": null,
  "sensor_trigger": null,
  "cron_trigger": null,
  "start_date": null,
  "end_date": null,
  "deployment_id": null,
  "create_deployment": false,
  "enabled": true,
  "is_active": true,
  "created_at": "2025-12-20T10:30:00",
  "modified_at": "2025-12-20T15:45:00",
  "modified_by": null
}
```

**Error Responses**:

```json
// 404 - Schedule not found
{
  "error": "Schedule not found"
}
```

#### Examples

```bash
# Get schedule details
curl "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000"
```

---

### 3. Get Active Schedule

Get the currently active schedule.

**Endpoint**: `GET /api/scheduler/ui/schedules/active`

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Response

**Success (200)**:

```json
{
  "active": true,
  "schedule": {
    "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Nightly Moth Survey",
    "description": "...",
    "event_patterns": [...],
    "trigger_type": "interval",
    "interval_trigger": {...},
    "enabled": true,
    "is_active": true,
    "created_at": "2025-12-20T10:30:00",
    "modified_at": "2025-12-20T15:45:00"
  }
}
```

**No Active Schedule**:

```json
{
  "active": false,
  "schedule": null
}
```

#### Examples

```bash
# Get active schedule
curl "http://localhost:5000/api/scheduler/ui/schedules/active"
```

---

### 4. Get Built-in Schedules

List all built-in schedule templates.

**Endpoint**: `GET /api/scheduler/ui/schedules/builtin`

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Response

**Success (200)**:

```json
{
  "schedules": [
    {
      "schedule_id": "builtin_hourly_night",
      "name": "Hourly Night Survey",
      "description": "Take photos every hour from sunset to sunrise",
      "trigger_type": "interval",
      "enabled": true,
      "is_active": false,
      "created_at": "2025-01-01T00:00:00",
      "modified_at": "2025-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

**Note**: Built-in schedules cannot be modified or deleted.

#### Examples

```bash
# List built-in schedules
curl "http://localhost:5000/api/scheduler/ui/schedules/builtin"
```

---

### 5. Create Schedule

Create a new schedule with embedded event patterns.

**Endpoint**: `POST /api/scheduler/ui/schedules`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "name": "Evening Moths",
  "description": "Capture moths every hour from sunset to midnight",
  "event_patterns": [
    {
      "pattern_id": "",
      "name": "UV Capture",
      "description": "UV light photography cycle",
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn on UV lights"
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 5,
          "parameters": {},
          "description": "Take photo"
        },
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 10,
          "parameters": {},
          "description": "Turn off UV lights"
        }
      ],
      "category": "user",
      "tags": []
    }
  ],
  "trigger_type": "interval",
  "interval_trigger": {
    "interval_minutes": 60,
    "time_window": {
      "start_time": "sunset",
      "end_time": "00:00",
      "start_offset_minutes": 30,
      "end_offset_minutes": 0
    },
    "days_of_week": null
  },
  "enabled": true
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Schedule name (max 200 chars) |
| `description` | string | No | Detailed description (max 2000 chars) |
| `event_patterns` | array | Yes | List of EventPattern objects (1-10 patterns) |
| `trigger_type` | string | Yes | Trigger type ("interval", "solar", "moon_phase", "fixed_time", "sensor", "cron") |
| `interval_trigger` | object | Conditional | Required if trigger_type="interval" |
| `solar_trigger` | object | Conditional | Required if trigger_type="solar" |
| `moon_phase_trigger` | object | Conditional | Required if trigger_type="moon_phase" |
| `fixed_time_trigger` | object | Conditional | Required if trigger_type="fixed_time" |
| `sensor_trigger` | object | Conditional | Required if trigger_type="sensor" |
| `cron_trigger` | object | Conditional | Required if trigger_type="cron" |
| `start_date` | string | No | Start date (ISO 8601: YYYY-MM-DD) |
| `end_date` | string | No | End date (ISO 8601: YYYY-MM-DD) |
| `deployment_id` | string | No | Linked deployment ID |
| `create_deployment` | boolean | No | Create deployment on activation (default: false) |
| `enabled` | boolean | No | Schedule enabled state (default: true) |

#### Response

**Success (201)**:

```json
{
  "message": "Schedule created",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "schedule": {
    "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Evening Moths",
    "description": "...",
    "event_patterns": [...],
    "trigger_type": "interval",
    "interval_trigger": {...},
    "enabled": true,
    "is_active": false,
    "created_at": "2025-12-27T10:30:00",
    "modified_at": "2025-12-27T10:30:00"
  }
}
```

**Error Responses**:

```json
// 400 - Missing required field
{
  "error": "Missing required field: name"
}

// 400 - Invalid schedule format
{
  "error": "Invalid schedule format"
}

// 400 - Validation error
{
  "error": "Schedule validation failed"
}

// 500 - Creation failed
{
  "error": "Failed to create schedule"
}
```

#### Examples

```bash
# Create interval schedule
curl -X POST "http://localhost:5000/api/scheduler/ui/schedules" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "name": "Evening Moths",
    "event_patterns": [{
      "name": "UV Capture",
      "actions": [
        {"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0},
        {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
        {"action_type": "gpio", "action_name": "attract_off", "offset_minutes": 10}
      ]
    }],
    "trigger_type": "interval",
    "interval_trigger": {
      "interval_minutes": 60,
      "time_window": {
        "start_time": "sunset",
        "end_time": "midnight",
        "start_offset_minutes": 30,
        "end_offset_minutes": 0
      }
    }
  }'
```

---

### 6. Update Schedule

Update an existing schedule.

**Endpoint**: `PUT /api/scheduler/ui/schedules/<schedule_id>`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON): Partial or complete schedule update data

```json
{
  "description": "Updated description",
  "enabled": false
}
```

#### Response

**Success (200)**:

```json
{
  "message": "Schedule updated",
  "schedule": {
    "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Evening Moths",
    "description": "Updated description",
    "enabled": false,
    "modified_at": "2025-12-27T11:00:00"
  }
}
```

**Error Responses**:

```json
// 400 - Validation error
{
  "error": "Validation failed"
}

// 403 - Cannot modify built-in
{
  "error": "Cannot modify built-in schedule"
}

// 404 - Not found
{
  "error": "Schedule not found"
}

// 500 - Update failed
{
  "error": "Failed to update schedule"
}
```

#### Examples

```bash
# Update schedule description
curl -X PUT "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"description": "Updated description"}'
```

---

### 7. Delete Schedule

Delete a schedule.

**Endpoint**: `DELETE /api/scheduler/ui/schedules/<schedule_id>`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "message": "Schedule deleted",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses**:

```json
// 403 - Cannot delete built-in
{
  "error": "Cannot delete built-in schedule"
}

// 404 - Not found
{
  "error": "Schedule not found"
}

// 500 - Deletion failed
{
  "error": "Failed to delete schedule"
}
```

#### Examples

```bash
# Delete schedule
curl -X DELETE "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

### 8. Activate Schedule

Activate a schedule (deactivates current active schedule).

**Endpoint**: `POST /api/scheduler/ui/schedules/<schedule_id>/activate`

**Rate Limiting**: 10 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

**Headers**:
- `Content-Type`: `application/json` (optional)
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON, optional):

```json
{
  "check_conflicts": true,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timezone": "America/Los_Angeles"
}
```

**Field Descriptions**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `check_conflicts` | boolean | No | true | Check for scheduling conflicts before activation |
| `latitude` | number | No | 0.0 | Latitude for solar/moon calculations (-90 to 90) |
| `longitude` | number | No | 0.0 | Longitude for solar/moon calculations (-180 to 180) |
| `timezone` | string | No | "UTC" | Timezone name (e.g., "America/New_York") |

**Note**: Both latitude and longitude must be provided together, or neither.

#### Response

**Success (200)**:

```json
{
  "message": "Schedule activated",
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses**:

```json
// 400 - Schedule disabled
{
  "error": "Schedule activation failed"
}

// 400 - Invalid coordinates
{
  "error": "Both latitude and longitude must be provided together"
}

// 400 - Coordinates out of range
{
  "error": "Invalid coordinates: Latitude must be between -90 and 90"
}

// 400 - Invalid timezone
{
  "error": "Invalid timezone: Unknown timezone"
}

// 404 - Not found
{
  "error": "Schedule not found"
}

// 409 - Conflict detected
{
  "error": "Schedule conflict detected",
  "conflict": true
}

// 500 - Activation failed
{
  "error": "Internal server error"
}
```

#### Examples

```bash
# Activate schedule with conflict check
curl -X POST "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000/activate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "check_conflicts": true,
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timezone": "America/Los_Angeles"
  }'

# Activate without conflict check
curl -X POST "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000/activate" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"check_conflicts": false}'
```

---

### 9. Deactivate Schedule

Deactivate the currently active schedule.

**Endpoint**: `POST /api/scheduler/ui/schedules/deactivate`

**Rate Limiting**: 10 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "message": "Schedule deactivated",
  "was_active": true,
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**No Active Schedule**:

```json
{
  "message": "No active schedule to deactivate",
  "was_active": false,
  "schedule_id": null
}
```

**Error Responses**:

```json
// 500 - Deactivation failed
{
  "error": "Failed to deactivate schedule"
}
```

#### Examples

```bash
# Deactivate current schedule
curl -X POST "http://localhost:5000/api/scheduler/ui/schedules/deactivate" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

### 10. Validate Schedule

Validate a schedule for conflicts without activating.

**Endpoint**: `POST /api/scheduler/ui/schedules/<schedule_id>/validate`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

**Headers**:
- `Content-Type`: `application/json` (optional)

**Body** (JSON, optional):

```json
{
  "days": 7,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timezone": "America/Los_Angeles"
}
```

**Field Descriptions**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `days` | integer | No | 7 | Preview days (1-90) |
| `latitude` | number | No | 0.0 | Latitude for solar/moon calculations (-90 to 90) |
| `longitude` | number | No | 0.0 | Longitude for solar/moon calculations (-180 to 180) |
| `timezone` | string | No | "UTC" | Timezone name |

#### Response

**Success (200)**:

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

**With Conflicts**:

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "valid": false,
  "has_warnings": true,
  "conflicts": [
    {
      "pattern_id": "660e8400-e29b-41d4-a716-446655440001",
      "pattern_name": "UV Capture",
      "execution_time": "2025-12-27T21:30:00",
      "conflict_type": "action_overlap",
      "severity": "error",
      "description": "Actions overlap with another pattern"
    }
  ],
  "total_conflicts": 1,
  "blocking_conflicts": 1
}
```

**Error Responses**:

```json
// 400 - Invalid parameters
{
  "error": "Both latitude and longitude must be provided together"
}

// 404 - Not found
{
  "error": "Schedule not found"
}

// 500 - Validation failed
{
  "error": "Internal server error"
}
```

#### Examples

```bash
# Validate schedule
curl -X POST "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "days": 7,
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timezone": "America/Los_Angeles"
  }'
```

---

### 11. Get Schedule Preview

Generate execution preview for a schedule.

**Endpoint**: `GET /api/scheduler/ui/schedules/<schedule_id>/preview`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `schedule_id` | string (UUID) | Yes | Schedule identifier |

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 7 | Number of days to preview (1-90) |
| `lat` | number | No | None | Override latitude (-90 to 90) |
| `lon` | number | No | None | Override longitude (-180 to 180) |
| `tz` | string | No | "UTC" | Timezone name |

#### Response

**Success (200)**:

```json
{
  "schedule_id": "550e8400-e29b-41d4-a716-446655440000",
  "schedule_name": "Nightly Moth Survey",
  "preview_start": "2025-12-27T00:00:00",
  "preview_end": "2026-01-03T00:00:00",
  "executions": [
    {
      "start_time": "2025-12-27T21:00:00",
      "end_time": "2025-12-27T21:15:00",
      "pattern_id": "660e8400-e29b-41d4-a716-446655440001",
      "pattern_name": "UV Capture Cycle",
      "trigger_info": "Interval: 60 minutes",
      "actions": [
        {
          "time": "2025-12-27T21:00:00",
          "action_name": "attract_on",
          "action_type": "gpio",
          "offset_minutes": 0,
          "description": "Turn on UV lights"
        },
        {
          "time": "2025-12-27T21:05:00",
          "action_name": "takephoto",
          "action_type": "camera",
          "offset_minutes": 5,
          "description": "Take photo"
        },
        {
          "time": "2025-12-27T21:15:00",
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
    "2025-12-27": {
      "date": "2025-12-27",
      "phase": "waning_crescent",
      "phase_name": "Waning Crescent",
      "illumination": 0.25
    }
  },
  "total_actions": 3,
  "total_executions": 1,
  "generated_at": "2025-12-27T10:00:00"
}
```

**Error Responses**:

```json
// 400 - Invalid days parameter
{
  "error": "Invalid days parameter"
}

// 400 - Invalid coordinates
{
  "error": "Invalid coordinates"
}

// 400 - Invalid timezone
{
  "error": "Invalid timezone"
}

// 404 - Schedule not found
{
  "error": "Schedule not found"
}

// 500 - Preview generation failed
{
  "error": "Internal server error",
  "message": "Failed to generate preview"
}
```

#### Examples

```bash
# Get 7-day preview
curl "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000/preview"

# Get 14-day preview with coordinates
curl "http://localhost:5000/api/scheduler/ui/schedules/550e8400-e29b-41d4-a716-446655440000/preview?days=14&lat=37.7749&lon=-122.4194&tz=America/Los_Angeles"
```

---

### 12. List Built-in Patterns

List all built-in event patterns extracted from built-in schedules.

**Endpoint**: `GET /api/scheduler/ui/patterns/builtin`

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Response

**Success (200)**:

```json
{
  "patterns": [
    {
      "pattern_id": "builtin_uv_capture",
      "name": "UV Light Capture",
      "description": "Standard UV light photography cycle",
      "actions": [
        {
          "action_type": "gpio",
          "action_name": "attract_on",
          "offset_minutes": 0,
          "parameters": {},
          "description": "Turn on UV lights"
        },
        {
          "action_type": "camera",
          "action_name": "takephoto",
          "offset_minutes": 5,
          "parameters": {},
          "description": "Take photo"
        },
        {
          "action_type": "gpio",
          "action_name": "attract_off",
          "offset_minutes": 10,
          "parameters": {},
          "description": "Turn off UV lights"
        }
      ],
      "category": "built-in",
      "tags": ["uv", "moth"],
      "source_schedule": "Hourly Night Survey",
      "duration_minutes": 10
    }
  ],
  "warnings": []
}
```

**Note**: Results are cached at module level for performance. Service restart required to refresh if built-in files are modified.

#### Examples

```bash
# List built-in patterns
curl "http://localhost:5000/api/scheduler/ui/patterns/builtin"
```

---

### 13. Validate Pattern

Validate an event pattern structure.

**Endpoint**: `POST /api/scheduler/ui/patterns/validate`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`

**Body** (JSON):

```json
{
  "name": "Pattern Name",
  "description": "Optional description",
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "offset_minutes": 0,
      "parameters": {},
      "description": ""
    }
  ],
  "category": "user",
  "tags": []
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Pattern name (max 200 chars) |
| `description` | string | No | Description (max 2000 chars) |
| `actions` | array | Yes | List of PatternAction objects (1-20 actions) |
| `category` | string | No | "user" or "built-in" (default: "user") |
| `tags` | array | No | Tags for filtering |

#### Response

**Valid Pattern (200)**:

```json
{
  "valid": true,
  "pattern": {
    "pattern_id": "auto-generated-uuid",
    "name": "Pattern Name",
    "description": "Optional description",
    "actions": [...],
    "category": "user",
    "tags": [],
    "duration_minutes": 0
  }
}
```

**Invalid Pattern (400)**:

```json
{
  "valid": false,
  "error": "Pattern name is required"
}
```

**Error Responses**:

```json
// 400 - Missing required field
{
  "valid": false,
  "error": "Missing required field: name"
}

// 400 - Invalid structure
{
  "valid": false,
  "error": "Invalid pattern structure"
}

// 500 - Validation error
{
  "valid": false,
  "error": "Internal server error during validation"
}
```

#### Examples

```bash
# Validate pattern
curl -X POST "http://localhost:5000/api/scheduler/ui/patterns/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "UV Capture",
    "actions": [
      {
        "action_type": "gpio",
        "action_name": "attract_on",
        "offset_minutes": 0
      }
    ]
  }'
```

---

### 14. Validate Cron Expression

Validate a cron expression and preview next executions (Expert Mode).

**Endpoint**: `POST /api/scheduler/ui/cron/validate`

**Rate Limiting**: 30 requests per minute

**Implementation**: `webui/backend/routes/scheduler_ui.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`

**Body** (JSON):

```json
{
  "expression": "*/5 * * * *",
  "count": 5
}
```

**Field Descriptions**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `expression` | string | Yes | - | Standard 5-field cron expression (max 100 chars) |
| `count` | integer | No | 5 | Number of next executions to preview (1-20) |

#### Response

**Valid Expression (200)**:

```json
{
  "valid": true,
  "expression": "*/5 * * * *",
  "next_executions": [
    "2025-12-27T10:05:00",
    "2025-12-27T10:10:00",
    "2025-12-27T10:15:00",
    "2025-12-27T10:20:00",
    "2025-12-27T10:25:00"
  ],
  "human_readable": "Every 5 minutes"
}
```

**Invalid Expression (400)**:

```json
{
  "valid": false,
  "error": "Invalid cron expression syntax"
}
```

**Error Responses**:

```json
// 400 - Missing expression
{
  "valid": false,
  "error": "Missing required field: expression"
}

// 400 - Empty expression
{
  "valid": false,
  "error": "Expression cannot be empty"
}

// 400 - Expression too long
{
  "valid": false,
  "error": "Expression too long (max 100 characters)"
}

// 400 - Invalid count
{
  "valid": false,
  "error": "Count must be between 1 and 20"
}

// 400 - Invalid syntax
{
  "valid": false,
  "error": "Invalid cron expression: cannot calculate execution times"
}

// 500 - Validation error
{
  "valid": false,
  "error": "Internal server error during validation"
}
```

#### Examples

```bash
# Validate cron expression
curl -X POST "http://localhost:5000/api/scheduler/ui/cron/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "0 */4 * * *",
    "count": 3
  }'
```

---

## Legacy Cron Endpoints

### 1. List Cron Jobs

List all Mothbox cron jobs.

**Endpoint**: `GET /api/scheduler/jobs`

**Implementation**: `webui/backend/routes/scheduler.py`

#### Response

**Success (200)**:

```json
{
  "jobs": [
    {
      "command": "/usr/bin/python3 /opt/mothbox/TakePhoto.py",
      "schedule": "0 * * * *",
      "enabled": true,
      "comment": "Hourly photo capture"
    }
  ]
}
```

#### Examples

```bash
# List cron jobs
curl "http://localhost:5000/api/scheduler/jobs"
```

---

### 2. Add Cron Job

Add a new cron job with command injection protection.

**Endpoint**: `POST /api/scheduler/job`

**Implementation**: `webui/backend/routes/scheduler.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "script_key": "takephoto",
  "schedule": "0 * * * *",
  "comment": "Hourly photo capture"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `script_key` | string | Yes | Whitelisted script key (see `cron_security.py`) |
| `schedule` | string | Yes | Cron schedule expression (5 fields) |
| `comment` | string | No | Job comment |

#### Response

**Success (200)**:

```json
{
  "success": true,
  "command": "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
}
```

**Error Responses**:

```json
// 400 - Missing parameters
{
  "error": "Missing script_key or schedule"
}

// 400 - Invalid script key
{
  "error": "Invalid script_key. Must be one of: ..."
}

// 400 - Script path validation failed
{
  "error": "Script path validation failed"
}

// 500 - Failed to add job
{
  "error": "Failed to add cron job"
}
```

#### Examples

```bash
# Add cron job
curl -X POST "http://localhost:5000/api/scheduler/job" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "script_key": "takephoto",
    "schedule": "0 * * * *",
    "comment": "Hourly photos"
  }'
```

---

### 3. Delete Cron Job

Delete a cron job with safety validation.

**Endpoint**: `DELETE /api/scheduler/job`

**Implementation**: `webui/backend/routes/scheduler.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "command": "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Full command string to delete |

#### Response

**Success (200)**:

```json
{
  "success": true,
  "removed_count": 1,
  "command": "/usr/bin/python3 /opt/mothbox/TakePhoto.py"
}
```

**Error Responses**:

```json
// 400 - Missing command
{
  "error": "Missing command"
}

// 400 - Not a Mothbox job
{
  "error": "Command does not appear to be a Mothbox job. Deletion rejected for safety.",
  "command": "..."
}

// 400 - Path not in MOTHBOX_HOME
{
  "error": "Command path is not within MOTHBOX_HOME (/opt/mothbox). Deletion rejected.",
  "command": "..."
}

// 500 - Deletion failed
{
  "error": "Failed to delete cron job"
}
```

#### Examples

```bash
# Delete cron job
curl -X DELETE "http://localhost:5000/api/scheduler/job" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"command": "/usr/bin/python3 /opt/mothbox/TakePhoto.py"}'
```

---

### 4. Get Scheduler Status

Get scheduler service status.

**Endpoint**: `GET /api/scheduler/status`

**Implementation**: `webui/backend/routes/scheduler.py`

#### Response

**Success (200)**:

```json
{
  "cron_active": true,
  "scheduler_script": "/opt/mothbox/Scheduler.py"
}
```

**Error Responses**:

```json
// 500 - Status check failed
{
  "error": "Failed to get scheduler status"
}
```

#### Examples

```bash
# Get scheduler status
curl "http://localhost:5000/api/scheduler/status"
```

---

## Data Structures

### Schedule

Complete schedule with embedded event patterns.

```json
{
  "schema_version": "2.0",
  "schedule_id": "UUID string",
  "name": "string (max 200 chars)",
  "description": "string (max 2000 chars)",
  "event_patterns": [EventPattern],
  "trigger_type": "interval|solar|moon_phase|fixed_time|sensor|cron",
  "interval_trigger": IntervalTrigger | null,
  "solar_trigger": SolarTrigger | null,
  "moon_phase_trigger": MoonPhaseTrigger | null,
  "fixed_time_trigger": FixedTimeTrigger | null,
  "sensor_trigger": SensorTrigger | null,
  "cron_trigger": CronTrigger | null,
  "start_date": "YYYY-MM-DD" | null,
  "end_date": "YYYY-MM-DD" | null,
  "deployment_id": "string" | null,
  "create_deployment": boolean,
  "enabled": boolean,
  "is_active": boolean,
  "created_at": "ISO 8601 datetime",
  "modified_at": "ISO 8601 datetime",
  "modified_by": "string" | null
}
```

### EventPattern

Reusable action sequence template.

```json
{
  "pattern_id": "UUID string",
  "name": "string (max 200 chars)",
  "description": "string (max 2000 chars)",
  "actions": [PatternAction],
  "category": "user|built-in",
  "tags": ["string"],
  "duration_minutes": number  // Computed from max action offset
}
```

### PatternAction

Single action within a pattern.

```json
{
  "action_type": "gpio|camera|gps_sync|service",
  "action_name": "attract_on|attract_off|flash_on|flash_off|takephoto|...",
  "offset_minutes": number,  // 0-1440
  "parameters": {},
  "description": "string (max 500 chars)"
}
```

### TimeWindow

Daily time window for execution.

```json
{
  "start_time": "HH:MM or solar_event",
  "end_time": "HH:MM or solar_event",
  "start_offset_minutes": number,  // +/- 120
  "end_offset_minutes": number     // +/- 120
}
```

### IntervalTrigger

Execute every N minutes within time window.

```json
{
  "interval_minutes": number,  // 1-10080 (1 min to 7 days)
  "time_window": TimeWindow,
  "days_of_week": [0-6] | null  // 0=Mon, 6=Sun
}
```

### SolarTrigger

Execute relative to solar event.

```json
{
  "solar_event": "dawn|sunrise|sunset|dusk|...",
  "offset_minutes": number,  // +/- 120
  "days_of_week": [0-6] | null
}
```

Solar events: `dawn`, `sunrise`, `noon`, `sunset`, `dusk`, `civil_dawn`, `civil_dusk`, `nautical_dawn`, `nautical_dusk`, `astronomical_dawn`, `astronomical_dusk`, `golden_hour_start`, `golden_hour_end`, `blue_hour_start`, `blue_hour_end`

### MoonPhaseTrigger

Execute on moon phases.

```json
{
  "phases": ["new|waxing_crescent|first_quarter|waxing_gibbous|full|waning_gibbous|last_quarter|waning_crescent"],
  "offset_days": number,  // +/- 7
  "time_window": TimeWindow | null
}
```

### FixedTimeTrigger

Execute at specific time daily.

```json
{
  "time": "HH:MM",
  "days_of_week": [0-6] | null
}
```

### SensorTrigger

Execute based on sensor readings.

```json
{
  "sensor_type": "motion|light|temperature",
  "threshold": number,
  "comparison": "gt|lt|eq|gte|lte",
  "cooldown_minutes": number,  // 0-60, default 5
  "time_window": TimeWindow | null
}
```

### CronTrigger

Raw cron expression (Expert Mode).

```json
{
  "cron_expression": "string"  // Standard 5-field cron (max 100 chars)
}
```

---

## Usage Examples

### Complete Workflow (JavaScript)

```javascript
// 1. Create schedule
const createScheduleExample = async () => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json())

  const response = await fetch('/api/scheduler/ui/schedules', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({
      name: 'Evening Moths',
      description: 'Hourly moth photography from sunset to midnight',
      event_patterns: [
        {
          name: 'UV Capture Cycle',
          actions: [
            { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
            { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
            { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 10 }
          ]
        }
      ],
      trigger_type: 'interval',
      interval_trigger: {
        interval_minutes: 60,
        time_window: {
          start_time: 'sunset',
          end_time: '00:00',
          start_offset_minutes: 30,
          end_offset_minutes: 0
        }
      }
    })
  })

  const schedule = await response.json()
  return schedule.schedule_id
}

// 2. Get preview
const getPreviewExample = async (scheduleId) => {
  const response = await fetch(
    `/api/scheduler/ui/schedules/${scheduleId}/preview?days=7&lat=37.7749&lon=-122.4194&tz=America/Los_Angeles`
  )
  const preview = await response.json()

  console.log(`Next ${preview.total_executions} executions:`)
  preview.executions.forEach(exec => {
    console.log(`${exec.start_time}: ${exec.pattern_name}`)
  })
}

// 3. Validate schedule
const validateScheduleExample = async (scheduleId) => {
  const response = await fetch(
    `/api/scheduler/ui/schedules/${scheduleId}/validate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        days: 7,
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: 'America/Los_Angeles'
      })
    }
  )

  const result = await response.json()

  if (result.valid) {
    console.log('Schedule is valid')
  } else {
    console.log(`Found ${result.blocking_conflicts} blocking conflicts`)
    result.conflicts.forEach(c => console.log(c.description))
  }
}

// 4. Activate schedule
const activateScheduleExample = async (scheduleId) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json())

  const response = await fetch(
    `/api/scheduler/ui/schedules/${scheduleId}/activate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken.csrf_token
      },
      body: JSON.stringify({
        check_conflicts: true,
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: 'America/Los_Angeles'
      })
    }
  )

  if (response.ok) {
    console.log('Schedule activated successfully')
  } else if (response.status === 409) {
    console.error('Schedule has conflicts')
  }
}

// Execute workflow
const main = async () => {
  try {
    const scheduleId = await createScheduleExample()
    await getPreviewExample(scheduleId)
    await validateScheduleExample(scheduleId)
    await activateScheduleExample(scheduleId)
  } catch (error) {
    console.error('Workflow failed:', error)
  }
}

main()
```

### React Hook Examples

```jsx
import {
  useSchedules,
  useSchedule,
  useSchedulePreview,
  useCreateSchedule,
  useActivateSchedule,
  useValidateSchedule
} from '../hooks/useSchedules'

function SchedulerUI() {
  const { data: schedules, isLoading } = useSchedules()
  const [selectedId, setSelectedId] = useState(null)
  const { data: schedule } = useSchedule(selectedId)
  const { data: preview } = useSchedulePreview(selectedId, { days: 7 })

  const createSchedule = useCreateSchedule()
  const activateSchedule = useActivateSchedule()
  const validateSchedule = useValidateSchedule()

  const handleCreate = () => {
    createSchedule.mutate({
      name: 'Evening Moths',
      event_patterns: [{
        name: 'UV Capture',
        actions: [
          { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
          { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
          { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 10 }
        ]
      }],
      trigger_type: 'interval',
      interval_trigger: {
        interval_minutes: 60,
        time_window: {
          start_time: 'sunset',
          end_time: '00:00',
          start_offset_minutes: 30,
          end_offset_minutes: 0
        }
      }
    }, {
      onSuccess: (response) => {
        setSelectedId(response.data.schedule_id)
      }
    })
  }

  const handleValidate = () => {
    validateSchedule.mutate({
      id: selectedId,
      data: {
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: 'America/Los_Angeles'
      }
    }, {
      onSuccess: (response) => {
        if (response.data.valid) {
          handleActivate()
        } else {
          alert(`${response.data.blocking_conflicts} conflicts found`)
        }
      }
    })
  }

  const handleActivate = () => {
    activateSchedule.mutate({
      id: selectedId,
      options: {
        latitude: 37.7749,
        longitude: -122.4194,
        timezone: 'America/Los_Angeles'
      }
    }, {
      onSuccess: () => {
        console.log('Schedule activated')
      }
    })
  }

  if (isLoading) return <div>Loading...</div>

  return (
    <div>
      <h1>Schedules</h1>
      <button onClick={handleCreate}>Create Schedule</button>

      <ul>
        {schedules?.schedules.map(s => (
          <li key={s.schedule_id} onClick={() => setSelectedId(s.schedule_id)}>
            {s.name} {s.is_active && '(Active)'}
          </li>
        ))}
      </ul>

      {schedule && (
        <div>
          <h2>{schedule.name}</h2>
          <p>{schedule.description}</p>
          <button onClick={handleValidate}>Validate & Activate</button>
        </div>
      )}

      {preview && (
        <div>
          <h3>Preview ({preview.total_executions} executions)</h3>
          <ul>
            {preview.executions.map((exec, i) => (
              <li key={i}>
                {exec.start_time}: {exec.pattern_name} ({exec.actions.length} actions)
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

### Python Client

```python
import requests
from typing import Dict, Any

class SchedulerClient:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()

        # Get CSRF token
        response = self.session.get(f"{base_url}/api/csrf-token")
        self.csrf_token = response.json()['csrf_token']

    def list_schedules(self, include_builtin: bool = False) -> Dict[str, Any]:
        """List all schedules."""
        params = {}
        if include_builtin:
            params['include_builtin'] = 'true'

        response = self.session.get(
            f"{self.base_url}/api/scheduler/ui/schedules",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Get schedule by ID."""
        response = self.session.get(
            f"{self.base_url}/api/scheduler/ui/schedules/{schedule_id}"
        )
        response.raise_for_status()
        return response.json()

    def create_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new schedule."""
        response = self.session.post(
            f"{self.base_url}/api/scheduler/ui/schedules",
            json=data,
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()

    def activate_schedule(
        self,
        schedule_id: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Activate schedule."""
        response = self.session.post(
            f"{self.base_url}/api/scheduler/ui/schedules/{schedule_id}/activate",
            json={
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()

    def get_preview(
        self,
        schedule_id: str,
        days: int = 7,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Get schedule preview."""
        params = {"days": days, "tz": timezone}
        if latitude is not None:
            params["lat"] = latitude
        if longitude is not None:
            params["lon"] = longitude

        response = self.session.get(
            f"{self.base_url}/api/scheduler/ui/schedules/{schedule_id}/preview",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage
client = SchedulerClient()

# Create schedule
schedule = client.create_schedule({
    "name": "Evening Moths",
    "event_patterns": [{
        "name": "UV Capture",
        "actions": [
            {"action_type": "gpio", "action_name": "attract_on", "offset_minutes": 0},
            {"action_type": "camera", "action_name": "takephoto", "offset_minutes": 5},
            {"action_type": "gpio", "action_name": "attract_off", "offset_minutes": 10}
        ]
    }],
    "trigger_type": "interval",
    "interval_trigger": {
        "interval_minutes": 60,
        "time_window": {
            "start_time": "sunset",
            "end_time": "00:00",
            "start_offset_minutes": 30,
            "end_offset_minutes": 0
        }
    }
})

schedule_id = schedule['schedule_id']
print(f"Created schedule: {schedule_id}")

# Get preview
preview = client.get_preview(schedule_id, days=7, latitude=37.7749, longitude=-122.4194)
print(f"Preview: {preview['total_executions']} executions")

# Activate
result = client.activate_schedule(schedule_id, latitude=37.7749, longitude=-122.4194)
print(f"Activated: {result['message']}")
```

---

## React Hooks Reference

All hooks from `useSchedules.js`:

| Hook | Type | Description | Parameters |
|------|------|-------------|------------|
| `useSchedules` | Query | List all schedules | `params`, `queryOptions` |
| `useSchedule` | Query | Get single schedule | `id`, `queryOptions` |
| `useActiveSchedule` | Query | Get active schedule | `queryOptions` |
| `useSchedulePreview` | Query | Get schedule preview | `id`, `params`, `queryOptions` |
| `useBuiltinSchedules` | Query | List built-in schedules | `queryOptions` |
| `useCreateSchedule` | Mutation | Create new schedule | - |
| `useUpdateSchedule` | Mutation | Update schedule | - |
| `useDeleteSchedule` | Mutation | Delete schedule | - |
| `useActivateSchedule` | Mutation | Activate schedule | - |
| `useDeactivateSchedule` | Mutation | Deactivate schedule | - |
| `useValidateSchedule` | Mutation | Validate schedule | - |

**Query Options**: All query hooks accept optional `queryOptions` parameter for customizing React Query behavior (e.g., `refetchInterval`, `onSuccess`, `onError`).

**Mutation Callbacks**: Mutation hooks accept `onSuccess` and `onError` callbacks in the mutation options.

**Cache Configuration**:
- Stale time: 5 minutes
- Garbage collection: 5 minutes (React Query default)
- Refetch on window focus: Enabled

---

## Performance Characteristics

### Response Times

| Endpoint | Response Time | Notes |
|----------|--------------|-------|
| `GET /schedules` | <50ms | List from storage |
| `GET /schedules/<id>` | <30ms | Single schedule lookup |
| `GET /schedules/active` | <30ms | Active schedule lookup |
| `GET /schedules/builtin` | <50ms | Built-in schedules from disk |
| `POST /schedules` | <100ms | Create and validate |
| `PUT /schedules/<id>` | <100ms | Update and validate |
| `DELETE /schedules/<id>` | <50ms | Delete from storage |
| `POST /schedules/<id>/activate` | <200ms | Activate and generate cron jobs |
| `POST /schedules/deactivate` | <100ms | Deactivate and clear cron |
| `GET /schedules/<id>/preview` | <500ms | Generate preview (7 days) |
| `GET /patterns/builtin` | <100ms | Cached after first request |
| `POST /patterns/validate` | <30ms | Pattern validation |
| `POST /cron/validate` | <50ms | Cron validation |

### Cache Configuration

**Built-in Patterns**:
- Module-level cache with thread-safe double-check locking
- Populated on first request
- Persists for process lifetime
- Service restart required to refresh

**Conflict Reports** (SchedulerService):
- LRU cache (128 schedules)
- 5-minute TTL
- Cache key: `(schedule_id, preview_days, latitude, longitude, timezone)`

### Resource Usage

**Memory**:
- Service baseline: ~5-10 MB
- Preview generation: +10-20 MB per request (7 days)
- Built-in patterns cache: ~1 MB

**Disk**:
- User schedules: ~5-50 KB per schedule
- Built-in schedules: ~200 KB total

**CPU**:
- Schedule CRUD: <1% CPU
- Preview generation: 5-15% CPU (single core, 7 days)
- Conflict detection: 10-20% CPU

---

## Related Documentation

- **Cron Bridge**: `webui/docs/dev/api/cron-bridge.md` - Schedule to cron conversion
- **Schedule Schema**: `webui/backend/lib/schedule_schema.py` - Data structures and validation
- **Scheduler Service**: `webui/backend/services/scheduler_service.py` - Business logic
- **Scheduler Storage**: `webui/backend/lib/schedule_storage.py` - File-based persistence
- **Schedule Preview**: `webui/backend/lib/schedule_preview.py` - Preview generation
- **Schedule Conflict**: `webui/backend/lib/schedule_conflict.py` - Conflict detection
- **User Guide**: Coming soon - Visual scheduler user documentation

---

**Document Version**: 1.0.0
**Last Validated**: 2025-12-27
**Issues**: #208 (Schema), #214 (Preview), #215 (Cron Bridge), #217 (Event Patterns), #218 (Schedule CRUD), #233 (Expert Mode)
