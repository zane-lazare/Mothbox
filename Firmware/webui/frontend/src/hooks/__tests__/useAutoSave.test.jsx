import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import useAutoSave from '../useAutoSave'

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('test_debounces_save_by_2_seconds', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Should not save immediately
    expect(onSave).not.toHaveBeenCalled()
    expect(result.current.status).toBe('idle')

    // Advance time by 1 second - still not called
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onSave).not.toHaveBeenCalled()

    // Advance time by another 1 second - now it should be called
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    // Run pending promises
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // Should have saved with correct data
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith({ value: 2 })
  })

  it('test_cancels_pending_save_on_new_change', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // First change
    rerender({ data: { value: 2 } })

    // Advance time by 1.5 seconds
    act(() => {
      vi.advanceTimersByTime(1500)
    })

    // Second change (should cancel previous timer)
    rerender({ data: { value: 3 } })

    // Advance time by 1 second (total 2.5s from first change, but only 1s from second)
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    // Should not have saved yet
    expect(onSave).not.toHaveBeenCalled()

    // Advance by another 1 second (now 2s from second change)
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // Should have saved with the latest data only once
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith({ value: 3 })
  })

  it('test_saves_immediately_with_saveNow', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Call saveNow immediately
    await act(async () => {
      result.current.saveNow()
      // Flush promises
      await Promise.resolve()
    })

    // Should have saved immediately without waiting for debounce
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith({ value: 2 })
  })

  it('test_returns_save_status_idle', () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result } = renderHook(() =>
      useAutoSave({ data: { value: 1 }, onSave })
    )

    expect(result.current.status).toBe('idle')
  })

  it('test_returns_save_status_saving', async () => {
    let resolvePromise
    const onSave = vi.fn().mockImplementation(() => {
      return new Promise((resolve) => {
        resolvePromise = resolve
      })
    })

    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data and trigger save
    rerender({ data: { value: 2 } })

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await Promise.resolve() // Let the promise start
    })

    // Status should be 'saving'
    expect(result.current.status).toBe('saving')

    // Resolve the promise to clean up
    await act(async () => {
      resolvePromise()
      await Promise.resolve()
    })
  })

  it('test_returns_save_status_saved', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Wait for debounce
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    // Run only pending promises, not the status reset timer
    await act(async () => {
      await Promise.resolve()
    })

    // Status should be 'saved'
    expect(result.current.status).toBe('saved')
  })

  it('test_returns_save_status_error', async () => {
    const error = new Error('Save failed')
    const onSave = vi.fn().mockRejectedValue(error)
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Wait for debounce
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    // Run pending promises
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // Status should be 'error'
    expect(result.current.status).toBe('error')
  })

  it('test_clears_pending_save_on_unmount', () => {
    const onSave = vi.fn().mockResolvedValue()
    const { rerender, unmount } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Verify timer is set (save not called yet)
    expect(onSave).not.toHaveBeenCalled()

    // Unmount before timer fires
    unmount()

    // Advance time
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    // Save should not have been called
    expect(onSave).not.toHaveBeenCalled()
  })

  it('test_calls_onSave_with_current_data', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const testData = { id: 1, name: 'Test', tags: ['tag1', 'tag2'] }
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change to specific data
    rerender({ data: testData })

    // Wait for debounce
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // Verify correct data was passed
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith(testData)
  })

  it('test_does_not_save_when_enabled_is_false', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, enabled: false }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Wait for debounce time
    await act(async () => {
      vi.advanceTimersByTime(2000)
      await Promise.resolve()
    })

    // Save should not have been called
    expect(onSave).not.toHaveBeenCalled()

    // Try saveNow as well
    await act(async () => {
      result.current.saveNow()
      await Promise.resolve()
    })

    // Still should not have been called
    expect(onSave).not.toHaveBeenCalled()
  })

  it('test_returns_error_object', async () => {
    const error = new Error('Network error')
    const onSave = vi.fn().mockRejectedValue(error)
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Initially no error
    expect(result.current.error).toBeNull()

    // Change data and trigger save
    rerender({ data: { value: 2 } })

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // Error should be available
    expect(result.current.status).toBe('error')
    expect(result.current.error).toBe(error)
    expect(result.current.error.message).toBe('Network error')
  })

  it('test_clears_error_on_retry', async () => {
    let shouldFail = true
    const onSave = vi.fn().mockImplementation(() => {
      if (shouldFail) {
        return Promise.reject(new Error('First error'))
      }
      return Promise.resolve()
    })

    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // First save that fails
    rerender({ data: { value: 2 } })

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    await act(async () => {
      await Promise.resolve()
    })

    expect(result.current.status).toBe('error')
    expect(result.current.error).not.toBeNull()

    // Second save that succeeds
    shouldFail = false
    rerender({ data: { value: 3 } })

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    await act(async () => {
      await Promise.resolve()
    })

    expect(result.current.status).toBe('saved')
    expect(result.current.error).toBeNull()
  })

  it('test_custom_delay', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 500 }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Should not save at 400ms
    act(() => {
      vi.advanceTimersByTime(400)
    })
    expect(onSave).not.toHaveBeenCalled()

    // Should save at 500ms
    act(() => {
      vi.advanceTimersByTime(100)
    })

    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('test_does_not_save_if_data_unchanged_from_initial', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const initialData = { value: 1 }
    const { result } = renderHook(() =>
      useAutoSave({ data: initialData, onSave })
    )

    // Wait for debounce time
    await act(async () => {
      vi.advanceTimersByTime(2000)
      await Promise.resolve()
    })

    // Should not have saved since data hasn't changed
    expect(onSave).not.toHaveBeenCalled()
    expect(result.current.status).toBe('idle')
  })

  it('test_detects_equality_regardless_of_key_order', async () => {
    // Regression test: JSON.stringify would fail this because key order differs
    const onSave = vi.fn().mockResolvedValue()
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { a: 1, b: 2 } } }
    )

    // Same data but different key order (would fail with JSON.stringify)
    rerender({ data: { b: 2, a: 1 } })

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await Promise.resolve()
    })

    // Should NOT save since data is semantically equal
    expect(onSave).not.toHaveBeenCalled()
  })

  it('test_detects_equality_with_nested_objects_different_key_order', async () => {
    // More complex case with nested objects
    const onSave = vi.fn().mockResolvedValue()
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { outer: { a: 1, b: 2 }, c: 3 } } }
    )

    // Same data but different key order at multiple levels
    rerender({ data: { c: 3, outer: { b: 2, a: 1 } } })

    await act(async () => {
      vi.advanceTimersByTime(2000)
      await Promise.resolve()
    })

    // Should NOT save since data is semantically equal
    expect(onSave).not.toHaveBeenCalled()
  })

  it('test_status_returns_to_idle_after_saved', async () => {
    const onSave = vi.fn().mockResolvedValue()
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave }),
      { initialProps: { data: { value: 1 } } }
    )

    // Change data
    rerender({ data: { value: 2 } })

    // Wait for debounce and save
    act(() => {
      vi.advanceTimersByTime(2000)
    })

    await act(async () => {
      await Promise.resolve()
    })

    // Status should be 'saved'
    expect(result.current.status).toBe('saved')

    // Wait for the status reset timer (1.5 seconds)
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })

    // Status should return to 'idle'
    expect(result.current.status).toBe('idle')
  })
})
