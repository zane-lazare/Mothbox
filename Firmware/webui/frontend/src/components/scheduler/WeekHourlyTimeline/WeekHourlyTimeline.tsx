/**
 * WeekHourlyTimeline - Cycle-aware hourly week view
 *
 * Displays a 7-day week grid with hourly rows, matching the refined
 * DayTimeline aesthetic. Features:
 * - Cycle-aware hour display (respects overnight schedules)
 * - ExecutionChip-style markers (time-only, action-type colored)
 * - ConflictSummary for displaying conflicts
 * - Responsive: Collapses to single-day view on mobile (<640px)
 * - Swipe navigation between days on mobile
 *
 * @module components/scheduler/WeekHourlyTimeline
 */

import { memo, useMemo, useState, useEffect, useCallback, useRef, Fragment } from 'react'
import DaySelector from './DaySelector'
import MoonPhaseIcon from '../CalendarView/MoonPhaseIcon'
import ConflictSummary from '../DayTimeline/ConflictSummary'
import ExecutionChip, { type Execution } from '../DayTimeline/ExecutionChip'
import HourRow from '../DayTimeline/HourRow'
import {
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
  groupExecutionsByCycleDay,
  getConflictsForDay,
  buildExecutionConflictsMap,
  formatHourLabel,
  getConflictForHour,
  getExecutionKey,
} from './weekTimelineUtils'

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
 * Conflict object structure
 */
interface Conflict {
  id?: string
  severity: 'error' | 'warning'
  message?: string
  start_time?: string
}

/**
 * Moon phase data
 */
interface MoonPhase {
  phase?: string
  phase_name?: string
  illumination?: number
}

/**
 * Display hour item - either a regular hour or collapsed indicator
 */
type DisplayHourItem = { type: 'hour'; hour: number } | { type: 'collapsed'; count: number }

/**
 * Component props interface
 */
export interface WeekHourlyTimelineProps {
  currentDate: Date
  executions?: Execution[]
  conflicts?: Conflict[]
  moonPhases?: Record<string, MoonPhase>
  cycleInfo?: CycleInfo | null
  onCellClick: (date: Date) => void
  onExecutionClick?: (execution: Execution) => void
  patternOffset?: number | null
}

/**
 * Day header cell for CSS Grid layout
 */
const DayHeaderCell = memo(function DayHeaderCell({
  dayIndex,
  moonPhase,
  onDayClick,
}: {
  dayIndex: number
  moonPhase: MoonPhase | null
  onDayClick: () => void
}) {
  const handleClick = () => {
    if (onDayClick) onDayClick()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div
      className={`${DAY_HEADER_STYLES.base} border-l border-gray-700 first:border-l-0 overflow-hidden`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`Day ${dayIndex + 1}, click to view day details`}
    >
      <div className="flex items-center justify-center gap-1 overflow-hidden">
        {moonPhase && <MoonPhaseIcon phase={moonPhase} size="xs" />}
      </div>
      <div className={DAY_HEADER_STYLES.normal}>
        {dayIndex + 1}
      </div>
    </div>
  )
})

/**
 * Hour label cell for CSS Grid layout
 */
