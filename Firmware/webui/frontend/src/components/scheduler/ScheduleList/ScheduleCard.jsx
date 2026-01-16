/**
 * ScheduleCard - Display schedule with routine indicators and action buttons (Issue #266)
 *
 * Displays a schedule card with:
 * - Schedule name and auto-generated description
 * - Active status badge
 * - Colored routine indicator dots (orange=GPIO, blue=camera, purple=HDR)
 * - Routine count
 * - Action buttons (Edit, Activate/Deactivate, Delete)
 * - Loading states for async operations
 *
 * @module components/scheduler/ScheduleList/ScheduleCard
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { PencilIcon, PlayIcon, StopIcon, TrashIcon } from '@heroicons/react/24/outline'
import ActiveScheduleBadge from './ActiveScheduleBadge'
import { SchedulePropType } from '../ScheduleEditor/propTypes'
import {
  getPrimaryActionColor,
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

/** Danger button style for Delete */
const BUTTON_DANGER = [
  BUTTON_BASE,
  'text-red-700 bg-white border border-red-300',
  'hover:bg-red-50 focus:ring-red-500',
  'dark:bg-gray-700 dark:text-red-400 dark:border-red-900 dark:hover:bg-red-900/20',
].join(' ')

/**
 * ScheduleCard component
 *
 * @param {Object} props - Component props
 * @param {Object} props.schedule - Schedule object
 * @param {boolean} props.isActive - Whether this schedule is active
 * @param {Function} props.onEdit - Callback when Edit button clicked
 * @param {Function} props.onActivate - Callback when Activate button clicked
 * @param {Function} props.onDeactivate - Callback when Deactivate button clicked
 * @param {Function} props.onDelete - Callback when Delete button clicked
 * @param {boolean} [props.isEditing] - Loading state for edit
 * @param {boolean} [props.isActivating] - Loading state for activation
 * @param {boolean} [props.isDeactivating] - Loading state for deactivation
 * @param {boolean} [props.isDeleting] - Loading state for deletion
 * @returns {JSX.Element} Schedule card component
 *
 * @example
 * <ScheduleCard
 *   schedule={schedule}
 *   isActive={false}
 *   onEdit={handleEdit}
 *   onActivate={handleActivate}
 *   onDeactivate={handleDeactivate}
 *   onDelete={handleDelete}
 * />
 */
function ScheduleCard({
  schedule,
  isActive,
  onEdit,
  onActivate,
  onDeactivate,
  onDelete,
  isEditing = false,
  isActivating = false,
  isDeactivating = false,
  isDeleting = false,
}) {
  const nameId = `schedule-name-${schedule.schedule_id}`

  const handleEdit = () => {
    onEdit(schedule)
  }

  const handleActivate = () => {
    onActivate(schedule)
  }

  const handleDeactivate = () => {
    onDeactivate(schedule)
  }

  const handleDelete = () => {
    onDelete(schedule)
  }

  return (
    <article
      role="article"
      aria-labelledby={nameId}
      className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4"
    >
      {/* Header: Name and Active Badge */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 id={nameId} className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {schedule.name}
          </h3>
        </div>
        <ActiveScheduleBadge isActive={isActive} />
      </div>

      {/* Description - manual or auto-generated */}
      {(schedule.description || schedule.routines?.length > 0) && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {schedule.description || generateScheduleDescription(schedule.routines)}
        </p>
      )}

      {/* Routine Indicators */}
      {schedule.routines?.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          {schedule.routines.map((routine, index) => (
            <div
              key={routine.routine_id || index}
              className={`w-1.5 h-1.5 rounded-full ${getPrimaryActionColor(routine.actions)}`}
              title={generateRoutineName(routine)}
            />
          ))}
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
            {schedule.routines.length} routine{schedule.routines.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={handleEdit}
          disabled={isEditing || isActivating || isDeactivating || isDeleting}
          className={BUTTON_PRIMARY}
        >
          <PencilIcon className="h-4 w-4" aria-hidden="true" />
          {isEditing ? 'Editing...' : 'Edit'}
        </button>

        {isActive ? (
          <button
            type="button"
            onClick={handleDeactivate}
            disabled={isEditing || isActivating || isDeactivating || isDeleting}
            className={BUTTON_PRIMARY}
          >
            <StopIcon className="h-4 w-4" aria-hidden="true" />
            {isDeactivating ? 'Deactivating...' : 'Deactivate'}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleActivate}
            disabled={isEditing || isActivating || isDeactivating || isDeleting}
            className={BUTTON_PRIMARY}
          >
            <PlayIcon className="h-4 w-4" aria-hidden="true" />
            {isActivating ? 'Activating...' : 'Activate'}
          </button>
        )}

        <button
          type="button"
          onClick={handleDelete}
          disabled={isEditing || isActivating || isDeactivating || isDeleting}
          className={BUTTON_DANGER}
        >
          <TrashIcon className="h-4 w-4" aria-hidden="true" />
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </article>
  )
}

ScheduleCard.propTypes = {
  schedule: SchedulePropType.isRequired,
  isActive: PropTypes.bool,
  onEdit: PropTypes.func.isRequired,
  onActivate: PropTypes.func.isRequired,
  onDeactivate: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  isEditing: PropTypes.bool,
  isActivating: PropTypes.bool,
  isDeactivating: PropTypes.bool,
  isDeleting: PropTypes.bool,
}

export default memo(ScheduleCard)
