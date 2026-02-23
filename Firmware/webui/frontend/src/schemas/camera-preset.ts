import { z } from 'zod'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = z.object({
  name: z.string()
    .trim()
    .min(1, 'Preset name is required')
    .min(3, 'Name must be at least 3 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Name can only contain letters, numbers, and underscores')
    .max(50, 'Name must be 50 characters or less'),
  description: z.string().max(200, 'Description must be 200 characters or less'),
  workflow: z.enum(WORKFLOW_VALUES),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
