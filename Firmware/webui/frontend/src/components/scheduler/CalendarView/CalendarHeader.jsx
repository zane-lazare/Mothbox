import PropTypes from 'prop-types'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { formatDateRange } from './calendarUtils'

/**
 * CalendarHeader Component
 *
 * Sticky header for the calendar view providing:
 * - Schedule selection dropdown
 * - Date navigation (previous/today/next)
 * - View mode toggle (day/week/month)
 * - Formatted date range display
 *
 * @component
 * @example
 * <CalendarHeader
 *   viewMode="month"
 *   currentDate={new Date()}
 *   onViewModeChange={(mode) => setViewMode(mode)}
 *   onNavigate={(direction) => handleNavigate(direction)}
 *   schedules={schedules}
 *   selectedScheduleId="sched-123"
 *   onScheduleSelect={(id) => setSelectedScheduleId(id)}
 * />
 */
export default function CalendarHeader({
  viewMode,
  currentDate,
  onViewModeChange,
  onNavigate,
  schedules,
  selectedScheduleId,
  onScheduleSelect,
}) {
  return (
    <div className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between">
        {/* Left Section - Schedule Selector */}
        <div className="flex items-center">
          <select
            value={selectedScheduleId || ''}
            onChange={(e) => onScheduleSelect(e.target.value || null)}
            className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 text-sm focus:border-blue-500 focus:ring-blue-500"
            aria-label="Select schedule"
          >
            <option value="">Select a schedule...</option>
            {schedules.map((schedule) => (
              <option key={schedule.schedule_id} value={schedule.schedule_id}>
                {schedule.name}
              </option>
            ))}
          </select>
        </div>

        {/* Center Section - Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate('prev')}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200"
            aria-label="Previous"
            type="button"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>

          <button
            onClick={() => onNavigate('today')}
            className="px-3 py-1 rounded-md bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200"
            type="button"
          >
            Today
          </button>

          <button
            onClick={() => onNavigate('next')}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200"
            aria-label="Next"
            type="button"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>

          <span className="text-lg font-semibold ml-4 text-gray-900 dark:text-gray-100">
            {formatDateRange(viewMode, currentDate)}
          </span>
        </div>

        {/* Right Section - View Mode Toggle */}
        <div className="inline-flex rounded-md shadow-sm" role="group" aria-label="View mode">
          {['day', 'week', 'month'].map((mode) => (
            <button
              key={mode}
              onClick={() => onViewModeChange(mode)}
              className={`px-4 py-2 text-sm font-medium border ${
                viewMode === mode
                  ? 'bg-blue-500 text-white border-blue-500 z-10'
                  : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
              } ${
                mode === 'day'
                  ? 'rounded-l-lg'
                  : mode === 'month'
                    ? 'rounded-r-lg'
                    : ''
              }`}
              type="button"
              aria-pressed={viewMode === mode}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

CalendarHeader.propTypes = {
  /** Current view mode: 'month', 'week', or 'day' */
  viewMode: PropTypes.oneOf(['month', 'week', 'day']).isRequired,

  /** The current date being displayed */
  currentDate: PropTypes.instanceOf(Date).isRequired,

  /** Callback when view mode changes */
  onViewModeChange: PropTypes.func.isRequired,

  /** Callback when navigation button clicked ('prev', 'next', 'today') */
  onNavigate: PropTypes.func.isRequired,

  /** Array of schedule objects with schedule_id and name */
  schedules: PropTypes.arrayOf(
    PropTypes.shape({
      schedule_id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    })
  ).isRequired,

  /** Currently selected schedule ID (null if none selected) */
  selectedScheduleId: PropTypes.string,

  /** Callback when schedule is selected/changed */
  onScheduleSelect: PropTypes.func.isRequired,
}
