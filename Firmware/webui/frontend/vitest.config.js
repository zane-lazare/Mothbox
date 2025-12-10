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
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    teardownTimeout: 5000,  // Force exit after 5 seconds if cleanup stalls
    testTimeout: 10000,  // 10 second per-test timeout to catch hanging tests
    hookTimeout: 10000,  // 10 second timeout for beforeEach/afterEach hooks
    // Parallelization settings for improved test performance
    // Using forks (separate processes) instead of threads to avoid memory issues
    // Threads share heap memory which causes OOM errors with large test suites
    pool: 'forks',
    poolOptions: {
      forks: {
        minForks: 1,
        maxForks: 2,  // Limited to prevent memory exhaustion in CI
      }
    },
    fileParallelism: true,  // Run test files in parallel
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.js',
      ]
    }
  },
})
