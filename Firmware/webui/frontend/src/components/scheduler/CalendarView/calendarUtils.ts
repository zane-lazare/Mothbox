/**
 * Calendar View Utilities
 *
 * Provides utility functions for calendar date calculations, formatting,
 * and execution grouping for the Mothbox Scheduler Calendar View.
 */

import type { Execution } from '../DayTimeline/dayTimelineUtils'

// =============================================================================
// Types
// =============================================================================

/**
 * Re-export Execution type from dayTimelineUtils for calendar visualization
 */
export type { Execution }

/**
 * Grouped executions by date key (YYYY-MM-DD).
 * Used by calendar views to display executions on specific days.
 */
export interface GroupedExecutions {
  [dateKey: string]: Execution[]
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Array of Tailwind color classes for pattern visualization
 */
export const PATTERN_COLORS: readonly string[] = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-cyan-500',
] as const

// =============================================================================
// Date Grid Functions
// =============================================================================

/**
 * Gets an array of 42 dates for a month grid (6 weeks)
 * Starts on Sunday and includes overflow days from previous/next months
 *
 * @param year - Full year (e.g., 2025)
 * @param month - Month (0-indexed, 0 = January, 11 = December)
 * @returns Array of 42 Date objects
 */
export function getMonthGridDates(year: number, month: number): Date[] {
  const dates: Date[] = []

  // Get the first day of the month
  const firstDayOfMonth = new Date(year, month, 1)
  const firstDayOfWeek = firstDayOfMonth.getDay() // 0 = Sunday, 6 = Saturday

  // Calculate the starting date (Sunday of the first week)
  const startDate = new Date(firstDayOfMonth)
  startDate.setDate(1 - firstDayOfWeek)

  // Generate 42 dates (6 weeks)
  for (let i = 0; i < 42; i++) {
    const date = new Date(startDate)
    date.setDate(startDate.getDate() + i)
    dates.push(date)
  }

  return dates
}

/**
 * Gets an array of 7 dates for the week containing the given date
 * Week starts on Sunday
 *
 * @param centerDate - Any date within the target week
 * @returns Array of 7 Date objects (Sunday to Saturday)
 */
export function getWeekDates(centerDate: Date): Date[] {
  const dates: Date[] = []
  const dayOfWeek = centerDate.getDay() // 0 = Sunday, 6 = Saturday

  // Calculate Sunday of this week
  const sunday = new Date(centerDate)
  sunday.setDate(centerDate.getDate() - dayOfWeek)

  // Generate 7 dates
  for (let i = 0; i < 7; i++) {
    const date = new Date(sunday)
    date.setDate(sunday.getDate() + i)
    dates.push(date)
  }

  return dates
}

/**
 * Gets an array of hour markers for day view (0-23)
 *
 * @returns Array of hours [0, 1, 2, ..., 23]
 */
export function getDayHours(): number[] {
  return Array.from({ length: 24 }, (_, i) => i)
}

// =============================================================================
// Execution Grouping
// =============================================================================

/**
 * Groups execution objects by local date (YYYY-MM-DD)
 * Converts ISO UTC time to local date before grouping
 *
 * @param executions - Array of execution objects with scheduled_time or start_time field
 * @returns Object keyed by local date (YYYY-MM-DD), values are arrays of executions
 */
export function groupExecutionsByDate(executions: Execution[] | null | undefined): GroupedExecutions {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  const grouped: GroupedExecutions = {}

  executions.forEach(execution => {
    // Support both scheduled_time (new API) and start_time (legacy API)
    const timeString = execution.scheduled_time || execution.start_time
    if (!timeString) return

    // Convert ISO string to Date and extract local date
    // This ensures executions appear on the correct calendar day for the user's timezone
    const date = new Date(timeString)
    if (isNaN(date.getTime())) return

    const isoDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

    if (!grouped[isoDate]) {
      grouped[isoDate] = []
    }

    grouped[isoDate].push(execution)
  })

  return grouped
}

// =============================================================================
// Date Formatting
// =============================================================================

/**
 * View mode for date range formatting
 */
export type ViewMode = 'month' | 'week' | 'day'

/**
 * Formats date range display based on view mode
 *
 * @param viewMode - 'month', 'week', or 'day'
 * @param currentDate - The current date being displayed
 * @param patternOffset - Pattern offset for week view pattern mode (0, 7, 14, etc.)
 *                        When provided, returns "Days X-Y" format
 * @returns Formatted date range string
 */
