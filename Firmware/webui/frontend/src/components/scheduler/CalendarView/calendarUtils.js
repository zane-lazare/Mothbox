/**
 * Calendar View Utilities
 *
 * Provides utility functions for calendar date calculations, formatting,
 * and execution grouping for the Mothbox Scheduler Calendar View.
 */

/**
 * Array of Tailwind color classes for pattern visualization
 */
export const PATTERN_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-cyan-500',
]

/**
 * Gets an array of 42 dates for a month grid (6 weeks)
 * Starts on Sunday and includes overflow days from previous/next months
 *
 * @param {number} year - Full year (e.g., 2025)
 * @param {number} month - Month (0-indexed, 0 = January, 11 = December)
 * @returns {Date[]} Array of 42 Date objects
 */
export function getMonthGridDates(year, month) {
  const dates = []

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
 * @param {Date} centerDate - Any date within the target week
 * @returns {Date[]} Array of 7 Date objects (Sunday to Saturday)
 */
export function getWeekDates(centerDate) {
  const dates = []
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
 * @returns {number[]} Array of hours [0, 1, 2, ..., 23]
 */
export function getDayHours() {
  return Array.from({ length: 24 }, (_, i) => i)
}

/**
 * Groups execution objects by ISO date (YYYY-MM-DD)
 * Extracts date from start_time field
 *
 * @param {Array} executions - Array of execution objects with start_time field
 * @returns {Object} Object keyed by ISO date (YYYY-MM-DD), values are arrays of executions
 */
export function groupExecutionsByDate(executions) {
  if (!executions || !Array.isArray(executions)) {
    return {}
  }

  const grouped = {}

  executions.forEach(execution => {
    if (!execution.start_time) return

    // Extract YYYY-MM-DD from ISO datetime string
    const isoDate = execution.start_time.split('T')[0]

    if (!grouped[isoDate]) {
      grouped[isoDate] = []
    }

    grouped[isoDate].push(execution)
  })

  return grouped
}

/**
 * Formats date range display based on view mode
 *
 * @param {string} viewMode - 'month', 'week', or 'day'
 * @param {Date} currentDate - The current date being displayed
 * @returns {string} Formatted date range string
 */
export function formatDateRange(viewMode, currentDate) {
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

/**
 * Gets a consistent color for a pattern ID using hash-based selection
 *
 * @param {string} patternId - The pattern identifier
 * @returns {string} Tailwind color class
 */
export function getPatternColor(patternId) {
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

/**
 * Checks if a date is today (ignoring time component)
 *
 * @param {Date} date - The date to check
 * @returns {boolean} True if date is today
 */
export function isToday(date) {
  const today = new Date()
  return isSameDay(date, today)
}

/**
 * Checks if two dates are the same day (ignoring time component)
 *
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @returns {boolean} True if both dates are the same day
 */
export function isSameDay(date1, date2) {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

/**
 * Formats ISO datetime string to time string (HH:MM format)
 *
 * @param {string} isoString - ISO datetime string (e.g., "2025-12-17T08:30:00Z")
 * @returns {string} Formatted time string (e.g., "8:30")
 */
export function formatTime(isoString) {
  const date = new Date(isoString)

  // Use UTC hours and minutes if the string contains 'Z' (UTC indicator)
  const hours = isoString.includes('Z') ? date.getUTCHours() : date.getHours()
  const minutes = isoString.includes('Z') ? date.getUTCMinutes() : date.getMinutes()

  // Format as H:MM or HH:MM (no leading zero for single-digit hours)
  const formattedMinutes = minutes.toString().padStart(2, '0')
  return `${hours}:${formattedMinutes}`
}

/**
 * Get ISO date key (YYYY-MM-DD) from a Date object or ISO string
 *
 * @param {Date|string} date - Date object or ISO date string
 * @returns {string|null} Date key in YYYY-MM-DD format, or null if invalid
 */
export function getDateKey(date) {
  if (typeof date === 'string') {
    // Handle ISO string input - extract date portion
    return date.split('T')[0]
  }
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) {
    console.warn('Invalid Date passed to getDateKey:', date)
    return null
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
