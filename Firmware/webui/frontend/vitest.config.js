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
    pool: 'forks',          // Use forks instead of threads for better isolation
    poolOptions: {
      forks: {
        singleFork: true    // Run all tests in a single fork for faster cleanup
      }
    },
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.js',
      ]
    }
  },
})
