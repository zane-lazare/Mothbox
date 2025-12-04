/**
 * Deep equality check for plain objects and arrays
 *
 * Handles: primitives, objects, arrays, null, undefined, Date, NaN
 * Does NOT handle: circular references, Maps, Sets, RegExp, functions
 *
 * This is a lightweight alternative to lodash.isEqual, suitable for
 * comparing metadata objects in the useAutoSave hook.
 *
 * @param {*} a - First value to compare
 * @param {*} b - Second value to compare
 * @returns {boolean} True if values are deeply equal
 */
export default function deepEqual(a, b) {
  // Same reference or both primitive equal
  if (a === b) return true

  // Handle null/undefined
  if (a == null || b == null) return a === b

  // Handle NaN (NaN !== NaN in JS)
  if (Number.isNaN(a) && Number.isNaN(b)) return true

  // Handle Date objects
  if (a instanceof Date && b instanceof Date) {
    return a.getTime() === b.getTime()
  }

  // Must both be objects after this point
  if (typeof a !== 'object' || typeof b !== 'object') return false

  // Handle arrays
  if (Array.isArray(a) !== Array.isArray(b)) return false
  if (Array.isArray(a)) {
    if (a.length !== b.length) return false
    return a.every((item, i) => deepEqual(item, b[i]))
  }

  // Handle plain objects
  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  if (keysA.length !== keysB.length) return false

  return keysA.every(key =>
    Object.prototype.hasOwnProperty.call(b, key) && deepEqual(a[key], b[key])
  )
}
