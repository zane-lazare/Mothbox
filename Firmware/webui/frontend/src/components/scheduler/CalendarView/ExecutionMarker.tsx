/**
 * ExecutionMarker - Visual marker for scheduled pattern executions (Issue #228)
 *
 * Displays pattern executions as small colored dots in the calendar view.
 * Color indicates action type; details shown in tooltip on hover.
 * Supports conflict highlighting for schedule conflicts (Issue #229).
 *
 * @module components/scheduler/CalendarView/ExecutionMarker
 */

import { memo } from 'react'
import { formatTime } from './calendarUtils'
import { getActionColor } from '@/utils/routineUtils'

/**
 * Action object structure
 */
interface Action {
  action_type?: string
  action_name?: string
  type?: string
}

/**
 * Execution object structure
 */
export interface Execution {
  pattern_id: string
  pattern_name: string
  start_time: string
  end_time?: string
  trigger_info?: string
  actions?: Action[]
}

/**
 * Conflict severity levels
 */
type ConflictSeverity = 'error' | 'warning' | null

/**
 * Component props interface
 */
export interface ExecutionMarkerProps {
  execution: Execution
  onClick: () => void
  conflictSeverity?: ConflictSeverity
  conflictMessage?: string
}

/**
 * Conflict severity ring classes for highlighting conflicting executions (Issue #229).
 * Error severity shows red ring, warning severity shows amber ring.
 */
const CONFLICT_RING_CLASSES = {
  error: 'ring-2 ring-red-500 dark:ring-red-400',
  warning: 'ring-2 ring-amber-500 dark:ring-amber-400',
} as const

/**
 * ExecutionMarker component
 *
 * @param {Object} props - Component props
 * @param {Object} props.execution - Execution object
 * @param {string} props.execution.pattern_id - Pattern identifier
 * @param {string} props.execution.pattern_name - Pattern display name
 * @param {string} props.execution.start_time - ISO datetime string
 * @param {string} [props.execution.end_time] - ISO datetime string
 * @param {string} [props.execution.trigger_info] - Trigger information
 * @param {Array} [props.execution.actions] - Array of action objects
 * @param {Function} props.onClick - Click handler
 * @param {string|null} [props.conflictSeverity=null] - Conflict severity for highlighting ('error'|'warning'|null)
 * @param {string} [props.conflictMessage] - Message describing the conflict
 * @returns {JSX.Element} Execution marker component
 *
 * @example
 * <ExecutionMarker
 *   execution={execution}
 *   onClick={() => handleClick(execution)}
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
function ExecutionMarker({
  execution,
  onClick,
  conflictSeverity = null,
  conflictMessage = '',
}: ExecutionMarkerProps) {
  const { pattern_name, start_time, actions } = execution

  // Format time for tooltip/aria-label
  const timeStr = formatTime(start_time)

  // Get solid color class for the dot based on primary action (matches ScheduleCard style)
  const primaryAction = actions?.[0]
  const dotColor = getActionColor(primaryAction)

  // Get conflict ring classes if there's a conflict (Issue #229)
  const conflictRingClass = conflictSeverity
    ? CONFLICT_RING_CLASSES[conflictSeverity]
    : ''

  // Build class string for small colored dot
  const dotClasses = [
    'w-1.5 h-1.5 rounded-full',
    dotColor,
    conflictRingClass,
    'cursor-pointer transition-all duration-150',
    'hover:brightness-110',
    'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-400',
  ]
    .filter(Boolean)
    .join(' ')

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation()
    onClick()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      e.stopPropagation()
      onClick()
    }
  }

  // Build title and aria-label, including conflict info if present (Issue #229)
  const baseTitle = `${pattern_name} at ${timeStr}`
  const baseAriaLabel = `Scheduled execution: ${pattern_name} at ${timeStr}`

  const title = conflictMessage
    ? `${baseTitle} - ${conflictMessage}`
    : baseTitle
  const ariaLabel = conflictSeverity
    ? `${baseAriaLabel} - conflict: ${conflictMessage || conflictSeverity}`
    : baseAriaLabel

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={dotClasses}
      title={title}
      aria-label={ariaLabel}
    />
  )
}

export default memo(ExecutionMarker)
