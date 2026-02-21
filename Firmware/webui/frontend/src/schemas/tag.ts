import { z } from 'zod';

/**
 * Tag mode options for bulk tag operations.
 */
export const TAG_MODES = ['add', 'replace', 'remove'] as const;

/**
 * Bulk tag form schema.
 *
 * Used by BulkTagModal.tsx via zodResolver. Tags are stored as
 * { value: string } objects because useFieldArray requires object elements.
 * The component maps these back to string[] when calling onApply.
 */
export const bulkTagSchema = z.object({
  tags: z.array(
    z.object({ value: z.string().trim().min(1, 'Tag cannot be empty') })
  ).min(1, 'At least one tag is required'),
  mode: z.enum(TAG_MODES),
});

export type BulkTagFormData = z.infer<typeof bulkTagSchema>;
