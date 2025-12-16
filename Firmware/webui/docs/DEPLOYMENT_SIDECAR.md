# Deployment Metadata Sidecar - User Guide

## Overview

The Deployment Metadata Sidecar system provides directory-level metadata for Mothbox photo collections. Unlike photo-level metadata (species tagging, notes), deployment metadata describes the entire collection: where it was deployed, when, environmental conditions, and custom project information.

## Features

- **Hierarchical Discovery**: Walk up directory tree to find nearest deployment metadata
- **Dual Format Support**: JSON (default) or YAML
- **Thread-Safe Operations**: File locking for atomic read-modify-write
- **Flexible Schema**: Required fields + extensible custom metadata
- **LRU Cache**: Fast access with configurable TTL
- **Batch Operations**: Bulk updates and template-based generation
- **Export Integration**: Deployment metadata included in photo exports

## Use Cases

### Scientific Surveys
Document multi-day moth surveys with precise location and time periods:
```json
{
  "deployment_name": "Oak Ridge Moth Survey - Summer 2024",
  "location_name": "Oak Ridge National Laboratory, TN",
  "latitude": 35.9606,
  "longitude": -83.9207,
  "altitude": 350.5,
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "environmental": {
    "habitat": "deciduous forest",
    "canopy_cover": "60-80%",
    "temperature_range": "18-28°C"
  },
  "custom": {
    "project_code": "ORNL-2024-001",
    "permit_number": "NPS-2024-SCI-1234",
    "principal_investigator": "Dr. Jane Smith"
  }
}
```

### Multi-Location Monitoring
Organize photos by deployment location:
```
/photos/
  site_a/
    deployment.json  # Site A metadata
    2024-06-01/
    2024-06-02/
  site_b/
    deployment.json  # Site B metadata
    2024-06-01/
    2024-06-02/
```

### Long-Term Monitoring
Track seasonal changes over years:
```json
{
  "deployment_name": "Backyard Moths - Spring Migration 2024",
  "start_date": "2024-03-15",
  "end_date": "2024-05-31",
  "environmental": {
    "season": "spring",
    "moon_phase": "new moon to full moon",
    "weather_notes": "mild, minimal precipitation"
  },
  "custom": {
    "year": 2024,
    "migration_study": true,
    "comparison_years": [2022, 2023]
  }
}
```

## Prerequisites

### Software Requirements
- Python 3.7+ with dependencies:
  - `mothbox_paths` (path resolution)
  - `PyYAML` (optional, for YAML format)

### Installation
Deployment sidecar support is built into the Mothbox web UI. No additional installation required.

## Creating Deployment Metadata

### Via Web UI (Coming Soon)
Future versions will include a web interface for managing deployment metadata.

### Via Python API

#### Create New Deployment
```python
from webui.backend.lib.deployment_sidecar import create_deployment_metadata, write_deployment_metadata
from pathlib import Path

# Create metadata
metadata = create_deployment_metadata(
    directory="/var/lib/mothbox/photos/forest_2024",
    name="Oak Ridge Forest Survey 2024",
    latitude=35.9606,
    longitude=-83.9207,
    altitude=350.5,
    location_name="Oak Ridge, TN, USA",
    start_date="2024-06-01",
    end_date="2024-08-31",
    environmental={
        "habitat": "deciduous forest",
        "temperature_range": "18-28°C"
    },
    mothbox_id="mothbox-001",
    firmware_version="5.2.1",
    custom={
        "project_code": "ORNL-2024-001"
    },
    modified_by="user123"
)

# Write to disk (JSON format)
success = write_deployment_metadata(
    "/var/lib/mothbox/photos/forest_2024",
    metadata,
    format="json",
    backup=True
)

if success:
    print("Deployment metadata created!")
```

#### Create YAML Format
```python
# Write as YAML instead of JSON
success = write_deployment_metadata(
    "/var/lib/mothbox/photos/forest_2024",
    metadata,
    format="yaml",
    backup=True
)
```

### Via REST API

#### Create Deployment (PUT)
```bash
curl -X PUT "http://localhost:5000/api/deployment/metadata/forest_2024?format=json" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "deployment_name": "Forest Survey 2024",
    "latitude": 35.9606,
    "longitude": -83.9207,
    "location_name": "Oak Ridge, TN, USA",
    "start_date": "2024-06-01",
    "end_date": "2024-08-31"
  }'
```

## Reading Deployment Metadata

### Via Python API

#### Read Deployment
```python
from webui.backend.lib.deployment_sidecar import read_deployment_metadata

metadata = read_deployment_metadata("/var/lib/mothbox/photos/forest_2024")

if metadata:
    print(f"Deployment: {metadata.deployment_name}")
    print(f"Location: {metadata.latitude}, {metadata.longitude}")
    print(f"Period: {metadata.start_date} to {metadata.end_date}")
```

