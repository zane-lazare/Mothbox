import { z } from 'zod';
import { REQUIRED, LENGTH, PRESET } from '../constants/errorMessages';

/**
 * Filter preset name schema.
 *
 * Used by SaveFilterPresetModal.tsx and SavePresetModal.tsx (filters) via zodResolver.
 * Any characters allowed (spaces, special chars); whitespace is trimmed
 * before length checks.
 */
export const filterPresetNameSchema = z.object({
  // .min(1) gives "required" message for empty input; .min(3) gives "too short"
  // for 1-2 char input. Both are needed for distinct UX feedback.
  name: z.string()
    .trim()
    .min(1, REQUIRED.field('Preset name'))
    .min(3, LENGTH.min(3))
    .max(50, LENGTH.max(50)),
});

export type FilterPresetNameData = z.infer<typeof filterPresetNameSchema>;

/**
 * Camera preset name schema.
 *
 * Used by the camera SavePresetModal at src/components/SavePresetModal.tsx
 * (distinct from the filters SavePresetModal at src/components/filters/).
 * Only letters, numbers, and underscores are allowed.
 */
export const cameraPresetNameSchema = z.object({
  name: z.string()
    .trim()
    .min(1, REQUIRED.field('Preset name'))
    .min(3, LENGTH.min(3))
    .regex(/^[a-zA-Z0-9_]+$/, PRESET.alphanumericOnly)
    .max(50, LENGTH.max(50)),
});

export type CameraPresetNameData = z.infer<typeof cameraPresetNameSchema>;
