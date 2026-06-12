/**
 * Shared types for Conflict Resolver components (Issue #229)
 *
 * These types match the backend Conflict dataclass from
 * webui/backend/lib/schedule_conflict.py
 */

/**
 * Valid conflict types from backend
 */
export const CONFLICT_TYPES = ['time_overlap', 'resource_contention', 'gpio_state_conflict'] as const

export type ConflictType = typeof CONFLICT_TYPES[number]

/**
 * Severity levels
 * - error: Blocking conflicts that prevent activation
 * - warning: Advisory conflicts that allow activation with warning
 */
export const SEVERITY_LEVELS = ['error', 'warning'] as const

export type SeverityLevel = typeof SEVERITY_LEVELS[number]

/**
 * Interface for a single conflict
 *
 * Matches backend Conflict.to_dict() output from schedule_conflict.py
 */
export interface Conflict {
  conflict_type: ConflictType
  severity: SeverityLevel
  event1_id: string
  event1_name: string
  event2_id: string
  event2_name: string
  start_time: string
  end_time: string
  resource?: string
  message: string
  suggested_resolution: string
}

/**
 * Type for a list of conflicts
 */
export type ConflictsList = Conflict[]

/**
 * Human-readable labels for conflict types
 */
export const CONFLICT_TYPE_LABELS: Record<ConflictType, string> = {
  time_overlap: 'Time Overlap',
  resource_contention: 'Resource Conflict',
  gpio_state_conflict: 'GPIO State Conflict',
}

/**
 * Human-readable labels for severity levels
 */
export const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  error: 'Blocking',
  warning: 'Warning',
}

export default Conflict
