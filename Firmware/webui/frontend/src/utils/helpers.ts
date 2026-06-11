/**
 * Shared utility functions for the Mothbox WebUI
 */

/**
 * Format a Unix timestamp to a localized date/time string
 * @param timestamp - Unix timestamp in seconds
 * @returns Formatted date string or "Never" if timestamp is 0 or invalid
 */
export function formatTimestamp(timestamp: number): string {
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
 * @param error - Error object with optional message property
 * @param prefix - Message prefix (e.g., "Error loading photos")
 * @param fallback - Fallback message when error.message is unavailable
 * @returns Formatted error message in the form "prefix: error message"
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
export function formatErrorMessage(
  error: unknown,
  prefix: string,
  fallback = 'An unexpected error occurred'
): string {
  const errorDetail =
    error && typeof error === 'object' && 'message' in error
      ? String(error.message)
      : fallback
  return `${prefix}: ${errorDetail}`
}

/**
 * Format an ISO date string for display
 *
 * Converts an ISO 8601 date string to a localized date/time string with
 * a short month format. Returns the original string if parsing fails.
 *
 * @param isoDate - ISO date string (e.g., "2024-03-15T14:30:00Z")
 * @returns Formatted date string (e.g., "Mar 15, 2024, 02:30 PM")
 *
 * @example
 * formatDate('2024-03-15T14:30:00Z')
 * // Returns: "Mar 15, 2024, 02:30 PM"
 */
export function formatDate(isoDate: string): string {
  try {
    const date = new Date(isoDate)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoDate
  }
}

/**
 * Format file size in bytes to human-readable format
 *
 * Converts a byte count to KB or MB based on size, returning null
 * for invalid/missing values.
 *
 * @param bytes - File size in bytes
 * @returns Formatted size (e.g., "1.5 MB", "512.3 KB") or null if bytes is falsy
 *
 * @example
 * formatSize(1536000)  // Returns: "1.5 MB"
 * formatSize(512000)   // Returns: "500.0 KB"
 * formatSize(0)        // Returns: null
 */
export function formatSize(bytes: number): string | null {
  if (!bytes) return null

  const kb = bytes / 1024
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`
  }

  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

/**
 * Get moth icon fallback image as data URI
 *
 * Returns a data URI containing an SVG moth icon for use as a fallback
 * when photo thumbnails fail to load. This is thematically appropriate
 * for the Mothbox insect photography system.
 *
 * @returns Data URI string containing the moth SVG
 *
 * @example
 * <img src={url} onError={(e) => { e.target.src = getMothFallbackIcon() }} />
 */
export function getMothFallbackIcon(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect fill="#e5e7eb" width="200" height="200"/>
    <g transform="translate(100, 100)">
      <ellipse cx="-35" cy="0" rx="30" ry="40" fill="#9ca3af" opacity="0.7" transform="rotate(-15 -35 0)"/>
      <ellipse cx="35" cy="0" rx="30" ry="40" fill="#9ca3af" opacity="0.7" transform="rotate(15 35 0)"/>
      <circle cx="-35" cy="-5" r="6" fill="#6b7280" opacity="0.5"/>
      <circle cx="-35" cy="8" r="4" fill="#6b7280" opacity="0.5"/>
      <circle cx="35" cy="-5" r="6" fill="#6b7280" opacity="0.5"/>
      <circle cx="35" cy="8" r="4" fill="#6b7280" opacity="0.5"/>
      <ellipse cx="0" cy="0" rx="8" ry="25" fill="#6b7280"/>
      <circle cx="0" cy="-22" r="6" fill="#6b7280"/>
      <path d="M -2,-26 Q -8,-35 -10,-42" stroke="#6b7280" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      <path d="M 2,-26 Q 8,-35 10,-42" stroke="#6b7280" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    </g>
    <text x="50%" y="85%" text-anchor="middle" fill="#6b7280" font-size="12" font-family="system-ui, -apple-system, sans-serif">Image Unavailable</text>
  </svg>`

  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
