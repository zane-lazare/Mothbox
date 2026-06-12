/**
 * DayTimeline utility functions (Issue #326)
 *
 * Provides pure utility functions for the DayTimeline component:
 * - Grouping executions by hour
 * - Formatting time strings
 * - Finding conflicts for specific hours
 * - Getting action type display information
 *
 * @module components/scheduler/DayTimeline/dayTimelineUtils
 *
 * @note TIMEZONE HANDLING: All times in this module are converted to the user's
 * local timezone for display. The backend API returns times in ISO 8601 UTC format
 * (e.g., "2025-12-17T18:30:00Z") and this module uses JavaScript's Date object to
 * convert them to local time before extracting hours/minutes/dates.
 */

import {
  ACTION_TYPE_COLORS,
  DEFAULT_ACTION_COLORS,
  isHdrAction,
} from './dayTimelineConstants'
import type { ActionType } from '@/utils/schedulerApi'

// =============================================================================
// Type Definitions
// =============================================================================

/**
 * Action object within an execution
 */
export interface ExecutionAction {
  time?: string
  action_name?: string
  action_type?: ActionType
  offset_minutes?: number
}

/**
 * Execution object from preview API
 */
export interface Execution {
  id?: string | number
  pattern_id: string
  pattern_name: string
  start_time: string
  end_time?: string
  actions?: ExecutionAction[]
}

/**
 * Conflict severity levels
 */
export type ConflictSeverity = 'error' | 'warning'

/**
 * Conflict type identifiers
 */
export type ConflictType = 'time_overlap' | 'resource_contention' | 'gpio_state_conflict'

/**
 * Conflict object from preview API
 */
export interface Conflict {
  id?: string
  conflict_type?: ConflictType
  severity: ConflictSeverity
  event1_id?: string
  event1_name?: string
  event2_id?: string
  event2_name?: string
  start_time?: string
  end_time?: string
  message?: string
}

/**
 * Cycle information from preview API
 */
export interface CycleInfo {
  start_hour?: number
  end_hour?: number
  spans_midnight?: boolean
  suggested_preview_days?: number
}

/**
 * Conflict count summary
 */
export interface ConflictCounts {
  total: number
  errors: number
  warnings: number
}

/**
 * Display colors for action types
 */
export interface ActionColors {
  bg: string
  text: string
}

/**
 * Collapsed hour indicator
 */
export interface CollapsedHour {
  type: 'collapsed'
  count: number
}

/**
 * Regular hour display
 */
export interface RegularHour {
  type: 'hour'
  hour: number
}

/**
 * Display hour (either collapsed or regular)
 */
export type DisplayHour = CollapsedHour | RegularHour

/**
 * Map of hour (0-23) to executions
 */
export type ExecutionsByHour = Record<number, Execution[]>

/**
 * Pattern count map for fingerprinting
 */
interface PatternCounts {
  [patternId: string]: number
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Logs a warning in development mode for invalid time strings.
 * @param isoString - The invalid ISO string
 * @param context - Function name for context
 */
function warnInvalidTime(isoString: string, context: string): void {
  if (import.meta.env.DEV) {
    console.warn(`[${context}] Invalid ISO time string:`, isoString)
  }
}

/**
 * Extracts the hour (0-23) from an ISO datetime string in local timezone.
 *
 * @param isoString - ISO datetime string (e.g., "2025-12-17T18:30:00Z")
 * @returns Hour number (0-23) in local timezone, or null if invalid
 */
export function getHourFromIsoTime(isoString: string): number | null {
  if (!isoString || typeof isoString !== 'string') {
    return null
  }

  // Convert to Date and extract local hour
  // This ensures times display correctly in the user's timezone
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    warnInvalidTime(isoString, 'getHourFromIsoTime')
    return null
  }

  return date.getHours()
}

/**
 * Extracts the minute (0-59) from an ISO datetime string in local timezone.
 *
 * @param isoString - ISO datetime string
 * @returns Minute number (0-59) in local timezone, or null if invalid
 */
