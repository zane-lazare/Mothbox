/**
 * ConflictSummary - Conflict count banner for DayTimeline (Issue #326)
 *
 * Displays a summary of conflicts in the timeline with counts
 * broken down by severity (collisions vs warnings).
 *
 * @module components/scheduler/DayTimeline/ConflictSummary
 */

import { memo } from 'react'
import PropTypes from 'prop-types'
import { countConflictsBySeverity } from './dayTimelineUtils'

/**
 * ConflictSummary component
 *
 * @param {Object} props - Component props
 * @param {Array} props.conflicts - Array of conflict objects
 * @returns {JSX.Element|null} Conflict summary banner or null if no conflicts
 *
 * @example
 * <ConflictSummary conflicts={[
 *   { severity: 'error', message: '...' },
 *   { severity: 'warning', message: '...' }
 * ]} />
 */
function ConflictSummary({ conflicts }) {
  const counts = countConflictsBySeverity(conflicts)

  // Don't render if no conflicts
  if (counts.total === 0) {
    return null
  }

  // Build breakdown text
  const breakdownParts = []
  if (counts.errors > 0) {
    breakdownParts.push(`${counts.errors} collision${counts.errors > 1 ? 's' : ''}`)
  }
  if (counts.warnings > 0) {
    breakdownParts.push(`${counts.warnings} warning${counts.warnings > 1 ? 's' : ''}`)
  }
  const breakdownText = breakdownParts.join(', ')

  const ariaLabel = `${counts.total} conflicts: ${breakdownText}`

  return (
    <div
      data-testid="conflict-summary"
      className="mb-6 p-3 border border-red-900/50 rounded text-sm flex items-center gap-3"
      role="status"
      aria-label={ariaLabel}
    >
      <span className="text-red-400">
        {counts.total} conflict{counts.total > 1 ? 's' : ''}
      </span>
      <span className="text-gray-600">|</span>
      <span className="text-gray-500">{breakdownText}</span>
    </div>
  )
}

ConflictSummary.propTypes = {
  /** Array of conflict objects with severity field */
  conflicts: PropTypes.arrayOf(
    PropTypes.shape({
      severity: PropTypes.oneOf(['error', 'warning']).isRequired,
    })
  ).isRequired,
}

export default memo(ConflictSummary)
