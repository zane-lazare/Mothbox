import { z } from 'zod';
import { TAG } from '../constants/errorMessages';

/**
 * Tag mode options for bulk tag operations.
 */
export const TAG_MODES = ['add', 'replace', 'remove'] as const;

/** Maximum characters per tag name. Shared by schema and UI guards. */
export const TAG_MAX_LENGTH = 100;

/** Maximum number of tags per operation. Shared by schema and UI guards. */
export const TAG_MAX_COUNT = 50;

/**
 * Bulk tag form schema.
 *
 * Used by BulkTagModal.tsx via zodResolver. Tags are stored as
 * { value: string } objects because useFieldArray requires object elements.
 * The component maps these back to string[] when calling onApply.
 */
export const bulkTagSchema = z.object({
  tags: z.array(
    z.object({ value: z.string().trim().min(1, TAG.empty).max(TAG_MAX_LENGTH, TAG.tooLong) })
  ).min(1, TAG.minRequired).max(TAG_MAX_COUNT, TAG.tooMany),
  mode: z.enum(TAG_MODES),
});

export type BulkTagFormData = z.infer<typeof bulkTagSchema>;
