/**
 * GPS coordinate conversion and formatting utilities.
 *
 * @deprecated Will be replaced by Zod schemas in src/schemas/coordinates.ts
 * during Phase 1 of the form validation standardization (#197). Do not add new imports.
 *
 * This module provides utilities for converting between decimal degrees and
 * DMS (Degrees, Minutes, Seconds) format, validating GPS coordinates, and
 * formatting coordinates for display.
 *
 * These utilities are designed for web UI display and match the behavior of
 * the Python backend implementation in webui/backend/utils/gps_coordinates.py.
 */

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * DMS (Degrees, Minutes, Seconds) coordinate representation.
 */
export interface DMSCoordinate {
  /** Whole degrees (0-180, always positive) */
  degrees: number;
  /** Whole minutes (0-59) */
  minutes: number;
  /** Decimal seconds (0.0-59.999...) */
  seconds: number;
  /** Hemisphere reference ('N'/'S' for latitude, 'E'/'W' for longitude) */
  reference: 'N' | 'S' | 'E' | 'W';
}

/**
 * Coordinate validation result.
 */
export interface CoordinateValidation {
  /** True if coordinate is valid, false otherwise */
  isValid: boolean;
  /** Error message if validation failed */
  error?: string;
}

/**
 * Coordinate format options for display.
 */
export type CoordinateFormat = 'dms' | 'decimal' | 'short';

/**
 * Coordinate type for validation.
 */
export type CoordinateType = 'latitude' | 'longitude';

// ============================================================================
// Core Conversion Functions
// ============================================================================

/**
 * Convert decimal degrees to DMS format.
 *
 * @param decimal - Decimal degrees (e.g., 37.7749 or -122.4194)
 * @param isLatitude - True if latitude, False if longitude
 * @param secondsPrecision - Number of decimal places for seconds (0-6, default 2)
 * @returns DMS coordinate with degrees, minutes, seconds, and reference
 * @throws Error if coordinate is invalid (out of range, NaN, infinity) or secondsPrecision is invalid
 *
 * @example
 * ```typescript
 * decimalToDMS(37.7749, true);
 * // Returns: { degrees: 37, minutes: 46, seconds: 29.64, reference: 'N' }
 *
 * decimalToDMS(-122.4194, false);
 * // Returns: { degrees: 122, minutes: 25, seconds: 9.84, reference: 'W' }
 *
 * decimalToDMS(37.7749, true, 4);
 * // Returns: { degrees: 37, minutes: 46, seconds: 29.6400, reference: 'N' }
 * ```
 */
export function decimalToDMS(
  decimal: number,
  isLatitude: boolean,
  secondsPrecision: number = 2
): DMSCoordinate {
  // 0. Validate secondsPrecision
  if (!Number.isInteger(secondsPrecision) || secondsPrecision < 0 || secondsPrecision > 6) {
    throw new Error(
      `Invalid secondsPrecision: ${secondsPrecision} (must be integer in range [0, 6])`
    );
  }

  // 1. Validate input is not null/undefined
  if (decimal === null || decimal === undefined) {
    throw new Error('Coordinate cannot be null or undefined');
  }

  // 2. Validate input is not NaN
  if (Number.isNaN(decimal)) {
    throw new Error('Coordinate cannot be NaN');
  }

  // 3. Validate input is not infinity
  if (!Number.isFinite(decimal)) {
    throw new Error('Coordinate cannot be infinity');
  }

  // 4. Validate coordinate range
  if (isLatitude) {
    if (decimal < -90 || decimal > 90) {
      throw new Error(`Invalid latitude: ${decimal} (must be in range [-90, 90])`);
    }
  } else {
    if (decimal < -180 || decimal > 180) {
      throw new Error(`Invalid longitude: ${decimal} (must be in range [-180, 180])`);
    }
  }

  // 5. Determine reference direction (N/S for latitude, E/W for longitude)
  const reference: 'N' | 'S' | 'E' | 'W' = isLatitude
    ? (decimal >= 0 ? 'N' : 'S')
    : (decimal >= 0 ? 'E' : 'W');

  // 6. Work with absolute value (sign is captured in reference)
  const decimalAbs = Math.abs(decimal);

  // 7. Extract degrees (integer part)
  let degrees = Math.floor(decimalAbs);

  // 8. Extract minutes (fractional part * 60)
  const minutesDecimal = (decimalAbs - degrees) * 60;
  let minutes = Math.floor(minutesDecimal);

  // 9. Extract seconds (remaining fractional minutes * 60)
  const secondsDecimal = (minutesDecimal - minutes) * 60;

  // 10. Round to specified precision
  const multiplier = Math.pow(10, secondsPrecision);
  let seconds = Math.round(secondsDecimal * multiplier) / multiplier;

  // 11. Handle seconds overflow (rounding 59.995 -> 60.00)
  if (seconds >= 60.0) {
    minutes += 1;
    seconds = 0.0;
  }

  // 12. Handle minutes overflow (59 minutes + 1 -> 60 minutes)
  if (minutes >= 60) {
    degrees += 1;
    minutes = 0;
  }

  return { degrees, minutes, seconds, reference };
}

