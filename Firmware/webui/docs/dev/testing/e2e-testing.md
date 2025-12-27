# E2E Testing Guide (Playwright)

End-to-end tests using Playwright run against a real Mothbox Pi server using Firefox browser.

## Quick Start

```bash
cd webui/frontend

# Run all E2E tests
npm run test:e2e

# Run tests with browser visible (headed mode)
npm run test:e2e:headed

# Debug tests interactively
npm run test:e2e:debug

# Use Playwright UI mode for test development
npm run test:e2e:ui

# View test report after running
npm run test:e2e:report

# Run specific test file
npx playwright test smoke.spec.js

# Run tests matching pattern
npx playwright test --grep "Gallery"
```

## Configuration

**File**: `webui/frontend/playwright.config.js`

| Setting | Value | Reason |
|---------|-------|--------|
| Target | `http://mothbox.lazare.nz:5000` | Remote Pi server |
| Browser | Firefox only | User requirement |
| Timeout | 60 seconds | Accounts for network latency |
| Workers | 1 | Sequential execution against single Pi |
| Artifacts | Screenshots, videos, traces | Captured on failure |

## Test Structure

```
webui/frontend/e2e/
├── fixtures/
│   └── test-helpers.js       # Shared utilities (rate limit handling, date formatting)
├── pages/
│   ├── gallery.page.js       # Gallery page object (photo grid, selection mode)
│   ├── lightbox.page.js      # Lightbox page object (navigation, zoom, metadata)
│   ├── filter-drawer.page.js # Filter drawer page object (date, tags, species)
│   └── export.page.js        # Export workflow page object (format, progress)
└── tests/
    ├── smoke.spec.js           # Basic connectivity and API health (5 tests)
    ├── gallery-browsing.spec.js # Gallery loading, scroll, view modes (8 tests)
    ├── lightbox-navigation.spec.js # Photo viewing, navigation (10 tests)
    ├── filter-search.spec.js   # Filter drawer, search (12 tests)
    ├── bulk-operations.spec.js # Selection mode, bulk actions (9 tests)
    └── export-workflow.spec.js # Export job creation, download (6 tests)
```

## Page Object Pattern

Tests use page objects to encapsulate UI interactions:

```javascript
import { GalleryPage } from '../pages/gallery.page.js'

const gallery = new GalleryPage(page)
await gallery.goto()
await gallery.toggleSelectMode()
await gallery.selectPhotos([0, 1, 2])
await gallery.clickBulkExport()
```

## Rate Limiting

The Pi server has a 50 requests/hour limit. Tests automatically skip when rate limited:

```javascript
import { isRateLimited } from '../fixtures/test-helpers.js'

test.beforeEach(async ({ page }) => {
  if (await isRateLimited(page)) {
    test.skip(true, 'Rate limited by server (50/hour)')
  }
})
```

## Adding New Tests

1. Create page object in `e2e/pages/` if needed
2. Use aria-labels and role attributes for selectors (not class names)
3. Add rate limit handling in `beforeEach`
4. Handle "no photos" edge case with `test.skip()`
5. Run `npm run test:e2e:ui` to develop tests interactively

## Important Notes

- Tests run against **real data** on the Pi (not mocked)
- **Bulk delete is SKIPPED** to protect real photos
- Bulk tag tests use unique timestamped tags for cleanup
- Export tests are reversible (files auto-cleanup)

## Photo Viewer Testing

### Overview

E2E tests for the photo viewer workflow are in `e2e/tests/photo-viewer-exif.spec.js`. These tests verify EXIF metadata display, GPS coordinates, series detection, and navigation.

### Test Fixtures

Photo fixtures with controlled EXIF data enable reliable testing without depending on real photo content. See [E2E Photo Fixtures](./e2e-photo-fixtures.md) for complete documentation.

**Fixture categories:**
- `with-gps/` - Photos with GPS coordinates for testing coordinate display and copy
- `without-gps/` - Photos without GPS for testing graceful handling
- `hdr-series/` - HDR series for testing series detection and navigation
- `focus-bracket/` - Focus bracket series for multi-image navigation

### LightboxPage Methods

The `LightboxPage` page object provides methods for EXIF testing. See [Lightbox Page Usage](../../../frontend/e2e/pages/LIGHTBOX_PAGE_USAGE.md) for complete API.

**Accordion Section Methods:**
```javascript
await lightbox.expandSection('EXIF Data')
await lightbox.clickMetadataSection('Tags')
const isExpanded = await lightbox.isSectionExpanded('EXIF Data')
const content = await lightbox.getSectionContent('EXIF Data')
```

**GPS Methods:**
```javascript
const hasGPS = await lightbox.hasGPSCoordinates()
const gpsText = await lightbox.getGPSText()  // "9.15° N, 79.85° W"
await lightbox.copyCoordinatesToClipboard()
```

**EXIF Field Methods:**
```javascript
const make = await lightbox.getEXIFFieldValue('Make')
const iso = await lightbox.getEXIFFieldValue('ISO')
const altitude = await lightbox.getEXIFFieldValue('Altitude')
```

**Series Methods:**
```javascript
const isSeries = await lightbox.isPartOfSeries()
const seriesText = await lightbox.getSeriesIndicatorText()  // "HDR Series: 1/3"
```

### Graceful Skipping

Tests skip gracefully when required data isn't available:

```javascript
test('displays GPS coordinates', async () => {
  const hasGPS = await lightbox.hasGPSCoordinates()
  if (!hasGPS) {
    test.skip(true, 'No photos with GPS available')
    return
  }

  const gpsText = await lightbox.getGPSText()
  expect(gpsText).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)
})
```

### Clipboard Testing

Clipboard tests require browser permissions:

```javascript
test('copies GPS coordinates', async ({ page, context }) => {
  // Grant clipboard permissions
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])

  // Copy coordinates
  await lightbox.copyCoordinatesToClipboard()

  // Verify clipboard content
  const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
  expect(clipboardText).toMatch(/°/)
})
```

### Series Detection Testing

Series tests verify detection and navigation:

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

### EXIF Field Testing

Test camera metadata display:

```javascript
test('displays camera EXIF fields', async () => {
  await lightbox.expandSection('EXIF Data')

  // Verify camera metadata
  const make = await lightbox.getEXIFFieldValue('Make')
  expect(make).toBeTruthy()

  const model = await lightbox.getEXIFFieldValue('Model')
  expect(model).toBeTruthy()

  // Verify capture settings (may be N/A)
  const iso = await lightbox.getEXIFFieldValue('ISO')
  if (iso) {
    expect(iso).toMatch(/ISO \d+/)
  }
})
```

## Related Documentation

- [E2E Photo Fixtures](./e2e-photo-fixtures.md) - Test photo fixture system
- [Lightbox Page Usage](../../../frontend/e2e/pages/LIGHTBOX_PAGE_USAGE.md) - Lightbox page object API
- [Gallery Testing](./gallery-testing.md) - Unit and integration tests for gallery
- [Camera Hardware Testing](./camera-hardware-testing.md) - Hardware-specific tests
