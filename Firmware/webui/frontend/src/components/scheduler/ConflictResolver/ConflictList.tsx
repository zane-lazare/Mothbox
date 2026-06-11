/**
 * ConflictList component (Issue #229)
 *
 * Displays a list of schedule conflicts grouped by severity.
 * Supports compact mode for embedding in banners.
 *
 * @component
 * @example
 * // Full list
 * <ConflictList conflicts={conflicts} />
 *
 * // Compact mode (max 3, with "+N more" link)
 * <ConflictList conflicts={conflicts} compact onViewAll={() => setShowAll(true)} />
 *
 * // Compact mode with custom limit
 * <ConflictList conflicts={conflicts} compact compactLimit={5} onViewAll={() => setShowAll(true)} />
 */

import { ExclamationTriangleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import ConflictItem, { type Conflict } from './ConflictItem'

/**
 * Default maximum conflicts to show in compact mode
 */
const DEFAULT_COMPACT_LIMIT = 3

/**
 * Grouped conflicts by severity
 */
interface GroupedConflicts {
  errors: Conflict[]
  warnings: Conflict[]
}

/**
 * Component props interface
 */
export interface ConflictListProps {
  conflicts?: Conflict[] | null
  compact?: boolean
  compactLimit?: number
  onViewAll?: () => void
}

/**
 * Sort and group conflicts by severity (errors first)
 */
function groupConflicts(conflicts: Conflict[]): GroupedConflicts {
  const errors = conflicts.filter((c) => c.severity === 'error')
  const warnings = conflicts.filter((c) => c.severity === 'warning')
  return { errors, warnings }
}

/**
 * ConflictList displays conflicts grouped by severity with optional compact mode
 */
function ConflictList({
  conflicts = null,
  compact = false,
  compactLimit = DEFAULT_COMPACT_LIMIT,
  onViewAll = undefined
}: ConflictListProps) {
  // Handle empty/null/undefined conflicts
  if (!conflicts || conflicts.length === 0) {
    return null
  }

  const { errors, warnings } = groupConflicts(conflicts)
  const totalCount = conflicts.length
  const blockingCount = errors.length

  // In compact mode, limit to compactLimit conflicts
  let displayConflicts: Conflict[] = []
  let hiddenCount = 0

  if (compact) {
    // Prioritize errors, then warnings
    const combined = [...errors, ...warnings]
    displayConflicts = combined.slice(0, compactLimit)
    hiddenCount = combined.length - displayConflicts.length
  } else {
    displayConflicts = [...errors, ...warnings]
  }

  // Determine which sections to show based on what's in displayConflicts
  const displayErrors = displayConflicts.filter((c) => c.severity === 'error')
  const displayWarnings = displayConflicts.filter((c) => c.severity === 'warning')

  const showErrorSection = displayErrors.length > 0
  const showWarningSection = displayWarnings.length > 0
  const showBothSections = showErrorSection && showWarningSection

  return (
    <div className="space-y-4 dark:text-gray-100">
      {/* Summary Header */}
      <div className="flex items-center gap-2 text-sm font-medium">
        <span>
          {totalCount} conflict{totalCount !== 1 ? 's' : ''} detected
        </span>
        {blockingCount > 0 && (
          <span className="text-red-600 dark:text-red-400">
            ({blockingCount} blocking)
          </span>
        )}
      </div>

      {/* Error Section */}
      {showErrorSection && (
        <section>
          {showBothSections && (
            <h3 className="flex items-center gap-1.5 text-sm font-medium text-red-800 dark:text-red-300 mb-2">
              <ExclamationTriangleIcon className="h-4 w-4" />
              Blocking Conflicts
            </h3>
          )}
          <ul
            role="list"
            aria-label={`${displayErrors.length} blocking conflict${displayErrors.length !== 1 ? 's' : ''}`}
            className="space-y-2"
          >
            {displayErrors.map((conflict, index) => (
              <ConflictItem
                key={`error-${conflict.event1_id}-${conflict.event2_id}-${index}`}
                conflict={conflict}
              />
            ))}
          </ul>
        </section>
      )}

      {/* Warning Section */}
      {showWarningSection && (
        <section>
          {showBothSections && (
            <h3 className="flex items-center gap-1.5 text-sm font-medium text-amber-800 dark:text-amber-300 mb-2">
              <ExclamationCircleIcon className="h-4 w-4" />
              Warnings
            </h3>
          )}
          <ul
            role="list"
            aria-label={`${displayWarnings.length} warning${displayWarnings.length !== 1 ? 's' : ''}`}
            className="space-y-2"
          >
            {displayWarnings.map((conflict, index) => (
              <ConflictItem
                key={`warning-${conflict.event1_id}-${conflict.event2_id}-${index}`}
                conflict={conflict}
              />
            ))}
          </ul>
        </section>
      )}

      {/* Show "+N more" link in compact mode if there are hidden conflicts */}
      {compact && hiddenCount > 0 && onViewAll && (
        <button
          type="button"
          onClick={onViewAll}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
        >
          +{hiddenCount} more conflict{hiddenCount !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  )
}

export default ConflictList
