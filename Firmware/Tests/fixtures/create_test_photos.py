#!/usr/bin/env python3
"""Generate test photo fixtures with controlled EXIF data for E2E testing.

This script creates test JPEG photos with controlled EXIF metadata for testing
the photo viewer UI, GPS coordinates display, and series navigation in E2E tests.

Fixture Categories:
    - with-gps/: Photos with full GPS EXIF data (Panama location)
    - without-gps/: Photos with no GPS EXIF data
    - hdr-series/: HDR series following naming pattern
    - focus-bracket/: Focus bracket series following naming pattern

Usage:
    # Generate fixtures in default location
    python Tests/fixtures/create_test_photos.py

    # Custom output directory
    python Tests/fixtures/create_test_photos.py --output-dir /path/to/output

    # Clean and regenerate all fixtures
    python Tests/fixtures/create_test_photos.py --clean

Example:
    $ python Tests/fixtures/create_test_photos.py
    Creating test photo fixtures...
    ✓ Created with-gps/moth_2024_01_15__10_00_00.jpg
    ✓ Created with-gps/moth_2024_01_15__10_05_00.jpg
    ✓ Created without-gps/moth_2024_01_16__11_00_00.jpg
    ✓ Created hdr-series/moth_2024_01_17__08_00_00_HDR0.jpg
    ...
    Successfully created 11 test photos in webui/frontend/e2e/fixtures/photos/
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Path setup for accessing mothbox_paths at firmware root
_fixtures_dir = Path(__file__).resolve().parent
_tests_dir = _fixtures_dir.parent
_firmware_root = _tests_dir.parent

# Allowed output directories for path validation
_ALLOWED_OUTPUT_ROOTS = [
    _firmware_root,  # Project directory
    Path('/tmp'),    # System temp directory
]

if str(_firmware_root) not in sys.path:
    sys.path.insert(0, str(_firmware_root))

# Import dependencies
try:
    import piexif
    from PIL import Image
except ImportError as e:
    print(f"ERROR: Required library not installed: {e}", file=sys.stderr)
    print("Install with: pip install Pillow piexif", file=sys.stderr)
    sys.exit(1)

# Import GPS EXIF utilities
from webui.backend.lib.gps_exif_lib import embed_gps_exif, verify_gps_exif

# Fixture configuration
DEFAULT_OUTPUT_DIR = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"

# GPS coordinates for test photos (Panama location)
TEST_GPS_DATA = {
    'latitude': 9.15,
    'longitude': -79.85,
    'altitude': 50.0,
    'gpstime': int(datetime(2024, 1, 15, 10, 0, 0).timestamp()),
    'fix_mode': 3,  # 3D fix
    'satellites_used': 8,
    'hdop': 1.2,
    'pdop': 2.1,
    'has_fix': True
}

# Camera EXIF data (Arducam OwlSight 64MP)
CAMERA_EXIF = {
    "0th": {
        piexif.ImageIFD.Make: b"Arducam",
        piexif.ImageIFD.Model: b"OwlSight 64MP",
        piexif.ImageIFD.Software: b"Mothbox Test Fixture Generator",
    },
    "Exif": {
        piexif.ExifIFD.ISOSpeedRatings: 400,
        piexif.ExifIFD.ExposureTime: (1, 100),  # 1/100 second
        piexif.ExifIFD.FNumber: (28, 10),  # f/2.8
        piexif.ExifIFD.FocalLength: (6, 1),  # 6mm
        piexif.ExifIFD.DateTimeOriginal: b"2024:01:15 10:00:00",
    },
    "GPS": {}  # Will be populated by embed_gps_exif()
}

# Test photo fixtures specification
FIXTURES = [
    # Photos with GPS data
    {
        'category': 'with-gps',
        'filename': 'moth_2024_01_15__10_00_00.jpg',
        'color': (0, 102, 204),  # Blue
        'has_gps': True,
        'datetime': '2024:01:15 10:00:00',
        'description': 'Photo with full GPS EXIF (Panama)',
    },
    {
        'category': 'with-gps',
        'filename': 'moth_2024_01_15__10_05_00.jpg',
        'color': (0, 153, 102),  # Teal
        'has_gps': True,
        'datetime': '2024:01:15 10:05:00',
        'description': 'Second photo with GPS EXIF',
    },
    # Photo without GPS data
    {
        'category': 'without-gps',
        'filename': 'moth_2024_01_16__11_00_00.jpg',
        'color': (204, 0, 102),  # Magenta
        'has_gps': False,
        'datetime': '2024:01:16 11:00:00',
        'description': 'Photo without GPS EXIF',
    },
    # HDR series (3 photos)
    {
        'category': 'hdr-series',
        'filename': 'moth_2024_01_17__08_00_00_HDR0.jpg',
        'color': (255, 153, 0),  # Orange
        'has_gps': True,
        'datetime': '2024:01:17 08:00:00',
        'description': 'HDR series photo 1 (underexposed)',
    },
    {
        'category': 'hdr-series',
        'filename': 'moth_2024_01_17__08_00_00_HDR1.jpg',
        'color': (255, 204, 0),  # Yellow
        'has_gps': True,
        'datetime': '2024:01:17 08:00:01',
        'description': 'HDR series photo 2 (normal)',
    },
    {
        'category': 'hdr-series',
        'filename': 'moth_2024_01_17__08_00_00_HDR2.jpg',
        'color': (255, 255, 102),  # Light yellow
        'has_gps': True,
        'datetime': '2024:01:17 08:00:02',
        'description': 'HDR series photo 3 (overexposed)',
    },
    # Focus bracket series (5 photos)
    {
        'category': 'focus-bracket',
        'filename': 'ManFocus_moth_2024_01_18__09_00_00_FB0.jpg',
        'color': (153, 102, 255),  # Purple
        'has_gps': True,
        'datetime': '2024:01:18 09:00:00',
        'description': 'Focus bracket photo 1 (closest)',
    },
    {
        'category': 'focus-bracket',
        'filename': 'ManFocus_moth_2024_01_18__09_00_00_FB1.jpg',
        'color': (204, 153, 255),  # Light purple
        'has_gps': True,
        'datetime': '2024:01:18 09:00:01',
        'description': 'Focus bracket photo 2',
    },
    {
        'category': 'focus-bracket',
        'filename': 'ManFocus_moth_2024_01_18__09_00_00_FB2.jpg',
        'color': (255, 153, 204),  # Pink
        'has_gps': True,
        'datetime': '2024:01:18 09:00:02',
        'description': 'Focus bracket photo 3 (middle)',
    },
    {
        'category': 'focus-bracket',
        'filename': 'ManFocus_moth_2024_01_18__09_00_00_FB3.jpg',
        'color': (255, 204, 204),  # Light pink
        'has_gps': True,
        'datetime': '2024:01:18 09:00:03',
        'description': 'Focus bracket photo 4',
    },
    {
        'category': 'focus-bracket',
        'filename': 'ManFocus_moth_2024_01_18__09_00_00_FB4.jpg',
        'color': (255, 229, 204),  # Peach
        'has_gps': True,
        'datetime': '2024:01:18 09:00:04',
        'description': 'Focus bracket photo 5 (farthest)',
    },
]


def validate_output_dir(output_dir: Path) -> bool:
    """Validate that output directory is within allowed paths.

    Args:
        output_dir: Directory to validate

    Returns:
        bool: True if directory is within allowed paths, False otherwise

    Note:
        Prevents directory traversal attacks by ensuring output is within
        either the project directory or /tmp.
    """
    try:
        resolved = output_dir.resolve()
        for allowed_root in _ALLOWED_OUTPUT_ROOTS:
            allowed_resolved = allowed_root.resolve()
            # Check if resolved path is within allowed root
            try:
                resolved.relative_to(allowed_resolved)
                return True
            except ValueError:
                continue
        return False
    except (OSError, ValueError):
        return False


def create_test_image(
    output_path: Path,
    color: tuple[int, int, int],
    size: tuple[int, int] = (100, 100)
) -> None:
    """Create a simple colored test image.

    Args:
        output_path: Path where image will be saved
        color: RGB color tuple (0-255 for each channel)
        size: Image dimensions in pixels (width, height)

    Note:
        Creates a solid color image for easy visual identification in tests.
    """
    img = Image.new('RGB', size, color=color)
    img.save(output_path, 'JPEG', quality=95)


def add_camera_exif(photo_path: Path, datetime_str: str) -> None:
    """Add camera EXIF metadata to a photo.

    Args:
        photo_path: Path to JPEG photo
        datetime_str: EXIF datetime string (format: "YYYY:MM:DD HH:MM:SS")

    Note:
        Embeds standard camera EXIF tags (Make, Model, ISO, Exposure, etc.)
        but does NOT add GPS EXIF (use embed_gps_exif() for that).
    """
    # Create EXIF dict with camera metadata
    exif_dict = CAMERA_EXIF.copy()
    exif_dict["0th"] = CAMERA_EXIF["0th"].copy()
    exif_dict["Exif"] = CAMERA_EXIF["Exif"].copy()

    # Update datetime
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = datetime_str.encode('ascii')

    # Dump EXIF to bytes
    exif_bytes = piexif.dump(exif_dict)

    # Re-save photo with EXIF
    img = Image.open(photo_path)
    img.save(photo_path, 'JPEG', exif=exif_bytes, quality=95)


def create_fixture(
    fixture: dict[str, Any],
    output_dir: Path,
    verbose: bool = True
) -> bool:
    """Create a single test photo fixture.

    Args:
        fixture: Fixture specification dict with keys:
            - category: Subdirectory name (e.g., 'with-gps', 'hdr-series')
            - filename: Photo filename
            - color: RGB color tuple
            - has_gps: Whether to embed GPS EXIF
            - datetime: EXIF datetime string
            - description: Human-readable description
        output_dir: Base output directory for fixtures
        verbose: Print progress messages

    Returns:
        bool: True if fixture created successfully, False on error

    Note:
        Creates directory structure, generates colored image, adds EXIF,
        and optionally embeds GPS coordinates.
    """
    # Create category subdirectory
    category_dir = output_dir / fixture['category']
    category_dir.mkdir(parents=True, exist_ok=True)

    # Full path to photo
    photo_path = category_dir / fixture['filename']

    try:
        # Step 1: Create colored test image
        create_test_image(photo_path, fixture['color'])

        # Step 2: Add camera EXIF metadata
        add_camera_exif(photo_path, fixture['datetime'])

        # Step 3: Embed GPS EXIF if requested
        if fixture['has_gps']:
            result = embed_gps_exif(
                photo_path,
                gps_data=TEST_GPS_DATA,
                backup=False,
                dry_run=False
            )

            if not result['success']:
                error_msg = result.get('error', 'Unknown error')
                print(f"✗ Failed to embed GPS EXIF in {photo_path}: {error_msg}", file=sys.stderr)
                return False

        # Step 4: Verify result
        if fixture['has_gps']:
            gps_info = verify_gps_exif(photo_path)
            if not gps_info['has_gps']:
                print(f"✗ GPS EXIF verification failed for {photo_path}", file=sys.stderr)
                return False

        # Success
        if verbose:
            gps_status = "with GPS" if fixture['has_gps'] else "without GPS"
            print(f"✓ Created {fixture['category']}/{fixture['filename']} ({gps_status})")

        return True

    except Exception as e:
        print(f"✗ Error creating {photo_path}: {e}", file=sys.stderr)
        return False


def clean_output_dir(output_dir: Path, verbose: bool = True) -> None:
    """Remove all existing fixtures in output directory.

    Args:
        output_dir: Directory to clean
        verbose: Print progress messages

    Note:
        Removes all category subdirectories and their contents.
        Safe to call even if directory doesn't exist.
    """
    if not output_dir.exists():
        return

    # Get all category directories
    categories = {fixture['category'] for fixture in FIXTURES}

    for category in categories:
        category_dir = output_dir / category
        if category_dir.exists():
            shutil.rmtree(category_dir)
            if verbose:
                print(f"Cleaned {category_dir}")


def verify_fixtures(output_dir: Path, verbose: bool = True) -> dict[str, Any]:
    """Verify all fixtures were created correctly.

    Args:
        output_dir: Base directory containing fixtures
        verbose: Print detailed verification results

    Returns:
        dict: Verification results with keys:
            - total: Total number of fixtures checked
            - passed: Number of fixtures that passed verification
            - failed: Number of fixtures that failed verification
            - errors: List of error messages

    Note:
        Checks that:
        1. All expected files exist
        2. Files are valid JPEGs
        3. GPS EXIF is present/absent as expected
        4. Camera EXIF is present
    """
    results = {
        'total': len(FIXTURES),
        'passed': 0,
        'failed': 0,
        'errors': []
    }

    for fixture in FIXTURES:
        photo_path = output_dir / fixture['category'] / fixture['filename']

        # Check file exists
        if not photo_path.exists():
            results['failed'] += 1
            results['errors'].append(f"Missing file: {photo_path}")
            continue

        # Check is valid JPEG
        try:
            img = Image.open(photo_path)
            img.verify()
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Invalid JPEG {photo_path}: {e}")
            continue

        # Check GPS EXIF
        gps_info = verify_gps_exif(photo_path)
        if fixture['has_gps'] and not gps_info['has_gps']:
            results['failed'] += 1
            results['errors'].append(f"Missing GPS EXIF: {photo_path}")
            continue
        elif not fixture['has_gps'] and gps_info['has_gps']:
            results['failed'] += 1
            results['errors'].append(f"Unexpected GPS EXIF: {photo_path}")
            continue

        # Check camera EXIF
        try:
            exif_dict = piexif.load(str(photo_path))
            if piexif.ImageIFD.Make not in exif_dict.get("0th", {}):
                results['failed'] += 1
                results['errors'].append(f"Missing camera EXIF: {photo_path}")
                continue
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"EXIF read error {photo_path}: {e}")
            continue

        # All checks passed
        results['passed'] += 1

    if verbose:
        print("\nVerification Results:")
        print(f"  Total fixtures: {results['total']}")
        print(f"  ✓ Passed: {results['passed']}")
        print(f"  ✗ Failed: {results['failed']}")

        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  • {error}")

    return results


def main() -> int:
    """Main entry point for fixture generator.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Generate test photo fixtures with controlled EXIF data for E2E testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate fixtures in default location
  python Tests/fixtures/create_test_photos.py

  # Custom output directory
  python Tests/fixtures/create_test_photos.py --output-dir /path/to/output

  # Clean and regenerate all fixtures
  python Tests/fixtures/create_test_photos.py --clean

