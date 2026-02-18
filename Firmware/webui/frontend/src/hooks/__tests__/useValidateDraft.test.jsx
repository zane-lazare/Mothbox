import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useValidateDraft } from '../useValidateDraft'
import * as schedulerApi from '../../utils/schedulerApi'

vi.mock('../../utils/schedulerApi')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const validRoutine = {
  trigger: { trigger_type: 'interval' },
  actions: [{ type: 'takephoto' }],
}

/**
 * Helper: advance fake timers past the debounce delay and flush all pending
 * promises so React Query can resolve its queryFn.
 */
async function flushDebounceAndQuery() {
  // Advance past the 400ms debounce
  act(() => {
    vi.advanceTimersByTime(500)
  })
  // Flush pending microtasks / promises (React Query queryFn resolution)
  await act(async () => {
    await vi.runAllTimersAsync()
  })
}

describe('useValidateDraft', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('returns initial state', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })
    // React Query data is undefined when query is disabled (no routines yet)
    expect(result.current.conflictReport).toBeUndefined()
    expect(result.current.isValidating).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.error).toBeNull()
    expect(typeof result.current.validateDraft).toBe('function')
    expect(typeof result.current.reset).toBe('function')
  })

  it('debounces validation calls', () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('triggers validation after debounce delay', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    await flushDebounceAndQuery()

    expect(schedulerApi.validateDraftRoutines).toHaveBeenCalledTimes(1)
  })

  it('filters routines without trigger_type or actions', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    const routines = [
      validRoutine,
      { trigger: {}, actions: [{ type: 'takephoto' }] },
      { trigger: { trigger_type: 'interval' }, actions: [] },
      null,
    ]

    act(() => {
      result.current.validateDraft(routines)
    })

    await flushDebounceAndQuery()

    expect(schedulerApi.validateDraftRoutines).toHaveBeenCalledTimes(1)
    const callArgs = schedulerApi.validateDraftRoutines.mock.calls[0][0]
    expect(callArgs.routines).toHaveLength(1)
  })

  it('does not call API when all routines are invalid', async () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([{ trigger: {}, actions: [] }])
    })

    await flushDebounceAndQuery()

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('passes options to API call', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(
      () => useValidateDraft({ days: 3, latitude: 9.0, longitude: -79.5, timezone: 'America/Panama' }),
      { wrapper: createWrapper() }
    )

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    await flushDebounceAndQuery()

    const callArgs = schedulerApi.validateDraftRoutines.mock.calls[0][0]
    expect(callArgs.days).toBe(3)
    expect(callArgs.latitude).toBe(9.0)
    expect(callArgs.longitude).toBe(-79.5)
    expect(callArgs.timezone).toBe('America/Panama')
  })

  it('returns conflict report after validation', async () => {
    const mockReport = {
      conflicts: [{ type: 'time_overlap', severity: 'warning' }],
      total_conflicts: 1,
    }
    schedulerApi.validateDraftRoutines.mockResolvedValue({ data: mockReport })

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    await flushDebounceAndQuery()

    expect(result.current.conflictReport).toEqual(mockReport)
  })

  it('handles API errors', async () => {
    schedulerApi.validateDraftRoutines.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    await flushDebounceAndQuery()

    expect(result.current.isError).toBe(true)
    expect(result.current.error).toBeTruthy()
  })

  it('resets state when reset is called', async () => {
    const mockResponse = { data: { conflicts: [], total_conflicts: 0 } }
    schedulerApi.validateDraftRoutines.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    await flushDebounceAndQuery()

    expect(result.current.conflictReport).toBeDefined()

    act(() => {
      result.current.reset()
    })

    // After reset, debouncedRoutines is null, query is disabled, data reverts to undefined
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(result.current.conflictReport).toBeUndefined()
  })

  it('cancels pending debounce on reset', async () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft([validRoutine])
    })

    act(() => {
      result.current.reset()
    })

    await flushDebounceAndQuery()

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })

  it('handles null/undefined routines array', async () => {
    const { result } = renderHook(() => useValidateDraft(), {
      wrapper: createWrapper(),
    })

    act(() => {
      result.current.validateDraft(null)
    })

    await flushDebounceAndQuery()

    expect(schedulerApi.validateDraftRoutines).not.toHaveBeenCalled()
  })
})
