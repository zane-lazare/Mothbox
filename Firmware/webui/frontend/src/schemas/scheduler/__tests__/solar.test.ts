import { describe, it, expect } from 'vitest'
import { solarTriggerSchema } from '../solar'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
} from '../../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('solarTriggerSchema', () => {
  describe('solar_event field', () => {
    it('accepts all valid solar events', () => {
      for (const event of SOLAR_EVENTS) {
        const result = solarTriggerSchema.safeParse({
          solar_event: event.value,
          offset_minutes: 0,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects an invalid solar event string', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'invalid_event',
        offset_minutes: 0,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidSolarEvent)
    })

    it('rejects a numeric solar event', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 123,
        offset_minutes: 0,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined solar event', () => {
      const result = solarTriggerSchema.safeParse({ offset_minutes: 0 })
      expect(result.success).toBe(false)
    })
  })

  describe('offset_minutes — valid values', () => {
    it('accepts zero offset', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 0,
      })
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 30,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -30,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum offset (1440)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimum offset (-1440)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts typical preset values', () => {
      for (const offset of [-60, -30, 0, 30, 60]) {
        const result = solarTriggerSchema.safeParse({
          solar_event: 'sunset',
          offset_minutes: offset,
        })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('offset_minutes — boundary rejection', () => {
    it('rejects 1441 (above maximum)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: SCHEDULE_LIMITS.MAX_OFFSET_MINUTES + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
      )
    })

    it('rejects -1441 (below minimum)', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: -(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES + 1),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
      )
    })
  })

  describe('offset_minutes — type rejection', () => {
    it('rejects float values', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: 30.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.integer('Offset'))
    })

    it('rejects string values', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: '30',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })

    it('rejects NaN', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })

    it('rejects undefined offset', () => {
      const result = solarTriggerSchema.safeParse({ solar_event: 'sunset' })
      expect(result.success).toBe(false)
    })

    it('rejects null offset', () => {
      const result = solarTriggerSchema.safeParse({
        solar_event: 'sunset',
        offset_minutes: null,
      })
      expect(result.success).toBe(false)
    })
  })
})
