/**
 * Shared utility functions for the Mothbox WebUI
 */

/**
 * Format a Unix timestamp to a localized date/time string
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} Formatted date string or "Never" if timestamp is 0 or invalid
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp || timestamp === 0) return 'Never'
  return new Date(timestamp * 1000).toLocaleString()
}

/**
 * Format an error message with a prefix and fallback
 *
 * Provides consistent error formatting throughout the application by combining
 * a message prefix with the error's message property, falling back to a default
 * when the error message is unavailable.
 *
 * @param {Error|Object|null|undefined} error - Error object with optional message property
 * @param {string} prefix - Message prefix (e.g., "Error loading photos")
 * @param {string} [fallback='An unexpected error occurred'] - Fallback message when error.message is unavailable
 * @returns {string} Formatted error message in the form "prefix: error message"
 *
 * @example
 * // With error object containing message
 * const error = new Error('Network timeout')
 * formatErrorMessage(error, 'Error loading photos')
 * // Returns: "Error loading photos: Network timeout"
 *
 * @example
 * // Without error message (uses fallback)
 * formatErrorMessage({}, 'Error loading photos')
 * // Returns: "Error loading photos: An unexpected error occurred"
 *
 * @example
 * // With custom fallback
 * formatErrorMessage(null, 'Failed to save', 'Unknown error')
 * // Returns: "Failed to save: Unknown error"
 */
export const formatErrorMessage = (error, prefix, fallback = 'An unexpected error occurred') => {
  const errorDetail = error?.message || fallback
  return `${prefix}: ${errorDetail}`
}
