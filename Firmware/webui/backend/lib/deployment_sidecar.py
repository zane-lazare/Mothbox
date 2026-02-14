"""
Deployment Sidecar Library for Mothbox Photo Gallery

Manages deployment-level metadata files (deployment.json/deployment.yaml) at the root
of photo directories. Deployment metadata describes the entire photo collection.

File Naming:
- JSON format: deployment.json (default, always supported)
- YAML format: deployment.yaml (optional, requires PyYAML)

Features:
- Hierarchical discovery: Walk up directory tree to find nearest deployment sidecar
- Thread-safe operations: FileLock for atomic read-modify-write
- JSON support: Always available
- YAML support: Optional via PyYAML library
- Atomic writes: Write to temp file, then rename
- Backup support: Create .bak file before overwriting
- Schema validation: Validate all fields against limits and formats

Usage:
    from webui.backend.lib.deployment_sidecar import (
        create_deployment_metadata,
        read_deployment_metadata,
        update_deployment_metadata,
        find_deployment_sidecar,
    )

    # Create new deployment metadata
    metadata = create_deployment_metadata(
        directory="/var/lib/mothbox/photos/forest_2024",
        name="Oak Ridge Forest Survey 2024",
        latitude=35.9606,
        longitude=-83.9207,
        location_name="Oak Ridge, TN, USA",
        start_date="2024-06-01",
        end_date="2024-08-31",
    )
    write_deployment_metadata(metadata.directory, metadata)

    # Read existing deployment metadata
    metadata = read_deployment_metadata("/var/lib/mothbox/photos/forest_2024")
    if metadata:
        print(f"Deployment: {metadata.deployment_name}")

    # Update deployment metadata
    metadata = update_deployment_metadata(
        "/var/lib/mothbox/photos/forest_2024",
        {"end_date": "2024-09-15"}
    )

    # Find nearest deployment sidecar (hierarchical)
    sidecar_path = find_deployment_sidecar("/var/lib/mothbox/photos/forest_2024/subfolder")
    # Returns: /var/lib/mothbox/photos/forest_2024/deployment.json
"""

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from mothbox_paths import PHOTOS_DIR
from webui.backend.lib.deployment_schema import (
    BACKUP_EXTENSION,
    DEPLOYMENT_FILENAME_JSON,
    DEPLOYMENT_FILENAME_YAML,
    DEPLOYMENT_SCHEMA_VERSION,
    MAX_CUSTOM_DEPTH,
    MAX_CUSTOM_KEYS,
    MAX_DEPLOYMENT_NAME_LENGTH,
    MAX_LATITUDE,
    MAX_LOCATION_NAME_LENGTH,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    SUPPORTED_FORMATS,
    SUPPORTED_VERSIONS,
    DeploymentMetadata,
    ValidationError,
)

from webui.backend.lib.file_lock import FileLock, LockTimeoutError

logger = logging.getLogger(__name__)

# ============================================================================
# YAML Support (optional)
# ============================================================================

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

    # Create a placeholder for yaml.YAMLError so except clauses don't raise NameError
    class _YAMLPlaceholder:
        class YAMLError(Exception):
            pass

    yaml = _YAMLPlaceholder()


# ============================================================================
# Path Utilities
# ============================================================================


def get_deployment_sidecar_path(directory: Path | str, format: str = "json") -> Path:
    """Get deployment sidecar path for a directory.

    Args:
        directory: Directory path
        format: File format ("json" or "yaml")

    Returns:
        Path to deployment sidecar file (deployment.json or deployment.yaml)

    Raises:
        ValueError: If format is not "json" or "yaml"

    Note:
        Path is resolved to absolute path to prevent path traversal attacks.

    Example:
        >>> get_deployment_sidecar_path("/photos/forest_2024")
        PosixPath('/photos/forest_2024/deployment.json')
        >>> get_deployment_sidecar_path("/photos/forest_2024", format="yaml")
        PosixPath('/photos/forest_2024/deployment.yaml')
    """
    if format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {format} (supported: {', '.join(SUPPORTED_FORMATS)})"
        )

    directory = Path(directory).resolve()
    filename = DEPLOYMENT_FILENAME_JSON if format == "json" else DEPLOYMENT_FILENAME_YAML
    return directory / filename


