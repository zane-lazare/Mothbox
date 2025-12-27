# E2E Photo Test Fixtures

## Overview

Test photo fixtures provide controlled EXIF metadata for E2E testing of the photo viewer, GPS coordinates display, and series navigation. These fixtures are generated using `Tests/fixtures/create_test_photos.py` and deployed to the Pi server's PHOTOS_DIR.

## Fixture Categories

### with-gps/

**Count**: 2 photos

**Purpose**: Testing GPS coordinate display, copy functionality, and map features

**GPS Location**: Panama (9.15°N, 79.85°W, 50m altitude)

**Files**:
- `moth_2024_01_15__10_00_00.jpg` (Blue #0066CC)
- `moth_2024_01_15__10_05_00.jpg` (Teal #009966)

**Use Cases**:
- GPS coordinate display in EXIF section
- Copy coordinates to clipboard
- Map marker placement
- Altitude display

### without-gps/

**Count**: 1 photo

**Purpose**: Testing graceful handling of missing GPS data

**Files**:
- `moth_2024_01_16__11_00_00.jpg` (Magenta #CC0066)

**Use Cases**:
- Verify "N/A" displayed for missing GPS
- Ensure no errors when GPS data absent
- Copy button disabled or hidden

### hdr-series/

**Count**: 3 photos

**Purpose**: Testing HDR series detection and navigation

**Naming Pattern**: `moth_2024_01_17__08_00_00_HDR{0,1,2}.jpg`

**Files**:
- `moth_2024_01_17__08_00_00_HDR0.jpg` (Orange #FF9900)
- `moth_2024_01_17__08_00_00_HDR1.jpg` (Yellow #FFCC00)
- `moth_2024_01_17__08_00_00_HDR2.jpg` (Light Yellow #FFFF66)

**GPS**: Included (Panama coordinates)

**Use Cases**:
- Series detection and grouping
- Series indicator display ("HDR Series: 1/3")
- Series navigation buttons
- Series counter updates

### focus-bracket/

**Count**: 5 photos

**Purpose**: Testing Focus Bracket series detection and navigation

**Naming Pattern**: `ManFocus_moth_2024_01_18__09_00_00_FB{0,1,2,3,4}.jpg`

**Files**:
- `ManFocus_moth_2024_01_18__09_00_00_FB0.jpg` (Purple #9966FF)
- `ManFocus_moth_2024_01_18__09_00_00_FB1.jpg` (Purple #AA77FF)
- `ManFocus_moth_2024_01_18__09_00_00_FB2.jpg` (Purple #BB88FF)
- `ManFocus_moth_2024_01_18__09_00_00_FB3.jpg` (Purple #CC99FF)
- `ManFocus_moth_2024_01_18__09_00_00_FB4.jpg` (Light Purple #FFE5CC)

**GPS**: Included (Panama coordinates)

**Use Cases**:
- Focus bracket series detection
- Series indicator display ("Focus Bracket: 2/5")
- Multi-image series navigation
- Series thumbnail display

## EXIF Metadata Embedded

### Camera Information

All photos include realistic Arducam OwlSight metadata:

| Field | Value |
|-------|-------|
| Make | Arducam |
| Model | OwlSight 64MP |
| ISO | 400 |
| Exposure | 1/100 second |
| Aperture | f/2.8 |
| Focal Length | 6mm |
| DateTimeOriginal | Controlled per photo |

### GPS Information

Photos with GPS include:

| Field | Value |
|-------|-------|
| Latitude | 9.15°N |
| Longitude | 79.85°W |
| Altitude | 50m above sea level |
| GPS Version | 2.2.0.0 |
| Map Datum | WGS-84 |

## Generating Fixtures

### Basic Usage

```bash
# Generate fixtures in default location (webui/frontend/e2e/fixtures/photos/)
python Tests/fixtures/create_test_photos.py

# Custom output directory
python Tests/fixtures/create_test_photos.py --output-dir /path/to/output

# Clean and regenerate all fixtures
python Tests/fixtures/create_test_photos.py --clean

# Suppress progress messages
python Tests/fixtures/create_test_photos.py --quiet
```

### Verification

```bash
# Verify existing fixtures without regenerating
python Tests/fixtures/create_test_photos.py --verify-only
```

The verification checks:
- Expected number of files in each category
- EXIF data correctness
- GPS data presence (where expected)
- File size and format

### Deployment to Pi

Fixtures should be generated directly on the Pi server:

```bash
# SSH to Pi
ssh pi@mothbox.lazare.nz

# Navigate to Firmware directory
cd /opt/mothbox/Firmware  # or ~/Desktop/Mothbox for legacy install

# Generate fixtures
python Tests/fixtures/create_test_photos.py

# Verify
python Tests/fixtures/create_test_photos.py --verify-only
```

## Using in E2E Tests

### Graceful Skipping

Tests should handle cases where fixtures aren't available:

```javascript
test('displays GPS coordinates', async () => {
  // Check if GPS data exists
  const hasGPS = await lightbox.hasGPSCoordinates()
  if (!hasGPS) {
    test.skip(true, 'No photos with GPS available')
    return
  }

  // Test GPS display
  const gpsText = await lightbox.getGPSText()
  expect(gpsText).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)
})
```

### Series Detection Testing

```javascript
test('detects HDR series', async () => {
  // Check if photo is part of series
  const isSeries = await lightbox.isPartOfSeries()
  if (!isSeries) {
    test.skip(true, 'No series photos available')
    return
  }

  // Verify series indicator
  const seriesText = await lightbox.getSeriesIndicatorText()
  expect(seriesText).toMatch(/HDR Series: \d+\/\d+/)
})
```

### Clipboard Testing

Clipboard operations require permissions:

```javascript
test('copies GPS coordinates', async ({ page, context }) => {
  // Grant clipboard permissions
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])

  // Check GPS availability
  const hasGPS = await lightbox.hasGPSCoordinates()
  if (!hasGPS) {
    test.skip(true, 'No photos with GPS available')
    return
  }

  // Copy coordinates
  const copied = await lightbox.copyCoordinatesToClipboard()
  expect(copied).toBeTruthy()

  // Verify clipboard content
  const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
  expect(clipboardText).toMatch(/°/)
})
```

## Visual Identification

Each category uses distinct colors for easy identification during test debugging:

| Category | Colors | Purpose |
|----------|--------|---------|
| with-gps | Blue (#0066CC), Teal (#009966) | GPS testing |
| without-gps | Magenta (#CC0066) | Missing GPS testing |
| hdr-series | Orange (#FF9900), Yellow (#FFCC00), Light Yellow (#FFFF66) | HDR series |
| focus-bracket | Purple shades (#9966FF → #FFE5CC) | Focus bracket series |

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

## Implementation Notes

### Dependencies

```bash
pip install Pillow piexif
```

### Mothbox GPS Integration

The fixture generator uses the existing Mothbox GPS EXIF infrastructure:

1. **Image Creation**: PIL creates 100×100 JPEG images with solid colors
2. **Camera EXIF**: piexif embeds standard camera metadata
3. **GPS EXIF**: `webui.backend.lib.gps_exif_lib.embed_gps_exif()` adds GPS tags
4. **Verification**: `verify_gps_exif()` confirms correct embedding

This ensures fixtures match real Mothbox photo EXIF structure and are compatible with the production GPS EXIF workflow.

### EXIF Tag Format

GPS coordinates are stored using EXIF GPS tags:

- **GPSLatitude/GPSLongitude**: Degrees, minutes, seconds (DMS) tuples
- **GPSLatitudeRef/GPSLongitudeRef**: 'N', 'S', 'E', 'W'
- **GPSAltitude**: Meters above sea level (rational)
- **GPSAltitudeRef**: 0 (above sea level)

## Related Documentation

- [GPS EXIF Service Guide](../../GPS_EXIF_SERVICE.md) - GPS EXIF tagging system
- [GPS EXIF User Guide](../../GPS_EXIF_USER_GUIDE.md) - Usage and batch processing
- [E2E Testing Guide](./e2e-testing.md) - Complete E2E testing guide
- [Lightbox Page Object](../../../frontend/e2e/pages/LIGHTBOX_PAGE_USAGE.md) - Page object API
- [Series Detection API](../api/gallery.md) - Series endpoints documentation
- [Test Fixtures README](../../../../Tests/fixtures/README.md) - Fixture generation details
