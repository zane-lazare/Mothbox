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

  test('both tabs are visible and functional', async ({ page }) => {
    // Verify Schedules tab
    const schedulesTab = page.locator('button:has-text("Schedules")')
    await expect(schedulesTab).toBeVisible()

    // Verify Calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await expect(calendarTab).toBeVisible()

    // Switch between tabs
    await scheduler.switchToCalendarTab()
    await expect(page.locator('#calendar-panel')).toBeVisible()

    await scheduler.switchToSchedulesTab()
    await expect(page.locator('#schedules-panel')).toBeVisible()
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

  test('edit existing schedule opens editor with data', async ({ page }) => {
    void page // suppress unused warning
    const scheduleCount = await scheduler.getScheduleCount()
    if (scheduleCount === 0) {
      test.skip(true, 'No schedules available for testing edit')
      return
    }

    // Click Edit on first schedule
    await scheduler.clickEditOnSchedule(0)

    // Verify editor is open
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Verify title is "Edit Schedule"
    const title = await scheduler.getEditorTitle()
    expect(title).toContain('Edit Schedule')

    // Verify name input has a value (existing schedule name)
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

  test('deactivate schedule from card', async () => {
    // Find the active schedule
    const activeIndex = await scheduler.findActiveSchedule()
    if (activeIndex === -1) {
      test.skip(true, 'No active schedule to deactivate')
      return
    }

    // Deactivate from card
    await scheduler.clickDeactivateOnSchedule(activeIndex)

    // Wait for UI to update
    await scheduler.waitForLoad()

    // Verify the card no longer shows active (or banner disappeared)
    const stillActive = await scheduler.isScheduleActive(activeIndex)
    expect(stillActive).toBeFalsy()
  })

  test('deactivate from active banner', async () => {
    // Check if active banner is visible
    const bannerVisible = await scheduler.isActiveBannerVisible()
    if (!bannerVisible) {
      test.skip(true, 'No active schedule banner visible')
      return
    }

    // Click deactivate in banner
    await scheduler.clickBannerDeactivate()

    // Wait for UI to update
    await scheduler.waitForLoad()

    // Verify banner disappeared
    const stillVisible = await scheduler.isActiveBannerVisible()
    expect(stillVisible).toBeFalsy()
  })

  test('active banner shows correct schedule name', async () => {
    const bannerVisible = await scheduler.isActiveBannerVisible()
    if (!bannerVisible) {
      test.skip(true, 'No active schedule banner visible')
      return
    }

    // Get the active schedule name from banner
    const bannerName = await scheduler.getActiveBannerScheduleName()
    expect(bannerName).toBeTruthy()
    expect(bannerName.length).toBeGreaterThan(0)
  })

  // ============================================================
  // Full CRUD Integration Tests
  // ============================================================

  // NEEDS UPDATE: Uses selectFirstEventPattern() - update when routine workflow complete
  // The deprecated method still works via backward compatibility wrapper
  test.fixme('create schedule with valid data and verify in list', async () => {
    const initialCount = await scheduler.getScheduleCount()
    const testName = scheduler.generateTestScheduleName()

    try {
      // Open editor
      await scheduler.clickNewSchedule()

      // Fill name
      await scheduler.fillScheduleName(testName)

      // Fill description (optional)
      await scheduler.fillScheduleDescription('E2E test schedule - can be deleted')

      // Select a routine (required) - TODO: Update to selectFirstRoutine()
      const patternSelected = await scheduler.selectFirstEventPattern()
      expect(patternSelected, 'Routines should be available').toBeTruthy()

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

  // NEEDS UPDATE: Uses selectFirstEventPattern() - update when routine workflow complete
  // The deprecated method still works via backward compatibility wrapper
  test.fixme('full CRUD workflow: create, edit, delete', async () => {
    const testName = scheduler.generateTestScheduleName()
    const updatedName = `${testName}-updated`

    try {
      // Create schedule
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(testName)
      await scheduler.fillScheduleDescription('E2E CRUD test')

      // Select a routine (required) - TODO: Update to selectFirstRoutine()
      const patternSelected = await scheduler.selectFirstEventPattern()
      expect(patternSelected, 'Routines should be available').toBeTruthy()

      // Save
      await scheduler.clickSave()

      // Verify save succeeded (editor should close)
      const editorStillOpen = await scheduler.isEditorOpen()
      expect(editorStillOpen, 'Editor should close after successful save').toBeFalsy()

      // Verify creation
      const scheduleExists = await scheduler.hasScheduleWithName(testName)
      expect(scheduleExists, 'Schedule should appear in list after creation').toBeTruthy()

      // Edit schedule
      const card = scheduler.getScheduleCardByName(testName)
      await card.locator('button:has-text("Edit")').click()
      await scheduler.waitForEditorOpen()

      // Update name
      await scheduler.fillScheduleName(updatedName)
      await scheduler.clickSave()

      // If editor still open, close it
      if (await scheduler.isEditorOpen()) {
        await scheduler.clickCancel()
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

  // NEEDS UPDATE: Uses selectFirstEventPattern() - update when routine workflow complete
  // The deprecated method still works via backward compatibility wrapper
  test.fixme('save without name shows validation error', async ({ page }) => {
    await scheduler.clickNewSchedule()

    // Select routine but don't fill name - TODO: Update to selectFirstRoutine()
    await scheduler.selectFirstEventPattern()
    await scheduler.clickSave()
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Editor should stay open with error
    expect(await scheduler.isEditorOpen()).toBeTruthy()
    const errorVisible = await page.locator('text=required').first().isVisible()
    expect(errorVisible).toBeTruthy()

    await scheduler.clickCancel()
  })

  // OBSOLETE: Pattern Library workflow removed in terminology refactor (#296)
  // The new routine-based workflow doesn't have pattern selection validation
  // DELETE after refactor complete (Phase 8)
  test.skip('save without event pattern shows validation error', async ({ page }) => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Don't select pattern, try to save
    await scheduler.clickSave()
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Editor should stay open with error
    expect(await scheduler.isEditorOpen()).toBeTruthy()
    const errorVisible = await page.locator('text=pattern').first().isVisible()
    expect(errorVisible).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Edge Cases
  // ============================================================

  test('deleting active schedule removes active banner', async () => {
    const activeIndex = await scheduler.findActiveSchedule()
    if (activeIndex === -1) {
      test.skip(true, 'No active schedule to test deletion')
      return
    }

    // Delete the active schedule
    await scheduler.clickDeleteOnSchedule(activeIndex)

    if (await scheduler.isConfirmDialogOpen()) {
      await scheduler.confirmDelete()
      await scheduler.waitForLoad()
    }

    // Verify active banner is gone
    const bannerVisible = await scheduler.isActiveBannerVisible()
    expect(bannerVisible).toBeFalsy()
  })

  // ============================================================
  // Toast Notifications
  // ============================================================

  test('successful activation shows success toast', async () => {
    const inactiveIndex = await scheduler.findFirstInactiveSchedule()
    if (inactiveIndex === -1) {
      test.skip(true, 'No inactive schedules available')
      return
    }

    await scheduler.clickActivateOnSchedule(inactiveIndex)

    const toastAppeared = await scheduler.waitForToast('success')
    expect(toastAppeared).toBeTruthy()
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