def deployment_has_sidecar(directory: Path | str) -> bool:
    """Check if directory has deployment sidecar metadata.

    Checks for both JSON and YAML formats (JSON has priority).

    Args:
        directory: Directory path

    Returns:
        True if deployment sidecar exists (JSON or YAML), False otherwise

    Example:
        >>> deployment_has_sidecar("/photos/forest_2024")
        True
    """
    directory = Path(directory).resolve()
    json_path = directory / DEPLOYMENT_FILENAME_JSON
    yaml_path = directory / DEPLOYMENT_FILENAME_YAML
    return json_path.exists() or yaml_path.exists()


def find_deployment_sidecar(photo_or_dir: Path | str) -> Path | None:
    """Find nearest deployment sidecar by walking up directory tree.

    Searches current directory and all parent directories up to PHOTOS_DIR root.
    Stops at PHOTOS_DIR to prevent searching outside photo storage.

    Args:
        photo_or_dir: Photo file path or directory path

    Returns:
        Path to nearest deployment sidecar (JSON or YAML), or None if not found

    Example:
        >>> find_deployment_sidecar("/photos/forest_2024/subfolder/photo.jpg")
        PosixPath('/photos/forest_2024/deployment.json')
        >>> find_deployment_sidecar("/photos/no_deployment")
        None
    """
    path = Path(photo_or_dir).resolve()

    # If path is a file, start from its parent directory
    if path.is_file():
        path = path.parent

    # Get PHOTOS_DIR as absolute path for comparison
    photos_root = PHOTOS_DIR.resolve()

    # Walk up directory tree
    current_dir = path
    while True:
        # Check for deployment sidecar in current directory
        json_path = current_dir / DEPLOYMENT_FILENAME_JSON
        yaml_path = current_dir / DEPLOYMENT_FILENAME_YAML

        # JSON has priority over YAML
        if json_path.exists():
            return json_path
        if yaml_path.exists():
            return yaml_path

        # Stop if we've reached PHOTOS_DIR root
        if current_dir == photos_root:
            break

        # Stop if we've reached filesystem root
        if current_dir == current_dir.parent:
            break

        # Move up one directory
        current_dir = current_dir.parent

    return None


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
            isinstance(k, str) and _is_valid_custom_value(v, depth + 1) for k, v in value.items()
        )

    return False


