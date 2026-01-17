/**
 * WeekHourlyTimeline - Cycle-aware hourly week view
 *
 * Displays a 7-day week grid with hourly rows, matching the refined
 * DayTimeline aesthetic. Features:
 * - Cycle-aware hour display (respects overnight schedules)
 * - ExecutionChip-style markers (time-only, action-type colored)
 * - TimelineLegend and ConflictSummary
 * - Responsive: Collapses to single-day view on mobile (<640px)
 * - Swipe navigation between days on mobile
 *
 * @module components/scheduler/WeekHourlyTimeline
 */

import { memo, useMemo, useState, useEffect, useCallback, useRef, Fragment } from 'react'
import PropTypes from 'prop-types'
import DayColumn from './DayColumn'
import DaySelector from './DaySelector'
import MoonPhaseIcon from '../CalendarView/MoonPhaseIcon'
import ConflictSummary from '../DayTimeline/ConflictSummary'
import ExecutionChip from '../DayTimeline/ExecutionChip'
import HourRow from '../DayTimeline/HourRow'
import {
  LEGEND_ITEMS,
  WEEK_VIEW_CONFIG,
  DAY_HEADER_STYLES,
  ROW_CONFLICT_STYLES,
} from './weekTimelineConstants'
import {
  getWeekDates,
  getDateKey,
  getCycleHours,
  collapseRepetitiveHours,
  groupExecutionsByDayAndHour,
  getConflictsForDay,
  buildExecutionConflictsMap,
  formatHourLabel,
  getConflictForHour,
  formatWeekDayHeader,
  getExecutionKey,
} from './weekTimelineUtils'

/**
 * Legend component for the timeline (same as DayTimeline)
 * Memoized since LEGEND_ITEMS is static
 */
const TimelineLegend = memo(function TimelineLegend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 mb-4 px-2">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${item.color}`} />
          {item.label}
        </div>
      ))}
    </div>
  )
})

/**
 * Day header cell for CSS Grid layout
 */
const DayHeaderCell = memo(function DayHeaderCell({
  date,
  dayIndex,
  patternOffset,
  moonPhase,
  onDayClick,
}) {
  const headerInfo = useMemo(
    () => formatWeekDayHeader(date, dayIndex, patternOffset),
    [date, dayIndex, patternOffset]
  )

  const handleClick = () => {
    if (onDayClick) onDayClick(date)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div
      className={`${DAY_HEADER_STYLES.base} border-l border-gray-700 first:border-l-0`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`${headerInfo.dayName}${patternOffset === null ? ` ${date.getDate()}` : ''}, click to view day details`}
    >
      <div className="flex items-center justify-center gap-1">
        <span className="text-xs font-medium text-gray-400">
          {headerInfo.dayName}
        </span>
        {moonPhase && <MoonPhaseIcon phase={moonPhase} size="xs" />}
      </div>
      <div className={headerInfo.isToday ? DAY_HEADER_STYLES.today : DAY_HEADER_STYLES.normal}>
        {headerInfo.dayNumber}
      </div>
    </div>
  )
})

DayHeaderCell.propTypes = {
  date: PropTypes.instanceOf(Date).isRequired,
  dayIndex: PropTypes.number.isRequired,
  patternOffset: PropTypes.number,
  moonPhase: PropTypes.object,
  onDayClick: PropTypes.func.isRequired,
}

/**
 * Hour label cell for CSS Grid layout
 */
const HourLabelCell = memo(function HourLabelCell({ item, index }) {
  if (item.type === 'collapsed') {
    return (
      <div className="p-1 border-b border-gray-800 text-[10px] text-gray-600 flex items-center">
        ...
      </div>
    )
  }

  return (
    <div className="p-1 border-b border-gray-800 text-[10px] text-gray-600 flex items-center">
      {formatHourLabel(item.hour)}
    </div>
  )
})

HourLabelCell.propTypes = {
  item: PropTypes.oneOfType([
    PropTypes.shape({ type: PropTypes.oneOf(['hour']), hour: PropTypes.number }),
    PropTypes.shape({ type: PropTypes.oneOf(['collapsed']), count: PropTypes.number }),
  ]).isRequired,
  index: PropTypes.number.isRequired,
}

/**
 * Week grid cell for CSS Grid layout (single hour/day intersection)
 */
