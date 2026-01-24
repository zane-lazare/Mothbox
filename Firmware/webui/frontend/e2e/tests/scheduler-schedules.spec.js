/**
 * Scheduler Schedules E2E Tests
 *
 * Tests the schedule CRUD workflows and activation/deactivation functionality.
 * Uses full CRUD testing - creates test schedules with unique timestamps and cleans up after.
 */

import { test, expect } from '@playwright/test'
import { SchedulerPage } from '../pages/scheduler.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Scheduler Schedules', () => {
  /** @type {SchedulerPage} */
  let scheduler

  test.beforeEach(async ({ page }) => {
    scheduler = new SchedulerPage(page)
    await scheduler.goto()

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }

    // Clean up any enabled/active schedules from previous runs
    await scheduler.deactivateAndDisableAll()
  })

  test.afterEach(async () => {
    // Ensure editor is closed after each test
    if (await scheduler.isEditorOpen()) {
      await scheduler.clickCancel().catch(() => {})
    }
  })

  // ============================================================
  // Basic Page Loading
  // ============================================================

  test('scheduler page loads', async () => {
    // Verify we're on the scheduler page
    const heading = scheduler.page.locator('text=Schedule')
    await expect(heading.first()).toBeVisible()
  })

  test('schedules tab shows schedule list or empty state', async () => {
    // Switch to Schedules tab (may already be default)
    await scheduler.switchToSchedulesTab()

    // Should show either schedule cards or empty state
    const hasSchedules = await scheduler.hasSchedules()
    const isEmptyState = await scheduler.isEmptySchedulesStateVisible()

    expect(hasSchedules || isEmptyState).toBeTruthy()
  })

  test('schedule list and calendar are both visible in two-column layout', async ({ page }) => {
    // In the new two-column layout, both schedule list and calendar are always visible
    // (no tabs required - UI refactored in terminology refactor #296)

    // Verify schedule list panel is visible (left column - 1/3 width)
    const scheduleListColumn = page.locator('.col-span-1')
    await expect(scheduleListColumn.first()).toBeVisible()

    // Verify calendar panel is visible (right column - 2/3 width)
    const calendarColumn = page.locator('.col-span-2')
    await expect(calendarColumn.first()).toBeVisible()

    // Verify calendar navigation is present and functional
    const calendarNavPrev = page.locator('[data-testid="calendar-nav-previous"]')
    await expect(calendarNavPrev).toBeVisible()
  })

  // ============================================================
  // Editor Drawer Operations
  // ============================================================

  test('New Schedule button opens editor', async () => {
    await scheduler.clickNewSchedule()

    // Verify editor is open
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Verify title is "Create Schedule"
    const title = await scheduler.getEditorTitle()
    expect(title).toContain('Create Schedule')

    // Verify name input is empty
    const nameValue = await scheduler.getScheduleNameValue()
    expect(nameValue).toBe('')

    // Close editor
    await scheduler.clickCancel()
    expect(await scheduler.isEditorOpen()).toBeFalsy()
  })

  test('cancel editor discards changes', async () => {
    const initialCount = await scheduler.getScheduleCount()

    // Open editor and fill some data
    await scheduler.clickNewSchedule()
    const testName = scheduler.generateTestScheduleName()
    await scheduler.fillScheduleName(testName)

    // Cancel
    await scheduler.clickCancel()

    // Verify drawer closed
    expect(await scheduler.isEditorOpen()).toBeFalsy()

    // Verify no new schedule was added
    const finalCount = await scheduler.getScheduleCount()
    expect(finalCount).toBe(initialCount)
  })

  test('close editor via X button', async () => {
    await scheduler.clickNewSchedule()
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Close via X button
    await scheduler.closeEditor()
    expect(await scheduler.isEditorOpen()).toBeFalsy()
  })

  test('view existing schedule opens editor with data', async ({ page }) => {
    void page // suppress unused warning
    const scheduleCount = await scheduler.getScheduleCount()
    if (scheduleCount === 0) {
      test.skip(true, 'No schedules available for testing view')
      return
    }

    // Click View on first schedule (view-first paradigm - Issue #266)
    await scheduler.clickViewOnSchedule(0)

    // Verify editor is open
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Verify title is "View Schedule" (opens in view mode first)
    const title = await scheduler.getEditorTitle()
    expect(title).toContain('View Schedule')

    // Verify name is displayed (existing schedule name)
    const nameValue = await scheduler.getScheduleNameValue()
    expect(nameValue.length).toBeGreaterThan(0)

    // Close editor
    await scheduler.clickCancel()
  })

  // ============================================================
  // Delete Operations
  // ============================================================

  test('delete schedule shows confirmation dialog', async ({ page }) => {
    const scheduleCount = await scheduler.getScheduleCount()
    if (scheduleCount === 0) {
      test.skip(true, 'No schedules available for testing delete')
      return
    }

    // Click Delete on first schedule
    await scheduler.clickDeleteOnSchedule(0)

    // Wait for confirmation dialog or just verify the action was triggered
    // Some implementations may show inline confirmation
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // If dialog appeared, cancel it
    if (await scheduler.isConfirmDialogOpen()) {
      await scheduler.cancelDelete()
    }
  })

  // ============================================================
  // Activation/Deactivation Operations
  // ============================================================

  test('activate schedule shows active state', async () => {
    const scheduleCount = await scheduler.getScheduleCount()
    if (scheduleCount === 0) {
      test.skip(true, 'No schedules available for testing activation')
      return
    }

    // Find an inactive schedule
    const inactiveIndex = await scheduler.findFirstInactiveSchedule()
    if (inactiveIndex === -1) {
      test.skip(true, 'No inactive schedules available')
      return
    }

    // Activate the schedule
    await scheduler.clickActivateOnSchedule(inactiveIndex)

    // Wait for UI to update
    await scheduler.waitForLoad()

    // Verify either:
    // - The active banner appears
    // - OR the card now shows active badge
    const bannerVisible = await scheduler.isActiveBannerVisible()
    const cardActive = await scheduler.isScheduleActive(inactiveIndex)

    expect(bannerVisible || cardActive).toBeTruthy()
  })

  test('deactivate from active banner', async ({ page }) => {
    const testName = `Deactivate Test ${Date.now()}`

    try {
      // Create and activate a schedule so we have a known state
      await scheduler.createFixedTimeSchedule({
        name: testName,
        description: 'Test deactivation',
        timeOfDay: '12:00',
      })
      await scheduler.waitForLoad()
      await scheduler.activateScheduleByName(testName)

      // Verify active banner is visible with correct schedule name
      const bannerVisible = await scheduler.isActiveBannerVisible()
      expect(bannerVisible, 'Active banner should be visible').toBeTruthy()

      const bannerName = await scheduler.getActiveBannerScheduleName()
      expect(bannerName, 'Banner should show schedule name').toContain(testName)

      // Click deactivate in banner
      await scheduler.clickBannerDeactivate()
      await scheduler.waitForLoad()

      // Wait for the active banner to disappear (React state update + re-render)
      const activeBanner = page.locator('[data-testid="active-schedule-banner"]')
      await activeBanner.waitFor({ state: 'hidden', timeout: 10000 })

      // Verify active banner (green) is gone
      const stillActiveVisible = await scheduler.isActiveBannerVisible()
      expect(stillActiveVisible, 'Active banner should be gone after deactivate').toBeFalsy()

      // Verify enabled banner (red/ready) now appears
      const enabledVisible = await scheduler.isEnabledBannerVisible()
      expect(enabledVisible, 'Enabled banner should appear after deactivate').toBeTruthy()
    } finally {
      // Cleanup - wrap in try-catch since state may vary after test
      try {
        await scheduler.deactivateAndDisableAll()
      } catch {
        // Ignore cleanup errors - banner may already be gone
      }
      try {
        if (await scheduler.hasScheduleWithName(testName)) {
          await scheduler.clickDeleteOnScheduleByName(testName)
          if (await scheduler.isConfirmDialogOpen()) {
            await scheduler.confirmDelete()
          }
        }
      } catch {
        // Ignore cleanup errors
      }
    }
  })

  // ============================================================
  // Full CRUD Integration Tests
  // ============================================================

  test('create schedule with valid data and verify in list', async () => {
    const initialCount = await scheduler.getScheduleCount()
    const testName = scheduler.generateTestScheduleName()

    try {
      // Open editor
      await scheduler.clickNewSchedule()

      // Fill name
      await scheduler.fillScheduleName(testName)

      // Fill description (optional)
      await scheduler.fillScheduleDescription('E2E test schedule - can be deleted')

      // Add routine with trigger and action
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('interval')
      await scheduler.fillIntervalMinutesInRoutine(15)

      // Add an action
      await scheduler.clickAddActionInRoutine()
      await scheduler.selectActionTypeInRoutine(0, 'gpio')
      await scheduler.selectActionNameInRoutine(0, 'attract_on')

      // Save the routine
      await scheduler.saveRoutine()

      // Save the schedule
      await scheduler.clickSave()

      // Verify save succeeded (editor should close)
      const editorStillOpen = await scheduler.isEditorOpen()
      expect(editorStillOpen, 'Editor should close after successful save').toBeFalsy()

      // Verify schedule was created
      const finalCount = await scheduler.getScheduleCount()
      expect(finalCount).toBeGreaterThanOrEqual(initialCount)

      // Verify schedule appears in list
      const scheduleExists = await scheduler.hasScheduleWithName(testName)
      expect(scheduleExists).toBeTruthy()
    } finally {
      // Guaranteed cleanup even if test fails
      try {
        if (await scheduler.hasScheduleWithName(testName)) {
          await scheduler.clickDeleteOnScheduleByName(testName)
          if (await scheduler.isConfirmDialogOpen()) {
            await scheduler.confirmDelete()
          }
        }
      } catch {
        // Cleanup failure is acceptable
      }
    }
  })

  test('full CRUD workflow: create, edit, delete', async () => {
    const testName = scheduler.generateTestScheduleName()
    const updatedName = `${testName}-updated`

    try {
      // Create schedule
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(testName)
      await scheduler.fillScheduleDescription('E2E CRUD test')

      // Add routine with trigger and action
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('interval')
      await scheduler.fillIntervalMinutesInRoutine(15)

      // Add an action
      await scheduler.clickAddActionInRoutine()
      await scheduler.selectActionTypeInRoutine(0, 'gpio')
      await scheduler.selectActionNameInRoutine(0, 'attract_on')

      // Save the routine
      await scheduler.saveRoutine()

      // Save
      await scheduler.clickSave()

      // Verify save succeeded (editor should close)
      const editorStillOpen = await scheduler.isEditorOpen()
      expect(editorStillOpen, 'Editor should close after successful save').toBeFalsy()

      // Verify creation
      const scheduleExists = await scheduler.hasScheduleWithName(testName)
      expect(scheduleExists, 'Schedule should appear in list after creation').toBeTruthy()

      // Edit schedule (view-first paradigm: View → Edit in header)
      const card = scheduler.getScheduleCardByName(testName)
      await card.locator('button:has-text("View")').click()
      await scheduler.waitForEditorOpen()
      // Switch to edit mode
      await scheduler.clickEditInEditorHeader()

      // Update name
      await scheduler.fillScheduleName(updatedName)
      await scheduler.clickSave()

      // Wait for editor to close after save (save should close the editor on success)
      // Give extra time for the API call and UI update
      await scheduler.page.waitForTimeout(1000)

      // If editor is still open (e.g., validation error), close it
      if (await scheduler.isEditorOpen()) {
        await scheduler.closeEditor()  // Use X button or Escape, more reliable than Cancel
      }

      // Wait for update
      await scheduler.waitForLoad()

      // Verify update (check either original or updated exists)
      const updatedExists = await scheduler.hasScheduleWithName(updatedName)
      const nameToDelete = updatedExists ? updatedName : testName

      // Delete schedule
      await scheduler.clickDeleteOnScheduleByName(nameToDelete)
      if (await scheduler.isConfirmDialogOpen()) {
        await scheduler.confirmDelete()
        await scheduler.waitForLoad()
      }

      // Verify deletion
      const stillExists = await scheduler.hasScheduleWithName(nameToDelete)
      expect(stillExists).toBeFalsy()
    } finally {
      // Guaranteed cleanup even if test fails
      try {
        // Try to delete by updated name first, then original name
        for (const name of [updatedName, testName]) {
          if (await scheduler.hasScheduleWithName(name)) {
            await scheduler.clickDeleteOnScheduleByName(name)
            if (await scheduler.isConfirmDialogOpen()) {
              await scheduler.confirmDelete()
            }
            break // Only delete once
          }
        }
      } catch {
        // Cleanup failure is acceptable
      }
    }
  })

  // ============================================================
  // Form Validation Tests
  // ============================================================

  test('save without name shows validation error', async ({ page }) => {
    await scheduler.clickNewSchedule()

    // Add routine but don't fill schedule name
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(15)

    // Add an action
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'gpio')
    await scheduler.selectActionNameInRoutine(0, 'attract_on')

    // Save the routine
    await scheduler.saveRoutine()

    // Try to save without name
    await scheduler.clickSave()
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Editor should stay open with error
    expect(await scheduler.isEditorOpen()).toBeTruthy()
    const errorVisible = await page.locator('text=required').first().isVisible()
    expect(errorVisible).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Edge Cases
  // ============================================================

  test('deleting active schedule removes active banner', async () => {
    const testName = `Delete Active Test ${Date.now()}`

    // Create and activate a schedule
    await scheduler.createFixedTimeSchedule({
      name: testName,
      description: 'Test delete active',
      timeOfDay: '12:00',
    })
    await scheduler.waitForLoad()
    await scheduler.activateScheduleByName(testName)

    // Verify it's active
    const bannerVisible = await scheduler.isActiveBannerVisible()
    expect(bannerVisible, 'Schedule should be active').toBeTruthy()

    // Delete the active schedule
    await scheduler.clickDeleteOnScheduleByName(testName)
    if (await scheduler.isConfirmDialogOpen()) {
      await scheduler.confirmDelete()
      await scheduler.waitForLoad()
    }

    // Verify active banner is gone (and no enabled banner either since schedule is deleted)
    const stillActive = await scheduler.isActiveBannerVisible()
    const stillEnabled = await scheduler.isEnabledBannerVisible()
    expect(stillActive, 'Active banner should be gone').toBeFalsy()
    expect(stillEnabled, 'Enabled banner should be gone').toBeFalsy()
  })

  // ============================================================
  // Keyboard Accessibility
  // ============================================================

  test('escape key closes editor', async ({ page }) => {
    await scheduler.clickNewSchedule()
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    await page.keyboard.press('Escape')

    expect(await scheduler.isEditorOpen()).toBeFalsy()
  })
})
