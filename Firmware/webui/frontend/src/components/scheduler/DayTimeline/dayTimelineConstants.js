/**
 * DayTimeline styling constants (Issue #326)
 *
 * Provides static Tailwind class mappings for JIT compatibility.
 * Dynamic class construction doesn't work with Tailwind's JIT compiler,
 * so we define all possible class combinations here.
 *
 * @module components/scheduler/DayTimeline/dayTimelineConstants
 */

/**
 * Action type color mapping for execution chips.
 * Maps action types to their Tailwind background/text classes.
 */
export const ACTION_TYPE_COLORS = {
  camera: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
  },
  gpio: {
    bg: 'bg-orange-500/20',
    text: 'text-orange-400',
  },
  hdr: {
    bg: 'bg-purple-500/20',
    text: 'text-purple-400',
  },
  gps_sync: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
  },
  service: {
    bg: 'bg-gray-500/20',
    text: 'text-gray-400',
  },
}

/**
 * Default colors for unknown action types.
 */
export const DEFAULT_ACTION_COLORS = {
  bg: 'bg-blue-500/20',
  text: 'text-blue-400',
}

/**
 * Row background and label colors for conflict states.
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
 * Conflict ring styles for execution chips.
 */
export const CHIP_CONFLICT_RINGS = {
  error: 'ring-1 ring-red-400',
  warning: 'ring-1 ring-yellow-400',
}

/**
 * Legend items for the timeline.
 */
export const LEGEND_ITEMS = [
  { color: 'bg-blue-400', label: 'Camera' },
  { color: 'bg-orange-400', label: 'GPIO' },
  { color: 'ring-1 ring-red-400', label: 'Collision', isRing: true },
  { color: 'ring-1 ring-yellow-400', label: 'Warning', isRing: true },
]

/**
 * Action names that indicate HDR mode.
 */
export const HDR_ACTION_NAMES = ['hdr', 'hdr_bracket', 'bracket']

/**
 * Checks if an action name indicates HDR mode.
 * @param {string} actionName - The action name to check
 * @returns {boolean} True if this is an HDR action
 */
export function isHdrAction(actionName) {
  if (!actionName) return false
  const lower = actionName.toLowerCase()
  return HDR_ACTION_NAMES.some((name) => lower.includes(name))
}
