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
 */

import {
  ACTION_TYPE_COLORS,
  DEFAULT_ACTION_COLORS,
  isHdrAction,
} from './dayTimelineConstants'

/**
 * Extracts the hour (0-23) from an ISO datetime string.
 * Uses regex extraction from ISO format for consistency.
 * Note: All times are treated as UTC to avoid timezone inconsistencies.
 *
 * @param {string} isoString - ISO datetime string (e.g., "2025-12-17T18:30:00")
 * @returns {number|null} Hour number (0-23), or null if invalid
 */
export function getHourFromIsoTime(isoString) {
  if (!isoString || typeof isoString !== 'string') {
    return null
  }

  // Extract time directly from ISO string format (HH:MM:SS)
  // This avoids timezone conversion issues
  const timeMatch = isoString.match(/T(\d{2}):(\d{2})/)
  if (timeMatch) {
    return parseInt(timeMatch[1], 10)
  }

  // Fallback to Date parsing for non-standard formats
  // Use UTC to match the behavior of regex extraction
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    return null
  }

  return date.getUTCHours()
}

/**
 * Extracts the minute (0-59) from an ISO datetime string.
 * Note: All times are treated as UTC to avoid timezone inconsistencies.
 *
 * @param {string} isoString - ISO datetime string
 * @returns {number|null} Minute number (0-59), or null if invalid
 */
export function getMinuteFromIsoTime(isoString) {
  if (!isoString || typeof isoString !== 'string') {
    return null
  }

  // Extract time directly from ISO string format (HH:MM:SS)
  const timeMatch = isoString.match(/T(\d{2}):(\d{2})/)
  if (timeMatch) {
    return parseInt(timeMatch[2], 10)
  }

  // Fallback to Date parsing for non-standard formats
  // Use UTC to match the behavior of regex extraction
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    return null
  }

  return date.getUTCMinutes()
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
 * Formats an ISO datetime string to a short time string (e.g., "18:30").
 *
 * @param {string} isoString - ISO datetime string
 * @returns {string} Formatted time string (HH:MM)
 */
export function formatTimeShort(isoString) {
  if (!isoString || typeof isoString !== 'string') {
    return ''
  }

  // Extract time directly from ISO string format to avoid timezone issues
  const timeMatch = isoString.match(/T(\d{2}):(\d{2})/)
  if (timeMatch) {
    const hours = parseInt(timeMatch[1], 10)
    const minutes = timeMatch[2]
    return `${hours}:${minutes}`
  }

  // Fallback to Date parsing for non-standard formats
  // Use UTC to match the behavior of regex extraction
  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    return ''
  }

  const hours = date.getUTCHours()
  const minutes = date.getUTCMinutes()
  return `${hours}:${minutes.toString().padStart(2, '0')}`
}

/**
 * Groups executions by hour (0-23) for a given date.
 *
 * @param {Array} executions - Array of execution objects with start_time
 * @param {string} date - ISO date string (YYYY-MM-DD) to filter by
 * @returns {Object} Map of hour (0-23) -> array of executions
 */
export function groupExecutionsByHour(executions, date) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  const grouped = {}

  executions.forEach((execution) => {
    if (!execution.start_time) return

    // Check if execution is on the target date
    const executionDate = execution.start_time.split('T')[0]
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
 * @param {number} hour - Hour to check (0-23)
 * @param {string} date - ISO date string (YYYY-MM-DD)
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

    // Check if conflict is on the target date
    const conflictDate = conflict.start_time.split('T')[0]
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
 * @param {Object} execution - Execution object
 * @returns {string} Unique key for React rendering
 */
export function getExecutionKey(execution) {
  const patternId = execution.pattern_id || 'unknown'
  const time = execution.start_time || ''
  return `${patternId}-${time}`
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
