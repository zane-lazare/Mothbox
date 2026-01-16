/**
 * WeekTimeline - Time-slot based week view (Calendar UX Improvements)
 *
 * Displays executions in a grid: 7 days × 4 time slots (Morning/Midday/Evening/Night)
 * More useful for planning than the cell-based week view.
 *
 * @module components/scheduler/CalendarView/WeekTimeline
 */

import { useMemo } from 'react'
import PropTypes from 'prop-types'
import ExecutionMarker from './ExecutionMarker'
import MoonPhaseIcon from './MoonPhaseIcon'
import { getWeekDates, isToday, getDateKey } from './calendarUtils'

/**
 * Time slots for grouping executions
 * Covers full 24 hours in 4 periods
 */
const TIME_SLOTS = [
  { id: 'morning', label: 'Morning', sublabel: '6am-12pm', startHour: 6, endHour: 11 },
  { id: 'midday', label: 'Midday', sublabel: '12pm-6pm', startHour: 12, endHour: 17 },
  { id: 'evening', label: 'Evening', sublabel: '6pm-9pm', startHour: 18, endHour: 20 },
  { id: 'night', label: 'Night', sublabel: '9pm-6am', startHour: 21, endHour: 5, spansDay: true },
]

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/**
 * Determine which time slot an hour belongs to
 * @param {number} hour - Hour (0-23)
 * @returns {string} Time slot ID
 */
function getTimeSlotForHour(hour) {
  if (hour >= 6 && hour <= 11) return 'morning'
  if (hour >= 12 && hour <= 17) return 'midday'
  if (hour >= 18 && hour <= 20) return 'evening'
  // Night: 21-23 and 0-5
  return 'night'
}

/**
 * Group executions by day and time slot
 * @param {Array} executions - Array of execution objects
 * @param {Date[]} weekDates - Array of 7 dates for the week
 * @returns {Object} Grouped executions { 'dayIndex-slotId': [executions] }
 */
function groupByDayAndSlot(executions, weekDates) {
  const grouped = {}

  // Initialize empty arrays for all day-slot combinations
  weekDates.forEach((_, dayIndex) => {
    TIME_SLOTS.forEach((slot) => {
      grouped[`${dayIndex}-${slot.id}`] = []
    })
  })

  if (!executions || !Array.isArray(executions)) {
    return grouped
  }

  executions.forEach((exec) => {
    if (!exec.start_time) return

    const execDate = new Date(exec.start_time)
    if (isNaN(execDate.getTime())) return

    // Find matching day in week
    const dayIndex = weekDates.findIndex(
      (d) =>
        d.getDate() === execDate.getDate() &&
        d.getMonth() === execDate.getMonth() &&
        d.getFullYear() === execDate.getFullYear()
    )

    if (dayIndex === -1) return

    const hour = execDate.getHours()
    const slotId = getTimeSlotForHour(hour)
    const key = `${dayIndex}-${slotId}`

    if (grouped[key]) {
      grouped[key].push(exec)
    }
  })

  // Sort executions within each slot by time
  Object.keys(grouped).forEach((key) => {
    grouped[key].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
  })

  return grouped
}

/**
 * WeekTimeline component
 *
 * @param {Object} props - Component props
 * @param {Date} props.currentDate - Any date within the target week
 * @param {Array} props.executions - Array of execution objects
 * @param {Object} props.moonPhases - Moon phases by date { 'YYYY-MM-DD': { phase, phase_name, illumination } }
 * @param {Function} props.onCellClick - Cell click handler (receives date)
 * @param {Function} props.onExecutionClick - Execution click handler (receives execution)
 * @returns {JSX.Element} Week timeline component
 */
