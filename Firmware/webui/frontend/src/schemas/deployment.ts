import { z } from 'zod'
import { REQUIRED, LENGTH, COORDINATES, DEPLOYMENT as DEPLOYMENT_MSGS } from '../constants/errorMessages'

/** Optional string that also accepts empty string (common for HTML inputs). */
const optionalStr = (max?: number) => {
  const base = z.string()
  return (max ? base.max(max, LENGTH.max(max)) : base).optional().or(z.literal(''))
}

/** A key-value pair for useFieldArray (environmental or custom fields). */
export const deploymentFieldEntrySchema = z.object({
  key: z.string(),
  value: z.string(),
})

export const deploymentSchema = z.object({
  deployment_name: z.string()
    .min(1, REQUIRED.field('Deployment name'))
    .max(200, LENGTH.max(200)),
  location_name: optionalStr(500),
  latitude: z.number().min(-90, COORDINATES.latitude).max(90, COORDINATES.latitude).nullable(),
  longitude: z.number().min(-180, COORDINATES.longitude).max(180, COORDINATES.longitude).nullable(),
  // z.coerce.number() converts "" to 0; preprocess intercepts empty input → null.
  // Belt-and-suspenders with setValueAs on the register() call in DeploymentEditor.
  altitude: z.preprocess(
    (v) => (v === '' || v === null || v === undefined) ? null : v,
    z.coerce.number().nullable(),
  ),
  start_date: optionalStr(),
  end_date: optionalStr(),
  environmental: z.array(deploymentFieldEntrySchema),
  custom: z.array(deploymentFieldEntrySchema).max(50, DEPLOYMENT_MSGS.maxCustomFields(50)),
  mothbox_id: optionalStr(),
  firmware_version: optionalStr(),
}).refine(
  (d) => {
    if (!d.start_date || !d.end_date) return true
    return d.start_date <= d.end_date
  },
  { message: DEPLOYMENT_MSGS.endBeforeStart, path: ['end_date'] }
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
