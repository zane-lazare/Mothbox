import { describe, it, expect } from 'vitest'
import { intervalTriggerSchema } from '../interval'
import { SCHEDULE_LIMITS } from '../../../components/scheduler/ScheduleEditor/constants'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('intervalTriggerSchema', () => {
  describe('valid values', () => {
    it('accepts minimum interval (1)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 1 })
      expect(result.success).toBe(true)
    })

    it('accepts default interval (60)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 60 })
      expect(result.success).toBe(true)
    })

    it('accepts maximum interval (10080)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 10080 })
      expect(result.success).toBe(true)
    })

    it('accepts typical preset values', () => {
      for (const minutes of [15, 30, 60, 120, 240]) {
        const result = intervalTriggerSchema.safeParse({ interval_minutes: minutes })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('boundary rejection', () => {
    it('rejects 0 (below minimum)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 0 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Interval must be at least ${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES} minute${SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES !== 1 ? 's' : ''}`,
      )
    })

    it('rejects negative values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: -10 })
      expect(result.success).toBe(false)
    })

    it('rejects 10081 (above maximum)', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 10081 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        `Interval cannot exceed ${SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES} minutes`,
      )
    })
  })

  describe('type rejection', () => {
    it('rejects float values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: 30.5 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Interval must be a whole number')
    })

    it('rejects string values', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: '60' })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Interval must be a number')
    })

    it('rejects NaN', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: NaN })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Interval must be a number')
    })

    it('rejects undefined', () => {
      const result = intervalTriggerSchema.safeParse({})
      expect(result.success).toBe(false)
    })

    it('rejects null', () => {
      const result = intervalTriggerSchema.safeParse({ interval_minutes: null })
      expect(result.success).toBe(false)
    })
  })
})
