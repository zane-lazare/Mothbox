/**
 * Type declarations for gpsPrecision.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with gpsPrecision.js.
 */

export interface GpsPrecisionOption {
  value: number
  label: string
  description: string
}

export declare const GPS_PRECISION_OPTIONS: readonly GpsPrecisionOption[]

/**
 * Get stored GPS precision or default to 2 decimal places.
 * @returns Precision value (0-6)
 */
export declare function getGpsPrecision(): number

/**
 * Set GPS precision preference in localStorage.
 * @param precision - Precision value (0-6)
 * @returns True if saved successfully, false if localStorage unavailable
 */
export declare function setGpsPrecision(precision: number): boolean
