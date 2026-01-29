/**
 * DaySelector - Day navigation dots for mobile week view
 *
 * Shows 7 circular buttons (one per day) for quick day navigation.
 * Active day is highlighted, today has a ring indicator.
 *
 * @module components/scheduler/WeekHourlyTimeline/DaySelector
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { isToday } from './weekTimelineUtils'

const CALENDAR_DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

/**
 * DaySelector component
 *
 * In pattern mode (when patternOffset is provided), shows "1", "2", "3", etc.
 * In calendar mode, shows "S", "M", "T", etc. with calendar dates.
 *
 * @param {Object} props - Component props
 * @param {Date[]} props.weekDates - Array of 7 dates for the week
 * @param {number} props.currentIndex - Currently selected day index (0-6)
 * @param {Function} props.onDaySelect - Handler when day is selected
 * @param {number|null} [props.patternOffset=null] - Pattern offset for pattern mode (0, 7, 14, etc.)
 * @returns {JSX.Element} Day selector component
 */
function DaySelector({ weekDates, currentIndex, onDaySelect, patternOffset = null }) {
  return (
    <div
      className="flex justify-center gap-2 py-3 bg-gray-900 border-b border-gray-700"
      role="tablist"
      aria-label="Select day"
      data-testid="day-selector"
    >
      {weekDates.map((date, index) => {
        const isActive = index === currentIndex
        // No "today" indicator in pattern mode
        const isTodayDate = patternOffset === null && isToday(date)

        // Pattern mode: show "1", "2", etc. / Calendar mode: show "S", "M", etc.
        const isPatternMode = patternOffset !== null
        const patternDay = isPatternMode ? patternOffset + index + 1 : null
        const dayLabel = isPatternMode ? String(patternDay) : CALENDAR_DAYS[date.getDay()]
        const ariaLabel = isPatternMode
          ? `Day ${patternDay}`
          : `${CALENDAR_DAYS[date.getDay()]} ${date.getDate()}`

        // Build button classes
        const buttonClasses = [
          'w-9 h-9 rounded-full text-xs font-medium transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 focus:ring-offset-gray-900',
          isActive
            ? 'bg-blue-500 text-white'
            : 'bg-gray-800 text-gray-300 hover:bg-gray-700',
          isTodayDate && !isActive && 'ring-2 ring-blue-400',
        ].filter(Boolean).join(' ')

        return (
          <button
            key={index}
            type="button"
            onClick={() => onDaySelect(index)}
            className={buttonClasses}
            role="tab"
            aria-selected={isActive}
            aria-label={ariaLabel}
            data-testid={`day-selector-${index}`}
          >
            {isPatternMode ? (
              // Pattern mode: single centered number
              <div className="flex items-center justify-center h-full text-sm">
                {patternDay}
              </div>
            ) : (
              // Calendar mode: day letter + date number
              <>
                <div className="text-[10px] text-gray-400">{dayLabel}</div>
                <div className="-mt-0.5">{date.getDate()}</div>
              </>
            )}
          </button>
        )
      })}
    </div>
  )
}

DaySelector.propTypes = {
  /** Array of 7 Date objects for the week */
  weekDates: PropTypes.arrayOf(PropTypes.instanceOf(Date)).isRequired,
  /** Currently selected day index (0-6) */
  currentIndex: PropTypes.number.isRequired,
  /** Handler when a day button is clicked */
  onDaySelect: PropTypes.func.isRequired,
  /** Pattern offset for pattern mode (null for calendar mode) */
  patternOffset: PropTypes.number,
}

export default memo(DaySelector)
