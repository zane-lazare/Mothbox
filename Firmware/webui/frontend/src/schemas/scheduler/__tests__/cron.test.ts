import { describe, it, expect } from 'vitest'
import { cronExpressionSchema, CRON_FORMAT_REGEX } from '../cron'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('CRON_FORMAT_REGEX', () => {
  const valid = [
    '* * * * *',
    '0 * * * *',
    '*/5 * * * *',
    '0 21 * * *',
    '0 21 * * 1-5',
    '0,30 * * * *',
    '0 0 1,15 * *',
    '*/15 9-17 * * 1-5',
    '5 4 * * 0',
    '0 0 1 1 *',
  ]

  const invalid = [
    '',
    '*',
    '* *',
    '* * *',
    '* * * *',
    '* * * * * *',       // 6 fields
    'every 5 minutes',
    '@daily',             // special syntax not supported
    '0 21 * * * extra',
  ]

  it.each(valid)('accepts "%s"', (expr) => {
    expect(CRON_FORMAT_REGEX.test(expr)).toBe(true)
  })

  it.each(invalid)('rejects "%s"', (expr) => {
    expect(CRON_FORMAT_REGEX.test(expr)).toBe(false)
  })
})

describe('cronExpressionSchema', () => {
  it('accepts valid cron expression', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: '0 21 * * *',
    })
    expect(result.success).toBe(true)
  })

  it('rejects empty string', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: '',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Cron expression is required')
  })

  it('rejects malformed expression', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: 'not a cron',
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Must be 5 space-separated cron fields')
  })

  it('rejects missing field', () => {
    const result = cronExpressionSchema.safeParse({})
    expect(result.success).toBe(false)
  })

  it('rejects non-string', () => {
    const result = cronExpressionSchema.safeParse({
      cron_expression: 42,
    })
    expect(result.success).toBe(false)
    expect(firstError(result)).toBe('Cron expression must be a string')
  })

  it('accepts all preset expressions', () => {
    const presets = [
      '0 * * * *',
      '*/5 * * * *',
      '*/15 * * * *',
      '0 0 * * *',
      '0 21 * * *',
      '0 21 * * 1-5',
    ]
    for (const expr of presets) {
      const result = cronExpressionSchema.safeParse({ cron_expression: expr })
      expect(result.success).toBe(true)
    }
  })
})
