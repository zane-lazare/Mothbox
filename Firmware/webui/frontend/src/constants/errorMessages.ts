/**
 * Centralized error messages for form validation across the Mothbox web UI.
 *
 * All validation schemas should import messages from this module rather than
 * inlining string literals. This ensures consistent wording and makes it easy
 * to audit or localize messages in the future.
 *
 * @module constants/errorMessages
 */

// ---------------------------------------------------------------------------
// Generic messages (by concept)
// ---------------------------------------------------------------------------

/** Required-field messages. */
export const REQUIRED = {
  /** e.g. "Preset name is required" */
  field: (name: string): string => `${name} is required`,
  /** e.g. "Action type must be selected" */
  selection: (name: string): string => `${name} must be selected`,
} as const

/** Numeric range messages (with optional unit suffix separated by a space). */
export const RANGE = {
  /** e.g. "Must be at least 5 s" */
  min: (val: number, unit?: string): string =>
    unit ? `Must be at least ${val} ${unit}` : `Must be at least ${val}`,
  /** e.g. "Cannot exceed 60 minutes" */
  max: (val: number, unit?: string): string =>
    unit ? `Cannot exceed ${val} ${unit}` : `Cannot exceed ${val}`,
  /** e.g. "Must be between 1 and 100 minutes" */
  between: (min: number, max: number, unit?: string): string =>
    unit
      ? `Must be between ${min} and ${max} ${unit}`
      : `Must be between ${min} and ${max}`,
} as const

/** String length messages. */
export const LENGTH = {
  /** e.g. "Must be at least 3 characters" */
  min: (val: number): string => `Must be at least ${val} characters`,
  /** e.g. "Must be 50 characters or less" */
  max: (val: number): string => `Must be ${val} characters or less`,
} as const

/** Type-coercion messages. Label is optional; when omitted, no field prefix. */
export const TYPE = {
  /** e.g. "Interval must be a number" or "Must be a number" */
  number: (label?: string): string =>
    label ? `${label} must be a number` : 'Must be a number',
  /** e.g. "Offset must be a whole number" or "Must be a whole number" */
  integer: (label?: string): string =>
    label ? `${label} must be a whole number` : 'Must be a whole number',
  /** e.g. "Cron expression must be a string" or "Must be a string" */
  string: (label?: string): string =>
    label ? `${label} must be a string` : 'Must be a string',
} as const

/**
 * Format / pattern messages.
 *
 * Four time variants exist because the original schemas used different phrasing:
 * - `time`:         generic, no field prefix (e.g. deployment coordinate labels)
 * - `validTime`:    fixed-time trigger ("Must be a **valid** time…")
 * - `timeRequired`: moon-phase + pre-condition ("**Time** must be…")
 * - `timeOrSolar`:  time-window trigger (accepts HH:MM or solar event strings)
 */
export const FORMAT = {
  /** Generic HH:MM — used by schemas that show the field label separately. */
  time: 'Must be in HH:MM format',
  /** FixedTimeTriggerForm (fixed-time.ts). */
  validTime: 'Must be a valid time in HH:MM format',
  /** MoonPhaseTriggerForm (moon-phase.ts) and PreConditionForm (pre-condition.ts). */
  timeRequired: 'Time must be in HH:MM format',
  /** TimeWindowInput (time-window.ts) — accepts HH:MM or solar event values. */
  timeOrSolar: 'Must be valid HH:MM time or solar event',
  /** Species referenceUrl and any future URL fields. */
  url: 'Please enter a valid URL (e.g., https://example.com)',
} as const

// ---------------------------------------------------------------------------
// Domain-specific messages
// ---------------------------------------------------------------------------

/** Coordinate validation messages. */
export const COORDINATES = {
  latitude: 'Latitude must be between -90 and 90',
  longitude: 'Longitude must be between -180 and 180',
} as const

/**
 * GPS settings messages.
 *
 * WARNING: timeoutMin/timeoutMax use compact "5s" format (no space before unit).
 * Do NOT substitute RANGE.min(val, 's') — that produces "Must be at least 5 s"
 * (with a space), which does not match the existing GPS schema strings.
 */
export const GPS = {
  invalidPath:
    'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.',
  invalidBaudrate: 'Invalid baudrate',
  /** e.g. "Must be at least 5s" */
  timeoutMin: (val: number): string => `Must be at least ${val}s`,
  /** e.g. "Cannot exceed 60s" */
  timeoutMax: (val: number): string => `Cannot exceed ${val}s`,
} as const

/** Deployment validation messages. */
export const DEPLOYMENT = {
  endBeforeStart: 'End date must be on or after start date',
  /** e.g. "Maximum 50 custom fields" */
  maxCustomFields: (max: number): string => `Maximum ${max} custom fields`,
} as const

/** Scheduler-specific messages. */
export const SCHEDULER = {
  sameStartEnd: 'Start and end times cannot be the same',
  invalidSolarEvent: 'Invalid solar event',
  invalidMoonPhase: 'Invalid moon phase',
  invalidSensorType: 'Invalid sensor type',
  invalidComparison: 'Invalid comparison operator',
} as const

/** Cron expression messages. */
export const CRON = {
  format: 'Must be 5 space-separated cron fields',
} as const

/** Preset naming messages. */
export const PRESET = {
  alphanumericOnly: 'Name can only contain letters, numbers, and underscores',
} as const

/** Tag validation messages. */
export const TAG = {
  empty: 'Tag cannot be empty',
  tooLong: 'Tag is too long',
  minRequired: 'At least one tag is required',
  tooMany: 'Too many tags',
} as const

/** Species identification messages. */
export const SPECIES = {
  nameTooLong: 'Species name is too long',
  commonNameTooLong: 'Common name is too long',
  urlTooLong: 'URL is too long',
} as const

/** Metadata field messages. */
export const METADATA = {
  /** e.g. 'Duplicate key: "habitat"' */
  duplicateKey: (key: string): string => `Duplicate key: "${key}"`,
} as const

/** Network / server communication messages. */
export const NETWORK = {
  connectionError: 'Unable to save. Please check your connection.',
  serverError: 'Server error. Please try again later.',
  timeout: 'Request timed out. Please try again.',
} as const

/**
 * General validation feedback messages (from legacy errorMessages.js).
 *
 * These are used by UI components for form-level status, NOT by Zod schemas.
 * For schema-level required-field messages, use REQUIRED.field(name) instead.
 */
export const VALIDATION = {
  general: 'Please fix the errors above.',
  requiredField: 'This field is required.',
} as const
