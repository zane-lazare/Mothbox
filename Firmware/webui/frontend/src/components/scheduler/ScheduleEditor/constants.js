/**
 * Constants for the Schedule Editor component
 * Must match backend schema in webui/backend/lib/schedule_schema.py
 */

/**
 * Validation limits for schedules and patterns
 * @constant {Object}
 */
export const SCHEDULE_LIMITS = {
  /** Maximum length for pattern names */
  NAME_MAX_LENGTH: 200,
  /** Maximum length for pattern descriptions */
  DESCRIPTION_MAX_LENGTH: 2000,
  /** Maximum number of actions per pattern */
  MAX_ACTIONS_PER_PATTERN: 20,
  /** Maximum number of patterns per schedule */
  MAX_PATTERNS_PER_SCHEDULE: 10,
  /** Maximum offset minutes (24 hours) */
  MAX_OFFSET_MINUTES: 1440,
  /** Maximum interval minutes (7 days) */
  MAX_INTERVAL_MINUTES: 10080,
  /** Minimum interval minutes */
  MIN_INTERVAL_MINUTES: 1,
  /** Maximum cooldown minutes */
  MAX_COOLDOWN_MINUTES: 60,
  /** Maximum offset days */
  MAX_OFFSET_DAYS: 7,
}

/**
 * Trigger type definitions with UI metadata
 * @constant {Object}
 */
export const TRIGGER_TYPES = {
  interval: {
    value: 'interval',
    label: 'Interval',
    icon: 'ClockIcon',
    description: 'Trigger at regular time intervals',
  },
  solar: {
    value: 'solar',
    label: 'Solar Event',
    icon: 'SunIcon',
    description: 'Trigger based on sun position (sunrise, sunset, etc.)',
  },
  moon_phase: {
    value: 'moon_phase',
    label: 'Moon Phase',
    icon: 'MoonIcon',
    description: 'Trigger on specific moon phases',
  },
  fixed_time: {
    value: 'fixed_time',
    label: 'Fixed Time',
    icon: 'ClockIcon',
    description: 'Trigger at specific times of day',
  },
  sensor: {
    value: 'sensor',
    label: 'Sensor',
    icon: 'BoltIcon',
    description: 'Trigger based on sensor readings',
  },
}

/**
 * Solar events with descriptions
 * @constant {Array<Object>}
 */
export const SOLAR_EVENTS = [
  {
    value: 'astronomical_dawn',
    label: 'Astronomical Dawn',
    description: 'Sun 18° below horizon (start of twilight)',
  },
  {
    value: 'nautical_dawn',
    label: 'Nautical Dawn',
    description: 'Sun 12° below horizon (horizon barely visible)',
  },
  {
    value: 'civil_dawn',
    label: 'Civil Dawn',
    description: 'Sun 6° below horizon (outdoor activities possible)',
  },
  {
    value: 'blue_hour_start',
    label: 'Blue Hour Start',
    description: 'Beginning of blue hour (soft blue light)',
  },
  {
    value: 'dawn',
    label: 'Dawn',
    description: 'Beginning of twilight before sunrise',
  },
  {
    value: 'sunrise',
    label: 'Sunrise',
    description: 'Sun appears above horizon',
  },
  {
    value: 'golden_hour_start',
    label: 'Golden Hour Start',
    description: 'Beginning of golden hour (warm light)',
  },
  {
    value: 'noon',
    label: 'Solar Noon',
    description: 'Sun at highest point in sky',
  },
  {
    value: 'golden_hour_end',
    label: 'Golden Hour End',
    description: 'End of golden hour before sunset',
  },
  {
    value: 'sunset',
    label: 'Sunset',
    description: 'Sun disappears below horizon',
  },
  {
    value: 'dusk',
    label: 'Dusk',
    description: 'End of twilight after sunset',
  },
  {
    value: 'blue_hour_end',
    label: 'Blue Hour End',
    description: 'End of blue hour (darkness approaching)',
  },
  {
    value: 'civil_dusk',
    label: 'Civil Dusk',
    description: 'Sun 6° below horizon (artificial light needed)',
  },
  {
    value: 'nautical_dusk',
    label: 'Nautical Dusk',
    description: 'Sun 12° below horizon (horizon no longer visible)',
  },
  {
    value: 'astronomical_dusk',
    label: 'Astronomical Dusk',
    description: 'Sun 18° below horizon (complete darkness)',
  },
]

/**
 * Moon phases
 * @constant {Array<Object>}
 */
export const MOON_PHASES = [
  { value: 'new', label: 'New Moon' },
  { value: 'waxing_crescent', label: 'Waxing Crescent' },
  { value: 'first_quarter', label: 'First Quarter' },
  { value: 'waxing_gibbous', label: 'Waxing Gibbous' },
  { value: 'full', label: 'Full Moon' },
  { value: 'waning_gibbous', label: 'Waning Gibbous' },
  { value: 'last_quarter', label: 'Last Quarter' },
  { value: 'waning_crescent', label: 'Waning Crescent' },
]

