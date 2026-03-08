# Migrate BulkSpeciesModal to react-hook-form + Zod — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate BulkSpeciesModal from manual useState validation to react-hook-form + Zod with TypeScript, creating a reusable species schema.

**Architecture:** Modal (uncontrolled) pattern — form owns state via `useForm`, calls parent `onApply` on submit with snake_case field mapping. Zod schema is the single source of truth for validation and types.

**Tech Stack:** React 19, react-hook-form 7.71, Zod 4.3, Vitest, @testing-library/react

---

### Task 1: Create species schema

**Files:**
- Create: `webui/frontend/src/schemas/species.ts`

**Step 1: Create the schema file**

```typescript
import { z } from 'zod'
import { METADATA_VALIDATION } from '../constants/config'

/**
 * Confidence levels for species identification.
 * Matches SPECIES_CONFIG.CONFIDENCE_OPTIONS values in config.js.
 */
export const CONFIDENCE_VALUES = ['certain', 'probable', 'possible', 'unknown'] as const

/**
 * Species identification schema.
 *
 * Used by BulkSpeciesModal.tsx (Phase 1) and MetadataSpecies (Phase 2).
 * All fields are optional at the schema level — individual components
 * enforce "required" via submit-button disable logic as appropriate.
 */
export const speciesSchema = z.object({
  species: z.string().trim().max(METADATA_VALIDATION.MAX_SPECIES_LENGTH, 'Species name is too long').optional().or(z.literal('')),
  commonName: z.string().trim().max(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH, 'Common name is too long').optional().or(z.literal('')),
  confidence: z.enum(CONFIDENCE_VALUES),
  referenceUrl: z.string().url('Invalid URL').max(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH, 'URL is too long').optional().or(z.literal('')),
})

export type SpeciesFormData = z.infer<typeof speciesSchema>
```

**Step 2: Commit**

```bash
git add webui/frontend/src/schemas/species.ts
git commit -m "feat(#441): create species.ts Zod schema with confidence enum"
```

---

### Task 2: Write schema tests

**Files:**
- Create: `webui/frontend/src/schemas/__tests__/species.test.ts`

**Step 1: Write schema unit tests**

Follow the pattern from `src/schemas/__tests__/preset.test.ts`. Pure Zod tests — no React rendering.

```typescript
import { describe, it, expect } from 'vitest'
import { speciesSchema, CONFIDENCE_VALUES } from '../species'
import { METADATA_VALIDATION } from '../../constants/config'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(result: { success: boolean; error?: { issues: { message: string }[] } }): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

describe('speciesSchema', () => {
  describe('valid data', () => {
    it('accepts all fields populated', () => {
      const result = speciesSchema.safeParse({
        species: 'Manduca sexta',
        commonName: 'Tobacco Hornworm',
        confidence: 'certain',
        referenceUrl: 'https://example.com/species/123',
      })
      expect(result.success).toBe(true)
    })

    it('accepts minimal data (confidence only)', () => {
      const result = speciesSchema.safeParse({ confidence: 'unknown' })
      expect(result.success).toBe(true)
    })

    it('accepts empty strings for optional fields', () => {
      const result = speciesSchema.safeParse({
        species: '',
        commonName: '',
        confidence: 'probable',
        referenceUrl: '',
      })
      expect(result.success).toBe(true)
    })

    it('accepts all confidence values', () => {
      for (const value of CONFIDENCE_VALUES) {
        const result = speciesSchema.safeParse({ confidence: value })
        expect(result.success).toBe(true)
      }
    })
  })

  describe('confidence validation', () => {
    it('rejects invalid confidence value', () => {
      const result = speciesSchema.safeParse({ confidence: 'maybe' })
      expect(result.success).toBe(false)
    })

    it('rejects missing confidence', () => {
      const result = speciesSchema.safeParse({ species: 'Manduca sexta' })
      expect(result.success).toBe(false)
    })
  })

  describe('string length limits', () => {
    it('accepts species at max length', () => {
      const result = speciesSchema.safeParse({
        species: 'a'.repeat(METADATA_VALIDATION.MAX_SPECIES_LENGTH),
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
    })

    it('rejects species exceeding max length', () => {
      const result = speciesSchema.safeParse({
        species: 'a'.repeat(METADATA_VALIDATION.MAX_SPECIES_LENGTH + 1),
        confidence: 'probable',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Species name is too long')
    })

    it('accepts commonName at max length', () => {
      const result = speciesSchema.safeParse({
        commonName: 'a'.repeat(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH),
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
    })

    it('rejects commonName exceeding max length', () => {
      const result = speciesSchema.safeParse({
        commonName: 'a'.repeat(METADATA_VALIDATION.MAX_COMMON_NAME_LENGTH + 1),
        confidence: 'probable',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Common name is too long')
    })
  })

  describe('whitespace trimming', () => {
    it('trims species whitespace', () => {
      const result = speciesSchema.safeParse({
        species: '  Manduca sexta  ',
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.species).toBe('Manduca sexta')
      }
    })

    it('trims commonName whitespace', () => {
      const result = speciesSchema.safeParse({
        species: 'Manduca sexta',
        commonName: '  Tobacco Hornworm  ',
        confidence: 'probable',
      })
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.commonName).toBe('Tobacco Hornworm')
      }
    })
  })

  describe('referenceUrl validation', () => {
    it('accepts a valid URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'https://www.inaturalist.org/taxa/12345',
      })
      expect(result.success).toBe(true)
    })

    it('rejects an invalid URL', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'not-a-url',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Invalid URL')
    })

    it('rejects URL exceeding max length', () => {
      const result = speciesSchema.safeParse({
        confidence: 'probable',
        referenceUrl: 'https://example.com/' + 'a'.repeat(METADATA_VALIDATION.MAX_REFERENCE_URL_LENGTH),
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('URL is too long')
    })
  })
})
```

