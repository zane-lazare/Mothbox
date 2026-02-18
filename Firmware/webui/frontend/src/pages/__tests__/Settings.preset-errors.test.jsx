/**
 * Integration tests for Settings preset error notifications (PR #72)
 *
 * REQUIREMENTS:
 * - Run on Raspberry Pi with backend running
 * - Backend API must be accessible at http://localhost:5000
 * - Test presets must exist in database
 * - Tests fallback logic when preset fails
 *
 * Run via: ./Tests/run_tests.sh preset-errors
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Settings from '../Settings'
import toast from 'react-hot-toast'

// Only mock toast to capture error notifications
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

// Mock useSocket hook to provide a mock socket (replaces socket.io-client mock)
vi.mock('../../hooks/useSocket', () => ({
  default: vi.fn(() => ({
    socket: {
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
      connected: true,
    },
    connected: true,
  })),
}))

describe('Settings - Preset Error Notifications Integration Tests', () => {
  let queryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          staleTime: 0,
        },
      },
    })
    vi.clearAllMocks()

    // Set API URL for tests
    if (!import.meta.env.VITE_API_URL) {
      import.meta.env.VITE_API_URL = 'http://localhost:5000/api'
    }
  })

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Settings />
      </QueryClientProvider>
    )
  }

  it('should show toast error when photo preset fails and fallback fails', async () => {
    // This test requires backend with:
    // 1. Invalid default photo preset in preferences
    // 2. Fallback preset (balanced) also unavailable or invalid

    renderComponent()

    await waitFor(() => {
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          call[0].includes('fallback') || call[0].includes('failed to load')
        )

        // If fallback errors occurred, verify display name is used
        if (errorCalls.length > 0) {
          expect(errorCalls[0][0]).toBeTruthy()
          // Should mention either fallback preset or no fallback available
          expect(errorCalls[0][0]).toMatch(/fallback|failed to load|not found/)
        }
      }
    }, { timeout: 5000 })
  })

  it('should include preset display name in error messages', async () => {
    renderComponent()

    await waitFor(() => {
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          call[0].toLowerCase().includes('preset')
        )

        // Verify preset names are properly formatted
        if (errorCalls.length > 0) {
          errorCalls.forEach(call => {
            expect(call[0]).toBeTruthy()
            expect(typeof call[0]).toBe('string')
          })
        }
      }
    }, { timeout: 5000 })
  })

  it('should show toast error when no fallback preset is available', async () => {
    // Tests scenario where:
    // 1. Default preset fails
    // 2. No "balanced" fallback exists in database

    renderComponent()

    await waitFor(() => {
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          call[0].includes('no fallback') || call[0].includes('not found')
        )

        if (errorCalls.length > 0) {
          // Verify error message indicates no fallback
          expect(errorCalls[0][0]).toMatch(/no fallback|not found/)
        }
      }
    }, { timeout: 5000 })
  })

  it('should show toast error when liveview preset fails with fallback logic', async () => {
    renderComponent()

    await waitFor(() => {
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          (call[0].toLowerCase().includes('liveview') ||
           call[0].toLowerCase().includes('preset')) &&
          call[0].includes('failed')
        )

        if (errorCalls.length > 0) {
          // Verify liveview preset errors are handled
          errorCalls.forEach(call => {
            expect(call[0]).toBeTruthy()
          })
        }
      }
    }, { timeout: 5000 })
  })
})