const WeekGridCell = memo(function WeekGridCell({
  hour,
  executions,
  conflict,
  onExecutionClick,
  executionConflicts,
  onOverflowClick,
}) {
  const maxVisible = WEEK_VIEW_CONFIG.MAX_VISIBLE_CHIPS
  const visibleExecutions = executions.slice(0, maxVisible)
  const hiddenCount = executions.length - maxVisible

  const conflictState = conflict?.severity || 'none'
  const rowStyles = ROW_CONFLICT_STYLES[conflictState] || ROW_CONFLICT_STYLES.none

  const cellClasses = [
    'p-1 min-h-8 space-y-0.5 border-l border-b border-gray-800',
    rowStyles.bg,
  ].filter(Boolean).join(' ')

  return (
    <div className={cellClasses} data-testid={`week-hour-${hour}`}>
      {visibleExecutions.map((execution, idx) => {
        const execConflict = executionConflicts[execution.pattern_id]
        const conflictSeverity = execConflict?.severity || null

        return (
          <ExecutionChip
            key={getExecutionKey(execution, idx)}
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
})

WeekGridCell.propTypes = {
  hour: PropTypes.number.isRequired,
  executions: PropTypes.array.isRequired,
  conflict: PropTypes.shape({
    id: PropTypes.string,
    severity: PropTypes.oneOf(['error', 'warning']).isRequired,
    message: PropTypes.string,
  }),
  onExecutionClick: PropTypes.func,
  executionConflicts: PropTypes.object.isRequired,
  onOverflowClick: PropTypes.func,
}

/**
 * Desktop week view - CSS Grid with aligned rows across all days
 */
const DesktopWeekView = memo(function DesktopWeekView({
  weekDates,
  displayHours,
  executionsByDayAndHour,
  conflicts,
  executionConflicts,
  moonPhases,
  onDayClick,
  onExecutionClick,
  patternOffset = null,
}) {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden overflow-x-auto">
      <div
        className="grid min-w-[700px]"
        style={{
          gridTemplateColumns: '48px repeat(7, minmax(80px, 1fr))',
          gridTemplateRows: `auto repeat(${displayHours.length}, minmax(32px, auto))`,
        }}
      >
        {/* Row 1: Empty corner cell + 7 day headers */}
        <div className="h-16 border-b border-gray-700" />
        {weekDates.map((date, index) => {
          const dateKey = getDateKey(date)
          const moonPhase = moonPhases?.[dateKey] || null

          return (
            <DayHeaderCell
              key={dateKey}
              date={date}
              dayIndex={index}
              patternOffset={patternOffset}
              moonPhase={moonPhase}
              onDayClick={onDayClick}
            />
          )
        })}

        {/* Remaining rows: Hour label + 7 day cells per row */}
        {displayHours.map((item, rowIndex) => {
          const isCollapsed = item.type === 'collapsed'
          const hour = item.hour

          return (
            <Fragment key={isCollapsed ? `collapsed-${rowIndex}` : `hour-${hour}`}>
              <HourLabelCell item={item} index={rowIndex} />
              {weekDates.map((date) => {
                const dateKey = getDateKey(date)
                const dayExecutions = executionsByDayAndHour[dateKey] || {}
                const dayConflicts = getConflictsForDay(conflicts, dateKey)
                const hourExecutions = isCollapsed ? [] : (dayExecutions[hour] || [])
                const hourConflict = isCollapsed ? null : getConflictForHour(dayConflicts, hour, dateKey)

                if (isCollapsed) {
                  return (
                    <div
                      key={`${dateKey}-collapsed`}
                      className="p-1 border-l border-b border-gray-800 text-center text-[10px] text-gray-600"
                    >
                      ...
                    </div>
                  )
                }

                return (
                  <WeekGridCell
                    key={`${dateKey}-${hour}`}
                    hour={hour}
                    executions={hourExecutions}
                    conflict={hourConflict}
                    onExecutionClick={onExecutionClick}
                    executionConflicts={executionConflicts}
                    onOverflowClick={() => onDayClick && onDayClick(date)}
                  />
                )
              })}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
})

DesktopWeekView.propTypes = {
  weekDates: PropTypes.array.isRequired,
  displayHours: PropTypes.array.isRequired,
  executionsByDayAndHour: PropTypes.object.isRequired,
  conflicts: PropTypes.array.isRequired,
  executionConflicts: PropTypes.object.isRequired,
  moonPhases: PropTypes.object,
  onDayClick: PropTypes.func.isRequired,
  onExecutionClick: PropTypes.func,
  patternOffset: PropTypes.number,
}

/**
 * Mobile week view - single day with swipe navigation
 */
const MobileWeekView = memo(function MobileWeekView({
  weekDates,
  displayHours,
  executionsByDayAndHour,
  conflicts,
  executionConflicts,
  moonPhases,
  onDayClick,
  onExecutionClick,
  patternOffset = null,
}) {
  const [currentDayIndex, setCurrentDayIndex] = useState(() => {
    // In pattern mode, default to first day; in calendar mode, default to today
    if (patternOffset !== null) return 0

    const today = new Date()
    const todayIndex = weekDates.findIndex(d =>
      d.getFullYear() === today.getFullYear() &&
      d.getMonth() === today.getMonth() &&
      d.getDate() === today.getDate()
    )
    return todayIndex >= 0 ? todayIndex : 0
  })

  // Swipe handling
  const touchStartX = useRef(0)
  const touchEndX = useRef(0)

  const handleTouchStart = useCallback((e) => {
    touchStartX.current = e.touches[0].clientX
  }, [])

  const handleTouchMove = useCallback((e) => {
    touchEndX.current = e.touches[0].clientX
  }, [])

  const handleTouchEnd = useCallback(() => {
    const diff = touchStartX.current - touchEndX.current
    const threshold = WEEK_VIEW_CONFIG.SWIPE_THRESHOLD

    if (Math.abs(diff) > threshold) {
      if (diff > 0 && currentDayIndex < 6) {
        // Swipe left -> next day
        setCurrentDayIndex(prev => prev + 1)
      } else if (diff < 0 && currentDayIndex > 0) {
        // Swipe right -> previous day
        setCurrentDayIndex(prev => prev - 1)
      }
    }
  }, [currentDayIndex])

  const currentDate = weekDates[currentDayIndex]
  const dateKey = getDateKey(currentDate)
  const dayExecutions = executionsByDayAndHour[dateKey] || {}
  const dayConflicts = getConflictsForDay(conflicts, dateKey)
  const currentMoonPhase = moonPhases?.[dateKey] || null

  return (
    <div>
      {/* Day selector dots */}
      <DaySelector
        weekDates={weekDates}
        currentIndex={currentDayIndex}
        onDaySelect={setCurrentDayIndex}
        patternOffset={patternOffset}
      />

      {/* Day content with swipe */}
      <div
        className="border border-gray-700 rounded-lg overflow-hidden mt-2"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Day header */}
        <div
          className="p-3 text-center border-b border-gray-700 cursor-pointer hover:bg-gray-800 transition-colors"
          onClick={() => onDayClick(currentDate)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onDayClick(currentDate)
            }
          }}
        >
          <div className="flex items-center justify-center gap-2 text-lg font-semibold">
            {patternOffset !== null
              ? `Day ${patternOffset + currentDayIndex + 1}`
              : currentDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
            }
            {currentMoonPhase && <MoonPhaseIcon phase={currentMoonPhase} size="sm" />}
          </div>
        </div>

        {/* Hour rows */}
        <div className="divide-y divide-gray-800">
          {displayHours.map((item, index) => {
            if (item.type === 'collapsed') {
              return (
                <div key={`collapsed-${index}`} className="p-3 text-center text-xs text-gray-600">
                  ... continues ({item.count} similar hour{item.count > 1 ? 's' : ''})
                </div>
              )
            }

            const hour = item.hour
            const hourExecutions = dayExecutions[hour] || []
            const hourConflict = getConflictForHour(dayConflicts, hour, dateKey)

            return (
              <HourRow
                key={hour}
                hour={hour}
                executions={hourExecutions}
                conflict={hourConflict}
                onExecutionClick={onExecutionClick}
                executionConflicts={executionConflicts}
              />
            )
          })}
        </div>
      </div>

      {/* Swipe hint */}
      <div className="text-center text-xs text-gray-600 mt-2">
        Swipe left/right to change day
      </div>
    </div>
  )
})

MobileWeekView.propTypes = {
  weekDates: PropTypes.array.isRequired,
  displayHours: PropTypes.array.isRequired,
  executionsByDayAndHour: PropTypes.object.isRequired,
  conflicts: PropTypes.array.isRequired,
  executionConflicts: PropTypes.object.isRequired,
  moonPhases: PropTypes.object,
  onDayClick: PropTypes.func.isRequired,
  onExecutionClick: PropTypes.func,
  patternOffset: PropTypes.number,
}

/**
 * WeekHourlyTimeline main component
 */
function WeekHourlyTimeline({
  currentDate,
  executions = [],
  conflicts = [],
  moonPhases = {},
  cycleInfo = null,
  onCellClick,
  onExecutionClick,
  patternOffset = null,
}) {
  // Mobile detection
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' && window.innerWidth < WEEK_VIEW_CONFIG.MOBILE_BREAKPOINT
  )

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < WEEK_VIEW_CONFIG.MOBILE_BREAKPOINT)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Get week dates
  // Pattern mode: 7 sequential days starting from today (for pattern display)
  // Calendar mode: Sunday to Saturday of current week
  const weekDates = useMemo(() => {
    if (patternOffset !== null) {
      // Pattern mode: return 7 sequential days starting from today
      const dates = []
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      for (let i = 0; i < 7; i++) {
        const date = new Date(today)
        date.setDate(today.getDate() + i)
        dates.push(date)
      }
      return dates
    }
    // Calendar mode: Sunday to Saturday
    return getWeekDates(currentDate)
  }, [currentDate, patternOffset])

  // Get cycle-aware hours
  const cycleHours = useMemo(() => getCycleHours(cycleInfo), [cycleInfo])

  // Group executions by day and hour
  const executionsByDayAndHour = useMemo(
    () => groupExecutionsByDayAndHour(executions, weekDates),
    [executions, weekDates]
  )

  // Build a combined executions-by-hour for collapse calculation
  // (collapse if ALL days have similar patterns)
  const combinedExecutionsByHour = useMemo(() => {
    const combined = {}
    cycleHours.forEach(hour => {
      combined[hour] = []
      Object.values(executionsByDayAndHour).forEach(dayMap => {
        if (dayMap[hour]) {
          combined[hour].push(...dayMap[hour])
        }
      })
    })
    return combined
  }, [cycleHours, executionsByDayAndHour])

  // Calculate display hours with collapsing
  const displayHours = useMemo(
    () => collapseRepetitiveHours(cycleHours, combinedExecutionsByHour),
    [cycleHours, combinedExecutionsByHour]
  )

  // Build execution conflicts map
  const executionConflicts = useMemo(
    () => buildExecutionConflictsMap(executions, conflicts),
    [executions, conflicts]
  )

  // Handle day click - switch to day view
  const handleDayClick = useCallback((date) => {
    if (onCellClick) onCellClick(date)
  }, [onCellClick])

  // Check for empty state
  const hasExecutions = executions.length > 0

  if (!hasExecutions) {
    return (
      <div className="p-4" data-testid="week-hourly-timeline">
        <TimelineLegend />
        <div className="text-center text-gray-500 py-8">
          No scheduled events this week
        </div>
      </div>
    )
  }

  return (
    <div className="p-4" data-testid="week-hourly-timeline">
      {/* Legend */}
      <TimelineLegend />

      {/* Conflict Summary */}
      {conflicts.length > 0 && <ConflictSummary conflicts={conflicts} />}

      {/* View - Desktop or Mobile */}
      {isMobile ? (
        <MobileWeekView
          weekDates={weekDates}
          displayHours={displayHours}
          executionsByDayAndHour={executionsByDayAndHour}
          conflicts={conflicts}
          executionConflicts={executionConflicts}
          moonPhases={moonPhases}
          onDayClick={handleDayClick}
          onExecutionClick={onExecutionClick}
          patternOffset={patternOffset}
        />
      ) : (
        <DesktopWeekView
          weekDates={weekDates}
          displayHours={displayHours}
          executionsByDayAndHour={executionsByDayAndHour}
          conflicts={conflicts}
          executionConflicts={executionConflicts}
          moonPhases={moonPhases}
          onDayClick={handleDayClick}
          onExecutionClick={onExecutionClick}
          patternOffset={patternOffset}
        />
      )}
    </div>
  )
}

WeekHourlyTimeline.propTypes = {
  /** Any date within the target week */
  currentDate: PropTypes.instanceOf(Date).isRequired,
  /** Array of execution objects from preview API */
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      pattern_id: PropTypes.string.isRequired,
      pattern_name: PropTypes.string.isRequired,
      start_time: PropTypes.string.isRequired,
      actions: PropTypes.array,
    })
  ),
  /** Array of conflict objects from preview API */
  conflicts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      severity: PropTypes.oneOf(['error', 'warning']).isRequired,
      message: PropTypes.string,
      start_time: PropTypes.string,
    })
  ),
  /** Moon phases by date { 'YYYY-MM-DD': { phase, phase_name, illumination } } */
  moonPhases: PropTypes.objectOf(
    PropTypes.shape({
      phase: PropTypes.string,
      phase_name: PropTypes.string,
      illumination: PropTypes.number,
    })
  ),
  /** Cycle info from preview API for cycle-aware rendering */
  cycleInfo: PropTypes.shape({
    start_hour: PropTypes.number,
    end_hour: PropTypes.number,
    spans_midnight: PropTypes.bool,
    suggested_preview_days: PropTypes.number,
  }),
  /** Click handler for day/cell clicks (receives Date) */
  onCellClick: PropTypes.func.isRequired,
  /** Click handler for execution clicks (receives execution object) */
  onExecutionClick: PropTypes.func,
  /** Pattern offset for pattern mode (null for calendar mode) */
  patternOffset: PropTypes.number,
}

export default memo(WeekHourlyTimeline)
