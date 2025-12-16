/**
 * Filter Drawer Page Object
 *
 * Encapsulates interactions with the gallery filter drawer
 */

import { TIMEOUTS } from '../fixtures/test-helpers.js'

export class FilterDrawerPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page

    // Selectors - Based on actual FilterDrawer.jsx component
    this.selectors = {
      // Drawer container - uses role="complementary" with aria-label="Filters"
      drawer: 'aside[role="complementary"][aria-label="Filters"]',
      drawerOverlay: '.fixed.inset-0.bg-black\\/50',

      // Toggle button (in gallery header) - uses aria-label="Show filters"
      toggleButton: 'button[aria-label*="Show filters"], button[aria-label*="filter"]',

      // Filter sections
      dateRangeSection: '[data-testid="date-range-filter"], :has-text("Date Range")',
      tagSection: '[data-testid="tag-filter"], :has-text("Tags")',
      speciesSection: '[data-testid="species-filter"], :has-text("Species")',
      fileTypeSection: '[data-testid="file-type-filter"], :has-text("File Type")',
      cameraSettingsSection: '[data-testid="camera-settings-filter"], :has-text("Camera Settings")',
      notesSection: '[data-testid="notes-filter"], :has-text("Notes")',
      customFieldsSection: '[data-testid="custom-fields-filter"], :has-text("Custom")',

      // Date range inputs
      dateStartInput: 'input[name="date_start"], input[placeholder*="Start"]',
      dateEndInput: 'input[name="date_end"], input[placeholder*="End"]',
      datePresets: '.date-preset, button:has-text("Last 7 days"), button:has-text("Last 30 days")',

      // Tag filter
      tagInput: '.tag-filter input, input[placeholder*="tag"]',
      tagSuggestion: '.tag-suggestion, [role="option"]',
      selectedTag: '.selected-tag, .tag-chip',
      tagMatchMode: 'button:has-text("Any"), button:has-text("All")',

      // Species filter
      speciesInput: '.species-filter input, input[placeholder*="species"]',
      speciesSuggestion: '.species-suggestion, [role="option"]',
      unidentifiedToggle: 'input[type="checkbox"]:near-text("Unidentified")',

      // File type checkboxes
      jpgCheckbox: 'input[type="checkbox"]:near-text("JPG")',
      pngCheckbox: 'input[type="checkbox"]:near-text("PNG")',
      rawCheckbox: 'input[type="checkbox"]:near-text("RAW")',
      videoCheckbox: 'input[type="checkbox"]:near-text("Video")',

      // Camera settings sliders
      isoSlider: 'input[type="range"]:near-text("ISO")',
      apertureSlider: 'input[type="range"]:near-text("Aperture")',
      shutterSlider: 'input[type="range"]:near-text("Shutter")',

      // Notes filter
      hasNotesCheckbox: 'input[type="checkbox"]:near-text("Has notes")',
      notesKeywordInput: 'input[placeholder*="keyword"]',

      // Active filter chips
      filterChips: '.active-filter-chips, [data-testid="active-filters"]',
      filterChip: '.filter-chip, [data-testid^="filter-chip-"]',
      removeChipButton: '.filter-chip button, [data-testid^="remove-filter-"]',

      // Action buttons
      applyButton: 'button:has-text("Apply")',
      clearAllButton: 'button:has-text("Clear"), button:has-text("Reset")',
      closeButton: 'button:has-text("Close"), button[aria-label="Close"]',

      // Preset management
      savePresetButton: 'button:has-text("Save Preset")',
      loadPresetButton: 'button:has-text("Load Preset")',
      presetList: '.preset-list, [data-testid="preset-list"]',
    }
  }

  /**
   * Check if drawer is open
   * @returns {Promise<boolean>}
   */
  async isOpen() {
    return this.page.locator(this.selectors.drawer).isVisible()
  }

  /**
   * Open the filter drawer
   */
  async open() {
    if (!(await this.isOpen())) {
      await this.page.click(this.selectors.toggleButton)
      await this.page.waitForSelector(this.selectors.drawer, {
        state: 'visible',
        timeout: TIMEOUTS.MEDIUM,
      })
      // Wait for animation to complete
      await this.page.waitForLoadState('domcontentloaded')
    }
  }

  /**
   * Close the filter drawer
   */
  async close() {
    if (await this.isOpen()) {
      const closeBtn = this.page.locator(this.selectors.closeButton).first()
      if (await closeBtn.isVisible()) {
        await closeBtn.click()
      } else {
        // Click outside or toggle button
        await this.page.click(this.selectors.toggleButton)
      }
      await this.page.waitForSelector(this.selectors.drawer, {
        state: 'hidden',
        timeout: TIMEOUTS.MEDIUM,
      })
    }
  }

  /**
   * Set date range filter
   * @param {string} startDate - YYYY-MM-DD format
   * @param {string} endDate - YYYY-MM-DD format
   */
  async setDateRange(startDate, endDate) {
    await this.page.fill(this.selectors.dateStartInput, startDate)
    await this.page.fill(this.selectors.dateEndInput, endDate)
    // Wait for inputs to update
    await this.page.waitForFunction(
      ([startSel, startVal, endSel, endVal]) => {
        const startInput = document.querySelector(startSel)
        const endInput = document.querySelector(endSel)
        return startInput?.value === startVal && endInput?.value === endVal
      },
      [this.selectors.dateStartInput, startDate, this.selectors.dateEndInput, endDate],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Click a date preset
   * @param {'7 days' | '30 days' | '90 days' | 'This month' | 'Last month'} preset
   */
  async clickDatePreset(preset) {
    await this.page.click(`button:has-text("${preset}")`)
    // Wait for date inputs to be populated
    await this.page.waitForLoadState('domcontentloaded')
  }

  /**
   * Add a tag to the filter
   * @param {string} tag
   */
  async addTag(tag) {
    await this.page.fill(this.selectors.tagInput, tag)
    // Wait for suggestions to appear
    const suggestion = this.page.locator(this.selectors.tagSuggestion).first()
    await suggestion.waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})

    // Click first suggestion or press Enter
    if (await suggestion.isVisible()) {
      await suggestion.click()
    } else {
      await this.page.press(this.selectors.tagInput, 'Enter')
    }
    // Wait for selected tag chip to appear
    await this.page.locator(this.selectors.selectedTag).last().waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }

  /**
   * Set tag match mode
   * @param {'any' | 'all'} mode
   */
  async setTagMatchMode(mode) {
    const buttonText = mode === 'any' ? 'Any' : 'All'
    const btn = this.page.locator(`button:has-text("${buttonText}")`)
    await btn.click()
    // Wait for button to show active state
    await btn.getAttribute('aria-pressed').then(async (pressed) => {
      if (pressed !== 'true') {
        await this.page.waitForFunction(
          (text) => {
            const button = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes(text))
            return button?.getAttribute('aria-pressed') === 'true' || button?.classList.contains('active')
          },
          buttonText,
          { timeout: TIMEOUTS.SHORT }
        ).catch(() => {})
      }
    })
  }

  /**
   * Add a species filter
   * @param {string} species
   */
  async addSpecies(species) {
    await this.page.fill(this.selectors.speciesInput, species)
    // Wait for suggestions to appear
    const suggestion = this.page.locator(this.selectors.speciesSuggestion).first()
    await suggestion.waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})

    if (await suggestion.isVisible()) {
      await suggestion.click()
    } else {
      await this.page.press(this.selectors.speciesInput, 'Enter')
    }
    // Wait for input to be processed
    await this.page.waitForLoadState('domcontentloaded')
  }

  /**
   * Toggle "show unidentified only" checkbox
   */
  async toggleUnidentified() {
    const checkbox = this.page.locator(this.selectors.unidentifiedToggle)
    const wasChecked = await checkbox.isChecked()
    await checkbox.click()
    // Wait for checkbox state to change
    await this.page.waitForFunction(
      ([sel, expected]) => {
        const cb = document.querySelector(sel)
        return cb?.checked === expected
      },
      [this.selectors.unidentifiedToggle, !wasChecked],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Toggle a file type filter
   * @param {'jpg' | 'png' | 'raw' | 'video'} fileType
   */
  async toggleFileType(fileType) {
    const selectors = {
      jpg: this.selectors.jpgCheckbox,
      png: this.selectors.pngCheckbox,
      raw: this.selectors.rawCheckbox,
      video: this.selectors.videoCheckbox,
    }
    const selector = selectors[fileType]
    const checkbox = this.page.locator(selector)
    const wasChecked = await checkbox.isChecked()
    await checkbox.click()
    // Wait for checkbox state to change
    await this.page.waitForFunction(
      ([sel, expected]) => {
        const cb = document.querySelector(sel)
        return cb?.checked === expected
      },
      [selector, !wasChecked],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Set notes keyword filter
   * @param {string} keyword
   */
  async setNotesKeyword(keyword) {
    await this.page.fill(this.selectors.notesKeywordInput, keyword)
    // Wait for input value to be set
    await this.page.waitForFunction(
      ([sel, val]) => document.querySelector(sel)?.value === val,
      [this.selectors.notesKeywordInput, keyword],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Toggle "has notes" filter
   */
  async toggleHasNotes() {
    const checkbox = this.page.locator(this.selectors.hasNotesCheckbox)
    const wasChecked = await checkbox.isChecked()
    await checkbox.click()
    // Wait for checkbox state to change
    await this.page.waitForFunction(
      ([sel, expected]) => {
        const cb = document.querySelector(sel)
        return cb?.checked === expected
      },
      [this.selectors.hasNotesCheckbox, !wasChecked],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Apply current filters
   */
  async applyFilters() {
    const applyBtn = this.page.locator(this.selectors.applyButton).first()
    if (await applyBtn.isVisible()) {
      await applyBtn.click()
    }
    // Wait for gallery to reload with filtered results
    await this.page.waitForLoadState('networkidle', { timeout: TIMEOUTS.NETWORK })
  }

  /**
   * Clear all filters
   */
  async clearAllFilters() {
    await this.page.click(this.selectors.clearAllButton)
    // Wait for gallery to reload with all results
    await this.page.waitForLoadState('networkidle', { timeout: TIMEOUTS.NETWORK })
  }

  /**
   * Get count of active filter chips
   * @returns {Promise<number>}
   */
  async getActiveFilterCount() {
    return this.page.locator(this.selectors.filterChip).count()
  }

  /**
   * Remove a filter chip by index
   * @param {number} index
   */
  async removeFilterChip(index) {
    const chips = this.page.locator(this.selectors.filterChip)
    const initialCount = await chips.count()
    const chip = chips.nth(index)
    const removeBtn = chip.locator('button').first()
    await removeBtn.click()
    // Wait for chip to be removed
    await this.page.waitForFunction(
      ([sel, expected]) => document.querySelectorAll(sel).length < expected,
      [this.selectors.filterChip, initialCount],
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Get all active filter chip texts
   * @returns {Promise<string[]>}
   */
  async getActiveFilterTexts() {
    const chips = this.page.locator(this.selectors.filterChip)
    const count = await chips.count()
    const texts = []

    for (let i = 0; i < count; i++) {
      const text = await chips.nth(i).textContent()
      texts.push(text.trim())
    }

    return texts
  }
}
