/**
 * Shared PropTypes for Conflict Resolver components (Issue #229)
 *
 * These PropTypes match the backend Conflict dataclass from
 * webui/backend/lib/schedule_conflict.py
 */

import PropTypes from 'prop-types'

/**
 * Valid conflict types from backend
 */
export const CONFLICT_TYPES = ['time_overlap', 'resource_contention', 'gpio_state_conflict']

/**
 * Severity levels
 * - error: Blocking conflicts that prevent activation
 * - warning: Advisory conflicts that allow activation with warning
 */
export const SEVERITY_LEVELS = ['error', 'warning']

/**
 * PropType for a single conflict
 *
 * Matches backend Conflict.to_dict() output from schedule_conflict.py
 */
export const ConflictPropType = PropTypes.shape({
  conflict_type: PropTypes.oneOf(CONFLICT_TYPES).isRequired,
  severity: PropTypes.oneOf(SEVERITY_LEVELS).isRequired,
  event1_id: PropTypes.string.isRequired,
  event1_name: PropTypes.string.isRequired,
  event2_id: PropTypes.string.isRequired,
  event2_name: PropTypes.string.isRequired,
  start_time: PropTypes.string.isRequired,
  end_time: PropTypes.string.isRequired,
  resource: PropTypes.string,
  message: PropTypes.string.isRequired,
  suggested_resolution: PropTypes.string.isRequired,
})

/**
 * PropType for a list of conflicts
 */
export const ConflictsPropType = PropTypes.arrayOf(ConflictPropType)

/**
 * Human-readable labels for conflict types
 */
export const CONFLICT_TYPE_LABELS = {
  time_overlap: 'Time Overlap',
  resource_contention: 'Resource Conflict',
  gpio_state_conflict: 'GPIO State Conflict',
}

/**
 * Human-readable labels for severity levels
 */
export const SEVERITY_LABELS = {
  error: 'Blocking',
  warning: 'Warning',
}

export default ConflictPropType
