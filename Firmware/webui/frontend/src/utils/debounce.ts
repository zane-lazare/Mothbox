/**
 * Debounce utility for delaying function execution
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Creates a debounced function that delays invoking func until after wait milliseconds
 * have elapsed since the last time the debounced function was invoked.
 *
 * @param func - The function to debounce
 * @param wait - The number of milliseconds to delay
 * @returns A debounced version of the function
 *
 * @example
 * const debouncedSearch = debounce((query: string) => {
 *   performSearch(query)
 * }, 300)
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  return function debounced(...args: Parameters<T>): void {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }

    timeoutId = setTimeout(() => {
      func(...args)
      timeoutId = null
    }, wait)
  }
}

/**
 * Creates a throttled function that only invokes func at most once per every wait milliseconds.
 *
 * @param func - The function to throttle
 * @param wait - The number of milliseconds to throttle
 * @returns A throttled version of the function
 *
 * @example
 * const throttledScroll = throttle(() => {
 *   handleScroll()
 * }, 100)
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  let lastRan: number | null = null

  return function throttled(...args: Parameters<T>): void {
    const now = Date.now()

    if (lastRan === null || now - lastRan >= wait) {
      func(...args)
      lastRan = now
    } else if (timeoutId === null) {
      timeoutId = setTimeout(() => {
        func(...args)
        lastRan = Date.now()
        timeoutId = null
      }, wait - (now - lastRan))
    }
  }
}
