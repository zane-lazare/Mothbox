/**
 * Deep equality comparison utility
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Performs a deep equality check between two values
 * Handles objects, arrays, dates, and primitive types
 *
 * @param a - First value to compare
 * @param b - Second value to compare
 * @returns True if values are deeply equal, false otherwise
 *
 * @example
 * deepEqual({ a: 1, b: { c: 2 } }, { a: 1, b: { c: 2 } }) // true
 * deepEqual([1, 2, 3], [1, 2, 3]) // true
 * deepEqual(new Date('2024-01-01'), new Date('2024-01-01')) // true
 */
export function deepEqual(a: any, b: any): boolean {
  // Handle null and undefined
  if (a === b) return true
  if (a == null || b == null) return false
  if (a !== a && b !== b) return true // NaN === NaN

  // Handle different types
  if (typeof a !== typeof b) return false

  // Handle primitives
  if (typeof a !== 'object') return a === b

  // Handle Date objects
  if (a instanceof Date && b instanceof Date) {
    return a.getTime() === b.getTime()
  }

  // Handle arrays
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    return a.every((item, index) => deepEqual(item, b[index]))
  }

  // Handle objects
  if (Array.isArray(a) !== Array.isArray(b)) return false

  const keysA = Object.keys(a)
  const keysB = Object.keys(b)

  if (keysA.length !== keysB.length) return false

  return keysA.every((key) => {
    if (!Object.prototype.hasOwnProperty.call(b, key)) return false
    return deepEqual(a[key], b[key])
  })
}
