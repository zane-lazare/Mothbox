# Lightbox Page Object - Updated API

## Overview
The `lightbox.page.js` page object has been updated to match the actual MetadataPanel implementation with accordion sections (not tabs).

## Breaking Changes

### Old Tab Selectors (REMOVED)
```javascript
// ❌ REMOVED - These selectors no longer exist
cameraTab: '[role="tab"]:has-text("Camera")'
locationTab: '[role="tab"]:has-text("Location")'
captureTab: '[role="tab"]:has-text("Capture")'
tagsTab: '[role="tab"]:has-text("Tags")'
deploymentTab: '[role="tab"]:has-text("Deployment")'
```

### New Accordion Section Selectors
```javascript
// ✅ NEW - Matches actual MetadataPanel structure
tagsSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Tags")'
speciesSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Species")'
notesSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Notes")'
exifSection: '[data-testid="metadata-panel"] [role="button"]:has-text("EXIF Data")'
customFieldsSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Custom Fields")'
```

## New Selectors

### GPS/EXIF Selectors
```javascript
gpsCoordinates: 'text=/\\d+\\.\\d+°\\s*[NS],\\s*\\d+\\.\\d+°\\s*[EW]/'
altitudeDisplay: 'text=/\\d+(\\.\\d+)?m/'
copyButton: 'button[aria-label*="Copy"]'
```

### Series Indicators
```javascript
seriesIndicator: '[data-testid="series-indicator"]'
seriesCounter: '[data-testid="series-counter"]'
```

## New Methods

### Section Expansion Methods

#### `clickMetadataSection(sectionName)`
Click a metadata section to expand/collapse (accordion pattern).

**Parameters:**
- `sectionName`: `'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'`

**Example:**
```javascript
await lightbox.clickMetadataSection('EXIF Data')
```

#### `expandSection(sectionName)`
Expand a metadata section (if not already expanded).

**Parameters:**
- `sectionName`: `'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'`

**Example:**
```javascript
await lightbox.expandSection('EXIF Data')
```

#### `isSectionExpanded(sectionName)`
Check if a metadata section is expanded.

**Returns:** `Promise<boolean>`

**Example:**
```javascript
const isExpanded = await lightbox.isSectionExpanded('EXIF Data')
expect(isExpanded).toBeTruthy()
```

#### `getSectionContent(sectionName)`
Get text content of a metadata section (auto-expands if needed).

**Returns:** `Promise<string|null>`

**Example:**
```javascript
const content = await lightbox.getSectionContent('EXIF Data')
expect(content).toContain('Arducam')
```

### GPS Methods

#### `hasGPSCoordinates()`
Check if GPS coordinates are displayed.

**Returns:** `Promise<boolean>`

**Example:**
```javascript
const hasGPS = await lightbox.hasGPSCoordinates()
if (hasGPS) {
  // Test GPS-related features
}
```

#### `getGPSText()`
Get GPS coordinates text in format "37.7749° N, 122.4194° W".

**Returns:** `Promise<string|null>`

**Example:**
```javascript
const gps = await lightbox.getGPSText()
expect(gps).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)
```

#### `copyCoordinatesToClipboard()`
Copy GPS coordinates to clipboard.

**Returns:** `Promise<boolean>` - True if copy succeeded

**Example:**
```javascript
const copied = await lightbox.copyCoordinatesToClipboard()
expect(copied).toBeTruthy()
```

### EXIF Methods

#### `getEXIFFieldValue(fieldLabel)`
Get EXIF field value by label.

**Parameters:**
- `fieldLabel`: `'Make' | 'Model' | 'Lens' | 'ISO' | 'Shutter Speed' | 'Aperture' | 'Focal Length' | 'Exposure Mode' | 'White Balance' | 'Captured' | 'GPS' | 'Altitude' | 'Deployment' | 'Device'`

**Returns:** `Promise<string|null>` - Field value or null if "N/A" or not found

**Example:**
```javascript
const make = await lightbox.getEXIFFieldValue('Make')
expect(make).toBe('Arducam')

const iso = await lightbox.getEXIFFieldValue('ISO')
expect(iso).toMatch(/ISO \d+/)

const altitude = await lightbox.getEXIFFieldValue('Altitude')
expect(altitude).toMatch(/\d+m/)
```

### Series Methods

#### `isPartOfSeries()`
Check if photo is part of a series (HDR or Focus Bracket).

**Returns:** `Promise<boolean>`

**Example:**
```javascript
const isSeries = await lightbox.isPartOfSeries()
if (isSeries) {
  const text = await lightbox.getSeriesIndicatorText()
  expect(text).toMatch(/HDR Series|Focus Bracket/)
}
```

#### `getSeriesIndicatorText()`
Get series indicator text (e.g., "HDR Series: 3/5" or "Focus Bracket: 2/7").

**Returns:** `Promise<string|null>`

**Example:**
```javascript
const seriesText = await lightbox.getSeriesIndicatorText()
expect(seriesText).toBe('HDR Series: 3/5')
```

