/**
 * WeekHourlyTimeline constants
 *
 * Configuration and styling constants for the week hourly timeline.
 *
 * @module components/scheduler/WeekHourlyTimeline/weekTimelineConstants
 */

// Re-export shared constants
export {
  ACTION_TYPE_COLORS,
  DEFAULT_ACTION_COLORS,
  CONFLICT_COLORS,
  ROW_CONFLICT_STYLES,
  ACTION_TYPE_LABELS,
  isHdrAction,
  getActionSolidColor,
  getActionTypeDisplay,
} from '../constants'

/**
 * Week view configuration
 */
export const WEEK_VIEW_CONFIG = {
  /** Maximum execution chips visible per hour cell before "+N more" */
  MAX_VISIBLE_CHIPS: 3,

  /** Breakpoint (px) below which we show mobile single-day view */
  MOBILE_BREAKPOINT: 640,

  /** Minimum swipe distance (px) to trigger day navigation */
  SWIPE_THRESHOLD: 50,

  /** Hour row height class */
  HOUR_ROW_HEIGHT: 'min-h-8',
}

/**
 * Legend items for the week view (same as day view)
 */
export const LEGEND_ITEMS = [
  { label: 'Camera', color: 'bg-blue-400' },
  { label: 'GPIO', color: 'bg-orange-400' },
  { label: 'HDR', color: 'bg-purple-400' },
  { label: 'GPS Sync', color: 'bg-green-400' },
  { label: 'Service', color: 'bg-gray-400' },
  { label: 'Collision', color: 'ring-2 ring-red-400 bg-transparent' },
  { label: 'Warning', color: 'ring-2 ring-yellow-400 bg-transparent' },
]

/**
 * Day header styling classes
 */
export const DAY_HEADER_STYLES = {
  base: 'p-2 text-center border-b border-gray-700 cursor-pointer hover:bg-gray-800 transition-colors',
  today: 'bg-blue-500 text-white rounded-full w-7 h-7 mx-auto flex items-center justify-center font-semibold text-sm',
  normal: 'text-sm font-semibold dark:text-gray-200',
}

/**
 * Chip conflict ring classes for week view
 */
export const CHIP_CONFLICT_RINGS = {
  error: 'ring-1 ring-red-400',
  warning: 'ring-1 ring-yellow-400',
}
