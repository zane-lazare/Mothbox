"""
Sidecar Metadata Library for Mothbox Photo Gallery (Issue #102)

Stores photo-level metadata (tags, species, notes) in JSON sidecar files.
Each photo can have an associated {photo}.json file with structured metadata.

File Naming:
- Photo: photo.jpg
- Sidecar: photo.jpg.json

Schema Version: 1.0
- version: Schema version (string, "1.0")
- photo_filename: Original photo filename (string)
- created_at: Timestamp of sidecar creation (ISO 8601 string)
- modified_at: Timestamp of last modification (ISO 8601 string)
- tags: List of tags (list[str], normalized to lowercase)
- species: Species identification (string | None, max 200 chars)
- notes: User notes (string | None, max 10000 chars)
- custom: Custom key-value metadata (dict, max 100 keys)
- modified_by: User identifier for last modification (string | None)

Usage:
    from webui.backend.lib.sidecar_metadata import (
        create_metadata,
        read_metadata,
        update_metadata,
        add_tag,
        remove_tag,
    )

    # Create new metadata
    metadata = create_metadata("photo.jpg", tags=["moth", "night"])

    # Read existing metadata
    metadata = read_metadata("photo.jpg")
    if metadata:
        print(f"Tags: {metadata.tags}")

    # Update metadata
    metadata = update_metadata("photo.jpg", {"species": "Actias luna"})

    # Tag operations
    add_tag("photo.jpg", "luna_moth")
    remove_tag("photo.jpg", "night")
"""

import contextlib
import fcntl
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

SCHEMA_VERSION = "1.0"
BACKUP_EXTENSION = ".bak"

# Validation limits
MAX_TAG_LENGTH = 50
MAX_SPECIES_LENGTH = 200
MAX_NOTES_LENGTH = 10000
MAX_CUSTOM_KEYS = 100


# ============================================================================
# Exceptions
# ============================================================================

class ValidationError(Exception):
    """Raised when metadata validation fails."""


class LockTimeoutError(Exception):
    """Raised when file lock acquisition times out."""


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SidecarMetadata:
    """Photo sidecar metadata structure.

    Attributes:
        version: Schema version (currently "1.0")
        photo_filename: Original photo filename
        created_at: ISO 8601 timestamp of creation
        modified_at: ISO 8601 timestamp of last modification
        tags: List of normalized tags (lowercase)
        species: Species identification (optional)
        notes: User notes (optional)
        custom: Custom metadata dictionary (optional)
        modified_by: User identifier for last modification (optional)
    """
    version: str
    photo_filename: str
    created_at: str
    modified_at: str
    tags: list[str]
    species: str | None
    notes: str | None
    custom: dict
    modified_by: str | None

    def to_dict(self) -> dict:
        """Convert metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation of metadata.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SidecarMetadata":
        """Create metadata instance from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            SidecarMetadata instance
        """
        return cls(
            version=data["version"],
            photo_filename=data["photo_filename"],
            created_at=data["created_at"],
            modified_at=data["modified_at"],
            tags=data["tags"],
            species=data.get("species"),
            notes=data.get("notes"),
            custom=data.get("custom", {}),
            modified_by=data.get("modified_by")
        )


# ============================================================================
# Path Utilities
# ============================================================================

def get_sidecar_path(photo_path: Path | str) -> Path:
    """Get sidecar JSON path for a photo.

    Args:
        photo_path: Path to photo file

    Returns:
        Path to sidecar JSON file ({photo}.json)

    Example:
        >>> get_sidecar_path("photo.jpg")
        PosixPath('photo.jpg.json')
    """
    photo_path = Path(photo_path)
    return photo_path.parent / f"{photo_path.name}.json"


def photo_has_sidecar(photo_path: Path | str) -> bool:
    """Check if photo has associated sidecar metadata.

    Args:
        photo_path: Path to photo file

    Returns:
        True if sidecar exists, False otherwise

    Example:
        >>> photo_has_sidecar("photo.jpg")
        True
    """
    sidecar_path = get_sidecar_path(photo_path)
    return sidecar_path.exists()


def list_photos_with_sidecars(directory: Path) -> list[Path]:
    """List all photos in directory that have sidecar metadata.

    Args:
        directory: Directory to search

    Returns:
        List of photo paths (Path objects) that have sidecars

    Example:
        >>> photos = list_photos_with_sidecars("/photos")
        >>> len(photos)
        42
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    photos_with_sidecars = []

    # Find all .json sidecar files
    for sidecar_path in directory.glob("*.json"):
        # Skip backup files
        if sidecar_path.name.endswith(".json.bak"):
            continue

        # Derive photo path from sidecar
        # Sidecar format: {photo}.json, so remove .json extension
        photo_name = sidecar_path.name[:-5]  # Remove .json
        photo_path = directory / photo_name

        # Only include if the photo actually exists
        if photo_path.exists() and photo_path.is_file():
            photos_with_sidecars.append(photo_path)

    return sorted(photos_with_sidecars)


