/**
 * GPS Precision Preference Utilities
 *
 * Manages the user's GPS coordinate precision preference stored in localStorage.
 * Used by GPSSettings component and other components that display GPS coordinates.
 */

// GPS Precision options with accuracy descriptions
export const GPS_PRECISION_OPTIONS = [
  { value: 0, label: '0 decimals (±30m)', description: 'Coarse location' },
  { value: 1, label: '1 decimal (±3m)', description: 'City block' },
  { value: 2, label: '2 decimals (±30cm)', description: 'Standard GPS' },
  { value: 3, label: '3 decimals (±3cm)', description: 'High precision' },
  { value: 4, label: '4 decimals (±3mm)', description: 'Survey grade' },
  { value: 5, label: '5 decimals (±0.3mm)', description: 'Scientific' },
  { value: 6, label: '6 decimals (±0.03mm)', description: 'Maximum' },
]

// LocalStorage key for GPS precision preference
const GPS_PRECISION_KEY = 'mothbox_gps_precision'

/**
 * Get stored GPS precision or default to 2 decimal places
 * @returns {number} Precision value (0-6)
 */
export function getGpsPrecision() {
  try {
    const stored = localStorage.getItem(GPS_PRECISION_KEY)
    if (stored !== null) {
      const value = parseInt(stored, 10)
      if (value >= 0 && value <= 6) return value
    }
  } catch {
    // localStorage not available
  }
  return 2 // Default precision
}

/**
 * Set GPS precision preference in localStorage
 * @param {number} precision - Precision value (0-6)
 */
export function setGpsPrecision(precision) {
  try {
    localStorage.setItem(GPS_PRECISION_KEY, String(precision))
  } catch {
    // localStorage not available
  }
}
