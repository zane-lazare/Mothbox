# Migrate SavePresetModal (filters) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the filters SavePresetModal from manual useState validation to react-hook-form + Zod with TypeScript.

**Architecture:** Clone the pattern from SaveFilterPresetModal.tsx (#438). Reuse `filterPresetNameSchema` from `src/schemas/preset.ts`. Add `defaultName` prop support via `useForm` defaultValues + reset.

**Tech Stack:** React 19, react-hook-form, Zod, @hookform/resolvers, TypeScript, Vitest, @testing-library/react, @testing-library/user-event

---

### Task 1: Write the migrated component

**Files:**
- Delete: `webui/frontend/src/components/filters/SavePresetModal.jsx`
- Create: `webui/frontend/src/components/filters/SavePresetModal.tsx`

**Step 1: Create SavePresetModal.tsx**

```tsx
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { filterPresetNameSchema, type FilterPresetNameData } from '../../schemas/preset'
import { FormField } from '../form/FormField'
import { Z_INDEX } from '../../constants/config'

interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (name: string) => void | Promise<void>
  isSaving?: boolean
  defaultName?: string
}

export default function SavePresetModal({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
  defaultName = '',
}: SavePresetModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isDirty },
  } = useForm<FilterPresetNameData>({
    resolver: zodResolver(filterPresetNameSchema),
    defaultValues: { name: defaultName },
    mode: 'onBlur',
  })

  // Reset form when modal opens or defaultName changes
  useEffect(() => {
    if (isOpen) {
      reset({ name: defaultName })
    }
  }, [isOpen, defaultName, reset])

  // Document-level Escape handler
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSaving) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, isSaving, onClose])

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
    }
  }

  return (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} overflow-y-auto`}>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={isSaving ? undefined : onClose}
        aria-hidden="true"
        data-testid="modal-backdrop"
      />

      {/* Modal */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div
          className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
          role="dialog"
          aria-modal="true"
          aria-labelledby="save-preset-title"
        >
          {/* Header */}
          <div className="mb-4">
            <h3
              id="save-preset-title"
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
              helperText="Choose a descriptive name for this filter preset"
            >
              <input
                type="text"
                {...register('name')}
                onKeyDown={handleKeyDown}
                aria-required="true"
                placeholder="e.g., Night Moths June 2024"
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
                    <span className="inline-block animate-spin mr-2">&#x231B;</span>
                    Saving...
                  </>
                ) : (
                  'Save Preset'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Update barrel export**

In `webui/frontend/src/components/filters/index.js`, the existing line:
```js
export { default as SavePresetModal } from './SavePresetModal'
```
No change needed — default export name is preserved, `.tsx` extension is resolved automatically by Vite.

**Step 3: Delete the old file**

```bash
rm webui/frontend/src/components/filters/SavePresetModal.jsx
```

**Step 4: Verify the component compiles**

```bash
cd webui/frontend && npx tsc --noEmit --pretty 2>&1 | head -30
```

Expected: No errors related to SavePresetModal.

**Step 5: Commit**

```bash
git add webui/frontend/src/components/filters/SavePresetModal.tsx
git add webui/frontend/src/components/filters/SavePresetModal.jsx
git commit -m "feat(#439): migrate filters SavePresetModal to react-hook-form + Zod + TypeScript"
```

---

### Task 2: Write the migrated tests

**Files:**
- Delete: `webui/frontend/src/components/filters/__tests__/SavePresetModal.test.jsx`
- Create: `webui/frontend/src/components/filters/__tests__/SavePresetModal.test.tsx`

**Step 1: Create SavePresetModal.test.tsx**

Follow the exact test structure from `SaveFilterPresetModal.test.tsx` but add `defaultName` tests.

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SavePresetModal from '../SavePresetModal'

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSave: vi.fn(),
}

function renderModal(overrides = {}) {
  return render(<SavePresetModal {...defaultProps} {...overrides} />)
}

