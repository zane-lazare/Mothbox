"""
iNaturalist Field Mapping Module for Mothbox Photo Gallery (Issue #118)

Provides field definitions, mappings, and utilities for transforming
Mothbox photo metadata to iNaturalist-compatible format with XMP sidecar support.

iNaturalist is a citizen science platform for biodiversity observations.
This module enables exporting Mothbox photos to iNaturalist with rich metadata
including taxonomy, location, quality grades, and observation notes.

Reference: https://www.inaturalist.org/pages/developers

Usage:
    from webui.backend.lib.inaturalist_mapping import (
        transform_metadata_to_inaturalist,
        validate_for_inaturalist,
        format_observation_title,
        build_taxonomy_keywords,
    )

    # Transform ExportMetadata to iNaturalist dict
    inat_record = transform_metadata_to_inaturalist(export_metadata)

    # Validate metadata for iNaturalist export
    validation = validate_for_inaturalist(export_metadata)

    # Format observation title for taxon parsing
    title = format_observation_title(export_metadata)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from webui.backend.services.export_metadata_service import ExportMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Required fields for iNaturalist export
INATURALIST_REQUIRED_FIELDS = ["latitude", "longitude", "timestamp"]

# Recommended fields for complete observations
INATURALIST_RECOMMENDED_FIELDS = [
    "species",
    "species_common_name",
    "species_confidence",
    "notes",
]

# Species confidence to iNaturalist quality grade mapping
# Reference: https://www.inaturalist.org/pages/help#quality
CONFIDENCE_TO_QUALITY_GRADE = {
    "certain": "research",      # High confidence, research grade quality
    "probable": "needs_id",     # Likely correct, community ID needed
    "possible": "needs_id",     # Possible match, needs verification
    "unknown": "casual",        # Low quality/casual observation
}

# Taxonomy keyword prefix following Naturtag pattern
# Reference: https://github.com/pyinat/naturtag
TAXONOMY_KEYWORD_PREFIX = "taxonomy:"

# Default values for iNaturalist fields
DEFAULT_LICENSE = "CC BY-NC 4.0"  # Creative Commons Attribution-NonCommercial
DEFAULT_CREATOR = "Mothbox"       # Default observer/creator
DEFAULT_QUALITY_GRADE = "needs_id"  # Default when confidence unknown


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class INaturalistFieldMapping:
    """Definition for iNaturalist field mapping.

    Attributes:
        inat_field: iNaturalist field name (e.g., "latitude", "species")
        source_field: ExportMetadata field name or None for computed/constant
        default_value: Default value if source is None
        is_required: Whether this field is required for iNaturalist
        xmp_field: XMP namespace field (e.g., "exif:GPSLatitude") for sidecar
        description: Human-readable description of the field
    """
    inat_field: str
    source_field: str | None
    default_value: Any
    is_required: bool
    xmp_field: str | None
    description: str


@dataclass
class ValidationResult:
    """Result of iNaturalist export validation.

    Attributes:
        is_valid: Whether metadata is valid for iNaturalist export
        missing_required: List of required fields that are missing
        missing_recommended: List of recommended fields that are missing
        warnings: List of validation warnings (non-fatal issues)
    """
    is_valid: bool
    missing_required: list[str] = field(default_factory=list)
    missing_recommended: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ============================================================================
# Helper Functions
# ============================================================================

def map_species_confidence_to_quality_grade(confidence: str | None) -> str:
    """Map Mothbox species confidence to iNaturalist quality grade.

    iNaturalist uses quality grades to indicate observation confidence:
    - research: High-quality observations with community consensus
    - needs_id: Observations needing community identification
    - casual: Low-quality or incomplete observations

    Args:
        confidence: Mothbox confidence value ("certain", "probable", "possible", "unknown")

    Returns:
        iNaturalist quality grade string

    Example:
        >>> map_species_confidence_to_quality_grade("certain")
        'research'
        >>> map_species_confidence_to_quality_grade("probable")
        'needs_id'
    """
    if confidence is None:
        return DEFAULT_QUALITY_GRADE

    return CONFIDENCE_TO_QUALITY_GRADE.get(confidence.lower(), DEFAULT_QUALITY_GRADE)


def build_taxonomy_keywords(species: str | None) -> list[str]:
    """Build hierarchical taxonomy keywords from species name.

    Follows the Naturtag keyword pattern for iNaturalist compatibility.
    Keywords enable hierarchical filtering and searching in photo management software.

    For moths/butterflies (Lepidoptera), generates:
    - taxonomy:kingdom=Animalia
    - taxonomy:phylum=Arthropoda
    - taxonomy:class=Insecta
    - taxonomy:order=Lepidoptera
    - taxonomy:genus=<Genus>
    - taxonomy:species=<Genus species>

    Args:
        species: Scientific name (e.g., "Actias luna")

    Returns:
        List of taxonomy keyword strings

    Example:
        >>> build_taxonomy_keywords("Actias luna")
        ['taxonomy:kingdom=Animalia', 'taxonomy:phylum=Arthropoda', ..., 'taxonomy:species=Actias luna']
    """
    if not species:
        return []

    # Clean species name (remove author citations like "(Linnaeus, 1758)")
    species_clean = re.sub(r'\s*\([^)]*\)\s*$', '', species).strip()

    if not species_clean:
        return []

    keywords = []

    # Fixed taxonomy for Lepidoptera (moth/butterfly)
    # All Mothbox observations are assumed to be insects
    keywords.extend([
        f"{TAXONOMY_KEYWORD_PREFIX}kingdom=Animalia",
        f"{TAXONOMY_KEYWORD_PREFIX}phylum=Arthropoda",
        f"{TAXONOMY_KEYWORD_PREFIX}class=Insecta",
        f"{TAXONOMY_KEYWORD_PREFIX}order=Lepidoptera",
    ])

    # Parse genus and species from binomial/trinomial name
    parts = species_clean.split()

    if len(parts) >= 1:
        # Genus
        genus = parts[0]
        keywords.append(f"{TAXONOMY_KEYWORD_PREFIX}genus={genus}")

    if len(parts) >= 2:
        # Species (binomial)
        species_binomial = f"{parts[0]} {parts[1]}"
        keywords.append(f"{TAXONOMY_KEYWORD_PREFIX}species={species_binomial}")

    # Note: Subspecies (trinomial) could be added here if needed
    # if len(parts) >= 3:
    #     species_trinomial = f"{parts[0]} {parts[1]} {parts[2]}"
    #     keywords.append(f"{TAXONOMY_KEYWORD_PREFIX}subspecies={species_trinomial}")

    return keywords


def format_observation_title(metadata: "ExportMetadata") -> str:
    """Format observation title for iNaturalist taxon parsing.

    iNaturalist can parse taxon names from photo titles to automatically
    suggest species identifications. Format follows pattern:
    - "Common Name (Scientific Name)" if both available
    - "Scientific Name" if only species available
    - "Common Name" if only common name available
    - "Unknown" if neither available

    Args:
        metadata: ExportMetadata instance

    Returns:
        Formatted title string

    Example:
        >>> format_observation_title(metadata_with_both)
        'Luna Moth (Actias luna)'
        >>> format_observation_title(metadata_species_only)
        'Actias luna'
    """
    species = metadata.species
    common_name = metadata.species_common_name

    if species and common_name:
        return f"{common_name} ({species})"
    elif species:
        return species
    elif common_name:
        return common_name
    else:
        return "Unknown"


def format_observation_notes(metadata: "ExportMetadata") -> str:
    """Combine notes, tags, and deployment info into observation notes.

    Formats comprehensive observation notes from available metadata:
    - User notes (if present)
    - Tags as comma-separated list (if present)
    - Deployment information (if present)

    Args:
        metadata: ExportMetadata instance

    Returns:
        Formatted notes string

    Example:
        >>> format_observation_notes(metadata)
        'Beautiful specimen\\n\\nTags: nocturnal, lepidoptera\\n\\nDeployment: oak-ridge-2024'
    """
    parts = []

    # User notes
    if metadata.notes:
        parts.append(metadata.notes)

    # Tags
    if metadata.tags:
        tags_str = ", ".join(metadata.tags)
        parts.append(f"Tags: {tags_str}")

    # Deployment information
    deployment_info = []
    if metadata.deployment_name:
        deployment_info.append(f"Deployment: {metadata.deployment_name}")
    if metadata.deployment_location_name:
        deployment_info.append(f"Location: {metadata.deployment_location_name}")

    if deployment_info:
        parts.append("\n".join(deployment_info))

    return "\n\n".join(parts)


def get_xmp_field_mappings() -> dict[str, str]:
    """Return mapping of iNaturalist fields to XMP fields.

    Maps iNaturalist field names to XMP namespace fields for sidecar generation.
    Supports Dublin Core (dc:), XMP (xmp:), EXIF (exif:), and IPTC namespaces.

    Returns:
        Dictionary mapping iNaturalist field -> XMP field

    Example:
        >>> mappings = get_xmp_field_mappings()
        >>> mappings["latitude"]
        'exif:GPSLatitude'
        >>> mappings["title"]
        'dc:title'
    """
    return {
        # Location fields (EXIF GPS namespace)
        "latitude": "exif:GPSLatitude",
        "longitude": "exif:GPSLongitude",
        "altitude": "exif:GPSAltitude",

        # Title and description (Dublin Core)
        "title": "dc:title",
        "notes": "dc:description",

        # Creator/observer (Dublin Core)
        "creator": "dc:creator",

        # Keywords/tags (Dublin Core)
        "keywords": "dc:subject",

        # License (XMP Rights)
        "license": "xmpRights:UsageTerms",

        # Timestamp (XMP)
        "timestamp": "xmp:CreateDate",

        # Species (IPTC Extension)
        "species": "Iptc4xmpExt:TaxonomicName",
    }


def transform_metadata_to_inaturalist(metadata: "ExportMetadata") -> dict[str, Any]:
    """Transform ExportMetadata to iNaturalist-compatible dict.

    Maps all available Mothbox metadata fields to iNaturalist equivalents,
    applying transformations where necessary (quality grade, taxonomy keywords,
    formatted title/notes).

    Args:
        metadata: ExportMetadata instance to transform

    Returns:
        Dictionary with iNaturalist field names as keys

    Example:
        >>> inat = transform_metadata_to_inaturalist(metadata)
        >>> inat["latitude"]
        37.7749
        >>> inat["quality_grade"]
        'research'
    """
    result: dict[str, Any] = {}

    # Required fields
    result["latitude"] = metadata.latitude
    result["longitude"] = metadata.longitude
    result["timestamp"] = metadata.timestamp

    # Species fields
    result["species"] = metadata.species or ""
    result["common_name"] = metadata.species_common_name or ""

    # Quality grade (mapped from confidence)
    result["quality_grade"] = map_species_confidence_to_quality_grade(
        metadata.species_confidence
    )

    # Formatted fields
    result["title"] = format_observation_title(metadata)
    result["notes"] = format_observation_notes(metadata)

    # Keywords (taxonomy + tags)
    keywords = build_taxonomy_keywords(metadata.species)
    if metadata.tags:
        keywords.extend(metadata.tags)
    result["keywords"] = keywords

    # License and creator
    result["license"] = DEFAULT_LICENSE
    result["creator"] = DEFAULT_CREATOR

    # Optional location fields
    if metadata.altitude is not None:
        result["altitude"] = metadata.altitude
    if metadata.gps_accuracy is not None:
        result["gps_accuracy"] = metadata.gps_accuracy

    # Observer (from deployment modified_by or default)
    result["observer"] = DEFAULT_CREATOR

    # Photo file info
    result["filename"] = metadata.filename

    return result


def is_valid_for_inaturalist_export(metadata: "ExportMetadata") -> bool:
    """Quick check if metadata has required fields for iNaturalist.

    Validates that GPS coordinates and timestamp are present and valid.

    Args:
        metadata: ExportMetadata instance to validate

    Returns:
        True if metadata can be exported, False otherwise

    Example:
        >>> is_valid_for_inaturalist_export(metadata_with_gps)
        True
        >>> is_valid_for_inaturalist_export(metadata_without_gps)
        False
    """
    # GPS coordinates required
    if metadata.latitude is None or metadata.longitude is None:
        return False

    # Timestamp required
    if not metadata.timestamp:
        return False

    # Validate coordinate ranges
    if not (-90 <= metadata.latitude <= 90):
        return False

    return -180 <= metadata.longitude <= 180


def validate_for_inaturalist(metadata: "ExportMetadata") -> ValidationResult:
    """Comprehensive validation with missing fields and warnings.

    Validates metadata against iNaturalist requirements and recommendations.
    Returns detailed validation result with missing required/recommended fields
    and warnings.

    Args:
        metadata: ExportMetadata instance to validate

    Returns:
        ValidationResult with validation status and details

    Example:
        >>> result = validate_for_inaturalist(metadata)
        >>> result.is_valid
        True
        >>> result.missing_recommended
        ['species_common_name']
    """
    missing_required = []
    missing_recommended = []
    warnings = []

    # Check required fields
    if metadata.latitude is None:
        missing_required.append("latitude")
    elif not (-90 <= metadata.latitude <= 90):
        missing_required.append("latitude (invalid range)")

    if metadata.longitude is None:
        missing_required.append("longitude")
    elif not (-180 <= metadata.longitude <= 180):
        missing_required.append("longitude (invalid range)")

    if not metadata.timestamp:
        missing_required.append("timestamp")

    # Check recommended fields
    if not metadata.species:
        missing_recommended.append("species")

    if not metadata.species_common_name:
        missing_recommended.append("species_common_name")

    if not metadata.species_confidence:
        warnings.append("species_confidence not set, defaulting to 'needs_id'")

    if not metadata.notes and not metadata.tags:
        warnings.append("No notes or tags provided")

    # Determine validity
    is_valid = len(missing_required) == 0

    return ValidationResult(
        is_valid=is_valid,
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        warnings=warnings,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Constants
    "INATURALIST_REQUIRED_FIELDS",
    "INATURALIST_RECOMMENDED_FIELDS",
    "CONFIDENCE_TO_QUALITY_GRADE",
    "TAXONOMY_KEYWORD_PREFIX",
    "DEFAULT_LICENSE",
    "DEFAULT_CREATOR",
    # Data classes
    "INaturalistFieldMapping",
    "ValidationResult",
    # Functions
    "map_species_confidence_to_quality_grade",
    "build_taxonomy_keywords",
    "format_observation_title",
    "format_observation_notes",
    "get_xmp_field_mappings",
    "transform_metadata_to_inaturalist",
    "is_valid_for_inaturalist_export",
    "validate_for_inaturalist",
]
