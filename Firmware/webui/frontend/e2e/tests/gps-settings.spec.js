/**
 * GPS Settings Tests
 *
 * Tests for GPS precision dropdown and localStorage persistence
 */

import { test, expect } from '@playwright/test'
import { isRateLimited, TIMEOUTS } from '../fixtures/test-helpers.js'

test.describe('GPS Settings', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings page
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')

    // Check for rate limiting before each test
    if (await isRateLimited(page)) {
      test.skip(true, 'Rate limited by server (50/hour)')
    }
  })

  test('settings page loads and GPS Settings card is visible', async ({ page }) => {
    // Wait for GPS Settings card to be visible
    const gpsCard = page.locator('text=🛰️ GPS Module Configuration')
    await expect(gpsCard).toBeVisible({ timeout: TIMEOUTS.NETWORK })
  })

  test('GPS precision dropdown is present with all options', async ({ page }) => {
    // Locate the GPS precision dropdown
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    // Verify all 7 options are present (0-6 decimal places)
    const options = precisionDropdown.locator('option')
    const optionCount = await options.count()
    expect(optionCount).toBe(7)

    // Verify each option value exists
    for (let i = 0; i <= 6; i++) {
      const option = options.nth(i)
      const value = await option.getAttribute('value')
      expect(value).toBe(String(i))
    }
  })

  test('selecting a precision value updates the dropdown', async ({ page }) => {
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    // Select precision value 4 (4 decimals)
    await precisionDropdown.selectOption('4')

    // Verify dropdown shows selected value
    const selectedValue = await precisionDropdown.inputValue()
    expect(selectedValue).toBe('4')
  })

  test('precision value is saved to localStorage', async ({ page }) => {
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    // Select precision value 3
    await precisionDropdown.selectOption('3')

    // Wait briefly for localStorage write to complete
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Check localStorage value
    const storedValue = await page.evaluate(() => {
      return localStorage.getItem('mothbox_gps_precision')
    })
    expect(storedValue).toBe('3')
  })

  test('precision persists after page reload', async ({ page }) => {
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    // Set precision to 5
    await precisionDropdown.selectOption('5')

    // Wait for state to save
    await page.waitForTimeout(TIMEOUTS.TRANSITION)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Check that dropdown still shows value 5
    const reloadedDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(reloadedDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    const selectedValue = await reloadedDropdown.inputValue()
    expect(selectedValue).toBe('5')
  })

  test('default precision is 2 decimals when no preference is stored', async ({ page }) => {
    // Clear localStorage before test
    await page.evaluate(() => {
      localStorage.removeItem('mothbox_gps_precision')
    })

    // Reload to apply cleared state
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Check default value
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    const defaultValue = await precisionDropdown.inputValue()
    expect(defaultValue).toBe('2')
  })

  test('each precision option has descriptive label', async ({ page }) => {
    const precisionDropdown = page.locator('select[aria-label="GPS Coordinate Precision"]')
    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })

    // Verify option text includes both label and description
    const options = precisionDropdown.locator('option')

    // Check a few specific options to verify format
    const option0 = await options.nth(0).textContent()
    expect(option0).toContain('0 decimals')
    expect(option0).toContain('Coarse location')

    const option2 = await options.nth(2).textContent()
    expect(option2).toContain('2 decimals')
    expect(option2).toContain('Standard GPS')

    const option6 = await options.nth(6).textContent()
    expect(option6).toContain('6 decimals')
    expect(option6).toContain('Maximum')
  })

  test('precision dropdown is part of GPS Settings card', async ({ page }) => {
    // Verify the dropdown is within the GPS Settings card
    const gpsCard = page.locator('text=🛰️ GPS Module Configuration').locator('..')
    const precisionDropdown = gpsCard.locator('select[aria-label="GPS Coordinate Precision"]')

    await expect(precisionDropdown).toBeVisible({ timeout: TIMEOUTS.NETWORK })
  })

  test('precision setting has descriptive help text', async ({ page }) => {
    // Use structural selector that's less prone to text changes
    const precisionSection = page.locator('select[aria-label="GPS Coordinate Precision"]').locator('..')
    const helpText = precisionSection.locator('.text-xs.text-gray-500')

    await expect(helpText).toBeVisible({ timeout: TIMEOUTS.NETWORK })
  })
})
