/**
 * DayColumn - Single day column in the week hourly timeline
 *
 * Displays a day header (name, date, moon phase) followed by hourly rows.
 * Used within the 7-column week grid layout.
 *
 * @module components/scheduler/WeekHourlyTimeline/DayColumn
 */

import { memo, useMemo } from 'react'
import PropTypes from 'prop-types'
import MoonPhaseIcon from '../CalendarView/MoonPhaseIcon'
import WeekHourRow from './WeekHourRow'
import { DAY_HEADER_STYLES } from './weekTimelineConstants'
import { getConflictForHour, getDateKey } from './weekTimelineUtils'

/**
 * DayColumn component
 *
 * @param {Object} props - Component props
 * @param {Date} props.date - The date for this column
 * @param {number} props.dayIndex - Day index within the week (0-6)
 * @param {number|null} [props.patternOffset=null] - Pattern offset for pattern mode (0, 7, 14, etc.)
 * @param {Array} props.displayHours - Array of hour objects to display (from collapseRepetitiveHours)
 * @param {Object} props.executionsByHour - Map of hour -> executions for this day
 * @param {Array} props.conflicts - Conflicts for this day
 * @param {Object} props.executionConflicts - Map of pattern_id -> conflict
 * @param {Object} [props.moonPhase] - Moon phase data for this day
 * @param {Function} props.onDayClick - Handler when day header is clicked
 * @param {Function} props.onExecutionClick - Handler when execution chip is clicked
 * @returns {JSX.Element} Day column component
 */
function DayColumn({
  date,
  dayIndex,
  patternOffset = null,
  displayHours,
  executionsByHour,
  conflicts,
  executionConflicts,
  moonPhase = null,
  onDayClick,
  onExecutionClick,
}) {
  const dateKey = useMemo(() => getDateKey(date), [date])

  // Handle day header click
  const handleDayClick = () => {
    if (onDayClick) onDayClick(date)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleDayClick()
    }
  }

  return (
    <div className="border-l border-gray-700 first:border-l-0">
      {/* Day Header */}
      <div
        className={DAY_HEADER_STYLES.base}
        onClick={handleDayClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={`Day ${dayIndex + 1}, click to view day details`}
      >
        <div className="flex items-center justify-center gap-1">
          {moonPhase && <MoonPhaseIcon phase={moonPhase} size="xs" />}
        </div>
        <div className={DAY_HEADER_STYLES.normal}>
          {dayIndex + 1}
        </div>
      </div>

      {/* Hour Rows */}
      <div className="divide-y divide-gray-800">
        {displayHours.map((item, index) => {
          // Handle collapsed indicator
          if (item.type === 'collapsed') {
            return (
              <div
                key={`collapsed-${index}`}
                className="p-1 text-center text-[10px] text-gray-600"
              >
                ...
              </div>
            )
          }

          // Regular hour row
          const hour = item.hour
          const hourExecutions = executionsByHour[hour] || []
          const hourConflict = getConflictForHour(conflicts, hour, dateKey)

          return (
            <WeekHourRow
              key={hour}
              hour={hour}
              executions={hourExecutions}
              conflict={hourConflict}
              onExecutionClick={onExecutionClick}
              executionConflicts={executionConflicts}
              onOverflowClick={() => onDayClick && onDayClick(date)}
            />
          )
        })}
      </div>
    </div>
  )
}

DayColumn.propTypes = {
  /** The date for this column */
  date: PropTypes.instanceOf(Date).isRequired,
  /** Day index within the week (0-6) */
  dayIndex: PropTypes.number.isRequired,
  /** Pattern offset for pattern mode (null for calendar mode) */
  patternOffset: PropTypes.number,
  /** Array of hour objects from collapseRepetitiveHours */
  displayHours: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.shape({ type: PropTypes.oneOf(['hour']), hour: PropTypes.number }),
      PropTypes.shape({ type: PropTypes.oneOf(['collapsed']), count: PropTypes.number }),
    ])
  ).isRequired,
  /** Map of hour -> executions for this day */
  executionsByHour: PropTypes.objectOf(PropTypes.array).isRequired,
  /** Conflicts for this day */
  conflicts: PropTypes.array.isRequired,
  /** Map of pattern_id -> conflict */
  executionConflicts: PropTypes.object.isRequired,
  /** Moon phase data */
  moonPhase: PropTypes.shape({
    phase: PropTypes.string,
    phase_name: PropTypes.string,
    illumination: PropTypes.number,
  }),
  /** Handler when day header is clicked */
  onDayClick: PropTypes.func.isRequired,
  /** Handler when execution chip is clicked */
  onExecutionClick: PropTypes.func,
}

export default memo(DayColumn)
