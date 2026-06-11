/**
 * DayTimeline - Hourly timeline for day view with cycle-aware rendering (Issue #326)
 *
 * Main container component that displays a timeline for a schedule cycle.
 * Shows scheduled executions as chips within hourly rows, with visual indicators
 * for time collisions (blocking errors) and GPIO state warnings (non-blocking).
 *
 * Features:
 * - Cycle-aware hour display (e.g., 17-23, 0-6 for overnight schedules)
 * - Automatic collapsing of repetitive consecutive hours
 * - Execution chips color-coded by action type
 * - Red highlighting for time collisions
 * - Yellow highlighting for GPIO warnings
 * - Conflict summary banner
 *
 * @module components/scheduler/DayTimeline
 */

import { memo, useMemo } from 'react'
import HourRow from './HourRow'
import ConflictSummary from './ConflictSummary'
import type { Execution } from './ExecutionChip'
import {
  groupExecutionsByHourCycleAware,
  getConflictForHour,
  getConflictForExecution,
  getCycleHours,
  collapseRepetitiveHours,
  getLocalDateFromIso,
  getNextDateKey,
  getHourFromIsoTime,
} from './dayTimelineUtils'

/**
 * Cycle information for schedule rendering
 */
interface CycleInfo {
  start_hour?: number
  end_hour?: number
  spans_midnight?: boolean
  suggested_preview_days?: number
}

/**
 * Conflict type identifiers
 */
type ConflictType = 'time_overlap' | 'resource_contention' | 'gpio_state_conflict'

/**
 * Conflict object structure
 */
interface Conflict {
  id?: string
  conflict_type?: ConflictType
  severity: 'error' | 'warning'
  event1_id?: string
  event1_name?: string
  event2_id?: string
  event2_name?: string
  start_time?: string
  end_time?: string
  message?: string
}

/**
 * Component props interface
 */
export interface DayTimelineProps {
  date: string
  executions?: Execution[]
  conflicts?: Conflict[]
  cycleInfo?: CycleInfo | null
  onExecutionClick?: (execution: Execution) => void
}

/**
 * Collapsed hours indicator row
 * Shows "... continues" when repetitive hours are collapsed
 */
const CollapsedIndicator = memo(function CollapsedIndicator({ count }: { count: number }) {
  return (
    <div className="flex p-3 text-gray-600 dark:text-gray-500">
      <span className="w-14 text-xs">...</span>
      <span className="text-xs">
        continues ({count} similar hour{count > 1 ? 's' : ''})
      </span>
    </div>
  )
})

/**
 * DayTimeline component
 *
 * @param {Object} props - Component props
 * @param {string} props.date - ISO date string (YYYY-MM-DD) for the day to display
 * @param {Array} [props.executions] - Array of execution objects from preview API
 * @param {Array} [props.conflicts] - Array of conflict objects from preview API
 * @param {Object} [props.cycleInfo] - Cycle info from preview API for cycle-aware rendering
 * @param {Function} [props.onExecutionClick] - Callback when an execution chip is clicked
 * @returns {JSX.Element} Day timeline component
 *
 * @example
 * <DayTimeline
 *   date="2025-12-17"
 *   executions={previewData.executions}
 *   conflicts={previewData.conflicts}
 *   cycleInfo={previewData.cycle_info}
 *   onExecutionClick={handleExecutionClick}
 * />
 */
function DayTimeline({
  date,
  executions = [],
  conflicts = [],
  cycleInfo = null,
  onExecutionClick,
}: DayTimelineProps) {
  // Get cycle-aware hours array (e.g., [17, 18, ..., 23, 0, 1, ..., 6] for overnight)
  const cycleHours = useMemo(
    () => getCycleHours(cycleInfo),
    [cycleInfo]
  )

  // Filter executions to those matching the specified date.
  // For overnight schedules (spans_midnight), also include next-day entries
  // up to end_hour so the full dusk-to-dawn cycle appears on one day.
  const filteredExecutions = useMemo(() => {
    if (!executions || !date) return executions

    const nextDate =
      cycleInfo?.spans_midnight ? getNextDateKey(date) : null
    const endHour = cycleInfo?.end_hour ?? 24

    return executions.filter((exec) => {
      const execDate = getLocalDateFromIso(exec.start_time)
      if (execDate === date) return true
      if (nextDate && execDate === nextDate) {
        const hour = getHourFromIsoTime(exec.start_time)
        return hour <= endHour
      }
      return false
    })
  }, [executions, date, cycleInfo])

  // Group executions by hour (cycle-aware)
  const executionsByHour = useMemo(
    () => groupExecutionsByHourCycleAware(filteredExecutions),
    [filteredExecutions]
  )

  // Collapse repetitive consecutive hours (>3 identical patterns)
  const displayHours = useMemo(
    () => collapseRepetitiveHours(cycleHours, executionsByHour),
    [cycleHours, executionsByHour]
  )

  // Build map of execution pattern_id to conflict for chip highlighting
  const executionConflictsMap = useMemo(() => {
    const map: Record<string, { severity: 'error' | 'warning' }> = {}
    executions.forEach((execution) => {
      const conflict = getConflictForExecution(execution, conflicts)
      if (conflict) {
        map[execution.pattern_id] = conflict
      }
    })
    return map
  }, [executions, conflicts])

  // Check if there are any executions for the filtered date
  const hasExecutions = filteredExecutions && filteredExecutions.length > 0

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
      {/* Conflict Summary */}
      {conflicts.length > 0 && <ConflictSummary conflicts={conflicts} />}

      {/* Timeline Grid */}
      <div className="border border-gray-800 rounded-lg divide-y divide-gray-800">
        {displayHours.map((item, index) => {
          // Collapsed indicator
          if (item.type === 'collapsed') {
            return <CollapsedIndicator key={`collapsed-${index}`} count={item.count} />
          }

          // Regular hour row
          const hour = item.hour
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

export default memo(DayTimeline)
