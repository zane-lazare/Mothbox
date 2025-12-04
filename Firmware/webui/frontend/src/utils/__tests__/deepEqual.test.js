import { describe, it, expect } from 'vitest'
import deepEqual from '../deepEqual'

describe('deepEqual', () => {
  describe('primitives', () => {
    it('returns true for identical strings', () => {
      expect(deepEqual('hello', 'hello')).toBe(true)
    })

    it('returns false for different strings', () => {
      expect(deepEqual('hello', 'world')).toBe(false)
    })

    it('returns true for identical numbers', () => {
      expect(deepEqual(42, 42)).toBe(true)
    })

    it('returns false for different numbers', () => {
      expect(deepEqual(42, 43)).toBe(false)
    })

    it('returns true for identical booleans', () => {
      expect(deepEqual(true, true)).toBe(true)
      expect(deepEqual(false, false)).toBe(true)
    })

    it('returns false for different booleans', () => {
      expect(deepEqual(true, false)).toBe(false)
    })

    it('returns true for both null', () => {
      expect(deepEqual(null, null)).toBe(true)
    })

    it('returns true for both undefined', () => {
      expect(deepEqual(undefined, undefined)).toBe(true)
    })

    it('returns false for null vs undefined', () => {
      expect(deepEqual(null, undefined)).toBe(false)
    })
  })

  describe('NaN handling', () => {
    it('returns true for both NaN', () => {
      expect(deepEqual(NaN, NaN)).toBe(true)
    })

    it('returns false for NaN vs number', () => {
      expect(deepEqual(NaN, 42)).toBe(false)
    })
  })

  describe('Date handling', () => {
    it('returns true for same dates', () => {
      const d1 = new Date('2024-01-01')
      const d2 = new Date('2024-01-01')
      expect(deepEqual(d1, d2)).toBe(true)
    })

    it('returns false for different dates', () => {
      const d1 = new Date('2024-01-01')
      const d2 = new Date('2024-01-02')
      expect(deepEqual(d1, d2)).toBe(false)
    })

    it('returns false for date vs string', () => {
      const d = new Date('2024-01-01')
      expect(deepEqual(d, '2024-01-01')).toBe(false)
    })
  })

  describe('arrays', () => {
    it('returns true for empty arrays', () => {
      expect(deepEqual([], [])).toBe(true)
    })

    it('returns true for identical arrays', () => {
      expect(deepEqual([1, 2, 3], [1, 2, 3])).toBe(true)
    })

    it('returns false for different length arrays', () => {
      expect(deepEqual([1, 2], [1, 2, 3])).toBe(false)
    })

    it('returns false for arrays with different values', () => {
      expect(deepEqual([1, 2, 3], [1, 2, 4])).toBe(false)
    })

    it('returns false for arrays with different order', () => {
      expect(deepEqual([1, 2, 3], [3, 2, 1])).toBe(false)
    })

    it('handles nested arrays', () => {
      expect(deepEqual([[1, 2], [3, 4]], [[1, 2], [3, 4]])).toBe(true)
      expect(deepEqual([[1, 2], [3, 4]], [[1, 2], [3, 5]])).toBe(false)
    })

    it('returns false for array vs object', () => {
      expect(deepEqual([1, 2], { 0: 1, 1: 2 })).toBe(false)
    })
  })

  describe('objects', () => {
    it('returns true for empty objects', () => {
      expect(deepEqual({}, {})).toBe(true)
    })

    it('returns true for identical objects', () => {
      expect(deepEqual({ a: 1, b: 2 }, { a: 1, b: 2 })).toBe(true)
    })

    it('returns true for objects with different key order', () => {
      // This is the key test that JSON.stringify fails
      expect(deepEqual({ a: 1, b: 2 }, { b: 2, a: 1 })).toBe(true)
    })

    it('returns false for objects with different keys', () => {
      expect(deepEqual({ a: 1 }, { b: 1 })).toBe(false)
    })

    it('returns false for objects with different values', () => {
      expect(deepEqual({ a: 1 }, { a: 2 })).toBe(false)
    })

    it('returns false for objects with different number of keys', () => {
      expect(deepEqual({ a: 1 }, { a: 1, b: 2 })).toBe(false)
    })

    it('handles nested objects', () => {
      expect(deepEqual(
        { a: { b: 1, c: 2 } },
        { a: { b: 1, c: 2 } }
      )).toBe(true)

      expect(deepEqual(
        { a: { b: 1, c: 2 } },
        { a: { b: 1, c: 3 } }
      )).toBe(false)
    })

    it('handles deeply nested objects with different key order', () => {
      expect(deepEqual(
        { a: { b: 1, c: 2 }, d: 3 },
        { d: 3, a: { c: 2, b: 1 } }
      )).toBe(true)
    })
  })

  describe('mixed types', () => {
    it('returns false for number vs string', () => {
      expect(deepEqual(1, '1')).toBe(false)
    })

    it('returns false for null vs object', () => {
      expect(deepEqual(null, {})).toBe(false)
    })

    it('returns false for undefined vs empty string', () => {
      expect(deepEqual(undefined, '')).toBe(false)
    })

    it('handles objects with arrays', () => {
      expect(deepEqual(
        { tags: ['a', 'b'], count: 2 },
        { tags: ['a', 'b'], count: 2 }
      )).toBe(true)

      expect(deepEqual(
        { tags: ['a', 'b'], count: 2 },
        { tags: ['a', 'c'], count: 2 }
      )).toBe(false)
    })

    it('handles arrays of objects', () => {
      expect(deepEqual(
        [{ a: 1 }, { b: 2 }],
        [{ a: 1 }, { b: 2 }]
      )).toBe(true)

      expect(deepEqual(
        [{ a: 1 }, { b: 2 }],
        [{ a: 1 }, { b: 3 }]
      )).toBe(false)
    })
  })

  describe('real-world metadata scenarios', () => {
    it('compares typical sidecar metadata objects', () => {
      const metadata1 = {
        tags: ['moth', 'nocturnal'],
        species: 'Actias luna',
        species_confidence: 'probable',
        notes: 'Found near porch light',
        custom: { location: 'backyard' }
      }

      const metadata2 = {
        species: 'Actias luna',
        tags: ['moth', 'nocturnal'],
        notes: 'Found near porch light',
        species_confidence: 'probable',
        custom: { location: 'backyard' }
      }

      // Same data, different key order - should be equal
      expect(deepEqual(metadata1, metadata2)).toBe(true)
    })

    it('detects changes in nested custom fields', () => {
      const before = {
        tags: ['moth'],
        custom: { field1: 'value1', field2: 'value2' }
      }

      const after = {
        tags: ['moth'],
        custom: { field1: 'value1', field2: 'changed' }
      }

      expect(deepEqual(before, after)).toBe(false)
    })

    it('detects tag additions', () => {
      const before = { tags: ['moth'] }
      const after = { tags: ['moth', 'new-tag'] }

      expect(deepEqual(before, after)).toBe(false)
    })
  })

  describe('edge cases', () => {
    it('handles same reference', () => {
      const obj = { a: 1 }
      expect(deepEqual(obj, obj)).toBe(true)
    })

    it('handles empty nested structures', () => {
      expect(deepEqual({ a: {} }, { a: {} })).toBe(true)
      expect(deepEqual({ a: [] }, { a: [] })).toBe(true)
    })

    it('handles 0 vs -0', () => {
      // In JavaScript, 0 === -0, so they should be equal
      expect(deepEqual(0, -0)).toBe(true)
    })

    it('handles Infinity', () => {
      expect(deepEqual(Infinity, Infinity)).toBe(true)
      expect(deepEqual(-Infinity, -Infinity)).toBe(true)
      expect(deepEqual(Infinity, -Infinity)).toBe(false)
    })
  })
})