# ============================================================================
# Tag Normalization
# ============================================================================

def normalize_tag(tag: str) -> str:
    """Normalize tag to lowercase and strip whitespace.

    Args:
        tag: Tag string to normalize

    Returns:
        Normalized tag (lowercase, stripped)

    Example:
        >>> normalize_tag("  MOTH  ")
        'moth'
        >>> normalize_tag("Luna_Moth")
        'luna_moth'
    """
    return tag.strip().lower()


# ============================================================================
# Schema Validation
# ============================================================================

def validate_schema(data: dict) -> bool:
    """Validate metadata dictionary against schema.

    Args:
        data: Metadata dictionary to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails

    Example:
        >>> validate_schema({"version": "1.0", "tags": [], ...})
        True
    """
    # Check required fields
    required_fields = ["version", "photo_filename", "created_at", "modified_at", "tags", "custom"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

    # Check version support
    if data["version"] != SCHEMA_VERSION:
        raise ValidationError(f"Unsupported schema version: {data['version']} (supported: {SCHEMA_VERSION})")

    # Validate tags
    if not isinstance(data["tags"], list):
        raise ValidationError("tags must be a list")

    for tag in data["tags"]:
        if len(tag) > MAX_TAG_LENGTH:
            raise ValidationError(f"Tag exceeds maximum length ({MAX_TAG_LENGTH} chars): {tag}")

    # Validate species
    if data.get("species") is not None and len(data["species"]) > MAX_SPECIES_LENGTH:
        raise ValidationError(f"species exceeds maximum length ({MAX_SPECIES_LENGTH} chars)")

    # Validate notes
    if data.get("notes") is not None and len(data["notes"]) > MAX_NOTES_LENGTH:
        raise ValidationError(f"notes exceeds maximum length ({MAX_NOTES_LENGTH} chars)")

    # Validate custom
    if not isinstance(data["custom"], dict):
        raise ValidationError("custom must be a dictionary")

    if len(data["custom"]) > MAX_CUSTOM_KEYS:
        raise ValidationError(f"custom exceeds maximum keys ({MAX_CUSTOM_KEYS})")

    return True


# ============================================================================
# File Locking
# ============================================================================

class FileLock:
    """File lock context manager using fcntl.

    Provides exclusive or shared locks with timeout support.
    Uses exponential backoff for lock acquisition.

    Args:
        path: Path to file to lock
        exclusive: True for exclusive lock (LOCK_EX), False for shared (LOCK_SH)
        timeout: Maximum seconds to wait for lock acquisition

    Raises:
        LockTimeoutError: If lock cannot be acquired within timeout

    Example:
        >>> with FileLock("file.json", exclusive=True) as f:
        ...     f.write(data)
    """

    def __init__(self, path: Path, exclusive: bool = True, timeout: float = 5.0):
        self.path = Path(path)
        self.exclusive = exclusive
        self.timeout = timeout
        self.file = None

    def __enter__(self):
        """Acquire lock and return file handle."""
        # Use text mode for reading, binary for writing
        mode = ("r+" if self.path.exists() else "w+") if self.exclusive else "r"

        self.file = open(self.path, mode)

        # Try to acquire lock with exponential backoff
        lock_type = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        start_time = time.time()
        wait_time = 0.001  # Start with 1ms

        while True:
            try:
                # Try non-blocking lock
                fcntl.flock(self.file.fileno(), lock_type | fcntl.LOCK_NB)
                return self.file
            except BlockingIOError:
                # Lock held by another process
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    self.file.close()
                    raise LockTimeoutError(f"Could not acquire lock on {self.path} within {self.timeout}s") from None

                # Exponential backoff
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 0.1)  # Max 100ms between attempts

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock and close file."""
        if self.file:
            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            except Exception:  # nosec B110 - Unlock errors are non-critical
                pass  # Lock release failures don't affect program correctness
            finally:
                self.file.close()


# ============================================================================
# Utility Functions
# ============================================================================

def _get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format.

    Returns:
        ISO 8601 timestamp string ending with 'Z'

    Example:
        >>> _get_current_timestamp()
        '2024-11-06T10:30:00Z'
    """
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


