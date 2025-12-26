/**
 * Scheduler Page Object
 *
 * Encapsulates interactions with the scheduler page for E2E testing.
 * Covers schedule CRUD, activation/deactivation, and calendar navigation.
 */

import { TIMEOUTS, optionalWait } from '../fixtures/test-helpers.js'

export class SchedulerPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page

    // Selectors - using multiple fallbacks for flexibility
    this.selectors = {
      // Page heading
      pageHeading: 'text=Schedule',

      // Tabs
      schedulesTab: 'button:has-text("Schedules")',
      calendarTab: 'button:has-text("Calendar")',
      schedulesPanel: '#schedules-panel',
      calendarPanel: '#calendar-panel',

      // Toolbar
      newScheduleButton: 'button:has-text("New Schedule")',

      // Schedule List
      scheduleCard: 'article[role="article"]',
      scheduleCardByName: (name) => `article[role="article"]:has-text("${name}")`,
      editButton: 'button:has-text("Edit")',
      activateButton: 'button:has-text("Activate")',
      deactivateButton: 'button:has-text("Deactivate")',
      deleteButton: 'button:has-text("Delete")',

      // Active Badge (within card)
      activeBadge: 'text=Active',

      // Active Banner (top-level status)
      activeBanner: '[role="status"]',
      bannerDeactivateButton: '[role="status"] button:has-text("Deactivate")',
      bannerScheduleName: '[role="status"] span',

      // Editor Drawer
      editorDrawer: '[data-testid="schedule-editor-drawer"]',
      drawerBackdrop: '[data-testid="drawer-backdrop"]',
      editorTitle: '[data-testid="schedule-editor-drawer"] h2',
      scheduleNameInput: '#schedule-name',
      scheduleDescriptionInput: '#schedule-description',
      saveButton: '[data-testid="schedule-editor-drawer"] button:has-text("Save")',
      cancelButton: '[data-testid="schedule-editor-drawer"] button:has-text("Cancel")',
      closeButton: 'button[aria-label="Close"]',

      // Delete Confirmation Dialog
      confirmDialog: '[data-testid="confirm-dialog"], [role="alertdialog"], [role="dialog"]:has-text("Delete")',
      confirmDeleteButton: '[data-testid="confirm-dialog-confirm"], button:has-text("Confirm")',
      cancelDeleteButton: '[data-testid="confirm-dialog-cancel"], button:has-text("Cancel")',

      // Calendar View
      scheduleSelector: '#calendar-panel select',
      dayViewButton: 'button:has-text("Day")',
      weekViewButton: 'button:has-text("Week")',
      monthViewButton: 'button:has-text("Month")',
      todayButton: 'button:has-text("Today")',
      prevButton: 'button[aria-label*="Previous"], button[aria-label*="Prev"]',
      nextButton: 'button[aria-label*="Next"]',
      emptyCalendarState: 'text=No schedule selected',
      calendarDateDisplay: '#calendar-panel header, #calendar-panel h2, #calendar-panel [class*="header"]',

      // Loading states
      loadingSpinner: '.loading, [data-testid="loading-spinner"]',
      emptySchedulesState: 'text=No schedules',

      // Toast notifications
      toastSuccess: '.toast-success, [class*="toast"]:has-text("success")',
      toastError: '.toast-error, [class*="toast"]:has-text("error"), [class*="toast"]:has-text("fail")',
    }
  }

  // ============================================================
  // Navigation
  // ============================================================

  /**
   * Navigate to scheduler page
   */
  async goto() {
    await this.page.goto('/scheduler')
    await this.page.waitForLoadState('networkidle')
    await this.waitForLoad()
  }

  /**
   * Wait for scheduler page to finish loading
   */
  async waitForLoad() {
    // Wait for loading spinner to disappear (if present)
    try {
      await this.page.waitForSelector(this.selectors.loadingSpinner, {
        state: 'hidden',
        timeout: TIMEOUTS.MEDIUM,
      })
    } catch {
      // Spinner might not appear on fast loads
    }

    // Wait for network to settle
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Switch to Schedules tab
   */
  async switchToSchedulesTab() {
    await this.page.click(this.selectors.schedulesTab)
    await this.page.locator(this.selectors.schedulesPanel).waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT })
  }

  /**
   * Switch to Calendar tab
   */
  async switchToCalendarTab() {
    await this.page.click(this.selectors.calendarTab)
    await this.page.locator(this.selectors.calendarPanel).waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT })
  }

  // ============================================================
  // Schedule List Operations
  // ============================================================

  /**
   * Get count of visible schedule cards
   * @returns {Promise<number>}
   */
  async getScheduleCount() {
    return this.page.locator(this.selectors.scheduleCard).count()
  }

  /**
   * Check if any schedules exist
   * @returns {Promise<boolean>}
   */
  async hasSchedules() {
    const count = await this.getScheduleCount()
    return count > 0
  }

  /**
   * Get schedule card by index
   * @param {number} index - Zero-based index
   * @returns {import('@playwright/test').Locator}
   */
  getScheduleCardByIndex(index) {
    return this.page.locator(this.selectors.scheduleCard).nth(index)
  }

  /**
   * Get schedule card by name
   * @param {string} name - Schedule name
   * @returns {import('@playwright/test').Locator}
   */
  getScheduleCardByName(name) {
    return this.page.locator(this.selectors.scheduleCardByName(name))
  }

  /**
   * Check if a schedule card exists by name
   * @param {string} name - Schedule name
   * @returns {Promise<boolean>}
   */
  async hasScheduleWithName(name) {
    return this.page.locator(this.selectors.scheduleCardByName(name)).isVisible()
  }

  /**
   * Click Edit button on a schedule card
   * @param {number} index - Zero-based index
   */
  async clickEditOnSchedule(index) {
    const card = this.getScheduleCardByIndex(index)
    await card.locator(this.selectors.editButton).click()
    await this.waitForEditorOpen()
  }

  /**
   * Click Activate button on a schedule card
   * @param {number} index - Zero-based index
   */
  async clickActivateOnSchedule(index) {
    const card = this.getScheduleCardByIndex(index)
    await card.locator(this.selectors.activateButton).click()
    // Wait for network and potential state change
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Deactivate button on a schedule card
   * @param {number} index - Zero-based index
   */
  async clickDeactivateOnSchedule(index) {
    const card = this.getScheduleCardByIndex(index)
    await card.locator(this.selectors.deactivateButton).click()
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Delete button on a schedule card
   * @param {number} index - Zero-based index
   */
  async clickDeleteOnSchedule(index) {
    const card = this.getScheduleCardByIndex(index)
    await card.locator(this.selectors.deleteButton).click()
    // Wait for confirmation dialog
    await optionalWait(this.page.locator(this.selectors.confirmDialog).waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }))
  }

  /**
   * Click Delete button on a schedule by name
   * @param {string} name - Schedule name
   */
  async clickDeleteOnScheduleByName(name) {
    const card = this.getScheduleCardByName(name)
    await card.locator(this.selectors.deleteButton).click()
    await optionalWait(this.page.locator(this.selectors.confirmDialog).waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT }))
  }

  /**
   * Check if a schedule card has active badge
   * @param {number} index - Zero-based index
   * @returns {Promise<boolean>}
   */
  async isScheduleActive(index) {
    const card = this.getScheduleCardByIndex(index)
    return card.locator(this.selectors.activeBadge).isVisible()
  }

  /**
   * Find the index of the first inactive schedule
   * @returns {Promise<number>} Index or -1 if none found
   */
  async findFirstInactiveSchedule() {
    const count = await this.getScheduleCount()
    for (let i = 0; i < count; i++) {
      const isActive = await this.isScheduleActive(i)
      if (!isActive) {
        return i
      }
    }
    return -1
  }

  /**
   * Find the index of the active schedule
   * @returns {Promise<number>} Index or -1 if none active
   */
  async findActiveSchedule() {
    const count = await this.getScheduleCount()
    for (let i = 0; i < count; i++) {
      const isActive = await this.isScheduleActive(i)
      if (isActive) {
        return i
      }
    }
    return -1
  }

  // ============================================================
  // Active Banner Operations
  // ============================================================

  /**
   * Check if active banner is visible
   * @returns {Promise<boolean>}
   */
  async isActiveBannerVisible() {
    return this.page.locator(this.selectors.activeBanner).isVisible()
  }

  /**
   * Get the name of the active schedule from banner
   * @returns {Promise<string|null>}
   */
  async getActiveBannerScheduleName() {
    const banner = this.page.locator(this.selectors.activeBanner)
    if (!(await banner.isVisible())) {
      return null
    }
    const text = await banner.textContent()
    // Extract name from "Active: Schedule Name"
    const match = text.match(/Active:\s*(.+?)(?:\s*Deactivate)?$/i)
    return match ? match[1].trim() : null
  }

  /**
   * Click Deactivate button in active banner
   */
  async clickBannerDeactivate() {
    await this.page.click(this.selectors.bannerDeactivateButton)
    await this.page.waitForLoadState('networkidle')
  }

  // ============================================================
  // Editor Drawer Operations
  // ============================================================

  /**
   * Click New Schedule button to open editor
   */
  async clickNewSchedule() {
    await this.page.click(this.selectors.newScheduleButton)
    await this.waitForEditorOpen()
  }

  /**
   * Check if editor drawer is open
   * @returns {Promise<boolean>}
   */
  async isEditorOpen() {
    return this.page.locator(this.selectors.editorDrawer).isVisible()
  }

  /**
   * Wait for editor drawer to open
   */
  async waitForEditorOpen() {
    await this.page.locator(this.selectors.editorDrawer).waitFor({ state: 'visible', timeout: TIMEOUTS.MEDIUM })
  }

  /**
   * Wait for editor drawer to close
   */
  async waitForEditorClose() {
    await this.page.locator(this.selectors.editorDrawer).waitFor({ state: 'hidden', timeout: TIMEOUTS.MEDIUM })
  }

  /**
   * Get editor title text
   * @returns {Promise<string>}
   */
  async getEditorTitle() {
    return this.page.locator(this.selectors.editorTitle).textContent()
  }

  /**
   * Fill schedule name input
   * @param {string} name
   */
  async fillScheduleName(name) {
    await this.page.fill(this.selectors.scheduleNameInput, name)
  }

  /**
   * Fill schedule description input
   * @param {string} description
   */
  async fillScheduleDescription(description) {
    await this.page.fill(this.selectors.scheduleDescriptionInput, description)
  }

  /**
   * Get schedule name input value
   * @returns {Promise<string>}
   */
  async getScheduleNameValue() {
    return this.page.locator(this.selectors.scheduleNameInput).inputValue()
  }

  /**
   * Click Save button in editor
   */
  async clickSave() {
    await this.page.click(this.selectors.saveButton)
    // Wait for network operation
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Cancel button in editor
   */
  async clickCancel() {
    await this.page.click(this.selectors.cancelButton)
    await this.waitForEditorClose()
  }

  /**
   * Close editor via X button or Escape
   */
  async closeEditor() {
    // Try X button first
    const closeButton = this.page.locator(this.selectors.closeButton)
    if (await closeButton.isVisible()) {
      await closeButton.click()
    } else {
      // Fallback to Escape key
      await this.page.keyboard.press('Escape')
    }
    await this.waitForEditorClose()
  }

  // ============================================================
  // Delete Confirmation Dialog
  // ============================================================

  /**
   * Check if delete confirmation dialog is open
   * @returns {Promise<boolean>}
   */
  async isConfirmDialogOpen() {
    return this.page.locator(this.selectors.confirmDialog).isVisible()
  }

  /**
   * Confirm delete in dialog
   */
  async confirmDelete() {
    await this.page.click(this.selectors.confirmDeleteButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Cancel delete in dialog
   */
  async cancelDelete() {
    await this.page.click(this.selectors.cancelDeleteButton)
    await optionalWait(this.page.locator(this.selectors.confirmDialog).waitFor({ state: 'hidden', timeout: TIMEOUTS.SHORT }))
  }

  // ============================================================
  // Calendar Operations
  // ============================================================

  /**
   * Select a schedule in the calendar dropdown
   * @param {string} name - Schedule name to select
   */
  async selectScheduleInCalendar(name) {
    const selector = this.page.locator(this.selectors.scheduleSelector)
    await selector.selectOption({ label: name })
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Get available schedule options in calendar dropdown
   * @returns {Promise<string[]>}
   */
  async getCalendarScheduleOptions() {
    const selector = this.page.locator(this.selectors.scheduleSelector)
    const options = await selector.locator('option').allTextContents()
    return options.filter(opt => opt.trim() !== '')
  }

  /**
   * Click Day view button
   */
  async clickDayView() {
    await this.page.click(this.selectors.dayViewButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Week view button
   */
  async clickWeekView() {
    await this.page.click(this.selectors.weekViewButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Month view button
   */
  async clickMonthView() {
    await this.page.click(this.selectors.monthViewButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Today button
   */
  async clickToday() {
    await this.page.click(this.selectors.todayButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Previous navigation button
   */
  async clickPrevious() {
    // Find any button that looks like a previous navigation
    const prevButton = this.page.locator('button').filter({ has: this.page.locator('[class*="chevron-left"], [class*="ChevronLeft"], svg') }).first()
    if (await prevButton.isVisible()) {
      await prevButton.click()
    } else {
      // Fallback to aria-label pattern
      await this.page.locator(this.selectors.prevButton).first().click()
    }
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Next navigation button
   */
  async clickNext() {
    const nextButton = this.page.locator('button').filter({ has: this.page.locator('[class*="chevron-right"], [class*="ChevronRight"], svg') }).last()
    if (await nextButton.isVisible()) {
      await nextButton.click()
    } else {
      await this.page.locator(this.selectors.nextButton).first().click()
    }
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Check if empty calendar state is visible
   * @returns {Promise<boolean>}
   */
  async isEmptyCalendarStateVisible() {
    return this.page.locator(this.selectors.emptyCalendarState).isVisible()
  }

  /**
   * Get current calendar date display text
   * @returns {Promise<string>}
   */
  async getCalendarDateDisplay() {
    const display = this.page.locator(this.selectors.calendarDateDisplay).first()
    return display.textContent()
  }

  // ============================================================
  // Utility Methods
  // ============================================================

  /**
   * Generate unique test schedule name
   * @returns {string}
   */
  generateTestScheduleName() {
    return `e2e-test-schedule-${Date.now()}`
  }

  /**
   * Check if loading spinner is visible
   * @returns {Promise<boolean>}
   */
  async isLoading() {
    return this.page.locator(this.selectors.loadingSpinner).isVisible()
  }

  /**
   * Check if empty schedules state is visible
   * @returns {Promise<boolean>}
   */
  async isEmptySchedulesStateVisible() {
    return this.page.locator(this.selectors.emptySchedulesState).isVisible()
  }

  /**
   * Wait for a toast notification
   * @param {'success' | 'error'} type - Toast type
   * @param {number} timeout - Max wait time
   * @returns {Promise<boolean>} - True if toast appeared
   */
  async waitForToast(type, timeout = TIMEOUTS.MEDIUM) {
    const selector = type === 'success' ? this.selectors.toastSuccess : this.selectors.toastError
    try {
      await this.page.locator(selector).waitFor({ state: 'visible', timeout })
      return true
    } catch {
      return false
    }
  }
}
