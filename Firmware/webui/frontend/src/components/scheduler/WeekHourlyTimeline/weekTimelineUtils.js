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

// Re-export shared cycle utilities
export { groupExecutionsByCycleDay } from '../utils/cycleGroupingUtils'

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
  // cycleInfo hours are already in local time (backend converts based on tz param)
  let isOvernight = false
  let endHour = null

  if (cycleInfo && typeof cycleInfo.start_hour === 'number' && typeof cycleInfo.end_hour === 'number') {
    // Hours are already in local time from the API
    endHour = cycleInfo.end_hour

    // Overnight if start > end (e.g., 21:00 start, 05:00 end)
    isOvernight = cycleInfo.start_hour > cycleInfo.end_hour
  }

  // Create set of valid date keys from weekDates
  const validDateKeys = new Set(weekDates.map(d => getLocalDateKey(d)))

  // Also track date key to index mapping for previous day lookup
  const dateKeyList = weekDates.map(d => getLocalDateKey(d))
  const dateKeyIndex = new Map(dateKeyList.map((key, idx) => [key, idx]))

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
    if (isOvernight && hour < endHour) {
      const dateIndex = dateKeyIndex.get(dateKey)
      if (dateIndex === undefined) return
      if (dateIndex > 0) {
        dateKey = dateKeyList[dateIndex - 1]
      } else {
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
 * Creates a map of pattern_id to conflict for all executions.
 *
 * @param {Array} executions - Array of execution objects
 * @param {Array} conflicts - Array of conflict objects
 * @returns {Object} Map of pattern_id -> conflict
 */
export function buildExecutionConflictsMap(executions, conflicts) {
  if (!executions || !conflicts) return {}

  // Pre-index conflicts for O(1) lookup instead of O(m) find per execution
  const byEvent1 = new Map()
  const byEvent2 = new Map()
  const byStartTime = new Map()
  conflicts.forEach(c => {
    if (c.event1_id && !byEvent1.has(c.event1_id)) byEvent1.set(c.event1_id, c)
    if (c.event2_id && !byEvent2.has(c.event2_id)) byEvent2.set(c.event2_id, c)
    if (c.start_time && !byStartTime.has(c.start_time)) byStartTime.set(c.start_time, c)
  })

  const map = {}
  executions.forEach(execution => {
    const conflict =
      byEvent1.get(execution.pattern_id) ||
      byEvent2.get(execution.pattern_id) ||
      byStartTime.get(execution.start_time)
    if (conflict) {
      map[execution.pattern_id] = conflict
    }
  })
  return map
}

