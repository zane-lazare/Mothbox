import { describe, it, expect } from 'vitest'
import { filterPresetNameSchema, cameraPresetNameSchema } from '../preset'
import { REQUIRED, LENGTH, PRESET } from '../../constants/errorMessages'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

// ---------------------------------------------------------------------------
// filterPresetNameSchema
// ---------------------------------------------------------------------------

describe('filterPresetNameSchema', () => {
  it('accepts a valid name', () => {
    const result = filterPresetNameSchema.safeParse({ name: 'Moths from June' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with special characters', () => {
    const result = filterPresetNameSchema.safeParse({ name: 'my-preset (v2)!' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with exactly 3 characters', () => {
    const result = filterPresetNameSchema.safeParse({ name: 'abc' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with exactly 50 characters', () => {
    const result = filterPresetNameSchema.safeParse({ name: 'a'.repeat(50) })
    expect(result.success).toBe(true)
  })

  it('rejects an empty string', () => {
    const result = filterPresetNameSchema.safeParse({ name: '' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('Preset name'))
  })

  it('rejects a whitespace-only string', () => {
    const result = filterPresetNameSchema.safeParse({ name: '   ' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('Preset name'))
  })

  it('rejects a name shorter than 3 characters after trim', () => {
    const result = filterPresetNameSchema.safeParse({ name: '  ab  ' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(LENGTH.min(3))
  })

  it('rejects a name longer than 50 characters', () => {
    const result = filterPresetNameSchema.safeParse({ name: 'a'.repeat(51) })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(LENGTH.max(50))
  })

  it('trims whitespace before validation', () => {
    const result = filterPresetNameSchema.safeParse({ name: '  hello world  ' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.name).toBe('hello world')
    }
  })

  it('returns correct error for missing name field', () => {
    const result = filterPresetNameSchema.safeParse({})
    expect(result.success).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// cameraPresetNameSchema
// ---------------------------------------------------------------------------

describe('cameraPresetNameSchema', () => {
  it('accepts a valid alphanumeric name', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'my_preset_01' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with only letters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'nightmode' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with exactly 3 characters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'abc' })
    expect(result.success).toBe(true)
  })

  it('accepts a name with exactly 50 characters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'a'.repeat(50) })
    expect(result.success).toBe(true)
  })

  it('rejects an empty string', () => {
    const result = cameraPresetNameSchema.safeParse({ name: '' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(REQUIRED.field('Preset name'))
  })

  it('rejects a name with spaces', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'my preset' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(PRESET.alphanumericOnly)
  })

  it('rejects a name with hyphens', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'my-preset' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(PRESET.alphanumericOnly)
  })

  it('rejects a name with special characters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'preset!' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(PRESET.alphanumericOnly)
  })

  it('rejects a name shorter than 3 characters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'ab' })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(LENGTH.min(3))
  })

  it('rejects a name longer than 50 characters', () => {
    const result = cameraPresetNameSchema.safeParse({ name: 'a'.repeat(51) })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe(LENGTH.max(50))
  })

  it('returns correct error for missing name field', () => {
    const result = cameraPresetNameSchema.safeParse({})
    expect(result.success).toBe(false)
  })
})
