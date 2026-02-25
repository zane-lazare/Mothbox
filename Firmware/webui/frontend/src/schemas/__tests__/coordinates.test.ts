import { describe, it, expect } from 'vitest'
import { coordinatesSchema } from '../coordinates'

function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('coordinatesSchema', () => {
  describe('valid data', () => {
    it('accepts valid coordinates', () => {
      const result = coordinatesSchema.safeParse({ latitude: 37.7749, longitude: -122.4194 })
      expect(result.success).toBe(true)
    })

    it('accepts null latitude and longitude', () => {
      const result = coordinatesSchema.safeParse({ latitude: null, longitude: null })
      expect(result.success).toBe(true)
    })

    it('accepts boundary values', () => {
      for (const [lat, lon] of [[-90, -180], [90, 180], [0, 0]]) {
        const result = coordinatesSchema.safeParse({ latitude: lat, longitude: lon })
        expect(result.success).toBe(true)
      }
    })

    it('accepts mixed null and number', () => {
      expect(coordinatesSchema.safeParse({ latitude: 10, longitude: null }).success).toBe(true)
      expect(coordinatesSchema.safeParse({ latitude: null, longitude: 10 }).success).toBe(true)
    })
  })

  describe('latitude validation', () => {
    it('rejects latitude > 90', () => {
      const result = coordinatesSchema.safeParse({ latitude: 91, longitude: 0 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Latitude must be between -90 and 90')
    })

    it('rejects latitude < -90', () => {
      const result = coordinatesSchema.safeParse({ latitude: -91, longitude: 0 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Latitude must be between -90 and 90')
    })
  })

  describe('longitude validation', () => {
    it('rejects longitude > 180', () => {
      const result = coordinatesSchema.safeParse({ latitude: 0, longitude: 181 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Longitude must be between -180 and 180')
    })

    it('rejects longitude < -180', () => {
      const result = coordinatesSchema.safeParse({ latitude: 0, longitude: -181 })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Longitude must be between -180 and 180')
    })
  })

  describe('type validation', () => {
    it('rejects string latitude', () => {
      const result = coordinatesSchema.safeParse({ latitude: 'abc', longitude: 0 })
      expect(result.success).toBe(false)
    })

    it('rejects undefined fields', () => {
      const result = coordinatesSchema.safeParse({})
      expect(result.success).toBe(false)
    })
  })
})
