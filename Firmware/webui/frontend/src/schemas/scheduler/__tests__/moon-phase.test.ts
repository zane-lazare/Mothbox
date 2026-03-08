import { describe, it, expect } from 'vitest'
import { moonPhaseTriggerSchema } from '../moon-phase'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
} from '../../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  moon_phase: 'full',
  time_of_day: '20:00',
  offset_days: 0,
}

describe('moonPhaseTriggerSchema', () => {
  describe('moon_phase field', () => {
    it('accepts all valid moon phases', () => {
      for (const phase of MOON_PHASES) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          moon_phase: phase.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects an invalid moon phase string', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        moon_phase: 'invalid_phase',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidMoonPhase)
    })

    it('rejects a numeric moon phase', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        moon_phase: 123,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined moon phase', () => {
      const { moon_phase: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('time_of_day field', () => {
    it('accepts valid HH:MM times', () => {
      for (const time of ['00:00', '12:30', '23:59', '09:05']) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          time_of_day: time,
        })
        expect(result.success).toBe(true)
      }
    })

    it('rejects invalid time formats', () => {
      for (const time of ['25:00', '12:60', '1:30', '12:5', 'abc', '']) {
        const result = moonPhaseTriggerSchema.safeParse({
          ...VALID_INPUT,
          time_of_day: time,
        })
        expect(result.success).toBe(false)
        if (time === '') {
          expect(firstError(result)).toBe(FORMAT.timeRequired)
        }
      }
    })

    it('rejects non-string time', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        time_of_day: 1200,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(REQUIRED.field('Time'))
    })

    it('rejects undefined time', () => {
      const { time_of_day: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('offset_days — valid values', () => {
    it('accepts zero offset', () => {
      const result = moonPhaseTriggerSchema.safeParse(VALID_INPUT)
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: 3,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -3,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum offset (7)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimum offset (-7)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      })
      expect(result.success).toBe(true)
    })
  })

  describe('offset_days — boundary rejection', () => {
    it('rejects 8 (above maximum)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: SCHEDULE_LIMITS.MAX_OFFSET_DAYS + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
      )
    })

    it('rejects -8 (below minimum)', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: -(SCHEDULE_LIMITS.MAX_OFFSET_DAYS + 1),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_DAYS, 'days'),
      )
    })
  })

  describe('offset_days — type rejection', () => {
    it('rejects float values', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: 2.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.integer('Offset'))
    })

    it('rejects string values', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: '3',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })

    it('rejects NaN', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })

    it('rejects undefined offset', () => {
      const { offset_days: _, ...rest } = VALID_INPUT
      const result = moonPhaseTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects null offset', () => {
      const result = moonPhaseTriggerSchema.safeParse({
        ...VALID_INPUT,
        offset_days: null,
      })
      expect(result.success).toBe(false)
    })
  })
})
