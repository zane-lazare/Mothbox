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
      const tab = this.page.locator(tabSelector)
      await tab.click()
      // Wait for tab to become selected
      await tab.getAttribute('aria-selected').then(async (selected) => {
        if (selected !== 'true') {
          await this.page.waitForFunction(
            (sel) => document.querySelector(sel)?.getAttribute('aria-selected') === 'true',
            tabSelector,
            { timeout: TIMEOUTS.SHORT }
          ).catch(() => {})
        }
      })
    }
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
