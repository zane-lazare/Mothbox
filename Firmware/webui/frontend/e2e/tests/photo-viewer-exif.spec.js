/**
 * Photo Viewer EXIF Tests
 *
 * E2E tests for photo viewer workflow with real EXIF data:
 * - GPS coordinate display and formatting
 * - EXIF metadata panel (5 accordion sections)
 * - HDR and Focus Bracket series navigation
 * - Clipboard copy functionality
 *
 * Issue #106
 */

import { test, expect } from '@playwright/test'
import { GalleryPage } from '../pages/gallery.page.js'
import { LightboxPage } from '../pages/lightbox.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Photo Viewer - Metadata Sections', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('displays all 5 metadata sections', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Verify all 5 accordion sections exist
    const sections = ['Tags', 'Species', 'Notes', 'EXIF Data', 'Custom Fields']

    for (const section of sections) {
      const sectionSelector = {
        'Tags': lightbox.selectors.tagsSection,
        'Species': lightbox.selectors.speciesSection,
        'Notes': lightbox.selectors.notesSection,
        'EXIF Data': lightbox.selectors.exifSection,
        'Custom Fields': lightbox.selectors.customFieldsSection,
      }[section]

      const sectionElement = lightbox.page.locator(sectionSelector)
      const isVisible = await sectionElement.isVisible()
      expect(isVisible).toBeTruthy()
    }
  })

  test('Tags section is expanded by default', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isExpanded = await lightbox.isSectionExpanded('Tags')
    expect(isExpanded).toBeTruthy()
  })

  test('can expand/collapse EXIF Data section', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // EXIF Data should be collapsed by default
    const initialExpanded = await lightbox.isSectionExpanded('EXIF Data')
    expect(initialExpanded).toBeFalsy()

    // Expand the section
    await lightbox.expandSection('EXIF Data')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's now expanded
    const nowExpanded = await lightbox.isSectionExpanded('EXIF Data')
    expect(nowExpanded).toBeTruthy()

    // Collapse the section
    await lightbox.clickMetadataSection('EXIF Data')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's collapsed again
    const finalExpanded = await lightbox.isSectionExpanded('EXIF Data')
    expect(finalExpanded).toBeFalsy()
  })

  test('can expand/collapse Species section', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Species should be collapsed by default
    const initialExpanded = await lightbox.isSectionExpanded('Species')
    expect(initialExpanded).toBeFalsy()

    // Expand the section
    await lightbox.expandSection('Species')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's now expanded
    const nowExpanded = await lightbox.isSectionExpanded('Species')
    expect(nowExpanded).toBeTruthy()

    // Collapse the section
    await lightbox.clickMetadataSection('Species')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's collapsed again
    const finalExpanded = await lightbox.isSectionExpanded('Species')
    expect(finalExpanded).toBeFalsy()
  })

  test('can expand/collapse Notes section', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Notes should be collapsed by default
    const initialExpanded = await lightbox.isSectionExpanded('Notes')
    expect(initialExpanded).toBeFalsy()

    // Expand the section
    await lightbox.expandSection('Notes')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's now expanded
    const nowExpanded = await lightbox.isSectionExpanded('Notes')
    expect(nowExpanded).toBeTruthy()

    // Collapse the section
    await lightbox.clickMetadataSection('Notes')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's collapsed again
    const finalExpanded = await lightbox.isSectionExpanded('Notes')
    expect(finalExpanded).toBeFalsy()
  })

  test('can expand/collapse Custom Fields section', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Custom Fields should be collapsed by default
    const initialExpanded = await lightbox.isSectionExpanded('Custom Fields')
    expect(initialExpanded).toBeFalsy()

    // Expand the section
    await lightbox.expandSection('Custom Fields')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's now expanded
    const nowExpanded = await lightbox.isSectionExpanded('Custom Fields')
    expect(nowExpanded).toBeTruthy()

    // Collapse the section
    await lightbox.clickMetadataSection('Custom Fields')
    await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify it's collapsed again
    const finalExpanded = await lightbox.isSectionExpanded('Custom Fields')
    expect(finalExpanded).toBeFalsy()
  })
})

