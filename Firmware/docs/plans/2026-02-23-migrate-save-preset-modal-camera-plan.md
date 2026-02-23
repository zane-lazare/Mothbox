# SavePresetModal (camera) Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the camera SavePresetModal from manual useState + utility validation to react-hook-form + Zod + TypeScript (issue #443).

**Architecture:** Two-layer validation: Zod schema validates the 3 form fields (name, description, workflow) via react-hook-form's zodResolver; the 26 liveview settings rules stay as a standalone TypeScript validator called at submit time. The component uses `createPortal`, `FormField`, and follows the same pattern as the filters `SavePresetModal.tsx`.

**Tech Stack:** React 19, react-hook-form, Zod, @hookform/resolvers, TypeScript, Vitest, @testing-library/react

---

### Task 1: Zod Schema + Schema Tests

**Files:**
- Create: `webui/frontend/src/schemas/camera-preset.ts`
- Create: `webui/frontend/src/schemas/__tests__/camera-preset.test.ts`
- Modify: `webui/frontend/src/schemas/index.ts`

**Step 1: Write the schema tests**

Create `webui/frontend/src/schemas/__tests__/camera-preset.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { cameraPresetFormSchema, WORKFLOW_VALUES } from '../camera-preset'

describe('cameraPresetFormSchema', () => {
  const validData = { name: 'my_preset', description: '', workflow: 'both' as const }

  describe('name', () => {
    it('accepts valid alphanumeric+underscore names', () => {
      const result = cameraPresetFormSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('rejects empty name', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: '' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Preset name is required')
    })

    it('rejects name shorter than 3 characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'ab' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Name must be at least 3 characters')
    })

    it('rejects name with spaces or special characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'my preset!' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe(
        'Name can only contain letters, numbers, and underscores'
      )
    })

    it('rejects name longer than 50 characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'a'.repeat(51) })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Name must be 50 characters or less')
    })

    it('trims whitespace before validation', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: '  my_preset  ' })
      expect(result.success).toBe(true)
      expect(result.data!.name).toBe('my_preset')
    })
  })

  describe('description', () => {
    it('defaults to empty string when omitted', () => {
      const result = cameraPresetFormSchema.safeParse({ name: 'abc', workflow: 'both' })
      expect(result.success).toBe(true)
      expect(result.data!.description).toBe('')
    })

    it('accepts description up to 200 characters', () => {
      const result = cameraPresetFormSchema.safeParse({
        ...validData,
        description: 'x'.repeat(200),
      })
      expect(result.success).toBe(true)
    })

    it('rejects description longer than 200 characters', () => {
      const result = cameraPresetFormSchema.safeParse({
        ...validData,
        description: 'x'.repeat(201),
      })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe(
        'Description must be 200 characters or less'
      )
    })
  })

  describe('workflow', () => {
    it.each(['photo', 'liveview', 'both'] as const)('accepts "%s"', (wf) => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, workflow: wf })
      expect(result.success).toBe(true)
    })

    it('rejects invalid workflow value', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, workflow: 'invalid' })
      expect(result.success).toBe(false)
    })

    it('defaults to "both" when omitted', () => {
      const result = cameraPresetFormSchema.safeParse({ name: 'abc', description: '' })
      expect(result.success).toBe(true)
      expect(result.data!.workflow).toBe('both')
    })
  })

  describe('WORKFLOW_VALUES', () => {
    it('exports the three workflow options', () => {
      expect(WORKFLOW_VALUES).toEqual(['photo', 'liveview', 'both'])
    })
  })
})
```

**Step 2: Run schema tests to verify they fail**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/camera-preset.test.ts`
Expected: FAIL — module `../camera-preset` not found.

**Step 3: Write the schema**

Create `webui/frontend/src/schemas/camera-preset.ts`:

```typescript
import { z } from 'zod'

export const WORKFLOW_VALUES = ['photo', 'liveview', 'both'] as const

export const cameraPresetFormSchema = z.object({
  name: z.string()
    .trim()
    .min(1, 'Preset name is required')
    .min(3, 'Name must be at least 3 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Name can only contain letters, numbers, and underscores')
    .max(50, 'Name must be 50 characters or less'),
  description: z.string().max(200, 'Description must be 200 characters or less').default(''),
  workflow: z.enum(WORKFLOW_VALUES).default('both'),
})

