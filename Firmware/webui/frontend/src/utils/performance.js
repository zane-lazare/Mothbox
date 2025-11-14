/**
 * Performance Utilities
 *
 * Debounce and throttle functions for optimizing event handlers.
 * Prevents excessive function calls from high-frequency events like
 * scroll, resize, mousemove, and touchmove.
 */

/**
 * Debounces a function call, delaying execution until after wait milliseconds
 * have elapsed since the last invocation.
 *
 * Useful for expensive operations that should only run after user has stopped
 * an action (e.g., resize handlers, search input, autosave).
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Delay in milliseconds before executing
 * @returns {Function} Debounced function with cancel() method
 *
 * @example
 * // Debounce resize handler
 * const debouncedResize = debounce(() => {
 *   console.log('Window resized!', window.innerWidth)
 * }, 300)
 *
 * window.addEventListener('resize', debouncedResize)
 *
 * // Cleanup
 * window.removeEventListener('resize', debouncedResize)
 * debouncedResize.cancel()
 *
 * @example
 * // Debounce search input
 * const debouncedSearch = debounce((query) => {
 *   fetch(`/api/search?q=${query}`)
 * }, 500)
 *
 * <input onChange={(e) => debouncedSearch(e.target.value)} />
 */
export function debounce(func, wait) {
  let timeoutId = null
  let pendingArgs = null
  let pendingContext = null

  const debouncedFunc = function (...args) {
    // Store context and args
    pendingContext = this
    pendingArgs = args

    // Clear existing timeout
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }

    // Set new timeout
    timeoutId = setTimeout(() => {
      func.apply(pendingContext, pendingArgs)
      timeoutId = null
      // Clear references after execution
      pendingArgs = null
      pendingContext = null
    }, wait)
  }

  // Add cancel method
  debouncedFunc.cancel = function () {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    // Clear pending references to help garbage collection
    pendingArgs = null
    pendingContext = null
  }

  return debouncedFunc
}

/**
 * Throttles a function call, limiting execution to once per limit milliseconds.
 * Executes immediately on first call, then enforces minimum time between calls.
 *
 * Useful for expensive operations that should run at most once per time period
 * (e.g., scroll handlers, mousemove tracking, animation frames).
 *
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum time between calls in milliseconds
 * @returns {Function} Throttled function with cancel() method
 *
 * @example
 * // Throttle scroll handler to run at most every 100ms
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll position:', window.scrollY)
 * }, 100)
 *
 * window.addEventListener('scroll', throttledScroll)
 *
 * // Cleanup
 * window.removeEventListener('scroll', throttledScroll)
 * throttledScroll.cancel()
 *
 * @example
 * // Throttle mousemove tracking
 * const throttledTrack = throttle((e) => {
 *   console.log('Mouse at:', e.clientX, e.clientY)
 * }, 50)
 *
 * <div onMouseMove={throttledTrack} />
 *
 * @difference Debounce vs Throttle
 * - Debounce: Waits until action stops, then executes once
 * - Throttle: Executes at regular intervals while action is ongoing
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
