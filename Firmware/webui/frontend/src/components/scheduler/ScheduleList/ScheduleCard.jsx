/**
 * ScheduleCard - Display schedule with routine indicators and action buttons (Issue #266)
 *
 * Displays a schedule card with:
 * - Schedule name and auto-generated description
 * - Active status badge
 * - Colored routine indicator dots (orange=GPIO, blue=camera, purple=HDR)
 * - Routine count
 * - Action buttons (View, Enable/Disable)
 * - Loading states for async operations
 *
 * Note: Delete functionality moved to ScheduleEditor (view-first paradigm)
 *
 * @module components/scheduler/ScheduleList/ScheduleCard
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { EyeIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline'
import ActiveScheduleBadge from './ActiveScheduleBadge'
import { SchedulePropType } from '../ScheduleEditor/propTypes'
import {
  getActionColor,
  generateRoutineName,
  generateScheduleDescription,
} from '../../../utils/routineUtils'

/** Base button styles shared across all action buttons */
const BUTTON_BASE = [
  'inline-flex items-center gap-1.5 px-3 py-1.5',
  'text-sm font-medium rounded-md',
  'focus:outline-none focus:ring-2 focus:ring-offset-2',
  'disabled:opacity-50 disabled:cursor-not-allowed',
].join(' ')

/** Primary button style for Edit, Activate, Deactivate */
const BUTTON_PRIMARY = [
  BUTTON_BASE,
  'text-gray-700 bg-white border border-gray-300',
  'hover:bg-gray-50 focus:ring-blue-500',
  'dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600',
].join(' ')

/** Success button style for Enable */
const BUTTON_SUCCESS = [
  BUTTON_BASE,
  'text-green-700 bg-white border border-green-300',
  'hover:bg-green-50 focus:ring-green-500',
  'dark:bg-gray-700 dark:text-green-400 dark:border-green-900 dark:hover:bg-green-900/20',
].join(' ')

/**
 * ScheduleCard component
 *
 * @param {Object} props - Component props
 * @param {Object} props.schedule - Schedule object
 * @param {boolean} props.isActive - Whether this schedule is active
 * @param {Function} props.onView - Callback when View button clicked
 * @param {Function} props.onToggleEnabled - Callback when Enable/Disable button clicked
 * @param {boolean} [props.isTogglingEnabled] - Loading state for enable/disable toggle
 * @returns {JSX.Element} Schedule card component
 *
 * @example
 * <ScheduleCard
 *   schedule={schedule}
 *   isActive={false}
 *   onView={handleView}
 *   onToggleEnabled={handleToggleEnabled}
 * />
 */
function ScheduleCard({
  schedule,
  isActive,
  onView,
  onToggleEnabled,
  isTogglingEnabled = false,
}) {
  const nameId = `schedule-name-${schedule.schedule_id}`
  const isEnabled = schedule.enabled !== false // Default to enabled if not explicitly set

  const handleView = () => {
    onView(schedule)
  }

  const handleToggleEnabled = () => {
    if (onToggleEnabled) {
      onToggleEnabled(schedule)
    }
  }

  return (
    <article
      role="article"
      aria-labelledby={nameId}
      className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4"
    >
      {/* Header: Name and Badges */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 id={nameId} className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {schedule.name}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {!isEnabled && (
            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full dark:bg-gray-700 dark:text-gray-400">
              Disabled
            </span>
          )}
          <ActiveScheduleBadge isActive={isActive} />
        </div>
      </div>

      {/* Description - manual or auto-generated */}
      {(schedule.description || schedule.routines?.length > 0) && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {schedule.description || generateScheduleDescription(schedule.routines)}
        </p>
      )}

      {/* Routine Indicators - shows all actions per routine, enclosed in pipes */}
      {schedule.routines?.length > 0 && (
        <div className="flex items-center gap-1 mb-3 flex-wrap">
          {/* Opening pipe */}
          <span className="text-gray-300 dark:text-gray-600 text-xs">|</span>
          {schedule.routines.map((routine, routineIndex) => (
            <div
              key={routine.routine_id || routineIndex}
              className="flex items-center gap-1"
              title={generateRoutineName(routine)}
            >
              {/* Pipe separator between routines */}
              {routineIndex > 0 && (
                <span className="text-gray-300 dark:text-gray-600 mx-1 text-xs">|</span>
              )}
              {/* Action dots for this routine */}
              {routine.actions?.map((action, actionIndex) => (
                <div
                  key={actionIndex}
                  className={`w-1.5 h-1.5 rounded-full ${getActionColor(action)}`}
                  title={action.action_name || action.name || 'Action'}
                />
              ))}
            </div>
          ))}
          {/* Closing pipe */}
          <span className="text-gray-300 dark:text-gray-600 ml-1 text-xs">|</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={handleView}
          disabled={isTogglingEnabled}
          className={BUTTON_PRIMARY}
        >
          <EyeIcon className="h-4 w-4" aria-hidden="true" />
          View
        </button>

        {/* Enable/Disable toggle - only show when not active */}
        {!isActive && onToggleEnabled && (
          <button
            type="button"
            onClick={handleToggleEnabled}
            disabled={isTogglingEnabled}
            className={isEnabled ? BUTTON_PRIMARY : BUTTON_SUCCESS}
          >
            {isEnabled ? (
              <>
                <XMarkIcon className="h-4 w-4" aria-hidden="true" />
                {isTogglingEnabled ? 'Disabling...' : 'Disable'}
              </>
            ) : (
              <>
                <CheckIcon className="h-4 w-4" aria-hidden="true" />
                {isTogglingEnabled ? 'Enabling...' : 'Enable'}
              </>
            )}
          </button>
        )}
      </div>
    </article>
  )
}

ScheduleCard.propTypes = {
  schedule: SchedulePropType.isRequired,
  isActive: PropTypes.bool,
  onView: PropTypes.func.isRequired,
  onToggleEnabled: PropTypes.func,
  isTogglingEnabled: PropTypes.bool,
}

export default memo(ScheduleCard)
