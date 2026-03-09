import { describe, it, expect } from 'vitest'
import { timeWindowSchema } from '../time-window'
import { SOLAR_EVENTS } from '../../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT } from '../../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  start_time: '20:00',
  end_time: '06:00',
  start_offset_minutes: 0,
  end_offset_minutes: 0,
}

describe('timeWindowSchema', () => {
  describe('start_time / end_time — valid values', () => {
    it('accepts valid HH:MM times for both fields', () => {
      for (const time of ['00:00', '12:30', '23:59', '09:05']) {
        const result = timeWindowSchema.safeParse({
          ...VALID_INPUT,
          start_time: time,
          end_time: time,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts all 15 solar events for start_time', () => {
      for (const event of SOLAR_EVENTS) {
        const result = timeWindowSchema.safeParse({
          ...VALID_INPUT,
          start_time: event.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts all 15 solar events for end_time', () => {
      for (const event of SOLAR_EVENTS) {
        const result = timeWindowSchema.safeParse({
          ...VALID_INPUT,
          end_time: event.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts mixed fixed time + solar event', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_time: 'sunset',
        end_time: '06:00',
      })
      expect(result.success).toBe(true)
    })

    it('accepts mixed solar event + fixed time', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_time: '20:00',
        end_time: 'sunrise',
      })
      expect(result.success).toBe(true)
    })
  })

  describe('start_time / end_time — invalid values', () => {
    it('rejects empty string for start_time', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_time: '',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        FORMAT.timeOrSolar,
      )
    })

    it('rejects empty string for end_time', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        end_time: '',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        FORMAT.timeOrSolar,
      )
    })

    it('rejects invalid time formats', () => {
      for (const time of ['25:00', '1:30', '12:60', '12:5']) {
        const result = timeWindowSchema.safeParse({
          ...VALID_INPUT,
          start_time: time,
        })
        expect(result.success).toBe(false)
        expect(firstError(result)).toBe(
          FORMAT.timeOrSolar,
        )
      }
    })

    it('rejects arbitrary strings', () => {
      for (const time of ['abc', 'not_a_solar_event', 'midnight']) {
        const result = timeWindowSchema.safeParse({
          ...VALID_INPUT,
          start_time: time,
        })
        expect(result.success).toBe(false)
        expect(firstError(result)).toBe(
          FORMAT.timeOrSolar,
        )
      }
    })

    it('rejects non-string types', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_time: 1200,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(REQUIRED.field('Time'))
    })

    it('rejects undefined start_time', () => {
      const { start_time: _, ...rest } = VALID_INPUT
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects undefined end_time', () => {
      const { end_time: _, ...rest } = VALID_INPUT
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('offset fields — valid values', () => {
    it('accepts zero offset for both fields', () => {
      const result = timeWindowSchema.safeParse(VALID_INPUT)
      expect(result.success).toBe(true)
    })

    it('accepts positive offset within range', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: 60,
        end_offset_minutes: 60,
      })
      expect(result.success).toBe(true)
    })

    it('accepts negative offset within range', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: -60,
        end_offset_minutes: -60,
      })
      expect(result.success).toBe(true)
    })

    it('accepts maximum offset (120)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: 120,
        end_offset_minutes: 120,
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimum offset (-120)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: -120,
        end_offset_minutes: -120,
      })
      expect(result.success).toBe(true)
    })

    it('defaults to 0 when start_offset_minutes is omitted', () => {
      const { start_offset_minutes: _, ...rest } = VALID_INPUT
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.start_offset_minutes).toBe(0)
      }
    })

    it('defaults to 0 when end_offset_minutes is omitted', () => {
      const { end_offset_minutes: _, ...rest } = VALID_INPUT
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.end_offset_minutes).toBe(0)
      }
    })

    it('defaults to 0 when both offsets are omitted', () => {
      const {
        start_offset_minutes: _s,
        end_offset_minutes: _e,
        ...rest
      } = VALID_INPUT
      const result = timeWindowSchema.safeParse(rest)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.start_offset_minutes).toBe(0)
        expect(result.data.end_offset_minutes).toBe(0)
      }
    })
  })

  describe('offset fields — boundary rejection', () => {
    it('rejects 121 for start_offset_minutes (above maximum)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: 121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(RANGE.max(120, 'minutes'))
    })

    it('rejects -121 for start_offset_minutes (below minimum)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: -121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(RANGE.min(-120, 'minutes'))
    })

    it('rejects 121 for end_offset_minutes (above maximum)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        end_offset_minutes: 121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(RANGE.max(120, 'minutes'))
    })

    it('rejects -121 for end_offset_minutes (below minimum)', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        end_offset_minutes: -121,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(RANGE.min(-120, 'minutes'))
    })
  })

  describe('offset fields — type rejection', () => {
    it('rejects float values', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: 2.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.integer('Offset'))
    })

    it('rejects string values', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        start_offset_minutes: '30',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })

    it('rejects NaN', () => {
      const result = timeWindowSchema.safeParse({
        ...VALID_INPUT,
        end_offset_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Offset'))
    })
  })
})
