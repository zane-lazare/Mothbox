import { z } from 'zod'
import { COORDINATES } from '../constants/errorMessages'

export const coordinatesSchema = z.object({
  latitude: z.number()
    .min(-90, COORDINATES.latitude)
    .max(90, COORDINATES.latitude)
    .nullable(),
  longitude: z.number()
    .min(-180, COORDINATES.longitude)
    .max(180, COORDINATES.longitude)
    .nullable(),
})

export type CoordinatesFormData = z.infer<typeof coordinatesSchema>
