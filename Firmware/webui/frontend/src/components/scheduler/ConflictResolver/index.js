/**
 * Conflict Resolver components (Issue #229)
 *
 * Components for displaying and resolving schedule conflicts.
 */

// PropTypes - exported first for use in other components
export {
  ConflictPropType,
  ConflictsPropType,
  CONFLICT_TYPES,
  SEVERITY_LEVELS,
  CONFLICT_TYPE_LABELS,
  SEVERITY_LABELS,
} from './ConflictPropTypes'

// Components
export { default as ConflictItem } from './ConflictItem'
export { default as ConflictList } from './ConflictList'
export { default as ConflictWarningBanner } from './ConflictWarningBanner'
