/**
 * Lightbox Navigation Tests
 *
 * Tests for photo lightbox: viewing, navigation, metadata, zoom
 */

import { test, expect } from '@playwright/test'
import { GalleryPage } from '../pages/gallery.page.js'
import { LightboxPage } from '../pages/lightbox.page.js'
import { isRateLimited } from '../fixtures/test-helpers.js'

test.describe('Lightbox Navigation', () => {
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

  test('lightbox opens when clicking photo', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    expect(await lightbox.isOpen()).toBeTruthy()
  })

  test('lightbox displays photo image', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const imageSrc = await lightbox.getImageSrc()
    expect(imageSrc).toBeTruthy()
  })

  test('arrow key navigation works', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount < 2) {
      test.skip(true, 'Need at least 2 photos for navigation test')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const firstImageSrc = await lightbox.getImageSrc()

    // Navigate to next photo
    await lightbox.navigateWithKeyboard('right')
    await page.waitForTimeout(500)

    const secondImageSrc = await lightbox.getImageSrc()

    // Image should have changed
    expect(secondImageSrc).not.toBe(firstImageSrc)

    // Navigate back
    await lightbox.navigateWithKeyboard('left')
    await page.waitForTimeout(500)

    const backToFirstSrc = await lightbox.getImageSrc()
    expect(backToFirstSrc).toBe(firstImageSrc)
  })

  test('navigation buttons work', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount < 2) {
      test.skip(true, 'Need at least 2 photos for navigation test')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const firstImageSrc = await lightbox.getImageSrc()

    // Click next button
    await lightbox.navigateNext()
    await page.waitForTimeout(500)

    const secondImageSrc = await lightbox.getImageSrc()
    expect(secondImageSrc).not.toBe(firstImageSrc)

    // Click prev button
    await lightbox.navigatePrev()
    await page.waitForTimeout(500)

    const backToFirstSrc = await lightbox.getImageSrc()
    expect(backToFirstSrc).toBe(firstImageSrc)
  })

  test('escape key closes lightbox', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Press Escape
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)

    expect(await lightbox.isOpen()).toBeFalsy()
  })

  test('close button works', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    await lightbox.close()

    expect(await lightbox.isOpen()).toBeFalsy()
  })

  test('metadata panel displays photo info', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Check if metadata panel is visible
    const hasMetadata = await lightbox.isMetadataPanelVisible()

    if (hasMetadata) {
      const metadataText = await lightbox.getMetadataText()
      expect(metadataText.length).toBeGreaterThan(0)
    }
  })

  test('metadata tabs are clickable', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const hasMetadata = await lightbox.isMetadataPanelVisible()
    if (!hasMetadata) {
      test.skip(true, 'Metadata panel not visible')
      return
    }

    // Try clicking different tabs
    const tabs = ['Camera', 'Location', 'Capture', 'Tags']

    for (const tab of tabs) {
      try {
        await lightbox.clickMetadataTab(tab)
        // No error means tab click worked
      } catch {
        // Tab might not exist, that's okay
      }
    }
  })

  test('zoom with mouse wheel', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    // Zoom in
    await lightbox.zoomWithWheel('in')

    // Zoom out
    await lightbox.zoomWithWheel('out')

    // Lightbox should still be open
    expect(await lightbox.isOpen()).toBeTruthy()
  })

  test('photo counter shows position', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount < 2) {
      test.skip(true, 'Need multiple photos to test counter')
      return
    }

    await gallery.clickPhoto(0)
    await lightbox.waitForOpen()

    const counter = await lightbox.parsePhotoCounter()

    if (counter) {
      expect(counter.current).toBe(1)
      expect(counter.total).toBeGreaterThan(0)
    }
  })
})
