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
