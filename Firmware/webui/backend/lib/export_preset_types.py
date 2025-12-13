"""
Export preset type definitions.

This module defines the data structures for export presets:
- ExportPresetCategory: Built-in vs user preset distinction
- ExportPreset: Complete preset configuration with format, filter, and options

Presets allow users to save and reuse export configurations for common
scenarios like GBIF submission, iNaturalist upload, or simple data sharing.

Author: Mothbox Team
Date: 2024
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from webui.backend.lib.export_job_types import ExportJobFilter, ExportJobFormat


class ExportPresetCategory(Enum):
    """
    Export preset category for distinguishing system vs user presets.

    Categories:
        BUILT_IN: System-provided presets, read-only
        USER: User-created presets, can be modified/deleted
    """

    BUILT_IN = "built-in"
    USER = "user"


@dataclass
class ExportPreset:
    """
    Export preset configuration.

    Stores a complete export configuration that can be saved, loaded,
    and applied to export jobs. Includes format, filter criteria,
    and format-specific options.

    Attributes:
        name: Unique identifier (alphanumeric + underscore only)
        display_name: Human-readable name for UI display
        export_format: Export format (DARWIN_CORE, INATURALIST, JSON, CSV)
        description: Purpose and use case description
        version: Schema version for compatibility
        created_at: ISO 8601 timestamp of creation
        author: Creator identifier ("system" for built-in, username for user)
        category: BUILT_IN or USER
        filter: Photo selection criteria
        options: Format-specific export options
    """

    name: str
    display_name: str
    export_format: ExportJobFormat
    description: str = ""
    version: str = "1.0"
    created_at: str = ""
    author: str = "user"
    category: ExportPresetCategory = ExportPresetCategory.USER
    filter: ExportJobFilter = field(default_factory=ExportJobFilter)
    options: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize preset to dictionary.

        Converts enums to string values and nested objects to dicts.
        Suitable for JSON serialization.

        Returns:
            Dictionary with all preset fields
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "export_format": self.export_format.value,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "author": self.author,
            "category": self.category.value,
            "filter": self.filter.to_dict(),
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportPreset:
        """
        Deserialize preset from dictionary.

        Converts string values back to enums and nested dicts to objects.

        Args:
            data: Dictionary with preset fields

        Returns:
            ExportPreset instance

        Raises:
            ValueError: If export_format or category strings are invalid
        """
        # Convert string format to enum
        try:
            export_format = ExportJobFormat(data["export_format"])
        except ValueError as e:
            raise ValueError(f"Invalid export_format value: {data['export_format']}") from e

        # Convert string category to enum (with default)
        category_str = data.get("category", "user")
        try:
            category = ExportPresetCategory(category_str)
        except ValueError as e:
            raise ValueError(f"Invalid category value: {category_str}") from e

        # Deserialize filter if present
        filter_data = data.get("filter", {})
        filter_obj = ExportJobFilter.from_dict(filter_data)

        return cls(
            name=data["name"],
            display_name=data["display_name"],
            export_format=export_format,
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", ""),
            author=data.get("author", "user"),
            category=category,
            filter=filter_obj,
            options=data.get("options", {}),
        )
