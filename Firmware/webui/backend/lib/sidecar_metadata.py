"""
Sidecar Metadata Library for Mothbox Photo Gallery

Stores photo-level metadata (tags, species, notes) in JSON sidecar files.
Each photo can have an associated {photo}.json file with structured metadata.

File Naming:
- Photo: photo.jpg
- Sidecar: photo.jpg.json

Schema Version: 1.1 (backward compatible with 1.0)
- version: Schema version (string, "1.0" or "1.1")
- photo_filename: Original photo filename (string)
- created_at: Timestamp of sidecar creation (ISO 8601 string)
- modified_at: Timestamp of last modification (ISO 8601 string)
- tags: List of tags (list[str], normalized to lowercase)
- species: Species identification (string | None, max 200 chars)
- notes: User notes (string | None, max 10000 chars)
- custom: Custom key-value metadata (dict, max 100 keys)
- modified_by: User identifier for last modification (string | None)
- species_confidence: Confidence level (string | None, enum: "certain", "probable", "possible", "unknown") [v1.1+]
- species_common_name: Common name for species (string | None, max 200 chars) [v1.1+]
- species_reference_url: Reference URL (string | None, valid http/https URL with hostname) [v1.1+]

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

    # Create with v1.1 fields
    metadata = create_metadata(
        "photo.jpg",
        species="Actias luna",
        species_confidence="certain",
        species_common_name="Luna Moth",
        species_reference_url="https://inaturalist.org/taxa/47921"
    )

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
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

SCHEMA_VERSION = "1.1"  # Current schema version
SUPPORTED_VERSIONS = ["1.0", "1.1"]  # All supported versions for backward compatibility
BACKUP_EXTENSION = ".bak"

# Validation limits
MAX_TAG_LENGTH = 50
MAX_SPECIES_LENGTH = 200
MAX_NOTES_LENGTH = 10000
MAX_CUSTOM_KEYS = 100
MAX_CUSTOM_DEPTH = 5  # Maximum nesting depth for custom values
MAX_COMMON_NAME_LENGTH = 200  # Maximum length for species_common_name
MAX_REFERENCE_URL_LENGTH = 500  # Maximum length for species_reference_url

# Enum values for species_confidence
SPECIES_CONFIDENCE_VALUES = ["certain", "probable", "possible", "unknown"]

# API limits (import from centralized constants, re-export for backwards compatibility)
from webui.backend.constants import MAX_BULK_FILES as MAX_BULK_FILES  # noqa: E402, F401

MAX_PAGINATION_LIMIT = 200  # Maximum items per page for list endpoints


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
        version: Schema version (currently "1.1")
        photo_filename: Original photo filename
        created_at: ISO 8601 timestamp of creation
        modified_at: ISO 8601 timestamp of last modification
        tags: List of normalized tags (lowercase)
        species: Species identification (optional)
        notes: User notes (optional)
        custom: Custom metadata dictionary (optional)
        modified_by: User identifier for last modification (optional)
        species_confidence: Confidence level for species ID (optional, v1.1+)
        species_common_name: Common name for species (optional, v1.1+)
        species_reference_url: Reference URL for species (optional, v1.1+)
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
    species_confidence: str | None = None
    species_common_name: str | None = None
    species_reference_url: str | None = None

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
            modified_by=data.get("modified_by"),
            species_confidence=data.get("species_confidence"),
            species_common_name=data.get("species_common_name"),
            species_reference_url=data.get("species_reference_url")
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

    Note:
        Path is resolved to absolute path to prevent path traversal attacks.

    Example:
        >>> get_sidecar_path("photo.jpg")
        PosixPath('/absolute/path/to/photo.jpg.json')
    """
    photo_path = Path(photo_path).resolve()
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

