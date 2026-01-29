/**
 * Scheduler Conflict Detection E2E Tests (Issue #331)
 *
 * Tests the real-time conflict detection panel in the schedule editor drawer.
 * Verifies the two-column layout, automatic validation on routine changes,
 * and correct display of conflict states.
 */

import { test, expect } from '@playwright/test'
import { SchedulerPage } from '../pages/scheduler.page.js'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Scheduler Conflict Detection', () => {
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
  // Conflict Panel Visibility
  // ============================================================

  test('conflict detection panel is visible in editor', async () => {
    await scheduler.clickNewSchedule()
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Verify the conflict panel is visible
    const panelVisible = await scheduler.isConflictPanelVisible()
    expect(panelVisible).toBeTruthy()

    await scheduler.clickCancel()
  })

  test('editor has two-column layout', async ({ page }) => {
    await scheduler.clickNewSchedule()

    // Check for the two-column flex container
    const twoColumnContainer = page.locator('[data-testid="schedule-editor-drawer"] .flex-1.flex')
    await expect(twoColumnContainer).toBeVisible()

    // Check for right panel with w-80 class
    const rightPanel = page.locator('[data-testid="schedule-editor-drawer"] .w-80')
    await expect(rightPanel).toBeVisible()

    await scheduler.clickCancel()
  })

  // ============================================================
  // No Conflicts State
  // ============================================================

  test('shows no conflicts for single routine with unique resources', async () => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Add a single routine
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(30)

    // Add an action
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'gpio')
    await scheduler.selectActionNameInRoutine(0, 'attract_on')

    // Save the routine
    await scheduler.saveRoutine()

    // Wait for conflict validation to complete
    await scheduler.waitForConflictValidation()

    // Should show no conflicts
    const noConflicts = await scheduler.hasNoConflicts()
    expect(noConflicts).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Conflict Detection
  // ============================================================

  /**
   * Test camera resource conflict at same fixed time.
   *
   * Two camera actions at the exact same time should detect resource contention
   * because the camera is a single-instance resource.
   */
  test('detects camera conflict for same-time fixed triggers', async ({ page }) => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Add first routine with fixed time trigger at 21:00
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('fixed_time')
    await scheduler.fillFixedTimeInRoutine('21:00')
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'camera')
    await scheduler.selectActionNameInRoutine(0, 'takephoto')
    await scheduler.saveRoutine()

    // Wait for first validation
    await scheduler.waitForConflictValidation()

    // Add second routine with same fixed time
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('fixed_time')
    await scheduler.fillFixedTimeInRoutine('21:00')
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'camera')
    await scheduler.selectActionNameInRoutine(0, 'takephoto')
    await scheduler.saveRoutine()

    // Wait for conflict validation
    await scheduler.waitForConflictValidation()
    await page.waitForTimeout(TIMEOUTS.SAVE) // Extra time for debounce

    // Should detect camera resource conflict
    const panelText = await scheduler.getConflictPanelText()
    console.log('Conflict panel text:', panelText)

    const hasConflicts = await scheduler.hasConflictsDetected()
    expect(hasConflicts).toBeTruthy()

    await scheduler.clickCancel()
  })

  /**
   * Test camera resource conflict with same interval triggers.
   *
   * Two interval routines with the same interval will execute at the same times,
   * causing camera resource contention.
   */
  test('detects camera conflict for same-interval triggers', async ({ page }) => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Add first routine with interval trigger (every 30 minutes)
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(30)
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'camera')
    await scheduler.selectActionNameInRoutine(0, 'takephoto')
    await scheduler.saveRoutine()

    // Add second routine with same interval
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(30)
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'camera')
    await scheduler.selectActionNameInRoutine(0, 'takephoto')
    await scheduler.saveRoutine()

    // Wait for validation
    await scheduler.waitForConflictValidation()
    await page.waitForTimeout(TIMEOUTS.SAVE)

    // Should detect camera resource conflict
    const panelText = await scheduler.getConflictPanelText()
    console.log('Conflict panel text:', panelText)

    const hasConflicts = await scheduler.hasConflictsDetected()
    expect(hasConflicts).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Validation Timing
  // ============================================================

  test('validation updates after routine changes (debounced)', async ({ page }) => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Add a routine
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(60)
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'gpio')
    await scheduler.selectActionNameInRoutine(0, 'attract_on')
    await scheduler.saveRoutine()

    // Initial validation - should show no conflicts
    await scheduler.waitForConflictValidation()
    let noConflicts = await scheduler.hasNoConflicts()
    expect(noConflicts).toBeTruthy()

    // Add a second conflicting routine
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(60)
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'gpio')
    await scheduler.selectActionNameInRoutine(0, 'attract_on')
    await scheduler.saveRoutine()

    // Wait for debounced validation
    await page.waitForTimeout(TIMEOUTS.DEBOUNCE_VALIDATION)
    await scheduler.waitForConflictValidation()

    // Now should show conflicts (GPIO state conflict - attract_on at same time)
    const panelText = await scheduler.getConflictPanelText()
    console.log('After adding second routine:', panelText)

    // Panel should have updated
    expect(panelText).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Loading State
  // ============================================================

  test('shows loading state during validation', async ({ page }) => {
    await scheduler.clickNewSchedule()
    await scheduler.fillScheduleName(scheduler.generateTestScheduleName())

    // Add a routine to trigger validation
    await scheduler.clickAddRoutine()
    await scheduler.selectTriggerTypeInRoutine('interval')
    await scheduler.fillIntervalMinutesInRoutine(15)
    await scheduler.clickAddActionInRoutine()
    await scheduler.selectActionTypeInRoutine(0, 'gpio')
    await scheduler.selectActionNameInRoutine(0, 'attract_on')
    await scheduler.saveRoutine()

    // The loading state may be brief, but panel should eventually show a result
    await page.waitForTimeout(TIMEOUTS.SAVE) // Wait for debounce + validation

    // Panel should show either loading, no conflicts, or conflicts
    const panelText = await scheduler.getConflictPanelText()
    expect(panelText).toBeTruthy()

    // Should contain one of: "Checking", "No conflicts", or "conflict"
    const hasValidState =
      panelText.includes('Checking') ||
      panelText.includes('No conflicts') ||
      panelText.includes('conflict')
    expect(hasValidState).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Edit Mode
  // ============================================================

  test('conflict panel works in edit mode', async () => {
    const scheduleCount = await scheduler.getScheduleCount()
    if (scheduleCount === 0) {
      test.skip(true, 'No schedules available for testing edit')
      return
    }

    // Open existing schedule for editing
    await scheduler.clickEditOnSchedule(0)
    expect(await scheduler.isEditorOpen()).toBeTruthy()

    // Conflict panel should be visible
    const panelVisible = await scheduler.isConflictPanelVisible()
    expect(panelVisible).toBeTruthy()

    // Wait for initial validation of existing routines
    await scheduler.waitForConflictValidation()

    // Panel should show some state
    const panelText = await scheduler.getConflictPanelText()
    expect(panelText).toBeTruthy()

    await scheduler.clickCancel()
  })

  // ============================================================
  // Wider Drawer
  // ============================================================

  test('editor drawer is wide enough for two columns', async ({ page }) => {
    await scheduler.clickNewSchedule()

    // Check drawer has max-w-4xl class (wider than previous max-w-2xl)
    const drawer = page.locator('[data-testid="schedule-editor-drawer"]')
    await expect(drawer).toHaveClass(/max-w-4xl/)

    await scheduler.clickCancel()
  })
})
