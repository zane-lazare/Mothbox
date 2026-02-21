import { z } from 'zod';

/**
 * Filter preset name schema.
 *
 * Mirrors the validation in SaveFilterPresetModal.jsx (lines 26-37).
 * Any characters allowed (spaces, special chars); whitespace is trimmed
 * before length checks.
 */
export const filterPresetNameSchema = z.object({
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
    .min(1, 'Preset name is required')
    .regex(/^[a-zA-Z0-9_]+$/, 'Name can only contain letters, numbers, and underscores')
    .min(3, 'Name must be at least 3 characters')
    .max(50, 'Name must be less than 50 characters'),
});

export type CameraPresetNameData = z.infer<typeof cameraPresetNameSchema>;