# ============================================================================
# CRUD Operations
# ============================================================================

def read_metadata(photo_path: Path | str) -> SidecarMetadata | None:
    """Read metadata from photo's sidecar file.

    Gracefully handles missing, corrupted, or invalid sidecars by returning None.
    Also returns None for unsupported future schema versions (fail safe).

    Args:
        photo_path: Path to photo file

    Returns:
        SidecarMetadata if valid sidecar exists, None otherwise

    Example:
        >>> metadata = read_metadata("photo.jpg")
        >>> if metadata:
        ...     print(metadata.tags)
    """
    sidecar_path = get_sidecar_path(photo_path)

    if not sidecar_path.exists():
        return None

    try:
        with FileLock(sidecar_path, exclusive=False) as f:
            data = json.load(f)

        # Validate schema
        validate_schema(data)

        return SidecarMetadata.from_dict(data)

    except ValidationError:
        # Invalid or unsupported schema - return None
        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        # Corrupted JSON or missing fields - return None
        return None
    except Exception:
        # Other errors (file permission, etc.) - return None
        return None


def write_metadata(
    photo_path: Path | str,
    metadata: SidecarMetadata,
    backup: bool = True
) -> bool:
    """Write metadata to photo's sidecar file.

    Uses atomic write via temporary file. Optionally creates backup.

    Args:
        photo_path: Path to photo file
        metadata: Metadata to write
        backup: If True, create .bak backup before overwriting

    Returns:
        True if successful, False otherwise

    Example:
        >>> metadata = create_metadata("photo.jpg", tags=["moth"])
        >>> write_metadata("photo.jpg", metadata)
        True
    """
    sidecar_path = get_sidecar_path(photo_path)

    try:
        # Create backup if requested and sidecar exists
        if backup and sidecar_path.exists():
            backup_path = sidecar_path.with_suffix(f".json{BACKUP_EXTENSION}")
            backup_path.write_text(sidecar_path.read_text())

        # Write to temporary file first (atomic write)
        temp_path = sidecar_path.with_suffix(".json.tmp")

        with open(temp_path, "w") as f:
            # Acquire exclusive lock for writing
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(metadata.to_dict(), f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Atomic rename
        temp_path.replace(sidecar_path)

        return True

    except Exception:
        # Clean up temp file if it exists
        temp_path = sidecar_path.with_suffix(".json.tmp")
        if temp_path.exists():
            with contextlib.suppress(Exception):
                temp_path.unlink()
        return False


def create_metadata(
    photo_path: Path | str,
    tags: list[str] | None = None,
    species: str | None = None,
    notes: str | None = None,
    custom: dict | None = None,
    modified_by: str | None = None
) -> SidecarMetadata:
    """Create new metadata for photo.

    Automatically sets timestamps and normalizes tags.

    Args:
        photo_path: Path to photo file
        tags: List of tags (will be normalized to lowercase)
        species: Species identification
        notes: User notes
        custom: Custom metadata dictionary
        modified_by: User identifier

    Returns:
        New SidecarMetadata instance

    Example:
        >>> metadata = create_metadata("photo.jpg", tags=["moth", "Night"])
        >>> metadata.tags
        ['moth', 'night']
    """
    photo_path = Path(photo_path)
    timestamp = _get_current_timestamp()

    # Normalize tags
    normalized_tags = []
    if tags:
        normalized_tags = [normalize_tag(tag) for tag in tags]

    return SidecarMetadata(
        version=SCHEMA_VERSION,
        photo_filename=photo_path.name,
        created_at=timestamp,
        modified_at=timestamp,
        tags=normalized_tags,
        species=species,
        notes=notes,
        custom=custom or {},
        modified_by=modified_by
    )


def update_metadata(
    photo_path: Path | str,
    updates: dict
) -> SidecarMetadata:
    """Update existing metadata or create new if doesn't exist.

    Performs partial update - only specified fields are modified.
    Automatically updates modified_at timestamp and normalizes tags.

    Args:
        photo_path: Path to photo file
        updates: Dictionary of fields to update

    Returns:
        Updated SidecarMetadata instance

    Example:
        >>> metadata = update_metadata("photo.jpg", {"species": "Actias luna"})
        >>> metadata.species
        'Actias luna'
    """
    # Read existing metadata or create new
    metadata = read_metadata(photo_path)
    if metadata is None:
        metadata = create_metadata(photo_path)

    # Update fields
    for key, value in updates.items():
        if key == "tags" and value is not None:
            # Normalize tags
            setattr(metadata, key, [normalize_tag(tag) for tag in value])
        elif hasattr(metadata, key):
            setattr(metadata, key, value)

    # Update modified_at timestamp
    metadata.modified_at = _get_current_timestamp()

    # Write to disk
    write_metadata(photo_path, metadata)

    return metadata


def delete_metadata(
    photo_path: Path | str,
    backup: bool = True
) -> bool:
    """Delete photo's sidecar metadata.

    Args:
        photo_path: Path to photo file
        backup: If True, create .bak backup before deleting

    Returns:
        True if sidecar was deleted, False if didn't exist

    Example:
        >>> delete_metadata("photo.jpg")
        True
    """
    sidecar_path = get_sidecar_path(photo_path)

    if not sidecar_path.exists():
        return False

    try:
        # Create backup if requested
        if backup:
            backup_path = sidecar_path.with_suffix(f".json{BACKUP_EXTENSION}")
            backup_path.write_text(sidecar_path.read_text())

        # Delete sidecar
        sidecar_path.unlink()
        return True

    except Exception:
        return False


# ============================================================================
# Tag Operations
# ============================================================================

def add_tag(photo_path: Path | str, tag: str) -> SidecarMetadata:
    """Add tag to photo metadata.

    Creates sidecar if doesn't exist. Normalizes tag and prevents duplicates.

    Args:
        photo_path: Path to photo file
        tag: Tag to add (will be normalized)

    Returns:
        Updated SidecarMetadata instance

    Example:
        >>> metadata = add_tag("photo.jpg", "Luna_Moth")
        >>> "luna_moth" in metadata.tags
        True
    """
    normalized_tag = normalize_tag(tag)

    # Read existing metadata or create new
    metadata = read_metadata(photo_path)
    if metadata is None:
        metadata = create_metadata(photo_path)

    # Add tag if not already present
    if normalized_tag not in metadata.tags:
        metadata.tags.append(normalized_tag)
        metadata.modified_at = _get_current_timestamp()
        write_metadata(photo_path, metadata)

    return metadata


def remove_tag(photo_path: Path | str, tag: str) -> SidecarMetadata:
    """Remove tag from photo metadata.

    Normalizes tag before removal. Returns unchanged metadata if tag not found.

    Args:
        photo_path: Path to photo file
        tag: Tag to remove (will be normalized)

    Returns:
        Updated SidecarMetadata instance

    Example:
        >>> metadata = remove_tag("photo.jpg", "MOTH")
        >>> "moth" in metadata.tags
        False
    """
    normalized_tag = normalize_tag(tag)

    # Read existing metadata
    metadata = read_metadata(photo_path)
    if metadata is None:
        # No metadata - create empty
        return create_metadata(photo_path)

    # Remove tag if present
    if normalized_tag in metadata.tags:
        metadata.tags.remove(normalized_tag)
        metadata.modified_at = _get_current_timestamp()
        write_metadata(photo_path, metadata)

    return metadata


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Data classes
    "SidecarMetadata",
    # Constants
    "SCHEMA_VERSION",
    "BACKUP_EXTENSION",
    # Exceptions
    "ValidationError",
    "LockTimeoutError",
    # Path utilities
    "get_sidecar_path",
    "photo_has_sidecar",
    "list_photos_with_sidecars",
    # Schema validation
    "validate_schema",
    # Tag normalization
    "normalize_tag",
    # CRUD operations
    "read_metadata",
    "write_metadata",
    "create_metadata",
    "update_metadata",
    "delete_metadata",
    # Tag operations
    "add_tag",
    "remove_tag",
    # File locking
    "FileLock",
]
