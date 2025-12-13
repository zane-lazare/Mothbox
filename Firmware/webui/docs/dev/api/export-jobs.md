# Export Job Queue API Documentation

**Last Updated**: 2025-12-13
**Version**: Issue #122 Implementation
**Base URL**: `/api/export`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Responses](#error-responses)
4. [Job Lifecycle](#job-lifecycle)
5. [Export Job Endpoints](#export-job-endpoints)
6. [Export Formats](#export-formats)
7. [Filter Options](#filter-options)
8. [Performance Characteristics](#performance-characteristics)
9. [Usage Examples](#usage-examples)

---

## Overview

The Export Job Queue API provides asynchronous background processing for long-running photo export operations. Jobs are queued, executed one at a time, and persist across server restarts.

**Key Features**:
- Async job queue with SQLite persistence
- Single job concurrency (protects Pi resources)
- Progress tracking with real-time status updates
- 10-minute default timeout per job
- 1-hour job TTL (automatic cleanup)
- Support for multiple export formats (Darwin Core, iNaturalist, JSON, CSV)
- Flexible filtering (date range, deployment, tags, series type, explicit photo list)

**Implementation**:
- `webui/backend/routes/export.py` - REST API endpoints
- `webui/backend/services/export_job_service.py` - Job queue service
- `webui/backend/lib/export_job_db.py` - SQLite persistence
- `webui/backend/lib/export_job_types.py` - Type definitions

---

## Authentication

**Current Status**: CSRF protection required for state-changing operations

**Security Measures**:
- CSRF tokens required for POST/DELETE endpoints
- Rate limiting on job creation (5 requests/minute)
- Path traversal protection on download endpoint
- Input validation for all parameters

**Future** (Issue #175): API key authentication planned

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
| 201 | Created | Job created successfully |
| 400 | Bad Request | Invalid parameters, validation error |
| 403 | Forbidden | CSRF validation failed |
| 404 | Not Found | Job not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Export job service not initialized |

---

## Job Lifecycle

Jobs transition through the following states:

```
pending → running → completed
                 → failed
                 → cancelled
                 → expired
```

### State Descriptions

| State | Description | Transitions To |
|-------|-------------|----------------|
| `pending` | Job created, waiting in queue | `running`, `cancelled` |
| `running` | Job currently executing | `completed`, `failed`, `cancelled` |
| `completed` | Job finished successfully, output available | `expired` |
| `failed` | Job encountered error and stopped | - |
| `cancelled` | Job cancelled by user | - |
| `expired` | Output file TTL expired, file deleted | - |

### Timeouts and TTL

- **Execution timeout**: 10 minutes (default, configurable)
- **Job TTL**: 1 hour after completion (default, configurable)
- **Max history**: 50 completed jobs (older jobs auto-deleted)

---

## Export Job Endpoints

### 1. Create Export Job

Create and queue a new export job.

**Endpoint**: `POST /api/export/jobs`

**Rate Limiting**: 5 requests per minute

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Headers**:
- `Content-Type`: `application/json`
- `X-CSRFToken`: CSRF token (required)

**Body** (JSON):

```json
{
  "format": "darwin_core",
  "filter": {
    "date_start": "2024-01-01",
    "date_end": "2024-12-31",
    "deployment": "forest_2024",
    "tags": ["moth", "nocturnal"],
    "series_type": "hdr",
    "has_species": true,
    "photo_paths": null
  },
  "options": {
    "include_photos": true,
    "zip_compression": 9
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format` | string | Yes | Export format (see [Export Formats](#export-formats)) |
| `filter` | object | Yes | Photo selection criteria (see [Filter Options](#filter-options)) |
| `options` | object | No | Format-specific options |

#### Response

**Success (201)**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "format": "darwin_core",
  "created_at": 1702483200.0,
  "message": "Export job created successfully"
}
```

**Error Responses**:

```json
// 400 - Invalid format
{
  "error": "Invalid format: 'invalid_format'. Valid formats: darwin_core, inaturalist, json, csv"
}

// 400 - Missing required filter
{
  "error": "Filter is required"
}

// 400 - Invalid filter parameter
{
  "error": "Invalid date_start format. Use ISO 8601: YYYY-MM-DD"
}

// 429 - Rate limit exceeded
{
  "error": "Rate limit exceeded. Try again in 60 seconds."
}

// 503 - Service unavailable
{
  "error": "Export job service not available"
}
```

#### Examples

```bash
# Create Darwin Core export job
curl -X POST "http://localhost:5000/api/export/jobs" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "format": "darwin_core",
    "filter": {
      "date_start": "2024-01-01",
      "deployment": "forest_2024"
    }
  }'

# Create job with explicit photo list
curl -X POST "http://localhost:5000/api/export/jobs" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "format": "inaturalist",
    "filter": {
      "photo_paths": [
        "2024-01/photo1.jpg",
        "2024-01/photo2.jpg"
      ]
    },
    "options": {
      "include_photos": true
    }
  }'
```

---

### 2. List Export Jobs

List all export jobs with optional filtering and pagination.

**Endpoint**: `GET /api/export/jobs`

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | None | Filter by status (pending, running, completed, failed, cancelled, expired) |
| `limit` | integer | No | 50 | Max jobs to return (max: 100) |
| `offset` | integer | No | 0 | Offset for pagination |

#### Response

**Success (200)**:

```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "format": "darwin_core",
      "filter": {
        "date_start": "2024-01-01",
        "deployment": "forest_2024"
      },
      "progress": {
        "current": 100,
        "total": 100,
        "percent": 100,
        "phase": "finalizing"
      },
      "created_at": 1702483200.0,
      "started_at": 1702483205.0,
      "completed_at": 1702483265.0,
      "output_path": "/tmp/exports/export_550e8400.csv",
      "output_size_bytes": 524288,
      "photo_count": 100,
      "error_message": null
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "running",
      "format": "inaturalist",
      "progress": {
        "current": 45,
        "total": 200,
        "percent": 22,
        "phase": "exporting"
      },
      "created_at": 1702483300.0,
      "started_at": 1702483305.0,
      "completed_at": null,
      "output_path": null,
      "photo_count": 0,
      "error_message": null
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Error Responses**:

```json
// 400 - Invalid status filter
{
  "error": "Invalid status: 'invalid'. Valid statuses: pending, running, completed, failed, cancelled, expired"
}

// 400 - Invalid pagination
{
  "error": "Limit must be between 1 and 100"
}
```

#### Examples

```bash
# List all jobs
curl "http://localhost:5000/api/export/jobs"

# List only completed jobs
curl "http://localhost:5000/api/export/jobs?status=completed"

# Paginate results
curl "http://localhost:5000/api/export/jobs?limit=10&offset=20"
```

---

### 3. Get Job Status

Get detailed status and progress for a specific export job.

**Endpoint**: `GET /api/export/jobs/<job_id>`

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job identifier |

#### Response

**Success (200)**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "format": "darwin_core",
  "filter": {
    "date_start": "2024-01-01",
    "deployment": "forest_2024"
  },
  "progress": {
    "current": 45,
    "total": 100,
    "percent": 45,
    "phase": "exporting"
  },
  "created_at": 1702483200.0,
  "started_at": 1702483205.0,
  "completed_at": null,
  "expires_at": null,
  "output_path": null,
  "output_size_bytes": 0,
  "photo_count": 0,
  "error_message": null,
  "errors": []
}
```

**Completed Job Response**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "format": "darwin_core",
  "progress": {
    "current": 100,
    "total": 100,
    "percent": 100,
    "phase": "completed"
  },
  "created_at": 1702483200.0,
  "started_at": 1702483205.0,
  "completed_at": 1702483265.0,
  "expires_at": 1702486865.0,
  "output_path": "/tmp/exports/export_550e8400.csv",
  "output_size_bytes": 524288,
  "photo_count": 100,
  "error_message": null,
  "errors": []
}
```

**Failed Job Response**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": {
    "current": 23,
    "total": 100,
    "percent": 23,
    "phase": "exporting"
  },
  "created_at": 1702483200.0,
  "started_at": 1702483205.0,
  "completed_at": 1702483230.0,
  "error_message": "Export failed: Disk full",
  "errors": [
    {
      "photo": "2024-01/photo23.jpg",
      "error": "Failed to write file: No space left on device"
    }
  ]
}
```

**Error Responses**:

```json
// 404 - Job not found
{
  "error": "Job not found"
}
```

#### Examples

```bash
# Get job status
curl "http://localhost:5000/api/export/jobs/550e8400-e29b-41d4-a716-446655440000"

# Poll for completion (React)
const { data } = useQuery({
  queryKey: ['export-job', jobId],
  queryFn: () =>
    fetch(`/api/export/jobs/${jobId}`).then(r => r.json()),
  refetchInterval: (data) =>
    data?.status === 'running' ? 2000 : false  // Poll every 2s while running
});
```

---

### 4. Download Export Result

Download the completed export file.

**Endpoint**: `GET /api/export/jobs/<job_id>/download`

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job identifier |

#### Response

**Success (200)**:

- **Content-Type**: Depends on export format
  - Darwin Core CSV: `text/csv`
  - iNaturalist ZIP: `application/zip`
  - JSON: `application/json`
  - CSV: `text/csv`
- **Content-Disposition**: `attachment; filename="export_<job_id>.<ext>"`
- **Body**: Binary file data

**Error Responses**:

```json
// 404 - Job not found
{
  "error": "Job not found"
}

// 400 - Job not completed
{
  "error": "Job not completed yet. Status: running"
}

// 404 - Output file not found (expired)
{
  "error": "Export file not found or expired"
}

// 403 - Path traversal attempt
{
  "error": "Invalid path"
}
```

#### Examples

```bash
# Download completed export
curl "http://localhost:5000/api/export/jobs/550e8400-e29b-41d4-a716-446655440000/download" \
  --output export.csv

# React download button
const downloadExport = async (jobId) => {
  const response = await fetch(`/api/export/jobs/${jobId}/download`);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `export_${jobId}.csv`;
  a.click();
};
```

---

### 5. Delete Export Job

Delete an export job and its output file.

**Endpoint**: `DELETE /api/export/jobs/<job_id>`

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job identifier |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "success": true,
  "message": "Job deleted successfully"
}
```

**Error Responses**:

```json
// 404 - Job not found
{
  "error": "Job not found"
}

// 400 - Cannot delete running job
{
  "error": "Cannot delete running job. Cancel it first."
}

// 500 - Delete failed
{
  "error": "Failed to delete job"
}
```

#### Examples

```bash
# Delete job
curl -X DELETE "http://localhost:5000/api/export/jobs/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

---

### 6. Cancel Export Job

Cancel a pending or running export job.

**Endpoint**: `POST /api/export/jobs/<job_id>/cancel`

**Implementation**: `webui/backend/routes/export.py`

#### Request

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job identifier |

**Headers**:
- `X-CSRFToken`: CSRF token (required)

#### Response

**Success (200)**:

```json
{
  "success": true,
  "message": "Job cancelled successfully"
}
```

**Error Responses**:

```json
// 404 - Job not found
{
  "error": "Job not found"
}

// 400 - Job already completed
{
  "error": "Cannot cancel completed job"
}

// 500 - Cancel failed
{
  "error": "Failed to cancel job"
}
```

#### Examples

```bash
# Cancel running job
curl -X POST "http://localhost:5000/api/export/jobs/550e8400-e29b-41d4-a716-446655440000/cancel" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"

# React cancel button
const cancelJob = async (jobId) => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  await fetch(`/api/export/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken.csrf_token
    }
  });
};
```

---

## Export Formats

### Supported Formats

| Format | Value | Description | Output Type |
|--------|-------|-------------|-------------|
| Darwin Core | `darwin_core` | Darwin Core Archive (DwC-A) CSV for biodiversity data portals (GBIF, iDigBio) | CSV file |
| iNaturalist | `inaturalist` | iNaturalist-compatible CSV with optional photo ZIP | ZIP or CSV |
| JSON | `json` | Generic JSON export with all metadata | JSON file |
| CSV | `csv` | Generic CSV export with flattened metadata | CSV file |

### Format-Specific Options

**Darwin Core** (`darwin_core`):
- No additional options currently supported

**iNaturalist** (`inaturalist`):
```json
{
  "include_photos": true,     // Include photos in ZIP (default: false)
  "zip_compression": 9         // ZIP compression level 0-9 (default: 6)
}
```

**JSON** (`json`):
```json
{
  "pretty_print": true         // Pretty-print JSON (default: false)
}
```

**CSV** (`csv`):
```json
{
  "delimiter": ",",            // CSV delimiter (default: ",")
  "quote_char": "\""           // CSV quote character (default: "\"")
}
```

---

## Filter Options

### ExportJobFilter Fields

All filter fields are optional. If `photo_paths` is provided, it takes precedence over all other filters.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `date_start` | string | Start date (ISO 8601: YYYY-MM-DD) | `"2024-01-01"` |
| `date_end` | string | End date (ISO 8601: YYYY-MM-DD) | `"2024-12-31"` |
| `deployment` | string | Deployment directory path | `"forest_2024"` |
| `tags` | array | List of tags (any tag matches) | `["moth", "nocturnal"]` |
| `series_type` | string | Series type filter | `"hdr"` or `"focus_bracket"` |
| `has_species` | boolean | Only photos with species ID | `true` |
| `photo_paths` | array | Explicit photo paths (overrides other filters) | `["2024-01/photo1.jpg"]` |

### Filter Examples

**Date range filter**:
```json
{
  "date_start": "2024-01-01",
  "date_end": "2024-03-31"
}
```

**Deployment filter**:
```json
{
  "deployment": "forest_2024"
}
```

**Tag filter** (any tag matches):
```json
{
  "tags": ["moth", "butterfly", "nocturnal"]
}
```

**Series type filter**:
```json
{
  "series_type": "hdr"
}
```

**Species identification filter**:
```json
{
  "has_species": true
}
```

**Combined filters** (AND logic):
```json
{
  "date_start": "2024-01-01",
  "deployment": "forest_2024",
  "tags": ["moth"],
  "has_species": true
}
```

**Explicit photo list** (ignores other filters):
```json
{
  "photo_paths": [
    "2024-01-15/photo1.jpg",
    "2024-01-15/photo2.jpg",
    "2024-02-10/photo3.jpg"
  ]
}
```

---

## Performance Characteristics

### Response Times

| Endpoint | Response Time | Notes |
|----------|--------------|-------|
| `POST /jobs` | <100ms | Job creation and queueing |
| `GET /jobs` | <50ms | List jobs from SQLite |
| `GET /jobs/<id>` | <10ms | Single job lookup |
| `GET /jobs/<id>/download` | Variable | Depends on file size |
| `DELETE /jobs/<id>` | <50ms | Includes file deletion |
| `POST /jobs/<id>/cancel` | <10ms | Sets cancellation flag |

### Export Job Execution Times

| Photos | Darwin Core CSV | iNaturalist ZIP (no photos) | iNaturalist ZIP (with photos) |
|--------|----------------|----------------------------|------------------------------|
| 100 | ~10 seconds | ~15 seconds | ~30 seconds |
| 500 | ~30 seconds | ~60 seconds | ~2 minutes |
| 1000 | ~60 seconds | ~2 minutes | ~5 minutes |

**Note**: Times vary based on:
- Photo metadata complexity
- Disk I/O speed
- Available system memory
- Concurrent system load

### Concurrency Limits

- **Single job execution**: Only 1 job runs at a time
- **Queue depth**: Unlimited (SQLite-backed)
- **Job timeout**: 10 minutes (default)
- **Job TTL**: 1 hour after completion
- **Max history**: 50 completed jobs

### Resource Usage

**Memory**:
- Job service: ~10-20 MB baseline
- Running export: +50-100 MB per 1000 photos

**Disk**:
- SQLite database: ~1 MB per 100 jobs
- Export outputs: 100 KB - 500 MB depending on format and photo count

**CPU**:
- Job creation: <1% CPU
- Export execution: 10-30% CPU (single core)

---

## Usage Examples

### Complete Workflow

```javascript
// 1. Create export job
const createExportJob = async () => {
  const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

  const response = await fetch('/api/export/jobs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.csrf_token
    },
    body: JSON.stringify({
      format: 'darwin_core',
      filter: {
        date_start: '2024-01-01',
        deployment: 'forest_2024',
        has_species: true
      }
    })
  });

  const job = await response.json();
  return job.job_id;
};

// 2. Poll for completion
const pollJobStatus = async (jobId) => {
  while (true) {
    const response = await fetch(`/api/export/jobs/${jobId}`);
    const job = await response.json();

    console.log(`Progress: ${job.progress.percent}% (${job.progress.phase})`);

    if (job.status === 'completed') {
      console.log('Export completed!');
      return job;
    } else if (job.status === 'failed') {
      console.error('Export failed:', job.error_message);
      throw new Error(job.error_message);
    } else if (job.status === 'cancelled') {
      console.log('Export cancelled');
      return null;
    }

    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
  }
};

// 3. Download result
const downloadResult = async (jobId) => {
  const response = await fetch(`/api/export/jobs/${jobId}/download`);
  const blob = await response.blob();

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `export_${jobId}.csv`;
  a.click();
};

// Execute workflow
const main = async () => {
  try {
    const jobId = await createExportJob();
    const job = await pollJobStatus(jobId);

    if (job) {
      await downloadResult(jobId);
    }
  } catch (error) {
    console.error('Export workflow failed:', error);
  }
};

main();
```

### React Hook

```jsx
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';

function useExportJob() {
  const [jobId, setJobId] = useState(null);

  // Create job mutation
  const createJob = useMutation({
    mutationFn: async ({ format, filter, options }) => {
      const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

      const response = await fetch('/api/export/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken.csrf_token
        },
        body: JSON.stringify({ format, filter, options })
      });

      if (!response.ok) {
        throw new Error('Failed to create export job');
      }

      return response.json();
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
    }
  });

  // Poll job status
  const { data: job } = useQuery({
    queryKey: ['export-job', jobId],
    queryFn: () =>
      fetch(`/api/export/jobs/${jobId}`).then(r => r.json()),
    enabled: !!jobId,
    refetchInterval: (data) =>
      data?.status === 'running' || data?.status === 'pending' ? 2000 : false
  });

  // Cancel job mutation
  const cancelJob = useMutation({
    mutationFn: async (jobId) => {
      const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

      await fetch(`/api/export/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken.csrf_token
        }
      });
    }
  });

  return {
    createJob: createJob.mutate,
    cancelJob: cancelJob.mutate,
    job,
    isCreating: createJob.isPending,
    isCancelling: cancelJob.isPending
  };
}

