#!/usr/bin/env python3
"""
GPS EXIF Batch Tagging Tool for Mothbox Photos

Batch tags multiple photos with GPS EXIF data. Supports:
- Reading GPS from controls.txt or manual override
- Date-based filtering (--after, --before)
- Recursive directory scanning
- Dry-run mode for testing
- Backup creation before modification

Usage:
    # Tag all photos in directory with current GPS from controls.txt
    ./batch_tag_photos.py /photos/

    # Tag with manual GPS coordinates
    ./batch_tag_photos.py /photos/ --lat 37.7749 --lon -122.4194

    # Tag photos from specific date range
    ./batch_tag_photos.py /photos/ --after 2025-01-15 --before 2025-01-20

    # Dry run (test without modifying)
    ./batch_tag_photos.py /photos/ --dry-run

    # Create backups before tagging
    ./batch_tag_photos.py /photos/ --backup

    # Recursive scan
    ./batch_tag_photos.py /photos/ --recursive

Related:
- Issue #98 Phase 3: Batch Tagging Tool (Days 4-7)
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
- Library: lib/gps_exif_lib.py
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import GPS EXIF library functions
from lib.gps_exif_lib import embed_gps_exif, get_gps_data_from_controls, is_already_tagged

# Import verification tool functions
from scripts.verify_gps_exif import extract_timestamp_from_filename


def filter_photos_by_date(
    photos: list[Path],
    after: datetime | None = None,
    before: datetime | None = None
) -> list[Path]:
    """
    Filter photos by date range based on filename timestamps.

    Extracts timestamps from Mothbox photo filenames and filters based on
    --after and --before date constraints.

    Args:
        photos: List of photo paths to filter
        after: Include photos on or after this date (inclusive)
        before: Include photos before this date (exclusive)

    Returns:
        list: Filtered list of photo paths

    Examples:
        >>> photos = [Path("mothbox_2025_01_15__12_00_00.jpg"),
        ...           Path("mothbox_2025_01_16__12_00_00.jpg")]
        >>> filter_photos_by_date(photos, after=datetime(2025, 1, 16))
        [Path("mothbox_2025_01_16__12_00_00.jpg")]

    Implementation:
        - Extracts timestamp from filename using extract_timestamp_from_filename()
        - Filters out photos with invalid/missing timestamps
        - Applies date range filters if provided
        - Preserves original order of photos
    """
    filtered = []

    for photo in photos:
        # Extract timestamp from filename
        timestamp = extract_timestamp_from_filename(photo)

        # Skip photos with invalid filenames
        if timestamp is None:
            continue

        # Apply date filters
        if after is not None and timestamp < after:
            continue

        if before is not None and timestamp >= before:
            continue

        filtered.append(photo)

    return filtered


def validate_gps_override(
    latitude: float | None,
    longitude: float | None
) -> bool:
    """
    Validate GPS coordinate override values.

    Checks that latitude and longitude are within valid ranges:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees

    Args:
        latitude: Latitude in decimal degrees (or None)
        longitude: Longitude in decimal degrees (or None)

    Returns:
        bool: True if coordinates are valid, False otherwise

    Examples:
        >>> validate_gps_override(37.7749, -122.4194)
        True

        >>> validate_gps_override(100, 0)  # Invalid latitude
        False

        >>> validate_gps_override(0, None)  # Missing longitude
        False

    Implementation:
        - Checks for None values
        - Validates latitude range (-90 to 90)
        - Validates longitude range (-180 to 180)
    """
    # Check for None values
    if latitude is None or longitude is None:
        return False

    # Validate latitude range
    if latitude < -90 or latitude > 90:
        return False

    # Validate longitude range
    return not (longitude < -180 or longitude > 180)


def batch_tag_with_override(
    photos: list[Path],
    controls_file: Path | None = None,
    override_lat: float | None = None,
    override_lon: float | None = None,
    dry_run: bool = False,
    backup: bool = False
) -> dict[str, int]:
    """
    Batch tag photos with GPS EXIF data.

    Tags multiple photos with GPS EXIF metadata. GPS data can come from:
    1. Manual override (--lat/--lon) - takes priority
    2. controls.txt file (default)

    Args:
        photos: List of photo paths to tag
        controls_file: Path to controls.txt (or None for default)
        override_lat: Manual latitude override
        override_lon: Manual longitude override
        dry_run: If True, don't actually modify photos
        backup: If True, create .bak files before modifying

    Returns:
        dict: Statistics with keys:
            - total: Total photos processed
            - tagged: Number of photos tagged
            - skipped: Number of photos skipped (already tagged)
            - errors: Number of errors

    Example:
        >>> photos = [Path("photo1.jpg"), Path("photo2.jpg")]
        >>> results = batch_tag_with_override(photos, override_lat=37.7749, override_lon=-122.4194)
        >>> print(f"Tagged {results['tagged']} of {results['total']} photos")

    Implementation:
        - Determines GPS source (manual override or controls.txt)
        - Skips photos already tagged (idempotent)
        - Handles errors gracefully (continues processing remaining photos)
        - Reports statistics for user feedback
    """
    # Initialize statistics
    stats = {
        'total': len(photos),
        'tagged': 0,
        'skipped': 0,
        'errors': 0
    }

    # Determine GPS data source
    if override_lat is not None and override_lon is not None:
        # Manual override
        gps_data = {
            'latitude': override_lat,
            'longitude': override_lon,
            'has_fix': True
        }
    else:
        # Read from controls.txt
        gps_data = get_gps_data_from_controls(controls_file)

        # Check if GPS has valid fix
        if not gps_data.get('has_fix', False):
            print("❌ No GPS fix available in controls.txt")
            return stats

    # Process each photo
    for photo in photos:
        try:
            # Skip if already tagged (idempotent)
            if is_already_tagged(photo):
                stats['skipped'] += 1
                continue

            # Embed GPS EXIF
            result = embed_gps_exif(
                photo,
                gps_data=gps_data,
                backup=backup,
                dry_run=dry_run
            )

            if result['success']:
                stats['tagged'] += 1
            elif result['skipped']:
                stats['skipped'] += 1
            else:
                stats['errors'] += 1
                print(f"⚠️  Error tagging {photo.name}: {result.get('error', 'Unknown error')}")

        except Exception as e:
            stats['errors'] += 1
            print(f"⚠️  Error processing {photo.name}: {str(e)}")

    return stats


def batch_tag_directory(
    directory: Path,
    controls_file: Path | None = None,
    override_lat: float | None = None,
    override_lon: float | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    recursive: bool = False,
    dry_run: bool = False,
    backup: bool = False
) -> dict[str, int]:
    """
    Batch tag all photos in a directory.

    Scans directory for JPEG files and tags them with GPS EXIF data.
    Supports recursive scanning and date-based filtering.

    Args:
        directory: Directory to scan for photos
        controls_file: Path to controls.txt (or None for default)
        override_lat: Manual latitude override
        override_lon: Manual longitude override
        after: Include photos on or after this date
        before: Include photos before this date
        recursive: If True, scan subdirectories recursively
        dry_run: If True, don't actually modify photos
        backup: If True, create .bak files before modifying

    Returns:
        dict: Statistics from batch_tag_with_override()

    Example:
        >>> results = batch_tag_directory(
        ...     Path("/photos"),
        ...     override_lat=37.7749,
        ...     override_lon=-122.4194,
        ...     after=datetime(2025, 1, 15),
        ...     recursive=True
        ... )

    Implementation:
        - Scans for .jpg and .jpeg files
        - Optionally scans subdirectories recursively
        - Filters by date if --after/--before specified
        - Delegates tagging to batch_tag_with_override()
    """
    # Collect photo paths
    if recursive:
        # Recursive glob
        photos = sorted(directory.rglob('*.jpg')) + sorted(directory.rglob('*.jpeg'))
    else:
        # Non-recursive glob
        photos = sorted(directory.glob('*.jpg')) + sorted(directory.glob('*.jpeg'))

    # Filter out symlinks (security: prevent directory traversal attacks)
    # Only process regular files within the intended directory
    photos = [p for p in photos if not p.is_symlink()]

    # Filter by date if specified
    if after is not None or before is not None:
        photos = filter_photos_by_date(photos, after=after, before=before)

    # Batch tag photos
    return batch_tag_with_override(
        photos,
        controls_file=controls_file,
        override_lat=override_lat,
        override_lon=override_lon,
        dry_run=dry_run,
        backup=backup
    )


def main() -> int:
    """
    Main entry point for GPS EXIF batch tagging tool.

    Parses command-line arguments and processes photos.

    Returns:
        int: Exit code (0 for success, non-zero for error)

    Command-line usage:
        batch_tag_photos.py DIRECTORY [options]

    Options:
        --lat LATITUDE      Manual latitude override
        --lon LONGITUDE     Manual longitude override
        --after YYYY-MM-DD  Only tag photos on or after this date
        --before YYYY-MM-DD Only tag photos before this date
        --recursive         Scan subdirectories recursively
        --dry-run           Don't modify photos, just show what would be done
        --backup            Create .bak files before modifying
        --help              Show help message
    """
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Batch tag Mothbox photos with GPS EXIF data',
        epilog='''
Examples:
  # Tag all photos with GPS from controls.txt
  %(prog)s /var/lib/mothbox/photos/

  # Tag with manual GPS coordinates
  %(prog)s /photos/ --lat 37.7749 --lon -122.4194

  # Tag photos from date range
  %(prog)s /photos/ --after 2025-01-15 --before 2025-01-20

  # Dry run (test without modifying)
  %(prog)s /photos/ --dry-run --lat 37.7749 --lon -122.4194

  # Create backups and scan recursively
  %(prog)s /photos/ --backup --recursive
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing photos to tag'
    )

    parser.add_argument(
        '--lat',
        type=float,
        metavar='LATITUDE',
        help='Manual latitude override (decimal degrees, -90 to 90)'
    )

    parser.add_argument(
        '--lon',
        type=float,
        metavar='LONGITUDE',
        help='Manual longitude override (decimal degrees, -180 to 180)'
    )

    parser.add_argument(
        '--after',
        type=str,
        metavar='YYYY-MM-DD',
        help='Only tag photos on or after this date'
    )

    parser.add_argument(
        '--before',
        type=str,
        metavar='YYYY-MM-DD',
        help='Only tag photos before this date'
    )

    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Scan subdirectories recursively'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Don\'t modify photos, just show what would be done'
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create .bak files before modifying photos'
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate directory with path traversal protection
    directory = Path(args.directory)

    # Canonicalize path to resolve symlinks and relative paths
    # This prevents directory traversal attacks (CWE-22)
    try:
        directory = directory.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        print(f"❌ Error: Cannot resolve directory path: {e}", file=sys.stderr)
        return 1

    if not directory.is_dir():
        print(f"❌ Error: Not a directory: {directory}", file=sys.stderr)
        return 1

    # Validate GPS coordinates if provided
    if args.lat is not None or args.lon is not None:
        # Both must be provided
        if args.lat is None or args.lon is None:
            print("❌ Error: Both --lat and --lon must be provided together", file=sys.stderr)
            return 1

        # Validate coordinate ranges
        if not validate_gps_override(args.lat, args.lon):
            print(f"❌ Error: Invalid GPS coordinates (lat: {args.lat}, lon: {args.lon})", file=sys.stderr)
            print("   Latitude must be -90 to 90, Longitude must be -180 to 180", file=sys.stderr)
            return 1

    # Check if GPS data available (either manual or controls.txt)
    if args.lat is None or args.lon is None:
        # Check if controls.txt has GPS
        gps_data = get_gps_data_from_controls()
        if not gps_data.get('has_fix', False):
            print("❌ Error: No GPS data available", file=sys.stderr)
            print("   Either provide --lat/--lon or ensure controls.txt has valid GPS fix", file=sys.stderr)
            return 1

    # Parse date filters
    after_date = None
    before_date = None

    if args.after:
        try:
            after_date = datetime.strptime(args.after, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Error: Invalid --after date format: {args.after}", file=sys.stderr)
            print("   Use YYYY-MM-DD format (e.g., 2025-01-15)", file=sys.stderr)
            return 1

    if args.before:
        try:
            before_date = datetime.strptime(args.before, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Error: Invalid --before date format: {args.before}", file=sys.stderr)
            print("   Use YYYY-MM-DD format (e.g., 2025-01-20)", file=sys.stderr)
            return 1

    # Print operation summary
    print("\n📸 Batch Tagging GPS EXIF")
    print("=" * 60)
    print(f"Directory: {directory}")

    if args.lat is not None and args.lon is not None:
        print(f"GPS Source: Manual override ({args.lat}, {args.lon})")
    else:
        print("GPS Source: controls.txt")

    if after_date:
        print(f"Date Filter: After {after_date.strftime('%Y-%m-%d')}")
    if before_date:
        print(f"Date Filter: Before {before_date.strftime('%Y-%m-%d')}")

    if args.recursive:
        print("Mode: Recursive")
    if args.dry_run:
        print("Mode: DRY RUN (no files will be modified)")
    if args.backup:
        print("Backup: Enabled")

    print("=" * 60)

    # Execute batch tagging
    results = batch_tag_directory(
        directory,
        override_lat=args.lat,
        override_lon=args.lon,
        after=after_date,
        before=before_date,
        recursive=args.recursive,
        dry_run=args.dry_run,
        backup=args.backup
    )

    # Print results
    print("\n✅ Batch Tagging Complete")
    print("=" * 60)
    print(f"Total Photos: {results['total']}")
    print(f"Tagged: {results['tagged']}")
    print(f"Skipped (already tagged): {results['skipped']}")
    print(f"Errors: {results['errors']}")
    print("=" * 60)

    # Return exit code
    if results['errors'] > 0:
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
