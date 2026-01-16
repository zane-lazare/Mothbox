/**
 * Utility functions for routine display and name generation
 * @module utils/routineUtils
 */

/**
 * Trigger type labels for display
 */
export const TRIGGER_LABELS = {
  interval: 'Interval',
  solar: 'Solar',
  fixed_time: 'Fixed',
  moon_phase: 'Moon',
  recurring_days: 'Days',
  cron: 'Cron',
}

/**
 * Action type color classes for display dots
 */
export const ACTION_COLORS = {
  gpio: 'bg-orange-400',
  camera: 'bg-blue-400',
  hdr: 'bg-purple-400',
  gps_sync: 'bg-green-400',
  service: 'bg-gray-400',
}

/**
 * Action name mappings for readable display
 */
const ACTION_NAME_MAP = {
  // GPIO actions
  attract_on: 'Attract On',
  attract_off: 'Attract Off',
  flash_on: 'Flash On',
  flash_off: 'Flash Off',
  uv_on: 'UV On',
  uv_off: 'UV Off',
  // Camera actions
  takephoto: 'Take Photo',
  take_photo: 'Take Photo',
  // GPS actions
  gps_sync: 'GPS Sync',
}

/**
 * Short labels for action summary (used when combining multiple actions)
 */
const ACTION_SHORT_LABELS = {
  attract_on: 'Attract',
  attract_off: 'Attract',
  flash_on: 'Flash',
  flash_off: 'Flash',
  uv_on: 'UV',
  uv_off: 'UV',
  takephoto: 'Photo',
  take_photo: 'Photo',
  gps_sync: 'GPS',
}

/**
 * Solar event labels for display
 */
const SOLAR_EVENT_MAP = {
  dawn: 'at Dawn',
  dusk: 'at Dusk',
  sunrise: 'at Sunrise',
  sunset: 'at Sunset',
  civil_dawn: 'at Civil Dawn',
  civil_dusk: 'at Civil Dusk',
  nautical_dawn: 'at Nautical Dawn',
  nautical_dusk: 'at Nautical Dusk',
  astronomical_dawn: 'at Astronomical Dawn',
  astronomical_dusk: 'at Astronomical Dusk',
  solar_noon: 'at Solar Noon',
}

/**
 * Get the trigger label for display
 * @param {Object} trigger - Trigger object
 * @returns {string} Label text
 */
export function getTriggerLabel(trigger) {
  if (!trigger?.trigger_type) return ''
  return TRIGGER_LABELS[trigger.trigger_type] || trigger.trigger_type
}

/**
 * Get the action color class based on action type
 * @param {Object} action - Action object
 * @returns {string} Tailwind color class
 */
export function getActionColor(action) {
  if (!action?.action_type) return ACTION_COLORS.service

  // Check for HDR-specific camera actions
  if (action.action_type === 'camera' && action.action_name?.toLowerCase().includes('hdr')) {
    return ACTION_COLORS.hdr
  }

  return ACTION_COLORS[action.action_type] || ACTION_COLORS.service
}

/**
 * Get the primary action color for a routine (based on first action)
 * @param {Array} actions - Array of action objects
 * @returns {string} Tailwind color class
 */
export function getPrimaryActionColor(actions) {
  if (!actions?.length) return ACTION_COLORS.service
  return getActionColor(actions[0])
}

/**
 * Summarize actions for display name generation
 * @param {Array} actions - Array of action objects
 * @returns {string} Summary text
 */
export function summarizeActions(actions) {
  if (!actions?.length) return ''

  // For single action, use full name
  if (actions.length === 1) {
    const actionName = actions[0].action_name || actions[0].name || ''
    const readableName = ACTION_NAME_MAP[actionName.toLowerCase()] || actionName
    return readableName.charAt(0).toUpperCase() + readableName.slice(1)
  }

  // For multiple actions, use short labels and deduplicate
  const shortLabels = actions.map(action => {
    const actionName = action.action_name || action.name || ''
    return ACTION_SHORT_LABELS[actionName.toLowerCase()] || actionName
  })

  // Remove duplicates while preserving order
  const uniqueLabels = [...new Set(shortLabels)].filter(Boolean)

  if (uniqueLabels.length === 0) return ''
  if (uniqueLabels.length === 1) return uniqueLabels[0]

  // Join with " + " for readability: "Flash + Photo"
  return uniqueLabels.join(' + ')
}

/**
 * Describe trigger for display name generation
 * @param {Object} trigger - Trigger object
 * @returns {string} Description text
 */
export function describeTrigger(trigger) {
  if (!trigger?.trigger_type) return ''

  switch (trigger.trigger_type) {
    case 'interval': {
      const minutes = trigger.interval_minutes || 15
      return `every ${minutes} min`
    }

    case 'solar': {
      const event = trigger.solar_event || 'sunset'
      const offset = trigger.offset_minutes || 0
      const eventText = SOLAR_EVENT_MAP[event] || `at ${event}`
      if (offset === 0) {
        return eventText
      }
      const sign = offset > 0 ? '+' : ''
      return `${eventText} ${sign}${offset}min`
    }

    case 'fixed_time': {
      const time = trigger.time_of_day || trigger.times?.[0] || '12:00'
      // Extract just the time value if it's an object
      const timeValue = typeof time === 'object' ? time.value : time
      return `at ${timeValue}`
    }

    case 'moon_phase': {
      const phase = trigger.moon_phase || 'full'
      return `on ${phase} moon`
    }

    case 'recurring_days': {
      const days = trigger.days_interval || trigger.days?.length || 1
      const time = trigger.time || '00:00'
      return `every ${days} days at ${time}`
    }

    case 'cron': {
      return 'on schedule'
    }

    default:
      return ''
  }
}

/**
 * Generate a display name for a routine based on its actions and trigger
 * @param {Object} routine - Routine object with actions and trigger
 * @returns {string} Generated display name
 */
export function generateRoutineName(routine) {
  // If explicit name exists and is not auto-generated placeholder, use it
  if (routine.name && !routine.name.startsWith('Routine ')) {
    return routine.name
  }

  // Generate from actions + trigger
  const actionSummary = summarizeActions(routine.actions)
  const triggerDesc = describeTrigger(routine.trigger)

  if (actionSummary && triggerDesc) {
    return `${actionSummary} ${triggerDesc}`
  }

  if (actionSummary) {
    return actionSummary
  }

  if (triggerDesc) {
    return `Run ${triggerDesc}`
  }

  return 'New Routine'
}

/**
 * Generate a human-readable description for a schedule from its routines
 * Reuses generateRoutineName for each routine and joins them.
 * @param {Array} routines - Array of routine objects
 * @returns {string} Generated description like "Take Photo every 15 min, Attract On at Dusk"
 */
export function generateScheduleDescription(routines) {
  if (!routines?.length) return ''

  // Reuse generateRoutineName for each routine
  const descriptions = routines.map(r => generateRoutineName(r)).filter(Boolean)

  // Join with commas, limiting to first 2-3 for brevity
  if (descriptions.length <= 3) {
    return descriptions.join(', ')
  }
  return `${descriptions.slice(0, 2).join(', ')} (+${descriptions.length - 2} more)`
}
