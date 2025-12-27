#!/usr/bin/env python3
"""Demonstration script showing how to use test photo fixtures in tests.

This script demonstrates typical usage patterns for the test fixtures
created by create_test_photos.py, showing how to:
- Load and verify GPS EXIF data
- Detect photo series patterns (HDR, Focus Bracket)
- Access camera EXIF metadata

Run this script to verify the fixtures are working correctly:
    python Tests/fixtures/test_fixtures_demo.py
"""

import sys
from pathlib import Path

# Path setup for accessing mothbox modules
_fixtures_dir = Path(__file__).resolve().parent
_tests_dir = _fixtures_dir.parent
_firmware_root = _tests_dir.parent

if str(_firmware_root) not in sys.path:
    sys.path.insert(0, str(_firmware_root))

# Import dependencies
try:
    import piexif

    from webui.backend.lib.gps_exif_lib import verify_gps_exif
    from webui.backend.lib.series_detection import detect_series_type
except ImportError as e:
    print(f"ERROR: Required module not found: {e}", file=sys.stderr)
    sys.exit(1)


def demo_gps_photos():
    """Demonstrate working with GPS EXIF data."""
    print("=" * 60)
    print("DEMO 1: Photos with GPS EXIF Data")
    print("=" * 60)

    fixtures_dir = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"
    gps_photos = list((fixtures_dir / "with-gps").glob("*.jpg"))

    for photo in sorted(gps_photos):
        print(f"\n📷 {photo.name}")

        # Verify GPS EXIF
        gps_info = verify_gps_exif(photo)

        if gps_info['has_gps']:
            print("  ✓ Has GPS: Yes")
            print(f"  📍 Location: {gps_info['latitude']:.4f}°N, {abs(gps_info['longitude']):.4f}°W")
            print(f"  🛰️  Satellites: {gps_info['satellites']}")
            print(f"  ⛰️  Altitude: {gps_info['altitude']}m")
            print(f"  📊 HDOP: {gps_info['hdop']}")

            # Verify coordinates match expected Panama location
            assert abs(gps_info['latitude'] - 9.15) < 0.01, "Latitude mismatch!"
            assert abs(gps_info['longitude'] - (-79.85)) < 0.01, "Longitude mismatch!"
        else:
            print("  ✗ Has GPS: No")

    print("\n✓ GPS EXIF demo completed successfully")


def demo_no_gps_photos():
    """Demonstrate working with photos without GPS EXIF."""
    print("\n" + "=" * 60)
    print("DEMO 2: Photos without GPS EXIF Data")
    print("=" * 60)

    fixtures_dir = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"
    no_gps_photos = list((fixtures_dir / "without-gps").glob("*.jpg"))

    for photo in sorted(no_gps_photos):
        print(f"\n📷 {photo.name}")

        # Verify no GPS EXIF
        gps_info = verify_gps_exif(photo)

        print(f"  Has GPS: {gps_info['has_gps']}")
        assert gps_info['has_gps'] is False, "Should not have GPS EXIF!"

    print("\n✓ No-GPS photo demo completed successfully")


def demo_hdr_series():
    """Demonstrate detecting HDR series patterns."""
    print("\n" + "=" * 60)
    print("DEMO 3: HDR Series Detection")
    print("=" * 60)

    fixtures_dir = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"
    hdr_photos = list((fixtures_dir / "hdr-series").glob("*.jpg"))

    print(f"\nFound {len(hdr_photos)} photos in HDR series:")
    for photo in sorted(hdr_photos):
        series_info = detect_series_type(photo.name)
        print(f"  📷 {photo.name}")
        print(f"     Series Type: {series_info.series_type}")
        print(f"     Base Name: {series_info.base_name}")
        print(f"     Index: {series_info.index}")

        assert series_info.series_type == "hdr", f"Expected HDR series, got {series_info.series_type}!"

    print("\n✓ HDR series detection demo completed successfully")


def demo_focus_bracket_series():
    """Demonstrate detecting Focus Bracket series patterns."""
    print("\n" + "=" * 60)
    print("DEMO 4: Focus Bracket Series Detection")
    print("=" * 60)

    fixtures_dir = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"
    fb_photos = list((fixtures_dir / "focus-bracket").glob("*.jpg"))

    print(f"\nFound {len(fb_photos)} photos in Focus Bracket series:")
    for photo in sorted(fb_photos):
        series_info = detect_series_type(photo.name)
        print(f"  📷 {photo.name}")
        print(f"     Series Type: {series_info.series_type}")
        print(f"     Base Name: {series_info.base_name}")
        print(f"     Index: {series_info.index}")

        assert series_info.series_type == "focus_bracket", f"Expected focus_bracket, got {series_info.series_type}!"

    print("\n✓ Focus Bracket series detection demo completed successfully")


def demo_camera_exif():
    """Demonstrate accessing camera EXIF metadata."""
    print("\n" + "=" * 60)
    print("DEMO 5: Camera EXIF Metadata")
    print("=" * 60)

    fixtures_dir = _firmware_root / "webui" / "frontend" / "e2e" / "fixtures" / "photos"
    sample_photo = fixtures_dir / "with-gps" / "moth_2024_01_15__10_00_00.jpg"

    print(f"\n📷 {sample_photo.name}")

    # Load EXIF
    exif_dict = piexif.load(str(sample_photo))

    # Display camera metadata
    make = exif_dict["0th"][piexif.ImageIFD.Make].decode()
    model = exif_dict["0th"][piexif.ImageIFD.Model].decode()
    iso = exif_dict["Exif"][piexif.ExifIFD.ISOSpeed]
    exposure = exif_dict["Exif"][piexif.ExifIFD.ExposureTime]
    fnumber = exif_dict["Exif"][piexif.ExifIFD.FNumber]
    focal_length = exif_dict["Exif"][piexif.ExifIFD.FocalLength]
    datetime_original = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode()

    print(f"  📸 Camera: {make} {model}")
    print(f"  🎞️  ISO: {iso}")
    print(f"  ⏱️  Exposure: 1/{exposure[1]} second")
    print(f"  🔍 Aperture: f/{fnumber[0]/fnumber[1]}")
    print(f"  📏 Focal Length: {focal_length[0]/focal_length[1]}mm")
    print(f"  📅 Date: {datetime_original}")

    # Verify expected values
    assert make == "Arducam", "Make should be Arducam"
    assert model == "OwlSight 64MP", "Model should be OwlSight 64MP"
    assert iso == 400, "ISO should be 400"
    assert exposure == (1, 100), "Exposure should be 1/100"
    assert fnumber == (28, 10), "Aperture should be f/2.8"
    assert focal_length == (6, 1), "Focal length should be 6mm"

    print("\n✓ Camera EXIF demo completed successfully")


def main():
    """Run all demonstrations."""
    print("\n🎬 Test Photo Fixtures Demonstration")
    print("=" * 60)

    try:
        demo_gps_photos()
        demo_no_gps_photos()
        demo_hdr_series()
        demo_focus_bracket_series()
        demo_camera_exif()

        print("\n" + "=" * 60)
        print("✓ ALL DEMOS PASSED!")
        print("=" * 60)
        print("\nThe test fixtures are working correctly and ready for E2E testing.")
        print("\nNext steps:")
        print("  1. Use these fixtures in Playwright E2E tests")
        print("  2. Test photo viewer GPS display")
        print("  3. Test series navigation (HDR, Focus Bracket)")
        print("  4. Test metadata display in photo details")
        print()

        return 0

    except AssertionError as e:
        print(f"\n✗ ASSERTION FAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
