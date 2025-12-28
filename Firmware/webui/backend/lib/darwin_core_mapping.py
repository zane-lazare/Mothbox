"""
Darwin Core Field Mapping Module for Mothbox Photo Gallery (Issue #116)

Provides field definitions, mappings, and utilities for transforming
Mothbox photo metadata to GBIF-compatible Darwin Core format.

Darwin Core (DwC) is a standard maintained by TDWG (Biodiversity Information
Standards) for sharing biodiversity occurrence data.

Reference: https://dwc.tdwg.org/terms/

Usage:
    from webui.backend.lib.darwin_core_mapping import (
        DARWIN_CORE_FIELD_MAPPINGS,
        generate_occurrence_id,
        map_species_confidence_to_qualifier,
        get_csv_headers,
        transform_metadata_to_darwin_core,
    )

    # Transform ExportMetadata to Darwin Core dict
    dwc_record = transform_metadata_to_darwin_core(export_metadata)

    # Get CSV headers in standard order
    headers = get_csv_headers()

    # Generate unique occurrence ID
    occ_id = generate_occurrence_id(export_metadata)
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from webui.backend.services.export_metadata_service import ExportMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Darwin Core terms required for GBIF submission
DARWIN_CORE_REQUIRED_FIELDS = [
    "occurrenceID",
    "basisOfRecord",
    "eventDate",
    "decimalLatitude",
    "decimalLongitude",
    "geodeticDatum",
]

# Darwin Core terms recommended for complete records
DARWIN_CORE_RECOMMENDED_FIELDS = [
    "scientificName",
    "countryCode",
    "recordedBy",
    "occurrenceStatus",
    "coordinateUncertaintyInMeters",
    "identificationQualifier",
    "vernacularName",
    "associatedMedia",
]

# All Darwin Core terms in CSV export order
DARWIN_CORE_CSV_COLUMN_ORDER = [
    # Required fields first
    "occurrenceID",
    "basisOfRecord",
    "eventDate",
    "decimalLatitude",
    "decimalLongitude",
    "geodeticDatum",
    # Taxonomy
    "scientificName",
    "vernacularName",
    "identificationQualifier",
    # Location
    "countryCode",
    "coordinateUncertaintyInMeters",
    # Occurrence
    "occurrenceStatus",
    "recordedBy",
    # Media
    "associatedMedia",
    # Device/deployment (Darwin Core extensions)
    "institutionCode",
    "collectionCode",
    "catalogNumber",
]

# Constant values for Darwin Core fields
DARWIN_CORE_CONSTANTS = {
    "basisOfRecord": "MachineObservation",  # Camera trap observation
    "geodeticDatum": "WGS84",  # GPS coordinate reference system
    "occurrenceStatus": "present",  # All photos represent presence
    "institutionCode": "Mothbox",  # Device identifier
}

# Species confidence to Darwin Core identification qualifier mapping
# Reference: https://dwc.tdwg.org/terms/#dwc:identificationQualifier
CONFIDENCE_TO_QUALIFIER = {
    "certain": "",  # No qualifier needed for confident IDs
    "probable": "cf.",  # confer - compare with (similar to)
    "possible": "aff.",  # affinis - affinity with (related to)
    "unknown": "?",  # Uncertain identification
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DarwinCoreFieldMapping:
    """Configuration for mapping a Mothbox field to Darwin Core term.

    Attributes:
        dwc_term: Darwin Core term name (e.g., "decimalLatitude")
        source_field: ExportMetadata field name or None for computed/constant
        default_value: Default value if source is None
        is_required: Whether this field is required for GBIF
        description: Human-readable description of the field
    """
    dwc_term: str
    source_field: str | None
    default_value: Any
    is_required: bool
    description: str


# Complete field mapping configuration
DARWIN_CORE_FIELD_MAPPINGS: list[DarwinCoreFieldMapping] = [
    # Required fields
    DarwinCoreFieldMapping(
        dwc_term="occurrenceID",
        source_field=None,  # Computed
        default_value="",
        is_required=True,
        description="Unique identifier for this occurrence (computed from deployment + filename hash)"
    ),
    DarwinCoreFieldMapping(
        dwc_term="basisOfRecord",
        source_field=None,  # Constant
        default_value="MachineObservation",
        is_required=True,
        description="Type of record - MachineObservation for camera trap photos"
    ),
    DarwinCoreFieldMapping(
        dwc_term="eventDate",
        source_field="timestamp",
        default_value="",
        is_required=True,
        description="Date/time of the observation in ISO 8601 format"
    ),
    DarwinCoreFieldMapping(
        dwc_term="decimalLatitude",
        source_field="latitude",
        default_value=None,
        is_required=True,
        description="GPS latitude in decimal degrees (-90 to 90)"
    ),
    DarwinCoreFieldMapping(
        dwc_term="decimalLongitude",
        source_field="longitude",
        default_value=None,
        is_required=True,
        description="GPS longitude in decimal degrees (-180 to 180)"
    ),
    DarwinCoreFieldMapping(
        dwc_term="geodeticDatum",
        source_field=None,  # Constant
        default_value="WGS84",
        is_required=True,
        description="Coordinate reference system - WGS84 for GPS"
    ),
    # Taxonomy fields
    DarwinCoreFieldMapping(
        dwc_term="scientificName",
        source_field="species",
        default_value="",
        is_required=False,
        description="Scientific name of the species"
    ),
    DarwinCoreFieldMapping(
        dwc_term="vernacularName",
        source_field="species_common_name",
        default_value="",
        is_required=False,
        description="Common name of the species"
    ),
    DarwinCoreFieldMapping(
        dwc_term="identificationQualifier",
        source_field="species_confidence",  # Transformed
        default_value="",
        is_required=False,
        description="Qualifier for species identification (cf., aff., ?)"
    ),
    # Location fields
    DarwinCoreFieldMapping(
        dwc_term="countryCode",
        source_field="country_code",  # Populated via geopip from GPS coordinates
        default_value="",
        is_required=False,
        description="ISO 3166-1 alpha-2 country code"
    ),
    DarwinCoreFieldMapping(
        dwc_term="coordinateUncertaintyInMeters",
        source_field="gps_accuracy",
        default_value=None,
        is_required=False,
        description="GPS accuracy in meters"
    ),
    # Occurrence fields
    DarwinCoreFieldMapping(
        dwc_term="occurrenceStatus",
        source_field=None,  # Constant
        default_value="present",
        is_required=False,
        description="Presence/absence - always 'present' for photos"
    ),
    DarwinCoreFieldMapping(
        dwc_term="recordedBy",
        source_field=None,  # Uses deployment modified_by or "Mothbox"
        default_value="Mothbox",
        is_required=False,
        description="Person or device that recorded the observation"
    ),
    # Media fields
    DarwinCoreFieldMapping(
        dwc_term="associatedMedia",
        source_field="photo_path",
        default_value="",
        is_required=False,
        description="Path or URL to the photo file"
    ),
    # Device/deployment fields (Darwin Core extensions)
    DarwinCoreFieldMapping(
        dwc_term="institutionCode",
        source_field=None,  # Constant
        default_value="Mothbox",
        is_required=False,
        description="Institution/device identifier"
    ),
    DarwinCoreFieldMapping(
        dwc_term="collectionCode",
        source_field="deployment_name",
        default_value="",
        is_required=False,
        description="Deployment/collection identifier"
    ),
    DarwinCoreFieldMapping(
        dwc_term="catalogNumber",
        source_field="filename",
        default_value="",
        is_required=False,
        description="Unique identifier within the collection (filename)"
    ),
]


# ============================================================================
# Helper Functions
# ============================================================================

def generate_occurrence_id(metadata: "ExportMetadata") -> str:
    """Generate a unique, deterministic occurrence ID for Darwin Core.

    Format: mothbox:{deployment_name}:{filename_hash}

    The ID is deterministic - the same metadata will always produce
    the same ID, enabling consistent exports and updates.

    Args:
        metadata: ExportMetadata instance with deployment_name and filename

    Returns:
        Unique occurrence ID string

    Example:
        >>> generate_occurrence_id(metadata)
        'mothbox:oak-ridge-2024:a1b2c3d4'
    """
    # Use deployment name if available, otherwise "unknown"
    deployment = metadata.deployment_name or "unknown"

    # Sanitize deployment name (replace spaces, special chars)
    deployment = deployment.lower().replace(" ", "-")
    deployment = "".join(c for c in deployment if c.isalnum() or c == "-")

    # Generate hash from deployment + filename for uniqueness
    hash_input = f"{deployment}:{metadata.filename}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    return f"mothbox:{deployment}:{hash_digest}"


def map_species_confidence_to_qualifier(confidence: str | None) -> str:
    """Map Mothbox species confidence to Darwin Core identification qualifier.

    Darwin Core uses specific qualifiers to indicate certainty:
    - (empty): Confident identification
    - cf.: "compare with" - similar to but not certain
    - aff.: "affinity with" - related to but distinct
    - ?: Uncertain

    Args:
        confidence: Mothbox confidence value ("certain", "probable", "possible", "unknown")

    Returns:
        Darwin Core identification qualifier string

    Example:
        >>> map_species_confidence_to_qualifier("probable")
        'cf.'
        >>> map_species_confidence_to_qualifier("certain")
        ''
    """
    if confidence is None:
        return ""
    return CONFIDENCE_TO_QUALIFIER.get(confidence.lower(), "")


def get_csv_headers() -> list[str]:
    """Get Darwin Core CSV column headers in standard order.

    Returns headers in the order defined by DARWIN_CORE_CSV_COLUMN_ORDER,
    which places required fields first followed by recommended fields.

    Returns:
        List of Darwin Core term names for CSV header row

    Example:
        >>> headers = get_csv_headers()
        >>> headers[0]
        'occurrenceID'
    """
    return DARWIN_CORE_CSV_COLUMN_ORDER.copy()


def _apply_gps_precision(
    value: float | None,
    precision: int | None
) -> float | None:
    """Apply GPS precision rounding to a coordinate value.

    Args:
        value: Coordinate value (latitude or longitude)
        precision: Number of decimal places (0-6), None for no rounding

    Returns:
        Rounded coordinate or original if precision is None
    """
    if value is None or precision is None:
        return value
    return round(value, precision)


def transform_metadata_to_darwin_core(
    metadata: "ExportMetadata",
    gps_precision: int | None = None,
) -> dict[str, Any]:
    """Transform ExportMetadata to Darwin Core record.

    Maps all available Mothbox metadata fields to their Darwin Core
    equivalents, applying transformations where necessary.

    Args:
        metadata: ExportMetadata instance to transform
        gps_precision: Number of decimal places for GPS coordinates (0-6),
                      None for full precision

    Returns:
        Dictionary with Darwin Core term names as keys

    Example:
        >>> dwc = transform_metadata_to_darwin_core(metadata)
        >>> dwc["basisOfRecord"]
        'MachineObservation'
        >>> dwc["decimalLatitude"]
        37.7749
    """
    result: dict[str, Any] = {}

    for mapping in DARWIN_CORE_FIELD_MAPPINGS:
        dwc_term = mapping.dwc_term

        # Handle computed/constant fields
        if mapping.source_field is None:
            if dwc_term == "occurrenceID":
                result[dwc_term] = generate_occurrence_id(metadata)
            elif dwc_term == "recordedBy":
                # Use modified_by from deployment if available
                # Note: modified_by is not currently in ExportMetadata,
                # so we default to "Mothbox"
                result[dwc_term] = mapping.default_value
            else:
                # Use constant value
                result[dwc_term] = mapping.default_value
        else:
            # Get value from source field
            value = getattr(metadata, mapping.source_field, None)

            # Apply transformations
            if dwc_term == "identificationQualifier":
                value = map_species_confidence_to_qualifier(value)
            elif dwc_term == "decimalLatitude" or dwc_term == "decimalLongitude":
                value = _apply_gps_precision(value, gps_precision)

            # Use default if None
            if value is None:
                value = mapping.default_value

            result[dwc_term] = value

    return result


def transform_to_csv_row(
    metadata: "ExportMetadata",
    gps_precision: int | None = None,
) -> list[str]:
    """Transform ExportMetadata to a CSV row.

    Returns values in the order defined by get_csv_headers().
    All values are converted to strings for CSV output.

    Args:
        metadata: ExportMetadata instance to transform
        gps_precision: Number of decimal places for GPS coordinates (0-6),
                      None for full precision

    Returns:
        List of string values in CSV column order

    Example:
        >>> row = transform_to_csv_row(metadata)
        >>> len(row) == len(get_csv_headers())
        True
    """
    dwc_record = transform_metadata_to_darwin_core(metadata, gps_precision=gps_precision)
    headers = get_csv_headers()

    row = []
    for header in headers:
        value = dwc_record.get(header, "")
        # Convert to string, handling None
        if value is None:
            row.append("")
        else:
            row.append(str(value))

    return row


def is_valid_for_export(metadata: "ExportMetadata") -> bool:
    """Check if metadata has required fields for Darwin Core export.

    Validates that GPS coordinates are present (GBIF strict mode).

    Args:
        metadata: ExportMetadata instance to validate

    Returns:
        True if metadata can be exported, False otherwise

    Example:
        >>> is_valid_for_export(metadata_with_gps)
        True
        >>> is_valid_for_export(metadata_without_gps)
        False
    """
    # GPS coordinates required (GBIF strict mode)
    if metadata.latitude is None or metadata.longitude is None:
        return False

    # Validate coordinate ranges
    if not (-90 <= metadata.latitude <= 90):
        return False

    return -180 <= metadata.longitude <= 180


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Constants
    "DARWIN_CORE_REQUIRED_FIELDS",
    "DARWIN_CORE_RECOMMENDED_FIELDS",
    "DARWIN_CORE_CSV_COLUMN_ORDER",
    "DARWIN_CORE_CONSTANTS",
    "CONFIDENCE_TO_QUALIFIER",
    # Data classes
    "DarwinCoreFieldMapping",
    "DARWIN_CORE_FIELD_MAPPINGS",
    # Functions
    "generate_occurrence_id",
    "map_species_confidence_to_qualifier",
    "get_csv_headers",
    "transform_metadata_to_darwin_core",
    "transform_to_csv_row",
    "is_valid_for_export",
]
