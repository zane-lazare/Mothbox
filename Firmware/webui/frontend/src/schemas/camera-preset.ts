import { z } from 'zod'
import { cameraPresetNameSchema } from './preset'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = cameraPresetNameSchema.extend({
  description: z.string().max(200, 'Description must be 200 characters or less'),
  workflow: z.enum(WORKFLOW_VALUES),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
