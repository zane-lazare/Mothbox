import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  GPS_PRECISION_OPTIONS,
  getGpsPrecision,
  setGpsPrecision,
} from '../gpsPrecision'

describe('gpsPrecision', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  describe('GPS_PRECISION_OPTIONS', () => {
    it('has 7 precision levels (0-6)', () => {
      expect(GPS_PRECISION_OPTIONS).toHaveLength(7)
    })

    it('includes all required precision values', () => {
      const values = GPS_PRECISION_OPTIONS.map(o => o.value)
      expect(values).toEqual([0, 1, 2, 3, 4, 5, 6])
    })

    it('has label and description for each option', () => {
      GPS_PRECISION_OPTIONS.forEach(option => {
        expect(option.label).toBeDefined()
        expect(option.description).toBeDefined()
        expect(typeof option.label).toBe('string')
        expect(typeof option.description).toBe('string')
      })
    })
  })

  describe('getGpsPrecision', () => {
    it('returns default value of 2 when localStorage is empty', () => {
      expect(getGpsPrecision()).toBe(2)
    })

    it('returns stored value from localStorage', () => {
      localStorage.setItem('mothbox_gps_precision', '4')
      expect(getGpsPrecision()).toBe(4)
    })

    it('returns default value for invalid stored values', () => {
      localStorage.setItem('mothbox_gps_precision', 'invalid')
      expect(getGpsPrecision()).toBe(2)
    })

    it('returns default value for out-of-range values (negative)', () => {
      localStorage.setItem('mothbox_gps_precision', '-1')
      expect(getGpsPrecision()).toBe(2)
    })

    it('returns default value for out-of-range values (> 6)', () => {
      localStorage.setItem('mothbox_gps_precision', '7')
      expect(getGpsPrecision()).toBe(2)
    })

    it('handles all valid precision values', () => {
      for (let i = 0; i <= 6; i++) {
        localStorage.setItem('mothbox_gps_precision', String(i))
        expect(getGpsPrecision()).toBe(i)
      }
    })
  })

  describe('setGpsPrecision', () => {
    it('stores precision value in localStorage', () => {
      setGpsPrecision(3)
      expect(localStorage.getItem('mothbox_gps_precision')).toBe('3')
    })

    it('stores precision as string', () => {
      setGpsPrecision(5)
      const stored = localStorage.getItem('mothbox_gps_precision')
      expect(typeof stored).toBe('string')
      expect(stored).toBe('5')
    })

    it('overwrites previous value', () => {
      setGpsPrecision(1)
      expect(localStorage.getItem('mothbox_gps_precision')).toBe('1')
      setGpsPrecision(4)
      expect(localStorage.getItem('mothbox_gps_precision')).toBe('4')
    })

    it('can be retrieved by getGpsPrecision', () => {
      setGpsPrecision(6)
      expect(getGpsPrecision()).toBe(6)
    })
  })

  describe('localStorage unavailable', () => {
    it('getGpsPrecision returns default when localStorage throws', () => {
      const originalGetItem = localStorage.getItem
      localStorage.getItem = vi.fn(() => {
        throw new Error('localStorage disabled')
      })

      expect(getGpsPrecision()).toBe(2)

      localStorage.getItem = originalGetItem
    })

    it('setGpsPrecision handles localStorage errors gracefully', () => {
      const originalSetItem = localStorage.setItem
      localStorage.setItem = vi.fn(() => {
        throw new Error('localStorage disabled')
      })

      // Should not throw
      expect(() => setGpsPrecision(3)).not.toThrow()

      localStorage.setItem = originalSetItem
    })
  })
})
