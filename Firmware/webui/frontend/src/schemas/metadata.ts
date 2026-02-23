import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'
import { speciesSchema } from './species'

/** A single custom field entry (key-value pair for useFieldArray). */
export const customFieldEntrySchema = z.object({
  key: z.string().min(1, 'Field name is required').max(100),
  value: z.string().max(1000),
})

/**
 * Full metadata form schema — used by MetadataPanel's useForm.
 *
 * Composes species.ts fields with tags, notes, and custom fields.
 * Custom fields are stored as {key, value}[] tuples internally
 * and converted to/from Record<string, string> at the API boundary.
 */
export const metadataFormSchema = z.object({
  tags: z.array(z.string().trim().min(1).max(METADATA_VALIDATION.MAX_TAG_LENGTH)),
  ...speciesSchema.shape,
  notes: z.string().max(METADATA_VALIDATION.MAX_NOTES_LENGTH).optional().or(z.literal('')),
  custom: z.array(customFieldEntrySchema).max(100),
})

export type MetadataFormData = z.infer<typeof metadataFormSchema>
export type CustomFieldEntry = z.infer<typeof customFieldEntrySchema>
