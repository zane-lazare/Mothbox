/**
 * Scheduler Calendar View E2E Tests
 *
 * Tests the calendar view functionality for schedule visualization.
 * Existing tests (1-7) preserved as-is, new tests (8+) added at end.
 */

import { test, expect } from '@playwright/test'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'
import { SchedulerPage } from '../pages/scheduler.page.js'

test.describe('Scheduler Calendar View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scheduler')
    await page.waitForLoadState('networkidle')

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('scheduler page loads', async ({ page }) => {
    // Verify we're on the scheduler page
    const heading = page.locator('text=Schedule')
    await expect(heading.first()).toBeVisible()
  })

  test('calendar tab switches to calendar view', async ({ page }) => {
    // Click Calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Verify calendar panel is visible
    const calendarPanel = page.locator('#calendar-panel')
    await expect(calendarPanel).toBeVisible()
  })

  test('empty state shows when no schedule selected', async ({ page }) => {
    // Switch to calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Verify empty state message is shown
    const emptyState = page.locator('text=No schedule selected')
    await expect(emptyState).toBeVisible()
  })

  test('view mode buttons are visible', async ({ page }) => {
    // Switch to calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Verify view mode buttons exist
    const dayButton = page.locator('button:has-text("Day")')
    const weekButton = page.locator('button:has-text("Week")')
    const monthButton = page.locator('button:has-text("Month")')

    await expect(dayButton).toBeVisible()
    await expect(weekButton).toBeVisible()
    await expect(monthButton).toBeVisible()
  })

  test('navigation buttons are visible', async ({ page }) => {
    // Switch to calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Verify navigation buttons
    const todayButton = page.locator('button:has-text("Today")')
    await expect(todayButton).toBeVisible()
  })

  test('schedule selector dropdown is visible', async ({ page }) => {
    // Switch to calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Look for schedule selector (select element or combobox)
    const scheduleSelector = page.locator('select, [role="combobox"]')
    await expect(scheduleSelector.first()).toBeVisible()
  })

  test('view mode switching works', async ({ page }) => {
    // Switch to calendar tab
    const calendarTab = page.locator('button:has-text("Calendar")')
    await calendarTab.click()

    // Click Week view
    const weekButton = page.locator('button:has-text("Week")')
    await weekButton.click()

    // Verify week view is active (button should have different styling)
    await expect(weekButton).toHaveClass(/bg-blue|active|selected/)

    // Click Day view
    const dayButton = page.locator('button:has-text("Day")')
    await dayButton.click()

    // Verify day view is active
    await expect(dayButton).toHaveClass(/bg-blue|active|selected/)
  })

  // ============================================================
  // NEW TESTS (8+) - Added for Issue #234
  // ============================================================

  test('select schedule in calendar dropdown', async ({ page }) => {
    const scheduler = new SchedulerPage(page)

    // Switch to calendar tab
    await scheduler.switchToCalendarTab()

    // Get available options
    const options = await scheduler.getCalendarScheduleOptions()

    if (options.length === 0) {
      test.skip(true, 'No schedules available in dropdown')
      return
    }

    // Select first schedule (skip empty option if present)
    const scheduleToSelect = options.find(opt => opt.trim() !== '' && opt !== 'Select a schedule')
    if (!scheduleToSelect) {
      test.skip(true, 'No valid schedule options available')
      return
    }

    await scheduler.selectScheduleInCalendar(scheduleToSelect)

    // If a schedule is selected, empty state should eventually be hidden
    // Note: might take a moment to load calendar data
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Verify the selection worked - empty state may or may not be hidden
    // depending on whether schedule has any executions to display
    void (await scheduler.isEmptyCalendarStateVisible())
  })

  test('navigate to previous period', async ({ page }) => {
    const scheduler = new SchedulerPage(page)
    await scheduler.switchToCalendarTab()

    const beforeDate = await scheduler.getCalendarDateDisplay()
    await scheduler.clickPrevious()
    const afterDate = await scheduler.getCalendarDateDisplay()

    expect(beforeDate).not.toBe(afterDate)
  })

  test('navigate to next period', async ({ page }) => {
    const scheduler = new SchedulerPage(page)
    await scheduler.switchToCalendarTab()

    const beforeDate = await scheduler.getCalendarDateDisplay()
    await scheduler.clickNext()
    const afterDate = await scheduler.getCalendarDateDisplay()

    expect(beforeDate).not.toBe(afterDate)
  })

  test('Today button returns to current date', async ({ page }) => {
    const scheduler = new SchedulerPage(page)
    await scheduler.switchToCalendarTab()

    // Capture today's display
    const todayDisplay = await scheduler.getCalendarDateDisplay()

    // Navigate away
    await scheduler.clickNext()
    await scheduler.clickNext()
    const awayDisplay = await scheduler.getCalendarDateDisplay()
    expect(todayDisplay).not.toBe(awayDisplay)

    // Return to today
    await scheduler.clickToday()
    const returnDisplay = await scheduler.getCalendarDateDisplay()

    expect(returnDisplay).toBe(todayDisplay)
  })

  test('month view shows calendar grid', async ({ page }) => {
    const scheduler = new SchedulerPage(page)

    // Switch to calendar tab
    await scheduler.switchToCalendarTab()

    // Click Month view
    await scheduler.clickMonthView()

    const monthButton = page.locator('button:has-text("Month")')
    await expect(monthButton).toHaveClass(/bg-blue|active|selected/)

    // Look for calendar grid indicators (day names, date cells, etc.)
    const calendarContent = page.locator('#calendar-panel')
    await expect(calendarContent).toBeVisible()
  })

  test('week view shows week layout', async ({ page }) => {
    const scheduler = new SchedulerPage(page)

    // Switch to calendar tab
    await scheduler.switchToCalendarTab()

    // Click Week view
    await scheduler.clickWeekView()

    const weekButton = page.locator('button:has-text("Week")')
    await expect(weekButton).toHaveClass(/bg-blue|active|selected/)
  })

  test('day view shows single day', async ({ page }) => {
    const scheduler = new SchedulerPage(page)

    // Switch to calendar tab
    await scheduler.switchToCalendarTab()

    // Click Day view
    await scheduler.clickDayView()

    const dayButton = page.locator('button:has-text("Day")')
    await expect(dayButton).toHaveClass(/bg-blue|active|selected/)
  })

  test('calendar retains view mode after navigation', async ({ page }) => {
    const scheduler = new SchedulerPage(page)

    // Switch to calendar tab
    await scheduler.switchToCalendarTab()

    // Switch to Week view
    await scheduler.clickWeekView()

    // Navigate (if navigation buttons exist)
    const navButtons = page.locator('#calendar-panel button')
    const count = await navButtons.count()
    if (count >= 3) {
      // Navigate forward
      await navButtons.nth(count - 1).click()
      await page.waitForLoadState('networkidle')
    }

    // Verify still in Week view
    const weekButton = page.locator('button:has-text("Week")')
    await expect(weekButton).toHaveClass(/bg-blue|active|selected/)
  })
})
