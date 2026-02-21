# SaveFilterPresetModal Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate SaveFilterPresetModal from manual useState validation to react-hook-form + Zod, converting .jsx to .tsx with new tests.

**Architecture:** Single-field modal using the "Modal (Uncontrolled)" pattern from the form validation design. The form remounts each time `isOpen` becomes true (early return pattern), so `useForm` gets a fresh instance automatically. Zod schema (`filterPresetNameSchema` from `src/schemas/preset.ts`) is the single source of truth for validation. FormField component handles error display and aria attributes.

**Tech Stack:** React 19, react-hook-form 7.71+, Zod 4.3+, @hookform/resolvers 5.2+, TypeScript, Vitest, @testing-library/react, userEvent

**Issue:** #438 | **Design doc:** `docs/plans/2026-02-21-save-filter-preset-modal-migration.md`

---

### Task 1: Write the component TypeScript file

**Files:**
- Create: `webui/frontend/src/components/filters/SaveFilterPresetModal.tsx`

**Step 1: Create SaveFilterPresetModal.tsx**

This replaces `SaveFilterPresetModal.jsx` entirely. The component uses `useForm` with `zodResolver`, `register('name')` on the input, and `FormField` for error display. The `if (!isOpen) return null` pattern gives free form reset on each open.

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { filterPresetNameSchema, type FilterPresetNameData } from '../../schemas/preset'
import { FormField } from '../form/FormField'
import { Z_INDEX } from '../../constants/config'

interface SaveFilterPresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (name: string) => void | Promise<void>
  isSaving?: boolean
}

export function SaveFilterPresetModal({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
}: SaveFilterPresetModalProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty },
  } = useForm<FilterPresetNameData>({
    resolver: zodResolver(filterPresetNameSchema),
    defaultValues: { name: '' },
    mode: 'onBlur',
  })

  if (!isOpen) return null

  const onSubmit = async (data: FilterPresetNameData) => {
    try {
      await onSave(data.name)
      onClose()
    } catch (error) {
      console.error('Error saving preset:', error)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(onSubmit)()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    }
  }

  return (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} overflow-y-auto`}>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div
          className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          {/* Header */}
          <div className="mb-4">
            <h3
              id="modal-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Save Filter Preset
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Save your current filter settings for quick access later
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              name="name"
              label="Preset Name *"
              error={errors.name}
              helperText="Choose a descriptive name for this filter combination"
            >
              <input
                type="text"
                {...register('name')}
                onKeyDown={handleKeyDown}
                placeholder="e.g., Moths from June 2024"
                disabled={isSaving}
                autoFocus
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 ${
                  errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                } disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed`}
              />
            </FormField>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSaving}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving || !isValid || !isDirty}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {isSaving ? (
                  <>
                    <span className="inline-block animate-spin mr-2">⏳</span>
                    Saving...
                  </>
                ) : (
                  'Save Preset'
                )}
              </button>
            </div>
          </form>

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-800 dark:text-blue-300">
              <span className="font-semibold">ℹ️ Note:</span> This will save your current filter
              settings. You can load this preset later to quickly apply these filters.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SaveFilterPresetModal
```

Key differences from the old `.jsx`:
- `useForm` replaces `useState` for `presetName` and `nameError`
- `register('name')` replaces manual `value`/`onChange` on the input
- `FormField` replaces manual label, error `<p>`, and helper text rendering
- `handleSubmit(onSubmit)` replaces manual `validateName()` call
- Submit button uses `type="submit"` and `!isValid || !isDirty` instead of `type="button"` with manual checks
- The form wraps the fields with `<form onSubmit={...}>` for proper HTML form semantics
- `onClose` called directly (no wrapper needed — form resets on remount)
- `onSave` receives `data.name` which Zod has already trimmed

**Step 2: Delete the old .jsx file**

```bash
cd webui/frontend
git rm src/components/filters/SaveFilterPresetModal.jsx
```

**Step 3: Verify the build compiles**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: No errors related to SaveFilterPresetModal. (Other pre-existing TS errors in unrelated files are OK.)

**Step 4: Commit**

```bash
git add src/components/filters/SaveFilterPresetModal.tsx
git commit -m "feat(#438): migrate SaveFilterPresetModal to react-hook-form + Zod

Replace manual useState validation with useForm + zodResolver.
Convert .jsx to .tsx with TypeScript interface for props.
Use FormField for standardized error display and aria attributes.
Remove PropTypes dependency."
```

---

### Task 2: Write the test file — rendering and validation tests

**Files:**
- Create: `webui/frontend/src/components/filters/__tests__/SaveFilterPresetModal.test.tsx`

**Step 1: Write rendering and validation tests**

Create the test file with the first two test groups. Uses `userEvent` for realistic interactions (blur triggers via `tab()`).

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { SaveFilterPresetModal } from '../SaveFilterPresetModal'

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSave: vi.fn(),
}

function renderModal(overrides = {}) {
  return render(<SaveFilterPresetModal {...defaultProps} {...overrides} />)
}

describe('SaveFilterPresetModal', () => {
  describe('Rendering', () => {
    it('renders modal when open', () => {
      renderModal()

      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('Save Filter Preset')).toBeInTheDocument()
      expect(screen.getByLabelText('Preset Name *')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeInTheDocument()
    })

    it('renders nothing when closed', () => {
      renderModal({ isOpen: false })

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('shows saving state', () => {
      renderModal({ isSaving: true })

      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.getByLabelText('Preset Name *')).toBeDisabled()
    })
  })

  describe('Validation', () => {
    it('shows error for empty name on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.click(input)
      await user.type(input, 'a')
      await user.clear(input)
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent('Preset name is required')
    })

    it('shows error for name shorter than 3 characters on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Name must be at least 3 characters'
      )
    })

    it('shows error for name exceeding 50 characters on blur', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'a'.repeat(51))
      await user.tab()

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Name must be less than 50 characters'
      )
    })

    it('shows no error for valid name', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'Valid Preset Name')
      await user.tab()

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('clears error after correcting input', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      // Type too-short name and blur to trigger error
      await user.type(input, 'ab')
      await user.tab()
      expect(await screen.findByRole('alert')).toBeInTheDocument()

      // Fix the name and blur again
      await user.click(input)
      await user.type(input, 'cde')
      await user.tab()

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })
})
```

