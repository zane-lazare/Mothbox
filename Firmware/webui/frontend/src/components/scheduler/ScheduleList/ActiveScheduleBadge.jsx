/**
 * ActiveScheduleBadge - Badge indicating active schedule status (Issue #266)
 *
 * Displays a small green badge with "Active" text when a schedule is
 * currently active. Renders nothing when the schedule is not active.
 *
 * @module components/scheduler/ScheduleList/ActiveScheduleBadge
 */

import PropTypes from 'prop-types'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

/**
 * ActiveScheduleBadge component
 *
 * @param {Object} props - Component props
 * @param {boolean} props.isActive - Whether the schedule is currently active
 * @returns {JSX.Element|null} Badge element or null if not active
 *
 * @example
 * <ActiveScheduleBadge isActive={true} />
 * // Renders: [checkmark icon] Active
 *
 * @example
 * <ActiveScheduleBadge isActive={false} />
 * // Renders: nothing
 */
export default function ActiveScheduleBadge({ isActive }) {
  if (!isActive) {
    return null
  }

  return (
    <span
      role="status"
      aria-label="Schedule is active"
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full dark:bg-green-900/30 dark:text-green-400"
    >
      <CheckCircleIcon className="h-3.5 w-3.5" aria-hidden="true" />
      Active
    </span>
  )
}

ActiveScheduleBadge.propTypes = {
  isActive: PropTypes.bool,
}

ActiveScheduleBadge.defaultProps = {
  isActive: false,
}
