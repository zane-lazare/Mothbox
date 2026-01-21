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
import { CARD_STYLES, TEXT_STYLES, BUTTON_STYLES } from '../constants'

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

  // Build card classes based on state
  const cardClasses = [
    CARD_STYLES.base,
    isActive && CARD_STYLES.active,
    !isEnabled && CARD_STYLES.disabled,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <article role="article" aria-labelledby={nameId} className={cardClasses}>
      {/* Header: Name and Badges */}
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex-1 min-w-0">
          <h3 id={nameId} className={TEXT_STYLES.title}>
            {schedule.name}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {!isEnabled && (
            <span className={TEXT_STYLES.meta}>Disabled</span>
          )}
          <ActiveScheduleBadge isActive={isActive} />
        </div>
      </div>

      {/* Description - manual or auto-generated */}
      {(schedule.description || schedule.routines?.length > 0) && (
        <p className={`${TEXT_STYLES.description} mb-3`}>
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
          className={`${BUTTON_STYLES.base} ${BUTTON_STYLES.primary}`}
        >
          <EyeIcon className="h-3.5 w-3.5" aria-hidden="true" />
          View
        </button>

        {/* Enable/Disable toggle - only show when not active */}
        {!isActive && onToggleEnabled && (
          <button
            type="button"
            onClick={handleToggleEnabled}
            disabled={isTogglingEnabled}
            className={`${BUTTON_STYLES.base} ${isEnabled ? BUTTON_STYLES.primary : BUTTON_STYLES.success}`}
          >
            {isEnabled ? (
              <>
                <XMarkIcon className="h-3.5 w-3.5" aria-hidden="true" />
                {isTogglingEnabled ? 'Disabling...' : 'Disable'}
              </>
            ) : (
              <>
                <CheckIcon className="h-3.5 w-3.5" aria-hidden="true" />
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
