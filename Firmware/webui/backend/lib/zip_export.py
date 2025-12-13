"""
ZIP export library for Mothbox photo collections.

Creates memory-efficient ZIP archives containing:
- Original photos (uncompressed - already JPEG)
- XMP sidecar files ({photo}.xmp) with metadata
- manifest.json with collection metadata
- summary.csv with tabular metadata

Performance target: 50 photos < 5 seconds
"""

import csv
import io
import json
import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final
from zipfile import ZIP_STORED, ZipFile

from webui.backend.lib.xmp_sidecar import generate_xmp_xml, get_xmp_sidecar_filename

if TYPE_CHECKING:
    from webui.backend.services.export_metadata_service import ExportMetadata


# ============================================================================
# Constants
# ============================================================================

ZIP_COMPRESSION_LEVEL: Final[int] = 0  # No compression for JPEGs (already compressed)
ZIP_BUFFER_SIZE: Final[int] = 8192  # 8KB streaming buffer
MAX_ZIP_FILE_SIZE: Final[int] = 2 * 1024 * 1024 * 1024  # 2GB limit
MANIFEST_FILENAME: Final[str] = 'manifest.json'
SUMMARY_FILENAME: Final[str] = 'summary.csv'
GENERATOR_VERSION: Final[str] = '5.0.0'  # Mothbox version


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ZipExportOptions:
    """Configuration for ZIP export."""

    include_xmp_sidecars: bool = True
    include_manifest: bool = True
    include_csv_summary: bool = True  # User confirmed this feature
    compression_level: int = 0  # 0 = no compression (best for JPEGs)
    flatten_structure: bool = False  # If True, all files at root level


@dataclass
class ZipExportResult:
    """Result of ZIP export operation."""

    success: bool
    zip_path: Path | None
    zip_size_bytes: int
    photo_count: int
    xmp_count: int
    errors: list[dict]
    took_ms: float


# ============================================================================
# CSV Summary Generation
# ============================================================================