function WeekTimeline({
  currentDate,
  executions = [],
  moonPhases = {},
  onCellClick,
  onExecutionClick,
}) {
  // Get 7 days for the week (Sunday to Saturday)
  const weekDates = useMemo(() => getWeekDates(currentDate), [currentDate])

  // Group executions by day and time slot
  const groupedExecutions = useMemo(
    () => groupByDayAndSlot(executions, weekDates),
    [executions, weekDates]
  )

  // Max visible per cell before "+N more"
  const MAX_VISIBLE = 3

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden overflow-x-auto">
      {/* Header row with day names and dates (responsive grid) */}
      <div className="grid grid-cols-[60px_repeat(7,1fr)] sm:grid-cols-[80px_repeat(7,1fr)] bg-gray-50 dark:bg-gray-800 min-w-[600px]">
        {/* Empty corner cell */}
        <div className="p-1 sm:p-2 text-xs font-medium text-gray-500 border-r border-gray-200 dark:border-gray-700" />

        {/* Day headers */}
        {weekDates.map((date, i) => {
          const isTodayDate = isToday(date)
          const dateKey = getDateKey(date)
          const moonPhase = moonPhases[dateKey]

          return (
            <div
              key={i}
              className="p-2 text-center border-l border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              onClick={() => onCellClick(date)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onCellClick(date)
                }
              }}
            >
              <div className="flex items-center justify-center gap-1">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {DAYS[date.getDay()]}
                </span>
                {moonPhase && <MoonPhaseIcon phase={moonPhase} size="xs" />}
              </div>
              <div
                className={
                  isTodayDate
                    ? 'bg-blue-500 text-white rounded-full w-7 h-7 mx-auto flex items-center justify-center font-semibold text-sm'
                    : 'text-sm font-semibold dark:text-gray-200'
                }
              >
                {date.getDate()}
              </div>
            </div>
          )
        })}
      </div>

      {/* Time slot rows (responsive grid matching header) */}
      {TIME_SLOTS.map((slot) => (
        <div
          key={slot.id}
          className="grid grid-cols-[60px_repeat(7,1fr)] sm:grid-cols-[80px_repeat(7,1fr)] border-t border-gray-200 dark:border-gray-700 min-w-[600px]"
        >
          {/* Time slot label */}
          <div className="p-1 sm:p-2 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
            <div className="text-[10px] sm:text-xs font-medium text-gray-600 dark:text-gray-300">
              {slot.label}
            </div>
            <div className="text-[9px] sm:text-[10px] text-gray-400 dark:text-gray-500 hidden sm:block">
              {slot.sublabel}
            </div>
          </div>

          {/* Day cells for this time slot */}
          {weekDates.map((date, dayIndex) => {
            const cellKey = `${dayIndex}-${slot.id}`
            const cellExecutions = groupedExecutions[cellKey] || []
            const visibleExecutions = cellExecutions.slice(0, MAX_VISIBLE)
            const hiddenCount = cellExecutions.length - visibleExecutions.length

            return (
              <div
                key={dayIndex}
                className="p-1 min-h-16 border-l border-gray-200 dark:border-gray-700 space-y-0.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                onClick={() => onCellClick(date)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onCellClick(date)
                  }
                }}
              >
                {visibleExecutions.map((exec, i) => (
                  <ExecutionMarker
                    key={exec.id || `${exec.pattern_id}-${exec.start_time}-${i}`}
                    execution={exec}
                    onClick={() => onExecutionClick(exec)}
                    compact
                  />
                ))}
                {hiddenCount > 0 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onCellClick(date)
                    }}
                    className="text-[10px] text-blue-500 dark:text-blue-400 hover:underline"
                    title={`${hiddenCount} more execution${hiddenCount > 1 ? 's' : ''}`}
                  >
                    +{hiddenCount} more
                  </button>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}

WeekTimeline.propTypes = {
  currentDate: PropTypes.instanceOf(Date).isRequired,
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      pattern_id: PropTypes.string.isRequired,
      pattern_name: PropTypes.string.isRequired,
      start_time: PropTypes.string.isRequired,
    })
  ),
  moonPhases: PropTypes.objectOf(
    PropTypes.shape({
      phase: PropTypes.string,
      phase_name: PropTypes.string,
      illumination: PropTypes.number,
    })
  ),
  onCellClick: PropTypes.func.isRequired,
  onExecutionClick: PropTypes.func.isRequired,
}

export default WeekTimeline
