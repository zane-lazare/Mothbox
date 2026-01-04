/**
 * Constants for TriggerSelector components
 * @module TriggerSelector/constants
 */

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
        cron_expression: '*/15 18-6 * * *',
      }
    default:
      return {
        trigger_type: 'interval',
        interval_minutes: 15,
        time_window: null,
      }
  }
}
