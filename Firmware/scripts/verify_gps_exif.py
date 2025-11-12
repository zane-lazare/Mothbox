#!/usr/bin/env python3
"""
GPS EXIF Verification Tool for Mothbox Photos

Verifies GPS EXIF data embedded in Mothbox photos and generates reports.
Can process single photos, directories, or photo lists.

Features:
- Print GPS info to console in human-readable format
- Generate CSV reports for batch analysis
- Extract photo timestamps from Mothbox filenames
- Handle missing files and corrupted EXIF gracefully

Usage:
    # Verify single photo
    ./verify_gps_exif.py /photos/mothbox_2025_01_15__12_30_00.jpg

    # Scan directory
    ./verify_gps_exif.py /photos/

    # Generate CSV report
    ./verify_gps_exif.py /photos/ --csv report.csv

    # Verify multiple photos
    ./verify_gps_exif.py photo1.jpg photo2.jpg photo3.jpg

Related:
- Issue #98 Phase 3: GPS EXIF Verification Tool (Days 1-3)
- Spec: webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md
- Library: lib/gps_exif_lib.py
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import GPS EXIF library functions
from lib.gps_exif_lib import verify_gps_exif


# Module exports
__all__ = [
    'extract_timestamp_from_filename',
    'print_gps_info',
    'generate_csv_report',
    'main',
]


# Mothbox filename parsing constants
MOTHBOX_PREFIX = 'mothbox'                    # Required filename prefix (lowercase)
FILENAME_YEAR_DIGITS = 4                       # Year component length
FILENAME_DATE_DIGITS = 2                       # Month/day component length
FILENAME_TIME_DIGITS = 2                       # Hour/minute/second component length

# Regex pattern for Mothbox filename format
# Format: mothbox_YYYY_MM_DD__HH_MM_SS[_bracket_N].{jpg|jpeg}
MOTHBOX_FILENAME_PATTERN = (
    r'^mothbox_'                               # Prefix (lowercase only)
    r'(\d{4})_'                                # Year (4 digits)
    r'(\d{2})_'                                # Month (2 digits)
    r'(\d{2})__'                               # Day (2 digits) + double underscore
    r'(\d{2})_'                                # Hour (2 digits)
    r'(\d{2})_'                                # Minute (2 digits)
    r'(\d{2})'                                 # Second (2 digits)
    r'(?:_bracket_\d+)?'                       # Optional: _bracket_N suffix
    r'\.[jJ][pP][eE]?[gG]$'                    # Extension: .jpg/.JPG/.jpeg/.JPEG
)


def extract_timestamp_from_filename(filename: str | Path) -> datetime | None:
    """
    Extract timestamp from Mothbox photo filename using regex pattern matching.

    Mothbox photos follow the naming convention:
        mothbox_YYYY_MM_DD__HH_MM_SS.jpg
        mothbox_YYYY_MM_DD__HH_MM_SS_bracket_N.jpg (focus bracketing)
        mothbox_YYYY_MM_DD__HH_MM_SS.jpeg (alternative extension)
        mothbox_YYYY_MM_DD__HH_MM_SS.JPG (case variants)

    This function uses regex pattern matching for robust parsing that handles:
    - Optional focus bracket suffixes
    - Case-insensitive file extensions (.jpg, .JPG, .jpeg, .JPEG)
    - Extra underscores or unexpected suffixes
    - Leading/trailing whitespace

    Args:
        filename: Photo filename or path (str or Path object)

    Returns:
        datetime: Parsed timestamp, or None if filename doesn't match format

    Examples:
        >>> extract_timestamp_from_filename("mothbox_2025_01_15__12_30_45.jpg")
        datetime(2025, 1, 15, 12, 30, 45)

        >>> extract_timestamp_from_filename("/photos/mothbox_2025_01_15__12_30_45_bracket_0.jpg")
        datetime(2025, 1, 15, 12, 30, 45)

        >>> extract_timestamp_from_filename("mothbox_2025_01_15__12_30_45.JPG")
        datetime(2025, 1, 15, 12, 30, 45)

        >>> extract_timestamp_from_filename("invalid.jpg")
        None

    Implementation:
        - Uses regex pattern for robust parsing
        - Handles Path objects and strings
        - Extracts basename from full paths
        - Validates date/time component ranges
        - Returns None for invalid formats (no exceptions raised)
    """
    # Convert to Path object and get basename
    if isinstance(filename, str):
        filename = Path(filename)

    basename = filename.name

    # Use module-level constant for filename pattern
    # Pattern is defined at top of module for easy maintenance
    # See MOTHBOX_FILENAME_PATTERN constant for pattern details
    match = re.match(MOTHBOX_FILENAME_PATTERN, basename)

    if not match:
        return None

    try:
        # Extract captured groups
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6))

        # Construct datetime (this validates ranges automatically)
        # Will raise ValueError if date/time is invalid (e.g., month=13, hour=25)
        timestamp = datetime(year, month, day, hour, minute, second)

        return timestamp

    except ValueError:
        # Invalid date/time values (e.g., Feb 30, hour=25)
        return None


def print_gps_info(photo_path: Path) -> None:
    """
    Print GPS EXIF information for a photo in human-readable format.

    Displays:
    - Filename
    - GPS coordinates (latitude, longitude)
    - Altitude (if available)
    - GPS timestamp (if available)
    - Number of satellites (if available)
    - HDOP (Horizontal Dilution of Precision, if available)
    - Photo capture timestamp (extracted from filename)

    Args:
        photo_path: Path to JPEG photo file

    Output format:
        File: mothbox_2025_01_15__12_30_00.jpg
        GPS Coordinates: 37.7749, -122.4194
        Altitude: 100.5 m
        GPS Timestamp: 2025:01:15 12:30:00
        Satellites: 8
        HDOP: 1.20
        Photo Timestamp: 2025-01-15 12:30:00

    Handles:
        - Missing files (prints error)
        - Photos without GPS data (prints "No GPS data")
        - Partial GPS data (shows available fields)
    """
    # Check if file exists
    if not photo_path.exists():
        print(f"❌ File not found: {photo_path.name}")
        return

    # Get GPS info from photo
    gps_info = verify_gps_exif(photo_path)

    # Print filename
    print(f"\n📷 File: {photo_path.name}")
    print("=" * 60)

    # Check if photo has GPS data
    if not gps_info['has_gps']:
        print("❌ No GPS EXIF data found in photo")
        return

    # Print GPS coordinates
    if gps_info['latitude'] is not None and gps_info['longitude'] is not None:
        lat = gps_info['latitude']
        lon = gps_info['longitude']
        print(f"📍 GPS Coordinates: {lat:.6f}, {lon:.6f}")

        # Format as degrees for readability
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        print(f"   {abs(lat):.6f}° {lat_dir}, {abs(lon):.6f}° {lon_dir}")

    # Print altitude
    if gps_info['altitude'] is not None:
        print(f"⛰️  Altitude: {gps_info['altitude']:.2f} m")

    # Print GPS timestamp
    if gps_info['timestamp'] is not None:
        print(f"🕐 GPS Timestamp: {gps_info['timestamp']}")

    # Print satellite count
    if gps_info['satellites'] is not None:
        print(f"🛰️  Satellites: {gps_info['satellites']}")

    # Print HDOP
    if gps_info['hdop'] is not None:
        print(f"📊 HDOP: {gps_info['hdop']:.2f}")

    # Extract and print photo timestamp from filename
    photo_timestamp = extract_timestamp_from_filename(photo_path)
    if photo_timestamp is not None:
        print(f"📸 Photo Timestamp: {photo_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    print("=" * 60)


def generate_csv_report(photos: list[Path], output_csv: Path) -> None:
    """
    Generate CSV report of GPS EXIF data for multiple photos.

    Creates a CSV file with columns:
    - filename: Photo filename
    - photo_timestamp: Timestamp from filename (YYYY-MM-DD HH:MM:SS)
    - has_gps: True/False
    - latitude: Decimal degrees
    - longitude: Decimal degrees
    - altitude: Meters (or N/A)
    - gps_timestamp: GPS timestamp from EXIF
    - satellites: Number of satellites
    - hdop: Horizontal DOP
    - status: OK, No GPS, Missing File, or Error

    Args:
        photos: List of photo paths to process
        output_csv: Output CSV file path

    Example:
        >>> photos = [Path(p) for p in glob.glob("/photos/*.jpg")]
        >>> generate_csv_report(photos, Path("gps_report.csv"))

    Handles:
        - Missing files (status: "Missing File")
        - Photos without GPS (status: "No GPS")
        - Corrupted EXIF (status: "Error")
        - Empty photo list (creates CSV with headers only)
    """
    # Define CSV columns
    fieldnames = [
        'filename',
        'photo_timestamp',
        'has_gps',
        'latitude',
        'longitude',
        'altitude',
        'gps_timestamp',
        'satellites',
        'hdop',
        'status'
    ]

    # Open CSV file for writing
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Process each photo
        for photo_path in photos:
            # Initialize row with defaults
            row = {
                'filename': photo_path.name,
                'photo_timestamp': '',
                'has_gps': False,
                'latitude': '',
                'longitude': '',
                'altitude': '',
                'gps_timestamp': '',
                'satellites': '',
                'hdop': '',
                'status': 'OK'
            }

            # Extract photo timestamp from filename
            photo_timestamp = extract_timestamp_from_filename(photo_path)
            if photo_timestamp:
                row['photo_timestamp'] = photo_timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Check if file exists
            if not photo_path.exists():
                row['status'] = 'Missing File'
                writer.writerow(row)
                continue

            # Try to read GPS EXIF
            try:
                gps_info = verify_gps_exif(photo_path)

                row['has_gps'] = gps_info['has_gps']

                if gps_info['has_gps']:
                    # Populate GPS fields
                    if gps_info['latitude'] is not None:
                        row['latitude'] = f"{gps_info['latitude']:.6f}"
                    if gps_info['longitude'] is not None:
                        row['longitude'] = f"{gps_info['longitude']:.6f}"
                    if gps_info['altitude'] is not None:
                        row['altitude'] = f"{gps_info['altitude']:.2f}"
                    if gps_info['timestamp'] is not None:
                        row['gps_timestamp'] = gps_info['timestamp']
                    if gps_info['satellites'] is not None:
                        row['satellites'] = gps_info['satellites']
                    if gps_info['hdop'] is not None:
                        row['hdop'] = f"{gps_info['hdop']:.2f}"

                    row['status'] = 'OK'
                else:
                    row['status'] = 'No GPS'

            except Exception as e:
                row['status'] = f'Error: {str(e)}'

            writer.writerow(row)

    print(f"\n✅ CSV report generated: {output_csv}")
    print(f"   Processed {len(photos)} photos")


def main() -> int:
    """
    Main entry point for GPS EXIF verification tool.

    Parses command-line arguments and processes photos.

    Returns:
        int: Exit code (0 for success, non-zero for error)

    Command-line usage:
        verify_gps_exif.py photo1.jpg photo2.jpg [options]
        verify_gps_exif.py /photos/ [options]

    Options:
        --csv OUTPUT.csv    Generate CSV report instead of printing to console
        --help              Show help message
    """
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Verify GPS EXIF data in Mothbox photos',
        epilog='''
Examples:
  # Verify single photo
  %(prog)s mothbox_2025_01_15__12_30_00.jpg

  # Scan directory
  %(prog)s /var/lib/mothbox/photos/

  # Generate CSV report
  %(prog)s /photos/ --csv report.csv

  # Verify multiple photos
  %(prog)s photo1.jpg photo2.jpg photo3.jpg --csv batch_report.csv
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'photos',
        nargs='+',
        type=str,
        help='Photo file(s) or directory to scan'
    )

    parser.add_argument(
        '--csv',
        type=str,
        metavar='OUTPUT.csv',
        help='Generate CSV report instead of printing to console'
    )

    # Parse arguments
    args = parser.parse_args()

    # Collect photo paths
    photo_paths = []

    for photo_arg in args.photos:
        photo_path = Path(photo_arg)

        if photo_path.is_dir():
            # Scan directory for JPEG files
            jpeg_files = sorted(photo_path.glob('*.jpg')) + sorted(photo_path.glob('*.jpeg'))
            photo_paths.extend(jpeg_files)
        elif photo_path.exists():
            # Single file
            photo_paths.append(photo_path)
        else:
            # Non-existent file (will be handled gracefully later)
            photo_paths.append(photo_path)

    # Check if any photos found
    if not photo_paths:
        print("❌ No photos found to process", file=sys.stderr)
        return 1

    # Generate report based on output format
    if args.csv:
        # CSV report mode
        csv_output = Path(args.csv)
        generate_csv_report(photo_paths, csv_output)
    else:
        # Console output mode
        print(f"\n🔍 Verifying GPS EXIF data for {len(photo_paths)} photos...\n")

        for photo_path in photo_paths:
            print_gps_info(photo_path)

    return 0


if __name__ == '__main__':
    sys.exit(main())
