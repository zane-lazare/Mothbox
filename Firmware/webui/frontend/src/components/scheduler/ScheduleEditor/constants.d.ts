/**
 * Type declarations for constants.js
 *
 * Provides TypeScript types for the scheduler constants module during the
 * gradual migration to TypeScript. Add types here as .tsx components
 * import additional constants from constants.js.
 *
 * IMPORTANT: Keep in sync with constants.js -- changes there must be
 * reflected here manually.
 */

export declare const SCHEDULE_LIMITS: {
  NAME_MAX_LENGTH: number
  DESCRIPTION_MAX_LENGTH: number
  MAX_ACTIONS_PER_PATTERN: number
  MAX_PATTERNS_PER_SCHEDULE: number
  MAX_OFFSET_MINUTES: number
  MAX_INTERVAL_MINUTES: number
  MIN_INTERVAL_MINUTES: number
  MAX_COOLDOWN_MINUTES: number
  MIN_COOLDOWN_MINUTES: number
  MAX_OFFSET_DAYS: number
}

export declare const DAYS_OF_WEEK: ReadonlyArray<{
  value: number
  label: string
  shortLabel: string
}>

export declare const SOLAR_EVENTS: ReadonlyArray<{
  value: string
  label: string
  description: string
}>

export declare const MOON_PHASES: ReadonlyArray<{
  value: string
  label: string
}>

export declare const TRIGGER_TYPES: Record<
  string,
  { value: string; label: string; icon: string; description: string }
>

export declare const SENSOR_TYPES: ReadonlyArray<{
  value: string
  label: string
  description: string
}>

export declare const SENSOR_COMPARISONS: ReadonlyArray<{
  value: string
  label: string
  symbol: string
}>

export declare const TRIGGER_DEFAULTS: Record<string, Record<string, unknown>>

export declare const TIME_FORMAT_REGEX: RegExp

export declare const MAX_DATE_RANGE_DAYS: number

export declare function validateNumericInput(
  value: string | number | undefined,
  min?: number,
  max?: number,
): number | null

export declare function isValidSolarEvent(value: string): boolean
