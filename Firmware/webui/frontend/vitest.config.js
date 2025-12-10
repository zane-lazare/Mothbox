import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

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
    pool: 'threads',  // Use worker threads (faster than forks for jsdom tests)
    poolOptions: {
      threads: {
        minThreads: 1,
        maxThreads: 4,  // Adjust based on available CPU cores
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
