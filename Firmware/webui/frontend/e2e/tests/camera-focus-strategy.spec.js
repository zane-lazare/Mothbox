/**
 * Focus Strategy Card Tests
 *
 * Tests for the Focus Strategy card on the Settings page:
 * - Card visibility and default expanded state
 * - Mode dropdown with all 4 options
 * - Conditional sub-controls per focus mode
 * - Slider interaction and display updates
 */

import { test, expect } from '@playwright/test'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('Focus Strategy Card', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings page
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('card is visible and expanded by default', async ({ page }) => {
    // The CollapsibleCard button with title should be visible
    const cardButton = page.locator('button', { has: page.locator('h4:has-text("Focus Strategy")') })
    await expect(cardButton).toBeVisible({ timeout: TIMEOUTS.NETWORK })
    await expect(cardButton).toHaveAttribute('aria-expanded', 'true')

    // Inner content (data-testid) should be visible since card starts expanded
    const cardContent = page.locator('[data-testid="focus-strategy-card"]')
    await expect(cardContent).toBeVisible()
  })

  test('mode dropdown has all 4 options', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    const options = dropdown.locator('option')
    const count = await options.count()
    expect(count).toBe(4)

    // Verify option values match CAMERA_SETTINGS.FOCUS_MODES constants
    const values = await options.evaluateAll(opts => opts.map(o => o.value))
    expect(values).toEqual(['auto-calibrate', 'manual', 'af-single', 'af-continuous'])
  })

  test('auto-calibrate mode shows interval slider and position display', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    await dropdown.selectOption('auto-calibrate')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    await expect(page.locator('[data-testid="calibration-interval-slider"]')).toBeVisible()
    await expect(page.locator('[data-testid="calibration-position-display"]')).toBeVisible()

    // Manual-only and AF-only controls should NOT be visible
    await expect(page.locator('[data-testid="lens-position-slider"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="af-range-select"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="af-speed-select"]')).not.toBeVisible()
  })

  test('manual mode shows lens position slider', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    await dropdown.selectOption('manual')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    await expect(page.locator('[data-testid="lens-position-slider"]')).toBeVisible()

    // Other sub-controls should NOT be visible
    await expect(page.locator('[data-testid="calibration-interval-slider"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="calibration-position-display"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="af-range-select"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="af-speed-select"]')).not.toBeVisible()
  })

  test('af-single mode shows range and speed dropdowns', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    await dropdown.selectOption('af-single')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    await expect(page.locator('[data-testid="af-range-select"]')).toBeVisible()
    await expect(page.locator('[data-testid="af-speed-select"]')).toBeVisible()

    // Other sub-controls should NOT be visible
    await expect(page.locator('[data-testid="calibration-interval-slider"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="calibration-position-display"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="lens-position-slider"]')).not.toBeVisible()
  })

  test('af-continuous mode shows range and speed dropdowns', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    await dropdown.selectOption('af-continuous')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    await expect(page.locator('[data-testid="af-range-select"]')).toBeVisible()
    await expect(page.locator('[data-testid="af-speed-select"]')).toBeVisible()

    // Other sub-controls should NOT be visible
    await expect(page.locator('[data-testid="calibration-interval-slider"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="calibration-position-display"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="lens-position-slider"]')).not.toBeVisible()
  })

  test('calibration interval slider updates display value', async ({ page }) => {
    const dropdown = page.locator('[data-testid="focus-mode-select"]')
    await expect(dropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    await dropdown.selectOption('auto-calibrate')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    const slider = page.locator('[data-testid="calibration-interval-slider"]')
    await expect(slider).toBeVisible()

    // Set slider to a known value
    await slider.fill('300')
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Label should reflect new value
    const label = page.locator('text=Calibration Interval: Every 300 seconds')
    await expect(label).toBeVisible()
  })
})
