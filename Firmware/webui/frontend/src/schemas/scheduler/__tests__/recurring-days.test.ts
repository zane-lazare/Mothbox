import { describe, it, expect } from 'vitest'
import { recurringDaysTriggerSchema, type RecurringDaysTriggerFormData } from '../recurring-days'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('recurringDaysTriggerSchema', () => {
  describe('valid values', () => {
    it('accepts a single day with valid time', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: '20:00' })
      expect(result.success).toBe(true)
    })

    it('accepts multiple days', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0, 3, 5], time: '08:30' })
      expect(result.success).toBe(true)
    })

    it('accepts all seven days', () => {
      const result = recurringDaysTriggerSchema.safeParse({
        days: [0, 1, 2, 3, 4, 5, 6],
        time: '12:00',
      })
      expect(result.success).toBe(true)
    })

    it('accepts midnight (00:00)', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [1], time: '00:00' })
      expect(result.success).toBe(true)
    })

    it('accepts 23:59', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [6], time: '23:59' })
      expect(result.success).toBe(true)
    })
  })

  describe('days rejection', () => {
    it('rejects empty days array', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [], time: '20:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('At least one day must be selected')
    })

    it('rejects day value below 0', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [-1], time: '20:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Day must be between 0 and 6')
    })

    it('rejects day value above 6', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [7], time: '20:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Day must be between 0 and 6')
    })

    it('rejects non-integer day values', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [1.5], time: '20:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Day must be a whole number')
    })

    it('rejects string day values', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: ['Monday'], time: '20:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Day must be a number')
    })

    it('rejects undefined days', () => {
      const result = recurringDaysTriggerSchema.safeParse({ time: '20:00' })
      expect(result.success).toBe(false)
    })

    it('rejects null days', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: null, time: '20:00' })
      expect(result.success).toBe(false)
    })
  })

  describe('time rejection', () => {
    it('rejects invalid time format (25:00)', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: '25:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects empty string', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: '' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects non-time string', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: 'evening' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects time with invalid minutes (12:60)', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: '12:60' })
      expect(result.success).toBe(false)
    })

    it('rejects single-digit hour (1:30)', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: '1:30' })
      expect(result.success).toBe(false)
    })

    it('rejects non-string value', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: 2000 })
      expect(result.success).toBe(false)
    })

    it('rejects undefined time', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0] })
      expect(result.success).toBe(false)
    })

    it('rejects null time', () => {
      const result = recurringDaysTriggerSchema.safeParse({ days: [0], time: null })
      expect(result.success).toBe(false)
    })
  })

  describe('type inference', () => {
    it('inferred type matches expected shape', () => {
      const data: RecurringDaysTriggerFormData = { days: [0, 5, 6], time: '20:00' }
      expect(data.days).toEqual([0, 5, 6])
      expect(data.time).toBe('20:00')
    })
  })
})