def validate_deployment_schema(data: dict) -> bool:
    """Validate deployment metadata dictionary against schema.

    Args:
        data: Deployment metadata dictionary to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails with detailed error message

    Example:
        >>> validate_deployment_schema(
        ...     {
        ...         "version": "1.0",
        ...         "deployment_name": "Forest Survey 2024",
        ...         "created_at": "2024-06-01T12:00:00Z",
        ...         "modified_at": "2024-06-01T12:00:00Z",
        ...         "latitude": 35.9606,
        ...         "longitude": -83.9207,
        ...     }
        ... )
        True
    """
    # Check required fields
    required_fields = ["version", "deployment_name", "created_at", "modified_at"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

    # Check version support
    if data["version"] not in SUPPORTED_VERSIONS:
        raise ValidationError(
            f"Unsupported schema version: {data['version']} "
            f"(supported: {', '.join(SUPPORTED_VERSIONS)})"
        )

    # Validate deployment_name
    if not isinstance(data["deployment_name"], str):
        raise ValidationError("deployment_name must be a string")
    if not data["deployment_name"].strip():
        raise ValidationError("deployment_name cannot be empty")
    if len(data["deployment_name"]) > MAX_DEPLOYMENT_NAME_LENGTH:
        raise ValidationError(
            f"deployment_name exceeds maximum length ({MAX_DEPLOYMENT_NAME_LENGTH} chars)"
        )

    # Validate location_name
    if data.get("location_name") is not None:
        if not isinstance(data["location_name"], str):
            raise ValidationError("location_name must be a string")
        if len(data["location_name"]) > MAX_LOCATION_NAME_LENGTH:
            raise ValidationError(
                f"location_name exceeds maximum length ({MAX_LOCATION_NAME_LENGTH} chars)"
            )

    # Validate latitude
    if data.get("latitude") is not None:
        lat = data["latitude"]
        if not isinstance(lat, (int, float)):
            raise ValidationError("latitude must be a number")
        if not (MIN_LATITUDE <= lat <= MAX_LATITUDE):
            raise ValidationError(f"latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}")

    # Validate longitude
    if data.get("longitude") is not None:
        lon = data["longitude"]
        if not isinstance(lon, (int, float)):
            raise ValidationError("longitude must be a number")
        if not (MIN_LONGITUDE <= lon <= MAX_LONGITUDE):
            raise ValidationError(f"longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}")

    # Validate altitude
    if data.get("altitude") is not None and not isinstance(data["altitude"], (int, float)):
        raise ValidationError("altitude must be a number")

    # Validate environmental
    if data.get("environmental") is not None:
        if not isinstance(data["environmental"], dict):
            raise ValidationError("environmental must be a dictionary")
        # Validate environmental values are JSON-serializable
        for key, value in data["environmental"].items():
            if not isinstance(key, str):
                raise ValidationError(f"environmental key must be string, got {type(key).__name__}")
            if not _is_valid_custom_value(value):
                raise ValidationError(f"environmental value type not allowed for key '{key}'")

    # Validate custom
    if data.get("custom") is not None:
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

    return True


# ============================================================================
# File I/O (JSON and YAML)
# ============================================================================


def _read_json(path: Path) -> dict | None:
    """Read JSON file with error handling.

    Args:
        path: Path to JSON file

    Returns:
        Dictionary if successful, None if file doesn't exist or is invalid

    Example:
        >>> _read_json(Path("/photos/deployment.json"))
        {'version': '1.0', 'deployment_name': 'Forest Survey', ...}
    """
    if not path.exists():
        return None

    try:
        with FileLock(path, exclusive=False) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.warning(f"Failed to read JSON from {path}: {e}")
        return None


def _write_json(path: Path, data: dict) -> None:
    """Write JSON file atomically with file locking.

    Args:
        path: Path to JSON file
        data: Dictionary to write

    Raises:
        OSError: If write fails

    Example:
        >>> _write_json(Path("/photos/deployment.json"), {"version": "1.0", ...})
    """
    with FileLock(path, exclusive=True) as f:
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)


def _read_yaml(path: Path) -> dict | None:
    """Read YAML file with error handling.

    Args:
        path: Path to YAML file

    Returns:
        Dictionary if successful, None if file doesn't exist or is invalid

    Raises:
        ValueError: If YAML support not available (PyYAML not installed)

    Example:
        >>> _read_yaml(Path("/photos/deployment.yaml"))
        {'version': '1.0', 'deployment_name': 'Forest Survey', ...}
    """
    if not YAML_AVAILABLE:
        raise ValueError("YAML support not available - install PyYAML")

    if not path.exists():
        return None

    try:
        with FileLock(path, exclusive=False) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, ValueError, OSError) as e:
        logger.warning(f"Failed to read YAML from {path}: {e}")
        return None


def _write_yaml(path: Path, data: dict) -> None:
    """Write YAML file atomically with file locking.

    Args:
        path: Path to YAML file
        data: Dictionary to write

    Raises:
        ValueError: If YAML support not available (PyYAML not installed)
        OSError: If write fails

    Example:
        >>> _write_yaml(Path("/photos/deployment.yaml"), {"version": "1.0", ...})
    """
    if not YAML_AVAILABLE:
        raise ValueError("YAML support not available - install PyYAML")

    with FileLock(path, exclusive=True) as f:
        f.seek(0)
        f.truncate()
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


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
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# ============================================================================
# CRUD Operations
# ============================================================================


