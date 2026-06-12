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
import CalendarCell from './CalendarCell'
import DayTimeline from '../DayTimeline'
import WeekHourlyTimeline from '../WeekHourlyTimeline'
import {
  getMonthGridDates,
  groupExecutionsByDate,
  getDateKey,
} from './calendarUtils'
import { PANEL_STYLES } from '../constants'
import {
  type Execution,
  type Conflict,
  type CycleInfo,
} from '../DayTimeline/dayTimelineUtils'

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

interface MoonPhase {
  phase?: string
  phase_name: string
  illumination?: number
}

export interface CalendarGridProps {
  viewMode: 'month' | 'week' | 'day'
  currentDate: Date
  executions?: Execution[]
  conflicts?: Conflict[]
  moonPhases?: Record<string, MoonPhase>
  cycleInfo?: CycleInfo | null
  onCellClick: (date: Date) => void
  onExecutionClick: (execution: Execution) => void
  patternOffset?: number | null
}

/**
 * CalendarGrid component
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
}: CalendarGridProps) {
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
          className={`grid grid-cols-7 border-t border-l ${PANEL_STYLES.grid}`}
        >
          {/* Day-of-week headers */}
          {DAYS.map((day) => (
            <div
              key={day}
              className={`py-2 text-center text-sm font-medium text-gray-500 dark:text-gray-400 border-r border-b ${PANEL_STYLES.grid}`}
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
  // Show only the first complete cycle of the schedule (from start_hour to end_hour)
  if (viewMode === 'day') {
    const currentDateKey = getDateKey(currentDate)

    // Extract first complete cycle from executions
    // A cycle runs from start_hour to end_hour (may span midnight)
    // cycleInfo hours are already in local time (backend converts based on tz param)
    let firstCycleExecutions = executions
    if (executions.length > 0 && cycleInfo?.end_hour != null) {
      // Hours are already in local time from the API
      const endHour = cycleInfo.end_hour

      // Find the first execution's timestamp as cycle start reference
      const sortedExecs = [...executions].sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      )
      const firstExecTime = new Date(sortedExecs[0].start_time)

      // Calculate when the first cycle ends (next occurrence of endHour after first exec)
      const cycleEnd = new Date(firstExecTime)
      cycleEnd.setHours(endHour, 0, 0, 0)

      // If cycle end is before first exec, it's the next day
      if (cycleEnd <= firstExecTime) {
        cycleEnd.setDate(cycleEnd.getDate() + 1)
      }

      // Filter to only executions within the first cycle
      firstCycleExecutions = sortedExecs.filter(
        (exec) => new Date(exec.start_time) < cycleEnd
      )
    }

    return (
      <DayTimeline
        date={currentDateKey}
        executions={firstCycleExecutions}
        conflicts={conflicts}
        cycleInfo={cycleInfo}
        onExecutionClick={onExecutionClick}
      />
    )
  }

  return null
}

export default CalendarGrid
