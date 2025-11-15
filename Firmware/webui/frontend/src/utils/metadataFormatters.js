/**
 * Metadata Formatters Utility Module
 *
 * Provides formatting functions for displaying photo metadata (EXIF, GPS, file info)
 * in human-readable formats.
 */

/**
 * Converts decimal degrees to Degrees, Minutes, Seconds (DMS) format.
 *
 * @param {number} decimal - Decimal degrees (positive or negative)
 * @returns {{degrees: number, minutes: number, seconds: number}} DMS components
 *
 * @example
 * decimalToDMS(34.0522) // { degrees: 34, minutes: 3, seconds: 7.92 }
 */
export function decimalToDMS(decimal) {
  const absolute = Math.abs(decimal)
  const degrees = Math.floor(absolute)
  const minutesDecimal = (absolute - degrees) * 60
  const minutes = Math.floor(minutesDecimal)
  const seconds = (minutesDecimal - minutes) * 60

  return {
    degrees,
    minutes,
    seconds,
  }
}

/**
 * Formats GPS coordinates in DMS format with cardinal direction.
 *
 * @param {number} value - Decimal coordinate value
 * @param {'lat'|'lon'} type - Coordinate type ('lat' for latitude, 'lon' for longitude)
 * @returns {string} Formatted GPS coordinate (e.g., "34°03'08.0\" N") or "N/A" if invalid
 *
 * @example
 * formatGPSCoordinate(34.0522, 'lat') // "34°03'08.0\" N"
 * formatGPSCoordinate(-118.2437, 'lon') // "118°14'37.3\" W"
 */
export function formatGPSCoordinate(value, type) {
  // Validate input
  if (
    value === null ||
    value === undefined ||
    isNaN(value) ||
    !type ||
    typeof type !== 'string' ||
    (type !== 'lat' && type !== 'lon')
  ) {
    return 'N/A'
  }

  const dms = decimalToDMS(value)
  const direction = type === 'lat'
    ? (value >= 0 ? 'N' : 'S')
    : (value >= 0 ? 'E' : 'W')

  return `${dms.degrees}°${String(dms.minutes).padStart(2, '0')}'${String(dms.seconds.toFixed(1)).padStart(4, '0')}" ${direction}`
}

/**
 * Formats altitude in meters.
 *
 * @param {number} value - Altitude in meters
 * @returns {string} Formatted altitude (e.g., "1234.5 m") or "N/A" if invalid
 *
 * @example
 * formatAltitude(1234.5) // "1234.5 m"
 * formatAltitude(-123.4) // "-123.4 m"
 */
export function formatAltitude(value) {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A'
  }
  // Don't show decimal for whole numbers
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `${formatted} m`
}

/**
 * Formats exposure time as either fractional seconds or decimal seconds.
 *
 * @param {number} value - Exposure time in seconds
 * @returns {string} Formatted exposure time (e.g., "1/200s" or "2.5s") or "N/A" if invalid
 *
 * @example
 * formatExposureTime(0.005) // "1/200s"
 * formatExposureTime(2.5) // "2.5s"
 */
export function formatExposureTime(value) {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }

  if (value < 1) {
    const denominator = Math.round(1 / value)
    return `1/${denominator}s`
  }

  return `${value}s`
}

/**
 * Formats aperture value with f-stop notation.
 *
 * @param {number} value - Aperture f-number
 * @returns {string} Formatted aperture (e.g., "f/2.8") or "N/A" if invalid
 *
 * @example
 * formatAperture(2.8) // "f/2.8"
 * formatAperture(8) // "f/8"
 */
export function formatAperture(value) {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  // Don't show decimal for whole numbers
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `f/${formatted}`
}

/**
 * Formats ISO sensitivity value.
 *
 * @param {number} value - ISO sensitivity value
 * @returns {string} Formatted ISO (e.g., "ISO 800") or "N/A" if invalid
 *
 * @example
 * formatISO(800) // "ISO 800"
 * formatISO(100) // "ISO 100"
 */
export function formatISO(value) {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  return `ISO ${Math.round(value)}`
}

/**
 * Formats focal length in millimeters.
 *
 * @param {number} value - Focal length in mm
 * @returns {string} Formatted focal length (e.g., "50mm") or "N/A" if invalid
 *
 * @example
 * formatFocalLength(50) // "50mm"
 * formatFocalLength(24.5) // "24.5mm"
 */
export function formatFocalLength(value) {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  // Don't show decimal for whole numbers
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `${formatted}mm`
}

/**
 * Formats timestamp as localized date/time string.
 *
 * @param {number|string|Date} value - Unix timestamp (seconds), ISO string, or Date object
 * @returns {string} Formatted date/time string or "N/A" if invalid
 *
 * @example
 * formatTimestamp(1698768000) // "10/31/2023, 12:00:00 PM" (locale-dependent)
 * formatTimestamp('2023-10-31T12:00:00Z') // "10/31/2023, 12:00:00 PM" (locale-dependent)
 */
export function formatTimestamp(value) {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }

  let date

  if (value instanceof Date) {
    date = value
  } else if (typeof value === 'number') {
    // Handle both seconds and milliseconds timestamps
    // Unix timestamps in seconds are typically < 10000000000
    // Milliseconds timestamps are >= 10000000000
    date = new Date(value < 10000000000 ? value * 1000 : value)
  } else if (typeof value === 'string') {
    date = new Date(value)
  } else {
    return 'N/A'
  }

  // Check if date is valid
  if (isNaN(date.getTime())) {
    return 'N/A'
  }

  return date.toLocaleString()
}

/**
 * Formats file size in human-readable units (B, KB, MB, GB, TB).
 *
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size (e.g., "1.5 MB") or "N/A" if invalid
 *
 * @example
 * formatFileSize(1024) // "1.0 KB"
 * formatFileSize(1048576) // "1.0 MB"
 * formatFileSize(500) // "500 B"
 */
export function formatFileSize(bytes) {
  if (bytes === null || bytes === undefined || isNaN(bytes) || bytes < 0) {
    return 'N/A'
  }

  if (bytes === 0) {
    return '0 B'
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  if (i === 0) {
    return `${bytes} B`
  }

  const size = bytes / Math.pow(k, i)
  return `${size.toFixed(1)} ${units[i]}`
}
