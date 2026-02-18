import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',  // happy-dom uses less memory than jsdom
    setupFiles: './src/setupTests.js',
    teardownTimeout: 5000,  // Force exit after 5 seconds if cleanup stalls
    testTimeout: 10000,  // 10 second per-test timeout to catch hanging tests
    hookTimeout: 10000,  // 10 second timeout for beforeEach/afterEach hooks
    // Exclude Playwright E2E tests - they use a separate test runner
    exclude: [
      'node_modules/**',
      'e2e/**',
    ],
    // Parallelization settings for improved test performance
    // Using forks (separate processes) instead of threads to avoid memory issues
    // Threads share heap memory which causes OOM errors with large test suites
    pool: 'forks',
    poolOptions: {
      forks: {
        minForks: 1,
        maxForks: process.env.CI ? 1 : 2,  // Single fork in CI for memory safety
        isolate: true,  // Fresh process per test file - prevents memory accumulation
      }
    },
    fileParallelism: true,  // Run test files in parallel
    // Force vitest to exit when tests finish, even if async operations are pending
    // This prevents hanging when tests don't properly clean up timers/promises
    forceExit: true,
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.js',
      ],
      thresholds: {
        statements: 70,
        branches: 60,
        functions: 70,
        lines: 70,
      },
    }
  },
})