describe('SavePresetModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

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
      await user.type(input, 'ab')
      await user.tab()
      expect(await screen.findByRole('alert')).toBeInTheDocument()

      await user.click(input)
      await user.type(input, 'cde')
      await user.tab()

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Save flow', () => {
    it('calls onSave with trimmed name on submit', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, '  My Preset  ')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onSave).toHaveBeenCalledWith('My Preset')
      expect(onSave).toHaveBeenCalledTimes(1)
    })

    it('does not call onSave when form is empty', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const saveButton = screen.getByRole('button', { name: 'Save Preset' })
      expect(saveButton).toBeDisabled()
      await user.click(saveButton)

      expect(onSave).not.toHaveBeenCalled()
    })

    it('shows validation error when submitting invalid name via Enter', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn()
      renderModal({ onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.type(input, '{Enter}')

      expect(await screen.findByRole('alert')).toBeInTheDocument()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('calls onClose after successful save', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      const onSave = vi.fn()
      renderModal({ onClose, onSave })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('keeps modal open when onSave throws', async () => {
      const user = userEvent.setup()
      const onSave = vi.fn().mockRejectedValue(new Error('save failed'))
      const onClose = vi.fn()
      renderModal({ onSave, onClose })

      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'My Preset')
      await user.tab()
      await user.click(screen.getByRole('button', { name: 'Save Preset' }))

      expect(onClose).not.toHaveBeenCalled()
      expect(screen.getByRole('dialog')).toBeInTheDocument()
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

      await user.click(screen.getByTestId('modal-backdrop'))

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close modal on backdrop click while saving', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ isSaving: true, onClose })

      await user.click(screen.getByTestId('modal-backdrop'))

      expect(onClose).not.toHaveBeenCalled()
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

    it('closes modal on Escape key from any focused element', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ onClose })

      await user.tab()
      await user.tab()
      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close modal on Escape key while saving', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      renderModal({ isSaving: true, onClose })

      await user.keyboard('{Escape}')

      expect(onClose).not.toHaveBeenCalled()
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

  describe('Default name', () => {
    it('populates input with defaultName prop', () => {
      renderModal({ defaultName: 'Default Preset' })

      expect(screen.getByLabelText('Preset Name *')).toHaveValue('Default Preset')
    })

    it('resets to defaultName when modal reopens', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal({ defaultName: 'Default' })

      const input = screen.getByLabelText('Preset Name *')
      await user.clear(input)
      await user.type(input, 'Modified')

      // Close and reopen
      rerender(<SavePresetModal {...defaultProps} isOpen={false} defaultName="Default" />)
      rerender(<SavePresetModal {...defaultProps} isOpen={true} defaultName="Default" />)

      expect(screen.getByLabelText('Preset Name *')).toHaveValue('Default')
    })

    it('marks form as dirty when defaultName is edited', async () => {
      const user = userEvent.setup()
      renderModal({ defaultName: 'Default' })

      // Save should be disabled initially (not dirty)
      expect(screen.getByRole('button', { name: 'Save Preset' })).toBeDisabled()

      const input = screen.getByLabelText('Preset Name *')
      await user.clear(input)
      await user.type(input, 'Changed')
      await user.tab()

      expect(screen.getByRole('button', { name: 'Save Preset' })).not.toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has correct dialog aria attributes', () => {
      renderModal()

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'save-preset-title')
    })

    it('marks input as aria-required', () => {
      renderModal()

      expect(screen.getByLabelText('Preset Name *')).toHaveAttribute('aria-required', 'true')
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

  describe('Form reset', () => {
    it('resets form state and errors when modal reopens', async () => {
      const user = userEvent.setup()
      const { rerender } = renderModal()

      // Trigger a validation error
      const input = screen.getByLabelText('Preset Name *')
      await user.type(input, 'ab')
      await user.tab()
      expect(await screen.findByRole('alert')).toBeInTheDocument()

      // Close modal
      rerender(<SavePresetModal {...defaultProps} isOpen={false} />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

      // Reopen modal — form and errors should be reset
      rerender(<SavePresetModal {...defaultProps} isOpen={true} />)
      const newInput = screen.getByLabelText('Preset Name *')
      expect(newInput).toHaveValue('')
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })
})
```

**Step 2: Delete old test file**

```bash
rm webui/frontend/src/components/filters/__tests__/SavePresetModal.test.jsx
```

**Step 3: Run the tests**

```bash
cd webui/frontend && npx vitest run src/components/filters/__tests__/SavePresetModal.test.tsx --reporter=verbose 2>&1 | tail -40
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add webui/frontend/src/components/filters/__tests__/SavePresetModal.test.tsx
git add webui/frontend/src/components/filters/__tests__/SavePresetModal.test.jsx
git commit -m "test(#439): migrate SavePresetModal tests to TypeScript + userEvent"
```

---

### Task 3: Run full validation and update schema doc comment

**Files:**
- Modify: `webui/frontend/src/schemas/preset.ts` (update doc comment to mention both consumers)

**Step 1: Update preset.ts doc comment**

Change line 7 from:
```ts
 * Used by SaveFilterPresetModal.tsx via zodResolver.
```
to:
```ts
 * Used by SaveFilterPresetModal.tsx and SavePresetModal.tsx via zodResolver.
```

**Step 2: Run TypeScript check**

```bash
cd webui/frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

Expected: No errors.

**Step 3: Run both modal test files to verify no regressions**

```bash
cd webui/frontend && npx vitest run src/components/filters/__tests__/ --reporter=verbose 2>&1 | tail -40
```

Expected: All tests pass for both SavePresetModal and SaveFilterPresetModal.

**Step 4: Commit**

```bash
git add webui/frontend/src/schemas/preset.ts
git commit -m "docs(#439): update preset schema comment to list both consumers"
```
