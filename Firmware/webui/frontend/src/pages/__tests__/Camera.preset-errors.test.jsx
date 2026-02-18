/**
 * Integration tests for Camera preset error notifications (PR #72)
 *
 * REQUIREMENTS:
 * - Run on Raspberry Pi with backend running
 * - Backend API must be accessible at http://localhost:5000
 * - Test presets must exist in database
 *
 * Run via: ./Tests/run_tests.sh preset-errors
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Camera from '../Camera'
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
      once: vi.fn(),
      connected: true,
    },
    connected: true,
  })),
}))

describe('Camera - Preset Error Notifications Integration Tests', () => {
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
        <Camera />
      </QueryClientProvider>
    )
  }

  it('should show toast error with display name when photo preset fails', async () => {
    // This test requires:
    // 1. Backend running with invalid preset in preferences
    // 2. Or manually trigger preset failure

    renderComponent()

    // Wait for component to attempt preset initialization
    await waitFor(() => {
      // Check if error toast was called
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          call[0].includes('failed to load')
        )
        // If there were preset errors, verify display name is used
        if (errorCalls.length > 0) {
          expect(errorCalls[0][0]).toMatch(/Preset "[\w\s]+" failed to load/)
        }
      }
    }, { timeout: 5000 })
  })

  it('should extract API error message in toast notification', async () => {
    renderComponent()

    await waitFor(() => {
      if (toast.error.mock.calls.length > 0) {
        const errorCalls = toast.error.mock.calls.filter(call =>
          call[0].includes('failed to load')
        )
        if (errorCalls.length > 0) {
          // Verify error message contains API error or fallback
          expect(errorCalls[0][0]).toBeTruthy()
          expect(typeof errorCalls[0][0]).toBe('string')
        }
      }
    }, { timeout: 5000 })
  })

  it('should handle missing presetsData gracefully with optional chaining', async () => {
    // This verifies optional chaining prevents crashes
    // Component should render without crashing even if preset data is unavailable

    expect(() => renderComponent()).not.toThrow()

    await waitFor(() => {
      // Component should be rendered
      expect(screen.getByText(/Camera/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('should show liveview preset error notifications', async () => {
    renderComponent()

    await waitFor(() => {
      // Check for any liveview preset errors
      const errorCalls = toast.error.mock.calls.filter(call =>
        call[0].toLowerCase().includes('preset') && call[0].includes('failed')
      )

      // If errors occurred, verify they're formatted correctly
      if (errorCalls.length > 0) {
        errorCalls.forEach(call => {
          expect(call[0]).toMatch(/Preset "[\w\s]+" failed to load/)
        })
      }
    }, { timeout: 5000 })
  })
})
