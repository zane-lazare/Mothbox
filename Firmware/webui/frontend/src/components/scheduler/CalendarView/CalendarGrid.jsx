/**
 * CalendarGrid - Main calendar grid layout (Issue #228)
 *
 * Renders calendar grid with date cells for month/week/day views.
 * Manages execution grouping and moon phase data distribution.
 * Day view uses DayTimeline component for hourly display with conflict highlighting (Issue #326).
 *
 * @module components/scheduler/CalendarView/CalendarGrid
 */

import { useMemo } from 'react'
import PropTypes from 'prop-types'
import CalendarCell from './CalendarCell'
import DayTimeline from '../DayTimeline'
import WeekHourlyTimeline from '../WeekHourlyTimeline'
import {
  getMonthGridDates,
  groupExecutionsByDate,
  getDateKey,
} from './calendarUtils'

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/**
 * CalendarGrid component
 *
 * @param {Object} props - Component props
 * @param {string} props.viewMode - 'month', 'week', or 'day' (required)
 * @param {Date} props.currentDate - The current date being displayed (required)
 * @param {Array} props.executions - Raw executions array from API
 * @param {Array} [props.conflicts] - Conflict objects from preview API (for day view)
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
  conflicts = [],
  moonPhases = {},
  cycleInfo = null,
  onCellClick,
  onExecutionClick,
  patternOffset = null,
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
      <div className="relative">
        {/* Skip link for keyboard navigation (WCAG 2.1) */}
        <a
          href="#calendar-grid-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:top-0 focus:left-0 focus:p-2 focus:bg-blue-500 focus:text-white focus:rounded focus:m-1"
        >
          Skip to calendar content
        </a>
        <div
          id="calendar-grid-content"
          className="grid grid-cols-7 border-t border-l border-gray-200 dark:border-gray-700"
        >
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
          const isCurrentMonth =
            date.getMonth() === currentDate.getMonth() &&
            date.getFullYear() === currentDate.getFullYear()

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
      </div>
    )
  }

  // Week View: Cycle-aware hourly timeline (Issue #XXX)
  if (viewMode === 'week') {
    return (
      <WeekHourlyTimeline
        currentDate={currentDate}
        executions={executions}
        conflicts={conflicts}
        moonPhases={moonPhases}
        cycleInfo={cycleInfo}
        onCellClick={onCellClick}
        onExecutionClick={onExecutionClick}
        patternOffset={patternOffset}
      />
    )
  }

  // Day View: Uses DayTimeline for hourly display with conflict highlighting (Issue #326)
  // Pass all executions and cycleInfo - DayTimeline handles cycle-aware filtering
  if (viewMode === 'day') {
    const currentDateKey = getDateKey(currentDate)

    return (
      <DayTimeline
        date={currentDateKey}
        executions={executions}
        conflicts={conflicts}
        cycleInfo={cycleInfo}
        onExecutionClick={onExecutionClick}
      />
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
  /** Conflict objects from preview API (for day view, Issue #326) */
  conflicts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      conflict_type: PropTypes.string,
      severity: PropTypes.oneOf(['error', 'warning']),
      message: PropTypes.string,
      start_time: PropTypes.string,
    })
  ),
  moonPhases: PropTypes.objectOf(
    PropTypes.shape({
      phase: PropTypes.string,
      phase_name: PropTypes.string,
      illumination: PropTypes.number,
    })
  ),
  /** Cycle info from preview API for day view cycle-aware rendering */
  cycleInfo: PropTypes.shape({
    start_hour: PropTypes.number,
    end_hour: PropTypes.number,
    spans_midnight: PropTypes.bool,
    suggested_preview_days: PropTypes.number,
  }),
  onCellClick: PropTypes.func.isRequired,
  onExecutionClick: PropTypes.func.isRequired,
  /** Pattern offset for week view pattern mode (null for calendar mode) */
  patternOffset: PropTypes.number,
}

export default CalendarGrid