def read_deployment_metadata(directory: Path | str) -> DeploymentMetadata | None:
    """Read deployment metadata from directory's sidecar file.

    Checks for both JSON and YAML formats (JSON has priority).
    Gracefully handles missing, corrupted, or invalid sidecars by returning None.

    Args:
        directory: Directory path

    Returns:
        DeploymentMetadata if valid sidecar exists, None otherwise

    Example:
        >>> metadata = read_deployment_metadata("/photos/forest_2024")
        >>> if metadata:
        ...     print(metadata.deployment_name)
        'Oak Ridge Forest Survey 2024'
    """
    directory = Path(directory).resolve()

    # Try JSON first (default format)
    json_path = directory / DEPLOYMENT_FILENAME_JSON
    if json_path.exists():
        data = _read_json(json_path)
        if data:
            try:
                validate_deployment_schema(data)
                return DeploymentMetadata.from_dict(data)
            except (ValidationError, KeyError, TypeError) as e:
                logger.warning(f"Invalid deployment metadata in {json_path}: {e}")
                return None

    # Try YAML if JSON not found
    yaml_path = directory / DEPLOYMENT_FILENAME_YAML
    if yaml_path.exists() and YAML_AVAILABLE:
        data = _read_yaml(yaml_path)
        if data:
            try:
                validate_deployment_schema(data)
                return DeploymentMetadata.from_dict(data)
            except (ValidationError, KeyError, TypeError) as e:
                logger.warning(f"Invalid deployment metadata in {yaml_path}: {e}")
                return None

    return None


def write_deployment_metadata(
    directory: Path | str, metadata: DeploymentMetadata, format: str = "json", backup: bool = True
) -> bool:
    """Write deployment metadata to directory's sidecar file atomically.

    Uses file locking for the entire backup + write operation to prevent
    race conditions. Writes directly to the locked file descriptor to
    ensure atomicity with other concurrent operations using FileLock.

    Args:
        directory: Directory path
        metadata: Metadata to write
        format: File format ("json" or "yaml")
        backup: If True, create .bak backup before overwriting

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If format is not "json" or "yaml", or YAML not available

    Example:
        >>> metadata = create_deployment_metadata("/photos/forest_2024", "Forest Survey")
        >>> write_deployment_metadata("/photos/forest_2024", metadata)
        True
    """
    if format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {format} (supported: {', '.join(SUPPORTED_FORMATS)})"
        )

    if format == "yaml" and not YAML_AVAILABLE:
        raise ValueError("YAML support not available - install PyYAML")

    directory = Path(directory).resolve()
    sidecar_path = get_deployment_sidecar_path(directory, format=format)

    try:
        # Ensure directory exists
        directory.mkdir(parents=True, exist_ok=True)

        # Hold lock for entire backup + write operation
        with FileLock(sidecar_path, exclusive=True) as f:
            # Create backup if requested and file has content
            if backup:
                content = f.read()
                if content:
                    backup_path = sidecar_path.with_suffix(
                        f"{sidecar_path.suffix}{BACKUP_EXTENSION}"
                    )
                    backup_path.write_text(content)
                f.seek(0)

            # Write directly to the locked file (not via temp file + replace)
            # This ensures the lock protects the actual file being written
            f.truncate()
            if format == "json":
                json.dump(metadata.to_dict(), f, indent=2)
            else:  # format == "yaml"
                yaml.safe_dump(metadata.to_dict(), f, default_flow_style=False, sort_keys=False)

        # Set file permissions outside lock (non-critical)
        try:
            sidecar_path.chmod(0o644)
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not set permissions on {sidecar_path}: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to write deployment metadata to {sidecar_path}: {e}")
        return False