def _is_valid_custom_value(value, depth: int = 0) -> bool:
    """Validate custom value is a safe JSON-serializable type.

    Checks that values are one of: None, str, int, float, bool, list, dict.
    Lists and dicts are recursively validated up to MAX_CUSTOM_DEPTH.

    Args:
        value: Value to check
        depth: Current nesting depth (max MAX_CUSTOM_DEPTH)

    Returns:
        True if valid, False otherwise
    """
    if depth > MAX_CUSTOM_DEPTH:
        return False  # Prevent deeply nested structures

    if value is None or isinstance(value, (str, int, float, bool)):
        return True

    if isinstance(value, list):
        return all(_is_valid_custom_value(v, depth + 1) for v in value)

    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_valid_custom_value(v, depth + 1)
            for k, v in value.items()
        )

    return False


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
        >>> validate_schema({"version": "1.1", "tags": [], ...})
        True
    """
    # Check required fields
    required_fields = ["version", "photo_filename", "created_at", "modified_at", "tags", "custom"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

    # Check version support (allow both 1.0 and 1.1 for backward compatibility)
    if data["version"] not in SUPPORTED_VERSIONS:
        raise ValidationError(f"Unsupported schema version: {data['version']} (supported: {', '.join(SUPPORTED_VERSIONS)})")

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

    # Validate custom key/value types
    for key, value in data["custom"].items():
        if not isinstance(key, str):
            raise ValidationError(f"custom key must be string, got {type(key).__name__}")

        if not _is_valid_custom_value(value):
            raise ValidationError(f"custom value type not allowed for key '{key}'")

    # Validate schema v1.1 fields
    if data.get("species_confidence") is not None and data["species_confidence"] not in SPECIES_CONFIDENCE_VALUES:
        raise ValidationError(
            f"species_confidence must be one of {SPECIES_CONFIDENCE_VALUES}, got '{data['species_confidence']}'"
        )

    if data.get("species_common_name") is not None and len(data["species_common_name"]) > MAX_COMMON_NAME_LENGTH:
        raise ValidationError(f"species_common_name exceeds maximum length ({MAX_COMMON_NAME_LENGTH} chars)")

    if data.get("species_reference_url") is not None:
        url = data["species_reference_url"]
        if len(url) > MAX_REFERENCE_URL_LENGTH:
            raise ValidationError(f"species_reference_url exceeds maximum length ({MAX_REFERENCE_URL_LENGTH} chars)")
        # Validate URL format using urlparse (not just prefix check)
        # Also check for spaces in URL (urlparse accepts them but they're invalid)
        if ' ' in url:
            raise ValidationError("species_reference_url must be a valid http:// or https:// URL")
        try:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                raise ValidationError("species_reference_url must be a valid http:// or https:// URL")
        except ValueError as err:
            raise ValidationError("species_reference_url must be a valid http:// or https:// URL") from err

    return True


# ============================================================================
# File Locking
# ============================================================================

class FileLock:
    """File lock context manager using fcntl with separate lock file.

    Uses a separate .lock file to acquire the lock BEFORE opening the data file.
    This prevents race conditions where threads open the data file before
    acquiring the lock and read stale content.

    Args:
        path: Path to data file to lock
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
        self.lock_path = Path(str(self.path) + ".lock")
        self.exclusive = exclusive
        self.timeout = timeout
        self.lock_file = None
        self.data_file = None

    def __enter__(self):
        """Acquire lock on lock file, then open data file."""
        # Open/create lock file and acquire lock on it
        self.lock_file = open(self.lock_path, "w")

        lock_type = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        start_time = time.time()
        wait_time = 0.001  # Start with 1ms

        while True:
            try:
                # Try non-blocking lock on the lock file
                fcntl.flock(self.lock_file.fileno(), lock_type | fcntl.LOCK_NB)
                break  # Lock acquired
            except BlockingIOError:
                # Lock held by another process/thread
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    self.lock_file.close()
                    raise LockTimeoutError(f"Could not acquire lock on {self.path} within {self.timeout}s") from None

                # Exponential backoff
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 0.1)  # Max 100ms between attempts

        # NOW open data file (after lock acquired) - this is the key fix
        # The file existence check and open happen AFTER we hold the lock
        mode = ("r+" if self.path.exists() else "w+") if self.exclusive else "r"
        self.data_file = open(self.path, mode)

        return self.data_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close data file, release lock, close lock file."""
        # Close data file first
        if self.data_file:
            with contextlib.suppress(Exception):
                self.data_file.close()

        # Release lock and close lock file
        if self.lock_file:
            with contextlib.suppress(Exception):
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            with contextlib.suppress(Exception):
                self.lock_file.close()


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
    """Write metadata to photo's sidecar file atomically.

    Uses file locking for the entire backup + write operation to prevent
    race conditions. Writes directly to the locked file descriptor to
    ensure atomicity with other concurrent operations using FileLock.

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
        # Hold lock for entire backup + write operation
        with FileLock(sidecar_path, exclusive=True) as f:
            # Create backup if requested and file has content
            if backup:
                content = f.read()
                if content:
                    backup_path = sidecar_path.with_suffix(f".json{BACKUP_EXTENSION}")
                    backup_path.write_text(content)
                f.seek(0)

            # Write directly to the locked file (not via temp file + replace)
            # This ensures the lock protects the actual file being written
            f.truncate()
            json.dump(metadata.to_dict(), f, indent=2)

        # Set file permissions outside lock (non-critical)
        try:
            sidecar_path.chmod(0o644)
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not set permissions on {sidecar_path}: {e}")

        return True

    except Exception:
        return False


def create_metadata(
    photo_path: Path | str,
    tags: list[str] | None = None,
    species: str | None = None,
    notes: str | None = None,
    custom: dict | None = None,
    modified_by: str | None = None,
    species_confidence: str | None = None,
    species_common_name: str | None = None,
    species_reference_url: str | None = None
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
        species_confidence: Confidence level (v1.1+)
        species_common_name: Common name (v1.1+)
        species_reference_url: Reference URL (v1.1+)

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
        modified_by=modified_by,
        species_confidence=species_confidence,
        species_common_name=species_common_name,
        species_reference_url=species_reference_url
    )