export function getMinuteFromIsoTime(isoString: string): number | null {
  if (!isoString || typeof isoString !== 'string') {
    return null
  }

  // Convert to Date and extract local minute
  // This ensures times display correctly in the user's timezone
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    warnInvalidTime(isoString, 'getMinuteFromIsoTime')
    return null
  }

  return date.getMinutes()
}

/**
 * Formats an hour number to a display string (e.g., 18 -> "18:00").
 *
 * @param hour - Hour number (0-23)
 * @returns Formatted time string
 */
export function formatHourLabel(hour: number): string {
  if (typeof hour !== 'number' || hour < 0 || hour > 23) {
    return ''
  }
  return `${hour}:00`
}

/**
 * Formats an ISO datetime string to a short time string in local timezone (e.g., "18:30").
 *
 * @param isoString - ISO datetime string
 * @returns Formatted time string (HH:MM) in local timezone
 */
export function formatTimeShort(isoString: string): string {
  if (!isoString || typeof isoString !== 'string') {
    return ''
  }

  // Convert to Date and extract local time
  // This ensures times display correctly in the user's timezone
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    warnInvalidTime(isoString, 'formatTimeShort')
    return ''
  }

  const hours = date.getHours()
  const minutes = date.getMinutes()
  return `${hours}:${minutes.toString().padStart(2, '0')}`
}

/**
 * Extracts local date (YYYY-MM-DD) from an ISO datetime string.
 * Converts UTC time to local timezone before extracting date.
 *
 * @param isoString - ISO datetime string
 * @returns Local date in YYYY-MM-DD format, or null if invalid
 */