**Step 2: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/species.test.ts`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/schemas/__tests__/species.test.ts
git commit -m "test(#441): add species schema unit tests"
```

---

### Task 3: Update schemas index

**Files:**
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Add species re-exports**

Add these lines to `src/schemas/index.ts`:

```typescript
export { speciesSchema, CONFIDENCE_VALUES } from './species';
export type { SpeciesFormData } from './species';
```

**Step 2: Commit**

```bash
git add webui/frontend/src/schemas/index.ts
git commit -m "feat(#441): re-export species schema from schemas/index"
```

---

### Task 4: Migrate BulkSpeciesModal component to TypeScript + react-hook-form

**Files:**
- Delete: `webui/frontend/src/components/gallery/BulkSpeciesModal.jsx`
- Create: `webui/frontend/src/components/gallery/BulkSpeciesModal.tsx`

**Context:**
- Consumer: `src/pages/Gallery.jsx` imports `BulkSpeciesModal` as default import (no extension in path, so Vite resolves `.tsx` automatically)
- Current component: 225 LOC, 3 useState fields, no `<form>` element, button onClick validation
- The `onApply` callback receives snake_case keys: `{ species, species_common_name?, species_confidence }`

**Step 1: Delete old .jsx and create new .tsx**

Delete `BulkSpeciesModal.jsx`. Write `BulkSpeciesModal.tsx`:

