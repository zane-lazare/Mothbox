import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'

/**
 * Confidence levels for species identification.
 * Matches SPECIES_CONFIG.CONFIDENCE_OPTIONS values in config.js.
 */
export const CONFIDENCE_VALUES = ['certain', 'probable', 'possible', 'unknown'] as const

/**
 * Species identification schema.
 *
 * Used by BulkSpeciesModal.tsx (Phase 1) and MetadataSpecies (Phase 2).
 * All fields are optional at the schema level — individual components
 * enforce "required" via submit-button disable logic as appropriate.
 */
export const speciesSchema = z.object({
  species: z.string().trim().max(METADATA_VALIDATION.MAX_SPECIES_LENGTH, 'Species name is too long').optional().or(z.literal('')),
  commonName: z.string().trim().max(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH, 'Common name is too long').optional().or(z.literal('')),
  confidence: z.enum(CONFIDENCE_VALUES),
  referenceUrl: z.string()
    .max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH, 'URL is too long')
    .refine((val) => {
      if (!val) return true
      try {
        const parsed = new URL(val)
        return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      } catch {
        return false
      }
    }, { message: 'URL must start with http:// or https://' })
    .optional()
    .or(z.literal('')),
})

export type SpeciesFormData = z.infer<typeof speciesSchema>
