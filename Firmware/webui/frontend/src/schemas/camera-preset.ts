import { z } from 'zod'
import { LENGTH } from '../constants/errorMessages'
import { cameraPresetNameSchema } from './preset'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = cameraPresetNameSchema.extend({
  description: z.string().max(200, LENGTH.max(200)),
  workflow: z.enum(WORKFLOW_VALUES),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