def update_metadata(
    photo_path: Path | str,
    updates: dict
) -> SidecarMetadata:
    """Update existing metadata or create new if doesn't exist.

    Performs atomic partial update - only specified fields are modified.
    Uses file locking to ensure thread-safe read-modify-write cycle,
    preventing lost updates when multiple threads modify different fields.

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
    sidecar_path = get_sidecar_path(photo_path)

    # Hold lock for entire read-modify-write operation (atomic)
    # FileLock creates the file if it doesn't exist (w+ mode)
    with FileLock(sidecar_path, exclusive=True) as f:
        # Read existing content or create new metadata
        try:
            content = f.read()
            if content:
                f.seek(0)
                data = json.load(f)
                validate_schema(data)
                metadata = SidecarMetadata.from_dict(data)
            else:
                # File was just created (empty)
                metadata = create_metadata(photo_path)
        except (json.JSONDecodeError, ValidationError, KeyError):
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

        # Write atomically while holding lock
        f.seek(0)
        f.truncate()
        json.dump(metadata.to_dict(), f, indent=2)

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
    """Add tag to photo metadata with atomic read-modify-write.

    Creates sidecar if doesn't exist. Normalizes tag and prevents duplicates.
    Uses file locking to ensure atomic operation under concurrent access.

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
    sidecar_path = get_sidecar_path(photo_path)

    # Hold lock for entire read-modify-write operation (atomic)
    # FileLock creates the file if it doesn't exist (w+ mode)
    with FileLock(sidecar_path, exclusive=True) as f:
        # Read existing content or create new metadata
        try:
            content = f.read()
            if content:
                f.seek(0)
                data = json.load(f)
                validate_schema(data)
                metadata = SidecarMetadata.from_dict(data)
            else:
                # File was just created (empty)
                metadata = create_metadata(photo_path)
        except (json.JSONDecodeError, ValidationError, KeyError):
            metadata = create_metadata(photo_path)

        # Modify - add tag if not already present
        if normalized_tag not in metadata.tags:
            metadata.tags.append(normalized_tag)
            metadata.modified_at = _get_current_timestamp()

            # Write atomically while holding lock
            f.seek(0)
            f.truncate()
            json.dump(metadata.to_dict(), f, indent=2)

    return metadata


def remove_tag(photo_path: Path | str, tag: str) -> SidecarMetadata:
    """Remove tag from photo metadata with atomic read-modify-write.

    Normalizes tag before removal. Returns unchanged metadata if tag not found
    or sidecar doesn't exist. Uses file locking for atomic operations.

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
    sidecar_path = get_sidecar_path(photo_path)

    # If sidecar doesn't exist, return empty metadata (nothing to remove)
    if not sidecar_path.exists():
        return create_metadata(photo_path)

    # Hold lock for entire read-modify-write operation (atomic)
    with FileLock(sidecar_path, exclusive=True) as f:
        try:
            content = f.read()
            if not content:
                # File exists but is empty (shouldn't happen, but handle it)
                return create_metadata(photo_path)
            f.seek(0)
            data = json.load(f)
            validate_schema(data)
            metadata = SidecarMetadata.from_dict(data)
        except (json.JSONDecodeError, ValidationError, KeyError):
            return create_metadata(photo_path)

        # Modify - remove tag if present
        if normalized_tag in metadata.tags:
            metadata.tags.remove(normalized_tag)
            metadata.modified_at = _get_current_timestamp()

            # Write atomically while holding lock
            f.seek(0)
            f.truncate()
            json.dump(metadata.to_dict(), f, indent=2)

    return metadata


# ============================================================================
# Cleanup Utilities
# ============================================================================

def cleanup_temp_files(directory: Path | str, max_age_seconds: int = 3600) -> int:
    """Remove stale .tmp and .lock files older than max_age_seconds.

    Call at startup or periodically to clean up orphaned temp and lock files
    that may remain if process crashes during atomic write operations.

    Args:
        directory: Directory to clean
        max_age_seconds: Remove files older than this (default: 1 hour)

    Returns:
        Number of files removed

    Example:
        >>> removed = cleanup_temp_files("/photos", max_age_seconds=3600)
        >>> print(f"Cleaned up {removed} temp files")
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0

    removed = 0
    current_time = time.time()

    # Clean up both .tmp and .lock files
    for pattern in ("*.json.tmp", "*.json.lock"):
        for tmp_file in directory.glob(pattern):
            try:
                age = current_time - tmp_file.stat().st_mtime
                if age > max_age_seconds:
                    tmp_file.unlink()
                    removed += 1
            except Exception:
                pass  # Non-critical cleanup

    return removed


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Data classes
    "SidecarMetadata",
    # Constants
    "SCHEMA_VERSION",
    "SUPPORTED_VERSIONS",
    "BACKUP_EXTENSION",
    "SPECIES_CONFIDENCE_VALUES",
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
    # Cleanup utilities
    "cleanup_temp_files",
]
