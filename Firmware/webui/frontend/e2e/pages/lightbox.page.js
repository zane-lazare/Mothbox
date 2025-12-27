/**
 * Lightbox Page Object
 *
 * Encapsulates interactions with the photo lightbox/viewer
 */

import { TIMEOUTS } from '../fixtures/test-helpers.js'

export class LightboxPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page

    // Selectors
    this.selectors = {
      // Lightbox container
      lightbox: '[role="dialog"], .lightbox, [class*="Lightbox"]',
      overlay: '.lightbox-overlay, [class*="overlay"]',

      // Main image
      image: '.lightbox img, [class*="Lightbox"] img',
      imageContainer: '.lightbox-image-container, [class*="ImageContainer"]',

      // Navigation
      prevButton: 'button[aria-label*="Previous"], button:has([class*="ChevronLeft"]), .prev-button',
      nextButton: 'button[aria-label*="Next"], button:has([class*="ChevronRight"]), .next-button',
      closeButton: 'button[aria-label*="Close"], button:has([class*="X"]), .close-button',

      // Metadata panel
      metadataPanel: '[data-testid="metadata-panel"], .metadata-panel, [class*="MetadataPanel"]',

      // Accordion sections (matches MetadataPanel.jsx lines 272-306)
      tagsSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Tags")',
      speciesSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Species")',
      notesSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Notes")',
      exifSection: '[data-testid="metadata-panel"] [role="button"]:has-text("EXIF Data")',
      customFieldsSection: '[data-testid="metadata-panel"] [role="button"]:has-text("Custom Fields")',

      // GPS display (from MetadataEXIF component)
      gpsCoordinates: 'text=/\\d+\\.\\d+°\\s*[NS],\\s*\\d+\\.\\d+°\\s*[EW]/',
      altitudeDisplay: 'text=/\\d+(\\.\\d+)?m/',
      copyButton: 'button[aria-label*="Copy"]',

      // Series indicator
      seriesIndicator: '[data-testid="series-indicator"]',
      seriesCounter: '[data-testid="series-counter"]',

      // Zoom controls
      zoomInButton: 'button[aria-label*="Zoom in"], button:has([class*="ZoomIn"])',
      zoomOutButton: 'button[aria-label*="Zoom out"], button:has([class*="ZoomOut"])',
      zoomReset: 'button[aria-label*="Reset"], button:has-text("Reset")',

      // Photo counter
      photoCounter: '.photo-counter, [class*="Counter"]',

      // Loading state
      loading: '.lightbox-loading, [class*="Loading"]',
    }
  }

  /**
   * Check if lightbox is open
   * @returns {Promise<boolean>}
   */
  async isOpen() {
    return this.page.locator(this.selectors.lightbox).isVisible()
  }

  /**
   * Wait for lightbox to be visible
   */
  async waitForOpen() {
    await this.page.waitForSelector(this.selectors.lightbox, {
      state: 'visible',
      timeout: TIMEOUTS.MEDIUM,
    })
    // Wait for opening animation to complete
    await this.page.locator(this.selectors.image).first().waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }).catch(() => {})
  }

  /**
   * Close the lightbox
   */
  async close() {
    // Try close button first
    const closeBtn = this.page.locator(this.selectors.closeButton).first()
    if (await closeBtn.isVisible()) {
      await closeBtn.click()
    } else {
      // Fallback to Escape key
      await this.page.keyboard.press('Escape')
    }

    await this.page.waitForSelector(this.selectors.lightbox, {
      state: 'hidden',
      timeout: TIMEOUTS.MEDIUM,
    })
  }

  /**
   * Navigate to next photo
   */
  async navigateNext() {
    const currentSrc = await this.getImageSrc()
    const nextBtn = this.page.locator(this.selectors.nextButton).first()
    if (await nextBtn.isVisible()) {
      await nextBtn.click()
    } else {
      await this.page.keyboard.press('ArrowRight')
    }
    // Wait for image to change (indicating navigation completed)
    await this.page.waitForFunction(
      (prevSrc) => {
        const img = document.querySelector('.lightbox img, [class*="Lightbox"] img')
        return img && img.src !== prevSrc
      },
      currentSrc,
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Navigate to previous photo
   */
  async navigatePrev() {
    const currentSrc = await this.getImageSrc()
    const prevBtn = this.page.locator(this.selectors.prevButton).first()
    if (await prevBtn.isVisible()) {
      await prevBtn.click()
    } else {
      await this.page.keyboard.press('ArrowLeft')
    }
    // Wait for image to change (indicating navigation completed)
    await this.page.waitForFunction(
      (prevSrc) => {
        const img = document.querySelector('.lightbox img, [class*="Lightbox"] img')
        return img && img.src !== prevSrc
      },
      currentSrc,
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Navigate using arrow keys
   * @param {'left' | 'right'} direction
   */
  async navigateWithKeyboard(direction) {
    const currentSrc = await this.getImageSrc()
    const key = direction === 'left' ? 'ArrowLeft' : 'ArrowRight'
    await this.page.keyboard.press(key)
    // Wait for image to change (indicating navigation completed)
    await this.page.waitForFunction(
      (prevSrc) => {
        const img = document.querySelector('.lightbox img, [class*="Lightbox"] img')
        return img && img.src !== prevSrc
      },
      currentSrc,
      { timeout: TIMEOUTS.SHORT }
    ).catch(() => {})
  }

  /**
   * Get current image src
   * @returns {Promise<string|null>}
   */
  async getImageSrc() {
    const img = this.page.locator(this.selectors.image).first()
    return img.getAttribute('src')
  }

  /**
   * Check if metadata panel is visible
   * @returns {Promise<boolean>}
   */
  async isMetadataPanelVisible() {
    return this.page.locator(this.selectors.metadataPanel).isVisible()
  }

  /**
   * Get text content of metadata panel
   * @returns {Promise<string>}
   */
  async getMetadataText() {
    const panel = this.page.locator(this.selectors.metadataPanel)
    return panel.textContent()
  }

  /**
   * Click a metadata section to expand/collapse (accordion pattern)
   * @param {'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'} sectionName
   * @returns {Promise<void>}
   */
  async clickMetadataSection(sectionName) {
    const sectionSelector = {
      'Tags': this.selectors.tagsSection,
      'Species': this.selectors.speciesSection,
      'Notes': this.selectors.notesSection,
      'EXIF Data': this.selectors.exifSection,
      'Custom Fields': this.selectors.customFieldsSection,
    }[sectionName]

    if (sectionSelector) {
      const section = this.page.locator(sectionSelector)
      await section.click()
      // Wait for aria-expanded to update
      await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
    }
  }

  /**
   * DEPRECATED: Use clickMetadataSection instead
   * @deprecated
   */
  async clickMetadataTab(tabName) {
    console.warn('clickMetadataTab is deprecated. Use clickMetadataSection instead.')
    // Map old tab names to new section names for backward compatibility
    const sectionMap = {
      'Camera': 'EXIF Data',
      'Location': 'EXIF Data',
      'Capture': 'EXIF Data',
      'Tags': 'Tags',
      'Deployment': 'EXIF Data',
    }
    const sectionName = sectionMap[tabName]
    if (sectionName) {
      await this.clickMetadataSection(sectionName)
    }
  }

  /**
   * Expand a metadata section (accordion pattern)
   * @param {'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'} sectionName
   * @returns {Promise<void>}
   */
  async expandSection(sectionName) {
    const isExpanded = await this.isSectionExpanded(sectionName)
    if (!isExpanded) {
      await this.clickMetadataSection(sectionName)
    }
  }

  /**
   * Check if a metadata section is expanded
   * @param {'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'} sectionName
   * @returns {Promise<boolean>}
   */
  async isSectionExpanded(sectionName) {
    const sectionSelector = {
      'Tags': this.selectors.tagsSection,
      'Species': this.selectors.speciesSection,
      'Notes': this.selectors.notesSection,
      'EXIF Data': this.selectors.exifSection,
      'Custom Fields': this.selectors.customFieldsSection,
    }[sectionName]

    if (!sectionSelector) return false

    const section = this.page.locator(sectionSelector)
    const ariaExpanded = await section.getAttribute('aria-expanded')
    return ariaExpanded === 'true'
  }

  /**
   * Get text content of a metadata section
   * @param {'Tags' | 'Species' | 'Notes' | 'EXIF Data' | 'Custom Fields'} sectionName
   * @returns {Promise<string|null>}
   */
  async getSectionContent(sectionName) {
    // Ensure section is expanded first
    await this.expandSection(sectionName)

    const sectionSelector = {
      'Tags': this.selectors.tagsSection,
      'Species': this.selectors.speciesSection,
      'Notes': this.selectors.notesSection,
      'EXIF Data': this.selectors.exifSection,
      'Custom Fields': this.selectors.customFieldsSection,
    }[sectionName]

    if (!sectionSelector) return null

    // Get the content div (next sibling of the button)
    const section = this.page.locator(sectionSelector)
    const contentId = await section.getAttribute('aria-controls')
    if (!contentId) return null

    const contentDiv = this.page.locator(`#${contentId}`)
    return contentDiv.textContent()
  }

  /**
   * Check if GPS coordinates are displayed
   * @returns {Promise<boolean>}
   */
  async hasGPSCoordinates() {
    await this.expandSection('EXIF Data')
    const gps = this.page.locator(this.selectors.gpsCoordinates)
    return gps.isVisible().catch(() => false)
  }

  /**
   * Get GPS coordinates text
   * @returns {Promise<string|null>} GPS text in format "37.7749° N, 122.4194° W" or null if not found
   */
  async getGPSText() {
    await this.expandSection('EXIF Data')
    const gps = this.page.locator(this.selectors.gpsCoordinates)
    if (await gps.isVisible().catch(() => false)) {
      return gps.textContent()
    }
    return null
  }

  /**
   * Copy GPS coordinates to clipboard
   * @returns {Promise<boolean>} True if copy succeeded, false otherwise
   */
  async copyCoordinatesToClipboard() {
    await this.expandSection('EXIF Data')

    // Find the GPS field and its associated copy button
    // The MetadataField component places the copy button next to the value
    const gpsField = this.page.locator('text="GPS"').locator('..')
    const copyBtn = gpsField.locator(this.selectors.copyButton).first()

    if (await copyBtn.isVisible().catch(() => false)) {
      await copyBtn.click()
      // Wait for copy animation to complete
      await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
      return true
    }
    return false
  }

  /**
   * Get EXIF field value by label
   * @param {'Make' | 'Model' | 'Lens' | 'ISO' | 'Shutter Speed' | 'Aperture' | 'Focal Length' | 'Exposure Mode' | 'White Balance' | 'Captured' | 'GPS' | 'Altitude' | 'Deployment' | 'Device'} fieldLabel
   * @returns {Promise<string|null>} Field value or null if not found
   */
  async getEXIFFieldValue(fieldLabel) {
    await this.expandSection('EXIF Data')

    // Find the MetadataField with the matching label
    const field = this.page.locator(`text="${fieldLabel}"`).locator('..')
    if (await field.isVisible().catch(() => false)) {
      // The value is in the second div child of the field container
      const valueDiv = field.locator('div').nth(1)
      const value = await valueDiv.textContent()
      // Return null if the value is "N/A"
      return value === 'N/A' ? null : value
    }
    return null
  }

  /**
   * Check if photo is part of a series (HDR or Focus Bracket)
   * @returns {Promise<boolean>}
   */
  async isPartOfSeries() {
    const indicator = this.page.locator(this.selectors.seriesIndicator)
    return indicator.isVisible().catch(() => false)
  }

  /**
   * Get series indicator text (e.g., "HDR Series: 3/5" or "Focus Bracket: 2/7")
   * @returns {Promise<string|null>}
   */
  async getSeriesIndicatorText() {
    const indicator = this.page.locator(this.selectors.seriesIndicator)
    if (await indicator.isVisible().catch(() => false)) {
      return indicator.textContent()
    }
    return null
  }

  /**
   * Zoom in using button
   */
  async zoomIn() {
    const btn = this.page.locator(this.selectors.zoomInButton).first()
    if (await btn.isVisible()) {
      await btn.click()
      // Wait for zoom animation to complete by checking for any transform change
      await this.page.waitForLoadState('domcontentloaded')
    }
  }

  /**
   * Zoom out using button
   */
  async zoomOut() {
    const btn = this.page.locator(this.selectors.zoomOutButton).first()
    if (await btn.isVisible()) {
      await btn.click()
      // Wait for zoom animation to complete
      await this.page.waitForLoadState('domcontentloaded')
    }
  }

  /**
   * Zoom with mouse wheel
   * @param {'in' | 'out'} direction
   */
  async zoomWithWheel(direction) {
    const imageContainer = this.page.locator(this.selectors.imageContainer).first()

    await imageContainer.hover()
    await this.page.mouse.wheel(0, direction === 'in' ? -100 : 100)
    // Wait for zoom to take effect
    await this.page.waitForLoadState('domcontentloaded')
  }

  /**
   * Get photo counter text (e.g., "3 of 24")
   * @returns {Promise<string|null>}
   */
  async getPhotoCounterText() {
    const counter = this.page.locator(this.selectors.photoCounter).first()
    if (await counter.isVisible()) {
      return counter.textContent()
    }
    return null
  }

  /**
   * Parse photo counter to get current index and total
   * @returns {Promise<{current: number, total: number} | null>}
   */
  async parsePhotoCounter() {
    const text = await this.getPhotoCounterText()
    if (!text) return null

    const match = text.match(/(\d+)\s*(?:of|\/)\s*(\d+)/i)
    if (match) {
      return {
        current: parseInt(match[1], 10),
        total: parseInt(match[2], 10),
      }
    }
    return null
  }
}