def create_deployment_metadata(
    directory: Path | str,
    name: str,
    latitude: float | None = None,
    longitude: float | None = None,
    altitude: float | None = None,
    location_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    environmental: dict | None = None,
    mothbox_id: str | None = None,
    firmware_version: str | None = None,
    custom: dict | None = None,
    modified_by: str | None = None,
) -> DeploymentMetadata:
    """Create new deployment metadata for directory.

    Automatically sets version and timestamps.

    Args:
        directory: Directory path
        name: Deployment name/description (required)
        latitude: GPS latitude in decimal degrees (-90.0 to 90.0)
        longitude: GPS longitude in decimal degrees (-180.0 to 180.0)
        altitude: Altitude in meters
        location_name: Human-readable location description
        start_date: Deployment start date (ISO 8601 date YYYY-MM-DD)
        end_date: Deployment end date (ISO 8601 date YYYY-MM-DD)
        environmental: Environmental conditions dictionary
        mothbox_id: Unique identifier for Mothbox hardware
        firmware_version: Firmware version string
        custom: Custom metadata dictionary
        modified_by: User identifier

    Returns:
        New DeploymentMetadata instance

    Raises:
        ValidationError: If validation fails

    Example:
        >>> metadata = create_deployment_metadata(
        ...     directory="/photos/forest_2024",
        ...     name="Oak Ridge Forest Survey 2024",
        ...     latitude=35.9606,
        ...     longitude=-83.9207,
        ...     location_name="Oak Ridge, TN, USA",
        ...     start_date="2024-06-01",
        ...     end_date="2024-08-31",
        ... )
        >>> metadata.deployment_name
        'Oak Ridge Forest Survey 2024'
    """
    timestamp = _get_current_timestamp()

    metadata = DeploymentMetadata(
        version=DEPLOYMENT_SCHEMA_VERSION,
        deployment_name=name,
        created_at=timestamp,
        modified_at=timestamp,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        location_name=location_name,
        start_date=start_date,
        end_date=end_date,
        environmental=environmental or {},
        mothbox_id=mothbox_id,
        firmware_version=firmware_version,
        custom=custom or {},
        modified_by=modified_by,
    )

    # Validate before returning
    validate_deployment_schema(metadata.to_dict())

    return metadata


def update_deployment_metadata(directory: Path | str, updates: dict) -> DeploymentMetadata:
    """Update existing deployment metadata or create new if doesn't exist.

    Performs atomic partial update - only specified fields are modified.
    Uses file locking to ensure thread-safe read-modify-write cycle,
    preventing lost updates when multiple threads modify different fields.

    Args:
        directory: Directory path
        updates: Dictionary of fields to update

    Returns:
        Updated DeploymentMetadata instance

    Raises:
        ValidationError: If updated metadata fails validation
        ValueError: If directory doesn't have deployment_name in updates and no existing metadata

    Example:
        >>> metadata = update_deployment_metadata(
        ...     "/photos/forest_2024", {"end_date": "2024-09-15", "modified_by": "user123"}
        ... )
        >>> metadata.end_date
        '2024-09-15'
    """
    directory = Path(directory).resolve()

    # Try to find existing sidecar (JSON or YAML)
    json_path = directory / DEPLOYMENT_FILENAME_JSON
    yaml_path = directory / DEPLOYMENT_FILENAME_YAML

    # Determine which file to use
    sidecar_path = None
    if json_path.exists():
        sidecar_path = json_path
    elif yaml_path.exists() and YAML_AVAILABLE:
        sidecar_path = yaml_path
    else:
        # No existing sidecar - will create new JSON file
        sidecar_path = json_path

    # Hold lock for entire read-modify-write operation (atomic)
    # FileLock creates the file if it doesn't exist (w+ mode)
    with FileLock(sidecar_path, exclusive=True) as f:
        # Read existing content or create new metadata
        try:
            content = f.read()
            if content:
                f.seek(0)
                data = json.load(f) if sidecar_path.suffix == ".json" else yaml.safe_load(f)
                validate_deployment_schema(data)
                metadata = DeploymentMetadata.from_dict(data)
            else:
                # File was just created (empty) - need deployment_name
                if "deployment_name" not in updates:
                    raise ValueError(
                        "deployment_name required when creating new deployment metadata"
                    )
                metadata = create_deployment_metadata(directory, name=updates["deployment_name"])
        except (json.JSONDecodeError, yaml.YAMLError, ValidationError, KeyError):
            # Corrupted or invalid - create new
            if "deployment_name" not in updates:
                raise ValueError(
                    "deployment_name required when creating new deployment metadata"
                ) from None
            metadata = create_deployment_metadata(directory, name=updates["deployment_name"])

        # Update fields
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        # Update modified_at timestamp
        metadata.modified_at = _get_current_timestamp()

        # Validate before writing
        validate_deployment_schema(metadata.to_dict())

        # Write atomically while holding lock
        f.seek(0)
        f.truncate()
        if sidecar_path.suffix == ".json":
            json.dump(metadata.to_dict(), f, indent=2)
        else:  # .yaml
            yaml.safe_dump(metadata.to_dict(), f, default_flow_style=False, sort_keys=False)

    return metadata


