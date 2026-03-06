/**
 * GPS coordinate formatting and conversion utilities.
 *
 * Pure display utilities extracted from the deprecated gpsCoordinates.ts.
 * For validation, use schemas/coordinates.ts (Zod schema).
 *
 * Intentionally omitted from gpsCoordinates.ts (zero consumers):
 * - dmsToDecimal() — no frontend code converts DMS back to decimal
 * - validateCoordinate() — replaced by schemas/coordinates.ts (Zod)
 * - formatCoordinatePair() — no frontend code formats lat+lon as a single string
 */

export interface DMSCoordinate {
  degrees: number
  minutes: number
  seconds: number
  reference: 'N' | 'S' | 'E' | 'W'
}

export type CoordinateFormat = 'dms' | 'decimal' | 'short'

/**
 * Convert decimal degrees to DMS (Degrees, Minutes, Seconds) format.
 */
export function decimalToDMS(
  decimal: number,
  isLatitude: boolean,
  secondsPrecision: number = 2,
): DMSCoordinate {
  if (!Number.isInteger(secondsPrecision) || secondsPrecision < 0 || secondsPrecision > 6) {
    throw new Error(`Invalid secondsPrecision: ${secondsPrecision} (must be integer in range [0, 6])`)
  }
  if (decimal === null || decimal === undefined) {
    throw new Error('Coordinate cannot be null or undefined')
  }
  if (Number.isNaN(decimal)) {
    throw new Error('Coordinate cannot be NaN')
  }
  if (!Number.isFinite(decimal)) {
    throw new Error('Coordinate cannot be infinity')
  }
  if (isLatitude && (decimal < -90 || decimal > 90)) {
    throw new Error(`Invalid latitude: ${decimal} (must be in range [-90, 90])`)
  }
  if (!isLatitude && (decimal < -180 || decimal > 180)) {
    throw new Error(`Invalid longitude: ${decimal} (must be in range [-180, 180])`)
  }

  const reference: 'N' | 'S' | 'E' | 'W' = isLatitude
    ? (decimal >= 0 ? 'N' : 'S')
    : (decimal >= 0 ? 'E' : 'W')

  const decimalAbs = Math.abs(decimal)
  let degrees = Math.floor(decimalAbs)
  const minutesDecimal = (decimalAbs - degrees) * 60
  let minutes = Math.floor(minutesDecimal)
  const multiplier = Math.pow(10, secondsPrecision)
  let seconds = Math.round((minutesDecimal - minutes) * 60 * multiplier) / multiplier

  if (seconds >= 60.0) {
    minutes += 1
    seconds = 0.0
  }
  if (minutes >= 60) {
    degrees += 1
    minutes = 0
  }

  return { degrees, minutes, seconds, reference }
}

/**
 * Format a coordinate for display.
 *
 * @param decimal - Decimal degrees
 * @param isLatitude - True if latitude, false if longitude
 * @param format - 'dms' (37°46'29.64"N), 'decimal' (37.774900°N), or 'short' (37.77°N)
 * @param secondsPrecision - Decimal places for seconds in DMS format (0-6, default 2)
 */
export function formatCoordinateDisplay(
  decimal: number,
  isLatitude: boolean,
  format: CoordinateFormat = 'dms',
  secondsPrecision: number = 2,
): string {
  if (format === 'dms') {
    const { degrees, minutes, seconds, reference } = decimalToDMS(decimal, isLatitude, secondsPrecision)
    return `${degrees}°${minutes}'${seconds.toFixed(secondsPrecision)}"${reference}`
  } else if (format === 'decimal') {
    const reference = isLatitude ? (decimal >= 0 ? 'N' : 'S') : (decimal >= 0 ? 'E' : 'W')
    return `${Math.abs(decimal).toFixed(6)}°${reference}`
  } else if (format === 'short') {
    const reference = isLatitude ? (decimal >= 0 ? 'N' : 'S') : (decimal >= 0 ? 'E' : 'W')
    return `${Math.abs(decimal).toFixed(2)}°${reference}`
  } else {
    throw new Error(`Invalid format: ${format} (must be 'dms', 'decimal', or 'short')`)
  }
}
