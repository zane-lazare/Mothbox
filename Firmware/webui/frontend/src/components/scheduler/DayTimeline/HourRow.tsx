/**
 * HourRow - Individual hour row in DayTimeline (Issue #326)
 *
 * Displays a single hour row with time label and execution chips.
 * Supports conflict highlighting with background colors and labels.
 *
 * @module components/scheduler/DayTimeline/HourRow
 */

import { memo } from 'react'
import ExecutionChip, { type Execution } from './ExecutionChip'
import { ROW_CONFLICT_STYLES } from './dayTimelineConstants'
import { formatHourLabel, getExecutionKey } from './dayTimelineUtils'

/**
 * Conflict object structure
 */
interface HourConflict {
  id?: string
  severity: 'error' | 'warning'
  message: string
  conflict_type?: string
}

/**
 * Execution conflict for highlighting individual chips
 */
interface ExecutionConflict {
  severity: 'error' | 'warning'
}

/**
 * Component props interface
 */
export interface HourRowProps {
  hour: number
  executions?: Execution[]
  conflict?: HourConflict | null
  onExecutionClick?: (execution: Execution) => void
  executionConflicts?: Record<string, ExecutionConflict>
}

/**
 * HourRow component
 *
 * @param {Object} props - Component props
 * @param {number} props.hour - Hour number (0-23)
 * @param {Array} [props.executions] - Array of executions for this hour
 * @param {Object} [props.conflict] - Conflict affecting this hour (if any)
 * @param {Function} [props.onExecutionClick] - Click handler for execution chips
 * @param {Object} [props.executionConflicts] - Map of execution pattern_id to conflict
 * @returns {JSX.Element} Hour row component
 *
 * @example
 * <HourRow hour={18} executions={hourExecutions} />
 *
 * @example
 * // With conflict
 * <HourRow
 *   hour={19}
 *   executions={hourExecutions}
 *   conflict={{ severity: 'error', message: 'Camera busy' }}
 * />
 */
function HourRow({
  hour,
  executions = [],
  conflict = null,
  onExecutionClick,
  executionConflicts = {},
}: HourRowProps) {
  // Get styling for this row based on conflict state
  const conflictState = conflict?.severity || 'none'
  const rowStyles = ROW_CONFLICT_STYLES[conflictState] || ROW_CONFLICT_STYLES.none

  // Format hour label
  const hourLabel = formatHourLabel(hour)

  // Build row classes
  const rowClasses = ['flex p-3', rowStyles.bg].filter(Boolean).join(' ')

  // Build hour label classes
  const labelClasses = ['w-12 text-xs', rowStyles.label].join(' ')

  const hasExecutions = executions.length > 0

  return (
    <div className={rowClasses} data-testid={`hour-row-${hour}`}>
      <span className={labelClasses}>{hourLabel}</span>

      {hasExecutions ? (
        <div className="flex gap-2 flex-wrap items-center">
          {executions.map((execution, index) => {
            // Check if this specific execution has a conflict
            const execConflict = executionConflicts[execution.pattern_id]
            const conflictSeverity = execConflict?.severity || null

            return (
              <ExecutionChip
                key={getExecutionKey(execution, index)}
                execution={execution}
                onClick={
                  onExecutionClick ? () => onExecutionClick(execution) : undefined
                }
                conflictSeverity={conflictSeverity}
              />
            )
          })}

          {/* Inline conflict message */}
          {conflict && (
            <span
              className={`text-xs ml-1 ${conflictState === 'error' ? 'text-red-400' : 'text-yellow-400'}`}
              data-testid={`conflict-${conflict.id || hour}`}
            >
              {conflict.message}
            </span>
          )}
        </div>
      ) : (
        <span className="text-xs text-gray-700 dark:text-gray-700">
          no executions
        </span>
      )}
    </div>
  )
}

export default memo(HourRow)