// Usage in component
function ExportDialog() {
  const { createJob, cancelJob, job, isCreating } = useExportJob();

  const handleExport = () => {
    createJob({
      format: 'darwin_core',
      filter: {
        date_start: '2024-01-01',
        has_species: true
      }
    });
  };

  return (
    <div>
      <button onClick={handleExport} disabled={isCreating}>
        Create Export
      </button>

      {job && (
        <div>
          <p>Status: {job.status}</p>
          <p>Progress: {job.progress.percent}%</p>
          <p>Phase: {job.progress.phase}</p>

          {job.status === 'running' && (
            <button onClick={() => cancelJob(job.job_id)}>
              Cancel
            </button>
          )}

          {job.status === 'completed' && (
            <a href={`/api/export/jobs/${job.job_id}/download`} download>
              Download Export ({(job.output_size_bytes / 1024).toFixed(1)} KB)
            </a>
          )}

          {job.status === 'failed' && (
            <p className="error">{job.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

### Python Client

```python
import time
import requests
from typing import Dict, Any

class ExportJobClient:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()

        # Get CSRF token
        response = self.session.get(f"{base_url}/api/csrf-token")
        self.csrf_token = response.json()['csrf_token']

    def create_job(
        self,
        format: str,
        filter: Dict[str, Any],
        options: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Create export job."""
        response = self.session.post(
            f"{self.base_url}/api/export/jobs",
            json={
                "format": format,
                "filter": filter,
                "options": options or {}
            },
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()
        return response.json()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        response = self.session.get(
            f"{self.base_url}/api/export/jobs/{job_id}"
        )
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, job_id: str, poll_interval: int = 2) -> Dict[str, Any]:
        """Poll job until completion."""
        while True:
            job = self.get_job(job_id)

            print(f"Progress: {job['progress']['percent']}% ({job['progress']['phase']})")

            if job['status'] in ('completed', 'failed', 'cancelled'):
                return job

            time.sleep(poll_interval)

    def download_result(self, job_id: str, output_path: str):
        """Download export result."""
        response = self.session.get(
            f"{self.base_url}/api/export/jobs/{job_id}/download",
            stream=True
        )
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def cancel_job(self, job_id: str):
        """Cancel running job."""
        response = self.session.post(
            f"{self.base_url}/api/export/jobs/{job_id}/cancel",
            headers={"X-CSRFToken": self.csrf_token}
        )
        response.raise_for_status()

# Usage
client = ExportJobClient()

# Create job
job = client.create_job(
    format="darwin_core",
    filter={
        "date_start": "2024-01-01",
        "deployment": "forest_2024",
        "has_species": True
    }
)

print(f"Created job: {job['job_id']}")

# Wait for completion
completed_job = client.wait_for_completion(job['job_id'])

if completed_job['status'] == 'completed':
    # Download result
    client.download_result(job['job_id'], 'export.csv')
    print(f"Downloaded export: {completed_job['photo_count']} photos")
else:
    print(f"Export failed: {completed_job['error_message']}")
```

---

## Related Documentation

- **Export Metadata Service**: `webui/backend/services/export_metadata_service.py` - Underlying export logic
- **Job Types**: `webui/backend/lib/export_job_types.py` - Type definitions
- **Job Database**: `webui/backend/lib/export_job_db.py` - SQLite persistence
- **Testing**: `Tests/unit/test_export_job_*.py` - Unit tests
- **Integration Tests**: `Tests/integration/test_export_job_workflow.py` - E2E tests

---

**Document Version**: 1.0.0
**Last Validated**: 2025-12-13
**Issue**: #122 - Export Job Queue System
