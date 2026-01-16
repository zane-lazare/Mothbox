/**
 * ExecutionMarker - Visual marker for scheduled pattern executions (Issue #228)
 *
 * Displays pattern executions as colored pills/badges in the calendar view.
 * Supports both compact (month view) and full (week/day view) display modes.
 * Supports conflict highlighting for schedule conflicts (Issue #229).
 *
 * @module components/scheduler/CalendarView/ExecutionMarker
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { getPatternColor, formatTime } from './calendarUtils'
import { ACTION_TYPE_COLORS } from '../constants'

/**
 * Static color class mappings for Tailwind JIT compatibility.
 * Dynamic class construction like `dark:bg-${color}-500` doesn't work with
 * Tailwind's JIT compiler, so we map each bg color to its corresponding
 * dark mode and focus ring classes.
 */
const COLOR_CLASS_MAP = {
  'bg-blue-500': { dark: 'dark:bg-blue-600', ring: 'focus:ring-blue-400' },
  'bg-green-500': { dark: 'dark:bg-green-600', ring: 'focus:ring-green-400' },
  'bg-purple-500': { dark: 'dark:bg-purple-600', ring: 'focus:ring-purple-400' },
  'bg-orange-500': { dark: 'dark:bg-orange-600', ring: 'focus:ring-orange-400' },
  'bg-pink-500': { dark: 'dark:bg-pink-600', ring: 'focus:ring-pink-400' },
  'bg-cyan-500': { dark: 'dark:bg-cyan-600', ring: 'focus:ring-cyan-400' },
}

/**
 * Conflict severity ring classes for highlighting conflicting executions (Issue #229).
 * Error severity shows red ring, warning severity shows amber ring.
 */
const CONFLICT_RING_CLASSES = {
  error: 'ring-2 ring-red-500 dark:ring-red-400',
  warning: 'ring-2 ring-amber-500 dark:ring-amber-400',
}

/**
 * Get the primary action type from execution's actions array
 * @param {Object} execution - Execution with actions array
 * @returns {string} Action type key (camera, gpio, etc.) or 'camera' as default
 */
function getPrimaryActionType(execution) {
  const firstAction = execution.actions?.[0]
  if (!firstAction?.action_type) return 'camera'

  // Check for HDR in action name
  if (
    firstAction.action_type === 'camera' &&
    firstAction.action_name?.toLowerCase().includes('hdr')
  ) {
    return 'hdr'
  }
  return firstAction.action_type
}

/**
 * ExecutionMarker component
 *
 * @param {Object} props - Component props
 * @param {Object} props.execution - Execution object
 * @param {string} props.execution.pattern_id - Pattern identifier for color selection
 * @param {string} props.execution.pattern_name - Pattern display name
 * @param {string} props.execution.start_time - ISO datetime string
 * @param {string} [props.execution.end_time] - ISO datetime string
 * @param {string} [props.execution.trigger_info] - Trigger information
 * @param {Array} [props.execution.actions] - Array of action objects
 * @param {Function} props.onClick - Click handler
 * @param {boolean} [props.compact=false] - Compact display mode for month view
 * @param {string|null} [props.conflictSeverity=null] - Conflict severity for highlighting ('error'|'warning'|null)
 * @param {string} [props.conflictMessage] - Message describing the conflict
 * @returns {JSX.Element} Execution marker component
 *
 * @example
 * // Full mode (week/day view)
 * <ExecutionMarker
 *   execution={execution}
 *   onClick={() => handleClick(execution)}
 * />
 *
 * @example
 * // Compact mode (month view)
 * <ExecutionMarker
 *   execution={execution}
 *   onClick={() => handleClick(execution)}
 *   compact
 * />
 *
 * @example
 * // With conflict highlighting (Issue #229)
 * <ExecutionMarker
 *   execution={execution}
 *   onClick={() => handleClick(execution)}
 *   conflictSeverity="error"
 *   conflictMessage="Camera resource conflict with Flash Photo"
 * />
 */