#### Find Deployment for Photo (Hierarchical)
```python
from webui.backend.lib.deployment_sidecar import find_deployment_sidecar, read_deployment_metadata

# Photo in nested subdirectory
photo_path = "/var/lib/mothbox/photos/forest_2024/subfolder/photo.jpg"

# Find nearest deployment.json by walking up tree
sidecar_path = find_deployment_sidecar(photo_path)

if sidecar_path:
    metadata = read_deployment_metadata(sidecar_path.parent)
    print(f"Photo belongs to: {metadata.deployment_name}")
else:
    print("No deployment metadata found")
```

### Via REST API

#### Get Deployment
```bash
curl "http://localhost:5000/api/deployment/metadata/forest_2024"
```

#### Discover Deployment for Photo
```bash
curl "http://localhost:5000/api/deployment/discover/forest_2024/subfolder/photo.jpg"
```

#### List All Deployments
```bash
curl "http://localhost:5000/api/deployment/list"
```

## Updating Deployment Metadata

### Via Python API

#### Partial Update (Recommended)
```python
from webui.backend.lib.deployment_sidecar import update_deployment_metadata

# Update only specific fields
metadata = update_deployment_metadata(
    "/var/lib/mothbox/photos/forest_2024",
    {
        "end_date": "2024-09-15",
        "modified_by": "user123"
    }
)

print(f"Updated: {metadata.deployment_name}")
```

#### Full Replacement
```python
from webui.backend.lib.deployment_sidecar import create_deployment_metadata, write_deployment_metadata

# Create new metadata
new_metadata = create_deployment_metadata(
    directory="/var/lib/mothbox/photos/forest_2024",
    name="Updated Survey Name",
    # ... all other fields
)

# Replace existing metadata
write_deployment_metadata(
    "/var/lib/mothbox/photos/forest_2024",
    new_metadata,
    format="json",
    backup=True  # Creates .bak file before overwriting
)
```

### Via REST API

#### Partial Update (PATCH)
```bash
curl -X PATCH "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "end_date": "2024-09-15",
    "environmental": {
      "habitat": "mixed forest"
    }
  }'
```

#### Full Replacement (PUT)
```bash
curl -X PUT "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "deployment_name": "Updated Survey Name",
    "latitude": 35.9606,
    "longitude": -83.9207
  }'
```

## Deleting Deployment Metadata

### Via Python API

```python
from webui.backend.lib.deployment_sidecar import delete_deployment_metadata

# Delete with backup
success = delete_deployment_metadata(
    "/var/lib/mothbox/photos/forest_2024",
    backup=True  # Creates .bak file before deleting
)

if success:
    print("Deployment metadata deleted")
```

### Via REST API

```bash
curl -X DELETE "http://localhost:5000/api/deployment/metadata/forest_2024" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

**Note**: Backup files (`.bak`) are created automatically before deletion.

## Batch Operations

### Batch Update Multiple Deployments

```bash
curl -X POST "http://localhost:5000/api/deployment/batch" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "updates": [
      {
        "directory": "forest_2024",
        "data": {"end_date": "2024-09-15"}
      },
      {
        "directory": "meadow_2024",
        "data": {"end_date": "2024-09-20"}
      }
    ]
  }'
```

**Response**:
```json
{
  "success": ["forest_2024", "meadow_2024"],
  "failed": [],
  "errors": {},
  "total": 2,
  "successful": 2,
  "failed_count": 0
}
```

### Generate Sidecars from Template

Create deployment metadata for all subdirectories using a template:

```bash
curl -X POST "http://localhost:5000/api/deployment/generate" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "directory": "surveys_2024",
    "template": {
      "deployment_name": "Auto-generated",
      "location_name": "Oak Ridge",
      "latitude": 35.9606,
      "longitude": -83.9207
    }
  }'
```

**Behavior**:
- Scans all subdirectories under `surveys_2024/`
- Creates `deployment.json` for each subdirectory that doesn't already have one
- Uses subdirectory name as `deployment_name` if not in template

## File Formats

### JSON Format (Default)

**File**: `deployment.json`

```json
{
  "version": "1.0",
  "deployment_name": "Forest Survey 2024",
  "created_at": "2024-06-01T12:00:00Z",
  "modified_at": "2024-08-31T15:30:00Z",
  "latitude": 35.9606,
  "longitude": -83.9207,
  "altitude": 350.5,
  "location_name": "Oak Ridge, TN, USA",
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "environmental": {
    "habitat": "deciduous forest"
  },
  "mothbox_id": "mothbox-001",
  "firmware_version": "5.2.1",
  "custom": {
    "project_code": "ORNL-2024-001"
  },
  "modified_by": "user123"
}
```

### YAML Format (Optional)

**File**: `deployment.yaml`

```yaml
version: '1.0'
deployment_name: Forest Survey 2024
created_at: '2024-06-01T12:00:00Z'
modified_at: '2024-08-31T15:30:00Z'
latitude: 35.9606
longitude: -83.9207
altitude: 350.5
location_name: Oak Ridge, TN, USA
start_date: '2024-06-01'
end_date: '2024-08-31'
environmental:
  habitat: deciduous forest