/**
 * Convert DMS format to decimal degrees.
 *
 * @param degrees - Degrees (0-180, always positive)
 * @param minutes - Minutes (0-59)
 * @param seconds - Seconds (0.0-59.999...)
 * @param reference - Reference direction ('N', 'S', 'E', or 'W')
 * @returns Decimal degrees (positive for N/E, negative for S/W)
 * @throws Error if reference is invalid
 *
 * @example
 * ```typescript
 * dmsToDecimal(37, 46, 29.64, 'N');
 * // Returns: 37.7749
 *
 * dmsToDecimal(122, 25, 9.84, 'W');
 * // Returns: -122.4194
 * ```
 */
export function dmsToDecimal(
  degrees: number,
  minutes: number,
  seconds: number,
  reference: 'N' | 'S' | 'E' | 'W'
): number {
  // 1. Validate reference
  if (!['N', 'S', 'E', 'W'].includes(reference)) {
    throw new Error(`Invalid reference: ${reference} (must be 'N', 'S', 'E', or 'W')`);
  }

  // 2. Convert to decimal
  let decimal = degrees + (minutes / 60.0) + (seconds / 3600.0);

  // 3. Apply sign based on reference
  if (reference === 'S' || reference === 'W') {
    decimal = -decimal;
  }

  return decimal;
}

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate a GPS coordinate.
 *
 * @param value - Decimal degrees to validate
 * @param coordType - Type of coordinate ('latitude' or 'longitude')
 * @returns Validation result with isValid flag and optional error message
 *
 * @example
 * ```typescript
 * validateCoordinate(37.7749, 'latitude');
 * // Returns: { isValid: true }
 *
 * validateCoordinate(91.0, 'latitude');
 * // Returns: { isValid: false, error: 'Invalid latitude: 91 (must be in range [-90, 90])' }
 * ```
 */
export function validateCoordinate(
  value: number,
  coordType: CoordinateType
): CoordinateValidation {
  const isLatitude = coordType === 'latitude';

  // Check for null/undefined
  if (value === null || value === undefined) {
    return {
      isValid: false,
      error: 'Coordinate cannot be null or undefined',
    };
  }

  // Check for NaN
  if (Number.isNaN(value)) {
    return {
      isValid: false,
      error: 'Coordinate cannot be NaN',
    };
  }

  // Check for infinity
  if (!Number.isFinite(value)) {
    return {
      isValid: false,
      error: 'Coordinate cannot be infinity',
    };
  }

  // Check range
  if (isLatitude) {
    if (value < -90 || value > 90) {
      return {
        isValid: false,
        error: `Invalid latitude: ${value} (must be in range [-90, 90])`,
      };
    }
  } else {
    if (value < -180 || value > 180) {
      return {
        isValid: false,
        error: `Invalid longitude: ${value} (must be in range [-180, 180])`,
      };
    }
  }

  return { isValid: true };
}

// ============================================================================
// Formatting Functions
// ============================================================================

