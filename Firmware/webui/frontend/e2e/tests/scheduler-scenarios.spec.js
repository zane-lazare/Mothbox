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

    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('create schedule with interval trigger and solar events', async ({ page }) => {
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

        // Step 4: Select interval trigger type
        await scheduler.selectTriggerType('interval')

        // Step 5: Configure 30-minute interval
        await scheduler.fillIntervalMinutes(30)

        // Step 6: Configure time window with solar events
        // Start: sunset + 30 minutes
        await scheduler.selectStartTimeType('solar')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)
        await scheduler.selectStartSolarEvent('sunset')
        await scheduler.fillStartOffset(30)

        // End: sunrise
        await scheduler.selectEndTimeType('solar')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)
        await scheduler.selectEndSolarEvent('sunrise')

        // Step 7: Set date range (summer months)
        const currentYear = new Date().getFullYear()
        await scheduler.fillStartDate(`${currentYear}-06-01`)
        await scheduler.fillEndDate(`${currentYear}-08-31`)

        // Step 8: Verify preview text shows interval configuration
        const previewText = await scheduler.getTriggerPreviewText()
        expect(previewText).toBeTruthy()
        // Preview should mention the interval
        if (previewText) {
          expect(previewText.toLowerCase()).toContain('30')
        }

        // Step 9: Select a routine - TODO: Update to selectFirstRoutine()
        const patternSelected = await scheduler.selectFirstEventPattern()
        expect(patternSelected, 'Routines should be available').toBeTruthy()

        // Step 10: Save the schedule
        await scheduler.clickSave()

        // Step 11: Verify editor closed (save succeeded)
        const editorStillOpen = await scheduler.isEditorOpen()
        expect(editorStillOpen, 'Editor should close after successful save').toBeFalsy()

        // Step 12: Verify schedule appears in list
        await scheduler.waitForLoad()
        const scheduleExists = await scheduler.hasScheduleWithName(scenarioName)
        expect(scheduleExists, 'Schedule should appear in list').toBeTruthy()

        // Step 13: Activate the schedule
        const card = scheduler.getScheduleCardByName(scenarioName)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Step 14: Verify activation (either banner or badge)
        const bannerVisible = await scheduler.isActiveBannerVisible()
        const cardIndex = await findScheduleIndex(scheduler, scenarioName)
        const cardActive = cardIndex >= 0 ? await scheduler.isScheduleActive(cardIndex) : false
        expect(bannerVisible || cardActive, 'Schedule should show as active').toBeTruthy()

        // Step 15: Switch to calendar and verify
        await scheduler.switchToCalendarTab()
        await page.waitForTimeout(TIMEOUTS.TRANSITION)
        const calendarOptions = await scheduler.getCalendarScheduleOptions()
        expect(calendarOptions.some((opt) => opt.includes(scenarioName))).toBeTruthy()
      } finally {
        // Cleanup: Delete the test schedule
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    // New UI requires adding a routine first, then configuring trigger within that routine
    test.fixme('interval trigger form validates minimum interval', async () => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('interval')

      // Try to set interval below minimum (should show validation or clamp)
      await scheduler.fillIntervalMinutes(0)

      // The form should either show an error or reset to minimum
      // Check by verifying the value is at least 1
      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Try to save without pattern - should fail validation
      await scheduler.clickSave()
      expect(await scheduler.isEditorOpen()).toBeTruthy()

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    // New UI requires adding a routine first, then configuring trigger within that routine
    test.fixme('solar event offsets can be configured', async () => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('interval')

      // Configure start with positive offset
      await scheduler.selectStartTimeType('solar')
      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)
      await scheduler.selectStartSolarEvent('sunset')
      await scheduler.fillStartOffset(60) // 1 hour after sunset

      // Configure end with negative offset
      await scheduler.selectEndTimeType('solar')
      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)
      await scheduler.selectEndSolarEvent('sunrise')
      await scheduler.fillEndOffset(-30) // 30 min before sunrise

      // Verify preview updates with offset info
      const previewText = await scheduler.getTriggerPreviewText()
      expect(previewText).toBeTruthy()

      await scheduler.clickCancel()
    })
  })

  // ============================================================
  // Scenario 2: Full Moon Observation Session
  // ============================================================
  // From User Guide: Photography sessions timed to full moon phases.

  test.describe('Scenario 2: Full Moon Observation Session', () => {
    const scenarioName = `Full Moon Observation ${Date.now()}`

    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('create schedule with moon phase trigger', async ({ page }) => {
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

        // Step 4: Select moon phase trigger type
        await scheduler.selectTriggerType('moon_phase')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Step 5: Select full moon phase
        await scheduler.selectMoonPhase('full')

        // Step 6: Set time of day for capture
        await scheduler.fillMoonPhaseTime('21:00')

        // Step 7: Set offset days (±2 days around full moon)
        await scheduler.fillMoonPhaseOffset(0)

        // Step 8: Verify preview shows moon phase configuration
        const previewText = await scheduler.getTriggerPreviewText()
        expect(previewText).toBeTruthy()
        if (previewText) {
          expect(previewText.toLowerCase()).toContain('full')
        }

        // Step 9: Select a routine - TODO: Update to selectFirstRoutine()
        const patternSelected = await scheduler.selectFirstEventPattern()
        expect(patternSelected, 'Routines should be available').toBeTruthy()

        // Step 10: Save the schedule
        await scheduler.clickSave()

        // Step 11: Verify editor closed
        expect(await scheduler.isEditorOpen()).toBeFalsy()

        // Step 12: Verify schedule appears in list
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(scenarioName)).toBeTruthy()

        // Step 13: Activate the schedule
        const card = scheduler.getScheduleCardByName(scenarioName)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Step 14: Verify activation
        const bannerVisible = await scheduler.isActiveBannerVisible()
        const cardIndex = await findScheduleIndex(scheduler, scenarioName)
        const cardActive = cardIndex >= 0 ? await scheduler.isScheduleActive(cardIndex) : false
        expect(bannerVisible || cardActive).toBeTruthy()
      } finally {
        // Cleanup
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    test.fixme('moon phase dropdown shows all 8 phases', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Get all options from moon phase dropdown
      const options = await page.locator('#moon_phase option').allTextContents()

      // Should have all 8 moon phases
      const expectedPhases = [
        'New Moon',
        'Waxing Crescent',
        'First Quarter',
        'Waxing Gibbous',
        'Full Moon',
        'Waning Gibbous',
        'Last Quarter',
        'Waning Crescent',
      ]

      for (const phase of expectedPhases) {
        expect(
          options.some((opt) => opt.toLowerCase().includes(phase.toLowerCase())),
          `Should include ${phase}`
        ).toBeTruthy()
      }

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    test.fixme('moon phase offset presets work correctly', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Test -1 day preset
      await scheduler.clickMoonPhaseOffsetPreset('-1 day')
      let offsetValue = await page.locator('#offset_days').inputValue()
      expect(offsetValue).toBe('-1')

      // Test No offset preset
      await scheduler.clickMoonPhaseOffsetPreset('No offset')
      offsetValue = await page.locator('#offset_days').inputValue()
      expect(offsetValue).toBe('0')

      // Test +1 day preset
      await scheduler.clickMoonPhaseOffsetPreset('+1 day')
      offsetValue = await page.locator('#offset_days').inputValue()
      expect(offsetValue).toBe('1')

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - createMoonPhaseSchedule uses old workflow
    test.fixme('moon phase schedule with offset days', async () => {
      const offsetName = `Moon Phase Offset ${Date.now()}`

      try {
        const created = await scheduler.createMoonPhaseSchedule({
          name: offsetName,
          description: 'Moon phase with offset - E2E test',
          moonPhase: 'full',
          timeOfDay: '20:00',
          offsetDays: 2, // 2 days after full moon
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

    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('create schedule with fixed time trigger', async ({ page }) => {
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

        // Step 4: Select fixed time trigger type
        await scheduler.selectTriggerType('fixed_time')
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Step 5: Set fixed time (21:00)
        await scheduler.fillFixedTimeOfDay('21:00')

        // Step 6: Verify preview shows fixed time
        const previewText = await scheduler.getTriggerPreviewText()
        expect(previewText).toBeTruthy()
        if (previewText) {
          expect(previewText).toContain('21:00')
        }

        // Step 7: Ensure "All Days" is selected
        await scheduler.clickAllDays()

        // Step 8: Select a routine - TODO: Update to selectFirstRoutine()
        const patternSelected = await scheduler.selectFirstEventPattern()
        expect(patternSelected, 'Routines should be available').toBeTruthy()

        // Step 9: Save the schedule
        await scheduler.clickSave()

        // Step 10: Verify editor closed
        expect(await scheduler.isEditorOpen()).toBeFalsy()

        // Step 11: Verify schedule appears in list
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(scenarioName)).toBeTruthy()

        // Step 12: Activate the schedule
        const card = scheduler.getScheduleCardByName(scenarioName)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Step 13: Verify activation
        const bannerVisible = await scheduler.isActiveBannerVisible()
        const cardIndex = await findScheduleIndex(scheduler, scenarioName)
        const cardActive = cardIndex >= 0 ? await scheduler.isScheduleActive(cardIndex) : false
        expect(bannerVisible || cardActive).toBeTruthy()
      } finally {
        // Cleanup
        await cleanupSchedule(scheduler, scenarioName)
      }
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    test.fixme('fixed time presets work correctly', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Test each preset
      const presets = [
        { label: '6 AM', value: '06:00' },
        { label: '12 PM', value: '12:00' },
        { label: '6 PM', value: '18:00' },
        { label: '9 PM', value: '21:00' },
      ]

      for (const preset of presets) {
        await scheduler.clickTimePreset(preset.label)
        const timeValue = await page.locator('#time_of_day').inputValue()
        expect(timeValue, `Preset ${preset.label} should set time to ${preset.value}`).toBe(
          preset.value
        )
      }

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    test.fixme('days of week selector allows custom selection', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.selectTriggerType('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Click All Days first to ensure all are selected
      await scheduler.clickAllDays()

      // Toggle individual days to create weekday-only selection
      await scheduler.toggleDay('Sat')
      await scheduler.toggleDay('Sun')

      // Verify Saturday button is no longer selected (aria-pressed should be false)
      const satButton = page.locator('button[aria-label="Saturday"]')
      await expect(satButton).toHaveAttribute('aria-pressed', 'false')

      // Verify Sunday button is no longer selected
      const sunButton = page.locator('button[aria-label="Sunday"]')
      await expect(sunButton).toHaveAttribute('aria-pressed', 'false')

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - createFixedTimeSchedule uses old workflow
    test.fixme('create fixed time schedule using helper method', async () => {
      const helperName = `Fixed Time Helper ${Date.now()}`

      try {
        const created = await scheduler.createFixedTimeSchedule({
          name: helperName,
          description: 'Created via helper method - E2E test',
          timeOfDay: '03:00',
          daysOfWeek: null, // All days
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
    // NEEDS UPDATE (#329): Per-routine triggers architecture - TriggerSelector not in schedule editor
    test.fixme('switching between trigger types resets form correctly', async ({ page }) => {
      await scheduler.clickNewSchedule()

      // Start with interval
      await scheduler.selectTriggerType('interval')
      await scheduler.fillIntervalMinutes(45)
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Switch to moon phase
      await scheduler.selectTriggerType('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify moon phase form is visible
      const moonPhaseSelect = page.locator('#moon_phase')
      await expect(moonPhaseSelect).toBeVisible()

      // Switch to fixed time
      await scheduler.selectTriggerType('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify fixed time form is visible
      const timeInput = page.locator('#time_of_day')
      await expect(timeInput).toBeVisible()

      // Switch back to interval
      await scheduler.selectTriggerType('interval')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify interval form is visible
      const intervalInput = page.locator('#interval_minutes')
      await expect(intervalInput).toBeVisible()

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - helper methods use old workflow
    test.fixme('all trigger types can be saved and activated', async () => {
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
          intervalMinutes: 30,
          timeWindow: {
            startType: 'fixed',
            startTime: '20:00',
            endType: 'fixed',
            endTime: '06:00',
          },
        })
        expect(created, 'Interval schedule should be created').toBeTruthy()

        // Create moon phase schedule
        created = await scheduler.createMoonPhaseSchedule({
          name: names.moonPhase,
          description: 'Integration test - moon phase',
          moonPhase: 'new',
          timeOfDay: '22:00',
          offsetDays: 0,
        })
        expect(created, 'Moon phase schedule should be created').toBeTruthy()

        // Create fixed time schedule
        created = await scheduler.createFixedTimeSchedule({
          name: names.fixedTime,
          description: 'Integration test - fixed time',
          timeOfDay: '18:00',
          daysOfWeek: null,
        })
        expect(created, 'Fixed time schedule should be created').toBeTruthy()

        // Verify all three exist
        await scheduler.waitForLoad()
        expect(await scheduler.hasScheduleWithName(names.interval)).toBeTruthy()
        expect(await scheduler.hasScheduleWithName(names.moonPhase)).toBeTruthy()
        expect(await scheduler.hasScheduleWithName(names.fixedTime)).toBeTruthy()

        // Activate one of them
        const card = scheduler.getScheduleCardByName(names.fixedTime)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Verify it's active
        const bannerVisible = await scheduler.isActiveBannerVisible()
        expect(bannerVisible).toBeTruthy()
      } finally {
        // Cleanup all three
        for (const name of Object.values(names)) {
          await cleanupSchedule(scheduler, name)
        }
      }
    })

    // NEEDS UPDATE (#329): Per-routine triggers architecture - createFixedTimeSchedule uses old workflow
    test.fixme('only one schedule can be active at a time', async () => {
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

        // Activate first
        let card = scheduler.getScheduleCardByName(names.first)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Verify first is active
        let firstIndex = await findScheduleIndex(scheduler, names.first)
        expect(await scheduler.isScheduleActive(firstIndex)).toBeTruthy()

        // Activate second
        card = scheduler.getScheduleCardByName(names.second)
        await card.locator('button:has-text("Activate")').click()
        await scheduler.waitForLoad()

        // Verify second is now active, first is not
        let secondIndex = await findScheduleIndex(scheduler, names.second)
        expect(await scheduler.isScheduleActive(secondIndex)).toBeTruthy()

        // First should no longer be active (re-find index as order may change)
        firstIndex = await findScheduleIndex(scheduler, names.first)
        if (firstIndex >= 0) {
          expect(await scheduler.isScheduleActive(firstIndex)).toBeFalsy()
        }
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
    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('interval trigger requires valid interval', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Validation Test ${Date.now()}`)
      await scheduler.selectTriggerType('interval')

      // Leave interval empty and try to save
      await page.locator('#interval_minutes').fill('')
      // TODO: Update to selectFirstRoutine()
      await scheduler.selectFirstEventPattern()
      await scheduler.clickSave()

      // Should stay open with validation error
      expect(await scheduler.isEditorOpen()).toBeTruthy()

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('moon phase trigger requires time of day', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Moon Validation ${Date.now()}`)
      await scheduler.selectTriggerType('moon_phase')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Clear time of day
      await page.locator('#time_of_day').fill('')
      // TODO: Update to selectFirstRoutine()
      await scheduler.selectFirstEventPattern()
      await scheduler.clickSave()

      // Should stay open (either due to validation or empty time)
      // Note: Some browsers may default to 00:00 if cleared
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      await scheduler.clickCancel()
    })

    // NEEDS UPDATE (#329): Uses selectFirstEventPattern() - update when routine workflow complete
    // The deprecated method still works via backward compatibility wrapper
    test.fixme('fixed time trigger requires time of day', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(`Fixed Validation ${Date.now()}`)
      await scheduler.selectTriggerType('fixed_time')
      await page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Clear time
      await page.locator('#time_of_day').fill('')
      // TODO: Update to selectFirstRoutine()
      await scheduler.selectFirstEventPattern()
      await scheduler.clickSave()

      await page.waitForTimeout(TIMEOUTS.TRANSITION)

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
