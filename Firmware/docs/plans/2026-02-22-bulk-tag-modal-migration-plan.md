# BulkTagModal Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate BulkTagModal from manual useState validation to react-hook-form + Zod with TypeScript, converting .jsx to .tsx.

**Architecture:** useForm manages the tags array (via useFieldArray) and mode radio. Local useState handles transient text input and autocomplete dropdown. Zod schema validates form shape on submit. Parent contract (`onApply({ tags: string[], mode })`) is preserved by mapping `{ value: string }[]` to `string[]` in onSubmit.

**Tech Stack:** react-hook-form (useForm, useFieldArray), Zod, @hookform/resolvers, TypeScript, Vitest

---

### Task 1: Create Zod Schema

**Files:**
- Create: `webui/frontend/src/schemas/tag.ts`

**Step 1: Write the schema file**

```typescript
// webui/frontend/src/schemas/tag.ts
import { z } from 'zod'

/**
 * Tag mode options for bulk tag operations.
 */
export const TAG_MODES = ['add', 'replace', 'remove'] as const

/**
 * Bulk tag form schema.
 *
 * Used by BulkTagModal.tsx via zodResolver. Tags are stored as
 * { value: string } objects because useFieldArray requires object elements.
 * The component maps these back to string[] when calling onApply.
 */
export const bulkTagSchema = z.object({
  tags: z.array(
    z.object({ value: z.string().trim().min(1, 'Tag cannot be empty') })
  ).min(1, 'At least one tag is required'),
  mode: z.enum(TAG_MODES),
})

export type BulkTagFormData = z.infer<typeof bulkTagSchema>
```

**Step 2: Verify the file compiles**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx tsc --noEmit src/schemas/tag.ts --esModuleInterop --moduleResolution node --jsx react-jsx --target es2020 --module es2020 --strict 2>&1 | head -20`

Expected: No errors (or only import resolution warnings that don't affect Vite)

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/tag.ts
git commit -m "feat(#440): add Zod schema for BulkTagModal"
```

---

### Task 2: Write Schema Tests

**Files:**
- Create: `webui/frontend/src/schemas/__tests__/tag.test.ts`

**Step 1: Write the failing tests**

```typescript
// webui/frontend/src/schemas/__tests__/tag.test.ts
import { describe, it, expect } from 'vitest'
import { bulkTagSchema, TAG_MODES } from '../tag'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

// ---------------------------------------------------------------------------
// bulkTagSchema
// ---------------------------------------------------------------------------

describe('bulkTagSchema', () => {
  describe('valid data', () => {
    it('accepts tags with add mode', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: 'moth' }, { value: 'nocturnal' }],
        mode: 'add',
      })
      expect(result.success).toBe(true)
    })

    it('accepts tags with replace mode', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: 'insect' }],
        mode: 'replace',
      })
      expect(result.success).toBe(true)
    })

    it('accepts tags with remove mode', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: 'unwanted' }],
        mode: 'remove',
      })
      expect(result.success).toBe(true)
    })

    it('accepts a single tag', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: 'moth' }],
        mode: 'add',
      })
      expect(result.success).toBe(true)
    })

    it('trims whitespace from tag values', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: '  moth  ' }],
        mode: 'add',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.tags[0].value).toBe('moth')
      }
    })
  })

  describe('invalid data', () => {
    it('rejects empty tags array', () => {
      const result = bulkTagSchema.safeParse({
        tags: [],
        mode: 'add',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('At least one tag is required')
    })

    it('rejects empty string tag value', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: '' }],
        mode: 'add',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Tag cannot be empty')
    })

    it('rejects whitespace-only tag value', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: '   ' }],
        mode: 'add',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Tag cannot be empty')
    })

    it('rejects invalid mode', () => {
      const result = bulkTagSchema.safeParse({
        tags: [{ value: 'moth' }],
        mode: 'invalid',
      })
      expect(result.success).toBe(false)
    })

    it('rejects missing tags field', () => {
      const result = bulkTagSchema.safeParse({ mode: 'add' })
      expect(result.success).toBe(false)
    })

    it('rejects missing mode field', () => {
      const result = bulkTagSchema.safeParse({ tags: [{ value: 'moth' }] })
      expect(result.success).toBe(false)
    })
  })

  describe('TAG_MODES constant', () => {
    it('exports all three modes', () => {
      expect(TAG_MODES).toEqual(['add', 'replace', 'remove'])
    })
  })
})
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/schemas/__tests__/tag.test.ts`

