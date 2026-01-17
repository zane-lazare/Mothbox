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
 * For overnight schedules (where start_hour > end_hour), post-midnight executions
 * are grouped with the previous day to show complete cycles per day column.
 *
 * @param {Array} executions - Array of execution objects with start_time
 * @param {Date[]} weekDates - Array of 7 Date objects for the week
 * @param {Object} [cycleInfo] - Cycle info with start_hour, end_hour for overnight handling
 * @returns {Object} Nested map of date -> hour -> executions
 *
 * @example
 * const grouped = groupExecutionsByDayAndHour(executions, weekDates, cycleInfo)
 * // grouped['2025-01-15'][18] = [{ pattern_id: '...', ... }]
 */
export function groupExecutionsByDayAndHour(executions, weekDates, cycleInfo = null) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  // Determine if this is an overnight schedule
  // cycleInfo hours are in UTC, but we display in local time
  // Convert UTC hours to local hours to check if it spans midnight locally
  let isOvernight = false
  let localEndHour = null

  if (cycleInfo && typeof cycleInfo.start_hour === 'number' && typeof cycleInfo.end_hour === 'number') {
    // Get timezone offset in hours (e.g., NZDT is +13)
    const tzOffsetHours = -new Date().getTimezoneOffset() / 60

    // Convert UTC hours to local hours
    const localStartHour = (cycleInfo.start_hour + tzOffsetHours + 24) % 24
    localEndHour = (cycleInfo.end_hour + tzOffsetHours + 24) % 24

    // Overnight if local start > local end (e.g., 21:00 start, 05:00 end)
    isOvernight = localStartHour > localEndHour
  }

  // Create set of valid date keys from weekDates
  const validDateKeys = new Set(weekDates.map(d => getLocalDateKey(d)))

  // Also track date key to index mapping for previous day lookup
  const dateKeyList = weekDates.map(d => getLocalDateKey(d))

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

    let dateKey = getDateKeyFromIso(execution.start_time)
    if (!dateKey) return

    const hour = getHourFromIso(execution.start_time)
    if (hour === null) return

    // For overnight schedules, shift post-midnight hours to previous day
    // This keeps complete cycles (dusk-to-dawn) in the same day column
    if (isOvernight && hour < localEndHour) {
      const dateIndex = dateKeyList.indexOf(dateKey)
      if (dateIndex > 0) {
        // Shift to previous day
        dateKey = dateKeyList[dateIndex - 1]
      } else if (dateIndex === 0) {
        // First day - skip post-midnight executions (they belong to previous week)
        return
      }
    }

    if (!validDateKeys.has(dateKey)) return

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
 * In pattern mode (when patternOffset is provided), returns pattern-based labels
 * like "Day 1", "Day 2", etc. In calendar mode, returns weekday names like "Sun", "Mon".
 *
 * @param {Date} date - Date to format
 * @param {number|null} [dayIndex=null] - Day index within the week (0-6), required for pattern mode
 * @param {number|null} [patternOffset=null] - Pattern offset (0, 7, 14, etc.) for pattern mode
 * @returns {Object} { dayName, dayNumber, isToday }
 */
export function formatWeekDayHeader(date, dayIndex = null, patternOffset = null) {
  // Pattern mode: "Day 1", "Day 2", etc.
  if (patternOffset !== null && dayIndex !== null) {
    const patternDay = patternOffset + dayIndex + 1
    return {
      dayName: `Day ${patternDay}`,
      dayNumber: patternDay,
      isToday: false, // No "today" concept in pattern view
    }
  }

  // Calendar mode: "Sun", "Mon", etc.
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
