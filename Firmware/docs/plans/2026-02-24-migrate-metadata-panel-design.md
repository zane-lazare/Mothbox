# Migrate MetadataPanel + Children to react-hook-form + Zod

**Issue**: #444
**Date**: 2026-02-24
**Status**: Design approved

## Decision Summary

| Decision | Choice |
|---|---|
| Scope | Full MetadataPanel + all 4 editable children (Species, Tags, Notes, CustomFields) |
| Form ownership | Single `useForm` in MetadataPanel, children receive `control`/`register` |
| Pattern | Pattern 3 (Hybrid prop-synced) from design doc |
| Schema | New `metadata.ts` composing `species.ts` shape + tags + notes + custom fields |
| Custom fields | `{ key, value }[]` tuples via `useFieldArray`, converted to/from `Record<string, string>` at API boundary |
| Tags | `z.array(z.string())` managed via `setValue`/`useWatch` (not `useFieldArray`) |
| URL validation | Add `.refine()` to `species.ts` for http/https enforcement |
| Auto-save | `useWatch({ control })` feeds existing `useAutoSave` hook |

## Schema

New file `src/schemas/metadata.ts`:

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'
import { speciesSchema } from './species'

export const customFieldEntrySchema = z.object({
  key: z.string().min(1, 'Field name is required').max(100),
  value: z.string().max(1000),
})

export const metadataFormSchema = z.object({
  tags: z.array(z.string().trim().min(1).max(METADATA_VALIDATION.MAX_TAG_LENGTH)),
  ...speciesSchema.shape,
  notes: z.string().max(METADATA_VALIDATION.MAX_NOTES_LENGTH).optional().or(z.literal('')),
  custom: z.array(customFieldEntrySchema).max(100),
})

export type MetadataFormData = z.infer<typeof metadataFormSchema>
```

Update `species.ts` referenceUrl with `.refine()`:

```typescript
referenceUrl: z.string()
  .url('Invalid URL')
  .max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH, 'URL is too long')
  .refine((url) => {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  }, { message: 'URL must start with http:// or https://' })
  .optional().or(z.literal(''))
```

## MetadataPanel (Container)

- Replace `editableData` useState with `useForm<MetadataFormData>`
- `reset()` syncs sidecar data on load (with `!isDirty` guard)
- `useWatch({ control })` feeds `useAutoSave`
- `onSave` converts camelCase form data → snake_case API payload
- Custom fields: `Object.entries()` on reset (API → form), `Object.fromEntries()` on save (form → API)
- All `handleSpeciesChange`, `handleTagAdd`, `handleTagRemove`, `handleNotesChange`, `handleCustomFieldsChange` callbacks removed
- Children receive `control`, `register`, `setValue`, `errors` as needed

## Child Components

### MetadataSpecies.tsx

- Props: `control`, `register`, `errors`, `disabled`
- `species`: `Controller` (needed for autocomplete `onMouseDown` → `field.onChange`)
- `commonName`, `referenceUrl`: `register()`
- `confidence`: `register()`
- `useSpecies` autocomplete: local UI state (`showSuggestions`) unchanged
- URL external link icon: reads value via `useWatch({ control, name: 'referenceUrl' })`

### MetadataTags.tsx

- Props: `control`, `setValue`, `disabled`, `onCopyToNext`
- Tags managed via `useWatch({ control, name: 'tags' })` + `setValue('tags', [...], { shouldDirty: true })`
- No `useFieldArray` — tags are `string[]`, add/remove via `setValue`
- Tag input remains local state (staging area before append)
- `useTags` autocomplete: local UI state unchanged

### MetadataNotes.tsx

- Props: `control`, `register`, `setValue`, `disabled`
- `register('notes')` on textarea
- Auto-height: local ref + `useWatch({ control, name: 'notes' })` for value changes
- Timestamp insertion: `setValue('notes', newValue, { shouldDirty: true })`
- Character counter: reads `useWatch` value

### MetadataCustomFields.tsx

- Props: `control`, `disabled`
- `useFieldArray({ control, name: 'custom' })` → `fields`, `append`, `remove`, `update`
- Add: `append({ key: 'field_N', value: '' })`
- Delete: `remove(index)`
- Key change: `update(index, { key: newKey, value: fields[index].value })`
- Duplicate key check: local UI error against `fields` array

## File Changes

| File | Change |
|---|---|
| `schemas/metadata.ts` | **New** — metadata form schema |
| `schemas/species.ts` | Add `.refine()` on referenceUrl |
| `schemas/index.ts` | Add metadata.ts re-export |
| `components/metadata/MetadataPanel.jsx` | → `.tsx`, lift useForm |
| `components/metadata/MetadataSpecies.jsx` | → `.tsx`, receive control/register |
| `components/metadata/MetadataTags.jsx` | → `.tsx`, receive control/setValue |
| `components/metadata/MetadataNotes.jsx` | → `.tsx`, receive control/register/setValue |
| `components/metadata/MetadataCustomFields.jsx` | → `.tsx`, receive control/useFieldArray |
| `__tests__/MetadataSpecies.test.jsx` | → `.test.tsx`, test wrapper with useForm |
| `__tests__/MetadataPanel.test.jsx` | → `.test.tsx`, update assertions |
| `__tests__/MetadataPanel.integration.test.jsx` | → `.test.tsx`, update assertions |
| `__tests__/MetadataPanel.mobile.test.jsx` | → `.test.tsx`, update assertions |

## Unchanged

- `useAutoSave.js` — no changes, watches whatever `data` it receives
- `useSpecies.js`, `useTags.js` — autocomplete hooks
- `AccordionSection`, `SaveStatusIndicator`, `MetadataSkeleton`, `MetadataEXIF`
- Components outside `metadata/` directory

## Test Strategy

Child component tests use a wrapper that provides form context:

```typescript
function renderWithForm(ui: (props: FormProps) => ReactElement, overrides?: Partial<MetadataFormData>) {
  function Wrapper() {
    const form = useForm<MetadataFormData>({
      resolver: zodResolver(metadataFormSchema),
      defaultValues: { tags: [], species: '', commonName: '', confidence: 'unknown', referenceUrl: '', notes: '', custom: [], ...overrides },
    })
    return ui({ control: form.control, register: form.register, setValue: form.setValue, errors: form.formState.errors })
  }
  return render(<Wrapper />, { wrapper: createQueryWrapper() })
}
```

MetadataPanel tests render the full tree as before — main updates are removing assertions on old callback interfaces.