Expected: All tests PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/__tests__/tag.test.ts
git commit -m "test(#440): add schema tests for bulkTagSchema"
```

---

### Task 3: Update Schema Index

**Files:**
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Add re-exports**

Add these lines to `webui/frontend/src/schemas/index.ts`:

```typescript
export { bulkTagSchema, TAG_MODES } from './tag';
export type { BulkTagFormData } from './tag';
```

**Step 2: Verify existing schema tests still pass**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/schemas/`

Expected: All schema tests pass (preset + tag)

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/index.ts
git commit -m "feat(#440): re-export tag schema from schemas index"
```

---

### Task 4: Migrate BulkTagModal Component

**Files:**
- Create: `webui/frontend/src/components/gallery/BulkTagModal.tsx`
- Delete: `webui/frontend/src/components/gallery/BulkTagModal.jsx` (after verification)

**Reference files to understand patterns:**
- `webui/frontend/src/components/filters/SaveFilterPresetModal.tsx` — completed migration (modal pattern)
- `webui/frontend/src/components/form/FormField.tsx` — shared form field wrapper
- `webui/frontend/src/components/gallery/TagChip.jsx` — tag display component (unchanged, still .jsx)

**Step 1: Write the migrated component**

Create `webui/frontend/src/components/gallery/BulkTagModal.tsx`:

```tsx
import { useState, useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import TagChip from './TagChip'
import useTags from '../../hooks/useTags'
import { bulkTagSchema, TAG_MODES, type BulkTagFormData } from '../../schemas/tag'
import { Z_INDEX } from '../../constants/config'

const MODES = [
  { value: 'add' as const, label: 'Add tags', description: 'Add to existing tags' },
  { value: 'replace' as const, label: 'Replace tags', description: 'Replace all existing tags', warning: true },
  { value: 'remove' as const, label: 'Remove tags', description: 'Remove these tags from photos' },
]

interface BulkTagModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Apply handler - receives { tags: string[], mode: 'add' | 'replace' | 'remove' } */
  onApply: (data: { tags: string[]; mode: typeof TAG_MODES[number] }) => void
  /** Number of selected photos */
  selectedCount: number
  /** Loading state */
  isLoading?: boolean
  /** Error message */
  error?: string | null
}

