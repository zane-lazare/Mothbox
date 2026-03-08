import { describe, it, expect } from 'vitest'
import { speciesSchema, CONFIDENCE_VALUES } from '../species'
import { METADATA_VALIDATION } from '../../constants/config'
import { SPECIES, FORMAT } from '../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('speciesSchema', () => {
  describe('valid data', () => {
    it('accepts all fields populated', () => {
      const result = speciesSchema.safeParse({
        species: 'Manduca sexta',
        commonName: 'Tobacco Hornworm',
        confidence: 'certain',
        referenceUrl: 'https://example.com/species/123',
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimal data (confidence only)', () => {
      const result = speciesSchema.safeParse({ confidence: 'unknown' })
      expect(result.success).toBe(true)
    })

    it('accepts empty strings for optional fields', () => {
      const result = speciesSchema.safeParse({
        species: '',
        commonName: '',
        confidence: 'probable',
        referenceUrl: '',
      })
      expect(result.success).toBe(true)
    })

    it('accepts all confidence values', () => {
      for (const value of CONFIDENCE_VALUES) {
        const result = speciesSchema.safeParse({ confidence: value })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('confidence validation', () => {
    it('rejects invalid confidence value', () => {
      const result = speciesSchema.safeParse({ confidence: 'maybe' })
      expect(result.success).toBe(false)
    })

    it('rejects missing confidence', () => {
      const result = speciesSchema.safeParse({ species: 'Manduca sexta' })
      expect(result.success).toBe(false)
    })
  })

  describe('string length limits', () => {
    it('accepts species at max length', () => {
      const result = speciesSchema.safeParse({
        species: 'a'.repeat(METADATA_VALIDATION.MAX_SPECIES_LENGTH),
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
    })

    it('rejects species exceeding max length', () => {
      const result = speciesSchema.safeParse({
        species: 'a'.repeat(METADATA_VALIDATION.MAX_SPECIES_LENGTH + 1),
        confidence: 'probable',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SPECIES.nameTooLong)
    })

    it('accepts commonName at max length', () => {
      const result = speciesSchema.safeParse({
        commonName: 'a'.repeat(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH),
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
    })

    it('rejects commonName exceeding max length', () => {
      const result = speciesSchema.safeParse({
        commonName: 'a'.repeat(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH + 1),
        confidence: 'probable',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SPECIES.commonNameTooLong)
    })
  })

  describe('whitespace trimming', () => {
    it('trims species whitespace', () => {
      const result = speciesSchema.safeParse({
        species: '  Manduca sexta  ',
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.species).toBe('Manduca sexta')
      }
    })

    it('trims commonName whitespace', () => {
      const result = speciesSchema.safeParse({
        species: 'Manduca sexta',
        commonName: '  Tobacco Hornworm  ',
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.commonName).toBe('Tobacco Hornworm')
      }
    })
  })

  describe('referenceUrl validation', () => {
    it('accepts a valid URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'https://www.inaturalist.org/taxa/12345',
      })
      expect(result.success).toBe(true)
    })

    it('rejects an invalid URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'not-a-url',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(FORMAT.url)
    })

    it('rejects ftp:// URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'ftp://example.com/file',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(FORMAT.url)
    })

    it('rejects file:// URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'file:///etc/passwd',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(FORMAT.url)
    })

    it('accepts http:// URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'http://example.com/species',
      })
      expect(result.success).toBe(true)
    })

    it('rejects URL exceeding max length', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'https://example.com/' + 'a'.repeat(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SPECIES.urlTooLong)
    })
  })
})
