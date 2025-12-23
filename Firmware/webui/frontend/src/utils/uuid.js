/**
 * UUID generation utility with fallback support
 *
 * Provides cross-environment UUID generation that works in:
 * - Modern browsers with crypto.randomUUID()
 * - Older browsers with crypto.getRandomValues()
 * - Test environments (happy-dom, jsdom)
 * - Any JavaScript environment as last resort
 *
 * @module utils/uuid
 */

/**
 * Generate a UUID v4 string
 *
 * Uses the most secure method available in the current environment:
 * 1. crypto.randomUUID() - Native, most secure (modern browsers/Node 15.7+)
 * 2. crypto.getRandomValues() - Cryptographically secure fallback
 * 3. Math.random() - Last resort (not cryptographically secure)
 *
 * @returns {string} A UUID v4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")
 *
 * @example
 * import { generateUUID } from '../utils/uuid'
 * const id = generateUUID() // "550e8400-e29b-41d4-a716-446655440000"
 */
export function generateUUID() {
  // Use native crypto.randomUUID if available (modern browsers, Node 15.7+)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  // Fallback: Use crypto.getRandomValues (broader browser support)
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    // RFC 4122 version 4 UUID
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) =>
      (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
    )
  }

  // Last resort fallback: Math.random (not cryptographically secure, but works everywhere)
  // This should only be hit in very old/unusual environments
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