export default function BulkTagModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null,
}: BulkTagModalProps) {
  const [inputValue, setInputValue] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const blurTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null)

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { isValid },
  } = useForm<BulkTagFormData>({
    resolver: zodResolver(bulkTagSchema),
    defaultValues: { tags: [], mode: 'add' },
    mode: 'onBlur',
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'tags',
  })

  const mode = watch('mode')

  // Clear blur timeout on unmount to prevent state updates after teardown
  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current) clearTimeout(blurTimeoutRef.current)
    }
  }, [])

  // Fetch available tags for autocomplete
  const { data: tagsData } = useTags({ sort: 'count', order: 'desc', limit: 20 })

  // Filter suggestions based on input value
  const suggestions = useMemo(() =>
    tagsData?.tags
      ?.filter((t: { name: string }) => t.name.toLowerCase().includes(inputValue.toLowerCase()))
      ?.filter((t: { name: string }) => !fields.some((existing) => existing.value.toLowerCase() === t.name.toLowerCase()))
      ?.slice(0, 8) || []
  , [tagsData, inputValue, fields])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      reset({ tags: [], mode: 'add' })
      setInputValue('')
      setShowSuggestions(false)
    }
  }, [isOpen, reset])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleAddTag = (tag: string) => {
    const trimmed = tag.trim()
    if (!trimmed) return
    // Case-insensitive duplicate check
    if (fields.some((t) => t.value.toLowerCase() === trimmed.toLowerCase())) return
    append({ value: trimmed })
    setInputValue('')
    setShowSuggestions(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault()
      handleAddTag(inputValue)
    }
  }

  const handleRemoveTag = (index: number) => {
    remove(index)
  }

  const onSubmit = (data: BulkTagFormData) => {
    onApply({ tags: data.tags.map(t => t.value), mode: data.mode })
  }

  const getModeLabel = () => {
    if (mode === 'add') return 'Add'
    if (mode === 'replace') return 'Replace'
    return 'Remove'
  }

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-tag-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-tag-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {getModeLabel()} tags for {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            type="button"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Mode selector */}
          <div className="mb-4" role="radiogroup" aria-label="Tag operation mode">
            {MODES.map(m => (
              <label
                key={m.value}
                className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer mb-2
                           ${mode === m.value
                    ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
              >
                <input
                  type="radio"
                  {...register('mode')}
                  value={m.value}
                  className="mt-1"
                  aria-label={m.label}
                />
                <div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{m.label}</span>
                  <p className={`text-sm ${m.warning ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'}`}>
                    {m.description}
                  </p>
                </div>
              </label>
            ))}
          </div>

          {/* Tag input */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100">Tags</label>
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => {
                  setInputValue(e.target.value)
                  setShowSuggestions(true)
                }}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => { blurTimeoutRef.current = setTimeout(() => setShowSuggestions(false), 150) }}
                placeholder="Type to search or create tags..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              />

              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <ul className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg dark:bg-gray-700 dark:border-gray-600 max-h-48 overflow-auto`}>
                  {suggestions.map((suggestion: { name: string; count: number }) => (
                    <li
                      key={suggestion.name}
                      onMouseDown={(e) => {
                        e.preventDefault()
                        handleAddTag(suggestion.name)
                      }}
                      className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 flex justify-between items-center text-gray-900 dark:text-gray-100"
                    >
                      <span>{suggestion.name}</span>
                      <span className="text-gray-400 text-sm">({suggestion.count})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Press Enter or comma to add tags
            </p>
          </div>

          {/* Selected tags */}
          {fields.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {fields.map((field, index) => (
                <TagChip
                  key={field.id}
                  tag={field.value}
                  removable
                  onRemove={() => handleRemoveTag(index)}
                />
              ))}
            </div>
          )}

          {/* Error message */}
          {error && (
            <p className="text-red-600 dark:text-red-400 text-sm mb-4">{error}</p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={fields.length === 0 || isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Applying...' : 'Apply'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
```

**Key decisions in this code:**
- Radio inputs use `{...register('mode')}` instead of manual `onChange` + `checked`. react-hook-form's `register` returns `{ onChange, onBlur, ref, name }` which handles radio groups natively — the `value` attribute on each radio determines which one is selected.
- Apply button uses `fields.length === 0` instead of `!isValid` for the disabled check. This is because `isValid` with `mode: 'onBlur'` starts as `false` and doesn't update until blur occurs on a registered field. Since the tag input isn't registered (it's local state), `isValid` would stay false even after tags are appended. Using `fields.length === 0` preserves the exact current UX.
- TagChip `key` uses `field.id` (from useFieldArray) instead of the tag string. This is the react-hook-form best practice for stable keys.
- Suggestion type annotations `(t: { name: string })` and `(suggestion: { name: string; count: number })` are added inline since `useTags` is still a .js hook without TypeScript types.

**Step 2: Delete the old component**

Delete: `webui/frontend/src/components/gallery/BulkTagModal.jsx`

**Step 3: Verify the Gallery page import still resolves**

The import in `Gallery.jsx` is `import BulkTagModal from '../components/gallery/BulkTagModal'` — Vite resolves `.tsx` when `.jsx` is gone.

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vite build 2>&1 | tail -5`

Expected: Build succeeds

**Step 4: Commit**

```bash
git add webui/frontend/src/components/gallery/BulkTagModal.tsx
git rm webui/frontend/src/components/gallery/BulkTagModal.jsx
git commit -m "feat(#440): migrate BulkTagModal to react-hook-form + Zod + TypeScript"
```

---

### Task 5: Migrate Component Tests

**Files:**
- Create: `webui/frontend/src/components/gallery/__tests__/BulkTagModal.test.tsx`
- Delete: `webui/frontend/src/components/gallery/__tests__/BulkTagModal.test.jsx`

**Step 1: Write the migrated test file**

```tsx
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BulkTagModal from '../BulkTagModal'

// Mock useTags hook to provide test tag data
vi.mock('../../../hooks/useTags', () => ({
  default: () => ({
    data: {
      tags: [
        { name: 'moth', count: 10 },
        { name: 'nocturnal', count: 5 },
        { name: 'insect', count: 8 },
      ],
    },
    isLoading: false,
    error: null,
  }),
}))

// Create QueryClient for tests
const createTestQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

interface RenderModalProps {
  isOpen?: boolean
  onClose?: ReturnType<typeof vi.fn>
  onApply?: ReturnType<typeof vi.fn>
  selectedCount?: number
  isLoading?: boolean
  error?: string | null
}

const renderModal = (props: RenderModalProps = {}) => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onApply: vi.fn(),
    selectedCount: 5,
  }

  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <BulkTagModal {...defaultProps} {...props} />
    </QueryClientProvider>
  )
}

