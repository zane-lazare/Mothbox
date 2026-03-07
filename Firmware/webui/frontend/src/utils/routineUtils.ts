/**
 * Utility functions for routine display and name generation
 * @module utils/routineUtils
 */

import { ACTION_TYPE_COLORS, isHdrAction } from '@/components/scheduler/constants'

// ---------------------------------------------------------------------------
// Loose helper types for display utilities
//
// These functions are called with partial / ad-hoc objects (tests pass `{}`,
// `{ trigger_type: 'solar', solar_event: 'dusk' }` without required fields
// like `offset_minutes`, etc.).  We therefore accept loose shapes and guard
// every property access at runtime.
// ---------------------------------------------------------------------------

/** Loose trigger shape accepted by display helpers. */
type LooseTrigger = {
  trigger_type?: string
  // Allow any additional trigger fields accessed via switch/case
  interval_minutes?: number
  solar_event?: string
  offset_minutes?: number
  time_of_day?: string
  times?: unknown[]
  moon_phase?: string
  days_interval?: number
  days?: unknown[]
  time?: string
  cron_expression?: string
  days_of_week?: number[] | null
}

/** Loose action shape accepted by display helpers. */
type LooseAction = {
  action_type?: string
  action_name?: string
  name?: string
  id?: string
  offset_minutes?: number
}

/** Loose routine shape accepted by display helpers. */
type LooseRoutine = {
  name?: string
  actions?: LooseAction[]
  trigger?: LooseTrigger | null
  routine_id?: string
  pre_condition?: unknown
}

/**
 * Trigger type labels for display
 */
export const TRIGGER_LABELS: Record<string, string> = {
  interval: 'Interval',
  solar: 'Solar',
  fixed_time: 'Fixed',
  moon_phase: 'Moon',
  recurring_days: 'Days',
  cron: 'Cron',
}

/**
 * Action type color classes for display dots
 * Derived from shared constants for single source of truth
 */
export const ACTION_COLORS: Record<string, string> = Object.fromEntries(
  Object.entries(ACTION_TYPE_COLORS).map(([key, val]) => [key, val.solid])
)

/**
 * Action name mappings for readable display
 */
const ACTION_NAME_MAP: Record<string, string> = {
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
const ACTION_SHORT_LABELS: Record<string, string> = {
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
const SOLAR_EVENT_MAP: Record<string, string> = {
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
 */
export function getTriggerLabel(trigger: LooseTrigger | null | undefined): string {
  if (!trigger?.trigger_type) return ''
  return TRIGGER_LABELS[trigger.trigger_type] || trigger.trigger_type
}

/**
 * Get the action color class based on action type
 * Uses shared constants for single source of truth
 */
export function getActionColor(action: LooseAction | null | undefined): string {
  if (!action?.action_type) return ACTION_COLORS.service

  // Check for HDR-specific camera actions using shared utility
  if (isHdrAction(action.action_name)) {
    return ACTION_COLORS.hdr
  }

  return ACTION_COLORS[action.action_type] || ACTION_COLORS.service
}

/**
 * Get the primary action color for a routine (based on first action)
 */
export function getPrimaryActionColor(actions: LooseAction[] | null | undefined): string {
  if (!actions?.length) return ACTION_COLORS.service
  return getActionColor(actions[0])
}

/**
 * Summarize actions for display name generation
 */
export function summarizeActions(actions: LooseAction[] | null | undefined): string {
  if (!actions?.length) return ''

  // For single action, use full name
  if (actions.length === 1) {
    const actionName = actions[0].action_name || actions[0].name || ''
    const readableName = ACTION_NAME_MAP[actionName.toLowerCase()] || actionName
    return readableName.charAt(0).toUpperCase() + readableName.slice(1)
  }

  // For multiple actions, use short labels and deduplicate
  const shortLabels: string[] = actions.map((action: LooseAction) => {
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
 */
export function describeTrigger(trigger: LooseTrigger | null | undefined): string {
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
      const timeValue = typeof time === 'object' ? (time as { value: string }).value : time
      return `at ${timeValue}`
    }

    case 'moon_phase': {
      const phase = trigger.moon_phase || 'full'
      return `on ${phase} moon`
    }

    case 'recurring_days': {
      const days = trigger.days_interval || (trigger.days as unknown[] | undefined)?.length || 1
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
 */
export function generateRoutineName(routine: LooseRoutine): string {
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
 */
export function generateScheduleDescription(routines: LooseRoutine[] | null | undefined): string {
  if (!routines?.length) return ''

  // Reuse generateRoutineName for each routine
  const descriptions: string[] = routines.map(r => generateRoutineName(r)).filter(Boolean)

  // Join with commas, limiting to first 2-3 for brevity
  if (descriptions.length <= 3) {
    return descriptions.join(', ')
  }
  return `${descriptions.slice(0, 2).join(', ')} (+${descriptions.length - 2} more)`
}
