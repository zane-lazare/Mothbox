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

const DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

/**
 * DaySelector component
 *
 * @param {Object} props - Component props
 * @param {Date[]} props.weekDates - Array of 7 dates for the week
 * @param {number} props.currentIndex - Currently selected day index (0-6)
 * @param {Function} props.onDaySelect - Handler when day is selected
 * @returns {JSX.Element} Day selector component
 */
function DaySelector({ weekDates, currentIndex, onDaySelect }) {
  return (
    <div
      className="flex justify-center gap-2 py-3 bg-gray-900 border-b border-gray-700"
      role="tablist"
      aria-label="Select day"
      data-testid="day-selector"
    >
      {weekDates.map((date, index) => {
        const isActive = index === currentIndex
        const isTodayDate = isToday(date)

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
            aria-label={`${DAYS[date.getDay()]} ${date.getDate()}`}
            data-testid={`day-selector-${index}`}
          >
            <div className="text-[10px] text-gray-400">{DAYS[date.getDay()]}</div>
            <div className="-mt-0.5">{date.getDate()}</div>
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
}

export default memo(DaySelector)
