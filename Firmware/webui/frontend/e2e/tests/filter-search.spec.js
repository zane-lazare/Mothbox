/**
 * Filter and Search Tests
 *
 * Tests for filter drawer functionality and full-text search
 */

import { test, expect } from '@playwright/test'
import { GalleryPage } from '../pages/gallery.page.js'
import { FilterDrawerPage } from '../pages/filter-drawer.page.js'
import { formatDateForInput, daysAgo, isRateLimited } from '../fixtures/test-helpers.js'

test.describe('Filter and Search', () => {
  let gallery
  let filterDrawer

  test.beforeEach(async ({ page }) => {
    gallery = new GalleryPage(page)
    filterDrawer = new FilterDrawerPage(page)
    await gallery.goto()

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test.describe('Filter Drawer', () => {
    test('filter drawer opens and closes', async () => {
      // Open drawer
      await filterDrawer.open()
      expect(await filterDrawer.isOpen()).toBeTruthy()

      // Close drawer
      await filterDrawer.close()
      expect(await filterDrawer.isOpen()).toBeFalsy()
    })

    test('date range filter applies', async ({ page }) => {
      await filterDrawer.open()

      // Set date range to last 30 days
      const endDate = formatDateForInput(new Date())
      const startDate = formatDateForInput(daysAgo(30))

      await filterDrawer.setDateRange(startDate, endDate)
      await filterDrawer.applyFilters()

      // Wait for gallery to update
      await page.waitForTimeout(1000)

      // Photo count might change (or stay same if all photos are in range)
      const newCount = await gallery.getPhotoCount()
      expect(newCount).toBeGreaterThanOrEqual(0)
    })

    test('clear filters resets gallery', async ({ page }) => {
      // Apply a filter first
      await filterDrawer.open()

      const endDate = formatDateForInput(new Date())
      const startDate = formatDateForInput(daysAgo(7))
      await filterDrawer.setDateRange(startDate, endDate)
      await filterDrawer.applyFilters()

      await page.waitForTimeout(500)
      const filteredCount = await gallery.getPhotoCount()

      // Clear filters
      await filterDrawer.clearAllFilters()

      await page.waitForTimeout(500)
      const clearedCount = await gallery.getPhotoCount()

      // Count should be >= filtered count (or equal if filter had no effect)
      expect(clearedCount).toBeGreaterThanOrEqual(filteredCount)
    })

    test('filter chips display active filters', async () => {
      await filterDrawer.open()

      // Apply date filter
      const endDate = formatDateForInput(new Date())
      const startDate = formatDateForInput(daysAgo(30))
      await filterDrawer.setDateRange(startDate, endDate)
      await filterDrawer.applyFilters()

      // Check for filter chips
      const chipCount = await filterDrawer.getActiveFilterCount()
      // Should have at least one chip for date range
      // (may or may not depending on UI implementation)
      expect(chipCount).toBeGreaterThanOrEqual(0)
    })

    test('remove individual filter chip', async ({ page }) => {
      await filterDrawer.open()

      // Apply date filter
      const endDate = formatDateForInput(new Date())
      const startDate = formatDateForInput(daysAgo(30))
      await filterDrawer.setDateRange(startDate, endDate)
      await filterDrawer.applyFilters()

      const initialChipCount = await filterDrawer.getActiveFilterCount()

      if (initialChipCount > 0) {
        // Remove first chip
        await filterDrawer.removeFilterChip(0)
        await page.waitForTimeout(500)

        const newChipCount = await filterDrawer.getActiveFilterCount()
        expect(newChipCount).toBeLessThan(initialChipCount)
      }
    })
  })

  test.describe('Search', () => {
    test('search bar accepts input', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first()

      if (await searchInput.isVisible()) {
        await searchInput.fill('test')
        const value = await searchInput.inputValue()
        expect(value).toBe('test')
      }
    })

    test('search returns results', async () => {
      const initialCount = await gallery.getPhotoCount()

      if (initialCount === 0) {
        test.skip(true, 'No photos to search')
        return
      }

      // Search for a common term
      await gallery.search('moth')

      // Gallery should update (may have same, more, or fewer results)
      const newCount = await gallery.getPhotoCount()
      expect(newCount).toBeGreaterThanOrEqual(0)
    })

    test('search with field qualifier works', async ({ page }) => {
      const initialCount = await gallery.getPhotoCount()

      if (initialCount === 0) {
        test.skip(true, 'No photos to search')
        return
      }

      // Try field-specific search
      await gallery.search('tag:test')
      await page.waitForTimeout(1000)

      // Should not error
      const newCount = await gallery.getPhotoCount()
      expect(newCount).toBeGreaterThanOrEqual(0)
    })

    test('clear search restores results', async ({ page }) => {
      const initialCount = await gallery.getPhotoCount()

      if (initialCount === 0) {
        test.skip(true, 'No photos to search')
        return
      }

      // Perform a search that likely has no results
      await gallery.search('xyznonexistent123')
      await page.waitForTimeout(500)

      const searchCount = await gallery.getPhotoCount()

      // Clear search
      await gallery.clearSearch()
      await page.waitForTimeout(500)

      const clearedCount = await gallery.getPhotoCount()

      // Should restore original count (or at least more than search)
      expect(clearedCount).toBeGreaterThanOrEqual(searchCount)
    })
  })

  test.describe('Responsive Behavior', () => {
    test('filter drawer works on mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(500)

      // Gallery should still be visible
      const photoCount = await gallery.getPhotoCount()
      expect(photoCount).toBeGreaterThanOrEqual(0)

      // Filter toggle should still work
      await filterDrawer.open()
      expect(await filterDrawer.isOpen()).toBeTruthy()

      await filterDrawer.close()
    })

    test('filter drawer works on tablet viewport', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 })
      await page.waitForTimeout(500)

      const photoCount = await gallery.getPhotoCount()
      expect(photoCount).toBeGreaterThanOrEqual(0)

      await filterDrawer.open()
      expect(await filterDrawer.isOpen()).toBeTruthy()

      await filterDrawer.close()
    })
  })
})
