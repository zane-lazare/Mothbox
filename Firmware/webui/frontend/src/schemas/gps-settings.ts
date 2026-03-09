import { z } from 'zod'
import { REQUIRED, GPS } from '../constants/errorMessages'

export const BAUDRATE_VALUES = [4800, 9600, 19200, 38400, 57600, 115200] as const

const DEVICE_PATH_PATTERN = /^\/dev\/(ttyAMA\d+|ttyACM\d+|ttyS\d+|ttyUSB\d+|ttyO\d+|serial\d+)$/

export const gpsSettingsSchema = z.object({
  enabled: z.boolean(),
  device: z.string()
    .min(1, REQUIRED.field('Device path'))
    .regex(DEVICE_PATH_PATTERN, GPS.invalidPath),
  baudrate: z.coerce.number().refine(
    (v) => (BAUDRATE_VALUES as readonly number[]).includes(v),
    GPS.invalidBaudrate,
  ),
  /** @deprecated Legacy field with no UI control — replaced by adaptive timeouts
   *  (timeout_hot/warm/cold/almanac). Kept only because the backend still
   *  expects gps_timeout in the mutation payload. Remove once backend drops it. */
  timeout: z.coerce.number().min(1),
  timeout_hot: z.coerce.number().min(5, GPS.timeoutMin(5)).max(60, GPS.timeoutMax(60)),
  timeout_warm: z.coerce.number().min(30, GPS.timeoutMin(30)).max(180, GPS.timeoutMax(180)),
  timeout_cold: z.coerce.number().min(60, GPS.timeoutMin(60)).max(300, GPS.timeoutMax(300)),
  timeout_almanac: z.coerce.number().min(300, GPS.timeoutMin(300)).max(1800, GPS.timeoutMax(1800)),
})

export type GpsSettingsFormData = z.infer<typeof gpsSettingsSchema>

export const GPS_SETTINGS_DEFAULTS: GpsSettingsFormData = {
  enabled: false,
  device: '/dev/ttyAMA0',
  baudrate: 9600,
  timeout: 10,
  timeout_hot: 15,
  timeout_warm: 60,
  timeout_cold: 90,
  timeout_almanac: 1200,
}
