# Test Fixtures

This directory contains utilities for generating test fixtures used in E2E and integration testing.

## Test Photo Fixture Generator

**Script**: `create_test_photos.py`

Generates test JPEG photos with controlled EXIF metadata for testing the photo viewer UI, GPS coordinates display, and series navigation in E2E tests.

### Fixture Categories

The generator creates 11 test photos organized into 4 categories:

| Category | Count | Description |
|----------|-------|-------------|
| `with-gps/` | 2 | Photos with full GPS EXIF data (Panama: 9.15°N, 79.85°W, 50m altitude) |
| `without-gps/` | 1 | Photos with no GPS EXIF data |
| `hdr-series/` | 3 | HDR series following naming pattern: `moth_2024_01_17__08_00_00_HDR{0,1,2}.jpg` |
| `focus-bracket/` | 5 | Focus bracket series: `ManFocus_moth_2024_01_18__09_00_00_FB{0-4}.jpg` |

### Camera EXIF Metadata

All photos include realistic camera EXIF data:

- **Make**: Arducam
- **Model**: OwlSight 64MP
- **ISO**: 400
- **Exposure**: 1/100 second
- **Aperture**: f/2.8
- **Focal Length**: 6mm
- **DateTimeOriginal**: Controlled dates per photo

### GPS EXIF Metadata

Photos in the `with-gps/`, `hdr-series/`, and `focus-bracket/` categories include:

- **Latitude**: 9.15°N (Panama)
- **Longitude**: 79.85°W
- **Altitude**: 50m above sea level
- **Fix Mode**: 3D fix
- **Satellites Used**: 8
- **HDOP**: 1.2
- **PDOP**: 2.1

## Usage

### Generate Fixtures

```bash
# Generate fixtures in default location (webui/frontend/e2e/fixtures/photos/)
python Tests/fixtures/create_test_photos.py

# Custom output directory
python Tests/fixtures/create_test_photos.py --output-dir /path/to/output

# Clean and regenerate all fixtures
python Tests/fixtures/create_test_photos.py --clean
```

### Verify Fixtures

```bash
# Verify existing fixtures without regenerating
python Tests/fixtures/create_test_photos.py --verify-only
```

### Quiet Mode

```bash
# Suppress progress messages
python Tests/fixtures/create_test_photos.py --quiet
```

## Output Structure

```
webui/frontend/e2e/fixtures/photos/
├── with-gps/
│   ├── moth_2024_01_15__10_00_00.jpg
│   └── moth_2024_01_15__10_05_00.jpg
├── without-gps/
│   └── moth_2024_01_16__11_00_00.jpg
├── hdr-series/
│   ├── moth_2024_01_17__08_00_00_HDR0.jpg
│   ├── moth_2024_01_17__08_00_00_HDR1.jpg
│   └── moth_2024_01_17__08_00_00_HDR2.jpg
└── focus-bracket/
    ├── ManFocus_moth_2024_01_18__09_00_00_FB0.jpg
    ├── ManFocus_moth_2024_01_18__09_00_00_FB1.jpg
    ├── ManFocus_moth_2024_01_18__09_00_00_FB2.jpg
    ├── ManFocus_moth_2024_01_18__09_00_00_FB3.jpg
    └── ManFocus_moth_2024_01_18__09_00_00_FB4.jpg
```

## Visual Identification

Each category uses a distinct color for easy visual identification in tests:

- **with-gps**: Blue (#0066CC) and Teal (#009966)
- **without-gps**: Magenta (#CC0066)
- **hdr-series**: Orange (#FF9900), Yellow (#FFCC00), Light Yellow (#FFFF66)
- **focus-bracket**: Purple shades (#9966FF → #FFE5CC)

## Dependencies

- **PIL/Pillow**: Image creation and manipulation
- **piexif**: EXIF metadata embedding
- **webui.backend.lib.gps_exif_lib**: GPS EXIF utilities

Install with:
```bash
pip install Pillow piexif
```

## Related Documentation

- GPS EXIF Implementation: `webui/docs/dev/issues/ISSUE_98_GPS_EXIF_IMPLEMENTATION_SPEC.md`
- E2E Testing Guide: `webui/docs/dev/testing/e2e-testing.md`
- Series Detection: `webui/docs/dev/api/gallery.md` (Series Endpoints section)

## Integration with E2E Tests

These fixtures are designed for use in Playwright E2E tests. Example usage:

```javascript
// In photo-viewer.spec.js
test('should display GPS coordinates for photos with GPS EXIF', async ({ page }) => {
  // Load fixture photo with GPS
  const photoPath = 'e2e/fixtures/photos/with-gps/moth_2024_01_15__10_00_00.jpg';

  // Navigate to photo viewer
  await page.goto('/photos');

  // Verify GPS coordinates are displayed
  await expect(page.locator('[data-testid="gps-coordinates"]')).toContainText('9.15°N, 79.85°W');
});

test('should group HDR series correctly', async ({ page }) => {
  // Load HDR series fixtures
  const seriesPhotos = [
    'e2e/fixtures/photos/hdr-series/moth_2024_01_17__08_00_00_HDR0.jpg',
    'e2e/fixtures/photos/hdr-series/moth_2024_01_17__08_00_00_HDR1.jpg',
    'e2e/fixtures/photos/hdr-series/moth_2024_01_17__08_00_00_HDR2.jpg',
  ];

  // Verify series detection and navigation
  await page.goto('/photos');
  await expect(page.locator('[data-testid="series-indicator"]')).toContainText('HDR (3 photos)');
});
```

## Implementation Notes

The generator uses the existing Mothbox GPS EXIF infrastructure:

1. **Image Creation**: PIL creates simple colored 100×100 JPEG images
2. **Camera EXIF**: piexif embeds standard camera metadata
3. **GPS EXIF**: `webui.backend.lib.gps_exif_lib.embed_gps_exif()` adds GPS tags
4. **Verification**: `verify_gps_exif()` confirms EXIF was embedded correctly

This ensures fixtures match real Mothbox photo EXIF structure and patterns.
