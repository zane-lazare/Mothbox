/**
 * Metadata Formatters Utility Module
 *
 * Provides formatting functions for displaying photo metadata (EXIF, GPS, file info)
 * in human-readable formats.
 */

/**
 * Threshold for determining if a timestamp is in seconds or milliseconds.
 * Unix timestamps in seconds are typically < 10000000000 (Sep 9, 2001).
 * Milliseconds timestamps are >= 10000000000.
 * This represents approximately 316 years after Unix epoch (1970).
 */
const TIMESTAMP_MILLISECONDS_THRESHOLD = 10000000000

interface DMSComponents {
  degrees: number
  minutes: number
  seconds: number
}

/**
 * Converts decimal degrees to Degrees, Minutes, Seconds (DMS) format.
 *
 * @param decimal - Decimal degrees (positive or negative)
 * @returns DMS components
 *
 * @example
 * decimalToDMS(34.0522) // { degrees: 34, minutes: 3, seconds: 7.92 }
 */
export function decimalToDMS(decimal: number): DMSComponents {
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
 * @param value - Decimal coordinate value
 * @param type - Coordinate type ('lat' for latitude, 'lon' for longitude)
 * @returns Formatted GPS coordinate (e.g., "34°03'08.0\" N") or "N/A" if invalid
 *
 * @example
 * formatGPSCoordinate(34.0522, 'lat') // "34°03'08.0\" N"
 * formatGPSCoordinate(-118.2437, 'lon') // "118°14'37.3\" W"
 */
export function formatGPSCoordinate(
  value: number | null | undefined,
  type: 'lat' | 'lon'
): string {
  if (
    value === null ||
    value === undefined ||
    isNaN(value) ||
    !type ||
    (type !== 'lat' && type !== 'lon')
  ) {
    return 'N/A'
  }

  const dms = decimalToDMS(value)
  const direction =
    type === 'lat' ? (value >= 0 ? 'N' : 'S') : value >= 0 ? 'E' : 'W'

  return `${dms.degrees}°${String(dms.minutes).padStart(2, '0')}'${String(dms.seconds.toFixed(1)).padStart(4, '0')}" ${direction}`
}

/**
 * Formats decimal GPS coordinates with consistent precision.
 *
 * @param value - Decimal coordinate value (latitude or longitude)
 * @returns Formatted coordinate with 6 decimal places (~0.11m precision) or "N/A" if invalid
 *
 * @example
 * formatDecimalCoordinate(34.052235) // "34.052235"
 * formatDecimalCoordinate(-118.243683) // "-118.243683"
 * formatDecimalCoordinate(null) // "N/A"
 */
export function formatDecimalCoordinate(
  value: number | null | undefined
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A'
  }
  // 6 decimal places provides ~0.11m precision for GPS coordinates
  return value.toFixed(6)
}

/**
 * Formats altitude in meters.
 *
 * @param value - Altitude in meters
 * @returns Formatted altitude (e.g., "1234.5 m") or "N/A" if invalid
 *
 * @example
 * formatAltitude(1234.5) // "1234.5 m"
 * formatAltitude(-123.4) // "-123.4 m"
 */
export function formatAltitude(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A'
  }
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `${formatted} m`
}

/**
 * Formats exposure time as either fractional seconds or decimal seconds.
 *
 * @param value - Exposure time in seconds
 * @returns Formatted exposure time (e.g., "1/200s" or "2.5s") or "N/A" if invalid
 *
 * @example
 * formatExposureTime(0.005) // "1/200s"
 * formatExposureTime(2.5) // "2.5s"
 */
export function formatExposureTime(value: number | null | undefined): string {
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
 * @param value - Aperture f-number
 * @returns Formatted aperture (e.g., "f/2.8") or "N/A" if invalid
 *
 * @example
 * formatAperture(2.8) // "f/2.8"
 * formatAperture(8) // "f/8"
 */
export function formatAperture(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `f/${formatted}`
}

/**
 * Formats ISO sensitivity value.
 *
 * @param value - ISO sensitivity value
 * @returns Formatted ISO (e.g., "ISO 800") or "N/A" if invalid
 *
 * @example
 * formatISO(800) // "ISO 800"
 * formatISO(100) // "ISO 100"
 */
export function formatISO(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  return `ISO ${Math.round(value)}`
}

/**
 * Formats focal length in millimeters.
 *
 * @param value - Focal length in mm
 * @returns Formatted focal length (e.g., "50mm") or "N/A" if invalid
 *
 * @example
 * formatFocalLength(50) // "50mm"
 * formatFocalLength(24.5) // "24.5mm"
 */
export function formatFocalLength(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value) || value <= 0) {
    return 'N/A'
  }
  const formatted = value % 1 === 0 ? value.toString() : value.toFixed(1)
  return `${formatted}mm`
}

/**
 * Formats timestamp as localized date/time string.
 *
 * @param value - Unix timestamp (seconds), ISO string, or Date object
 * @returns Formatted date/time string or "N/A" if invalid
 *
 * @example
 * formatTimestamp(1698768000) // "10/31/2023, 12:00:00 PM" (locale-dependent)
 * formatTimestamp('2023-10-31T12:00:00Z') // "10/31/2023, 12:00:00 PM" (locale-dependent)
 */
export function formatTimestamp(
  value: number | string | Date | null | undefined
): string {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }

  let date: Date

  if (value instanceof Date) {
    date = value
  } else if (typeof value === 'number') {
    // Handle both seconds and milliseconds timestamps
    date = new Date(
      value < TIMESTAMP_MILLISECONDS_THRESHOLD ? value * 1000 : value
    )
  } else if (typeof value === 'string') {
    date = new Date(value)
  } else {
    return 'N/A'
  }

  if (isNaN(date.getTime())) {
    return 'N/A'
  }

  return date.toLocaleString()
}

/**
 * Formats file size in human-readable units (B, KB, MB, GB, TB).
 *
 * @param bytes - File size in bytes
 * @returns Formatted file size (e.g., "1.5 MB") or "N/A" if invalid
 *
 * @example
 * formatFileSize(1024) // "1.0 KB"
 * formatFileSize(1048576) // "1.0 MB"
 * formatFileSize(500) // "500 B"
 */
export function formatFileSize(bytes: number | null | undefined): string {
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