/**
 * Days of week (ISO 8601: 0=Monday, 6=Sunday)
 * @constant {Array<Object>}
 */
export const DAYS_OF_WEEK = [
  { value: 0, label: 'Monday', shortLabel: 'Mon' },
  { value: 1, label: 'Tuesday', shortLabel: 'Tue' },
  { value: 2, label: 'Wednesday', shortLabel: 'Wed' },
  { value: 3, label: 'Thursday', shortLabel: 'Thu' },
  { value: 4, label: 'Friday', shortLabel: 'Fri' },
  { value: 5, label: 'Saturday', shortLabel: 'Sat' },
  { value: 6, label: 'Sunday', shortLabel: 'Sun' },
]

/**
 * Sensor types
 * @constant {Array<Object>}
 */
export const SENSOR_TYPES = [
  {
    value: 'motion',
    label: 'Motion',
    description: 'Detect motion or movement',
  },
  {
    value: 'light',
    label: 'Light',
    description: 'Measure light levels (lux)',
  },
  {
    value: 'temperature',
    label: 'Temperature',
    description: 'Measure temperature (°C)',
  },
]

/**
 * Sensor comparison operators
 * @constant {Array<Object>}
 */
export const SENSOR_COMPARISONS = [
  { value: 'gt', label: 'Greater Than', symbol: '>' },
  { value: 'lt', label: 'Less Than', symbol: '<' },
  { value: 'eq', label: 'Equal To', symbol: '=' },
  { value: 'gte', label: 'Greater Than or Equal', symbol: '≥' },
  { value: 'lte', label: 'Less Than or Equal', symbol: '≤' },
]

/**
 * Default trigger configurations for each trigger type
 * @constant {Object}
 */
export const TRIGGER_DEFAULTS = {
  interval: {
    trigger_type: 'interval',
    interval_minutes: 60,
    time_window_start: '00:00',
    time_window_end: '23:59',
    days_of_week: [0, 1, 2, 3, 4, 5, 6],
  },
  solar: {
    trigger_type: 'solar',
    solar_event: 'sunset',
    offset_minutes: 0,
    days_of_week: [0, 1, 2, 3, 4, 5, 6],
  },
  moon_phase: {
    trigger_type: 'moon_phase',
    moon_phase: 'full',
    time_of_day: '20:00',
    offset_days: 0,
  },
  fixed_time: {
    trigger_type: 'fixed_time',
    time_of_day: '12:00',
    days_of_week: [0, 1, 2, 3, 4, 5, 6],
  },
  sensor: {
    trigger_type: 'sensor',
    sensor_type: 'light',
    comparison: 'lt',
    threshold: 100,
    cooldown_minutes: 5,
  },
}

/**
 * Regular expression for HH:MM time format validation
 * @constant {RegExp}
 */
export const TIME_FORMAT_REGEX = /^([0-1][0-9]|2[0-3]):([0-5][0-9])$/

/**
 * Maximum date range in days (10 years)
 * @constant {number}
 */
export const MAX_DATE_RANGE_DAYS = 3650

/**
 * Validates a numeric input value against optional min/max constraints.
 * Returns the validated number or null if invalid.
 *
 * @param {string|number} value - The input value to validate
 * @param {number} [min] - Optional minimum value (inclusive)
 * @param {number} [max] - Optional maximum value (inclusive)
 * @returns {number|null} The validated number or null if invalid
 *
 * @example
 * validateNumericInput('42', 0, 100) // returns 42
 * validateNumericInput('abc') // returns null
 * validateNumericInput(150, 0, 100) // returns null (exceeds max)
 */
export const validateNumericInput = (value, min, max) => {
  // Handle empty/whitespace strings (Number('') === 0, but we want null)
  if (typeof value === 'string' && value.trim() === '') return null

  // Handle undefined
  if (value === undefined) return null

  const num = Number(value)

  // Reject NaN
  if (isNaN(num)) return null

  // Reject Infinity
  if (!isFinite(num)) return null

  // Check min constraint
  if (min !== undefined && num < min) return null

  // Check max constraint
  if (max !== undefined && num > max) return null

  return num
}

/**
 * Checks if a value is a valid solar event name.
 *
 * @param {string} value - The value to check
 * @returns {boolean} True if the value is a valid solar event
 *
 * @example
 * isValidSolarEvent('sunset') // returns true
 * isValidSolarEvent('12:00') // returns false
 * isValidSolarEvent('invalid') // returns false
 */
export const isValidSolarEvent = (value) => {
  if (typeof value !== 'string') return false
  return SOLAR_EVENTS.some((event) => event.value === value)
}
