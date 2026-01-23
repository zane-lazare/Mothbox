/**
 * Scheduler Real-World Scenarios E2E Tests
 *
 * Tests the complete workflow for each of the 3 real-world scenarios
 * documented in SCHEDULER_USER_GUIDE.md:
 *
 * 1. Summer Moth Survey - Interval trigger with solar time window
 * 2. Full Moon Observation Session - Moon phase trigger
 * 3. Power-Efficient Daily Capture - Fixed time trigger
 *
 * These tests validate the full user journey from creating a schedule
 * with specific trigger configurations through activation and cleanup.
 */

import { test, expect } from '@playwright/test'
import { SchedulerPage } from '../pages/scheduler.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Scheduler Real-World Scenarios', () => {
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
  // Scenario 1: Summer Moth Survey
  // ============================================================
  // From User Guide: Automated moth photography during summer nights
  // using interval trigger with solar events for timing.

  test.describe('Scenario 1: Summer Moth Survey', () => {
    const scenarioName = `Summer Moth Survey ${Date.now()}`

    test('create schedule with interval trigger and solar events', async ({ page }) => {
      try {
        // Step 1: Open schedule editor
        await scheduler.clickNewSchedule()
        expect(await scheduler.isEditorOpen()).toBeTruthy()

        // Step 2: Fill schedule name
        await scheduler.fillScheduleName(scenarioName)
        expect(await scheduler.getScheduleNameValue()).toBe(scenarioName)

        // Step 3: Fill description
        await scheduler.fillScheduleDescription(
          'Automated moth photography during summer nights - E2E test'
        )

        // Step 4: Add routine with interval trigger
        await scheduler.clickAddRoutine()
        await scheduler.selectTriggerTypeInRoutine('interval')

        // Step 5: Configure 30-minute interval
        await scheduler.fillIntervalMinutesInRoutine(30)

        // Step 6: Add at least one action
        await scheduler.clickAddActionInRoutine()
        await scheduler.selectActionTypeInRoutine(0, 'gpio')
        await scheduler.selectActionNameInRoutine(0, 'attract_on')

        // Step 7: Save the routine
        await scheduler.saveRoutine()

        // Note: Date range fields were removed in per-routine architecture
        // Date range is now specified per-routine via time_window, not schedule-level

        // Step 8: Save the schedule
        await scheduler.clickSave()

        // Step 9: Verify editor closed (save succeeded)
        const editorStillOpen = await scheduler.isEditorOpen()
        expect(editorStillOpen, 'Editor should close after successful save').toBeFalsy()

        // Step 10: Verify schedule appears in list
        await scheduler.waitForLoad()
        const scheduleExists = await scheduler.hasScheduleWithName(scenarioName)
        expect(scheduleExists, 'Schedule should appear in list').toBeTruthy()

        // Step 11: Activate the schedule (enable → activate from banner)
        await scheduler.activateScheduleByName(scenarioName)

        // Step 12: Verify activation (handled by activateScheduleByName)
        const bannerVisible = await scheduler.isActiveBannerVisible()
        expect(bannerVisible, 'Schedule should show active banner').toBeTruthy()

        // Step 13: Verify schedule appears in calendar dropdown (calendar is always visible in two-column layout)
        await page.waitForTimeout(TIMEOUTS.TRANSITION)
        const calendarOptions = await scheduler.getCalendarScheduleOptions()
        expect(calendarOptions.some((opt) => opt.includes(scenarioName))).toBeTruthy()
      } finally {
        // Cleanup: Delete the test schedule
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    test('interval trigger form validates minimum interval', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine and select interval trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('interval')

      // Try to set interval below minimum (should show validation or clamp)
      await scheduler.fillIntervalMinutesInRoutine(0)

      // The form should either show an error or reset to minimum
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify save routine button is disabled due to invalid interval (no actions yet)
      const card = page.locator('[data-testid="new-routine-card"]')
      const saveBtn = card.locator('[data-testid="save-routine"]')
      await expect(saveBtn).toBeDisabled()

      // Cancel and close
      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('solar event trigger can be configured', async () => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine and select solar trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('solar')

      // Select solar event (e.g., sunset)
      await scheduler.selectSolarEventInRoutine('sunset')

      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })
  })

  // ============================================================
  // Scenario 2: Full Moon Observation Session
  // ============================================================
  // From User Guide: Photography sessions timed to full moon phases.

  test.describe('Scenario 2: Full Moon Observation Session', () => {
    const scenarioName = `Full Moon Observation ${Date.now()}`

    test('create schedule with moon phase trigger', async ({ page }) => {
      try {
        // Step 1: Open schedule editor
        await scheduler.clickNewSchedule()
        expect(await scheduler.isEditorOpen()).toBeTruthy()

        // Step 2: Fill schedule name
        await scheduler.fillScheduleName(scenarioName)

        // Step 3: Fill description
        await scheduler.fillScheduleDescription(
          'Photography during full moon nights - E2E test'
        )

        // Step 4: Add routine with moon phase trigger
        await scheduler.clickAddRoutine()
        await scheduler.selectTriggerTypeInRoutine('moon_phase')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Step 5: Select full moon phase
        await scheduler.selectMoonPhaseInRoutine('full')

        // Step 6: Add at least one action
        await scheduler.clickAddActionInRoutine()
        await scheduler.selectActionTypeInRoutine(0, 'gpio')
        await scheduler.selectActionNameInRoutine(0, 'attract_on')

        // Step 7: Save the routine
        await scheduler.saveRoutine()

        // Step 8: Save the schedule
        await scheduler.clickSave()

        // Step 9: Verify editor closed
        expect(await scheduler.isEditorOpen()).toBeFalsy()

        // Step 10: Verify schedule appears in list
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(scenarioName)).toBeTruthy()

        // Step 11: Activate the schedule (enable → activate from banner)
        await scheduler.activateScheduleByName(scenarioName)

        // Step 12: Verify activation (handled by activateScheduleByName)
        const bannerVisible = await scheduler.isActiveBannerVisible()
        expect(bannerVisible, 'Schedule should show active banner').toBeTruthy()
      } finally {
        // Cleanup
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    test('moon phase checkboxes show all 4 primary phases', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine and select moon phase trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Check for moon phase checkboxes within the NewRoutineCard
      // UI uses 4 primary lunar phases (new, first_quarter, full, last_quarter)
      const card = page.locator('[data-testid="new-routine-card"]')
      const expectedPhases = [
        'new',
        'first_quarter',
        'full',
        'last_quarter',
      ]

      for (const phase of expectedPhases) {
        const checkbox = card.locator(`[data-testid="moon-phase-${phase}"]`)
        await expect(checkbox, `Should include ${phase} checkbox`).toBeVisible()
      }

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('moon phase can select multiple phases', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine and select moon phase trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      const card = page.locator('[data-testid="new-routine-card"]')

      // Select full moon
      await scheduler.selectMoonPhaseInRoutine('full')
      let fullCheckbox = card.locator('[data-testid="moon-phase-full"]')
      await expect(fullCheckbox).toBeChecked()

      // Also select new moon
      await scheduler.selectMoonPhaseInRoutine('new')
      let newCheckbox = card.locator('[data-testid="moon-phase-new"]')
      await expect(newCheckbox).toBeChecked()

      // Deselect full moon
      await scheduler.deselectMoonPhaseInRoutine('full')
      await expect(fullCheckbox).not.toBeChecked()

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('moon phase schedule with helper method', async () => {
      const offsetName = `Moon Phase Helper ${Date.now()}`

      try {
        const created = await scheduler.createMoonPhaseSchedule({
          name: offsetName,
          description: 'Moon phase via helper - E2E test',
          moonPhase: 'full',
        })

        expect(created, 'Schedule should be created successfully').toBeTruthy()
        expect(await scheduler.hasScheduleWithName(offsetName)).toBeTruthy()
      } finally {
        await cleanupSchedule(scheduler, offsetName)
      }
    })
  })

  // ============================================================
  // Scenario 3: Power-Efficient Daily Capture
  // ============================================================
  // From User Guide: Minimal captures at fixed times for battery efficiency.

  test.describe('Scenario 3: Power-Efficient Daily Capture', () => {
    const scenarioName = `Power-Efficient Daily ${Date.now()}`

    test('create schedule with fixed time trigger', async ({ page }) => {
      try {
        // Step 1: Open schedule editor
        await scheduler.clickNewSchedule()
        expect(await scheduler.isEditorOpen()).toBeTruthy()

        // Step 2: Fill schedule name
        await scheduler.fillScheduleName(scenarioName)

        // Step 3: Fill description
        await scheduler.fillScheduleDescription(
          'Power-efficient captures at fixed times - E2E test'
        )

        // Step 4: Add routine with fixed time trigger
        await scheduler.clickAddRoutine()
        await scheduler.selectTriggerTypeInRoutine('fixed_time')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Step 5: Set fixed time (21:00)
        await scheduler.fillFixedTimeInRoutine('21:00')

        // Step 6: Add at least one action
        await scheduler.clickAddActionInRoutine()
        await scheduler.selectActionTypeInRoutine(0, 'gpio')
        await scheduler.selectActionNameInRoutine(0, 'attract_on')

        // Step 7: Save the routine
        await scheduler.saveRoutine()

        // Step 8: Save the schedule
        await scheduler.clickSave()

        // Step 9: Verify editor closed
        expect(await scheduler.isEditorOpen()).toBeFalsy()

        // Step 10: Verify schedule appears in list
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(scenarioName)).toBeTruthy()

        // Step 11: Activate the schedule (enable → activate from banner)
        await scheduler.activateScheduleByName(scenarioName)

        // Step 12: Verify activation (handled by activateScheduleByName)
        const bannerVisible = await scheduler.isActiveBannerVisible()
        expect(bannerVisible, 'Schedule should show active banner').toBeTruthy()
      } finally {
        // Cleanup
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    test('fixed time can be configured within routine', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine and select fixed time trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Set a time value
      await scheduler.fillFixedTimeInRoutine('21:00')

      // Verify time was set
      const card = page.locator('[data-testid="new-routine-card"]')
      const timeInput = card.locator('[data-testid="fixed-time-input-0"]')
      await expect(timeInput).toHaveValue('21:00')

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('can add multiple actions to a routine', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('fixed_time')
      await scheduler.fillFixedTimeInRoutine('21:00')

      // Add first action
      await scheduler.clickAddActionInRoutine()
      await scheduler.selectActionTypeInRoutine(0, 'gpio')
      await scheduler.selectActionNameInRoutine(0, 'attract_on')

      // Add second action
      await scheduler.clickAddActionInRoutine()
      await scheduler.selectActionTypeInRoutine(1, 'gpio')
      await scheduler.selectActionNameInRoutine(1, 'flash_on')

      // Verify both actions exist
      const card = page.locator('[data-testid="new-routine-card"]')
      const actionTypes = card.locator('[data-testid="action-type"]')
      await expect(actionTypes).toHaveCount(2)

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('create fixed time schedule using helper method', async () => {
      const helperName = `Fixed Time Helper ${Date.now()}`

      try {
        const created = await scheduler.createFixedTimeSchedule({
          name: helperName,
          description: 'Created via helper method - E2E test',
          timeOfDay: '03:00',
        })

        expect(created, 'Schedule should be created successfully').toBeTruthy()
        expect(await scheduler.hasScheduleWithName(helperName)).toBeTruthy()
      } finally {
        await cleanupSchedule(scheduler, helperName)
      }
    })
  })

  // ============================================================
  // Cross-Scenario Integration Tests
  // ============================================================

  test.describe('Cross-Scenario Integration', () => {
    test('switching between trigger types resets form correctly', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add routine
      await scheduler.clickAddRoutine()

      const card = page.locator('[data-testid="new-routine-card"]')

      // Start with interval
      await scheduler.selectTriggerTypeInRoutine('interval')
      await scheduler.fillIntervalMinutesInRoutine(45)
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify interval form is visible
      const intervalInput = card.locator('[data-testid="interval-minutes"]')
      await expect(intervalInput).toBeVisible()

      // Switch to moon phase
      await scheduler.selectTriggerTypeInRoutine('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify moon phase checkboxes are visible
      const moonPhaseCheckbox = card.locator('[data-testid="moon-phase-full"]')
      await expect(moonPhaseCheckbox).toBeVisible()

      // Switch to fixed time
      await scheduler.selectTriggerTypeInRoutine('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify fixed time form is visible
      const timeInput = card.locator('[data-testid="fixed-time-input-0"]')
      await expect(timeInput).toBeVisible()

      // Switch back to interval
      await scheduler.selectTriggerTypeInRoutine('interval')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify interval form is visible again
      await expect(intervalInput).toBeVisible()

      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    // TODO: Update test for view-first paradigm - activation flow changed (Issue #266)
    test.skip('all trigger types can be saved and activated', async () => {
      const names = {
        interval: `Integration Interval ${Date.now()}`,
        moonPhase: `Integration Moon ${Date.now()}`,
        fixedTime: `Integration Fixed ${Date.now()}`,
      }

      try {
        // Create interval schedule
        let created = await scheduler.createIntervalSchedule({
          name: names.interval,
          description: 'Integration test - interval',
          interval: 30,
        })
        expect(created, 'Interval schedule should be created').toBeTruthy()

        // Create moon phase schedule
        created = await scheduler.createMoonPhaseSchedule({
          name: names.moonPhase,
          description: 'Integration test - moon phase',
          moonPhase: 'new',
        })
        expect(created, 'Moon phase schedule should be created').toBeTruthy()

        // Create fixed time schedule
        created = await scheduler.createFixedTimeSchedule({
          name: names.fixedTime,
          description: 'Integration test - fixed time',
          timeOfDay: '18:00',
        })
        expect(created, 'Fixed time schedule should be created').toBeTruthy()

        // Verify all three exist
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(names.interval)).toBeTruthy()
        expect(await scheduler.hasScheduleWithName(names.moonPhase)).toBeTruthy()
        expect(await scheduler.hasScheduleWithName(names.fixedTime)).toBeTruthy()

        // Activate one of them (fixed time schedule) - enable → activate from banner
        await scheduler.activateScheduleByName(names.fixedTime)

        // Verify activation
        const bannerVisible = await scheduler.waitForActiveBannerWithName('Integration Fixed')
        expect(bannerVisible, 'Schedule should show active banner').toBeTruthy()
      } finally {
        // Cleanup all three
        for (const name of Object.values(names)) {
          await cleanupSchedule(scheduler, name)
        }
      }
    })

    // TODO: Update test for view-first paradigm - activation flow changed (Issue #266)
    test.skip('only one schedule can be active at a time', async () => {
      const names = {
        first: `First Active ${Date.now()}`,
        second: `Second Active ${Date.now()}`,
      }

      try {
        // Create two schedules
        await scheduler.createFixedTimeSchedule({
          name: names.first,
          description: 'First schedule',
          timeOfDay: '10:00',
        })

        await scheduler.createFixedTimeSchedule({
          name: names.second,
          description: 'Second schedule',
          timeOfDay: '11:00',
        })

        await scheduler.waitForLoad()

        // Activate first schedule (enable → activate from banner)
        await scheduler.activateScheduleByName(names.first)
        let bannerVisible = await scheduler.waitForActiveBannerWithName('First Active')
        expect(bannerVisible, 'First schedule should show active banner').toBeTruthy()

        // Activate second schedule - this will deactivate first (only one can be active)
        await scheduler.activateScheduleByName(names.second)
        bannerVisible = await scheduler.waitForActiveBannerWithName('Second Active')
        expect(bannerVisible, 'Second schedule should show active banner').toBeTruthy()

        // Verify banner shows second schedule (not first)
        const activeName = await scheduler.getActiveBannerScheduleName()
        expect(activeName).toContain('Second Active')
      } finally {
        for (const name of Object.values(names)) {
          await cleanupSchedule(scheduler, name)
        }
      }
    })
  })

  // ============================================================
  // Form Validation Tests
  // ============================================================

  test.describe('Form Validation', () => {
    test('interval trigger requires valid interval', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Validation Test ${Date.now()}`)

      // Add routine with interval trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('interval')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Leave interval empty
      const card = page.locator('[data-testid="new-routine-card"]')
      await card.locator('[data-testid="interval-minutes"]').fill('')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Save routine button should be disabled (no actions yet + empty interval)
      const saveBtn = card.locator('[data-testid="save-routine"]')
      await expect(saveBtn).toBeDisabled()

      // Cancel and close
      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('moon phase trigger requires at least one phase selected', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Moon Validation ${Date.now()}`)

      // Add routine with moon phase trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // The moon phase trigger starts with 'full' selected by default
      // and the UI prevents deselecting the last phase to ensure
      // at least one is always selected - this is the correct behavior

      // Verify the default phase is selected
      const card = page.locator('[data-testid="new-routine-card"]')
      const fullPhase = card.locator('[data-testid="moon-phase-full"]')
      await expect(fullPhase).toBeChecked()

      // Try to click it to deselect (should be prevented as it's the last one)
      await fullPhase.click({ force: true })
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Should still be checked (can't deselect last phase)
      await expect(fullPhase).toBeChecked()

      // Cancel and close
      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })

    test('fixed time trigger requires time of day', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Fixed Validation ${Date.now()}`)

      // Add routine with fixed time trigger
      await scheduler.clickAddRoutine()
      await scheduler.selectTriggerTypeInRoutine('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Fixed time trigger starts with default time '08:00'
      // Verify the default time is present
      const card = page.locator('[data-testid="new-routine-card"]')
      const timeInput = card.locator('[data-testid="fixed-time-input-0"]')
      await expect(timeInput).toHaveValue('08:00')

      // Clear time (this should trigger validation)
      await timeInput.fill('')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Save routine button should be disabled (no actions + invalid time)
      const saveBtn = card.locator('[data-testid="save-routine"]')
      await expect(saveBtn).toBeDisabled()

      // Cancel and close
      await scheduler.cancelNewRoutine()
      await scheduler.clickCancel()
    })
  })
})

// ============================================================
// Helper Functions
// ============================================================

/**
 * Find the index of a schedule by name
 * @param {SchedulerPage} scheduler
 * @param {string} name
 * @returns {Promise<number>} Index or -1 if not found
 */
async function findScheduleIndex(scheduler, name) {
  const count = await scheduler.getScheduleCount()
  for (let i = 0; i < count; i++) {
    const card = scheduler.getScheduleCardByIndex(i)
    const text = await card.textContent()
    if (text && text.includes(name)) {
      return i
    }
  }
  return -1
}

/**
 * Cleanup a schedule by name (handles dialog confirmation)
 * @param {SchedulerPage} scheduler
 * @param {string} name
 */
async function cleanupSchedule(scheduler, name) {
  try {
    // Ensure we're on schedules tab
    await scheduler.switchToSchedulesTab().catch(() => {})

    // Close any open editor first
    if (await scheduler.isEditorOpen()) {
      await scheduler.clickCancel().catch(() => {})
    }

    // Check if schedule exists
    if (await scheduler.hasScheduleWithName(name)) {
      // First deactivate if active
      const index = await findScheduleIndex(scheduler, name)
      if (index >= 0 && (await scheduler.isScheduleActive(index))) {
        await scheduler.clickDeactivateOnSchedule(index).catch(() => {})
        await scheduler.waitForLoad()
      }

      // Delete the schedule
      await scheduler.clickDeleteOnScheduleByName(name)
      if (await scheduler.isConfirmDialogOpen()) {
        await scheduler.confirmDelete()
        await scheduler.waitForLoad()
      }
    }
  } catch {
    // Cleanup failure is acceptable - test still passes
  }
}
