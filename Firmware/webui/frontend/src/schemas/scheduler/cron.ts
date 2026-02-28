import { z } from 'zod'

/**
 * Regex matching a single cron field token.
 * Allows: *, N, N-M, N,M,... , *​/N, N-M/N, and combinations.
 * Does NOT validate numeric ranges (server handles that).
 */
const CRON_FIELD = String.raw`(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?(?:,(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?)*`

/**
 * Regex matching a 5-field cron expression (minute hour day month weekday).
 * Exported for direct use in tests and parent schemas.
 */
// Note: \s+ intentionally allows any whitespace (tabs, multiple spaces).
// */0 is accepted by the regex (semantically invalid step value).
// Both are by design — this is a format check only; the server validates semantics.
export const CRON_FORMAT_REGEX = new RegExp(
  `^${CRON_FIELD}(?:\\s+${CRON_FIELD}){4}$`,
)

/**
 * Schema for a cron expression field.
 * Sync format validation only — full semantic validation (range checks,
 * day-of-month limits) is handled by the server via useCronValidation.
 */
export const cronExpressionSchema = z.object({
  cron_expression: z
    .string({ error: 'Cron expression must be a string' })
    .min(1, 'Cron expression is required')
    .regex(CRON_FORMAT_REGEX, 'Must be 5 space-separated cron fields'),
})

export type CronExpressionFormData = z.infer<typeof cronExpressionSchema>
