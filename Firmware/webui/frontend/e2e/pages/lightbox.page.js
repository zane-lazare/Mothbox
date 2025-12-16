/**
 * Lightbox Page Object
 *
 * Encapsulates interactions with the photo lightbox/viewer
 */

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
      metadataTab: '[role="tab"]',
      cameraTab: '[role="tab"]:has-text("Camera")',
      locationTab: '[role="tab"]:has-text("Location")',
      captureTab: '[role="tab"]:has-text("Capture")',
      tagsTab: '[role="tab"]:has-text("Tags")',
      deploymentTab: '[role="tab"]:has-text("Deployment")',

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
      timeout: 5000,
    })
    await this.page.waitForTimeout(300) // Animation
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
      timeout: 5000,
    })
  }

  /**
   * Navigate to next photo
   */
  async navigateNext() {
    const nextBtn = this.page.locator(this.selectors.nextButton).first()
    if (await nextBtn.isVisible()) {
      await nextBtn.click()
    } else {
      await this.page.keyboard.press('ArrowRight')
    }
    await this.page.waitForTimeout(300)
  }

  /**
   * Navigate to previous photo
   */
  async navigatePrev() {
    const prevBtn = this.page.locator(this.selectors.prevButton).first()
    if (await prevBtn.isVisible()) {
      await prevBtn.click()
    } else {
      await this.page.keyboard.press('ArrowLeft')
    }
    await this.page.waitForTimeout(300)
  }

  /**
   * Navigate using arrow keys
   * @param {'left' | 'right'} direction
   */
  async navigateWithKeyboard(direction) {
    const key = direction === 'left' ? 'ArrowLeft' : 'ArrowRight'
    await this.page.keyboard.press(key)
    await this.page.waitForTimeout(300)
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
   * Click a metadata tab
   * @param {'Camera' | 'Location' | 'Capture' | 'Tags' | 'Deployment'} tabName
   */
  async clickMetadataTab(tabName) {
    const tabSelector = {
      Camera: this.selectors.cameraTab,
      Location: this.selectors.locationTab,
      Capture: this.selectors.captureTab,
      Tags: this.selectors.tagsTab,
      Deployment: this.selectors.deploymentTab,
    }[tabName]

    if (tabSelector) {
      await this.page.click(tabSelector)
      await this.page.waitForTimeout(200)
    }
  }

  /**
   * Zoom in using button
   */
  async zoomIn() {
    const btn = this.page.locator(this.selectors.zoomInButton).first()
    if (await btn.isVisible()) {
      await btn.click()
    }
    await this.page.waitForTimeout(200)
  }

  /**
   * Zoom out using button
   */
  async zoomOut() {
    const btn = this.page.locator(this.selectors.zoomOutButton).first()
    if (await btn.isVisible()) {
      await btn.click()
    }
    await this.page.waitForTimeout(200)
  }

  /**
   * Zoom with mouse wheel
   * @param {'in' | 'out'} direction
   */
  async zoomWithWheel(direction) {
    const imageContainer = this.page.locator(this.selectors.imageContainer).first()

    await imageContainer.hover()
    await this.page.mouse.wheel(0, direction === 'in' ? -100 : 100)
    await this.page.waitForTimeout(200)
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
