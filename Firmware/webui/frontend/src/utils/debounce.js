/**
 * Debounce utility for delaying function execution
 *
 * Creates a debounced version of the provided function that delays execution
 * until after `delay` milliseconds have elapsed since the last invocation.
 * Useful for optimizing performance of high-frequency events (resize, scroll, input).
 *
 * @module utils/debounce
 */

/**
 * Debounce a function to delay execution until after a specified delay
 *
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function with optional cancel() method
 *
 * @example
 * // Basic usage
 * const debouncedResize = debounce(() => {
 *   console.log('Window resized');
 * }, 150);
 * window.addEventListener('resize', debouncedResize);
 *
 * @example
 * // With cleanup
 * const debouncedFn = debounce(expensiveOperation, 300);
 * window.addEventListener('scroll', debouncedFn);
 * // Later, in cleanup:
 * window.removeEventListener('scroll', debouncedFn);
 * debouncedFn.cancel(); // Cancel any pending execution
 */
export function debounce(fn, delay) {
  let timeoutId = null;

  const debounced = function debounced(...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, delay);
  };

  // Provide cancel method for cleanup
  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  return debounced;
}
