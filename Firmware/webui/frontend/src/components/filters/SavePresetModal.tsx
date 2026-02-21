import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { filterPresetNameSchema, type FilterPresetNameData } from '../../schemas/preset'
import { FormField } from '../form/FormField'
import { Z_INDEX } from '../../constants/config'

interface SavePresetModalProps {
  isOpen: boolean
  onClose: () => void
  /**
   * Called with the trimmed preset name. Callers should show their own
   * toast/notification before (re-)throwing — thrown errors keep the modal
   * open but are only logged to the console.
   */
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
    watch,
    trigger,
    formState: { errors, isValid, isDirty },
  } = useForm<FilterPresetNameData>({
    resolver: zodResolver(filterPresetNameSchema),
    defaultValues: { name: defaultName },
    mode: 'onChange',
  })

  const nameValue = watch('name', '')

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

  // Reset form when modal opens or defaultName changes.
  // Eagerly validate when defaultName is provided so isValid reflects the pre-filled value.
  useEffect(() => {
    if (isOpen) {
      reset({ name: defaultName })
      if (defaultName) {
        trigger('name')
      }
    }
  }, [isOpen, defaultName, reset, trigger])

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

  const canSave = isValid && (isDirty || !!defaultName)

  if (!isOpen) return null

  return createPortal(
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center overflow-y-auto p-4`}>
      {/* Backdrop — absolute so it sits behind the dialog in paint order */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={isSaving ? undefined : onClose}
        aria-hidden="true"
        data-testid="modal-backdrop"
      />

      {/* Modal — stopPropagation prevents dialog clicks from reaching the backdrop */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transform transition-all"
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-preset-title"
        onClick={(e) => e.stopPropagation()}
        // TODO(#462): Add focus trap wrapper here
      >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
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
            <FormField
              name="name"
              label="Preset Name *"
              error={errors.name}
              helperText="Choose a descriptive name for this filter combination"
              extraDescribedBy="name-counter"
            >
              <input
                type="text"
                {...register('name')}
                onKeyDown={handleKeyDown}
                aria-required="true"
                placeholder="Enter preset name..."
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
                disabled={isSaving || !canSave}
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
        </div>
    </div>,
    document.body
  )
}

export default SavePresetModal
