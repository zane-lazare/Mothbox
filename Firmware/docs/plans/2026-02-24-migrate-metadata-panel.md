# MetadataPanel + Children Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate MetadataPanel and its 4 editable children (MetadataSpecies, MetadataTags, MetadataNotes, MetadataCustomFields) from useState/prop-types to react-hook-form + Zod + TypeScript.

**Architecture:** Single `useForm` in MetadataPanel owns all editable state. Children receive `control`/`register`/`setValue` and render form fields. `useWatch` feeds the existing `useAutoSave` hook. Custom fields use `useFieldArray` with `{ key, value }` tuples, converted to/from `Record<string, string>` at the API boundary.

**Tech Stack:** react-hook-form, Zod, @hookform/resolvers, TypeScript, Vitest, React Testing Library

**Design doc:** `docs/plans/2026-02-24-migrate-metadata-panel-design.md`

---

## Task 1: Schema — Update species.ts and create metadata.ts

**Files:**
- Modify: `webui/frontend/src/schemas/species.ts`
- Create: `webui/frontend/src/schemas/metadata.ts`
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Update species.ts referenceUrl with .refine()**

In `webui/frontend/src/schemas/species.ts`, replace the `referenceUrl` field:

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'

export const CONFIDENCE_VALUES = ['certain', 'probable', 'possible', 'unknown'] as const

export const speciesSchema = z.object({
  species: z.string().trim().max(METADATA_VALIDATION.MAX_SPECIES_LENGTH, 'Species name is too long').optional().or(z.literal('')),
  commonName: z.string().trim().max(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH, 'Common name is too long').optional().or(z.literal('')),
  confidence: z.enum(CONFIDENCE_VALUES),
  referenceUrl: z.string()
    .max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH, 'URL is too long')
    .refine((val) => {
      if (!val) return true
      try {
        const parsed = new URL(val)
        return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      } catch {
        return false
      }
    }, { message: 'URL must start with http:// or https://' })
    .optional()
    .or(z.literal('')),
})

export type SpeciesFormData = z.infer<typeof speciesSchema>
```

Note: We replace `.url()` with `.refine()` because `.url()` accepts any protocol (ftp://, file://, data:) and we need http/https only. The `.refine()` also handles the "invalid URL format" case via the try/catch.

**Step 2: Create metadata.ts**

Create `webui/frontend/src/schemas/metadata.ts`:

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'
import { speciesSchema } from './species'

/** A single custom field entry (key-value pair for useFieldArray). */
export const customFieldEntrySchema = z.object({
  key: z.string().min(1, 'Field name is required').max(100),
  value: z.string().max(1000),
})

/**
 * Full metadata form schema — used by MetadataPanel's useForm.
 *
 * Composes species.ts fields with tags, notes, and custom fields.
 * Custom fields are stored as {key, value}[] tuples internally
 * and converted to/from Record<string, string> at the API boundary.
 */
export const metadataFormSchema = z.object({
  tags: z.array(z.string().trim().min(1).max(METADATA_VALIDATION.MAX_TAG_LENGTH)),
  ...speciesSchema.shape,
  notes: z.string().max(METADATA_VALIDATION.MAX_NOTES_LENGTH).optional().or(z.literal('')),
  custom: z.array(customFieldEntrySchema).max(100),
})

export type MetadataFormData = z.infer<typeof metadataFormSchema>
export type CustomFieldEntry = z.infer<typeof customFieldEntrySchema>
```

**Step 3: Update schemas/index.ts**

Add re-exports for metadata.ts:

```typescript
export { metadataFormSchema, customFieldEntrySchema } from './metadata';
export type { MetadataFormData, CustomFieldEntry } from './metadata';
```

**Step 4: Run existing tests to verify no regressions**

Run: `cd webui/frontend && npx vitest run src/schemas/ --reporter=verbose`
Expected: All existing schema tests pass. The `.refine()` change on referenceUrl should not break BulkSpeciesModal since that modal does not display the referenceUrl field.

Also run: `cd webui/frontend && npx vitest run src/components/gallery/__tests__/BulkSpeciesModal --reporter=verbose`
Expected: PASS — BulkSpeciesModal doesn't use referenceUrl.

**Step 5: Commit**

```bash
git add webui/frontend/src/schemas/species.ts webui/frontend/src/schemas/metadata.ts webui/frontend/src/schemas/index.ts
git commit -m "feat(#444): add metadata form schema, enforce http/https on referenceUrl"
```

---

