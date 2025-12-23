/**
 * ScheduleCard - Display schedule with trigger info and action buttons (Issue #266)
 *
 * Displays a schedule card with:
 * - Schedule name and description
 * - Active status badge
 * - Trigger type icon and summary
 * - Action buttons (Edit, Activate/Deactivate, Delete)
 * - Loading states for async operations
 *
 * @module components/scheduler/ScheduleList/ScheduleCard
 */

import { memo, useMemo } from 'react'
import PropTypes from 'prop-types'
import {
  ClockIcon,
  SunIcon,
  MoonIcon,
  BoltIcon,
  PencilIcon,
  PlayIcon,
  StopIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import ActiveScheduleBadge from './ActiveScheduleBadge'
import { SchedulePropType } from '../ScheduleEditor/propTypes'
import { MOON_PHASES } from '../ScheduleEditor/constants'

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

/** Icon component map for trigger types */
const TRIGGER_ICON_MAP = {
  interval: ClockIcon,
  solar: SunIcon,
  moon_phase: MoonIcon,
  fixed_time: ClockIcon,
  sensor: BoltIcon,
}

/**
 * Format trigger summary text
 * @param {Object} trigger - Trigger configuration
 * @returns {string} Summary text
 */
function formatTriggerSummary(trigger) {
  if (!trigger) return ''

  switch (trigger.trigger_type) {
    case 'interval': {
      const startTime = trigger.time_window?.start_time || '00:00'
      const endTime = trigger.time_window?.end_time || '23:59'
      return `Every ${trigger.interval_minutes} min, ${startTime} - ${endTime}`
    }

    case 'solar': {
      const event = trigger.solar_event || 'sunset'
      const offset = trigger.offset_minutes || 0
      if (offset === 0) {
        return `At ${event}`
      }
      const sign = offset >= 0 ? '+' : ''
      return `At ${event} ${sign}${offset} min`
    }

    case 'moon_phase': {
      const phase = trigger.moon_phase || 'full'
      // Find label from MOON_PHASES constant
      const phaseLabel =
        MOON_PHASES.find((p) => p.value === phase)?.label || phase.replace('_', ' ')
      const time = trigger.time_of_day || '20:00'
      return `${phaseLabel}, at ${time}`
    }

    case 'fixed_time': {
      const time = trigger.time_of_day || '12:00'
      return `Daily at ${time}`
    }

    case 'sensor': {
      const sensorType = trigger.sensor_type || 'light'
      const comparison = trigger.comparison || 'lt'
      const threshold = trigger.threshold || 0
      const compSymbol = {
        gt: '>',
        lt: '<',
        eq: '=',
        gte: '≥',
        lte: '≤',
      }[comparison]
      return `When ${sensorType} ${compSymbol} ${threshold}`
    }

    default:
      return ''
  }
}

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
  const triggerSummary = formatTriggerSummary(schedule.trigger)

  // Memoize icon to avoid recreating on every render
  const triggerIcon = useMemo(() => {
    const Icon = TRIGGER_ICON_MAP[schedule.trigger?.trigger_type] || ClockIcon
    return <Icon className="h-5 w-5 text-gray-400 dark:text-gray-500" aria-hidden="true" />
  }, [schedule.trigger?.trigger_type])

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

      {/* Description */}
      {schedule.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{schedule.description}</p>
      )}

      {/* Trigger Info */}
      <div className="flex items-center gap-2 mb-4">
        {triggerIcon}
        <span className="text-sm text-gray-700 dark:text-gray-300">{triggerSummary}</span>
      </div>

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
