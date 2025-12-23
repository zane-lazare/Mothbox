import { describe, it, expect, vi, afterEach } from 'vitest'
import { generateUUID } from '../uuid'

// UUID v4 format regex
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

describe('generateUUID', () => {
  describe('Basic functionality', () => {
    it('returns a string', () => {
      const result = generateUUID()
      expect(typeof result).toBe('string')
    })

    it('returns a valid UUID v4 format', () => {
      const result = generateUUID()
      expect(result).toMatch(UUID_REGEX)
    })

    it('returns unique values on each call', () => {
      const uuid1 = generateUUID()
      const uuid2 = generateUUID()
      const uuid3 = generateUUID()

      expect(uuid1).not.toBe(uuid2)
      expect(uuid2).not.toBe(uuid3)
      expect(uuid1).not.toBe(uuid3)
    })

    it('generates 100 unique UUIDs', () => {
      const uuids = new Set()
      for (let i = 0; i < 100; i++) {
        uuids.add(generateUUID())
      }
      expect(uuids.size).toBe(100)
    })
  })

  describe('UUID format validation', () => {
    it('has correct length (36 characters)', () => {
      const result = generateUUID()
      expect(result.length).toBe(36)
    })

    it('has hyphens at correct positions', () => {
      const result = generateUUID()
      expect(result[8]).toBe('-')
      expect(result[13]).toBe('-')
      expect(result[18]).toBe('-')
      expect(result[23]).toBe('-')
    })

    it('has version 4 indicator at position 14', () => {
      const result = generateUUID()
      expect(result[14]).toBe('4')
    })

    it('has valid variant bits at position 19', () => {
      const result = generateUUID()
      expect(['8', '9', 'a', 'b']).toContain(result[19].toLowerCase())
    })
  })

  describe('Fallback behavior', () => {
    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('falls back to getRandomValues when randomUUID is unavailable', () => {
      // Mock crypto without randomUUID
      vi.stubGlobal('crypto', {
        getRandomValues: (arr) => {
          for (let i = 0; i < arr.length; i++) {
            arr[i] = Math.floor(Math.random() * 256)
          }
          return arr
        }
      })

      const result = generateUUID()
      expect(result).toMatch(UUID_REGEX)
    })

    it('falls back to Math.random when crypto is completely unavailable', () => {
      // Remove crypto entirely
      vi.stubGlobal('crypto', undefined)

      const result = generateUUID()
      expect(result).toMatch(UUID_REGEX)
    })

    it('falls back to Math.random when crypto exists but has no methods', () => {
      // Mock crypto with no useful methods
      vi.stubGlobal('crypto', {})

      const result = generateUUID()
      expect(result).toMatch(UUID_REGEX)
    })
  })

  describe('Edge cases', () => {
    it('handles rapid successive calls', () => {
      const uuids = []
      for (let i = 0; i < 1000; i++) {
        uuids.push(generateUUID())
      }

      // All should be valid UUIDs
      uuids.forEach((uuid) => {
        expect(uuid).toMatch(UUID_REGEX)
      })

      // All should be unique
      const uniqueUuids = new Set(uuids)
      expect(uniqueUuids.size).toBe(1000)
    })
  })
})