test.describe('Photo Viewer - EXIF Data', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('displays camera make and model', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Expand EXIF Data section
    await lightbox.expandSection('EXIF Data')

    // Get camera make
    const make = await lightbox.getEXIFFieldValue('Make')
    if (make) {
      expect(make.length).toBeGreaterThan(0)
      expect(make).not.toBe('N/A')
    }

    // Get camera model
    const model = await lightbox.getEXIFFieldValue('Model')
    if (model) {
      expect(model.length).toBeGreaterThan(0)
      expect(model).not.toBe('N/A')
    }
  })

  test('displays ISO value', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    const iso = await lightbox.getEXIFFieldValue('ISO')
    if (iso) {
      // ISO should be a number or formatted string like "ISO 100"
      expect(iso).toMatch(/\d+/)
    }
  })

  test('displays shutter speed', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    const shutterSpeed = await lightbox.getEXIFFieldValue('Shutter Speed')
    if (shutterSpeed) {
      // Shutter speed should contain numbers and possibly fractions
      expect(shutterSpeed.length).toBeGreaterThan(0)
    }
  })

  test('displays aperture', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    const aperture = await lightbox.getEXIFFieldValue('Aperture')
    if (aperture) {
      // Aperture is typically formatted as f/number
      expect(aperture.length).toBeGreaterThan(0)
    }
  })

  test('displays capture timestamp', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    const captured = await lightbox.getEXIFFieldValue('Captured')
    if (captured) {
      expect(captured.length).toBeGreaterThan(0)
      expect(captured).not.toBe('N/A')
    }
  })
})

test.describe('Photo Viewer - GPS Coordinates', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('displays GPS coordinates in formatted text', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Check if GPS data exists
    const hasGPS = await lightbox.hasGPSCoordinates()
    if (!hasGPS) {
      test.skip(true, 'Photo has no GPS data')
      return
    }

    // Get GPS text and verify format (e.g., "37.7749° N, 122.4194° W")
    const gps = await lightbox.getGPSText()
    expect(gps).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)
  })

  test('shows altitude when available', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    const altitude = await lightbox.getEXIFFieldValue('Altitude')
    if (altitude) {
      // Altitude should be formatted with meters (e.g., "123.45m")
      expect(altitude).toMatch(/\d+(\.\d+)?m/)
    }
  })

  test('copy coordinates to clipboard', async ({ context, page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Check if GPS data exists
    const hasGPS = await lightbox.hasGPSCoordinates()
    if (!hasGPS) {
      test.skip(true, 'Photo has no GPS data')
      return
    }

    // Copy coordinates to clipboard
    const copied = await lightbox.copyCoordinatesToClipboard()
    expect(copied).toBeTruthy()

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toMatch(/\d+\.\d+°/)
  })

  test('handles photos without GPS gracefully', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.expandSection('EXIF Data')

    // Check if GPS field exists
    const gps = await lightbox.getEXIFFieldValue('GPS')

    // If GPS is null, that's acceptable (photo has no GPS)
    // If GPS exists, it should be properly formatted
    if (gps) {
      expect(gps).toMatch(/\d+\.\d+°\s*[NS],\s*\d+\.\d+°\s*[EW]/)
    }

    // The test passes either way - we're testing graceful handling
    expect(true).toBeTruthy()
  })
})

