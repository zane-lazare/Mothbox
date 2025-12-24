/**
 * ConflictItem component (Issue #229)
 *
 * Displays a single schedule conflict with severity-based styling.
 * Shows conflict type, involved patterns, time range, and resolution suggestion.
 *
 * @component
 * @example
 * const conflict = {
 *   conflict_type: 'resource_contention',
 *   severity: 'error',
 *   event1_name: 'UV Capture',
 *   event2_name: 'Flash Photo',
 *   start_time: '2024-06-15T21:30:00Z',
 *   end_time: '2024-06-15T21:45:00Z',
 *   resource: 'camera',
 *   message: 'Camera conflict...',
 *   suggested_resolution: 'Adjust timing...',
 * }
 * return <ConflictItem conflict={conflict} />
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  ClockIcon,
  CubeIcon,
  BoltIcon,
} from '@heroicons/react/24/outline'
import { ConflictPropType, CONFLICT_TYPE_LABELS } from './ConflictPropTypes'
import { formatTime } from '../CalendarView/calendarUtils'

/**
 * Get the appropriate icon for a conflict type
 */
function getConflictTypeIcon(conflictType) {
  switch (conflictType) {
    case 'time_overlap':
      return ClockIcon
    case 'resource_contention':
      return CubeIcon
    case 'gpio_state_conflict':
      return BoltIcon
    default:
      return ExclamationCircleIcon
  }
}

/**
 * Styling constants for severity variants
 */
const SEVERITY_STYLES = {
  error: {
    container: [
      'bg-red-50 border-red-200 text-red-900',
      'dark:bg-red-900/20 dark:border-red-800 dark:text-red-100',
    ].join(' '),
    icon: 'text-red-600 dark:text-red-400',
    badge: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200',
  },
  warning: {
    container: [
      'bg-amber-50 border-amber-200 text-amber-900',
      'dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-100',
    ].join(' '),
    icon: 'text-amber-600 dark:text-amber-400',
    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200',
  },
}

/**
 * ConflictItem displays a single schedule conflict with appropriate styling
 */
function ConflictItem({ conflict }) {
  const {
    conflict_type,
    severity,
    event1_name,
    event2_name,
    start_time,
    end_time,
    resource,
    message,
    suggested_resolution,
  } = conflict

  const styles = SEVERITY_STYLES[severity] || SEVERITY_STYLES.warning
  const SeverityIcon = severity === 'error' ? ExclamationTriangleIcon : ExclamationCircleIcon
  const TypeIcon = getConflictTypeIcon(conflict_type)
  const typeLabel = CONFLICT_TYPE_LABELS[conflict_type] || conflict_type

  const ariaLabel = `${severity === 'error' ? 'Blocking' : 'Warning'} conflict: ${message}`

  return (
    <li
      role="listitem"
      aria-label={ariaLabel}
      className={`p-3 border rounded-lg ${styles.container}`}
    >
      {/* Header: Icon + Type Badge */}
      <div className="flex items-start gap-2">
        <SeverityIcon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${styles.icon}`} />

        <div className="flex-1 min-w-0">
          {/* Conflict Type Badge */}
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded ${styles.badge}`}
            >
              <TypeIcon className="h-3 w-3" />
              {typeLabel}
            </span>
            {resource && (
              <span className="text-xs opacity-75">
                ({resource})
              </span>
            )}
          </div>

          {/* Pattern Names */}
          <div className="text-sm font-medium mb-1">
            <span>{event1_name}</span>
            <span className="mx-1 opacity-50">↔</span>
            <span>{event2_name}</span>
          </div>

          {/* Time Range */}
          <div className="text-xs opacity-75 mb-2">
            {formatTime(start_time)} – {formatTime(end_time)}
          </div>

          {/* Message */}
          <p className="text-sm mb-2">{message}</p>

          {/* Suggested Resolution */}
          {suggested_resolution && (
            <div className="text-xs opacity-90 bg-white/50 dark:bg-black/20 rounded p-2">
              <span className="font-medium">Suggestion: </span>
              {suggested_resolution}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}

ConflictItem.propTypes = {
  /** The conflict object to display */
  conflict: ConflictPropType.isRequired,
}

export default memo(ConflictItem)