def delete_deployment_metadata(directory: Path | str, backup: bool = True) -> bool:
    """Delete directory's deployment metadata.

    Deletes both JSON and YAML formats if they exist.

    Args:
        directory: Directory path
        backup: If True, create .bak backup before deleting

    Returns:
        True if at least one sidecar was deleted, False if none existed

    Example:
        >>> delete_deployment_metadata("/photos/forest_2024")
        True
    """
    directory = Path(directory).resolve()
    deleted = False

    # Delete JSON sidecar
    json_path = directory / DEPLOYMENT_FILENAME_JSON
    if json_path.exists():
        try:
            if backup:
                backup_path = json_path.with_suffix(f".json{BACKUP_EXTENSION}")
                backup_path.write_text(json_path.read_text())
            json_path.unlink()
            deleted = True
        except Exception as e:
            logger.error(f"Failed to delete {json_path}: {e}")

    # Delete YAML sidecar
    yaml_path = directory / DEPLOYMENT_FILENAME_YAML
    if yaml_path.exists():
        try:
            if backup:
                backup_path = yaml_path.with_suffix(f".yaml{BACKUP_EXTENSION}")
                backup_path.write_text(yaml_path.read_text())
            yaml_path.unlink()
            deleted = True
        except Exception as e:
            logger.error(f"Failed to delete {yaml_path}: {e}")

    return deleted


# ============================================================================
# Cleanup Utilities
# ============================================================================


def cleanup_temp_files(directory: Path | str) -> int:
    """Remove stale .lock files from deployment sidecar operations.

    Call at startup or periodically to clean up orphaned lock files
    that may remain if process crashes during atomic write operations.

    Args:
        directory: Directory to clean

    Returns:
        Number of lock files removed

    Example:
        >>> removed = cleanup_temp_files("/photos/forest_2024")
        >>> print(f"Cleaned up {removed} lock files")
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0

    removed = 0

    # Clean up .lock files for both JSON and YAML formats
    for pattern in ("deployment.json.lock", "deployment.yaml.lock"):
        lock_file = directory / pattern
        if lock_file.exists():
            try:
                # Check if lock file is stale (older than 1 hour)
                age = time.time() - lock_file.stat().st_mtime
                if age > 3600:  # 1 hour
                    lock_file.unlink()
                    removed += 1
            except Exception as e:
                logger.debug(f"Failed to clean up {lock_file}: {e}")

    return removed


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Data classes
    "DeploymentMetadata",
    # Constants
    "DEPLOYMENT_SCHEMA_VERSION",
    "SUPPORTED_VERSIONS",
    "DEPLOYMENT_FILENAME_JSON",
    "DEPLOYMENT_FILENAME_YAML",
    "BACKUP_EXTENSION",
    "YAML_AVAILABLE",
    # Exceptions
    "ValidationError",
    "LockTimeoutError",
    # Path utilities
    "get_deployment_sidecar_path",
    "deployment_has_sidecar",
    "find_deployment_sidecar",
    # Schema validation
    "validate_deployment_schema",
    # CRUD operations
    "read_deployment_metadata",
    "write_deployment_metadata",
    "create_deployment_metadata",
    "update_deployment_metadata",
    "delete_deployment_metadata",
    # File locking (re-exported from sidecar_metadata)
    "FileLock",
    # Cleanup utilities
    "cleanup_temp_files",
]
