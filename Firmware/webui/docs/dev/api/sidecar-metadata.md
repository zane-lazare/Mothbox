# Sidecar Metadata API Documentation

**Last Updated**: 2025-12-01
**Version**: 1.0.0 (Issue #102 Phase E)
**Schema Version**: 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [JSON Schema Reference](#json-schema-reference)
3. [Library API Reference](#library-api-reference)
4. [Service API Reference](#service-api-reference)
5. [Usage Examples](#usage-examples)
6. [Error Handling](#error-handling)
7. [Design Decisions](#design-decisions)
8. [Performance Characteristics](#performance-characteristics)
9. [Related Documentation](#related-documentation)

---

## Overview

The sidecar metadata system stores photo-level metadata (tags, species identification, notes, custom fields) in JSON sidecar files alongside photos. This approach provides structured metadata without modifying original photo files.

### What is the Sidecar Metadata System?

A **sidecar file** is a separate JSON file that stores metadata for a photo:
- Photo: `moth_2024_11_06__10_30_00.jpg`
- Sidecar: `moth_2024_11_06__10_30_00.jpg.json`

The sidecar contains structured metadata like tags, species identification, notes, and custom key-value pairs.

### Why JSON Sidecars?

**Advantages over alternatives**:

1. **vs. Embedded EXIF**:
   - No risk of corrupting original photo files
   - Unlimited metadata size and structure
   - Easy to read/edit with any JSON tool
   - Supports complex nested data structures

2. **vs. Database**:
   - Works offline without database server
   - Easy to backup with photo files
   - No database migration headaches
   - Portable across systems

3. **vs. Spreadsheet/CSV**:
   - One sidecar per photo (no centralized bottleneck)
   - Concurrent access with file locking
   - Structured data with validation
   - Easy to delete metadata by deleting file

### File Naming Convention

Sidecar files follow a strict naming convention:

```
{photo_filename}.json
```

**Examples**:
- Photo: `moth.jpg` → Sidecar: `moth.jpg.json`
- Photo: `photo_2024_11_06__10_30_00_HDR0.jpg` → Sidecar: `photo_2024_11_06__10_30_00_HDR0.jpg.json`
- Photo: `ManFocus_moth_2024_11_06__10_30_00_FB2.jpg` → Sidecar: `ManFocus_moth_2024_11_06__10_30_00_FB2.jpg.json`

### Key Features

- **Schema Validation**: Enforced schema with version tracking
- **Tag Normalization**: Automatic lowercase normalization for consistency
- **File Locking**: Prevents concurrent write conflicts
- **Atomic Writes**: Temp file + rename for crash safety
- **Automatic Backups**: Optional `.bak` file creation
- **Two-Level Cache**: Fast access with L1 (memory) + L2 (file) cache
- **Batch Operations**: Efficient processing of multiple photos

### Implementation Files

- **Library**: `webui/backend/lib/sidecar_metadata.py` - Core CRUD operations (713 lines)
- **Service**: `webui/backend/services/sidecar_service.py` - Cached service layer (588 lines)
- **Tests**: `Tests/unit/test_sidecar_metadata_lib.py` (99+ tests, 99% coverage)
- **Tests**: `Tests/unit/test_sidecar_service.py` (60+ tests, 97% coverage)

---

## JSON Schema Reference

### Schema Structure

```json
{
  "version": "1.0",
  "photo_filename": "moth_2024_11_06__10_30_00.jpg",
  "created_at": "2024-11-06T10:30:00Z",
  "modified_at": "2024-11-06T11:45:00Z",
  "modified_by": null,
  "tags": ["moth", "night", "luna_moth"],
  "species": "Actias luna",
  "notes": "Large specimen found near pond. Perfect wing condition.",
  "custom": {
    "weather": "clear",
    "temperature": "18C",
    "moon_phase": "full"
  }
}
```

### Field Reference

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `version` | string | Yes | Schema version | Currently "1.0" |
| `photo_filename` | string | Yes | Original photo filename | Must match sidecar name |
| `created_at` | string | Yes | Creation timestamp | ISO 8601 format (UTC) |
| `modified_at` | string | Yes | Last modification timestamp | ISO 8601 format (UTC) |
| `modified_by` | string \| null | No | User identifier for last modification | Optional, default: null |
| `tags` | array[string] | Yes | List of tags | Normalized to lowercase, max 50 chars each |
| `species` | string \| null | No | Species identification | Optional, max 200 chars |
| `notes` | string \| null | No | User notes | Optional, max 10000 chars |
| `custom` | object | Yes | Custom key-value metadata | Max 100 keys, default: {} |

### Field Details

#### `version`
- **Type**: String
- **Current**: "1.0"
- **Purpose**: Track schema changes for backward compatibility
- **Validation**: Must match `SCHEMA_VERSION` constant

#### `photo_filename`
- **Type**: String
- **Example**: `"moth_2024_11_06__10_30_00.jpg"`
- **Purpose**: Reference to photo file
- **Validation**: Should match photo file in same directory

#### `created_at` / `modified_at`
- **Type**: ISO 8601 timestamp string
- **Format**: `YYYY-MM-DDTHH:MM:SSZ` (always UTC, 'Z' suffix)
- **Example**: `"2024-11-06T10:30:00Z"`
- **Auto-managed**: Set automatically by library functions

#### `modified_by`
- **Type**: String or null
- **Example**: `"admin"`, `"user123"`, `null`
- **Purpose**: Track who made last change (for future multi-user support)
- **Default**: `null`

#### `tags`
- **Type**: Array of strings
- **Normalization**: Automatically converted to lowercase
- **Max Length**: 50 characters per tag
- **Example**: `["moth", "night", "luna_moth"]`
- **Use Cases**: Searching, filtering, categorization

#### `species`
- **Type**: String or null
- **Max Length**: 200 characters
- **Example**: `"Actias luna"`, `"Unknown moth species"`
- **Use Cases**: Species identification, scientific records

#### `notes`
- **Type**: String or null
- **Max Length**: 10000 characters
- **Example**: `"Large specimen found near pond. Perfect wing condition."`
- **Use Cases**: Observations, detailed descriptions

#### `custom`
- **Type**: Object (dictionary)
- **Max Keys**: 100
- **Example**: `{"weather": "clear", "temperature": "18C"}`
- **Use Cases**: Extensibility for domain-specific metadata

### Validation Rules

**Schema validation enforces**:
1. All required fields present
2. Correct data types
3. String length limits
4. Array/object size limits
5. Version compatibility

**Validation exceptions**:
- `ValidationError`: Raised when validation fails
- Contains descriptive error message

---

## Library API Reference

The library (`webui/backend/lib/sidecar_metadata.py`) provides low-level CRUD operations.

### Path Utilities

#### `get_sidecar_path(photo_path)`

Get sidecar JSON file path for a photo.

**Signature**:
```python
def get_sidecar_path(photo_path: Path | str) -> Path
```

**Parameters**:
- `photo_path`: Path to photo file (Path or string)

**Returns**:
- Path to sidecar JSON file (`{photo}.json`)

**Example**:
```python
from webui.backend.lib.sidecar_metadata import get_sidecar_path

sidecar_path = get_sidecar_path("/photos/moth.jpg")
# Returns: PosixPath('/photos/moth.jpg.json')
```

---

#### `photo_has_sidecar(photo_path)`

Check if photo has associated sidecar metadata.

**Signature**:
```python
def photo_has_sidecar(photo_path: Path | str) -> bool
```

**Parameters**:
- `photo_path`: Path to photo file

**Returns**:
- `True` if sidecar exists, `False` otherwise

**Example**:
```python
from webui.backend.lib.sidecar_metadata import photo_has_sidecar

has_metadata = photo_has_sidecar("/photos/moth.jpg")
# Returns: True or False
```

---

#### `list_photos_with_sidecars(directory)`

List all photos in directory that have sidecar metadata.

**Signature**:
```python
def list_photos_with_sidecars(directory: Path) -> list[Path]
```

**Parameters**:
- `directory`: Directory to search

**Returns**:
- List of Path objects for photos with sidecars (sorted alphabetically)

**Example**:
```python
from pathlib import Path
from webui.backend.lib.sidecar_metadata import list_photos_with_sidecars

photos = list_photos_with_sidecars(Path("/photos"))
# Returns: [Path('/photos/moth1.jpg'), Path('/photos/moth2.jpg')]

print(f"Found {len(photos)} photos with metadata")
```

**Performance**: O(n) where n = number of files in directory

---

### Schema Validation

#### `validate_schema(data)`

Validate metadata dictionary against schema.

**Signature**:
```python
def validate_schema(data: dict) -> bool
```

**Parameters**:
- `data`: Metadata dictionary to validate

**Returns**:
- `True` if valid

**Raises**:
- `ValidationError`: If validation fails (with descriptive message)

**Example**:
```python
from webui.backend.lib.sidecar_metadata import validate_schema, ValidationError

metadata_dict = {
    "version": "1.0",
    "photo_filename": "moth.jpg",
    "created_at": "2024-11-06T10:30:00Z",
    "modified_at": "2024-11-06T10:30:00Z",
    "tags": ["moth", "night"],
    "species": "Actias luna",
    "notes": "Large specimen",
    "custom": {},
    "modified_by": None
}

try:
    validate_schema(metadata_dict)
    print("Valid!")
except ValidationError as e:
    print(f"Invalid: {e}")
```

**Validation Checks**:
- Required fields present
- Schema version supported
- Field types correct
- String length limits
- Array/object size limits

---

### Tag Normalization

#### `normalize_tag(tag)`

Normalize tag to lowercase and strip whitespace.

**Signature**:
```python
def normalize_tag(tag: str) -> str
```

**Parameters**:
- `tag`: Tag string to normalize

**Returns**:
- Normalized tag (lowercase, stripped)

**Example**:
```python
from webui.backend.lib.sidecar_metadata import normalize_tag

tag1 = normalize_tag("  MOTH  ")
# Returns: "moth"

tag2 = normalize_tag("Luna_Moth")
# Returns: "luna_moth"

tag3 = normalize_tag("Night Photography")
# Returns: "night photography"
```

**Use Cases**:
- Prevent duplicate tags with different case
- Consistent tag searching
- User input normalization

---

### CRUD Operations

#### `read_metadata(photo_path)`

Read metadata from photo's sidecar file.

**Signature**:
```python
def read_metadata(photo_path: Path | str) -> SidecarMetadata | None
```

**Parameters**:
- `photo_path`: Path to photo file

**Returns**:
- `SidecarMetadata` object if valid sidecar exists
- `None` if sidecar doesn't exist, is corrupted, or has unsupported schema

**Example**:
```python
from webui.backend.lib.sidecar_metadata import read_metadata

metadata = read_metadata("/photos/moth.jpg")

if metadata:
    print(f"Tags: {metadata.tags}")
    print(f"Species: {metadata.species}")
    print(f"Notes: {metadata.notes}")
else:
    print("No metadata found")
```

**Graceful Degradation**:
- Missing file → `None`
- Corrupted JSON → `None`
- Invalid schema → `None`
- Unsupported version → `None`
- File permission error → `None`

**Performance**: <10ms with file locking

---

#### `write_metadata(photo_path, metadata, backup=True)`

Write metadata to photo's sidecar file.

**Signature**:
```python
def write_metadata(
    photo_path: Path | str,
    metadata: SidecarMetadata,
    backup: bool = True
) -> bool
```

**Parameters**:
- `photo_path`: Path to photo file
- `metadata`: SidecarMetadata object to write
- `backup`: If True, create `.bak` backup before overwriting (default: True)

**Returns**:
- `True` if successful
- `False` if write failed

**Example**:
```python
from webui.backend.lib.sidecar_metadata import create_metadata, write_metadata

metadata = create_metadata(
    "/photos/moth.jpg",
    tags=["moth", "night"],
    species="Actias luna"
)

success = write_metadata("/photos/moth.jpg", metadata, backup=True)
if success:
    print("Metadata saved!")
```

**Safety Features**:
- **Atomic write**: Uses temp file + rename (crash-safe)
- **Optional backup**: Creates `.bak` file before overwriting
- **File locking**: Prevents concurrent write conflicts
- **Auto-cleanup**: Removes temp file if write fails

**Performance**: <20ms with atomic write

---

#### `create_metadata(photo_path, tags=None, species=None, notes=None, custom=None, modified_by=None)`

Create new metadata object for photo.

**Signature**:
```python
def create_metadata(
    photo_path: Path | str,
    tags: list[str] | None = None,
    species: str | None = None,
    notes: str | None = None,
    custom: dict | None = None,
    modified_by: str | None = None
) -> SidecarMetadata
```

**Parameters**:
- `photo_path`: Path to photo file
- `tags`: List of tags (will be normalized to lowercase)
- `species`: Species identification
- `notes`: User notes
- `custom`: Custom metadata dictionary
- `modified_by`: User identifier

**Returns**:
- New `SidecarMetadata` object (not yet written to disk)

**Example**:
```python
from webui.backend.lib.sidecar_metadata import create_metadata

metadata = create_metadata(
    "/photos/moth.jpg",
    tags=["moth", "Night", "LUNA_MOTH"],  # Will be normalized
    species="Actias luna",
    notes="Large specimen found near pond",
    custom={"weather": "clear", "temperature": "18C"},
    modified_by="admin"
)

# Tags are normalized
print(metadata.tags)
# Output: ['moth', 'night', 'luna_moth']
```

**Auto-Generated Fields**:
- `version`: Set to current schema version
- `created_at`: Current UTC timestamp
- `modified_at`: Same as created_at
- `photo_filename`: Extracted from photo_path

**Performance**: <1ms (in-memory object creation)

---

#### `update_metadata(photo_path, updates)`

Update existing metadata or create new if doesn't exist.

**Signature**:
```python
def update_metadata(
    photo_path: Path | str,
    updates: dict
) -> SidecarMetadata
```

**Parameters**:
- `photo_path`: Path to photo file
- `updates`: Dictionary of fields to update

**Returns**:
- Updated `SidecarMetadata` object (already written to disk)

**Example**:
```python
from webui.backend.lib.sidecar_metadata import update_metadata

# Update species and add notes
metadata = update_metadata(
    "/photos/moth.jpg",
    {
        "species": "Actias luna",
        "notes": "Confirmed identification"
    }
)

print(f"Updated: {metadata.species}")
# Output: Updated: Actias luna
```

**Partial Update Behavior**:
- Only specified fields are modified
- Other fields remain unchanged
- `modified_at` automatically updated
- Creates new metadata if none exists

**Tag Update Example**:
```python
# Replace all tags
metadata = update_metadata(
    "/photos/moth.jpg",
    {"tags": ["moth", "verified", "luna"]}
)
```

**Auto-Written**: Changes are immediately written to disk (no need to call `write_metadata`)

**Performance**: <20ms (read + modify + write)

---

#### `delete_metadata(photo_path, backup=True)`

Delete photo's sidecar metadata.

**Signature**:
```python
def delete_metadata(
    photo_path: Path | str,
    backup: bool = True
) -> bool
```

**Parameters**:
- `photo_path`: Path to photo file
- `backup`: If True, create `.bak` backup before deleting (default: True)

**Returns**:
- `True` if sidecar was deleted
- `False` if sidecar didn't exist

**Example**:
```python
from webui.backend.lib.sidecar_metadata import delete_metadata

# Delete with backup
deleted = delete_metadata("/photos/moth.jpg", backup=True)

if deleted:
    print("Metadata deleted (backup created)")
else:
    print("No metadata to delete")
```

**Backup Location**: `{photo}.json.bak` in same directory

**Safety**: Backup allows recovery from accidental deletion

**Performance**: <10ms

---

### Tag Operations

#### `add_tag(photo_path, tag)`

Add tag to photo metadata.

**Signature**:
```python
def add_tag(photo_path: Path | str, tag: str) -> SidecarMetadata
```

**Parameters**:
- `photo_path`: Path to photo file
- `tag`: Tag to add (will be normalized)

**Returns**:
- Updated `SidecarMetadata` object

**Example**:
```python
from webui.backend.lib.sidecar_metadata import add_tag

# Add tag (normalized to lowercase)
metadata = add_tag("/photos/moth.jpg", "Luna_Moth")

print(metadata.tags)
# Output: ['moth', 'night', 'luna_moth']
```

**Behavior**:
- Creates sidecar if doesn't exist
- Normalizes tag to lowercase
- Prevents duplicate tags
- Updates `modified_at` timestamp
- Auto-writes to disk

**Idempotent**: Adding same tag multiple times is safe (no duplicates)

**Performance**: <20ms

---

#### `remove_tag(photo_path, tag)`

Remove tag from photo metadata.

**Signature**:
```python
def remove_tag(photo_path: Path | str, tag: str) -> SidecarMetadata
```

**Parameters**:
- `photo_path`: Path to photo file
- `tag`: Tag to remove (will be normalized)

**Returns**:
- Updated `SidecarMetadata` object

**Example**:
```python
from webui.backend.lib.sidecar_metadata import remove_tag

# Remove tag (case-insensitive)
metadata = remove_tag("/photos/moth.jpg", "NIGHT")

print(metadata.tags)
# Output: ['moth', 'luna_moth']
```

**Behavior**:
- Normalizes tag before removal
- Returns unchanged metadata if tag not found
- Creates empty metadata if sidecar doesn't exist
- Updates `modified_at` timestamp
- Auto-writes to disk

**Idempotent**: Removing non-existent tag is safe (no error)

**Performance**: <20ms

---

### Data Classes

#### `SidecarMetadata`

Dataclass representing photo metadata structure.

**Attributes**:
- `version` (str): Schema version
- `photo_filename` (str): Photo filename
- `created_at` (str): ISO 8601 creation timestamp
- `modified_at` (str): ISO 8601 modification timestamp
- `tags` (list[str]): Normalized tags
- `species` (str | None): Species identification
- `notes` (str | None): User notes
- `custom` (dict): Custom metadata
- `modified_by` (str | None): User identifier

**Methods**:
- `to_dict() -> dict`: Convert to dictionary for JSON serialization
- `from_dict(data: dict) -> SidecarMetadata`: Create from dictionary

**Example**:
```python
from webui.backend.lib.sidecar_metadata import SidecarMetadata

# Access fields
print(metadata.tags)
print(metadata.species)

# Convert to dict
data = metadata.to_dict()

# Create from dict
metadata2 = SidecarMetadata.from_dict(data)
```

---

### Exceptions

#### `ValidationError`

Raised when metadata validation fails.

**Base Class**: `Exception`

**Example**:
```python
from webui.backend.lib.sidecar_metadata import ValidationError

try:
    validate_schema({"version": "2.0"})  # Unsupported version
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Output: Validation failed: Unsupported schema version: 2.0 (supported: 1.0)
```

---

#### `LockTimeoutError`

Raised when file lock acquisition times out.

**Base Class**: `Exception`

**Example**:
```python
from webui.backend.lib.sidecar_metadata import LockTimeoutError

try:
    # Another process has lock for >5 seconds
    with FileLock("file.json", timeout=5.0):
        pass
except LockTimeoutError as e:
    print(f"Could not acquire lock: {e}")
```

**Default Timeout**: 5.0 seconds

---

### File Locking

#### `FileLock(path, exclusive=True, timeout=5.0)`

Context manager for file locking with timeout.

**Parameters**:
- `path`: Path to file to lock
- `exclusive`: True for exclusive lock (write), False for shared (read)
- `timeout`: Maximum seconds to wait for lock

**Example**:
```python
from webui.backend.lib.sidecar_metadata import FileLock

# Exclusive lock (for writing)
with FileLock("file.json", exclusive=True, timeout=5.0) as f:
    f.write("data")

# Shared lock (for reading)
with FileLock("file.json", exclusive=False, timeout=5.0) as f:
    data = f.read()
```

**Features**:
- **Exponential backoff**: Starts at 1ms, doubles up to 100ms
- **Auto-cleanup**: Unlocks on context exit
- **Cross-process**: Works across multiple processes

---

## Service API Reference

The service (`webui/backend/services/sidecar_service.py`) provides a cached layer over the library.

### `SidecarService`

Two-level LRU cache for photo metadata with thread-safe access.

**Architecture**:
- **L1 Cache**: In-memory LRU (fast, ~1000 entries) - <10ms
- **L2 Cache**: File-based LRU (persistent, ~10000 entries) - <50ms

**Constructor**:
```python
def __init__(
    self,
    cache_dir: Path | str,
    l1_max_size: int = 1000,
    l2_max_size: int = 10000,
    cache_version: str = "1.0"
)
```

**Parameters**:
- `cache_dir`: Directory for L2 file-based cache
- `l1_max_size`: Maximum entries in L1 memory cache (default: 1000)
- `l2_max_size`: Maximum entries in L2 file cache (default: 10000)
- `cache_version`: Cache format version (default: "1.0")

**Example**:
```python
from pathlib import Path
from webui.backend.services.sidecar_service import SidecarService

service = SidecarService(
    cache_dir=Path("/var/cache/mothbox/sidecar"),
    l1_max_size=1000,
    l2_max_size=10000
)
```

**Thread Safety**: All methods are thread-safe with proper locking

---

### Methods

#### `get_metadata(photo_path)`

Get metadata from cache (L1 → L2 → disk).

**Signature**:
```python
def get_metadata(self, photo_path: str) -> SidecarMetadata | None
```

**Parameters**:
- `photo_path`: Path to photo file (string)

**Returns**:
- `SidecarMetadata` if found
- `None` if not found

**Cache Behavior**:
1. Check L1 (in-memory) - <10ms if hit
2. Check L2 (file cache) - <50ms if hit
3. Read from disk - ~100ms, then cache in L1 and L2

**Example**:
```python
# First call - cache miss, reads from disk (~100ms)
metadata = service.get_metadata("/photos/moth.jpg")

# Second call - L1 hit (<10ms)
metadata = service.get_metadata("/photos/moth.jpg")
```

**Performance**:
- L1 hit: <10ms
- L2 hit: <50ms
- Disk read: ~100ms

---

#### `set_metadata(photo_path, metadata)`

Store metadata in L1, L2, and disk sidecar.

**Signature**:
```python
def set_metadata(self, photo_path: str, metadata: SidecarMetadata) -> None
```

**Parameters**:
- `photo_path`: Path to photo file
- `metadata`: SidecarMetadata object to store

**Example**:
```python
from webui.backend.lib.sidecar_metadata import create_metadata

metadata = create_metadata(
    "/photos/moth.jpg",
    tags=["moth", "night"]
)

service.set_metadata("/photos/moth.jpg", metadata)
```

**Write Order**: Disk → L2 → L1 (ensures consistency)

---

#### `update_metadata(photo_path, updates)`

Update metadata and cache.

**Signature**:
```python
def update_metadata(self, photo_path: str, updates: dict) -> SidecarMetadata | None
```

**Parameters**:
- `photo_path`: Path to photo file
- `updates`: Dictionary of fields to update

**Returns**:
- Updated `SidecarMetadata` if successful
- `None` if photo doesn't exist

**Example**:
```python
metadata = service.update_metadata(
    "/photos/moth.jpg",
    {"species": "Actias luna", "notes": "Confirmed ID"}
)

if metadata:
    print(f"Updated: {metadata.species}")
else:
    print("Photo not found")
```

**Cache Update**: Updates L1, L2, and disk atomically

---

#### `invalidate(photo_path)`

Remove photo from L1 and L2 cache.

**Signature**:
```python
def invalidate(self, photo_path: str) -> bool
```

**Parameters**:
- `photo_path`: Path to photo file

**Returns**:
- `True` if entry was removed from cache
- `False` if not in cache

**Example**:
```python
# Force re-read from disk on next access
removed = service.invalidate("/photos/moth.jpg")

if removed:
    print("Cache invalidated")
```

**Use Cases**:
- External modification detected
- Manual metadata edit
- Testing cache behavior

---

#### `clear()`

Clear entire cache (both L1 and L2) and reset statistics.

**Signature**:
```python
def clear(self) -> None
```

**Example**:
```python
# Clear all cached metadata
service.clear()

# Verify cache is empty
stats = service.get_statistics()
print(f"L1 hits: {stats['l1_hits']}")  # 0
```

**Warning**: All cached data is lost (disk sidecars unaffected)

---

#### `get_statistics()`

Get current cache statistics.

**Signature**:
```python
def get_statistics(self) -> dict
```

**Returns**:
Dictionary with cache metrics:
- `l1_hits` (int): L1 cache hits
- `l1_misses` (int): L1 cache misses
- `l2_hits` (int): L2 cache hits
- `l2_misses` (int): Complete cache misses (read from disk)
- `hit_ratio` (float): Overall cache hit ratio (0.0-1.0)

**Example**:
```python
stats = service.get_statistics()

print(f"L1 hits: {stats['l1_hits']}")
print(f"L2 hits: {stats['l2_hits']}")
print(f"Cache misses: {stats['l2_misses']}")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")

# Example output:
# L1 hits: 850
# L2 hits: 120
# Cache misses: 30
# Hit ratio: 97.00%
```

---

### Batch Operations

#### `batch_get_metadata(photo_paths)`

Get metadata for multiple photos.

**Signature**:
```python
def batch_get_metadata(self, photo_paths: list[str]) -> list[SidecarMetadata | None]
```

**Parameters**:
- `photo_paths`: List of photo paths

**Returns**:
- List of `SidecarMetadata` (or `None` if not found), in same order as input

**Example**:
```python
photos = [
    "/photos/moth1.jpg",
    "/photos/moth2.jpg",
    "/photos/moth3.jpg"
]

results = service.batch_get_metadata(photos)

for photo, metadata in zip(photos, results):
    if metadata:
        print(f"{photo}: {metadata.tags}")
    else:
        print(f"{photo}: No metadata")
```

**Performance**: ~1000 photos in <2 seconds (with cache)

---

#### `list_metadata_for_directory(directory, limit=50, offset=0)`

List metadata for all photos with sidecars in directory (paginated).

**Signature**:
```python
def list_metadata_for_directory(
    self,
    directory: Path | str,
    limit: int = 50,
    offset: int = 0
) -> dict
```

**Parameters**:
- `directory`: Directory to search
- `limit`: Maximum number of results (default: 50)
- `offset`: Number of results to skip (default: 0)

**Returns**:
Dictionary with:
- `items` (list[dict]): List of metadata dictionaries (serialized)
- `total` (int): Total number of photos with sidecars
- `limit` (int): Limit used
- `offset` (int): Offset used
- `has_next` (bool): Whether there are more results

**Example**:
```python
# First page
page1 = service.list_metadata_for_directory(
    "/photos",
    limit=50,
    offset=0
)

print(f"Total photos: {page1['total']}")
print(f"Showing: {len(page1['items'])}")
print(f"Has more: {page1['has_next']}")

# Iterate through items
for item in page1['items']:
    print(f"- {item['photo_filename']}: {item['tags']}")

# Next page
if page1['has_next']:
    page2 = service.list_metadata_for_directory(
        "/photos",
        limit=50,
        offset=50
    )
```

**Performance**: <200ms for 50 items (with cache)

---

#### `batch_update_metadata(updates)`

Update multiple photos' metadata.

**Signature**:
```python
def batch_update_metadata(self, updates: list[tuple[str, dict]]) -> list[bool]
```

**Parameters**:
- `updates`: List of (photo_path, updates_dict) tuples

**Returns**:
- List of boolean success indicators (same order as input)

**Example**:
```python
updates = [
    ("/photos/moth1.jpg", {"species": "Actias luna"}),
    ("/photos/moth2.jpg", {"species": "Actias selene"}),
    ("/photos/moth3.jpg", {"tags": ["moth", "verified"]})
]

results = service.batch_update_metadata(updates)

for (photo, _), success in zip(updates, results):
    if success:
        print(f"✓ {photo} updated")
    else:
        print(f"✗ {photo} failed")
```

**Performance**: ~1000 updates in <5 seconds

**Transaction**: Not atomic (each update is independent)

---

## Usage Examples

### Basic Usage

```python
from webui.backend.lib.sidecar_metadata import (
    read_metadata,
    write_metadata,
    create_metadata,
    add_tag,
    update_metadata
)

# Create new metadata
metadata = create_metadata(
    "/photos/moth.jpg",
    tags=["moth", "night"],
    species="Actias luna",
    notes="Large specimen found near pond"
)

# Write to disk
write_metadata("/photos/moth.jpg", metadata)

# Read metadata
metadata = read_metadata("/photos/moth.jpg")
if metadata:
    print(f"Tags: {metadata.tags}")
    print(f"Species: {metadata.species}")

# Add a tag
metadata = add_tag("/photos/moth.jpg", "Luna Moth")
# Tag normalized to "luna moth"

# Update fields
metadata = update_metadata(
    "/photos/moth.jpg",
    {
        "species": "Actias luna (confirmed)",
        "custom": {"weather": "clear", "temperature": "18C"}
    }
)
```

---

### Using the Service with Caching

```python
from pathlib import Path
from webui.backend.services.sidecar_service import SidecarService

# Initialize service
service = SidecarService(cache_dir=Path("/var/cache/mothbox"))

# Get metadata (uses cache)
metadata = service.get_metadata("/photos/moth.jpg")

if metadata:
    print(f"Tags: {metadata.tags}")
else:
    print("No metadata found")

# Update metadata (updates cache + disk)
metadata = service.update_metadata(
    "/photos/moth.jpg",
    {"species": "Actias luna"}
)

# Check cache statistics
stats = service.get_statistics()
print(f"Cache hit ratio: {stats['hit_ratio']:.2%}")
```

---

### Batch Operations

```python
from pathlib import Path
from webui.backend.services.sidecar_service import SidecarService

service = SidecarService(cache_dir=Path("/var/cache/mothbox"))

# Get metadata for multiple photos
photo_paths = [
    "/photos/moth1.jpg",
    "/photos/moth2.jpg",
    "/photos/moth3.jpg"
]

results = service.batch_get_metadata(photo_paths)

for photo, metadata in zip(photo_paths, results):
    if metadata:
        print(f"{photo}: {metadata.tags}")

# List metadata for directory (paginated)
page = service.list_metadata_for_directory(
    "/photos",
    limit=50,
    offset=0
)

print(f"Total: {page['total']}, Showing: {len(page['items'])}")

for item in page['items']:
    print(f"- {item['photo_filename']}: {item['tags']}")

# Batch update
updates = [
    ("/photos/moth1.jpg", {"species": "Actias luna"}),
    ("/photos/moth2.jpg", {"species": "Actias selene"})
]

results = service.batch_update_metadata(updates)
print(f"Updated: {sum(results)} of {len(results)}")
```

---

### Tag Management

```python
from webui.backend.lib.sidecar_metadata import (
    add_tag,
    remove_tag,
    read_metadata
)

# Add tags (normalized to lowercase)
add_tag("/photos/moth.jpg", "MOTH")
add_tag("/photos/moth.jpg", "Night")
add_tag("/photos/moth.jpg", "Luna_Moth")

# Read tags
metadata = read_metadata("/photos/moth.jpg")
print(metadata.tags)
# Output: ['moth', 'night', 'luna_moth']

# Remove tag (case-insensitive)
remove_tag("/photos/moth.jpg", "NIGHT")

metadata = read_metadata("/photos/moth.jpg")
print(metadata.tags)
# Output: ['moth', 'luna_moth']
```

---

### Error Handling

```python
from webui.backend.lib.sidecar_metadata import (
    read_metadata,
    update_metadata,
    ValidationError,
    LockTimeoutError
)

# Graceful handling of missing metadata
metadata = read_metadata("/photos/moth.jpg")
if metadata is None:
    print("No metadata found - creating new")
    metadata = update_metadata("/photos/moth.jpg", {"tags": ["moth"]})

# Validation errors
try:
    # Tag too long
    update_metadata("/photos/moth.jpg", {
        "tags": ["x" * 100]  # Exceeds MAX_TAG_LENGTH (50)
    })
except ValidationError as e:
    print(f"Validation error: {e}")

# Lock timeout
try:
    from webui.backend.lib.sidecar_metadata import FileLock
    with FileLock("/photos/locked.json", timeout=1.0):
        # Will timeout if another process has lock
        pass
except LockTimeoutError as e:
    print(f"Could not acquire lock: {e}")
```

---

### Custom Metadata

```python
from webui.backend.lib.sidecar_metadata import update_metadata, read_metadata

# Store domain-specific metadata
metadata = update_metadata(
    "/photos/moth.jpg",
    {
        "custom": {
            "weather": "clear",
            "temperature": "18C",
            "moon_phase": "full",
            "location": "pond_area_3",
            "trap_id": "trap_002",
            "light_type": "UV_blacklight"
        }
    }
)

# Read custom fields
metadata = read_metadata("/photos/moth.jpg")
print(f"Weather: {metadata.custom.get('weather')}")
print(f"Trap ID: {metadata.custom.get('trap_id')}")
```

**Custom Field Limits**:
- Max 100 keys
- No value size limit (but reasonable sizes recommended)

---

### Cache Invalidation

```python
from pathlib import Path
from webui.backend.services.sidecar_service import SidecarService

service = SidecarService(cache_dir=Path("/var/cache/mothbox"))

# Scenario: External process modifies sidecar file
# Invalidate cache to force re-read from disk

service.invalidate("/photos/moth.jpg")

# Next access reads from disk
metadata = service.get_metadata("/photos/moth.jpg")

# Clear entire cache (e.g., after bulk external changes)
service.clear()
```

---

## Error Handling

### Exception Types

The sidecar metadata system uses two custom exceptions:

1. **`ValidationError`**
   - Raised when metadata validation fails
   - Indicates schema violations (missing fields, wrong types, exceeded limits)
   - Always contains descriptive error message

2. **`LockTimeoutError`**
   - Raised when file lock cannot be acquired within timeout
   - Indicates concurrent access conflict
   - Default timeout: 5.0 seconds

### Graceful Degradation

The library follows a "fail-safe" design:

**`read_metadata()`** returns `None` for:
- Missing sidecar file
- Corrupted JSON
- Invalid schema
- Unsupported schema version
- File permission errors
- Any other exception

**Benefits**:
- No crashes on corrupted data
- Forward compatibility (new versions can read old files)
- Backward compatibility (old versions return None for new files)

### Error Handling Patterns

**Pattern 1: Check before use**
```python
metadata = read_metadata("/photos/moth.jpg")

if metadata:
    print(f"Tags: {metadata.tags}")
else:
    print("No metadata available")
```

**Pattern 2: Create if missing**
```python
metadata = read_metadata("/photos/moth.jpg")

if metadata is None:
    metadata = create_metadata("/photos/moth.jpg", tags=["moth"])
    write_metadata("/photos/moth.jpg", metadata)
```

**Pattern 3: Handle validation errors**
```python
try:
    metadata = update_metadata("/photos/moth.jpg", {
        "tags": ["x" * 100]  # Exceeds limit
    })
except ValidationError as e:
    print(f"Invalid metadata: {e}")
    # Fallback to safe defaults
    metadata = create_metadata("/photos/moth.jpg", tags=["moth"])
```

**Pattern 4: Handle lock timeout**
```python
try:
    with FileLock("/photos/sidecar.json", timeout=5.0):
        # Critical section
        pass
except LockTimeoutError:
    print("File locked by another process")
    # Retry later or skip
```

---

## Design Decisions

### Why Lowercase Tag Normalization?

**Problem**: Users might enter "Moth", "MOTH", "moth" as separate tags.

**Solution**: Automatically normalize to lowercase.

**Benefits**:
- Prevents duplicate tags with different case
- Consistent tag searching (case-insensitive)
- Simplified UI (no need to handle case variations)

**Tradeoff**: Cannot preserve original case (acceptable for tag use case)

---

### Why Fail-Safe for Unknown Schema Versions?

**Problem**: Future versions may introduce incompatible schema changes.

**Solution**: Return `None` for unsupported versions instead of raising error.

**Benefits**:
- Old code doesn't crash on new files
- Allows gradual migration
- No breaking changes when upgrading

**Example**:
```python
# Old code (v1.0) reading new sidecar (v2.0)
metadata = read_metadata("/photos/moth.jpg")
# Returns None instead of crashing

if metadata is None:
    # Handle gracefully (e.g., show "upgrade required" message)
    pass
```

---

### Why Atomic Writes with Temp Files?

**Problem**: Write interrupted by crash/power loss → corrupted sidecar.

**Solution**: Write to `.tmp` file, then atomic rename.

**Benefits**:
- Crash-safe (incomplete writes don't corrupt original)
- Atomic operation (readers see old or new, never partial)
- Standard practice for critical data

**Performance Cost**: Minimal (rename is atomic syscall)

---

### Why Two-Level Cache Architecture?

**Problem**: Large photo collections overwhelm memory cache.

**Solution**: L1 (memory, fast) + L2 (file, persistent).

**Benefits**:
- **L1**: Ultra-fast access (<10ms) for hot data
- **L2**: Fast access (<50ms) for warm data, survives restarts
- **LRU eviction**: Automatically manages cache size
- **Persistent**: L2 survives application restarts

**Performance Targets**:
- L1 hit rate: ~60% (<10ms)
- L2 hit rate: ~15% (~50ms)
- Overall hit rate: >70%

**Cache Flow**:
```
Request → L1 hit? → Return (<10ms)
       ↓ L1 miss
       → L2 hit? → Promote to L1 → Return (<50ms)
       ↓ L2 miss
       → Read disk → Cache in L1 + L2 → Return (~100ms)
```

---

## Performance Characteristics

### Library Operations

| Operation | Complexity | Avg Time | Notes |
|-----------|------------|----------|-------|
| `get_sidecar_path()` | O(1) | <1ms | String concatenation |
| `photo_has_sidecar()` | O(1) | <5ms | File existence check |
| `list_photos_with_sidecars()` | O(n) | 10-50ms | n = files in directory |
| `normalize_tag()` | O(1) | <1ms | String operations |
| `validate_schema()` | O(n) | <5ms | n = number of tags |
| `read_metadata()` | O(1) | <10ms | File read + JSON parse |
| `write_metadata()` | O(1) | <20ms | JSON write + atomic rename |
| `create_metadata()` | O(1) | <1ms | In-memory object creation |
| `update_metadata()` | O(1) | <20ms | Read + modify + write |
| `delete_metadata()` | O(1) | <10ms | File delete |
| `add_tag()` | O(n) | <20ms | n = number of tags |
| `remove_tag()` | O(n) | <20ms | n = number of tags |

### Service Operations (with Cache)

| Operation | L1 Hit | L2 Hit | Miss (Disk) | Notes |
|-----------|--------|--------|-------------|-------|
| `get_metadata()` | <10ms | <50ms | ~100ms | Cold read |
| `set_metadata()` | - | - | ~20ms | Write to all layers |
| `update_metadata()` | - | - | ~30ms | Read + write |
| `invalidate()` | <5ms | <5ms | - | Cache removal |
| `clear()` | <10ms | <50ms | - | Full cache clear |
| `get_statistics()` | <1ms | - | - | In-memory read |

### Batch Operations

| Operation | Items | Avg Time | Throughput | Notes |
|-----------|-------|----------|------------|-------|
| `batch_get_metadata()` | 100 | <500ms | 200/sec | With cache |
| `batch_get_metadata()` | 1000 | <2s | 500/sec | With cache |
| `list_metadata_for_directory()` | 50 | <200ms | - | Paginated |
| `batch_update_metadata()` | 100 | <2s | 50/sec | Disk writes |
| `batch_update_metadata()` | 1000 | <20s | 50/sec | Disk writes |

### Cache Performance

**Hit Ratios** (after warmup):
- L1 hit rate: 60-70%
- L2 hit rate: 10-20%
- Overall hit rate: 70-90%

**Cache Size**:
- L1: ~1000 entries (1-2 MB memory)
- L2: ~10000 entries (10-20 MB disk)

**Eviction**:
- L1: LRU eviction on each insert when full
- L2: Batch eviction (10% of cache) when full

---

## Related Documentation

- **Library Implementation**: `webui/backend/lib/sidecar_metadata.py` (713 lines)
- **Service Implementation**: `webui/backend/services/sidecar_service.py` (588 lines)
- **Unit Tests**: `Tests/unit/test_sidecar_metadata_lib.py` (99+ tests, 99% coverage)
- **Service Tests**: `Tests/unit/test_sidecar_service.py` (60+ tests, 97% coverage)
- **Issue Tracker**: [Issue #102](https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues/102) - Sidecar Metadata Implementation

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-01
**Schema Version**: 1.0
**Next Review**: Phase F API Integration (Issue #102)
