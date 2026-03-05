import { describe, it, expect } from 'vitest'
import { fixedTimeTriggerSchema, type FixedTimeTriggerFormData } from '../fixed-time'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('fixedTimeTriggerSchema', () => {
  describe('valid values', () => {
    it('accepts valid HH:MM time (14:30)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '14:30' })
      expect(result.success).toBe(true)
    })

    it('accepts midnight (00:00)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '00:00' })
      expect(result.success).toBe(true)
    })

    it('accepts 23:59', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '23:59' })
      expect(result.success).toBe(true)
    })

    it('accepts typical preset times', () => {
      for (const time of ['06:00', '12:00', '18:00', '20:00', '09:05']) {
        const result = fixedTimeTriggerSchema.safeParse({ time_of_day: time })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('rejection', () => {
    it('rejects invalid time format (25:00)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '25:00' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects empty string', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects non-time string (noon)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: 'noon' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Must be a valid time in HH:MM format')
    })

    it('rejects time with invalid minutes (12:60)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '12:60' })
      expect(result.success).toBe(false)
    })

    it('rejects single-digit hour (1:30)', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: '1:30' })
      expect(result.success).toBe(false)
    })

    it('rejects non-string value', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: 1430 })
      expect(result.success).toBe(false)
    })

    it('rejects undefined time_of_day', () => {
      const result = fixedTimeTriggerSchema.safeParse({})
      expect(result.success).toBe(false)
    })

    it('rejects null time_of_day', () => {
      const result = fixedTimeTriggerSchema.safeParse({ time_of_day: null })
      expect(result.success).toBe(false)
    })
  })

  describe('type inference', () => {
    it('inferred type matches expected shape', () => {
      const data: FixedTimeTriggerFormData = { time_of_day: '14:30' }
      expect(data.time_of_day).toBe('14:30')
    })
  })
})
