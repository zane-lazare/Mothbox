import { z } from 'zod';

/**
 * Filter preset name schema.
 *
 * Used by SaveFilterPresetModal.tsx via zodResolver.
 * Any characters allowed (spaces, special chars); whitespace is trimmed
 * before length checks.
 */
export const filterPresetNameSchema = z.object({
  // .min(1) gives "required" message for empty input; .min(3) gives "too short"
  // for 1-2 char input. Both are needed for distinct UX feedback.
  name: z.string()
    .trim()
    .min(1, 'Preset name is required')
    .min(3, 'Name must be at least 3 characters')
    .max(50, 'Name must be less than 50 characters'),
});

export type FilterPresetNameData = z.infer<typeof filterPresetNameSchema>;

/**
 * Camera preset name schema.
 *
 * Mirrors the validation in SavePresetModal.jsx (lines 21-35).
 * Only letters, numbers, and underscores are allowed.
 */
export const cameraPresetNameSchema = z.object({
  name: z.string()
    .trim()
    .min(1, 'Preset name is required')
    .min(3, 'Name must be at least 3 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Name can only contain letters, numbers, and underscores')
    .max(50, 'Name must be less than 50 characters'),
});

export type CameraPresetNameData = z.infer<typeof cameraPresetNameSchema>;
