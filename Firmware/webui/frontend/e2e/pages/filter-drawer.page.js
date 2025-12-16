/**
 * Filter Drawer Page Object
 *
 * Encapsulates interactions with the gallery filter drawer
 */

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
        timeout: 5000,
      })
      await this.page.waitForTimeout(300) // Animation
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
        timeout: 5000,
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
    await this.page.waitForTimeout(200)
  }

  /**
   * Click a date preset
   * @param {'7 days' | '30 days' | '90 days' | 'This month' | 'Last month'} preset
   */
  async clickDatePreset(preset) {
    await this.page.click(`button:has-text("${preset}")`)
    await this.page.waitForTimeout(200)
  }

  /**
   * Add a tag to the filter
   * @param {string} tag
   */
  async addTag(tag) {
    await this.page.fill(this.selectors.tagInput, tag)
    await this.page.waitForTimeout(300) // Wait for suggestions

    // Click first suggestion or press Enter
    const suggestion = this.page.locator(this.selectors.tagSuggestion).first()
    if (await suggestion.isVisible()) {
      await suggestion.click()
    } else {
      await this.page.press(this.selectors.tagInput, 'Enter')
    }
    await this.page.waitForTimeout(200)
  }

  /**
   * Set tag match mode
   * @param {'any' | 'all'} mode
   */
  async setTagMatchMode(mode) {
    const buttonText = mode === 'any' ? 'Any' : 'All'
    await this.page.click(`button:has-text("${buttonText}")`)
    await this.page.waitForTimeout(200)
  }

  /**
   * Add a species filter
   * @param {string} species
   */
  async addSpecies(species) {
    await this.page.fill(this.selectors.speciesInput, species)
    await this.page.waitForTimeout(300)

    const suggestion = this.page.locator(this.selectors.speciesSuggestion).first()
    if (await suggestion.isVisible()) {
      await suggestion.click()
    } else {
      await this.page.press(this.selectors.speciesInput, 'Enter')
    }
    await this.page.waitForTimeout(200)
  }

  /**
   * Toggle "show unidentified only" checkbox
   */
  async toggleUnidentified() {
    await this.page.click(this.selectors.unidentifiedToggle)
    await this.page.waitForTimeout(200)
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
    await this.page.click(selectors[fileType])
    await this.page.waitForTimeout(200)
  }

  /**
   * Set notes keyword filter
   * @param {string} keyword
   */
  async setNotesKeyword(keyword) {
    await this.page.fill(this.selectors.notesKeywordInput, keyword)
    await this.page.waitForTimeout(200)
  }

  /**
   * Toggle "has notes" filter
   */
  async toggleHasNotes() {
    await this.page.click(this.selectors.hasNotesCheckbox)
    await this.page.waitForTimeout(200)
  }

  /**
   * Apply current filters
   */
  async applyFilters() {
    const applyBtn = this.page.locator(this.selectors.applyButton).first()
    if (await applyBtn.isVisible()) {
      await applyBtn.click()
    }
    await this.page.waitForTimeout(500)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Clear all filters
   */
  async clearAllFilters() {
    await this.page.click(this.selectors.clearAllButton)
    await this.page.waitForTimeout(500)
    await this.page.waitForLoadState('networkidle')
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
    const chip = chips.nth(index)
    const removeBtn = chip.locator('button').first()
    await removeBtn.click()
    await this.page.waitForTimeout(300)
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