export type CameraPresetFormData = z.infer<typeof cameraPresetFormSchema>
```

**Step 4: Re-export from schemas/index.ts**

Add to `webui/frontend/src/schemas/index.ts`:

```typescript
export { cameraPresetFormSchema, WORKFLOW_VALUES } from './camera-preset';
export type { CameraPresetFormData } from './camera-preset';
```

**Step 5: Run schema tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/schemas/__tests__/camera-preset.test.ts`
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add webui/frontend/src/schemas/camera-preset.ts \
       webui/frontend/src/schemas/__tests__/camera-preset.test.ts \
       webui/frontend/src/schemas/index.ts
git commit -m "feat(#443): add cameraPresetFormSchema Zod schema with tests"
```

---

### Task 2: Port presetValidation.js to TypeScript

**Files:**
- Rename: `webui/frontend/src/utils/presetValidation.js` → `webui/frontend/src/utils/presetValidation.ts`
- Rename: `webui/frontend/src/utils/__tests__/presetValidation.test.js` → `webui/frontend/src/utils/__tests__/presetValidation.test.ts`

**Step 1: Rename source file and add types**

Rename `presetValidation.js` → `presetValidation.ts` via `git mv`. Then add TypeScript types. The logic stays identical — only add type annotations:

Key type additions at top of file:

```typescript
import { toBackendKey } from './cameraControlMapping'

/** Result from validating a single setting. */
export interface SettingsValidationError {
  key: string
  value: unknown
  message: string
}

type Validator = (value: unknown) => boolean

interface ValidationRule {
  validator: Validator
  errorMessage: string
}
```

Type the factory functions:

```typescript
const createBooleanValidator = (): Validator => {
  return (value: unknown): boolean => {
    if (typeof value === 'boolean') return true
    const strValue = String(value).toLowerCase()
    return strValue === 'true' || strValue === 'false'
  }
}

const createEnumValidator = (allowedValues: number[]): Validator => {
  return (value: unknown): boolean => {
    try {
      const intValue = parseInt(String(value), 10)
      if (isNaN(intValue)) return false
      return allowedValues.includes(intValue)
    } catch {
      return false
    }
  }
}

const createRangeValidator = (min: number, max: number, isInteger = false): Validator => {
  return (value: unknown): boolean => {
    try {
      const numValue = isInteger ? parseInt(String(value), 10) : parseFloat(String(value))
      if (isNaN(numValue)) return false
      return numValue >= min && numValue <= max
    } catch {
      return false
    }
  }
}

const createStringEnumValidator = (allowedValues: string[]): Validator => {
  return (value: unknown): boolean => {
    const strValue = String(value).toLowerCase()
    return allowedValues.includes(strValue)
  }
}
```

Type the `LIVEVIEW_VALIDATION_RULES` object:

```typescript
export const LIVEVIEW_VALIDATION_RULES: Record<string, ValidationRule> = {
  // ... (all 26 rules stay exactly the same, no changes to values)
}
```

Type the exported functions:

```typescript
export const validateSetting = (key: string, value: unknown): SettingsValidationError | null => {
  // ... (same logic)
}

export const validatePresetSettings = (settings: Record<string, unknown>): SettingsValidationError[] => {
  // ... (same logic)
}

export const formatValidationErrors = (errors: SettingsValidationError[], maxErrors = 5): string => {
  // ... (same logic)
}
```

**Step 2: Rename test file**

Rename `presetValidation.test.js` → `presetValidation.test.ts` via `git mv`. No content changes needed — the tests import functions, not types. TypeScript will infer everything.

**Step 3: Run validation tests to verify they still pass**

Run: `cd webui/frontend && npx vitest run src/utils/__tests__/presetValidation.test.ts`
Expected: All existing tests PASS (no logic changed, only types added).

**Step 4: Commit**

```bash
git add webui/frontend/src/utils/presetValidation.ts \
       webui/frontend/src/utils/__tests__/presetValidation.test.ts
git commit -m "refactor(#443): port presetValidation to TypeScript"
```

**Note:** `git mv` handles the rename. If TypeScript complains about `cameraControlMapping.js` import, add a `// @ts-expect-error` or `declare module` — the mapping file is not being migrated in this issue.

---

### Task 3: Migrate SavePresetModal Component to TypeScript + react-hook-form

**Files:**
- Delete: `webui/frontend/src/components/SavePresetModal.jsx`
- Create: `webui/frontend/src/components/SavePresetModal.tsx`

**Step 1: Delete the old component and create the new one**

