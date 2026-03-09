import { describe, it, expect } from 'vitest'
import { bulkTagSchema, TAG_MODES, TAG_MAX_LENGTH, TAG_MAX_COUNT } from '../tag'
import { TAG } from '../../constants/errorMessages'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

// ---------------------------------------------------------------------------
// TAG_MODES
// ---------------------------------------------------------------------------

describe('TAG_MODES', () => {
  it('exports all three mode values', () => {
    expect(TAG_MODES).toEqual(['add', 'replace', 'remove'])
  })
})

// ---------------------------------------------------------------------------
// bulkTagSchema – valid data
// ---------------------------------------------------------------------------

describe('bulkTagSchema – valid data', () => {
  it('accepts tags with add mode', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }], mode: 'add' })
    expect(result.success).toBe(true)
  })

  it('accepts tags with replace mode', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }], mode: 'replace' })
    expect(result.success).toBe(true)
  })

  it('accepts tags with remove mode', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }], mode: 'remove' })
    expect(result.success).toBe(true)
  })

  it('accepts a single tag', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'nocturnal' }], mode: 'add' })
    expect(result.success).toBe(true)
  })

  it('accepts multiple tags', () => {
    const result = bulkTagSchema.safeParse({
      tags: [{ value: 'moth' }, { value: 'nocturnal' }, { value: 'field-site-A' }],
      mode: 'add',
    })
    expect(result.success).toBe(true)
  })

  it('trims whitespace from tag values', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: '  moth  ' }], mode: 'add' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags[0].value).toBe('moth')
    }
  })
})

// ---------------------------------------------------------------------------
// bulkTagSchema – invalid data
// ---------------------------------------------------------------------------

describe('bulkTagSchema – invalid data', () => {
  it('rejects an empty tags array', () => {
    const result = bulkTagSchema.safeParse({ tags: [], mode: 'add' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TAG.minRequired)
  })

  it('rejects an empty string tag', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: '' }], mode: 'add' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TAG.empty)
  })

  it('rejects a whitespace-only tag', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: '   ' }], mode: 'add' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TAG.empty)
  })

  it('rejects an invalid mode', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }], mode: 'invalid' })
    expect(result.success).toBe(false)
  })

  it('rejects missing tags field', () => {
    const result = bulkTagSchema.safeParse({ mode: 'add' })
    expect(result.success).toBe(false)
  })

  it('rejects missing mode field', () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }] })
    expect(result.success).toBe(false)
  })

  it(`rejects a tag longer than ${TAG_MAX_LENGTH} characters`, () => {
    const result = bulkTagSchema.safeParse({ tags: [{ value: 'a'.repeat(TAG_MAX_LENGTH + 1) }], mode: 'add' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TAG.tooLong)
  })

  it(`rejects more than ${TAG_MAX_COUNT} tags`, () => {
    const tags = Array.from({ length: TAG_MAX_COUNT + 1 }, (_, i) => ({ value: `tag-${i}` }))
    const result = bulkTagSchema.safeParse({ tags, mode: 'add' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(TAG.tooMany)
  })
})
