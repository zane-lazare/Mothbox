/**
 * Constants for TriggerSelector components
 * @module TriggerSelector/constants
 */

/**
 * Shared border style for trigger form containers
 * Lighter than routine card borders to show visual hierarchy
 * @constant {string}
 */
export const TRIGGER_FORM_BORDER = 'border border-gray-200 dark:border-gray-700 rounded-lg p-4'

/**
 * Trigger type options for the dropdown selector
 * @constant {Array<Object>}
 */
export const TRIGGER_TYPE_OPTIONS = [
  { value: 'interval', label: 'Interval', description: 'repeat at fixed intervals' },
  { value: 'fixed_time', label: 'Fixed Time', description: 'run at specific times' },
  { value: 'solar', label: 'Solar Event', description: 'based on sun position' },
  { value: 'moon_phase', label: 'Moon Phase', description: 'lunar cycle events' },
  { value: 'recurring_days', label: 'Recurring Days', description: 'weekly schedule' },
  { value: 'cron', label: 'Cron Expression', description: 'advanced', badge: 'advanced' },
]

/**
 * Solar events matching backend schema
 * @constant {Array<Object>}
 */
export const SOLAR_EVENTS = [
  { value: 'sunset', label: 'Sunset' },
  { value: 'civil_dusk', label: 'Civil Dusk' },
  { value: 'nautical_dusk', label: 'Nautical Dusk' },
  { value: 'astronomical_dusk', label: 'Astronomical Dusk' },
  { value: 'sunrise', label: 'Sunrise' },
  { value: 'civil_dawn', label: 'Civil Dawn' },
  { value: 'nautical_dawn', label: 'Nautical Dawn' },
  { value: 'astronomical_dawn', label: 'Astronomical Dawn' },
]

/**
 * Moon phases with emoji representations
 * @constant {Array<Object>}
 */
export const MOON_PHASES = [
  { value: 'new', label: 'New', emoji: '🌑' },
  { value: 'first_quarter', label: 'First', emoji: '🌓' },
  { value: 'full', label: 'Full', emoji: '🌕' },
  { value: 'last_quarter', label: 'Last', emoji: '🌗' },
]

/**
 * Days of week (0=Sunday per mockup convention)
 * @constant {Array<Object>}
 */
export const DAYS_OF_WEEK = [
  { value: 0, label: 'Sunday', short: 'S' },
  { value: 1, label: 'Monday', short: 'M' },
  { value: 2, label: 'Tuesday', short: 'T' },
  { value: 3, label: 'Wednesday', short: 'W' },
  { value: 4, label: 'Thursday', short: 'T' },
  { value: 5, label: 'Friday', short: 'F' },
  { value: 6, label: 'Saturday', short: 'S' },
]

/**
 * Interval unit options
 * @constant {Array<Object>}
 */
export const INTERVAL_UNITS = [
  { value: 'minutes', label: 'minutes', multiplier: 1 },
  { value: 'hours', label: 'hours', multiplier: 60 },
]

/**
 * Validate a cron expression using cronstrue
 * Returns true if valid, false otherwise
 * @param {string} expression - The cron expression to validate
 * @returns {boolean}
 */
function isValidCronExpression(expression) {
  if (!expression) return false
  // Simple validation: cron should have 5 space-separated fields
  const fields = expression.trim().split(/\s+/)
  if (fields.length !== 5) return false
  // Check each field has valid characters
  const validPattern = /^[\d,\-*/]+$/
  return fields.every(f => validPattern.test(f))
}

/**
 * Validate a trigger configuration and return field-level error
 * @param {Object} trigger - The trigger configuration
 * @returns {string|null} - Error message or null if valid
 */
export function validateTrigger(trigger) {
  if (!trigger) return null

  const type = trigger.trigger_type

  switch (type) {
    case 'cron': {
      const expression = trigger.cron_expression
      if (!expression) return 'Cron expression is required'
      if (!isValidCronExpression(expression)) {
        return 'Invalid cron expression'
      }
      return null
    }

    case 'fixed_time': {
      const times = trigger.times
      if (!times || times.length === 0) {
        return 'At least one time is required'
      }
      // Handle both old format (string[]) and new format ({ id, value }[])
      const hasValidTime = times.some(t =>
        typeof t === 'string' ? t : t?.value
      )
      if (!hasValidTime) return 'At least one valid time is required'
      return null
    }

    case 'moon_phase': {
      const phases = trigger.phases
      if (!phases || phases.length === 0) {
        return 'At least one moon phase is required'
      }
      return null
    }

    case 'recurring_days': {
      const days = trigger.days
      if (!days || days.length === 0) {
        return 'At least one day is required'
      }
      return null
    }

    case 'interval': {
      const intervalMinutes = trigger.interval_minutes
      if (intervalMinutes === undefined || intervalMinutes === null) {
        return 'Interval is required'
      }
      if (intervalMinutes < 1) {
        return 'Interval must be at least 1 minute'
      }
      if (intervalMinutes > 1440) {
        return 'Interval cannot exceed 24 hours (1440 minutes)'
      }
      return null
    }

    case 'solar': {
      const offset = trigger.offset_minutes
      if (offset !== undefined && offset !== null) {
        if (offset < -120 || offset > 120) {
          return 'Offset must be between -120 and 120 minutes'
        }
      }
      return null
    }

    default:
      return null
  }
}

/**
 * Create default trigger configuration for a given type
 *
 * @param {string} type - The trigger type
 * @returns {Object} Default trigger configuration
 */
export function createDefaultTrigger(type) {
  switch (type) {
    case 'interval':
      return {
        trigger_type: 'interval',
        interval_minutes: 15,
        time_window: null,
      }
    case 'fixed_time':
      return {
        trigger_type: 'fixed_time',
        times: ['08:00'],
      }
    case 'solar':
      return {
        trigger_type: 'solar',
        solar_event: 'sunset',
        offset_minutes: 0,
      }
    case 'moon_phase':
      return {
        trigger_type: 'moon_phase',
        phases: ['full'],
      }
    case 'recurring_days':
      return {
        trigger_type: 'recurring_days',
        days: [0, 5, 6],
        time: '20:00',
      }
    case 'cron':
      return {
        trigger_type: 'cron',
        cron_expression: '0 20 * * *',
      }
    default:
      return {
        trigger_type: 'interval',
        interval_minutes: 15,
        time_window: null,
      }
  }
}
