/**
 * ConflictPanel component for schedule editor (Issue #331)
 *
 * Displays real-time conflict detection results in the schedule editor drawer.
 * Shows loading, empty, conflict, and error states.
 *
 * @component
 * @example
 * <ConflictPanel
 *   conflictReport={conflictReport}
 *   isValidating={isValidating}
 *   isError={isError}
 *   error={error}
 * />
 */

import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { ConflictList } from '../ConflictResolver'
import type { ConflictReport } from './scheduler-types'

interface ConflictPanelProps {
  conflictReport?: ConflictReport | null;
  isValidating?: boolean;
  isError?: boolean;
  error?: { message?: string } | null;
}

/**
 * ConflictPanel displays conflict detection status in the schedule editor
 */
function ConflictPanel({ conflictReport = null, isValidating = false, isError = false, error = null }: ConflictPanelProps) {
  // Loading state
  if (isValidating) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
        <ArrowPathIcon className="h-8 w-8 animate-spin mb-3" />
        <p className="text-sm font-medium">Checking for conflicts...</p>
      </div>
    )
  }

  // Error state
  if (isError) {
    const errorMessage = error?.message || 'Failed to check for conflicts'
    return (
      <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-4">
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-red-800 dark:text-red-300">
              Validation Error
            </h4>
            <p className="mt-1 text-sm text-red-700 dark:text-red-400">
              {errorMessage}
            </p>
          </div>
        </div>
      </div>
    )
  }

  // No conflicts (empty state)
  if (!conflictReport?.conflicts?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
        <CheckCircleIcon className="h-8 w-8 text-green-500 dark:text-green-400 mb-3" />
        <p className="text-sm font-medium text-green-700 dark:text-green-400">
          No conflicts detected
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Your routines are conflict-free
        </p>
      </div>
    )
  }

  // Conflicts found - use ConflictList
  return (
    <div className="space-y-4">
      {/* Header with blocking indicator */}
      {conflictReport.has_blocking_conflicts && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 px-3 py-2">
          <p className="text-xs font-medium text-red-800 dark:text-red-300">
            Blocking conflicts must be resolved before saving
          </p>
        </div>
      )}

      {/* Conflict list */}
      <ConflictList conflicts={conflictReport.conflicts} />
    </div>
  )
}

export default ConflictPanel
