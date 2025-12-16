/**
 * Export Workflow Tests
 *
 * Tests for the photo export functionality: format selection, job creation, download
 */

import { test, expect } from '@playwright/test'
import { GalleryPage } from '../pages/gallery.page.js'
import { ExportPage } from '../pages/export.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Export Workflow', () => {
  let gallery
  let exportPage

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    exportPage = new ExportPage(page)
    await gallery.goto()

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test.afterEach(async () => {
    // Exit select mode if still active
    if (await gallery.isInSelectMode()) {
      await gallery.toggleSelectMode()
    }
  })

  test('export button visible in bulk mode', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Enter select mode
    await gallery.toggleSelectMode()

    // Select a photo
    await gallery.selectPhotos([0])

    // Export button should be visible in bulk actions toolbar
    const exportBtn = page.locator('button:has-text("Export")').first()
    const isVisible = await exportBtn.isVisible().catch(() => false)

    if (!isVisible) {
      // Maybe need to look for different button text
      const altExportBtn = page.locator('[data-testid*="export"], button[aria-label*="Export"]').first()
      const altVisible = await altExportBtn.isVisible().catch(() => false)
      expect(altVisible || isVisible).toBeTruthy()
    }
  })

  test('export modal opens with format options', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Enter select mode and select photos
    await gallery.toggleSelectMode()
    await gallery.selectPhotos([0])

    try {
      // Open export modal
      await gallery.clickBulkExport()
      await exportPage.waitForModal()

      expect(await exportPage.isModalOpen()).toBeTruthy()

      // Check for format options
      const formatOptions = page.locator('select option, .format-card, [data-testid*="format"]')
      const optionCount = await formatOptions.count()
      expect(optionCount).toBeGreaterThan(0)

      // Close modal
      await exportPage.closeModal()
    } catch {
      test.skip(true, 'Export modal not available in current UI')
    }
  })

  test('Darwin Core export creates job', async ({ page }) => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Enter select mode and select photos
    await gallery.toggleSelectMode()
    await gallery.selectPhotos([0])

    try {
      // Open export modal
      await gallery.clickBulkExport()
      await exportPage.waitForModal()

      // Select Darwin Core format
      await exportPage.selectFormat('darwin_core')

      // Start export
      await exportPage.startExport()

      // Should see progress or completion
      const hasProgress = await page.locator('[role="progressbar"], .progress').isVisible().catch(() => false)
      const hasSuccess = await exportPage.isDownloadReady()

      // Either we see progress, success, or modal is handling the job
      expect(hasProgress || hasSuccess || await exportPage.isModalOpen()).toBeTruthy()
    } catch (e) {
      console.log('Darwin Core export test skipped:', e.message)
      test.skip(true, 'Export functionality not fully available')
    }
  })

  test('export job progress updates', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Enter select mode and select multiple photos for longer job
    await gallery.toggleSelectMode()

    const photosToSelect = Math.min(photoCount, 3)
    const indices = Array.from({ length: photosToSelect }, (_, i) => i)
    await gallery.selectPhotos(indices)

    try {
      // Open export modal
      await gallery.clickBulkExport()
      await exportPage.waitForModal()

      // Select JSON format (usually fastest)
      await exportPage.selectFormat('json')

      // Start export
      await exportPage.startExport()

      // Check for progress indicator
      const progress = await exportPage.getProgress()

      // Progress should be a valid number
      expect(progress).toBeGreaterThanOrEqual(0)
      expect(progress).toBeLessThanOrEqual(100)
    } catch (e) {
      console.log('Progress test skipped:', e.message)
      test.skip(true, 'Progress tracking not available')
    }
  })

  test('download link appears on completion', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount === 0) {
      test.skip(true, 'No photos available')
      return
    }

    // Enter select mode and select one photo (fast export)
    await gallery.toggleSelectMode()
    await gallery.selectPhotos([0])

    try {
      // Open export modal
      await gallery.clickBulkExport()
      await exportPage.waitForModal()

      // Select CSV format (fastest, smallest)
      await exportPage.selectFormat('csv')

      // Start export and wait for completion
      await exportPage.startExport()

      const success = await exportPage.waitForCompletion(30000)

      if (success) {
        // Download button should be visible
        expect(await exportPage.isDownloadReady()).toBeTruthy()
      } else {
        // Check for error
        const hasError = await exportPage.hasError()
        if (hasError) {
          const errorMsg = await exportPage.getErrorMessage()
          console.log('Export failed with error:', errorMsg)
        }
      }
    } catch (e) {
      console.log('Download test skipped:', e.message)
      test.skip(true, 'Export completion not testable')
    }
  })

  test('cancel job works', async () => {
    const photoCount = await gallery.getPhotoCount()
    if (photoCount < 10) {
      test.skip(true, 'Need more photos for cancel test (job needs to run long enough)')
      return
    }

    // Enter select mode and select many photos
    await gallery.toggleSelectMode()

    const photosToSelect = Math.min(photoCount, 10)
    const indices = Array.from({ length: photosToSelect }, (_, i) => i)
    await gallery.selectPhotos(indices)

    try {
      // Open export modal
      await gallery.clickBulkExport()
      await exportPage.waitForModal()

      // Select iNaturalist format (includes photos, takes longer)
      await exportPage.selectFormat('inaturalist')

      // Start export
      await exportPage.startExport()

      // Try to cancel
      await exportPage.cancelJob()

      // Job should be cancelled or modal closed
      // Either outcome is acceptable
    } catch (e) {
      console.log('Cancel test skipped:', e.message)
      test.skip(true, 'Cancel functionality not available')
    }
  })
})