function ExecutionMarker({ execution, onClick, compact = false, conflictSeverity = null, conflictMessage = '' }) {
  const { pattern_id, pattern_name, start_time } = execution

  // Get consistent color for this pattern
  const colorClass = getPatternColor(pattern_id)

  // Get static dark mode and focus ring classes from mapping
  // Falls back to blue if color not in map (defensive)
  const colorMapping = COLOR_CLASS_MAP[colorClass] || COLOR_CLASS_MAP['bg-blue-500']

  // Format time from start_time
  const timeStr = formatTime(start_time)

  // Get action type color for indicator dot
  const actionType = getPrimaryActionType(execution)
  const actionColor = ACTION_TYPE_COLORS[actionType]?.solid || 'bg-blue-400'

  // Use full name - CSS truncation handles overflow
  const displayName = pattern_name

  // Get conflict ring classes if there's a conflict (Issue #229)
  const conflictRingClass = conflictSeverity ? CONFLICT_RING_CLASSES[conflictSeverity] : ''

  // Base classes for the marker - using static classes for Tailwind JIT
  const baseClasses = [
    'inline-flex items-center gap-1.5',
    'rounded-full px-2 py-1',
    'text-white',
    colorClass,
    colorMapping.dark,
    'cursor-pointer transition-all duration-150',
    'hover:brightness-110 hover:scale-105',
    'focus:outline-none focus:ring-2 focus:ring-offset-1',
    colorMapping.ring,
    conflictRingClass, // Add conflict highlighting if present
  ].filter(Boolean).join(' ')

  const textClasses = compact
    ? 'text-[10px] font-medium truncate max-w-[60px]'
    : 'text-sm font-medium truncate max-w-[180px]'

  const handleClick = (e) => {
    e.stopPropagation()
    onClick()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      e.stopPropagation()
      onClick()
    }
  }

  // Build title and aria-label, including conflict info if present (Issue #229)
  const baseTitle = `${pattern_name} at ${timeStr}`
  const baseAriaLabel = `Scheduled execution: ${pattern_name} at ${timeStr}`

  const title = conflictMessage ? `${baseTitle} - ${conflictMessage}` : baseTitle
  const ariaLabel = conflictSeverity
    ? `${baseAriaLabel} - conflict: ${conflictMessage || conflictSeverity}`
    : baseAriaLabel

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={baseClasses}
      title={title}
      aria-label={ariaLabel}
    >
      {/* Action type indicator dot */}
      <span
        className={`w-2 h-2 rounded-full flex-shrink-0 ${actionColor}`}
        aria-hidden="true"
      />

      {/* Time display - always show but smaller in compact mode */}
      <span
        className={
          compact
            ? 'text-[10px] font-medium text-white/80 whitespace-nowrap'
            : 'text-xs font-semibold whitespace-nowrap'
        }
      >
        {timeStr}
      </span>

      {/* Pattern name with CSS truncation */}
      <span className={textClasses}>{displayName}</span>
    </button>
  )
}

ExecutionMarker.propTypes = {
  /** Execution object containing pattern and timing details */
  execution: PropTypes.shape({
    pattern_id: PropTypes.string.isRequired,
    pattern_name: PropTypes.string.isRequired,
    start_time: PropTypes.string.isRequired,
    end_time: PropTypes.string,
    trigger_info: PropTypes.string,
    actions: PropTypes.array,
  }).isRequired,
  /** Click handler for when marker is selected */
  onClick: PropTypes.func.isRequired,
  /** Compact display mode for month view */
  compact: PropTypes.bool,
  /** Conflict severity for highlighting ('error'|'warning'|null) - Issue #229 */
  conflictSeverity: PropTypes.oneOf(['error', 'warning', null]),
  /** Message describing the conflict - Issue #229 */
  conflictMessage: PropTypes.string,
}

export default memo(ExecutionMarker)
