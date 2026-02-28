# CronExpressionInput Migration Design

**Issue:** #451
**Date:** 2026-02-28
**Pattern:** Thin Typed Wrapper (no internal RHF)

## Goal

Migrate CronExpressionInput from .jsx to .tsx, add a Zod schema for sync format validation, and type the useCronValidation hook with full response interfaces.

## Architecture

The component stays a pure controlled component (`value`/`onChange`/`disabled`) with TypeScript props replacing PropTypes. No internal RHF form — this is a single text input that passes every keystroke to the parent without validation gating.

A Zod schema provides sync format validation for use by parent forms that compose the cron field. The existing `useCronValidation` hook handles async API validation and is migrated to TypeScript with full response typing.

## Files

| File | Action |
|------|--------|
| `src/schemas/scheduler/cron.ts` | Create — Zod schema |
| `src/schemas/scheduler/__tests__/cron.test.ts` | Create — schema tests |
| `src/hooks/useCronValidation.js` → `.ts` | Rename + type |
| `src/hooks/__tests__/useCronValidation.test.js` → `.test.ts` | Rename + type |
| `ExpertMode/CronExpressionInput.jsx` → `.tsx` | Rename + type |
| `ExpertMode/__tests__/CronExpressionInput.test.jsx` → `.test.tsx` | Rename + type |
| `ExpertMode/index.js` | Update barrel export |
| `ExpertMode/constants.js` → `.ts` | Type preset/help objects |

## Zod Schema

Minimal sync validation — 5 space-separated fields, each matching cron token patterns. Does NOT replicate server's full validation (range bounds, day-of-month limits). Catches obviously malformed input before the API call.

```ts
export const cronExpressionSchema = z.object({
  cron_expression: z.string()
    .min(1, 'Cron expression is required')
    .regex(CRON_FORMAT_REGEX, 'Must be 5 space-separated cron fields')
})
```

## Hook Typing

```ts
interface CronValidationResult {
  valid: boolean
  expression: string
  description?: string
  next_executions?: string[]
  error?: string
}

interface UseCronValidationOptions {
  count?: number
  queryOptions?: Partial<UseQueryOptions<CronValidationResult>>
}

export function useCronValidation(
  expression: string,
  options?: UseCronValidationOptions
): UseQueryResult<CronValidationResult> & { errorMessage: string | null }
```

## Component Props

```ts
interface CronExpressionInputProps {
  value?: string
  onChange: (value: string) => void
  disabled?: boolean
}
```

## What This Does NOT Do

- No RHF form internally (single field, no validation gating needed)
- No client-side range validation (server handles via API)
- No changes to parent TriggerForm.jsx (still .jsx, imports stay compatible)
- No changes to CronExpressionErrorBoundary.jsx (separate concern)
