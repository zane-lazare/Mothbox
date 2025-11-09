import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useViewMode } from '../useViewMode'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getPreferences: vi.fn(),
  setPreference: vi.fn(),
}))

/**
 * Test suite for useViewMode hook
 *
 * This hook manages gallery view mode preference (grid vs list)
 * with backend API persistence for cross-device sync.
 */
describe('useViewMode', () => {
  let queryClient

  /**
   * Create a fresh QueryClient for each test to prevent state leakage
   */
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for faster tests
          cacheTime: 0, // Don't cache between tests
        },
        mutations: {
          retry: false,
        },
      },
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  /**
   * Helper to render hook with QueryClient provider
   */
  const renderUseViewMode = () => {
    return renderHook(() => useViewMode(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    })
  }

  describe('Initial State', () => {
    it('returns grid as default when preferences API returns empty object', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.viewMode).toBe('grid')
    })

    it('loads saved view mode from backend API on mount', async () => {
      api.getPreferences.mockResolvedValue({
        data: { gallery_view_mode: 'list' },
      })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.viewMode).toBe('list')
      })
    })

    it('returns grid as default when API call fails', async () => {
      api.getPreferences.mockRejectedValue(new Error('Network error'))

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.viewMode).toBe('grid')
    })

    it('sets isLoading to true while fetching preference', () => {
      api.getPreferences.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: {} }), 100))
      )

      const { result } = renderUseViewMode()

      // Initially loading
      expect(result.current.isLoading).toBe(true)
    })
  })

  describe('State Updates', () => {
    it('setViewMode updates state to list', async () => {
      // Mock initial state
      api.getPreferences.mockResolvedValue({ data: {} })

      // Mock setPreference to update the backend state
      api.setPreference.mockImplementation(async (key, value) => {
        // After setting, update the mock to return new value on next fetch
        api.getPreferences.mockResolvedValue({ data: { [key]: value } })
        return { data: { success: true } }
      })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Change to list view
      act(() => {
        result.current.setViewMode('list')
      })

      await waitFor(() => {
        expect(result.current.viewMode).toBe('list')
      })
    })

    it('setViewMode updates state to grid', async () => {
      // Mock initial state as 'list'
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'list' } })

      // Mock setPreference to update the backend state
      api.setPreference.mockImplementation(async (key, value) => {
        // After setting, update the mock to return new value on next fetch
        api.getPreferences.mockResolvedValue({ data: { [key]: value } })
        return { data: { success: true } }
      })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.viewMode).toBe('list')
      })

      // Change to grid view
      act(() => {
        result.current.setViewMode('grid')
      })

      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })
    })

    it('setViewMode calls backend API with correct parameters', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.setPreference.mockResolvedValue({ data: { success: true } })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.setViewMode('list')
      })

      await waitFor(() => {
        expect(api.setPreference).toHaveBeenCalledWith('gallery_view_mode', 'list')
      })
    })
  })

  describe('Optimistic Updates', () => {
    it('updates UI immediately before API call completes', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'grid' } })
      api.setPreference.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: { success: true } }), 100))
      )

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })

      // Change view mode
      act(() => {
        result.current.setViewMode('list')
      })

      // Should update immediately (optimistic)
      await waitFor(() => {
        expect(result.current.viewMode).toBe('list')
      })
    })

    it('rolls back to previous state if API call fails', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'grid' } })
      api.setPreference.mockRejectedValue(new Error('Network error'))

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })

      // Attempt to change view mode
      result.current.setViewMode('list')

      // Should rollback to 'grid' after failure
      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })
    })
  })

  describe('Validation', () => {
    it('only accepts grid or list values', async () => {
      api.getPreferences.mockResolvedValue({ data: {} })
      api.setPreference.mockResolvedValue({ data: { success: true } })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Try to set invalid value
      result.current.setViewMode('invalid')

      // Should not change from default 'grid'
      expect(result.current.viewMode).toBe('grid')
      expect(api.setPreference).not.toHaveBeenCalled()
    })

    it('handles corrupted preference data from API gracefully', async () => {
      api.getPreferences.mockResolvedValue({
        data: { gallery_view_mode: 'corrupted_value' },
      })

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Should default to 'grid' when data is invalid
      expect(result.current.viewMode).toBe('grid')
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully during initial load', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      api.getPreferences.mockRejectedValue(new Error('Network timeout'))

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.viewMode).toBe('grid')

      consoleWarnSpy.mockRestore()
    })

    it('handles API timeout during preference save', async () => {
      api.getPreferences.mockResolvedValue({ data: { gallery_view_mode: 'grid' } })
      api.setPreference.mockRejectedValue(new Error('Request timeout'))

      const { result } = renderUseViewMode()

      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })

      result.current.setViewMode('list')

      // Should rollback after timeout
      await waitFor(() => {
        expect(result.current.viewMode).toBe('grid')
      })
    })
  })
})
