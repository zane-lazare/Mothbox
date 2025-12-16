/**
 * Gallery Page Object
 *
 * Encapsulates interactions with the gallery page
 */

import { TIMEOUTS } from '../fixtures/test-helpers.js'

export class GalleryPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page

    // Selectors - using multiple fallbacks for flexibility
    this.selectors = {
      // Gallery container
      gallery: '[data-testid="gallery"], .gallery-container, [class*="Gallery"]',
      photoGrid: '[data-testid="photo-grid"], .photo-grid, [class*="PhotoGrid"]',

      // Photo items - actual components use button[aria-label*="View photo"]
      photoItem: 'button[aria-label*="View photo"], .group.relative button, [data-testid^="photo-item-"]',
      photoThumbnail: 'img[src*="thumbnail"], img[alt]',

      // Overlay/modal dismissal
      modalOverlay: '.fixed.inset-0.bg-black, [aria-hidden="true"].fixed',

      // View controls - ViewModeToggle uses aria-label="Grid/List/Map view"
      viewModeToggle: '[role="group"][aria-label="View mode toggle"]',
      gridViewButton: 'button[aria-label="Grid view"]',
      listViewButton: 'button[aria-label="List view"]',
      mapViewButton: 'button[aria-label="Map view"]',

      // Selection mode - SelectModeToggle uses aria-label="Enter/Exit selection mode"
      selectModeToggle: 'button[aria-label*="selection mode"], button:has-text("Select"):not(:has-text("All"))',
      selectAllButton: 'button:has-text("Select All")',
      selectedCount: '[data-testid="selected-count"], span:has-text("selected")',

      // Bulk actions toolbar
      bulkActionsToolbar: '[data-testid="bulk-actions-toolbar"], [class*="BulkActions"], .fixed.bottom-0',
      bulkTagButton: 'button:has-text("Tag"), button[aria-label*="Tag"]',
      bulkExportButton: 'button:has-text("Export"), button[aria-label*="Export"]',
      bulkDeleteButton: 'button:has-text("Delete"), button[aria-label*="Delete"]',

      // Filter drawer toggle - FilterDrawerToggle uses aria-label="Show filters"
      filterDrawerToggle: 'button[aria-label*="Show filters"], button[aria-label*="filter"]',

      // Search bar
      searchInput: 'input[placeholder*="Search"], input[type="search"]',

      // Loading states
      loadingSpinner: '[data-testid="loading-spinner"], .loading, [class*="Spinner"]',
      emptyState: '[data-testid="empty-state"], .empty-state, :has-text("No photos")',
    }
  }

  /**
   * Navigate to gallery page
   */
  async goto() {
    await this.page.goto('/gallery')
    await this.page.waitForLoadState('networkidle')
    await this.waitForLoad()
  }

  /**
   * Wait for gallery to finish loading
   */
  async waitForLoad() {
    // Wait for loading to finish
    try {
      await this.page.waitForSelector(this.selectors.loadingSpinner, {
        state: 'hidden',
        timeout: TIMEOUTS.MEDIUM,
      })
    } catch {
      // Spinner might not appear
    }

    // Wait for network to settle
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Dismiss any open modals/overlays that might block interactions
   */
  async dismissOverlays() {
    // Try pressing Escape to close any modals
    await this.page.keyboard.press('Escape')

    // Wait for overlay to be hidden (if it exists)
    const overlay = this.page.locator(this.selectors.modalOverlay).first()
    try {
      await overlay.waitFor({ state: 'hidden', timeout: TIMEOUTS.SHORT })
    } catch {
      // Overlay might not exist or already hidden
    }
  }

  /**
   * Get number of visible photos
   * @returns {Promise<number>}
   */
  async getPhotoCount() {
    return this.page.locator(this.selectors.photoItem).count()
  }

  /**
   * Check if gallery has photos
   * @returns {Promise<boolean>}
   */
  async hasPhotos() {
    const count = await this.getPhotoCount()
    return count > 0
  }

  /**
   * Check if empty state is visible
   * @returns {Promise<boolean>}
   */
  async isEmptyStateVisible() {
    return this.page.locator(this.selectors.emptyState).isVisible()
  }

  /**
   * Click on a photo by index to open lightbox
   * @param {number} index - Zero-based index
   */
  async clickPhoto(index) {
    const photos = this.page.locator(this.selectors.photoItem)
    await photos.nth(index).click()
    // Wait for lightbox to open
    await this.page.waitForSelector('[role="dialog"], .lightbox, [class*="Lightbox"]', {
      timeout: TIMEOUTS.MEDIUM,
    })
  }

  /**
   * Scroll to bottom to trigger infinite scroll
   * @returns {Promise<number>} - New photo count after scroll
   */
  async scrollToLoadMore() {
    const initialCount = await this.getPhotoCount()

    await this.page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight)
    })

    // Wait for more photos to load (count increases) or network settles
    try {
      await this.page.waitForFunction(
        (selector, prevCount) => document.querySelectorAll(selector).length > prevCount,
        this.selectors.photoItem,
        initialCount,
        { timeout: TIMEOUTS.MEDIUM }
      )
    } catch {
      // May not load more if at end of list
    }

    await this.waitForLoad()
    return this.getPhotoCount()
  }

  /**
   * Toggle select mode on/off
   */
  async toggleSelectMode() {
    const wasInSelectMode = await this.isInSelectMode()
    await this.page.click(this.selectors.selectModeToggle)

    // Wait for mode to toggle (toolbar appears/disappears)
    const toolbar = this.page.locator(this.selectors.bulkActionsToolbar)
    if (wasInSelectMode) {
      await toolbar.waitFor({ state: 'hidden', timeout: TIMEOUTS.SHORT }).catch(() => {})
    } else {
      await toolbar.waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
    }
  }

  /**
   * Check if in select mode
   * @returns {Promise<boolean>}
   */
  async isInSelectMode() {
    return this.page.locator(this.selectors.bulkActionsToolbar).isVisible()
  }

  /**
   * Select photos by indices
   * @param {number[]} indices - Array of zero-based indices
   */
  async selectPhotos(indices) {
    const photos = this.page.locator(this.selectors.photoItem)

    for (const index of indices) {
      // Ctrl+click for multi-select
      await photos.nth(index).click({ modifiers: ['Control'] })
    }
  }

  /**
   * Select range of photos with shift+click
   * @param {number} startIndex
   * @param {number} endIndex
   */
  async selectRange(startIndex, endIndex) {
    const photos = this.page.locator(this.selectors.photoItem)

    // Click first photo
    await photos.nth(startIndex).click()

    // Shift+click last photo
    await photos.nth(endIndex).click({ modifiers: ['Shift'] })
  }

  /**
   * Click select all button
   */
  async selectAll() {
    await this.page.click(this.selectors.selectAllButton)
    // Wait for selection count to update
    await this.page.locator(this.selectors.selectedCount).waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }

  /**
   * Get count of selected photos
   * @returns {Promise<number>}
   */
  async getSelectedCount() {
    const countEl = this.page.locator(this.selectors.selectedCount)
    if (await countEl.isVisible()) {
      const text = await countEl.textContent()
      const match = text.match(/\d+/)
      return match ? parseInt(match[0], 10) : 0
    }
    return 0
  }

  /**
   * Open filter drawer
   */
  async openFilterDrawer() {
    await this.page.click(this.selectors.filterDrawerToggle)
    // Wait for filter drawer to be visible
    await this.page.locator('aside[role="complementary"][aria-label="Filters"]')
      .waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }

  /**
   * Type in search bar
   * @param {string} query
   */
  async search(query) {
    await this.page.fill(this.selectors.searchInput, query)
    await this.page.press(this.selectors.searchInput, 'Enter')
    await this.waitForLoad()
  }

  /**
   * Clear search
   */
  async clearSearch() {
    await this.page.fill(this.selectors.searchInput, '')
    await this.page.press(this.selectors.searchInput, 'Enter')
    await this.waitForLoad()
  }

  /**
   * Switch to grid view
   */
  async switchToGridView() {
    await this.dismissOverlays()
    const button = this.page.locator(this.selectors.gridViewButton)
    await button.click({ force: true })
    // Wait for button to show pressed state
    await button.getAttribute('aria-pressed').then(async (pressed) => {
      if (pressed !== 'true') {
        await this.page.waitForFunction(
          (sel) => document.querySelector(sel)?.getAttribute('aria-pressed') === 'true',
          this.selectors.gridViewButton,
          { timeout: TIMEOUTS.SHORT }
        ).catch(() => {})
      }
    })
  }

  /**
   * Switch to list view
   */
  async switchToListView() {
    await this.dismissOverlays()
    const button = this.page.locator(this.selectors.listViewButton)
    await button.click({ force: true })
    // Wait for button to show pressed state
    await button.getAttribute('aria-pressed').then(async (pressed) => {
      if (pressed !== 'true') {
        await this.page.waitForFunction(
          (sel) => document.querySelector(sel)?.getAttribute('aria-pressed') === 'true',
          this.selectors.listViewButton,
          { timeout: TIMEOUTS.SHORT }
        ).catch(() => {})
      }
    })
  }

  /**
   * Click bulk tag button
   */
  async clickBulkTag() {
    await this.page.click(this.selectors.bulkTagButton)
    // Wait for modal to appear
    await this.page.locator('[role="dialog"]').waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }

  /**
   * Click bulk export button
   */
  async clickBulkExport() {
    await this.page.click(this.selectors.bulkExportButton)
    // Wait for modal to appear
    await this.page.locator('[role="dialog"]').waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }
}