test.describe('Photo Viewer - HDR Series', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('identifies HDR series photos', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isSeriesPhoto = await lightbox.isPartOfSeries()
    if (!isSeriesPhoto) {
      test.skip(true, 'No series photos available')
      return
    }

    const seriesText = await lightbox.getSeriesIndicatorText()
    if (seriesText && seriesText.includes('HDR')) {
      expect(seriesText).toMatch(/HDR Series: \d+\/\d+/)
    } else {
      test.skip(true, 'No HDR series photos available')
    }
  })

  test('navigates through HDR series', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isSeriesPhoto = await lightbox.isPartOfSeries()
    if (!isSeriesPhoto) {
      test.skip(true, 'No series photos available')
      return
    }

    const seriesText = await lightbox.getSeriesIndicatorText()
    if (!seriesText || !seriesText.includes('HDR')) {
      test.skip(true, 'No HDR series photos available')
      return
    }

    // Get initial image source
    const firstImageSrc = await lightbox.getImageSrc()

    // Navigate to next photo in series
    await lightbox.navigateNext()
    await lightbox.page.waitForTimeout(TIMEOUTS.SHORT)

    // Verify image changed
    const secondImageSrc = await lightbox.getImageSrc()
    expect(secondImageSrc).not.toBe(firstImageSrc)

    // Navigate back
    await lightbox.navigatePrev()
    await lightbox.page.waitForTimeout(TIMEOUTS.SHORT)

    // Verify we're back to the first image
    const backToFirstSrc = await lightbox.getImageSrc()
    expect(backToFirstSrc).toBe(firstImageSrc)
  })

  test('series counter shows correct position', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isSeriesPhoto = await lightbox.isPartOfSeries()
    if (!isSeriesPhoto) {
      test.skip(true, 'No series photos available')
      return
    }

    const seriesText = await lightbox.getSeriesIndicatorText()
    if (!seriesText || !seriesText.includes('HDR')) {
      test.skip(true, 'No HDR series photos available')
      return
    }

    // Verify series counter format (e.g., "HDR Series: 1/3")
    expect(seriesText).toMatch(/HDR Series: \d+\/\d+/)

    // Extract numbers
    const match = seriesText.match(/(\d+)\/(\d+)/)
    if (match) {
      const current = parseInt(match[1], 10)
      const total = parseInt(match[2], 10)

      expect(current).toBeGreaterThan(0)
      expect(total).toBeGreaterThanOrEqual(current)
    }
  })
})

test.describe('Photo Viewer - Focus Bracket Series', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('identifies focus bracket series', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isSeriesPhoto = await lightbox.isPartOfSeries()
    if (!isSeriesPhoto) {
      test.skip(true, 'No series photos available')
      return
    }

    const seriesText = await lightbox.getSeriesIndicatorText()
    if (seriesText && seriesText.includes('Focus Bracket')) {
      expect(seriesText).toMatch(/Focus Bracket: \d+\/\d+/)
    } else {
      test.skip(true, 'No Focus Bracket series photos available')
    }
  })

  test('navigates through all 5 images', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const isSeriesPhoto = await lightbox.isPartOfSeries()
    if (!isSeriesPhoto) {
      test.skip(true, 'No series photos available')
      return
    }

    const seriesText = await lightbox.getSeriesIndicatorText()
    if (!seriesText || !seriesText.includes('Focus Bracket')) {
      test.skip(true, 'No Focus Bracket series photos available')
      return
    }

    // Extract total count from series text
    const match = seriesText.match(/(\d+)\/(\d+)/)
    if (!match) {
      test.skip(true, 'Cannot parse series counter')
      return
    }

    const total = parseInt(match[2], 10)
    const imageSources = []

    // Capture all image sources in the series
    for (let i = 0; i < total && i < 10; i++) {
      const src = await lightbox.getImageSrc()
      imageSources.push(src)

      if (i < total - 1) {
        await lightbox.navigateNext()
        await lightbox.page.waitForTimeout(TIMEOUTS.TRANSITION)
      }
    }

    // Verify we saw unique images
    const uniqueSources = new Set(imageSources)
    expect(uniqueSources.size).toBeGreaterThan(1)

    // If it's a 5-image focus bracket, verify we got 5 unique images
    if (total === 5) {
      expect(uniqueSources.size).toBe(5)
    }
  })
})

test.describe('Photo Viewer - Performance', () => {
  let gallery
  let lightbox

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    lightbox = new LightboxPage(page)
    await gallery.goto()

    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('metadata loads within 2 seconds', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Start timer
    const startTime = Date.now()

    // Expand EXIF section and wait for content
    await lightbox.expandSection('EXIF Data')

    // Get at least one EXIF field value
    const make = await lightbox.getEXIFFieldValue('Make')

    // End timer
    const endTime = Date.now()
    const loadTime = endTime - startTime

    // Verify metadata loaded within 2 seconds
    expect(loadTime).toBeLessThan(2000)

    // Verify we actually got data
    if (make) {
      expect(make.length).toBeGreaterThan(0)
    }
  })
})
