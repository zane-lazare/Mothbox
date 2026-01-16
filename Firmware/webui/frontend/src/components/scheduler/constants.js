/**
 * Shared scheduler constants
 *
 * Single source of truth for action type colors, labels, and conflict styling
 * across all scheduler UI components (ScheduleCard, RoutineCard, DayTimeline, etc.)
 *
 * @module components/scheduler/constants
 */

/**
 * Action type keys for type safety
 */
export const ACTION_TYPES = {
  CAMERA: 'camera',
  GPIO: 'gpio',
  HDR: 'hdr',
  GPS_SYNC: 'gps_sync',
  SERVICE: 'service',
}

/**
 * Action type color definitions
 *
 * Each type has three color variants:
 * - solid: Full opacity background for dots/badges (e.g., bg-blue-400)
 * - bg: Semi-transparent background for chips/cards (e.g., bg-blue-500/20)
 * - text: Text color for labels (e.g., text-blue-400)
 */
export const ACTION_TYPE_COLORS = {
  camera: {
    solid: 'bg-blue-400',
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
  },
  gpio: {
    solid: 'bg-orange-400',
    bg: 'bg-orange-500/20',
    text: 'text-orange-400',
  },
  hdr: {
    solid: 'bg-purple-400',
    bg: 'bg-purple-500/20',
    text: 'text-purple-400',
  },
  gps_sync: {
    solid: 'bg-green-400',
    bg: 'bg-green-500/20',
    text: 'text-green-400',
  },
  service: {
    solid: 'bg-gray-400',
    bg: 'bg-gray-500/20',
    text: 'text-gray-400',
  },
}

/**
 * Default colors for unknown action types
 */
export const DEFAULT_ACTION_COLORS = {
  solid: 'bg-blue-400',
  bg: 'bg-blue-500/20',
  text: 'text-blue-400',
}

/**
 * Human-readable labels for action types
 */
export const ACTION_TYPE_LABELS = {
  camera: 'Camera',
  gpio: 'GPIO',
  hdr: 'HDR',
  gps_sync: 'GPS Sync',
  service: 'Service',
}

/**
 * Conflict/collision color definitions
 *
 * Used for highlighting time collisions (errors) and GPIO warnings
 */
export const CONFLICT_COLORS = {
  error: {
    ring: 'ring-1 ring-red-400',
    bg: 'bg-red-950/20',
    text: 'text-red-400',
  },
  warning: {
    ring: 'ring-1 ring-yellow-400',
    bg: 'bg-yellow-950/20',
    text: 'text-yellow-400',
  },
}

/**
 * Row conflict styles for DayTimeline hour rows
 */
export const ROW_CONFLICT_STYLES = {
  error: {
    bg: 'bg-red-950/20',
    label: 'text-red-400',
  },
  warning: {
    bg: 'bg-yellow-950/20',
    label: 'text-yellow-400',
  },
  none: {
    bg: '',
    label: 'text-gray-600 dark:text-gray-600',
  },
}

/**
 * Action names that indicate HDR mode
 */
export const HDR_ACTION_NAMES = ['hdr', 'hdr_bracket', 'bracket']

/**
 * Checks if an action name indicates HDR mode
 * @param {string} actionName - The action name to check
 * @returns {boolean} True if this is an HDR action
 */
export function isHdrAction(actionName) {
  if (!actionName) return false
  const lower = actionName.toLowerCase()
  return HDR_ACTION_NAMES.some((name) => lower.includes(name))
}

/**
 * Gets the solid color class for an action type
 * @param {string} actionType - The action type key
 * @returns {string} Tailwind solid background class
 */
export function getActionSolidColor(actionType) {
  return ACTION_TYPE_COLORS[actionType]?.solid || DEFAULT_ACTION_COLORS.solid
}

/**
 * Gets display colors for an action type (bg + text)
 * @param {string} actionType - Action type ('camera', 'gpio', etc.)
 * @param {string} actionName - Action name (used to detect HDR)
 * @returns {Object} { bg, text } Tailwind classes
 */
export function getActionTypeDisplay(actionType, actionName) {
  // Check for HDR first (special purple color)
  if (isHdrAction(actionName)) {
    return {
      bg: ACTION_TYPE_COLORS.hdr.bg,
      text: ACTION_TYPE_COLORS.hdr.text,
    }
  }

  const colors = ACTION_TYPE_COLORS[actionType] || DEFAULT_ACTION_COLORS
  return {
    bg: colors.bg,
    text: colors.text,
  }
}
