import { z } from 'zod'

/** A key-value pair for useFieldArray (environmental or custom fields). */
export const deploymentFieldEntrySchema = z.object({
  key: z.string(),
  value: z.string(),
})

export const deploymentSchema = z.object({
  deployment_name: z.string()
    .min(1, 'Deployment name is required')
    .max(200, 'Must be 200 characters or less'),
  location_name: z.string().max(500, 'Must be 500 characters or less').optional().or(z.literal('')),
  latitude: z.number().min(-90, 'Must be between -90 and 90').max(90, 'Must be between -90 and 90').nullable(),
  longitude: z.number().min(-180, 'Must be between -180 and 180').max(180, 'Must be between -180 and 180').nullable(),
  altitude: z.coerce.number().nullable(),
  start_date: z.string().optional().or(z.literal('')),
  end_date: z.string().optional().or(z.literal('')),
  environmental: z.array(deploymentFieldEntrySchema),
  custom: z.array(deploymentFieldEntrySchema).max(50, 'Maximum 50 custom fields'),
  mothbox_id: z.string().optional().or(z.literal('')),
  firmware_version: z.string().optional().or(z.literal('')),
}).refine(
  (d) => {
    if (!d.start_date || !d.end_date) return true
    return d.start_date <= d.end_date
  },
  { message: 'End date must be on or after start date', path: ['end_date'] }
)

export type DeploymentFormData = z.infer<typeof deploymentSchema>

export const DEPLOYMENT_DEFAULTS: DeploymentFormData = {
  deployment_name: '',
  location_name: '',
  latitude: null,
  longitude: null,
  altitude: null,
  start_date: '',
  end_date: '',
  environmental: [],
  custom: [],
  mothbox_id: '',
  firmware_version: '',
}