Delete `SavePresetModal.jsx` and create `SavePresetModal.tsx`. The new component follows the same pattern as `src/components/filters/SavePresetModal.tsx` (createPortal, FormField, useForm, Escape handler, backdrop click).

Full component — `webui/frontend/src/components/SavePresetModal.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { cameraPresetFormSchema, type CameraPresetFormData, WORKFLOW_VALUES } from '../schemas/camera-preset'
import { FormField } from './form/FormField'
import { validatePresetSettings, type SettingsValidationError } from '../utils/presetValidation'
import { Z_INDEX } from '../constants/config'

interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description: string
    workflow: string
    from_current: boolean
  }) => void | Promise<void>
  isSaving?: boolean
  defaultWorkflow?: typeof WORKFLOW_VALUES[number]
  currentSettings?: Record<string, unknown>
}

export function SavePresetModal({
  isOpen,
  onClose,
  onSave,
  isSaving = false,
  defaultWorkflow = 'both',
  currentSettings = {},
}: SavePresetModalProps) {
  const [settingsErrors, setSettingsErrors] = useState<SettingsValidationError[]>([])

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isValid },
  } = useForm<CameraPresetFormData>({
    resolver: zodResolver(cameraPresetFormSchema),
    defaultValues: { name: '', description: '', workflow: defaultWorkflow },
    mode: 'onChange',
  })

  const nameValue = watch('name', '')
  const descriptionValue = watch('description', '')
  const workflowValue = watch('workflow', defaultWorkflow)

  const onSubmit = async (data: CameraPresetFormData) => {
    // Validate liveview settings when workflow includes liveview
    if (data.workflow !== 'photo') {
      const errors = validatePresetSettings(currentSettings)
      if (errors.length > 0) {
        setSettingsErrors(errors)
        return
      }
    }

    try {
      await onSave({
        name: data.name,
        description: data.description.trim(),
        workflow: data.workflow,
        from_current: true,
      })
      // Reset form on success
      reset({ name: '', description: '', workflow: defaultWorkflow })
      setSettingsErrors([])
    } catch (error) {
      console.error('Error saving preset:', error)
    }
  }

  // Explicit Enter handler — happy-dom doesn't support implicit form submission
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(onSubmit)()
    }
  }

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      reset({ name: '', description: '', workflow: defaultWorkflow })
      setSettingsErrors([])
    }
  }, [isOpen, defaultWorkflow, reset])

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

  return createPortal(
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center overflow-y-auto p-4`}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={isSaving ? undefined : onClose}
        aria-hidden="true"
        data-testid="modal-backdrop"
      />

      {/* Modal */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-camera-preset-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3
              id="save-camera-preset-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Save Current Settings as Preset
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Create a reusable preset from your current camera and live view settings
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <XMarkIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name Input */}
          <FormField
            name="name"
            label="Preset Name *"
            error={errors.name}
            helperText="Use only letters, numbers, and underscores"
            extraDescribedBy="name-counter"
          >
            <input
              type="text"
              {...register('name')}
              onKeyDown={handleKeyDown}
              aria-required="true"
              placeholder="e.g., my_field_setup"
              maxLength={50}
              disabled={isSaving}
              autoFocus
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white dark:border-gray-600 ${
                errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              } disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed`}
            />
          </FormField>
          <p
            id="name-counter"
            aria-live="polite"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            {nameValue.length}/50 characters
          </p>

          {/* Description Input */}
          <FormField
            name="description"
            label="Description (optional)"
            error={errors.description}
            extraDescribedBy="description-counter"
          >
            <textarea
              {...register('description')}
              placeholder="Describe when to use this preset..."
              rows={3}
              disabled={isSaving}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-900 disabled:cursor-not-allowed"
            />
          </FormField>
          <p
            id="description-counter"
            aria-live="polite"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            {descriptionValue.length}/200 characters
          </p>

          {/* Workflow Selection */}
          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Workflow Type <span className="text-red-500">*</span>
            </legend>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="photo"
                  disabled={isSaving}
                  className="w-4 h-4 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Photo</strong> (Capture only)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="liveview"
                  disabled={isSaving}
                  className="w-4 h-4 text-green-600 focus:ring-green-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Live View</strong> (Stream only)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  {...register('workflow')}
                  value="both"
                  disabled={isSaving}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 disabled:opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  <strong>Both</strong> (Photo & Live View)
                </span>
              </label>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Choose which workflow this preset is designed for
            </p>
          </fieldset>

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
              disabled={isSaving || !isValid || !nameValue}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {isSaving ? (
                <>
                  <span className="inline-block animate-spin mr-2" aria-hidden="true">&#x231B;</span>
                  Saving...
                </>
              ) : (
                'Save Preset'
              )}
            </button>
          </div>
        </form>

        {/* Settings Validation Errors */}
        {settingsErrors.length > 0 && (
          <div
            role="alert"
            aria-live="polite"
            className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-lg max-h-48 overflow-y-auto"
          >
            <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
              Invalid Settings ({settingsErrors.length} error{settingsErrors.length > 1 ? 's' : ''})
            </p>
            <div className="space-y-1">
              {settingsErrors.slice(0, 5).map((error, index) => (
                <div key={index} className="text-xs text-red-700 dark:text-red-400">
                  <span className="font-mono bg-red-100 dark:bg-red-900/40 px-1 rounded">{error.key}</span>
                  {' = '}
                  <span className="font-mono bg-red-100 dark:bg-red-900/40 px-1 rounded">{String(error.value)}</span>
                  <div className="ml-2 text-red-600 dark:text-red-400">{error.message}</div>
                </div>
              ))}
              {settingsErrors.length > 5 && (
                <p className="text-xs text-red-600 dark:text-red-400 italic mt-2">
                  ... and {settingsErrors.length - 5} more error{settingsErrors.length - 5 > 1 ? 's' : ''}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Info */}
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
          <p className="text-xs text-blue-800 dark:text-blue-300">
            <span className="font-semibold">Note:</span> This will capture all current camera and live view settings.
            You can apply this preset later to quickly switch between configurations.
          </p>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default SavePresetModal
```

