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

    // Selectors - using multiple fallbacks for flexibility during terminology refactor
    // Strategy: Prefer data-testid (stable) > aria-label (accessible) > text content (fragile)
    // Fallbacks ensure tests work during incremental UI updates (Phases 1-8)
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
      // View mode buttons scoped to role="group" to avoid matching "Today" button
      dayViewButton: '[role="group"][aria-label="View mode"] button:has-text("Day")',
      weekViewButton: '[role="group"][aria-label="View mode"] button:has-text("Week")',
      monthViewButton: '[role="group"][aria-label="View mode"] button:has-text("Month")',
      todayButton: 'button:has-text("Today")',
      prevButton: '[data-testid="calendar-nav-previous"], button[aria-label="Previous"]',
      nextButton: '[data-testid="calendar-nav-next"], button[aria-label="Next"]',
      emptyCalendarState: 'text=No schedule selected',
      // data-testid preferred, CSS class fallback for pre-deployment compatibility
      calendarDateDisplay: '[data-testid="calendar-date-display"], #calendar-panel span.text-lg.font-semibold',

      // Loading states
      loadingSpinner: '.loading, [data-testid="loading-spinner"]',
      emptySchedulesState: 'text=No schedules',

      // Toast notifications
      toastSuccess: '.toast-success, [class*="toast"]:has-text("success")',
      toastError: '.toast-error, [class*="toast"]:has-text("error"), [class*="toast"]:has-text("fail")',

      // Routine Selection (formerly Event Pattern)
      routineTabLibrary: '[data-testid="routine-tab-library"], button[role="tab"]:has-text("Library")',
      routineTabCustom: '[data-testid="routine-tab-custom"], button[role="tab"]:has-text("Custom")',
      routineCard: '[data-testid^="routine-"], [role="article"][aria-label^="Routine:"]',
      selectedRoutineSummary: '[data-testid="selected-routine-summary"]',
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
   * Click Save button in editor and wait for API response
   */
  async clickSave() {
    // Wait for either create (POST) or update (PUT) API response
    const savePromise = this.page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/scheduler/ui/schedules') &&
        (resp.request().method() === 'POST' || resp.request().method() === 'PUT') &&
        resp.status() < 400,
      { timeout: TIMEOUTS.NETWORK }
    )

    await this.page.click(this.selectors.saveButton)

    try {
      await savePromise
      // Wait for drawer to close after successful save
      await this.waitForEditorClose()
    } catch {
      // If no API response (e.g., validation error prevented submission),
      // the test will verify this via isEditorOpen() check
      // Still wait a moment for any error messages to appear
      await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
    }
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
  // Routine Selection (formerly Event Pattern)
  // ============================================================

  /**
   * Select the first available routine from the library
   * @returns {Promise<boolean>} True if a routine was selected
   * @deprecated #329 - Use selectFirstRoutine() instead. This method kept for backward compatibility.
   */
  async selectFirstEventPattern() {
    return this.selectFirstRoutine()
  }

  /**
   * Select the first available routine from the library
   * @returns {Promise<boolean>} True if a routine was selected
   */
  async selectFirstRoutine() {
    // Wait for routines to load - look for "Use Routine" or "Add Routine" button
    // Prefer data-testid (more stable) over aria-label (may change with UI text updates)
    const useRoutineButton = this.page.locator('[data-testid="add-routine"], button[aria-label="Use Routine"]').first()
    try {
      await useRoutineButton.waitFor({ state: 'visible', timeout: TIMEOUTS.MEDIUM })
      // Scroll the button into view to ensure it's clickable
      await useRoutineButton.scrollIntoViewIfNeeded()
      await useRoutineButton.click()
      // Wait for routine to be applied and UI to update
      await this.page.waitForTimeout(TIMEOUTS.SAVE)
      return true
    } catch {
      // No routines available or button not found, try clicking routine card as fallback
      const routineCard = this.page.locator(this.selectors.routineCard).first()
      try {
        await routineCard.waitFor({ state: 'visible', timeout: TIMEOUTS.SHORT })
        await routineCard.scrollIntoViewIfNeeded()
        await routineCard.click()
        return true
      } catch {
        return false
      }
    }
  }

  /**
   * Check if a routine is currently selected
   * @returns {Promise<boolean>}
   * @deprecated #329 - Use isRoutineSelected() instead. This method kept for backward compatibility.
   */
  async isEventPatternSelected() {
    return this.isRoutineSelected()
  }

  /**
   * Check if a routine is currently selected
   * @returns {Promise<boolean>}
   */
  async isRoutineSelected() {
    const summary = this.page.locator(this.selectors.selectedRoutineSummary)
    return summary.isVisible()
  }

  // ============================================================
  // Routine Creation Workflow (Per-Routine Triggers)
  // ============================================================

  /**
   * Click the "Add Routine" button to start creating a new routine
   */
  async clickAddRoutine() {
    await this.page.click('[data-testid="add-routine"]')
    await this.waitForNewRoutineCard()
  }

  /**
   * Wait for the NewRoutineCard to appear
   */
  async waitForNewRoutineCard() {
    await this.page.locator('[data-testid="new-routine-card"]').waitFor({
      state: 'visible',
      timeout: TIMEOUTS.MEDIUM
    })
  }

  /**
   * Save the current routine being edited
   */
  async saveRoutine() {
    await this.page.click('[data-testid="save-routine"]')
    await this.page.waitForTimeout(TIMEOUTS.SAVE)
  }

  /**
   * Cancel creating a new routine
   */
  async cancelNewRoutine() {
    await this.page.click('[data-testid="cancel-new-routine"]')
  }

  // ============================================================
  // Scoped Trigger Methods (within NewRoutineCard)
  // ============================================================

  /**
   * Select trigger type within the NewRoutineCard context
   * @param {'interval' | 'solar' | 'fixed_time' | 'moon_phase' | 'cron'} triggerType
   */
  async selectTriggerTypeInRoutine(triggerType) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="trigger-type"]').selectOption(triggerType)
    await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
  }

  /**
   * Fill interval minutes within the NewRoutineCard context
   * @param {number} minutes
   */
  async fillIntervalMinutesInRoutine(minutes) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="interval-minutes"]').fill(String(minutes))
  }

  /**
   * Select solar event within the NewRoutineCard context
   * @param {string} event - e.g., 'dusk', 'dawn', 'sunrise', 'sunset'
   */
  async selectSolarEventInRoutine(event) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="solar-event"]').selectOption(event)
  }

  /**
   * Fill fixed time within the NewRoutineCard context
   * @param {string} time - HH:MM format
   */
  async fillFixedTimeInRoutine(time) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="fixed-time-input-0"]').fill(time)
  }

  /**
   * Select moon phase within the NewRoutineCard context
   * @param {string} phase - e.g., 'full', 'new', 'first_quarter', 'last_quarter'
   */
  async selectMoonPhaseInRoutine(phase) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator(`[data-testid="moon-phase-${phase}"]`).check()
  }

  /**
   * Uncheck a moon phase within the NewRoutineCard context
   * @param {string} phase
   */
  async deselectMoonPhaseInRoutine(phase) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator(`[data-testid="moon-phase-${phase}"]`).uncheck()
  }

  // ============================================================
  // Action Methods (within NewRoutineCard)
  // ============================================================

  /**
   * Click "Add Action" button within the NewRoutineCard
   */
  async clickAddActionInRoutine() {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="add-action"]').click()
    await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
  }

  /**
   * Select action type for a specific action within the routine
   * @param {number} index - Action index (0-based)
   * @param {string} type - e.g., 'gpio', 'camera', 'gps_sync', 'service'
   */
  async selectActionTypeInRoutine(index, type) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    // ActionForm uses data-testid="action-type" - we need to find the right one by index
    await card.locator('[data-testid="action-type"]').nth(index).selectOption(type)
  }

  /**
   * Select action name for a specific action within the routine
   * @param {number} index - Action index (0-based)
   * @param {string} name - e.g., 'attract_on', 'attract_off', 'takephoto'
   */
  async selectActionNameInRoutine(index, name) {
    const card = this.page.locator('[data-testid="new-routine-card"]')
    await card.locator('[data-testid="action-name"]').nth(index).selectOption(name)
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
    await this.page.click(this.selectors.prevButton)
    await this.page.waitForLoadState('networkidle')
  }

  /**
   * Click Next navigation button
   */
  async clickNext() {
    await this.page.click(this.selectors.nextButton)
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

  // ============================================================
  // Trigger Type Selection
  // ============================================================

  /**
   * Select a trigger type from the dropdown
   * @param {'interval' | 'solar' | 'moon_phase' | 'fixed_time' | 'sensor'} triggerType
   */
  async selectTriggerType(triggerType) {
    // data-testid preferred, #trigger_type fallback for pre-deployment compatibility
    await this.page.selectOption('[data-testid="trigger-type"], #trigger_type', triggerType)
    // Wait for the form to update
    await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
  }

  /**
   * Get currently selected trigger type
   * @returns {Promise<string>}
   */
  async getSelectedTriggerType() {
    // data-testid preferred, #trigger_type fallback for pre-deployment compatibility
    return this.page.locator('[data-testid="trigger-type"], #trigger_type').inputValue()
  }

  // ============================================================
  // Interval Trigger Form
  // ============================================================

  /**
   * Fill the interval minutes field
   * @param {number} minutes
   */
  async fillIntervalMinutes(minutes) {
    await this.page.fill('#interval_minutes', String(minutes))
  }

  /**
   * Click an interval preset button
   * @param {string} label - e.g., '15 min', '30 min', '60 min'
   */
  async clickIntervalPreset(label) {
    await this.page.click(`button:has-text("${label}")`)
  }

  /**
   * Select start time type (fixed or solar)
   * @param {'fixed' | 'solar'} type
   */
  async selectStartTimeType(type) {
    if (type === 'fixed') {
      await this.page.click('label:has-text("Fixed Time"):near(:text("Start Time"))')
    } else {
      await this.page.click('label:has-text("Solar Event"):near(:text("Start Time"))')
    }
    await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
  }

  /**
   * Select end time type (fixed or solar)
   * @param {'fixed' | 'solar'} type
   */
  async selectEndTimeType(type) {
    if (type === 'fixed') {
      await this.page.click('label:has-text("Fixed Time"):near(:text("End Time"))')
    } else {
      await this.page.click('label:has-text("Solar Event"):near(:text("End Time"))')
    }
    await this.page.waitForTimeout(TIMEOUTS.TRANSITION)
  }

  /**
   * Fill fixed start time
   * @param {string} time - HH:MM format
   */
  async fillStartTime(time) {
    await this.page.fill('input[aria-label="Start time (fixed)"]', time)
  }

  /**
   * Fill fixed end time
   * @param {string} time - HH:MM format
   */
  async fillEndTime(time) {
    await this.page.fill('input[aria-label="End time (fixed)"]', time)
  }

  /**
   * Select solar event for start time
   * @param {string} event - e.g., 'sunset', 'sunrise', 'dusk', 'dawn'
   */
  async selectStartSolarEvent(event) {
    await this.page.selectOption('select[aria-label="Start time (solar event)"]', event)
  }

  /**
   * Select solar event for end time
   * @param {string} event - e.g., 'sunset', 'sunrise', 'dusk', 'dawn'
   */
  async selectEndSolarEvent(event) {
    await this.page.selectOption('select[aria-label="End time (solar event)"]', event)
  }

  /**
   * Fill start time offset (for solar events)
   * @param {number} minutes
   */
  async fillStartOffset(minutes) {
    await this.page.fill('#start_offset', String(minutes))
  }

  /**
   * Fill end time offset (for solar events)
   * @param {number} minutes
   */
  async fillEndOffset(minutes) {
    await this.page.fill('#end_offset', String(minutes))
  }

  // ============================================================
  // Moon Phase Trigger Form
  // ============================================================

  /**
   * Select a moon phase
   * @param {string} phase - e.g., 'full', 'new', 'first_quarter', 'last_quarter'
   */
  async selectMoonPhase(phase) {
    await this.page.selectOption('#moon_phase', phase)
  }

  /**
   * Get selected moon phase
   * @returns {Promise<string>}
   */
  async getSelectedMoonPhase() {
    return this.page.locator('#moon_phase').inputValue()
  }

  /**
   * Fill moon phase time of day
   * @param {string} time - HH:MM format
   */
  async fillMoonPhaseTime(time) {
    await this.page.fill('#time_of_day', time)
  }

  /**
   * Fill moon phase offset days
   * @param {number} days
   */
  async fillMoonPhaseOffset(days) {
    await this.page.fill('#offset_days', String(days))
  }

  /**
   * Click moon phase offset preset
   * @param {string} label - e.g., '-1 day', 'No offset', '+1 day'
   */
  async clickMoonPhaseOffsetPreset(label) {
    await this.page.click(`button:has-text("${label}")`)
  }

  // ============================================================
  // Fixed Time Trigger Form
  // ============================================================

  /**
   * Fill fixed time of day (for fixed_time trigger)
   * @param {string} time - HH:MM format
   */
  async fillFixedTimeOfDay(time) {
    await this.page.fill('#time_of_day', time)
  }

  /**
   * Click a time preset button
   * @param {string} label - e.g., '6 AM', '12 PM', '6 PM', '9 PM'
   */
  async clickTimePreset(label) {
    await this.page.click(`button:has-text("${label}")`)
  }

  // ============================================================
  // Days of Week Selector
  // ============================================================

  /**
   * Toggle a specific day of the week
   * @param {string} dayLabel - e.g., 'Mon', 'Tue', 'Wed', etc.
   */
  async toggleDay(dayLabel) {
    await this.page.click(`button[aria-label="${this.getDayFullLabel(dayLabel)}"]`)
  }

  /**
   * Click "All Days" button
   */
  async clickAllDays() {
    await this.page.click('button:has-text("All Days")')
  }

  /**
   * Get full day label from short label
   * @param {string} shortLabel
   * @returns {string}
   */
  getDayFullLabel(shortLabel) {
    const dayMap = {
      'Mon': 'Monday',
      'Tue': 'Tuesday',
      'Wed': 'Wednesday',
      'Thu': 'Thursday',
      'Fri': 'Friday',
      'Sat': 'Saturday',
      'Sun': 'Sunday',
    }
    return dayMap[shortLabel] || shortLabel
  }

  // ============================================================
  // Date Range Section
  // ============================================================

  /**
   * Fill start date
   * @param {string} date - YYYY-MM-DD format
   */
  async fillStartDate(date) {
    await this.page.fill('#start-date', date)
  }

  /**
   * Fill end date
   * @param {string} date - YYYY-MM-DD format
   */
  async fillEndDate(date) {
    await this.page.fill('#end-date', date)
  }

  /**
   * Clear start date
   */
  async clearStartDate() {
    await this.page.click('button[aria-label="Clear start date"]')
  }

  /**
   * Clear end date
   */
  async clearEndDate() {
    await this.page.click('button[aria-label="Clear end date"]')
  }

  // ============================================================
  // Routine Selection (Extended) - formerly Event Pattern
  // ============================================================

  /**
   * Select a routine by name
   * @param {string} routineName
   * @returns {Promise<boolean>} True if routine was found and selected
   */
  async selectRoutineByName(routineName) {
    const routineCard = this.page.locator(`[data-testid^="routine-"]:has-text("${routineName}"), [role="article"][aria-label^="Routine: ${routineName}"]`)
    try {
      await routineCard.waitFor({ state: 'visible', timeout: TIMEOUTS.MEDIUM })
      await routineCard.click()
      return true
    } catch {
      return false
    }
  }

  /**
   * @deprecated #329 - Use selectRoutineByName() instead. This method kept for backward compatibility.
   */
  async selectEventPatternByName(patternName) {
    return this.selectRoutineByName(patternName)
  }

  /**
   * Check if a routine with the given name exists
   * @param {string} routineName
   * @returns {Promise<boolean>}
   */
  async hasRoutineWithName(routineName) {
    const routineCard = this.page.locator(`[data-testid^="routine-"]:has-text("${routineName}"), [role="article"][aria-label^="Routine: ${routineName}"]`)
    return routineCard.isVisible()
  }

  /**
   * @deprecated #329 - Use hasRoutineWithName() instead. This method kept for backward compatibility.
   */
  async hasPatternWithName(patternName) {
    return this.hasRoutineWithName(patternName)
  }

  /**
   * Get count of available routines
   * @returns {Promise<number>}
   */
  async getRoutineCount() {
    return this.page.locator(this.selectors.routineCard).count()
  }

  /**
   * @deprecated #329 - Use getRoutineCount() instead. This method kept for backward compatibility.
   */
  async getPatternCount() {
    return this.getRoutineCount()
  }

  // ============================================================
  // Preview Section
  // ============================================================

  /**
   * Get the trigger preview text
   * @returns {Promise<string|null>}
   */
  async getTriggerPreviewText() {
    const preview = this.page.locator('.italic.bg-gray-50, .italic.dark\\:bg-gray-800')
    if (await preview.isVisible()) {
      return preview.textContent()
    }
    return null
  }

  // ============================================================
  // Full Scenario Helpers
  // ============================================================

  /**
   * Create a complete schedule with interval trigger
   * @param {Object} config - Schedule configuration
   * @param {string} config.name - Schedule name
   * @param {string} config.description - Schedule description
   * @param {number} config.interval - Interval in minutes (default: 15)
   * @param {number} config.intervalMinutes - Alias for config.interval (deprecated)
   * @returns {Promise<boolean>} True if schedule was created successfully
   */
  async createIntervalSchedule(config) {
    await this.clickNewSchedule()
    await this.fillScheduleName(config.name)
    if (config.description) {
      await this.fillScheduleDescription(config.description)
    }

    // Add routine with interval trigger
    await this.clickAddRoutine()
    await this.selectTriggerTypeInRoutine('interval')
    await this.fillIntervalMinutesInRoutine(config.interval || config.intervalMinutes || 15)

    // Add at least one action (attract_on by default)
    await this.clickAddActionInRoutine()
    await this.selectActionTypeInRoutine(0, 'gpio')
    await this.selectActionNameInRoutine(0, 'attract_on')

    await this.saveRoutine()
    await this.clickSave()
    await this.waitForLoad()
    return !(await this.isEditorOpen())
  }

  /**
   * Create a complete schedule with moon phase trigger
   * @param {Object} config - Schedule configuration
   * @param {string} config.name - Schedule name
   * @param {string} config.description - Schedule description
   * @param {string} config.moonPhase - Moon phase (full, new, first_quarter, last_quarter)
   * @param {string} config.timeOfDay - Time of day (HH:MM) - currently not used in per-routine workflow
   * @param {number} config.offsetDays - Offset days - currently not used in per-routine workflow
   * @returns {Promise<boolean>} True if schedule was created successfully
   */
  async createMoonPhaseSchedule(config) {
    await this.clickNewSchedule()
    await this.fillScheduleName(config.name)
    if (config.description) {
      await this.fillScheduleDescription(config.description)
    }

    // Add routine with moon phase trigger
    await this.clickAddRoutine()
    await this.selectTriggerTypeInRoutine('moon_phase')
    await this.selectMoonPhaseInRoutine(config.moonPhase || 'full')

    // Add at least one action (attract_on by default)
    await this.clickAddActionInRoutine()
    await this.selectActionTypeInRoutine(0, 'gpio')
    await this.selectActionNameInRoutine(0, 'attract_on')

    await this.saveRoutine()
    await this.clickSave()
    await this.waitForLoad()
    return !(await this.isEditorOpen())
  }

  /**
   * Create a complete schedule with fixed time trigger
   * @param {Object} config - Schedule configuration
   * @param {string} config.name - Schedule name
   * @param {string} config.description - Schedule description
   * @param {string} config.timeOfDay - Time of day (HH:MM)
   * @param {Array<number>|null} config.daysOfWeek - Days of week (null for all days) - currently not used
   * @returns {Promise<boolean>} True if schedule was created successfully
   */
  async createFixedTimeSchedule(config) {
    await this.clickNewSchedule()
    await this.fillScheduleName(config.name)
    if (config.description) {
      await this.fillScheduleDescription(config.description)
    }

    // Add routine with fixed time trigger
    await this.clickAddRoutine()
    await this.selectTriggerTypeInRoutine('fixed_time')
    await this.fillFixedTimeInRoutine(config.timeOfDay || '21:00')

    // Add at least one action (attract_on by default)
    await this.clickAddActionInRoutine()
    await this.selectActionTypeInRoutine(0, 'gpio')
    await this.selectActionNameInRoutine(0, 'attract_on')

    await this.saveRoutine()
    await this.clickSave()
    await this.waitForLoad()
    return !(await this.isEditorOpen())
  }
}
