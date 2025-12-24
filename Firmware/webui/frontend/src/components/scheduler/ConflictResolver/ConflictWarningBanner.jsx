/**
 * ConflictWarningBanner component (Issue #229)
 *
 * Displays a warning banner when schedule conflicts are detected.
 * Shows severity-appropriate styling and allows viewing conflict details.
 *
 * @component
 * @example
 * // Blocking conflicts (prevents activation)
 * <ConflictWarningBanner
 *   conflicts={conflicts}
 *   hasBlockingConflicts
 *   blockingCount={2}
 *   warningCount={1}
 *   onViewDetails={() => openModal()}
 * />
 *
 * // Warnings only (allows activation with confirmation)
 * <ConflictWarningBanner
 *   conflicts={conflicts}
 *   warningCount={3}
 *   onDismiss={() => setDismissed(true)}
 * />
 */

import { useState } from 'react'
import PropTypes from 'prop-types'
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { ConflictsPropType } from './ConflictPropTypes'
import ConflictList from './ConflictList'

/**
 * Styling for severity variants
 */
const SEVERITY_STYLES = {
  error: {
    container: [
      'bg-red-50 border-red-200',
      'dark:bg-red-900/20 dark:border-red-800',
    ].join(' '),
    icon: 'text-red-600 dark:text-red-400',
    title: 'text-red-800 dark:text-red-200',
    text: 'text-red-700 dark:text-red-300',
    button: [
      'text-red-700 bg-white border-red-300',
      'hover:bg-red-50 focus:ring-red-500',
      'dark:bg-red-900/50 dark:text-red-200 dark:border-red-700 dark:hover:bg-red-900',
    ].join(' '),
  },
  warning: {
    container: [
      'bg-amber-50 border-amber-200',
      'dark:bg-amber-900/20 dark:border-amber-800',
    ].join(' '),
    icon: 'text-amber-600 dark:text-amber-400',
    title: 'text-amber-800 dark:text-amber-200',
    text: 'text-amber-700 dark:text-amber-300',
    button: [
      'text-amber-700 bg-white border-amber-300',
      'hover:bg-amber-50 focus:ring-amber-500',
      'dark:bg-amber-900/50 dark:text-amber-200 dark:border-amber-700 dark:hover:bg-amber-900',
    ].join(' '),
  },
}

/**
 * Button base classes
 */
const BUTTON_BASE = [
  'inline-flex items-center gap-1.5 px-3 py-1.5',
  'text-sm font-medium border rounded-md',
  'focus:outline-none focus:ring-2 focus:ring-offset-2',
  'transition-colors',
].join(' ')

/**
 * ConflictWarningBanner displays a warning when conflicts are detected
 */
function ConflictWarningBanner({
  conflicts,
  hasBlockingConflicts = false,
  blockingCount = 0,
  warningCount = 0,
  onViewDetails,
  onDismiss,
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Handle empty/null/undefined conflicts
  if (!conflicts || conflicts.length === 0) {
    return null
  }

  // Calculate counts if not provided
  const actualBlockingCount = blockingCount || conflicts.filter((c) => c.severity === 'error').length
  const actualWarningCount = warningCount || conflicts.filter((c) => c.severity === 'warning').length
  const isBlocking = hasBlockingConflicts || actualBlockingCount > 0
  const totalCount = conflicts.length

  const styles = isBlocking ? SEVERITY_STYLES.error : SEVERITY_STYLES.warning
  const Icon = isBlocking ? ExclamationTriangleIcon : ExclamationCircleIcon

  const role = isBlocking ? 'alert' : 'status'
  const ariaLive = isBlocking ? 'assertive' : 'polite'

  const handleToggleExpand = () => {
    setIsExpanded((prev) => !prev)
    if (!isExpanded && onViewDetails) {
      onViewDetails()
    }
  }

  return (
    <div
      role={role}
      aria-live={ariaLive}
      className={`border rounded-lg p-4 ${styles.container}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Icon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${styles.icon}`} />

          <div>
            {/* Title */}
            <h4 className={`font-medium ${styles.title}`}>
              {totalCount} conflict{totalCount !== 1 ? 's' : ''} detected
              {actualBlockingCount > 0 && (
                <span className="ml-2 text-sm font-normal">
                  ({actualBlockingCount} blocking
                  {actualWarningCount > 0 && `, ${actualWarningCount} warning${actualWarningCount !== 1 ? 's' : ''}`})
                </span>
              )}
            </h4>

            {/* Message */}
            <p className={`text-sm mt-1 ${styles.text}`}>
              {isBlocking
                ? 'Cannot activate schedule with blocking conflicts. Please resolve them first.'
                : 'Potential scheduling issues detected. Review before activating.'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* View Details / Hide Details button */}
          <button
            type="button"
            onClick={handleToggleExpand}
            className={`${BUTTON_BASE} ${styles.button}`}
          >
            {isExpanded ? (
              <>
                <ChevronUpIcon className="h-4 w-4" />
                Hide Details
              </>
            ) : (
              <>
                <ChevronDownIcon className="h-4 w-4" />
                View Details
              </>
            )}
          </button>

          {/* Dismiss button (warnings only) */}
          {!isBlocking && onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className={`${BUTTON_BASE} ${styles.button}`}
              aria-label="Dismiss"
            >
              <XMarkIcon className="h-4 w-4" />
              Dismiss
            </button>
          )}
        </div>
      </div>

      {/* Expanded Conflict List */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-current/10">
          <ConflictList conflicts={conflicts} />
        </div>
      )}
    </div>
  )
}

ConflictWarningBanner.propTypes = {
  /** Array of conflict objects */
  conflicts: ConflictsPropType,
  /** Whether there are blocking (error severity) conflicts */
  hasBlockingConflicts: PropTypes.bool,
  /** Number of blocking conflicts */
  blockingCount: PropTypes.number,
  /** Number of warning conflicts */
  warningCount: PropTypes.number,
  /** Callback when "View Details" is clicked */
  onViewDetails: PropTypes.func,
  /** Callback when "Dismiss" is clicked (warnings only) */
  onDismiss: PropTypes.func,
}

ConflictWarningBanner.defaultProps = {
  conflicts: null,
  hasBlockingConflicts: false,
  blockingCount: 0,
  warningCount: 0,
  onViewDetails: undefined,
  onDismiss: undefined,
}

export default ConflictWarningBanner
