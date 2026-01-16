/**
 * WeekHourRow - Compact hour cell for week view grid
 *
 * Displays executions for a single hour within a day column.
 * More compact than DayTimeline's HourRow - designed for 7-column grid.
 *
 * Features:
 * - Stacks chips vertically
 * - Conflict background styling
 * - Max 3 visible chips with "+N more" overflow
 * - No hour label (position indicates hour)
 *
 * @module components/scheduler/WeekHourlyTimeline/WeekHourRow
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import ExecutionChip from '../DayTimeline/ExecutionChip'
import { ROW_CONFLICT_STYLES, WEEK_VIEW_CONFIG } from './weekTimelineConstants'
import { getExecutionKey } from './weekTimelineUtils'

/**
 * WeekHourRow component
 *
 * @param {Object} props - Component props
 * @param {number} props.hour - Hour number (0-23), used for data-testid
 * @param {Array} [props.executions] - Executions for this hour cell
 * @param {Object} [props.conflict] - Conflict affecting this hour (if any)
 * @param {Function} [props.onExecutionClick] - Click handler for chips
 * @param {Object} [props.executionConflicts] - Map of pattern_id to conflict
 * @param {Function} [props.onOverflowClick] - Click handler for "+N more" button
 * @returns {JSX.Element} Week hour row component
 */
function WeekHourRow({
  hour,
  executions = [],
  conflict = null,
  onExecutionClick,
  executionConflicts = {},
  onOverflowClick,
}) {
  const maxVisible = WEEK_VIEW_CONFIG.MAX_VISIBLE_CHIPS
  const visibleExecutions = executions.slice(0, maxVisible)
  const hiddenCount = executions.length - maxVisible

  // Get conflict styling
  const conflictState = conflict?.severity || 'none'
  const rowStyles = ROW_CONFLICT_STYLES[conflictState] || ROW_CONFLICT_STYLES.none

  // Build cell classes
  const cellClasses = [
    'p-1 min-h-8 space-y-0.5',
    rowStyles.bg,
  ].filter(Boolean).join(' ')

  return (
    <div
      className={cellClasses}
      data-testid={`week-hour-${hour}`}
    >
      {visibleExecutions.map((execution, index) => {
        const execConflict = executionConflicts[execution.pattern_id]
        const conflictSeverity = execConflict?.severity || null

        return (
          <ExecutionChip
            key={getExecutionKey(execution, index)}
            execution={execution}
            onClick={onExecutionClick ? () => onExecutionClick(execution) : undefined}
            conflictSeverity={conflictSeverity}
          />
        )
      })}

      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            if (onOverflowClick) onOverflowClick()
          }}
          className="text-[10px] text-blue-400 hover:underline"
          title={`${hiddenCount} more execution${hiddenCount > 1 ? 's' : ''}`}
        >
          +{hiddenCount} more
        </button>
      )}
    </div>
  )
}

WeekHourRow.propTypes = {
  /** Hour number (0-23) */
  hour: PropTypes.number.isRequired,
  /** Executions for this hour cell */
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      pattern_id: PropTypes.string.isRequired,
      pattern_name: PropTypes.string.isRequired,
      start_time: PropTypes.string.isRequired,
      actions: PropTypes.array,
    })
  ),
  /** Conflict affecting this hour */
  conflict: PropTypes.shape({
    id: PropTypes.string,
    severity: PropTypes.oneOf(['error', 'warning']).isRequired,
    message: PropTypes.string,
  }),
  /** Click handler for execution chips */
  onExecutionClick: PropTypes.func,
  /** Map of pattern_id to conflict */
  executionConflicts: PropTypes.objectOf(
    PropTypes.shape({
      severity: PropTypes.oneOf(['error', 'warning']).isRequired,
    })
  ),
  /** Click handler for "+N more" overflow button */
  onOverflowClick: PropTypes.func,
}

export default memo(WeekHourRow)