mothbox_id: mothbox-001
firmware_version: '5.2.1'
custom:
  project_code: ORNL-2024-001
modified_by: user123
```

**Note**: YAML support requires `PyYAML` library. JSON is always supported.

### Format Priority

When both `deployment.json` and `deployment.yaml` exist in the same directory:
1. **JSON has priority** - `deployment.json` is read first
2. YAML is only used if JSON doesn't exist

## Integration with Export System

**Note (Issue #200)**: Deployment metadata is **optional** for exports. The export system falls back to GPS coordinates from photo EXIF headers if no deployment metadata is available.

Deployment metadata is automatically included when exporting photos (if available):

```python
from webui.backend.services.export_metadata_service import ExportMetadataService

service = ExportMetadataService()

# Export includes deployment metadata if available
metadata = service.export_photo_metadata("/photos/forest_2024/photo.jpg")

print(metadata['deployment'])
# {
#   'deployment_name': 'Forest Survey 2024',
#   'location_name': 'Oak Ridge, TN, USA',
#   'latitude': 35.9606,
#   'longitude': -83.9207,
#   ...
# }
```

**Export Formats**:
- **JSON**: Full deployment metadata object
- **CSV**: Selected deployment fields (name, location, coordinates)
- **Darwin Core**: Deployment location and dates mapped to DwC terms

## Validation and Constraints

### Required Fields
- `deployment_name`: Non-empty string, max 200 characters
- `version`: Schema version (always "1.0")
- `created_at`: ISO 8601 timestamp with 'Z' suffix
- `modified_at`: ISO 8601 timestamp with 'Z' suffix

### Optional Fields
- `latitude`: Decimal degrees, -90.0 to 90.0
- `longitude`: Decimal degrees, -180.0 to 180.0
- `altitude`: Meters (any numeric value)
- `location_name`: Max 500 characters
- `start_date`: ISO 8601 date (YYYY-MM-DD)
- `end_date`: ISO 8601 date (YYYY-MM-DD)
- `environmental`: Arbitrary JSON object
- `mothbox_id`: No length limit
- `firmware_version`: No length limit
- `custom`: Max 100 keys, max depth 5, JSON-serializable values only
- `modified_by`: No length limit

### Custom Fields Validation
```python
# Valid custom fields
custom = {
    "string_field": "value",
    "number_field": 42,
    "boolean_field": True,
    "null_field": None,
    "list_field": [1, 2, 3],
    "nested_object": {
        "key": "value"
    }
}

# Invalid custom fields
custom = {
    "too_deep": {
        "level1": {"level2": {"level3": {"level4": {"level5": {"level6": "error"}}}}}
    },  # Exceeds max depth (5)
    "invalid_type": object(),  # Not JSON-serializable
}
```

## Troubleshooting

### Deployment Not Found

**Symptom**: API returns 404 "Deployment not found"

**Solutions**:
1. Check if `deployment.json` or `deployment.yaml` exists in directory:
   ```bash
   ls /var/lib/mothbox/photos/forest_2024/
   ```
2. Verify file has valid JSON/YAML:
   ```bash
   python3 -m json.tool /var/lib/mothbox/photos/forest_2024/deployment.json
   ```
3. Check file permissions:
   ```bash
   ls -la /var/lib/mothbox/photos/forest_2024/deployment.json
   ```

### Validation Errors

**Symptom**: API returns 400 with validation error

**Common Causes**:
1. **Invalid coordinates**: `latitude must be between -90.0 and 90.0`
   - Check latitude/longitude ranges
2. **Invalid date format**: `start_date must be in ISO 8601 format (YYYY-MM-DD)`
   - Use YYYY-MM-DD format, not other date formats
3. **Too many custom fields**: `Too many custom fields (max 100)`
   - Reduce number of custom fields or use nested objects
4. **Nested too deep**: `Custom field nesting exceeds maximum depth (5)`
   - Flatten nested objects

### Permission Errors

**Symptom**: "Permission denied" when writing deployment metadata

**Solutions**:
1. Check directory permissions:
   ```bash
   ls -ld /var/lib/mothbox/photos/forest_2024
   ```
2. Ensure web UI user has write access:
   ```bash
   sudo chown -R pi:pi /var/lib/mothbox/photos
   sudo chmod -R u+w /var/lib/mothbox/photos
   ```

### Format Errors

**Symptom**: "YAML support not available - install PyYAML"

**Solution**:
```bash
pip3 install PyYAML
```

Or use JSON format instead (always available):
```bash
curl -X PUT "http://localhost:5000/api/deployment/metadata/forest_2024?format=json" ...
```

## Best Practices

### For Scientific Surveys
1. **Be precise**: Include exact coordinates, dates, and environmental conditions
2. **Use custom fields**: Add project-specific metadata (permit numbers, PIs, etc.)
3. **Document methods**: Store survey methodology in custom fields
4. **Version control**: Keep backup files (use `backup=True`)

### For Multi-Location Monitoring
1. **Organize by site**: Create one deployment per physical location
2. **Use consistent naming**: Follow a naming convention for deployment names
3. **Document hardware**: Store Mothbox ID and firmware version
4. **Track changes**: Use `modified_by` field to track who made updates

### For Data Integrity
1. **Validate before writing**: Test with dry runs first
2. **Use backups**: Always use `backup=True` for important data
3. **Verify after creation**: Read back metadata to confirm
4. **Keep templates**: Save common deployment templates for reuse

### For Performance
1. **Cache-friendly**: Service caches metadata for fast access (5-minute TTL)
2. **Batch updates**: Use batch endpoint for multiple updates
3. **Hierarchical discovery**: Place deployment.json at appropriate directory level

## Performance Optimization

### Cache Performance
- **Cache hit**: <10ms
- **Disk read**: <50ms
- **Cache TTL**: 300 seconds (5 minutes)
- **Target hit ratio**: >80%

### Monitoring Cache
```bash
# Get cache statistics
curl "http://localhost:5000/api/deployment/stats"

