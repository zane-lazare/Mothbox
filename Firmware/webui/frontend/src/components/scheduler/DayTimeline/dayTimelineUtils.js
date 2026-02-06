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

/**
 * Logs a warning in development mode for invalid time strings.
 * @param {string} isoString - The invalid ISO string
 * @param {string} context - Function name for context
 */
function warnInvalidTime(isoString, context) {
  if (import.meta.env.DEV) {
    console.warn(`[${context}] Invalid ISO time string:`, isoString)
  }
}

/**
 * Extracts the hour (0-23) from an ISO datetime string in local timezone.
 *
 * @param {string} isoString - ISO datetime string (e.g., "2025-12-17T18:30:00Z")
 * @returns {number|null} Hour number (0-23) in local timezone, or null if invalid
 */
export function getHourFromIsoTime(isoString) {
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
 * @param {string} isoString - ISO datetime string
 * @returns {number|null} Minute number (0-59) in local timezone, or null if invalid
 */
export function getMinuteFromIsoTime(isoString) {
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
 * @param {number} hour - Hour number (0-23)
 * @returns {string} Formatted time string
 */
export function formatHourLabel(hour) {
  if (typeof hour !== 'number' || hour < 0 || hour > 23) {
    return ''
  }
  return `${hour}:00`
}

/**
 * Formats an ISO datetime string to a short time string in local timezone (e.g., "18:30").
 *
 * @param {string} isoString - ISO datetime string
 * @returns {string} Formatted time string (HH:MM) in local timezone
 */
export function formatTimeShort(isoString) {
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
 * @param {string} isoString - ISO datetime string
 * @returns {string|null} Local date in YYYY-MM-DD format, or null if invalid
 */
export function getLocalDateFromIso(isoString) {
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
 * @param {string} dateStr - Date string in YYYY-MM-DD format
 * @returns {string} Next date in YYYY-MM-DD format
 */
export function getNextDateKey(dateStr) {
  const d = new Date(dateStr + 'T12:00:00') // noon avoids DST edge cases
  d.setDate(d.getDate() + 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/**
 * Groups executions by hour (0-23) for a given local date.
 *
 * @param {Array} executions - Array of execution objects with start_time
 * @param {string} date - Local date string (YYYY-MM-DD) to filter by
 * @returns {Object} Map of hour (0-23) -> array of executions
 */
export function groupExecutionsByHour(executions, date) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  const grouped = {}

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
 * @param {Array} conflicts - Array of conflict objects with start_time/end_time
 * @param {number} hour - Hour to check (0-23) in local timezone
 * @param {string} date - Local date string (YYYY-MM-DD)
 * @returns {Object|null} Most severe conflict for this hour, or null
 */
export function getConflictForHour(conflicts, hour, date) {
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
 * @param {string} actionType - Action type ('camera', 'gpio', 'gps_sync', 'service')
 * @param {string} actionName - Action name (used to detect HDR)
 * @returns {Object} { bg, text, darkBg, darkText } Tailwind classes
 */
export function getActionTypeDisplay(actionType, actionName) {
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
 * @param {Array} conflicts - Array of conflict objects
 * @returns {Object} { total, errors, warnings }
 */
export function countConflictsBySeverity(conflicts) {
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
 * @param {Object} execution - Execution object with pattern_id
 * @param {Array} conflicts - Array of conflict objects
 * @returns {Object|null} Conflict affecting this execution, or null
 */
export function getConflictForExecution(execution, conflicts) {
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
 * @param {Object} execution - Execution object
 * @param {number} [index=0] - Array index for uniqueness fallback
 * @returns {string} Unique key for React rendering
 */
export function getExecutionKey(execution, index = 0) {
  const patternId = execution.pattern_id || 'unknown'
  const time = execution.start_time || ''
  const uniqueId = execution.id || index
  return `${patternId}-${time}-${uniqueId}`
}

/**
 * Formats execution for data-testid attribute.
 * Format: execution-{routine_id}-{time}
 *
 * @param {Object} execution - Execution object
 * @returns {string} data-testid value
 */
export function getExecutionTestId(execution) {
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
 * @param {Object|null} cycleInfo - Cycle info from preview API
 * @param {number} cycleInfo.start_hour - Hour when cycle begins (0-23)
 * @param {number} cycleInfo.end_hour - Hour when cycle ends (0-23)
 * @param {boolean} cycleInfo.spans_midnight - True if cycle crosses midnight
 * @returns {Array<number>} Array of hours in cycle order
 */
export function getCycleHours(cycleInfo) {
  // Default to all 24 hours if no cycle info
  if (!cycleInfo) {
    return Array.from({ length: 24 }, (_, i) => i)
  }

  const { start_hour, end_hour, spans_midnight } = cycleInfo
  const hours = []

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
 * @param {Array} executions - Array of execution objects with start_time
 * @returns {Object} Map of hour (0-23) -> array of executions
 */
export function groupExecutionsByHourCycleAware(executions) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  // Sort executions by time to get chronological order
  const sorted = [...executions].sort((a, b) => {
    return new Date(a.start_time) - new Date(b.start_time)
  })

  // Track which time strings we've seen to dedupe
  const seenTimes = new Set()
  const grouped = {}

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
 * @param {Array} executions - Array of executions for an hour
 * @returns {string} Fingerprint string for comparison
 */
function getHourFingerprint(executions) {
  if (!executions || executions.length === 0) {
    return 'empty'
  }

  // Count executions per pattern
  const patternCounts = {}
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
 * @param {Array<number>} hours - Array of hours in cycle order
 * @param {Object} executionsByHour - Map of hour -> executions
 * @returns {Array} Array of {type: 'hour', hour} or {type: 'collapsed', count}
 */
export function collapseRepetitiveHours(hours, executionsByHour) {
  if (!hours || hours.length === 0) {
    return []
  }

  const result = []
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
