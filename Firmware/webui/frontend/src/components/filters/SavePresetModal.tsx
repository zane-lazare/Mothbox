import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { filterPresetNameSchema, type FilterPresetNameData } from '../../schemas/preset'
import { FormField } from '../form/FormField'
import { Z_INDEX } from '../../constants/config'

interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  /** Called with the trimmed preset name. Must handle its own errors — thrown errors are logged but not surfaced to the user. */
  onSave: (name: string) => void | Promise<void>
  isSaving?: boolean
  defaultName?: string
}

export function SavePresetModal({
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

  // Document-level Escape handler (works regardless of focus position)
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

  // Explicit Enter handler — happy-dom doesn't support implicit form
  // submission, and this ensures consistent behavior across environments.
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
          // TODO(#462): Add focus trap wrapper here
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
              helperText="Choose a descriptive name for this filter combination"
            >
              <input
                type="text"
                {...register('name')}
                onKeyDown={handleKeyDown}
                aria-required="true"
                placeholder="Enter preset name..."
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
                // With mode:'onBlur', isValid stays false until first blur.
                // Clicking the button blurs the input first, so the second click works.
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

export default SavePresetModal
