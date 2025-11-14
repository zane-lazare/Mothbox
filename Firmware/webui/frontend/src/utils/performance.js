/**
 * Performance Utilities
 *
 * Debounce and throttle functions for optimizing event handlers
 */

/**
 * Debounce function - delays execution until after wait time has elapsed since last call
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Milliseconds to wait before executing
 * @returns {Function} Debounced function with cancel method
 */
export function debounce(func, wait) {
  let timeoutId = null

  const debouncedFunc = function (...args) {
    // Clear existing timeout
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }

    // Set new timeout
    timeoutId = setTimeout(() => {
      func.apply(this, args)
      timeoutId = null
    }, wait)
  }

  // Add cancel method
  debouncedFunc.cancel = function () {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return debouncedFunc
}

/**
 * Throttle function - limits execution to once per time period
 * Executes immediately on first call, then throttles subsequent calls
 *
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum milliseconds between executions
 * @returns {Function} Throttled function with cancel method
 */
export function throttle(func, limit) {
  let lastRan = 0
  let timeoutId = null
  let lastArgs = null
  let lastContext = null

  const throttledFunc = function (...args) {
    lastArgs = args
    lastContext = this

    const now = Date.now()

    // If enough time has passed since last execution, execute immediately
    if (now - lastRan >= limit) {
      func.apply(lastContext, lastArgs)
      lastRan = now
      lastArgs = null
      lastContext = null
    } else {
      // Otherwise, schedule execution for when the throttle period expires
      if (timeoutId === null) {
        timeoutId = setTimeout(() => {
          if (lastArgs !== null) {
            func.apply(lastContext, lastArgs)
            lastRan = Date.now()
            lastArgs = null
            lastContext = null
          }
          timeoutId = null
        }, limit - (now - lastRan))
      }
    }
  }

  // Add cancel method
  throttledFunc.cancel = function () {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    lastArgs = null
    lastContext = null
  }

  return throttledFunc
}
