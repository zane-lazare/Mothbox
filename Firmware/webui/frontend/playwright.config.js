import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E Test Configuration
 *
 * Tests run against the remote Mothbox Pi at mothbox.lazare.nz:5000
 * Uses Firefox browser as specified in project requirements
 *
 * Run tests:
 *   npm run test:e2e           # Run all tests sequentially (~53 min)
 *   npm run test:e2e:parallel  # Run 4 shards in parallel (~13 min)
 *   npm run test:e2e:shard1    # Run shard 1 of 4 only
 *   npm run test:e2e:headed    # Run with visible browser
 *   npm run test:e2e:debug     # Debug mode with inspector
 *   npm run test:e2e:ui        # Interactive UI mode
 */

export default defineConfig({
  testDir: './e2e/tests',
  testMatch: '**/*.spec.js',

  // Global test settings
  timeout: 60000, // 60s per test (network latency to remote Pi)
  expect: {
    timeout: 10000, // 10s per assertion
  },

  // Retry and parallelization
  retries: 0, // Local testing against real Pi, no retries needed
  workers: 1, // Sequential execution against single Pi server

  // Report configuration
  reporter: [
    ['list'], // Console output
    ['html', { open: 'never' }], // HTML report (open manually)
  ],

  // Output directories
  outputDir: './test-results',

  // Global browser settings
  use: {
    // Target remote Mothbox Pi
    baseURL: 'http://mothbox.lazare.nz:5000',

    // Artifact collection
    trace: 'retain-on-failure', // Collect trace on failure
    screenshot: 'only-on-failure', // Screenshot on failure
    video: 'retain-on-failure', // Video on failure

    // Navigation settings
    navigationTimeout: 30000, // 30s for page navigation
    actionTimeout: 15000, // 15s for actions (clicks, etc.)

    // Browser context
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  },

  // Browser projects - Firefox only as specified
  projects: [
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
      },
    },
  ],

  // No webServer configuration - tests run against remote Pi
  // The Pi should already be running the Mothbox backend at mothbox.lazare.nz:5000
})