## Task 2: Migrate MetadataSpecies

**Files:**
- Rename: `webui/frontend/src/components/metadata/MetadataSpecies.jsx` → `.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataSpecies.test.jsx` → `.test.tsx`

**Step 1: Write MetadataSpecies.tsx**

Replace the full file. Key changes from the original:
- Props change from `{ species, confidence, commonName, referenceUrl, onChange, disabled }` to `{ control, register, errors, disabled }`
- `useState` for `inputValue`/`urlInputValue`/`urlError` removed — form owns state
- `useEffect` prop sync removed — parent `reset()` handles this
- Species field uses `Controller` for autocomplete integration
- Other fields use `register()`
- URL external link reads value via `useWatch`
- `showSuggestions` remains as local UI state

```tsx
import { useState, useMemo, useCallback } from 'react'
import { Controller, useWatch } from 'react-hook-form'
import type { Control, UseFormRegister, FieldErrors } from 'react-hook-form'
import { MagnifyingGlassIcon, LinkIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import useSpecies from '../../hooks/useSpecies'
import { METADATA_VALIDATION, SPECIES_CONFIG, Z_INDEX } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataSpeciesProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  errors: FieldErrors<MetadataFormData>
  disabled?: boolean
}

export default function MetadataSpecies({
  control,
  register,
  errors,
  disabled = false,
}: MetadataSpeciesProps) {
  const [showSuggestions, setShowSuggestions] = useState(false)

  const { species: speciesData } = useSpecies({ sort: 'count', order: 'desc', limit: 20 })

  // Read current species value for filtering suggestions
  const speciesValue = useWatch({ control, name: 'species' }) ?? ''
  const referenceUrlValue = useWatch({ control, name: 'referenceUrl' }) ?? ''

  const suggestions = useMemo(() =>
    speciesData
      ?.filter(s => s.name.toLowerCase().includes(speciesValue.toLowerCase()))
      ?.slice(0, 5) || []
  , [speciesData, speciesValue])

  return (
    <div className="space-y-3">
      {/* Species Name with Autocomplete */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Scientific Name
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="w-4 h-4 text-gray-400" />
          </div>
          <Controller
            name="species"
            control={control}
            render={({ field }) => (
              <input
                type="text"
                role="combobox"
                aria-expanded={showSuggestions && suggestions.length > 0 && !!field.value}
                aria-controls="species-suggestions"
                aria-autocomplete="list"
                aria-haspopup="listbox"
                value={field.value ?? ''}
                onChange={(e) => {
                  field.onChange(e.target.value)
                  setShowSuggestions(true)
                }}
                onBlur={() => {
                  setShowSuggestions(false)
                  field.onBlur()
                }}
                onFocus={() => setShowSuggestions(true)}
                placeholder="e.g., Actias luna"
                disabled={disabled}
                maxLength={METADATA_VALIDATION.MAX_SPECIES_LENGTH}
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
            )}
          />

          {showSuggestions && suggestions.length > 0 && speciesValue && (
            <ul
              id="species-suggestions"
              role="listbox"
              aria-label="Species suggestions"
              className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-800 dark:border-gray-600 max-h-48 overflow-auto`}
            >
              {suggestions.map((s) => (
                <li
                  key={s.name}
                  role="option"
                  aria-selected={false}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    // Directly set the form value via Controller's field
                    // We need to get the field ref to call onChange
                  }}
                  className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {s.name} <span className="text-gray-400">({s.count})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Common Name */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Common Name
        </label>
        <input
          type="text"
          {...register('commonName')}
          placeholder="e.g., Luna Moth"
          disabled={disabled}
          maxLength={METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        />
      </div>

      {/* Confidence Level */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Confidence
        </label>
        <select
          {...register('confidence')}
          disabled={disabled}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
        >
          {SPECIES_CONFIG.CONFIDENCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Reference URL */}
      <div>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
          Reference Link
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon className="w-4 h-4 text-gray-400" />
          </div>
          <input
            type="url"
            {...register('referenceUrl')}
            placeholder="https://inaturalist.org/..."
            disabled={disabled}
            maxLength={METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH}
            className={`w-full pl-9 ${referenceUrlValue && !errors.referenceUrl ? 'pr-10' : 'pr-3'} py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 ${
              errors.referenceUrl ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
          />
          {referenceUrlValue && !errors.referenceUrl && (
            <a
              href={referenceUrlValue}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-blue-500 hover:text-blue-700"
              aria-label="Visit reference link"
            >
              <ArrowTopRightOnSquareIcon className="w-4 h-4" />
            </a>
          )}
        </div>
        {errors.referenceUrl?.message && (
          <p className="mt-1 text-xs text-red-500">{errors.referenceUrl.message}</p>
        )}
      </div>
    </div>
  )
}
```

**Important implementation note:** The autocomplete suggestion `onMouseDown` handler needs access to the Controller's `field.onChange`. The cleanest approach is to lift the suggestion handler inside the Controller render prop, or use a ref. During implementation, use a `setValue` prop:

```tsx
interface MetadataSpeciesProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  errors: FieldErrors<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  disabled?: boolean
}
```

Then suggestion click: `setValue('species', s.name, { shouldDirty: true, shouldValidate: true })`. This avoids the Controller render-prop scoping issue.

**Step 2: Write MetadataSpecies.test.tsx**

Replace the test file. Key changes:
- Test wrapper provides `useForm` context instead of raw props
- No more `mockOnChange` — assertions check form state or rendered values
- Autocomplete and URL validation tests check the rendered output

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetadataSpecies from '../MetadataSpecies'
import { metadataFormSchema, type MetadataFormData } from '../../../schemas/metadata'

vi.mock('../../../hooks/useSpecies', () => ({
  default: vi.fn(() => ({
    species: [
      { name: 'Actias luna', count: 42 },
      { name: 'Actias selene', count: 18 },
      { name: 'Antheraea polyphemus', count: 35 },
      { name: 'Automeris io', count: 27 },
      { name: 'Callosamia promethea', count: 12 },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

const DEFAULT_VALUES: MetadataFormData = {
  tags: [],
  species: '',
  commonName: '',
  confidence: 'unknown',
  referenceUrl: '',
  notes: '',
  custom: [],
}

const createQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

/**
 * Test wrapper that provides react-hook-form context.
 * `onFormChange` is called on every form state change so tests
 * can assert on form values without reaching into internals.
 */
function renderSpecies(
  overrides: Partial<MetadataFormData> = {},
  opts: { disabled?: boolean } = {},
) {
  const onFormChange = vi.fn()

  function Wrapper() {
    const { control, register, setValue, formState: { errors }, watch } = useForm<MetadataFormData>({
      resolver: zodResolver(metadataFormSchema),
      defaultValues: { ...DEFAULT_VALUES, ...overrides },
      mode: 'onBlur',
    })

    // Expose form values to tests via callback
    const values = watch()
    onFormChange(values)

    return (
      <QueryClientProvider client={createQueryClient()}>
        <MetadataSpecies
          control={control}
          register={register}
          setValue={setValue}
          errors={errors}
          disabled={opts.disabled}
        />
      </QueryClientProvider>
    )
  }

  const result = render(<Wrapper />)
  return { ...result, onFormChange }
}

describe('MetadataSpecies', () => {
  it('renders species input with current value', () => {
    renderSpecies({ species: 'Actias luna' })
    const input = screen.getByPlaceholderText(/e.g., Actias luna/)
    expect(input).toHaveValue('Actias luna')
  })

  it('shows autocomplete suggestions on input', async () => {
    renderSpecies()
    const input = screen.getByPlaceholderText(/e.g., Actias luna/)
    fireEvent.change(input, { target: { value: 'Actias' } })
    fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
      expect(screen.getByText(/Actias selene/)).toBeInTheDocument()
    })
  })

  it('selects suggestion and updates input', async () => {
    renderSpecies()
    const input = screen.getByPlaceholderText(/e.g., Actias luna/)
    fireEvent.change(input, { target: { value: 'Actias' } })
    fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByText(/Actias luna/)).toBeInTheDocument()
    })

    fireEvent.mouseDown(screen.getByText(/Actias luna/))

    await waitFor(() => {
      expect(input).toHaveValue('Actias luna')
    })
  })

  it('renders confidence dropdown with options', () => {
    renderSpecies({ confidence: 'certain' })
    expect(screen.getByRole('option', { name: 'Certain' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Probable' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Possible' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
  })

  it('renders common name field', () => {
    renderSpecies({ commonName: 'Luna Moth' })
    const input = screen.getByPlaceholderText(/e.g., Luna Moth/)
    expect(input).toHaveValue('Luna Moth')
  })

  it('renders reference link field', () => {
    renderSpecies({ referenceUrl: 'https://inaturalist.org/taxa/47924' })
    const input = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)
    expect(input).toHaveValue('https://inaturalist.org/taxa/47924')
  })

  it('shows URL validation error on blur', async () => {
    renderSpecies()
    const input = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)
    fireEvent.change(input, { target: { value: 'not-a-url' } })
    fireEvent.blur(input)

    await waitFor(() => {
      expect(screen.getByText(/URL must start with http:\/\/ or https:\/\//)).toBeInTheDocument()
    })
  })

  it('clears URL error when valid URL entered', async () => {
    renderSpecies()
    const input = screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)

    fireEvent.change(input, { target: { value: 'not-a-url' } })
    fireEvent.blur(input)

    await waitFor(() => {
      expect(screen.getByText(/URL must start with http:\/\/ or https:\/\//)).toBeInTheDocument()
    })

    fireEvent.change(input, { target: { value: 'https://inaturalist.org/taxa/47924' } })
    fireEvent.blur(input)

    await waitFor(() => {
      expect(screen.queryByText(/URL must start with http:\/\/ or https:\/\//)).not.toBeInTheDocument()
    })
  })

  it('disables all fields when disabled', () => {
    renderSpecies(
      { species: 'Actias luna', confidence: 'certain', commonName: 'Luna Moth', referenceUrl: 'https://example.com' },
      { disabled: true },
    )

    expect(screen.getByPlaceholderText(/e.g., Actias luna/)).toBeDisabled()
    expect(screen.getByPlaceholderText(/e.g., Luna Moth/)).toBeDisabled()
    expect(screen.getByDisplayValue('Certain')).toBeDisabled()
    expect(screen.getByPlaceholderText(/https:\/\/inaturalist.org\/.../)).toBeDisabled()
  })

  it('shows external link icon for valid URL', () => {
    renderSpecies({ referenceUrl: 'https://inaturalist.org/taxa/47924' })
    expect(screen.getByLabelText('Visit reference link')).toBeInTheDocument()
  })
})
```

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/metadata/__tests__/MetadataSpecies --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/components/metadata/MetadataSpecies.tsx webui/frontend/src/components/metadata/__tests__/MetadataSpecies.test.tsx
git rm webui/frontend/src/components/metadata/MetadataSpecies.jsx webui/frontend/src/components/metadata/__tests__/MetadataSpecies.test.jsx
git commit -m "feat(#444): migrate MetadataSpecies to react-hook-form + Zod + TypeScript"
```

---

## Task 3: Migrate MetadataTags

**Files:**
- Rename: `webui/frontend/src/components/metadata/MetadataTags.jsx` → `.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataTags.test.jsx` → `.test.tsx` (if exists)

**Step 1: Write MetadataTags.tsx**

Key changes:
- Props change from `{ tags, onAddTag, onRemoveTag, onCopyToNext, disabled }` to `{ control, setValue, onCopyToNext, disabled }`
- No `useFieldArray` — tags are `string[]` managed via `useWatch`/`setValue`
- Local `inputValue` state stays (staging area)
- `useTags` autocomplete stays

```tsx
import { useState, useMemo, useCallback } from 'react'
import { useWatch } from 'react-hook-form'
import type { Control, UseFormSetValue } from 'react-hook-form'
import { XMarkIcon, ClipboardDocumentIcon } from '@heroicons/react/24/outline'
import useTags from '../../hooks/useTags'
import { METADATA_VALIDATION, Z_INDEX } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataTagsProps {
  control: Control<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  onCopyToNext?: () => void
  disabled?: boolean
}

export default function MetadataTags({
  control,
  setValue,
  onCopyToNext,
  disabled = false,
}: MetadataTagsProps) {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)

  const tags = useWatch({ control, name: 'tags' }) ?? []
  const { data: tagsData } = useTags({ sort: 'count', order: 'desc', limit: 20 })

  const suggestions = useMemo(() =>
    tagsData?.tags
      ?.filter((t) => t.name.toLowerCase().includes(inputValue.toLowerCase()))
      ?.filter((t) => !tags.some((existing) => existing.toLowerCase() === t.name.toLowerCase()))
      ?.slice(0, 5) || []
  , [tagsData, inputValue, tags])

  const addTag = useCallback((tag: string) => {
    const trimmed = tag.trim()
    if (!trimmed) return
    if (tags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) return
    setValue('tags', [...tags, trimmed], { shouldDirty: true })
    setInputValue('')
    setShowSuggestions(false)
  }, [tags, setValue])

  const removeTag = useCallback((index: number) => {
    setValue('tags', tags.filter((_, i) => i !== index), { shouldDirty: true })
  }, [tags, setValue])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault()
      addTag(inputValue)
    }
  }, [addTag, inputValue])

  return (
    <div className="space-y-2">
      {/* Tag Chips */}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, index) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full dark:bg-blue-900 dark:text-blue-200"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              disabled={disabled}
              className="hover:text-blue-600 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={`Remove tag ${tag}`}
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </span>
        ))}
        {tags.length === 0 && (
          <span className="text-gray-400 text-sm">Add tags...</span>
        )}
      </div>

      {/* Input with Autocomplete */}
      <div className="relative">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            setShowSuggestions(true)
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setShowSuggestions(false)}
          placeholder="Type to add tags..."
          disabled={disabled}
          maxLength={METADATA_VALIDATION.MAX_TAG_LENGTH}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
        />

        {showSuggestions && suggestions.length > 0 && inputValue && !disabled && (
          <ul className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-800 dark:border-gray-600 max-h-60 overflow-auto`}>
            {suggestions.map((suggestion) => (
              <li
                key={suggestion.name}
                onMouseDown={(e) => {
                  e.preventDefault()
                  addTag(suggestion.name)
                }}
                className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 flex justify-between items-center"
              >
                <span>{suggestion.name}</span>
                <span className="text-gray-400 text-sm">({suggestion.count})</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Copy to Next Button */}
      {onCopyToNext && (
        <button
          type="button"
          onClick={onCopyToNext}
          disabled={disabled || tags.length === 0}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ClipboardDocumentIcon className="w-4 h-4" />
          Copy tags to next photo
        </button>
      )}
    </div>
  )
}
```

**Step 2: Write MetadataTags.test.tsx**

Follow the same wrapper pattern as MetadataSpecies. Test file should cover: rendering chips, add via Enter/comma, remove, autocomplete, duplicate prevention, disabled state, copy-to-next. Use the `renderWithForm` wrapper providing `control` and `setValue`.

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/metadata/__tests__/MetadataTags --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/components/metadata/MetadataTags.tsx webui/frontend/src/components/metadata/__tests__/MetadataTags.test.tsx
git rm webui/frontend/src/components/metadata/MetadataTags.jsx webui/frontend/src/components/metadata/__tests__/MetadataTags.test.jsx
git commit -m "feat(#444): migrate MetadataTags to react-hook-form + TypeScript"
```

---

## Task 4: Migrate MetadataNotes

**Files:**
- Rename: `webui/frontend/src/components/metadata/MetadataNotes.jsx` → `.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataNotes.test.jsx` → `.test.tsx` (if exists)

**Step 1: Write MetadataNotes.tsx**

Key changes:
- Props: `{ control, register, setValue, disabled }` — no more `value`/`onChange`/`maxLength`
- `register('notes')` on textarea
- Auto-height uses `useWatch({ control, name: 'notes' })` to track value
- Timestamp insertion uses `setValue('notes', ...)` with `{ shouldDirty: true }`
- Character counter reads watched value length
- `maxLength` comes from `METADATA_VALIDATION.MAX_NOTES_LENGTH` directly (no prop needed)

```tsx
import { useRef, useEffect, useCallback } from 'react'
import { useWatch } from 'react-hook-form'
import type { Control, UseFormRegister, UseFormSetValue } from 'react-hook-form'
import { ClockIcon } from '@heroicons/react/24/outline'
import { METADATA_VALIDATION } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataNotesProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  disabled?: boolean
}

export default function MetadataNotes({
  control,
  register,
  setValue,
  disabled = false,
}: MetadataNotesProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const maxLength = METADATA_VALIDATION.MAX_NOTES_LENGTH

  const notesValue = useWatch({ control, name: 'notes' }) ?? ''

  // Auto-expand textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.max(80, textarea.scrollHeight)}px`
    }
  }, [])

  useEffect(() => {
    adjustHeight()
  }, [notesValue, adjustHeight])

  const { ref: registerRef, ...registerRest } = register('notes', {
    onChange: () => adjustHeight(),
  })

  const insertTimestamp = () => {
    const now = new Date()
    const timestamp = now.toISOString().slice(0, 16).replace('T', ' ') + ' - '
    const cursorPos = textareaRef.current?.selectionStart || notesValue.length
    const newValue = notesValue.slice(0, cursorPos) + timestamp + notesValue.slice(cursorPos)
    setValue('notes', newValue, { shouldDirty: true })

    setTimeout(() => {
      if (textareaRef.current) {
        const newPos = cursorPos + timestamp.length
        textareaRef.current.focus()
        textareaRef.current.setSelectionRange(newPos, newPos)
      }
    }, 0)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault()
      textareaRef.current?.blur()
    }
  }

  const charCount = notesValue.length
  const isNearLimit = charCount >= maxLength * 0.9
  const isAtLimit = charCount >= maxLength

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <button
          type="button"
          onClick={insertTimestamp}
          disabled={disabled}
          className="inline-flex items-center gap-1 text-xs text-gray-600 hover:text-blue-600 disabled:opacity-50"
          title="Insert timestamp"
        >
          <ClockIcon className="w-4 h-4" />
          Add timestamp
        </button>
        <span className={`text-xs ${isNearLimit ? (isAtLimit ? 'text-red-500' : 'text-yellow-500') : 'text-gray-400'}`}>
          {charCount.toLocaleString()} / {maxLength.toLocaleString()} characters
        </span>
      </div>

      <textarea
        ref={(el) => {
          registerRef(el)
          textareaRef.current = el
        }}
        {...registerRest}
        onKeyDown={handleKeyDown}
        placeholder="Add notes about this photo..."
        disabled={disabled}
        maxLength={maxLength}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 resize-none overflow-hidden whitespace-pre-wrap dark:bg-gray-800 dark:border-gray-600 min-h-[80px]"
        style={{ whiteSpace: 'pre-wrap' }}
      />

      <p className="text-xs text-gray-400">
        Ctrl+Enter to finish editing
      </p>
    </div>
  )
}
```

**Note:** The `ref` callback merges react-hook-form's `registerRef` with our local `textareaRef` for height adjustment and cursor positioning.

**Step 2: Write MetadataNotes.test.tsx**

Use form wrapper. Test: rendering, auto-expand, character count, timestamp insertion, disabled state, Ctrl+Enter blur, max length.

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/metadata/__tests__/MetadataNotes --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/components/metadata/MetadataNotes.tsx webui/frontend/src/components/metadata/__tests__/MetadataNotes.test.tsx
git rm webui/frontend/src/components/metadata/MetadataNotes.jsx webui/frontend/src/components/metadata/__tests__/MetadataNotes.test.jsx
git commit -m "feat(#444): migrate MetadataNotes to react-hook-form + TypeScript"
```

---

## Task 5: Migrate MetadataCustomFields

**Files:**
- Rename: `webui/frontend/src/components/metadata/MetadataCustomFields.jsx` → `.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataCustomFields.test.jsx` → `.test.tsx` (if exists)

**Step 1: Write MetadataCustomFields.tsx**

Key changes:
- Props: `{ control, disabled }` — no more `fields`/`onChange`/`maxFields`
- Uses `useFieldArray({ control, name: 'custom' })` for `fields`, `append`, `remove`, `update`
- Each entry has `key` and `value` string fields
- Duplicate key check: local UI error, reads `fields` array

```tsx
import { useState } from 'react'
import { useFieldArray } from 'react-hook-form'
import type { Control } from 'react-hook-form'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataCustomFieldsProps {
  control: Control<MetadataFormData>
  disabled?: boolean
}

const MAX_FIELDS = 100

export default function MetadataCustomFields({
  control,
  disabled = false,
}: MetadataCustomFieldsProps) {
  const [keyError, setKeyError] = useState<string | null>(null)
  const { fields, append, remove, update } = useFieldArray({ control, name: 'custom' })

  const canAddMore = fields.length < MAX_FIELDS

  const handleKeyChange = (index: number, newKey: string) => {
    const currentKey = fields[index].key
    if (newKey && newKey !== currentKey && fields.some((f, i) => i !== index && f.key === newKey)) {
      setKeyError(`Key "${newKey}" already exists`)
      return
    }
    setKeyError(null)
    update(index, { key: newKey, value: fields[index].value })
  }

  const handleValueChange = (index: number, newValue: string) => {
    update(index, { key: fields[index].key, value: newValue })
  }

  const handleAdd = () => {
    if (!canAddMore) return
    let tempKey = 'field_1'
    let i = 1
    while (fields.some((f) => f.key === tempKey)) {
      i++
      tempKey = `field_${i}`
    }
    append({ key: tempKey, value: '' })
  }

  const handleDelete = (index: number) => {
    remove(index)
    setKeyError(null)
  }

  return (
    <div className="space-y-2">
      {fields.length === 0 ? (
        <p className="text-sm text-gray-500">No custom fields</p>
      ) : (
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div key={field.id} className="flex gap-2 items-start">
              <input
                type="text"
                value={field.key}
                onChange={(e) => handleKeyChange(index, e.target.value)}
                placeholder="Field name"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <input
                type="text"
                value={field.value}
                onChange={(e) => handleValueChange(index, e.target.value)}
                placeholder="Value"
                disabled={disabled}
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
              />
              <button
                type="button"
                onClick={() => handleDelete(index)}
                disabled={disabled}
                className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
                aria-label={`Delete field ${field.key}`}
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {keyError && (
        <p className="text-xs text-red-500">{keyError}</p>
      )}

      <button
        type="button"
        onClick={handleAdd}
        disabled={disabled || !canAddMore}
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <PlusIcon className="w-4 h-4" />
        Add custom field
        {!canAddMore && <span className="text-gray-400">(max {MAX_FIELDS})</span>}
      </button>
    </div>
  )
}
```

**Step 2: Write MetadataCustomFields.test.tsx**

Use form wrapper. Test: rendering key-value pairs, add, edit key, edit value, delete, duplicate key error, max fields limit, empty state, disabled state.

**Step 3: Run tests**

Run: `cd webui/frontend && npx vitest run src/components/metadata/__tests__/MetadataCustomFields --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add webui/frontend/src/components/metadata/MetadataCustomFields.tsx webui/frontend/src/components/metadata/__tests__/MetadataCustomFields.test.tsx
git rm webui/frontend/src/components/metadata/MetadataCustomFields.jsx webui/frontend/src/components/metadata/__tests__/MetadataCustomFields.test.jsx
git commit -m "feat(#444): migrate MetadataCustomFields to useFieldArray + TypeScript"
```

---

## Task 6: Migrate MetadataPanel (Container)

**Files:**
- Rename: `webui/frontend/src/components/metadata/MetadataPanel.jsx` → `.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataPanel.test.jsx` → `.test.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataPanel.integration.test.jsx` → `.integration.test.tsx`
- Rename: `webui/frontend/src/components/metadata/__tests__/MetadataPanel.mobile.test.jsx` → `.mobile.test.tsx`

**Step 1: Write MetadataPanel.tsx**

Key changes from original:
- Replace `editableData` useState with `useForm<MetadataFormData>`
- Replace all `handleXxxChange` callbacks with `control`/`register`/`setValue` passed to children
- `useWatch({ control })` feeds `useAutoSave`
- `reset()` syncs sidecar data (with `!isDirty` guard)
- `onSave` converts camelCase form → snake_case API
- Custom fields: `Object.entries()` → `{ key, value }[]` on reset, `Object.fromEntries()` on save
- Remove `PropTypes`, add TypeScript interface

The file is large (~310 lines currently). Key structural changes:

```tsx
import { useState, useEffect, useCallback, useRef } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
// ... other imports ...
import { metadataFormSchema, type MetadataFormData } from '../../schemas/metadata'

interface MetadataPanelProps {
  photoPath: string
  className?: string
  onClose?: () => void
}

export default function MetadataPanel({ photoPath, className = '', onClose }: MetadataPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const filename = photoPath || null
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  const { data: exifData, isLoading: exifLoading, isError: exifError, refetch: refetchExif } = usePhotoMetadata(photoPath)
  const { data: sidecarData, isLoading: sidecarLoading, updateMetadata } = useSidecarMetadata(filename)

  const { control, register, reset, setValue, formState: { isDirty } } = useForm<MetadataFormData>({
    resolver: zodResolver(metadataFormSchema),
    defaultValues: {
      tags: [], species: '', commonName: '', confidence: 'unknown',
      referenceUrl: '', notes: '', custom: [],
    },
    mode: 'onBlur',
  })

  // Sync sidecar data → form (only when user hasn't made edits)
  useEffect(() => {
    if (sidecarData && !isDirty) {
      reset({
        tags: sidecarData.tags || [],
        species: sidecarData.species || '',
        commonName: sidecarData.species_common_name || '',
        confidence: sidecarData.species_confidence || 'unknown',
        referenceUrl: sidecarData.species_reference_url || '',
        notes: sidecarData.notes || '',
        custom: Object.entries(sidecarData.custom || {}).map(([key, value]) => ({ key, value: String(value) })),
      })
    }
  }, [sidecarData, isDirty, reset])

  // Watch all form values for auto-save
  const watchedData = useWatch({ control })

  const { status: saveStatus, error: saveError, saveNow } = useAutoSave({
    data: watchedData,
    onSave: async (data) => {
      await updateMetadata({
        tags: data.tags,
        species: data.species,
        species_confidence: data.confidence,
        species_common_name: data.commonName,
        species_reference_url: data.referenceUrl,
        notes: data.notes,
        custom: Object.fromEntries((data.custom || []).map(({ key, value }) => [key, value])),
      })
    },
    delay: 2000,
    enabled: !!filename,
  })

  // ... keyboard shortcuts (unchanged) ...

  // Render children with form props instead of callbacks:
  // <MetadataSpecies control={control} register={register} setValue={setValue} errors={errors} />
  // <MetadataTags control={control} setValue={setValue} />
  // <MetadataNotes control={control} register={register} setValue={setValue} />
  // <MetadataCustomFields control={control} />
}
```

**Step 2: Update MetadataPanel.test.tsx**

Key changes:
- Child component mocks update to accept new props (`control`, `register`, `setValue` instead of value/onChange)
- Mock stubs should render `data-testid` attributes as before
- Remove assertions on old callback args (`handleSpeciesChange`, `handleTagAdd`, etc.)
- Add assertions that form state syncs properly

**Step 3: Update MetadataPanel.integration.test.tsx**

Key changes:
- No child mocks — renders real children
- Auto-save assertions should still work (useAutoSave watches form data)
- Tag add/remove tests: interact with real MetadataTags (which now uses setValue)
- API payload assertions update to match same shape (should be unchanged since we convert at boundary)

**Step 4: Update MetadataPanel.mobile.test.tsx**

Minimal changes — mostly CSS class assertions and drawer behavior. Just update mock stubs for new prop signatures.

**Step 5: Run all MetadataPanel tests**

Run: `cd webui/frontend && npx vitest run src/components/metadata/__tests__/MetadataPanel --reporter=verbose`
Expected: All 43 tests PASS (20 + 9 + 14)

**Step 6: Commit**

```bash
git add webui/frontend/src/components/metadata/MetadataPanel.tsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.test.tsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.integration.test.tsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.mobile.test.tsx
git rm webui/frontend/src/components/metadata/MetadataPanel.jsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.test.jsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.integration.test.jsx webui/frontend/src/components/metadata/__tests__/MetadataPanel.mobile.test.jsx
git commit -m "feat(#444): migrate MetadataPanel container to useForm + TypeScript"
```

---

## Task 7: Full Integration Verification

**Step 1: Run all metadata tests together**

Run: `cd webui/frontend && npx vitest run src/components/metadata/ --reporter=verbose`
Expected: ALL tests pass across all files.

**Step 2: Run type-check**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No type errors in metadata files.

**Step 3: Run linter**

Run: `cd webui/frontend && npx eslint src/components/metadata/ src/schemas/metadata.ts`
Expected: No lint errors.

**Step 4: Verify no old files remain**

Check: No `.jsx` files left in `src/components/metadata/` (except AccordionSection, SaveStatusIndicator, MetadataSkeleton, MetadataEXIF which are out of scope).

**Step 5: Verify imports**

Run: `cd webui/frontend && grep -r "from.*MetadataSpecies\|from.*MetadataTags\|from.*MetadataNotes\|from.*MetadataCustomFields\|from.*MetadataPanel" src/ --include="*.jsx" --include="*.tsx" --include="*.ts"`
Expected: No files import the old `.jsx` paths. All imports resolve to `.tsx`.

**Step 6: Final commit if any cleanup needed**

```bash
git commit -m "chore(#444): cleanup and verify metadata migration"
```

---

## Reference: Existing Test Counts

| Test File | Tests | Notes |
|---|---|---|
| MetadataSpecies.test | 14 | Autocomplete, URL validation, disabled state |
| MetadataTags.test | 20 | Chips, add/remove, autocomplete, dedup, copy-to-next |
| MetadataNotes.test | 13 | Textarea, auto-resize, timestamp, char count |
| MetadataCustomFields.test | 10 | Key-value CRUD, duplicate key, max fields |
| MetadataPanel.test | 20 | Accordion, auto-save, editing, keyboard shortcuts |
| MetadataPanel.integration.test | 9 | Real hooks, debounce, tag operations |
| MetadataPanel.mobile.test | 14 | Drawer, FAB, backdrop, accessibility |
| **Total** | **100** | All should pass after migration |