# Response:
# {
#   "cache_hits": 450,
#   "cache_misses": 50,
#   "hit_ratio": 0.90,
#   ...
# }
```

### Invalidating Cache
```bash
# Invalidate entire cache
curl -X POST "http://localhost:5000/api/deployment/cache/invalidate" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"

# Invalidate specific directory
curl -X POST "http://localhost:5000/api/deployment/cache/invalidate?directory=forest_2024" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

## Advanced Usage

### Programmatic Batch Processing
```python
from webui.backend.services.deployment_service import DeploymentService
from pathlib import Path

service = DeploymentService(cache_ttl=300, max_cache_size=100)

# Batch update multiple deployments
updates = [
    (Path("/photos/forest_2024"), {"end_date": "2024-09-15"}),
    (Path("/photos/meadow_2024"), {"end_date": "2024-09-20"}),
]

results = service.batch_update_deployments(updates)

print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed_count']}")
```

### Template-Based Generation
```python
template = {
    "location_name": "Oak Ridge",
    "latitude": 35.9606,
    "longitude": -83.9207,
    "mothbox_id": "mothbox-001",
}

# Generate deployment.json for all subdirectories
count = service.generate_sidecars_for_directory(
    "/var/lib/mothbox/photos/surveys_2024",
    template
)

print(f"Generated {count} deployment sidecars")
```

## Frequently Asked Questions

**Q: Can I have multiple deployment.json files in nested directories?**
A: Yes. Hierarchical discovery finds the *nearest* deployment.json by walking up the directory tree. Subdirectories can have their own deployment metadata.

**Q: What happens if I have both deployment.json and deployment.yaml?**
A: JSON has priority. If `deployment.json` exists, `deployment.yaml` is ignored.

**Q: Is deployment metadata included in photo exports?**
A: Yes. The export system automatically includes deployment metadata when exporting photos.

**Q: Can I store arbitrary data in custom fields?**
A: Yes, as long as it's JSON-serializable (strings, numbers, booleans, null, lists, objects). Max 50 keys, max depth 5.

**Q: Are deployment metadata files backed up?**
A: Yes, when using `backup=True` (default for Python API). REST API always creates .bak files before delete.

**Q: How is deployment metadata different from photo sidecar metadata?**
A: Deployment metadata is *directory-level* (describes entire collection), while photo sidecars are *file-level* (describe individual photos).

**Q: Can I use deployment metadata without the web UI?**
A: Yes. The library (`webui/backend/lib/deployment_sidecar.py`) can be used standalone via Python API.

## Support and Documentation

- **API Documentation**: See `webui/docs/dev/api/deployment.md`
- **Library Documentation**: See `webui/backend/lib/deployment_sidecar.py` docstrings
- **Schema Reference**: See `webui/backend/lib/deployment_schema.py`
- **Testing**: See `Tests/unit/test_deployment_*.py`
- **Issue Tracker**: Report bugs on GitHub issue tracker

## Version History

- **v1.0** (December 2024): Initial release (Issue #114)
  - Core CRUD operations
  - JSON and YAML format support
  - Thread-safe file locking
  - LRU cache with TTL
  - Batch operations
  - REST API endpoints
  - Comprehensive test suite (95%+ coverage)
