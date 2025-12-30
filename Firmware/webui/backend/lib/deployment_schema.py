"""
Deployment Metadata Schema for Mothbox Photo Gallery

Stores deployment-level metadata in JSON/YAML files at the root of photo directories.
Deployment metadata describes the entire photo collection: location, time period,
environmental conditions, and hardware configuration.

File Naming:
- JSON format: deployment.json (default)
- YAML format: deployment.yaml (alternative)

Schema Version: 1.0
- version: Schema version (string, "1.0")
- deployment_name: Name/description of deployment (string, required)
- created_at: Timestamp of metadata creation (ISO 8601 string)
- modified_at: Timestamp of last modification (ISO 8601 string)
- latitude: GPS latitude in decimal degrees (float | None, -90.0 to 90.0)
- longitude: GPS longitude in decimal degrees (float | None, -180.0 to 180.0)
- altitude: Altitude in meters (float | None)
- location_name: Human-readable location description (string | None, max 500 chars)
- start_date: Deployment start date (ISO 8601 date string | None, YYYY-MM-DD)
- end_date: Deployment end date (ISO 8601 date string | None, YYYY-MM-DD)
- environmental: Environmental conditions dictionary (dict, e.g., temperature, humidity)
- mothbox_id: Unique identifier for Mothbox hardware (string | None)
- firmware_version: Firmware version string (string | None)
- custom: Custom key-value metadata (dict, max 100 keys, max 5 nesting depth)
- modified_by: User identifier for last modification (string | None)

Usage:
    from webui.backend.lib.deployment_schema import (
        DeploymentMetadata,
        DEPLOYMENT_SCHEMA_VERSION,
        DEPLOYMENT_FILENAME_JSON,
    )

    # Create new deployment metadata
    metadata = DeploymentMetadata(
        version=DEPLOYMENT_SCHEMA_VERSION,
        deployment_name="Oak Ridge Forest Survey 2024",
        created_at=datetime.now(UTC).isoformat(),
        modified_at=datetime.now(UTC).isoformat(),
        latitude=35.9606,
        longitude=-83.9207,
        location_name="Oak Ridge, TN, USA",
        start_date="2024-06-01",
        end_date="2024-08-31",
        environmental={"temperature_avg_c": 24.5, "humidity_avg_pct": 65},
        mothbox_id="mothbox-001",
        firmware_version="5.2.1",
    )

    # Convert to dictionary for serialization
    data = metadata.to_dict()

    # Create from dictionary
    metadata = DeploymentMetadata.from_dict(data)
"""

import logging
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Schema version and compatibility
DEPLOYMENT_SCHEMA_VERSION = "1.0"  # Current schema version
SUPPORTED_VERSIONS = ["1.0"]  # All supported versions for backward compatibility

# File format and naming
SUPPORTED_FORMATS = ["json", "yaml"]
DEPLOYMENT_FILENAME_JSON = "deployment.json"
DEPLOYMENT_FILENAME_YAML = "deployment.yaml"
BACKUP_EXTENSION = ".bak"

# Validation limits
MAX_DEPLOYMENT_NAME_LENGTH = 200  # Maximum length for deployment_name
MAX_LOCATION_NAME_LENGTH = 500  # Maximum length for location_name
MAX_CUSTOM_KEYS = 100  # Maximum number of keys in custom dict
MAX_CUSTOM_DEPTH = 5  # Maximum nesting depth for custom values

# Geographic coordinate ranges (WGS84)
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


# ============================================================================
# Exceptions
# ============================================================================


class ValidationError(Exception):
    """Raised when deployment metadata validation fails."""


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class DeploymentMetadata:
    """Deployment metadata structure.

    Attributes:
        version: Schema version (currently "1.0")
        deployment_name: Name/description of deployment (required)
        created_at: ISO 8601 timestamp of creation
        modified_at: ISO 8601 timestamp of last modification
        latitude: GPS latitude in decimal degrees (optional, -90.0 to 90.0)
        longitude: GPS longitude in decimal degrees (optional, -180.0 to 180.0)
        altitude: Altitude in meters (optional)
        location_name: Human-readable location description (optional, max 500 chars)
        start_date: Deployment start date (optional, ISO 8601 date YYYY-MM-DD)
        end_date: Deployment end date (optional, ISO 8601 date YYYY-MM-DD)
        environmental: Environmental conditions dictionary (optional)
        mothbox_id: Unique identifier for Mothbox hardware (optional)
        firmware_version: Firmware version string (optional)
        custom: Custom metadata dictionary (optional, max 100 keys)
        modified_by: User identifier for last modification (optional)

    Example:
        >>> metadata = DeploymentMetadata(
        ...     version="1.0",
        ...     deployment_name="Forest Survey 2024",
        ...     created_at="2024-06-01T12:00:00Z",
        ...     modified_at="2024-06-01T12:00:00Z",
        ...     latitude=35.9606,
        ...     longitude=-83.9207,
        ...     location_name="Oak Ridge, TN",
        ...     start_date="2024-06-01",
        ... )
    """

    version: str
    deployment_name: str
    created_at: str
    modified_at: str
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    location_name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    environmental: dict = field(default_factory=dict)
    mothbox_id: str | None = None
    firmware_version: str | None = None
    custom: dict = field(default_factory=dict)
    modified_by: str | None = None

    def to_dict(self) -> dict:
        """Convert metadata to dictionary for JSON/YAML serialization.

        Returns:
            Dictionary representation of deployment metadata with all fields.

        Example:
            >>> metadata = DeploymentMetadata(
            ...     version="1.0",
            ...     deployment_name="Test",
            ...     created_at="2024-01-01T00:00:00Z",
            ...     modified_at="2024-01-01T00:00:00Z",
            ... )
            >>> data = metadata.to_dict()
            >>> isinstance(data, dict)
            True
            >>> data["deployment_name"]
            'Test'
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DeploymentMetadata":
        """Create metadata instance from dictionary.

        Args:
            data: Dictionary with deployment metadata fields. Must contain
                  required fields: version, deployment_name, created_at, modified_at.
                  Optional fields are set to None or default empty dict if not present.

        Returns:
            DeploymentMetadata instance populated from dictionary data.

        Example:
            >>> data = {
            ...     "version": "1.0",
            ...     "deployment_name": "Test Deployment",
            ...     "created_at": "2024-01-01T00:00:00Z",
            ...     "modified_at": "2024-01-01T00:00:00Z",
            ...     "latitude": 35.9606,
            ...     "longitude": -83.9207,
            ... }
            >>> metadata = DeploymentMetadata.from_dict(data)
            >>> metadata.deployment_name
            'Test Deployment'
            >>> metadata.latitude
            35.9606
        """
        return cls(
            version=data["version"],
            deployment_name=data["deployment_name"],
            created_at=data["created_at"],
            modified_at=data["modified_at"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            altitude=data.get("altitude"),
            location_name=data.get("location_name"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            environmental=data.get("environmental", {}),
            mothbox_id=data.get("mothbox_id"),
            firmware_version=data.get("firmware_version"),
            custom=data.get("custom", {}),
            modified_by=data.get("modified_by"),
        )
