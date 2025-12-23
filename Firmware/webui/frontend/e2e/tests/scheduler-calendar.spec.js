/**
 * Scheduler Calendar View E2E Tests
 *
 * Tests the calendar view functionality for schedule visualization
 */

import { test, expect } from '@playwright/test'
import { isRateLimited } from '../fixtures/test-helpers.js'

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
})