/**
 * Format a coordinate for display.
 *
 * @param decimal - Decimal degrees
 * @param isLatitude - True if latitude, False if longitude
 * @param format - Display format ('dms', 'decimal', or 'short')
 * @param secondsPrecision - Number of decimal places for seconds in DMS format (0-6, default 2)
 * @returns Formatted coordinate string
 * @throws Error if coordinate is invalid, format is invalid, or secondsPrecision is invalid
 *
 * @example
 * ```typescript
 * formatCoordinateDisplay(37.7749, true, 'dms');
 * // Returns: "37°46'29.64\"N"
 *
 * formatCoordinateDisplay(37.7749, true, 'decimal');
 * // Returns: "37.774900°N"
 *
 * formatCoordinateDisplay(37.7749, true, 'short');
 * // Returns: "37.77°N"
 *
 * formatCoordinateDisplay(37.7749, true, 'dms', 4);
 * // Returns: "37°46'29.6400\"N"
 * ```
 */
export function formatCoordinateDisplay(
  decimal: number,
  isLatitude: boolean,
  format: CoordinateFormat = 'dms',
  secondsPrecision: number = 2
): string {
  if (format === 'dms') {
    // DMS format: "37°46'29.64\"N"
    const { degrees, minutes, seconds, reference } = decimalToDMS(
      decimal,
      isLatitude,
      secondsPrecision
    );
    return `${degrees}°${minutes}'${seconds.toFixed(secondsPrecision)}"${reference}`;
  } else if (format === 'decimal') {
    // Decimal format: "37.774900°N" (6 decimal places)
    const reference = isLatitude
      ? (decimal >= 0 ? 'N' : 'S')
      : (decimal >= 0 ? 'E' : 'W');
    return `${Math.abs(decimal).toFixed(6)}°${reference}`;
  } else if (format === 'short') {
    // Short format: "37.77°N" (2 decimal places)
    const reference = isLatitude
      ? (decimal >= 0 ? 'N' : 'S')
      : (decimal >= 0 ? 'E' : 'W');
    return `${Math.abs(decimal).toFixed(2)}°${reference}`;
  } else {
    throw new Error(`Invalid format: ${format} (must be 'dms', 'decimal', or 'short')`);
  }
}

/**
 * Format a coordinate pair (latitude, longitude) for display.
 *
 * This convenience function combines latitude and longitude formatting into
 * a single call, making it easier to display complete location coordinates.
 *
 * @param latitude - Latitude in decimal degrees (-90.0 to 90.0)
 * @param longitude - Longitude in decimal degrees (-180.0 to 180.0)
 * @param format - Display format ('dms', 'decimal', or 'short')
 * @param secondsPrecision - Number of decimal places for seconds in DMS format (0-6, default 2)
 * @returns Formatted string: "LAT_STRING LON_STRING"
 * @throws Error if either coordinate is invalid or secondsPrecision is invalid
 *
 * @example
 * ```typescript
 * formatCoordinatePair(37.7749, -122.4194);
 * // Returns: "37°46'29.64\"N 122°25'9.84\"W"
 *
 * formatCoordinatePair(37.7749, -122.4194, 'decimal');
 * // Returns: "37.774900°N 122.419400°W"
 *
 * formatCoordinatePair(37.7749, -122.4194, 'short');
 * // Returns: "37.77°N 122.42°W"
 *
 * formatCoordinatePair(37.7749, -122.4194, 'dms', 4);
 * // Returns: "37°46'29.6400\"N 122°25'9.8400\"W"
 * ```
 */
export function formatCoordinatePair(
  latitude: number,
  longitude: number,
  format: CoordinateFormat = 'dms',
  secondsPrecision: number = 2
): string {
  // Validate latitude
  const latValidation = validateCoordinate(latitude, 'latitude');
  if (!latValidation.isValid) {
    throw new Error(latValidation.error || `Invalid latitude: ${latitude}`);
  }

  // Validate longitude
  const lonValidation = validateCoordinate(longitude, 'longitude');
  if (!lonValidation.isValid) {
    throw new Error(lonValidation.error || `Invalid longitude: ${longitude}`);
  }

  // Format both coordinates
  const latStr = formatCoordinateDisplay(latitude, true, format, secondsPrecision);
  const lonStr = formatCoordinateDisplay(longitude, false, format, secondsPrecision);

  return `${latStr} ${lonStr}`;
}
