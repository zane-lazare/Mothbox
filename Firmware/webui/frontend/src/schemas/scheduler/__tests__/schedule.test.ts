import { describe, it, expect } from 'vitest'
import { scheduleSchema, type ScheduleFormData } from '../schedule'
import { SCHEDULE_LIMITS } from '@/components/scheduler/ScheduleEditor/constants'

describe('scheduleSchema', () => {
  describe('name field', () => {
    it('accepts a valid name', () => {
      const result = scheduleSchema.safeParse({ name: 'My Schedule', description: '' })
      expect(result.success).toBe(true)
    })

    it('rejects empty name', () => {
      const result = scheduleSchema.safeParse({ name: '', description: '' })
      expect(result.success).toBe(false)
    })

    it('rejects whitespace-only name', () => {
      const result = scheduleSchema.safeParse({ name: '   ', description: '' })
      expect(result.success).toBe(false)
    })

    it('rejects name exceeding max length', () => {
      const longName = 'a'.repeat(SCHEDULE_LIMITS.NAME_MAX_LENGTH + 1)
      const result = scheduleSchema.safeParse({ name: longName, description: '' })
      expect(result.success).toBe(false)
    })

    it('accepts name at max length', () => {
      const maxName = 'a'.repeat(SCHEDULE_LIMITS.NAME_MAX_LENGTH)
      const result = scheduleSchema.safeParse({ name: maxName, description: '' })
      expect(result.success).toBe(true)
    })

    it('trims whitespace from name', () => {
      const result = scheduleSchema.safeParse({ name: '  My Schedule  ', description: '' })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.name).toBe('My Schedule')
      }
    })
  })

  describe('description field', () => {
    it('accepts empty description', () => {
      const result = scheduleSchema.safeParse({ name: 'Test', description: '' })
      expect(result.success).toBe(true)
    })

    it('defaults description to empty string when omitted', () => {
      const result = scheduleSchema.safeParse({ name: 'Test' })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.description).toBe('')
      }
    })

    it('rejects description exceeding max length', () => {
      const longDesc = 'a'.repeat(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH + 1)
      const result = scheduleSchema.safeParse({ name: 'Test', description: longDesc })
      expect(result.success).toBe(false)
    })

    it('accepts description at max length', () => {
      const maxDesc = 'a'.repeat(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH)
      const result = scheduleSchema.safeParse({ name: 'Test', description: maxDesc })
      expect(result.success).toBe(true)
    })
  })

  describe('type inference', () => {
    it('inferred type matches expected shape', () => {
      const data: ScheduleFormData = { name: 'Test', description: 'desc' }
      expect(data.name).toBe('Test')
      expect(data.description).toBe('desc')
    })
  })
})
