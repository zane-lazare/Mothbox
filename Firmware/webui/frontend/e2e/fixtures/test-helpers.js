/**
 * E2E Test Helpers
 *
 * Shared utilities for Playwright E2E tests
 */

/**
 * Check if page is showing rate limit error (429)
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<boolean>}
 */
export async function isRateLimited(page) {
  const content = await page.content()
  return content.includes('Too Many Requests') || content.includes('429')
}

/**
 * Skip test if rate limited
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test')} test
 */
export async function skipIfRateLimited(page, test) {
  if (await isRateLimited(page)) {
    test.skip(true, 'Rate limited by server (50/hour)')
    return true
  }
  return false
}

/**
 * Wait for gallery to finish loading photos
 * @param {import('@playwright/test').Page} page
 */
export async function waitForGalleryLoad(page) {
  // Wait for loading spinner to disappear
  await page.waitForSelector('[data-testid="loading-spinner"]', {
    state: 'hidden',
    timeout: 30000,
  }).catch(() => {
    // Loading spinner might not appear if data loads fast
  })

  // Wait for at least one photo to be visible - using actual PhotoGridItem selector
  await page.waitForSelector('button[aria-label*="View photo"], [data-testid^="photo-item-"], .photo-item', {
    state: 'visible',
    timeout: 30000,
  })
}

/**
 * Wait for network to be idle (no pending requests)
 * @param {import('@playwright/test').Page} page
 * @param {number} timeout - Max wait time in ms
 */
export async function waitForNetworkIdle(page, timeout = 10000) {
  await page.waitForLoadState('networkidle', { timeout })
}

/**
 * Scroll to bottom of page to trigger infinite scroll
 * @param {import('@playwright/test').Page} page
 */
export async function scrollToBottom(page) {
  await page.evaluate(() => {
    window.scrollTo(0, document.body.scrollHeight)
  })
  // Wait a bit for scroll event to trigger
  await page.waitForTimeout(500)
}

/**
 * Get count of visible photos in gallery
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<number>}
 */
export async function getPhotoCount(page) {
  // PhotoGridItem uses button with aria-label="View photo: {filename}"
  const selectors = [
    'button[aria-label*="View photo"]',
    '[data-testid^="photo-item-"]',
    '.photo-item',
    '.gallery-photo',
    '[class*="PhotoCard"]',
  ]

  for (const selector of selectors) {
    const count = await page.locator(selector).count()
    if (count > 0) return count
  }

  return 0
}

/**
 * Generate unique test tag name for cleanup
 * @returns {string}
 */
export function generateTestTag() {
  const timestamp = Date.now()
  return `e2e-test-tag-${timestamp}`
}

/**
 * Take screenshot with descriptive name
 * @param {import('@playwright/test').Page} page
 * @param {string} name
 */
export async function takeScreenshot(page, name) {
  await page.screenshot({
    path: `./test-results/screenshots/${name}-${Date.now()}.png`,
    fullPage: true,
  })
}

/**
 * Check if element is visible in viewport
 * @param {import('@playwright/test').Page} page
 * @param {string} selector
 * @returns {Promise<boolean>}
 */
export async function isInViewport(page, selector) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel)
    if (!el) return false

    const rect = el.getBoundingClientRect()
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.right <= window.innerWidth
    )
  }, selector)
}

/**
 * Format date for filter input
 * @param {Date} date
 * @returns {string} - YYYY-MM-DD format
 */
export function formatDateForInput(date) {
  return date.toISOString().split('T')[0]
}

/**
 * Get date N days ago
 * @param {number} days
 * @returns {Date}
 */
export function daysAgo(days) {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date
}