const HourLabelCell = memo(function HourLabelCell({ item }: { item: DisplayHourItem }) {
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

/**
 * Week grid cell for CSS Grid layout (single hour/day intersection)
 */
const WeekGridCell = memo(function WeekGridCell({
  hour,
  executions,
  conflict,
  onExecutionClick,
  executionConflicts,
}: {
  hour: number
  executions: Execution[]
  conflict: Conflict | null
  onExecutionClick?: (execution: Execution) => void
  executionConflicts: Record<string, { severity: 'error' | 'warning' }>
}) {
  const conflictState = conflict?.severity || 'none'
  const rowStyles = ROW_CONFLICT_STYLES[conflictState] || ROW_CONFLICT_STYLES.none

  const cellClasses = [
    'p-1 min-h-8 border-l border-b border-gray-800',
    rowStyles.bg,
  ].filter(Boolean).join(' ')

  return (
    <div className={cellClasses} data-testid={`week-hour-${hour}`}>
      {/* Horizontal flex layout for small dots - show all executions */}
      <div className="flex flex-wrap gap-0.5 items-center">
        {executions.map((execution, idx) => {
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
      </div>
    </div>
  )
})

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
}: {
  weekDates: Date[]
  displayHours: DisplayHourItem[]
  executionsByDayAndHour: Record<string, Record<number, Execution[]>>
  conflicts: Conflict[]
  executionConflicts: Record<string, { severity: 'error' | 'warning' }>
  moonPhases?: Record<string, MoonPhase>
  onDayClick: (date: Date) => void
  onExecutionClick?: (execution: Execution) => void
  patternOffset?: number | null
}) {
  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden overflow-x-auto">
      <div
        className="grid"
        style={{
          gridTemplateColumns: '40px repeat(7, minmax(36px, 1fr))',
          gridTemplateRows: `auto repeat(${displayHours.length}, minmax(32px, auto))`,
        }}
      >
        {/* Row 1: Empty corner cell + 7 day headers */}
        <div className="border-b border-gray-700" />
        {weekDates.map((date, index) => {
          const dateKey = getDateKey(date)
          const moonPhase = moonPhases?.[dateKey] || null

          return (
            <DayHeaderCell
              key={dateKey}
              dayIndex={index}
              moonPhase={moonPhase}
              onDayClick={() => onDayClick && onDayClick(date)}
            />
          )
        })}

        {/* Remaining rows: Hour label + 7 day cells per row */}
        {displayHours.map((item, rowIndex) => {
          const isCollapsed = item.type === 'collapsed'
          const hour = item.type === 'hour' ? item.hour : 0

          return (
            <Fragment key={isCollapsed ? `collapsed-${rowIndex}` : `hour-${hour}`}>
              <HourLabelCell item={item} />
              {weekDates.map((date, dayIndex) => {
                const dateKey = getDateKey(date)
                // In pattern mode, use cycle-based keys; in calendar mode, use date keys
                const dayKey = patternOffset !== null ? `day-${dayIndex}` : dateKey
                const dayExecutions = executionsByDayAndHour[dayKey] || {}
                const dayConflicts = getConflictsForDay(conflicts, dateKey)
                const hourExecutions = isCollapsed ? [] : (dayExecutions[hour] || [])
                const hourConflict = isCollapsed ? null : getConflictForHour(dayConflicts, hour, dateKey)

                if (isCollapsed) {
                  return (
                    <div
                      key={`${dayKey}-collapsed`}
                      className="p-1 border-l border-b border-gray-800 text-center text-[10px] text-gray-600"
                    >
                      ...
                    </div>
                  )
                }

                return (
                  <WeekGridCell
                    key={`${dayKey}-${hour}`}
                    hour={hour}
                    executions={hourExecutions}
                    conflict={hourConflict}
                    onExecutionClick={onExecutionClick}
                    executionConflicts={executionConflicts}
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
}: {
  weekDates: Date[]
  displayHours: DisplayHourItem[]
  executionsByDayAndHour: Record<string, Record<number, Execution[]>>
  conflicts: Conflict[]
  executionConflicts: Record<string, { severity: 'error' | 'warning' }>
  moonPhases?: Record<string, MoonPhase>
  onDayClick: (date: Date) => void
  onExecutionClick?: (execution: Execution) => void
  patternOffset?: number | null
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

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
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
  // In pattern mode, use cycle-based keys; in calendar mode, use date keys
  const dayKey = patternOffset !== null ? `day-${currentDayIndex}` : dateKey
  const dayExecutions = executionsByDayAndHour[dayKey] || {}
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
}: WeekHourlyTimelineProps) {
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

  // Get cycle-aware hours (only active hours for the schedule)
  const cycleHours = useMemo(() => getCycleHours(cycleInfo), [cycleInfo])

  // Group executions by day and hour
  // In pattern mode, use cycle-based grouping to handle overnight schedules correctly
  // In calendar mode, use date-based grouping with post-midnight shifting
  const executionsByDayAndHour = useMemo(() => {
    if (patternOffset !== null && cycleInfo) {
      // Align reference with cycle start_hour so Day 1 shows a complete cycle
      const reference = new Date(weekDates[0])
      reference.setHours(cycleInfo.start_hour ?? 0, 0, 0, 0)
      return groupExecutionsByCycleDay(executions, cycleInfo, reference)
    }
    return groupExecutionsByDayAndHour(executions, weekDates, cycleInfo)
  }, [executions, weekDates, cycleInfo, patternOffset])

  // Build a combined executions-by-hour for collapse calculation
  // (collapse if ALL days have similar patterns)
  const combinedExecutionsByHour = useMemo(() => {
    const combined: Record<number, Execution[]> = {}
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
  const handleDayClick = useCallback((date: Date) => {
    if (onCellClick) onCellClick(date)
  }, [onCellClick])

  // Check for empty state
  const hasExecutions = executions.length > 0

  if (!hasExecutions) {
    return (
      <div className="p-4" data-testid="week-hourly-timeline">
        <div className="text-center text-gray-500 py-8">
          No scheduled events this week
        </div>
      </div>
    )
  }

  return (
    <div className="p-4" data-testid="week-hourly-timeline">
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

export default memo(WeekHourlyTimeline)
