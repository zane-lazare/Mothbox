import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { debounce, throttle } from '../performance'

describe('performance utilities', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('debounce', () => {
    it('delays function execution', () => {
      const func = vi.fn()
      const debouncedFunc = debounce(func, 300)

      debouncedFunc()

      // Should not call immediately
      expect(func).not.toHaveBeenCalled()

      // Fast-forward time
      vi.advanceTimersByTime(299)
      expect(func).not.toHaveBeenCalled()

      vi.advanceTimersByTime(1)
      expect(func).toHaveBeenCalledTimes(1)
    })

    it('only calls once after rapid calls', () => {
      const func = vi.fn()
      const debouncedFunc = debounce(func, 300)

      // Rapid calls
      debouncedFunc()
      debouncedFunc()
      debouncedFunc()
      debouncedFunc()
      debouncedFunc()

      // Should not call yet
      expect(func).not.toHaveBeenCalled()

      // Fast-forward time
      vi.advanceTimersByTime(300)

      // Should only call once
      expect(func).toHaveBeenCalledTimes(1)
    })

    it('restarts timer on new calls', () => {
      const func = vi.fn()
      const debouncedFunc = debounce(func, 300)

      debouncedFunc()
      vi.advanceTimersByTime(200)

      // Call again, should restart timer
      debouncedFunc()
      vi.advanceTimersByTime(200)
      expect(func).not.toHaveBeenCalled()

      // Complete the new delay
      vi.advanceTimersByTime(100)
      expect(func).toHaveBeenCalledTimes(1)
    })

    it('passes arguments correctly', () => {
      const func = vi.fn()
      const debouncedFunc = debounce(func, 300)

      debouncedFunc('arg1', 'arg2', { key: 'value' })
      vi.advanceTimersByTime(300)

      expect(func).toHaveBeenCalledWith('arg1', 'arg2', { key: 'value' })
    })

    it('cancels pending calls on cleanup', () => {
      const func = vi.fn()
      const debouncedFunc = debounce(func, 300)

      debouncedFunc()

      // Cancel the debounced call
      debouncedFunc.cancel()
      vi.advanceTimersByTime(300)

      expect(func).not.toHaveBeenCalled()
    })
  })

  describe('throttle', () => {
    it('limits call frequency', () => {
      const func = vi.fn()
      const throttledFunc = throttle(func, 100)

      // Rapid calls
      throttledFunc() // t=0 (should execute)
      throttledFunc() // t=0 (should be throttled)
      throttledFunc() // t=0 (should be throttled)

      expect(func).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(50)
      throttledFunc() // t=50 (should be throttled)
      expect(func).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(50)
      throttledFunc() // t=100 (should execute)
      expect(func).toHaveBeenCalledTimes(2)
    })

    it('allows first call immediately', () => {
      const func = vi.fn()
      const throttledFunc = throttle(func, 100)

      throttledFunc()

      // First call should execute immediately
      expect(func).toHaveBeenCalledTimes(1)
    })

    it('executes trailing call after limit expires', () => {
      const func = vi.fn()
      const throttledFunc = throttle(func, 100)

      throttledFunc() // t=0 (executes immediately)
      expect(func).toHaveBeenCalledTimes(1)

      throttledFunc() // t=0 (throttled)
      throttledFunc() // t=0 (throttled)

      // Wait for throttle period to expire
      vi.advanceTimersByTime(100)

      // Trailing call should execute
      expect(func).toHaveBeenCalledTimes(2)
    })

    it('passes arguments correctly', () => {
      const func = vi.fn()
      const throttledFunc = throttle(func, 100)

      throttledFunc('arg1', 'arg2', { key: 'value' })

      expect(func).toHaveBeenCalledWith('arg1', 'arg2', { key: 'value' })
    })

    it('cancels pending calls on cleanup', () => {
      const func = vi.fn()
      const throttledFunc = throttle(func, 100)

      throttledFunc() // Immediate execution
      throttledFunc() // Scheduled for trailing execution

      expect(func).toHaveBeenCalledTimes(1)

      // Cancel the throttled call
      throttledFunc.cancel()
      vi.advanceTimersByTime(100)

      // Should not execute trailing call
      expect(func).toHaveBeenCalledTimes(1)
    })
  })
})
