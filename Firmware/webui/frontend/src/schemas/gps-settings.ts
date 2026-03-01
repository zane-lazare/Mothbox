import { z } from 'zod'

export const BAUDRATE_VALUES = [4800, 9600, 19200, 38400, 57600, 115200] as const

const DEVICE_PATH_PATTERN = /^\/dev\/(ttyAMA\d+|ttyS\d+|ttyUSB\d+|serial\d+)$/

export const gpsSettingsSchema = z.object({
  enabled: z.boolean(),
  device: z.string()
    .min(1, 'Device path is required')
    .regex(DEVICE_PATH_PATTERN, 'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.'),
  baudrate: z.coerce.number().refine(
    (v) => (BAUDRATE_VALUES as readonly number[]).includes(v),
    'Invalid baudrate',
  ),
  // Legacy field: no UI control, replaced by adaptive timeouts. Kept because
  // the backend still expects gps_timeout in the mutation payload.
  timeout: z.coerce.number(),
  timeout_hot: z.coerce.number().min(5, 'Must be at least 5s').max(60, 'Cannot exceed 60s'),
  timeout_warm: z.coerce.number().min(30, 'Must be at least 30s').max(180, 'Cannot exceed 180s'),
  timeout_cold: z.coerce.number().min(60, 'Must be at least 60s').max(300, 'Cannot exceed 300s'),
  timeout_almanac: z.coerce.number().min(300, 'Must be at least 300s').max(1800, 'Cannot exceed 1800s'),
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