Fixture Categories:
  with-gps/        Photos with full GPS EXIF data (Panama: 9.15°N, 79.85°W)
  without-gps/     Photos with no GPS EXIF data
  hdr-series/      3-photo HDR series following naming pattern
  focus-bracket/   5-photo focus bracket series following naming pattern

Camera EXIF:
  Make:            Arducam
  Model:           OwlSight 64MP
  ISO:             400
  Exposure:        1/100 second
  Aperture:        f/2.8
  Focal Length:    6mm
        """
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for fixtures (default: {DEFAULT_OUTPUT_DIR})"
    )

    parser.add_argument(
        '--clean',
        action='store_true',
        help="Remove existing fixtures before generating new ones"
    )

    parser.add_argument(
        '--verify-only',
        action='store_true',
        help="Only verify existing fixtures, don't create new ones"
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    verbose = not args.quiet

    # Validate output directory to prevent directory traversal
    if not validate_output_dir(args.output_dir):
        print(
            f"ERROR: Output directory '{args.output_dir}' is not within allowed paths.\n"
            f"Allowed paths: project directory ({_firmware_root}) or /tmp",
            file=sys.stderr
        )
        return 1

    # Verify-only mode
    if args.verify_only:
        if verbose:
            print(f"Verifying fixtures in {args.output_dir}...")
        results = verify_fixtures(args.output_dir, verbose=verbose)
        return 0 if results['failed'] == 0 else 1

    # Clean if requested
    if args.clean:
        if verbose:
            print(f"Cleaning {args.output_dir}...")
        clean_output_dir(args.output_dir, verbose=verbose)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate fixtures
    if verbose:
        print(f"\nCreating test photo fixtures in {args.output_dir}...")

    success_count = 0
    for fixture in FIXTURES:
        if create_fixture(fixture, args.output_dir, verbose=verbose):
            success_count += 1

    # Verify all fixtures
    if verbose:
        print(f"\n{success_count}/{len(FIXTURES)} fixtures created successfully")
        print("\nVerifying fixtures...")

    results = verify_fixtures(args.output_dir, verbose=verbose)

    # Summary
    if verbose:
        print(f"\nSuccessfully created {success_count} test photos in {args.output_dir}")
        print("\nFixture summary:")
        categories = {}
        for fixture in FIXTURES:
            cat = fixture['category']
            categories[cat] = categories.get(cat, 0) + 1

        for category, count in sorted(categories.items()):
            print(f"  {category}/: {count} photos")

    # Return exit code based on verification results
    return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