**Step 2: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/filters/__tests__/SaveFilterPresetModal.test.tsx`

Expected: 8 tests pass.

**Step 3: Commit**

```bash
git add src/components/filters/__tests__/SaveFilterPresetModal.test.tsx
git commit -m "test(#438): add rendering and validation tests for SaveFilterPresetModal"
```

---

### Task 3: Add save flow, cancel, keyboard, disabled state, and accessibility tests

**Files:**
- Modify: `webui/frontend/src/components/filters/__tests__/SaveFilterPresetModal.test.tsx`

**Step 1: Append remaining test groups**

Add these describe blocks after the `Validation` block inside the outer `describe`:

```tsx
  describe('Save flow', () => {
    it('calls onSave with trimmed name on submit', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, '  My Preset  ')
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onSave).toHaveBeenCalledWith('My Preset')
      expect(onSave).toHaveBeenCalledTimes(1)
    })

    it('does not call onSave when form is invalid', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      // Try to submit without entering a name (button should be disabled)
      const saveButton = screen.getByRole('button', { name: 'Save Preset' })
      expect(saveButton).toBeDisabled()
      await user.click(saveButton)

      expect(onSave).not.toHaveBeenCalled()
    })

    it('calls onClose after successful save', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      const onSave = vi.fn()
      renderModal({ onClose, onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Cancel and close', () => {
    it('calls onClose when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.click(screen.getByRole('button', { name: 'Cancel' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when backdrop is clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      // Backdrop is the element with aria-hidden="true"
      const backdrop = screen.getByRole('dialog').parentElement!
        .previousElementSibling as HTMLElement
      await user.click(backdrop)

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Keyboard shortcuts', () => {
    it('submits form on Enter key with valid input', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.type(input, '{Enter}')

      expect(onSave).toHaveBeenCalledWith('My Preset')
    })

    it('closes modal on Escape key', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      const input = screen.getByLabelText('Preset Name *')
      await user.click(input)
      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Disabled states', () => {
    it('disables save button when input is empty', () => {
      renderModal()

      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeDisabled()
    })

    it('disables save button when validation error exists', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      await screen.findByRole('alert')
      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeDisabled()
    })

    it('disables save button and input when isSaving is true', () => {
      renderModal({ isSaving: true })

      expect(screen.getByLabelText('Preset Name *')).toBeDisabled()
      expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has correct dialog aria attributes', () => {
      renderModal()

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title')
    })

    it('sets aria-invalid and aria-describedby on errored input', async () => {
      const user = userEvent.setup()
      renderModal()

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()

      await screen.findByRole('alert')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      expect(input).toHaveAttribute('aria-describedby', 'name-error')
    })
  })
```

**Step 2: Run all tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/filters/__tests__/SaveFilterPresetModal.test.tsx`

Expected: 20 tests pass (8 from Task 2 + 12 new).

**Step 3: Commit**

```bash
git add src/components/filters/__tests__/SaveFilterPresetModal.test.tsx
git commit -m "test(#438): add save flow, keyboard, disabled state, and a11y tests"
```

---

### Task 4: Final verification

**Step 1: Run the full test file one more time**

Run: `cd webui/frontend && npx vitest run src/components/filters/__tests__/SaveFilterPresetModal.test.tsx --reporter=verbose`

Expected: All 20 tests pass with names visible.

**Step 2: Run TypeScript check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | grep -i 'SaveFilterPresetModal' || echo "No TS errors for this file"`

Expected: No errors for SaveFilterPresetModal.

**Step 3: Run the consumer's tests to check nothing broke**

Run: `cd webui/frontend && npx vitest run src/components/filters/__tests__/FilterPresetManager.test.jsx`

Expected: All FilterPresetManager tests pass (the import resolves `.tsx` automatically).

**Step 4: Run lint**

Run: `cd webui/frontend && npx eslint src/components/filters/SaveFilterPresetModal.tsx`

Expected: No errors.

**Step 5: Verify the old .jsx is gone and no stale imports remain**

Run: `cd webui/frontend && ls src/components/filters/SaveFilterPresetModal.* 2>&1`

Expected: Only `SaveFilterPresetModal.tsx` exists (no `.jsx`).

Run: `cd webui/frontend && grep -r 'SaveFilterPresetModal.jsx' src/ || echo "No stale .jsx imports"`

Expected: No stale imports found.
