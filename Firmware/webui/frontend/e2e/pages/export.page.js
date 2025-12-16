/**
 * Export Page Object
 *
 * Encapsulates interactions with the export workflow (modals, job status)
 */

export class ExportPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page

    // Selectors
    this.selectors = {
      // Export modal
      exportModal: '[data-testid="export-modal"], .export-modal, [role="dialog"]:has-text("Export")',
      modalTitle: '.modal-title, [class*="ModalTitle"]',
      modalClose: 'button[aria-label="Close"], button:has([class*="X"])',

      // Format selection
      formatSelect: 'select[name="format"], [data-testid="format-select"]',
      formatOption: 'option, [role="option"]',
      darwinCoreOption: 'option[value="darwin_core"], [data-testid="format-darwin-core"]',
      iNaturalistOption: 'option[value="inaturalist"], [data-testid="format-inaturalist"]',
      jsonOption: 'option[value="json"], [data-testid="format-json"]',
      csvOption: 'option[value="csv"], [data-testid="format-csv"]',

      // Format cards (if using card-based selection)
      formatCard: '.format-card, [data-testid^="format-card-"]',
      selectedFormatCard: '.format-card.selected, [data-testid^="format-card-"].selected',

      // Export options
      includePhotosCheckbox: 'input[type="checkbox"]:near-text("Include photos")',
      includeMetadataCheckbox: 'input[type="checkbox"]:near-text("Include metadata")',
      compressCheckbox: 'input[type="checkbox"]:near-text("Compress")',

      // Deployment metadata section
      deploymentSection: '[data-testid="deployment-section"], :has-text("Deployment")',
      deploymentNameInput: 'input[name="deployment_name"], input[placeholder*="deployment"]',
      locationInput: 'input[name="location"], input[placeholder*="location"]',
      dateStartInput: 'input[name="start_date"]',
      dateEndInput: 'input[name="end_date"]',

      // Action buttons
      startExportButton: 'button:has-text("Start Export"), button:has-text("Export")',
      cancelButton: 'button:has-text("Cancel")',

      // Progress modal
      progressModal: '[data-testid="progress-modal"], .progress-modal',
      progressBar: '[role="progressbar"], .progress-bar',
      progressPercent: '.progress-percent, [data-testid="progress-percent"]',
      progressPhase: '.progress-phase, [data-testid="progress-phase"]',
      progressStatus: '.progress-status, [data-testid="progress-status"]',

      // Job result
      downloadButton: 'a:has-text("Download"), button:has-text("Download")',
      downloadLink: 'a[download], a[href*="download"]',
      successMessage: '.success-message, :has-text("completed")',
      errorMessage: '.error-message, :has-text("failed")',

      // Job list (if showing job history)
      jobList: '[data-testid="job-list"], .job-list',
      jobItem: '[data-testid^="job-item-"], .job-item',
      jobStatus: '.job-status',
      cancelJobButton: 'button:has-text("Cancel")',
      deleteJobButton: 'button:has-text("Delete")',
    }
  }

  /**
   * Check if export modal is open
   * @returns {Promise<boolean>}
   */
  async isModalOpen() {
    return this.page.locator(this.selectors.exportModal).isVisible()
  }

  /**
   * Wait for export modal to open
   */
  async waitForModal() {
    await this.page.waitForSelector(this.selectors.exportModal, {
      state: 'visible',
      timeout: 5000,
    })
    await this.page.waitForTimeout(300)
  }

  /**
   * Close the export modal
   */
  async closeModal() {
    await this.page.click(this.selectors.cancelButton)
    await this.page.waitForSelector(this.selectors.exportModal, {
      state: 'hidden',
      timeout: 5000,
    })
  }

  /**
   * Select export format
   * @param {'darwin_core' | 'inaturalist' | 'json' | 'csv'} format
   */
  async selectFormat(format) {
    // Try dropdown first
    const select = this.page.locator(this.selectors.formatSelect)
    if (await select.isVisible()) {
      await select.selectOption(format)
    } else {
      // Try format cards
      const formatLabels = {
        darwin_core: 'Darwin Core',
        inaturalist: 'iNaturalist',
        json: 'JSON',
        csv: 'CSV',
      }
      await this.page.click(`.format-card:has-text("${formatLabels[format]}")`)
    }
    await this.page.waitForTimeout(200)
  }

  /**
   * Fill deployment metadata
   * @param {Object} metadata
   * @param {string} [metadata.name] - Deployment name
   * @param {string} [metadata.location] - Location description
   * @param {string} [metadata.startDate] - Start date (YYYY-MM-DD)
   * @param {string} [metadata.endDate] - End date (YYYY-MM-DD)
   */
  async fillDeploymentMetadata(metadata) {
    if (metadata.name) {
      await this.page.fill(this.selectors.deploymentNameInput, metadata.name)
    }
    if (metadata.location) {
      await this.page.fill(this.selectors.locationInput, metadata.location)
    }
    if (metadata.startDate) {
      await this.page.fill(this.selectors.dateStartInput, metadata.startDate)
    }
    if (metadata.endDate) {
      await this.page.fill(this.selectors.dateEndInput, metadata.endDate)
    }
  }

  /**
   * Toggle "include photos" option
   */
  async toggleIncludePhotos() {
    await this.page.click(this.selectors.includePhotosCheckbox)
    await this.page.waitForTimeout(100)
  }

  /**
   * Start the export job
   */
  async startExport() {
    await this.page.click(this.selectors.startExportButton)
    await this.page.waitForTimeout(500)
  }

  /**
   * Wait for export to complete
   * @param {number} timeout - Max wait time in ms
   * @returns {Promise<boolean>} - True if succeeded, false if failed
   */
  async waitForCompletion(timeout = 120000) {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      // Check for success
      const downloadBtn = this.page.locator(this.selectors.downloadButton).first()
      if (await downloadBtn.isVisible()) {
        return true
      }

      // Check for error
      const errorMsg = this.page.locator(this.selectors.errorMessage).first()
      if (await errorMsg.isVisible()) {
        return false
      }

      await this.page.waitForTimeout(1000)
    }

    throw new Error('Export timed out')
  }

  /**
   * Get current progress percentage
   * @returns {Promise<number>}
   */
  async getProgress() {
    const progressEl = this.page.locator(this.selectors.progressPercent).first()
    if (await progressEl.isVisible()) {
      const text = await progressEl.textContent()
      const match = text.match(/(\d+)/)
      return match ? parseInt(match[1], 10) : 0
    }

    // Try progressbar value attribute
    const progressBar = this.page.locator(this.selectors.progressBar).first()
    if (await progressBar.isVisible()) {
      const value = await progressBar.getAttribute('aria-valuenow')
      return value ? parseInt(value, 10) : 0
    }

    return 0
  }

  /**
   * Get current progress phase
   * @returns {Promise<string|null>}
   */
  async getPhase() {
    const phaseEl = this.page.locator(this.selectors.progressPhase).first()
    if (await phaseEl.isVisible()) {
      return phaseEl.textContent()
    }
    return null
  }

  /**
   * Click download button and wait for download
   * @returns {Promise<import('@playwright/test').Download>}
   */
  async clickDownload() {
    const downloadPromise = this.page.waitForEvent('download')
    await this.page.click(this.selectors.downloadButton)
    return downloadPromise
  }

  /**
   * Cancel current export job
   */
  async cancelJob() {
    await this.page.click(this.selectors.cancelJobButton)
    await this.page.waitForTimeout(500)
  }

  /**
   * Check if download button is visible
   * @returns {Promise<boolean>}
   */
  async isDownloadReady() {
    return this.page.locator(this.selectors.downloadButton).isVisible()
  }

  /**
   * Check if error message is displayed
   * @returns {Promise<boolean>}
   */
  async hasError() {
    return this.page.locator(this.selectors.errorMessage).isVisible()
  }

  /**
   * Get error message text
   * @returns {Promise<string|null>}
   */
  async getErrorMessage() {
    const errorEl = this.page.locator(this.selectors.errorMessage).first()
    if (await errorEl.isVisible()) {
      return errorEl.textContent()
    }
    return null
  }
}
