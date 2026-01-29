import { test } from '@playwright/test';

test('interactive screenshot', async ({ page }) => {
  // Go to the scheduler page
  await page.goto('/scheduler');
  
  // Pause - navigate to the page you want, then click Resume
  await page.pause();
  
  // Take screenshot after resume
  await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
  console.log('Screenshot saved to /tmp/screenshot.png');
});
