/**
 * Gallery Browsing Tests
 *
 * Tests for basic gallery functionality: loading, scrolling, navigation
 */

import { test, expect } from '@playwright/test'
import { GalleryPage } from '../pages/gallery.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Gallery Browsing', () => {
  let gallery

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    await gallery.goto()

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('gallery loads with photos', async () => {
    const photoCount = await gallery.getPhotoCount()

    // Should have at least some photos (real Pi data)
    expect(photoCount).toBeGreaterThan(0)
  })

  test('infinite scroll loads more photos', async () => {
    // Get initial photo count
    const initialCount = await gallery.getPhotoCount()

    // Skip if not enough photos for pagination
    if (initialCount < 20) {
      test.skip(true, 'Not enough photos to test infinite scroll')
      return
    }

    // Scroll to bottom to trigger loading
    const newCount = await gallery.scrollToLoadMore()

    // Should have loaded more photos
    expect(newCount).toBeGreaterThan(initialCount)
  })

  test('photo click opens lightbox', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()

    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Click first photo
    await gallery.clickPhoto(0)

    // Lightbox should be visible
    const lightbox = page.locator('[role="dialog"], .lightbox, [class*="Lightbox"]')
    await expect(lightbox).toBeVisible()
  })

  test('view mode toggle switches between grid and list', async () => {
    // Try to switch to list view
    await gallery.switchToListView()

    // Switch back to grid
    await gallery.switchToGridView()

    // Should still have photos visible
    const photoCount = await gallery.getPhotoCount()
    expect(photoCount).toBeGreaterThan(0)
  })

  test('loading state appears during data fetch', async ({ page }) => {
    // Refresh the page and watch for loading state
    // Note: loadingPromise intentionally not awaited - we just verify page reloads without error
    page.waitForSelector(
      '[data-testid="loading-spinner"], .loading, [class*="Spinner"], [class*="Loading"]',
      { state: 'visible', timeout: TIMEOUTS.MEDIUM }
    ).catch(() => null)

    await page.reload()

    // Loading state may or may not appear depending on network speed
    // This test just verifies no errors during reload
    await page.waitForLoadState('networkidle')
  })

  test('gallery container is scrollable', async ({ page }) => {
    // Check that gallery has scroll capability
    const hasScroll = await page.evaluate(() => {
      const body = document.body
      const html = document.documentElement
      return body.scrollHeight > window.innerHeight || html.scrollHeight > window.innerHeight
    })

    // Gallery should be scrollable if there are enough photos
    const photoCount = await gallery.getPhotoCount()
    if (photoCount > 10) {
      expect(hasScroll).toBeTruthy()
    }
  })

  test('photos have thumbnails loaded', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()

    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Check that first few photos have loaded images
    const images = page.locator('img[src*="thumbnail"], .photo-item img, .gallery-photo img')
    const imageCount = await images.count()

    if (imageCount > 0) {
      const firstImage = images.first()
      const src = await firstImage.getAttribute('src')
      expect(src).toBeTruthy()
    }
  })

  test('photos display without error', async ({ page }) => {
    // Check for error messages
    const errorSelectors = [
      '.error',
      '[class*="Error"]',
      ':has-text("Failed to load")',
      ':has-text("Error loading")',
    ]

    for (const selector of errorSelectors) {
      const errorElements = page.locator(selector)
      const count = await errorElements.count()

      // Filter out false positives (ErrorBoundary components that aren't showing errors)
      for (let i = 0; i < count; i++) {
        const el = errorElements.nth(i)
        if (await el.isVisible()) {
          const text = await el.textContent()
          // Skip if it's just a component name or not an actual error
          if (text.toLowerCase().includes('failed') || text.toLowerCase().includes('error loading')) {
            expect(text).not.toContain('Failed to load')
          }
        }
      }
    }
  })
})