export function getLocalDateFromIso(isoString: string): string | null {
  if (!isoString || typeof isoString !== 'string') {
    return null
  }
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    return null
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

/**
 * Get the next calendar date key (YYYY-MM-DD) from a given date string.
 * Handles month/year boundaries correctly by using Date arithmetic.
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @returns Next date in YYYY-MM-DD format
 */
export function getNextDateKey(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00') // noon avoids DST edge cases
  d.setDate(d.getDate() + 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/**
 * Groups executions by hour (0-23) for a given local date.
 *
 * @param executions - Array of execution objects with start_time
 * @param date - Local date string (YYYY-MM-DD) to filter by
 * @returns Map of hour (0-23) -> array of executions
 */
export function groupExecutionsByHour(executions: Execution[], date: string): ExecutionsByHour {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  const grouped: ExecutionsByHour = {}

  executions.forEach((execution) => {
    if (!execution.start_time) return

    // Check if execution is on the target local date
    const executionDate = getLocalDateFromIso(execution.start_time)
    if (date && executionDate !== date) return

    const hour = getHourFromIsoTime(execution.start_time)
    if (hour === null) return

    if (!grouped[hour]) {
      grouped[hour] = []
    }

    grouped[hour].push(execution)
  })

  return grouped
}

/**
 * Finds the most severe conflict affecting a specific hour.
 *
 * @param conflicts - Array of conflict objects with start_time/end_time
 * @param hour - Hour to check (0-23) in local timezone
 * @param date - Local date string (YYYY-MM-DD)
 * @returns Most severe conflict for this hour, or null
 */
export function getConflictForHour(conflicts: Conflict[], hour: number, date: string): Conflict | null {
  if (!conflicts || !Array.isArray(conflicts) || conflicts.length === 0) {
    return null
  }

  if (typeof hour !== 'number' || hour < 0 || hour > 23) {
    return null
  }

  // Find all conflicts that affect this hour
  const matchingConflicts = conflicts.filter((conflict) => {
    if (!conflict.start_time) return false

    // Check if conflict is on the target local date
    const conflictDate = getLocalDateFromIso(conflict.start_time)
    if (date && conflictDate !== date) return false

    const conflictHour = getHourFromIsoTime(conflict.start_time)
    return conflictHour === hour
  })

  if (matchingConflicts.length === 0) {
    return null
  }

  // Return the most severe conflict (error > warning)
  const errorConflict = matchingConflicts.find((c) => c.severity === 'error')
  return errorConflict || matchingConflicts[0]
}

/**
 * Gets display information for an action type.
 *
 * @param actionType - Action type ('camera', 'gpio', 'gps_sync', 'service')
 * @param actionName - Action name (used to detect HDR)
 * @returns { bg, text, darkBg, darkText } Tailwind classes
 */
export function getActionTypeDisplay(actionType: string, actionName: string): ActionColors {
  // Check for HDR first (special purple color)
  if (isHdrAction(actionName)) {
    return ACTION_TYPE_COLORS.hdr
  }

  // Return colors for known action types, or default
  return ACTION_TYPE_COLORS[actionType] || DEFAULT_ACTION_COLORS
}

/**
 * Counts conflicts by severity.
 *
 * @param conflicts - Array of conflict objects
 * @returns { total, errors, warnings }
 */
export function countConflictsBySeverity(conflicts: Conflict[]): ConflictCounts {
  if (!conflicts || !Array.isArray(conflicts)) {
    return { total: 0, errors: 0, warnings: 0 }
  }

  const errors = conflicts.filter((c) => c.severity === 'error').length
  const warnings = conflicts.filter((c) => c.severity === 'warning').length

  return {
    total: conflicts.length,
    errors,
    warnings,
  }
}

/**
 * Checks if an execution is involved in a conflict.
 *
 * @param execution - Execution object with pattern_id
 * @param conflicts - Array of conflict objects
 * @returns Conflict affecting this execution, or null
 */
export function getConflictForExecution(execution: Execution, conflicts: Conflict[]): Conflict | null {
  if (!execution || !conflicts || !Array.isArray(conflicts)) {
    return null
  }

  // Find conflict by matching pattern_id or execution time
  const match = conflicts.find((conflict) => {
    // Check by event IDs
    if (conflict.event1_id === execution.pattern_id) return true
    if (conflict.event2_id === execution.pattern_id) return true

    // Check by time overlap
    if (conflict.start_time && execution.start_time) {
      const conflictTime = conflict.start_time
      const execTime = execution.start_time
      // Exact time match indicates this execution is part of the conflict
      if (conflictTime === execTime) return true
    }

    return false
  })

  return match || null
}

/**
 * Generates a unique key for an execution chip.
 *
 * Uses execution.id if available, otherwise falls back to pattern_id + time + index.
 * The index parameter prevents key collisions when multiple executions share
 * the same pattern_id and start_time.
 *
 * @param execution - Execution object
 * @param index - Array index for uniqueness fallback
 * @returns Unique key for React rendering
 */
export function getExecutionKey(execution: Execution, index: number = 0): string {
  const patternId = execution.pattern_id || 'unknown'
  const time = execution.start_time || ''
  const uniqueId = execution.id || index
  return `${patternId}-${time}-${uniqueId}`
}

/**
 * Formats execution for data-testid attribute.
 * Format: execution-{routine_id}-{time}
 *
 * @param execution - Execution object
 * @returns data-testid value
 */
export function getExecutionTestId(execution: Execution): string {
  const routineId = execution.pattern_id || 'unknown'
  const time = formatTimeShort(execution.start_time).replace(':', '')
  return `execution-${routineId}-${time}`
}

// =============================================================================
// Cycle-Aware Functions (for overnight schedules)
// =============================================================================

/**
 * Generates an array of hours based on cycle info.
 *
 * For overnight schedules (spans_midnight=true), returns hours in cycle order:
 * e.g., [17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6]
 *
 * For daytime schedules (spans_midnight=false), returns hours in normal order:
 * e.g., [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
 *
 * If no cycleInfo provided, returns all 24 hours [0, 1, ..., 23].
 *
 * @param cycleInfo - Cycle info from preview API
 * @returns Array of hours in cycle order
 */
export function getCycleHours(cycleInfo: CycleInfo | null | undefined): number[] {
  // Default to all 24 hours if no cycle info or missing required properties
  if (!cycleInfo || cycleInfo.start_hour === undefined || cycleInfo.end_hour === undefined) {
    return Array.from({ length: 24 }, (_, i) => i)
  }

  const { start_hour, end_hour, spans_midnight } = cycleInfo
  const hours: number[] = []

  if (spans_midnight) {
    // Overnight: start_hour -> 23, then 0 -> end_hour
    for (let h = start_hour; h <= 23; h++) {
      hours.push(h)
    }
    for (let h = 0; h <= end_hour; h++) {
      hours.push(h)
    }
  } else {
    // Daytime: start_hour -> end_hour
    for (let h = start_hour; h <= end_hour; h++) {
      hours.push(h)
    }
  }

  return hours
}

/**
 * Groups executions by hour, taking only the first occurrence of each time.
 *
 * For overnight schedules spanning 2 days, this filters to show only
 * one cycle's worth of executions (avoiding duplicates from day 2's
 * evening hours that would start another cycle).
 *
 * @param executions - Array of execution objects with start_time
 * @returns Map of hour (0-23) -> array of executions
 */
export function groupExecutionsByHourCycleAware(executions: Execution[]): ExecutionsByHour {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  // Sort executions by time to get chronological order
  const sorted = [...executions].sort((a, b) => {
    return new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  })

  // Track which time strings we've seen to dedupe
  const seenTimes = new Set<string>()
  const grouped: ExecutionsByHour = {}

  sorted.forEach((execution) => {
    if (!execution.start_time) return

    // Create a time key (HH:MM) to dedupe executions at same time
    const timeKey = formatTimeShort(execution.start_time)
    const hour = getHourFromIsoTime(execution.start_time)
    if (hour === null) return

    // Skip if we've already seen an execution at this exact time
    // This filters out the "second cycle" executions from day 2
    const dedupeKey = `${hour}-${timeKey}-${execution.pattern_id}`
    if (seenTimes.has(dedupeKey)) return
    seenTimes.add(dedupeKey)

    if (!grouped[hour]) {
      grouped[hour] = []
    }

    grouped[hour].push(execution)
  })

  return grouped
}

/**
 * Gets a "pattern fingerprint" for an hour's executions.
 *
 * Used to compare hours for collapse logic - two hours are "identical"
 * if they have the same number of executions and the same routine types.
 *
 * @param executions - Array of executions for an hour
 * @returns Fingerprint string for comparison
 */
function getHourFingerprint(executions: Execution[] | undefined): string {
  if (!executions || executions.length === 0) {
    return 'empty'
  }

  // Count executions per pattern
  const patternCounts: PatternCounts = {}
  executions.forEach((exec) => {
    const patternId = exec.pattern_id || 'unknown'
    patternCounts[patternId] = (patternCounts[patternId] || 0) + 1
  })

  // Create sorted fingerprint
  const sorted = Object.entries(patternCounts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([id, count]) => `${id}:${count}`)
    .join(',')

  return sorted
}

/**
 * Collapses consecutive hours with identical execution patterns.
 *
 * When more than 3 consecutive hours have the same pattern (same number
 * of executions from the same routines), collapses them into a single
 * "continues" indicator.
 *
 * @param hours - Array of hours in cycle order
 * @param executionsByHour - Map of hour -> executions
 * @returns Array of {type: 'hour', hour} or {type: 'collapsed', count}
 */
export function collapseRepetitiveHours(hours: number[], executionsByHour: ExecutionsByHour): DisplayHour[] {
  if (!hours || hours.length === 0) {
    return []
  }

  const result: DisplayHour[] = []
  let i = 0

  while (i < hours.length) {
    const hour = hours[i]
    const fingerprint = getHourFingerprint(executionsByHour[hour])

    // Count consecutive hours with same fingerprint
    let runLength = 1
    while (
      i + runLength < hours.length &&
      getHourFingerprint(executionsByHour[hours[i + runLength]]) === fingerprint
    ) {
      runLength++
    }

    // If more than 3 consecutive identical hours, collapse the middle
    if (runLength > 3) {
      // Show first 2 hours
      result.push({ type: 'hour', hour: hours[i] })
      result.push({ type: 'hour', hour: hours[i + 1] })

      // Collapsed indicator for middle hours
      result.push({ type: 'collapsed', count: runLength - 3 })

      // Show last hour
      result.push({ type: 'hour', hour: hours[i + runLength - 1] })

      i += runLength
    } else {
      // Show all hours normally
      for (let j = 0; j < runLength; j++) {
        result.push({ type: 'hour', hour: hours[i + j] })
      }
      i += runLength
    }
  }

  return result
}