**Key changes from original:**
- `useForm` replaces manual `useState` for name/description/workflow
- `FormField` wraps name and description inputs (adds aria attributes automatically)
- `createPortal` renders to `document.body` (matches filters modal)
- `fieldset`/`legend` replaces plain `div`/`label` for radio group (accessibility)
- Dark mode classes added (matches filters modal pattern)
- `XMarkIcon` close button added (matches filters modal)
- Emojis removed from UI text (per project convention)
- `settingsErrors` stays as local `useState` (not part of form state)
- Default export preserved for backward compatibility with `Camera.jsx` and `Settings.jsx`

**Step 2: Verify the app still compiles**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No errors related to SavePresetModal.

**Step 3: Commit**

```bash
git add webui/frontend/src/components/SavePresetModal.tsx
git rm webui/frontend/src/components/SavePresetModal.jsx
git commit -m "feat(#443): migrate SavePresetModal (camera) to react-hook-form + Zod + TypeScript"
```

---

### Task 4: Migrate Component Tests

**Files:**
- Delete: `webui/frontend/src/components/__tests__/SavePresetModal.test.jsx`
- Create: `webui/frontend/src/components/__tests__/SavePresetModal.test.tsx`

**Step 1: Delete old tests and create new test file**

Delete `SavePresetModal.test.jsx` and create `SavePresetModal.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SavePresetModal } from '../SavePresetModal'
import { validatePresetSettings } from '../../utils/presetValidation'

vi.mock('../../utils/presetValidation', () => ({
  validatePresetSettings: vi.fn(() => []),
}))

const mockedValidate = vi.mocked(validatePresetSettings)

describe('SavePresetModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    isSaving: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockedValidate.mockReturnValue([])
  })

  const renderModal = (props = {}) =>
    render(<SavePresetModal {...defaultProps} {...props} />)

  describe('Rendering', () => {
    it('returns null when isOpen is false', () => {
      const { container } = renderModal({ isOpen: false })
      expect(container.innerHTML).toBe('')
    })

    it('renders modal when open with title, inputs, and buttons', () => {
      renderModal()
      expect(screen.getByText('Save Current Settings as Preset')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Describe when to use this preset...')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Save Preset')).toBeInTheDocument()
    })
  })

  describe('Name validation', () => {
    it('shows error for empty name after blur', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'a')
      await user.clear(input)
      expect(await screen.findByRole('alert')).toHaveTextContent('Preset name is required')
    })

    it('shows error for name shorter than 3 characters', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'ab')
      expect(await screen.findByText('Name must be at least 3 characters')).toBeInTheDocument()
    })

    it('shows error for invalid characters', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'my preset!')
      expect(
        await screen.findByText('Name can only contain letters, numbers, and underscores')
      ).toBeInTheDocument()
    })

    it('clears error when valid name is entered', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'ab')
      expect(await screen.findByText('Name must be at least 3 characters')).toBeInTheDocument()
      await user.type(input, 'c')
      await waitFor(() => {
        expect(screen.queryByText('Name must be at least 3 characters')).not.toBeInTheDocument()
      })
    })
  })

  describe('Description', () => {
    it('displays character counter', () => {
      renderModal()
      expect(screen.getByText('0/200 characters')).toBeInTheDocument()
    })

    it('updates character counter as user types', async () => {
      const user = userEvent.setup()
      renderModal()
      const textarea = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(textarea, 'Hello')
      expect(screen.getByText('5/200 characters')).toBeInTheDocument()
    })
  })

  describe('Workflow selection', () => {
    it('defaults to "both" workflow', () => {
      renderModal()
      const bothRadio = screen.getByRole('radio', { name: /Both/i })
      expect(bothRadio).toBeChecked()
    })

    it('selects photo workflow', async () => {
      const user = userEvent.setup()
      renderModal()
      const photoRadio = screen.getByRole('radio', { name: /Photo/i })
      await user.click(photoRadio)
      expect(photoRadio).toBeChecked()
    })

    it('uses defaultWorkflow prop', () => {
      renderModal({ defaultWorkflow: 'photo' })
      const photoRadio = screen.getByRole('radio', { name: /Photo/i })
      expect(photoRadio).toBeChecked()
    })
  })

  describe('Settings validation', () => {
    it('skips settings validation for photo-only workflow', async () => {
      const user = userEvent.setup()
      renderModal({ currentSettings: { sharpness: 99 } })
      const photoRadio = screen.getByRole('radio', { name: /Photo/i })
      await user.click(photoRadio)
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'photo_only')
      await user.click(screen.getByText('Save Preset'))
      expect(mockedValidate).not.toHaveBeenCalled()
      expect(defaultProps.onSave).toHaveBeenCalled()
    })

    it('validates settings for non-photo workflow', async () => {
      const user = userEvent.setup()
      const settings = { sharpness: 2.0 }
      renderModal({ currentSettings: settings })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'both_preset')
      await user.click(screen.getByText('Save Preset'))
      expect(mockedValidate).toHaveBeenCalledWith(settings)
    })

    it('shows settings errors and blocks save', async () => {
      const user = userEvent.setup()
      mockedValidate.mockReturnValue([
        { key: 'sharpness', value: 99, message: 'Sharpness must be between 0.0 and 4.0' },
      ])
      renderModal({ currentSettings: { sharpness: 99 } })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'bad_settings')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).not.toHaveBeenCalled()
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      expect(screen.getByText('sharpness')).toBeInTheDocument()
      expect(screen.getByText('99')).toBeInTheDocument()
      expect(screen.getByText('Sharpness must be between 0.0 and 4.0')).toBeInTheDocument()
    })

    it('truncates settings errors after 5 and shows count', async () => {
      const user = userEvent.setup()
      const errors = Array.from({ length: 7 }, (_, i) => ({
        key: `setting_${i}`,
        value: i,
        message: `Error ${i}`,
      }))
      mockedValidate.mockReturnValue(errors)
      renderModal({ currentSettings: {} })
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'many_errors')
      await user.click(screen.getByText('Save Preset'))
      expect(screen.getByText(/and 2 more/)).toBeInTheDocument()
      expect(screen.queryByText('setting_5')).not.toBeInTheDocument()
    })
  })

  describe('Save flow', () => {
    it('calls onSave with correct payload', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(descInput, 'A test description')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).toHaveBeenCalledWith({
        name: 'test_preset',
        description: 'A test description',
        workflow: 'both',
        from_current: true,
      })
    })

    it('trims description whitespace on save', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      const descInput = screen.getByPlaceholderText('Describe when to use this preset...')
      await user.type(descInput, '  padded  ')
      await user.click(screen.getByText('Save Preset'))
      expect(defaultProps.onSave).toHaveBeenCalledWith(
        expect.objectContaining({ description: 'padded' })
      )
    })

    it('resets form after successful save', async () => {
      const user = userEvent.setup()
      renderModal()
      const nameInput = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(nameInput, 'test_preset')
      await user.click(screen.getByText('Save Preset'))
      await waitFor(() => {
        expect(nameInput).toHaveValue('')
      })
    })
  })

  describe('Cancel and close', () => {
    it('calls onClose when cancel is clicked', async () => {
      const user = userEvent.setup()
      renderModal()
      await user.click(screen.getByText('Cancel'))
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose on Escape key', async () => {
      const user = userEvent.setup()
      renderModal()
      await user.keyboard('{Escape}')
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose on backdrop click', async () => {
      const user = userEvent.setup()
      renderModal()
      const backdrop = screen.getByTestId('modal-backdrop')
      await user.click(backdrop)
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('does not close on Escape when saving', async () => {
      const user = userEvent.setup()
      renderModal({ isSaving: true })
      await user.keyboard('{Escape}')
      expect(defaultProps.onClose).not.toHaveBeenCalled()
    })
  })

  describe('Disabled states', () => {
    it('disables save button when name is empty', () => {
      renderModal()
      expect(screen.getByText('Save Preset')).toBeDisabled()
    })

    it('disables all inputs and buttons when saving', () => {
      renderModal({ isSaving: true })
      expect(screen.getByPlaceholderText('e.g., my_field_setup')).toBeDisabled()
      expect(screen.getByPlaceholderText('Describe when to use this preset...')).toBeDisabled()
      expect(screen.getByText('Cancel')).toBeDisabled()
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has dialog role and aria-modal', () => {
      renderModal()
      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('sets aria-invalid on name input when invalid', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'a')
      await user.clear(input)
      await screen.findByRole('alert')
      expect(input).toHaveAttribute('aria-invalid', 'true')
    })

    it('sets aria-required on name input', () => {
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      expect(input).toHaveAttribute('aria-required', 'true')
    })

    it('has aria-describedby linking to error and counter', () => {
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      const describedBy = input.getAttribute('aria-describedby') || ''
      expect(describedBy).toContain('name-counter')
    })
  })

  describe('Keyboard', () => {
    it('submits form on Enter key in name input', async () => {
      const user = userEvent.setup()
      renderModal()
      const input = screen.getByPlaceholderText('e.g., my_field_setup')
      await user.type(input, 'enter_test')
      await user.keyboard('{Enter}')
      expect(defaultProps.onSave).toHaveBeenCalled()
    })
  })
})
```