## Deprecated Methods

### `clickMetadataTab(tabName)` - DEPRECATED
**Status:** Deprecated but maintained for backward compatibility

The old `clickMetadataTab` method now maps old tab names to new section names:
- `'Camera'` → `'EXIF Data'`
- `'Location'` → `'EXIF Data'`
- `'Capture'` → `'EXIF Data'`
- `'Tags'` → `'Tags'`
- `'Deployment'` → `'EXIF Data'`

**Migration:**
```javascript
// ❌ Old (deprecated)
await lightbox.clickMetadataTab('Camera')

// ✅ New
await lightbox.clickMetadataSection('EXIF Data')
```

## Complete Test Examples

### Example 1: Test GPS Coordinates Display
```javascript
test('displays GPS coordinates in EXIF section', async () => {
  const photoCount = await gallery.getPhotoCount()
  if (photoCount === 0) {
    test.skip(true, 'No photos available')
    return
  }

  // Open lightbox
  await gallery.clickPhoto(0)
  await lightbox.waitForOpen()

  // Check if GPS data exists
  const hasGPS = await lightbox.hasGPSCoordinates()
  if (!hasGPS) {
    test.skip(true, 'Photo has no GPS data')
    return
  }

  // Get GPS text
  const gps = await lightbox.getGPSText()
  expect(gps).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)

  // Test copy functionality
  const copied = await lightbox.copyCoordinatesToClipboard()
  expect(copied).toBeTruthy()
})
```

### Example 2: Test EXIF Metadata Fields
```javascript
test('displays camera EXIF metadata', async () => {
  await gallery.clickPhoto(0)
  await lightbox.waitForOpen()

  // Expand EXIF section
  await lightbox.expandSection('EXIF Data')

  // Verify camera metadata
  const make = await lightbox.getEXIFFieldValue('Make')
  expect(make).toBeTruthy()

  const model = await lightbox.getEXIFFieldValue('Model')
  expect(model).toBeTruthy()

  // Verify capture settings
  const iso = await lightbox.getEXIFFieldValue('ISO')
  if (iso) {
    expect(iso).toMatch(/ISO \d+/)
  }

  const aperture = await lightbox.getEXIFFieldValue('Aperture')
  if (aperture) {
    expect(aperture).toMatch(/f\/\d+/)
  }
})
```

### Example 3: Test HDR Series Detection
```javascript
test('displays HDR series indicator', async () => {
  // Find an HDR series photo (you may need to filter in gallery first)
  await gallery.clickPhoto(0)
  await lightbox.waitForOpen()

  // Check if part of series
  const isSeries = await lightbox.isPartOfSeries()
  if (!isSeries) {
    test.skip(true, 'Photo is not part of a series')
    return
  }

  // Get series information
  const seriesText = await lightbox.getSeriesIndicatorText()
  expect(seriesText).toMatch(/HDR Series: \d+\/\d+|Focus Bracket: \d+\/\d+/)
})
```

### Example 4: Test Section Expansion
```javascript
test('accordion sections expand and collapse', async () => {
  await gallery.clickPhoto(0)
  await lightbox.waitForOpen()

  // Tags section should be expanded by default
  const tagsExpanded = await lightbox.isSectionExpanded('Tags')
  expect(tagsExpanded).toBeTruthy()

  // EXIF section should be collapsed by default
  const exifExpanded = await lightbox.isSectionExpanded('EXIF Data')
  expect(exifExpanded).toBeFalsy()

  // Expand EXIF section
  await lightbox.expandSection('EXIF Data')

  // Verify it's now expanded
  const nowExpanded = await lightbox.isSectionExpanded('EXIF Data')
  expect(nowExpanded).toBeTruthy()

  // Click to collapse
  await lightbox.clickMetadataSection('EXIF Data')

  // Verify it's collapsed
  const nowCollapsed = await lightbox.isSectionExpanded('EXIF Data')
  expect(nowCollapsed).toBeFalsy()
})
```

## Migration Guide

### Before (Incorrect Selectors)
```javascript
// ❌ These don't work because tabs don't exist
await lightbox.clickMetadataTab('Camera')
const cameraTab = page.locator('[role="tab"]:has-text("Camera")')
```

### After (Correct Accordion Sections)
```javascript
// ✅ Use accordion sections
await lightbox.clickMetadataSection('EXIF Data')
const exifSection = page.locator('[data-testid="metadata-panel"] [role="button"]:has-text("EXIF Data")')

// ✅ Or use the new methods
await lightbox.expandSection('EXIF Data')
const make = await lightbox.getEXIFFieldValue('Make')
```

## Reference Files
- **Implementation:** `webui/frontend/src/components/metadata/MetadataPanel.jsx` (lines 272-306)
- **EXIF Component:** `webui/frontend/src/components/metadata/MetadataEXIF.jsx`
- **Accordion Component:** `webui/frontend/src/components/metadata/AccordionSection.jsx`
- **Test Examples:** `webui/frontend/e2e/tests/lightbox-navigation.spec.js`
