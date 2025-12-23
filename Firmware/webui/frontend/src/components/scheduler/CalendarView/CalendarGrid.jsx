/**
 * CalendarGrid - Main calendar grid layout (Issue #228)
 *
 * Renders calendar grid with date cells for month/week/day views.
 * Manages execution grouping and moon phase data distribution.
 *
 * @module components/scheduler/CalendarView/CalendarGrid
 */

import { useMemo } from 'react'
import PropTypes from 'prop-types'
import CalendarCell from './CalendarCell'
import {
  getMonthGridDates,
  getWeekDates,
  groupExecutionsByDate,
  isToday,
  formatTime,
  getPatternColor,
} from './calendarUtils'

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/**
 * Get timezone-agnostic date key from Date object (YYYY-MM-DD format)
 * Uses local date components to avoid UTC conversion issues
 *
 * @param {Date} date - The date to convert
 * @returns {string} Date key in YYYY-MM-DD format
 */
function getDateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * CalendarGrid component
 *
 * @param {Object} props - Component props
 * @param {string} props.viewMode - 'month', 'week', or 'day' (required)
 * @param {Date} props.currentDate - The current date being displayed (required)
 * @param {Array} props.executions - Raw executions array from API
 * @param {Object} props.moonPhases - Moon phases by date { 'YYYY-MM-DD': { phase, phase_name, illumination } }
 * @param {Function} props.onCellClick - Cell click handler (receives date)
 * @param {Function} props.onExecutionClick - Execution click handler (receives execution)
 * @returns {JSX.Element} Calendar grid component
 *
 * @example
 * <CalendarGrid
 *   viewMode="month"
 *   currentDate={new Date(2025, 11, 17)}
 *   executions={executionsArray}
 *   moonPhases={moonPhasesObject}
 *   onCellClick={(date) => handleDateClick(date)}
 *   onExecutionClick={(exec) => handleExecutionClick(exec)}
 * />
 */
function CalendarGrid({
  viewMode,
  currentDate,
  executions = [],
  moonPhases = {},
  onCellClick,
  onExecutionClick,
}) {
  // Group executions by date (memoized for performance)
  const executionsByDate = useMemo(
    () => groupExecutionsByDate(executions),
    [executions]
  )

  // Month View: 7x6 grid with day headers
  if (viewMode === 'month') {
    const gridDates = getMonthGridDates(
      currentDate.getFullYear(),
      currentDate.getMonth()
    )

    return (
      <div className="grid grid-cols-7 border-t border-l border-gray-200 dark:border-gray-700">
        {/* Day-of-week headers */}
        {DAYS.map((day) => (
          <div
            key={day}
            className="py-2 text-center text-sm font-medium text-gray-500 dark:text-gray-400 border-r border-b border-gray-200 dark:border-gray-700"
          >
            {day}
          </div>
        ))}

        {/* Calendar cells - 42 cells (6 weeks) */}
        {gridDates.map((date) => {
          const dateKey = getDateKey(date)
          const isCurrentMonth = date.getMonth() === currentDate.getMonth()

          return (
            <CalendarCell
              key={dateKey}
              date={date}
              isCurrentMonth={isCurrentMonth}
              executions={executionsByDate[dateKey] || []}
              moonPhase={moonPhases[dateKey] || null}
              onClick={onCellClick}
              onExecutionClick={onExecutionClick}
            />
          )
        })}
      </div>
    )
  }

  // Week View: 7 columns with date headers
  if (viewMode === 'week') {
    const weekDates = getWeekDates(currentDate)

    return (
      <div className="grid grid-cols-7 border-t border-l border-gray-200 dark:border-gray-700">
        {/* Day-of-week headers with dates */}
        {weekDates.map((date) => {
          const isTodayDate = isToday(date)

          return (
            <div
              key={getDateKey(date)}
              className="py-2 text-center border-r border-b border-gray-200 dark:border-gray-700"
            >
              <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {DAYS[date.getDay()]}
              </div>
              <div
                className={
                  isTodayDate
                    ? 'bg-blue-500 text-white rounded-full w-8 h-8 mx-auto flex items-center justify-center font-semibold'
                    : 'text-lg dark:text-gray-200'
                }
              >
                {date.getDate()}
              </div>
            </div>
          )
        })}

        {/* Week cells */}
        {weekDates.map((date) => {
          const dateKey = getDateKey(date)

          return (
            <CalendarCell
              key={dateKey}
              date={date}
              isCurrentMonth={true}
              executions={executionsByDate[dateKey] || []}
              moonPhase={moonPhases[dateKey] || null}
              onClick={onCellClick}
              onExecutionClick={onExecutionClick}
            />
          )
        })}
      </div>
    )
  }

  // Day View: Single day with all executions listed
  if (viewMode === 'day') {
    const currentDateKey = getDateKey(currentDate)
    const dayExecutions = executionsByDate[currentDateKey] || []

    // Format full date for header
    const monthNames = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ]
    const dayNames = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
    ]

    const fullDate = `${dayNames[currentDate.getDay()]}, ${
      monthNames[currentDate.getMonth()]
    } ${currentDate.getDate()}, ${currentDate.getFullYear()}`

    return (
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        {/* Day header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {fullDate}
          </div>
        </div>

        {/* Day content - show all executions for the day */}
        <div className="p-4 space-y-2">
          {dayExecutions.map((exec) => (
            <div
              key={exec.start_time}
              className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors duration-150"
              onClick={() => onExecutionClick(exec)}
              role="button"
              tabIndex={0}
              aria-label={`${exec.pattern_name} at ${formatTime(exec.start_time)}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onExecutionClick(exec)
                }
              }}
            >
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${getPatternColor(exec.pattern_id)}`}
                />
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {exec.pattern_name}
                </span>
                <span className="text-gray-500 dark:text-gray-400 ml-auto">
                  {formatTime(exec.start_time)}
                </span>
              </div>
            </div>
          ))}

          {/* Empty state */}
          {dayExecutions.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">
              No executions scheduled
            </p>
          )}
        </div>
      </div>
    )
  }

  return null
}

CalendarGrid.propTypes = {
  viewMode: PropTypes.oneOf(['month', 'week', 'day']).isRequired,
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

export default CalendarGrid
