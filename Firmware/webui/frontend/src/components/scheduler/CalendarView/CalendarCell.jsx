/**
 * CalendarCell - Individual date cell in calendar month grid (Issue #228)
 *
 * Displays a single date cell with executions and moon phase information.
 * Used in the Calendar View month grid to show scheduled executions.
 *
 * @module components/scheduler/CalendarView/CalendarCell
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import MoonPhaseIcon from './MoonPhaseIcon'
import ExecutionMarker from './ExecutionMarker'
import { isToday } from './calendarUtils'

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

  // Calculate how many executions are hidden
  const visibleExecutions = executions.slice(0, 3)
  const hiddenCount = executions.length - visibleExecutions.length

  // Handle cell click
  const handleCellClick = () => {
    onClick(date)
  }

  // Handle execution click (prevent bubbling to cell)
  const handleExecutionClick = (execution) => {
    return (e) => {
      e.stopPropagation()
      onExecutionClick(execution)
    }
  }

  // Build cell classes
  const cellClasses = [
    'min-h-24 p-1',
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
      role="button"
      tabIndex={0}
      aria-label={`${date.toLocaleDateString()}, ${executions.length} executions`}
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

      {/* Executions container */}
      <div className="space-y-1 mt-1 overflow-y-auto max-h-16">
        {visibleExecutions.map((exec) => (
          <ExecutionMarker
            key={exec.id || exec.start_time}
            execution={exec}
            onClick={handleExecutionClick(exec)}
            compact
          />
        ))}

        {/* "+N more" indicator */}
        {hiddenCount > 0 && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            +{hiddenCount} more
          </span>
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
