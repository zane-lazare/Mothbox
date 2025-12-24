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
 * Truncate text with ellipsis if longer than maxLength
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text with ellipsis if needed
 */
function truncateText(text, maxLength) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
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

  // Prepare display text - truncate in both modes to prevent layout breaks
  const displayName = compact
    ? truncateText(pattern_name, 10)
    : truncateText(pattern_name, 30)

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
    ? 'text-xs font-medium truncate max-w-[80px]'
    : 'text-sm font-medium truncate max-w-[200px]'

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
      {/* Time display (hidden in compact mode) */}
      {!compact && (
        <span className="text-xs font-semibold whitespace-nowrap">{timeStr}</span>
      )}

      {/* Pattern name */}
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
