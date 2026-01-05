/**
 * DayTimeline - Hourly timeline for day view with conflict highlighting (Issue #326)
 *
 * Main container component that displays a 24-hour timeline for a single day.
 * Shows scheduled executions as chips within hourly rows, with visual indicators
 * for time collisions (blocking errors) and GPIO state warnings (non-blocking).
 *
 * Features:
 * - 24 hourly rows (0-23)
 * - Execution chips color-coded by action type
 * - Red highlighting for time collisions
 * - Yellow highlighting for GPIO warnings
 * - Conflict summary banner
 *
 * @module components/scheduler/DayTimeline
 */

import { memo, useMemo } from 'react'
import PropTypes from 'prop-types'
import HourRow from './HourRow'
import ConflictSummary from './ConflictSummary'
import { LEGEND_ITEMS } from './dayTimelineConstants'
import {
  groupExecutionsByHour,
  getConflictForHour,
  getConflictForExecution,
} from './dayTimelineUtils'

/**
 * Legend component for the timeline
 */
function TimelineLegend() {
  return (
    <div className="flex items-center gap-6 text-xs text-gray-500 mb-6">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${item.isRing ? item.color : item.color}`}
          />
          {item.label}
        </div>
      ))}
    </div>
  )
}

/**
 * DayTimeline component
 *
 * @param {Object} props - Component props
 * @param {string} props.date - ISO date string (YYYY-MM-DD) for the day to display
 * @param {Array} [props.executions] - Array of execution objects from preview API
 * @param {Array} [props.conflicts] - Array of conflict objects from preview API
 * @param {Function} [props.onExecutionClick] - Callback when an execution chip is clicked
 * @returns {JSX.Element} Day timeline component
 *
 * @example
 * <DayTimeline
 *   date="2025-12-17"
 *   executions={previewData.executions}
 *   conflicts={previewData.conflicts}
 *   onExecutionClick={handleExecutionClick}
 * />
 */
function DayTimeline({
  date,
  executions = [],
  conflicts = [],
  onExecutionClick,
}) {
  // Generate array of hours [0, 1, 2, ..., 23]
  const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), [])

  // Group executions by hour
  const executionsByHour = useMemo(
    () => groupExecutionsByHour(executions, date),
    [executions, date]
  )

  // Build map of execution pattern_id to conflict for chip highlighting
  const executionConflictsMap = useMemo(() => {
    const map = {}
    executions.forEach((execution) => {
      const conflict = getConflictForExecution(execution, conflicts)
      if (conflict) {
        map[execution.pattern_id] = conflict
      }
    })
    return map
  }, [executions, conflicts])

  // Check if there are any executions
  const hasExecutions = executions.length > 0

  // Empty state
  if (!hasExecutions) {
    return (
      <div
        data-testid="day-timeline"
        className="p-4"
        aria-label={`Day timeline for ${date}`}
      >
        <div
          data-testid="day-timeline-empty"
          className="text-center text-gray-500 dark:text-gray-400 py-8"
        >
          No scheduled events
        </div>
      </div>
    )
  }

  return (
    <div
      data-testid="day-timeline"
      className="p-4"
      aria-label={`Day timeline for ${date}`}
    >
      {/* Legend */}
      <TimelineLegend />

      {/* Conflict Summary */}
      {conflicts.length > 0 && <ConflictSummary conflicts={conflicts} />}

      {/* Timeline Grid */}
      <div className="border border-gray-800 rounded-lg divide-y divide-gray-800">
        {hours.map((hour) => {
          const hourExecutions = executionsByHour[hour] || []
          const hourConflict = getConflictForHour(conflicts, hour, date)

          return (
            <HourRow
              key={hour}
              hour={hour}
              executions={hourExecutions}
              conflict={hourConflict}
              onExecutionClick={onExecutionClick}
              executionConflicts={executionConflictsMap}
            />
          )
        })}
      </div>
    </div>
  )
}

DayTimeline.propTypes = {
  /** ISO date string (YYYY-MM-DD) for the day to display */
  date: PropTypes.string.isRequired,
  /** Array of execution objects from preview API */
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      pattern_id: PropTypes.string.isRequired,
      pattern_name: PropTypes.string.isRequired,
      start_time: PropTypes.string.isRequired,
      actions: PropTypes.arrayOf(
        PropTypes.shape({
          time: PropTypes.string,
          action_name: PropTypes.string,
          action_type: PropTypes.oneOf([
            'camera',
            'gpio',
            'gps_sync',
            'service',
          ]),
          offset_minutes: PropTypes.number,
        })
      ),
    })
  ),
  /** Array of conflict objects from preview API */
  conflicts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      conflict_type: PropTypes.oneOf([
        'time_overlap',
        'resource_contention',
        'gpio_state_conflict',
      ]),
      severity: PropTypes.oneOf(['error', 'warning']).isRequired,
      event1_id: PropTypes.string,
      event1_name: PropTypes.string,
      event2_id: PropTypes.string,
      event2_name: PropTypes.string,
      start_time: PropTypes.string,
      end_time: PropTypes.string,
      message: PropTypes.string,
    })
  ),
  /** Callback when an execution chip is clicked */
  onExecutionClick: PropTypes.func,
}

export default memo(DayTimeline)
