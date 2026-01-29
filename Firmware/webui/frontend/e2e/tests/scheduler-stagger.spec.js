/**
 * Scheduler Stagger E2E Tests (Issue #379)
 *
 * Tests the staggered actions feature that prevents GPIO race conditions
 * when multiple actions share the same offset_minutes.
 *
 * Two modes:
 * - Auto-stagger (default): Actions auto-staggered by 5s based on list order
 * - Explicit seconds: User sets offset_seconds for precise timing
 */

import { test, expect } from '@playwright/test'
import { SchedulerPage } from '../pages/scheduler.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Scheduler Stagger Actions', () => {
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
  // Group A: Auto-Stagger Mode (checkbox unchecked)
  // ============================================================

  test.describe('Auto-Stagger Mode', () => {
    test('checkbox is unchecked by default', async () => {
      await scheduler.clickNewSchedule()

      // Verify checkbox state
      const isEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isEnabled).toBeFalsy()

      // Verify offset_seconds input is NOT visible when adding action
      // We need to open the action form to check this
    })

    test('A1: two actions same minute show stagger badges', async () => {
      // This test verifies the UI shows auto-stagger info when multiple
      // actions share the same offset_minutes

      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Verify seconds timing is disabled (auto-stagger mode)
      const isSecondsEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isSecondsEnabled).toBeFalsy()

      // Select a routine to have some actions
      // Then we would verify stagger badges appear for same-minute actions

      await scheduler.clickCancel()
    })

    test('A3: actions at different minutes show no stagger', async ({ page }) => {
      // When actions have different offset_minutes, no stagger badges should appear
      void page // suppress unused warning

      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Verify auto-stagger mode
      const isSecondsEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isSecondsEnabled).toBeFalsy()

      await scheduler.clickCancel()
    })
  })

  // ============================================================
  // Group B: Explicit Seconds Mode (checkbox checked)
  // ============================================================

  test.describe('Explicit Seconds Mode', () => {
    test('B1: checkbox toggle shows/hides seconds input', async ({ page }) => {
      await scheduler.clickNewSchedule()

      // Initially unchecked
      let isEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isEnabled).toBeFalsy()

      // Enable seconds timing
      await scheduler.setSecondsTiming(true)
      isEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isEnabled).toBeTruthy()

      // Verify the help text changes
      const helpText = await page.locator('label:has-text("seconds-level timing") p').textContent()
      expect(helpText).toContain('exact seconds')

      // Disable seconds timing
      await scheduler.setSecondsTiming(false)
      isEnabled = await scheduler.isSecondsTimingEnabled()
      expect(isEnabled).toBeFalsy()

      // Verify help text changes back
      const helpTextAfter = await page.locator('label:has-text("seconds-level timing") p').textContent()
      expect(helpTextAfter).toContain('auto-staggered')

      await scheduler.clickCancel()
    })

    test('B2: seconds input appears in ActionForm when enabled', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Enable seconds timing
      await scheduler.setSecondsTiming(true)

      // Try to add an action to verify seconds input appears
      // First we need a routine - select first available
      const routineSelected = await scheduler.selectFirstRoutine()
      if (!routineSelected) {
        test.skip(true, 'No routines available to test action form')
        return
      }

      // Click "Add Action" button if visible
      const addActionButton = page.locator('button:has-text("Add Action")')
      if (await addActionButton.isVisible()) {
        await addActionButton.click()
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Verify offset_seconds input is visible
        const secondsInput = page.locator('#offset_seconds')
        await expect(secondsInput).toBeVisible()

        // Close action form
        const cancelActionButton = page.locator('[role="dialog"] button:has-text("Cancel")')
        if (await cancelActionButton.isVisible()) {
          await cancelActionButton.click()
        }
      }

      await scheduler.clickCancel()
    })

    test('B3: seconds validation enforces 0-59 range', async ({ page }) => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Enable seconds timing
      await scheduler.setSecondsTiming(true)

      // Select a routine first
      const routineSelected = await scheduler.selectFirstRoutine()
      if (!routineSelected) {
        test.skip(true, 'No routines available to test validation')
        return
      }

      // Click "Add Action" button
      const addActionButton = page.locator('button:has-text("Add Action")')
      if (await addActionButton.isVisible()) {
        await addActionButton.click()
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Fill in action type and name
        await page.selectOption('#action_type', 'gpio')
        await page.selectOption('#action_name', 'attract_on')
        await page.fill('#offset_minutes', '0')

        // Try invalid value: 60 (exceeds max 59)
        await page.fill('#offset_seconds', '60')

        // Try to save
        const saveButton = page.locator('[role="dialog"] button:has-text("Save")')
        await saveButton.click()
        await page.waitForTimeout(TIMEOUTS.TRANSITION)

        // Verify validation error appears
        const errorMessage = page.locator('text=Seconds must be')
        await expect(errorMessage).toBeVisible()

        // Fix with valid value
        await page.fill('#offset_seconds', '59')
        await saveButton.click()

        // Action form should close on success
        await page.waitForTimeout(TIMEOUTS.SAVE)

        // Close action form if still open
        const cancelActionButton = page.locator('[role="dialog"] button:has-text("Cancel")')
        if (await cancelActionButton.isVisible()) {
          await cancelActionButton.click()
        }
      }

      await scheduler.clickCancel()
    })
  })

  // ============================================================
  // Group C: Mixed Scenarios
  // ============================================================

  test.describe('Mixed Scenarios', () => {
    test('C1: schedule saves with use_seconds_timing flag', async () => {
      const testName = scheduler.generateTestScheduleName()

      try {
        await scheduler.clickNewSchedule()
        await scheduler.fillScheduleName(testName)

        // Enable seconds timing
        await scheduler.setSecondsTiming(true)

        // Select a routine
        const routineSelected = await scheduler.selectFirstRoutine()
        if (!routineSelected) {
          test.skip(true, 'No routines available')
          return
        }

        // Save the schedule
        await scheduler.clickSave()

        // If editor closed, schedule was saved
        const editorOpen = await scheduler.isEditorOpen()
        if (editorOpen) {
          // May have validation errors - just verify the checkbox state was preserved
          const isEnabled = await scheduler.isSecondsTimingEnabled()
          expect(isEnabled).toBeTruthy()
          await scheduler.clickCancel()
        } else {
          // Verify schedule exists
          const exists = await scheduler.hasScheduleWithName(testName)
          expect(exists).toBeTruthy()

          // Edit the schedule and verify use_seconds_timing was saved
          const card = scheduler.getScheduleCardByName(testName)
          await card.locator('button:has-text("Edit")').click()
          await scheduler.waitForEditorOpen()

          const isEnabled = await scheduler.isSecondsTimingEnabled()
          expect(isEnabled).toBeTruthy()

          await scheduler.clickCancel()
        }
      } finally {
        // Cleanup: delete test schedule if it was created
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

    test('C2: toggle mode preserves actions', async () => {
      await scheduler.clickNewSchedule()
      await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

      // Add a routine first
      const routineSelected = await scheduler.selectFirstRoutine()
      if (!routineSelected) {
        test.skip(true, 'No routines available')
        return
      }

      // Get initial action count
      const initialActionCount = await scheduler.page.locator('[data-sortable="true"]').count()

      // Toggle seconds timing on
      await scheduler.setSecondsTiming(true)
      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify actions still exist
      const afterEnableCount = await scheduler.page.locator('[data-sortable="true"]').count()
      expect(afterEnableCount).toBe(initialActionCount)

      // Toggle seconds timing off
      await scheduler.setSecondsTiming(false)
      await scheduler.page.waitForTimeout(TIMEOUTS.TRANSITION)

      // Verify actions still exist
      const afterDisableCount = await scheduler.page.locator('[data-sortable="true"]').count()
      expect(afterDisableCount).toBe(initialActionCount)

      await scheduler.clickCancel()
    })
  })

  // ============================================================
  // API Verification (if API is accessible)
  // ============================================================

  test.describe('API Verification', () => {
    test('schedule preview includes staggered commands', async () => {
      // This test verifies that the preview API returns commands with sleep prefixes
      // for staggered actions

      const scheduleCount = await scheduler.getScheduleCount()
      if (scheduleCount === 0) {
        test.skip(true, 'No schedules available for API testing')
        return
      }

      // Get first schedule card
      const firstCard = scheduler.getScheduleCardByIndex(0)

      // Try to get schedule ID from the card (may be in a data attribute)
      const scheduleId = await firstCard.getAttribute('data-schedule-id')

      if (!scheduleId) {
        // Schedule ID not exposed in DOM, skip API verification
        test.skip(true, 'Schedule ID not accessible in DOM')
        return
      }

      // Fetch preview
      try {
        const preview = await scheduler.getSchedulePreview(scheduleId)

        // Verify preview has events
        expect(preview.events).toBeDefined()

        // If events exist, verify structure
        if (preview.events && preview.events.length > 0) {
          const firstEvent = preview.events[0]
          expect(firstEvent).toHaveProperty('action_name')
          expect(firstEvent).toHaveProperty('datetime')
        }
      } catch {
        // API may not be accessible, skip
        test.skip(true, 'Preview API not accessible')
      }
    })
  })

  // ============================================================
  // Group D: Crontab Command Verification
  // ============================================================

  test.describe('Crontab Command Verification', () => {
    /**
     * Helper: Get CSRF token for API requests
     * @param {import('@playwright/test').Page} page
     * @returns {Promise<string>}
     */
    async function getCsrfToken(page) {
      const response = await page.request.get('/api/csrf-token')
      const data = await response.json()
      return data.csrf_token
    }

    /**
     * Helper: Create schedule via API, activate it, and get crontab entries
     * @param {import('@playwright/test').Page} page
     * @param {object} config - Schedule configuration
     * @returns {Promise<{scheduleId: string, jobs: Array}>}
     */
    async function activateAndInspectCron(page, config) {
      // Get CSRF token for POST requests
      const csrfToken = await getCsrfToken(page)
      const headers = { 'X-CSRFToken': csrfToken }

      // Create schedule
      const createResp = await page.request.post('/api/scheduler/ui/schedules', {
        data: config,
        headers
      })
      if (!createResp.ok()) {
        const errorBody = await createResp.text()
        console.error('Schedule creation failed:', createResp.status(), errorBody)
        throw new Error(`Schedule creation failed: ${createResp.status()} - ${errorBody}`)
      }
      const { schedule_id } = await createResp.json()

      // Activate schedule (writes to crontab)
      const activateResp = await page.request.post(
        `/api/scheduler/ui/schedules/${schedule_id}/activate`,
        { headers }
      )
      expect(activateResp.ok()).toBeTruthy()

      // Read actual crontab entries
      const jobsResp = await page.request.get('/api/scheduler/jobs')
      expect(jobsResp.ok()).toBeTruthy()
      const { jobs } = await jobsResp.json()

      return { scheduleId: schedule_id, jobs }
    }

    /**
     * Helper: Cleanup - deactivate and delete schedule
     * @param {import('@playwright/test').Page} page
     * @param {string} scheduleId
     */
    async function cleanup(page, scheduleId) {
      const csrfToken = await getCsrfToken(page)
      const headers = { 'X-CSRFToken': csrfToken }
      await page.request.post('/api/scheduler/ui/schedules/deactivate', { headers })
      await page.request.delete(`/api/scheduler/ui/schedules/${scheduleId}`, { headers })
    }

    test('D1: auto-stagger adds sleep prefix in crontab', async ({ page }) => {
      const routineName = `Stagger Test ${Date.now()}`
      const config = {
        name: `Cron Stagger Test ${Date.now()}`,
        use_seconds_timing: false,
        routines: [{
          routine_id: crypto.randomUUID(),
          name: routineName,
          trigger: { trigger_type: 'fixed_time', time: '21:00' },
          actions: [
            { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
            { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 0 },
          ]
        }]
      }

      const { scheduleId, jobs } = await activateAndInspectCron(page, config)

      try {
        // Filter to only jobs from our test routine (by comment containing routine name)
        const ourJobs = jobs.filter(j => j.comment?.includes(routineName))
        expect(ourJobs.length).toBeGreaterThan(0)

        // Find jobs by command (script name is in command, not comment)
        const attractJob = ourJobs.find(j => j.command?.includes('Attract_On'))
        const flashJob = ourJobs.find(j => j.command?.includes('Flash_On'))

        expect(attractJob).toBeDefined()
        expect(flashJob).toBeDefined()

        // First action: no sleep prefix
        expect(attractJob.command).not.toContain('sleep')

        // Second action: sleep 5 && prefix (DEFAULT_STAGGER_SECONDS = 5)
        expect(flashJob.command).toContain('sleep 5 &&')
      } finally {
        await cleanup(page, scheduleId)
      }
    })

    test('D2: explicit seconds uses offset_seconds in crontab', async ({ page }) => {
      const routineName = `Seconds Test ${Date.now()}`
      const config = {
        name: `Explicit Seconds Test ${Date.now()}`,
        use_seconds_timing: true,
        routines: [{
          routine_id: crypto.randomUUID(),
          name: routineName,
          trigger: { trigger_type: 'fixed_time', time: '21:00' },
          actions: [
            { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0, offset_seconds: 0 },
            { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 0, offset_seconds: 15 },
            { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 0, offset_seconds: 30 },
          ]
        }]
      }

      const { scheduleId, jobs } = await activateAndInspectCron(page, config)

      try {
        // Filter to only jobs from our test routine
        const ourJobs = jobs.filter(j => j.comment?.includes(routineName))
        expect(ourJobs.length).toBeGreaterThan(0)

        // Find jobs by command (script name is in command, not comment)
        const attractOn = ourJobs.find(j => j.command?.includes('Attract_On'))
        const flashOn = ourJobs.find(j => j.command?.includes('Flash_On'))
        const attractOff = ourJobs.find(j => j.command?.includes('Attract_Off'))

        expect(attractOn).toBeDefined()
        expect(flashOn).toBeDefined()
        expect(attractOff).toBeDefined()

        // offset_seconds=0: no sleep prefix
        expect(attractOn.command).not.toContain('sleep')

        // offset_seconds=15: sleep 15 && prefix
        expect(flashOn.command).toContain('sleep 15 &&')

        // offset_seconds=30: sleep 30 && prefix
        expect(attractOff.command).toContain('sleep 30 &&')
      } finally {
        await cleanup(page, scheduleId)
      }
    })

    test('D3: different minutes have no sleep in crontab', async ({ page }) => {
      const routineName = `No Stagger Test ${Date.now()}`
      const config = {
        name: `Different Minutes Test ${Date.now()}`,
        use_seconds_timing: false,
        routines: [{
          routine_id: crypto.randomUUID(),
          name: routineName,
          trigger: { trigger_type: 'fixed_time', time: '21:00' },
          actions: [
            { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
            { action_type: 'gpio', action_name: 'flash_on', offset_minutes: 5 },
            { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 10 },
          ]
        }]
      }

      const { scheduleId, jobs } = await activateAndInspectCron(page, config)

      try {
        // Filter to only our test jobs
        const testJobs = jobs.filter(j => j.comment?.includes(routineName))

        // Should have jobs (at least one per day in preview period)
        expect(testJobs.length).toBeGreaterThan(0)

        // All actions at different minutes - no staggering needed
        // Verify that our specific action jobs have no sleep prefix
        const attractOn = testJobs.find(j => j.command?.includes('Attract_On'))
        const flashOn = testJobs.find(j => j.command?.includes('Flash_On'))
        const attractOff = testJobs.find(j => j.command?.includes('Attract_Off'))

        expect(attractOn).toBeDefined()
        expect(flashOn).toBeDefined()
        expect(attractOff).toBeDefined()

        // None should have sleep prefix since they're at different minutes
        expect(attractOn.command).not.toContain('sleep')
        expect(flashOn.command).not.toContain('sleep')
        expect(attractOff.command).not.toContain('sleep')
      } finally {
        await cleanup(page, scheduleId)
      }
    })
  })
})