def generate_csv_summary(metadata_list: list['ExportMetadata']) -> str:
    """Generate summary.csv content.

    Columns: filename, timestamp, latitude, longitude, species, species_common_name, tags

    Args:
        metadata_list: List of ExportMetadata instances

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            'filename',
            'timestamp',
            'latitude',
            'longitude',
            'species',
            'species_common_name',
            'tags',
        ],
    )
    writer.writeheader()

    for metadata in metadata_list:
        # Format tags as semicolon-separated string
        tags_str = ""
        if metadata.tags:
            tags_str = "; ".join(metadata.tags)

        writer.writerow({
            'filename': metadata.filename or "",
            'timestamp': metadata.timestamp or "",
            'latitude': metadata.latitude if metadata.latitude is not None else "",
            'longitude': metadata.longitude if metadata.longitude is not None else "",
            'species': metadata.species or "",
            'species_common_name': metadata.species_common_name or "",
            'tags': tags_str,
        })

    return output.getvalue()


# ============================================================================
# Manifest Generation
# ============================================================================


def generate_manifest(
    photo_paths: list[Path],
    metadata_list: list['ExportMetadata'],
    options: ZipExportOptions,
) -> dict:
    """Generate manifest.json content.

    Structure:
    {
        "version": "1.0",
        "generator": "Mothbox",
        "generator_version": "5.0.0",
        "created_at": "2024-01-15T12:00:00Z",
        "export_format": "inaturalist",
        "options": {...},
        "photo_count": 50,
        "total_size_bytes": 125000000,
        "photos": [
            {
                "filename": "moth_2024_01_15.jpg",
                "xmp_sidecar": "moth_2024_01_15.xmp",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timestamp": "2024-01-15T10:00:00",
                "species": "Actias luna"
            }
        ]
    }

    Args:
        photo_paths: List of photo file paths
        metadata_list: List of ExportMetadata instances
        options: ZipExportOptions instance

    Returns:
        Manifest dictionary
    """
    # Calculate total size of all photos
    total_size_bytes = 0
    for path in photo_paths:
        if path.exists():
            total_size_bytes += path.stat().st_size

    # Build photo entries
    photos = []
    for metadata in metadata_list:
        photo_entry = {
            'filename': metadata.filename,
            'latitude': metadata.latitude,
            'longitude': metadata.longitude,
            'timestamp': metadata.timestamp,
            'species': metadata.species,
        }

        # Add XMP sidecar filename if enabled
        if options.include_xmp_sidecars and metadata.filename:
            xmp_filename = get_xmp_sidecar_filename(metadata.filename)
            photo_entry['xmp_sidecar'] = xmp_filename

        photos.append(photo_entry)

    manifest = {
        'version': '1.0',
        'generator': 'Mothbox',
        'generator_version': GENERATOR_VERSION,
        'created_at': datetime.now(UTC).isoformat(),
        'photo_count': len(metadata_list),
        'total_size_bytes': total_size_bytes,
        'photos': photos,
    }

    return manifest


# ============================================================================
# Add Photo to ZIP
# ============================================================================


def add_photo_to_zip(
    zip_file: ZipFile,
    photo_path: Path,
    metadata: 'ExportMetadata',
    include_xmp: bool = True,
) -> dict:
    """Add photo and optional XMP sidecar to ZIP.

    Args:
        zip_file: ZipFile instance (opened in write mode)
        photo_path: Path to photo file
        metadata: ExportMetadata instance
        include_xmp: Whether to include XMP sidecar

    Returns:
        Dict with: filename, xmp_filename (if generated), size, success, error
    """
    result = {
        'filename': metadata.filename,
        'xmp_filename': None,
        'size': 0,
        'success': False,
    }

    try:
        # Add photo to ZIP
        if not photo_path.exists():
            result['error'] = f"Photo file not found: {photo_path}"
            return result

        # Write photo with no compression (already JPEG)
        zip_file.write(photo_path, arcname=metadata.filename, compress_type=ZIP_STORED)
        result['size'] = photo_path.stat().st_size

        # Generate and add XMP sidecar if requested
        if include_xmp:
            xmp_content = generate_xmp_xml(metadata)
            xmp_filename = get_xmp_sidecar_filename(metadata.filename)
            zip_file.writestr(xmp_filename, xmp_content, compress_type=ZIP_STORED)
            result['xmp_filename'] = xmp_filename

        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


# ============================================================================
# ZIP Integrity Validation
# ============================================================================


def validate_zip_integrity(zip_path: Path) -> bool:
    """Validate ZIP file integrity (can be opened and read).

    Args:
        zip_path: Path to ZIP file

    Returns:
        True if ZIP is valid, False otherwise
    """
    try:
        if not zip_path.exists():
            return False

        with ZipFile(zip_path, 'r') as zf:
            # Test ZIP integrity
            zf.testzip()  # Returns None if OK, filename if error
            return True

    except Exception:
        return False


# ============================================================================
# ZIP Size Estimation
# ============================================================================


def estimate_zip_size(
    photo_paths: list[Path],
    include_xmp: bool = True,
) -> int:
    """Estimate final ZIP size in bytes (for progress/validation).

    Args:
        photo_paths: List of photo file paths
        include_xmp: Whether XMP sidecars will be included

    Returns:
        Estimated ZIP size in bytes
    """
    total_size = 0

    for path in photo_paths:
        try:
            # Add photo size
            total_size += path.stat().st_size

            # Estimate XMP overhead (~2-5KB per file)
            if include_xmp:
                total_size += 3000  # Conservative estimate

        except FileNotFoundError:
            pass  # Skip missing files

    # Add overhead for ZIP structure, manifest, CSV (~5%)
    total_size = int(total_size * 1.05)

    return total_size


# ============================================================================
# Create ZIP Export
# ============================================================================


def create_zip_export(
    photo_paths: list[Path],
    metadata_list: list['ExportMetadata'],
    output_path: Path,
    options: ZipExportOptions | None = None,
) -> ZipExportResult:
    """Create ZIP archive with photos and XMP sidecars.

    Creates a ZIP containing:
    - Original photos (uncompressed - already JPEG)
    - XMP sidecar files ({photo}.xmp) if include_xmp_sidecars=True
    - manifest.json if include_manifest=True
    - summary.csv if include_csv_summary=True

    Args:
        photo_paths: List of photo file paths
        metadata_list: List of ExportMetadata instances
        output_path: Path where ZIP file will be created
        options: ZipExportOptions (uses defaults if None)

    Returns:
        ZipExportResult with success status and statistics
    """
    start_time = time.time()
    options = options or ZipExportOptions()

    photo_count = 0
    xmp_count = 0
    errors = []

    try:
        with ZipFile(output_path, 'w', compression=ZIP_STORED) as zf:
            # Add photos and XMP sidecars
            for photo_path, metadata in zip(photo_paths, metadata_list, strict=True):
                result = add_photo_to_zip(
                    zf, photo_path, metadata, include_xmp=options.include_xmp_sidecars
                )

                if result['success']:
                    photo_count += 1
                    if result['xmp_filename']:
                        xmp_count += 1
                else:
                    errors.append({
                        'filename': metadata.filename,
                        'error': result.get('error', 'Unknown error'),
                    })

            # Add manifest.json
            if options.include_manifest:
                manifest = generate_manifest(photo_paths, metadata_list, options)
                manifest_json = json.dumps(manifest, indent=2)
                zf.writestr(MANIFEST_FILENAME, manifest_json, compress_type=ZIP_STORED)

            # Add summary.csv
            if options.include_csv_summary:
                csv_content = generate_csv_summary(metadata_list)
                zf.writestr(SUMMARY_FILENAME, csv_content, compress_type=ZIP_STORED)

        # Get final ZIP size
        zip_size_bytes = output_path.stat().st_size if output_path.exists() else 0

        # Calculate elapsed time
        took_ms = (time.time() - start_time) * 1000

        return ZipExportResult(
            success=True,
            zip_path=output_path,
            zip_size_bytes=zip_size_bytes,
            photo_count=photo_count,
            xmp_count=xmp_count,
            errors=errors,
            took_ms=took_ms,
        )

    except Exception as e:
        took_ms = (time.time() - start_time) * 1000
        errors.append({'error': str(e)})

        return ZipExportResult(
            success=False,
            zip_path=None,
            zip_size_bytes=0,
            photo_count=photo_count,
            xmp_count=xmp_count,
            errors=errors,
            took_ms=took_ms,
        )


# ============================================================================
# Stream ZIP Export
# ============================================================================


def stream_zip_export(
    photo_paths: list[Path],
    metadata_list: list['ExportMetadata'],
    options: ZipExportOptions | None = None,
) -> Generator[bytes | ZipExportResult]:
    """Stream ZIP archive for HTTP response (memory efficient).

    Yields bytes as ZIP is built, then yields ZipExportResult when done.

    Args:
        photo_paths: List of photo file paths
        metadata_list: List of ExportMetadata instances
        options: ZipExportOptions (uses defaults if None)

    Yields:
        ZIP file bytes in chunks, then ZipExportResult at the end
    """
    start_time = time.time()
    options = options or ZipExportOptions()

    photo_count = 0
    xmp_count = 0
    errors = []
    total_bytes = 0

    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()

    try:
        with ZipFile(zip_buffer, 'w', compression=ZIP_STORED) as zf:
            # Add photos and XMP sidecars
            for photo_path, metadata in zip(photo_paths, metadata_list, strict=True):
                result = add_photo_to_zip(
                    zf, photo_path, metadata, include_xmp=options.include_xmp_sidecars
                )

                if result['success']:
                    photo_count += 1
                    if result['xmp_filename']:
                        xmp_count += 1
                else:
                    errors.append({
                        'filename': metadata.filename,
                        'error': result.get('error', 'Unknown error'),
                    })

            # Add manifest.json
            if options.include_manifest:
                manifest = generate_manifest(photo_paths, metadata_list, options)
                manifest_json = json.dumps(manifest, indent=2)
                zf.writestr(MANIFEST_FILENAME, manifest_json, compress_type=ZIP_STORED)

            # Add summary.csv
            if options.include_csv_summary:
                csv_content = generate_csv_summary(metadata_list)
                zf.writestr(SUMMARY_FILENAME, csv_content, compress_type=ZIP_STORED)

        # Get ZIP content
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
        total_bytes = len(zip_content)

        # Yield ZIP content in chunks
        offset = 0
        while offset < total_bytes:
            chunk = zip_content[offset:offset + ZIP_BUFFER_SIZE]
            yield chunk
            offset += len(chunk)

        # Calculate elapsed time
        took_ms = (time.time() - start_time) * 1000

        # Yield final result
        yield ZipExportResult(
            success=True,
            zip_path=None,  # No file path for streaming
            zip_size_bytes=total_bytes,
            photo_count=photo_count,
            xmp_count=xmp_count,
            errors=errors,
            took_ms=took_ms,
        )

    except Exception as e:
        took_ms = (time.time() - start_time) * 1000
        errors.append({'error': str(e)})

        yield ZipExportResult(
            success=False,
            zip_path=None,
            zip_size_bytes=total_bytes,
            photo_count=photo_count,
            xmp_count=xmp_count,
            errors=errors,
            took_ms=took_ms,
        )
