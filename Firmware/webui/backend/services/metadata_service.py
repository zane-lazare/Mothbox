"""
Metadata service for extracting photo EXIF data (stub for Issue #100).

This is a temporary stub. The full implementation will come from Issue #99.
For now, it provides basic metadata extraction for testing.
"""

from typing import Dict, Any
from pathlib import Path
import json


class MetadataService:
    """Service for extracting metadata from photos"""

    def get_photo_metadata(self, photo_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from photo.

        This is a stub implementation for testing. The real implementation
        will come from Issue #99 (metadata.py routes and MetadataService).

        Args:
            photo_path: Path to photo file

        Returns:
            Metadata dictionary with camera, location, capture, deployment, file info
        """
        # For now, return basic file info
        # Real implementation will extract EXIF, GPS, etc.
        return {
            "camera": {
                "make": "Unknown",
                "model": "Unknown"
            },
            "location": {},
            "capture": {},
            "deployment": {},
            "file": {
                "path": str(photo_path),
                "size": photo_path.stat().st_size if photo_path.exists() else 0,
                "format": photo_path.suffix.upper().lstrip('.')
            }
        }
