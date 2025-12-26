/**
 * Tests for useCronValidation hook (Issue #233)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import useCronValidation from '../useCronValidation'
import * as cronApi from '../../utils/cronApi'

// Mock the cronApi module
vi.mock('../../utils/cronApi')

describe('useCronValidation', () => {
  let queryClient

  beforeEach(() => {
    // Create a fresh QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Disable retries for tests
        },
      },
    })

    // Reset all mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  /**
   * Helper to render hook with QueryClient wrapper
   */
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )

  describe('Basic Functionality', () => {
    it('should not fetch when expression is empty', () => {
      const { result } = renderHook(() => useCronValidation(''), { wrapper })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isFetching).toBe(false)
      expect(cronApi.validateCronExpression).not.toHaveBeenCalled()
    })

    it('should not fetch when expression is whitespace only', () => {
      const { result } = renderHook(() => useCronValidation('   '), { wrapper })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.isFetching).toBe(false)
      expect(cronApi.validateCronExpression).not.toHaveBeenCalled()
    })

    it('should fetch when expression is provided', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00', '2024-12-26T15:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(cronApi.validateCronExpression).toHaveBeenCalledWith('0 * * * *', 5)
      expect(result.current.data).toEqual(mockResponse)
    })

    it('should pass custom count to API', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: Array(10).fill('2024-12-26T14:00:00'),
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () => useCronValidation('0 * * * *', { count: 10 }),
        { wrapper }
      )

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(cronApi.validateCronExpression).toHaveBeenCalledWith('0 * * * *', 10)
    })
  })

  describe('Debouncing', () => {
    it('should eventually call API after debounce delay', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 21 * * *',
        description: 'At 21:00 every day',
        next_executions: ['2024-12-26T21:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result, rerender } = renderHook(
        ({ expr }) => useCronValidation(expr),
        { wrapper, initialProps: { expr: '' } }
      )

      // Change to a valid expression
      rerender({ expr: '0 21 * * *' })

      // Wait for debounce and API call
      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 2000 })

      expect(cronApi.validateCronExpression).toHaveBeenCalledWith('0 21 * * *', 5)
    })

    it('should debounce rapid changes and validate final value', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result, rerender } = renderHook(
        ({ expr }) => useCronValidation(expr),
        { wrapper, initialProps: { expr: '' } }
      )

      // Rapidly change expression (simulating typing)
      rerender({ expr: '0' })
      rerender({ expr: '0 *' })
      rerender({ expr: '0 * *' })
      rerender({ expr: '0 * * *' })
      rerender({ expr: '0 * * * *' })

      // Wait for debounce and API call
      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 2000 })

      // Should validate the final expression
      expect(cronApi.validateCronExpression).toHaveBeenCalledWith('0 * * * *', 5)
    })
  })

  describe('Valid Expression', () => {
    it('should return validation result for valid expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 21 * * *',
        description: 'At 21:00 every day',
        next_executions: [
          '2024-12-26T21:00:00',
          '2024-12-27T21:00:00',
          '2024-12-28T21:00:00',
        ],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('0 21 * * *'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data.valid).toBe(true)
      expect(result.current.data.description).toBe('At 21:00 every day')
      expect(result.current.data.next_executions).toHaveLength(3)
    })

    it('should return next executions for valid expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '*/5 * * * *',
        description: 'Every 5 minutes',
        next_executions: [
          '2024-12-26T14:00:00',
          '2024-12-26T14:05:00',
          '2024-12-26T14:10:00',
          '2024-12-26T14:15:00',
          '2024-12-26T14:20:00',
        ],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('*/5 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data.valid).toBe(true)
      expect(result.current.data.next_executions).toHaveLength(5)
    })
  })

  describe('Invalid Expression', () => {
    it('should return error for invalid expression', async () => {
      const mockResponse = {
        valid: false,
        expression: 'invalid * * * *',
        error: 'Invalid cron expression: invalid is not a valid minute value',
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('invalid * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data.valid).toBe(false)
      expect(result.current.data.error).toBe(
        'Invalid cron expression: invalid is not a valid minute value'
      )
    })

    it('should handle API errors gracefully', async () => {
      const mockError = new Error('Network error')
      cronApi.validateCronExpression.mockRejectedValue(mockError)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error).toBeTruthy()
    })
  })

  describe('Caching', () => {
    it('should use cached result for same expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result: result1 } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result1.current.isSuccess).toBe(true))

      // Render hook again with same expression
      const { result: result2 } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      // Should use cached result, not call API again
      expect(result2.current.data).toEqual(mockResponse)
      expect(cronApi.validateCronExpression).toHaveBeenCalledTimes(1)
    })

    it('should fetch again for different expression', async () => {
      const mockResponse1 = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      const mockResponse2 = {
        valid: true,
        expression: '0 21 * * *',
        description: 'At 21:00 every day',
        next_executions: ['2024-12-26T21:00:00'],
      }

      cronApi.validateCronExpression
        .mockResolvedValueOnce(mockResponse1)
        .mockResolvedValueOnce(mockResponse2)

      const { result: result1 } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result1.current.isSuccess).toBe(true))

      // Render hook with different expression
      const { result: result2 } = renderHook(() => useCronValidation('0 21 * * *'), { wrapper })

      await waitFor(() => expect(result2.current.isSuccess).toBe(true))

      // Should call API twice (different cache keys)
      expect(cronApi.validateCronExpression).toHaveBeenCalledTimes(2)
      expect(result2.current.data).toEqual(mockResponse2)
    })
  })

  describe('Custom Options', () => {
    it('should accept custom stale time from query options', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(
        () =>
          useCronValidation('0 * * * *', {
            queryOptions: { staleTime: 0 }, // Override default 1 minute
          }),
        { wrapper }
      )

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      // Verify query was successful
      expect(result.current.data).toEqual(mockResponse)
    })
  })

  describe('Loading States', () => {
    it('should show loading state while fetching', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      // Create a promise that resolves after a delay
      let resolvePromise
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })

      cronApi.validateCronExpression.mockReturnValue(delayedPromise)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      // Should be loading initially
      await waitFor(() => expect(result.current.isLoading).toBe(true))

      // Resolve the promise
      resolvePromise(mockResponse)

      // Should finish loading
      await waitFor(() => expect(result.current.isSuccess).toBe(true))
    })
  })

  describe('Error Message Normalization', () => {
    it('should return null errorMessage for valid expression', async () => {
      const mockResponse = {
        valid: true,
        expression: '0 * * * *',
        description: 'At minute 0 of every hour',
        next_executions: ['2024-12-26T14:00:00'],
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.errorMessage).toBeNull()
    })

    it('should return validation error from API response', async () => {
      const mockResponse = {
        valid: false,
        expression: 'invalid',
        error: 'Invalid cron syntax: too few fields',
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('invalid'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.errorMessage).toBe('Invalid cron syntax: too few fields')
    })

    it('should return fallback message when API returns invalid without error', async () => {
      const mockResponse = {
        valid: false,
        expression: 'bad',
      }

      cronApi.validateCronExpression.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useCronValidation('bad'), { wrapper })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.errorMessage).toBe('Invalid cron expression')
    })

    it('should return network error message on request failure', async () => {
      const networkError = new Error('Network Error')

      cronApi.validateCronExpression.mockRejectedValue(networkError)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.errorMessage).toBe('Validation failed: Network Error')
    })

    it('should extract server error from response data', async () => {
      const serverError = new Error('Request failed')
      serverError.response = {
        data: {
          error: 'Server validation failed',
        },
      }

      cronApi.validateCronExpression.mockRejectedValue(serverError)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.errorMessage).toBe('Server validation failed')
    })

    it('should return generic message when no error details available', async () => {
      const unknownError = {}

      cronApi.validateCronExpression.mockRejectedValue(unknownError)

      const { result } = renderHook(() => useCronValidation('0 * * * *'), { wrapper })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.errorMessage).toBe('Unable to validate expression. Please try again.')
    })
  })
})