export function formatDateRange(viewMode: ViewMode, currentDate: Date, patternOffset: number | null = null): string {
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ]

  const shortMonthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ]

  if (viewMode === 'month') {
    const month = monthNames[currentDate.getMonth()]
    const year = currentDate.getFullYear()
    return `${month} ${year}`
  }

  if (viewMode === 'week') {
    // Pattern mode: "Days 1-7", "Days 8-14", etc.
    if (patternOffset !== null) {
      const startDay = patternOffset + 1
      const endDay = patternOffset + 7
      return `Days ${startDay}-${endDay}`
    }

    // Calendar mode: "Dec 14-20, 2025"
    const weekDates = getWeekDates(currentDate)
    const startDate = weekDates[0]
    const endDate = weekDates[6]

    const startMonth = shortMonthNames[startDate.getMonth()]
    const endMonth = shortMonthNames[endDate.getMonth()]
    const startDay = startDate.getDate()
    const endDay = endDate.getDate()
    const year = endDate.getFullYear()

    if (startDate.getMonth() === endDate.getMonth()) {
      // Same month: "Dec 14-20, 2025"
      return `${startMonth} ${startDay}-${endDay}, ${year}`
    } else {
      // Different months: "Dec 28 - Jan 3, 2025"
      return `${startMonth} ${startDay} - ${endMonth} ${endDay}, ${year}`
    }
  }

  if (viewMode === 'day') {
    const month = monthNames[currentDate.getMonth()]
    const day = currentDate.getDate()
    const year = currentDate.getFullYear()
    return `${month} ${day}, ${year}`
  }

  return ''
}

// =============================================================================
// Color Utilities
// =============================================================================

/**
 * Gets a consistent color for a pattern ID using hash-based selection
 *
 * @param patternId - The pattern identifier
 * @returns Tailwind color class
 */
export function getPatternColor(patternId: string | null | undefined): string {
  if (!patternId) {
    return PATTERN_COLORS[0]
  }

  // Simple hash function for consistent color selection
  let hash = 0
  for (let i = 0; i < patternId.length; i++) {
    hash = ((hash << 5) - hash) + patternId.charCodeAt(i)
    hash = hash >>> 0 // Convert to 32-bit unsigned integer
  }

  // Map hash to color index
  const index = Math.abs(hash) % PATTERN_COLORS.length
  return PATTERN_COLORS[index]
}

// =============================================================================
// Date Comparison
// =============================================================================

/**
 * Checks if a date is today (ignoring time component)
 *
 * @param date - The date to check
 * @returns True if date is today
 */
export function isToday(date: Date): boolean {
  const today = new Date()
  return isSameDay(date, today)
}

/**
 * Checks if two dates are the same day (ignoring time component)
 *
 * @param date1 - First date
 * @param date2 - Second date
 * @returns True if both dates are the same day
 */
export function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

// =============================================================================
// Time Formatting
// =============================================================================

/**
 * Formats ISO datetime string to time string (HH:MM format)
 * Always displays in user's local timezone for consistent display.
 *
 * @param isoString - ISO datetime string (e.g., "2025-12-17T08:30:00Z")
 * @returns Formatted time string in local timezone (e.g., "8:30")
 */
export function formatTime(isoString: string | null | undefined): string {
  if (!isoString || typeof isoString !== 'string') {
    return ''
  }

  const date = new Date(isoString)
  if (isNaN(date.getTime())) {
    if (import.meta.env.DEV) {
      console.warn('Invalid ISO string passed to formatTime:', isoString)
    }
    return ''
  }

  // Always display in user's local timezone for consistent behavior
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const formattedMinutes = minutes.toString().padStart(2, '0')
  return `${hours}:${formattedMinutes}`
}

/**
 * Get ISO date key (YYYY-MM-DD) from a Date object or ISO string
 *
 * @param date - Date object or ISO date string
 * @returns Date key in YYYY-MM-DD format, or null if invalid
 */
export function getDateKey(date: Date | string | null | undefined): string | null {
  if (typeof date === 'string') {
    // Validate ISO date format (YYYY-MM-DD at start of string)
    const isoDateMatch = date.match(/^(\d{4}-\d{2}-\d{2})/)
    if (!isoDateMatch) {
      if (import.meta.env.DEV) {
        console.warn('Invalid ISO string passed to getDateKey:', date)
      }
      return null
    }
    return isoDateMatch[1]
  }
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) {
    if (import.meta.env.DEV) {
      console.warn('Invalid Date passed to getDateKey:', date)
    }
    return null
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
