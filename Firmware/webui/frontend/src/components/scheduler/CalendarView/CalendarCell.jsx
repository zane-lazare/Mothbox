/**
 * CalendarCell - Individual date cell in calendar month grid (Issue #228)
 *
 * Displays a single date cell with executions and moon phase information.
 * Used in the Calendar View month grid to show scheduled executions.
 *
 * @module components/scheduler/CalendarView/CalendarCell
 */

import { memo, useCallback, useState } from 'react'
import PropTypes from 'prop-types'
import MoonPhaseIcon from './MoonPhaseIcon'
import ExecutionMarker from './ExecutionMarker'
import { isToday, formatTime } from './calendarUtils'

/**
 * Get summary of hidden execution times
 * @param {Array} hiddenExecutions - Array of hidden executions
 * @returns {string} Comma-separated time summary (max 3)
 */
function getHiddenTimesSummary(hiddenExecutions) {
  const times = hiddenExecutions
    .slice(0, 3)
    .map((exec) => formatTime(exec.start_time))
    .filter(Boolean)

  const suffix = hiddenExecutions.length > 3 ? '...' : ''
  return times.join(', ') + suffix
}

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December']

/**
 * CalendarCell component
 *
 * @param {Object} props - Component props
 * @param {Date} props.date - The date this cell represents (required)
 * @param {boolean} props.isCurrentMonth - Whether date is in the displayed month
 * @param {Array} props.executions - Executions for this date (from groupExecutionsByDate)
 * @param {Object|null} props.moonPhase - Moon phase data { phase, phase_name, illumination }
 * @param {Function} props.onClick - Cell click handler (receives date)
 * @param {Function} props.onExecutionClick - Execution click handler (receives execution)
 * @returns {JSX.Element} Calendar cell component
 *
 * @example
 * <CalendarCell
 *   date={new Date(2025, 11, 17)}
 *   isCurrentMonth={true}
 *   executions={[execution1, execution2]}
 *   moonPhase={{ phase: 'full', phase_name: 'Full Moon', illumination: 1.0 }}
 *   onClick={(date) => handleDateClick(date)}
 *   onExecutionClick={(exec) => handleExecutionClick(exec)}
 * />
 */
function CalendarCell({
  date,
  isCurrentMonth,
  executions = [],
  moonPhase = null,
  onClick,
  onExecutionClick,
}) {
  // Check if this date is today
  const isTodayDate = isToday(date)

  // Hover expansion state
  const [isHovered, setIsHovered] = useState(false)

  // Show more executions in cells (5 instead of 3)
  const MAX_VISIBLE = 5
  const visibleExecutions = executions.slice(0, MAX_VISIBLE)
  const hiddenCount = executions.length - visibleExecutions.length

  // Only expand if there are hidden executions
  const shouldExpand = isHovered && hiddenCount > 0

  // Use stable primitive for date dependency (Date objects create new instances on each render)
  const dateTime = date.getTime()

  // Handle cell click - memoized to prevent unnecessary re-renders
  const handleCellClick = useCallback(() => {
    onClick(date)
  }, [onClick, dateTime]) // eslint-disable-line react-hooks/exhaustive-deps

  // Build cell classes (responsive: smaller on mobile, larger on desktop)
  const cellClasses = [
    'min-h-20 sm:min-h-24 p-0.5 sm:p-1',
    'border-r border-b',
    'border-gray-200 dark:border-gray-700',
    'relative cursor-pointer',
    'transition-colors duration-150',
    'hover:bg-gray-50 dark:hover:bg-gray-800',
    // Dimmed non-current-month dates
    !isCurrentMonth && 'bg-gray-50 dark:bg-gray-900',
  ]
    .filter(Boolean)
    .join(' ')

  // Build date number classes
  const dateNumberClasses = [
    'text-sm font-medium',
    // Today highlight: blue circle
    isTodayDate && 'bg-blue-500 text-white rounded-full px-2',
    // Dimmed text for non-current-month
    !isCurrentMonth && !isTodayDate && 'text-gray-400 dark:text-gray-600',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={cellClasses}
      onClick={handleCellClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="button"
      tabIndex={0}
      aria-label={`${WEEKDAYS[date.getDay()]}, ${MONTHS[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}${
        moonPhase ? `, ${moonPhase.phase_name}` : ''
      }${executions.length > 0 ? `, ${executions.length} scheduled execution${executions.length > 1 ? 's' : ''}` : ''}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleCellClick()
        }
      }}
    >
      {/* Header row: date number + moon phase */}
      <div className="flex items-center justify-between">
        <span className={dateNumberClasses}>{date.getDate()}</span>
        {moonPhase && <MoonPhaseIcon phase={moonPhase} size="sm" />}
      </div>

      {/* Executions container with hover expansion */}
      <div
        className={`
          space-y-0.5 mt-1 overflow-y-auto transition-all duration-200
          ${
            shouldExpand
              ? 'absolute left-0 right-0 top-8 z-20 bg-white dark:bg-gray-800 shadow-lg rounded-b-lg p-2 max-h-48 border border-gray-200 dark:border-gray-700'
              : 'max-h-24'
          }
        `}
      >
        {/* Show all executions when expanded, limited when not */}
        {(shouldExpand ? executions : visibleExecutions).map((exec, index) => (
          <ExecutionMarker
            key={exec.id || `${exec.pattern_id}-${exec.start_time}-${index}`}
            execution={exec}
            onClick={() => onExecutionClick(exec)}
            compact
          />
        ))}

        {/* "+N more" only shows when not expanded */}
        {!shouldExpand && hiddenCount > 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onClick(date) // Switch to day view to see all
            }}
            className="text-[10px] text-blue-500 dark:text-blue-400 hover:underline"
            title={`${hiddenCount} more executions - click to view all`}
          >
            +{hiddenCount} more ({getHiddenTimesSummary(executions.slice(MAX_VISIBLE))})
          </button>
        )}
      </div>
    </div>
  )
}

CalendarCell.propTypes = {
  date: PropTypes.instanceOf(Date).isRequired,
  isCurrentMonth: PropTypes.bool.isRequired,
  executions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      pattern_id: PropTypes.string.isRequired,
      pattern_name: PropTypes.string.isRequired,
      start_time: PropTypes.string.isRequired,
    })
  ),
  moonPhase: PropTypes.shape({
    phase: PropTypes.string,
    phase_name: PropTypes.string,
    illumination: PropTypes.number,
  }),
  onClick: PropTypes.func.isRequired,
  onExecutionClick: PropTypes.func.isRequired,
}

export default memo(CalendarCell)
