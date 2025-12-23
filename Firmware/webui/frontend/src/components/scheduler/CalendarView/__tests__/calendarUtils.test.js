import { describe, it, expect } from 'vitest'
import {
  getMonthGridDates,
  getWeekDates,
  getDayHours,
  groupExecutionsByDate,
  formatDateRange,
  getPatternColor,
  isToday,
  isSameDay,
  formatTime,
  getDateKey,
  PATTERN_COLORS,
} from '../calendarUtils'

describe('calendarUtils', () => {
  describe('getMonthGridDates', () => {
    it('returns 42 dates for a typical month', () => {
      // December 2025
      const dates = getMonthGridDates(2025, 11) // 0-indexed months
      expect(dates).toHaveLength(42)
    })

    it('starts on Sunday', () => {
      // December 2025 starts on Monday, so grid starts on Sunday Nov 30
      const dates = getMonthGridDates(2025, 11)
      expect(dates[0].getDay()).toBe(0) // Sunday
    })

    it('ends on Saturday', () => {
      const dates = getMonthGridDates(2025, 11)
      expect(dates[41].getDay()).toBe(6) // Saturday
    })

    it('includes previous month overflow days', () => {
      // December 2025 starts on Monday, so Sunday Nov 30 should be first
      const dates = getMonthGridDates(2025, 11)
      expect(dates[0].getMonth()).toBe(10) // November (0-indexed)
      expect(dates[0].getDate()).toBe(30)
    })

    it('includes next month overflow days', () => {
      // December 2025 ends on Wednesday, so we need Jan 1-10 to fill grid
      const dates = getMonthGridDates(2025, 11)
      const lastDate = dates[41]
      expect(lastDate.getMonth()).toBe(0) // January
      expect(lastDate.getFullYear()).toBe(2026)
    })

    it('handles February in leap year', () => {
      // 2024 is a leap year
      const dates = getMonthGridDates(2024, 1) // February
      expect(dates).toHaveLength(42)
      // February 2024 starts on Thursday, ends on Thursday 29th
      const feb29 = dates.find(d => d.getMonth() === 1 && d.getDate() === 29)
      expect(feb29).toBeDefined()
    })

    it('handles February in non-leap year', () => {
      // 2025 is not a leap year
      const dates = getMonthGridDates(2025, 1) // February
      expect(dates).toHaveLength(42)
      // No Feb 29 in 2025
      const feb29 = dates.find(d => d.getMonth() === 1 && d.getDate() === 29)
      expect(feb29).toBeUndefined()
    })

    it('returns Date objects', () => {
      const dates = getMonthGridDates(2025, 11)
      dates.forEach(date => {
        expect(date).toBeInstanceOf(Date)
      })
    })
  })

  describe('getWeekDates', () => {
    it('returns 7 dates', () => {
      const centerDate = new Date(2025, 11, 17) // Wednesday Dec 17, 2025
      const dates = getWeekDates(centerDate)
      expect(dates).toHaveLength(7)
    })

    it('starts on Sunday of the given week', () => {
      const centerDate = new Date(2025, 11, 17) // Wednesday Dec 17, 2025
      const dates = getWeekDates(centerDate)
      expect(dates[0].getDay()).toBe(0) // Sunday
      expect(dates[0].getDate()).toBe(14) // Dec 14
    })

    it('ends on Saturday of the given week', () => {
      const centerDate = new Date(2025, 11, 17)
      const dates = getWeekDates(centerDate)
      expect(dates[6].getDay()).toBe(6) // Saturday
      expect(dates[6].getDate()).toBe(20) // Dec 20
    })

    it('handles week crossing month boundary', () => {
      // Dec 31, 2025 is Wednesday
      const centerDate = new Date(2025, 11, 31)
      const dates = getWeekDates(centerDate)
      // Week should be Dec 28 (Sun) to Jan 3 (Sat)
      expect(dates[0].getMonth()).toBe(11) // December
      expect(dates[0].getDate()).toBe(28)
      expect(dates[6].getMonth()).toBe(0) // January 2026
      expect(dates[6].getDate()).toBe(3)
    })

    it('handles week crossing year boundary', () => {
      // Jan 1, 2026 is Thursday
      const centerDate = new Date(2026, 0, 1)
      const dates = getWeekDates(centerDate)
      // Week should include both Dec 2025 and Jan 2026
      expect(dates[0].getFullYear()).toBe(2025)
      expect(dates[6].getFullYear()).toBe(2026)
    })
  })

  describe('getDayHours', () => {
    it('returns 24 hour markers', () => {
      const hours = getDayHours()
      expect(hours).toHaveLength(24)
    })

    it('starts at 0 (midnight)', () => {
      const hours = getDayHours()
      expect(hours[0]).toBe(0)
    })

    it('ends at 23', () => {
      const hours = getDayHours()
      expect(hours[23]).toBe(23)
    })

    it('returns consecutive hours', () => {
      const hours = getDayHours()
      for (let i = 0; i < 24; i++) {
        expect(hours[i]).toBe(i)
      }
    })
  })

  describe('groupExecutionsByDate', () => {
    const mockExecutions = [
      { id: '1', start_time: '2025-12-17T08:00:00Z', pattern_name: 'Morning' },
      { id: '2', start_time: '2025-12-17T12:00:00Z', pattern_name: 'Noon' },
      { id: '3', start_time: '2025-12-18T08:00:00Z', pattern_name: 'Next Day' },
      { id: '4', start_time: '2025-12-17T20:00:00Z', pattern_name: 'Evening' },
    ]

    it('groups executions by ISO date', () => {
      const grouped = groupExecutionsByDate(mockExecutions)
      expect(Object.keys(grouped)).toHaveLength(2)
      expect(grouped['2025-12-17']).toHaveLength(3)
      expect(grouped['2025-12-18']).toHaveLength(1)
    })

    it('handles empty array', () => {
      const grouped = groupExecutionsByDate([])
      expect(grouped).toEqual({})
    })

    it('preserves execution order within date', () => {
      const grouped = groupExecutionsByDate(mockExecutions)
      const dec17 = grouped['2025-12-17']
      expect(dec17[0].id).toBe('1')
      expect(dec17[1].id).toBe('2')
      expect(dec17[2].id).toBe('4')
    })

    it('handles null/undefined input gracefully', () => {
      expect(groupExecutionsByDate(null)).toEqual({})
      expect(groupExecutionsByDate(undefined)).toEqual({})
    })

    it('extracts date from ISO datetime string', () => {
      const executions = [
        { id: '1', start_time: '2025-01-15T23:59:59Z' },
      ]
      const grouped = groupExecutionsByDate(executions)
      expect(grouped['2025-01-15']).toBeDefined()
    })
  })

  describe('formatDateRange', () => {
    describe('month view', () => {
      it('formats as "Month Year"', () => {
        const date = new Date(2025, 11, 15) // December 15, 2025
        const result = formatDateRange('month', date)
        expect(result).toBe('December 2025')
      })

      it('handles January correctly', () => {
        const date = new Date(2025, 0, 1)
        expect(formatDateRange('month', date)).toBe('January 2025')
      })
    })

    describe('week view', () => {
      it('formats as date range within same month', () => {
        const date = new Date(2025, 11, 17) // Wednesday Dec 17
        const result = formatDateRange('week', date)
        // Dec 14-20, 2025
        expect(result).toMatch(/Dec(?:ember)?\s+14\s*[-–]\s*20,?\s*2025/)
      })

      it('formats date range crossing months', () => {
        const date = new Date(2025, 11, 31) // Wednesday Dec 31
        const result = formatDateRange('week', date)
        // Should show Dec 28 - Jan 3 or similar
        expect(result).toMatch(/Dec|Jan/)
      })
    })

    describe('day view', () => {
      it('formats as full date', () => {
        const date = new Date(2025, 11, 17)
        const result = formatDateRange('day', date)
        expect(result).toMatch(/December\s+17,?\s*2025|Dec\s+17,?\s*2025/)
      })
    })
  })

  describe('getPatternColor', () => {
    it('returns a color from PATTERN_COLORS', () => {
      const color = getPatternColor('pattern-123')
      expect(PATTERN_COLORS).toContain(color)
    })

    it('returns consistent color for same pattern ID', () => {
      const color1 = getPatternColor('my-pattern-id')
      const color2 = getPatternColor('my-pattern-id')
      expect(color1).toBe(color2)
    })

    it('returns different colors for different patterns (usually)', () => {
      const colors = new Set()
      for (let i = 0; i < 20; i++) {
        colors.add(getPatternColor(`pattern-${i}`))
      }
      // Should have some variety (at least 3 different colors)
      expect(colors.size).toBeGreaterThanOrEqual(3)
    })

    it('handles empty string', () => {
      const color = getPatternColor('')
      expect(PATTERN_COLORS).toContain(color)
    })

    it('handles special characters', () => {
      const color = getPatternColor('pattern_with-special.chars/123')
      expect(PATTERN_COLORS).toContain(color)
    })

    it('handles hash overflow correctly with 32-bit conversion', () => {
      // Test with a long string that will cause hash overflow
      const longPattern = 'very-long-pattern-id-that-will-definitely-overflow-the-hash-calculation-with-many-characters'
      const color = getPatternColor(longPattern)
      expect(PATTERN_COLORS).toContain(color)

      // Verify consistency even with overflow
      const color2 = getPatternColor(longPattern)
      expect(color).toBe(color2)
    })

    it('handles large Unicode characters', () => {
      // Test with emojis and special Unicode
      const unicodePattern = '🦋-pattern-123-🌙'
      const color = getPatternColor(unicodePattern)
      expect(PATTERN_COLORS).toContain(color)
      expect(color).toBe(getPatternColor(unicodePattern))
    })
  })

  describe('isToday', () => {
    it('returns true for today', () => {
      const today = new Date()
      expect(isToday(today)).toBe(true)
    })

    it('returns false for yesterday', () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      expect(isToday(yesterday)).toBe(false)
    })

    it('returns false for tomorrow', () => {
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      expect(isToday(tomorrow)).toBe(false)
    })

    it('ignores time component', () => {
      const todayMidnight = new Date()
      todayMidnight.setHours(0, 0, 0, 0)
      const todayNoon = new Date()
      todayNoon.setHours(12, 0, 0, 0)
      expect(isToday(todayMidnight)).toBe(true)
      expect(isToday(todayNoon)).toBe(true)
    })
  })

  describe('isSameDay', () => {
    it('returns true for same day', () => {
      const date1 = new Date(2025, 11, 17, 8, 0, 0)
      const date2 = new Date(2025, 11, 17, 20, 30, 45)
      expect(isSameDay(date1, date2)).toBe(true)
    })

    it('returns false for different days', () => {
      const date1 = new Date(2025, 11, 17)
      const date2 = new Date(2025, 11, 18)
      expect(isSameDay(date1, date2)).toBe(false)
    })

    it('returns false for different months', () => {
      const date1 = new Date(2025, 11, 17)
      const date2 = new Date(2025, 10, 17)
      expect(isSameDay(date1, date2)).toBe(false)
    })

    it('returns false for different years', () => {
      const date1 = new Date(2025, 11, 17)
      const date2 = new Date(2024, 11, 17)
      expect(isSameDay(date1, date2)).toBe(false)
    })
  })

  describe('formatTime', () => {
    it('formats time from ISO string', () => {
      const result = formatTime('2025-12-17T08:30:00Z')
      // Should contain hour and minute in some format
      expect(result).toMatch(/\d{1,2}:\d{2}/)
    })

    it('handles midnight', () => {
      const result = formatTime('2025-12-17T00:00:00Z')
      expect(result).toMatch(/12:00|0:00|00:00/)
    })

    it('handles noon', () => {
      const result = formatTime('2025-12-17T12:00:00Z')
      expect(result).toMatch(/12:00/)
    })
  })

  describe('getDateKey', () => {
    it('formats Date object to YYYY-MM-DD', () => {
      const date = new Date(2025, 11, 17) // December 17, 2025
      expect(getDateKey(date)).toBe('2025-12-17')
    })

    it('handles single-digit months with zero-padding', () => {
      const date = new Date(2025, 0, 5) // January 5, 2025
      expect(getDateKey(date)).toBe('2025-01-05')
    })

    it('handles single-digit days with zero-padding', () => {
      const date = new Date(2025, 11, 9) // December 9, 2025
      expect(getDateKey(date)).toBe('2025-12-09')
    })

    it('handles ISO string input with time component', () => {
      const isoString = '2025-12-17T20:30:00Z'
      expect(getDateKey(isoString)).toBe('2025-12-17')
    })

    it('handles date-only ISO string input', () => {
      const isoString = '2025-12-17'
      expect(getDateKey(isoString)).toBe('2025-12-17')
    })

    it('handles ISO string with timezone offset', () => {
      const isoString = '2025-12-17T14:30:00-05:00'
      expect(getDateKey(isoString)).toBe('2025-12-17')
    })

    it('handles year boundary dates', () => {
      const newYearsDay = new Date(2025, 0, 1)
      const newYearsEve = new Date(2025, 11, 31)
      expect(getDateKey(newYearsDay)).toBe('2025-01-01')
      expect(getDateKey(newYearsEve)).toBe('2025-12-31')
    })

    it('handles leap year dates', () => {
      const leapDay = new Date(2024, 1, 29) // February 29, 2024
      expect(getDateKey(leapDay)).toBe('2024-02-29')
    })

    it('returns null for null input', () => {
      expect(getDateKey(null)).toBe(null)
    })

    it('returns null for undefined input', () => {
      expect(getDateKey(undefined)).toBe(null)
    })

    it('returns null for invalid Date object', () => {
      const invalidDate = new Date('invalid')
      expect(getDateKey(invalidDate)).toBe(null)
    })

    it('continues to work with valid Date objects after invalid input', () => {
      // Ensure validation doesn't break subsequent valid calls
      getDateKey(null) // Invalid
      getDateKey(new Date('invalid')) // Invalid
      const validDate = new Date(2025, 11, 17)
      expect(getDateKey(validDate)).toBe('2025-12-17') // Should still work
    })
  })

  describe('PATTERN_COLORS', () => {
    it('exports array of color classes', () => {
      expect(Array.isArray(PATTERN_COLORS)).toBe(true)
      expect(PATTERN_COLORS.length).toBeGreaterThanOrEqual(6)
    })

    it('contains Tailwind color classes', () => {
      PATTERN_COLORS.forEach(color => {
        expect(color).toMatch(/^bg-\w+-\d+/)
      })
    })
  })
})
