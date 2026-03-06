/**
 * Liveview settings validation schema.
 *
 * Mirrors backend ALLOWED_LIVEVIEW_SETTINGS from webui/backend/utils.py.
 * Replaces the imperative validators in utils/presetValidation.ts with Zod.
 *
 * All fields are optional because consumers validate partial settings objects
 * (only the keys present in the current preset/form). Unknown keys pass through.
 */
import { z } from 'zod'
import { toBackendKey } from '../utils/cameraControlMapping'

// ---------------------------------------------------------------------------
// Helpers — coerce string-encoded values from backend CSV storage
// ---------------------------------------------------------------------------

/**
 * Accept boolean or string "true"/"false" (case-insensitive).
 * Intentionally does NOT coerce to boolean — backend expects string "true"/"false"
 * from CSV storage, and consumers pass through without transformation.
 */
const booleanish = z.union([
  z.boolean(),
  z.string().refine(
    (v) => v.toLowerCase() === 'true' || v.toLowerCase() === 'false',
    { message: 'Must be "true" or "false"' },
  ),
])

/** Accept number or string-encoded integer, then validate against allowed values. */
const intEnum = (allowed: number[], label: string) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseInt(v, 10) : v),
    z.number({ message: `${label} must be a number` })
      .int(`${label} must be an integer`)
      .refine((n) => allowed.includes(n), {
        message: `${label} must be one of: ${allowed.join(', ')}`,
      }),
  )

/** Accept number or string-encoded float, then validate range. */
const floatRange = (min: number, max: number, label: string) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseFloat(v) : v),
    z.number({ message: `${label} must be a number` })
      .min(min, `${label} must be at least ${min}`)
      .max(max, `${label} must be at most ${max}`),
  )

/** Accept number or string-encoded integer, then validate range. */
const intRange = (min: number, max: number, label: string, { minExclusive = false } = {}) =>
  z.preprocess(
    (v) => (typeof v === 'string' ? parseInt(v, 10) : v),
    z.number({ message: `${label} must be a number` })
      .int(`${label} must be a whole number`)
      .refine((n) => (minExclusive ? n > min : n >= min), {
        message: `${label} must be ${minExclusive ? 'greater than' : 'at least'} ${min}`,
      })
      .max(max, `${label} must be at most ${max}`),
  )

const stringEnum = (allowed: string[], label: string) =>
  z.string().refine(
    (v) => allowed.includes(v.toLowerCase()),
    { message: `${label} must be one of: ${allowed.join(', ')}` },
  )

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

export const liveviewSettingsSchema = z.object({
  // Boolean controls
  focus_peaking_enabled: booleanish.optional(),
  awb_enable: booleanish.optional(),
  ae_enable: booleanish.optional(),
  lens_shading_enable: booleanish.optional(),
  defect_correction_enable: booleanish.optional(),
  use_custom_tuning: booleanish.optional(),

  // Integer enum controls
  af_mode: intEnum([0, 1, 2], 'AF mode').optional(),
  af_speed: intEnum([0, 1], 'AF speed').optional(),
  af_range: intEnum([0, 1, 2], 'AF range').optional(),
  awb_mode: intEnum([0, 1, 2, 3, 4, 5, 6, 7], 'AWB mode').optional(),
  noise_reduction_mode: intEnum([0, 1, 2], 'Noise reduction mode').optional(),
  ae_metering_mode: intEnum([0, 1, 2], 'AE metering mode').optional(),

  // Float range controls
  sharpness: floatRange(0.0, 4.0, 'Sharpness').optional(),
  brightness: floatRange(-1.0, 1.0, 'Brightness').optional(),
  contrast: floatRange(0.0, 4.0, 'Contrast').optional(),
  saturation: floatRange(0.0, 4.0, 'Saturation').optional(),
  lens_position: floatRange(0.0, 10.0, 'Lens position').optional(),
  exposure_value: floatRange(-8.0, 8.0, 'Exposure value').optional(),
  analogue_gain: floatRange(1.0, 16.0, 'Analogue gain').optional(),
  colour_gains_red: floatRange(1.0, 4.0, 'Red colour gain').optional(),
  colour_gains_blue: floatRange(1.0, 4.0, 'Blue colour gain').optional(),

  // Integer range controls
  exposure_time: intRange(0, 999999, 'Exposure time', { minExclusive: true }).optional(),
  focus_peaking_intensity: intRange(50, 200, 'Focus peaking intensity').optional(),

  // String enum controls
  // British and American spelling variants — both accepted by backend
  focus_peaking_colour: stringEnum(['green', 'red', 'yellow', 'cyan', 'magenta'], 'Focus peaking colour').optional(),
  focus_peaking_color: stringEnum(['green', 'red', 'yellow', 'cyan', 'magenta'], 'Focus peaking color').optional(),
  focus_peaking_algorithm: stringEnum(['laplacian', 'sobel', 'canny'], 'Focus peaking algorithm').optional(),
}).passthrough()

export type LiveviewSettingsData = z.infer<typeof liveviewSettingsSchema>

// ---------------------------------------------------------------------------
// Compatibility wrappers — drop-in replacements for presetValidation.ts API
// ---------------------------------------------------------------------------

export interface LiveviewValidationError {
  key: string
  value: unknown
  message: string
}

/**
 * Validate a settings object. Converts camelCase keys to snake_case before
 * checking. Returns an array of per-field errors (empty if valid).
 *
 * Drop-in replacement for `validatePresetSettings` from presetValidation.ts.
 */
export function validateLiveviewSettings(
  settings: Record<string, unknown>,
): LiveviewValidationError[] {
  // Convert camelCase keys to snake_case
  const converted: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(settings)) {
    converted[toBackendKey(key)] = value
  }

  const result = liveviewSettingsSchema.safeParse(converted)
  if (result.success) return []

  return result.error.issues.map((issue) => ({
    key: String(issue.path[0] ?? ''),
    value: converted[String(issue.path[0] ?? '')] ?? null,
    message: issue.message,
  }))
}

/**
 * Format validation errors into a user-friendly message.
 *
 * Drop-in replacement for `formatValidationErrors` from presetValidation.ts.
 */
export function formatLiveviewValidationErrors(
  errors: LiveviewValidationError[],
  maxErrors = 5,
): string {
  if (errors.length === 0) return ''

  const count = errors.length
  const shown = errors.slice(0, maxErrors)

  let msg = `Invalid preset settings (${count} error${count > 1 ? 's' : ''}):\n\n`
  shown.forEach((e, i) => {
    msg += `${i + 1}. ${e.key} = ${e.value}\n   ${e.message}\n`
  })

  if (count > maxErrors) {
    msg += `\n... and ${count - maxErrors} more error${count - maxErrors > 1 ? 's' : ''}`
  }

  return msg.trim()
}
