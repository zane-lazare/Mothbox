/**
 * Simple UUID v4 generator
 * Uses crypto.randomUUID() when available, falls back to manual generation
 */

/**
 * Generates a random UUID v4 string
 * @returns A UUID v4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")
 */
export function generateUUID(): string {
  // Use native crypto.randomUUID() if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }

  // Fallback implementation for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Generates a short random ID (8 characters)
 * Useful for temporary IDs that don't need full UUID collision resistance
 * @returns A short random ID string
 */
export function generateShortId(): string {
  return Math.random().toString(36).substring(2, 10)
}