```tsx
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { speciesSchema, type SpeciesFormData } from '../../schemas/species'
import { SPECIES_CONFIG, Z_INDEX } from '../../constants/config'

interface BulkSpeciesModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Apply handler - receives { species, species_common_name?, species_confidence } */
  onApply: (data: { species: string; species_common_name?: string; species_confidence: string }) => void
  /** Number of selected photos */
  selectedCount: number
  /** Loading state */
  isLoading?: boolean
  /** Error message */
  error?: string | null
}

export default function BulkSpeciesModal({
  isOpen,
  onClose,
  onApply,
  selectedCount,
  isLoading = false,
  error = null,
}: BulkSpeciesModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
  } = useForm<SpeciesFormData>({
    resolver: zodResolver(speciesSchema),
    defaultValues: { species: '', commonName: '', confidence: 'probable' },
    mode: 'onBlur',
  })

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      reset({ species: '', commonName: '', confidence: 'probable' })
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

  const onSubmit = (data: SpeciesFormData) => {
    const trimmedSpecies = (data.species ?? '').trim()
    const trimmedCommonName = (data.commonName ?? '').trim()

    if (!trimmedSpecies) return

    const payload: { species: string; species_common_name?: string; species_confidence: string } = {
      species: trimmedSpecies,
      species_confidence: data.confidence,
    }

    if (trimmedCommonName) {
      payload.species_common_name = trimmedCommonName
    }

    onApply(payload)
  }

  const speciesValue = watch('species')
  const isApplyDisabled = !(speciesValue ?? '').trim() || isLoading

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
        aria-labelledby="bulk-species-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-species-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Set species for {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
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

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Species Name Input (Required) */}
          <div>
            <label
              htmlFor="species-name"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Species Name <span className="text-red-500">*</span>
            </label>
            <input
              id="species-name"
              type="text"
              {...register('species')}
              placeholder="e.g., Danaus plexippus"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Common Name Input (Optional) */}
          <div>
            <label
              htmlFor="common-name"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Common Name
            </label>
            <input
              id="common-name"
              type="text"
              {...register('commonName')}
              placeholder="e.g., Monarch Butterfly"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Confidence Dropdown */}
          <div>
            <label
              htmlFor="confidence"
              className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-100"
            >
              Confidence
            </label>
            <select
              id="confidence"
              {...register('confidence')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600
                         rounded-md bg-white dark:bg-gray-700
                         text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {SPECIES_CONFIG.CONFIDENCE_OPTIONS.map((option: { value: string; label: string }) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Error message */}
          {error && (
            <p role="alert" className="text-red-600 dark:text-red-400 text-sm">
              {error}
            </p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 mt-6">
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
              disabled={isApplyDisabled}
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

**Key differences from original:**
- `useForm` replaces 3x `useState`
- `register()` spreads on inputs instead of manual `value`/`onChange`
- Proper `<form>` element wraps fields and buttons
- `handleSubmit(onSubmit)` on the form's `onSubmit`
- Close button gets `type="button"` to prevent form submission
- `watch('species')` replaces direct state access for disabled check
- `reset()` in useEffect replaces manual state clearing
- TypeScript interface replaces PropTypes
- No `required` HTML attribute (react-hook-form handles validation)

**Step 2: Commit**

```bash
git add webui/frontend/src/components/gallery/BulkSpeciesModal.tsx
git rm webui/frontend/src/components/gallery/BulkSpeciesModal.jsx
git commit -m "feat(#441): migrate BulkSpeciesModal to react-hook-form + Zod + TypeScript"
```

---

### Task 5: Migrate component tests to TypeScript

**Files:**
- Delete: `webui/frontend/src/components/gallery/__tests__/BulkSpeciesModal.test.jsx`
- Create: `webui/frontend/src/components/gallery/__tests__/BulkSpeciesModal.test.tsx`

**Context:**
- All 20 existing tests are preserved with minimal changes
- The `required` attribute test is removed (react-hook-form doesn't add HTML `required`)
- Form is now a `<form>` element, so test interactions remain the same
- `register('species')` generates an input with `name="species"`, so `getByLabelText` still works via the `<label htmlFor="species-name">` + `id="species-name"` pairing

**Step 1: Delete old .test.jsx and create new .test.tsx**

Delete `BulkSpeciesModal.test.jsx`. Write `BulkSpeciesModal.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BulkSpeciesModal from '../BulkSpeciesModal'

