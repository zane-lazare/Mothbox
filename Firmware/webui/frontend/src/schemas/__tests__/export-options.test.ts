import { describe, it, expect } from 'vitest'
import {
  exportOptionsSchema,
  FORMAT_VALUES,
  DELIMITER_VALUES,
  EXPORT_DEFAULTS,
} from '../export-options'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('exportOptionsSchema', () => {
  describe('FORMAT_VALUES constant', () => {
    it('contains all four export formats', () => {
      expect(FORMAT_VALUES).toEqual(['darwin_core', 'inaturalist', 'json', 'csv'])
    })
  })

  describe('DELIMITER_VALUES constant', () => {
    it('contains comma, tab, semicolon', () => {
      expect(DELIMITER_VALUES).toEqual([',', '\t', ';'])
    })
  })

  describe('darwin_core format', () => {
    it('accepts valid darwin_core options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        validate: true,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects darwin_core with missing validate field', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects darwin_core with csv-specific field', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2,
        validate: true,
        include_warnings: false,
        delimiter: ',',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('inaturalist format', () => {
    it('accepts valid inaturalist options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'inaturalist',
        gps_precision: 3,
        include_xmp_sidecars: true,
        include_manifest: true,
        include_csv_summary: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects inaturalist with missing include_xmp_sidecars', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'inaturalist',
        gps_precision: 3,
        include_manifest: true,
        include_csv_summary: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('json format', () => {
    it('accepts valid json options', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'json',
        gps_precision: 2,
        pretty_print: true,
        include_raw_exif: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects json with missing pretty_print', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'json',
        gps_precision: 2,
        include_raw_exif: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('csv format', () => {
    it('accepts valid csv options with comma delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ',',
      })
      expect(result.success).toBe(true)
    })

    it('accepts tab delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: '\t',
      })
      expect(result.success).toBe(true)
    })

    it('accepts semicolon delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ';',
      })
      expect(result.success).toBe(true)
    })

    it('rejects invalid delimiter', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: '|',
      })
      expect(result.success).toBe(false)
    })
  })

  describe('gps_precision validation', () => {
    it('accepts gps_precision 0', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 0,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('accepts gps_precision 6', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 6,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(true)
    })

    it('rejects gps_precision below 0', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: -1,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects gps_precision above 6', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 7,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })

    it('rejects non-integer gps_precision', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'darwin_core',
        gps_precision: 2.5,
        validate: false,
        include_warnings: false,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('discriminated union', () => {
    it('rejects unknown format', () => {
      const result = exportOptionsSchema.safeParse({
        format: 'xml',
        gps_precision: 2,
      })
      expect(result.success).toBe(false)
    })

    it('rejects missing format', () => {
      const result = exportOptionsSchema.safeParse({
        gps_precision: 2,
      })
      expect(result.success).toBe(false)
    })
  })

  describe('EXPORT_DEFAULTS', () => {
    it('provides defaults for all four formats', () => {
      expect(EXPORT_DEFAULTS).toHaveProperty('darwin_core')
      expect(EXPORT_DEFAULTS).toHaveProperty('inaturalist')
      expect(EXPORT_DEFAULTS).toHaveProperty('json')
      expect(EXPORT_DEFAULTS).toHaveProperty('csv')
    })

    it('all defaults pass schema validation', () => {
      for (const format of FORMAT_VALUES) {
        const result = exportOptionsSchema.safeParse(EXPORT_DEFAULTS[format])
        expect(result.success).toBe(true)
      }
    })

    it('darwin_core defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.darwin_core).toEqual({
        format: 'darwin_core',
        gps_precision: 2,
        validate: false,
        include_warnings: false,
      })
    })

    it('inaturalist defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.inaturalist).toEqual({
        format: 'inaturalist',
        gps_precision: 2,
        include_xmp_sidecars: true,
        include_manifest: true,
        include_csv_summary: false,
      })
    })

    it('json defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.json).toEqual({
        format: 'json',
        gps_precision: 2,
        pretty_print: true,
        include_raw_exif: false,
      })
    })

    it('csv defaults match current component behavior', () => {
      expect(EXPORT_DEFAULTS.csv).toEqual({
        format: 'csv',
        gps_precision: 2,
        include_bom: true,
        delimiter: ',',
      })
    })
  })
})
