/**
 * WeekHourlyTimeline utility functions
 *
 * Provides utility functions for the week hourly timeline:
 * - Grouping executions by day and hour
 * - Filtering conflicts by day
 * - Week date calculations
 *
 * @module components/scheduler/WeekHourlyTimeline/weekTimelineUtils
 */

// Re-export shared utilities from DayTimeline
export {
  getCycleHours,
  formatTimeShort,
  formatHourLabel,
  getConflictForExecution,
  getConflictForHour,
  getHourFromIsoTime,
  getExecutionKey,
  collapseRepetitiveHours,
} from '../DayTimeline/dayTimelineUtils'

// Re-export from calendarUtils
export { getWeekDates, isToday, getDateKey } from '../CalendarView/calendarUtils'

/**
 * Gets a date key (YYYY-MM-DD) from a Date object in local timezone.
 *
 * @param {Date} date - Date object
 * @returns {string} Date key in YYYY-MM-DD format
 */
function getLocalDateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Gets a date key from an ISO datetime string in local timezone.
 *
 * @param {string} isoString - ISO datetime string
 * @returns {string|null} Date key in YYYY-MM-DD format, or null if invalid
 */
function getDateKeyFromIso(isoString) {
  if (!isoString || typeof isoString !== 'string') return null
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return null
  return getLocalDateKey(date)
}

/**
 * Gets the hour (0-23) from an ISO datetime string in local timezone.
 *
 * @param {string} isoString - ISO datetime string
 * @returns {number|null} Hour number or null if invalid
 */
function getHourFromIso(isoString) {
  if (!isoString || typeof isoString !== 'string') return null
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return null
  return date.getHours()
}

/**
 * Groups executions by day (date key) and hour.
 *
 * Returns a nested structure: { 'YYYY-MM-DD': { hour: [executions] } }
 *
 * @param {Array} executions - Array of execution objects with start_time
 * @param {Date[]} weekDates - Array of 7 Date objects for the week
 * @returns {Object} Nested map of date -> hour -> executions
 *
 * @example
 * const grouped = groupExecutionsByDayAndHour(executions, weekDates)
 * // grouped['2025-01-15'][18] = [{ pattern_id: '...', ... }]
 */
export function groupExecutionsByDayAndHour(executions, weekDates) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  // Create set of valid date keys from weekDates
  const validDateKeys = new Set(weekDates.map(d => getLocalDateKey(d)))

  // Initialize empty structure for all dates
  const grouped = {}
  weekDates.forEach(date => {
    grouped[getLocalDateKey(date)] = {}
  })

  // Track seen executions to deduplicate (same pattern at same time)
  const seenKeys = new Set()

  // Sort chronologically first
  const sorted = [...executions].sort((a, b) =>
    new Date(a.start_time) - new Date(b.start_time)
  )

  sorted.forEach(execution => {
    if (!execution.start_time) return

    const dateKey = getDateKeyFromIso(execution.start_time)
    if (!dateKey || !validDateKeys.has(dateKey)) return

    const hour = getHourFromIso(execution.start_time)
    if (hour === null) return

    // Dedupe key: date + hour + pattern_id + formatted time
    const timeStr = new Date(execution.start_time).toTimeString().slice(0, 5)
    const dedupeKey = `${dateKey}-${hour}-${execution.pattern_id}-${timeStr}`
    if (seenKeys.has(dedupeKey)) return
    seenKeys.add(dedupeKey)

    if (!grouped[dateKey][hour]) {
      grouped[dateKey][hour] = []
    }
    grouped[dateKey][hour].push(execution)
  })

  return grouped
}

/**
 * Gets conflicts that affect a specific date.
 *
 * @param {Array} conflicts - Array of conflict objects with start_time
 * @param {string} dateKey - Date key in YYYY-MM-DD format
 * @returns {Array} Conflicts for that day
 */
export function getConflictsForDay(conflicts, dateKey) {
  if (!conflicts || !Array.isArray(conflicts) || !dateKey) {
    return []
  }

  return conflicts.filter(conflict => {
    if (!conflict.start_time) return false
    const conflictDateKey = getDateKeyFromIso(conflict.start_time)
    return conflictDateKey === dateKey
  })
}

/**
 * Counts conflicts for a specific date by severity.
 *
 * @param {Array} conflicts - Array of conflict objects
 * @param {string} dateKey - Date key in YYYY-MM-DD format
 * @returns {Object} { errors, warnings, total }
 */
export function countConflictsForDay(conflicts, dateKey) {
  const dayConflicts = getConflictsForDay(conflicts, dateKey)
  const errors = dayConflicts.filter(c => c.severity === 'error').length
  const warnings = dayConflicts.filter(c => c.severity === 'warning').length
  return { errors, warnings, total: dayConflicts.length }
}

/**
 * Gets the maximum number of executions in any single hour cell across the week.
 * Useful for determining if columns need to accommodate many items.
 *
 * @param {Object} executionsByDayAndHour - Nested map from groupExecutionsByDayAndHour
 * @returns {number} Maximum execution count in any hour cell
 */
export function getMaxExecutionsPerHour(executionsByDayAndHour) {
  let max = 0

  Object.values(executionsByDayAndHour).forEach(hourMap => {
    Object.values(hourMap).forEach(executions => {
      if (executions.length > max) {
        max = executions.length
      }
    })
  })

  return max
}

/**
 * Creates a map of pattern_id to conflict for all executions.
 *
 * @param {Array} executions - Array of execution objects
 * @param {Array} conflicts - Array of conflict objects
 * @returns {Object} Map of pattern_id -> conflict
 */
export function buildExecutionConflictsMap(executions, conflicts) {
  if (!executions || !conflicts) return {}

  const map = {}
  executions.forEach(execution => {
    const conflict = conflicts.find(c =>
      c.event1_id === execution.pattern_id ||
      c.event2_id === execution.pattern_id ||
      c.start_time === execution.start_time
    )
    if (conflict) {
      map[execution.pattern_id] = conflict
    }
  })
  return map
}

/**
 * Formats a date for the week header display.
 *
 * @param {Date} date - Date to format
 * @returns {Object} { dayName, dayNumber, isToday }
 */
export function formatWeekDayHeader(date) {
  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const today = new Date()
  const isTodayDate =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()

  return {
    dayName: DAYS[date.getDay()],
    dayNumber: date.getDate(),
    isToday: isTodayDate,
  }
}
