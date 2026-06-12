/**
 * Conflict Resolver components (Issue #229)
 *
 * Components for displaying and resolving schedule conflicts.
 */

// Types and constants - exported first for use in other components
export {
  CONFLICT_TYPES,
  SEVERITY_LEVELS,
  CONFLICT_TYPE_LABELS,
  SEVERITY_LABELS,
} from './ConflictPropTypes'

export type {
  Conflict,
  ConflictsList,
  ConflictType,
  SeverityLevel,
} from './ConflictPropTypes'

// Components
export { default as ConflictItem } from './ConflictItem'
export { default as ConflictList } from './ConflictList'
export { default as ConflictWarningBanner } from './ConflictWarningBanner'

export type { ConflictItemProps } from './ConflictItem'
export type { ConflictListProps } from './ConflictList'
export type { ConflictWarningBannerProps } from './ConflictWarningBanner'
