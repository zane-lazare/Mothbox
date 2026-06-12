/**
 * ExecutionChip - Execution marker within DayTimeline (Issue #326)
 *
 * Displays individual scheduled execution as a small colored dot.
 * Color indicates action type; details shown in tooltip on hover.
 * Supports conflict highlighting with ring indicators.
 *
 * @module components/scheduler/DayTimeline/ExecutionChip
 */

import { memo } from 'react'
import { CHIP_CONFLICT_RINGS } from './dayTimelineConstants'
import {
  formatTimeShort,
  getExecutionTestId,
  type Execution,
  type ConflictSeverity,
} from './dayTimelineUtils'
import { getActionColor } from '@/utils/routineUtils'

/**
 * Conflict severity levels (including null for no conflict)
 */
type ConflictSeverityOrNull = ConflictSeverity | null

/**
 * Component props interface
 */
export interface ExecutionChipProps {
  execution: Execution
  onClick?: () => void
  conflictSeverity?: ConflictSeverityOrNull
}

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
function ExecutionChip({ execution, onClick, conflictSeverity = null }: ExecutionChipProps) {
  const { pattern_name, start_time, actions } = execution

  // Format the time for tooltip/aria-label
  const timeStr = formatTimeShort(start_time)

  // Find the "primary" action - prefer camera/gps_sync over flash_on/flash_off/attract_on/attract_off
  const auxiliaryActions = ['flash_on', 'flash_off', 'attract_on', 'attract_off']
  const primaryAction =
    actions?.find((a) => !auxiliaryActions.includes(a.action_name || '')) ||
    actions?.[0]

  // Get solid color class for the dot (matches ScheduleCard style)
  const dotColor = getActionColor(primaryAction)

  // Get conflict ring class if applicable
  const conflictRing = conflictSeverity
    ? CHIP_CONFLICT_RINGS[conflictSeverity]
    : ''

  // Build class string for small colored dot
  const chipClasses = [
    'w-1.5 h-1.5 rounded-full',
    dotColor,
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

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation()
    if (onClick) {
      onClick()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
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
    />
  )
}

export default memo(ExecutionChip)