**Step 2: Run tests to verify they pass**

Run: `cd webui/frontend && npx vitest run src/components/__tests__/SavePresetModal.test.tsx`
Expected: All tests PASS.

**Step 3: Commit**

```bash
git rm webui/frontend/src/components/__tests__/SavePresetModal.test.jsx
git add webui/frontend/src/components/__tests__/SavePresetModal.test.tsx
git commit -m "test(#443): migrate SavePresetModal (camera) tests to TypeScript"
```

---

### Task 5: Run Full Test Suite + Verify No Regressions

**Step 1: Run all schema tests**

Run: `cd webui/frontend && npx vitest run src/schemas/`
Expected: All schema tests pass (including existing preset, tag, species, export-options tests).

**Step 2: Run all presetValidation tests**

Run: `cd webui/frontend && npx vitest run src/utils/__tests__/presetValidation.test.ts`
Expected: All 26+ existing validation tests pass.

**Step 3: Run the component tests**

Run: `cd webui/frontend && npx vitest run src/components/__tests__/SavePresetModal.test.tsx`
Expected: All tests pass.

**Step 4: Run TypeScript compilation check**

Run: `cd webui/frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No type errors.

**Step 5: Build frontend**

Run: `cd webui/frontend && npm run build`
Expected: Build succeeds. `dist/` output generated.

**Step 6: Commit build output if changed**

```bash
git add webui/frontend/dist/
git commit -m "build(#443): update frontend dist after SavePresetModal migration"
```

---

### Task 6: Final Cleanup

**Step 1: Verify old .jsx files are deleted**

Run: `ls webui/frontend/src/components/SavePresetModal.jsx webui/frontend/src/components/__tests__/SavePresetModal.test.jsx 2>&1`
Expected: Both files should not exist (deleted in Tasks 3 and 4).

**Step 2: Verify old .js validation files are renamed**

Run: `ls webui/frontend/src/utils/presetValidation.js webui/frontend/src/utils/__tests__/presetValidation.test.js 2>&1`
Expected: Both files should not exist (renamed to .ts in Task 2).

**Step 3: Verify imports in parent components still work**

Check that `Camera.jsx` and `Settings.jsx` still import correctly — `import SavePresetModal from '../components/SavePresetModal'` resolves to the `.tsx` file via Vite's resolver. No changes needed in parent components.

Run: `cd webui/frontend && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: No import resolution failures.
