/**
 * Smoke Tests
 *
 * Basic tests to verify the Mothbox server is reachable and responding
 * Run these first to ensure the Pi is online before running full suite
 */

import { test, expect } from '@playwright/test'

test.describe('Smoke Tests', () => {
  test('server is reachable', async ({ request }) => {
    // Try to reach the gallery endpoint (SPA routes through index.html)
    const response = await request.get('/gallery')
    // Server returns 200 for SPA routes
    expect(response.status()).toBeLessThan(500)
  })

  test('gallery page loads', async ({ page }) => {
    await page.goto('/gallery')
    await page.waitForLoadState('networkidle')

    // Page should have loaded without error
    const title = await page.title()
    expect(title).toBeTruthy()
  })

  test('API returns photos list', async ({ request }) => {
    const response = await request.get('/api/gallery/photos/paginated?limit=5')

    // Should get 200 OK
    expect(response.ok()).toBeTruthy()

    // Should return JSON
    const data = await response.json()
    expect(data).toHaveProperty('photos')
    expect(Array.isArray(data.photos)).toBeTruthy()
  })

  test('static assets load', async ({ page }) => {
    const response = await page.goto('/gallery')

    // If we get rate limited, skip the test
    if (response && response.status() === 429) {
      test.skip(true, 'Rate limited by server')
      return
    }

    await page.waitForLoadState('networkidle')

    // Check that page loaded (even if it shows an error, we want to see content)
    const pageContent = await page.content()
    expect(pageContent.length).toBeGreaterThan(100)

    // Check for any rendered content (React app or server-rendered HTML)
    const hasAnyContent = await page.locator('body *').first().isVisible()
    expect(hasAnyContent).toBeTruthy()
  })

  test('CSRF token endpoint works', async ({ request }) => {
    const response = await request.get('/api/csrf-token')
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data).toHaveProperty('csrf_token')
    expect(typeof data.csrf_token).toBe('string')
  })
})
