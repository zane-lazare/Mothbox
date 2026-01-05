/**
 * ExecutionChip - Execution marker within DayTimeline (Issue #326)
 *
 * Displays individual scheduled execution as a small chip/pill.
 * Shows time and action name with color-coding by action type.
 * Supports conflict highlighting with ring indicators.
 *
 * @module components/scheduler/DayTimeline/ExecutionChip
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { CHIP_CONFLICT_RINGS } from './dayTimelineConstants'
import {
  formatTimeShort,
  getActionTypeDisplay,
  getExecutionTestId,
} from './dayTimelineUtils'

/**
 * ExecutionChip component
 *
 * @param {Object} props - Component props
 * @param {Object} props.execution - Execution object
 * @param {string} props.execution.pattern_id - Pattern/routine identifier
 * @param {string} props.execution.pattern_name - Pattern display name
 * @param {string} props.execution.start_time - ISO datetime string
 * @param {Array} [props.execution.actions] - Array of action objects
 * @param {Function} [props.onClick] - Click handler
 * @param {string|null} [props.conflictSeverity] - Conflict severity ('error'|'warning'|null)
 * @returns {JSX.Element} Execution chip component
 *
 * @example
 * <ExecutionChip
 *   execution={{ pattern_id: 'p1', pattern_name: 'Photo', start_time: '...' }}
 *   onClick={() => handleClick(execution)}
 * />
 *
 * @example
 * // With conflict highlighting
 * <ExecutionChip
 *   execution={execution}
 *   conflictSeverity="error"
 * />
 */
function ExecutionChip({ execution, onClick, conflictSeverity = null }) {
  const { pattern_name, start_time, actions } = execution

  // Format the time display
  const timeStr = formatTimeShort(start_time)

  // Determine action type from first action, or default to camera
  const actionType = actions?.[0]?.action_type || 'camera'
  const actionName = actions?.[0]?.action_name || pattern_name

  // Get color classes for this action type
  const colorClasses = getActionTypeDisplay(actionType, actionName)

  // Get conflict ring class if applicable
  const conflictRing = conflictSeverity ? CHIP_CONFLICT_RINGS[conflictSeverity] : ''

  // Build chip display text
  const displayText = actionName ? `${timeStr} ${actionName}` : timeStr

  // Build class string
  const chipClasses = [
    'text-xs px-2 py-0.5 rounded',
    colorClasses.bg,
    colorClasses.text,
    conflictRing,
    onClick ? 'cursor-pointer hover:brightness-110 transition-all' : '',
    'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-400',
  ]
    .filter(Boolean)
    .join(' ')

  // Build aria-label
  const ariaLabel = conflictSeverity
    ? `${pattern_name} at ${timeStr} - ${conflictSeverity} conflict`
    : `${pattern_name} at ${timeStr}`

  const handleClick = (e) => {
    e.stopPropagation()
    if (onClick) {
      onClick()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      e.stopPropagation()
      if (onClick) {
        onClick()
      }
    }
  }

  return (
    <button
      type="button"
      data-testid={getExecutionTestId(execution)}
      className={chipClasses}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      title={`${pattern_name} at ${timeStr}`}
      aria-label={ariaLabel}
    >
      {displayText}
    </button>
  )
}

ExecutionChip.propTypes = {
  /** Execution object containing pattern and timing details */
  execution: PropTypes.shape({
    pattern_id: PropTypes.string.isRequired,
    pattern_name: PropTypes.string.isRequired,
    start_time: PropTypes.string.isRequired,
    actions: PropTypes.arrayOf(
      PropTypes.shape({
        time: PropTypes.string,
        action_name: PropTypes.string,
        action_type: PropTypes.string,
        offset_minutes: PropTypes.number,
      })
    ),
  }).isRequired,
  /** Click handler for when chip is selected */
  onClick: PropTypes.func,
  /** Conflict severity for highlighting ('error'|'warning'|null) */
  conflictSeverity: PropTypes.oneOf(['error', 'warning', null]),
}

export default memo(ExecutionChip)
