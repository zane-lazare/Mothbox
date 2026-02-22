import { z } from 'zod'
import { getGpsPrecision } from '../utils/gpsPrecision'

export const FORMAT_VALUES = ['darwin_core', 'inaturalist', 'json', 'csv'] as const

export const DELIMITER_VALUES = [',', '\t', ';'] as const

const gpsPrecision = z.number().int().min(0).max(6)

const darwinCoreSchema = z.strictObject({
  format: z.literal('darwin_core'),
  gps_precision: gpsPrecision,
  validate: z.boolean(),
  include_warnings: z.boolean(),
})

const inaturalistSchema = z.strictObject({
  format: z.literal('inaturalist'),
  gps_precision: gpsPrecision,
  include_xmp_sidecars: z.boolean(),
  include_manifest: z.boolean(),
  include_csv_summary: z.boolean(),
})

const jsonSchema = z.strictObject({
  format: z.literal('json'),
  gps_precision: gpsPrecision,
  pretty_print: z.boolean(),
  include_raw_exif: z.boolean(),
})

const csvSchema = z.strictObject({
  format: z.literal('csv'),
  gps_precision: gpsPrecision,
  include_bom: z.boolean(),
  delimiter: z.enum(DELIMITER_VALUES),
})

export const exportOptionsSchema = z.discriminatedUnion('format', [
  darwinCoreSchema,
  inaturalistSchema,
  jsonSchema,
  csvSchema,
])

export type ExportOptionsFormData = z.infer<typeof exportOptionsSchema>

/** Per-format default values for form reset. */
export const EXPORT_DEFAULTS: Record<typeof FORMAT_VALUES[number], ExportOptionsFormData> = {
  darwin_core: {
    format: 'darwin_core',
    gps_precision: 2,
    validate: false,
    include_warnings: false,
  },
  inaturalist: {
    format: 'inaturalist',
    gps_precision: 2,
    include_xmp_sidecars: true,
    include_manifest: true,
    include_csv_summary: false,
  },
  json: {
    format: 'json',
    gps_precision: 2,
    pretty_print: true,
    include_raw_exif: false,
  },
  csv: {
    format: 'csv',
    gps_precision: 2,
    include_bom: true,
    delimiter: ',',
  },
}

/**
 * Build default values for a given format, using the user's stored GPS precision.
 * Call this at form initialization or when format changes to pick up localStorage.
 */
export function getExportDefaults(format: typeof FORMAT_VALUES[number]): ExportOptionsFormData {
  return { ...EXPORT_DEFAULTS[format], gps_precision: getGpsPrecision() }
}
