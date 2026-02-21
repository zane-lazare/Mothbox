# BulkTagModal Migration to react-hook-form + Zod

**Issue**: #440
**Parent**: #197 (Form Validation Standardization)
**Date**: 2026-02-22
**Status**: Design approved

## Decision Summary

| Decision | Choice |
|---|---|
| Form pattern | Modal (uncontrolled) — Pattern 1 from design doc |
| Tag array management | `useFieldArray` from react-hook-form |
| Text input state | Local `useState` (transient typing, not form data) |
| Autocomplete | `useTags` hook unchanged (read-only data) |
| Validation mode | `onBlur` default (tags validated on submit via Zod) |
| Schema file | `src/schemas/tag.ts` (new) |

## Schema (`src/schemas/tag.ts`)

`useFieldArray` requires object elements, so each tag is `{ value: string }`:

```typescript
import { z } from 'zod'

export const TAG_MODES = ['add', 'replace', 'remove'] as const

export const bulkTagSchema = z.object({
  tags: z.array(
    z.object({ value: z.string().trim().min(1, 'Tag cannot be empty') })
  ).min(1, 'At least one tag is required'),
  mode: z.enum(TAG_MODES),
})

export type BulkTagFormData = z.infer<typeof bulkTagSchema>
```

The `onApply` callback maps `{ value: string }[]` back to `string[]`:

```typescript
const onSubmit = (data: BulkTagFormData) => {
  onApply({ tags: data.tags.map(t => t.value), mode: data.mode })
}
```

Duplicate prevention stays as UI logic in `handleAddTag` (case-insensitive dedup on the current set, not a schema concern).

## Component Structure

Three react-hook-form hooks:

- **`useForm<BulkTagFormData>`** — owns tags array + mode, validates with zodResolver
- **`useFieldArray`** — `append`/`remove` for the tags array
- **Local `useState`** — `inputValue` and `showSuggestions` (transient)

### Behavioral Mapping

| Current (useState) | Migrated (react-hook-form) |
|---|---|
| `setMode('add')` | `register('mode')` on radio inputs |
| `setTags([...tags, trimmed])` | `append({ value: trimmed })` |
| `tags.filter(t => t !== tag)` | `remove(index)` |
| `tags.length === 0` disables Apply | `!isValid` from formState |
| `if (!isOpen) reset state` | `reset()` in useEffect on `isOpen` |
| `handleApply` calls `onApply` | `handleSubmit(onSubmit)` maps and calls parent |

### Unchanged

- `inputValue` / `showSuggestions` — transient typing state
- `blurTimeoutRef` — blur timing for suggestion dropdown
- `useTags` hook — read-only autocomplete data
- Modal chrome (portal, backdrop, escape key, all styling)

The `<form>` element wraps modal content. Apply becomes `type="submit"`.

## Testing Strategy

### Schema Tests (`src/schemas/__tests__/tag.test.ts`)

Pure unit tests, no React:
- Valid data passes (tags + mode)
- Empty tags array rejected
- Empty string tag rejected
- Invalid mode rejected
- Whitespace-only tags rejected (trim + min 1)

### Component Tests (`BulkTagModal.test.tsx`)

Migrate existing 26 tests. Most stay nearly identical since they interact via `userEvent`:

- `.test.jsx` → `.test.tsx`
- Import from `BulkTagModal.tsx`
- Props typed with TypeScript interface
- Apply disabled logic now driven by `formState.isValid` (same observable behavior)

One test added: submit with no tags shows Zod validation error.

## Files Changed

| File | Action |
|---|---|
| `src/schemas/tag.ts` | Create — Zod schema + types |
| `src/schemas/__tests__/tag.test.ts` | Create — Schema unit tests |
| `src/schemas/index.ts` | Edit — Add re-exports |
| `src/components/gallery/BulkTagModal.jsx` | Delete |
| `src/components/gallery/BulkTagModal.tsx` | Create — Migrated component |
| `src/components/gallery/__tests__/BulkTagModal.test.jsx` | Delete |
| `src/components/gallery/__tests__/BulkTagModal.test.tsx` | Create — Migrated tests |

No changes to parent components — `onApply({ tags: string[], mode })` contract preserved.