describe('BulkTagModal', () => {
  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      renderModal({ isOpen: false })
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders modal when isOpen is true', () => {
      renderModal()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    it('shows photo count in title - multiple photos', () => {
      renderModal({ selectedCount: 5 })
      expect(screen.getByText(/Add tags for 5 photos/i)).toBeInTheDocument()
    })

    it('shows photo count in title - single photo', () => {
      renderModal({ selectedCount: 1 })
      expect(screen.getByText(/Add tags for 1 photo$/i)).toBeInTheDocument()
    })

    it('renders as portal to document.body', () => {
      renderModal()
      const modal = screen.getByRole('dialog')
      expect(document.body.contains(modal)).toBe(true)
    })
  })

  describe('Mode Selector', () => {
    it('shows three mode options: Add, Replace, Remove', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      const radios = within(radioGroup).getAllByRole('radio')

      expect(radios).toHaveLength(3)
      expect(within(radioGroup).getByLabelText(/Add tags/i)).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Replace tags/i)).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Remove tags/i)).toBeInTheDocument()
    })

    it('"Add" mode is selected by default', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      const addRadio = within(radioGroup).getByLabelText(/Add tags/i)
      expect(addRadio).toBeChecked()
    })

    it('clicking mode option selects it', async () => {
      const user = userEvent.setup()
      renderModal()

      const radioGroup = screen.getByRole('radiogroup')
      const replaceRadio = within(radioGroup).getByLabelText(/Replace tags/i)
      await user.click(replaceRadio)

      expect(replaceRadio).toBeChecked()
      expect(within(radioGroup).getByLabelText(/Add tags/i)).not.toBeChecked()
    })

    it('"Add" shows description "Add to existing tags"', () => {
      renderModal()
      expect(screen.getByText(/Add to existing tags/i)).toBeInTheDocument()
    })

    it('"Replace" shows warning "Replace all existing tags"', () => {
      renderModal()
      expect(screen.getByText(/Replace all existing tags/i)).toBeInTheDocument()
    })

    it('"Remove" shows description "Remove these tags from photos"', () => {
      renderModal()
      expect(screen.getByText(/Remove these tags from photos/i)).toBeInTheDocument()
    })

    it('title updates when mode changes', async () => {
      const user = userEvent.setup()
      renderModal({ selectedCount: 5 })

      // Default: Add
      expect(screen.getByText(/Add tags for 5 photos/i)).toBeInTheDocument()

      // Change to Replace
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))
      expect(screen.getByText(/Replace tags for 5 photos/i)).toBeInTheDocument()

      // Change to Remove
      await user.click(within(radioGroup).getByLabelText(/Remove tags/i))
      expect(screen.getByText(/Remove tags for 5 photos/i)).toBeInTheDocument()
    })
  })

  describe('Tag Input', () => {
    it('shows tag input field', () => {
      renderModal()
      expect(screen.getByPlaceholderText(/Type to search or create tags/i)).toBeInTheDocument()
    })

    it('can add tags by typing and pressing Enter', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      // Tag should be displayed as chip
      expect(screen.getByText('moth')).toBeInTheDocument()
    })

    it('shows selected tags as removable chips', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'nocturnal{Enter}')

      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(screen.getByText('nocturnal')).toBeInTheDocument()
    })

    it('can remove tags by clicking X on chip', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      expect(screen.getByText('moth')).toBeInTheDocument()

      // Click remove button
      const removeButton = screen.getByLabelText(/Remove tag moth/i)
      await user.click(removeButton)

      expect(screen.queryByText('moth')).not.toBeInTheDocument()
    })

    it('prevents duplicate tags (case-insensitive)', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'MOTH{Enter}')

      // Should only have one "moth" tag (case-insensitive duplicate rejected)
      const mothTags = screen.getAllByText('moth')
      expect(mothTags).toHaveLength(1)
    })

    it('shows existing tags in dropdown when typing', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'mo')

      // Wait for dropdown to appear with filtered suggestions
      await waitFor(() => {
        expect(screen.getByText('(10)')).toBeInTheDocument() // moth count
      })
    })
  })

  describe('Action Buttons', () => {
    it('shows Cancel button', () => {
      renderModal()
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
    })

    it('shows Apply button', () => {
      renderModal()
      expect(screen.getByRole('button', { name: /Apply/i })).toBeInTheDocument()
    })

    it('Apply button is disabled when no tags selected', () => {
      renderModal()
      const applyButton = screen.getByRole('button', { name: /Apply/i })
      expect(applyButton).toBeDisabled()
    })

    it('Apply button is enabled when tags are selected', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      expect(applyButton).toBeEnabled()
    })

    it('Cancel button calls onClose prop', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('Apply button calls onApply with { tags, mode } in Add mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')
      await user.type(input, 'nocturnal{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['moth', 'nocturnal'],
        mode: 'add',
      })
    })

    it('Apply button calls onApply with Replace mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      // Change to Replace mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'new-tag{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['new-tag'],
        mode: 'replace',
      })
    })

    it('Apply button calls onApply with Remove mode', async () => {
      const user = userEvent.setup()
      const onApply = vi.fn()
      renderModal({ onApply })

      // Change to Remove mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Remove tags/i))

      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'unwanted-tag{Enter}')

      const applyButton = screen.getByRole('button', { name: /Apply/i })
      await user.click(applyButton)

      expect(onApply).toHaveBeenCalledWith({
        tags: ['unwanted-tag'],
        mode: 'remove',
      })
    })
  })

  describe('Modal Behavior', () => {
    it('Escape key closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('clicking backdrop closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      // Click the backdrop (not the modal content)
      const modal = screen.getByRole('dialog')
      const container = modal.parentElement!
      const backdrop = container.querySelector('.bg-black\\/50')!
      await user.click(backdrop)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does NOT close modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const modal = screen.getByRole('dialog')
      await user.click(modal)

      expect(onClose).not.toHaveBeenCalled()
    })

    it('clicking Cancel closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      await user.click(cancelButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('modal resets state when closed and reopened', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal({ isOpen: true })

      // Add tags
      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      // Change mode
      const radioGroup = screen.getByRole('radiogroup')
      await user.click(within(radioGroup).getByLabelText(/Replace tags/i))

      expect(screen.getByText('moth')).toBeInTheDocument()
      expect(within(radioGroup).getByLabelText(/Replace tags/i)).toBeChecked()

      // Close modal
      rerender(
        <QueryClientProvider client={createTestQueryClient()}>
          <BulkTagModal isOpen={false} onClose={vi.fn()} onApply={vi.fn()} selectedCount={5} />
        </QueryClientProvider>
      )

      // Reopen modal
      rerender(
        <QueryClientProvider client={createTestQueryClient()}>
          <BulkTagModal isOpen={true} onClose={vi.fn()} onApply={vi.fn()} selectedCount={5} />
        </QueryClientProvider>
      )

      // State should be reset
      expect(screen.queryByText('moth')).not.toBeInTheDocument()
      const newRadioGroup = screen.getByRole('radiogroup')
      expect(within(newRadioGroup).getByLabelText(/Add tags/i)).toBeChecked()
    })
  })

  describe('Loading/Error States', () => {
    it('shows loading state when isLoading prop is true', () => {
      renderModal({ isLoading: true })
      expect(screen.getByText(/Applying.../i)).toBeInTheDocument()
    })

    it('Apply button disabled during loading', async () => {
      const user = userEvent.setup()
      renderModal({ isLoading: true })

      // Even if we have tags, button should be disabled
      const input = screen.getByPlaceholderText(/Type to search or create tags/i)
      await user.type(input, 'moth{Enter}')

      const applyButton = screen.getByRole('button', { name: /Applying.../i })
      expect(applyButton).toBeDisabled()
    })

    it('Cancel button disabled during loading', () => {
      renderModal({ isLoading: true })
      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      expect(cancelButton).toBeDisabled()
    })

    it('shows error message when error prop provided', () => {
      renderModal({ error: 'Failed to apply tags' })
      expect(screen.getByText('Failed to apply tags')).toBeInTheDocument()
    })

    it('error message has proper styling', () => {
      renderModal({ error: 'Failed to apply tags' })
      const errorMessage = screen.getByText('Failed to apply tags')
      expect(errorMessage).toHaveClass('text-red-600')
    })
  })

  describe('Accessibility', () => {
    it('has role="dialog" and aria-modal', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby for title', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      const titleId = dialog.getAttribute('aria-labelledby')
      expect(titleId).toBeTruthy()
      expect(document.getElementById(titleId!)).toBeInTheDocument()
    })

    it('mode options are radio buttons with proper ARIA', () => {
      renderModal()
      const radioGroup = screen.getByRole('radiogroup')
      expect(radioGroup).toHaveAttribute('aria-label', 'Tag operation mode')

      const radios = within(radioGroup).getAllByRole('radio')
      expect(radios).toHaveLength(3)
      radios.forEach(radio => {
        expect(radio).toHaveAttribute('name', 'mode')
      })
    })

    it('close button has aria-label', () => {
      renderModal()
      const closeButton = screen.getByLabelText(/Close modal/i)
      expect(closeButton).toBeInTheDocument()
    })

    it('tags label is properly displayed', () => {
      renderModal()
      const label = screen.getByText('Tags')
      expect(label).toHaveClass('block')
    })
  })
})
```

**Key test changes from original:**
- `RenderModalProps` TypeScript interface for `renderModal`
- Non-null assertions (`!`) on DOM queries in backdrop test
- Radio `name` attribute check changed from `'tag-mode'` to `'mode'` (react-hook-form uses the field name)
- Error styling test renamed from "proper ARIA role" to "proper styling" (the error `<p>` doesn't have `role="alert"` — it's a prop-passed error from parent, not a form validation error)

**Step 2: Delete the old test file**

Delete: `webui/frontend/src/components/gallery/__tests__/BulkTagModal.test.jsx`

**Step 3: Run the migrated tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/components/gallery/__tests__/BulkTagModal.test.tsx`

Expected: All 26 tests PASS

**Step 4: Run the Gallery bulk-selection tests to verify no regressions**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run src/pages/__tests__/Gallery.bulk-selection.test.jsx`

Expected: All tests PASS (imports resolve to new .tsx file)

**Step 5: Commit**

```bash
git add webui/frontend/src/components/gallery/__tests__/BulkTagModal.test.tsx
git rm webui/frontend/src/components/gallery/__tests__/BulkTagModal.test.jsx
git commit -m "test(#440): migrate BulkTagModal tests to TypeScript"
```

---

### Task 6: Final Verification

**Step 1: Run all frontend tests**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vitest run 2>&1 | tail -20`

Expected: All tests pass, no regressions

**Step 2: Run production build**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx vite build 2>&1 | tail -5`

Expected: Build succeeds

**Step 3: Run linter**

Run: `cd /home/zane/projects/Mothbox/Firmware/webui/frontend && npx eslint src/schemas/tag.ts src/components/gallery/BulkTagModal.tsx src/schemas/__tests__/tag.test.ts src/components/gallery/__tests__/BulkTagModal.test.tsx`

Expected: No errors