describe('BulkSpeciesModal', () => {
  const mockOnClose = vi.fn()
  const mockOnApply = vi.fn()

  const defaultProps = {
    isOpen: true as const,
    onClose: mockOnClose,
    onApply: mockOnApply,
    selectedCount: 5,
    isLoading: false,
    error: null as string | null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('does NOT render when isOpen is false', () => {
      render(<BulkSpeciesModal {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByLabelText(/close modal/i)).toBeInTheDocument()
    })

    it('shows "Set species for X photos" title', () => {
      render(<BulkSpeciesModal {...defaultProps} selectedCount={5} />)

      expect(screen.getByText(/Set species for 5 photos/i)).toBeInTheDocument()
    })

    it('shows "Set species for 1 photo" title for single photo', () => {
      render(<BulkSpeciesModal {...defaultProps} selectedCount={1} />)

      expect(screen.getByText(/Set species for 1 photo$/i)).toBeInTheDocument()
    })
  })

  describe('Form Fields', () => {
    it('shows species name input', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const input = screen.getByLabelText(/species name/i)
      expect(input).toBeInTheDocument()
    })

    it('shows common name input', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const input = screen.getByLabelText(/common name/i)
      expect(input).toBeInTheDocument()
    })

    it('shows confidence dropdown with options: Certain, Probable, Possible, Unknown', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const select = screen.getByLabelText(/confidence/i)
      expect(select).toBeInTheDocument()

      expect(screen.getByRole('option', { name: 'Certain' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Probable' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Possible' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
    })

    it('confidence defaults to "Probable"', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const select = screen.getByLabelText(/confidence/i)
      expect(select).toHaveValue('probable')
    })
  })

  describe('Validation', () => {
    it('Apply button disabled when species name is empty', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const applyButton = screen.getByRole('button', { name: /apply/i })
      expect(applyButton).toBeDisabled()
    })

    it('Apply button enabled when species name provided', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      await user.type(speciesInput, 'Danaus plexippus')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      expect(applyButton).toBeEnabled()
    })

    it('trims whitespace from inputs', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)

      await user.type(speciesInput, '  Danaus plexippus  ')
      await user.type(commonNameInput, '  Monarch Butterfly  ')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_common_name: 'Monarch Butterfly',
        species_confidence: 'probable',
      })
    })

    it('does not send species_common_name if only whitespace', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, '   ')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_confidence: 'probable',
      })
    })
  })

  describe('Action Buttons', () => {
    it('Cancel button closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('Apply button calls onApply with species data', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)
      const confidenceSelect = screen.getByLabelText(/confidence/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, 'Monarch Butterfly')
      await user.selectOptions(confidenceSelect, 'certain')

      const applyButton = screen.getByRole('button', { name: /apply/i })
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith({
        species: 'Danaus plexippus',
        species_common_name: 'Monarch Butterfly',
        species_confidence: 'certain',
      })
    })

    it('Apply button shows "Applying..." when loading', () => {
      render(<BulkSpeciesModal {...defaultProps} isLoading={true} />)

      expect(screen.getByText('Applying...')).toBeInTheDocument()
    })

    it('Cancel button disabled when loading', () => {
      render(<BulkSpeciesModal {...defaultProps} isLoading={true} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      expect(cancelButton).toBeDisabled()
    })
  })

  describe('Modal Behavior', () => {
    it('Escape closes modal', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      fireEvent.keyDown(document, { key: 'Escape' })

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('backdrop click closes modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const backdrop = screen.getByRole('dialog').parentElement!.firstChild as HTMLElement
      await user.click(backdrop)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('clicking modal content does NOT close modal', async () => {
      const user = userEvent.setup()
      render(<BulkSpeciesModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      await user.click(dialog)

      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('state resets on reopen', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<BulkSpeciesModal {...defaultProps} />)

      const speciesInput = screen.getByLabelText(/species name/i)
      const commonNameInput = screen.getByLabelText(/common name/i)
      const confidenceSelect = screen.getByLabelText(/confidence/i)

      await user.type(speciesInput, 'Danaus plexippus')
      await user.type(commonNameInput, 'Monarch Butterfly')
      await user.selectOptions(confidenceSelect, 'certain')

      // Close modal
      rerender(<BulkSpeciesModal {...defaultProps} isOpen={false} />)

      // Reopen modal
      rerender(<BulkSpeciesModal {...defaultProps} isOpen={true} />)

      // Fields should be reset
      expect(screen.getByLabelText(/species name/i)).toHaveValue('')
      expect(screen.getByLabelText(/common name/i)).toHaveValue('')
      expect(screen.getByLabelText(/confidence/i)).toHaveValue('probable')
    })
  })

  describe('Error Handling', () => {
    it('displays error message when provided', () => {
      render(<BulkSpeciesModal {...defaultProps} error="Failed to apply species" />)

      expect(screen.getByText('Failed to apply species')).toBeInTheDocument()
    })

    it('does not display error when null', () => {
      render(<BulkSpeciesModal {...defaultProps} error={null} />)

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby')
    })

    it('close button has accessible label', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      const closeButton = screen.getByLabelText(/close modal/i)
      expect(closeButton).toBeInTheDocument()
    })

    it('all form inputs have labels', () => {
      render(<BulkSpeciesModal {...defaultProps} />)

      expect(screen.getByLabelText(/species name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/common name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confidence/i)).toBeInTheDocument()
    })
  })
})
```

**Key differences from original test:**
- TypeScript (`.test.tsx`)
- `defaultProps.error` typed as `string | null`
- Backdrop access uses non-null assertion (`!`) and `as HTMLElement`
- Removed `required` attribute assertion from "species name input" test
- Removed `not.toHaveAttribute('required')` from "common name input" test

**Step 2: Run all tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/gallery/__tests__/BulkSpeciesModal.test.tsx src/schemas/__tests__/species.test.ts`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add webui/frontend/src/components/gallery/__tests__/BulkSpeciesModal.test.tsx
git rm webui/frontend/src/components/gallery/__tests__/BulkSpeciesModal.test.jsx
git commit -m "test(#441): migrate BulkSpeciesModal tests to TypeScript"
```

---

### Task 6: Run full lint + type check

**Step 1: Run lint**

Run: `cd webui/frontend && npx eslint src/schemas/species.ts src/components/gallery/BulkSpeciesModal.tsx`
Expected: No errors

**Step 2: Run type check**

Run: `cd webui/frontend && npx tsc --noEmit`
Expected: No type errors (or only pre-existing ones unrelated to this change)

**Step 3: Fix any issues found, then commit if changes were needed**

```bash
git add -A && git commit -m "fix(#441): address lint/type issues"
```

---
