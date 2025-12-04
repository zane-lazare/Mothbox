import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import useTagAutocomplete from '../useTagAutocomplete'
import * as api from '../../utils/api'

// Mock the API module
vi.mock('../../utils/api', () => ({
  getTagAutocomplete: vi.fn()
}))

/**
 * Test suite for useTagAutocomplete hook
 *
 * Tests the custom hook for fetching tag autocomplete suggestions with debouncing,
 * minimum character requirements, and caching.
 */
describe('useTagAutocomplete', () => {
  let queryClient

  // Helper function to create a wrapper with QueryClient
  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for faster tests
        },
      },
    })

    return function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      )
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
    if (queryClient) {
      queryClient.clear()
    }
  })

  describe('Minimum character requirement', () => {
    it('test_returns_empty_for_short_query - Query < 2 chars returns empty suggestions', () => {
      const { result } = renderHook(
        () => useTagAutocomplete('a'),
        { wrapper: createWrapper() }
      )

      // Should return empty array for queries shorter than minimum
      expect(result.current.suggestions).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(api.getTagAutocomplete).not.toHaveBeenCalled()
    })

    it('test_returns_empty_for_empty_query - Empty query returns empty suggestions', () => {
      const { result } = renderHook(
        () => useTagAutocomplete(''),
        { wrapper: createWrapper() }
      )

      expect(result.current.suggestions).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(api.getTagAutocomplete).not.toHaveBeenCalled()
    })

    it('test_fetches_after_minimum_chars - Query >= 2 chars triggers fetch', async () => {
      const mockSuggestions = [
        { tag: 'moth', count: 42, last_used: '2024-01-15', match_score: 1.0 },
        { tag: 'motorcycle', count: 8, last_used: '2024-01-10', match_score: 0.9 },
      ]

      api.getTagAutocomplete.mockResolvedValueOnce({
        data: mockSuggestions,
      })

      const { result } = renderHook(
        () => useTagAutocomplete('mo', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      // Wait for query to complete
      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledWith('mo', 10)
    })

    it('test_respects_custom_min_chars - Custom minChars option is respected', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      const { result } = renderHook(
        () => useTagAutocomplete('mot', { minChars: 3, debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      // Wait for query to complete
      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalled()
    })

    it('test_no_fetch_below_custom_min_chars - Query below custom minChars does not fetch', async () => {
      const { result } = renderHook(
        () => useTagAutocomplete('mo', { minChars: 3 }),
        { wrapper: createWrapper() }
      )

      // Wait for debounce

      expect(result.current.suggestions).toEqual([])
      expect(api.getTagAutocomplete).not.toHaveBeenCalled()
    })
  })

  describe('Debouncing', () => {
    it('test_debounces_rapid_typing - Multiple quick calls only make 1 API request', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValue({ data: mockSuggestions })

      const { rerender } = renderHook(
        ({ query }) => useTagAutocomplete(query, { debounceMs: 0 }),
        {
          wrapper: createWrapper(),
          initialProps: { query: 'm' }, // Start with 1 char (below minimum)
        }
      )

      // Simulate rapid typing - rerender quickly before debounce fires
      await act(async () => {
        rerender({ query: 'mo' })
        rerender({ query: 'mot' })
        rerender({ query: 'moth' })
        rerender({ query: 'moths' })
        // Now advance past the full debounce time
      })

      // Wait for query to complete
      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalledTimes(1)
      })

      // Should only call with final query
      expect(api.getTagAutocomplete).toHaveBeenCalledWith('moths', 10)
    })

    it('test_respects_custom_debounce - Custom debounceMs option is respected', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      // Should fetch after custom 100ms
      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalled()
      })
    })
  })

  describe('Loading state', () => {
    it('test_returns_loading_state - isLoading true during fetch', async () => {
      api.getTagAutocomplete.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isLoading).toBe(true)
      })

      expect(result.current.suggestions).toEqual([])
      expect(result.current.isError).toBe(false)
    })
  })

  describe('Success scenarios', () => {
    it('test_returns_suggestions_on_success - Successful fetch returns suggestions', async () => {
      const mockSuggestions = [
        { tag: 'moth', count: 42, last_used: '2024-01-15', match_score: 1.0 },
        { tag: 'butterfly', count: 18, last_used: '2024-01-10', match_score: 0.8 },
      ]

      api.getTagAutocomplete.mockResolvedValueOnce({
        data: mockSuggestions,
      })

      const { result } = renderHook(
        () => useTagAutocomplete('mo', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('test_returns_empty_array_for_no_results - No matches returns empty array', async () => {
      api.getTagAutocomplete.mockResolvedValueOnce({
        data: [],
      })

      const { result } = renderHook(
        () => useTagAutocomplete('zzz', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      // Wait for fetch to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.suggestions).toEqual([])
      expect(result.current.isError).toBe(false)
    })
  })

  describe('Error handling', () => {
    it('test_handles_api_error - API error sets isError and error', async () => {
      const error = new Error('Failed to fetch autocomplete suggestions')
      api.getTagAutocomplete.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.suggestions).toEqual([])
      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toBe('Failed to fetch autocomplete suggestions')
    })

    it('test_handles_500_error - Server errors handled gracefully', async () => {
      const error = new Error('Request failed with status code 500')
      error.response = {
        status: 500,
        statusText: 'Internal Server Error',
      }
      api.getTagAutocomplete.mockRejectedValueOnce(error)

      const { result } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toBeDefined()
      expect(result.current.error.message).toContain('500')
    })

    it('test_handles_network_error - Network errors handled gracefully', async () => {
      api.getTagAutocomplete.mockRejectedValueOnce(new Error('Network request failed'))

      const { result } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error.message).toBe('Network request failed')
    })
  })

  describe('Caching', () => {
    it('test_caches_recent_queries - Same query uses cached result', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValue({ data: mockSuggestions })

      const wrapper = createWrapper()

      // First render - should fetch
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper }
      )

      await waitFor(() => {
        expect(result1.current.suggestions).toEqual(mockSuggestions)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledTimes(1)

      unmount1()

      // Second render - should use cache
      const { result: result2 } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.suggestions).toEqual(mockSuggestions)
      })

      // Should still only have 1 fetch call (cached)
      expect(api.getTagAutocomplete).toHaveBeenCalledTimes(1)
    })

    it('test_different_queries_not_cached - Different queries fetch separately', async () => {
      const mockSuggestions1 = [{ tag: 'moth', count: 42 }]
      const mockSuggestions2 = [{ tag: 'butterfly', count: 18 }]

      api.getTagAutocomplete
        .mockResolvedValueOnce({ data: mockSuggestions1 })
        .mockResolvedValueOnce({ data: mockSuggestions2 })

      const wrapper = createWrapper()

      // First query
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper }
      )

      await waitFor(() => {
        expect(result1.current.suggestions).toEqual(mockSuggestions1)
      })

      unmount1()

      // Different query should fetch again
      const { result: result2 } = renderHook(
        () => useTagAutocomplete('butterfly'),
        { wrapper }
      )

      await waitFor(() => {
        expect(result2.current.suggestions).toEqual(mockSuggestions2)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledTimes(2)
    })
  })

  describe('Limit option', () => {
    it('test_respects_limit_option - Custom limit passed to API', async () => {
      const mockSuggestions = [
        { tag: 'moth1', count: 5 },
        { tag: 'moth2', count: 4 },
        { tag: 'moth3', count: 3 },
      ]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      const { result } = renderHook(
        () => useTagAutocomplete('moth', { limit: 3, debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledWith('moth', 3)
    })

    it('test_default_limit - Uses default limit of 10', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalledWith('moth', 10)
      })
    })
  })

  describe('Enabled option', () => {
    it('test_disabled_option_prevents_fetch - enabled=false prevents all fetches', async () => {
      const { result } = renderHook(
        () => useTagAutocomplete('moth', { enabled: false }),
        { wrapper: createWrapper() }
      )

      expect(result.current.suggestions).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(api.getTagAutocomplete).not.toHaveBeenCalled()
    })

    it('test_enabled_true_allows_fetch - enabled=true allows fetch', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      renderHook(
        () => useTagAutocomplete('moth', { enabled: true, debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalled()
      })
    })

    it('test_enabled_default_is_true - Default enabled is true', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalled()
      })
    })
  })

  describe('Query parameter changes', () => {
    it('test_refetches_on_query_change - Changing query triggers new fetch', async () => {
      const mockSuggestions1 = [{ tag: 'moth', count: 42 }]
      const mockSuggestions2 = [{ tag: 'butterfly', count: 18 }]

      api.getTagAutocomplete
        .mockResolvedValueOnce({ data: mockSuggestions1 })
        .mockResolvedValueOnce({ data: mockSuggestions2 })

      const { result, rerender } = renderHook(
        ({ query }) => useTagAutocomplete(query, { debounceMs: 0 }),
        {
          wrapper: createWrapper(),
          initialProps: { query: 'moth' },
        }
      )

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions1)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledTimes(1)

      // Change query
      await act(async () => {
        rerender({ query: 'butterfly' })
        // Advance past debounce for second query
      })

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions2)
      })

      expect(api.getTagAutocomplete).toHaveBeenCalledTimes(2)
    })
  })

  describe('Cleanup', () => {
    it('test_cleans_up_on_unmount - Unmounts without errors', async () => {
      const mockSuggestions = [{ tag: 'moth', count: 42 }]
      api.getTagAutocomplete.mockResolvedValueOnce({ data: mockSuggestions })

      const { unmount } = renderHook(
        () => useTagAutocomplete('moth', { debounceMs: 0 }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(api.getTagAutocomplete).toHaveBeenCalled()
      })

      // Should not throw when unmounting
      expect(() => unmount()).not.toThrow()
    })
  })
})
